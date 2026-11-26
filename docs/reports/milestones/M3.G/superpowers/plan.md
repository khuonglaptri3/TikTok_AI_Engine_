# M3.G Gate Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Unify `N`'s `M3.1` repeated-ingest replay receipt (`g3_capacity_and_replay_receipt.json`) and `K`'s deterministic `G3` verification probe (`run_g3_checks.py` + `test_m3_g_gate_checks.py`) across `20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2` (`452` native comments), and `m3_3_playwright_comments_20261125_v5` (`2,823` DOM comments) at `USD 0` spend with `0` byte mutations.

**Architecture:** `docs/reports/milestones/M3.G/evidence/run_g3_checks.py` provides importable verification, readiness-matrix, and 4-component capacity functions backed by `6` unit tests in `tests/unit/test_m3_g_gate_checks.py`, while `g3_capacity_and_replay_receipt.json`, `g3_verification_receipt.json`, and `g3-gate-decision-receipt.json` record both contributors' measured timings and freeze further live crawling.

**Tech Stack:** Python `3.11+`, `pyarrow`, `pandas`, `pydantic`, `pytest`, `mypy` (Linux + `--platform win32`), `packages.analytics.load_verified_corpus`, `packages.retrieval.HybridRetrievalService`, `pipelines.ingest_incremental_to_gold.ingest_incremental_batch_to_gold`.

**Spec:** `docs/reports/milestones/M3.G/superpowers/spec.md`

## Completed Tasks

- [x] **Task 1 (`N`, `2026-11-23`):** Execute disposable `/tmp` `M3.1` repeated-ingest replays (`update_existing=False` in `5.64 s`, `update_existing=True` in `6.14 s`, `0` duplicates, SHA-256 preserved), audit `29` `.mp3` durations (`46.683` min), and record `N_minutes = 15.0` in `g3_capacity_and_replay_receipt.json`.
- [x] **Task 2 (`K`, `2026-11-23`):** Implement TDD `run_g3_checks.py` and `tests/unit/test_m3_g_gate_checks.py` (`6/6` tests passing after whole-branch code review hardening: `.mp3` tamper/orphan checks, fail-closed `G0`/`M3.x` receipts, `15 K / 15 N` completeness & ID parity, `>= 150` comments & `>= 10` videos readiness transitions, dynamic telemetry, and `3 -> 2` duplicate-comment `update_existing=True` preservation probe).
- [x] **Task 3 (`K`, `2026-11-26`):** Re-execute unified `run_g3_checks.py` across `base`, `v1`, `v2` (`452` comments / `28` videos), and `v5` (`2,823` comments / `118` videos) -> `PASS in 22.819s` (`M4.1 = READY_UNBLOCKED`, `M5.1 = READY_UNBLOCKED`, `M5.2 = READY_UNBLOCKED`, `10/10` searchable, `0` byte mutations), record `K_minutes = 18.0`, and synchronize `M3.G/README.md`, `workflow.md`, and `docs/reports/milestones/README.md`.
