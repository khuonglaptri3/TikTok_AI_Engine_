# Owner Scope — AI Modules & Evidence-Grounded Demonstration

This repository is engineered by a single AI Engineer following the `SenticRAG` operational discipline:

1. **AI-Only Scope:** Deliver typed domain packages (`packages/`), reproducible offline CLI pipelines (`pipelines/`), typed FastAPI endpoints (`apps/api/`), and one lightweight Gradio UI mounted at `/demo/` (`apps/demo/`). Do not add user authentication, CRUD accounts, or Jupyter Notebooks in production flows.
2. **100% Upstream Data Preservation:** Preserve all `1.50 GB` (`37,840` files) of raw/interim/legacy datasets intact under `data/`. All downstream serving consumes immutable, SHA256-verified Gold snapshots under `data/corpus/<snapshot-id>/`.
3. **Zero Paid Spend & Secret Hygiene:** Keep `GEMINI_API_KEY` exclusively in `.env` (never in source files). Enforce `python3 scripts/check_secrets.py` before commits. Cap Gemini Free-Tier usage to `<= 2` calls per request with sliding-window rate limiting and zero paid fallback.
4. **Fail-Closed Integrity:** Verify `manifest.json` SHA256 hashes at startup. Separate measured live stage latencies (`ms`) from frozen benchmark reports (`artifacts/benchmarks/`). Never insert fabricated sample outputs when a dependency or API quota is unavailable.
5. **Milestone Reporting Convention:** Store milestone reports under `docs/reports/milestones/<TASK-ID>/` containing `README.md`, `evidence/`, and `superpowers/{spec.md, plan.md}` in English.
