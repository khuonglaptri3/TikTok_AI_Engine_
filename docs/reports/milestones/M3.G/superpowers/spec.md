# M3.G — Specification: Bounded Capture-to-Transcript-to-Search & Resource Capacity Gate (`G3`)

- **Task ID:** `M3.G` (Gate `G3`)
- **Created:** `2026-11-23`, unified `2026-11-26` (`Asia/Ho_Chi_Minh`)
- **Primary Owner (`M3.G` Gate Decision):** Trần Đình Khương (`K`, `2` effort points)
- **Peer Reviewer & Replay Preparation Contributor:** Nguyễn Việt Nguyên (`N`, `2` effort points)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`, lines 57, 100, 127)
- **Cost & Access Constraint:** Strictly `USD 0` spend, local CPU execution, zero CAPTCHA/anti-bot bypass, and zero historical TikTok re-crawling.

## 1. Purpose & Governance Model

`M3.G` evaluates whether the `M3` incremental ingestion subsystem (`M3.1` dual-sink converter, `M3.2` bounded collector worker, and `M3.3` capped real-data capture-to-transcript-to-search pilot plus comment enrichments) satisfies its minimum vertical slice, cryptographic data-readiness invariants, and local CPU resource budgets, and locks post-pilot collection boundaries.

Per the two-person reciprocal governance rule in `TikTok_AI_Engine_Milestone.md` (line 69), neither contributor approves a gate unilaterally. `N` prepared the initial `M3.1` replay timing and `29`-`.mp3` throughput evidence ([g3_capacity_and_replay_receipt.json](../evidence/g3_capacity_and_replay_receipt.json)); `K` implemented the deterministic `G3` verification suite ([run_g3_checks.py](../evidence/run_g3_checks.py)), recorded `K`'s inspection timing (`18.0` min alongside `N`'s `15.0` min = `33.0` min total), verified both `m3_3_pilot_snapshot_v2` (`452` native comments across `28/30` pilot videos) and `m3_3_playwright_comments_20261125_v5` (`2,823` DOM comments across `118/130` fresh F&B videos), and published `g3-gate-decision-receipt.json` (`n_peer_approval = "PENDING_N_FINAL_CONCURRENCE"` before flipping global `G3` from `NOT_RUN` to `PASS`).

## 2. Scope & Technical Architecture

Grounded in MLOps data-readiness gate patterns (`DVC`/`LakeFS` cryptographic SHA-256 snapshot verification combined with `Dagster`-style per-downstream blocking asset checks and stage-decomposed capacity modeling), `M3.G` comprises four verification and decision components:

1. **Cryptographic Snapshot Lineage & Non-Mutation Verification:**
   - Fail-closed verification of prerequisite gates (`G0 == PASS`, `G1 == PASS` local-only, `G2 == PASS`) and upstream tasks (`M3.1 == COMPLETE`, `M3.2 == COMPLETE`, `M3.3 == COMPLETE`).
   - Pre- and post-probe SHA-256 verification (`0` byte mutations) across `data/corpus/20261118_taxonomy_fix_v1/` (`70,996` historical videos), `data/corpus/m3_3_pilot_snapshot_v1/` (`71,026` videos, `436` voice segments, `0` comments), `data/corpus/m3_3_pilot_snapshot_v2/` (`71,026` videos, `452` native-ID comments across `28` pilot videos), `data/corpus/m3_3_playwright_comments_20261125_v5/` (`71,126` videos, `2,823` DOM comments across `118` fresh F&B videos), and all `29` `64 kbps` `.mp3` files (`22,524,055` B, `46.683` min) in `crawl_manifest.json`.
   - `10/10` (`>= 5`) fresh ASR-transcribed video searchability re-check on `artifacts/indexes/bm25-m3_3-pilot/`, `30/30` (`15 K / 15 N`) `human_verified == True` parity check, and disposable `/tmp` `M3.1` repeated-ingest & sparse `update_existing=True` deduplication/preservation probes (`5.64 s` / `6.14 s` replay + `3 -> 2` deduplicated comment merge preserving `436` voice segments).
2. **Per-Downstream Modality Readiness Matrix:**
   - `M4.1` (`Timestamp / Prosody CPU Evaluation`) = **`READY_UNBLOCKED`** (`29` verified `.mp3`s = `46.683` min `<= 60.0` cap; `27/30 = 90.0%` pure in-domain F&B audio).
   - `M4.2_audio_join` = **`GATED_ON_M4_1`**.
   - `M5.1` (`Duplicate / Contact / Noise Indicators`) & `M5.2` (`Four-Aspect Sentiment with Source Spans`) = **`READY_UNBLOCKED`** (`452` native-ID comments across `28` pilot videos in `m3_3_pilot_snapshot_v2` plus `2,823` DOM comments across `118` videos in `v5`, exceeding `>= 150` comments and `>= 10` videos).
3. **Empirical Yield, Domain-Purity & Four-Component Capacity Model:**
   - Captures exact observed rates (`capture_yield_rate = 0.60`, `audio_availability_rate = 0.9667`, `pure_fnb_audio_rate = 0.90`, `effective_usable_fnb_audio_yield_per_candidate = 0.54`, CPU Whisper `small` `RTF = 0.1971`, `0.1534` CPU hours projected for full `29`-file `M4.1` ASR `<< 4.0` CPU-hour cap, and `33.0` combined person-minutes across `N = 15.0` min + `K = 18.0` min `M3.3` sample inspection).
4. **Post-Pilot Collection Freeze:**
   - With `29` verified `.mp3` files (`46.683` min), `452` native pilot comments (`v2`), and `2,823` Playwright comments (`v5` / `2,429` video-disjoint train comments across `90` expansion videos) already on disk, **all further live TikTok network crawling is frozen at `0` new sessions** unless a new bounded gate budget is explicitly authorized.
