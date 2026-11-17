"""Scan/hash every upload file, then verify its exact staged Git identity."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[4]
sys.path.insert(0, str(ROOT))
from scripts.check_secrets import SECRET_PATTERNS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    if args.staged:
        manifest = json.loads((EVIDENCE / "upload-file-hashes.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "PASS" and not manifest["credential_findings"]
        raw = subprocess.check_output(["git", "ls-files", "--stage", "-z", "--", "data", "artifacts/indexes", "artifacts/enrichment"], cwd=ROOT)
        indexed = {}
        for item in raw.split(b"\0"):
            if item:
                metadata, name = item.split(b"\t", 1)
                mode, oid, stage = metadata.decode().split()
                assert mode == "100644" and stage == "0"
                indexed[name.decode()] = oid
        expected = {item["path"]: item["git_blob"] for item in manifest["files"]}
        assert indexed == expected, {"missing": sorted(set(expected) - set(indexed)), "extra": sorted(set(indexed) - set(expected)), "mismatched": [p for p in expected if p in indexed and expected[p] != indexed[p]]}
        result = {"status": "PASS", "staged_files": len(indexed), "logical_bytes": manifest["logical_bytes"],
                  "exact_git_blob_match": True, "historical_sha256_and_blob_checks": manifest["historical_checked"],
                  "credential_findings": 0}
        (EVIDENCE / "staged-data-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result), flush=True)
        return

    started = time.perf_counter()
    inventory = json.loads((EVIDENCE / "upload-inventory.json").read_text(encoding="utf-8"))
    historical = json.loads((ROOT / "docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-input-manifest.json").read_text(encoding="utf-8"))["files"]
    expected = {item["destination_path"]: item for item in historical}
    patterns = [(label, re.compile(pattern.pattern.encode())) for label, pattern in SECRET_PATTERNS]
    files, findings = [], []
    def scan(item: dict) -> tuple[dict, list[dict]]:
        path = ROOT / item["path"]
        sha256 = hashlib.sha256()
        blob = hashlib.sha1(b"blob " + str(item["bytes"]).encode() + b"\0")
        tail, size = b"", 0
        item_findings = []
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
                sha256.update(chunk)
                blob.update(chunk)
                size += len(chunk)
                block = tail + chunk
                for label, pattern in patterns:
                    if pattern.search(block):
                        item_findings.append({"path": item["path"], "kind": label})
                tail = block[-128:]
        assert size == item["bytes"], item["path"]
        row = {**item, "sha256": sha256.hexdigest(), "git_blob": blob.hexdigest()}
        if item["path"] in expected:
            prior = expected[item["path"]]
            assert row["sha256"] == prior["expected_sha256_from_verified_archive"], item["path"]
            assert row["git_blob"] == prior["expected_git_blob_sha1"], item["path"]
        return row, item_findings

    checked = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for number, (row, item_findings) in enumerate(pool.map(scan, inventory["files"]), 1):
            files.append(row)
            findings.extend(item_findings)
            checked += row["path"] in expected
            if number % 5000 == 0:
                print(json.dumps({"hashed_and_scanned": number, "total": len(inventory["files"])}), flush=True)
    assert checked == len(historical)
    result = {"status": "PASS" if not findings else "FAIL", "files": files, "file_count": len(files),
              "logical_bytes": sum(row["bytes"] for row in files), "historical_checked": checked,
              "credential_findings": findings, "read_workers": 8,
              "elapsed_seconds": round(time.perf_counter() - started, 3)}
    (EVIDENCE / "upload-file-hashes.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "files"}), flush=True)
    assert not findings, "Credential-bearing upload candidate; values were not printed"


if __name__ == "__main__":
    main()
