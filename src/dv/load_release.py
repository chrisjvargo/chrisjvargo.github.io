from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_release(release_dir: Path) -> dict[str, Any]:
    required = [
        "release.json",
        "claims.json",
        "hypothesis_verification.csv",
        "case_summaries.json",
        "damages_summary.csv",
        "proof_matrix.csv",
        "source_manifest_public.csv",
        "codebook_public.csv",
        "SHA256SUMS",
    ]
    missing = [name for name in required if not (release_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"DV release missing required files: {missing}")
    public_tables: dict[str, list[dict[str, str]]] = {}
    table_dir = release_dir / "public_tables"
    if table_dir.exists():
        for table in table_dir.glob("*.csv"):
            public_tables[table.name] = read_csv(table)
    return {
        "release_dir": release_dir,
        "release": read_json(release_dir / "release.json"),
        "claims": read_json(release_dir / "claims.json"),
        "hypotheses": read_csv(release_dir / "hypothesis_verification.csv"),
        "cases": read_json(release_dir / "case_summaries.json"),
        "damages": read_csv(release_dir / "damages_summary.csv"),
        "proof": read_csv(release_dir / "proof_matrix.csv"),
        "limitations": read_json(release_dir / "limitations.json"),
        "public_tables": public_tables,
    }

