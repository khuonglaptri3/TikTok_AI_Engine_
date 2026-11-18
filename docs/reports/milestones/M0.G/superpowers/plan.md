# M0.G (G0) — Execution Plan

1. Verify current git revision (`git rev-parse HEAD`), clean working tree, and completion status of `M0.1`, `M0.2`, and `M0.3`.
2. Run and archive fresh G0 verification checks on the recorded environment:
   - Environment & packaging probe (`python --version`, `pip check`, `import apps, packages, pipelines`, `docker --version` / daemon check).
   - Secret scan (`python scripts/check_secrets.py`).
   - Static checks (`ruff check`, `mypy packages apps pipelines`).
   - Contract, smoke, and full `pytest` suites (`pytest tests/contract tests/smoke -v`, `pytest -v`).
   - ASGI in-process readiness probe (`/health/live`, `/health/ready`, `/demo/`).
3. Record all results, exact revision, hardware/Python environment, and explicit limitations (upstream terms, semantic limits, Docker daemon status, `M0.3-UI-*` notes) into `evidence/g0_verification_receipt.json`, `evidence/workflow.md`, and `M0.G/README.md`.
4. Update `docs/reports/milestones/README.md` with the `M0.G` row and run final pre-handoff `scripts/check_secrets.py`.
