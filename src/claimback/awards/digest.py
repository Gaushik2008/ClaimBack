"""Parse CIO "Mediclaim book" digests (short case summaries).

Layout per case: "<CENTRE> OMBUDSMAN CENTRE", "Case No.xx-xxx-xxxx-xx", a
"<complainant> V/s. <insurer>" line, "Award dated ...", dispute type, then a
facts paragraph and a reasoning/outcome paragraph.

Privacy: the complainant's name is NOT stored. Only the insurer is kept.
Missing fields stay None. Outcome and ground labels are rule-based.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CENTRE_RE = re.compile(r"\n[ \t]*([A-Z][A-Z ]+?) OMBUDSMAN CENTRE[ \t]*\n")
CASE_RE = re.compile(r"Case\s*No\.?\s*([0-9A-Za-z][0-9A-Za-z\-/(). ]{4,40}?)(?:\n|$)")
VS_RE = re.compile(r"^(.*?)\s+V/?s\.?\s+(.*)$", re.I)
DATE_RE = re.compile(r"Award\s+dated\s+(.+)", re.I)
MONEY_RE = re.compile(r"Rs\.?\s*([\d,]+(?:\.\d+)?)")

OUTCOME_RULES = [  # order matters: first match wins
    ("dismissed", r"(?:settlement|decision|repudiation|deduction)[^.]{0,50}(?:is|are)\s+(?:in\s+order|correct|valid)"),
    ("allowed", r"(?:paid|pay|payment)[^.]{0,80}within\s+\d+\s+days|consent\s+letter"),
    ("disposed", r"mutually\s+agreed|redressed|settled\s+(?:the\s+)?(?:claim|complaint)\s+during|without\s+any\s+formal\s+award"),
    ("allowed", r"award\s+shall\s+be\s+implemented|direction\s+to\s+the\s+insur|were\s+allowed|complaint\s+is\s+allowed"),
    ("disposed", r"beyond\s+the\s+jurisdiction|without\s+any\s+quantitative|withdrawn|time[\s-]*barred|not\s+maintainable|closed\s+the\s+file"),
    ("dismissed", r"not\s+payable|no\s+room\s+(?:for|to)\s+interfere|can\s*not\s+submit\s+any|decision[^.]{0,60}(?:justified|upheld|just\b|proper|fair|correct|in order)|(?:justified|rightly|upheld)|not\s+tenable\s+for\s+complainant|fails\s+to\s+succeed|without\s+any\s+relief|decision\s+is\s+(?:fully\s+)?(?:upheld|justified|just|proper)|(?:just|fair|justified)\s+(?:and\s+(?:fair|proper)\s+)?without|cannot\s+be\s+interfered|no\s+(?:new\s+)?ground\s+to\s+interfere|right\s+decision|stands\s+disposed|approved\s+the\s+decision"),
    ("allowed", r"complaint\s+is\s+(?:partly\s+)?allowed|not\s+(?:tenable|sustainable)|(?:unjustified|not\s+justified)|directed\s+to\s+pay|is\s+directed|shall\s+pay|award(?:ed)?\s+(?:of\s+)?Rs|pay\s+Rs|reimburse|set\s+aside|not\s+justified|liable\s+to\s+pay|complaint\s+(?:is\s+)?allowed|should\s+(?:pay|settle)"),
]
GROUND_RULES = [
    ("non_disclosure", r"non[\s-]*disclos|suppress|misrepresent|conceal|not\s+mentioned\s+in\s+the\s+proposal"),
    ("pre_existing", r"pre[\s-]*existing|\bPED\b|since\s+\d+\s+(?:year|month)|duration\s+of\s+(?:the\s+)?disease"),
    ("waiting_period", r"waiting\s+period|first\s+30\s+days|two\s+years|excluded\s+for\s+two|4\.3|4\.2"),
    ("room_rent", r"room\s+rent|proportionate|capping|ICU\s+charges"),
    ("not_medically_necessary", r"not\s+medically\s+necessary|domiciliary|no\s+active\s+line|unnecessary|only\s+for\s+diagnostic|investigation(?:s)?\s+only"),
    ("documentation_or_fraud", r"fals[ei]|bogus|fake|forged|document|intimation|investigation\s+report|discrepanc"),
    ("exclusion", r"exclu|not\s+covered|congenital|cosmetic|dental|permanently"),
    ("deduction_partial", r"deduct|partial"),
]


@dataclass
class Case:
    case_id: Optional[str] = None
    centre: Optional[str] = None
    insurer: Optional[str] = None
    award_date: Optional[str] = None
    year: Optional[int] = None
    dispute_type: Optional[str] = None
    claim_kind: Optional[str] = None  # repudiation | partial
    facts: str = ""
    reasoning: str = ""
    amounts: list[float] = field(default_factory=list)
    outcome: str = "unknown"  # dismissed | allowed | disposed | unknown
    ground: Optional[str] = None
    clauses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _norm(s: str) -> str:
    return " ".join(s.replace("\u2019", "'").split())


def _first(rules, text):
    for label, pat in rules:
        if re.search(pat, text, re.I):
            return label
    return None


CENTRE_HDR = re.compile(r"([A-Z]{4,}) OMBUDSMAN CENT(?:RE|ER)", re.I)
AWARD_DATE_ANY = re.compile(r"(?:Award(?:\s+No\.?\s*\S+)?\s+dated|AWARD\s+DATED)\s*[:\-]?\s*([0-9A-Za-z.\-/ ,]{6,30})", re.I)
KIND_WORDS = re.compile(r"(repudiation|partial|settlement|rejection|non[\s-]*settlement)", re.I)


def _centre_from_id(cid: str, last: Optional[str]) -> Optional[str]:
    if cid.startswith("IO"):
        return "Chennai"
    if cid.startswith("GI/"):
        return "Delhi"
    if re.match(r"\d{2}-\d{3}-\d{4}-\d{2}", cid):
        return "Ahmedabad"
    return last


def parse_case(centre: Optional[str], block: str) -> Optional[Case]:
    """``block`` starts at the 'Case No' line."""
    m = CASE_RE.search(block)
    if not m:
        return None
    c = Case(case_id=_norm(m.group(1)).replace(" ", ""), centre=centre)
    raw_lines = block.split("\n")
    lines = [l.strip() for l in raw_lines]
    # insurer: line after a bare 'vs' line, or 'X V/s. Y'
    for i, l in enumerate(lines[:14]):
        mv = VS_RE.match(l)
        if mv and "Case No" not in l and len(l) < 160:
            c.insurer = _norm(mv.group(2)).rstrip(". ")
            if not c.insurer:
                continue
            break
        if re.fullmatch(r"(?i)vs\.?", l) or re.match(r"(?i)^vs\.?\s+\S", l):
            rest = re.sub(r"(?i)^vs\.?\s*", "", l)
            if rest:
                c.insurer = _norm(rest).rstrip(". ")
            else:
                nxt = [x for x in lines[i + 1:i + 5] if x]
                c.insurer = _norm(nxt[0]).rstrip(". ") if nxt else None
            break
    head = "\n".join(lines[:16])
    md = AWARD_DATE_ANY.search(head)
    if md:
        c.award_date = _norm(md.group(1))
        my = re.search(r"(20\d{2})", c.award_date)
        if my:
            c.year = int(my.group(1))
        else:
            my2 = re.search(r"\.(\d{2})\b", c.award_date)
            c.year = 2000 + int(my2.group(1)) if my2 else None
    for l in lines[:14]:
        if KIND_WORDS.search(l) and ("mediclaim" in l.lower() or "claim" in l.lower() or "settlement" in l.lower()) and len(l) < 80 and "dated" not in l.lower():
            c.dispute_type = _norm(l)
            break
    # body: paragraphs after the header lines (paragraphs split on blank lines)
    text = "\n".join(raw_lines)
    text = re.sub(r"\*{5,}.*", "", text, flags=re.S)  # cut at separator line
    paras = [_norm(p) for p in re.split(r"\n\s*\n", text)]
    paras = [p for p in paras if len(p) > 70 and not p.lower().startswith(("case no", "award"))]
    # drop header-ish paragraphs (party lines)
    paras = [p for p in paras if not VS_RE.match(p) or len(p) > 160]
    if not paras:
        return c
    c.facts = paras[0]
    c.reasoning = " ".join(paras[1:])
    full = " ".join(paras)
    dt = (c.dispute_type or "").lower() + " " + full[:160].lower()
    c.claim_kind = "partial" if "partial" in dt or "short" in dt or "deduct" in dt else ("repudiation" if re.search(r"repudiat|reject|not allowed|denied", dt) else None)
    c.amounts = [float(x.replace(",", "")) for x in MONEY_RE.findall(full) if re.fullmatch(r"[\d,]*\d(?:\.\d+)?", x)]
    c.clauses = sorted(set(re.findall(r"(?:clause|condition|exclusion)s?\s*(?:no\.?)?\s*(\d+(?:\.\d+)?)", full, re.I)))
    tail = c.reasoning or c.facts
    c.outcome = _first(OUTCOME_RULES, tail[-220:]) or _first(OUTCOME_RULES, tail[-400:]) or _first(OUTCOME_RULES, full) or "unknown"
    c.ground = _first(GROUND_RULES, full)
    return c


def split_digest(text: str) -> list[tuple[Optional[str], str]]:
    text = text.replace("\f", "\n")
    marks = [m.start() for m in re.finditer(r"Case\s*No\.?\s*[0-9A-Za-z]", text)]
    hdrs = [(m.start(), m.group(1).title()) for m in CENTRE_HDR.finditer(text)]
    out = []
    for i, st in enumerate(marks):
        en = marks[i + 1] if i + 1 < len(marks) else len(text)
        last = None
        for pos, name in hdrs:
            if pos <= st:
                last = name
        out.append((last, text[st:en]))
    return out


def build_digest(pdf_text: str) -> list[Case]:
    seen, out = set(), []
    for centre, block in split_digest(pdf_text):
        m = CASE_RE.search(block)
        cid = _norm(m.group(1)).replace(" ", "") if m else ""
        c = parse_case(_centre_from_id(cid, centre), block)
        if c and c.case_id not in seen:
            seen.add(c.case_id)
            out.append(c)
    return out


def summarize(cases: list[Case]) -> dict:
    return {
        "cases": len(cases),
        "outcomes": dict(Counter(c.outcome for c in cases)),
        "grounds": dict(Counter(c.ground for c in cases)),
        "centres": dict(Counter(c.centre for c in cases)),
        "no_insurer": sum(c.insurer is None for c in cases),
    }


def main(argv=None) -> int:
    import argparse, subprocess

    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="data/raw/digests/Mediclaim-Book17.pdf")
    ap.add_argument("--out", default="data/processed/cases.jsonl")
    a = ap.parse_args(argv)
    text = subprocess.run(["pdftotext", "-layout", a.pdf, "-"], capture_output=True, text=True, check=True).stdout
    cases = build_digest(text)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        for c in cases:
            fh.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
    print(json.dumps(summarize(cases), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
