from __future__ import annotations

import re

BANNED = [
    r"\bwar on men\b",
    r"\brigged\b",
    r"\bcorrupt\b",
    r"\bwitch hunt\b",
    r"\banti-male conspiracy\b",
    r"\beveryone knew\b",
    r"\bthe data prove intent\b",
]

REQUIRES_QUALIFICATION = [
    r"\bfalse allegation\b",
    r"\bknowingly false\b",
    r"\bexonerated\b",
    r"\bproven innocent\b",
    r"\bdamages\b",
    r"\bpolice charged\b",
    r"\bboulder county police\b",
    r"\bdiscrimination\b",
    r"\billegal\b",
    r"\bunconstitutional\b",
    r"\bfabricated\b",
    r"\bmalicious\b",
]

ALLOWED_CONTEXT = {
    "damages": ["adjudicated damages", "not adjudicated damages", "damages ledger", "damages_summary", "damages award"],
    "unconstitutional": ["constitutional/trial error", "constitutional error"],
    "discrimination": ["sex-discrimination finding", "not sex discrimination", "sex discrimination"],
    "false allegation": ["not a false allegation finding", "no verified finding of false private allegation", "does not establish false allegation"],
    "knowingly false": ["knowingly false private allegations"],
    "malicious": ["malicious prosecution"],
    "fabricated": ["fabrication"],
}


def lint_text(text: str) -> list[str]:
    lower = text.lower()
    errors: list[str] = []
    for pattern in BANNED:
        if re.search(pattern, lower):
            errors.append(f"banned phrase: {pattern}")
    for pattern in REQUIRES_QUALIFICATION:
        match = re.search(pattern, lower)
        if not match:
            continue
        phrase = match.group(0)
        if any(token in lower for token in ALLOWED_CONTEXT.get(phrase, [])):
            continue
        errors.append(f"qualified legal phrase requires proof/context: {phrase}")
    return errors
