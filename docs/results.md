# ClaimBack Empirical Evaluation Results & Methodology

## 1. Per-Centre Baseline Evaluation (Wilson 95% Confidence Intervals)

Total dataset size: 1,086 unique deduplicated cases across Books 10, 11, 17, and 18.
Evaluation task: Leave-One-Out classification on binary outcome (`allowed` vs `dismissed`) strictly within each centre.

| Centre | $n$ | Outcome Split (Dismissed / Allowed) | Majority Baseline [95% Wilson CI] | Keyword Rule [95% Wilson CI] | TF-IDF Precedent k-NN [95% Wilson CI] |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Ahmedabad** | 379 | 322 (85.0%) / 57 (15.0%) | 85.0% [81.0% - 88.2%] | 68.9% [64.0% - 73.3%] | 84.2% [80.2% - 87.5%] |
| **Delhi** | 194 | 24 (12.4%) / 170 (87.6%) | 87.6% [82.3% - 91.5%] | 16.0% [11.5% - 21.8%] | 86.1% [80.5% - 90.3%] |
| **Kolkata** | 67 | 19 (28.4%) / 48 (71.6%) | 71.6% [59.9% - 81.0%] | 38.8% [28.0% - 50.8%] | 59.7% [47.7% - 70.6%] |
| **Chennai** | 81 | 50 (61.7%) / 31 (38.3%) | 61.7% [50.8% - 71.6%] | 61.7% [50.8% - 71.6%] | 56.8% [45.9% - 67.0%] |

### Key Baseline Takeaway
- **The Confound**: In Ahmedabad, predicting "dismissed" blind yields 85.0% accuracy. In Delhi, predicting "allowed" blind yields 87.6% accuracy. TF-IDF precedent k-NN tracks the centre's dominant class and cannot beat the majority baseline.
- **Unconfounded Floor**: Chennai represents the most balanced geographic sample ($n=81$, 50 dismissed vs 31 allowed). All statistical baselines on Chennai perform near chance (56.8% - 61.7%).

---

## 2. LLM Evaluation & Citation Verification Harness
- Tested using `claimback.eval.llm` and `claimback.eval.run_llm`.
- The RAG predictor retrieves 5 nearest precedents (excluding the query case via Leave-One-Out) and enforces JSON parsing with OpenAI-compatible backend `nvidia/nemotron-3-ultra-550b-a55b`.
- **Citation Hallucination Verifier**: Verifies every cited precedent ID in `cited_precedents` against the retrieved set. Unit test `test_citation_verifier_flags_invented_ids` asserts that invented or fabricated case IDs are flagged.

---

## 3. Product Pipeline & Deterministic Rule Verification
- Masking verified (`claimback.privacy`): Aadhaar, PAN, phone, policy, and claim numbers redacted before processing.
- Date rules verified (`claimback.rules.dates`): Leap years, month boundaries, 30-day initial waiting period, accidental emergency exception, and 5-year moratorium rule under IRDAI Master Circular (2024).
- Verbatim clause presence check (`claimback.policy.parser`): Insurer-cited clauses verified against uploaded policy wording.
- Full suite of 24 unit and API integration tests passing in 0.70s.

---

## 4. Limitations
1. **Ombudsman Centre Confound**: Geographic variation in historical award outcomes is substantial. Pooled accuracy across centres is misleading and must never be headlined.
2. **Digest Summaries vs Full Orders**: Digests provide condensed factual summaries (1-3 paragraphs) rather than multi-page legal awards.
3. **Data Period (2008-2013)**: The digests cover Ombudsman cases from 2008 to 2013. While IRDAI statutory rules (waiting periods, moratorium) are current, historical case distributions reflect older policy wordings.
4. **Rule-Based Labels**: The digest dataset labels are generated via deterministic outcome regex patterns.
5. **Selection Bias**: The dataset comprises only matters escalated to the Insurance Ombudsman, excluding claims resolved internally by insurers.
