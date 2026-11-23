# M3.G — Acquisition & Resource Gate Preparation (`Gate G3 = NOT_RUN`)

- Status: IN_PROGRESS (`N` completed `M3.1` repeated-ingest verification, `29`-file `.mp3` audio capacity accounting, and throughput projections in [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json); **official Gate `G3` remains `NOT_RUN`** awaiting `K` `15/15` `M3.3` inspection, recorded human annotation time, and `K`/`N` joint sign-off)
- Gate result: NOT_RUN
- Execution date: 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`)
- Repository version: `main` (prepared over `186a4b0a`)
- Primary owner (`M3.G` Gate Decision): Trần Đình Khương (`K`) · Peer reviewer & preparation contributor: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Gate `G3` (`M3.G`) technical preparation passes all `M3.1` repeated-ingest and resource-accounting checks (`0` duplicate keys, `100%` SHA256 base/pilot preservation, `1,322.89 MiB` replay peak RSS), while `M3.G` stays `IN_PROGRESS` (`G3 = NOT_RUN`) because `K`'s `15/15` `M3.3` inspection, actual human annotation timings, and a joint ruling on `comment_coverage_rate = 0.0` remain open.**

- **Repeated Dual-Sink Ingest (`M3.1` Replay, [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json)):** Both `update_existing=False` (`5,635.45 ms`) and `update_existing=True` (`6,140.35 ms`) over [m3_3_pilot_snapshot_v1](../../../../data/corpus/m3_3_pilot_snapshot_v1/manifest.json) produced `71,026` videos (`71,026` unique `video_id`), `264` creators, `436` voice segments (`436` unique `segment_id`), `0` comments, and `30` ABSA rows with `zero_duplicate_keys=true`, `manifest_checksums_verified=true`, and `100%` unchanged SHA256s on both `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1`.
- **Observed Pilot Throughput & Audio Inventory ([m3_3_pilot_receipt.json](../M3.3/evidence/m3_3_pilot_receipt.json)):** `50` candidates -> `30` succeeded (`capture_yield_rate = 0.6`, `failure_rate = 0.0`, `comment_coverage_rate = 0.0`); `29` captured `.mp3` files total **`2,801 s` (`46.683` min)** across **`22,524,055` B** (`0.4601 MiB/audio-min`); CPU `faster-whisper/small-cpu-int8` transcribed `10` videos (`16.683` min) in `197.269 s` (`RTF = 0.1971`, ASR peak RSS `1,009.46 MiB`); `10/10` searchable in `bm25-m3_3-pilot`; whole pilot `744.154 s`, peak RSS `3,214.92 MiB`, total disk `125,741,108` B.
- **Projections & Strict Budget Guardrail:** Transcribing the remaining `19` captured pilot `.mp3` files (`30.0` audio min) at measured `RTF = 0.1971` projects `~552.08 s` (`~9.20` min) total ASR time across all `29` files. A hypothetical `50`-succeeded-video batch (strictly contingent on an explicit approved budget after `G3`) projects `~84` candidates (`60%` yield), `~20.67` min total wall time at pilot rate, `~37.04 MiB` audio disk, and **`~50.0` min human review** scaled from `N`'s reported `~15.0` min estimate for `15` videos (`~1.0` min/video; `K`'s timing remains `PENDING_MEASUREMENT`).
- **Comment Block Honest Record:** Re-testing `TikTokApi` with updated `MS_TOKEN` (`len=156`) on this headless terminal raised `EmptyResponseException` (`AntiBotChallengeError`); comment collection remains at `0` unless executed on a GUI desktop with `--no-tiktok-headless` or explicitly deferred in `G3`.

## Work performed

- Verified byte-for-byte SHA256 hashes of `20261118_taxonomy_fix_v1` and `m3_3_pilot_snapshot_v1` before and after temporary `/tmp` `M3.1` replay runs.
- Executed `ingest_incremental_batch_to_gold` over `m3_3_pilot_snapshot_v1` + `data/raw_incremental/m3_3_pilot_run/batch/videos_4m.jsonl` under both `update_existing=False` and `update_existing=True` (`5.64 s` and `6.14 s`).
- Audited all `29` `.mp3` files in `audio_64k/` (`46.683` min total), inspection counts in [sample_inspection_sheet.jsonl](../M3.3/evidence/sample_inspection_sheet.jsonl) (`N: 15/15`, `K: 0/15`), and conservative capacity projections into [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json).

## Outputs

| File | Purpose |
| --- | --- |
| [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) | Measured `M3.1` replay timing/dedup, SHA256 preservation proofs, `29`-`.mp3` audio totals, inspection split counts, throughput estimates, and blocking open items |
| [workflow.md](evidence/workflow.md) | `M3.G` preparation workflow provenance, commands, and blocker log |
| [spec.md](superpowers/spec.md), [plan.md](superpowers/plan.md) | Gate `G3` preparation specification and execution plan |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `M3.1` replay verification script (`ingest_incremental_batch_to_gold`, `update_existing=False` & `True`) | PASS | `5,635.45 ms` / `6,140.35 ms`; `zero_duplicate_keys=true`; `base_corpus_bytes_preserved_sha256=true`; [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) |
| `.venv/bin/python -m pytest tests/unit/test_snapshot_continuity.py tests/unit/test_incremental_absa_seeding.py tests/unit/test_m3_3_pilot_pipeline.py -v` | PASS (`38 passed in 10.04s`) | Snapshot continuity, Dual-Sink ABSA/ingest, and M3.3 pilot regression checks |
| `python3 scripts/check_secrets.py` & `M3.G` relative links/layout check | PASS (`0` leaks; `54` relative links `0` broken) | `M3.G/` top-level (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`) verified |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `K` has not yet completed `15/15` manual verification in [sample_inspection_sheet.jsonl](../M3.3/evidence/sample_inspection_sheet.jsonl) (`K: 0/15`, `N: 15/15`) | Blocks closing `M3.3` and evaluating Gate `G3` (`NOT_RUN`) | `K` verifies the `15` `K` rows |
| Human `annotation_time_minutes` (`M3.3` sample inspection) | `N` reported `~15.0` min estimate (`~1.0` min/video); `K` timing still `PENDING_MEASUREMENT` | `K` records actual time while completing `15/15` inspection for final `G3` estimate |
| `comment_coverage_rate = 0.0` (`TikTokApi` headless Chromium hit `EmptyResponseException`) | `M3.3`/`M3.G`/`M4.1` audio & search paths are unblocked; `M5.1`/`M5.2` real-comment evaluation awaits GUI desktop capture (`--no-tiktok-headless`) or explicit deferral | Decide jointly at `G3` whether to run desktop GUI comment enrichment or defer `M5` real-comment gates |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Repeated ingest passes & base corpus preserved | Met (`update_existing=False` & `True`, `0` duplicate keys, SHA256 identical) | [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) |
| `M3.3` vertical slice meets technical/human inspection | Partial (`30/30` captured, `10/10` searchable, `N=15/15`; `K=0/15` pending) | [M3.3/README.md](../M3.3/README.md), [sample_inspection_sheet.jsonl](../M3.3/evidence/sample_inspection_sheet.jsonl) |
| Measure audio RTF, capture yield, comment coverage & annotation time | Partial (`RTF=0.1971`, `yield=0.6`, `comment_coverage=0.0`, `N ~15.0 min` reported; `K` timing `PENDING_MEASUREMENT`) | [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) |
| Further batch estimate & no-expansion guardrail + `K`/`N` joint gate sign-off | Drafted by `N`; `K` completion & joint `G3` sign-off pending | [spec.md](superpowers/spec.md), [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) |

Final task status: **IN_PROGRESS** (`Gate G3 = NOT_RUN`; technical repeated-ingest & capacity prep complete by `N`, handed off to `K` for `M3.3` `15/15` inspection, annotation timing, and joint `G3` decision).
