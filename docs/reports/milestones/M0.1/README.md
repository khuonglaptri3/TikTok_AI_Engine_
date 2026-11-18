# M0.1 — Historical Asset Preservation, Pinned Recovery & Provenance Baseline

- Status: IN_PROGRESS (Primary owner data & provenance verification complete; awaiting independent peer check by Nguyễn Việt Nguyên)
- Execution date: 2026-11-16 (initial audit); 2026-11-17 (pinned recovery & Gold/BM25 v2 build); 2026-11-18 (provenance consolidation at synchronized checkout, Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.1`)
- Repository version: `main` (`c3348e93d66ad4eeba133c1d05752d26da18d774`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

The legacy `21KHDL-TikTok-Analytics` repository was sanitized of all 149 hardcoded API keys (`scripts/check_secrets.py` exits `0`), and all **37,840 selected historical source files (`1,504,284,701` logical bytes)** were restored from pinned upstream revision `f142e5656a220f94f8024de168b0832754b3bd9e` without historical TikTok recrawling or overwriting any differing pre-existing local file. The upstream `data/` tree scope (**37,837 blobs / `1,475,677,482` bytes**) plus **3 mapped legacy app tables (`28,607,219` bytes)** is kept explicitly separate from the prior owner-copy claim (`37,840` files / `~1.50 GB`), whose unavailable pre-recovery file list is not reconstructed by assertion.

Downstream runtime artifacts are verified and active at `c3348e93d66ad4eeba133c1d05752d26da18d774`: immutable Gold snapshot **`data/corpus/20261117_recovered_v1`** (`264` creators, `70,996` unique videos across `49` columns, `21,748` accepted transcripts, `23,448` POI-tagged rows, `5,798` `is_ec_video` rows; date bounds `2023-11-25` to `2025-03-19`) and Vietnamese NFC CSR lexical index **`artifacts/indexes/bm25-v2`** (`21,748` documents, `391,043` terms, `9,464,226` postings). All **37,849 published data and runtime files (`1,593,622,816` bytes)** match between local disk and `origin/main`. Source redistribution licensing, semantic/ASR/POI ground-truth accuracy, and the absent 120-day fresh stream remain explicitly bounded as open limitations. Under the two-person workflow, `M0.1` remains `IN_PROGRESS` pending independent receipt verification by Nguyễn Việt Nguyên (`N`) before gate `M0.G` (`G0`).

## Verified data sources, checksums, and observation timeline

| Layer / asset | Source & observation timestamp (UTC) | Verified scope, counts & parameters | SHA256 / Git revision provenance |
| --- | --- | --- | --- |
| **Pinned historical inputs (`37,840` files)** | Upstream `TrggTin/21KHDL-TikTok-Analytics` at `f142e5656a220f94f8024de168b0832754b3bd9e`. Restored `2026-11-17T05:46:23Z`; reread verified `2026-11-17T05:55:45Z` (`557.457s`); re-verified `2026-11-18T01:49:50Z` (`161.733s`). | `37,837` blobs under `data/` (`1,475,677,482` B: `23,122` transcripts, `14,252` `foods-and-locations`, `413` `raw` incl. `4` `.m4a` files, `21` `interim`, `10` `processed`, `7` `UserList`, `5` `prompts`, `2` `content-features-dataset`, `1` `ScriptGen-data`, `1` `content_analysis`, `1` `error`, `1` `filters`, `1` `insights`) + `3` mapped tables under `data/legacy_app_data/` (`28,607,219` B) = **`37,840` files / `1,504,284,701` B**. | Input manifest (`restore-input-manifest.json`): `11843e609ade980f354b153f71f29bec5edd6ec349d2176b5f2588a98eb83bc1`. Anchor `data/processed/cleaned_video_info.csv`: `ce76aa4acaf6bbc5b2c8976f206710cb7693eae5328bfb913cc15aabbb73e102`. |
| **Pre-existing local baseline (`2` files)** | Hashed before and after restoration on `2026-11-17` and re-verified on `2026-11-18T01:49:50Z`. | `0` differing existing files overwritten; both pre-existing files preserved byte-for-byte. | `data/corpus/20261116_v1/manifest.json`: `9565c9fc7dd9ce00a638cfcb4cc35032347ddc746c686eb7ccdc91ba911278f6`; `data/evaluation/v1/queries.jsonl`: `fffeec843da264e398f6c3f3fe8e057cac2b35d2345a9d42eb4a4de50d46ed98`. |
| **Published data & runtime tree (`37,849` files)** | Private `khuonglaptri3/TikTok_AI_Engine_` (`origin/main` at `c3348e93d66ad4eeba133c1d05752d26da18d774`), verified `2026-11-18T01:47:09Z–01:49:50Z`. | `37,840` historical files + `9` Gold/BM25/evaluation/manifest files = **`37,849` files / `1,593,622,816` B**; `0` missing/extra paths or blob mismatches between local and `origin/main`. | Upload hash inventory (`upload-file-hashes.json`): `d57a2c7217cda4200c577012c5e7eb716995606c0bd91dc3e0c38793b67bc64f`. |
| **Active Gold snapshot (`20261117_recovered_v1`)** | Built `2026-11-17T05:57:01.466195+00:00` via `pipelines.build_gold_corpus`; schema/keys/joins re-verified `2026-11-18T01:49:50Z`. | `264` creators (`dim_creators.parquet`: `264x15`, `35,285` B); `70,996` unique videos (`fact_videos.parquet`: `70,996x49`, `58,852,759` B); `21,748` accepted transcripts (from `23,122` raw JSONs); `23,448` POI rows; `5,798` `is_ec_video` rows; dates `2023-11-25` to `2025-03-19` (Mar–Apr 2025 engagement capture). | `manifest.json`: `10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4`; `dim_creators.parquet`: `0a704391fd5395582770a4113dca6eeabfbc6fcb2520731b08a9c0e4177facf7`; `fact_videos.parquet`: `1bfc6c6f819b4c0176345029e5ae4e630a4e9c0438c89548aab893e1d30c1ecd`. |
| **Active BM25 index (`bm25-v2`)** | Built `2026-11-17T05:59:02.535593+00:00` via `pipelines.build_dense_sparse_index`; CSR structure re-verified `2026-11-18T01:49:50Z`. | `okapi_bm25_vn_nfc_csr` bound to `20261117_recovered_v1`: `21,748` documents (100% match to eligible transcribed videos), `391,043` terms, `9,464,226` postings, `avgdl=309.4`, `k1=1.5`, `b=0.75`. | `bm25-receipt.json`: `97fdeb649d267e31114fb6d7eccea927c713fac34e8d2ca1178f363e8f825ccb`; `video_ids.json`: `0af8ecbc4527086616359495b39a9d81a2334cbeb15dbbdb6b6fa69660a71cee`; `vocab.json`: `ab18f0979b5624186b10f04470d03b0bbfc6d6345f1ea3bd6e08cd3a95934ffc`; `bm25_csr.npz`: `184728bd872aa25d1512d149bedcf4421cae91b0faa856fb04fa11f1a63cb205`. |
| **Weak-label retrieval receipt (`retrieval_v2`)** | Generated `2026-11-17` against `20261117_recovered_v1` and `bm25-v2`; input/code hashes re-verified `2026-11-18T01:49:50Z`. | `16` lexical/metadata weak-label queries (macro standard `Recall@10` ceiling `0.2948`). `BM25 + viral boost`: `Recall@10=0.1837`, `Precision@10=0.6000`, `MRR@10=0.8875`, `nDCG@10=0.6962`, `p95=37.04 ms`. `BM25 + phrase rerank`: `Recall@10=0.1901`, `Precision@10=0.6438`, `MRR@10=0.8127`, `nDCG@10=0.7083`, `p95=86.73 ms`. | `retrieval_v2.json`: `03adf6eaa7e7cf006cf7f3a9be871574b6bf58edbd56a27c50b0461fa2d39c4c` (legacy `retrieval_v1.json` `33c523d528aff22970c40f7bf253e88617a39d901a0ba6e687f0776a9da6b22c` preserved as historical record). |

## Work performed

- Purged 148 Gemini keys and 1 third-party key across 16 legacy coursework files, archived legacy coursework under `archive/legacy_coursework/`, and added automated secret scanning (`scripts/check_secrets.py`, `tests/unit/test_secret_hygiene.py`).
- Restored `37,837` upstream `data/` files (`1,475,677,482` bytes) and `3` legacy app tables (`28,607,219` bytes) from `TrggTin/21KHDL-TikTok-Analytics` (`f142e5656a220f94f8024de168b0832754b3bd9e`) with exclusive write creation and exhaustive Git blob SHA1 + SHA256 verification.
- Built immutable Gold snapshot `data/corpus/20261117_recovered_v1` (`70,996` videos, `264` creators) and CSR index `artifacts/indexes/bm25-v2` (`21,748` documents) with collision-safe atomic staging (`packages/common/snapshots.py`).
- Consolidated all verified counts, checksums, observation timestamps, and unverified boundaries into [m0.1-data-provenance-summary.json](evidence/m0.1-data-provenance-summary.json), replacing stale single-person `20261116_v1` / `retrieval_v1` assertions from the initial draft report.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers skill provenance, rulings, and verification ledger for `M0.1` |
| [m0.1-data-provenance-summary.json](evidence/m0.1-data-provenance-summary.json) | Consolidated machine-readable receipt of `37,840` source files, SHA256 digests, upstream revision, Gold `20261117_recovered_v1`, `bm25-v2`, timestamps, and unverified limits |
| [restore-review.md](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-review.md) | Detailed pinned upstream mapping (`37,837` `data/` + `3` legacy app tables) and byte-preservation method |
| [restore-verification.json](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-verification.json) | Exhaustive `2026-11-17T05:55:45Z` verification of all `37,840` restored files and `2` pre-existing files |
| [data-verification.json](../../tasks/team-progress-sync-2026-11-18/evidence/data-verification.json) | Fresh `2026-11-18T01:49:50Z` verification of `37,849` local/remote files, Gold schemas/keys/joins, and `bm25-v2` CSR invariants at `c3348e9` |
| [manifest.json](../../../../data/corpus/20261117_recovered_v1/manifest.json) | Active Gold snapshot manifest (`20261117_recovered_v1`, SHA256 `10ed9c66...`) |
| [bm25-receipt.json](../../../../artifacts/indexes/bm25-v2/bm25-receipt.json) | Active Vietnamese NFC BM25 CSR index receipt (`bm25-v2`, SHA256 `97fdeb64...`) |
| [retrieval_v2.json](../../../../artifacts/benchmarks/retrieval_v2.json) | Standard-recall weak-label retrieval benchmark receipt bound to `20261117_recovered_v1` and `bm25-v2` |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace source/evidence secret scan; additionally `37,849` data/runtime files scanned with `0` credential matches in [upload-file-hashes.json](../../tasks/full-data-publication-2026-11-17/evidence/upload-file-hashes.json) |
| Pinned historical restoration (`37,840` files / `1,504,284,701` B) | PASS (`0` mismatches, `0` overwrites) | Exhaustive Git blob SHA1 and archive-derived SHA256 reread in [restore-verification.json](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-verification.json) |
| Synchronized local/remote data, Gold & BM25 audit (`37,849` files / `1,593,622,816` B) | PASS (`0` failures in `161.733s`) | 8-worker content/blob scan plus Gold `20261117_recovered_v1` and `bm25-v2` structural checks at `c3348e9` in [data-verification.json](../../tasks/team-progress-sync-2026-11-18/evidence/data-verification.json) |
| Full project test suite (`python -m pytest`) | PASS (`63 passed in 50.47s`) | Includes secret hygiene, snapshot continuity, Gold corpus integrity, BM25 retrieval, and ASGI smoke tests in [pytest-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log) |

## Open issues and unverified limitations

| Issue / limitation | Impact | Follow-up / responsible task |
| --- | --- | --- |
| **Unavailable pre-recovery owner-copy inventory vs. pinned upstream scope** | The prior owner-copy claim (`37,840` files / `~1.50 GB`) had no saved pre-recovery manifest; verified restoration proves the `37,837` upstream `data/` blobs + `3` legacy app tables (`37,840` files / `1,504,284,701` B) at `f142e5656a220f94f8024de168b0832754b3bd9e` and preservation of pre-existing local files, not an unverified historical owner inventory | Retained as an explicit permanent evidence boundary in `M0.1` and `M0.G` |
| **Unresolved upstream dataset reuse / redistribution license** | `TrggTin/21KHDL-TikTok-Analytics` states no open data license; public redistribution of raw/Gold TikTok data remains blocked while local/private evaluation is permitted | `M1.G` (`G1`) and `M6.G` (`G6`) public-hosting/redistribution gate |
| **Byte integrity vs. semantic/ASR/POI ground truth** | Matching SHA256 hashes do not prove speech transcription accuracy (`21,748` parsed transcripts), physical venue presence (`23,448` platform POI tags), taxonomy label correctness, or human relevance quality (`retrieval_v2` uses 16 weak lexical/metadata labels) | `M1.1` (120-record stratified taxonomy audit) and `M2.2` (40-query human relevance pilot) |
| **Historical cohort window & absent fresh/multimodal tables** | Historical videos cover `2023-11-25` to `2025-03-19` (Mar–Apr 2025 single-snapshot engagement) with `wps_estimated` timing; `data/raw_incremental/`, `fact_voice_segments.parquet`, `fact_comments.parquet`, `fact_absa_reviews.parquet`, and populated Qdrant dense vectors are absent | `M3.1`–`M3.3`, `M4.1`, `M5.1`–`M5.2`, `M6.1` |
| **Independent peer review of `M0.1` receipts by Nguyễn Việt Nguyên (`N`)** | Required by the two-person reciprocal review policy before closing `M0.1` and evaluating `M0.G` (`G0`) | Hand off [m0.1-data-provenance-summary.json](evidence/m0.1-data-provenance-summary.json) to `N` for independent check |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| No differing existing original overwritten; `37,840` historical files recovered and verified by SHA256 & Git blob SHA1 | Met | [restore-verification.json](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-verification.json), [data-verification.json](../../tasks/team-progress-sync-2026-11-18/evidence/data-verification.json) |
| Keep `37,837` upstream `data/` and `37,840` combined/owner-copy scopes separate; enumerate provenance and missing/unverified assets | Met | [m0.1-data-provenance-summary.json](evidence/m0.1-data-provenance-summary.json), [restore-review.md](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-review.md) |
| Record source terms, observation timestamps, Gold `20261117_recovered_v1` and `bm25-v2` receipts | Met | [m0.1-data-provenance-summary.json](evidence/m0.1-data-provenance-summary.json), [manifest.json](../../../../data/corpus/20261117_recovered_v1/manifest.json), [bm25-receipt.json](../../../../artifacts/indexes/bm25-v2/bm25-receipt.json) |
| Secret scanner `python scripts/check_secrets.py` exits `0` | Met | [secrets-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/secrets-current.log) |
| Independent peer verification of recovery receipts by Nguyễn Việt Nguyên (`N`) | Pending peer review | Handed off to `N` prior to `M0.G` (`G0`) |

Final task status: **IN_PROGRESS** (all primary-owner data recovery, checksum, Gold `20261117_recovered_v1`, and `bm25-v2` provenance evidence is complete; ready for independent peer verification by Nguyễn Việt Nguyên before `M0.G` / `G0`).
