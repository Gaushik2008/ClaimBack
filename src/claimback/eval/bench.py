"""Benchmark: predict whether the complainant gets relief, from the case facts only.

Task: binary, ``allowed`` (complainant gets relief) vs ``dismissed`` (insurer upheld).
Cases labelled ``disposed`` or ``unknown`` are excluded. Labels are rule-based
(see awards/digest.py) and NOT hand-verified; run ``audit_sample`` and check them.
Leakage control: the model sees only the facts paragraph, with any sentence that
already states the decision removed.
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from pathlib import Path

from ..awards.digest import OUTCOME_RULES

LABELS = ("allowed", "dismissed")
_LEAK = re.compile("|".join(p for _, p in OUTCOME_RULES), re.I)


def load_cases(path: str | Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def model_input(case: dict) -> str:
    sents = re.split(r"(?<=[.!?])\s+", case.get("facts") or "")
    return " ".join(s for s in sents if not _LEAK.search(s)).strip()


def labelled(cases: list[dict]) -> list[dict]:
    return [c for c in cases if c["outcome"] in LABELS and model_input(c)]


def split(cases: list[dict], test_frac: float = 0.3, seed: int = 7) -> tuple[list[dict], list[dict]]:
    """Deterministic split stratified by (centre, outcome)."""
    rng = random.Random(seed)
    groups: dict[tuple, list[dict]] = {}
    for c in sorted(labelled(cases), key=lambda c: c["case_id"]):
        groups.setdefault((c["centre"], c["outcome"]), []).append(c)
    train, test = [], []
    for k in sorted(groups, key=str):
        g = groups[k][:]
        rng.shuffle(g)
        n = max(1, round(len(g) * test_frac)) if len(g) > 1 else 0
        test += g[:n]
        train += g[n:]
    return train, test


def audit_sample(cases: list[dict], n: int = 30, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    pool = labelled(cases)
    return [{"case_id": c["case_id"], "label": c["outcome"], "text": (c["facts"] + " " + c["reasoning"])[:700],
             "human_label": ""} for c in rng.sample(pool, min(n, len(pool)))]


def metrics(y_true: list[str], y_pred: list[str], n_boot: int = 1000, seed: int = 0) -> dict:
    def acc(t, p):
        return sum(a == b for a, b in zip(t, p)) / len(t)

    def bal(t, p):
        rs = []
        for lab in LABELS:
            idx = [i for i, a in enumerate(t) if a == lab]
            if idx:
                rs.append(sum(p[i] == lab for i in idx) / len(idx))
        return sum(rs) / len(rs)

    def f1(t, p, lab):
        tp = sum(a == lab and b == lab for a, b in zip(t, p))
        fp = sum(a != lab and b == lab for a, b in zip(t, p))
        fn = sum(a == lab and b != lab for a, b in zip(t, p))
        return 2 * tp / (2 * tp + fp + fn) if tp else 0.0

    rng = random.Random(seed)
    n = len(y_true)
    boots = []
    for _ in range(n_boot):
        ix = [rng.randrange(n) for _ in range(n)]
        boots.append(bal([y_true[i] for i in ix], [y_pred[i] for i in ix]))
    boots.sort()
    return {
        "n": n,
        "accuracy": round(acc(y_true, y_pred), 3),
        "balanced_accuracy": round(bal(y_true, y_pred), 3),
        "balanced_acc_95ci": [round(boots[int(.025 * n_boot)], 3), round(boots[int(.975 * n_boot)], 3)],
        "f1_allowed": round(f1(y_true, y_pred, "allowed"), 3),
        "confusion": dict(Counter(zip(y_true, y_pred))) and {f"{a}->{b}": v for (a, b), v in Counter(zip(y_true, y_pred)).items()},
    }
