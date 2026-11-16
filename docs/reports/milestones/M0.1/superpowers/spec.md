# M0.1 — Specification: Legacy Audit, Secret Sanitization & Monorepo Baseline

- **Date:** 2026-11-16
- **Task ID:** `M0.1`
- **Owner:** Trần Đình Khương, AI Engineer

## Scope & Requirements
1. Audit the legacy `21KHDL-TikTok-Analytics` coursework codebase and dataset (`~1.50 GB`, `37,840` files) to document structural bugs, dropped metadata columns, and disconnected LLM prompt templates.
2. Purge 100% of hardcoded Gemini (`AIzaSy*`) and third-party API keys across all legacy files and enforce automated secret scanning via `scripts/check_secrets.py`.
3. Archive legacy notebooks, LaTeX reports, and Streamlit UI under `archive/legacy_coursework/` while preserving 100% of original data files intact on disk.
4. Establish the SenticRAG-aligned AI Engineering monorepo (`apps/`, `packages/`, `pipelines/`, `infra/`, `tests/`, `docs/`), Gold Corpus (`20261116_v1`), Vietnamese NFC BM25 index, Grounded Script Engine, and Dual-Sink 4-month incremental extension contracts.

## Acceptance Criteria
- `python3 scripts/check_secrets.py` reports `0` secret leaks across the workspace.
- Original `37,840` files (`1.50 GB`) remain intact on local disk; immutable Gold Corpus (`70,996` videos, `264` creators, `23,448` GPS POIs, `21,748` speech transcripts) passes SHA256 verification.
- `mypy` and `pytest` pass with zero errors.
