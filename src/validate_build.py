#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class HeadScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data: dict[str, str] = {}
        for k, v in attrs:
            if k is None:
                continue
            data[k.lower()] = v or ""
        if tag == "meta":
            self.meta.append(data)
        elif tag == "link":
            self.links.append(data)


def meta_values(scanner: HeadScanner, name: str) -> list[str]:
    out: list[str] = []
    needle = name.lower()
    for tag in scanner.meta:
        if tag.get("name", "").lower() == needle:
            value = tag.get("content", "").strip()
            if value:
                out.append(value)
    return out


def canonical_links(scanner: HeadScanner) -> list[str]:
    out: list[str] = []
    for tag in scanner.links:
        rel = tag.get("rel", "").lower().split()
        if "canonical" in rel:
            href = tag.get("href", "").strip()
            if href:
                out.append(href)
    return out


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("publications_manifest.json missing records list")
    return records


def validate_record(dist: Path, record: dict, site_url: str) -> list[str]:
    errors: list[str] = []
    slug = record.get("slug", "<unknown>")

    record_path = str(record.get("record_path") or "").lstrip("/")
    html_path = dist / record_path
    if not html_path.exists():
        return [f"{slug}: missing record HTML at {record_path}"]

    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    scanner = HeadScanner()
    scanner.feed(html_text)

    if not (record.get("abstract") or "").strip() and not bool(record.get("no_abstract_ok")):
        errors.append(f"{slug}: missing abstract and no_abstract_ok=false")

    if not meta_values(scanner, "citation_title"):
        errors.append(f"{slug}: missing citation_title meta tag")
    if not meta_values(scanner, "citation_author"):
        errors.append(f"{slug}: missing citation_author meta tag")
    if not meta_values(scanner, "citation_publication_date"):
        errors.append(f"{slug}: missing citation_publication_date meta tag")

    canon = canonical_links(scanner)
    if not canon:
        errors.append(f"{slug}: missing canonical link")
    else:
        expected_canonical = str(record.get("canonical_url") or "").strip()
        if expected_canonical and canon[0] != expected_canonical:
            errors.append(
                f"{slug}: canonical mismatch (found {canon[0]!r}, expected {expected_canonical!r})"
            )

    robots_tags = meta_values(scanner, "robots")
    if any("noindex" in tag.lower() for tag in robots_tags):
        errors.append(f"{slug}: robots meta contains noindex")

    if bool(record.get("has_local_pdf")):
        pdf_tags = meta_values(scanner, "citation_pdf_url")
        if not pdf_tags:
            errors.append(f"{slug}: has local PDF but missing citation_pdf_url")
        else:
            pdf_url = pdf_tags[0]
            expected_pdf_url = str(record.get("expected_citation_pdf_url") or "").strip()
            expected_relative = str(record.get("expected_pdf_relative") or "").strip()
            parsed = urlparse(pdf_url)
            same_dir_prefix = "/" + str(record.get("detail_url", "")).strip("/") + "/"

            if not parsed.path.lower().endswith(".pdf"):
                errors.append(f"{slug}: citation_pdf_url does not end with .pdf ({pdf_url})")
            if same_dir_prefix != "//" and not parsed.path.startswith(same_dir_prefix):
                errors.append(
                    f"{slug}: citation_pdf_url not under record directory ({pdf_url}, expected prefix {same_dir_prefix})"
                )
            if expected_pdf_url and pdf_url != expected_pdf_url:
                errors.append(
                    f"{slug}: citation_pdf_url mismatch (found {pdf_url!r}, expected {expected_pdf_url!r})"
                )
            if expected_relative and parsed.path != expected_relative:
                errors.append(
                    f"{slug}: citation_pdf_url path mismatch (found {parsed.path!r}, expected {expected_relative!r})"
                )

            local_pdf_path = dist / parsed.path.lstrip("/")
            if not local_pdf_path.exists():
                errors.append(f"{slug}: local PDF missing from build output ({parsed.path})")

    citation_files = record.get("citation_files") or {}
    for kind in ["bib", "ris", "json"]:
        rel = str(citation_files.get(kind) or "").lstrip("/")
        if not rel:
            errors.append(f"{slug}: missing citation file reference ({kind})")
            continue
        path = dist / rel
        if not path.exists():
            errors.append(f"{slug}: missing citation file in output ({rel})")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--site-url", default="https://chrisjvargo.com")
    args = parser.parse_args()

    dist = args.dist
    manifest_path = dist / "publications_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest missing: {manifest_path}")

    records = load_manifest(manifest_path)
    all_errors: list[str] = []
    for record in records:
        all_errors.extend(validate_record(dist, record, args.site_url.rstrip("/")))

    if all_errors:
        sys.stderr.write("Build validation failed:\n")
        for err in all_errors:
            sys.stderr.write(f"- {err}\n")
        raise SystemExit(1)

    print(f"Validation passed for {len(records)} publication record pages.")


if __name__ == "__main__":
    main()
