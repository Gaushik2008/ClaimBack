"""Deterministic waiting-period and policy date calculations based on IRDAI rules.

Sources:
- IRDAI Master Circular on Health Insurance Business (Ref: IRDAI/HLT/REG/CIR/099/05/2024; also 2016/2020 Standardization circulars)
- URL: https://irdai.gov.in/document-detail?documentId=392949 (Retrieved 2024-04-01 / verified 2024 Master Circular)
- Rules:
  1. Initial waiting period: 30 days from inception. Exception: Hospitalization caused by accidental injury has 0 waiting period.
  2. Specific illness / 1st/2nd year exclusions: 24/36/48 months from inception, waived if continuity ported.
  3. Pre-existing disease (PED): Max waiting period was 48 months (reduced to 36 months under May 2024 circular).
  4. Moratorium period: No policy can be contested after 8 continuous years (reduced to 5 continuous years under May 2024 circular) except for proven fraud.
  5. Portability & Continuity: Cumulative continuous coverage duration across previous ported insurers must count towards waiting periods.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

CONFIG_PATH = Path(__file__).parent.parent / "config" / "irdai.json"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("irda_guidelines", {}).get("rules", {})
    return {
        "initial_waiting_period_days": 30,
        "accident_exception": True,
        "ped_waiting_period_max_months": 36,
        "moratorium_period_continuous_years": 5,
        "grace_period_days": 30,
    }


RULES = _load_config()


def parse_date(d_str: str) -> Optional[date]:
    """Parse common Indian date formats (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY)."""
    if not d_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(d_str.strip(), fmt).date()
        except ValueError:
            pass
    return None


@dataclass
class DateCheckResult:
    check_name: str
    passed: bool
    details: str
    days_or_months_elapsed: Optional[int] = None
    statutory_threshold: Optional[int] = None
    advisory_note: str = ""


def check_initial_waiting_period(policy_start: date, admission_date: date, is_accident: bool = False) -> DateCheckResult:
    """Check 30-day initial waiting period."""
    if is_accident:
        return DateCheckResult(
            check_name="initial_30_day_waiting_period",
            passed=True,
            details="Emergency accidental hospitalization is exempt from the initial 30-day waiting period under IRDAI guidelines.",
            statutory_threshold=30,
            advisory_note="Accident exception applies: insurer cannot repudiate under initial waiting period."
        )

    delta_days = (admission_date - policy_start).days
    if delta_days >= 30:
        return DateCheckResult(
            check_name="initial_30_day_waiting_period",
            passed=True,
            details=f"Admission is {delta_days} days after policy start (threshold: 30 days).",
            days_or_months_elapsed=delta_days,
            statutory_threshold=30,
            advisory_note="Initial 30-day waiting period completed."
        )
    else:
        return DateCheckResult(
            check_name="initial_30_day_waiting_period",
            passed=False,
            details=f"Admission occurred on day {delta_days} of policy inception (within 30-day window).",
            days_or_months_elapsed=delta_days,
            statutory_threshold=30,
            advisory_note="Repudiation under 30-day waiting period is valid unless illness arose from an accident."
        )


def check_waiting_period_months(first_inception_date: date, admission_date: date, required_waiting_months: int, continuity_months: int = 0) -> DateCheckResult:
    """Check specific waiting period (e.g. 24 or 36 or 48 months for PED/specific disease)."""
    # Calculate approximate months elapsed
    years_diff = admission_date.year - first_inception_date.year
    months_diff = admission_date.month - first_inception_date.month
    days_diff = admission_date.day - first_inception_date.day
    
    total_months = years_diff * 12 + months_diff
    if days_diff < 0:
        total_months -= 1
        
    total_effective_months = total_months + continuity_months

    passed = total_effective_months >= required_waiting_months
    return DateCheckResult(
        check_name=f"waiting_period_{required_waiting_months}_months",
        passed=passed,
        details=f"Total continuous coverage elapsed: {total_effective_months} months (required: {required_waiting_months} months).",
        days_or_months_elapsed=total_effective_months,
        statutory_threshold=required_waiting_months,
        advisory_note="Waiting period satisfied." if passed else f"Waiting period of {required_waiting_months} months not yet completed."
    )


def check_moratorium(continuous_years_completed: float) -> DateCheckResult:
    """IRDAI Moratorium rule (5 continuous years / earlier 8 years):

    After 5 continuous policy years without break, no health insurance policy can be
    contested by the insurer on grounds of non-disclosure or pre-existing disease (except fraud).
    """
    threshold = RULES.get("moratorium_period_continuous_years", 5)
    passed = continuous_years_completed >= threshold
    return DateCheckResult(
        check_name="moratorium_protection",
        passed=passed,
        details=f"Continuous coverage: {continuous_years_completed:.1f} years (Moratorium threshold: {threshold} years).",
        days_or_months_elapsed=int(continuous_years_completed * 12),
        statutory_threshold=int(threshold * 12),
        advisory_note="Protected by IRDAI Moratorium rule: insurer cannot repudiate for non-disclosure/PED." if passed else f"Moratorium of {threshold} continuous years not completed."
    )
