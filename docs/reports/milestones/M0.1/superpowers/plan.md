# M0.1 — Execution & Verification Plan

- **Date:** 2026-11-16 (initial baseline); revised 2026-11-18 (two-person provenance consolidation)
- **Task ID:** `M0.1`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Spec:** [spec.md](spec.md)

## Execution Steps
- [x] **Step 1: Legacy Audit & Secret Sanitization (2026-11-16)**
  - Scrub 148 Gemini keys and 1 third-party key across 16 legacy coursework files; relocate legacy coursework to `archive/legacy_coursework/` and enforce `scripts/check_secrets.py`.
- [x] **Step 2: Pinned Upstream Recovery & Exhaustive Byte Verification (2026-11-17)**
  - Recover `37,837` `data/` blobs (`1,475,677,482` bytes) and `3` legacy app tables (`28,607,219` bytes) from `TrggTin/21KHDL-TikTok-Analytics` at `f142e5656a220f94f8024de168b0832754b3bd9e` (`37,840` files / `1,504,284,701` bytes total) without overwriting pre-existing local files.
  - Record per-file Git blob SHA1 and SHA256 in `docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/restore-input-manifest.json` and verify in `restore-verification.json`.
- [x] **Step 3: Immutable Gold Snapshot & BM25 v2 Build (2026-11-17)**
  - Build and verify `data/corpus/20261117_recovered_v1` (`264` creators, `70,996` videos, `21,748` transcripts, `23,448` POIs) and `artifacts/indexes/bm25-v2` (`21,748` docs, `391,043` terms, `9,464,226` postings), plus provenance-bound `artifacts/benchmarks/retrieval_v2.json`.
- [x] **Step 4: Full-Inventory & Synchronized Checkout Re-verification (2026-11-18)**
  - Re-verify all `37,840` historical files and `37,849` published data/runtime files (`1,593,622,816` bytes), Gold table schemas/checksums/joins, and BM25 CSR invariants at synchronized `main` commit `c3348e93d66ad4eeba133c1d05752d26da18d774` (`docs/reports/tasks/team-progress-sync-2026-11-18/evidence/data-verification.json`).
- [x] **Step 5: Consolidate M0.1 Provenance Receipt & Finalize Report (2026-11-18)**
  - Generate `docs/reports/milestones/M0.1/evidence/m0.1-data-provenance-summary.json` binding all verified counts, SHA256 digests, observation timestamps, and unverified boundaries.
  - Update `docs/reports/milestones/M0.1/README.md`, `docs/reports/milestones/M0.1/evidence/workflow.md`, and `docs/reports/milestones/README.md` for reciprocal review by Nguyễn Việt Nguyên (`N`).

## Verification Plan
- Verify all checksums and counts against `restore-verification.json`, `data-verification.json`, `data/corpus/20261117_recovered_v1/manifest.json`, `artifacts/indexes/bm25-v2/bm25-receipt.json`, and `artifacts/benchmarks/retrieval_v2.json`.
- Run `python scripts/check_secrets.py` -> expect exit code `0` (`PASS: Zero secret leaks detected across workspace.`).
