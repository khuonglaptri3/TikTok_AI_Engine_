"""Restore pinned historical inputs only; never run downloaded upstream code.

Run with --download to cache the archive and --restore to verify/install selected
data. The archive stays outside the repository so reconnects can reuse it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import time
from datetime import datetime, timezone
import urllib.request
import zipfile


REVISION = "f142e5656a220f94f8024de168b0832754b3bd9e"
REPOSITORY = "TrggTin/21KHDL-TikTok-Analytics"
ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parent
DATA_ROOT = (ROOT / "data").resolve()
PARENT_RESOLUTIONS: dict[Path, Path] = {}
CACHE = Path(tempfile.gettempdir()) / f"tiktok-core-recovery-{REVISION}"
ARCHIVE = CACHE / "upstream.zip"
ARCHIVE_URL = f"https://codeload.github.com/{REPOSITORY}/zip/{REVISION}"
TREE_URL = f"https://api.github.com/repos/{REPOSITORY}/git/trees/{REVISION}?recursive=1"
PREFIX = f"21KHDL-TikTok-Analytics-{REVISION}/"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(name: str, data: object) -> None:
    target = EVIDENCE / f"restore-{name}.json"
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=True, indent=2)
        stream.write("\n")


def progress(event: str, **details: object) -> None:
    record = {"at": now(), "event": event, **details}
    print(json.dumps(record, ensure_ascii=True), flush=True)
    with (EVIDENCE / "restore-progress.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def destination_hashes(path: Path) -> tuple[str, str]:
    blob = hashlib.sha1(f"blob {path.stat().st_size}\0".encode("ascii"))
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            blob.update(chunk)
            sha256.update(chunk)
    return blob.hexdigest(), sha256.hexdigest()


def tree() -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / "tree.json"
    if target.is_file():
        data = json.loads(target.read_text(encoding="utf-8"))
    else:
        request = urllib.request.Request(TREE_URL, headers={"User-Agent": "Codex-local-data-restoration"})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.load(response)
        target.write_text(json.dumps(data), encoding="utf-8")
    if data.get("truncated"):
        raise RuntimeError("Refusing an incomplete Git source tree")
    return data


def destination(source: str) -> str | None:
    if source.startswith("data/"):
        return source
    parts = PurePosixPath(source).parts
    if len(parts) >= 5 and parts[:2] == ("src", "app") and parts[3] == "data":
        if PurePosixPath(source).suffix.lower() in {".csv", ".parquet", ".json", ".jsonl", ".xlsx", ".feather"}:
            return str(PurePosixPath("data", "legacy_app_data", parts[2], *parts[4:]))
    return None


def selected(data: dict) -> list[dict]:
    records = []
    for item in data["tree"]:
        if item["type"] != "blob":
            continue
        dest = destination(item["path"])
        if dest is not None:
            if item["mode"] != "100644":
                raise RuntimeError("Unexpected source mode for selected data")
            records.append({"source_path": item["path"], "destination_path": dest,
                            "expected_git_blob_sha1": item["sha"], "expected_bytes": item["size"]})
    return sorted(records, key=lambda item: item["source_path"])


def fetch_archive() -> None:
    if ARCHIVE.is_file():
        progress("archive_cache_reused", archive=str(ARCHIVE), bytes=ARCHIVE.stat().st_size)
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    partial = ARCHIVE.with_suffix(".zip.part")
    offset = partial.stat().st_size if partial.is_file() else 0
    headers = {"User-Agent": "Codex-local-data-restoration"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(ARCHIVE_URL, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        if offset and response.status != 206:
            progress("archive_resume_unsupported_restart", discarded_partial_bytes=offset)
            offset = 0
        expected = response.headers.get("Content-Length")
        progress("download_started", archive=str(ARCHIVE), resume_bytes=offset,
                 remaining_http_content_length=int(expected) if expected else None)
        total = offset
        checkpoint = total
        start = time.monotonic()
        with partial.open("ab" if offset else "wb") as stream:
            while chunk := response.read(4 * 1024 * 1024):
                stream.write(chunk)
                total += len(chunk)
                if total - checkpoint >= 32 * 1024 * 1024:
                    progress("download_progress", bytes=total, elapsed_seconds=round(time.monotonic() - start, 2))
                    checkpoint = total
        if expected and total != offset + int(expected):
            raise RuntimeError("Incomplete HTTP archive response")
    with zipfile.ZipFile(partial) as archive:
        count = len(archive.infolist())
    partial.rename(ARCHIVE)
    record_archive(count)


def record_archive(count: int | None = None) -> None:
    if count is None:
        with zipfile.ZipFile(ARCHIVE) as archive:
            count = len(archive.infolist())
    archive_hash = sha256_file(ARCHIVE)
    save("archive", {"recorded_at": now(),
                     "archive_file_modified_at": datetime.fromtimestamp(ARCHIVE.stat().st_mtime, timezone.utc).isoformat(),
                     "repository": REPOSITORY, "revision": REVISION,
                     "source_url": ARCHIVE_URL, "cache_path": str(ARCHIVE),
                     "bytes": ARCHIVE.stat().st_size, "sha256": archive_hash, "zip_entries": count})
    progress("download_complete", bytes=ARCHIVE.stat().st_size, sha256=archive_hash, zip_entries=count)


def checked_destination(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or pure.parts[0] != "data":
        raise RuntimeError("Destination is not inside the data directory")
    if any(part in {"", ".", ".."} or ":" in part or "\\" in part for part in pure.parts):
        raise RuntimeError("Unsafe destination path")
    target = ROOT.joinpath(*pure.parts)
    # Only 224 selected parent directories exist in the pinned source. Resolve
    # each parent once rather than issuing tens of thousands of repeated Windows
    # filesystem lookups for absent leaf files. This worker is the sole writer
    # of the restored directories; existing leaf symlinks are rejected outright.
    parent = target.parent
    if parent not in PARENT_RESOLUTIONS:
        PARENT_RESOLUTIONS[parent] = parent.resolve()
    resolved = PARENT_RESOLUTIONS[parent] / target.name
    if not resolved.is_relative_to(DATA_ROOT):
        raise RuntimeError("Resolved destination escapes the data directory")
    if target.is_symlink():
        raise RuntimeError("Refusing a symbolic-link destination")
    if target.exists() and not target.is_file():
        raise RuntimeError("A selected destination exists and is not a file")
    return target


def restore(data: dict, entries: list[dict]) -> None:
    if not ARCHIVE.is_file():
        raise RuntimeError("Download the pinned archive before restoration")
    existing = [{"path": item.relative_to(ROOT).as_posix(), "bytes": item.stat().st_size,
                 "sha256": sha256_file(item)} for item in sorted((ROOT / "data").rglob("*")) if item.is_file()]
    # Retain the original pre-restoration inventory across interrupted resumes.
    baseline = EVIDENCE / "restore-existing-before.json"
    save("resume-existing-before" if baseline.is_file() else "existing-before", {"at": now(), "files": existing})
    records = []
    started = now()
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = archive.infolist()
        by_name = {}
        for info in members:
            if info.filename in by_name:
                raise RuntimeError("Duplicate ZIP member")
            by_name[info.filename] = info
        targets = set()
        for entry in entries:
            path = checked_destination(entry["destination_path"])
            target_key = str(path.resolve()).casefold()
            if target_key in targets:
                raise RuntimeError("Case-insensitive destination collision")
            targets.add(target_key)
            member = PREFIX + entry["source_path"]
            if member not in by_name:
                raise RuntimeError("Expected selected source missing from ZIP")
            info = by_name[member]
            if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                raise RuntimeError("Unexpected directory or symlink source")
            if info.file_size != entry["expected_bytes"]:
                raise RuntimeError("Git tree and ZIP file size disagree")
        progress("restore_started", expected_files=len(entries), expected_bytes=sum(x["expected_bytes"] for x in entries),
                 existing_files=len(existing))
        for index, entry in enumerate(entries, start=1):
            path = checked_destination(entry["destination_path"])
            source_sha1 = hashlib.sha1(f"blob {entry['expected_bytes']}\0".encode("ascii"))
            source_sha256 = hashlib.sha256()
            payload = archive.read(PREFIX + entry["source_path"])
            source_sha1.update(payload)
            source_sha256.update(payload)
            actual_git_sha1 = source_sha1.hexdigest()
            if actual_git_sha1 != entry["expected_git_blob_sha1"]:
                raise RuntimeError("Source archive Git blob checksum mismatch")
            expected_sha256 = source_sha256.hexdigest()
            status = "CREATED"
            if path.exists():
                if sha256_file(path) != expected_sha256:
                    raise RuntimeError("Refusing to overwrite a differing existing destination")
                status = "PRESERVED_IDENTICAL"
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation ensures even a concurrent destination is never overwritten.
                with path.open("xb") as output:
                    output.write(payload)
            installed_blob_sha1, installed_sha256 = destination_hashes(path)
            if installed_blob_sha1 != entry["expected_git_blob_sha1"] or installed_sha256 != expected_sha256 or path.stat().st_size != entry["expected_bytes"]:
                raise RuntimeError("Restored destination checksum mismatch")
            records.append({**entry, "actual_git_blob_sha1": actual_git_sha1,
                            "expected_sha256_from_verified_archive": expected_sha256,
                            "actual_destination_sha256": installed_sha256,
                            "actual_destination_git_blob_sha1": installed_blob_sha1,
                            "actual_bytes": path.stat().st_size, "status": status,
                            "git_blob_sha1_match": True, "sha256_match": True})
            if index % 2000 == 0:
                progress("restore_progress", files=index, expected_files=len(entries))
        after_existing = []
        for original in existing:
            current_hash = sha256_file(ROOT / original["path"])
            after_existing.append({**original, "sha256_after": current_hash, "unchanged": current_hash == original["sha256"]})
        if not all(item["unchanged"] for item in after_existing):
            raise RuntimeError("An original local data file changed during recovery")
    groups = {}
    for item in records:
        group = item["destination_path"].split("/")[1]
        current = groups.setdefault(group, {"files": 0, "bytes": 0})
        current["files"] += 1
        current["bytes"] += item["actual_bytes"]
    summary = {"status": "PASS", "started_at": started, "completed_at": now(),
               "repository": REPOSITORY, "revision": REVISION, "tree_sha": data["sha"],
               "tree_truncated": False, "recovered_files": len(records),
               "recovered_bytes": sum(item["actual_bytes"] for item in records),
               "upstream_data_files": sum(item["source_path"].startswith("data/") for item in records),
               "upstream_data_bytes": sum(item["actual_bytes"] for item in records if item["source_path"].startswith("data/")),
               "legacy_app_files": sum(item["source_path"].startswith("src/app/") for item in records),
               "groups": groups, "created_files": sum(item["status"] == "CREATED" for item in records),
               "preserved_identical_files": sum(item["status"] == "PRESERVED_IDENTICAL" for item in records),
               "all_git_blob_checks_pass": True, "all_sha256_checks_pass": True,
               "existing_files_preserved": after_existing,
               "limitations": ["Recovered inventory is pinned upstream content; it does not independently verify the owner's historical 37840-file claim.",
                               "SHA256 expectations are computed from archive bytes whose Git blob SHA1 matches the pinned tree; upstream does not publish a per-file SHA256 manifest.",
                               "No historical TikTok crawl, upstream code execution, Gold/index build, provider call, or paid operation was performed."]}
    save("input-manifest", {"repository": REPOSITORY, "revision": REVISION, "files": records})
    save("summary", summary)
    progress("restore_complete", files=summary["recovered_files"], bytes=summary["recovered_bytes"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--adopt-download", action="store_true",
                        help="Validate and adopt a completed cURL ZIP from the cache .part path")
    arguments = parser.parse_args()
    data = tree()
    entries = selected(data)
    save("source-tree", {"inventory_written_at": now(),
                         "source_tree_cache_modified_at": datetime.fromtimestamp((CACHE / "tree.json").stat().st_mtime, timezone.utc).isoformat(),
                         "repository": REPOSITORY, "revision": REVISION,
                         "tree_sha": data["sha"], "tree_truncated": False, "source_url": TREE_URL,
                         "files": entries})
    progress("source_tree_ready", selected_files=len(entries), selected_bytes=sum(x["expected_bytes"] for x in entries),
             data_files=sum(x["source_path"].startswith("data/") for x in entries))
    if arguments.download:
        fetch_archive()
    if arguments.adopt_download:
        if not ARCHIVE.is_file():
            partial = ARCHIVE.with_suffix(".zip.part")
            with zipfile.ZipFile(partial):
                pass
            partial.rename(ARCHIVE)
        record_archive()
    if arguments.restore:
        restore(data, entries)


if __name__ == "__main__":
    main()
