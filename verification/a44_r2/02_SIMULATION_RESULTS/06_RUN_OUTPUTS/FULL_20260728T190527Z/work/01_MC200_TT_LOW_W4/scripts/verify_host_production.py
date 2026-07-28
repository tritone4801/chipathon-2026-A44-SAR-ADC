#!/usr/bin/env python3
"""Verify the live Windows SAR_CURRENT tree against the frozen 113-file receipt."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_host_production.py PACKAGE_ROOT PRODUCTION_ROOT")
    root = Path(sys.argv[1]).resolve()
    production = Path(sys.argv[2]).resolve()
    manifest = root / "manifests" / "production_source_integrity.csv"
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    failures = []
    for row in rows:
        path = production / row["relative_path"]
        if not path.is_file():
            failures.append({"relative_path": row["relative_path"], "reason": "missing"})
        elif path.stat().st_size != int(row["expected_size_bytes"]):
            failures.append({"relative_path": row["relative_path"], "reason": "size"})
        elif sha256(path) != row["expected_sha256"]:
            failures.append({"relative_path": row["relative_path"], "reason": "sha256"})

    package_manifest = production / "manifests" / "package_manifest_sha256.csv"
    result = {
        "status": "PASS_HOST_PRODUCTION_SOURCE_AUDIT" if not failures and len(rows) == 113 else "FAIL_HOST_PRODUCTION_SOURCE_AUDIT",
        "pass": not failures and len(rows) == 113,
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "production_root": str(production),
        "declared_files": len(rows),
        "matching_files": len(rows) - len(failures),
        "receipt_sha256": sha256(manifest),
        "package_manifest_present": package_manifest.is_file(),
        "package_manifest_sha256": sha256(package_manifest) if package_manifest.is_file() else None,
        "failures": failures,
    }
    output = root / "results" / "host_production_source_audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
