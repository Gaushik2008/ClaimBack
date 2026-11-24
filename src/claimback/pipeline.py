"""Core analysis pipeline for ClaimBack.

Input:
- rejection_text: str (Required)
- policy_text: str (Optional)
- discharge_summary: str (Optional)
- metadata: dict (Optional dates: policy_start, admission_date, is_accident, continuity_years)

Output:
JSON containing:
- rejection_ground: str
- clause_cited: Optional[str]
- clause_verified: bool
- date_checks: list[dict]
- similar_precedents: list[{case_id, outcome, centre, why_similar}]
- verdict: "strong_appeal" | "weak_appeal" | "insurer_likely_right" | "insufficient_information"
- confidence: float
- missing_documents: list[str]
- escalation_path: dict
- centre_bias_warning: Optional[str]
- disclaimer: str
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from .privacy import mask_pii
from .policy.parser import verify_clause_presence, parse_policy
from .rules.dates import (
    parse_date,
    check_initial_waiting_period,
    check_waiting_period_months,
    check_moratorium,
)
from .eval.baselines import TfidfKNN
from .awards.digest import GROUND_RULES

DEFAULT_DISCLAIMER = "Advisory information, not legal advice."

# Cache precedents from processed corpus
CORPUS_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "cases_all.json"


def _load_corpus() -> list[dict]:
    if CORPUS_PATH.exists():
        try:
            with open(CORPUS_PATH, "r", encoding="utf-8") as f:
                cases = json.load(f)
                return [c for c in cases if c.get("outcome") in ("allowed", "dismissed")]
        except Exception:
            pass
    return []


_CACHED_CORPUS = _load_corpus()
_RETRIEVER = TfidfKNN(k=5).fit(_CACHED_CORPUS) if _CACHED_CORPUS else None


def extract_rejection_ground(text: str) -> str:
    """Rule-based ground extraction from rejection letter text."""
    lower = text.lower()
    for ground, pat in GROUND_RULES:
        if re.search(pat, lower):
            return ground
    if "first 30 days" in lower or "initial waiting" in lower:
        return "waiting_period"
    if "hypertension" in lower or "diabetes" in lower or "ped" in lower:
        return "pre_existing"
    if "clause" in lower or "section" in lower:
        return "exclusion"
    return "rejection_general"


def extract_cited_clause(text: str) -> Optional[str]:
    """Finds clause number cited in rejection letter (e.g. Clause 4.1, Condition 5.2)."""
    m = re.search(r"(?i)\b(?:clause|condition|exclusion|section|rule)\s*(?:no\.?)?\s*([0-9]+(?:\.[0-9]+)*)\b", text)
    return m.group(1) if m else None


def analyze_claim(
    rejection_text: str,
    policy_text: str = "",
    discharge_summary: str = "",
    policy_start_date: Optional[str] = None,
    admission_date: Optional[str] = None,
    is_accident: bool = False,
    continuous_coverage_years: float = 0.0,
) -> Dict[str, Any]:
    # 1. Mask PII before processing
    masked_rejection, _ = mask_pii(rejection_text)
    masked_discharge, _ = mask_pii(discharge_summary)

    # 2. Extract ground and cited clause
    ground = extract_rejection_ground(masked_rejection + " " + masked_discharge)
    clause = extract_cited_clause(masked_rejection)

    # 3. Clause verification against policy text
    clause_verified = False
    if clause and policy_text:
        clause_verified = verify_clause_presence(clause, policy_text)

    # 4. Deterministic Date & Statutory Checks
    date_checks = []
    p_date = parse_date(policy_start_date) if policy_start_date else None
    a_date = parse_date(admission_date) if admission_date else None

    if p_date and a_date:
        # Check initial 30 days
        chk_init = check_initial_waiting_period(p_date, a_date, is_accident=is_accident)
        date_checks.append({
            "check_name": chk_init.check_name,
            "passed": chk_init.passed,
            "details": chk_init.details,
            "advisory_note": chk_init.advisory_note,
        })

    if continuous_coverage_years > 0:
        chk_mora = check_moratorium(continuous_coverage_years)
        date_checks.append({
            "check_name": chk_mora.check_name,
            "passed": chk_mora.passed,
            "details": chk_mora.details,
            "advisory_note": chk_mora.advisory_note,
        })

    # 5. Retrieve Precedents
    similar_precedents = []
    centre_bias_warning = None
    if _RETRIEVER and _CACHED_CORPUS:
        query_doc = {"facts": masked_rejection + " " + masked_discharge}
        neighbours = _RETRIEVER.neighbours(query_doc, k=5)
        centres_found = set()
        for score, p in neighbours:
            centres_found.add(p.get("centre"))
            similar_precedents.append({
                "case_id": p.get("case_id"),
                "outcome": p.get("outcome"),
                "centre": p.get("centre"),
                "why_similar": f"Ombudsman {p.get('centre')} decision involving {p.get('ground', 'similar health claim')}.",
                "similarity_score": round(score, 3)
            })
        if len(centres_found) == 1 and centres_found != {None}:
            only_c = list(centres_found)[0]
            centre_bias_warning = (
                f"Caution: All retrieved precedents originate from the {only_c} Ombudsman Centre. "
                "Ombudsman decisions may show geographic outcome variation."
            )

    # 6. Missing documents detection
    missing_docs = []
    if not policy_text:
        missing_docs.append("Complete Policy Wording (including Terms & Conditions schedule)")
    if not discharge_summary:
        missing_docs.append("Hospital Discharge Summary (stating active treatment and final diagnosis)")
    if not admission_date:
        missing_docs.append("Hospital Admission and Discharge Dates")
    if not policy_start_date:
        missing_docs.append("Initial Policy Inception Date (to compute waiting period)")

    # 7. Synthesize Verdict (Deterministic rules drive verdict, precedents inform)
    # Check if evidence is thin
    if len(masked_rejection.strip()) < 30:
        verdict = "insufficient_information"
        confidence = 0.2
    else:
        # Evaluate date checks & moratorium
        moratorium_passed = any(dc["check_name"] == "moratorium_protection" and dc["passed"] for dc in date_checks)
        accident_waived = any(dc["check_name"] == "initial_30_day_waiting_period" and dc["passed"] and is_accident for dc in date_checks)
        initial_wait_failed = any(dc["check_name"] == "initial_30_day_waiting_period" and not dc["passed"] for dc in date_checks)

        if moratorium_passed:
            verdict = "strong_appeal"
            confidence = 0.90
        elif accident_waived:
            verdict = "strong_appeal"
            confidence = 0.88
        elif initial_wait_failed and not is_accident:
            verdict = "insurer_likely_right"
            confidence = 0.85
        elif clause and policy_text and not clause_verified:
            # Insurer cited a clause that doesn't exist in policy
            verdict = "strong_appeal"
            confidence = 0.80
        else:
            # Rely on precedents and ground
            allowed_count = sum(1 for p in similar_precedents if p["outcome"] == "allowed")
            dismissed_count = sum(1 for p in similar_precedents if p["outcome"] == "dismissed")
            if allowed_count >= 3:
                verdict = "strong_appeal"
                confidence = 0.75
            elif dismissed_count >= 4:
                verdict = "insurer_likely_right"
                confidence = 0.70
            elif ground in ("deduction_partial", "room_rent"):
                verdict = "strong_appeal"
                confidence = 0.72
            else:
                verdict = "weak_appeal"
                confidence = 0.55

    escalation_path = {
        "step_1": "Grievance Redressal Officer (GRO) of the Insurer (Statutory 15-day resolution turnaround)",
        "step_2": "Insurance Ombudsman (Jurisdictional centre under Redressal of Public Grievance Rules, 2017)",
        "step_3": "Consumer Disputes Redressal Commission (District/State Forum if unresolved)"
    }

    return {
        "rejection_ground": ground,
        "clause_cited": clause,
        "clause_verified": clause_verified,
        "date_checks": date_checks,
        "similar_precedents": similar_precedents,
        "verdict": verdict,
        "confidence": confidence,
        "missing_documents": missing_docs,
        "escalation_path": escalation_path,
        "centre_bias_warning": centre_bias_warning,
        "disclaimer": DEFAULT_DISCLAIMER
    }
