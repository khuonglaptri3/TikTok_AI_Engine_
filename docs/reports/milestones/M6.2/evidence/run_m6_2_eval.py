"""Offline M6.2 30-question evaluation & single-concurrency latency probe."""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from packages.common.resources import get_peak_rss_mib
from packages.common.settings import AppSettings


def _percentile(vals: list[float], pct: float) -> float:
    if not vals:
        return 0.0
    ordered = sorted(vals)
    idx = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 3)


def run_evaluation(
    *,
    questions_path: Path,
    corpus_dir: Path,
    bm25_dir: Path,
    output_receipt: Path,
    output_answers: Path,
) -> dict[str, Any]:
    questions = [
        json.loads(line)
        for line in questions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    voice_vids: set[str] = set()
    voice_pq = corpus_dir / "fact_voice_segments.parquet"
    if voice_pq.is_file():
        voice_vids = set(pd.read_parquet(voice_pq, columns=["video_id"])["video_id"].astype(str))

    t_boot = time.perf_counter()
    cfg = AppSettings(
        corpus_dir=corpus_dir,
        bm25_index_dir=bm25_dir,
        reranker_enabled=True,
        gemini_api_key="",
    )
    app = create_app(settings=cfg, mount_demo=True)
    client = TestClient(app)
    startup_ms = round((time.perf_counter() - t_boot) * 1000.0, 3)

    # Check /health/ready and /demo/ HTTP 200 baseline
    health_resp = client.get("/health/ready")
    demo_resp = client.get("/demo/")
    assert health_resp.status_code == 200
    assert demo_resp.status_code == 200

    valid_video_ids = set(app.state.container.analytics.df_videos["video_id"].astype(str))

    retrieval_latencies_ms: list[float] = []
    script_latencies_ms: list[float] = []
    combined_latencies_ms: list[float] = []

    resolved_citations = 0
    total_citations = 0
    answer_rows: list[dict[str, Any]] = []

    for q in questions:
        qid = str(q["query_id"])
        q_text = str(q["query"])
        filters = dict(q.get("filters") or {})

        # 1. /api/v1/retrieval/search
        t_r0 = time.perf_counter()
        r_resp = client.post(
            "/api/v1/retrieval/search",
            json={
                "query": q_text,
                "mode": "bm25",
                "top_k": 5,
                "rerank": True,
                "filters": filters,
            },
        )
        r_ms = round((time.perf_counter() - t_r0) * 1000.0, 3)
        r_body = r_resp.json()
        retrieval_latencies_ms.append(r_ms)

        r_items = r_body.get("items", []) if r_resp.status_code == 200 else []
        r_vids = [str(it["citation"]["video_id"]) for it in r_items]
        for vid in r_vids:
            total_citations += 1
            if vid in valid_video_ids:
                resolved_citations += 1

        # Annotate actual temporal provenance per retrieved video_id
        vid_provenance = {
            vid: ("audio_derived" if vid in voice_vids else "wps_estimated")
            for vid in r_vids
        }

        # 2. /api/v1/script/generate (offline_grounded, zero LLM calls)
        t_s0 = time.perf_counter()
        s_resp = client.post(
            "/api/v1/script/generate",
            json={
                "brief": q_text,
                "target_duration_sec": 35,
                "top_k_evidence": 5,
                "generation_mode": "offline_grounded",
                "filters": filters,
            },
        )
        s_ms = round((time.perf_counter() - t_s0) * 1000.0, 3)
        s_body = s_resp.json()
        script_latencies_ms.append(s_ms)
        combined_latencies_ms.append(round(r_ms + s_ms, 3))

        s_beat_vids: list[str] = []
        if s_resp.status_code == 200:
            for beat in s_body.get("beats", []):
                for vid in beat.get("cited_video_ids", []):
                    s_beat_vids.append(str(vid))
                    total_citations += 1
                    if str(vid) in valid_video_ids:
                        resolved_citations += 1

        guardrail = s_body.get("guardrail", {}) if s_resp.status_code == 200 else {}
        answer_rows.append(
            {
                "query_id": qid,
                "category": q["category"],
                "expect_insufficient_evidence": bool(q["expect_insufficient_evidence"]),
                "query": q_text,
                "filters": filters,
                "retrieval_status": r_resp.status_code,
                "retrieval_insufficient_evidence": bool(r_body.get("insufficient_evidence", False))
                if r_resp.status_code == 200
                else True,
                "retrieval_abstain_reason": r_body.get("abstain_reason")
                if r_resp.status_code == 200
                else r_body.get("code"),
                "retrieved_video_ids": r_vids,
                "retrieved_provenance": vid_provenance,
                "target_video_hit": (
                    str(q["target_video_id"]) in r_vids
                    if q.get("target_video_id")
                    else None
                ),
                "script_status": s_resp.status_code,
                "script_error_code": s_body.get("code") if s_resp.status_code != 200 else None,
                "script_error_message": s_body.get("message") if s_resp.status_code != 200 else None,
                "script_warnings": guardrail.get("warnings", []),
                "script_cited_video_ids": sorted(set(s_beat_vids)),
                "guardrail_valid_citations_ratio": guardrail.get("valid_citations_ratio"),
                "guardrail_citation_coverage_ratio": guardrail.get("citation_coverage_ratio"),
                "retrieval_ms": r_ms,
                "script_ms": s_ms,
                "N_human_verified": False,
                "K_human_verified": False,
                "N_claim_note": "",
                "K_claim_note": "",
            }
        )

    output_answers.parent.mkdir(parents=True, exist_ok=True)
    output_answers.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in answer_rows) + "\n",
        encoding="utf-8",
    )

    ans_rows = [r for r in answer_rows if not r["expect_insufficient_evidence"]]
    no_ans_rows = [r for r in answer_rows if r["expect_insufficient_evidence"]]
    no_ans_blocked_or_warned = [
        r
        for r in no_ans_rows
        if r["retrieval_insufficient_evidence"]
        or r["script_status"] != 200
        or bool(r["script_warnings"])
    ]

    receipt = {
        "task_id": "M6.2",
        "mode": "offline_grounded_30q_dry_run",
        "corpus_snapshot_id": str(app.state.container.analytics.manifest.snapshot_id),
        "bm25_index_dir": str(bm25_dir),
        "hardware": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "concurrency": 1,
        },
        "startup_artifact_load_ms": startup_ms,
        "peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        "health_ready_status": health_resp.status_code,
        "demo_mount_status": demo_resp.status_code,
        "questions_total": len(answer_rows),
        "answerable_count": len(ans_rows),
        "answerable_retrieval_hits_nonempty": sum(
            1 for r in ans_rows if not r["retrieval_insufficient_evidence"] and r["retrieved_video_ids"]
        ),
        "answerable_fresh_target_hits": sum(1 for r in ans_rows if r["target_video_hit"] is True),
        "answerable_fresh_target_total": sum(1 for r in ans_rows if r["target_video_hit"] is not None),
        "no_answer_count": len(no_ans_rows),
        "no_answer_strict_retrieval_or_http_refusal_count": sum(
            1 for r in no_ans_rows if r["retrieval_insufficient_evidence"] or r["script_status"] != 200
        ),
        "no_answer_flagged_or_refused_count": len(no_ans_blocked_or_warned),
        "source_resolution_rate": round(resolved_citations / total_citations, 4) if total_citations else 1.0,
        "total_citations_checked": total_citations,
        "latency_ms_excluding_startup": {
            "retrieval": {
                "p50": _percentile(retrieval_latencies_ms, 50),
                "p95": _percentile(retrieval_latencies_ms, 95),
                "max": round(max(retrieval_latencies_ms), 3),
            },
            "script_offline_grounded": {
                "p50": _percentile(script_latencies_ms, 50),
                "p95": _percentile(script_latencies_ms, 95),
                "max": round(max(script_latencies_ms), 3),
            },
            "combined_per_question": {
                "p50": _percentile(combined_latencies_ms, 50),
                "p95": _percentile(combined_latencies_ms, 95),
                "max": round(max(combined_latencies_ms), 3),
            },
        },
        "meets_offline_p95_lte_5000ms": _percentile(combined_latencies_ms, 95) <= 5000.0,
        "human_inspection_complete": False,
    }
    output_receipt.parent.mkdir(parents=True, exist_ok=True)
    output_receipt.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M6.2 30-question offline evaluation & latency probe.")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("data/evaluation/m6_2/held_out_questions_30.jsonl"),
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/corpus/m3_3_pilot_snapshot_v2"),
    )
    parser.add_argument(
        "--bm25-dir",
        type=Path,
        default=Path("artifacts/indexes/bm25-m3_3-pilot"),
    )
    parser.add_argument(
        "--output-receipt",
        type=Path,
        default=Path("docs/reports/milestones/M6.2/evidence/m6_2_offline_dry_run_receipt.json"),
    )
    parser.add_argument(
        "--output-answers",
        type=Path,
        default=Path("docs/reports/milestones/M6.2/evidence/m6_2_answers_sheet.jsonl"),
    )
    args = parser.parse_args()
    rcpt = run_evaluation(
        questions_path=args.questions,
        corpus_dir=args.corpus_dir,
        bm25_dir=args.bm25_dir,
        output_receipt=args.output_receipt,
        output_answers=args.output_answers,
    )
    print(json.dumps(rcpt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
