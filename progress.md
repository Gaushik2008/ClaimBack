# Progress

## 2026-11-24
- [x] Chose the idea (ClaimBack) and track (C1, "The $15-an-hour expert")
- [x] Wrote README.md and the docs: `docs/architecture.md`, `docs/evaluation.md`, `data/README.md`
- [x] Created the repo skeleton (`src/`, `eval/`, `prompts/`, `tests/`, `data/`), MIT license, `.gitignore`, `pyproject.toml`
- [x] Pushed everything to GitHub

## 2026-11-24 (build, day 1)
- [x] Tested whether the workspace can download Ombudsman awards: **blocked** (the network policy returns 403 for cioins.co.in), so award PDFs must be downloaded manually into `data/raw/awards/`; steps added to `data/README.md`
- [x] Inspected the layout of a real award (fields 1-19, numbered sections, `AWARD` heading, outcome wording) to design the parser
- [x] Built the award parser (`src/claimback/awards/parser.py`): splits multi-award files, extracts insurer, nature of complaint, reason, amounts, facts, observations, outcome label, and a keyword ground-hint baseline. Leaves missing fields empty; does not store the complainant's name or address
- [x] Built the PDF-to-JSONL build step (`python -m claimback.awards.build`) with a summary of parsed awards, outcomes and missing fields
- [x] Added 9 unit tests; all pass. **Caveat:** tested on a synthetic fixture and a synthetic PDF only, not yet on real award PDFs

