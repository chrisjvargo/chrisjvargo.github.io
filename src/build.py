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

from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from merge_preprints import attach_preprints  # noqa: E402
from parse_cv import clean_latex_text, parse_cv  # noqa: E402


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
    for src in static_dir.glob("*"):
        if src.is_file():
            shutil.copy2(src, out_assets / src.name)


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


def publication_links(item: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    urls = item.get("urls", []) or []

    publisher = None
    pdf_link = None
    for url in urls:
        if is_doi_url(url):
            continue
        if url.lower().endswith(".pdf") and not pdf_link:
            pdf_link = url
            continue
        if not publisher:
            publisher = url

    doi = item.get("doi")
    if publisher:
        links.append({"label": "publisher", "url": publisher})
    if doi:
        links.append({"label": "doi", "url": f"https://doi.org/{doi}"})
    if item.get("preprint_url"):
        links.append({"label": "preprint", "url": item["preprint_url"]})
    if pdf_link:
        links.append({"label": "pdf", "url": pdf_link})

    return links


def collect_publication_groups(cv_data: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for section in cv_data.get("sections", []):
        if section.get("title") != "Research":
            continue
        for subsection in section.get("subsections", []):
            items = []
            for item in subsection.get("items", []):
                item_copy = dict(item)
                item_copy["links"] = publication_links(item_copy)
                items.append(item_copy)
            if items:
                groups.append({"title": subsection.get("title", "Untitled"), "items": items})
    return groups


def collect_preprint_items(pub_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preprints: list[dict[str, Any]] = []
    for group in pub_groups:
        for item in group.get("items", []):
            if item.get("preprint_url"):
                preprints.append({"group": group.get("title"), **item})
    return preprints


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


def render_build_report_text(report: dict[str, Any]) -> str:
    lines = [
        f"total_publications: {report.get('total_publications', 0)}",
        f"matched_preprints: {report.get('matched_preprints', 0)}",
        f"unmatched_publications: {report.get('unmatched_publications', 0)}",
        f"unused_preprints_rows: {report.get('unused_preprints_rows', 0)}",
        "",
        "questionable_matches (up to 20):",
    ]

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

    lines.append("")
    lines.append("unmatched_publication_samples (up to 50):")
    ups = report.get("unmatched_publication_samples", []) or []
    if not ups:
        lines.append("- none")
    else:
        for row in ups[:50]:
            lines.append(
                "- [{sub}] {title}".format(
                    sub=row.get("subsection", "?"),
                    title=(row.get("title_guess") or row.get("text") or "")[:180],
                )
            )

    lines.append("")
    lines.append("unused_preprints_samples (up to 50):")
    ups2 = report.get("unused_preprints_samples", []) or []
    if not ups2:
        lines.append("- none")
    else:
        for row in ups2[:50]:
            lines.append(
                "- row={row} doi={doi} title={title}".format(
                    row=row.get("row"),
                    doi=row.get("doi") or "",
                    title=(row.get("title") or "")[:180],
                )
            )

    return "\n".join(lines) + "\n"


def build_site(input_tex: Path, preprints_csv: Path, out_dir: Path, site_url: str, domain: str) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = SCRIPT_DIR / "templates"
    static_dir = SCRIPT_DIR / "static"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    ensure_dir(out_dir)
    ensure_dir(out_dir / "assets")

    cv_data = parse_cv(input_tex)
    ensure_dir(SCRIPT_DIR / "cache")
    write_text(SCRIPT_DIR / "cache" / "cv.json", json.dumps(cv_data, indent=2, ensure_ascii=False))

    cv_data, preprint_report = attach_preprints(cv_data, preprints_csv, threshold=0.86)

    pub_groups = collect_publication_groups(cv_data)
    preprint_items = collect_preprint_items(pub_groups)

    # Optional section pages requested by user.
    optional_titles = {
        "Teaching",
        "Service",
        "Grant Applications & Funds Raised",
        "Awards",
    }

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
        {"title": "Preprints", "url": "/preprints/"},
        {"title": "CV", "url": "/cv/"},
    ]

    optional_nav = []
    for sec in optional_sections:
        slug = slugify(sec["title"])
        sec["slug"] = slug
        optional_nav.append({"title": sec["title"], "url": f"/{slug}/"})

    nav = base_nav + optional_nav

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cv_html, cv_html_status = run_pandoc(input_tex, out_dir)
    cv_pdf_ok, cv_pdf_status = ensure_cv_pdf(input_tex, repo_root, out_dir / "assets" / "cv.pdf")

    meta = cv_data.get("meta", {})
    meta.setdefault("name", "Chris J. Vargo")
    meta.setdefault("current_as_of", "")

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
        "build_timestamp": timestamp,
        "site_url": site_url.rstrip("/"),
    }

    # Home
    home_html = env.get_template("index.html").render(
        **common_ctx,
        bio_text=bio_text,
        research_interests=research_interests,
        quick_links=nav,
    )
    write_text(out_dir / "index.html", home_html)

    # Publications
    pubs_html = env.get_template("publications.html").render(
        **common_ctx,
        publication_groups=pub_groups,
    )
    write_text(out_dir / "publications" / "index.html", pubs_html)

    # Preprints
    preprints_html = env.get_template("preprints.html").render(
        **common_ctx,
        preprints=preprint_items,
    )
    write_text(out_dir / "preprints" / "index.html", preprints_html)

    # CV page
    cv_html_page = env.get_template("cv.html").render(
        **common_ctx,
        cv_html=cv_html,
        cv_html_status=cv_html_status,
        cv_pdf_ok=cv_pdf_ok,
    )
    write_text(out_dir / "cv" / "index.html", cv_html_page)

    # Optional pages
    section_template = env.get_template("section.html")
    for sec in optional_sections:
        rendered = section_template.render(**common_ctx, section=sec)
        write_text(out_dir / sec["slug"] / "index.html", rendered)

    # Build reports
    report = {
        **preprint_report,
        "cv_html_status": cv_html_status,
        "cv_pdf_status": cv_pdf_status,
        "publication_groups": [g.get("title") for g in pub_groups],
        "preprints_page_count": len(preprint_items),
        "build_timestamp": timestamp,
    }
    write_text(out_dir / "build_report.json", json.dumps(report, indent=2, ensure_ascii=False))
    write_text(out_dir / "build_report.txt", render_build_report_text(report))

    # Static assets
    copy_static(static_dir, out_dir / "assets")

    # Site-level control files
    write_text(out_dir / "robots.txt", "User-agent: *\nAllow: /\n")
    write_text(
        out_dir / "404.html",
        env.get_template("base.html").render(
            **common_ctx,
            page_title="Page Not Found",
            content_html="<h2>404</h2><p>The page you requested does not exist.</p><p><a href='/'>&larr; Back to home</a></p>",
        ),
    )

    # CNAME for custom domain clarity.
    write_text(out_dir / "CNAME", f"{domain}\n")

    # Sitemap
    page_paths = [
        "/",
        "/publications/",
        "/preprints/",
        "/cv/",
    ] + [x["url"] for x in optional_nav]

    urls_xml = "\n".join(
        f"  <url><loc>{html.escape(site_url.rstrip('/') + path)}</loc></url>" for path in page_paths
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls_xml}\n"
        "</urlset>\n"
    )
    write_text(out_dir / "sitemap.xml", sitemap)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--preprints", required=True, type=Path)
    parser.add_argument("--out", default=Path("dist"), type=Path)
    parser.add_argument("--site-url", default="https://chrisjvargo.com")
    parser.add_argument("--domain", default="chrisjvargo.com")
    args = parser.parse_args()

    report = build_site(args.input, args.preprints, args.out, args.site_url, args.domain)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
