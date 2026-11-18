# M0.3 — Superpowers Workflow Provenance

- **Date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M0.3`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, pending independent reproduction)
- **Skills read and applied:** `using-superpowers`, `brainstorming`, `writing-plans`, `executing-plans`, `verification-before-completion`
- **Authorization provenance:** Explicit owner request on `2026-11-18` to run `python scripts/dev.py run-demo` on the real recovered corpus (`20261117_recovered_v1` and `bm25-v2`), test `/demo/` in `offline_grounded` mode (search citations, draft labeling & source excerpt matching, benchmarks & timings, and invalid input handling), and record all results, outputs, and remaining issues in `docs/reports/milestones/M0.3/`.

## Process & Rulings
1. **Authored Planning Files First:** Created `docs/reports/milestones/M0.3/superpowers/spec.md` and `docs/reports/milestones/M0.3/superpowers/plan.md` prior to launching the live demo verification.
2. **Windows Subprocess Cleanup Ruling:** An initial probe run (`task-79`) used `subprocess.PIPE` on `scripts/dev.py run-demo`; on Windows, terminating the parent wrapper left the child `uvicorn` process holding the pipe handle open during `proc.communicate()`. Replaced pipe buffering with direct file redirection to `evidence/run-demo-server.log` and `taskkill /F /T /PID` process-tree cleanup, completing cleanly in `40.2s` (`2026-11-18T03:46:50Z–03:47:31Z`, exit code `0`).
3. **Zero-Spend & Zero-Network Discipline:** Executed with `GEMINI_API_KEY=""` and `GRADIO_ANALYTICS_ENABLED="False"`. Confirmed `provider_calls = 0` and `provider_spend_usd = 0.0`.
4. **Honest Issue Recording:** Recorded all real-data and UI observations without masking them: FastAPI/Pydantic `422` validation errors vs. `ViralRagError` formatting in `/demo/` (`M0.3-UI-1`, `M0.3-UI-2`), hardcoded `mode="hybrid_rrf"` / `total_cands=5` header in Tab 1 (`M0.3-UI-3`), mid-clause word-budget truncation in `offline_grounded` beats (`M0.3-DRAFT-1`), and song-lyric historical transcripts / unfiltered city lexical hits (`M0.3-DATA-1`).

## Commands & Verification Receipts
- Live server & `/demo/` probe (`uv run --offline --no-project --python 3.12 --with '.[demo,dev]' python .../verify_m03_demo.py`): `EXIT=0` -> [run-demo-server.log](run-demo-server.log), [demo-live-verification.json](demo-live-verification.json), [demo-rendered-outputs.md](demo-rendered-outputs.md).
- Package & Docker COPY-context wheel build receipt: `EXIT=0` -> [package-final.log](../../../tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/package-final.log).
- Full test suite & static checks at `c3348e9`: `63 passed` ([pytest-current.log](../../../tasks/team-progress-sync-2026-11-18/evidence/pytest-current.log)), `mypy` over `76` files ([mypy-current.log](../../../tasks/team-progress-sync-2026-11-18/evidence/mypy-current.log)).
- Workspace secret scan (`python scripts/check_secrets.py`): `EXIT=0` (`Zero secret leaks detected`).
