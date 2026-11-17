# Provider, deployment, and runtime review

- Inspection date: 2026-11-17 (Asia/Saigon).
- Local revision: `cdbc6ed9ccad11db437aa66c68638cf018701fe5`.
- External pages describe publicly documented conditions, not the owner's verified account entitlements. No provider request, deployment, payment configuration, or model inference was performed.

## External conditions

### E01 - HIGH: the default Gemini model needs a current free-tier compatibility decision

The repository defaults to `gemini-2.5-flash` (`packages/common/settings/__init__.py:31,62`). Google's current deprecation notice says access is restricted to prior active users and that requests will route to a billed replacement from 2026-12-01. This is a near-term compatibility and zero-spend risk, not proof that this owner's existing free key has already stopped working. Model availability and eligibility must be verified before enabling online synthesis; leave it disabled if a genuinely free eligible model cannot be established. [Official deprecation schedule](https://aistudio.google.com/docs/deprecations#gemini-2.5-flash-models).

The documented quota is project-specific and includes RPM, TPM, and RPD; a hardcoded 15 RPM is a local throttle, not a provider guarantee. Record the actual model/project allowance without exposing the key, bound tokens and calls, and return the documented blocked state when unavailable. [Official rate-limit documentation](https://aistudio.google.com/docs/rate-limits). The client does not inspect billing eligibility. No paid fallback is useful but does not itself prove USD 0 execution.

### E02 - HIGH: free hosting must be validated against plan prerequisites

Hugging Face currently distinguishes free hourly CPU Basic hardware from eligibility to create Gradio/Docker Spaces: ordinary new compute Spaces require a paid account plan. A limited free personal ZeroGPU exception is a separate profile and does not validate the specified CPU-only ASGI deployment. Therefore CPU Basic must not be accepted as satisfying the owner's no-paid-plan prerequisite. Its documented default resources are 2 CPU cores, 16 GB RAM, and 50 GB ephemeral disk; free execution may sleep. [Official Spaces overview](https://huggingface.co/docs/hub/spaces-overview). This is an evaluated candidate, not a claim that the existing project selected it.

Render documents a genuine Free web-service option, but with 0.1 CPU and 512 MB RAM, sleep after 15 idle minutes, ephemeral storage, and 750 shared instance-hours/month. Without a payment method, exhausted included bandwidth suspends services and exhausted build allowance disables builds; with billing enabled, supplementary usage can be charged. [Free service limits](https://render.com/docs/free), [compute resources](https://render.com/docs/compute-plans). It is only a candidate for a measured small read-only demo with billing disabled. Full-corpus Pandas, CSR indexes, neural models, Gradio, Redis, and Qdrant have not been shown to fit. No host is certified by this audit; local CPU demonstration remains the supported feasibility baseline.

## Local root causes and fresh verification

| Check | Actual result | Interpretation / evidence |
| --- | --- | --- |
| Resolve/build project with demo/dev extras in an ephemeral uv environment | PASS | Project package builds and dependencies install on Windows Python 3.12.14; no dependency lock was added. Versions are recorded in [runtime-probes.json](runtime-probes.json). |
| Full existing pytest suite | FAIL: 15 passed, 5 failed in 35.19 s | All five failures require missing raw/Gold assets. This is an unreproduced data-dependent runtime, not evidence that all five algorithms are defective. [Full output](pytest-full.log). |
| `mypy packages apps pipelines` | PASS: 74 source files | Fresh type checking, not model accuracy or deployment verification. [Output](mypy.log). |
| Base installation API import without demo extra | FAIL: missing `gradio` | `apps/api/app/main.py:6` imports Gradio unconditionally while `pyproject.toml:34-37` makes it optional. [Output](base-install-import.log). |
| Wheel build with the Dockerfile's copied source set | FAIL: missing `pipelines` package | Dockerfile copies `packages`, `apps`, and `configs`, while Poetry's package list requires `pipelines`. This was a controlled packaging reproduction, not an actual Linux image build. [Output](docker-context-build.log). The Dockerfile also installs base dependencies without the required demo extra. |
| Direct citation/duration/empty-script probes | Defects reproduced | An uncited statement gets a source ID, citation ratio 1.0, and `passed=true`; 3 seconds of dialogue targeting 300 seconds passes; empty dialogue passes. [Inputs and code](runtime-probes.py), [results](runtime-probes.json). |
| Sequential synthetic incremental batches | Defects reproduced | A then B retains video rows but only B's voice/comments/ABSA; replaying A empties those tables. Passing the base directory as output is accepted and rewrites its manifest. All writes were in automatically cleaned temporary fixtures. [Results](runtime-probes.json). |
| Secret check | PASS | The repository scanner detects its supported patterns only; it does not prove historic sanitization, revocation, or complete secret coverage. Final execution is recorded in [verification.json](verification.json). |

## Additional boundary weaknesses

- `llm_deadline_seconds` and `max_llm_calls_per_turn` are declared settings, but no use enforces them around the actual provider operation. The current script generation makes one explicit call; this audit does not claim it currently makes more than two. The settings model accepts five, which is outside the owner's allowed bound, as demonstrated in the controlled probe. The SDK call has no project-configured timeout/output-token bound passed to it (`packages/llm/clients/gemini.py:99-107`).
- The Redis limiter reads a count and adds a request in separate operations (`packages/llm/clients/gemini.py:39-49`), so concurrent callers can pass the same count. The single-process in-memory limiter has a lock. Distributed quota safety is unverified; it must not inherit the local unit-test claim.
- No fresh full-corpus latency, dense retrieval, ASR throughput, live crawl success, Gemini output quality, host memory fit, or public deployment was measured. The 21 ms artifact is a historical BM25/rule-reranker result.
- On this Windows machine, `python`/`python3` resolve to nonfunctional WindowsApps aliases, while a working managed Python 3.12.14 exists. Audit checks used its explicit executable or uv; this environment finding does not invalidate the documented Python 3.11+ requirement.

## Follow-up conditions

Before deployment, make base/demo dependencies and the image build consistent; package or retrieve checksum-pinned permitted Gold/index artifacts; measure cold/warm startup, peak memory, and response latency; choose a current free eligible provider profile with bounded failures; and record the selected host's exact account, storage, sleep, quota, and no-overage configuration. Keep crawling, ASR, and index generation offline from the thin demonstration service unless measured resources establish otherwise.
