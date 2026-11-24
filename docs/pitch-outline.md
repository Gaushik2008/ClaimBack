# ClaimBack Pitch Outline

**Track:** C1: "The $15-an-hour expert"  
**Elevator Pitch:** ClaimBack is an advisory assistant that enables Indian health-insurance policyholders to understand claim rejection letters, verify clauses and waiting periods against policy wordings and statutory IRDAI regulations, and generate grounded appeal letters to the Grievance Redressal Officer and the Insurance Ombudsman.

---

## 1. The Problem
- **Asymmetry of Information**: Indian health insurance policyholders receive dense repudiation letters invoking technical clauses (e.g., Clause 4.1 waiting periods, Clause 4.2 pre-existing diseases, proportionate deductions).
- **Time Pressure**: Insurers often enforce strict appeal timelines, while statutory turnaround limits (IRDAI 15-day resolution) are obscure to ordinary consumers.
- **Cost of Advice**: Engaging an insurance consultant or lawyer costs thousands of rupees—often exceeding the disputed deduction amount on small or medium claims.

---

## 2. The Solution: ClaimBack
- **Deterministic-First Analysis**: Waiting periods, continuity/portability, leap years, and the 5-year moratorium are calculated with deterministic code, not LLM arithmetic.
- **Verbatim Clause Verification**: Never hallucinates clauses. Verifies whether the cited rejection clause exists verbatim in the policy wording.
- **1,086 Ombudsman Precedents Corpus**: Retrieves real cases from the Insurance Ombudsman digest archive (Books 10, 11, 17, and 18) to cite relevant historical rulings.
- **Strict Privacy**: PII (Aadhaar, PAN, phone, email, policy, and claim numbers) is masked client-side before any processing or LLM call. Documents are processed in-memory and discarded.
- **Grounded Appeal Drafting**: Generates customized representation letters to the Insurer's Grievance Redressal Officer (GRO) and Form VI-A complaints to the Insurance Ombudsman with explicit `[TO FILL]` placeholders.
- **Automated Escalation Tracking**: Integrated n8n workflow tracks the statutory 15-day GRO deadline and alerts policyholders 7 days and 1 day before expiry.

---

## 3. Evidence & Honest Negatives
- **Per-Centre Ombudsman Variation**: Thorough evaluation across 1,086 cases revealed strong geographic confounds (Ahmedabad 85% insurer-upheld; Delhi 87.6% policyholder relief). ClaimBack flags this geographic variation explicitly to the user rather than claiming misleading pooled accuracy.
- **Honest Floor**: In balanced centres like Chennai ($n=81$, 50 dismissed vs 31 allowed), standard statistical models perform at chance (56.8% - 61.7%). ClaimBack abstains (`insufficient_information`) whenever documentary evidence is thin.
- **Citation Hallucination Rate**: Zero tolerance for invented citations. Every cited case ID is checked against the retrieved set.

---

## 4. Market & Business Potential
1. **Hospital Billing Desks & TPAs**: Cashless claim denials frequently force patients into stressful discharge disputes. Hospitals can deploy ClaimBack at the billing counter to instantly triage whether a denial has grounds for immediate reconsideration.
2. **Insurance Brokers & POSP Agents**: Individual agents can use ClaimBack to provide post-sales dispute support to clients, increasing customer retention.
3. **Corporate HR & Employee Benefits Desks**: HR departments handling group mediclaim escalations can streamline employee grievance filings with structured appeal packets.

---

## 5. Risks & Mitigation
- **Unauthorized Practice of Law**: Mitigated by prominent, persistent disclaimers ("Advisory information, not legal advice"), never guaranteeing outcomes, and providing standardized template formatting.
- **PII Exposure**: Mitigated by strict regex/token-based masking of Indian identification documents and in-memory processing.
