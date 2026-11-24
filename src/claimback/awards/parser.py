"""Parse Insurance Ombudsman award text into structured cases.

Layout this parser targets (Insurance Ombudsman Rules, 2017 era awards):

* header block starting "PROCEEDINGS BEFORE THE INSURANCE OMBUDSMAN"
* a numbered field table (1..19): insurer, nature of complaint, amounts, ...
* numbered sections: brief facts, submissions, result of hearing
* an "AWARD" heading, then the closing "Dated at ..." line

Labels vary between awards, so fields are matched by keyword, not exact string.
Anything that cannot be found is left as ``None``; never guessed.

Privacy: the complainant's name and address (field 1) and the "Case of X Vs Y"
line are deliberately not stored. The free-text sections can still contain
personal details, so processed output must stay out of version control.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Optional

HEADER_RE = re.compile(r"PROCEEDINGS\s+BEFORE\s+THE\s+INSURANCE\s+OMBUDSMAN", re.I)

# Start of the next numbered item, e.g. "\n 7. " or "\n14a. "
_NEXT_ITEM = r"(?=\n\s*\d{1,2}[a-z]?\s*[.)]\s+[A-Z(]|\Z)"

REF_RE = re.compile(r"\b([A-Z]{2,5}-[A-Z]-\d{3}-\d{4}-\d{4})\b")
AWARD_NO_RE = re.compile(r"\b(IO/[A-Z]{2,5}/A/[A-Z]{1,3}/\d{3,5}/\d{4}-\d{4})\b")

# (label regex for the field, attribute name)
FIELD_LABELS = {
    "insurer": r"Name\s+of\s+the\s+Insurer",
    "policy_type": r"Type\s+of\s+Policy",
    "reason": r"Reason\s+for\s+(?:partial\s+settlement|repudiation|short\s+settlement|rejection)(?:\s*\([^)\n]*\))?",
    "nature_of_complaint": r"Nature\s+of\s+Complaint",
    "claim_amount": r"Amount\s+of\s+Claim",
    "amount_paid": r"Amount\s+paid\s+by\s+the\s+Insurer",
    "relief_sought": r"Amount\s+of\s+Relief\s+sought(?:\s*\([^)\n]*\))?",
    "date_of_award": r"Date\s+of\s+Award\s*/?\s*Order",
}

SECTION_LABELS = {
    "facts": r"Brief\s+facts\s+of\s+the\s+complaint",
    "observations": r"Result\s+of\s+hearing(?:\s*\([^)\n]*\))?|Observations\s+and\s+Conclusion",
}

GROUND_KEYWORDS = [
    ("pre_existing", r"pre[\s-]*existing|\bPED\b"),
    ("waiting_period", r"waiting\s+period"),
    ("non_disclosure", r"non[\s-]*disclosure|suppress|misrepresent|concealment"),
    ("room_rent", r"room\s+rent|proportionate\s+deduction|ICU\s+charges"),
    ("medical_necessity", r"not\s+medically\s+necessary|medical\s+necessity|unnecessary\s+hospitali[sz]ation|no\s+active\s+line\s+of\s+treatment|domiciliary"),
    ("documentation", r"documents?\s+(?:not|were\s+not)\s+submitted|non[\s-]*submission|incomplete\s+documents|delay\s+in\s+intimation|late\s+intimation"),
    ("exclusion", r"exclusion|excluded|not\s+covered"),
]


@dataclass
class Award:
    ref_no: Optional[str] = None
    award_no: Optional[str] = None
    insurer: Optional[str] = None
    policy_type: Optional[str] = None
    nature_of_complaint: Optional[str] = None
    reason: Optional[str] = None
    claim_amount: Optional[float] = None
    amount_paid: Optional[float] = None
    relief_sought: Optional[float] = None
    date_of_award: Optional[str] = None
    facts: Optional[str] = None
    observations: Optional[str] = None
    outcome: str = "unknown"  # allowed | partly_allowed | dismissed | disposed | unknown
    ground_hint: Optional[str] = None  # keyword baseline only, not a model output
    char_len: int = 0
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def split_awards(text: str) -> list[str]:
    """Split a multi-award document on the header block.

    A header can be repeated inside one award (seen in the wild), so a chunk
    is kept only if it contains a numbered field table or an AWARD heading;
    otherwise it is merged into the previous chunk.
    """
    starts = [m.start() for m in HEADER_RE.finditer(text)]
    if not starts:
        return [text] if text.strip() else []
    starts.append(len(text))
    chunks = [text[a:b] for a, b in zip(starts, starts[1:])]

    merged: list[str] = []
    for chunk in chunks:
        looks_complete = bool(re.search(r"\n\s*\d{1,2}\s*[.)]\s+\S", chunk)) and (
            re.search(r"\bAWARD\b", chunk) or re.search(r"Dated\s+at", chunk, re.I)
        )
        if merged and not looks_complete and not _has_new_ref(chunk, merged[-1]):
            merged[-1] += chunk
        else:
            merged.append(chunk)
    return merged


def _has_new_ref(chunk: str, previous: str) -> bool:
    ref = REF_RE.search(chunk)
    return bool(ref) and ref.group(1) not in previous


def parse_amount(value: Optional[str]) -> Optional[float]:
    """'Rs. 1,23,456/-' -> 123456.0 ; returns None if no number is present."""
    if not value:
        return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", value)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip(" :-\t")
    return value or None


def _field(text: str, label: str) -> Optional[str]:
    m = re.search(
        rf"\n\s*\d{{1,2}}[a-z]?\s*[.)]\s*(?:{label})\s*[:\-]?\s*(.*?){_NEXT_ITEM}",
        text,
        re.I | re.S,
    )
    return _clean(m.group(1)) if m else None


def _section(text: str, label: str) -> Optional[str]:
    m = re.search(
        rf"\n\s*\d{{1,2}}\s*[.)]\s*(?:{label})\s*[:\-]?\s*(.*?){_NEXT_ITEM}",
        text,
        re.I | re.S,
    )
    return _clean(m.group(1)) if m else None


def classify_outcome(text: str) -> str:
    """Outcome from the closing part of the award only (not the submissions)."""
    m = re.search(r"\n\s*AWARD\b", text)
    tail = text[m.start():] if m else text[-3000:]
    t = re.sub(r"\s+", " ", tail).lower()
    if re.search(r"complaint\s+is\s+(?:hereby\s+)?(?:not\s+allowed|dismissed|rejected)|not\s+(?:allowed|sustainable)|no\s+relief", t):
        return "dismissed"
    if re.search(r"(?:partly|partially)\s+allowed", t):
        return "partly_allowed"
    if re.search(r"complaint\s+is\s+(?:hereby\s+)?allowed|is\s+allowed", t):
        return "allowed"
    if re.search(r"disposed\s+of", t):
        return "disposed"
    return "unknown"


def guess_ground(*texts: Optional[str]) -> Optional[str]:
    """Cheap keyword baseline for the rejection ground. First match wins."""
    blob = " ".join(t for t in texts if t)
    for name, pattern in GROUND_KEYWORDS:
        if re.search(pattern, blob, re.I):
            return name
    return None


def parse_award(text: str) -> Award:
    text = "\n" + text.replace("\r", "")
    award = Award(char_len=len(text))

    ref = REF_RE.search(text)
    award.ref_no = ref.group(1) if ref else None
    ano = AWARD_NO_RE.search(text)
    award.award_no = ano.group(1) if ano else None

    for attr, label in FIELD_LABELS.items():
        value = _field(text, label)
        if attr in ("claim_amount", "amount_paid", "relief_sought"):
            setattr(award, attr, parse_amount(value))
        else:
            setattr(award, attr, value)

    for attr, label in SECTION_LABELS.items():
        setattr(award, attr, _section(text, label))

    award.outcome = classify_outcome(text)
    award.ground_hint = guess_ground(award.reason, award.nature_of_complaint, award.facts)

    required = ["insurer", "nature_of_complaint", "facts"]
    award.missing = [f for f in required if getattr(award, f) is None]
    if award.outcome == "unknown":
        award.missing.append("outcome")
    return award
