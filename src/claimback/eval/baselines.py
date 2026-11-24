"""Non-LLM baselines. Any ClaimBack/LLM system must beat these to mean anything."""
from __future__ import annotations

import math
import re
from collections import Counter

from .bench import model_input

_TOK = re.compile(r"[a-z]{3,}")


def _tokens(text: str) -> list[str]:
    return _TOK.findall(text.lower())


class Majority:
    name = "majority"

    def fit(self, train):
        self.label = Counter(c["outcome"] for c in train).most_common(1)[0][0]
        return self

    def predict(self, case):
        return self.label


class KeywordRule:
    """Hand rule: claims that cite an exclusion/waiting period/PED are upheld; deductions get relief."""
    name = "keyword_rule"

    def fit(self, train):
        return self

    def predict(self, case):
        t = model_input(case).lower()
        if re.search(r"pre[\s-]*existing|waiting|exclu|non[\s-]*disclos|fals|congenital|cosmetic", t):
            return "dismissed"
        return "allowed" if re.search(r"deduct|partial|proportion|capping|short", t) else "dismissed"


class TfidfKNN:
    """Precedent retrieval: majority label of the k most similar training cases (cosine on TF-IDF)."""
    name = "tfidf_knn"

    def __init__(self, k: int = 7):
        self.k = k

    def fit(self, train):
        self.train = train
        docs = [Counter(_tokens(model_input(c))) for c in train]
        df = Counter(t for d in docs for t in d)
        n = len(docs)
        self.idf = {t: math.log((1 + n) / (1 + v)) + 1 for t, v in df.items()}
        self.vecs = [self._vec(d) for d in docs]
        return self

    def _vec(self, counts):
        v = {t: (1 + math.log(c)) * self.idf.get(t, 0) for t, c in counts.items() if t in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def neighbours(self, case, k=None):
        q = self._vec(Counter(_tokens(model_input(case))))
        sims = [(sum(w * v.get(t, 0) for t, w in q.items()), i) for i, v in enumerate(self.vecs)]
        sims.sort(reverse=True)
        return [(s, self.train[i]) for s, i in sims[: k or self.k]]

    def predict(self, case):
        votes = Counter()
        for s, c in self.neighbours(case):
            votes[c["outcome"]] += s
        return votes.most_common(1)[0][0] if votes else "dismissed"


class CentreOnly:
    """Confound detector: predicts the majority outcome of the case's own centre.

    If this scores close to a 'real' system, that system is exploiting which
    centre wrote the summary, not the legal substance.
    """
    name = "centre_only"

    def fit(self, train):
        by = {}
        for c in train:
            by.setdefault(c["centre"], Counter())[c["outcome"]] += 1
        self.by = {k: v.most_common(1)[0][0] for k, v in by.items()}
        self.default = Counter(c["outcome"] for c in train).most_common(1)[0][0]
        return self

    def predict(self, case):
        return self.by.get(case["centre"], self.default)
