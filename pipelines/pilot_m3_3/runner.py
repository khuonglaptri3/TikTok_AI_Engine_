from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.multimodal import RawIncrementalVideoRecord
from packages.data_contracts.query import RetrievalRequest
from packages.retrieval import HybridRetrievalService
from packages.retrieval.sparse.bm25 import BM25Index
from pipelines.crawl_incremental.__main__ import _load_protected_corpus_ids
from pipelines.crawl_incremental.crawler_service import write_incremental_batch
from pipelines.crawl_incremental.models import CollectorBounds
from pipelines.crawl_incremental.providers import (
    LiveTikTokCollectorProvider,
    OfflineFixtureAudioConverter,
    OfflineFixtureCollectorProvider,
    YtDlpAudioConverter64k,
)
from pipelines.crawl_incremental.worker import BoundedIncrementalCollector, _atomic_write_json
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold
from pipelines.pilot_m3_3.asr import BoundedCpuAsrRunner, CpuAsrEngine, FasterWhisperCpuAsrEngine
from pipelines.pilot_m3_3.models import (
    CollectionSummaryReceipt,
    M33PilotConfig,
    M33PilotReceipt,
    PilotStatus,
    ResourceReceipt,
    SearchabilityReceipt,
)

_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def _dir_size_bytes(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def _build_probe_query(transcript: str, caption: str, vocab: dict[str, int] | None = None) -> str:
    # Strip trailing hashtag tokens so queries stay clean natural Vietnamese
    clean_cap = re.sub(r"#\S+", " ", caption)
    clean_cap = re.sub(r"\breview\b", " ", clean_cap, flags=re.IGNORECASE)
    raw = f"{clean_cap} {transcript}"
    words = [w for w in _TOKEN_RE.findall(raw) if len(w) >= 2 and not w.isdigit()]
    if vocab:
        in_vocab = [w for w in words if w.lower() in vocab]
        if in_vocab:
            words = in_vocab
    if not words:
        return "review món ăn"
    seen: set[str] = set()
    unique_words: list[str] = []
    for w in words:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            unique_words.append(w)
        if len(unique_words) >= 6:
            break
    return " ".join(unique_words)


def _write_inspection_sheet(
    path: Path,
    records: list[RawIncrementalVideoRecord],
) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    k_cnt = 0
    n_cnt = 0
    for idx, rec in enumerate(records):
        reviewer = "K" if idx % 2 == 0 else "N"
        if reviewer == "K":
            k_cnt += 1
        else:
            n_cnt += 1
        lines.append(
            json.dumps(
                {
                    "video_id": rec.video_id,
                    "author_handle": rec.author_handle,
                    "create_time": rec.create_time,
                    "caption": rec.caption,
                    "has_audio": bool(rec.audio_path),
                    "comment_count_collected": len(rec.comments),
                    "transcript": rec.transcript,
                    "assigned_reviewer": reviewer,
                    "human_verified": False,
                    "reviewer_notes": "",
                },
                ensure_ascii=False,
            )
        )
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return k_cnt, n_cnt


def _venv_search_path() -> str:
    bin_dir = str(Path(sys.executable).parent)
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if bin_dir not in parts:
        return f"{bin_dir}{os.pathsep}{current}" if current else bin_dir
    return current


def _check_live_prerequisites(
    config: M33PilotConfig,
    protected_ids: set[str],
    has_injected_asr: bool,
) -> list[str]:
    blockers: list[str] = []
    search_path = _venv_search_path()
    if not config.allow_live_network:
        blockers.append("--allow-live-network is required for live_pilot mode")
    if not protected_ids:
        blockers.append(f"Protected historical video IDs missing at {config.base_corpus_dir}")
    if not config.creators:
        blockers.append("At least 1 creator handle (--creator) is required for live_pilot mode")
    if not os.environ.get("MS_TOKEN", "").strip():
        blockers.append("MS_TOKEN environment credential is missing")
    if shutil.which("yt-dlp", path=search_path) is None:
        blockers.append("yt-dlp binary is missing from PATH")
    if shutil.which("ffmpeg", path=search_path) is None:
        blockers.append("ffmpeg binary is missing from PATH")
    if not has_injected_asr:
        try:
            import importlib.util

            if importlib.util.find_spec("faster_whisper") is None:
                blockers.append("faster-whisper Python package is not installed")
        except Exception:
            blockers.append("faster-whisper availability check failed")
    return blockers


def run_m3_3_pilot(
    config: M33PilotConfig,
    *,
    asr_engine: CpuAsrEngine | None = None,
) -> M33PilotReceipt:
    """Execute bounded M3.3 capture -> CPU ASR -> M3.1 Gold -> BM25 -> searchability slice."""
    t0 = time.perf_counter()
    now_iso = datetime.now(UTC).isoformat()
    protected_ids, base_snapshot_id = _load_protected_corpus_ids(config.base_corpus_dir)

    if config.mode == "live_pilot":
        blockers = _check_live_prerequisites(
            config,
            protected_ids,
            has_injected_asr=(asr_engine is not None),
        )
        if blockers:
            receipt = M33PilotReceipt(
                mode=config.mode,
                pilot_status="BLOCKED",
                is_synthetic_fixture=False,
                executed_at_utc=now_iso,
                blocker_reasons=blockers,
                base_corpus_snapshot_id=base_snapshot_id,
                collection=CollectionSummaryReceipt(historical_protected_count=len(protected_ids)),
                resources=ResourceReceipt(
                    wall_seconds=round(time.perf_counter() - t0, 3),
                    peak_rss_mib=round(float(get_peak_rss_mib()), 2),
                ),
            )
            _atomic_write_json(config.receipt_path, receipt.model_dump())
            return receipt

    bounds = CollectorBounds(
        window_days=config.window_days,
        max_creators=config.max_creators,
        max_candidate_videos=config.max_candidate_videos,
        max_succeeded_videos=config.max_succeeded_videos,
        max_audio_minutes=config.max_audio_minutes,
        max_comments_total=config.max_comments_total,
        session_deadline_seconds=config.session_deadline_seconds,
    )

    if config.mode == "dry_run_fixture":
        if config.fixture_path is None:
            raise ValueError("fixture_path is required when mode='dry_run_fixture'")
        collector = BoundedIncrementalCollector(
            provider=OfflineFixtureCollectorProvider(config.fixture_path),
            audio_converter=OfflineFixtureAudioConverter(),
            bounds=bounds,
            sleep_fn=lambda _: None,
        )
        active_asr: CpuAsrEngine = asr_engine or FasterWhisperCpuAsrEngine(
            model_size=config.asr_model_size
        )
    else:
        os.environ["PATH"] = _venv_search_path()
        ms_token = os.environ.get("MS_TOKEN", "").strip()
        active_asr = asr_engine or FasterWhisperCpuAsrEngine(model_size=config.asr_model_size)
        collector = BoundedIncrementalCollector(
            provider=LiveTikTokCollectorProvider(
                allow_live_network=config.allow_live_network,
                ms_token=ms_token,
            ),
            audio_converter=YtDlpAudioConverter64k(allow_live_network=config.allow_live_network),
            bounds=bounds,
        )

    manifest = collector.run(
        output_dir=config.batch_dir,
        as_of_utc=config.as_of_utc,
        historical_video_ids=protected_ids,
        base_corpus_snapshot_id=base_snapshot_id,
        creators=config.creators or None,
        resume=False,
    )

    jsonl_path = config.batch_dir / manifest.output_jsonl
    raw_records = (
        [
            RawIncrementalVideoRecord.model_validate(json.loads(line))
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if jsonl_path.is_file()
        else []
    )

    asr_runner = BoundedCpuAsrRunner(
        engine=active_asr,
        max_videos=config.max_asr_videos,
        max_audio_minutes=config.max_asr_minutes,
    )
    enriched_records, asr_receipt = asr_runner.run(records=raw_records, batch_dir=config.batch_dir)
    write_incremental_batch(enriched_records, config.batch_dir)

    req_cnt = manifest.requested_count
    succ_cnt = manifest.succeeded_count
    fail_cnt = manifest.failed_count
    with_comments = sum(1 for r in enriched_records if r.comments)
    collection_summary = CollectionSummaryReceipt(
        requested_count=req_cnt,
        succeeded_count=succ_cnt,
        failed_count=fail_cnt,
        skipped_count=manifest.skipped_count,
        historical_protected_count=manifest.historical_protected_count,
        converted_audio_count=manifest.converted_audio_count,
        collected_comments_count=manifest.collected_comments_count,
        capture_yield_rate=round(succ_cnt / req_cnt, 4) if req_cnt else 0.0,
        failure_rate=round(fail_cnt / req_cnt, 4) if req_cnt else 0.0,
        comment_coverage_rate=round(with_comments / len(enriched_records), 4)
        if enriched_records
        else 0.0,
    )

    k_cnt, n_cnt = _write_inspection_sheet(config.inspection_sheet_path, enriched_records)

    transcribed_fresh = [r for r in enriched_records if r.transcript.strip()]
    blockers_after: list[str] = []
    if not enriched_records:
        blockers_after.append("No fresh records succeeded within 120-day window")
        receipt = M33PilotReceipt(
            mode=config.mode,
            pilot_status="BLOCKED" if config.mode == "live_pilot" else "FIXTURE_DRY_RUN_ONLY",
            is_synthetic_fixture=manifest.is_synthetic_fixture,
            executed_at_utc=now_iso,
            blocker_reasons=blockers_after,
            base_corpus_snapshot_id=base_snapshot_id,
            collection=collection_summary,
            asr=asr_receipt,
            resources=ResourceReceipt(
                wall_seconds=round(time.perf_counter() - t0, 3),
                peak_rss_mib=round(float(get_peak_rss_mib()), 2),
                batch_disk_bytes=_dir_size_bytes(config.batch_dir),
                total_disk_bytes=_dir_size_bytes(config.batch_dir),
            ),
            inspection_k_count=k_cnt,
            inspection_n_count=n_cnt,
        )
        _atomic_write_json(config.receipt_path, receipt.model_dump())
        return receipt

    # Dual-sink ingest into new Gold snapshot (never mutates base historical snapshot)
    gold_manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=config.base_corpus_dir,
        incremental_jsonl=jsonl_path,
        output_corpus_dir=config.output_gold_dir,
    )

    _, _, df_videos = load_verified_corpus(config.output_gold_dir)
    sub = df_videos[df_videos["has_transcript"] & (df_videos["rag_document"].str.len() > 0)]
    bm25 = BM25Index.build(
        video_ids=sub["video_id"].astype(str).tolist(),
        documents=sub["rag_document"].astype(str).tolist(),
        min_bigram_df=1,
    )
    bm25.save(index_dir=config.output_bm25_dir, corpus_snapshot_id=gold_manifest.snapshot_id)

    service = HybridRetrievalService.from_dirs(
        df_videos=df_videos,
        bm25_dir=config.output_bm25_dir,
        reranker_enabled=True,
    )

    matched_ids: list[str] = []
    probe_queries: dict[str, str] = {}
    for rec in transcribed_fresh:
        q_text = _build_probe_query(rec.transcript, rec.caption, vocab=bm25.vocab)
        probe_queries[rec.video_id] = q_text
        resp = service.search(
            RetrievalRequest(query=q_text, mode="bm25", top_k=10, rerank=True)
        )
        returned_ids = {item.citation.video_id for item in resp.items}
        if rec.video_id in returned_ids:
            matched_ids.append(rec.video_id)

    searchability = SearchabilityReceipt(
        indexed_total_documents=len(sub),
        probed_fresh_transcribed_count=len(transcribed_fresh),
        searchable_fresh_transcribed_count=len(matched_ids),
        matched_fresh_video_ids=matched_ids,
        probe_queries=probe_queries,
    )

    status: PilotStatus
    if config.mode == "dry_run_fixture":
        status = "FIXTURE_DRY_RUN_ONLY"
    elif len(matched_ids) >= config.min_searchable_fresh_videos:
        status = "PASS"
    else:
        status = "BLOCKED"
        blockers_after.append(
            f"Searchable fresh transcribed videos ({len(matched_ids)}) below minimum required ({config.min_searchable_fresh_videos})"
        )

    b_bytes = _dir_size_bytes(config.batch_dir)
    g_bytes = _dir_size_bytes(config.output_gold_dir)
    i_bytes = _dir_size_bytes(config.output_bm25_dir)
    resources = ResourceReceipt(
        wall_seconds=round(time.perf_counter() - t0, 3),
        peak_rss_mib=round(float(get_peak_rss_mib()), 2),
        batch_disk_bytes=b_bytes,
        gold_snapshot_disk_bytes=g_bytes,
        bm25_index_disk_bytes=i_bytes,
        total_disk_bytes=b_bytes + g_bytes + i_bytes,
    )

    final_receipt = M33PilotReceipt(
        mode=config.mode,
        pilot_status=status,
        is_synthetic_fixture=manifest.is_synthetic_fixture,
        executed_at_utc=now_iso,
        blocker_reasons=blockers_after,
        base_corpus_snapshot_id=base_snapshot_id,
        output_gold_snapshot_id=gold_manifest.snapshot_id,
        collection=collection_summary,
        asr=asr_receipt,
        searchability=searchability,
        resources=resources,
        inspection_k_count=k_cnt,
        inspection_n_count=n_cnt,
    )
    _atomic_write_json(config.receipt_path, final_receipt.model_dump())
    return final_receipt
