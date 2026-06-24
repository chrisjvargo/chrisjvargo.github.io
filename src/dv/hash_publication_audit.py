from __future__ import annotations

import hashlib
from pathlib import Path


def main() -> None:
    root = Path("dv_publication")
    files = [p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.as_posix()}"
        for path in sorted(files)
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
