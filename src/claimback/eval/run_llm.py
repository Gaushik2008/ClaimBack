"""Run plain-LLM vs ClaimBack(RAG) on the Chennai leave-one-out set.  Needs NVIDIA_API_KEY.

    python -m claimback.eval.run_llm [--limit N] [--all-centres]
Writes eval/results_llm.json (aggregate metrics + citation-hallucination rate only).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .bench import labelled, load_cases, metrics
from .llm import ClaimBackLLM, PlainLLM


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="data/processed/cases.jsonl")
    ap.add_argument("--out", default="eval/results_llm.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all-centres", action="store_true", help="pooled; confounded by centre, report with care")
    a = ap.parse_args(argv)
    if "NVIDIA_API_KEY" not in os.environ:
        raise SystemExit("Set NVIDIA_API_KEY first (do not commit it).")
    pool = labelled(load_cases(a.cases))
    pool = pool if a.all_centres else [c for c in pool if c["centre"] == "Chennai"]
    pool = pool[: a.limit] if a.limit else pool
    y = [c["outcome"] for c in pool]
    res = {"n": len(pool), "scope": "all_centres" if a.all_centres else "chennai_leave_one_out", "systems": {}}
    plain = PlainLLM()
    res["systems"]["plain_llm"] = metrics(y, [plain.predict(c) for c in pool])
    preds, audit = [], []
    for i, c in enumerate(pool):
        m = ClaimBackLLM().fit(pool[:i] + pool[i + 1:])  # leave-one-out retrieval: never retrieves itself
        preds.append(m.predict(c))
        audit += m.audit
    res["systems"]["claimback_rag"] = metrics(y, preds)
    cited = sum(x["cited"] for x in audit)
    res["citation_check"] = {"cited": cited, "invalid": sum(x["invalid"] for x in audit),
                             "hallucination_rate": round(sum(x["invalid"] for x in audit) / cited, 3) if cited else None}
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
