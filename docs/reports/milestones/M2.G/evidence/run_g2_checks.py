"""Asserting G2 historical core gate verification probe across G0, G1, M2.1-M2.3, and real-corpus ASGI /demo/."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.main import create_app  # noqa: E402
from packages.common.settings import AppSettings  # noqa: E402

OUT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dir_hashes(folder: Path) -> dict[str, str]:
    return {p.name: _sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}


async def _run_asgi_probe() -> dict[str, Any]:
    t_start = time.perf_counter()
    settings = AppSettings.from_env().model_copy(
        update={
            "gemini_api_key": "",
            "corpus_dir": ROOT / "data/corpus/20261118_taxonomy_fix_v1",
            "bm25_index_dir": ROOT / "artifacts/indexes/bm25-v3",
            "benchmark_report_path": ROOT / "artifacts/benchmarks/retrieval_v3_4_final_pilot.json",
        }
    )
    app = create_app(settings=settings, mount_demo=True)
    startup_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

    stages: dict[str, Any] = {"app_startup_ms": startup_ms}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health & readiness
        t0 = time.perf_counter()
        r_live = await client.get("/health/live")
        live_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_live.status_code == 200 and "X-Request-ID" in r_live.headers

        t0 = time.perf_counter()
        r_ready = await client.get("/health/ready")
        ready_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_ready.status_code == 200
        ready_body = r_ready.json()
        assert ready_body["status"] == "ready", ready_body
        assert ready_body["total_videos"] == 70996, ready_body
        assert ready_body["indexed_bm25_videos"] == 21748, ready_body
        stages["health"] = {
            "live_ms": live_ms,
            "ready_ms": ready_ms,
            "total_videos": ready_body["total_videos"],
            "indexed_bm25_videos": ready_body["indexed_bm25_videos"],
        }

        # 2. Modules & evaluation summary
        r_mod = await client.get("/api/v1/demo/modules")
        assert r_mod.status_code == 200
        assert len(r_mod.json()["taxonomy"]["video_formats"]) == 5

        t0 = time.perf_counter()
        r_eval = await client.get("/api/v1/evaluation/summary")
        eval_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_eval.status_code == 200
        eval_body = r_eval.json()
        assert eval_body["benchmark_id"] == "retrieval_v3_4_final_pilot", eval_body
        stages["evaluation_summary"] = {"latency_ms": eval_ms, "benchmark_id": eval_body["benchmark_id"]}

        # 3. Analytics Niche Micro-Benchmark
        t0 = time.perf_counter()
        r_bench = await client.post(
            "/api/v1/analytics/niche-benchmark",
            json={"video_format": "Review quán ăn", "city_norm": "hồ chí minh"},
        )
        bench_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_bench.status_code == 200
        bench_body = r_bench.json()
        assert bench_body["matched_videos"] > 500, bench_body
        assert bench_body["sparse_slice_abstained"] is False
        stages["analytics_niche_benchmark"] = {
            "http_ms": bench_ms,
            "reported_latency_ms": bench_body.get("latency_ms"),
            "matched_videos": bench_body["matched_videos"],
            "corpus_snapshot": bench_body.get("observation_snapshot"),
        }

        # 4. Retrieval Search (answerable + no-answer abstention)
        t0 = time.perf_counter()
        r_search = await client.post(
            "/api/v1/retrieval/search",
            json={"query": "bánh mì thịt nướng Sài Gòn", "mode": "hybrid_rrf", "top_k": 5, "rerank": True},
        )
        search_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_search.status_code == 200
        search_body = r_search.json()
        assert len(search_body["items"]) == 5
        assert search_body["insufficient_evidence"] is False

        t0 = time.perf_counter()
        r_noans = await client.post(
            "/api/v1/retrieval/search",
            json={"query": "review nhà hàng thịt lạc đà nướng tảng chuẩn Dubai", "mode": "bm25", "top_k": 5, "rerank": True},
        )
        noans_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_noans.status_code == 200
        noans_body = r_noans.json()
        assert noans_body["insufficient_evidence"] is True, noans_body
        assert len(noans_body["items"]) == 0, noans_body
        stages["retrieval"] = {
            "answerable_http_ms": search_ms,
            "answerable_timings_ms": search_body.get("timings_ms"),
            "answerable_items": len(search_body["items"]),
            "no_answer_http_ms": noans_ms,
            "no_answer_abstained": noans_body["insufficient_evidence"],
            "no_answer_reason": noans_body.get("abstain_reason"),
        }

        # 5. Grounded script generation (offline_grounded, 503 missing key, 422 OOD)
        t0 = time.perf_counter()
        r_script = await client.post(
            "/api/v1/script/generate",
            json={
                "brief": "Review phở bò tái lăn chuẩn vị Hà Nội buổi sáng giá dưới 60k",
                "target_duration_sec": 40,
                "top_k_evidence": 5,
                "generation_mode": "offline_grounded",
            },
        )
        script_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_script.status_code == 200
        sc_body = r_script.json()
        assert sc_body["guardrail"]["passed"] is True, sc_body["guardrail"]
        assert sc_body["draft_status"] == "creative_draft"
        assert len(sc_body["beats"]) == 4

        r_nokey = await client.post(
            "/api/v1/script/generate",
            json={"brief": "Review phở bò chuẩn vị Hà Nội buổi sáng", "generation_mode": "gemini_free"},
        )
        assert r_nokey.status_code == 503 and r_nokey.json()["code"] == "PROVIDER_KEY_MISSING"

        r_ood = await client.post(
            "/api/v1/script/generate",
            json={
                "brief": "Phân tích biểu đồ nến đầu tư chứng khoán và tiền ảo bitcoin",
                "generation_mode": "offline_grounded",
            },
        )
        assert r_ood.status_code == 422 and r_ood.json()["code"] == "UNSUPPORTED_DOMAIN"
        stages["script_generation"] = {
            "offline_http_ms": script_ms,
            "offline_reported_ms": sc_body.get("latency_ms"),
            "beats_count": len(sc_body["beats"]),
            "guardrail_passed": sc_body["guardrail"]["passed"],
            "missing_key_status": r_nokey.status_code,
            "ood_status": r_ood.status_code,
        }

        # 6. Mounted Gradio UI /demo/
        t0 = time.perf_counter()
        r_demo = await client.get("/demo/")
        demo_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        assert r_demo.status_code == 200
        assert "TikTok" in r_demo.text and len(r_demo.text) > 1000
        stages["gradio_demo_mount"] = {
            "status_code": r_demo.status_code,
            "http_ms": demo_ms,
            "html_bytes": len(r_demo.text.encode("utf-8")),
        }

    return stages


def main() -> int:
    t0 = time.perf_counter()
    snap_v2 = ROOT / "data/corpus/20261118_taxonomy_fix_v1"
    bm25_v3 = ROOT / "artifacts/indexes/bm25-v3"
    r_v1_path = ROOT / "artifacts/benchmarks/retrieval_v1.json"
    r_v2_path = ROOT / "artifacts/benchmarks/retrieval_v2.json"
    r_v3_4_path = ROOT / "artifacts/benchmarks/retrieval_v3_4_final_pilot.json"

    before_snap = _dir_hashes(snap_v2)
    before_bm25 = _dir_hashes(bm25_v3)
    before_bench = {p.name: _sha256(p) for p in (r_v1_path, r_v2_path, r_v3_4_path)}

    # 1. Verify prerequisite gates and M2.1-M2.3 completion in index and receipts
    g0_receipt = json.loads(
        (ROOT / "docs/reports/milestones/M0.G/evidence/owner-gate-decision-receipt.json").read_text(encoding="utf-8")
    )
    g1_receipt = json.loads(
        (ROOT / "docs/reports/milestones/M1.G/evidence/g1-gate-decision-receipt.json").read_text(encoding="utf-8")
    )
    assert g0_receipt["gate_id"] == "G0" and g0_receipt["decision"] == "PASS", g0_receipt
    assert g1_receipt["gate_id"] == "G1" and g1_receipt["decision"] == "PASS", g1_receipt

    index_text = (ROOT / "docs/reports/milestones/README.md").read_text(encoding="utf-8")
    for row_prefix in ("| M0.G |", "| M1.G |", "| M2.1 |", "| M2.2 |", "| M2.3 |"):
        matches = [line for line in index_text.splitlines() if line.startswith(row_prefix)]
        assert len(matches) == 1 and "| COMPLETE |" in matches[0], matches

    # Verify M2.1, M2.2, M2.3 review/signoff evidence presence
    assert (ROOT / "docs/reports/milestones/M2.1/evidence/khuong-peer-review.md").is_file()
    m2_1_repro = json.loads(
        (ROOT / "docs/reports/milestones/M2.1/evidence/khuong_m2_1_reproduction.json").read_text(encoding="utf-8")
    )
    m2_1_linux = json.loads(
        (ROOT / "docs/reports/milestones/M2.1/evidence/latency_benchmark_100.json").read_text(encoding="utf-8")
    )
    m2_2_n_signoff = json.loads(
        (ROOT / "docs/reports/milestones/M2.2/evidence/nguyen_signoff_receipt.json").read_text(encoding="utf-8")
    )
    assert (ROOT / "docs/reports/milestones/M2.2/evidence/nguyen_peer_review_and_signoff.md").is_file()
    assert m2_2_n_signoff["N_human_verified"] is True

    m2_3_summary = json.loads(
        (ROOT / "docs/reports/milestones/M2.3/evidence/combined_30_summary.json").read_text(encoding="utf-8")
    )
    m2_3_n_signoff = json.loads(
        (ROOT / "docs/reports/milestones/M2.3/evidence/nguyen_signoff_receipt.json").read_text(encoding="utf-8")
    )
    assert m2_3_summary["fabricated_id_count"] == 0
    assert m2_3_summary["K_human_audit"]["supported_factual_claims"] >= 108
    assert m2_3_summary["N_human_audit"]["supported_factual_claims"] >= 108
    assert m2_3_n_signoff["confirmed_totals"]["N_citation_coverage_ok_drafts"] == 30

    # 2. Load weak-label v1 vs human-judged v2_pilot benchmarks
    r_v1 = json.loads(r_v1_path.read_text(encoding="utf-8"))
    r_v2 = json.loads(r_v2_path.read_text(encoding="utf-8"))
    r_v3_4 = json.loads(r_v3_4_path.read_text(encoding="utf-8"))
    assert r_v1["benchmark_id"] == "retrieval_v1", r_v1
    assert r_v3_4["evaluation"]["human_signoff_complete"] if "human_signoff_complete" in r_v3_4["evaluation"] else r_v3_4["evaluation"]["independent_two_human_signoff_complete"] is True
    assert r_v3_4["evaluation"]["qrels_completeness"]["K_human_verified_all"] is True
    assert r_v3_4["evaluation"]["qrels_completeness"]["N_human_verified_all"] is True

    weak_vs_human = {
        "historical_v1_initial_receipt": {
            "benchmark_id": r_v1["benchmark_id"],
            "snapshot": r_v1["corpus_snapshot_id"],
            "bm25": r_v1["configurations"]["bm25_viral_boost"],
            "bm25_reranked": r_v1["configurations"]["bm25_viral_boost_reranked"],
        },
        "historical_weak_label_v1_in_v2_receipt": {
            "benchmark_id": r_v2["benchmark_id"],
            "snapshot": r_v2["corpus_snapshot_id"],
            "queries": r_v2["configurations"]["bm25_viral_boost"]["query_count"],
            "label_source": r_v2["evaluation"]["label_source"],
            "bm25": r_v2["configurations"]["bm25_viral_boost"],
            "bm25_reranked": r_v2["configurations"]["bm25_viral_boost_reranked"],
        },
        "human_judged_v2_pilot_final": {
            "benchmark_id": r_v3_4["benchmark_id"],
            "snapshot": r_v3_4["corpus_snapshot_id"],
            "label_source": r_v3_4["evaluation"]["label_source"],
            "qrels_completeness": r_v3_4["evaluation"]["qrels_completeness"],
            "locked_test_bm25": r_v3_4["splits"]["locked_test"]["bm25"],
            "locked_test_bm25_reranked": r_v3_4["splits"]["locked_test"]["bm25_reranked"],
            "latency_locked_test": r_v3_4["latency_100_warm_requests"],
        },
    }

    # 3. Run real-corpus ASGI API & mounted Gradio /demo/ checks
    asgi_stages = asyncio.run(_run_asgi_probe())

    # 4. Assert zero mutation of immutable corpus/index/benchmark files
    assert before_snap == _dir_hashes(snap_v2)
    assert before_bm25 == _dir_hashes(bm25_v3)
    assert before_bench == {p.name: _sha256(p) for p in (r_v1_path, r_v2_path, r_v3_4_path)}

    receipt = {
        "gate_id": "G2",
        "probe_executed_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
        },
        "prerequisites_verified": {
            "G0": g0_receipt["decision"],
            "G1": g1_receipt["decision"],
            "G1_scope": g1_receipt["decision_scope"],
            "M2_1": "COMPLETE",
            "M2_2": "COMPLETE",
            "M2_3": "COMPLETE",
        },
        "m2_1_summary": {
            "linux_latency_ms": m2_1_linux,
            "windows_reproduction_runs": list(m2_1_repro.keys()) if isinstance(m2_1_repro, dict) else "present",
        },
        "m2_2_weak_vs_human_comparison": weak_vs_human,
        "m2_3_summary": m2_3_summary,
        "asgi_real_corpus_probe": asgi_stages,
        "immutable_sha256_preserved": {
            "20261118_taxonomy_fix_v1_manifest": before_snap["manifest.json"],
            "bm25_v3_receipt": before_bm25["bm25-receipt.json"],
            "retrieval_v1": before_bench["retrieval_v1.json"],
            "retrieval_v2": before_bench["retrieval_v2.json"],
            "retrieval_v3_4_final_pilot": before_bench["retrieval_v3_4_final_pilot.json"],
        },
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }

    out_path = OUT / "g2_verification_receipt.json"
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: wrote {out_path.relative_to(ROOT)} in {receipt['elapsed_seconds']}s")
    print("ASGI stages:", json.dumps(asgi_stages, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
