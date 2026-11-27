# M6.G — Gate G6 Release & Hosting Decision Specification

- **Task ID:** `M6.G` (`Gate G6`)
- **Authored at:** `2026-11-27T08:44:00+07:00` (`Asia/Ho_Chi_Minh`)
- **Requirement source:** [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.G`) & [TikTok_AI_Engine_Resources_and_Deployment.md](../../../planning/TikTok_AI_Engine_Resources_and_Deployment.md) (Section 5)
- **Contributors:** Nguyễn Việt Nguyên (`N`, `2` pts) & Trần Đình Khương (`K`, `2` pts) — joint review & owner-confirmed sign-off (`2026-11-27`)

## 1. Scope & Objective

Execute the final project release gate (`Gate G6`) after reciprocal `N` + `K` closure of `M3.G` (`G3 = PASS`), `M4.G` (`G4 = PASS`), `M5.G` (`G5 = PASS`), `M6.1` (`COMPLETE`), and `M6.2` (`COMPLETE`). Separately evaluate and record:
1. **Local CPU Release Decision (`local_cpu_release`):** Reproducible offline FastAPI + ASGI-mounted Gradio `/demo/` serving all accepted `M0`–`M6` capabilities at `USD 0` spend.
2. **Conditional Public Hosting Decision (`public_hosting`):** Measured free-tier candidate evaluation against strict `USD 0` / no-credit-card / no-overage rules, measured RAM/storage/cold-start footprints, and `G1` upstream data redistribution & privacy boundaries.

## 2. Measurable Acceptance Criteria

1. **Upstream Gate & Task Completeness (Fail-Closed):**
   - Prior gates `G0`, `G1` (local-only), `G2`, `G3`, `G4`, and `G5` must all record `PASS`.
   - All `23` upstream tasks (`M0.1` through `M6.2`) must be `COMPLETE` in `docs/reports/milestones/README.md` with valid `README.md`, `evidence/`, and `superpowers/{spec.md, plan.md}` directory structure.
2. **Cryptographic Corpus Integrity & Zero Spend:**
   - Zero byte mutations across all verified Gold snapshots (`20261117_recovered_v1`, `20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`, `m3_3_playwright_comments_20261125_v5`).
   - `python3 scripts/check_secrets.py` exits `0`; `MAX_LLM_CALLS_PER_TURN == 2`; missing provider key returns `503 PROVIDER_KEY_MISSING`; out-of-domain & forbidden epistemic prompts return `422 UNSUPPORTED_DOMAIN`; zero paid fallback.
3. **Packaging, Suite & Reproducible Local CPU Runtime:**
   - Full `pytest` suite, strict `mypy` (Linux & `--platform win32`), clean package build (`sdist` + `wheel`), and documentation/link hygiene checks pass.
   - Live in-process ASGI `/demo/` (`apps.demo.main:create_app`) serves historical analytics, `bm25-m3_3-pilot` retrieval (`21,758` indexed transcripts), offline grounded script generation, multimodal corpus catalog (`130` videos / `2,823` comments / `436` `audio_derived` segments / `29` `.mp3` prosody receipts), `M4.2` disclosure separation, `M5.1` diagnostic-only comment flags, `M5.2` `>=3`-comment span-grounded ABSA, and `M2.2`–`M6.2` milestone scorecard with finite `ms` stage timings and `peak_rss_mib <= 8,192 MiB`.
4. **Separate Hosting Eligibility Ruling:**
   - Candidate hosting tiers (`Hugging Face Spaces Free CPU Basic`, `Render Free Web Service`, `Railway / Fly.io`) evaluated against measured disk/RAM footprints and `G1` data redistribution terms.
   - Because upstream TikTok raw/derived transcripts, `2,823` viewer comments, and `29` `.mp3` files have no public redistribution license (`G1`: `public redistribution BLOCKED`), **`public_hosting` is recorded honestly as `BLOCKED`**, while **`local_cpu_release` is accepted as `PASS`**.
