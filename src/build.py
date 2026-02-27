#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pypdf import PdfReader

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from merge_preprints import attach_preprints, normalize_doi  # noqa: E402
from parse_cv import clean_latex_text, parse_cv  # noqa: E402

AUTHOR_RE = re.compile(r"([A-Z][A-Za-z'’`.-]+),\s*((?:[A-Z]\.\s*){1,5})")

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

DEFAULT_OG_IMAGE = "/assets/og-default.png"
HIDDEN_RESEARCH_SUBSECTIONS = {"manuscripts under review"}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def copy_static(static_dir: Path, out_assets: Path) -> None:
    ensure_dir(out_assets)
    for src in static_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(static_dir)
            dst = out_assets / rel
            ensure_dir(dst.parent)
            shutil.copy2(src, dst)


def extract_body_html(pandoc_html: str) -> str | None:
    m = re.search(r"<body[^>]*>(.*)</body>", pandoc_html, flags=re.S | re.I)
    if not m:
        return None
    body = m.group(1).strip()
    return body or None


def run_pandoc(tex_path: Path, out_dir: Path) -> tuple[str | None, str]:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return None, "pandoc_not_available"

    temp_html = out_dir / "cv" / "cv_from_pandoc.html"
    ensure_dir(temp_html.parent)

    cmd = [pandoc, str(tex_path), "-f", "latex", "-t", "html", "-o", str(temp_html)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not temp_html.exists():
        return None, "pandoc_failed"

    raw = temp_html.read_text(encoding="utf-8", errors="ignore")
    body = extract_body_html(raw)
    if not body:
        return None, "pandoc_unreadable"
    return body, "pandoc_ok"


def ensure_cv_pdf(tex_path: Path, repo_root: Path, out_pdf: Path) -> tuple[bool, str]:
    tex_pdf = tex_path.with_suffix(".pdf")
    repo_pdf = repo_root / "cv" / "Vargo_CV.pdf"

    latexmk = shutil.which("latexmk")
    if latexmk:
        cmd = [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
        subprocess.run(cmd, cwd=tex_path.parent, capture_output=True, text=True)

    if tex_pdf.exists():
        ensure_dir(repo_pdf.parent)
        if tex_pdf.resolve() != repo_pdf.resolve():
            shutil.copy2(tex_pdf, repo_pdf)
        ensure_dir(out_pdf.parent)
        shutil.copy2(tex_pdf, out_pdf)
        return True, "compiled_with_latexmk"

    if repo_pdf.exists():
        ensure_dir(out_pdf.parent)
        shutil.copy2(repo_pdf, out_pdf)
        return True, "copied_cached_pdf"

    return False, "pdf_missing"


def is_doi_url(url: str) -> bool:
    return bool(re.search(r"https?://(?:dx\.)?doi\.org/", url, flags=re.I))


def abs_url(site_url: str, path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{site_url.rstrip('/')}/{path_or_url.lstrip('/')}"


def is_external(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def shorten(text: str, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "..."


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_authors(citation_text: str) -> list[str]:
    head = clean_latex_text((citation_text or "").split("(", 1)[0])
    names = []
    for match in AUTHOR_RE.finditer(head):
        last = match.group(1).strip()
        initials = normalize_whitespace(match.group(2))
        full = normalize_whitespace(f"{initials} {last}")
        if full and full not in names:
            names.append(full)

    if names:
        return names

    chunks = re.split(r"\s*(?:,|&| and )\s*", head)
    fallback = [normalize_whitespace(c) for c in chunks if normalize_whitespace(c)]
    return fallback[:8]


def parse_publication_date(raw_text: str, citation_text: str, year: int | None) -> str | None:
    source = raw_text or citation_text or ""
    m = re.search(r"\((\d{4})\s*,\s*([A-Za-z]{3,9})\.?\s*(\d{1,2})?", source)
    if m:
        y = int(m.group(1))
        month_token = m.group(2).lower()
        month = MONTHS.get(month_token)
        day = int(m.group(3)) if m.group(3) else None
        if month and day:
            try:
                return dt.date(y, month, day).isoformat()
            except ValueError:
                return str(y)
        return str(y)

    if year:
        return str(year)

    y_match = re.search(r"\((\d{4})\)", source)
    if y_match:
        return y_match.group(1)
    return None


def infer_year_from_text(text: str) -> int | None:
    years = [int(x) for x in re.findall(r"\b(19\d{2}|20\d{2})\b", text or "")]
    if not years:
        return None
    valid = [y for y in years if 1900 <= y <= 2100]
    return valid[0] if valid else None


def normalize_date_like(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    if re.match(r"^\d{4}$", value):
        return value
    return fallback


def resolve_local_pdf_override(path_value: str | None, repo_root: Path) -> Path | None:
    if not path_value:
        return None
    raw = path_value.strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    rel_candidate = (repo_root / candidate).resolve()
    if rel_candidate.exists():
        return rel_candidate

    return None


def parse_chapter_preprints(override: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    raw_entries = override.get("chapter_preprints")
    if not isinstance(raw_entries, list):
        return []

    out: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_entries, start=1):
        if not isinstance(raw, dict):
            continue
        label = normalize_whitespace(str(raw.get("label") or f"chapter {idx}"))
        public_pdf_filename = str(raw.get("public_pdf_filename") or f"chapter-{idx:02d}.pdf").strip()
        if not public_pdf_filename.lower().endswith(".pdf"):
            public_pdf_filename = f"{public_pdf_filename}.pdf"

        local_source_pdf = resolve_local_pdf_override(str(raw.get("local_pdf_path") or ""), repo_root)
        external_pdf_url = str(raw.get("external_pdf_url") or "").strip() or None
        if not local_source_pdf and not external_pdf_url:
            continue

        out.append(
            {
                "label": label,
                "public_pdf_filename": public_pdf_filename,
                "local_source_pdf": str(local_source_pdf) if local_source_pdf else None,
                "external_pdf_url": external_pdf_url,
                "url": None,
                "absolute_url": None,
            }
        )

    return out


def format_venue_line(pub: dict[str, Any]) -> str | None:
    bits: list[str] = []
    if pub.get("venue_display"):
        bits.append(pub["venue_display"])

    volume_issue = ""
    if pub.get("volume") and pub.get("issue"):
        volume_issue = f"{pub['volume']}({pub['issue']})"
    elif pub.get("volume"):
        volume_issue = str(pub["volume"])

    pages = ""
    if pub.get("firstpage") and pub.get("lastpage"):
        pages = f"{pub['firstpage']}-{pub['lastpage']}"
    elif pub.get("firstpage"):
        pages = str(pub["firstpage"])

    if volume_issue and pages:
        bits.append(f"{volume_issue}:{pages}")
    elif volume_issue:
        bits.append(volume_issue)
    elif pages:
        bits.append(pages)

    if pub.get("publication_date"):
        bits.append(pub["publication_date"])
    elif pub.get("year"):
        bits.append(str(pub["year"]))

    out = ", ".join([x for x in bits if x])
    return out or None


def build_author_links(authors: list[str], primary_orcid: str | None) -> list[dict[str, str | None]]:
    links: list[dict[str, str | None]] = []
    orcid_url = f"https://orcid.org/{primary_orcid}" if primary_orcid else None
    for name in authors:
        if orcid_url and "vargo" in name.lower():
            links.append({"name": name, "orcid_url": orcid_url})
        else:
            links.append({"name": name, "orcid_url": None})
    return links


def citation_date_tag_value(publication_date: str | None, year: int | None) -> str | None:
    if publication_date and re.match(r"^\d{4}-\d{2}-\d{2}$", publication_date):
        return publication_date.replace("-", "/")
    if publication_date and re.match(r"^\d{4}$", publication_date):
        return publication_date
    if year:
        return str(year)
    return None


def first_non_doi_url(urls: list[str]) -> str | None:
    for url in urls:
        if not is_doi_url(url):
            return url
    return None


def split_venue_tail(citation_text: str, title: str) -> str:
    text = citation_text or ""
    text = re.sub(r"https?://\S+", "", text)
    if title and title in text:
        return text.split(title, 1)[1].strip(" .")
    m = re.search(r"\)\.?\s+(.*)", text)
    return (m.group(1) if m else "").strip(" .")


def parse_venue_details(citation_text: str, title: str, subsection: str) -> dict[str, Any]:
    tail = split_venue_tail(citation_text, title)
    details: dict[str, Any] = {
        "container_type": "other",
        "journal_title": None,
        "conference_title": None,
        "book_title": None,
        "volume": None,
        "issue": None,
        "firstpage": None,
        "lastpage": None,
        "issn": None,
        "isbn": None,
        "publisher": None,
        "venue_display": None,
    }

    issn_m = re.search(r"\b(\d{4}-\d{3}[\dXx])\b", citation_text or "")
    if issn_m:
        details["issn"] = issn_m.group(1).upper()

    isbn_m = re.search(r"\b(?:97[89][\- ]?)?\d[\d\- ]{8,}\d\b", citation_text or "")
    if isbn_m and ("book" in subsection.lower() or "chapter" in subsection.lower()):
        details["isbn"] = re.sub(r"\s+", "", isbn_m.group(0))

    if "conference" in subsection.lower() or "proceedings" in subsection.lower():
        details["container_type"] = "conference"
        conf = re.split(r"\.\s+", tail, maxsplit=1)[0].strip(" .")
        details["conference_title"] = conf or None
        details["venue_display"] = details["conference_title"]
        return details

    if "book" in subsection.lower() and "chapter" not in subsection.lower():
        details["container_type"] = "book"
        details["book_title"] = title
        details["venue_display"] = title
        publisher = re.split(r"\.\s+", tail, maxsplit=1)[0].strip(" .")
        details["publisher"] = publisher or None
        return details

    if "chapter" in subsection.lower():
        details["container_type"] = "chapter"
        m = re.search(r"In\s+(.+?)(?:\.|$)", tail)
        details["book_title"] = m.group(1).strip(" .") if m else None
        details["venue_display"] = details["book_title"]
        return details

    details["container_type"] = "journal"

    m_full = re.search(
        r"(?P<journal>[^,]+),\s*(?P<volume>\d+)\((?P<issue>[^)]+)\),\s*(?P<spage>\d+)\s*[\-–]\s*(?P<epage>\d+)",
        tail,
    )
    if m_full:
        details["journal_title"] = m_full.group("journal").strip(" .")
        details["volume"] = m_full.group("volume")
        details["issue"] = m_full.group("issue")
        details["firstpage"] = m_full.group("spage")
        details["lastpage"] = m_full.group("epage")
    else:
        m_part = re.search(
            r"(?P<journal>[^,]+),\s*(?P<volume>\d+)\((?P<issue>[^)]+)\)",
            tail,
        )
        if m_part:
            details["journal_title"] = m_part.group("journal").strip(" .")
            details["volume"] = m_part.group("volume")
            details["issue"] = m_part.group("issue")
        else:
            m_journal = re.search(r"(?P<journal>[^,]+)", tail)
            details["journal_title"] = m_journal.group("journal").strip(" .") if m_journal else None

        m_pages = re.search(r"\b(?P<spage>\d+)\s*[\-–]\s*(?P<epage>\d+)\b", tail)
        if m_pages:
            details["firstpage"] = m_pages.group("spage")
            details["lastpage"] = m_pages.group("epage")

    details["venue_display"] = details["journal_title"]
    return details


def local_preprint_source(preprint_url: str | None, static_dir: Path) -> Path | None:
    if not preprint_url:
        return None
    if not preprint_url.startswith("/assets/preprints/"):
        return None
    if not preprint_url.lower().endswith(".pdf"):
        return None

    filename = Path(preprint_url).name
    candidate = static_dir / "preprints" / filename
    return candidate if candidate.exists() else None


def read_pdf_text(path: Path, max_pages: int = 2) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            chunks.append(txt)
    return normalize_whitespace(" ".join(chunks))


def extract_abstract_and_keywords_from_text(text: str) -> tuple[str, list[str]]:
    if not text:
        return "", []

    abstract = ""
    keywords: list[str] = []

    abstract_match = re.search(
        r"\babstract\b\s*[:\-]?\s*(.{80,3500}?)(?:\bkeywords?\b\s*[:\-]|\bkey words\b\s*[:\-]|\bintroduction\b|\b1\s*[\.)])",
        text,
        flags=re.I | re.S,
    )
    if abstract_match:
        abstract = normalize_whitespace(abstract_match.group(1))
    else:
        abstract_match2 = re.search(r"\babstract\b\s*[:\-]?\s*(.{80,2500})", text, flags=re.I | re.S)
        if abstract_match2:
            abstract = normalize_whitespace(abstract_match2.group(1))
            abstract = re.split(r"\b(?:introduction|references)\b", abstract, maxsplit=1, flags=re.I)[0]
            abstract = abstract[:1400].strip()

    kw_match = re.search(r"\bkeywords?\b\s*[:\-]\s*(.{4,400})", text, flags=re.I | re.S)
    if kw_match:
        chunk = normalize_whitespace(kw_match.group(1))
        chunk = re.split(r"\b(?:introduction|abstract)\b", chunk, maxsplit=1, flags=re.I)[0]
        raw_parts = re.split(r"[,;|]", chunk)
        for part in raw_parts:
            token = normalize_whitespace(part)
            if token and len(token) <= 80 and token.lower() not in {"and", "or"}:
                keywords.append(token)
        keywords = keywords[:10]

    return abstract, keywords


def extract_abstract_and_keywords_from_pdf(path: Path) -> tuple[str, list[str]]:
    text = read_pdf_text(path, max_pages=2)
    return extract_abstract_and_keywords_from_text(text)


def load_publication_overrides(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return {}
    return {}


def get_publication_override(overrides: dict[str, Any], slug: str, doi: str | None) -> dict[str, Any]:
    by_slug = overrides.get("by_slug") if isinstance(overrides.get("by_slug"), dict) else {}
    by_doi = overrides.get("by_doi") if isinstance(overrides.get("by_doi"), dict) else {}

    if slug in by_slug and isinstance(by_slug[slug], dict):
        return dict(by_slug[slug])

    if doi and doi in by_doi and isinstance(by_doi[doi], dict):
        return dict(by_doi[doi])

    if slug in overrides and isinstance(overrides.get(slug), dict):
        return dict(overrides.get(slug))

    if doi and doi in overrides and isinstance(overrides.get(doi), dict):
        return dict(overrides.get(doi))

    return {}


def assign_detail_urls(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used: dict[str, int] = {}
    flat: list[dict[str, Any]] = []

    for group in groups:
        subsection = group.get("title", "Publications")
        for item in group.get("items", []):
            basis = item.get("title_guess") or item.get("text") or "publication"
            root = slugify(basis)[:88].strip("-") or "publication"
            seen = used.get(root, 0) + 1
            used[root] = seen
            slug = root if seen == 1 else f"{root}-{seen}"
            detail_url = f"/publications/{slug}/"
            item["slug"] = slug
            item["detail_url"] = detail_url
            flat.append({"subsection": subsection, "item": item})

    return flat


def entry_type_for_pub(pub: dict[str, Any]) -> str:
    ctype = pub.get("container_type")
    if ctype == "journal":
        return "article"
    if ctype == "conference":
        return "inproceedings"
    if ctype == "book":
        return "book"
    if ctype == "chapter":
        return "incollection"
    return "misc"


def ris_type_for_pub(pub: dict[str, Any]) -> str:
    ctype = pub.get("container_type")
    if ctype == "journal":
        return "JOUR"
    if ctype == "conference":
        return "CPAPER"
    if ctype == "book":
        return "BOOK"
    if ctype == "chapter":
        return "CHAP"
    return "GEN"


def csl_type_for_pub(pub: dict[str, Any]) -> str:
    ctype = pub.get("container_type")
    if ctype == "journal":
        return "article-journal"
    if ctype == "conference":
        return "paper-conference"
    if ctype == "book":
        return "book"
    if ctype == "chapter":
        return "chapter"
    return "article"


def split_name_for_csl(name: str) -> dict[str, str]:
    parts = normalize_whitespace(name).split(" ")
    if len(parts) <= 1:
        return {"family": parts[0] if parts else "", "given": ""}
    return {"family": parts[-1], "given": " ".join(parts[:-1])}


def bibtex_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
    )


def bibtex_entry(pub: dict[str, Any]) -> str:
    entry_type = entry_type_for_pub(pub)
    key = pub["slug"]

    fields: list[tuple[str, str]] = []
    fields.append(("title", pub["title"]))
    if pub.get("authors"):
        fields.append(("author", " and ".join(pub["authors"])))
    if pub.get("year"):
        fields.append(("year", str(pub["year"])))

    if pub.get("container_type") == "journal" and pub.get("journal_title"):
        fields.append(("journal", pub["journal_title"]))
    if pub.get("container_type") == "conference" and pub.get("conference_title"):
        fields.append(("booktitle", pub["conference_title"]))
    if pub.get("container_type") in {"book", "chapter"} and pub.get("book_title"):
        fields.append(("booktitle", pub["book_title"]))

    for key_name in ["volume", "issue", "firstpage", "lastpage", "doi", "issn", "isbn"]:
        value = pub.get(key_name)
        if value:
            mapped = {
                "issue": "number",
                "firstpage": "pages",
                "lastpage": "pages",
            }.get(key_name, key_name)
            if key_name == "firstpage" and pub.get("lastpage"):
                value = f"{pub['firstpage']}--{pub['lastpage']}"
            elif key_name == "lastpage" and pub.get("firstpage"):
                continue
            fields.append((mapped, str(value)))

    if pub.get("doi"):
        fields.append(("url", f"https://doi.org/{pub['doi']}"))
    elif pub.get("publisher_url"):
        fields.append(("url", pub["publisher_url"]))

    if pub.get("abstract"):
        fields.append(("abstract", pub["abstract"]))
    if pub.get("keywords"):
        fields.append(("keywords", ", ".join(pub["keywords"])))
    if pub.get("version_label"):
        fields.append(("note", pub["version_label"]))

    body = ",\n".join(f"  {k} = {{{bibtex_escape(v)}}}" for k, v in fields)
    return f"@{entry_type}{{{key},\n{body}\n}}\n"


def ris_entry(pub: dict[str, Any]) -> str:
    lines = [f"TY  - {ris_type_for_pub(pub)}"]
    for author in pub.get("authors", []):
        lines.append(f"AU  - {author}")
    lines.append(f"TI  - {pub['title']}")

    if pub.get("container_type") == "journal" and pub.get("journal_title"):
        lines.append(f"JO  - {pub['journal_title']}")
    if pub.get("container_type") == "conference" and pub.get("conference_title"):
        lines.append(f"T2  - {pub['conference_title']}")
    if pub.get("container_type") in {"book", "chapter"} and pub.get("book_title"):
        lines.append(f"T2  - {pub['book_title']}")

    if pub.get("year"):
        lines.append(f"PY  - {pub['year']}")
    if pub.get("publication_date") and len(pub["publication_date"]) == 10:
        lines.append(f"DA  - {pub['publication_date'].replace('-', '/')}" )
    if pub.get("volume"):
        lines.append(f"VL  - {pub['volume']}")
    if pub.get("issue"):
        lines.append(f"IS  - {pub['issue']}")
    if pub.get("firstpage"):
        lines.append(f"SP  - {pub['firstpage']}")
    if pub.get("lastpage"):
        lines.append(f"EP  - {pub['lastpage']}")
    if pub.get("doi"):
        lines.append(f"DO  - {pub['doi']}")

    lines.append(f"UR  - {pub['canonical_url']}")

    if pub.get("abstract"):
        lines.append(f"AB  - {pub['abstract']}")
    for kw in pub.get("keywords", []):
        lines.append(f"KW  - {kw}")
    if pub.get("version_label"):
        lines.append(f"N1  - {pub['version_label']}")

    lines.append("ER  -")
    return "\n".join(lines) + "\n"


def csl_json_record(pub: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": pub["slug"],
        "type": csl_type_for_pub(pub),
        "title": pub["title"],
        "author": [split_name_for_csl(a) for a in pub.get("authors", [])],
        "URL": pub["canonical_url"],
    }

    if pub.get("doi"):
        payload["DOI"] = pub["doi"]
    if pub.get("year"):
        payload["issued"] = {"date-parts": [[int(pub["year"])]]}
    if pub.get("publication_date") and len(pub["publication_date"]) == 10:
        y, m, d = pub["publication_date"].split("-")
        payload["issued"] = {"date-parts": [[int(y), int(m), int(d)]]}

    if pub.get("container_type") == "journal":
        if pub.get("journal_title"):
            payload["container-title"] = pub["journal_title"]
    elif pub.get("container_type") == "conference":
        if pub.get("conference_title"):
            payload["container-title"] = pub["conference_title"]
    elif pub.get("container_type") in {"book", "chapter"}:
        if pub.get("book_title"):
            payload["container-title"] = pub["book_title"]

    for key in ["volume", "issue", "firstpage", "lastpage", "issn", "isbn", "abstract"]:
        value = pub.get(key)
        if value:
            mapping = {
                "firstpage": "page-first",
                "lastpage": "page-last",
                "issn": "ISSN",
                "isbn": "ISBN",
            }
            payload[mapping.get(key, key)] = value

    if pub.get("firstpage") and pub.get("lastpage"):
        payload["page"] = f"{pub['firstpage']}-{pub['lastpage']}"

    if pub.get("keywords"):
        payload["keyword"] = ", ".join(pub["keywords"])

    return payload


def build_coins(pub: dict[str, Any]) -> str:
    params: list[tuple[str, str]] = []

    ctype = pub.get("container_type")
    if ctype == "journal":
        fmt = "info:ofi/fmt:kev:mtx:journal"
        genre = "article"
    elif ctype == "conference":
        fmt = "info:ofi/fmt:kev:mtx:journal"
        genre = "conference"
    elif ctype in {"book", "chapter"}:
        fmt = "info:ofi/fmt:kev:mtx:book"
        genre = "bookitem" if ctype == "chapter" else "book"
    else:
        fmt = "info:ofi/fmt:kev:mtx:journal"
        genre = "article"

    params.extend(
        [
            ("ctx_ver", "Z39.88-2004"),
            ("rft_val_fmt", fmt),
            ("rft.genre", genre),
            ("rft.atitle", pub["title"]),
            ("rft.date", str(pub.get("publication_date") or pub.get("year") or "")),
        ]
    )

    for author in pub.get("authors", []):
        params.append(("rft.au", author))

    if pub.get("journal_title"):
        params.append(("rft.jtitle", pub["journal_title"]))
    if pub.get("conference_title"):
        params.append(("rft.btitle", pub["conference_title"]))
    if pub.get("book_title"):
        params.append(("rft.btitle", pub["book_title"]))
    if pub.get("volume"):
        params.append(("rft.volume", str(pub["volume"])))
    if pub.get("issue"):
        params.append(("rft.issue", str(pub["issue"])))
    if pub.get("firstpage"):
        params.append(("rft.spage", str(pub["firstpage"])))
    if pub.get("lastpage"):
        params.append(("rft.epage", str(pub["lastpage"])))
    if pub.get("issn"):
        params.append(("rft.issn", pub["issn"]))
    if pub.get("isbn"):
        params.append(("rft.isbn", pub["isbn"]))

    if pub.get("doi"):
        params.append(("rft_id", f"info:doi/{pub['doi']}"))
        params.append(("rft_id", f"https://doi.org/{pub['doi']}"))

    return urlencode(params, doseq=True)


def build_journal_is_part_of(pub: dict[str, Any]) -> dict[str, Any]:
    periodical: dict[str, Any] = {"@type": "Periodical", "name": pub["journal_title"]}
    if pub.get("issn"):
        periodical["issn"] = pub["issn"]

    if pub.get("volume") and pub.get("issue"):
        return {
            "@type": "PublicationIssue",
            "issueNumber": str(pub["issue"]),
            "isPartOf": {
                "@type": "PublicationVolume",
                "volumeNumber": str(pub["volume"]),
                "isPartOf": periodical,
            },
        }
    if pub.get("volume"):
        return {
            "@type": "PublicationVolume",
            "volumeNumber": str(pub["volume"]),
            "isPartOf": periodical,
        }
    return periodical


def schema_org_payload(pub: dict[str, Any]) -> str:
    ctype = pub.get("container_type")
    if ctype == "book":
        schema_type = "Book"
    elif ctype == "chapter":
        schema_type = "Chapter"
    else:
        schema_type = "ScholarlyArticle"

    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": pub["title"],
        "headline": pub["title"],
        "url": pub["canonical_url"],
        "mainEntityOfPage": pub["canonical_url"],
        "description": pub.get("abstract") or pub.get("citation_text"),
    }

    if pub.get("authors"):
        payload["author"] = [{"@type": "Person", "name": name} for name in pub["authors"]]

    if pub.get("publication_date"):
        payload["datePublished"] = pub["publication_date"]
    elif pub.get("year"):
        payload["datePublished"] = str(pub["year"])

    if pub.get("doi"):
        doi_url = f"https://doi.org/{pub['doi']}"
        payload["identifier"] = {"@type": "PropertyValue", "propertyID": "doi", "value": pub["doi"]}
        payload["sameAs"] = [doi_url]

    if ctype == "journal" and pub.get("journal_title"):
        payload["isPartOf"] = build_journal_is_part_of(pub)
    elif ctype == "conference" and pub.get("conference_title"):
        payload["isPartOf"] = {"@type": "Event", "name": pub["conference_title"]}
    elif ctype in {"book", "chapter"} and pub.get("book_title"):
        payload["isPartOf"] = {"@type": "Book", "name": pub["book_title"]}

    if pub.get("local_pdf_url"):
        payload["encoding"] = {
            "@type": "MediaObject",
            "contentUrl": pub["local_pdf_absolute_url"],
            "fileFormat": "application/pdf",
        }

    if pub.get("license", {}).get("license_url"):
        payload["license"] = pub["license"]["license_url"]

    return json.dumps(payload, ensure_ascii=False)


def publication_meta_tags(pub: dict[str, Any]) -> list[dict[str, str]]:
    tags: list[dict[str, str]] = []

    def add(name: str, value: str | None) -> None:
        if value is None:
            return
        value = str(value).strip()
        if not value:
            return
        tags.append({"name": name, "content": value})

    add("citation_title", pub["title"])
    for author in pub.get("authors", []):
        add("citation_author", author)

    add("citation_publication_date", pub.get("citation_publication_date"))
    add("citation_online_date", pub.get("citation_online_date"))
    add("citation_abstract_html_url", pub.get("canonical_url"))
    add("citation_public_url", pub.get("canonical_url"))

    if pub.get("local_pdf_absolute_url"):
        add("citation_pdf_url", pub.get("local_pdf_absolute_url"))
    if pub.get("doi"):
        add("citation_doi", pub.get("doi"))

    ctype = pub.get("container_type")
    if ctype == "journal":
        add("citation_journal_title", pub.get("journal_title"))
        add("citation_volume", pub.get("volume"))
        add("citation_issue", pub.get("issue"))
        add("citation_firstpage", pub.get("firstpage"))
        add("citation_lastpage", pub.get("lastpage"))
        add("citation_issn", pub.get("issn"))
    elif ctype == "conference":
        add("citation_conference_title", pub.get("conference_title"))
    elif ctype in {"book", "chapter"}:
        add("citation_book_title", pub.get("book_title"))
        add("citation_isbn", pub.get("isbn"))

    add("citation_publisher", pub.get("publisher"))

    for kw in pub.get("keywords", []):
        add("citation_keywords", kw)

    add("DC.type", "Text")
    add("DC.title", pub["title"])
    for author in pub.get("authors", []):
        add("DC.creator", author)
    add("DC.issued", pub.get("publication_date") or (str(pub.get("year")) if pub.get("year") else None))
    add("DC.description", pub.get("abstract") or "")
    add("DC.identifier", pub.get("canonical_url"))
    if pub.get("doi"):
        add("DC.identifier", f"https://doi.org/{pub['doi']}")

    return tags


def record_head_links(pub: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "rel": "alternate",
            "type": "application/x-bibtex",
            "href": pub["citation_files"]["bib"],
            "title": "BibTeX citation",
        },
        {
            "rel": "alternate",
            "type": "application/x-research-info-systems",
            "href": pub["citation_files"]["ris"],
            "title": "RIS citation",
        },
        {
            "rel": "alternate",
            "type": "application/vnd.citationstyles.csl+json",
            "href": pub["citation_files"]["json"],
            "title": "CSL-JSON citation",
        },
    ]


def build_record_links(pub: dict[str, Any]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    if pub.get("publisher_url"):
        links.append({"label": "publisher", "url": pub["publisher_url"], "external": True})
    if pub.get("doi"):
        links.append({"label": "doi", "url": f"https://doi.org/{pub['doi']}", "external": True})
    if pub.get("chapter_preprints"):
        for chapter in pub["chapter_preprints"]:
            chapter_url = chapter.get("url")
            if not chapter_url:
                continue
            links.append(
                {
                    "label": chapter.get("label") or "chapter",
                    "url": chapter_url,
                    "external": is_external(chapter_url),
                }
            )
    elif pub.get("local_pdf_url"):
        links.append({"label": "pre-print", "url": pub["local_pdf_url"], "external": False})
    elif pub.get("external_pdf_url"):
        links.append({"label": "pre-print", "url": pub["external_pdf_url"], "external": True})
    return links


def compare_pub_sort_key(pub: dict[str, Any]) -> tuple[Any, ...]:
    date_str = pub.get("online_date") or pub.get("publication_date") or (str(pub.get("year")) if pub.get("year") else "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        y, m, d = date_str.split("-")
        return (int(y), int(m), int(d), pub["title"])
    if re.match(r"^\d{4}$", date_str):
        return (int(date_str), 1, 1, pub["title"])
    return (0, 1, 1, pub["title"])


def rfc3339_date(value: str, fallback: dt.datetime) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value or ""):
        return value + "T00:00:00Z"
    if re.match(r"^\d{4}$", value or ""):
        return value + "-01-01T00:00:00Z"
    return fallback.strftime("%Y-%m-%dT%H:%M:%SZ")


def file_lastmod(path: Path, fallback: dt.datetime) -> str:
    if path.exists():
        ts = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    else:
        ts = fallback
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def render_build_report_text(report: dict[str, Any]) -> str:
    lines = [
        f"total_publications: {report.get('total_publications', 0)}",
        f"matched_preprints: {report.get('matched_preprints', 0)}",
        f"unmatched_publications: {report.get('unmatched_publications', 0)}",
        f"unused_preprints_rows: {report.get('unused_preprints_rows', 0)}",
        f"missing_abstracts: {report.get('missing_abstracts', 0)}",
        "",
        "abstract_todos (up to 100):",
    ]

    todos = report.get("abstract_todos", []) or []
    if not todos:
        lines.append("- none")
    else:
        for todo in todos[:100]:
            lines.append(f"- {todo}")

    lines.append("")
    lines.append("questionable_matches (up to 20):")
    qm = report.get("questionable_matches", []) or []
    if not qm:
        lines.append("- none")
    else:
        for row in qm[:20]:
            lines.append(
                "- score={score} | row={row} | pub={pub}".format(
                    score=row.get("score"),
                    row=row.get("matched_row"),
                    pub=row.get("pub_title", "")[:180],
                )
            )

    return "\n".join(lines) + "\n"


def build_publication_records(
    cv_data: dict[str, Any],
    site_url: str,
    static_dir: Path,
    repo_root: Path,
    build_now: dt.datetime,
    overrides: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    groups: list[dict[str, Any]] = []
    for section in cv_data.get("sections", []):
        if section.get("title") != "Research":
            continue
        for subsection in section.get("subsections", []):
            subsection_title = subsection.get("title", "Untitled")
            normalized_subsection = normalize_whitespace(subsection_title).casefold()
            if normalized_subsection in HIDDEN_RESEARCH_SUBSECTIONS:
                continue
            items = [dict(x) for x in subsection.get("items", [])]
            if items:
                groups.append({"title": subsection_title, "items": items})

    flat = assign_detail_urls(groups)
    abstract_cache: dict[str, tuple[str, list[str]]] = {}
    abstract_todos: list[str] = []

    by_slug: dict[str, dict[str, Any]] = {}
    for record in flat:
        subsection = record["subsection"]
        item = record["item"]

        slug = item["slug"]
        detail_url = item["detail_url"]
        title = item.get("title_guess") or item.get("text") or "Publication"
        citation_text = item.get("text") or ""
        doi = normalize_doi(item.get("doi"))
        doi = normalize_doi(str(get_publication_override(overrides, slug, doi).get("doi") or doi)) or doi
        authors = parse_authors(citation_text)
        year = item.get("year") or infer_year_from_text(item.get("raw") or citation_text)
        publication_date = parse_publication_date(item.get("raw") or "", citation_text, year)

        override = get_publication_override(overrides, slug, doi)
        suppress_default_preprint = bool(override.get("suppress_default_preprint_link", False))
        override_year = override.get("year")
        if override_year:
            try:
                year = int(str(override_year).strip())
            except ValueError:
                pass
        publication_date = normalize_date_like(str(override.get("publication_date") or ""), publication_date or "")
        publication_date = publication_date or parse_publication_date(item.get("raw") or "", citation_text, year)
        if year is None and publication_date and re.match(r"^\d{4}", publication_date):
            try:
                year = int(publication_date[:4])
            except ValueError:
                year = None
        citation_pub_date = citation_date_tag_value(publication_date, year)

        online_date = normalize_date_like(str(override.get("online_date") or ""), build_now.strftime("%Y-%m-%d"))
        citation_online_date = citation_date_tag_value(online_date, None)

        venue = parse_venue_details(citation_text, title, subsection)
        publisher_url = str(override.get("publisher_url") or "").strip() or first_non_doi_url(item.get("urls") or [])

        preprint_url = item.get("preprint_url")
        pdf_override = override.get("pdf") if isinstance(override.get("pdf"), dict) else {}
        license_override = override.get("license") if isinstance(override.get("license"), dict) else {}
        resources_override = (
            override.get("open_resources") if isinstance(override.get("open_resources"), dict) else {}
        )

        override_local_pdf = resolve_local_pdf_override(str(pdf_override.get("local_pdf_path") or ""), repo_root)
        local_source_pdf = override_local_pdf or local_preprint_source(preprint_url, static_dir)
        external_pdf_url = (
            str(pdf_override.get("external_pdf_url") or "").strip()
            or (preprint_url if preprint_url and is_external(preprint_url) else None)
        )
        chapter_preprints = parse_chapter_preprints(override, repo_root)
        if suppress_default_preprint and chapter_preprints:
            local_source_pdf = None
            external_pdf_url = None

        public_pdf_filename = str(pdf_override.get("public_pdf_filename") or "preprint.pdf")
        local_pdf_url = f"{detail_url}{public_pdf_filename}" if local_source_pdf else None
        for chapter in chapter_preprints:
            if chapter.get("local_source_pdf"):
                chapter["url"] = f"{detail_url}{chapter['public_pdf_filename']}"
                chapter["absolute_url"] = abs_url(site_url, chapter["url"])
            elif chapter.get("external_pdf_url"):
                chapter["url"] = chapter["external_pdf_url"]
                chapter["absolute_url"] = chapter["external_pdf_url"]

        override_abstract = normalize_whitespace(str(override.get("abstract") or ""))
        override_keywords = override.get("keywords") if isinstance(override.get("keywords"), list) else []

        inferred_abstract = ""
        inferred_keywords: list[str] = []
        if not override_abstract and local_source_pdf:
            key = str(local_source_pdf)
            if key not in abstract_cache:
                abstract_cache[key] = extract_abstract_and_keywords_from_pdf(local_source_pdf)
            inferred_abstract, inferred_keywords = abstract_cache[key]

        abstract = override_abstract or inferred_abstract
        keywords = [normalize_whitespace(str(k)) for k in (override_keywords or inferred_keywords) if normalize_whitespace(str(k))]

        no_abstract_ok = bool(override.get("no_abstract_ok", False))
        if not abstract:
            if not no_abstract_ok:
                no_abstract_ok = True
                abstract_todos.append(f"{slug}: add abstract")

        version_label = str(override.get("version_label") or "").strip()
        if not version_label and (local_source_pdf or external_pdf_url):
            version_label = "Author preprint"

        license_name = str(license_override.get("license_name") or "").strip() or None
        license_url = str(license_override.get("license_url") or "").strip() or None

        publication = {
            "slug": slug,
            "subsection": subsection,
            "detail_url": detail_url,
            "canonical_url": abs_url(site_url, detail_url),
            "title": title,
            "citation_text": citation_text,
            "authors": authors,
            "year": year,
            "publication_date": publication_date,
            "citation_publication_date": citation_pub_date,
            "online_date": online_date,
            "citation_online_date": citation_online_date,
            "doi": doi,
            "publisher_url": publisher_url,
            "abstract": abstract,
            "abstract_display": abstract or "Abstract not currently available on this page.",
            "no_abstract_ok": no_abstract_ok,
            "keywords": keywords,
            "version_label": version_label or None,
            "license": {
                "license_name": license_name,
                "license_url": license_url,
            },
            "open_resources": {
                "code_url": str(resources_override.get("code_url") or "").strip() or None,
                "data_url": str(resources_override.get("data_url") or "").strip() or None,
                "materials_url": str(resources_override.get("materials_url") or "").strip() or None,
            },
            "pdf": {
                "local_pdf_path": str(local_source_pdf) if local_source_pdf else None,
                "public_pdf_filename": public_pdf_filename,
                "external_pdf_url": external_pdf_url,
            },
            "local_pdf_url": local_pdf_url,
            "local_pdf_absolute_url": abs_url(site_url, local_pdf_url) if local_pdf_url else None,
            "external_pdf_url": external_pdf_url,
            "suppress_default_preprint_link": suppress_default_preprint,
            "chapter_preprints": chapter_preprints,
            "container_type": venue["container_type"],
            "journal_title": venue.get("journal_title"),
            "conference_title": venue.get("conference_title"),
            "book_title": venue.get("book_title"),
            "volume": venue.get("volume"),
            "issue": venue.get("issue"),
            "firstpage": venue.get("firstpage"),
            "lastpage": venue.get("lastpage"),
            "issn": venue.get("issn"),
            "isbn": venue.get("isbn"),
            "publisher": venue.get("publisher"),
            "venue_display": venue.get("venue_display"),
            "venue_line": None,
            "author_links": [],
            "coins": "",
            "meta_tags": [],
            "jsonld": "",
            "head_links": [],
            "list_links": [],
            "citation_files": {
                "bib": f"{detail_url}citation.bib",
                "ris": f"{detail_url}citation.ris",
                "json": f"{detail_url}citation.json",
            },
        }

        publication["meta_tags"] = publication_meta_tags(publication)
        publication["jsonld"] = schema_org_payload(publication)
        publication["coins"] = build_coins(publication)
        publication["head_links"] = record_head_links(publication)
        publication["list_links"] = build_record_links(publication)
        publication["venue_line"] = format_venue_line(publication)

        by_slug[slug] = publication

    publication_groups: list[dict[str, Any]] = []
    for group in groups:
        group_items: list[dict[str, Any]] = []
        for item in group["items"]:
            pub = by_slug.get(item["slug"])
            if not pub:
                continue
            group_items.append(
                {
                    "slug": pub["slug"],
                    "detail_url": pub["detail_url"],
                    "citation_text": pub["citation_text"],
                    "list_links": pub["list_links"],
                }
            )
        if group_items:
            publication_groups.append({"title": group["title"], "items": group_items})

    publications = list(by_slug.values())
    return publications, publication_groups, abstract_todos


def flatten_section_entries(section: dict[str, Any]) -> dict[str, Any]:
    direct_entries = section.get("entries", []) or []
    direct_items = [x.get("text") for x in (section.get("items", []) or []) if x.get("text")]

    subsections = []
    for sub in section.get("subsections", []) or []:
        sub_entries = list(sub.get("entries", []) or [])
        sub_entries.extend([x.get("text") for x in (sub.get("items", []) or []) if x.get("text")])
        if sub_entries:
            subsections.append({"title": sub.get("title"), "entries": sub_entries})

    return {
        "title": section.get("title"),
        "entries": direct_entries + direct_items,
        "subsections": subsections,
    }


def build_feed_xml(site_url: str, publications: list[dict[str, Any]], build_now: dt.datetime) -> str:
    updated = build_now.strftime("%Y-%m-%dT%H:%M:%SZ")
    sorted_pubs = sorted(publications, key=compare_pub_sort_key, reverse=True)

    entries: list[str] = []
    for pub in sorted_pubs[:50]:
        pub_updated = rfc3339_date(pub.get("online_date") or pub.get("publication_date") or "", build_now)
        summary = html.escape(shorten(pub.get("abstract") or pub.get("citation_text") or "", 500))
        title = html.escape(pub["title"])
        link = html.escape(pub["canonical_url"])
        entries.append(
            "<entry>"
            f"<id>{link}</id>"
            f"<title>{title}</title>"
            f"<link href=\"{link}\" />"
            f"<updated>{pub_updated}</updated>"
            f"<summary>{summary}</summary>"
            "</entry>"
        )

    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<feed xmlns=\"http://www.w3.org/2005/Atom\">"
        f"<id>{html.escape(site_url.rstrip('/'))}/feed.xml</id>"
        "<title>Chris J. Vargo Publications</title>"
        f"<updated>{updated}</updated>"
        f"<link href=\"{html.escape(site_url.rstrip('/'))}/feed.xml\" rel=\"self\" />"
        + "".join(entries)
        + "</feed>\n"
    )


def build_llms_txt(site_url: str, optional_nav: list[dict[str, str]]) -> str:
    lines = [
        "# Chris J. Vargo",
        "",
        "> Academic profile with publication records, preprints, and machine-readable citation exports.",
        "",
        "## Publications",
        f"- [Publication Index]({site_url.rstrip('/')}/publications/)",
        f"- [Publications CSL-JSON]({site_url.rstrip('/')}/publications.json)",
        f"- [Publications BibTeX]({site_url.rstrip('/')}/publications.bib)",
        f"- [Publications RIS]({site_url.rstrip('/')}/publications.ris)",
        "",
    ]

    if optional_nav:
        lines.append("## Optional")
        for item in optional_nav:
            lines.append(f"- [{item['title']}]({site_url.rstrip('/')}{item['url']})")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_site(
    input_tex: Path,
    preprints_csv: Path,
    out_dir: Path,
    site_url: str,
    domain: str | None,
    skip_validate: bool = False,
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = SCRIPT_DIR / "templates"
    static_dir = SCRIPT_DIR / "static"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "assets")

    build_now = dt.datetime.now(dt.timezone.utc)
    build_timestamp = build_now.strftime("%Y-%m-%d %H:%M UTC")

    cv_data = parse_cv(input_tex)
    ensure_dir(SCRIPT_DIR / "cache")
    write_text(SCRIPT_DIR / "cache" / "cv.json", json.dumps(cv_data, indent=2, ensure_ascii=False))

    cv_data, preprint_report = attach_preprints(cv_data, preprints_csv, threshold=0.86)

    overrides_path = repo_root / "publication_overrides.json"
    overrides = load_publication_overrides(overrides_path)

    meta = cv_data.get("meta", {})
    meta.setdefault("name", "Chris J. Vargo")
    meta.setdefault("current_as_of", "")
    meta.setdefault("scholar_url", "https://scholar.google.com/citations?user=LTnXrjYAAAAJ")

    publications, publication_groups, abstract_todos = build_publication_records(
        cv_data=cv_data,
        site_url=site_url,
        static_dir=static_dir,
        repo_root=repo_root,
        build_now=build_now,
        overrides=overrides,
    )

    optional_titles = {"Teaching", "Service", "Awards"}
    optional_sections = []
    for section in cv_data.get("sections", []):
        title = section.get("title")
        if title in optional_titles:
            payload = flatten_section_entries(section)
            if payload["entries"] or payload["subsections"]:
                optional_sections.append(payload)

    base_nav = [
        {"title": "Home", "url": "/"},
        {"title": "Publications", "url": "/publications/"},
        {"title": "CV", "url": "/cv/"},
    ]

    optional_nav = []
    for sec in optional_sections:
        slug = slugify(sec["title"])
        sec["slug"] = slug
        optional_nav.append({"title": sec["title"], "url": f"/{slug}/"})

    nav = base_nav + optional_nav + [
        {"title": "GitHub", "url": "https://github.com/chrisjvargo", "external": True},
        {"title": "LinkedIn", "url": "https://www.linkedin.com/in/chrisjvargo/", "external": True},
    ]

    cv_html, cv_html_status = run_pandoc(input_tex, out_dir)
    cv_pdf_ok, cv_pdf_status = ensure_cv_pdf(input_tex, repo_root, out_dir / "assets" / "cv.pdf")

    for pub in publications:
        pub["author_links"] = build_author_links(pub.get("authors", []), meta.get("orcid"))

    bio_text = (
        "Chris J. Vargo is an associate professor whose research focuses on computational "
        "content analysis, social media dynamics, advertising, and agenda-setting theory."
    )

    research_interests = [
        "Computational content analysis and machine learning for media research",
        "Agenda-setting, agendamelding, and intermedia influence",
        "Political communication and online platform behavior",
        "Advertising analytics and digital trace data methods",
    ]

    common_ctx = {
        "meta": meta,
        "nav": nav,
        "build_timestamp": build_timestamp,
        "site_url": site_url.rstrip("/"),
    }

    # Home
    home_html = env.get_template("index.html").render(
        **common_ctx,
        canonical_url=abs_url(site_url, "/"),
        page_description="Academic profile, publications, and CV for Chris J. Vargo.",
        bio_text=bio_text,
        research_interests=research_interests,
        quick_links=nav,
        social_title=f"{meta.get('name', 'Chris J. Vargo')} - Home",
        social_description=shorten(bio_text, 200),
        social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
        social_url=abs_url(site_url, "/"),
        og_type="website",
    )
    write_text(out_dir / "index.html", home_html)

    # Publications index
    pubs_html = env.get_template("publications.html").render(
        **common_ctx,
        canonical_url=abs_url(site_url, "/publications/"),
        page_description="Publication list with DOI, publisher, and pre-print links.",
        publication_groups=publication_groups,
        social_title=f"{meta.get('name', 'Chris J. Vargo')} - Publications",
        social_description="Publication records with citation exports and preprint links.",
        social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
        social_url=abs_url(site_url, "/publications/"),
        og_type="website",
    )
    write_text(out_dir / "publications" / "index.html", pubs_html)

    # Per-record pages and per-record citation files.
    publication_template = env.get_template("publication.html")
    publication_detail_paths: list[str] = []

    csl_records: list[dict[str, Any]] = []
    bib_entries: list[str] = []
    ris_entries: list[str] = []

    manifest_records: list[dict[str, Any]] = []

    for pub in publications:
        pub_dir = out_dir / pub["detail_url"].strip("/")
        ensure_dir(pub_dir)

        if pub.get("pdf", {}).get("local_pdf_path"):
            src_pdf = Path(pub["pdf"]["local_pdf_path"])
            if src_pdf.exists() and pub.get("local_pdf_url"):
                dst_pdf = pub_dir / pub["pdf"].get("public_pdf_filename", "preprint.pdf")
                ensure_dir(dst_pdf.parent)
                shutil.copy2(src_pdf, dst_pdf)

        for chapter in pub.get("chapter_preprints", []):
            src_chapter_pdf = chapter.get("local_source_pdf")
            if isinstance(src_chapter_pdf, str) and src_chapter_pdf:
                src_path = Path(src_chapter_pdf)
            else:
                src_path = None
            if src_path and src_path.exists():
                dst_chapter_pdf = pub_dir / str(chapter.get("public_pdf_filename") or "chapter.pdf")
                ensure_dir(dst_chapter_pdf.parent)
                shutil.copy2(src_path, dst_chapter_pdf)

        bib_text = bibtex_entry(pub)
        ris_text = ris_entry(pub)
        csl_obj = csl_json_record(pub)

        write_text(pub_dir / "citation.bib", bib_text)
        write_text(pub_dir / "citation.ris", ris_text)
        write_text(pub_dir / "citation.json", json.dumps(csl_obj, indent=2, ensure_ascii=False) + "\n")

        csl_records.append(csl_obj)
        bib_entries.append(bib_text)
        ris_entries.append(ris_text)

        rights_note = None
        if pub.get("version_label") and pub.get("doi"):
            rights_note = (
                f"This is the {pub['version_label'].lower()}. "
                "For the final published version, see the DOI above."
            )
        elif pub.get("version_label"):
            rights_note = f"This is the {pub['version_label'].lower()}."

        rendered = publication_template.render(
            **common_ctx,
            canonical_url=pub["canonical_url"],
            page_title=pub["title"],
            page_description=shorten(pub.get("abstract") or pub.get("citation_text") or "", 220),
            publication=pub,
            rights_note=rights_note,
            head_meta_tags=pub.get("meta_tags", []),
            head_links=pub.get("head_links", []),
            social_title=pub["title"],
            social_description=shorten(pub.get("abstract") or pub.get("citation_text") or "", 200),
            social_url=pub["canonical_url"],
            social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
            og_type="article",
        )
        write_text(pub_dir / "index.html", rendered)
        publication_detail_paths.append(pub["detail_url"])

        manifest_records.append(
            {
                "slug": pub["slug"],
                "detail_url": pub["detail_url"],
                "record_path": f"{pub['detail_url']}index.html",
                "canonical_url": pub["canonical_url"],
                "title": pub["title"],
                "authors": pub.get("authors", []),
                "publication_date": pub.get("publication_date"),
                "abstract": pub.get("abstract", ""),
                "no_abstract_ok": bool(pub.get("no_abstract_ok")),
                "has_local_pdf": bool(pub.get("local_pdf_url")),
                "expected_citation_pdf_url": pub.get("local_pdf_absolute_url"),
                "expected_pdf_relative": (
                    f"{pub['detail_url']}{pub['pdf'].get('public_pdf_filename', 'preprint.pdf')}"
                    if pub.get("local_pdf_url")
                    else None
                ),
                "citation_files": pub.get("citation_files", {}),
            }
        )

    # Site-wide citation exports.
    write_text(out_dir / "publications.bib", "\n".join(bib_entries))
    write_text(out_dir / "publications.ris", "\n".join(ris_entries))
    write_text(out_dir / "publications.json", json.dumps(csl_records, indent=2, ensure_ascii=False) + "\n")
    write_text(
        out_dir / "publications_model.json",
        json.dumps({"generated_at": build_timestamp, "records": publications}, indent=2, ensure_ascii=False),
    )

    # CV page
    cv_html_page = env.get_template("cv.html").render(
        **common_ctx,
        canonical_url=abs_url(site_url, "/cv/"),
        page_description="Curriculum Vitae of Chris J. Vargo.",
        cv_html=cv_html,
        cv_html_status=cv_html_status,
        cv_pdf_ok=cv_pdf_ok,
        social_title=f"{meta.get('name', 'Chris J. Vargo')} - CV",
        social_description="Curriculum Vitae and downloadable PDF.",
        social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
        social_url=abs_url(site_url, "/cv/"),
        og_type="website",
    )
    write_text(out_dir / "cv" / "index.html", cv_html_page)

    # Optional pages
    section_template = env.get_template("section.html")
    for sec in optional_sections:
        rendered = section_template.render(
            **common_ctx,
            canonical_url=abs_url(site_url, f"/{sec['slug']}/"),
            page_description=f"{sec['title']} information for {meta.get('name', 'Chris J. Vargo')}.",
            section=sec,
            social_title=f"{meta.get('name', 'Chris J. Vargo')} - {sec['title']}",
            social_description=shorten(f"{sec['title']} information for {meta.get('name', 'Chris J. Vargo')}.", 200),
            social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
            social_url=abs_url(site_url, f"/{sec['slug']}/"),
            og_type="website",
        )
        write_text(out_dir / sec["slug"] / "index.html", rendered)

    # Build reports
    report = {
        **preprint_report,
        "cv_html_status": cv_html_status,
        "cv_pdf_status": cv_pdf_status,
        "publication_groups": [g.get("title") for g in publication_groups],
        "preprints_page_count": len([p for p in publications if p.get("local_pdf_url") or p.get("external_pdf_url")]),
        "publication_detail_pages": len(publication_detail_paths),
        "missing_abstracts": len([p for p in publications if not p.get("abstract")]),
        "abstract_todos": abstract_todos,
        "build_timestamp": build_timestamp,
    }
    write_text(out_dir / "build_report.json", json.dumps(report, indent=2, ensure_ascii=False))
    write_text(out_dir / "build_report.txt", render_build_report_text(report))

    # Manifest for validation
    write_text(out_dir / "publications_manifest.json", json.dumps({"records": manifest_records}, indent=2, ensure_ascii=False))

    # Static assets
    copy_static(static_dir, out_dir / "assets")

    # Site-level control files
    write_text(
        out_dir / "robots.txt",
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {site_url.rstrip('/')}/sitemap.xml\n",
    )

    write_text(
        out_dir / "404.html",
        env.get_template("base.html").render(
            **common_ctx,
            page_title="Page Not Found",
            page_description="Page not found.",
            canonical_url=abs_url(site_url, "/404.html"),
            content_html="<h2>404</h2><p>The page you requested does not exist.</p><p><a href='/'>&larr; Back to home</a></p>",
            social_title="Page Not Found",
            social_description="Page not found.",
            social_image=abs_url(site_url, DEFAULT_OG_IMAGE),
            social_url=abs_url(site_url, "/404.html"),
            og_type="website",
        ),
    )

    # CNAME
    cname_path = out_dir / "CNAME"
    if domain:
        write_text(cname_path, f"{domain.strip()}\n")
    elif cname_path.exists():
        cname_path.unlink()

    # Feed and llms.txt
    write_text(out_dir / "feed.xml", build_feed_xml(site_url, publications, build_now))
    write_text(out_dir / "llms.txt", build_llms_txt(site_url, optional_nav))

    # Sitemap with lastmod and PDF/citation resources.
    entries: list[tuple[str, Path]] = []

    core_pages = [
        ("/", out_dir / "index.html"),
        ("/publications/", out_dir / "publications" / "index.html"),
        ("/cv/", out_dir / "cv" / "index.html"),
        ("/feed.xml", out_dir / "feed.xml"),
        ("/llms.txt", out_dir / "llms.txt"),
        ("/publications.bib", out_dir / "publications.bib"),
        ("/publications.ris", out_dir / "publications.ris"),
        ("/publications.json", out_dir / "publications.json"),
        ("/publications_model.json", out_dir / "publications_model.json"),
    ]
    entries.extend(core_pages)

    for x in optional_nav:
        entries.append((x["url"], out_dir / x["url"].strip("/") / "index.html"))

    for pub in publications:
        detail_dir = out_dir / pub["detail_url"].strip("/")
        entries.append((pub["detail_url"], detail_dir / "index.html"))
        entries.append((pub["citation_files"]["bib"], detail_dir / "citation.bib"))
        entries.append((pub["citation_files"]["ris"], detail_dir / "citation.ris"))
        entries.append((pub["citation_files"]["json"], detail_dir / "citation.json"))
        if pub.get("local_pdf_url"):
            entries.append((pub["local_pdf_url"], detail_dir / pub["pdf"].get("public_pdf_filename", "preprint.pdf")))

    urls_xml = "\n".join(
        "  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>".format(
            loc=html.escape(abs_url(site_url, rel_url)),
            lastmod=html.escape(file_lastmod(path, build_now)),
        )
        for rel_url, path in entries
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls_xml}\n"
        "</urlset>\n"
    )
    write_text(out_dir / "sitemap.xml", sitemap)

    if not skip_validate:
        validate_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "validate_build.py"),
            "--dist",
            str(out_dir),
            "--site-url",
            site_url,
        ]
        subprocess.run(validate_cmd, check=True)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--preprints", required=True, type=Path)
    parser.add_argument("--out", default=Path("dist"), type=Path)
    parser.add_argument("--site-url", default="https://chrisjvargo.com")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    report = build_site(
        args.input,
        args.preprints,
        args.out,
        args.site_url,
        args.domain,
        skip_validate=args.skip_validate,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
