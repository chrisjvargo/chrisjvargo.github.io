#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from collections import defaultdict
from pathlib import Path

REQUIRED_COLUMNS = [
    "hypothesis_id",
    "support_status",
    "primary_estimand",
    "minimum_unit",
    "required_denominator",
    "available_public_evidence",
    "missing_fields",
    "request_targets",
    "request_files",
    "analysis_ready",
    "current_answer",
]

AGENCY_REQUEST_FILES = [
    "records_requests/boulder_police_department.md",
    "records_requests/boulder_county_sheriff_office.md",
    "records_requests/longmont_public_safety.md",
    "records_requests/lafayette_police.md",
    "records_requests/louisville_police.md",
    "records_requests/erie_police.md",
    "records_requests/cu_boulder_police.md",
]

COURT_DA_REQUEST_FILES = [
    "records_requests/twentieth_judicial_da.md",
    "records_requests/colorado_judicial_branch.md",
    "records_requests/boulder_municipal_court.md",
    "records_requests/other_municipal_courts.md",
]

SUBMISSION_CHANNELS = {
    "records_requests/audit_46_cases/boulder_police_46_case_audit_crosswalk.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercolorado.gov/boulder-police-department-data-and-report-request",
        "official_source_url": "https://bouldercolorado.gov/services/request-crime-reports-or-records",
        "source_note": "City page says police records requests can include police reports, photos, body/dash camera video, 911 audio, and CAD incident reports.",
    },
    "records_requests/audit_46_cases/twentieth_da_46_case_audit_crosswalk.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/district-attorney/discovery-unit/",
        "official_source_url": "https://bouldercounty.gov/district-attorney/discovery-unit/",
        "source_note": "DA page directs other criminal-case record requests to the Open Records Portal.",
    },
    "records_requests/boulder_county_communications.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/records/colorado-open-records-act/",
        "official_source_url": "https://bouldercounty.gov/records/colorado-open-records-act/",
        "source_note": "Boulder County CORA page directs requesters to the county Open Records Center.",
    },
    "records_requests/boulder_county_jail.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/safety/sheriff/records/",
        "official_source_url": "https://bouldercounty.gov/safety/sheriff/records/",
        "source_note": "Sheriff Records Section page provides records-request contact information.",
    },
    "records_requests/boulder_county_sheriff_office.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/safety/sheriff/records/",
        "official_source_url": "https://bouldercounty.gov/safety/sheriff/records/",
        "source_note": "Sheriff Records Section page provides records-request contact information.",
    },
    "records_requests/boulder_municipal_court.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercolorado.gov/services/municipal-court-records-forms-and-requests",
        "official_source_url": "https://bouldercolorado.gov/services/municipal-court-records-forms-and-requests",
        "source_note": "Boulder Municipal Court records, forms, and requests page identifies the court contact and request area.",
    },
    "records_requests/boulder_police_department.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercolorado.gov/boulder-police-department-data-and-report-request",
        "official_source_url": "https://bouldercolorado.gov/services/request-crime-reports-or-records",
        "source_note": "City page says police records requests can include police reports, photos, body/dash camera video, 911 audio, and CAD incident reports.",
    },
    "records_requests/claims_and_settlements/boulder_county_claims_settlements.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/records/colorado-open-records-act/",
        "official_source_url": "https://bouldercounty.gov/records/colorado-open-records-act/",
        "source_note": "Boulder County CORA page directs requesters to the county Open Records Center.",
    },
    "records_requests/claims_and_settlements/city_of_boulder_claims_settlements.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercolorado.gov/open-records-request",
        "official_source_url": "https://bouldercolorado.gov/open-records-request",
        "source_note": "City CORA page directs non-police department requests through the open records form.",
    },
    "records_requests/colorado_bureau_of_investigation.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://cbi.colorado.gov/about/colorado-criminal-justice-records-act-ccjra/public-records-requests",
        "official_source_url": "https://cbi.colorado.gov/about/colorado-criminal-justice-records-act-ccjra/public-records-requests",
        "source_note": "CBI CCJRA page explains CBI can provide records that pertain to CBI and directs requests to the appropriate custodian.",
    },
    "records_requests/colorado_judicial_branch.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "official_source_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "source_note": "Judicial Branch guide directs compiled-data requests to CJD 05-01 section 4.40 and Addendum A.",
    },
    "records_requests/court_outcomes/unjust_claims_court_outcomes.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "official_source_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "source_note": "Judicial Branch guide covers compiled court-data requests; municipal court components require municipal custodians.",
    },
    "records_requests/cu_boulder/cu_boulder_oiec_litigation_settlements.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.cu.edu/university-relations/cu-offices/university-relations/open-records-requests",
        "official_source_url": "https://www.cu.edu/university-relations/cu-offices/university-relations/open-records-requests",
        "source_note": "CU open-records page identifies CORA as the formal vehicle for university public-information requests.",
    },
    "records_requests/cu_boulder_police.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.colorado.edu/police/content/request-criminal-justice-record",
        "official_source_url": "https://www.colorado.edu/police/records",
        "source_note": "CUPD records page points to an online form for police report requests and gives records contact information.",
    },
    "records_requests/erie_police.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://townoferiecopd.nextrequest.com/",
        "official_source_url": "https://www.erieco.gov/2350/Police",
        "source_note": "Erie Police page links to records requests; Erie Police NextRequest portal accepts public records requests.",
    },
    "records_requests/lafayette_police.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.lafayetteco.gov/528/Records-Division",
        "official_source_url": "https://www.lafayetteco.gov/528/Records-Division",
        "source_note": "Lafayette Records Division page provides records-request links and contact information.",
    },
    "records_requests/longmont_public_safety.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://longmontcolorado.gov/public-safety/about-longmont-public-safety/collaborative-services-division/public-safety-records/",
        "official_source_url": "https://longmontcolorado.gov/public-safety/about-longmont-public-safety/collaborative-services-division/public-safety-records/",
        "source_note": "Longmont Public Safety Records page describes public-safety records requests and release functions.",
    },
    "records_requests/louisville_police.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://www.louisvilleco.gov/local-government/public-records-requests",
        "official_source_url": "https://www.louisvilleco.gov/local-government/public-records-requests",
        "source_note": "Louisville public-records page distinguishes police criminal-justice records from City Clerk records.",
    },
    "records_requests/other_municipal_courts.md": {
        "channel_status": "multi_custodian_manual_verification_required",
        "official_submission_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "official_source_url": "https://www.coloradojudicial.gov/access-guide-public-records",
        "source_note": "Use Judicial Branch compiled-data guidance for state data; separate municipal court custodians require case-by-case channel verification.",
    },
    "records_requests/twentieth_judicial_da.md": {
        "channel_status": "official_channel_identified",
        "official_submission_url": "https://bouldercounty.gov/district-attorney/discovery-unit/",
        "official_source_url": "https://bouldercounty.gov/district-attorney/discovery-unit/",
        "source_note": "DA page directs other criminal-case record requests to the Open Records Portal.",
    },
}

CHANNEL_VERIFICATION_DATE = "2026-06-26"


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def expanded_request_files(value: str) -> list[str]:
    raw = value.strip()
    if raw == "all agency records_requests/*.md":
        return AGENCY_REQUEST_FILES
    if raw == "agency, DA, and court records requests":
        return unique(AGENCY_REQUEST_FILES + COURT_DA_REQUEST_FILES)

    files: list[str] = []
    for part in [item.strip() for item in raw.split(";") if item.strip()]:
        if part == "agency records requests":
            files.extend(AGENCY_REQUEST_FILES)
        elif part.endswith(" and peer agency requests"):
            first = part.removesuffix(" and peer agency requests").strip()
            files.extend([first, *[f for f in AGENCY_REQUEST_FILES if f != first]])
        else:
            files.append(part)
    return unique(files)


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        next_row = dict(row)
        next_row["request_files"] = "; ".join(expanded_request_files(row.get("request_files", "")))
        normalized.append(next_row)
    return normalized


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [col for col in REQUIRED_COLUMNS if col not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"{path} missing required columns: {', '.join(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "hypothesis_id",
        "support_status",
        "analysis_ready",
        "minimum_unit",
        "required_denominator",
        "missing_fields",
        "request_targets",
        "request_files",
        "current_answer",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_request_title(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return path.stem.replace("_", " ").title()


def build_dispatch_rows(release_root: Path, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    linked_hypotheses: dict[str, list[str]] = defaultdict(list)
    linked_missing_fields: dict[str, list[str]] = defaultdict(list)
    linked_targets: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        hypothesis_id = row.get("hypothesis_id", "")
        for rel in expanded_request_files(row.get("request_files", "")):
            if not rel.startswith("records_requests/"):
                continue
            linked_hypotheses[rel].append(hypothesis_id)
            linked_missing_fields[rel].append(row.get("missing_fields", ""))
            linked_targets[rel].append(row.get("request_targets", ""))

    request_files = sorted(path.relative_to(release_root).as_posix() for path in (release_root / "records_requests").rglob("*.md"))
    dispatch_rows: list[dict[str, str]] = []
    for rel in request_files:
        dispatch_rows.append(
            {
                "request_file": rel,
                "public_download_path": f"/dv/downloads/{rel}",
                "request_title": read_request_title(release_root / rel),
                "linked_hypotheses": "; ".join(unique(linked_hypotheses.get(rel, []))),
                "linked_missing_fields": " | ".join(unique([v for v in linked_missing_fields.get(rel, []) if v])),
                "linked_request_targets": " | ".join(unique([v for v in linked_targets.get(rel, []) if v])),
                "authorization_status": "not_authorized_to_transmit",
                "transmission_status": "not_transmitted_requires_user_authorization",
                "sent_date": "",
                "response_status": "not_requested",
                "response_date": "",
                "current_next_action": "obtain explicit authorization before sending; update this matrix after transmission and response",
            }
        )
    return dispatch_rows


def write_dispatch_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "request_file",
        "public_download_path",
        "request_title",
        "linked_hypotheses",
        "linked_missing_fields",
        "linked_request_targets",
        "authorization_status",
        "transmission_status",
        "sent_date",
        "response_status",
        "response_date",
        "current_next_action",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def build_channel_rows(dispatch_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    channel_rows: list[dict[str, str]] = []
    for row in dispatch_rows:
        rel = row.get("request_file", "")
        channel = SUBMISSION_CHANNELS.get(rel, {})
        channel_rows.append(
            {
                "request_file": rel,
                "request_title": row.get("request_title", ""),
                "linked_hypotheses": row.get("linked_hypotheses", ""),
                "channel_status": channel.get("channel_status", "manual_channel_verification_required"),
                "official_submission_url": channel.get("official_submission_url", ""),
                "official_source_url": channel.get("official_source_url", ""),
                "source_verification_date": CHANNEL_VERIFICATION_DATE,
                "source_note": channel.get("source_note", ""),
                "authorization_status": row.get("authorization_status", "not_authorized_to_transmit"),
                "transmission_status": row.get("transmission_status", "not_transmitted_requires_user_authorization"),
            }
        )
    return channel_rows


def write_channels_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "request_file",
        "request_title",
        "linked_hypotheses",
        "channel_status",
        "official_submission_url",
        "official_source_url",
        "source_verification_date",
        "source_note",
        "authorization_status",
        "transmission_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_sha256sums(root: Path) -> None:
    files = [path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in sorted(files)
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_release_request_files(root: Path, rows: list[dict[str, str]]) -> None:
    missing: list[str] = []
    for row in rows:
        for rel in expanded_request_files(row.get("request_files", "")):
            if rel.startswith("records_requests/") and not (root / rel).exists():
                missing.append(rel)
    if missing:
        raise SystemExit("release is missing referenced request files: " + ", ".join(sorted(set(missing))))


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    status_counts = Counter(row.get("support_status", "unknown") for row in rows)
    readiness_counts = Counter(row.get("analysis_ready", "unknown") for row in rows)
    unresolved = [row for row in rows if row.get("support_status") == "unresolved_required_data_unavailable"]
    rows_with_paths = sum(1 for row in unresolved if row.get("request_files"))

    lines = [
        "# DV Evidence Gap Register",
        "",
        "Generated from `data/dv_public_release/public_tables/hypothesis_data_resolution.csv`.",
        "",
        "## Summary",
        "",
        f"- Hypotheses tracked: {len(rows)}",
        f"- Unresolved for required data/model artifacts: {len(unresolved)}",
        f"- Unresolved hypotheses with mapped request files: {rows_with_paths}/{len(unresolved)}",
        "",
        "## Support Status Counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Analysis Readiness Counts", ""])
    for status, count in sorted(readiness_counts.items()):
        lines.append(f"- `{status}`: {count}")

    lines.extend(
        [
            "",
            "## Hypothesis-Level Gaps",
            "",
            "| Hypothesis | Readiness | Minimum unit | Required denominator | Missing fields | Request targets | Current answer |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        values = [
            row.get("hypothesis_id", ""),
            row.get("analysis_ready", ""),
            row.get("minimum_unit", ""),
            row.get("required_denominator", ""),
            row.get("missing_fields", ""),
            row.get("request_targets", ""),
            row.get("current_answer", ""),
        ]
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This register is an acquisition and verification control sheet. It does not convert public aggregate context into confirmatory findings.",
            "A hypothesis remains unresolved until the required denominator, unit-level records, and model artifacts are present and regenerated through the release pipeline.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dispatch_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    linked = [row for row in rows if row.get("linked_hypotheses")]
    lines = [
        "# DV Records Request Dispatch Matrix",
        "",
        "Generated from the public evidence-gap register and release request-package files.",
        "",
        "## Summary",
        "",
        f"- Request packages tracked: {len(rows)}",
        f"- Request packages linked to unresolved hypotheses: {len(linked)}",
        "- Transmission status: not transmitted; explicit user authorization is required before sending any request.",
        "",
        "## Request Packages",
        "",
        "| Request package | Linked hypotheses | Transmission status |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        package = f"[{row.get('request_title')}]({row.get('public_download_path')})"
        lines.append(
            "| "
            + " | ".join(
                [
                    package,
                    row.get("linked_hypotheses", "") or "supplemental/not directly linked",
                    row.get("transmission_status", ""),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/dv_public_release/public_tables/hypothesis_data_resolution.csv"),
    )
    parser.add_argument("--out-csv", type=Path, default=Path("dv_publication/evidence_gap_register.csv"))
    parser.add_argument("--out-md", type=Path, default=Path("DV_EVIDENCE_GAP_REGISTER.md"))
    parser.add_argument(
        "--dispatch-csv",
        type=Path,
        default=Path("dv_publication/records_request_dispatch_matrix.csv"),
    )
    parser.add_argument(
        "--dispatch-md",
        type=Path,
        default=Path("DV_RECORDS_REQUEST_DISPATCH_MATRIX.md"),
    )
    parser.add_argument(
        "--release-csv",
        type=Path,
        default=Path("data/dv_public_release/public_tables/evidence_gap_register.csv"),
    )
    parser.add_argument(
        "--release-dispatch-csv",
        type=Path,
        default=Path("data/dv_public_release/public_tables/records_request_dispatch_matrix.csv"),
    )
    parser.add_argument(
        "--channels-csv",
        type=Path,
        default=Path("dv_publication/records_request_submission_channels.csv"),
    )
    parser.add_argument(
        "--release-channels-csv",
        type=Path,
        default=Path("data/dv_public_release/public_tables/records_request_submission_channels.csv"),
    )
    parser.add_argument(
        "--release-root",
        type=Path,
        default=Path("data/dv_public_release"),
        help="Refresh this release directory's SHA256SUMS after writing --release-csv.",
    )
    args = parser.parse_args()

    rows = normalize_rows(read_rows(args.source))
    if len(rows) != 14:
        raise SystemExit(f"expected 14 hypotheses, found {len(rows)}")
    unresolved = [row for row in rows if row.get("support_status") == "unresolved_required_data_unavailable"]
    incomplete = [
        row.get("hypothesis_id", "<unknown>")
        for row in unresolved
        if not (row.get("missing_fields") and row.get("request_targets") and row.get("request_files"))
    ]
    if incomplete:
        raise SystemExit("unresolved hypotheses missing gap mapping: " + ", ".join(incomplete))
    validate_release_request_files(args.release_root, rows)
    dispatch_rows = build_dispatch_rows(args.release_root, rows)
    channel_rows = build_channel_rows(dispatch_rows)

    write_csv(args.out_csv, rows)
    write_csv(args.release_csv, rows)
    write_markdown(args.out_md, rows)
    write_dispatch_csv(args.dispatch_csv, dispatch_rows)
    write_dispatch_csv(args.release_dispatch_csv, dispatch_rows)
    write_dispatch_markdown(args.dispatch_md, dispatch_rows)
    write_channels_csv(args.channels_csv, channel_rows)
    write_channels_csv(args.release_channels_csv, channel_rows)
    write_sha256sums(args.release_root)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.release_csv}")
    print(f"Wrote {args.out_md}")
    print(f"Wrote {args.dispatch_csv}")
    print(f"Wrote {args.release_dispatch_csv}")
    print(f"Wrote {args.dispatch_md}")
    print(f"Wrote {args.channels_csv}")
    print(f"Wrote {args.release_channels_csv}")
    print(f"Refreshed {args.release_root / 'SHA256SUMS'}")


if __name__ == "__main__":
    main()
