# M3.G — Specification: Bounded Capture-to-Transcript-to-Search & Resource Capacity Gate (`G3`)

- **Task ID:** `M3.G` (Gate `G3`)
- **Created:** `2026-11-23` (`Asia/Ho_Chi_Minh`)
- **Primary Owner:** Trần Đình Khương (`K`, `2` effort points)
- **Peer Reviewer & Co-Approver:** Nguyễn Việt Nguyên (`N`, `2` effort points)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`, lines 57, 100, 127)
- **Cost & Access Constraint:** Strictly `USD 0` spend, local CPU execution, zero CAPTCHA/anti-bot bypass, and zero historical TikTok re-crawling.

## 1. Purpose & Governance Model

`M3.G` evaluates whether the `M3` incremental ingestion subsystem (`M3.1` dual-sink converter, `M3.2` bounded collector worker, and `M3.3` capped real-data capture-to-transcript-to-search pilot) satisfies its minimum vertical slice, cryptographic data-readiness invariants, and local CPU resource budgets, and establishes an explicit bounded post-pilot collection budget before any further live network activity.

Per the two-person reciprocal governance rule in `TikTok_AI_Engine_Milestone.md` (line 69), neither contributor approves their own task or gate unilaterally. `K` (Primary Owner) builds the deterministic `G3` verification suite, empirical capacity model, and primary-owner gate recommendation (`CONDITIONAL_PASS_UNBLOCK_M4_1_AND_BOUNDED_COMMENT_BACKFILL`), while recording `n_peer_approval = "PENDING_N_REVIEW"` until `N` independently reproduces the checks and signs off.

## 2. Scope & Technical Architecture

Grounded in production MLOps data-readiness gate patterns (`DVC`/`LakeFS` cryptographic SHA-256 snapshot verification combined with `Dagster`-style per-downstream blocking asset checks and stage-decomposed capacity modeling), `M3.G` comprises four cohesive verification and decision components:

### 2.1 Cryptographic Snapshot Lineage & Non-Mutation Verification
1. **Prerequisite Gate & Task Receipts:** Confirm `G0 == PASS` (`M0.G`), `G1 == PASS` (`M1.G`, local-only), `G2 == PASS` (`M2.G`), and `M3.1`, `M3.2`, `M3.3` all `COMPLETE`.
2. **Base Historical Immutability:** Verify every Parquet file in `data/corpus/20261118_taxonomy_fix_v1/` (`70,996` historical videos) matches its recorded `manifest.json` SHA-256 checksums (`parent_manifest_sha256 = 49f23739f9e2ea8f1f66fe1b299fe636c19965c99fcadf2bdd6eef7dc18c27de`) before and after running `run_g3_checks.py` (`0` byte mutations).
3. **Pilot Gold & Raw Media Integrity:**
   - Verify `data/corpus/m3_3_pilot_snapshot_v1/manifest.json` and all `5` Parquet tables (`dim_creators.parquet` = `264` rows, `fact_videos.parquet` = `71,026` rows, `fact_voice_segments.parquet` = `436` rows, `fact_comments.parquet` = `0` rows, `fact_absa_reviews.parquet` = `30` rows) match their SHA-256 checksums and load cleanly through `load_verified_corpus`.
   - Verify all `29` `64 kbps` `.mp3` files under `data/raw_incremental/m3_3_pilot_run/batch/audio_64k/` match their exact `audio_bytes` and `audio_sha256` entries in `crawl_manifest.json`, and confirm the single no-audio slideshow item (`7709372899198602514`, `#19`) is explicitly accounted for (`skipped_no_audio_count = 1`).
   - Verify `artifacts/indexes/bm25-m3_3-pilot/` (`21,758` indexed documents = `21,748` historical + `10` fresh transcribed) retrieves at least `5` (`10/10` actual) fresh transcribed `M3.3` videos by exact `video_id` using the recorded probe queries.
   - Verify `docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl` contains `30/30` unique pilot records with `15` `K` and `15` `N` assignments and `100%` `human_verified == True`.
4. **Repeated Dual-Sink Ingestion Readiness (`M3.1` Contract):** Execute an isolated temporary-directory probe confirming idempotent replay and `update_existing=True` comment-only enrichment preserve existing `transcript` / `whisper_segments` / historical rows without mutating base snapshot bytes.

### 2.2 Per-Downstream Modality Readiness Matrix
Rather than treating partially populated multimodal batches as an all-or-nothing boolean, `run_g3_checks.py` computes an explicit readiness status per downstream milestone consumer:

| Downstream Task | Required Modalities & Thresholds | Observed Pilot Evidence (`m3_3_pilot_snapshot_v1`) | Readiness Status |
| --- | --- | --- | --- |
| `M4.1` (`Timestamp / Prosody CPU Evaluation`) | `<= 60` min successful pilot `.mp3` audio; `<= 20` min & `>= 50` utterances available for 2-person review | `29/30` (`96.67%`) valid `64 kbps` `.mp3` files (`46.683` min total; `27/30 = 90.00%` pure in-domain F&B audio; `436` Whisper segments already observed on first `10` videos = `16.683` min) | **`READY_UNBLOCKED`** |
| `M4.2` (Audio Prosody Join Extension, post-`M4.1`) | Accepted `M4.1` audio-derived segments/prosody on fresh audio-bearing items | Text/flag study `COMPLETE`; fresh audio join gated on `M4.1` completion | **`GATED_ON_M4_1`** |
| `M5.1` (`Duplicate / Contact / Noise Indicators`) | `>= 150` (up to `300`) real pilot comments across video-disjoint threads | `collected_comments_count = 0` (`comment_coverage_rate = 0.0` under `yt-dlp`-only pilot run) | **`BLOCKED_PENDING_COMMENT_BACKFILL`** |
| `M5.2` (`Four-Aspect Sentiment with Source Spans`) | `>= 120` (up to `200`) real pilot text units across `>= 10` videos including viewer comments for KOC-vs-viewer overlap (`>= 3` viewer comments/aspect) | Creator captions (`30`) & pilot transcripts (`10`) present, but viewer `fact_comments` = `0` rows | **`BLOCKED_PENDING_COMMENT_BACKFILL`** |

### 2.3 Empirical Yield, Domain-Purity & Four-Component Capacity Model
`run_g3_checks.py` derives all projections strictly from measured `M3.3` telemetry (`m3_3_pilot_receipt.json`, `crawl_manifest.json`, `sample_inspection_sheet.jsonl`) without hardcoded synthetic throughput constants:

1. **Observed Yield & Domain-Purity Rates:**
   - `capture_yield_rate = 30 / 50 = 0.6000` (`20` candidates skipped by historical/cutoff/ceiling filters, `0` failed).
   - `audio_availability_rate = 29 / 30 = 0.9667` (`1` photo slideshow without audio stream).
   - `pure_fnb_domain_rate_all = 27 / 30 = 0.9000` across audio-bearing pure F&B videos (`28 / 30 = 0.9333` including no-audio convenience-store promo `#19`; `1/30` mixed photo/food festival `#13`; `1/30` out-of-domain museum vlog `#26`).
   - `effective_usable_fnb_audio_yield_per_candidate = (30 / 50) * (27 / 30) = 0.5400` (`27` pure F&B audio videos per `50` candidates).
2. **Stage-Decomposed Runtime & Resource Model:**
   - **Stage 1 — Network Discovery & Media/Comment Capture:** Observed `~539.9 s` for `30` videos (`18.00 s/succeeded video`, `22.65 MB` raw batch disk = `754.9 KB/video`). For rate-limited `TikTokApi` comment pagination, model explicit conservative per-video session/jitter + retry overhead (`1.25x`–`1.50x` retry buffer, bounded by `session_deadline_seconds <= 3,600 s`).
   - **Stage 2 — Local CPU ASR (`faster-whisper/small-cpu-int8`):** Observed `197.269 s` over `16.683` audio minutes (`10` videos) -> **`RTF = 0.1971`** (`11.825 s` CPU wall time per audio minute, `1,009.46 MiB` peak RSS). Full `M4.1` transcription of all `29` pilot `.mp3` files (`46.683` audio min, or `19` remaining `.mp3`s = `30.000` min) projects **`~552.0 s` total (`~354.7 s` incremental)** = **`0.153` CPU hours** (`3.8%` of `M4.1`'s `4.0` CPU-hour ceiling) and `~1.0–3.2 GiB` peak RSS (`<= 8.0 GiB` ceiling).
   - **Stage 3 — Dual-Sink Parquet Publication & BM25 Rebuild:** Observed `~7.0 s` fixed corpus-scale step (`58.97 MiB` Gold snapshot + `44.13 MiB` BM25 index per published version, `3,214.92 MiB` combined pipeline peak RSS).
   - **Stage 4 — Two-Contributor Inspection & Double-Annotation Effort:** Estimate person-minutes per stage using explicit inspection/annotation rates (`M3.3` sample inspection, `M4.1` `>= 50`-utterance timestamp/text reference verification, `M5.1` `150–300` comment double-annotation + adjudication, `M5.2` `120–200` unit aspect/span double-annotation + adjudication).

### 2.4 Post-Pilot Collection Budget Decision
Compare three explicit post-pilot resource options and codify **Option 1** as the primary-owner decision:
- **Option 1 (Authorized Bounded Budget — Decoupled Comment-Only Backfill, `0` New Videos):**
  - **Video/Audio Crawl:** Frozen at `0` new videos (`M4.1` uses the existing `29` verified `.mp3` files = `46.683` min directly, avoiding redundant network crawl and anti-bot exposure).
  - **Comment Backfill Ceiling:** Strictly `1` bounded `TikTokApiCollectorProvider` (`--backend tiktokapi` or `--backend auto`) comment-enrichment session targeting only the `30` existing `m3_3_pilot_snapshot_v1` `video_id`s (`max_videos = 30`, `max_comments_per_video = 50`, `max_comments_total = 1,000`, `max_audio_minutes = 0.0`, `session_deadline_seconds = 3,600.0`, `USD 0` spend, immediate fail-closed halt on `AntiBotChallengeError`), ingested via `ingest_incremental_batch_to_gold(..., update_existing=True)` into a new immutable snapshot (`m3_3_pilot_snapshot_v2_comments`) without overwriting `m3_3_pilot_snapshot_v1`.
- **Option 2 (Rejected — Full Second `30`-Video Crawl Batch):** Incurs additional `~12–18` min capture/ASR runtime, `~126 MiB` extra snapshot/index disk, and unnecessary anti-bot exposure despite `M4.1` already having `46.683` min (`27` pure F&B `.mp3`s).
- **Option 3 (Contingency Fallback if Comment Backfill Hits Persistent Anti-Bot Block):** Do not bypass CAPTCHA or scrape third-party paid proxies; retain `G2 = PASS` historical core + `M4.1` audio evaluation, record `M5.1`/`M5.2` live comment acquisition as `BLOCKED`, and keep comment filtering in `diagnostic_only_unvalidated` mode per `M5.G`.

## 3. Deliverables & File Layout

1. `tests/unit/test_m3_g_gate_checks.py` — Unit tests for `run_g3_checks.py` covering SHA-256 tamper detection, modality readiness classification, domain-purity/yield math, 4-component capacity projections, `M3.1` comment-enrichment preservation, and bounded backfill contract invariants.
2. `docs/reports/milestones/M3.G/evidence/run_g3_checks.py` — Deterministic executable `G3` verification script producing `g3_verification_receipt.json` with `0` byte mutations to repository data/artifacts.
3. `docs/reports/milestones/M3.G/evidence/g3_verification_receipt.json` — Machine-readable verification receipt containing SHA-256 hashes, readiness matrix, yield/domain breakdown, and capacity projections.
4. `docs/reports/milestones/M3.G/evidence/g3-gate-decision-receipt.json` — Machine-readable gate decision receipt recording `K`'s primary-owner decision, explicit comment-backfill ceilings, and `n_peer_approval = "PENDING_N_REVIEW"`.
5. `docs/reports/milestones/M3.G/README.md` & `docs/reports/milestones/M3.G/evidence/workflow.md` — Main `M3.G` milestone report and Superpowers execution/verification ledger in English.
6. `docs/reports/milestones/README.md` — Updated quick review index adding the single canonical `M3.G` row.

## 4. Acceptance Criteria

- `run_g3_checks.py` exits `0`, confirming `G0`/`G1`/`G2` = `PASS`, `M3.1`–`M3.3` = `COMPLETE`, `30/30` `human_verified == True`, `10/10` (`>= 5`) fresh transcribed videos searchable by exact `video_id`, `M3.1` comment-enrichment idempotency/preservation, and `0` byte mutations across `20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, and `audio_64k/*.mp3`.
- `g3_verification_receipt.json` and `M3.G/README.md` report exact measured `RTF` (`0.1971`), capture yield (`0.60`), audio yield (`29/30`), pure F&B audio yield (`27/30`), comment coverage (`0.0`), 4-component runtime/RAM/disk/annotation projections, and the per-downstream readiness matrix (`M4.1 = READY_UNBLOCKED`, `M5.1/M5.2 = BLOCKED_PENDING_COMMENT_BACKFILL`).
- Post-pilot collection budget explicitly freezes new video/audio crawling (`0` new videos) and bounds comment-only backfill to the `30` pilot `video_id`s (`<= 50` comments/video, `<= 1,000` total, `USD 0`, fail-closed anti-bot policy), with fallback behavior documented.
- Two-person gate governance is respected (`K` primary recommendation recorded; `N` peer review explicitly tracked as pending before flipping global plan `G3` from `NOT_RUN` to `PASS`).
- Full `pytest`, Linux and `--platform win32` `mypy`, `ruff`, and `python3 scripts/check_secrets.py` (`0` leaks) pass, with `0` machine-specific workstation absolute paths in authored docs/evidence and exact `README.md` + `evidence/` + `superpowers/{spec.md, plan.md}` directory structure.
