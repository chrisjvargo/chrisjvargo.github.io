#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SECTION_RE = re.compile(r"^\\section\{(.+?)\}\s*$")
SUBSECTION_RE = re.compile(r"^\\subsection\*\{(.+?)\}\s*$")
MAILTO_RE = re.compile(r"\\href\{mailto:([^}]+)\}\{([^}]+)\}")
ORCID_RE = re.compile(r"ORCID:\s*([0-9X-]{15,})", re.IGNORECASE)
CURRENT_AS_OF_RE = re.compile(r"Current as of\s+([^}]+)", re.IGNORECASE)
URL_CMD_RE = re.compile(r"\\url\{([^}]+)\}")
HREF_CMD_RE = re.compile(r"\\href\{([^}]+)\}\{([^}]+)\}")
PLAIN_URL_RE = re.compile(r"https?://[^\s\]}]+")
DOI_RE = re.compile(
    r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\((?:[^)]*?)(\d{4})(?:[^)]*?)\)")

LATEX_REPLACEMENTS = {
    r"\&": "&",
    r"\%": "%",
    r"\_": "_",
    r"\#": "#",
    r"\$": "$",
    r"\textbullet": "•",
    r"\,": " ",
}


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


def strip_latex_math(text: str) -> str:
    # Remove lightweight inline math that occasionally appears in CV formatting.
    return re.sub(r"\$[^$]*\$", "", text)


def clean_latex_text(text: str) -> str:
    text = strip_latex_math(text)

    # Preserve useful content before stripping commands.
    text = HREF_CMD_RE.sub(lambda m: m.group(2), text)
    text = URL_CMD_RE.sub(lambda m: m.group(1), text)

    for src, dst in LATEX_REPLACEMENTS.items():
        text = text.replace(src, dst)

    text = text.replace("``", '"').replace("''", '"')
    text = text.replace("---", "—").replace("--", "–")
    text = text.replace(r"\\", " ")

    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", text)

    text = re.sub(r"\\[a-zA-Z@]+\*?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_urls(raw_item: str) -> list[str]:
    urls: list[str] = []
    urls.extend(URL_CMD_RE.findall(raw_item))
    urls.extend([m.group(1) for m in HREF_CMD_RE.finditer(raw_item)])
    urls.extend(PLAIN_URL_RE.findall(raw_item))

    out: list[str] = []
    for u in urls:
        cleaned = u.strip().rstrip(".,;)")
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def guess_title(citation_text: str) -> str | None:
    m = re.search(r"\)\.?\s+(.*)", citation_text)
    if not m:
        return None
    tail = m.group(1).strip()
    if not tail:
        return None

    parts = re.split(r"\.\s+(?=[A-Z\[])", tail)
    if not parts:
        return None
    title = parts[0].strip(" .")
    return title or None


def extract_year(raw_item: str) -> int | None:
    m = YEAR_RE.search(raw_item)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def parse_braced_args(text: str, macro: str, n_args: int) -> list[str] | None:
    needle = f"\\{macro}"
    pos = text.find(needle)
    if pos < 0:
        return None
    i = pos + len(needle)
    args: list[str] = []

    while len(args) < n_args and i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        depth = 0
        start = i + 1
        i += 1
        while i < len(text):
            ch = text[i]
            if ch == "{" and (i == 0 or text[i - 1] != "\\"):
                depth += 1
            elif ch == "}" and (i == 0 or text[i - 1] != "\\"):
                if depth == 0:
                    args.append(text[start:i])
                    i += 1
                    break
                depth -= 1
            i += 1
        else:
            return None
    return args if len(args) == n_args else None


def parse_list_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    in_list = False
    current: list[str] = []

    def flush_current() -> None:
        nonlocal current
        if current:
            joined = " ".join(current).strip()
            if joined:
                items.append(joined)
        current = []

    for line in lines:
        stripped = line.strip()
        if re.search(r"\\begin\{(?:enumerate|itemize)\}", stripped):
            in_list = True
            flush_current()
            continue
        if re.search(r"\\end\{(?:enumerate|itemize)\}", stripped):
            flush_current()
            in_list = False
            continue
        if not in_list:
            continue

        if stripped.startswith(r"\item"):
            flush_current()
            current.append(stripped[len(r"\item") :].strip())
        else:
            if current:
                current.append(stripped)

    flush_current()
    return items


def parse_command_entries(lines: list[str]) -> list[str]:
    entries: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(r"\cventry"):
            args = parse_braced_args(stripped, "cventry", 3)
            if args:
                title, date, place = [clean_latex_text(x) for x in args]
                entries.append("; ".join(x for x in [title, date, place] if x))
        elif stripped.startswith(r"\cvcourse"):
            args = parse_braced_args(stripped, "cvcourse", 3)
            if args:
                title, term, note = [clean_latex_text(x) for x in args]
                entries.append("; ".join(x for x in [title, term, note] if x))
    return entries


def build_item(raw_item: str) -> dict[str, Any]:
    urls = extract_urls(raw_item)
    doi = None
    for u in urls:
        doi = normalize_doi(u)
        if doi:
            break
    if not doi:
        doi = normalize_doi(raw_item)

    text = clean_latex_text(raw_item)
    return {
        "raw": raw_item.strip(),
        "text": text,
        "urls": urls,
        "doi": doi,
        "year": extract_year(raw_item),
        "title_guess": guess_title(text),
    }


def parse_center_meta(tex: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "name": None,
        "email": None,
        "email_display": None,
        "orcid": None,
        "current_as_of": None,
        "address_lines": [],
    }

    m = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", tex, flags=re.S)
    if not m:
        return meta

    block = m.group(1)

    name_m = re.search(r"\\textbf\{([^}]+)\}", block)
    if name_m:
        meta["name"] = clean_latex_text(name_m.group(1))

    email_m = MAILTO_RE.search(block)
    if email_m:
        meta["email"] = email_m.group(1).strip()
        meta["email_display"] = email_m.group(2).strip()

    orcid_m = ORCID_RE.search(block)
    if orcid_m:
        meta["orcid"] = orcid_m.group(1).strip()

    asof_m = CURRENT_AS_OF_RE.search(block)
    if asof_m:
        meta["current_as_of"] = clean_latex_text(asof_m.group(1))

    raw_lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    address_lines: list[str] = []
    for ln in raw_lines:
        if "textbf" in ln or "mailto:" in ln or "Current as of" in ln:
            continue
        cleaned = clean_latex_text(ln)
        if cleaned:
            address_lines.append(cleaned)

    meta["address_lines"] = address_lines
    return meta


def parse_subsections(section_lines: list[str]) -> list[dict[str, Any]]:
    subsections: list[dict[str, Any]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush_subsection() -> None:
        nonlocal current_title, current_lines
        if current_title is None:
            return
        items = [build_item(x) for x in parse_list_items(current_lines)]
        entries = parse_command_entries(current_lines)
        subsections.append(
            {
                "title": current_title,
                "items": items,
                "entries": entries,
            }
        )
        current_title = None
        current_lines = []

    for line in section_lines:
        m = SUBSECTION_RE.match(line.strip())
        if m:
            flush_subsection()
            current_title = clean_latex_text(m.group(1))
            continue
        if current_title is not None:
            current_lines.append(line)

    flush_subsection()
    return subsections


def parse_sections(tex: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_title, current_lines
        if current_title is None:
            return

        section_entries = parse_command_entries(current_lines)
        section_items = [build_item(x) for x in parse_list_items(current_lines)]
        subsections = parse_subsections(current_lines)

        section_obj: dict[str, Any] = {
            "title": current_title,
            "entries": section_entries,
            "items": section_items,
            "subsections": subsections,
        }
        sections.append(section_obj)

        current_title = None
        current_lines = []

    for line in tex.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            flush_section()
            current_title = clean_latex_text(m.group(1))
            continue
        if current_title is not None:
            current_lines.append(line)

    flush_section()
    return sections


def parse_cv(tex_path: Path) -> dict[str, Any]:
    text = tex_path.read_text(encoding="utf-8")
    return {
        "meta": parse_center_meta(text),
        "sections": parse_sections(text),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    data = parse_cv(args.input)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
