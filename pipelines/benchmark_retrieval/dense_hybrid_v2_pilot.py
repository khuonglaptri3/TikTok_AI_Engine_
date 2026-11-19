"""M6.1 CPU dense & hybrid_rrf parity benchmark on v2_pilot (dev + locked_test)."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib
from packages.retrieval import HybridRetrievalService
from pipelines.benchmark_retrieval.pilot_m2_2 import (
    _load_jsonl,
    _load_qrels,
    _sha256_file,
    evaluate_pilot_split,
    measure_warm_latency,
    paired_bootstrap_ci,
)

RetrievalMode = Literal["bm25", "dense", "hybrid_rrf"]

CONFIGS: tuple[tuple[str, RetrievalMode, bool], ...] = (
    ("bm25", "bm25", False),
    ("bm25_reranked", "bm25", True),
    ("dense", "dense", False),
    ("dense_reranked", "dense", True),
    ("hybrid_rrf", "hybrid_rrf", False),
    ("hybrid_rrf_reranked", "hybrid_rrf", True),
)

PAIRED_CONTRASTS: tuple[tuple[str, str, str], ...] = (
    ("dense_minus_bm25", "dense", "bm25"),
    ("hybrid_rrf_minus_bm25", "hybrid_rrf", "bm25"),
    ("dense_reranked_minus_bm25_reranked", "dense_reranked", "bm25_reranked"),
    ("hybrid_rrf_reranked_minus_bm25_reranked", "hybrid_rrf_reranked", "bm25_reranked"),
    ("bm25_reranked_minus_bm25", "bm25_reranked", "bm25"),
)


def _compare_pair(
    cand: dict[str, Any],
    base: dict[str, Any],
    *,
    k: int = 10,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for metric in (
        f"mrr_at_{k}",
        f"ndcg_at_{k}",
        f"pooled_recall_at_{k}",
        f"precision_at_{k}",
        f"mrr_at_{k}_all_answerable",
        f"ndcg_at_{k}_all_answerable",
    ):
        # pilot_m2_2.paired_bootstrap_ci returns mean(vals_b - vals_a), so pass base as A and cand as B.
        va = cand["vectors"][metric]
        vb = base["vectors"][metric]
        if len(va) == len(vb) and va:
            out[metric] = paired_bootstrap_ci(vb, va, n_boot=n_boot, seed=seed)
    return out


def benchmark_dense_backend(
    *,
    df_videos: pd.DataFrame,
    bm25_dir: Path,
    dense_dir: Path,
    dev_queries: list[dict[str, Any]],
    test_queries: list[dict[str, Any]],
    qrels: dict[str, dict[str, str]],
    n_warm: int = 100,
    n_boot: int = 1000,
    k: int = 10,
) -> dict[str, Any]:
    """Run exact <=5,000-doc parity, paired CIs, and warm CPU latency for one dense index."""
    receipt = json.loads((dense_dir / "dense-receipt.json").read_text(encoding="utf-8"))
    video_ids = json.loads((dense_dir / "video_ids.json").read_text(encoding="utf-8"))
    if len(video_ids) > 5000:
        raise ValueError(f"M6.1 caps dense index at <= 5,000 records, got {len(video_ids)}")

    eligible_ids = {str(vid) for vid in video_ids}
    df_parity = df_videos[df_videos["video_id"].astype(str).isin(eligible_ids)].copy()
    if len(df_parity) != len(eligible_ids):
        raise ValueError(
            f"Corpus parity slice mismatch: expected {len(eligible_ids)}, matched {len(df_parity)}"
        )

    service = HybridRetrievalService.from_dirs(
        df_videos=df_parity,
        bm25_dir=bm25_dir,
        dense_dir=dense_dir,
    )

    splits_out: dict[str, Any] = {}
    for split_name, split_queries in (("dev", dev_queries), ("locked_test", test_queries)):
        configs_res: dict[str, dict[str, Any]] = {}
        for cfg_name, mode, rerank in CONFIGS:
            configs_res[cfg_name] = evaluate_pilot_split(
                service,
                split_queries,
                qrels,
                mode=mode,
                rerank=rerank,
                k=k,
                eligible_video_ids=eligible_ids,
            )

        comparisons = {
            cmp_name: _compare_pair(
                configs_res[cand_name],
                configs_res[base_name],
                k=k,
                n_boot=n_boot,
            )
            for cmp_name, cand_name, base_name in PAIRED_CONTRASTS
        }

        for bundle in configs_res.values():
            bundle.pop("vectors", None)

        splits_out[split_name] = {
            "configs": configs_res,
            "paired_bootstrap_comparisons": comparisons,
        }

    latency_queries = test_queries if test_queries else dev_queries
    latency_out = {
        cfg_name: measure_warm_latency(
            service,
            latency_queries,
            mode=mode,
            rerank=rerank,
            n_warm=n_warm,
            k=k,
        )
        for cfg_name, mode, rerank in CONFIGS
    }

    return {
        "dense_dir": str(dense_dir),
        "dense_receipt": receipt,
        "parity_slice_doc_count": len(eligible_ids),
        "splits": splits_out,
        "latency_warm_requests": latency_out,
    }


def _evaluate_full_corpus_bm25(
    *,
    df_videos: pd.DataFrame,
    bm25_dir: Path,
    dev_queries: list[dict[str, Any]],
    test_queries: list[dict[str, Any]],
    qrels: dict[str, dict[str, str]],
    k: int = 10,
) -> dict[str, Any]:
    service = HybridRetrievalService.from_dirs(df_videos=df_videos, bm25_dir=bm25_dir)
    out: dict[str, Any] = {}
    for split_name, split_queries in (("dev", dev_queries), ("locked_test", test_queries)):
        bm25_res = evaluate_pilot_split(service, split_queries, qrels, mode="bm25", rerank=False, k=k)
        rerank_res = evaluate_pilot_split(service, split_queries, qrels, mode="bm25", rerank=True, k=k)
        bm25_res.pop("vectors", None)
        rerank_res.pop("vectors", None)
        out[split_name] = {"bm25": bm25_res, "bm25_reranked": rerank_res}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run M6.1 dense & hybrid_rrf parity benchmark on v2_pilot."
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261118_taxonomy_fix_v1"))
    parser.add_argument("--bm25", type=Path, default=Path("artifacts/indexes/bm25-v3"))
    parser.add_argument(
        "--dense-dirs",
        type=Path,
        nargs="+",
        required=True,
        help="One or more populated <=5,000-record dense index directories to benchmark",
    )
    parser.add_argument(
        "--dev-queries", type=Path, default=Path("data/evaluation/v2_pilot/dev_queries.jsonl")
    )
    parser.add_argument(
        "--test-queries", type=Path, default=Path("data/evaluation/v2_pilot/test_queries.jsonl")
    )
    parser.add_argument(
        "--qrels", type=Path, default=Path("data/evaluation/v2_pilot/qrels_pooled_draft.jsonl")
    )
    parser.add_argument("--n-warm", type=int, default=100)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--benchmark-id", default="m6_1_v2_pilot")
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/benchmarks/m6_1_v2_pilot.json")
    )
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Benchmark receipt already exists: {args.output}")

    manifest, _, df_videos = load_verified_corpus(args.corpus)
    bm25_receipt = json.loads((args.bm25 / "bm25-receipt.json").read_text(encoding="utf-8"))
    if bm25_receipt.get("corpus_snapshot_id") != manifest.snapshot_id:
        raise ValueError("BM25 index receipt snapshot ID does not match verified corpus snapshot ID")

    for d_dir in args.dense_dirs:
        d_receipt = json.loads((d_dir / "dense-receipt.json").read_text(encoding="utf-8"))
        if d_receipt.get("corpus_snapshot_id") != manifest.snapshot_id:
            raise ValueError(
                f"Dense index snapshot ID mismatch for {d_dir}: "
                f"{d_receipt.get('corpus_snapshot_id')} != {manifest.snapshot_id}"
            )

    dev_queries = _load_jsonl(args.dev_queries)
    test_queries = _load_jsonl(args.test_queries)
    qrels, qrels_meta = _load_qrels(args.qrels)

    dev_texts = {q["query"].strip().lower() for q in dev_queries}
    test_texts = {q["query"].strip().lower() for q in test_queries}
    if dev_texts & test_texts:
        raise ValueError("dev_queries and test_queries must be strictly disjoint")

    full_ref = _evaluate_full_corpus_bm25(
        df_videos=df_videos,
        bm25_dir=args.bm25,
        dev_queries=dev_queries,
        test_queries=test_queries,
        qrels=qrels,
        k=10,
    )

    backend_results: dict[str, Any] = {}
    for d_dir in args.dense_dirs:
        res = benchmark_dense_backend(
            df_videos=df_videos,
            bm25_dir=args.bm25,
            dense_dir=d_dir,
            dev_queries=dev_queries,
            test_queries=test_queries,
            qrels=qrels,
            n_warm=args.n_warm,
            n_boot=args.n_boot,
            k=10,
        )
        backend_results[d_dir.name] = res

    repo_root = Path(__file__).resolve().parents[2]
    report = {
        "benchmark_id": args.benchmark_id,
        "metric_schema_version": 4,
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "full_corpus_eligible_videos": int(df_videos["has_transcript"].sum()),
        "evaluation": {
            "label_source": (
                "two_human_verified_pooled_judgments"
                if qrels_meta["human_signoff_complete"]
                else "ai_assisted_pooled_draft_pending_human_K_N_signoff"
            ),
            "independent_two_human_signoff_complete": qrels_meta["human_signoff_complete"],
            "parity_note": (
                "Each backend comparison restricts bm25, dense, and hybrid_rrf to the exact populated "
                "<=5,000-record dense slice via restrict_to_df=True and scopes qrels positives to that slice."
            ),
            "qrels_completeness": qrels_meta,
            "m6_1_resource_limits": {
                "max_dense_records": 5000,
                "warm_cpu_p95_ms_max": 1000.0,
                "peak_rss_mib_max": 8192.0,
            },
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(args.corpus / "manifest.json"),
            "dev_queries_sha256": _sha256_file(args.dev_queries),
            "test_queries_sha256": _sha256_file(args.test_queries),
            "qrels_sha256": _sha256_file(args.qrels),
            "bm25_receipt": bm25_receipt,
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "pipelines/benchmark_retrieval/dense_hybrid_v2_pilot.py",
                    "pipelines/benchmark_retrieval/pilot_m2_2.py",
                    "packages/retrieval/service.py",
                    "packages/retrieval/dense/encoder.py",
                    "packages/retrieval/dense/local_index.py",
                )
            },
        },
        "full_corpus_bm25_reference": full_ref,
        "backends": backend_results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: wrote {args.output} ({len(backend_results)} dense backend(s))")


if __name__ == "__main__":
    main()
