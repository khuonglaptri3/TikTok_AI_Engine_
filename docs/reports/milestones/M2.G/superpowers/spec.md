# M2.G — Specification: Historical Demonstration Decision (`G2`)

- **Task ID:** `M2.G` (Gate `G2`)
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer & Gate Approver:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.G`, lines 53, 93, 126)

## Scope & Objective
Evaluate and assemble all evidence required to decide Gate `G2` (`M2.G` — historical local CPU demonstration decision), strictly within `USD 0` spend and local-only data boundaries:
1. Verify prerequisite gates & tasks: `G0 == PASS` (`M0.G`), `G1 == PASS` (local-only, `M1.G`), and `M2.1`, `M2.2`, `M2.3` all `COMPLETE` with reciprocal review receipts.
2. Execute full repository verification on the pinned `main` commit: `pytest -v`, configured `mypy`, `scripts/check_secrets.py`, Ruff lint on package/app/pipeline/test targets, and clean wheel build + `pip check`.
3. Execute an asserting real-corpus ASGI probe (FastAPI + mounted Gradio `/demo/`) against `data/corpus/20261118_taxonomy_fix_v1` (`70,996` videos) and `artifacts/indexes/bm25-v3/` (`21,748` transcribed documents) with `$0` provider calls, measuring per-stage latencies (`ms`) across analytics, retrieval, offline grounded drafting, error/abstention boundaries, and `/demo/` UI HTML serving.
4. Contrast weak-label historical baseline results (`retrieval_v1.json`, `retrieval_v2.json` over `16` queries) against two-contributor human-verified `v2_pilot` results (`retrieval_v3_4_final_pilot.json` over `20 dev / 20 locked_test`) and `M2.3` `30`-draft full-transcript claim audit (`108/120 = 90.00%` supported, `30/30` cited, `0` fabricated IDs).
5. Document all known limitations and explicit `G2` scope boundaries (local CPU historical core only; does not grant `G3–G6`, multimodal trust, live trends, live crawling, or public hosting), leaving formal `G2 = PASS` confirmation to `N` & `K`.
