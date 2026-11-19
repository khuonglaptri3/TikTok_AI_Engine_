# M1.G (G1) — Execution & Verification Plan

**Goal:** Update the qualified Gold corpus data card, run an asserting `G1` integrity/lineage/rights probe across `20261117_recovered_v1` and `20261118_taxonomy_fix_v1`, and publish the `M1.G` gate bundle for reciprocal review by Nguyễn Việt Nguyên (`N`).
**Spec:** [spec.md](spec.md)

## Global Constraints
- Zero mutation to `data/` historical files, `data/corpus/20261117_recovered_v1/`, or `data/corpus/20261118_taxonomy_fix_v1/`.
- CPU/offline execution only (`USD 0`, zero provider calls).
- Do not self-approve `G1 = PASS` without `N`'s peer review (`M1.G` stays `IN_PROGRESS`, `G1` stays `NOT_RUN`).

## Steps
- [x] **Step 1:** Author `M1.G/superpowers/spec.md` and `M1.G/superpowers/plan.md`.
- [x] **Step 2:** Update [tiktok_fnb_corpus_v1.md](../../../../data-cards/tiktok_fnb_corpus_v1.md) with `20261118_taxonomy_fix_v1` lineage/deltas, `M1.1` sampled error rates (`K_*` human `n=30` & `N_*` Gemini-assisted `n=120`), and the explicit local-only / no-public-redistribution rights boundary.
- [x] **Step 3:** Create and execute `M1.G/evidence/run_g1_checks.py` to assert `G0 == PASS`, `M1.1`/`M1.2` completion, full `load_verified_corpus` + SHA256 verification on both snapshots, safe-ratio finiteness, taxonomy deltas, unchanged snapshot bytes, and data-card completeness; emit `M1.G/evidence/g1_verification_receipt.json` and `M1.G/evidence/g1_checks.log`.
- [x] **Step 4:** Write `M1.G/evidence/workflow.md` and `M1.G/README.md`, add the `M1.G` row to [milestones/README.md](../../README.md), and verify `scripts/check_secrets.py`, bundle layout, and markdown links.
- [x] **Step 5 (Owner-confirmed `N` review — 2026-11-18):** Archive pre-confirmation `M1.G/README.md` to `evidence/report-before-n-review-confirmation.md`, emit `evidence/g1-gate-decision-receipt.json`, update `M1.G/README.md`, [milestones/README.md](../../README.md), and [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) to `M1.G = COMPLETE` and `G1 = PASS` (local-only scope; public redistribution `BLOCKED`), and re-run secret/layout/link verification.
