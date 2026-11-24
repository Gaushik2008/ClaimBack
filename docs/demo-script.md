# ClaimBack Demo Script (2-Minute Narrative Walkthrough)

**Track:** "The $15-an-hour expert"  
**Target User:** Indian health insurance policyholder facing a sudden claim repudiation.

---

## 00:00 - 00:30: The Problem
> *"Last week, a family member was admitted to the hospital emergency following a road accident. Two days later, their Mediclaim reimbursement of ₹1.2 Lakhs was rejected by the insurer with a one-liner: 'Repudiated under Clause 4.1: Claim within initial 30 days.' The policyholder has no legal background, no broker to assist, and 15 days to respond before losing their appeal window."*

- **Open ClaimBack Web App** (`http://localhost:8080`).
- Point out the Privacy Notice banner: *"Notice that before anything touches an AI model or server, sensitive identifiers—Aadhaar, PAN, phone, and policy numbers—are masked client-side."*

---

## 00:30 - 01:10: Document Analysis & Deterministic Verification
- Click **"Load Fictional Demo Case"**.
- Point out the inputs populated:
  - Rejection letter mentioning Clause 4.1.
  - Policy start date (Jan 1, 2023) and Admission date (Jan 15, 2023 - 14 days later).
  - Emergency accident checkbox checked.
  - Policy wording pasted with Clause 4.1 containing the accident exception.
- Click **"Analyze Claim & Verify Clauses"**.
- Show the results:
  1. **Verdict**: **Strong Grounds for Appeal** (Confidence 88%).
  2. **Deterministic Date Check**: **INITIAL 30 DAY WAITING PERIOD: PASSED**. *Explain: Under IRDAI Master Circular guidelines and verified policy text, accidental injury emergency admissions are completely exempt from the 30-day waiting period.*
  3. **Clause Check**: **Clause 4.1 Verified in Policy**.
  4. **Precedents**: Relevant Ombudsman decisions cited with actual Case IDs and centres.

---

## 01:10 - 01:45: Automated Grounded Appeal Drafting
- Click **"Generate Appeal Letter Drafts"**.
- Show the two generated tabs:
  1. **Grievance Officer (GRO)**: Structured letter citing statutory IRDAI 15-day resolution turnaround and the accident exception under Clause 4.1.
  2. **Insurance Ombudsman (Form VI-A)**: Formal complaint under Rule 14(1) of the Insurance Ombudsman Rules, 2017.
- Point out that every unsupplied field uses `[TO FILL]` placeholders—no names, amounts, or facts were invented.
- Demonstrate **"Copy Letter"** and **"Download as Text"**.

---

## 01:45 - 02:00: Honesty & Statutory Escalation
- Point out the disclaimer and the automated **n8n Statutory Deadline Tracker** that counts down the insurer's 15-day window.
- Conclude: *"ClaimBack doesn't replace an advocate; it empowers an everyday consumer with the deterministic rules, precedent intelligence, and drafting rigor of a $15-an-hour expert in under two minutes."*
