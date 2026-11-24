"""Privacy and PII masking for ClaimBack.

Masks sensitive personal identifiers before any text goes to an LLM:
- Aadhaar numbers (12-digit patterns, formatted with spaces/dashes or contiguous)
- PAN numbers (Permanent Account Number: 5 letters, 4 digits, 1 letter)
- Indian mobile phone numbers (10 digits, optional +91/0 prefix)
- Policy numbers (common patterns e.g. 12-20 digit/alphanumeric sequences)
- Claim numbers
- Email addresses
"""
from __future__ import annotations

import re
from typing import Tuple

# Regex patterns
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# PAN: 5 uppercase letters, 4 digits, 1 letter
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)
# Aadhaar: 12 digits, often formatted as 4-4-4
AADHAAR_RE = re.compile(r"\b[2-9][0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b")
# Indian mobile phones: +91 or 0 followed by 10 digits starting with 6, 7, 8, or 9
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9][0-9]{4}[\s-]?[0-9]{5}\b")
# Policy and claim numbers
POLICY_NUM_RE = re.compile(r"(?i)\b(?:policy\s*(?:no\.?|number|#)?\s*[:\-]?\s*)([A-Z0-9\-/]{6,30})\b")
CLAIM_NUM_RE = re.compile(r"(?i)\b(?:claim\s*(?:no\.?|number|#|id)?\s*[:\-]?\s*)([A-Z0-9\-/]{6,30})\b")


def mask_pii(text: str) -> Tuple[str, dict]:
    """Masks PII in the input text and returns (masked_text, redaction_counts)."""
    if not text:
        return "", {}

    counts = {
        "email": 0,
        "pan": 0,
        "aadhaar": 0,
        "phone": 0,
        "policy_number": 0,
        "claim_number": 0,
    }

    # Mask email
    def _mask_email(m):
        counts["email"] += 1
        return "[EMAIL_REDACTED]"

    masked = EMAIL_RE.sub(_mask_email, text)

    # Mask PAN
    def _mask_pan(m):
        counts["pan"] += 1
        return "[PAN_REDACTED]"

    masked = PAN_RE.sub(_mask_pan, masked)

    # Mask Aadhaar
    def _mask_aadhaar(m):
        counts["aadhaar"] += 1
        return "[AADHAAR_REDACTED]"

    masked = AADHAAR_RE.sub(_mask_aadhaar, masked)

    # Mask Phone
    def _mask_phone(m):
        counts["phone"] += 1
        return "[PHONE_REDACTED]"

    masked = PHONE_RE.sub(_mask_phone, masked)

    # Mask Policy Number
    def _mask_policy(m):
        counts["policy_number"] += 1
        return m.group(0).replace(m.group(1), "[POLICY_NO_REDACTED]")

    masked = POLICY_NUM_RE.sub(_mask_policy, masked)

    # Mask Claim Number
    def _mask_claim(m):
        counts["claim_number"] += 1
        return m.group(0).replace(m.group(1), "[CLAIM_NO_REDACTED]")

    masked = CLAIM_NUM_RE.sub(_mask_claim, masked)

    return masked, counts
