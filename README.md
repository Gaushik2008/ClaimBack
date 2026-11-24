# ClaimBack

> **Advisory information, not legal advice.** Never promises an outcome.

ClaimBack is an advisory tool for Indian health-insurance policyholders (Track: "The $15-an-hour expert"). It helps a policyholder understand why their claim was rejected or deducted, verifies waiting periods and clauses against policy wordings and IRDAI regulations, retrieves relevant Insurance Ombudsman precedents, and drafts grounded appeal letters.

---

## What It Does
1. **Document Analysis**: Parses insurer rejection letters, policy wordings, and hospital discharge summaries.
2. **Clause Verification**: Verifies whether cited clauses actually exist verbatim in the uploaded policy text.
3. **Deterministic Date Checks**: Computes 30-day initial waiting period, accidental injury exemption, specific illness waiting periods, and the 5-year moratorium rule under IRDAI Master Circular guidelines.
4. **Precedent Retrieval**: Retrieves real Insurance Ombudsman awards across 1,086 deduplicated cases from Books 10, 11, 17, and 18.
5. **Grounded Appeal Drafting**: Drafts formal representation letters to the Insurer's Grievance Redressal Officer (GRO) and Form VI-A complaints to the Insurance Ombudsman, using strict `[TO FILL]` placeholders.
6. **Privacy by Design**: Masks Aadhaar, PAN, phone numbers, policy numbers, claim numbers, and emails before analysis. No personal documents are stored.

---

## How to Run the App Locally

### 1. Setup Environment
```bash
git clone https://github.com/Gaushik2008/ClaimBack.git
cd ClaimBack
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2. Run Tests
```bash
pytest -v
```
All 24 unit and API integration tests should pass.

### 3. Start the Web Server
```bash
python -m app.server 8080
```
Open your browser at `http://localhost:8080`.

- Click **"Load Fictional Demo Case"** to preview a sample claim repudiation and accident waiting-period exemption.
- Click **"Analyze Claim & Verify Clauses"** to inspect the timeline, clause checks, and precedents.
- Click **"Generate Appeal Letter Drafts"** to review and copy the GRO and Ombudsman appeal letters.

---

## Architecture & Codebase Layout
- `src/claimback/privacy.py`: Client/server-side PII masking for Aadhaar, PAN, phone, and policy identifiers.
- `src/claimback/policy/`: Policy parser and verbatim clause presence checker.
- `src/claimback/rules/dates.py`: Pure deterministic date calculations citing official IRDAI circulars.
- `src/claimback/pipeline.py`: Core analysis pipeline synthesizing deterministic checks, precedents, and verdicts.
- `src/claimback/letters.py`: Grievance and Ombudsman appeal letter generator.
- `src/claimback/awards/digest.py`: Digest parser for CIO Mediclaim books.
- `src/claimback/eval/`: Baseline and LLM evaluation harness.
- `app/`: Web server (`app/server.py`) and responsive UI (`app/static/index.html`).
- `n8n/`: Escalation deadline tracker workflow (`n8n/deadline-tracker.json`).
- `keploy/`: Keploy record/replay API regression configuration.

---

## Evaluation & Empirical Results
See [`docs/results.md`](docs/results.md) for detailed per-centre baseline tables, Wilson confidence intervals, and limitations.

---

## License
MIT License.
