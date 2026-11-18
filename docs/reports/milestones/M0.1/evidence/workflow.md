# M0.1 — Superpowers Workflow Provenance

- **Date:** 2026-11-16 (initial baseline); updated 2026-11-18 (two-person recovery & provenance consolidation)
- **Task ID:** `M0.1`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, pending reciprocal receipt check)
- **Skills read and applied:** `using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `verification-before-completion`
- **Authorization provenance:**
  - `2026-11-16`: Initial user authorization to sanitize 149 legacy API keys, preserve local data, and establish the `TikTok_AI_Engine_` monorepo.
  - `2026-11-17`: Owner approval of the recovery-first two-person plan (`RECOVERY_FIRST_EQUAL_TEAM_2026_11_17`), pinned historical input recovery from `TrggTin/21KHDL-TikTok-Analytics` at `f142e5656a220f94f8024de168b0832754b3bd9e`, and full data publication to private `khuonglaptri3/TikTok_AI_Engine_`.
  - `2026-11-18`: Explicit user instruction to finalize `M0.1` data provenance evidence using existing verified receipts (`37,840` source files, checksums, upstream revision, Gold `20261117_recovered_v1`, BM25 `bm25-v2`, observation timestamps, and unverified limitations) without re-crawling or rebuilding.

## Key Decisions & Rulings
1. **Separate Inventory Scopes (`37,837 + 3 = 37,840` vs. Prior Owner Copy):** Recorded the exact pinned upstream tree scope (`37,837` blobs under `data/` totaling `1,475,677,482` bytes plus `3` legacy app tables under `src/app/...` mapped to `data/legacy_app_data/` totaling `28,607,219` bytes = `37,840` files / `1,504,284,701` bytes) separately from the prior owner-copy claim (`37,840` files / `~1.50 GB`), avoiding any unverified claim that the unavailable original local inventory was reconstructed by assertion.
2. **Active vs. Historical Artifacts:** Bound `M0.1` acceptance evidence to the verified recovered Gold snapshot `data/corpus/20261117_recovered_v1` (`manifest.json` SHA256 `10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4`), lexical index `artifacts/indexes/bm25-v2` (`bm25-receipt.json` SHA256 `97fdeb649d267e31114fb6d7eccea927c713fac34e8d2ca1178f363e8f825ccb`), and standard-recall receipt `artifacts/benchmarks/retrieval_v2.json` (`03adf6eaa7e7cf006cf7f3a9be871574b6bf58edbd56a27c50b0461fa2d39c4c`), while retaining `20261116_v1/manifest.json` and `retrieval_v1.json` strictly as dated historical records.
3. **Two-Person Status Discipline:** Set `M0.1` status to `IN_PROGRESS` (Primary owner evidence complete; awaiting independent peer check by Nguyễn Việt Nguyên `N`) in accordance with `docs/planning/TikTok_AI_Engine_Milestone.md` (`Neither person can approve their own task alone`).

## Verification Executed & Referenced Receipts
- **Secret Hygiene:** `python scripts/check_secrets.py` -> `PASS: Zero secret leaks detected across workspace.`
- **Pinned Input Restoration & Byte Preservation (`2026-11-17T05:55:45Z`):** [restore-verification.json](../../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-verification.json) and [restore-input-manifest.json](../../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-input-manifest.json) (`37,840` files / `1,504,284,701` bytes verified against Git blob SHA1 and SHA256; `0` differing existing files overwritten).
- **Synchronized Checkout & Full-Inventory Verification (`2026-11-18T01:49:50Z` at `c3348e9`):** [data-verification.json](../../../tasks/team-progress-sync-2026-11-18/evidence/data-verification.json) (`37,849` published local/remote files / `1,593,622,816` bytes verified in `161.733s` with `0` mismatches; Gold `20261117_recovered_v1` and `bm25-v2` CSR checks `PASS`).
- **Consolidated M0.1 Summary Receipt:** [m0.1-data-provenance-summary.json](m0.1-data-provenance-summary.json).
