"""Run all baselines on the held-out split.  python -m claimback.eval.run"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .baselines import CentreOnly, KeywordRule, Majority, TfidfKNN
from .bench import audit_sample, labelled, load_cases, metrics, split


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="data/processed/cases.jsonl")
    ap.add_argument("--out", default="eval/results.json")
    ap.add_argument("--audit", default="data/processed/label_audit.json")
    a = ap.parse_args(argv)
    cases = load_cases(a.cases)
    train, test = split(cases)
    y = [c["outcome"] for c in test]
    res = {"train": len(train), "test": len(test), "test_label_counts": {l: y.count(l) for l in set(y)}, "systems": {}}
    for sys_ in (Majority(), CentreOnly(), KeywordRule(), TfidfKNN()):
        sys_.fit(train)
        res["systems"][sys_.name] = metrics(y, [sys_.predict(c) for c in test])
    # Within-centre leave-one-out on Chennai: the only centre with both outcomes in volume.
    ch = [c for c in labelled(cases) if c["centre"] == "Chennai"]
    loo = {}
    for mk in (Majority, KeywordRule, TfidfKNN):
        preds = [mk().fit(ch[:i] + ch[i + 1:]).predict(ch[i]) for i in range(len(ch))]
        loo[mk().name] = metrics([c["outcome"] for c in ch], preds)
    res["chennai_leave_one_out"] = {"n": len(ch), "systems": loo}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2))
    Path(a.audit).write_text(json.dumps(audit_sample(cases), indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
