# M3.3 — Execution Plan

1. Author `docs/reports/milestones/M3.3/superpowers/spec.md`, `plan.md`, and initialize `evidence/workflow.md`.
2. Write TDD failing tests in `tests/unit/test_m3_3_pilot_pipeline.py` (RED) covering:
   - Bounded CPU ASR stage enforcing `max_asr_videos <= 10` and `max_asr_minutes <= 20.0`, skipping missing/empty `.mp3` files without fabricating transcripts, computing `real_time_factor` (`wall_sec / audio_sec`) and `peak_rss_mib`, and failing closed when `faster-whisper` is absent;
   - End-to-end `dry_run_fixture` pipeline (`M3.2` collector -> bounded CPU ASR -> `M3.1` Dual-Sink Gold snapshot -> `BM25Index` build -> `HybridRetrievalService` fresh-video searchability probe -> 50/50 `K`/`N` inspection export) preserving base `20261118_taxonomy_fix_v1` SHA256 hashes and marking `is_synthetic_fixture=True`;
   - Honest `BLOCKED` status on `live_pilot` when prerequisites (`yt-dlp`, `ffmpeg`, `faster-whisper`, or `MS_TOKEN`) are missing or searchable fresh videos `< 5`.
3. Implement `pipelines/pilot_m3_3/` (`models.py`, `asr.py`, `runner.py`, `__main__.py`, `__init__.py`) to pass all TDD regressions (GREEN).
4. Run an offline `--mode dry_run_fixture` wiring probe directly against real `20261118_taxonomy_fix_v1` (`70,996` protected historical IDs) into a temporary directory, plus check `live_pilot` preflight readiness on the current Linux host.
5. Run full `pytest -v`, `mypy packages apps pipelines`, `ruff check`, and `scripts/check_secrets.py`.
6. Record `docs/reports/milestones/M3.3/README.md` cleanly (`Status: IN_PROGRESS` / preflight scaffolding ready for live execution once host tools & `MS_TOKEN` are supplied).
