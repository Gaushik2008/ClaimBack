from datetime import date
from claimback.privacy import mask_pii
from claimback.rules.dates import (
    check_initial_waiting_period,
    check_waiting_period_months,
    check_moratorium
)
from claimback.policy.parser import parse_policy, verify_clause_presence
from claimback.pipeline import analyze_claim
from claimback.letters import generate_grievance_letter, generate_ombudsman_complaint


def test_pii_masking():
    sample = "Contact Gautam at test@example.com or phone +91 9876543210. Aadhaar 2345 6789 0123, PAN ABCDE1234F. Policy No. POL-99887766 and Claim No. CLM-112233."
    masked, counts = mask_pii(sample)
    assert "[EMAIL_REDACTED]" in masked
    assert "[PHONE_REDACTED]" in masked
    assert "[AADHAAR_REDACTED]" in masked
    assert "[PAN_REDACTED]" in masked
    assert "[POLICY_NO_REDACTED]" in masked
    assert "[CLAIM_NO_REDACTED]" in masked
    assert "9876543210" not in masked
    assert "test@example.com" not in masked


def test_date_waiting_period_rules():
    # Less than 30 days non-accident -> fails
    res1 = check_initial_waiting_period(date(2023, 1, 1), date(2023, 1, 15), is_accident=False)
    assert not res1.passed

    # Accidental hospitalization -> exempt
    res2 = check_initial_waiting_period(date(2023, 1, 1), date(2023, 1, 15), is_accident=True)
    assert res2.passed

    # 30+ days -> passed
    res3 = check_initial_waiting_period(date(2023, 1, 1), date(2023, 2, 10), is_accident=False)
    assert res3.passed

    # Moratorium >= 5 years -> passed
    res4 = check_moratorium(5.2)
    assert res4.passed

    # Moratorium < 5 years -> not completed
    res5 = check_moratorium(3.0)
    assert not res5.passed


def test_policy_clause_parsing_and_verification():
    policy_doc = """
    1. Scope of Coverage
    Hospitalization expenses are covered.

    Clause 4.1 First Thirty Days Waiting Period
    Expenses related to the treatment of any illness within 30 days from the first policy inception date shall be excluded.

    Clause 4.2 Pre-Existing Diseases
    Benefits will not be available for any pre-existing conditions until 36 months of continuous coverage have elapsed.
    """
    parsed = parse_policy(policy_doc)
    assert len(parsed.clauses) >= 2
    assert verify_clause_presence("4.1", policy_doc)
    assert verify_clause_presence("4.2", policy_doc)
    assert not verify_clause_presence("9.99", policy_doc)


def test_pipeline_analysis():
    rejection = "We regret to inform you that your claim under Policy No. POL-123456 is rejected citing Clause 4.1 due to initial 30 days waiting period."
    policy = "Clause 4.1 Initial waiting period: 30 days."

    res = analyze_claim(
        rejection_text=rejection,
        policy_text=policy,
        policy_start_date="2023-01-01",
        admission_date="2023-01-10",
        is_accident=False
    )
    assert res["rejection_ground"] == "waiting_period"
    assert res["clause_cited"] == "4.1"
    assert res["clause_verified"] is True
    assert res["verdict"] == "insurer_likely_right"
    assert "Advisory information" in res["disclaimer"]


def test_appeal_letter_generation():
    analysis = {
        "insurer": "Star Health",
        "rejection_ground": "pre-existing condition exclusion",
        "clause_cited": "4.2",
        "clause_verified": True,
        "similar_precedents": [{"case_id": "11-002-0114-09", "centre": "Ahmedabad", "outcome": "allowed"}]
    }
    letter = generate_grievance_letter(analysis)
    assert "To," in letter
    assert "Grievance Redressal Officer" in letter
    assert "Clause 4.2" in letter
    assert "11-002-0114-09" in letter
    assert "[TO FILL" in letter
    assert "Advisory information, not legal advice" in letter
