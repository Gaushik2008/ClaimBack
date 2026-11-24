"""Tests for the award parser.

The fixture below is SYNTHETIC: invented text that mimics the field and section
layout of real Ombudsman awards. It contains no real person, insurer decision or
case. Real-text behaviour must still be checked on downloaded PDFs.
"""

from claimback.awards.parser import (
    classify_outcome,
    guess_ground,
    parse_amount,
    parse_award,
    split_awards,
)

SYNTHETIC = """
PROCEEDINGS BEFORE THE INSURANCE OMBUDSMAN, STATE OF EXAMPLE
Case of Mr A Person Vs Example Health Insurance Co. Ltd.
REF NO: EXM-H-001-2021-0001  Award No: IO/EXM/A/HI/0001/2021-2022
1. Name & Address of the Complainant Mr A Person, 1 Example Street
2. Type of Policy Individual Health Insurance
3. Name of the Insured Mr A Person
4. Name of the Insurer Example Health Insurance Co. Ltd.
5. Date of repudiation 01.01.2021
6. Reason for repudiation Pre-existing disease, claim denied within the waiting period
8. Nature of Complaint Repudiation of claim
10. Amount of Claim Rs. 1,23,456/-
11. Amount paid by the Insurer Rs. 20,000/-
13. Amount of Relief sought Rs. 1,03,456/-
19. Date of Award/Order 15.04.2021
20. Brief facts of the complaint The complainant was hospitalised for a procedure and the claim was
repudiated by the insurer citing a pre-existing condition.
21. Insurer's submission The policy had a waiting period which was not complete.
24. Result of hearing (Observations and Conclusion) The condition was not diagnosed before the policy
began. The repudiation is not justified.
AWARD
Thus, the complaint is allowed. The insurer shall pay Rs. 1,03,456/- in full and final settlement.
25. Attention of the insurer is drawn to Rules 17(6), 17(7) and 17(8).
Dated at Example on this 15th day of April 2021
PROCEEDINGS BEFORE THE INSURANCE OMBUDSMAN, STATE OF EXAMPLE
REF NO: EXM-H-001-2021-0002  Award No: IO/EXM/A/HI/0002/2021-2022
4. Name of the Insurer Other Insurance Co. Ltd.
8. Nature of Complaint Claim not covered, room rent proportionate deduction
10. Amount of Claim Rs. 50,000/-
20. Brief facts of the complaint The insurer applied a proportionate deduction for room rent.
24. Result of hearing The deduction is as per policy terms.
AWARD
Thus, the complaint is not allowed.
25. Attention of the insurer is drawn to Rules 17(6), 17(7) and 17(8).
Dated at Example on this 20th day of April 2021
"""


def test_split_finds_two_awards():
    assert len(split_awards(SYNTHETIC)) == 2


def test_duplicate_header_inside_one_award_is_merged():
    doubled = SYNTHETIC.split("PROCEEDINGS BEFORE", 2)
    # header repeated inside the first award, with no new ref number
    text = "PROCEEDINGS BEFORE" + doubled[1] + "\nPROCEEDINGS BEFORE THE INSURANCE OMBUDSMAN\n"
    assert len(split_awards(text)) == 1


def test_fields_first_award():
    a = parse_award(split_awards(SYNTHETIC)[0])
    assert a.ref_no == "EXM-H-001-2021-0001"
    assert a.award_no == "IO/EXM/A/HI/0001/2021-2022"
    assert a.insurer == "Example Health Insurance Co. Ltd."
    assert a.nature_of_complaint == "Repudiation of claim"
    assert a.claim_amount == 123456.0
    assert a.amount_paid == 20000.0
    assert a.relief_sought == 103456.0
    assert a.date_of_award == "15.04.2021"
    assert a.reason and a.reason.startswith("Pre-existing disease")
    assert a.observations and a.observations.startswith("The condition was not diagnosed")
    assert a.facts and "hospitalised" in a.facts
    assert a.outcome == "allowed"
    assert a.ground_hint == "pre_existing"
    assert a.missing == []


def test_complainant_identity_not_stored():
    a = parse_award(split_awards(SYNTHETIC)[0])
    blob = " ".join(str(v) for v in a.to_dict().values())
    assert "Mr A Person" not in blob.split("hospitalised")[0]  # not in structured fields
    assert not hasattr(a, "complainant")


def test_second_award_dismissed_and_missing_fields_reported():
    a = parse_award(split_awards(SYNTHETIC)[1])
    assert a.outcome == "dismissed"
    assert a.ground_hint == "room_rent"
    assert a.reason is None  # not present: left empty, never guessed


def test_outcome_uses_award_section_not_submissions():
    text = "\n1. Brief facts of the complaint says complaint not allowed earlier\nAWARD\nThus, the complaint is allowed.\n"
    assert classify_outcome(text) == "allowed"


def test_outcome_variants():
    assert classify_outcome("\nAWARD\nThe complaint is partly allowed.") == "partly_allowed"
    assert classify_outcome("\nAWARD\nThe complaint is disposed of accordingly.") == "disposed"
    assert classify_outcome("\nAWARD\nNothing relevant here.") == "unknown"


def test_parse_amount_indian_grouping():
    assert parse_amount("Rs. 1,23,456/-") == 123456.0
    assert parse_amount("Rs 2,50,000.50") == 250000.5
    assert parse_amount("NIL") is None
    assert parse_amount(None) is None


def test_guess_ground_none_when_no_keywords():
    assert guess_ground("claim paid late", None) is None
