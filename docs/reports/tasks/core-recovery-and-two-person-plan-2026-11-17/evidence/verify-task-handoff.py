"""Validate current task structure, authored links, review index and final hashes."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

EVIDENCE = Path(__file__).resolve().parent
TASK = EVIDENCE.parent
ROOT = EVIDENCE.parents[4]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    assert {p.name for p in TASK.iterdir()} == {"README.md", "evidence", "superpowers"}
    assert {p.name for p in (TASK / "superpowers").iterdir()} == {"spec.md", "plan.md"}
    report = (TASK / "README.md").read_text(encoding="utf-8")
    status = re.search(r"^- Status: (IN_PROGRESS|COMPLETE)$", report, re.M).group(1)
    assert "superpowers/spec.md" in report and "superpowers/plan.md" in report
    assert "evidence/workflow.md" in report
    index = (ROOT / "docs/reports/tasks/README.md").read_text(encoding="utf-8")
    rows = [line for line in index.splitlines() if line.startswith(f"| {TASK.name} |")]
    assert len(rows) == 1 and f"| {status} |" in rows[0]
    authored = [TASK / "README.md", TASK / "superpowers/spec.md", TASK / "superpowers/plan.md",
                EVIDENCE / "workflow.md", EVIDENCE / "restore-review.md", ROOT / "README.md",
                ROOT / "docs/reports/tasks/README.md", ROOT / "docs/reports/milestones/README.md"]
    broken, count, destinations = [], 0, []
    generated = {EVIDENCE / "handoff-verification.json", EVIDENCE / "final-sha256.json"}
    for path in authored:
        text = re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[ \t]*$", "", path.read_text(encoding="utf-8"))
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0]).strip("<>")
            if relative:
                count += 1
                destination = (path.parent / relative).resolve()
                destinations.append(destination)
                if not destination.exists() and destination not in generated:
                    broken.append({"file": path.relative_to(ROOT).as_posix(), "target": target})
    assert not broken, broken
    # The original archive receipts remain fixed historical records. This manifest
    # describes final bytes, including any later review-driven corrections.
    candidates = [p for p in TASK.rglob("*") if p.is_file() and p.name not in {
        "handoff-verification.json", "final-sha256.json",
    } and "__pycache__" not in p.parts]
    # Include all source paths from the integration receipt and current planning files.
    names = [item["path"] for item in json.loads((EVIDENCE / "integration-manifest.json").read_text(encoding="utf-8"))["files"]]
    names += ["README.md", "AGENTS.md", "docs/planning/TikTok_AI_Engine_Milestone.md",
              "docs/planning/TikTok_AI_Engine_Resources_and_Deployment.md", "ReFactor_structure/04_IMPLEMENTATION_PLAN.md",
              "docs/reports/tasks/README.md", "docs/reports/milestones/README.md",
              "artifacts/benchmarks/retrieval_v1.json", "artifacts/benchmarks/retrieval_v2.json"]
    names += ["data/corpus/20261117_recovered_v1/" + name for name in (
        "manifest.json", "dim_creators.parquet", "fact_videos.parquet",
    )]
    names += ["artifacts/indexes/bm25-v2/" + name for name in (
        "bm25-receipt.json", "video_ids.json", "vocab.json", "bm25_csr.npz",
    )]
    names.append("data/evaluation/v1/queries.jsonl")
    assert sha(ROOT / "artifacts/benchmarks/retrieval_v1.json") == "33c523d528aff22970c40f7bf253e88617a39d901a0ba6e687f0776a9da6b22c"
    benchmark = json.loads((ROOT / "artifacts/benchmarks/retrieval_v2.json").read_text(encoding="utf-8"))
    provenance = benchmark["provenance"]
    assert provenance["corpus_manifest_sha256"] == sha(ROOT / "data/corpus/20261117_recovered_v1/manifest.json")
    assert provenance["queries_sha256"] == sha(ROOT / "data/evaluation/v1/queries.jsonl")
    for group, parent in (("code_files_sha256", ROOT),
                          ("index_files_sha256", ROOT / "artifacts/indexes/bm25-v2"),
                          ("corpus_files_sha256", ROOT / "data/corpus/20261117_recovered_v1")):
        assert all(sha(parent / name) == value for name, value in provenance[group].items())
    candidates += [ROOT / name for name in names]
    manifest = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(candidates))}
    (EVIDENCE / "final-sha256.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert all(sha(ROOT / name) == value for name, value in manifest.items())
    result = {"status": "PASS", "task_status": status, "canonical_layout": True, "current_report_index_agree": True,
              "authored_local_links_checked": count, "broken_links": broken,
              "hashed_files": len(manifest), "all_recorded_hashes_rechecked": True,
              "benchmark_provenance_rechecked": True, "historical_benchmark_preserved": True,
              "hash_manifest_sha256": sha(EVIDENCE / "final-sha256.json"),
              "scope": "Canonical bundle, current authored links/index and final byte hashes; original archived evidence remains historical. Manifest and this result exclude their own mutable bytes."}
    (EVIDENCE / "handoff-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    assert all(path.exists() for path in destinations)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
