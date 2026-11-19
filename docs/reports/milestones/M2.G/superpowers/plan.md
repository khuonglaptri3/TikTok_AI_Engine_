# M2.G — Execution Plan (`G2`)

1. Author `docs/reports/milestones/M2.G/superpowers/spec.md`, `plan.md`, and initialize `evidence/workflow.md` per `AGENTS.md`.
2. Write reproducible verification script `docs/reports/milestones/M2.G/evidence/run_g2_checks.py` that:
   - Asserts `G0 == PASS`, `G1 == PASS`, and `M2.1`, `M2.2`, `M2.3` all `COMPLETE` in `docs/reports/milestones/README.md` + task sign-off receipts;
   - Preserves SHA256 hashes of `20261118_taxonomy_fix_v1`, `bm25-v3`, `retrieval_v1.json`, `retrieval_v2.json`, and `retrieval_v3_4_final_pilot.json`;
   - Compares `retrieval_v1.json` / `retrieval_v2.json` (weak-label `16` queries) vs `retrieval_v3_4_final_pilot.json` (human-verified `v2_pilot`);
   - Launches in-process FastAPI + Gradio `/demo/` (`create_app(..., mount_demo=True)`) wired to `20261118_taxonomy_fix_v1`, `bm25-v3`, and `retrieval_v3_4_final_pilot.json`, measures per-stage endpoint latency (`ms`) over `/health/live`, `/health/ready`, `/api/v1/demo/modules`, `/api/v1/evaluation/summary`, `/api/v1/analytics/niche-benchmark`, `/api/v1/retrieval/search`, `/api/v1/script/generate` (`offline_grounded`, fail-closed `gemini_free` `503`, out-of-domain `422`), and `/demo/` HTML;
   - Saves machine-readable `docs/reports/milestones/M2.G/evidence/g2_verification_receipt.json`.
3. Execute repository checks on current `main` HEAD (`dc595f04`+):
   - `.venv/bin/python docs/reports/milestones/M2.G/evidence/run_g2_checks.py`
   - `.venv/bin/python -m pytest -v`
   - `.venv/bin/python -m mypy packages apps pipelines`
   - `python3 scripts/check_secrets.py`
   - Clean wheel build check via `uv build --offline --wheel` into temporary `/tmp` dir + `.venv/bin/python -m pip check`
   - Relative markdown link check across `M2.G` files.
4. Summarize all verified outputs, stage timings, weak-label vs human-judged deltas, and known limitations in `docs/reports/milestones/M2.G/README.md` (`IN_PROGRESS` pending `N` & `K` formal `G2` confirmation), update `docs/reports/milestones/README.md`, and present a concise confirmation summary to `N`.
