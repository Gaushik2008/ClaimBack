"""Policy wording parser for ClaimBack.

Parses policy wording text or PDF into clauses (id, title, text).
Detects:
- Initial 30-day waiting period (Clause 4.1 / 4.2 / standard)
- Specific illness waiting periods (24/36/48 months)
- Pre-existing disease (PED) clauses
- Room rent / ICU sub-limits and co-pay
- Permanent exclusions
Verifies verbatim clause presence in the user's uploaded policy text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PolicyClause:
    clause_id: str
    title: str
    text: str
    category: str  # waiting_period | ped | sublimit | exclusion | copay | other


@dataclass
class ParsedPolicy:
    clauses: List[PolicyClause] = field(default_factory=list)
    raw_text: str = ""

    def get_clause_by_id(self, clause_id: str) -> Optional[PolicyClause]:
        for c in self.clauses:
            if c.clause_id.lower() == clause_id.lower():
                return c
        return None


CLAUSE_HEADER_RE = re.compile(
    r"(?im)^[ \t]*(?:clause|section|condition)?\s*([0-9]+(?:\.[0-9]+)*)[.:\s\-]+([A-Za-z0-9 ,'\-/()]+)$"
)


def categorize_clause_text(text: str, title: str = "") -> str:
    combined = (title + " " + text).lower()
    if "first 30 days" in combined or "30 days waiting" in combined:
        return "waiting_period"
    if "pre-existing" in combined or "ped" in combined:
        return "ped"
    if "room rent" in combined or "icu charges" in combined or "proportionate" in combined:
        return "sublimit"
    if "co-pay" in combined or "copay" in combined:
        return "copay"
    if "waiting period" in combined or "two years" in combined or "24 months" in combined:
        return "waiting_period"
    if "exclusion" in combined or "not covered" in combined or "permanently excluded" in combined:
        return "exclusion"
    return "other"


def parse_policy(text: str) -> ParsedPolicy:
    """Parses policy wording text into structured clauses."""
    lines = text.splitlines()
    clauses: List[PolicyClause] = []

    current_id: Optional[str] = None
    current_title: str = ""
    current_body: List[str] = []

    for line in lines:
        m = CLAUSE_HEADER_RE.match(line.strip())
        if m and len(m.group(1)) <= 10 and len(m.group(2)) < 100:
            if current_id and current_body:
                body_txt = " ".join(current_body).strip()
                cat = categorize_clause_text(body_txt, current_title)
                clauses.append(PolicyClause(clause_id=current_id, title=current_title, text=body_txt, category=cat))
            current_id = m.group(1).strip()
            current_title = m.group(2).strip()
            current_body = []
        else:
            if current_id:
                current_body.append(line.strip())

    if current_id and current_body:
        body_txt = " ".join(current_body).strip()
        cat = categorize_clause_text(body_txt, current_title)
        clauses.append(PolicyClause(clause_id=current_id, title=current_title, text=body_txt, category=cat))

    # If header regex found few or no clauses, search by common headings
    if not clauses:
        # Fallback block parsing
        blocks = re.split(r"\n\s*\n", text)
        for i, b in enumerate(blocks):
            clean_b = " ".join(b.split())
            if len(clean_b) > 40:
                cat = categorize_clause_text(clean_b)
                if cat != "other":
                    clauses.append(PolicyClause(clause_id=f"Sec-{len(clauses)+1}", title=cat.upper(), text=clean_b, category=cat))

    return ParsedPolicy(clauses=clauses, raw_text=text)


def verify_clause_presence(clause_id_or_num: str, policy_text: str) -> bool:
    """Verifies whether the cited clause number/identifier actually exists verbatim in the policy text.

    Rule: Never claim a clause is verified unless confirmed in the uploaded document.
    """
    if not clause_id_or_num or not policy_text:
        return False
    # Pattern searches for clause X or condition X or section X
    pat = re.compile(rf"(?i)\b(?:clause|condition|section|sub-clause|rule)?\s*(?:no\.?)?\s*{re.escape(clause_id_or_num.strip())}\b")
    return bool(pat.search(policy_text))
