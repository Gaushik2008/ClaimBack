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
- [x] Investigated why the award PDFs could not be found. Findings: the cioins.co.in homepage has no awards menu (only Archives and Download links, which the workspace cannot open); the CIO annual report 2023-24 describes a per-complainant award download using a registered mobile number, which suggests recent awards may not be published in bulk; older monthly PDFs do exist at direct links (found for Nov 2019, Apr 2021, Apr 2023, May 2023). **Consequence:** "use the newest awards as the test set" may not be possible, so the contamination control in `docs/evaluation.md` needs revising. Not resolved yet.


## 2026-11-24 (build, day 1, continued: real data from the uploaded Mediclaim book)
- [x] Obtained real data: the CIO "Mediclaim Book 17" digest (376 pages, text layer, ~400 case summaries, mostly 2012 awards) uploaded by the team. Raw PDF lives in `data/raw/digests/` (git-ignored)
- [x] Built a digest parser (`src/claimback/awards/digest.py`; `python -m claimback.awards.digest`). 326 cases parsed (Ahmedabad 207, Chennai 57, Delhi 35, Kolkata 27). Complainant names are not stored. Outcome and ground labels are **rule-based and not hand-verified**: 251 labelled (allowed 79, dismissed 147, disposed 25), 75 unknown. A spot check of 14 cases found 2 wrong labels before fixes; the rules were then tightened, but real label accuracy is still unmeasured. `data/processed/label_audit.json` holds 30 cases for a human to check
- [x] Built the benchmark (`src/claimback/eval/bench.py`): binary task (relief vs insurer upheld) from case facts only, outcome-stating sentences removed, deterministic split stratified by centre and outcome (149 train / 65 test), bootstrap CIs
- [x] Built baselines and ran them (`python -m claimback.eval.run`, results in `eval/results.json`)
- [x] **Key finding: the pooled benchmark is confounded by centre.** Ahmedabad cases are 113 upheld vs 3 relief; Delhi 34 relief vs 1 upheld; Kolkata 25 vs 2. A centre-only baseline scores 89.2% accuracy and a TF-IDF precedent kNN 90.8%, so the kNN adds nothing real. Do **not** report the pooled number as a system result
- [x] Honest floor: within Chennai only (n=36, 17 relief / 19 upheld), leave-one-out accuracy is 50-53% for every baseline, i.e. chance. An LLM system must beat this, on a small sample, with wide intervals
- [x] Wrote the LLM predictor (`src/claimback/eval/llm.py`): retrieves 5 precedents, asks for a JSON verdict, verifies that every cited case id was actually retrieved (citation-hallucination rate). **Not run against a live model** (no API key available here); tested with a fake client only
- [x] 15 unit tests pass (parser, leakage filter, split determinism, metrics, baselines, citation verifier, LLM wrapper with a fake client)

### Not done / next
- [ ] Human-check `data/processed/label_audit.json` (30 cases) and report label accuracy
- [ ] Run the LLM system and a plain single-prompt LLM on the Chennai set (needs `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`); report with CIs
- [ ] Memorisation check (these 2012 awards are public and may be in training data)
- [ ] Policy-wording parser, date/waiting-period checker, appeal-letter generator, UI, n8n deadline tracker
- [ ] Collect 5-10 real rejection letters from real users (the strongest evidence available)

## 2026-11-24 (NVIDIA backend)
- [x] Switched the LLM backend to NVIDIA Nemotron 3 Ultra (`nvidia/nemotron-3-ultra-550b-a55b`) through the OpenAI-compatible endpoint `https://integrate.api.nvidia.com/v1`; key is read from `NVIDIA_API_KEY` and never stored. Model id taken from NVIDIA's build page
- [x] Added a plain single-prompt baseline (`PlainLLM`) and `python -m claimback.eval.run_llm` (plain vs ClaimBack-RAG, Chennai leave-one-out, citation-hallucination rate). 16 tests pass with fake clients
- [ ] **Not yet run live**: the authoring sandbox cannot reach NVIDIA and has no key. Run locally: `export NVIDIA_API_KEY=...; python -m claimback.eval.run_llm --limit 5` first, then the full run

## 2026-11-24
- Verified 2 of 7 real-case leads against Indian Kanoon (see docs/real_case_leads.md); 5 not found, none to be cited.
- Added tests/fixtures/SYNTHETIC_awards.md (100 fictional awards, test/demo only, excluded from all metrics; fixed stray markup in entry 9055).
- Added eval/verified_real_cases.json (3 sourced HC orders; demo only, not in metrics). Note: all 3 are insurer losses, so selection bias applies.

## 2026-11-24 (books 10, 11, 18)
- Parser fix: Book 18 has no blank lines between paragraphs, so every case body was dropped (239/393 unknown). Added _fallback_paras and three outcome rules ("complaint dismissed", "complaint succeeds", "no formal award").
- Result on the 3 new books (rule-based labels, NOT hand-verified): 700 unique cases (192+115+393 minus duplicates); 220 allowed, 352 dismissed, 13 disposed, 115 unknown.
- Parse misses ~8-25% of "Case No" lines per book (e.g. Book10 192 of 209), cause not yet investigated.
- Same centre confound persists: Ahmedabad 306 dismissed vs 61 allowed; Delhi 123 allowed vs 8 dismissed. Chennai only 25 labelled.
- The outcome-rule change also affects Book 17 labels; re-run eval.run and re-audit label_audit.json.
- Data stays in data/raw (git-ignored), not committed.
