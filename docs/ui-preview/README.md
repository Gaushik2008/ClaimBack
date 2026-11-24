# Light-theme UI preview (design alternative)

`claimback-light-preview.html` is a single static page (open it in a browser) kept as a design reference. The live app UI is `app/static/index.html`, served by `app/server.py`; this file does not replace it.

What it shows: light theme, a hero with a sample letter and date-check card, a working browser-only date check with a draft appeal letter, and an evidence section with only measured numbers. The 60-month moratorium and waiting-period rules here must be verified against current IRDAI sources (see `src/claimback/config/irdai.json` and `src/claimback/rules/dates.py` for the app's own rules).
