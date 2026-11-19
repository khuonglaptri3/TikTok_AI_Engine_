# M2.G — Historical Core & Local Demonstration Gate (`G2 = PASS`, Local Historical Core)

- Status: COMPLETE (All technical checks, clean package/source build, real-corpus ASGI `/demo/` stage timings, and `M2.1`–`M2.3` evidence audits passed on `main` @ `dc595f04`; confirmed by `N` and `K` on `2026-11-19T16:50+07:00`)
- Gate result: PASS for narrow historical local CPU core (`G0 = PASS`, `G1 = PASS` local-only, `G2 = PASS`; `G3`–`G6` remain `NOT_RUN`)
- Execution date: 2026-11-19 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.G`)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer & gate approver: Trần Đình Khương (`K`)
- Repository version: `main` @ `dc595f04e527289ff4e84a6d5380eb9f5c95a621`
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

All technical, packaging, and real-corpus runtime criteria for Gate `G2` (`M2.G`) have been executed and verified on `main` (`dc595f04`) with `0` code mutations to immutable snapshots or historical benchmarks, and formally confirmed by both contributor `N` and peer reviewer/approver `K` ([g2-gate-decision-receipt.json](evidence/g2-gate-decision-receipt.json)). **`M2.G` is `COMPLETE` and Gate `G2` is `PASS` for the narrow historical local CPU core**:
- **Prerequisites (`COMPLETE` & Reviewed):** [M0.G](../M0.G/README.md) (`G0 = PASS`), [M1.G](../M1.G/README.md) (`G1 = PASS`, local-only), [M2.1](../M2.1/README.md) (`COMPLETE` + `K` Linux/Windows reproduction), [M2.2](../M2.2/README.md) (`COMPLETE` + `K`/`N` `408`-pair sign-off & `N` peer review), and [M2.3](../M2.3/README.md) (`COMPLETE` + `K`/`N` `30`-draft / `120`-beat full-transcript claim audit & `K` peer review).
- **Full Repository Verification (`dc595f04`):** `177/177` `pytest` passed (`25.44s`), `95/95` source files clean in `mypy`, `0` secret leaks (`scripts/check_secrets.py`), clean `uv build` source `.tar.gz` (`131K`) + `.whl` (`171K`), and `pip check` clean.
- **Real-Corpus ASGI + Gradio `/demo/` (`20261118_taxonomy_fix_v1` + `bm25-v3`, `USD 0`):** Cold startup `3,125.34 ms`, `/health/ready` (`70,996` total / `21,748` indexed) `29.56 ms`, niche analytics (`13,347` matched) `12.85 ms`, hybrid retrieval (`5` items) `39.58 ms` (`total_ms=36.90`), no-answer abstention `6.25 ms`, offline grounded script generation (`4` beats, `guardrail=True`) `53.57 ms`, fail-closed missing-key (`503`) & OOD (`422`), and `/demo/` HTML (`67,990` bytes) `23.13 ms`.

## Weak-Label Baseline vs. Human-Verified `v2_pilot` Comparison

| Benchmark | Snapshot & Corpus Scope | Query / Label Basis | BM25 `MRR@10` / `nDCG@10` | BM25+Rerank `MRR@10` / `nDCG@10` | Guardrails & Latency |
| --- | --- | --- | --- | --- | --- |
| [retrieval_v2.json](../../../../artifacts/benchmarks/retrieval_v2.json) | `20261117_recovered_v1` (`21,748` indexed) | `16` v1 keyword weak labels (`lexical_metadata_weak_labels`, regression only) | `0.8875` / `0.6962` (`Recall@10=0.1837`) | `0.8127` / `0.7083` (`Recall@10=0.1901`) | Mean `17.24 ms` / `p95=37.04 ms` (`rerank p95=86.73 ms`) |
| [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) | `20261118_taxonomy_fix_v1` (`21,748` indexed) | `40` disjoint (`20 dev / 20 locked_test`), `two_human_verified_pooled_judgments` (`408/408` `K` & `N` signed off) | Test `14`-pos: **`0.7976`** / **`0.7819`** (all-`16`: `0.6979` / `0.6842`) | Test `14`-pos: **`0.8571`** / **`0.7178`** (all-`16`: `0.7500` / `0.6281`) | **`4/4` (`100%`)** no-answer abstain (`0` fab), **`0/16`** false abstain, warm `p95`: `15.61 ms` (`reranked 32.44 ms`) |

- **Descriptive Analytics ([M2.1](../M2.1/README.md)):** Linux `warm p95 = 17.57 ms` (`cold = 10.08 ms`), Windows `K` reproduction `warm p95 = 38.81–40.92 ms` (`<= 250 ms`), zero-division & `< 5` sparse-slice abstention verified.
- **Script Grounding & Audit ([M2.3](../M2.3/README.md)):** `30/30` (`100%`) structural/timing/membership/citation coverage pass, `0` fabricated IDs, **`108/120` (`90.00% >= 90%`)** human-verified supported culinary claims (`K` & `N` both confirmed), `0` provider calls offline, `<= 2` calls/turn bound on `gemini_free`.

## Real-Corpus ASGI `/demo/` Stage Timings (`run_g2_checks.py`)

Measured in-process over `data/corpus/20261118_taxonomy_fix_v1` (`70,996` videos) + `artifacts/indexes/bm25-v3/` (`21,748` indexed) + [retrieval_v3_4_final_pilot.json](../../../../artifacts/benchmarks/retrieval_v3_4_final_pilot.json) ([g2_verification_receipt.json](evidence/g2_verification_receipt.json)):

| Stage / Endpoint | Measured Latency (`ms`) | Verified Outcome |
| --- | ---: | --- |
| FastAPI + Gradio app startup (`create_app(..., mount_demo=True)`) | `3,125.34 ms` | Loaded verified Gold corpus + `bm25-v3` (`USD 0`, offline) |
| `/health/live` & `/health/ready` | `4.64 ms` / `29.56 ms` | `status="ready"`, `total_videos=70,996`, `indexed_bm25_videos=21,748` |
| `/api/v1/evaluation/summary` | `1.76 ms` | Returned `benchmark_id="retrieval_v3_4_final_pilot"` |
| `/api/v1/analytics/niche-benchmark` | `12.85 ms` | `matched_videos=13,347` (HCMC `Review quán ăn`), `sparse_slice_abstained=False` |
| `/api/v1/retrieval/search` (answerable `hybrid_rrf` + rerank) | `39.58 ms` (`total_ms=36.90`) | `5` items returned (`bm25=1.23 ms`, `dense=24.71 ms`, `rerank=6.71 ms`) |
| `/api/v1/retrieval/search` (`no_answer` guardrail) | `6.25 ms` | `insufficient_evidence=True`, `items=[]` (`no_candidate_matches_query_anchors`) |
| `/api/v1/script/generate` (`offline_grounded`, `503`, `422`) | `53.57 ms` | `4` beats, `guardrail.passed=True`, `503 PROVIDER_KEY_MISSING`, `422 UNSUPPORTED_DOMAIN` |
| Mounted Gradio UI (`GET /demo/`) | `23.13 ms` | `HTTP 200`, `67,990` bytes rendered |

## Outputs

| File | Purpose |
| --- | --- |
| [g2-gate-decision-receipt.json](evidence/g2-gate-decision-receipt.json) | Formal `G2 = PASS` (`M2.G = COMPLETE`) decision receipt confirmed by `N` & `K` |
| [workflow.md](evidence/workflow.md) | `M2.G` workflow ledger and verification commands |
| [run_g2_checks.py](evidence/run_g2_checks.py) | Reproducible asserting `G2` probe (`G0/G1/M2.1-M2.3`, SHA256 preservation, weak-vs-human comparison, real-corpus ASGI `/demo/`) |
| [g2_verification_receipt.json](evidence/g2_verification_receipt.json) | Machine-readable `G2` verification receipt, stage latencies, and SHA256 hashes |
| [g2_checks.log](evidence/g2_checks.log) | Console output from `run_g2_checks.py` (`PASS in 3.858s`) |
| [g2_build.log](evidence/g2_build.log), [g2_mypy.log](evidence/g2_mypy.log), [g2_pytest.log](evidence/g2_pytest.log) | Clean `uv build` (`sdist + wheel`), `95`-file `mypy`, and `177`-test `pytest` logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python docs/reports/milestones/M2.G/evidence/run_g2_checks.py` | PASS (`3.858s`, `0` byte mutations) | `G0/G1` + `M2.1–M2.3` receipts, SHA256 hashes, weak-vs-human summary, real-corpus ASGI `/demo/`; [g2_verification_receipt.json](evidence/g2_verification_receipt.json) |
| `uv build --out-dir "$TMP_W" .` + `.venv/bin/python -m pip check` | PASS (`sdist 131K` + `wheel 171K`; `No broken requirements`) | Clean source distribution & wheel build from repository root; [g2_build.log](evidence/g2_build.log) |
| `.venv/bin/python -m pytest -v` | PASS (`177 passed in 25.44s`) | Full repository contract, eval, smoke, and unit suite; [g2_pytest.log](evidence/g2_pytest.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`95/95` source files) | Full static type check; [g2_mypy.log](evidence/g2_mypy.log) |
| `.venv/bin/python -m ruff check .../run_g2_checks.py` & `python3 scripts/check_secrets.py` | PASS (`0` Ruff errors, `0` secret leaks) | Script lint & full workspace secret hygiene |

## Open issues & Explicit Gate Boundaries

- **Known Historical-Corpus Limitations:** (1) `M2.2` reports dual denominators because `2/16` `locked_test` answerable queries (`t_k04`, `t_k07`) have empty positive pools in top-10 BM25 (`14/16` vs `16/16`), (2) `M2.3` records `9/120` unmarked song-lyric beats (`C1`) and `3/120` upstream location-mislabel / `"vibe Đà Lạt"` beats (`C2`) lowering whole-draft editorial fitness to `20/30` (`66.67%`), and (3) public corpus redistribution remains **`BLOCKED`** per [M1.G](../M1.G/README.md).
- **Explicit `G2` Scope Boundary:** Passing `G2` approves **only the narrow historical local CPU demonstration core** (`M2.1`–`M2.3` on recovered Gold snapshots). It does **not** certify multimodal trust/seeding detection (`M4`/`M5`), live TikTok collection (`M3.2`/`M3.3`), real-time trend forecasting, live free-tier Gemini quota availability, or public hosting (`G6`).
- **Formal Sign-Off Recorded (`2026-11-19T16:50+07:00`):** Both `N` (primary owner) and `K` (peer reviewer & gate approver) confirmed `G2 = PASS` in [g2-gate-decision-receipt.json](evidence/g2-gate-decision-receipt.json).

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| `G1 = PASS` and `M2.1–M2.3` `COMPLETE` & reviewed | Met | [M1.G](../M1.G/README.md), [M2.1](../M2.1/README.md), [M2.2](../M2.2/README.md), [M2.3](../M2.3/README.md) |
| Full `pytest`, configured `mypy`, secret scanner, clean package/source build | Met (`177 passed`, `95 files mypy`, `0` leaks, `sdist+whl` built) | [g2_pytest.log](evidence/g2_pytest.log), [g2_mypy.log](evidence/g2_mypy.log), [g2_build.log](evidence/g2_build.log) |
| Actual recovered-corpus ASGI `/demo/`, timings, weak-vs-human comparison & limits | Met (`20261118_taxonomy_fix_v1` + `bm25-v3`) | [g2_verification_receipt.json](evidence/g2_verification_receipt.json) |
| Formal gate confirmation (`N` + `K`) | Met (`G2 = PASS`, `2026-11-19T16:50+07:00`) | [g2-gate-decision-receipt.json](evidence/g2-gate-decision-receipt.json) |

Final status: **`M2.G` is `COMPLETE` and Gate `G2` is `PASS`** (narrow historical local CPU core only; `G3`–`G6` remain `NOT_RUN`).
