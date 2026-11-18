# M0.3 — Installable API/Demo Foundation & Real-Corpus `/demo/` Verification

- Status: IN_PROGRESS (Primary owner live `/demo/`, API, and package verification complete; awaiting independent reproduction by Nguyễn Việt Nguyên)
- Execution date: 2026-11-18 (Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.3`)
- Repository version: `main` (`c3348e93d66ad4eeba133c1d05752d26da18d774`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

The single-process FastAPI + ASGI-mounted Gradio demonstration (`python scripts/dev.py run-demo` -> `http://127.0.0.1:8000/demo/`) and declared source-package profile (`pyproject.toml` + `infra/docker/Dockerfile.api` COPY context) **PASS** live verification on the recovered historical dataset (`20261117_recovered_v1`: `70,996` videos, `264` creators; `bm25-v2`: `21,748` indexed transcripts) with **zero provider calls (`USD 0`)**.

Across live HTTP requests and `/demo/` Gradio handlers (`2026-11-18T03:46:50Z–03:47:31Z`):
1. **Search & Reference Citations (`PASS`):** `5/5` returned videos for `"bánh mì thịt nướng Sài Gòn"` (`20.37 ms` internal, `57.69 ms` HTTP wall) resolve 100% accurately (`video_id`, `author_handle`, `tiktok_url`, `play_count`, `hook_text`, `transcript_excerpt`) against `fact_videos.parquet` and `bm25-v2`.
2. **Offline Draft Qualification & Source Excerpt Matching (`PASS`):** `offline_grounded` (`model_used="offline_evidence_blueprint_v1"`, `1,072.62 ms` internal) explicitly labels the script as a unverified creative draft (`draft_status="creative_draft"`, `grounding_verified=false`, UI draft disclaimers), cites only returned `evidence_cards` (`4/4` beats), and embeds `Nguồn cũ: "..."` quotes that match `4/4` cited source transcripts.
3. **Benchmarks & Stage Timings (`PASS`):** Niche benchmarks (`9,631` videos for HCMC `Review quán ăn` in `217.06 ms`) preserve IQR ordering (`37s <= 63s <= 80s`, hashtags `5 <= 9`), and all endpoints/tabs render finite non-negative `*_ms` stage timings.
4. **Invalid Input Handling (`PASS` at API boundary; 3 minor UI display issues recorded):** Domain and readiness errors (`422 UNSUPPORTED_DOMAIN`, `503 PROVIDER_KEY_MISSING`, `503 INDEX_NOT_READY`) display clean actionable messages in `/demo/`, while FastAPI/Pydantic `422` validation errors (`blank query` / `blank brief`) expose minor UI formatting rough edges (`M0.3-UI-1`, `M0.3-UI-2`) documented below.

Task `M0.3` remains `IN_PROGRESS` pending independent checkout/demo reproduction by Nguyễn Việt Nguyên (`N`) prior to gate `M0.G` (`G0`).

## Work performed

- Verified `pyproject.toml` (`gradio>=6.0.0` in default `dependencies`, backward-compatible `demo = []` extra) and `infra/docker/Dockerfile.api` (`COPY pipelines ./pipelines` included), cross-referencing root and Docker COPY-context wheel builds (`tiktok_viral_rag-0.2.0-py3-none-any.whl`).
- Launched `python scripts/dev.py run-demo` on `http://127.0.0.1:8000` with `GEMINI_API_KEY=""` (`16,452.47 ms` cold startup loading `70,996` Parquet rows and `bm25-v2` CSR arrays) and probed `/`, `/demo/` (`67,944` B HTML), `/demo/config` (`Gradio 6.32.0`, `56` components), `/health/live`, `/health/ready`, `/api/v1/demo/modules`, and `/api/v1/evaluation/summary`.
- Executed live HTTP and `/demo/` Gradio handler checks (`handle_generate_script` in `offline_grounded` mode, `handle_explore_evidence`, `handle_trust_audit`, `handle_refresh_status`) and verified every citation ID and `Nguồn cũ: "..."` excerpt against `fact_videos.parquet`.
- Exercised 8 invalid/boundary input cases across API routes and `/demo/` UI tabs, capturing exact rendered Markdown outputs in [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) and structured verification data in [demo-live-verification.json](evidence/demo-live-verification.json).

## Summary of verified `/demo/` flows

| Check area | Input / action | Observed result & latency | Evidence |
| --- | --- | --- | --- |
| **Server & `/demo/` mount** | `python scripts/dev.py run-demo` -> `GET /`, `/demo/`, `/demo/config`, `/health/live`, `/health/ready` | `307 -> /demo/`; `/demo/` `200 OK`; `/health/ready` `200 OK` (`20261117_recovered_v1`, `70,996` videos, `21,748` BM25 docs, `qdrant_dense_ready=false`, `gemini_key_configured=false`). Cold startup: `16,452.47 ms`. | [run-demo-server.log](evidence/run-demo-server.log), [demo-live-verification.json](evidence/demo-live-verification.json) |
| **1. Evidence search & citations** | `"bánh mì thịt nướng Sài Gòn"` (`mode="bm25"`, `top_k=5`, `rerank=True`), unfiltered & filtered (`Review quán ăn`, `hồ chí minh`) | `200 OK`; `40` candidates -> `5` items (`#1 @mioanh91 / 7392429774674693384`, `5.1M` plays; filtered `#1 @didausaigon / 7475992859783482642`). `5/5` citations & excerpts match `fact_videos.parquet` & `bm25-v2`. Internal `total_ms=20.37 ms` (`bm25_ms=3.02 ms`, `rerank_ms=16.48 ms`). | [demo-live-verification.json](evidence/demo-live-verification.json), [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) |
| **2. `offline_grounded` script & source excerpts** | Default Tab 1 brief (`"Review quán ốc sinh viên bình dân khoảng 35k ăn đêm ở Quận 4 Sài Gòn..."`, `45s`, `top_k=5`, `offline_grounded`) | `200 OK`; `draft_status="creative_draft"`, `grounding_verified=false`; UI heading `### Bản Nháp Kịch Bản` + disclaimer; `175` words / `44.9s` (`-0.1s` vs `45.0s` target). `4/4` beats cite returned `evidence_cards` (`7357939713132580103`, `7416326498296057106`, `7313084913899654401`) and match exact `Nguồn cũ` hook prefixes. `total_ms=1,072.62 ms`. | [demo-live-verification.json](evidence/demo-live-verification.json), [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) |
| **3. Niche benchmark & stage timings** | `{"video_format": "Review quán ăn", "city_norm": "hồ chí minh"}` + stage timings across Tabs 1–3 | `200 OK`; `9,631` matched (`3,187` transcribed, `9,323` POI), median `77,600` / P75 `210,300` views, duration IQR `37s–63s–80s`, hashtag IQR `5–9`. Finite non-negative `*_ms` timings (`filter_ms=50.18 ms`, `aggregate_ms=166.81 ms`, `total_ms=217.06 ms`; Tab 3 trust audit `total_ms=0.99 ms`). | [demo-live-verification.json](evidence/demo-live-verification.json), [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) |
| **4. Invalid & boundary inputs** | Out-of-domain crypto brief, `gemini_free` without key, `mode="dense"` without Qdrant, blank/short strings, extra JSON fields, `target_duration_sec=5` | API rejects all 8 cases with exact status codes (`422 UNSUPPORTED_DOMAIN`, `503 PROVIDER_KEY_MISSING`, `503 INDEX_NOT_READY`, `422` Pydantic validation). Domain/readiness errors render clean UI messages; Pydantic `422` UI formatting gaps logged as `M0.3-UI-1` & `M0.3-UI-2`. | [demo-live-verification.json](evidence/demo-live-verification.json), [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) |

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers skill usage, Windows process-tree cleanup ruling, and verification ledger |
| [run-demo-server.log](evidence/run-demo-server.log) | Raw Uvicorn HTTP access and startup log from `python scripts/dev.py run-demo` on `127.0.0.1:8000` |
| [demo-live-verification.json](evidence/demo-live-verification.json) | Machine-readable receipt of HTTP status codes, Gold/BM25 citation checks, excerpt grounding, timings, and invalid-input probes |
| [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) | Exact Markdown rendered by `/demo/` Tabs 1–3 and invalid-input handlers on `20261117_recovered_v1` |
| [package-final.log](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/package-final.log) | Root wheel and replicated `Dockerfile.api` COPY-context wheel build verification |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| Live `python scripts/dev.py run-demo` HTTP & `/demo/` UI probe | PASS (`0` provider calls) | `/health/live`, `/health/ready`, `/demo/`, search citations (`5/5`), `offline_grounded` beats (`4/4`), benchmark IQR, `timings_ms`, and 8 invalid-input checks; [demo-live-verification.json](evidence/demo-live-verification.json) |
| Root & `Dockerfile.api` COPY-context wheel builds | PASS (`exit 0`) | `tiktok_viral_rag-0.2.0-py3-none-any.whl` includes `gradio>=6.0.0` and `pipelines`; Docker engine was not executed; [package-final.log](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/package-final.log) |
| Full project pytest & mypy at `c3348e9` | PASS (`63 passed`, `76` files typed) | [pytest-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log), [mypy-current.log](../../tasks/team-progress-sync-2026-11-18/evidence/mypy-current.log) |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Zero hardcoded credentials across repository and `M0.3` evidence |

## Open issues and observed limitations

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| **`M0.3-UI-1` (Low):** Blank query (`"   "`) in `/demo/` Tab 2 renders `### ⚠️ Lỗi truy xuất (422)` with an empty body | `apps/demo/ui.py:118` reads `r_data.get("message", "")`, which is absent on FastAPI default `422` `{"detail": [...]}` responses | Normalize `RequestValidationError` or extract `detail[0].msg` in `apps/demo/ui.py` (`M2.3` / `M6.2` UI polish or pre-`G0` patch) |
| **`M0.3-UI-2` (Low):** Blank brief/transcript in `/demo/` Tabs 1 & 3 displays raw Pydantic `{"detail": [...]}` JSON under `### ⚠️ Lỗi (422)` | Functional `422` rejection works, but validation errors are less readable than `CanonicalErrorResponse` domain errors | Add FastAPI `RequestValidationError` -> `CanonicalErrorResponse` handler or UI formatter (`M2.3` / `M6.2`) |
| **`M0.3-UI-3` (Low):** `/demo/` Tab 1 evidence header hardcodes `mode=hybrid_rrf` and `5 ứng viên` (`len(evidence_cards)`) | Cosmetic header mismatch when Qdrant is offline (`effective_mode="bm25"`, candidate pool `40`) | Pass actual retrieval metadata in `ScriptGenerationResponse` (`M2.3` / `M6.2`) |
| **`M0.3-DRAFT-1` (Medium — downstream quality):** `offline_grounded` beat dialogue truncates trailing words mid-clause (`"...Bạn muốn"`, `"...trước khi"`, `"...thời điểm trải"`) to meet exact word budget | Passes structural duration guardrail (`44.9s` vs `45.0s`), but sentence endings read abruptly | Refine sentence-boundary trimming in `packages/script_engine/` during `M2.3` |
| **`M0.3-DATA-1` (Medium — corpus/retrieval semantics):** Unfiltered `"bánh mì thịt nướng Sài Gòn"` ranks high-play Đà Lạt video `#2`, and `@anngongovap` ốc clips carry background song lyrics in `transcript` | Citations are 100% faithful to corpus bytes, but noisy transcripts and soft location terms affect topical quality | Address in `M1.1` (transcript/taxonomy audit), `M2.1` (sparse-slice abstention for `n=2` narrow slices), and `M2.2` (human relevance pilot) |
| **`M0.3-SCOPE-1` (Info):** Actual Docker daemon container run and real browser clicks were not executed | Wheel + COPY-context build and live `uvicorn` HTTP + Gradio handler execution are verified; Linux container runtime remains unexecuted | Retain explicit scope boundary in `M0.G` (`G0`); Nguyễn Việt Nguyên (`N`) reproduces `/demo/` independently |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Base/demo dependency alignment & Docker COPY-context source wheel build | Met (source-package scope; Docker daemon not run) | `pyproject.toml`, `infra/docker/Dockerfile.api`, [package-final.log](../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/package-final.log) |
| Single FastAPI process with ASGI `/demo/`, `/health/live`, and `/health/ready` on real data | Met | [run-demo-server.log](evidence/run-demo-server.log), [demo-live-verification.json](evidence/demo-live-verification.json) |
| Valid/invalid API and `/demo/` checks (`offline_grounded`, citations, excerpts, benchmarks, `ms` timings) pass with `0` provider calls | Met (with minor UI `422` formatting & truncation notes recorded) | [demo-live-verification.json](evidence/demo-live-verification.json), [demo-rendered-outputs.md](evidence/demo-rendered-outputs.md) |
| Independent integration reproduction by Nguyễn Việt Nguyên (`N`) | Pending peer review | Hand off `M0.3` checklist and receipts to `N` before `M0.G` (`G0`) |

Final task status: **IN_PROGRESS** (all primary-owner packaging, live `run-demo`, citation/excerpt grounding, timing, and invalid-input checks complete; awaiting independent reproduction by Nguyễn Việt Nguyên prior to `M0.G` / `G0`).
