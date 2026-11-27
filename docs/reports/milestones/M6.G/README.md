# M6.G — Final Release & Hosting Decision Gate (`G6 = PASS` Local CPU Release; Public Hosting `BLOCKED`)

- Status: COMPLETE (All `23/23` upstream tasks `COMPLETE` and `G0`–`G5` `PASS`; deterministic `G6` probe [run_g6_checks.py](evidence/run_g6_checks.py) passed in `39.899 s` with `0` byte mutations across `5` Gold snapshots, offline `sdist + wheel` build `PASS`, end-to-end multimodal ASGI `/demo/` verified at `USD 0` spend, and joint `N` + `K` confirmation recorded in [g6-gate-decision-receipt.json](evidence/g6-gate-decision-receipt.json) on `2026-11-27`)
- Execution date: 2026-11-27 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M6.G`) & [TikTok_AI_Engine_Resources_and_Deployment.md](../../../planning/TikTok_AI_Engine_Resources_and_Deployment.md) (Section 5)
- Repository version: `main` (post-`8d6a2e8f`)
- Primary owner: Nguyễn Việt Nguyên (`N`, `2` pts) · Peer reviewer & probe author: Trần Đình Khương (`K`, `2` pts)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the final release and hosting readiness gate (`Gate G6`) across the unified `M0`–`M6` repository ([run_g6_checks.py](evidence/run_g6_checks.py) -> [g6_verification_receipt.json](evidence/g6_verification_receipt.json), [g6-gate-decision-receipt.json](evidence/g6-gate-decision-receipt.json)). Following owner-confirmed `N` + `K` concurrence across `M3.G` (`G3 = PASS`), `M4.G` (`G4 = PASS`), `M5.G` (`G5 = PASS`), `M6.1` (`COMPLETE`), and `M6.2` (`COMPLETE`), **`M6.G` is `COMPLETE` with two separate, explicit rulings**:

1. **Local CPU Release = `PASS` (`USD 0` Spend, `0` Network Dependency):**
   - All `6` prior gates (`G0`–`G5`) are `PASS` and all `23` upstream tasks (`M0.1`–`M6.2`) are `COMPLETE` with `0` byte mutations across all `5` SHA-256-verified Gold snapshots (`20261117_recovered_v1`, `20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`, `m3_3_playwright_comments_20261125_v5`).
   - Offline `uv build --offline` succeeded (`tiktok_viral_rag-0.2.0.tar.gz` = `233,699` B; `tiktok_viral_rag-0.2.0-py3-none-any.whl` = `290,994` B), workspace secret scanner exited `0`, and combined active demo artifacts occupy `154.87 MiB` on disk with `1,347.97 MiB <= 8,192 MiB` peak RSS.
   - End-to-end ASGI `/demo/` (`apps.demo.main:create_app`) verified all accepted `M0`–`M6` routes in milliseconds (`niche-benchmark = 17.10 ms`, `retrieval = 19.20 ms`, `offline_script = 44.56 ms`, `multimodal_catalog = 5.58 ms`, `multimodal_video_audit = 100.64 ms`, `/demo/` HTML = `64.17 ms`), enforcing `503 PROVIDER_KEY_MISSING`, `422 UNSUPPORTED_DOMAIN` on OOD/epistemic prompts, `hide_seeding = False` diagnostic-only comment flags, and `>= 3`-comment ABSA abstention.
2. **Conditional Public Hosting = `BLOCKED` (Data Redistribution Rights & Free-Tier Constraints):**
   - Per [M1.G](../M1.G/README.md) (`G1`) and [TikTok_AI_Engine_Resources_and_Deployment.md](../../../planning/TikTok_AI_Engine_Resources_and_Deployment.md), upstream TikTok transcripts (`70,996` historical + `130` fresh), `2,823` viewer comments (`@author_handle`), and `29` `.mp3` clips carry no public redistribution license. In addition, `Render Free` (`512 MB` RAM) OOMs on the `1,347.97 MiB` runtime footprint, and `Railway` / `Fly.io` lack a perpetual card-free tier. Public deployment is therefore honestly recorded as **`BLOCKED`** without invalidating the accepted local CPU release.

## Measured Runtime Latencies & Public Hosting Candidate Matrix

| Endpoint / Check (`apps.demo.main:create_app`) | Measured Latency / Value | Verified Outcome |
| --- | ---: | --- |
| Cold startup (`m3_3_pilot_snapshot_v2` + `bm25` + `v5` multimodal) | `9,823.69 ms` | `71,026` videos, `21,758` BM25 docs, `2,823` comments, `436` voice segs (`1,347.97 MiB` RSS) |
| `GET /health/ready` | `117.80 ms` | `status="ready"`, multimodal & historical snapshots verified |
| `POST /api/v1/analytics/niche-benchmark` | `17.10 ms` | HCMC `Review quán ăn` cohort quantiles & missingness |
| `POST /api/v1/retrieval/search` (`bm25` + rerank) | `19.20 ms` | Fresh `M3.3` query (`Đậu hũ thúi Quận 1`) resolved with valid citations |
| `POST /api/v1/script/generate` (`offline_grounded` / `503` / `422`) | `44.56 ms` | `guardrail.passed=True`; `503` missing key & `422` Bitcoin OOD enforced |
| `GET /api/v1/trust/corpus-videos` & `/corpus-video/{id}` | `5.58 ms` / `100.64 ms` | Full `M4.1` prosody + `M4.2` disclosure + `M5.1` seeding + `M5.2` NFC ABSA |
| `POST /api/v1/trust/disclosure-check` (epistemic guard) | `< 5 ms` | `HTTP 422 UNSUPPORTED_DOMAIN` on hidden-PR certainty prompt |
| `GET /demo/` (mounted Gradio Studio UI) | `64.17 ms` | `HTTP 200` (`163,546` B), 4 tabs, zero login/account system |

| Hosting Candidate | Free-Tier Spec & Sleep Limits | Resource Fit (`1.35 GiB` RSS / `155 MiB` Disk) | `G6` Ruling |
| --- | --- | --- | --- |
| **Hugging Face Spaces (CPU Basic)** | `2 vCPU`, `16 GB` RAM, `50 GB` ephemeral; `48h` idle sleep (`$0`) | Fits compute & disk | **`BLOCKED`** (`G1` upstream data redistribution & comment PII) |
| **Render Free Web Service** | `0.1 CPU`, `512 MB` RAM, ephemeral disk; `15m` spin-down (`$0`) | **Fails RAM (`1,348 MiB > 512 MiB`)** | **`REJECTED`** (OOM + `G1` redistribution rights) |
| **Railway / Fly.io** | Trial credit expiry / billing-method prerequisite | Fits compute | **`REJECTED`** (violates perpetual zero-card/zero-upgrade rule) |

## Work performed

- **Reciprocal upstream gate & task closure (`N` + `K`):** Recorded `N`'s owner-relayed confirmation across [M3.G](../M3.G/README.md), [M4.G](../M4.G/README.md), [M5.G](../M5.G/README.md), [M6.1](../M6.1/README.md), and [M6.2](../M6.2/README.md), bringing all `23` upstream deliverables to `COMPLETE`.
- **TDD `G6` verification suite ([test_m6_g_gate_checks.py](../../../../tests/unit/test_m6_g_gate_checks.py), [run_g6_checks.py](evidence/run_g6_checks.py)):** Authored `3` fail-closed unit tests (`RED -> GREEN`) and executed the full `G6` probe across `5` Gold snapshots, offline `sdist + wheel` build, live multimodal ASGI `/demo/`, and free-hosting candidate evaluation.

## Outputs

| File | Purpose |
| --- | --- |
| [g6-gate-decision-receipt.json](evidence/g6-gate-decision-receipt.json) | Formal `G6` decision (`local_cpu_release = PASS`, `public_hosting = BLOCKED`) confirmed by `K` & `N` |
| [g6_verification_receipt.json](evidence/g6_verification_receipt.json) | Measured package sizes, `5`-snapshot SHA-256 digests, `1,347.97 MiB` RSS, route timings, and hosting matrix |
| [run_g6_checks.py](evidence/run_g6_checks.py) | Deterministic executable Gate `G6` release & hosting verification script |
| [workflow.md](evidence/workflow.md) | Superpowers TDD (`RED -> GREEN`) and final release verification ledger |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M6.G/evidence/run_g6_checks.py` | PASS (`39.899 s`, `0` byte mutations) | `G0`–`G5` `PASS`, `23/23` upstream tasks `COMPLETE`, `sdist+whl` offline build, live ASGI `/demo/`; [g6_verification_receipt.json](evidence/g6_verification_receipt.json) |
| `python3 -m pytest tests/unit/test_m6_g_gate_checks.py -v` | PASS (`3 passed in 13.74s`) | Fail-closed gate/task readiness, hosting block rules, and live runtime guards |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`0` failures / `0` issues) | Full repository test suite and cross-platform static typing |
| `python3 scripts/check_secrets.py` & docs hygiene check | PASS (`0` leaks; `0` broken links) | Workspace secret hygiene and `24/24` milestone directory/index parity |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Upstream TikTok redistribution license absent (`G1`) | Public cloud hosting of raw/derived transcripts, `2,823` comments, and `29` `.mp3` clips remains `BLOCKED` | Retain local-only CPU demonstration unless upstream rights & PII redaction are separately cleared |
| Diagnostic-only `M5.1` comment flags, sparse `M5.2` `service` support (`0` gold in pilot), and deferred hidden-PR detection (`M4.2`) | Auto-filtering of comments and hidden-sponsorship probability claims remain disabled; `< 3`-comment aspect gaps abstain | Enforced transparently in API responses and `/demo/` UI banners |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| All released features have passing prior gates (`G0`–`G5`) & `COMPLETE` upstream tasks (`23/23`) | Met (`6/6` gates `PASS`, `23/23` tasks `COMPLETE`) | [g6_verification_receipt.json](evidence/g6_verification_receipt.json), [README.md](../README.md) |
| Full `pytest`, `mypy` (Linux & Win32), secret scanner, offline `sdist + wheel` build, and `5`-snapshot SHA-256 integrity | Met (`233 KB` `.tar.gz` + `291 KB` `.whl`, `0` secret leaks, `0` byte mutations) | [g6_verification_receipt.json](evidence/g6_verification_receipt.json) |
| Reproducible local CPU setup & separate honest public-hosting ruling confirmed by `N` & `K` | Met (`local_cpu_release = PASS`, `public_hosting = BLOCKED`) | [g6-gate-decision-receipt.json](evidence/g6-gate-decision-receipt.json) |

Final status: **`M6.G` is `COMPLETE` — Gate `G6` is `PASS` for the reproducible local CPU release (`USD 0`), and `public_hosting` is recorded as `BLOCKED` (`24/24` milestone tasks across `M0`–`M6` complete)**.
