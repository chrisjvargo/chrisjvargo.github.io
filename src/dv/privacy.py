from __future__ import annotations

import re
from pathlib import Path

PRIVATE_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),
    "date_of_birth": re.compile(r"\b(?:dob|date of birth)\b", re.I),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "restricted_path": re.compile(r"(?:^|[\"'(/\\])data/restricted(?:[\"')/\\]|$)", re.I),
}


def scan_text(text: str) -> list[str]:
    return [name for name, pattern in PRIVATE_PATTERNS.items() if pattern.search(text)]


def scan_dist(dist: Path) -> list[str]:
    errors: list[str] = []
    for path in dist.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".json", ".csv", ".txt", ".xml"}:
            for hit in scan_text(path.read_text(encoding="utf-8", errors="ignore")):
                errors.append(f"{path}: {hit}")
    return errors
