#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from merge_preprints import normalize_doi
from parse_cv import parse_cv

DRIVE_ID_PATTERNS = [
    re.compile(r"/file/d/([^/]+)"),
    re.compile(r"[?&]id=([^&]+)"),
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass
class SyncResult:
    row: int
    doi: str | None
    expected_title: str | None
    source_url: str
    local_url: str | None
    local_file: str | None
    source_ext: str | None
    verify_status: str
    verify_score: float
    doi_present_in_text: bool
    notes: str


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "preprint"


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_drive_id(url: str) -> str | None:
    for pattern in DRIVE_ID_PATTERNS:
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


def collect_cv_title_index(input_tex: Path) -> dict[str, str]:
    cv_data = parse_cv(input_tex)
    index: dict[str, str] = {}
    for section in cv_data.get("sections", []):
        if section.get("title") != "Research":
            continue
        for subsection in section.get("subsections", []):
            for item in subsection.get("items", []):
                doi = normalize_doi(item.get("doi"))
                if not doi:
                    continue
                title = item.get("title_guess") or item.get("text")
                if title and doi not in index:
                    index[doi] = title
    return index


def parse_content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r'filename\*=(?:UTF-8\'\')?([^;]+)', value, flags=re.I)
    if m:
        return m.group(1).strip().strip('"')
    m = re.search(r'filename="?([^";]+)"?', value, flags=re.I)
    if m:
        return m.group(1).strip()
    return None


def sniff_extension(payload: bytes, headers: dict[str, str], source_url: str) -> str:
    if payload.startswith(b"%PDF-"):
        return ".pdf"
    if payload.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return ".doc"
    if payload.startswith(b"{\\rtf"):
        return ".rtf"
    if payload.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                names = set(zf.namelist())
                if "word/document.xml" in names:
                    return ".docx"
                if "ppt/presentation.xml" in names:
                    return ".pptx"
                if "xl/workbook.xml" in names:
                    return ".xlsx"
        except zipfile.BadZipFile:
            pass
        return ".zip"

    cd_name = parse_content_disposition_filename(headers.get("content-disposition"))
    if cd_name and "." in cd_name:
        return "." + cd_name.rsplit(".", 1)[-1].lower()

    m = re.search(r"\.([a-z0-9]{2,5})(?:$|[?#])", source_url, flags=re.I)
    if m:
        return "." + m.group(1).lower()
    return ".bin"


def download_file(source_url: str, session: requests.Session, timeout: int = 120) -> tuple[bytes, dict[str, str]]:
    local_path = Path(source_url)
    if source_url.startswith("/") and local_path.exists() and local_path.is_file():
        return local_path.read_bytes(), {}

    file_id = find_drive_id(source_url)
    if file_id:
        direct_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        response = session.get(direct_url, timeout=timeout)
        response.raise_for_status()
        return response.content, dict(response.headers)

    response = session.get(source_url, timeout=timeout)
    response.raise_for_status()
    return response.content, dict(response.headers)


def extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return ""

    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    text = html.unescape(xml)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    chunks: list[str] = []
    for page in reader.pages[:2]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text:
            chunks.append(text)
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def verify_match(expected_title: str | None, doi: str | None, observed_text: str) -> tuple[str, float, bool, str]:
    observed_norm = normalize_text(observed_text)
    title_norm = normalize_text(expected_title or "")

    doi_present = False
    if doi and observed_text:
        doi_present = doi.lower() in observed_text.lower()

    if doi_present:
        return "verified", 1.0, True, "DOI found in document text"

    if not title_norm:
        return "unknown", 0.0, False, "No expected title available"
    if not observed_norm:
        return "low_confidence", 0.0, False, "Unable to extract document text"

    title_tokens = [tok for tok in title_norm.split() if len(tok) >= 4 and tok not in STOPWORDS]
    if not title_tokens:
        title_tokens = [tok for tok in title_norm.split() if tok]
    token_hits = sum(1 for tok in title_tokens if tok in observed_norm)
    token_score = (token_hits / len(title_tokens)) if title_tokens else 0.0

    probe = observed_norm[: max(2000, len(title_norm) * 3)]
    seq_score = SequenceMatcher(None, title_norm, probe).ratio()
    score = max(token_score, seq_score)

    if title_norm in observed_norm:
        return "verified", 1.0, False, "Expected title appears verbatim in document text"
    if score >= 0.80:
        return "verified", round(score, 4), False, "High title match confidence"
    if score >= 0.60:
        return "likely", round(score, 4), False, "Moderate title match confidence"
    return "low_confidence", round(score, 4), False, "Weak title match confidence"


def convert_docx_to_pdf(source_docx: Path, out_dir: Path) -> Path | None:
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(out_dir),
        str(source_docx),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    pdf_path = out_dir / f"{source_docx.stem}.pdf"
    if pdf_path.exists():
        return pdf_path
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="CV TeX file")
    parser.add_argument("--csv", required=True, type=Path, help="preprints.csv")
    parser.add_argument("--source-dir", default=Path("preprints/source"), type=Path)
    parser.add_argument("--static-dir", default=Path("src/static/preprints"), type=Path)
    parser.add_argument("--report-json", default=Path("src/cache/preprint_sync_report.json"), type=Path)
    parser.add_argument("--report-txt", default=Path("src/cache/preprint_sync_report.txt"), type=Path)
    parser.add_argument("--timeout", default=120, type=int)
    args = parser.parse_args()

    title_index = collect_cv_title_index(args.input)

    with args.csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "source_url" not in fieldnames:
        fieldnames.append("source_url")
    if "local_file" not in fieldnames:
        fieldnames.append("local_file")
    if "verify_status" not in fieldnames:
        fieldnames.append("verify_status")
    if "verify_score" not in fieldnames:
        fieldnames.append("verify_score")
    if "verify_notes" not in fieldnames:
        fieldnames.append("verify_notes")

    if args.source_dir.exists():
        shutil.rmtree(args.source_dir)
    if args.static_dir.exists():
        shutil.rmtree(args.static_dir)
    args.source_dir.mkdir(parents=True, exist_ok=True)
    args.static_dir.mkdir(parents=True, exist_ok=True)
    temp_pdf_dir = args.source_dir / "_converted_pdf"
    temp_pdf_dir.mkdir(parents=True, exist_ok=True)

    results: list[SyncResult] = []
    used_basenames: set[str] = set()

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 preprint-sync/1.0"})

    for idx, row in enumerate(rows, start=1):
        doi = normalize_doi(row.get("doi"))
        source_url = (row.get("source_url") or row.get("preprint_url") or "").strip()
        expected_title = (row.get("title") or "").strip() or (title_index.get(doi) if doi else None)

        if not source_url:
            results.append(
                SyncResult(
                    row=idx,
                    doi=doi,
                    expected_title=expected_title,
                    source_url="",
                    local_url=None,
                    local_file=None,
                    source_ext=None,
                    verify_status="missing_source",
                    verify_score=0.0,
                    doi_present_in_text=False,
                    notes="No source URL provided",
                )
            )
            continue

        base_root = slugify(doi or expected_title or f"preprint-{idx}")[:96]
        base = f"{idx:02d}_{base_root}"
        if base in used_basenames:
            suffix = 2
            while f"{base}-{suffix}" in used_basenames:
                suffix += 1
            base = f"{base}-{suffix}"
        used_basenames.add(base)

        try:
            payload, headers = download_file(source_url, session=session, timeout=args.timeout)
        except Exception as exc:
            results.append(
                SyncResult(
                    row=idx,
                    doi=doi,
                    expected_title=expected_title,
                    source_url=source_url,
                    local_url=None,
                    local_file=None,
                    source_ext=None,
                    verify_status="download_failed",
                    verify_score=0.0,
                    doi_present_in_text=False,
                    notes=f"Download failed: {exc}",
                )
            )
            continue

        source_ext = sniff_extension(payload, headers, source_url)
        source_file = args.source_dir / f"{base}{source_ext}"
        source_file.write_bytes(payload)

        observed_text = ""
        hosted_file: Path | None = None
        conversion_note = ""

        if source_ext == ".docx":
            observed_text = extract_docx_text(source_file)
            pdf_path = convert_docx_to_pdf(source_file, temp_pdf_dir)
            if pdf_path and pdf_path.exists():
                hosted_file = args.static_dir / f"{base}.pdf"
                shutil.copy2(pdf_path, hosted_file)
                conversion_note = "Converted DOCX to PDF for hosting"
            else:
                hosted_file = args.static_dir / source_file.name
                shutil.copy2(source_file, hosted_file)
                conversion_note = "DOCX conversion to PDF failed; hosting DOCX"
        elif source_ext == ".pdf":
            observed_text = extract_pdf_text(source_file)
            hosted_file = args.static_dir / source_file.name
            shutil.copy2(source_file, hosted_file)
        else:
            if source_ext in {".doc", ".rtf"}:
                conversion_note = "Non-DOCX office file; hosted original format"
            else:
                conversion_note = "Unknown format; hosted original file"
            hosted_file = args.static_dir / source_file.name
            shutil.copy2(source_file, hosted_file)

        if not observed_text and hosted_file and hosted_file.suffix.lower() == ".pdf":
            observed_text = extract_pdf_text(hosted_file)

        status, score, doi_present, note = verify_match(expected_title, doi, observed_text)
        notes = note
        if conversion_note:
            notes = f"{notes}; {conversion_note}"

        local_url = f"/assets/preprints/{hosted_file.name}" if hosted_file else None

        row["source_url"] = source_url
        if local_url:
            row["preprint_url"] = local_url
        row["local_file"] = hosted_file.name if hosted_file else ""
        row["verify_status"] = status
        row["verify_score"] = str(score)
        row["verify_notes"] = notes

        results.append(
            SyncResult(
                row=idx,
                doi=doi,
                expected_title=expected_title,
                source_url=source_url,
                local_url=local_url,
                local_file=hosted_file.name if hosted_file else None,
                source_ext=source_ext,
                verify_status=status,
                verify_score=score,
                doi_present_in_text=doi_present,
                notes=notes,
            )
        )

    with args.csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    counts: dict[str, int] = {}
    for result in results:
        counts[result.verify_status] = counts.get(result.verify_status, 0) + 1

    report = {
        "total_rows": len(results),
        "status_counts": counts,
        "results": [result.__dict__ for result in results],
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"total_rows: {len(results)}",
    ]
    for key in sorted(counts):
        lines.append(f"{key}: {counts[key]}")
    lines.append("")
    lines.append("rows:")
    for result in results:
        lines.append(
            f"- row={result.row} status={result.verify_status} score={result.verify_score} "
            f"file={result.local_file or '-'} note={result.notes}"
        )
    args.report_txt.parent.mkdir(parents=True, exist_ok=True)
    args.report_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    shutil.rmtree(temp_pdf_dir, ignore_errors=True)

    print(json.dumps({"total_rows": len(results), "status_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
