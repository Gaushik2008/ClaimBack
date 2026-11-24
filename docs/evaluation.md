# Evaluation protocol

Status: **plan**. No results yet. Fill in the results section only with numbers we have actually measured.

## Questions we want to answer

1. Does ClaimBack reach the same outcome as the Insurance Ombudsman on real cases?
2. Does it point to the clause the Ombudsman relied on?
3. Does it ever cite something that does not exist?
4. Is it meaningfully better than a plain LLM prompt on the same inputs?
5. Do real users and experts find the output useful?

## Data

- **Source:** published Insurance Ombudsman awards for health / mediclaim complaints.
- **Parsing:** extract complaint facts, insurer, the ground for repudiation, relevant clause, and outcome (allowed / partly allowed / dismissed).
- **Strip the answer:** the system only sees the facts, never the decision or the reasoning.
- **Split:** train / dev / test by **date**. The test set is the most recent awards.

### Contamination control

Public awards may appear in a language model's training data. Use the most recent awards for testing and report the date range, so the reader can judge. If results on older and newer cases differ sharply, say so.

**Update 2026-11-24:** the newest bulk-published awards may be from 2023 or earlier (recent awards seem to be available per complainant only), in which case recency alone cannot prevent contamination. If so: report that plainly, probe for memorisation (e.g. ask the model to complete award numbers or outcomes from facts it should not know), and put more weight on cases that cannot be in training data: real pilot letters, labelled by an expert.

### Selection bias

Cases that reach the Ombudsman are not a random sample of all rejections. State this wherever accuracy numbers are shown, and complement the benchmark with real user cases.

## Metrics

| Metric | Definition |
|---|---|
| Outcome agreement | Share of test cases where the predicted label matches the Ombudsman outcome (report the confusion matrix, not just accuracy) |
| Clause match | Share of cases where the system's top clause matches the clause relied on |
| Citation hallucination rate | Share of cited clauses / awards that do not exist or whose quote does not match (**target: 0%**) |
| Calibration | Does confidence track correctness? Report accuracy by confidence bucket |
| Letter quality | Blind rubric score by a domain expert (clarity, correct clause, correct escalation, tone) |
| Cost and latency | Per-case time and cost |

## Baselines and ablations

- **Baseline:** one prompt to a general LLM with the same documents, no retrieval, no rule checks.
- **Ablations:** remove, in turn, precedent retrieval, rule checks, the citation checker, and the clarification of missing documents. Report what each contributes.

## Human evaluation

- About 20 appeal letters (ClaimBack vs. baseline), shuffled and unlabelled, scored by an expert (an insurance advisor, claims professional or advocate).
- Real-user pilot: anonymised real rejection letters, run with the user's consent. Record what the user did next and whether it was useful. Do not claim outcomes (such as "claim was paid") unless they actually happened.

## Reporting template

| Experiment | N | ClaimBack | Baseline | Notes |
|---|---|---|---|---|
| Outcome agreement | | | | |
| Clause match | | | | |
| Hallucinated citations | | | | |
| Expert letter score | | | | |

Include the test date range, model versions, and any known failure modes.


## Update 2026-11-24: findings from the first real data

- Data actually available: the CIO Mediclaim Book 17 digest (about 2012 awards, four centres). It is a public PDF, so memorisation by LLMs cannot be ruled out; a measured memorisation check is still required.
- **The pooled benchmark is confounded by centre** (outcome mix differs sharply by ombudsman office). Always report the `centre_only` baseline next to any system. A system is only credible if it beats it, or if it is evaluated within a single balanced centre.
- Current honest benchmark: Chennai only (n=36), leave-one-out. All non-LLM baselines are at chance (about 50%). Intervals are wide; say so on the slide.
- Labels are rule-based and unverified until the 30-case audit is done.
