# ClaimBack: build prompt for fcc-claude

Paste everything below the line into fcc-claude, run from a clone of https://github.com/Gaushik2008/ClaimBack (branch main, HEAD should be 14b8da8 or later).
Before you paste: `export NVIDIA_API_KEY=...` in that terminal (never paste the key into chat), and copy the PDFs/text of Mediclaim Books 10, 11, 17, 18 into `data/raw/digests/`.

---

# ROLE AND GOAL

You are a senior engineer finishing ClaimBack, a hackathon app (track "The $15-an-hour expert"): it helps an Indian health-insurance policyholder understand a claim rejection and draft an appeal. Build the working app on top of the existing repo. Work in phases; stop after each phase and report.

# NON-NEGOTIABLE RULES

1. Honesty: never invent results, citations, case ids, clause numbers, legal limits or numbers. Report exactly what scripts print. If something fails, say so and fix or log it.
2. Advisory only: every output and the UI carry the footer "Advisory information, not legal advice." The app never promises an outcome.
3. Abstain over guess: if evidence is thin, return `insufficient_information`.
4. Secrets: NVIDIA_API_KEY is read from the environment only. Never print, log, commit, or put it in client-side code. No `.env` committed.
5. Data hygiene: never commit `data/raw`, `data/processed`, PDFs, complainant names, or any real user's documents. Mask phone numbers, Aadhaar, PAN, policy and claim numbers before any text goes to the LLM, and say so in the UI.
6. Synthetic data (`tests/fixtures/SYNTHETIC_*`) is for tests and demos only. It is never counted in any metric and never used as retrieval corpus for evaluation.
7. After each task: append a dated entry to `progress.md`, commit with a clear message, push to main at the end of each phase. Add the trailer `Co-Authored-By` only if your tooling does so by default.
8. Model: `nvidia/nemotron-3-ultra-550b-a55b` via `https://integrate.api.nvidia.com/v1` (OpenAI-compatible). It is a reasoning model: tolerate text around JSON; add retries with backoff and timeouts; if replies often fail to parse, fix the prompt/parser.

# CURRENT STATE (verify, do not assume)

- Python package `src/claimback/`: `awards/digest.py` (parses "Mediclaim book" summaries; complainant names not stored), `awards/parser.py`, `eval/` (baselines, bench, llm, run, run_llm). 16 tests pass with `PYTHONPATH=src pytest -q` or after `pip install -e .[dev]`.
- Digest parser on Books 10/11/18 gives 700 unique cases (220 allowed, 352 dismissed, 13 disposed, 115 unknown). Labels are rule-based and NOT hand-verified. Book 17 had 326 cases; its labels may have shifted after a rule change on 2026-11-24.
- Known confound: outcomes track ombudsman centre (Ahmedabad mostly insurer-upheld; Delhi mostly relief). A centre-only baseline scored ~89% on Book 17 pooled data. Never headline a pooled accuracy.
- `eval/verified_real_cases.json`: 3 sourced High Court orders (demo only). `docs/real_case_leads.md`: status of other leads (5 NOT FOUND: do not cite).
- Not built yet: policy parser, date/waiting-period checker, pipeline, letter generator, UI, n8n workflow, Keploy tests, deploy.
- Parser misses some "Case No" lines (Book 10: 192 of 209). Investigate in Phase 0.

# PHASE 0: SETUP AND DATA

1. `python -m venv .venv`, `pip install -e .[dev]`, `pytest -q` (expect 16 pass).
2. Put the four books in `data/raw/digests/`. Run `python -m claimback.awards.digest` per book; print counts and outcome distribution.
3. Find why ~8-25% of "Case No" lines are not parsed (likely header variants, merged blocks, page breaks). Fix with tests. Report before/after counts. Deduplicate across books by case id.
4. Build a unified corpus file `data/processed/cases_all.json` (git-ignored) with fields: case_id, centre, insurer, year, dispute_type, facts, reasoning, outcome, ground, clauses, source_book.
5. Hand-audit support: write `python -m claimback.eval.audit` that samples 40 cases stratified by centre, shows facts+reasoning with the outcome hidden, lets the user enter a/d/o/skip, then reports agreement with the rule label and writes aggregate-only `eval/label_audit_result.json`. Do not run it unattended; tell the user when it is ready.

# PHASE 1: EVALUATION (evidence)

6. `python -m claimback.eval.run` for all four books. Report per-centre results (Ahmedabad, Delhi, Kolkata, Chennai) with baselines: majority, centre-only, keyword rule, TF-IDF kNN. Add 95% Wilson intervals. State n for each.
7. LLM evaluation (`run_llm`): for each centre with at least 40 labelled cases, leave-one-out: plain single-prompt LLM vs ClaimBack-RAG (5 retrieved precedents, test case excluded, same-centre retrieval allowed but also report a no-centre-signal variant that strips centre/insurer-style cues). Output JSON verdict; verify every cited case id was actually retrieved; report citation-hallucination rate. Save `eval/results_llm.json`. Do not claim superiority unless the intervals support it.
8. Memorisation probe: ~25 cases, give only case id + insurer + year, ask for the outcome; report accuracy vs chance as evidence of training-data exposure. Save `eval/results_memorisation.json`.
9. Stop and show the user the three result files.

# PHASE 2: PRODUCT MODULES (small, typed, tested)

10. `src/claimback/policy/`: parse policy-wording text/PDF into clauses (id, title, text). Detect: initial 30-day wait, specific-disease waits (24/36/48 months), PED waiting, room-rent/sub-limit/co-pay, exclusions. Rule-based first. LLM only maps a rejection reason to clause ids. Every clause the system cites must be verified to exist verbatim in the uploaded text; otherwise mark `clause_verified=false`.
11. `src/claimback/rules/dates.py`: pure, deterministic functions (no LLM arithmetic): days between policy start and admission, waiting-period completion using continuity/renewal/port-in dates, accident exception to the initial 30-day wait, and the moratorium. Before hard-coding any IRDAI number (e.g. moratorium period, PED look-back), fetch the current IRDAI Master Circular text, cite the source in a code comment, and put the numbers in a config file with the source URL and retrieval date. Unit tests for leap years, month-end dates, renewal gaps, port-in continuity.
12. `src/claimback/pipeline.py`: input = rejection letter text + policy text + discharge summary text (the last two optional). Output JSON:
   `{rejection_ground, clause_cited, clause_verified, date_checks[], similar_precedents[{case_id, outcome, centre, why_similar}], verdict, confidence, missing_documents[], escalation_path, disclaimer}`.
   `verdict` is one of `strong_appeal | weak_appeal | insurer_likely_right | insufficient_information`. Verdict is driven mainly by deterministic checks (dates, clause existence); precedents inform but do not decide. Include a note when retrieved precedents come from one centre only.
13. `src/claimback/letters.py`: draft the appeal letter (first to the insurer's grievance officer, then Insurance Ombudsman). Cite only verified clauses and retrieved precedent ids. Include the facts the user supplied as placeholders `[TO FILL]` where missing; never invent dates, amounts or names. Verify the current Ombudsman complaint timelines and escalation steps from official CIO / IRDAI sources before stating any number of days; cite the source in a code comment and in the letter's notes. Footer: advisory, not legal advice.
14. Privacy: `src/claimback/privacy.py` masks phone, Aadhaar, PAN, policy/claim numbers, emails before LLM calls; unit-test with synthetic strings.

# PHASE 3: APP

15. Backend: FastAPI in `app/api/` with `POST /analyze` (three text fields or file uploads: PDF/text/image-OCR optional), `POST /letter`, `GET /health`. The LLM client lives server-side only. Rate-limit and size-limit uploads. No document is stored; process in memory and discard.
16. Frontend: simple, accessible, mobile-friendly (many users will be on phones). Streamlit is acceptable; a small static HTML+JS page calling the API is better for deploy. Screens: (a) upload/paste three documents with a visible "personal numbers are masked before analysis" notice; (b) result: rejection ground, clause check (verified / not found), date checks as a small timeline, similar precedents with ids, verdict + confidence, missing documents; (c) draft letter with Copy and Download (.docx or PDF) buttons; (d) always-visible disclaimer.
17. Languages: English first. Add Hindi and Tamil output for the explanation and the letter as a stretch, generated by the LLM from the English result; label them "machine-translated, please review."
18. Demo mode: a clearly labelled FICTIONAL sample case (policy + rejection + discharge summary) in `demo/`, so the demo never uses real people's data.

# PHASE 4: INTEGRATIONS AND QUALITY

19. n8n: `n8n/deadline-tracker.json` workflow: webhook receives case id + escalation deadline, Wait nodes, reminders at 7 days and 1 day before (email; WhatsApp optional). `n8n/README.md` with import steps and required credentials (placeholders only).
20. Keploy: record/replay API tests for the backend, config and README steps, so the hackathon's Keploy requirement is met. Repo must be public with a clear README.
21. Tests: unit tests for privacy masking, date math, clause verification, citation checking, letter placeholders; an API smoke test with a fake LLM client; CI (GitHub Actions) running `pytest`.
22. Deploy: backend on a host that keeps the API key server-side (e.g. Render/Fly/Railway), frontend static. Ask the user before attaching a domain.

# PHASE 5: EVIDENCE AND SUBMISSION DOCS

23. `docs/results.md`: only measured numbers: label audit agreement, per-centre baselines with intervals, plain LLM vs ClaimBack-RAG, citation-hallucination rate, memorisation probe. Explicit Limitations: centre confound, summaries not full awards, 2008-2013 data, rule-based labels, selection bias (only Ombudsman-decided complaints), small n per centre.
24. Ask the user for 5-10 REAL rejection letters (redacted by them). Run the pipeline; record an anonymised qualitative table (ground, clause found?, date check result, verdict, user's own rating of usefulness). No identifying details.
25. Update `README.md` (what it does, how to run, results, limits, disclaimer), write `docs/demo-script.md` (2-minute narrative using the fictional demo case plus the sourced real High Court cases in `eval/verified_real_cases.json`) and `docs/pitch-outline.md` (problem; solution; evidence including honest negatives; business potential: hospital billing desks, insurance agents, employer HR benefits desks; risks).

# DEFINITION OF DONE

- All tests pass; `pytest -q` output pasted in the report.
- `eval/results_llm.json`, `eval/results_memorisation.json`, `eval/label_audit_result.json` exist and are summarised honestly.
- A user can paste a rejection letter and policy text into the deployed app and get ground, verified clause, date checks, precedents, verdict (or abstention) and a draft letter, with masking and disclaimers visible.
- No secret, PDF, or personal data is in git history (`git log -p` grep for the key prefix and for "Aadhaar").

# HOW TO REPORT

After each phase: what ran, exact outputs, what failed, what you need from the user. Ask one concise question at a time. Do not start the next phase until the user says go.
