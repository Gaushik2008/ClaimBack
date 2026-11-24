# Architecture

Status: **draft plan**. Nothing here is implemented yet; update this file as decisions are made.

## Goals

1. Turn a rejection or partial-settlement into a verdict a non-expert can act on.
2. Never state something the sources do not support.
3. Make the system measurable (see [`evaluation.md`](evaluation.md)).

## Pipeline

| # | Stage | Input | Output | Notes |
|---|---|---|---|---|
| 1 | Document parsing | PDFs, photos | Clean text with page references | OCR for scans; keep page and clause anchors |
| 2 | Case extraction | Parsed text | `Case` object (below) | LLM extraction, then schema validation |
| 3 | Clause finder | `Case` + policy text | Candidate clauses, ranked | Retrieval over clause-level chunks |
| 4 | Rule checks | `Case` + clause | Pass / fail per check, with working | **Code, not LLM**: dates, waiting periods, sub-limits, deductions |
| 5 | Precedent retrieval | `Case` | Similar Ombudsman awards | Embedding + keyword hybrid |
| 6 | Verdict engine | Everything above | Verdict + confidence + reasoning | Reasoning must cite clause / award IDs |
| 7 | Letter generator | Verdict | Appeal letter + checklist | Citations validated before output |
| 8 | Deadline tracker | Case dates | Reminders | Workflow automation (n8n) |

## Core data shapes (draft)

```jsonc
// Case: what we extract from the user's documents
{
  "insurer": "string",
  "policy_name": "string",
  "policy_start": "YYYY-MM-DD",
  "admission_date": "YYYY-MM-DD",
  "diagnosis": "string",
  "claim_amount": 0,
  "settled_amount": 0,
  "stated_ground": "waiting_period | pre_existing | non_disclosure | room_rent | medical_necessity | documentation | other",
  "stated_reason_text": "string, verbatim from the letter",
  "evidence": [{"doc": "string", "page": 0, "quote": "string"}]
}

// Verdict
{
  "label": "strong_appeal | weak_appeal | insurer_correct",
  "confidence": 0.0,
  "reasoning": [{"claim": "string", "sources": ["clause:ID", "award:ID"]}],
  "missing_documents": ["string"],
  "escalation_path": ["insurer grievance officer", "Ombudsman"]
}
```

## Design decisions

- **Code does the arithmetic.** Waiting-period math, moratorium checks and proportionate deductions are deterministic functions with unit tests. The model extracts the facts; code evaluates them.
- **Citation checker.** Each cited clause or award ID must exist in the indexed corpus and the quoted text must match. Failures block the output.
- **Abstain when unsure.** If the policy is missing or parsing confidence is low, ask for the document instead of guessing.
- **Rules change.** IRDAI limits on waiting periods, moratorium and claim timelines change over time. Do not hard-code them from memory; load them from a dated rules file that cites the current circular, and verify before use.

## Components to decide

- Language and framework (proposed: Python backend, light web UI)
- Vector store (a local one is enough at this scale)
- LLM provider(s) and per-case cost budget
- OCR approach for scanned policies and letters

## Out of scope (for now)

Claims other than health, legal filing on the user's behalf, and any guarantee of outcome.
