#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


DOI_RE = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)",
    re.IGNORECASE,
)


@dataclass
class PreprintRow:
    idx: int
    doi: str | None
    title: str
    preprint_url: str
    note: str


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    m = DOI_RE.search(raw)
    if m:
        val = m.group(1)
    else:
        val = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE).strip()
    val = val.strip().strip(".,;:)\"]}")
    if re.match(r"^10\.\d{4,9}/\S+$", val, flags=re.IGNORECASE):
        return val.lower()
    return None


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_preprints(path: Path) -> list[PreprintRow]:
    rows: list[PreprintRow] = []
    if not path.exists():
        return rows

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            verify_status = (row.get("verify_status") or "").strip().lower()
            if verify_status and verify_status not in {"verified", "likely", "manual_verified"}:
                # Keep uncertain rows in CSV for audit, but do not publish as linked preprints.
                continue

            doi = normalize_doi((row.get("doi") or "").strip())
            title = (row.get("title") or "").strip()
            preprint_url = (row.get("preprint_url") or "").strip()
            note = (row.get("note") or "").strip()
            if not preprint_url:
                continue
            rows.append(PreprintRow(idx=idx, doi=doi, title=title, preprint_url=preprint_url, note=note))
    return rows


def collect_publication_items(cv_data: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    pubs: list[tuple[str, str, dict[str, Any]]] = []
    for section in cv_data.get("sections", []):
        if section.get("title") != "Research":
            continue
        for subsection in section.get("subsections", []):
            subtitle = subsection.get("title", "")
            for item in subsection.get("items", []):
                pubs.append((section.get("title", "Research"), subtitle, item))
    return pubs


def attach_preprints(
    cv_data: dict[str, Any], preprints_path: Path, threshold: float = 0.86
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = load_preprints(preprints_path)
    pubs = collect_publication_items(cv_data)

    doi_index: dict[str, list[PreprintRow]] = {}
    for row in rows:
        if row.doi:
            doi_index.setdefault(row.doi, []).append(row)

    used_rows: set[int] = set()
    questionable: list[dict[str, Any]] = []

    matched_count = 0

    # DOI exact matching first.
    for _, subtitle, item in pubs:
        item["preprint_url"] = None
        item["preprint_note"] = None
        item["preprint_match"] = None

        doi = normalize_doi(item.get("doi"))
        if not doi:
            continue
        candidates = [r for r in doi_index.get(doi, []) if r.idx not in used_rows]
        if not candidates:
            continue
        chosen = candidates[0]
        item["preprint_url"] = chosen.preprint_url
        item["preprint_note"] = chosen.note or None
        item["preprint_match"] = {"type": "doi", "score": 1.0, "row": chosen.idx, "subsection": subtitle}
        used_rows.add(chosen.idx)
        matched_count += 1

    # Fuzzy title matching for remaining entries.
    for _, subtitle, item in pubs:
        if item.get("preprint_url"):
            continue

        pub_title = normalize_title(item.get("title_guess") or item.get("text") or "")
        if not pub_title:
            continue

        best: tuple[float, PreprintRow] | None = None
        tie = False

        for row in rows:
            if row.idx in used_rows:
                continue
            if row.doi:
                # DOI rows are already handled with strict matching.
                continue
            row_title = normalize_title(row.title)
            if not row_title:
                continue
            score = SequenceMatcher(None, pub_title, row_title).ratio()
            if best is None or score > best[0]:
                best = (score, row)
                tie = False
            elif best is not None and abs(score - best[0]) < 1e-9:
                tie = True

        if best is None:
            continue

        score, row = best
        if score < threshold or tie:
            continue

        item["preprint_url"] = row.preprint_url
        item["preprint_note"] = row.note or None
        item["preprint_match"] = {
            "type": "title",
            "score": round(score, 4),
            "row": row.idx,
            "subsection": subtitle,
            "title_source": row.title,
        }
        used_rows.add(row.idx)
        matched_count += 1

        if score < threshold + 0.05:
            questionable.append(
                {
                    "score": round(score, 4),
                    "pub_title": item.get("title_guess") or item.get("text"),
                    "matched_row": row.idx,
                    "matched_title": row.title,
                    "subsection": subtitle,
                }
            )

    unmatched = []
    for _, subtitle, item in pubs:
        if not item.get("preprint_url"):
            unmatched.append(
                {
                    "subsection": subtitle,
                    "title_guess": item.get("title_guess"),
                    "text": item.get("text"),
                    "doi": item.get("doi"),
                }
            )

    unused = []
    for row in rows:
        if row.idx not in used_rows:
            unused.append(
                {
                    "row": row.idx,
                    "doi": row.doi,
                    "title": row.title,
                    "preprint_url": row.preprint_url,
                    "note": row.note,
                }
            )

    report = {
        "total_publications": len(pubs),
        "matched_preprints": matched_count,
        "unmatched_publications": len(unmatched),
        "unused_preprints_rows": len(unused),
        "questionable_matches": questionable[:20],
        "unmatched_publication_samples": unmatched[:50],
        "unused_preprints_samples": unused[:50],
    }

    return cv_data, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv-json", required=True, type=Path)
    parser.add_argument("--preprints", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=0.86)
    args = parser.parse_args()

    cv_data = json.loads(args.cv_json.read_text(encoding="utf-8"))
    merged, report = attach_preprints(cv_data, args.preprints, threshold=args.threshold)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
