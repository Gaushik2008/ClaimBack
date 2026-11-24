from datetime import date

from claimback.pipeline import analyze_claim
from claimback.rules.dates import check_condition_vs_policy, check_ombudsman_deadline

REJ = "Claim repudiated citing clause 4.2, a waiting period applies to this illness."


def test_ombudsman_window_open_and_closed():
    ok = check_ombudsman_deadline(date(2026, 10, 20), date(2026, 11, 24))
    assert ok.passed and "330 days" in ok.details
    late = check_ombudsman_deadline(date(2025, 1, 10), date(2026, 11, 24))
    assert not late.passed and "closed" in late.details


def test_ombudsman_unanswered_grievance_note():
    r = check_ombudsman_deadline(date(2026, 10, 1), date(2026, 11, 24), date(2026, 10, 10), False)
    assert "no reply" in r.details and "30 days" in r.advisory_note


def test_leap_day_rejection_does_not_crash():
    assert check_ombudsman_deadline(date(2024, 2, 29), date(2025, 1, 1)).details


def test_condition_check_flags_pre_policy_diagnosis():
    r = check_condition_vs_policy(date(2021, 5, 1), date(2022, 3, 12), 24, date(2024, 6, 9))
    assert r.passed and "before the policy started" in r.details


def test_prior_cover_counts_toward_waiting_period():
    no = check_condition_vs_policy(date(2022, 1, 1), date(2023, 1, 1), 36, date(2024, 1, 1), 0)
    yes = check_condition_vs_policy(date(2022, 1, 1), date(2023, 1, 1), 36, date(2024, 1, 1), 24)
    assert not no.passed and yes.passed


def test_pipeline_uses_intake_and_stays_backward_compatible():
    base = analyze_claim(REJ)
    assert "supporting_factors" in base and base["supporting_factors"] == []
    r = analyze_claim(REJ, policy_start_date="2022-03-12", admission_date="2024-06-09",
                      intake={"ped_wait_months": "24", "claim_amount": "142,000", "settled_amount": "90000",
                              "documents_in_hand": ["rejection_letter"]})
    names = [c["check_name"] for c in r["date_checks"]]
    assert "waiting_period_24_months" in names
    assert r["verdict"] == "strong_appeal"
    assert any("52,000" in f for f in r["supporting_factors"])
    assert "Final hospital bill and payment receipts" in r["missing_documents"]
    assert "Insurer's rejection letter" not in r["missing_documents"]


def test_bad_numbers_do_not_crash():
    r = analyze_claim(REJ, intake={"claim_amount": "abc", "ped_wait_months": "x", "prior_cover_months": ""})
    assert r["verdict"]
