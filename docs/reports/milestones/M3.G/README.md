# M3.G — Bounded Capture-to-Transcript-to-Search & Capacity Gate (`G3 = PASS`)

- Status: COMPLETE (All technical `G3` checks, `M3.1` repeated-ingest replays, `29`-`.mp3` SHA-256 verification, `30/30` `N`+`K` inspection timings (`33.0` min total), and `v2`/`v5` comment readiness checks **PASS**; joint `K` + `N` confirmation recorded in [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) on `2026-11-27T08:39:15+07:00`, flipping `G3 = PASS`)
- Execution date: 2026-11-23 to 2026-11-27 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`)
- Primary owner: Trần Đình Khương (`K`, `2` pts) · Peer reviewer & replay contributor: Nguyễn Việt Nguyên (`N`, `2` pts)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed and unified both `N`'s repeated-ingest replay preparation ([g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json)) and `K`'s deterministic Gate `G3` verification suite ([run_g3_checks.py](evidence/run_g3_checks.py) -> [g3_verification_receipt.json](evidence/g3_verification_receipt.json)) across all four Gold snapshots (`20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`, and `m3_3_playwright_comments_20261125_v5`) at **`USD 0` spend** with **`0` byte mutations**:

- **Vertical Slice, Replays & Cryptographic Lineage (`PASS` in `29.639 s`):** `G0`, `G1` (local-only), and `G2` are `PASS`; `M3.1`, `M3.2`, and `M3.3` are `COMPLETE`. All Parquet SHA-256 digests across `base` (`70,996` historical videos), `v1` (`71,026` videos, `436` voice segments), `v2` (`452` native-ID comments across `28/30` pilot videos), and `v5` (`2,823` DOM comments across `118/130` fresh F&B videos), all `29/29` `64 kbps` `.mp3` SHA-256 digests (`22,524,055` B, `46.683` audio min), **`10/10` (`>= 5`)** fresh ASR-transcribed video retrievals on `bm25-m3_3-pilot`, **`30/30` (`15 K` + `15 N`)** human verifications (`N = 15.0` min + `K = 18.0` min = **`33.0` person-minutes**), and disposable `/tmp` `M3.1` repeated-ingest (`5.64 s` / `6.14 s`) + duplicate-comment `update_existing=True` preservation probes (`3 -> 2` deduplicated comments, `436` voice segments preserved) passed.
- **Per-Downstream Modality Readiness Matrix (`ALL READY_UNBLOCKED`):**
  - **`M4.1` (`Timestamp / Prosody CPU Evaluation`) = `READY_UNBLOCKED`:** `29/30` (`96.67%`) valid `64 kbps` `.mp3` files (`46.683` min `<= 60.0` cap; **`27/30 = 90.0%`** pure in-domain F&B audio). `N` has already processed all `29` `.mp3`s (`RTF = 0.009` prosody, `436/436` `audio_derived`) and verified `38/38` `N` utterances in [M4.1](../M4.1/README.md).
  - **`M5.1` (`Duplicate / Contact / Noise Indicators`) = `READY_UNBLOCKED`:** `452` native-ID comments across `28` pilot videos in `m3_3_pilot_snapshot_v2` (`>= 150` comments & `>= 10` videos); `300`-comment pool exported with `N` `180/180` verified in [M5.1](../M5.1/README.md).
  - **`M5.2` (`Four-Aspect Sentiment with Source Spans`) = `READY_UNBLOCKED`:** `452` native-ID viewer comments across `28` pilot videos in `v2` (`180`-unit pool exported with `N` `115/115` verified in [M5.2](../M5.2/README.md)), plus `2,429` video-disjoint expansion comments (`90` videos) in `data/annotations/absa_train_video_disjoint_v1.jsonl`.
- **Post-Pilot Collection Freeze ([g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json)):** Because all downstream `M4`/`M5` modalities are populated on disk, **all further live TikTok network crawling is frozen (`0` additional sessions authorized)**. Per two-person governance, `M3.G` records `K`'s primary-owner `PASS` recommendation and awaits `N`'s final co-sign on the unified `v1`/`v2`/`v5` receipt before flipping global `G3` from `NOT_RUN` to `PASS`.

## Work performed

- **`N` repeated-ingest replay & throughput baseline ([g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json)):** Executed `/tmp` `ingest_incremental_batch_to_gold` replays (`update_existing=False` in `5,635.45 ms`, `update_existing=True` in `6,140.35 ms`, `zero_duplicate_keys=true`), measured `29`-`.mp3` byte/minute rates (`0.4601 MiB/min`), and recorded `N_minutes = 15.0`.
- **`K` MLOps readiness probe, whole-branch review hardening & `v1`/`v2`/`v5` unification ([run_g3_checks.py](evidence/run_g3_checks.py), [test_m3_g_gate_checks.py](../../../../tests/unit/test_m3_g_gate_checks.py)):** Implemented `6` TDD unit tests covering `.mp3` SHA-256/orphan checks, fail-closed `G0`/`M3.x` receipts, `15 K / 15 N` completeness & ID parity, `>= 150` comments & `>= 10` videos readiness transitions, dynamic capacity projections, and `3 -> 2` duplicate-comment `update_existing=True` preservation; recorded `K_minutes = 18.0` (`33.0` min total) and verified all four Gold snapshots end-to-end.

## Measured Yield, Readiness & Capacity Summary

| Metric / Stage | Observed Measurement | Downstream Status & Policy |
| --- | --- | --- |
| Candidate -> Succeeded -> Audio -> Pure F&B Audio (`v1`) | `50` -> `30` (`60.0%`) -> `29` (`96.7%`) -> **`27` (`90.0%`)** | Effective pure F&B audio yield = **`0.54` videos/candidate** (`#13` mixed, `#19` no-audio, `#26` museum OOD) |
| Stage 1: Network Capture & Comment Enrichments (`v1`, `v2`, `v5`) | `v1` capture `539.885 s` · `v2` `TikTokApi` `41.141 s` (`452` comments / `28` vids) · `v5` Playwright `2,383.1 s` (`2,823` comments / `118` vids) | **Frozen at `0` new sessions**; `M5.1` & `M5.2` **`READY_UNBLOCKED`** |
| Stage 2: CPU ASR (`faster-whisper/small-cpu-int8`) | `197.269 s` / `16.683` min (**`RTF = 0.1971`**, `1,009.46 MiB` RSS) | Full `29`-file `M4.1` (`46.683` min) projected **`552.07 s` (`0.1534` CPU h `<= 4.0` CPU h)**; **`M4.1 = READY_UNBLOCKED`** |
| Stage 3: Dual-Sink Gold Replay & BM25 Publish | Replay `5.64 s` / `6.14 s` (`0` duplicates, `3,214.92 MiB` max RSS) | `100%` SHA-256 immutability verified across `base`, `v1`, `v2`, and `v5` |
| Stage 4: Two-Person Inspection & Annotation | `M3.3` `30/30` verified in **`33.0` min** (`N = 15.0` min + `K = 18.0` min) | `M4.1` (`60` utts): `~90` min · `M5.1` (`300` comments): `~150` min · `M5.2` (`180` units): `~180` min |

## Outputs

| File | Purpose |
| --- | --- |
| [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) | Primary-owner `G3` recommendation (`PASS_FREEZE_FURTHER_CRAWLING`), `N`+`K` inspection timings, and `0`-session freeze |
| [g3_verification_receipt.json](evidence/g3_verification_receipt.json) | Unified `G3` SHA-256 lineage (`base`, `v1`, `v2`, `v5`), readiness matrix (`ALL READY_UNBLOCKED`), and capacity receipt |
| [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json) | `N`'s `M3.1` `update_existing=False/True` replay timings (`5.64 s` / `6.14 s`) and `29`-`.mp3` throughput receipt |
| [run_g3_checks.py](evidence/run_g3_checks.py) | Deterministic executable `G3` verification and capacity-modeling script |
| [g3_checks.log](evidence/g3_checks.log) | Console execution log (`PASS in 29.639s`, `M4.1/M5.1/M5.2 = READY_UNBLOCKED`, `10/10` searchable) |
| [workflow.md](evidence/workflow.md) | Two-contributor (`N` + `K`) Superpowers TDD workflow ledger and verification SHA-256 digests |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M3.G/evidence/run_g3_checks.py` | PASS (`29.639 s`, `0` byte mutations) | `G0/G1/G2` + `M3.1–M3.3`, SHA-256 across `base`/`v1`/`v2`/`v5` & `29` `.mp3`s, `10/10` BM25 searchability, `30/30` inspection, `M3.1` dedup/preservation; [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| `python3 -m pytest tests/unit/test_m3_g_gate_checks.py -v` | PASS (`6 passed`) | Tamper/orphan detection, fail-closed `G0`/`M3.x` receipts, `15 K / 15 N` completeness & ID parity, `>=150` comments & `>=10` videos readiness transitions, dynamic capacity & dedup probe |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`265 passed, 10 skipped`; `117` source files `0` type issues) | Full unified workspace regression and cross-platform static typing |
| `python3 scripts/check_secrets.py` | PASS (`0` secret leaks) | Full repository secret hygiene check |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| None (further live crawling frozen at `0` new sessions) | All `M4`/`M5` datasets are verified on disk; any future live TikTok crawl requires a new bounded gate budget | Preserved in [M6.G](../M6.G/README.md) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Repeated `M3.1` ingest & `M3.3` minimum vertical slice (`>= 5` searchable real fresh videos) | Met (`5.64 s` / `6.14 s` replays; `10/10` searchable; `436` voice segments preserved) | [g3_capacity_and_replay_receipt.json](evidence/g3_capacity_and_replay_receipt.json), [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| Measured audio `RTF`, capture yield, domain purity, comment coverage & annotation time | Met (`RTF = 0.1971`, `0.60` capture, `27/30` pure F&B audio, `93.33%` `v2` comment coverage / `2,823` `v5` comments, `33.0` min `N`+`K` inspection) | [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| Further collection estimated & bounded by explicit budget | Met (`0` further live sessions authorized; all `M4`/`M5` datasets on disk) | [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) |
| Two-person reciprocal gate confirmation (`K` + `N`) | Met (`K` & `N` confirmed `G3 = PASS`, `2026-11-27T08:39:15+07:00`) | [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) |

Final status: **`M3.G` is `COMPLETE` and Gate `G3` is `PASS` (`0` additional live crawl sessions authorized; `M4`/`M5` datasets frozen on verified Gold snapshots)**.
