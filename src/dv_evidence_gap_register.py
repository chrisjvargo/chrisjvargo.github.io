#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
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


def write_sha256sums(root: Path) -> None:
    files = [path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in sorted(files)
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "--release-csv",
        type=Path,
        default=Path("data/dv_public_release/public_tables/evidence_gap_register.csv"),
    )
    parser.add_argument(
        "--release-root",
        type=Path,
        default=Path("data/dv_public_release"),
        help="Refresh this release directory's SHA256SUMS after writing --release-csv.",
    )
    args = parser.parse_args()

    rows = read_rows(args.source)
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

    write_csv(args.out_csv, rows)
    write_csv(args.release_csv, rows)
    write_markdown(args.out_md, rows)
    write_sha256sums(args.release_root)
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.release_csv}")
    print(f"Wrote {args.out_md}")
    print(f"Refreshed {args.release_root / 'SHA256SUMS'}")


if __name__ == "__main__":
    main()
