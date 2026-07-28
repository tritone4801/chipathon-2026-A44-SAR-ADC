#!/usr/bin/env python3
"""Create and audit a SHA-256 manifest for a completed evidence package."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    manifest_path = root / "manifest_sha256.csv"
    audit_path = root / "manifest_audit.json"
    excluded_paths = {manifest_path, audit_path}
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path not in excluded_paths
        and "__pycache__" not in path.relative_to(root).parts
        and path.suffix != ".pyc"
        and "tmp" not in path.relative_to(root).parts
    )

    rows = [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
    ]
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["relative_path", "size_bytes", "sha256"]
        )
        writer.writeheader()
        writer.writerows(rows)

    failures = []
    for row in rows:
        path = root / row["relative_path"]
        if not path.is_file():
            failures.append({"relative_path": row["relative_path"], "reason": "missing"})
        elif path.stat().st_size != int(row["size_bytes"]):
            failures.append({"relative_path": row["relative_path"], "reason": "size"})
        elif sha256(path) != row["sha256"]:
            failures.append({"relative_path": row["relative_path"], "reason": "sha256"})

    audit = {
        "status": "PASS_MANIFEST_AUDIT" if not failures else "FAIL_MANIFEST_AUDIT",
        "pass": not failures,
        "root": str(root),
        "manifest_entries": len(rows),
        "manifest_sha256": sha256(manifest_path),
        "failures": failures,
        "excluded": [
            manifest_path.relative_to(root).as_posix(),
            audit_path.relative_to(root).as_posix(),
            "tmp/",
            "__pycache__/",
            "*.pyc",
        ],
    }
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return 0 if audit["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
