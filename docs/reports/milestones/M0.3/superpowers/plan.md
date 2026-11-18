# M0.3 — Execution & Verification Plan

- **Date:** 2026-11-18
- **Task ID:** `M0.3`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Spec:** [spec.md](spec.md)

## Execution Steps
- [x] **Step 1: Verify Package & Docker COPY-Context Build Metadata**
  - Inspected `pyproject.toml` (`gradio>=6.0.0` in default `dependencies`, `demo = []` backward-compatible alias, `apps`/`packages`/`pipelines` included) and `infra/docker/Dockerfile.api` (`COPY pipelines ./pipelines` included); cross-checked wheel build receipt (`docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/package-final.log`).
- [x] **Step 2: Launch Live Demo Server (`python scripts/dev.py run-demo`) and Run Real-Data Probe**
  - Started `python scripts/dev.py run-demo` on `http://127.0.0.1:8000` with `GEMINI_API_KEY=""` (`0` provider calls).
  - Verified live HTTP endpoints (`/`, `/demo/`, `/demo/config`, `/health/live`, `/health/ready`, `/api/v1/demo/modules`, `/api/v1/evaluation/summary`, `/api/v1/analytics/niche-benchmark`, `/api/v1/retrieval/search`, `/api/v1/script/generate`) and invoked all 4 Gradio UI handlers (`handle_generate_script`, `handle_explore_evidence`, `handle_trust_audit`, `handle_refresh_status`).
- [x] **Step 3: Verify Citation Resolution, Excerpt Grounding, Benchmarks, Timings & Invalid Inputs**
  - Verified `5/5` search citations and `4/4` `offline_grounded` script beats against `data/corpus/20261117_recovered_v1/fact_videos.parquet` and `artifacts/indexes/bm25-v2/video_ids.json`, including `Nguồn cũ: "..."` dialogue prefixes.
  - Tested invalid/boundary inputs (`UNSUPPORTED_DOMAIN`, `PROVIDER_KEY_MISSING`, `INDEX_NOT_READY`, blank/whitespace queries and briefs, too-short briefs, unknown extra fields, out-of-range durations) across API and `/demo/` UI handlers, documenting observed UI formatting and draft-truncation issues (`M0.3-UI-1`..`M0.3-UI-3`, `M0.3-DRAFT-1`).
- [x] **Step 4: Save Evidence & Author M0.3 Report**
  - Saved `run-demo-server.log`, `demo-live-verification.json`, `demo-rendered-outputs.md`, and `workflow.md` under `docs/reports/milestones/M0.3/evidence/`.
  - Authored `docs/reports/milestones/M0.3/README.md` and updated `docs/reports/milestones/README.md`.
  - Executed `python scripts/check_secrets.py` to confirm zero secret leaks.
