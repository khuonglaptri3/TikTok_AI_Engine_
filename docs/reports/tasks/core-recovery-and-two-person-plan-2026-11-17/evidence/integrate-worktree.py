"""Copy the resumed task's source changes after rejecting local conflicts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[4]
WORKTREE = Path("C:/Users/lanph/.codex/worktrees/bf1f/TikTok_AI_Engine_")


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    changed = git(WORKTREE, "diff", "--name-only", "-z").decode().split("\0")
    added = git(WORKTREE, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    paths = sorted({name for name in changed + added if name})
    records = []
    for name in paths:
        source, target = WORKTREE / name, ROOT / name
        if not target.resolve().is_relative_to(ROOT.resolve()) or not source.is_file():
            raise RuntimeError(f"Unsafe/missing integration path: {name}")
        tracked = bool(git(ROOT, "ls-files", "--", name).strip())
        if tracked:
            if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", name]).returncode:
                raise RuntimeError(f"Local tracked edit requires reconciliation: {name}")
        elif target.exists():
            raise RuntimeError(f"Local untracked destination already exists: {name}")
        records.append({"path": name, "before_sha256": sha(target) if target.exists() else None,
                        "worktree_sha256": sha(source)})
    (EVIDENCE / "integrated-source.diff").write_bytes(git(WORKTREE, "diff", "--binary"))
    for record in records:
        name = record["path"]
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORKTREE / name, target)
        record["integrated_sha256"] = sha(target)
        assert record["integrated_sha256"] == record["worktree_sha256"]
    (EVIDENCE / "integration-manifest.json").write_text(json.dumps({
        "baseline": git(ROOT, "rev-parse", "HEAD").decode().strip(),
        "scope": "Source-only integration; existing documentation and data retained; no commit or branch mutation.",
        "files": records,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"integrated_files": len(records), "all_source_hashes_match": True}))


if __name__ == "__main__":
    main()
