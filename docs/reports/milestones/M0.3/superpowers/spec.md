# M0.3 — Specification: Installable API/Demo Foundation & Real-Corpus Offline Verification

- **Date:** 2026-11-18
- **Task ID:** `M0.3`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.3`)

## Scope & Requirements
1. **Declared Dependency Profile & Source Packaging:**
   - Align base and `demo` dependency profiles in `pyproject.toml` so `gradio>=6.0.0` is available in default installations and `infra/docker/Dockerfile.api` copies `pipelines/` alongside `packages/`, `apps/`, and `configs/`.
   - Verify wheel builds from both the repository root and the replicated `Dockerfile.api` `COPY` context while explicitly distinguishing source-package verification from an unrun Docker engine/container.
2. **Single-Process FastAPI + ASGI-Mounted Gradio `/demo/` on Real Recovered Data:**
   - Run the live demo server via `python scripts/dev.py run-demo` (`uvicorn apps.demo.main:create_app --factory --host 127.0.0.1 --port 8000`) backed by `data/corpus/20261117_recovered_v1` (`70,996` videos, `264` creators) and `artifacts/indexes/bm25-v2` (`21,748` indexed transcripts) with zero external provider calls (`GEMINI_API_KEY` blanked).
   - Verify `/health/live`, `/health/ready`, `/demo/` HTML & `/demo/config`, `/api/v1/demo/modules`, and `/api/v1/evaluation/summary`.
3. **End-to-End `/demo/` Functional & Data-Grounding Checks (`offline_grounded`):**
   - **Evidence Search (`/demo/` Tab 2 & `/api/v1/retrieval/search`):** Verify returned video ranks, scores, metadata, and `citation` objects (`video_id`, `author_handle`, `tiktok_url`, `play_count`, `viral_multiplier`, `engagement_rate`) resolve accurately to `fact_videos.parquet` and `bm25-v2`.
   - **Offline Grounded Script Drafting (`/demo/` Tab 1 & `/api/v1/script/generate` with `generation_mode="offline_grounded"`):** Verify the generated script is explicitly labeled as a creative draft (`draft_status="creative_draft"`, `grounding_verified=False`, draft disclaimers in UI Markdown), every beat's `cited_video_ids` is a valid subset of the returned `evidence_cards`, and every quoted `Nguồn cũ: "..."` excerpt matches the source video's `hook_text` / `transcript_excerpt`.
   - **Niche Micro-Benchmark & Stage Timings:** Verify `niche_benchmark` summary statistics (counts, medians, IQR ordering `duration_q25_sec <= duration_median_sec <= duration_q75_sec`, `hashtag_q25 <= hashtag_q75`, top hours/hashtags/POIs) and finite non-negative `timings_ms` stage latencies display accurately in both API JSON and `/demo/` Markdown.
   - **Invalid Input & Bounded Error Handling:** Verify clear rejection and error handling across API and `/demo/` UI for:
     - Out-of-domain brief (`422 UNSUPPORTED_DOMAIN`),
     - Missing Gemini API key when `gemini_free` is selected (`503 PROVIDER_KEY_MISSING`),
     - Unpopulated Qdrant dense index when `mode="dense"` is selected (`503 INDEX_NOT_READY`),
     - Blank/whitespace-only or out-of-range inputs (`422` Pydantic validation errors), documenting any remaining UI formatting differences between `ViralRagError` payloads and FastAPI default `422` validation payloads.

## Acceptance Criteria
- Clean declared-profile import, root and Docker `COPY`-context wheel builds, `/health/live`, `/health/ready`, valid/invalid API checks, and live `python scripts/dev.py run-demo` `/demo/` checks pass with zero provider calls (`USD 0`).
- All verified outputs, timings, citation-to-source excerpt checks, and remaining UI/packaging limitations are recorded in `docs/reports/milestones/M0.3/`.
- Independent integration reproduction by Nguyễn Việt Nguyên (`N`) is completed before gate `M0.G` (`G0`).
