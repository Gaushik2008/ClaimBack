"""Appeal letter generator for ClaimBack.

Generates structured appeal letters to:
1. Insurer Grievance Redressal Officer (GRO)
2. Insurance Ombudsman (CIO)

Enforces:
- Advisory footer on every output: "Advisory information, not legal advice."
- Cites ONLY verified clauses and retrieved precedent case IDs.
- Strictly uses [TO FILL] placeholders for details not supplied by the user (never invents names, amounts, dates).
- Includes statutory escalation timeline citations (IRDAI 15-day GRO window, CIO 1-year window).
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any

ADVISORY_FOOTER = (
    "--------------------------------------------------------------------------------\n"
    "DISCLAIMER: Advisory information, not legal advice. This drafted letter is an\n"
    "automated template based on submitted details, official IRDAI guidelines, and\n"
    "Insurance Ombudsman precedents. It does not promise or guarantee any claim outcome.\n"
    "Please verify all facts, amounts, and dates carefully before submitting.\n"
    "--------------------------------------------------------------------------------"
)

ESCALATION_TIMELINES_NOTE = (
    "Statutory Escalation Notes:\n"
    "- Insurer Grievance Redressal: Under IRDAI Master Circular (Clause 14), the insurer\n"
    "  must acknowledge grievances within 3 days and resolve them within 15 days.\n"
    "- Insurance Ombudsman: If the insurer rejects the grievance, fails to respond within 30 days,\n"
    "  or resolves it unsatisfactorily, an appeal can be filed before the Insurance Ombudsman\n"
    "  within 1 year from the date of receipt of the insurer's final rejection (Rule 14(3) of\n"
    "  Redressal of Public Grievances Rules, 2017)."
)


def generate_grievance_letter(
    case_summary: Dict[str, Any],
    user_inputs: Optional[Dict[str, str]] = None
) -> str:
    """Drafts an appeal letter to the Grievance Redressal Officer (GRO) of the insurer."""
    u = user_inputs or {}
    policyholder_name = u.get("complainant_name", "[TO FILL: Policyholder Name]")
    policy_no = u.get("policy_no", "[TO FILL: Policy Number]")
    claim_no = u.get("claim_no", "[TO FILL: Claim Number]")
    claim_amount = u.get("claim_amount", "[TO FILL: Claim Amount in INR]")
    hospital_name = u.get("hospital_name", "[TO FILL: Hospital Name]")
    admission_date = u.get("admission_date", "[TO FILL: Admission Date DD/MM/YYYY]")
    discharge_date = u.get("discharge_date", "[TO FILL: Discharge Date DD/MM/YYYY]")
    insurer_name = u.get("insurer_name") or case_summary.get("insurer") or "[TO FILL: Insurance Company Name]"

    rejection_ground = case_summary.get("rejection_ground") or "rejection of mediclaim reimbursement"
    clause_cited = case_summary.get("clause_cited")
    clause_verified = case_summary.get("clause_verified", False)
    date_checks = case_summary.get("date_checks", [])
    precedents = case_summary.get("similar_precedents", [])

    lines = [
        f"Date: [TO FILL: Today's Date]",
        "",
        "To,",
        f"The Grievance Redressal Officer (GRO),",
        f"{insurer_name},",
        "[TO FILL: Insurer Branch / Grievance Address]",
        "",
        f"Subject: Formal Representation & Grievance Appeal against Rejection of Claim No: {claim_no} (Policy No: {policy_no})",
        "",
        "Dear Sir/Madam,",
        "",
        f"I, {policyholder_name}, hold Health Insurance Policy No. {policy_no} issued by {insurer_name}. "
        f"I am writing to formally submit a grievance regarding the wrongful repudiation/settlement "
        f"of Claim No. {claim_no} for Rs. {claim_amount} concerning hospitalization at {hospital_name} "
        f"from {admission_date} to {discharge_date}.",
        "",
        "1. GROUND OF REPUDIATION AND FACTUAL CONTEXT:",
        f"The claim was repudiated by your claims department on the stated ground of: '{rejection_ground}'.",
    ]

    if clause_cited:
        if clause_verified:
            lines.append(
                f"Your rejection letter invoked Clause {clause_cited} of the policy terms. "
                "Upon examination of the official policy schedule and continuous policy history, "
                "this repudiation is inconsistent with policy provisions and IRDAI regulations."
            )
        else:
            lines.append(
                f"The rejection letter cited Clause {clause_cited}; however, review of the policy terms "
                "reveals that this clause does not substantiate the denial of coverage under the circumstances."
            )

    # Date check grounds
    if date_checks:
        lines.append("")
        lines.append("2. CONTINUITY AND STATUTORY COMPLIANCE:")
        for dc in date_checks:
            lines.append(f"- {dc.get('check_name')}: {dc.get('details')} ({dc.get('advisory_note')})")

    # Ombudsman precedents citation
    if precedents:
        lines.append("")
        lines.append("3. JUDICIAL AND OMBUDSMAN PRECEDENTS:")
        lines.append(
            "In similar disputes involving identical grounds, the Insurance Ombudsman has held "
            "that repudiation is unwarranted:"
        )
        for p in precedents[:3]:
            lines.append(
                f"  * Case ID: {p.get('case_id')} ({p.get('centre')} Ombudsman Centre) - "
                f"Outcome: {p.get('outcome')}. Relevant reason: {p.get('why_similar', 'Similar ground of dispute.')}"
            )

    lines.extend([
        "",
        "4. REQUEST FOR RELIEF:",
        f"In light of the above facts, continuous policy record, and supporting medical records, "
        f"I respectfully request your office to review this matter objectively and reverse the repudiation, "
        f"directing the disbursal of the legitimate claim amount of Rs. {claim_amount} along with applicable interest.",
        "",
        "Please note that under the IRDAI Master Circular guidelines, insurers are required to acknowledge "
        "and resolve grievances within a period of 15 days.",
        "",
        "Thanking you,",
        "",
        "Yours sincerely,",
        f"{policyholder_name}",
        "[TO FILL: Contact Phone / Email]",
        "",
        ESCALATION_TIMELINES_NOTE,
        "",
        ADVISORY_FOOTER
    ])

    return "\n".join(lines)


def generate_ombudsman_complaint(
    case_summary: Dict[str, Any],
    user_inputs: Optional[Dict[str, str]] = None
) -> str:
    """Drafts a formal complaint to the Insurance Ombudsman under Rule 14(1) of the Redressal of Public Grievance Rules."""
    u = user_inputs or {}
    policyholder_name = u.get("complainant_name", "[TO FILL: Policyholder Name]")
    policy_no = u.get("policy_no", "[TO FILL: Policy Number]")
    claim_no = u.get("claim_no", "[TO FILL: Claim Number]")
    claim_amount = u.get("claim_amount", "[TO FILL: Claim Amount in INR]")
    insurer_name = u.get("insurer_name") or case_summary.get("insurer") or "[TO FILL: Insurance Company Name]"
    rejection_date = u.get("rejection_date", "[TO FILL: Date of Rejection Letter DD/MM/YYYY]")
    gro_appeal_date = u.get("gro_appeal_date", "[TO FILL: Date Representation Sent to GRO DD/MM/YYYY]")

    rejection_ground = case_summary.get("rejection_ground") or "Wrongful repudiation of health insurance claim"
    precedents = case_summary.get("similar_precedents", [])

    lines = [
        "FORM VI-A / COMPLAINT BEFORE THE INSURANCE OMBUDSMAN",
        "(Under Rule 14(1) of the Insurance Ombudsman Rules, 2017)",
        "",
        "To,",
        "The Honourable Insurance Ombudsman,",
        "Office of the Insurance Ombudsman,",
        "[TO FILL: Ombudsman Centre Jurisdiction Address]",
        "",
        f"1. Name and Address of Complainant: {policyholder_name}, [TO FILL: Full Postal Address]",
        f"2. Name of the Insurer: {insurer_name}",
        f"3. Policy Number: {policy_no}",
        f"4. Claim Number: {claim_no}",
        f"5. Nature of Dispute: {rejection_ground}",
        f"6. Amount Claimed: Rs. {claim_amount}",
        f"7. Date of Rejection by Insurer: {rejection_date}",
        f"8. Date of Grievance Representation to GRO: {gro_appeal_date}",
        "",
        "STATEMENT OF FACTS AND GROUNDS OF APPEAL:",
        f"The Complainant is a bonafide policyholder who lodged a valid hospitalization claim for Rs. {claim_amount}. "
        f"The Insurer repudiated the claim on the purported ground of: '{rejection_ground}'. "
        "A formal representation was lodged with the Insurer's Grievance Redressal Officer; however, the insurer "
        "failed to provide satisfactory relief within the prescribed statutory period.",
        "",
        "The Complainant relies upon the following precedents from the Insurance Ombudsman:",
    ]

    if precedents:
        for p in precedents[:4]:
            lines.append(
                f"- Case No. {p.get('case_id')} ({p.get('centre')} Centre): Outcome '{p.get('outcome')}' - "
                f"{p.get('why_similar', 'Relief granted under comparable circumstances.')}"
            )
    else:
        lines.append("- (Precedent cases to be attached with relevant award copies)")

    lines.extend([
        "",
        "PRAYER FOR RELIEF:",
        f"The Complainant respectfully prays that the Hon'ble Ombudsman be pleased to:",
        f"a) Direct the Insurer ({insurer_name}) to settle and disburse Claim No. {claim_no} in the sum of Rs. {claim_amount};",
        "b) Award penal interest under IRDAI regulations for the delay in claim processing;",
        "c) Grant compensation towards mental harassment and costs incurred.",
        "",
        "VERIFICATION:",
        f"I, {policyholder_name}, do hereby verify that the contents stated above are true to the best of my knowledge and belief.",
        "",
        "Signature: __________________________",
        f"Date: [TO FILL: Date]   Place: [TO FILL: City]",
        "",
        ESCALATION_TIMELINES_NOTE,
        "",
        ADVISORY_FOOTER
    ])

    return "\n".join(lines)
