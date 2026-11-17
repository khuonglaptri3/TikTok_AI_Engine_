from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from packages.data_contracts.corpus import CorpusManifest
from packages.retrieval import BM25Index
from pipelines.benchmark_retrieval.__main__ import main


def test_historical_v1_preserves_recorded_rank_and_latency_regression() -> None:
    """Historical weak labels retain rank checks; its capped recall is not standard recall."""
    report_path = Path("artifacts/benchmarks/retrieval_v1.json")
    assert report_path.is_file(), "Benchmark report must exist; run pipelines.benchmark_retrieval"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["indexed_videos"] == 21748

    reranked = report["configurations"]["bm25_viral_boost_reranked"]
    assert reranked["query_count"] >= 15
    assert reranked["mrr_at_10"] >= 0.50
    assert reranked["ndcg_at_10"] >= 0.35
    assert reranked["p95_latency_ms"] <= 2000.0


@pytest.fixture
def benchmark_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    videos = pd.DataFrame(
        [{"video_id": "v1", "caption": "noodle", "transcript": "noodle", "has_transcript": True}]
    )
    creators = pd.DataFrame([{"author_handle": "fixture"}])
    videos.to_parquet(corpus_dir / "fact_videos.parquet", index=False)
    creators.to_parquet(corpus_dir / "dim_creators.parquet", index=False)
    manifest = CorpusManifest(
        snapshot_id="fixture-v2",
        created_at="2026-11-17T00:00:00Z",
        date_window_start="2023-11-01",
        date_window_end="2025-03-31",
        total_creators=1,
        total_videos=1,
        transcribed_videos=1,
        poi_tagged_videos=0,
        ec_tagged_videos=0,
        files=[
            {
                "filename": name,
                "rows": 1,
                "columns": columns,
                "size_bytes": (corpus_dir / name).stat().st_size,
                "sha256": hashlib.sha256((corpus_dir / name).read_bytes()).hexdigest(),
            }
            for name, columns in [("dim_creators.parquet", 1), ("fact_videos.parquet", 4)]
        ],
        caveats=["Controlled fixture, not a relevance-quality measurement."],
    )
    (corpus_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    index_dir = tmp_path / "index"
    BM25Index.build(["v1"], ["noodle"]).save(index_dir, corpus_snapshot_id="fixture-v2")
    queries = tmp_path / "queries.jsonl"
    queries.write_text(
        json.dumps({"query_id": "q1", "query": "noodle", "relevant_video_ids": ["v1", "v2"]}) + "\n",
        encoding="utf-8",
    )
    return corpus_dir, index_dir, queries


def test_versioned_report_binds_correct_metrics_to_inputs(
    benchmark_inputs: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus, index, queries = benchmark_inputs
    output = tmp_path / "retrieval_v2.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "benchmark", "--corpus", str(corpus), "--index", str(index), "--queries", str(queries),
            "--benchmark-id", "retrieval_v2", "--output", str(output),
        ],
    )
    main()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["benchmark_id"] == "retrieval_v2"
    assert report["metric_schema_version"] == 2
    assert report["evaluation"]["independent_relevance_judgments"] is False
    assert report["evaluation"]["label_source"] == "lexical_metadata_weak_labels"
    assert report["evaluation"]["relevant_video_counts"] == {"q1": 2}
    metrics = report["configurations"]["bm25_viral_boost_reranked"]
    assert metrics["recall_at_10"] == 0.5
    assert metrics["precision_at_10"] == 0.1
    provenance = report["provenance"]
    assert provenance["queries_sha256"] == hashlib.sha256(queries.read_bytes()).hexdigest()
    assert provenance["corpus_manifest_sha256"] == hashlib.sha256((corpus / "manifest.json").read_bytes()).hexdigest()
    assert provenance["index_files_sha256"]["bm25-receipt.json"] == hashlib.sha256((index / "bm25-receipt.json").read_bytes()).hexdigest()
    assert provenance["code_files_sha256"]["pipelines/benchmark_retrieval/__main__.py"] == hashlib.sha256(Path("pipelines/benchmark_retrieval/__main__.py").read_bytes()).hexdigest()
    before = output.read_bytes()
    # A repeated invocation cannot erase an existing measurement receipt.
    with pytest.raises(FileExistsError):
        main()
    assert output.read_bytes() == before


def test_report_rejects_index_receipt_for_a_different_corpus(
    benchmark_inputs: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus, index, queries = benchmark_inputs
    receipt_path = index / "bm25-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["corpus_snapshot_id"] = "wrong-corpus"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    output = tmp_path / "mismatched.json"
    monkeypatch.setattr(
        "sys.argv",
        ["benchmark", "--corpus", str(corpus), "--index", str(index), "--queries", str(queries), "--output", str(output)],
    )
    with pytest.raises(ValueError, match="snapshot"):
        main()
    assert not output.exists()
