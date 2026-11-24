# Data

No raw data is committed to this repository (see `.gitignore`). This file says what to get and where to put it.

## Sources

| Data | Where | Goes in |
|---|---|---|
| Insurance Ombudsman awards (health / mediclaim) | Monthly award PDFs on [cioins.co.in](https://www.cioins.co.in) | `data/raw/awards/` |
| Insurer policy wordings | Insurer websites (start with 3–5 popular insurers) | `data/raw/policies/` |
| IRDAI circulars and statistics | [irdai.gov.in](https://irdai.gov.in) | `data/raw/irdai/` |
| Real rejection letters from pilot users | Provided with consent, **anonymised** | `data/raw/letters/` (never committed) |

## Rules

- Check each source's terms of use before sharing derived data.
- Remove names, policy numbers, phone numbers and addresses from any real user document before it is stored or used in a demo.
- Parsed outputs go in `data/processed/` and are git-ignored by default.
- Record the download date and URL of everything you add in `data/SOURCES.log`.

## Getting the awards (manual step)

The assistant workspace cannot reach cioins.co.in (blocked by its network policy), so download the PDFs yourself:

1. Open the monthly awards listing on [cioins.co.in](https://www.cioins.co.in) and pick **health** awards (individual and group), starting with the **most recent months**. The test set must be the newest awards.
2. Save the PDFs into `data/raw/awards/` (sub-folders are fine, e.g. `data/raw/awards/2026-10/`).
3. Build the structured file:

   ```bash
   pip install -e ".[dev]"
   python -m claimback.awards.build --raw data/raw/awards --out data/processed/awards.jsonl
   ```

The script prints how many awards were parsed, the outcome counts and which fields were missing. PDFs with no extractable text are listed separately; they are scans and need OCR.
