"""Interactive terminal audit tool for human validation of rule-based case outcomes.

Samples 40 cases stratified by centre (Ahmedabad, Delhi, Kolkata, Chennai).
Shows case facts and reasoning with the outcome hidden.
Prompts for user judgment: a (allowed), d (dismissed), o (disposed), or s (skip).
Outputs agreement statistics and saves aggregate-only summary to eval/label_audit_result.json.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Optional


def load_cases(path: str = "data/processed/cases_all.json") -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Processed cases file not found at {path}. Run data prep first.")
    with open(p, "r", encoding="utf-8") as f:
        cases = json.load(f)
    return cases


def sample_stratified(cases: list[dict], total: int = 40, seed: int = 42) -> list[dict]:
    """Sample cases stratified across major centres."""
    rng = random.Random(seed)
    centres = ["Ahmedabad", "Delhi", "Kolkata", "Chennai"]
    by_centre: dict[str, list[dict]] = {c: [] for c in centres}
    for case in cases:
        c = case.get("centre")
        if c in by_centre and (case.get("facts") or case.get("reasoning")):
            by_centre[c].append(case)

    per_centre = total // len(centres)
    sampled = []
    for c in centres:
        pool = by_centre[c]
        k = min(per_centre, len(pool))
        sampled.extend(rng.sample(pool, k))

    # If short of total, fill from remaining
    if len(sampled) < total:
        remaining = [c for c in cases if c not in sampled and (c.get("facts") or c.get("reasoning"))]
        sampled.extend(rng.sample(remaining, min(total - len(sampled), len(remaining))))

    rng.shuffle(sampled)
    return sampled[:total]


def run_audit(sample_size: int = 40, cases_path: str = "data/processed/cases_all.json", out_path: str = "eval/label_audit_result.json") -> dict:
    cases = load_cases(cases_path)
    sample = sample_stratified(cases, total=sample_size)

    results = []
    print("\n" + "=" * 70)
    print("CLAIMBACK HUMAN LABEL AUDIT")
    print(f"Auditing {len(sample)} sampled cases. Outcome is hidden.")
    print("Options: [a]llowed | [d]ismissed | [o]ther/disposed | [s]kip | [q]uit")
    print("=" * 70 + "\n")

    label_map = {
        "a": "allowed",
        "d": "dismissed",
        "o": "disposed",
    }

    for idx, case in enumerate(sample, 1):
        print(f"\n--- Case {idx}/{len(sample)}: {case.get('case_id')} ({case.get('centre')}) ---")
        print(f"Insurer: {case.get('insurer') or 'Unknown'}")
        if case.get("dispute_type"):
            print(f"Dispute: {case.get('dispute_type')}")
        print("\nFACTS:")
        print(case.get("facts") or "[No facts extracted]")
        if case.get("reasoning"):
            print("\nREASONING / DETAILS:")
            print(case.get("reasoning"))

        while True:
            try:
                choice = input("\nYour verdict (a/d/o/s/q): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAudit aborted by user.")
                return {}

            if choice == "q":
                print("\nEnding audit early.")
                break
            if choice == "s":
                print("Skipped.")
                break
            if choice in label_map:
                human_verdict = label_map[choice]
                rule_verdict = case.get("outcome", "unknown")
                match = (human_verdict == rule_verdict)
                print(f"Recorded: Human={human_verdict} | Rule={rule_verdict} ({'MATCH' if match else 'MISMATCH'})")
                results.append({
                    "case_id": case.get("case_id"),
                    "centre": case.get("centre"),
                    "human": human_verdict,
                    "rule": rule_verdict,
                    "match": match,
                })
                break
            print("Invalid input. Enter 'a' for allowed, 'd' for dismissed, 'o' for disposed, 's' to skip, or 'q' to quit.")

        if choice == "q":
            break

    if not results:
        print("\nNo cases were audited.")
        return {}

    n = len(results)
    matches = sum(1 for r in results if r["match"])
    agreement_rate = matches / n

    # Centre breakdown
    by_centre = {}
    for r in results:
        c = r["centre"]
        if c not in by_centre:
            by_centre[c] = {"n": 0, "matches": 0}
        by_centre[c]["n"] += 1
        if r["match"]:
            by_centre[c]["matches"] += 1

    for c, stat in by_centre.items():
        stat["agreement"] = round(stat["matches"] / stat["n"], 4) if stat["n"] > 0 else 0.0

    summary = {
        "n_audited": n,
        "n_matched": matches,
        "agreement_rate": round(agreement_rate, 4),
        "by_centre": by_centre,
        "human_distribution": dict(Counter(r["human"] for r in results)),
        "rule_distribution": dict(Counter(r["rule"] for r in results)),
    }

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY (Aggregate Only)")
    print(f"Total audited: {n}")
    print(f"Agreement with rule-based labels: {matches}/{n} ({agreement_rate:.1%})")
    print(f"Saved aggregate report to: {out_path}")
    print("=" * 70 + "\n")

    return summary


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Interactive human audit for rule-based case outcomes")
    ap.add_argument("--size", type=int, default=40, help="Number of cases to sample (default: 40)")
    ap.add_argument("--cases", default="data/processed/cases_all.json", help="Path to cases_all.json")
    ap.add_argument("--out", default="eval/label_audit_result.json", help="Output path for summary")
    args = ap.parse_args(argv)

    run_audit(sample_size=args.size, cases_path=args.cases, out_path=args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
