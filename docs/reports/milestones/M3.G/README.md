# M3.G — Bounded Capture-to-Transcript-to-Search & Capacity Gate (`G3`)

- Status: IN_PROGRESS (`K` primary-owner `G3` verification probe, per-downstream modality readiness matrix, 4-component capacity projections, and bounded comment-backfill decision complete; awaiting `N` peer review & co-approval before changing global `G3` from `NOT_RUN`)
- Execution date: 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.G`)
- Primary owner: Trần Đình Khương (`K`, `2` pts) · Peer reviewer & gate co-approver: Nguyễn Việt Nguyên (`N`, `2` pts)
- Repository version: `feat/k-m3.g-gate-decision` (`4479dd24`+)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the deterministic Gate `G3` (`M3.G`) verification probe ([run_g3_checks.py](evidence/run_g3_checks.py) -> [g3_verification_receipt.json](evidence/g3_verification_receipt.json)) over the completed `M3.1`–`M3.3` incremental pipeline and real pilot artifacts (`m3_3_pilot_snapshot_v1`, `bm25-m3_3-pilot`, and `29` `64 kbps` `.mp3` files) at **`USD 0` spend** with **`0` byte mutations** to any historical or pilot dataset:

- **Vertical Slice & Cryptographic Lineage Verified (`PASS`):** `G0`, `G1` (local-only), and `G2` are `PASS`; `M3.1`, `M3.2`, and `M3.3` are `COMPLETE`. All Parquet checksums in `20261118_taxonomy_fix_v1` (`70,996` historical videos) and `m3_3_pilot_snapshot_v1` (`71,026` videos, `436` voice segments, `30` ABSA rows), all `29/29` `64 kbps` `.mp3` SHA-256 digests (`22,524,055` B, `46.683` audio min), **`10/10` (`>= 5`)** fresh ASR-transcribed video retrievals on `bm25-m3_3-pilot`, **`30/30` (`15 K` + `15 N`)** human sample verifications, and non-destructive `M3.1` `update_existing=True` comment-backfill preservation (`436` voice segments & `21,758` transcripts preserved intact) passed in `8.742 s`.
- **Per-Downstream Modality Readiness Matrix (`Dagster`-Style Blocking Checks):**
  - **`M4.1` (`Timestamp / Prosody CPU Evaluation`) = `READY_UNBLOCKED`:** `29/30` (`96.67%`) valid `64 kbps` `.mp3` files (`46.683` min `<= 60.0` cap), including **`27/30` (`90.00%` of batch; `93.10%` of `.mp3`s)** confirmed pure in-domain Vietnamese F&B speech (`#13` mixed photo/food festival, `#19` no-audio slideshow promo, `#26` out-of-domain museum vlog). Full `29`-file CPU ASR (`faster-whisper/small-cpu-int8`, measured `RTF = 0.1971`) projects **`552.07 s` (`9.20` min = `0.1534` CPU hours `<< 4.0` CPU-hour cap; `354.78 s` incremental for the remaining `30.0` min)** and `3.14 GiB <= 8.0 GiB` RAM.
  - **`M5.1` & `M5.2` (Real-Comment Diagnostics) = `BLOCKED_PENDING_COMMENT_BACKFILL`:** Initial `yt-dlp` capture recorded `collected_comments_count = 0` (`comment_coverage_rate = 0.0`). Real-comment evaluation stays gated until comment-only backfill populates `>= 150` real comments (`M5.1`) across `>= 10` videos (`M5.2`).
- **Authorized Post-Pilot Budget ([g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json)):** Freeze new video/audio crawling at **`0` additional videos** and authorize **strictly `1` bounded `TikTokApiCollectorProvider` comment-only backfill pass** targeting the existing `30` pilot `video_id`s (`<= 50` comments/video, `<= 1,000` comments total, `0.0` audio min, `<= 3,600 s` deadline, `~511 s` projected with `1.4x` retry buffer, `USD 0`, fail-closed on `AntiBotChallengeError`), ingested via `M3.1` (`update_existing=True`) into `m3_3_pilot_snapshot_v2_comments`. Per two-person governance, `n_peer_approval` remains `"PENDING_N_REVIEW"` until `N` concurs.

## Work performed

- **Grounded `M3.G` in production MLOps data-readiness standards ([spec.md](superpowers/spec.md), [plan.md](superpowers/plan.md)):** Combined `DVC`/`LakeFS`-style end-to-end SHA-256 verification (`20261118_taxonomy_fix_v1` -> `m3_3_pilot_snapshot_v1` + `crawl_manifest.json` `.mp3` digests), `Dagster`-style per-downstream modality blocking checks, effective in-domain usable yield (`0.60 capture * 0.90 pure_fnb_audio = 0.54` per candidate), and stage-decomposed capacity modeling.
- **Implemented TDD `G3` verification suite ([run_g3_checks.py](evidence/run_g3_checks.py), [test_m3_g_gate_checks.py](../../../../tests/unit/test_m3_g_gate_checks.py)):** Verified `.mp3` SHA-256 tamper detection, `15 K / 15 N` human verification enforcement, Parquet checksum tamper detection, modality readiness transitions (`>= 150` comments & `>= 10` videos), and live temporary-workspace `M3.1` `update_existing=True` sparse comment-backfill preservation (`436` voice segments retained).

## Measured Yield, Readiness & Capacity Summary

| Metric / Stage | Observed `M3.3` Measurement | Downstream Projection & Budget Rule |
| --- | --- | --- |
| Candidate -> Succeeded -> Audio -> Pure F&B Audio | `50` -> `30` (`60.0%`) -> `29` (`96.7%`) -> **`27` (`90.0%`)** | Effective pure F&B audio yield = **`0.54` videos/candidate** (`#13` mixed, `#19` no-audio, `#26` museum OOD) |
| Stage 1: Network Discovery & Media Capture I/O | `539.885 s` (`18.00 s/video`), `21.60 MiB` raw batch | Frozen at **`0` new videos**; `1` comment-only pass (`30` existing IDs, `<= 1,000` comments) projected at **`~511 s`** (`1.4x` retry buffer, `<= 3,600 s` cap) |
| Stage 2: CPU ASR (`faster-whisper/small-cpu-int8`) | `197.269 s` / `16.683` min (**`RTF = 0.1971`**, `1,009.46 MiB` RSS) | Full `29`-file `M4.1` (`46.683` min): **`552.07 s` total (`354.78 s` incremental)** = **`0.1534` CPU h `<= 4.0` CPU h** |
| Stage 3: Dual-Sink Gold + BM25 Index Publish | `~7.0 s` (`56.23 MiB` Gold + `42.08 MiB` BM25, `3,214.92 MiB` peak RSS) | Comment-only snapshot `m3_3_pilot_snapshot_v2_comments` adds **`~56.5 MiB`** without mutating `v1` |
| Stage 4: Two-Person Inspection & Annotation | `M3.3` `30/30` verified (`~60` person-min completed) | `M4.1` (`>= 50` utterances): `~90` min · `M5.1` (`150–300` comments): `~150` min · `M5.2` (`120–200` units): `~180` min |

## Outputs

| File | Purpose |
| --- | --- |
| [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) | Primary-owner `G3` decision receipt, comment-only backfill budget, and `PENDING_N_REVIEW` status |
| [g3_verification_receipt.json](evidence/g3_verification_receipt.json) | Machine-readable `G3` SHA-256 lineage, readiness matrix, domain-purity yield, and capacity receipt |
| [run_g3_checks.py](evidence/run_g3_checks.py) | Deterministic executable `G3` verification and capacity-modeling script |
| [g3_checks.log](evidence/g3_checks.log) | Console execution log (`PASS in 8.742s`, `10/10` searchable, `0` byte mutations) |
| [workflow.md](evidence/workflow.md) | Superpowers TDD workflow ledger, MLOps grounding, rulings, and verification commands |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M3.G/evidence/run_g3_checks.py` | PASS (`8.567 s`, `0` byte mutations) | `G0/G1/G2` + `M3.1–M3.3` SHA-256 lineage, `29` `.mp3` digests, `10/10` BM25 searchability, `30/30` inspection, `M3.1` `update_existing=True` dedup/preservation; [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| `python3 -m pytest tests/unit/test_m3_g_gate_checks.py -v` | PASS (`6 passed`) | Tamper/orphan detection (`.mp3` & Parquet), fail-closed `G0`/`M3.x` receipts, `15 K / 15 N` completeness & ID parity, `>=150` comments & `>=10` videos readiness transitions, dynamic capacity & dedup enrichment probe |
| `python3 -m pytest -q` | PASS (`224 passed`) | Full workspace unit, contract, smoke, and evaluation regression suite |
| `python3 -m mypy packages apps pipelines .../run_g3_checks.py .../test_m3_g_gate_checks.py` & `--platform win32` | PASS (`0` issues on Linux & `win32`) | Static typing across repository packages, pipelines, and `M3.G` probe/tests |
| `python3 scripts/check_secrets.py` | PASS (`0` secret leaks) | Full repository secret hygiene check |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `fact_comments.parquet` in `m3_3_pilot_snapshot_v1` has `0` rows (`yt-dlp` extractor limitation) | Blocks `M5.1` (`>= 150` real comments) and `M5.2` (`>= 10` videos viewer overlap) real-data evaluation; does **not** block `M4.1` (`29` `.mp3`s ready) | Execute the `1` authorized `TikTokApiCollectorProvider` comment-only backfill pass (`<= 1,000` comments) -> `M3.1` (`update_existing=True`) before `M5.1`/`M5.2` live annotation; if anti-bot blocked, apply Option 3 contingency (`diagnostic_only_unvalidated`) |
| `N` reciprocal peer review & gate co-approval pending | Per two-person rule, global `G3` remains `NOT_RUN` in [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) until `N` reproduces `run_g3_checks.py` and signs off | `N` peer review on PR (`2` effort points) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Repeated `M3.1` ingest & `M3.3` minimum vertical slice (`>= 5` searchable real fresh videos) | Met (`10/10` searchable; `436` voice segments preserved under `update_existing=True` probe) | [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| Measured audio `RTF`, capture yield, domain purity, comment coverage & annotation time | Met (`RTF = 0.1971`, `0.60` capture, `29/30` audio, `27/30` pure F&B audio, `0.0` comments, stage person-min estimates) | [g3_verification_receipt.json](evidence/g3_verification_receipt.json) |
| Further collection estimated from observed throughput + retry/review cost & bounded by explicit budget | Met (`0` new videos; `1` comment-only backfill `<= 50/video`, `<= 1,000` total, `USD 0`, contingency fallback defined) | [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) |
| Two-person reciprocal gate confirmation (`K` + `N`) | In progress (`K` primary decision recorded; awaiting `N` peer sign-off) | [g3-gate-decision-receipt.json](evidence/g3-gate-decision-receipt.json) |

Final status: **`M3.G` is `IN_PROGRESS` (primary-owner `G3` deliverable complete; awaiting `N` peer review to finalize `M3.G -> COMPLETE` / `G3 -> PASS`)**. Direct handoff to **`M4.1`**: `29` verified `.mp3` files (`46.683` min total; `27` pure F&B `.mp3`s excluding `#13` mixed and `#26` museum OOD) under `data/raw_incremental/m3_3_pilot_run/batch/audio_64k/`.
