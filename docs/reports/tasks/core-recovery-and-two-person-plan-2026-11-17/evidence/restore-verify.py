"""Fresh read-only verification of the full recovered input manifest."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[4]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    started = time.perf_counter()
    manifest = json.loads((EVIDENCE / "restore-input-manifest.json").read_text(encoding="utf-8"))
    original = json.loads((EVIDENCE / "restore-existing-before.json").read_text(encoding="utf-8"))["files"]
    files = manifest["files"]
    failures = []
    verified_bytes = 0
    paths = []
    for index, record in enumerate(files, start=1):
        relative = record["destination_path"]
        paths.append(relative)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            failures.append({"path": relative, "check": "regular_destination_file"})
            continue
        size = path.stat().st_size
        blob = hashlib.sha1(f"blob {size}\0".encode("ascii"))
        sha256 = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
                blob.update(chunk)
                sha256.update(chunk)
        if size != record["expected_bytes"]:
            failures.append({"path": relative, "check": "bytes"})
        if blob.hexdigest() != record["expected_git_blob_sha1"]:
            failures.append({"path": relative, "check": "pinned_git_blob_sha1"})
        if sha256.hexdigest() != record["expected_sha256_from_verified_archive"]:
            failures.append({"path": relative, "check": "archive_source_sha256"})
        verified_bytes += size
        if index % 5000 == 0:
            print(json.dumps({"verified_files": index, "expected_files": len(files)}), flush=True)
    unchanged = []
    for record in original:
        preserved = sha256_file(ROOT / record["path"]) == record["sha256"]
        unchanged.append({"path": record["path"], "sha256": record["sha256"], "unchanged": preserved})
        if not preserved:
            failures.append({"path": record["path"], "check": "existing_file_preserved"})
    ignore = subprocess.run(["git", "check-ignore", "-z", "--stdin"],
                            input=("\0".join(paths) + "\0").encode("utf-8"),
                            cwd=ROOT, capture_output=True, check=False)
    ignored = {entry.decode("utf-8") for entry in ignore.stdout.split(b"\0") if entry}
    unexpected_tracked = sorted(set(paths) - ignored)
    if ignore.returncode != 0 or unexpected_tracked:
        failures.append({"check": "recovered_files_gitignored", "exit_code": ignore.returncode,
                         "nonignored_paths": unexpected_tracked})
    known_csv = "data/processed/cleaned_video_info.csv"
    known_hash = "ce76aa4acaf6bbc5b2c8976f206710cb7693eae5328bfb913cc15aabbb73e102"
    actual_known_hash = sha256_file(ROOT / known_csv)
    if actual_known_hash != known_hash:
        failures.append({"check": "independent_prior_audit_csv_sha256"})
    inventory = Counter(record["source_path"].split("/")[1] if record["source_path"].startswith("data/")
                        else "legacy_app_data" for record in files)
    result = {
        "status": "PASS" if not failures else "FAIL",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "command": "C:/Users/lanph/.local/bin/python3.12.exe " + Path(__file__).relative_to(ROOT).as_posix(),
        "revision": manifest["revision"], "expected_files": len(files),
        "verified_file_bytes": verified_bytes, "groups": dict(inventory),
        "all_expected_git_blob_sha1_and_sha256_verified": not failures,
        "preexisting_files": unchanged, "git_check_ignore_exit_code": ignore.returncode,
        "gitignored_recovered_files": len(ignored),
        "prior_audit_csv_sha256": {"path": known_csv, "expected": known_hash,
                                    "actual": actual_known_hash, "match": actual_known_hash == known_hash},
        "failures": failures, "elapsed_seconds": round(time.perf_counter() - started, 3),
        "scope": "Exhaustive fresh installed-byte, Gitignore and preservation verification; no Gold build or semantic data-quality validation."
    }
    with (EVIDENCE / "restore-verification.json").open("w", encoding="utf-8", newline="\n") as target:
        json.dump(result, target, ensure_ascii=True, indent=2)
        target.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"groups", "preexisting_files", "failures"}}, indent=2), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
