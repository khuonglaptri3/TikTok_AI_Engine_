"""Verify real Git byte preservation and the explicit publication scope."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[4]
RECOVERY = ROOT / "docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence"


def git(*args: str, payload: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", *args], input=payload, cwd=ROOT)


def bindings() -> dict[str, str]:
    result = json.loads((RECOVERY / "final-sha256.json").read_text(encoding="utf-8"))
    benchmark = json.loads((ROOT / "artifacts/benchmarks/retrieval_v2.json").read_text(encoding="utf-8"))
    result.update(benchmark["provenance"]["code_files_sha256"])
    for item in json.loads((RECOVERY / "restore-existing-before.json").read_text(encoding="utf-8"))["files"]:
        result[item["path"]] = item["sha256"]
    return result


def git_bound_paths() -> list[str]:
    names = list(bindings())
    probe = subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=ROOT,
                           input=("\0".join(names) + "\0").encode(), capture_output=True)
    assert probe.returncode in (0, 1)
    ignored = {item.decode() for item in probe.stdout.split(b"\0") if item}
    return sorted(set(names) - ignored)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["before", "after", "staged"], required=True)
    args = parser.parse_args()
    failures, rows = [], []
    immutable = bindings()
    # New navigation is a new task change; old global manifests remain dated
    # observations. All unchanged source/evidence bindings must still match.
    mutable = {"README.md", "docs/reports/tasks/README.md"}
    for name, expected in immutable.items():
        if name not in mutable:
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    if args.phase != "staged":
        for name in git_bound_paths():
            raw = (ROOT / name).read_bytes()
            raw_oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            filtered = git("hash-object", "--path=" + name, "--stdin", payload=raw).decode().strip()
            row = {"path": name, "raw_git_blob": raw_oid, "filtered_git_blob": filtered,
                   "byte_identical": filtered == raw_oid}
            rows.append(row)
            if filtered != raw_oid:
                failures.append(name)
        output = EVIDENCE / f"byte-filter-{args.phase}.json"
    else:
        names = [name.decode() for name in git("diff", "--cached", "--name-only", "-z").split(b"\0") if name]
        assert names, "Nothing staged for publication"
        # This receipt cannot hash itself; the Git tree binds its final bytes.
        self_path = (EVIDENCE / "staged-files.json").relative_to(ROOT).as_posix()
        names = [name for name in names if name != self_path]
        oids = [git("rev-parse", ":" + name).decode().strip() for name in names]
        packed = io.BytesIO(git("cat-file", "--batch", payload=("\n".join(oids) + "\n").encode()))
        for name in names:
            oid, kind, size = packed.readline().decode().strip().split()
            assert kind == "blob"
            stored = packed.read(int(size))
            assert packed.read(1) == b"\n"
            raw = (ROOT / name).read_bytes()
            assert stored == raw, f"Git staged bytes differ: {name}"
            assert len(raw) <= 50 * 1024 * 1024, f"Exceeds task's 50 MiB publication cap: {name}"
            assert Path(name).suffix.lower() not in {".parquet", ".npz"}, name
            assert ((Path(name).name != ".env" and not Path(name).name.startswith(".env."))
                    or Path(name).name == ".env.example"), name
            assert not name.startswith(("data/raw/", "data/interim/", "data/processed/", "data/transcripts/", "data/raw_incremental/", "artifacts/indexes/")), name
            if name.startswith("data/"):
                assert name in {"data/corpus/20261116_v1/manifest.json",
                                "data/corpus/20261117_recovered_v1/manifest.json",
                                "data/evaluation/v1/queries.jsonl"}, name
            rows.append({"path": name, "bytes": len(raw), "git_blob": oid,
                         "sha256": hashlib.sha256(raw).hexdigest()})
        output = EVIDENCE / "staged-files.json"
    result = {"status": "PASS" if not failures else "FAIL", "phase": args.phase,
              "checked_files": len(rows), "failures": failures, "files": rows,
              "scope": "Exact Git clean-filter/staged byte preservation and immutable recovery bindings; staged manifest excludes itself. Raw data/runtime binaries/secrets excluded by explicit publication checks."}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "phase", "checked_files", "failures")}))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
