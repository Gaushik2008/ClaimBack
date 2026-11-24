"""Build data/processed/awards.jsonl from award PDFs in data/raw/awards/.

Usage:
    python -m claimback.awards.build --raw data/raw/awards --out data/processed/awards.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .parser import parse_award, split_awards


def extract_text(pdf_path: Path) -> str:
    """Extract text with pdfplumber, falling back to pypdf. Scanned PDFs need OCR (not done here)."""
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        from pypdf import PdfReader

        return "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)


def build(raw_dir: Path, out_path: Path) -> dict:
    pdfs = sorted(raw_dir.rglob("*.pdf"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {"pdfs": len(pdfs), "awards": 0, "outcomes": Counter(), "missing": Counter(), "empty_pdfs": []}
    seen: set[str] = set()

    with out_path.open("w", encoding="utf-8") as fh:
        for pdf in pdfs:
            text = extract_text(pdf)
            if len(text.strip()) < 200:
                stats["empty_pdfs"].append(pdf.name)  # likely scanned: needs OCR
                continue
            for chunk in split_awards(text):
                award = parse_award(chunk)
                key = award.award_no or award.ref_no
                if key and key in seen:
                    continue  # same award repeated across files
                if key:
                    seen.add(key)
                record = award.to_dict()
                record["source_file"] = pdf.name
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                stats["awards"] += 1
                stats["outcomes"][award.outcome] += 1
                for m in award.missing:
                    stats["missing"][m] += 1
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=Path("data/raw/awards"))
    ap.add_argument("--out", type=Path, default=Path("data/processed/awards.jsonl"))
    args = ap.parse_args(argv)

    if not args.raw.exists() or not any(args.raw.rglob("*.pdf")):
        print(f"No PDFs found under {args.raw}. See data/README.md for what to download.", file=sys.stderr)
        return 1

    stats = build(args.raw, args.out)
    print(f"PDFs: {stats['pdfs']}  awards parsed: {stats['awards']}  -> {args.out}")
    print("Outcomes:", dict(stats["outcomes"]))
    print("Missing fields:", dict(stats["missing"]))
    if stats["empty_pdfs"]:
        print(f"{len(stats['empty_pdfs'])} PDF(s) had no extractable text (scanned?): {stats['empty_pdfs'][:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
