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
from pipelines.crawl_incremental.crawler_service import (
    compute_cutoff_utc,
    load_dotenv_if_present,
    select_curated_fnb_creators,
    write_incremental_batch,
)
from pipelines.crawl_incremental.models import CollectorBounds
from pipelines.crawl_incremental.providers import (
    CollectorProvider,
    OfflineFixtureAudioConverter,
    OfflineFixtureCollectorProvider,
    YtDlpAudioConverter64k,
    build_live_collector_provider,
    is_tiktokapi_available,
)
from pipelines.crawl_incremental.worker import BoundedIncrementalCollector, _atomic_write_json
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold
from pipelines.pilot_m3_3.asr import BoundedCpuAsrRunner, CpuAsrEngine, FasterWhisperCpuAsrEngine
from pipelines.pilot_m3_3.models import (
    AsrPilotReceipt,
    CollectionSummaryReceipt,
    M33PilotConfig,
    M33PilotReceipt,
    M33PreflightReport,
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
    *,
    preserve_existing_verifications: bool = False,
) -> tuple[int, int]:
    existing_by_vid: dict[str, dict[str, object]] = {}
    if preserve_existing_verifications and path.is_file():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                parsed = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            vid_key = str(parsed.get("video_id") or "").strip()
            if vid_key:
                existing_by_vid[vid_key] = parsed

    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    k_cnt = 0
    n_cnt = 0
    for idx, rec in enumerate(records):
        prev = existing_by_vid.get(rec.video_id)
        default_reviewer = "K" if idx % 2 == 0 else "N"
        reviewer = str(prev.get("assigned_reviewer") or default_reviewer) if prev else default_reviewer
        if reviewer == "K":
            k_cnt += 1
        else:
            n_cnt += 1
        human_verified = bool(prev.get("human_verified", False)) if prev else False
        reviewer_notes = str(prev.get("reviewer_notes") or "") if prev else ""
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
                    "human_verified": human_verified,
                    "reviewer_notes": reviewer_notes,
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


def _resolve_pilot_creators(
    config: M33PilotConfig,
    creator_filter_file: Path = Path("data/filters/author_unique_ids.txt"),
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for raw_c in config.creators:
        c = raw_c.lstrip("@").strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            merged.append(c)
            if len(merged) >= config.max_creators:
                return merged
    if config.auto_creators > 0:
        auto_list = select_curated_fnb_creators(
            config.base_corpus_dir,
            top_k=max(config.auto_creators, config.max_creators),
            filter_file=creator_filter_file,
        )
        for auto_c in auto_list:
            if auto_c.lower() not in seen:
                seen.add(auto_c.lower())
                merged.append(auto_c)
                if len(merged) >= min(len(config.creators) + config.auto_creators, config.max_creators):
                    break
    return merged[: config.max_creators]


def _resolve_output_gold_dir(output_gold_dir: Path, resume: bool) -> Path:
    """Preserve immutable Gold snapshots while auto-allocating a clean versioned directory on --resume or enrichment."""
    if not output_gold_dir.exists():
        return output_gold_dir
    if not resume:
        return output_gold_dir
    idx = 1
    while True:
        candidate = output_gold_dir.parent / f"{output_gold_dir.name}_resume_{idx}"
        if not candidate.exists():
            return candidate
        idx += 1


def _resolve_enriched_gold_dir(output_gold_dir: Path) -> Path:
    """Allocate a clean immutable Gold directory when enriching comments over an existing pilot snapshot."""
    if not output_gold_dir.exists():
        return output_gold_dir
    idx = 1
    while True:
        candidate = output_gold_dir.parent / f"{output_gold_dir.name}_comments_{idx}"
        if not candidate.exists():
            return candidate
        idx += 1


def _resolve_env_view(dotenv_path: Path | None) -> dict[str, str]:
    target = dict(os.environ)
    if dotenv_path is not None:
        return load_dotenv_if_present(dotenv_path, target_env=target)
    return load_dotenv_if_present(Path("__nonexistent_dotenv__"), target_env=target)


def run_m3_3_preflight(
    config: M33PilotConfig,
    *,
    dotenv_path: Path | None = None,
    creator_filter_file: Path = Path("data/filters/author_unique_ids.txt"),
    has_injected_asr: bool = False,
) -> M33PreflightReport:
    """Inspect local M3.3 live_pilot readiness (0 network calls, zero secret values echoed)."""
    env_view = _resolve_env_view(dotenv_path)
    protected_ids, _ = _load_protected_corpus_ids(config.base_corpus_dir)
    selected_creators = _resolve_pilot_creators(config, creator_filter_file=creator_filter_file)
    search_path = _venv_search_path()

    ms_token_present = bool(str(env_view.get("MS_TOKEN", "")).strip())
    env_cookies = str(env_view.get("TIKTOK_COOKIES_FILE", "")).strip()
    cookies_path = config.cookies_file or (Path(env_cookies) if env_cookies else None)
    cookies_file_present = bool(cookies_path is not None and cookies_path.is_file())

    ytdlp_found = shutil.which("yt-dlp", path=search_path) is not None
    ffmpeg_found = shutil.which("ffmpeg", path=search_path) is not None
    tiktokapi_installed = is_tiktokapi_available()

    if has_injected_asr:
        faster_whisper_found = True
    else:
        try:
            import importlib.util

            faster_whisper_found = importlib.util.find_spec("faster_whisper") is not None
        except Exception:
            faster_whisper_found = False

    if config.backend == "tiktokapi":
        resolved_backend = "tiktokapi_only" if tiktokapi_installed else "tiktokapi_missing"
    elif config.backend == "ytdlp":
        resolved_backend = "ytdlp_only"
    else:
        resolved_backend = "tiktokapi_with_ytdlp_fallback" if tiktokapi_installed else "ytdlp_only"

    blockers: list[str] = []
    if not config.allow_live_network:
        blockers.append("--allow-live-network is required for live_pilot mode")
    if not protected_ids:
        blockers.append(f"Protected historical video IDs missing at {config.base_corpus_dir}")
    if not config.enrich_comments_only and not selected_creators:
        blockers.append(
            "At least 1 creator handle (--creator or --auto-creators) is required for live_pilot mode"
        )
    if config.enrich_comments_only and not (config.batch_dir / "videos_4m.jsonl").is_file():
        blockers.append(
            f"Existing batch videos_4m.jsonl not found at {config.batch_dir / 'videos_4m.jsonl'} for --enrich-comments-only"
        )
    if not ms_token_present:
        blockers.append("MS_TOKEN environment credential is missing")
    if cookies_path is not None and not cookies_file_present:
        blockers.append("Configured cookies_file was not found on disk")
    if config.backend == "tiktokapi" and not tiktokapi_installed:
        blockers.append(
            "TikTokApi package is not installed (--backend tiktokapi requested; install TikTokApi + playwright or use --backend auto)"
        )
    if not config.enrich_comments_only:
        if resolved_backend in {"ytdlp_only", "tiktokapi_with_ytdlp_fallback"} and not ytdlp_found:
            blockers.append("yt-dlp binary is missing from PATH")
        elif not ytdlp_found:
            # Even tiktokapi_only uses yt-dlp for 64 kbps .mp3 extraction
            blockers.append("yt-dlp binary is missing from PATH")
        if not ffmpeg_found:
            blockers.append("ffmpeg binary is missing from PATH")
        if not faster_whisper_found:
            blockers.append("faster-whisper Python package is not installed")
    if not config.resume and not config.enrich_comments_only and config.output_gold_dir.exists():
        blockers.append(
            f"Output Gold snapshot directory already exists ({config.output_gold_dir.name}); pass --resume or choose a new --output-gold path"
        )

    return M33PreflightReport(
        ready_for_live_pilot=not blockers,
        ms_token_present=ms_token_present,
        cookies_file_present=cookies_file_present,
        ytdlp_found=ytdlp_found,
        ffmpeg_found=ffmpeg_found,
        faster_whisper_found=faster_whisper_found,
        tiktokapi_installed=tiktokapi_installed,
        resolved_backend=resolved_backend,
        historical_protected_count=len(protected_ids),
        selected_creators=selected_creators,
        blocker_reasons=blockers,
    )


def run_m3_3_pilot(
    config: M33PilotConfig,
    *,
    asr_engine: CpuAsrEngine | None = None,
    dotenv_path: Path | None = None,
    creator_filter_file: Path = Path("data/filters/author_unique_ids.txt"),
) -> M33PilotReceipt:
    """Execute bounded M3.3 capture -> CPU ASR -> M3.1 Gold -> BM25 -> searchability slice."""
    if config.enrich_comments_only:
        return run_m3_3_comment_enrichment(
            config,
            dotenv_path=dotenv_path,
        )
    t0 = time.perf_counter()
    now_iso = datetime.now(UTC).isoformat()
    env_view = _resolve_env_view(dotenv_path)
    protected_ids, base_snapshot_id = _load_protected_corpus_ids(config.base_corpus_dir)
    selected_creators = _resolve_pilot_creators(config, creator_filter_file=creator_filter_file)

    if config.mode == "live_pilot":
        preflight = run_m3_3_preflight(
            config,
            dotenv_path=dotenv_path,
            creator_filter_file=creator_filter_file,
            has_injected_asr=(asr_engine is not None),
        )
        if preflight.blocker_reasons:
            receipt = M33PilotReceipt(
                mode=config.mode,
                pilot_status="BLOCKED",
                is_synthetic_fixture=False,
                executed_at_utc=now_iso,
                blocker_reasons=preflight.blocker_reasons,
                base_corpus_snapshot_id=base_snapshot_id,
                collection=CollectionSummaryReceipt(
                    collector_backend_requested=config.backend,
                    historical_protected_count=len(protected_ids),
                ),
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
    effective_as_of = config.as_of_utc or datetime.now(UTC)
    if effective_as_of.tzinfo is None:
        effective_as_of = effective_as_of.replace(tzinfo=UTC)
    cutoff_utc = compute_cutoff_utc(reference_now=effective_as_of, window_days=config.window_days)

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
        ms_token = str(env_view.get("MS_TOKEN", "")).strip()
        env_cookies = str(env_view.get("TIKTOK_COOKIES_FILE", "")).strip()
        cookies_path = config.cookies_file or (Path(env_cookies) if env_cookies else None)
        active_asr = asr_engine or FasterWhisperCpuAsrEngine(model_size=config.asr_model_size)
        live_provider = build_live_collector_provider(
            backend=config.backend,
            allow_live_network=config.allow_live_network,
            ms_token=ms_token,
            cookies_file=cookies_path,
            browser=config.tiktok_browser,
            headless=config.tiktok_headless,
            cutoff_utc=cutoff_utc,
        )
        collector = BoundedIncrementalCollector(
            provider=live_provider,
            audio_converter=YtDlpAudioConverter64k(
                allow_live_network=config.allow_live_network,
                ms_token=ms_token,
                cookies_file=cookies_path,
            ),
            bounds=bounds,
        )

    manifest = collector.run(
        output_dir=config.batch_dir,
        as_of_utc=effective_as_of,
        historical_video_ids=protected_ids,
        base_corpus_snapshot_id=base_snapshot_id,
        creators=selected_creators or None,
        resume=config.resume,
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
        collector_backend_requested=manifest.collector_backend_requested,
        collector_backends_used=manifest.collector_backends_used,
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
    if manifest.discovery_error:
        blockers_after.append(manifest.discovery_error)
    elif manifest.stopped_reason == "anti_bot_challenge_blocked":
        blockers_after.append(
            "Anti-bot/CAPTCHA challenge encountered; collector halted fail-closed without bypass"
        )
    elif manifest.stopped_reason == "discovery_failed":
        blockers_after.append("Candidate discovery failed across active collector backend(s)")

    if not enriched_records or (
        config.mode == "live_pilot" and manifest.stopped_reason == "anti_bot_challenge_blocked"
    ):
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

    # Dual-sink ingest into new Gold snapshot (never mutates base or prior snapshot)
    target_gold_dir = _resolve_output_gold_dir(config.output_gold_dir, config.resume)
    gold_manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=config.base_corpus_dir,
        incremental_jsonl=jsonl_path,
        output_corpus_dir=target_gold_dir,
    )

    _, _, df_videos = load_verified_corpus(target_gold_dir)
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
    elif manifest.stopped_reason == "anti_bot_challenge_blocked":
        status = "BLOCKED"
    elif len(matched_ids) >= config.min_searchable_fresh_videos:
        status = "PASS"
    else:
        status = "BLOCKED"
        blockers_after.append(
            f"Searchable fresh transcribed videos ({len(matched_ids)}) below minimum required ({config.min_searchable_fresh_videos})"
        )

    b_bytes = _dir_size_bytes(config.batch_dir)
    g_bytes = _dir_size_bytes(target_gold_dir)
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


def run_m3_3_comment_enrichment(
    config: M33PilotConfig,
    *,
    provider: CollectorProvider | None = None,
    dotenv_path: Path | None = None,
) -> M33PilotReceipt:
    """Enrich comments onto an existing M3.3 pilot batch without re-running discovery, audio, or ASR."""
    t0 = time.perf_counter()
    now_iso = datetime.now(UTC).isoformat()
    env_view = _resolve_env_view(dotenv_path)
    protected_ids, base_snapshot_id = _load_protected_corpus_ids(config.base_corpus_dir)

    prior_asr_receipt: AsrPilotReceipt | None = None
    if config.receipt_path.is_file():
        try:
            prev_rcpt = M33PilotReceipt.model_validate(
                json.loads(config.receipt_path.read_text(encoding="utf-8"))
            )
            prior_asr_receipt = prev_rcpt.asr
        except Exception:
            prior_asr_receipt = None

    if config.mode == "live_pilot" and provider is None:
        preflight = run_m3_3_preflight(
            config.model_copy(update={"enrich_comments_only": True}),
            dotenv_path=dotenv_path,
            has_injected_asr=True,
        )
        if preflight.blocker_reasons:
            receipt = M33PilotReceipt(
                mode=config.mode,
                pilot_status="BLOCKED",
                is_synthetic_fixture=False,
                executed_at_utc=now_iso,
                blocker_reasons=preflight.blocker_reasons,
                base_corpus_snapshot_id=base_snapshot_id,
                collection=CollectionSummaryReceipt(
                    collector_backend_requested=config.backend,
                    historical_protected_count=len(protected_ids),
                ),
                asr=prior_asr_receipt,
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
    effective_as_of = config.as_of_utc or datetime.now(UTC)
    if effective_as_of.tzinfo is None:
        effective_as_of = effective_as_of.replace(tzinfo=UTC)
    cutoff_utc = compute_cutoff_utc(reference_now=effective_as_of, window_days=config.window_days)

    active_provider: CollectorProvider
    if provider is not None:
        active_provider = provider
    elif config.mode == "dry_run_fixture":
        if config.fixture_path is None:
            raise ValueError("fixture_path is required when mode='dry_run_fixture'")
        active_provider = OfflineFixtureCollectorProvider(config.fixture_path)
    else:
        os.environ["PATH"] = _venv_search_path()
        ms_token = str(env_view.get("MS_TOKEN", "")).strip()
        env_cookies = str(env_view.get("TIKTOK_COOKIES_FILE", "")).strip()
        cookies_path = config.cookies_file or (Path(env_cookies) if env_cookies else None)
        active_provider = build_live_collector_provider(
            backend=config.backend,
            allow_live_network=config.allow_live_network,
            ms_token=ms_token,
            cookies_file=cookies_path,
            browser=config.tiktok_browser,
            headless=config.tiktok_headless,
            cutoff_utc=cutoff_utc,
        )

    collector = BoundedIncrementalCollector(
        provider=active_provider,
        audio_converter=OfflineFixtureAudioConverter(),
        bounds=bounds,
        sleep_fn=(lambda _: None) if (provider is not None or config.mode == "dry_run_fixture") else time.sleep,
    )
    manifest = collector.enrich_existing_comments(
        output_dir=config.batch_dir,
        as_of_utc=effective_as_of,
        historical_video_ids=protected_ids,
        base_corpus_snapshot_id=base_snapshot_id,
    )

    jsonl_path = config.batch_dir / manifest.output_jsonl
    enriched_records = (
        [
            RawIncrementalVideoRecord.model_validate(json.loads(line))
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if jsonl_path.is_file()
        else []
    )

    if prior_asr_receipt is None:
        transcribed_cnt = sum(1 for r in enriched_records if r.transcript.strip())
        no_audio_cnt = sum(1 for r in enriched_records if not r.audio_path)
        acc_asr_min = round(
            sum((r.duration_sec / 60.0) for r in enriched_records if r.transcript.strip()),
            3,
        )
        prior_asr_receipt = AsrPilotReceipt(
            engine_model_id=f"faster-whisper/{config.asr_model_size}-cpu-int8",
            max_videos_cap=config.max_asr_videos,
            max_audio_minutes_cap=config.max_asr_minutes,
            transcribed_count=transcribed_cnt,
            skipped_no_audio_count=no_audio_cnt,
            skipped_asr_ceiling_count=max(0, len(enriched_records) - transcribed_cnt - no_audio_cnt),
            failed_count=0,
            accumulated_audio_minutes=acc_asr_min,
            wall_seconds=0.0,
            real_time_factor=0.0,
            peak_rss_mib=round(float(get_peak_rss_mib()), 2),
        )

    req_cnt = manifest.requested_count
    succ_cnt = manifest.succeeded_count
    fail_cnt = manifest.failed_count
    with_comments = sum(1 for r in enriched_records if r.comments)
    collection_summary = CollectionSummaryReceipt(
        collector_backend_requested=manifest.collector_backend_requested,
        collector_backends_used=manifest.collector_backends_used,
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

    k_cnt, n_cnt = _write_inspection_sheet(
        config.inspection_sheet_path,
        enriched_records,
        preserve_existing_verifications=True,
    )

    transcribed_fresh = [r for r in enriched_records if r.transcript.strip()]
    blockers_after: list[str] = []
    if manifest.stopped_reason == "anti_bot_challenge_blocked":
        failed_reasons = [i.reason for i in manifest.items if i.status == "failed" and i.reason]
        detail_msg = failed_reasons[0] if failed_reasons else "anti_bot_challenge_blocked"
        blockers_after.append(
            f"Anti-bot/CAPTCHA challenge encountered during comment enrichment ({detail_msg}); collector halted fail-closed without bypass"
        )

    if not enriched_records or (
        config.mode == "live_pilot" and manifest.stopped_reason == "anti_bot_challenge_blocked"
    ):
        if not enriched_records:
            blockers_after.append("No records found in batch videos_4m.jsonl for comment enrichment")
        receipt = M33PilotReceipt(
            mode=config.mode,
            pilot_status="BLOCKED" if config.mode == "live_pilot" else "FIXTURE_DRY_RUN_ONLY",
            is_synthetic_fixture=manifest.is_synthetic_fixture,
            executed_at_utc=now_iso,
            blocker_reasons=blockers_after,
            base_corpus_snapshot_id=base_snapshot_id,
            collection=collection_summary,
            asr=prior_asr_receipt,
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

    target_gold_dir = _resolve_enriched_gold_dir(config.output_gold_dir)
    gold_manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=config.base_corpus_dir,
        incremental_jsonl=jsonl_path,
        output_corpus_dir=target_gold_dir,
        update_existing=True,
    )

    _, _, df_videos = load_verified_corpus(target_gold_dir)
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
    g_bytes = _dir_size_bytes(target_gold_dir)
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
        asr=prior_asr_receipt,
        searchability=searchability,
        resources=resources,
        inspection_k_count=k_cnt,
        inspection_n_count=n_cnt,
    )
    _atomic_write_json(config.receipt_path, final_receipt.model_dump())
    return final_receipt
