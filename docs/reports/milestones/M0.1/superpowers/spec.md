# M0.1 — Specification: Historical Asset Preservation, Pinned Recovery & Provenance Baseline

- **Date:** 2026-11-16 (initial baseline); revised 2026-11-18 (two-person recovery & provenance reconciliation)
- **Task ID:** `M0.1`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.1`)

## Scope & Requirements
1. **Secret Sanitization & Hygiene:** Purge all hardcoded Gemini (`AIzaSy*`) and third-party API keys across legacy coursework files (`149` keys across `16` files) and enforce zero-leak workspace scanning via `scripts/check_secrets.py`.
2. **Pinned Historical Asset Recovery & Byte Preservation:**
   - Recover permitted historical data assets from the pinned upstream repository `TrggTin/21KHDL-TikTok-Analytics` at revision `f142e5656a220f94f8024de168b0832754b3bd9e` without historical TikTok recrawling or executing upstream code.
   - Explicitly separate the two inventory scopes:
     - **Upstream `data/` tree:** `37,837` blobs (`1,475,677,482` logical bytes).
     - **Mapped legacy app tables (`3` files, `28,607,219` logical bytes):** `src/app/trend_analysis/data/final_location_food_data.parquet`, `src/app/video_analysis/data/content_analyse.csv`, and `src/app/video_analysis/data/preprocessed_video.parquet` mapped under `data/legacy_app_data/`.
     - **Combined selected pinned inventory:** `37,840` files (`1,504,284,701` logical bytes), kept distinct from the unverified prior owner-copy claim (`37,840` files / `~1.50 GB` whose unavailable original file list is not reconstructed by assertion).
   - Verify every restored file's byte size, pinned Git blob SHA1, and archive-derived SHA256 (`restore-input-manifest.json` SHA256 `11843e609ade980f354b153f71f29bec5edd6ec349d2176b5f2588a98eb83bc1`), and verify that zero pre-existing local files with differing bytes are overwritten (`2` pre-existing files preserved byte-for-byte).
3. **Gold Snapshot & BM25 Provenance Baseline:**
   - Record verified counts, schemas, and SHA256 checksums for active Gold snapshot `data/corpus/20261117_recovered_v1` (`manifest.json` SHA256 `10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4`; `264` creators in `dim_creators.parquet`; `70,996` videos across `49` columns in `fact_videos.parquet`; `21,748` accepted transcripts; `23,448` POI-tagged rows; `5,798` `is_ec_video` rows; date window `2023-11-25` to `2025-03-19`) while retaining `data/corpus/20261116_v1/manifest.json` as historical evidence.
   - Record verified counts, parameters, and SHA256 checksums for active lexical index `artifacts/indexes/bm25-v2` (`bm25-receipt.json` SHA256 `97fdeb649d267e31114fb6d7eccea927c713fac34e8d2ca1178f363e8f825ccb`; `21,748` documents, `391,043` terms, `9,464,226` CSR postings) and weak-label benchmark receipt `artifacts/benchmarks/retrieval_v2.json` (`03adf6eaa7e7cf006cf7f3a9be871574b6bf58edbd56a27c50b0461fa2d39c4c`).
4. **Source Terms, Observation Timestamps & Unverified Boundaries:**
   - State exact data sources, observation/verification timestamps (`2026-11-16`, `2026-11-17`, and `2026-11-18` at commit `c3348e93d66ad4eeba133c1d05752d26da18d774`), and unresolved limitations (unresolved upstream reuse/redistribution license blocking public corpus redistribution; byte checksums vs. semantic/ASR/POI ground truth; absent fresh 120-day stream and multimodal tables).

## Acceptance Criteria
- No differing existing original file overwritten; all `37,840` selected historical files (`1,504,284,701` bytes) and `37,849` published data/runtime files (`1,593,622,816` bytes) verified by SHA256 and Git blob SHA1.
- Provenance, observation timestamps, inventory scope separation (`37,837` upstream `data/` + `3` legacy app tables vs. prior owner-copy claim), and unresolved source redistribution terms explicitly documented.
- `python scripts/check_secrets.py` exits with `0` (`Zero secret leaks detected`).
- Independent peer verification of recovery receipts by Nguyễn Việt Nguyên (`N`) completed before gate `M0.G` (`G0`).
