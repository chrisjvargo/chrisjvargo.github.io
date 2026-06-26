#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class Check:
    check_id: str
    area: str
    status: str
    evidence: str
    next_action: str


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def git_status(repo: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "git_status_unavailable"
    return proc.stdout.strip()


def phrase_check(page: str, required: list[str], forbidden: list[str]) -> tuple[bool, str]:
    missing = [phrase for phrase in required if phrase not in page]
    present_forbidden = [phrase for phrase in forbidden if phrase in page]
    problems = []
    if missing:
        problems.append("missing=" + "; ".join(missing))
    if present_forbidden:
        problems.append("forbidden_present=" + "; ".join(present_forbidden))
    return not problems, "; ".join(problems) if problems else "all required phrases present; forbidden phrases absent"


def build_audit(repo: Path, dist: Path) -> list[Check]:
    build_report = read_json(dist / "build_report.json")
    dv_report = read_json(dist / "dv" / "dv_build_report.json")
    home = text(dist / "index.html")
    cv = text(dist / "cv" / "index.html")
    status = git_status(repo)
    checks: list[Check] = []

    checks.append(
        Check(
            "OPS001",
            "local_build_artifacts",
            "pass" if build_report else "open_gap",
            "dist/build_report.json present" if build_report else "dist/build_report.json missing",
            "Run `make build`." if not build_report else "Keep running `make build` before deploy.",
        )
    )
    checks.append(
        Check(
            "OPS002",
            "cv_pdf_and_html",
            "pass"
            if build_report.get("cv_html_status") == "pandoc_ok"
            and build_report.get("cv_pdf_status") in {"compiled_with_latexmk", "copied_cached_pdf"}
            and "Pandoc HTML conversion is not available" not in cv
            else "open_gap",
            (
                f"cv_html_status={build_report.get('cv_html_status')}; "
                f"cv_pdf_status={build_report.get('cv_pdf_status')}; "
                f"fallback_visible={'Pandoc HTML conversion is not available' in cv}"
            ),
            "Fix CV generation or rerun `make cv && make build`."
            if build_report.get("cv_html_status") != "pandoc_ok"
            else "No action needed for local CV generation.",
        )
    )

    home_ok, home_evidence = phrase_check(
        home,
        required=[
            "Google Cloud AI work",
            "Research, teaching, and software for AI field readiness.",
            "Ph.D., Mass Communication",
            "Master of Arts, Advertising &amp; Public Relations",
            "Bachelor of Arts, Advertising &amp; Public Relations",
            "Field-readiness needs analysis",
            "Seller-readiness transcript demo",
            "LLM deployment courseware",
            "socialcontext.ai",
            "Inside a Social Media Brand Safety Algorithm",
            "Toward a Tweet Typology",
            "From Ads to Addiction",
        ],
        forbidden=[
            "Portfolio Links",
            "Quick Links",
            "4,499 citations",
            "h-index 26",
            "126,582 Coursera",
        ],
    )
    checks.append(
        Check(
            "OPS003",
            "homepage_cv_positioning",
            "pass" if home_ok else "open_gap",
            home_evidence,
            "Update homepage copy/data and rerun `make build && make validate`." if not home_ok else "No action needed locally.",
        )
    )

    root_cv_artifacts = sorted(path.name for path in repo.glob("Vargo_CV.*") if path.is_file())
    checks.append(
        Check(
            "OPS004",
            "latex_artifact_hygiene",
            "pass" if not root_cv_artifacts else "open_gap",
            "no root-level Vargo_CV.* artifacts" if not root_cv_artifacts else "root artifacts=" + "; ".join(root_cv_artifacts),
            "Remove root-level generated LaTeX artifacts and run `make cv`." if root_cv_artifacts else "No action needed.",
        )
    )

    dv_statuses = dv_report.get("hypothesis_status_counts", {})
    unresolved = int(dv_statuses.get("unresolved_required_data_unavailable", 0) or 0)
    checks.append(
        Check(
            "OPS005",
            "dv_publication_evidence",
            "open_gap" if unresolved else "pass",
            f"hypothesis_status_counts={dv_statuses}",
            "Acquire/verify required case-level data and model artifacts, then regenerate the DV public release."
            if unresolved
            else "No unresolved DV hypothesis status remains in the public release.",
        )
    )

    missing_abstracts = int(build_report.get("missing_abstracts", 0) or 0)
    unmatched_publications = int(build_report.get("unmatched_publications", 0) or 0)
    required_metadata_gaps = int(build_report.get("required_publication_metadata_gaps", 0) or 0)
    selected_expected = int(build_report.get("selected_publication_expected_pages", 0) or 0)
    selected_present = int(build_report.get("selected_publication_detail_pages", 0) or 0)
    metadata_policy_exists = (repo / "PUBLICATION_METADATA_POLICY.md").exists()
    publication_metadata_ok = required_metadata_gaps == 0 and selected_expected == selected_present and metadata_policy_exists
    checks.append(
        Check(
            "OPS006",
            "publication_metadata",
            "pass" if publication_metadata_ok else "open_gap",
            (
                f"required_publication_metadata_gaps={required_metadata_gaps}; "
                f"selected_publication_pages={selected_present}/{selected_expected}; "
                f"metadata_policy_exists={metadata_policy_exists}; "
                f"optional_missing_abstracts={missing_abstracts}; "
                f"optional_unmatched_preprints={unmatched_publications}"
            ),
            "Fix required citation metadata or selected publication links."
            if not publication_metadata_ok
            else "Optional abstract/preprint enrichment remains backlog, not a full-operation blocker.",
        )
    )

    checks.append(
        Check(
            "OPS007",
            "deployment_state",
            "open_gap" if status else "pass",
            "working_tree_clean" if not status else "working_tree_changes=" + status.replace("\n", " | "),
            "Commit, push, and let the GitHub Pages workflow deploy." if status else "Verify live site after deployment.",
        )
    )

    root_cv_visual_report = read_json(repo / "dv_publication" / "root_cv_visual_qa_report.json")
    visual_artifacts = [
        repo / "dv_publication" / "root_cv_visual_qa_report.json",
        repo / "dv_publication" / "root_cv_screenshot_manifest.csv",
        repo / "dv_publication" / "screenshot_manifest.csv",
        repo / "DV_ACCESSIBILITY_REPORT.md",
        repo / "DV_PERFORMANCE_REPORT.md",
    ]
    visual_evidence = [str(path.relative_to(repo)) for path in visual_artifacts if path.exists()]
    root_cv_visual_passed = root_cv_visual_report.get("status") == "pass"
    visual_status = "pass" if root_cv_visual_passed and len(visual_evidence) == len(visual_artifacts) else "partial" if visual_evidence else "open_gap"
    checks.append(
        Check(
            "OPS008",
            "visual_accessibility_performance_qa",
            visual_status,
            (
                "root_cv_visual_status="
                + str(root_cv_visual_report.get("status", "missing"))
                + "; artifacts="
                + ("; ".join(visual_evidence) if visual_evidence else "none")
            ),
            "Run `make site-visual-qa` and preserve DV accessibility/performance artifacts."
            if visual_status != "pass"
            else "Local root/CV screenshot and smoke accessibility checks are current.",
        )
    )

    return checks


def write_markdown(path: Path, checks: list[Check]) -> None:
    counts: dict[str, int] = {}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    lines = [
        "# System Operation Gap Review",
        "",
        f"Generated from local inspection on {date.today().isoformat()}.",
        "",
        "## Status Summary",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Current Checks",
            "",
            "| ID | Area | Status | Evidence | Next action |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for check in checks:
        lines.append(
            "| "
            + " | ".join(
                value.replace("|", "\\|").replace("\n", " ")
                for value in [
                    check.check_id,
                    check.area,
                    check.status,
                    check.evidence,
                    check.next_action,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Recommended Verification Command",
            "",
            "```bash",
            "make cv && make build && make validate && make dv-test && make site-visual-qa && make operation-audit",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--out-md", type=Path, default=Path("SYSTEM_OPERATION_GAP_REVIEW.md"))
    parser.add_argument("--out-json", type=Path, default=Path("dist/system_operation_audit.json"))
    args = parser.parse_args()

    repo = args.repo.resolve()
    dist = args.dist if args.dist.is_absolute() else repo / args.dist
    checks = build_audit(repo, dist)
    out_md = args.out_md if args.out_md.is_absolute() else repo / args.out_md
    out_json = args.out_json if args.out_json.is_absolute() else repo / args.out_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(out_md, checks)
    out_json.write_text(json.dumps([asdict(check) for check in checks], indent=2), encoding="utf-8")
    print(f"Wrote {out_md.relative_to(repo)}")
    print(f"Wrote {out_json.relative_to(repo)}")


if __name__ == "__main__":
    main()
