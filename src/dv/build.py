from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment

from .charts import svg_bar_chart
from .language_lint import lint_text
from .load_release import load_release, sha256


DV_ROUTES = [
    ("", "index.html", "Overview"),
    ("findings", "simple.html", "Findings"),
    ("funnel", "simple.html", "Funnel"),
    ("investigation", "simple.html", "Investigation"),
    ("civil-criminal", "simple.html", "Civil And Criminal Classification"),
    ("cases", "cases.html", "Cases"),
    ("costs", "costs.html", "Costs"),
    ("methods", "simple.html", "Methods"),
    ("robustness", "simple.html", "Robustness"),
    ("data", "data.html", "Data"),
    ("sources", "simple.html", "Sources"),
    ("limitations", "simple.html", "Limitations"),
    ("responses", "simple.html", "Responses"),
    ("corrections", "simple.html", "Corrections"),
    ("updates", "simple.html", "Updates"),
    ("brief", "brief.html", "Brief"),
    ("downloads", "data.html", "Downloads"),
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "case"


def copy_downloads(release_dir: Path, out_dir: Path) -> dict[str, str]:
    downloads = out_dir / "downloads"
    if downloads.exists():
        shutil.rmtree(downloads)
    downloads.mkdir(parents=True)
    copied = {}
    for src in release_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(release_dir)
            dst = downloads / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied[str(rel)] = sha256(dst)
    return copied


def table_html(rows: list[dict[str, Any]], max_rows: int | None = None) -> str:
    if max_rows is not None:
        rows = rows[:max_rows]
    if not rows:
        return "<p>No rows.</p>"
    cols = list(rows[0].keys())
    out = ['<div class="table-wrap"><table><thead><tr>']
    out.extend(f'<th scope="col">{html.escape(c.replace("_", " "))}</th>' for c in cols)
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        out.extend(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in cols)
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def status_counts(hypotheses: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in hypotheses:
        counts[row["support_status"]] = counts.get(row["support_status"], 0) + 1
    return counts


def json_ld(payload: dict[str, Any]) -> str:
    return '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False) + "</script>"


def build_dv_pages(repo_root: Path, out_dir: Path, site_url: str, common_ctx: dict[str, Any], env: Environment) -> dict[str, Any]:
    release_dir = repo_root / "data" / "dv_public_release"
    data = load_release(release_dir)
    release = data["release"]
    hypotheses = data["hypotheses"]
    claims = data["claims"]
    cases = data["cases"]
    for case in cases:
        case["case_slug"] = slugify(case.get("public_name_or_pseudonym") or case.get("case_id"))
    damages = data["damages"]
    public_tables = data["public_tables"]
    limitations = data["limitations"]

    dv_out = out_dir / "dv"
    copied = copy_downloads(release_dir, dv_out)
    claim_by_id = {c["claim_id"]: c for c in claims}
    hero_claim = claim_by_id.get("claim-public-001", claims[0] if claims else {})
    table_rates = public_tables.get("boulder_pd_public_call_arrest_disposition_rates.csv", [])
    domestic_rows = [r for r in table_rates if r.get("candidate_family") == "domestic_label"]
    chart = svg_bar_chart(
        "Boulder Police domestic-labeled public calls",
        "Arrest-coded disposition counts for domestic-labeled public call rows by year.",
        [{"label": r["year"], "value": r["arrest_disposition_n"]} for r in domestic_rows],
        "label",
        "value",
    )
    pages: list[dict[str, str]] = []
    dv_nav = [
        {"title": "Findings", "url": "/dv/findings/"},
        {"title": "Cases & Costs", "url": "/dv/cases/"},
        {"title": "Methods", "url": "/dv/methods/"},
        {"title": "Data", "url": "/dv/data/"},
        {"title": "Responses", "url": "/dv/responses/"},
    ]
    base_context = {
        **common_ctx,
        "dv_nav": dv_nav,
        "release": release,
        "claims": claims,
        "hypotheses": hypotheses,
        "cases": cases,
        "damages": damages,
        "limitations": limitations,
        "hero_claim": hero_claim,
        "hypothesis_status_counts": status_counts(hypotheses),
        "public_call_table": table_rates,
        "domestic_call_chart": chart,
        "downloads": copied,
        "json_ld": json_ld(
            {
                "@context": "https://schema.org",
                "@type": "Dataset",
                "name": "Boulder County Domestic Violence Enforcement Audit public status release",
                "url": f"{site_url.rstrip('/')}/dv/",
                "dateModified": release["generated_at_utc"],
                "creator": {"@type": "Person", "name": "Chris J. Vargo"},
                "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{site_url.rstrip('/')}/dv/downloads/claims.json"}],
            }
        ),
    }
    for slug, template_name, title in DV_ROUTES:
        page_dir = dv_out if not slug else dv_out / slug
        rendered = env.get_template(f"dv/{template_name}").render(
            **base_context,
            page_title=f"{title} | Boulder County Domestic Violence Enforcement Audit",
            page_description="Disclosure-safe public status release for a Boulder County domestic-violence enforcement audit.",
            canonical_url=f"{site_url.rstrip('/')}/dv/{slug + '/' if slug else ''}",
            social_title=f"{title} | DV Audit",
            social_description="Disclosure-safe public evidence release with claim registry, methods, cases, costs, and limitations.",
            social_url=f"{site_url.rstrip('/')}/dv/{slug + '/' if slug else ''}",
            social_image=f"{site_url.rstrip('/')}/assets/og-default.png",
            og_type="website",
            section_title=title,
        )
        errors = lint_text(rendered)
        if errors:
            raise ValueError(f"DV language lint failed for /dv/{slug}/: {errors}")
        write(page_dir / "index.html", rendered)
        pages.append({"url": f"/dv/{slug + '/' if slug else ''}", "path": str(page_dir / "index.html")})
    case_template = env.get_template("dv/case.html")
    for case in cases:
        rendered = case_template.render(
            **base_context,
            case=case,
            page_title=f"{case.get('public_name_or_pseudonym')} | DV Audit Case",
            page_description="Disclosure-safe case memo with proof-tier and finality status.",
            canonical_url=f"{site_url.rstrip('/')}/dv/cases/{case['case_slug']}/",
            social_title=f"{case.get('public_name_or_pseudonym')} | DV Audit",
            social_description="Procedural case status, proof-tier classification, and public-source limitations.",
            social_url=f"{site_url.rstrip('/')}/dv/cases/{case['case_slug']}/",
            social_image=f"{site_url.rstrip('/')}/assets/og-default.png",
            og_type="article",
        )
        errors = lint_text(rendered)
        if errors:
            raise ValueError(f"DV language lint failed for case {case['case_slug']}: {errors}")
        write(dv_out / "cases" / case["case_slug"] / "index.html", rendered)
        pages.append({"url": f"/dv/cases/{case['case_slug']}/", "path": str(dv_out / "cases" / case["case_slug"] / "index.html")})
    write(dv_out / "feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>DV Audit Updates</title><id>{site_url.rstrip("/")}/dv/updates/</id><updated>{datetime.now(timezone.utc).isoformat()}</updated></feed>\n')
    write(dv_out / "llms.txt", "# Boulder County Domestic Violence Enforcement Audit\n\nDisclosure-safe public status release.\n")
    pages.extend([{"url": "/dv/feed.xml", "path": str(dv_out / "feed.xml")}, {"url": "/dv/llms.txt", "path": str(dv_out / "llms.txt")}])
    build_report = {"release_id": release["release_id"], "release_version": release["release_version"], "hypothesis_status_counts": status_counts(hypotheses), "claim_count": len(claims), "case_count": len(cases), "download_count": len(copied)}
    write(dv_out / "dv_build_report.json", json.dumps(build_report, indent=2) + "\n")
    pages.append({"url": "/dv/dv_build_report.json", "path": str(dv_out / "dv_build_report.json")})
    return {"pages": pages, "build_report": build_report}
