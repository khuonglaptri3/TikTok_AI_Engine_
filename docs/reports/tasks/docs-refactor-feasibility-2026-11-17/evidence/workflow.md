# Workflow provenance

## Authorization and scope

The owner requested review of `docs/` and `ReFactor_structure/` and then supplied `https://github.com/TrggTin/21KHDL-TikTok-Analytics` as the data source. This authorizes a substantive audit and its mandatory report artifacts, not implementation or data mutation. Planning files were created on 2026-11-17 before substantive investigation; no earlier work is described as Superpowers execution.

## Skills actually read

Installed package: `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`.

| Skill path relative to package | Application |
| --- | --- |
| `using-superpowers/SKILL.md` and `using-superpowers/references/codex-tools.md` | Read first; used to select applicable process skills and available collaboration tools. |
| `writing-plans/SKILL.md` | Read; used for scoped specification, checkable investigation plan, and self-review. Owner-required report location overrides default paths. Code implementation handoff does not apply to this authorized audit. |
| `dispatching-parallel-agents/SKILL.md` | Read; used for independent, read-only review domains with isolated contexts. |
| `executing-plans/SKILL.md` | Read for applicability; its implementation, TDD, worktree, and commit machinery is not being claimed as followed for this documentation-only investigation. |
| `verification-before-completion/SKILL.md` | Read; applies before any completion claim and final evidence validation. |
| `systematic-debugging/SKILL.md` | Read after audit failures were observed; used for root-cause confirmation, minimal controlled reproductions, and separating missing-data/environment errors from product defects. No product implementation/fix phase was performed. |
| `requesting-code-review/SKILL.md` | Read; used to request a fresh isolated review of the synthesized audit, supporting evidence, and acceptance scope. This is a report review rather than a code merge. |

## Execution record

- Preliminary actions: read process skills and root `AGENTS.md`, list requested documents, confirm clean `main` worktree, inspect project dependency declarations, and open the owner-supplied upstream repository.
- Canonical specification: [spec.md](../superpowers/spec.md).
- Canonical investigation plan: [plan.md](../superpowers/plan.md).
- Independent read-only domains were delegated with isolated contexts: all six refactor documents and implementation consistency; all nine original `docs/` files and scientific scope; pinned upstream data availability/schema/provenance. The root reviewed all three delivered evidence files and reconciled overlapping findings.
- The document inventory records 15 original files with SHA256. The only planned original-document mutation is a navigation link from the milestone index to independent task reports; final source-integrity verification treats that exact file as an authorized change and checks every other inventoried document unchanged.
- Data source: upstream commit `f142e5656a220f94f8024de168b0832754b3bd9e`. Public tree/schema/aggregate inspection was bounded; no complete repository clone, historical TikTok recrawl, provider call, raw identity persistence, or source dataset mutation occurred. Details and sampling limits are in [upstream-data-review.md](upstream-data-review.md).
- Working Python: explicit managed Python 3.12.14, since WindowsApps `python`/`python3` aliases do not work on this machine. An ephemeral uv environment installed the project with `demo,dev` extras; no `.venv`, lockfile, or dependency declaration was added to the project. Normal ignored Python/test/type-check caches may be created by checks.
- Full existing tests: `uv run --no-project --python 3.12 --with '.[demo,dev]' python -m pytest --tb=short` returned exit 1, with 15 passed and 5 failed in 35.19 seconds. All five failures require absent raw/Gold inputs; see [pytest-full.log](pytest-full.log). These results supersede any assumption that historical pass claims reproduce in this checkout.
- Fresh type check: same ephemeral environment, `python -m mypy packages apps pipelines`, exit 0, no issues in 74 source files; see [mypy.log](mypy.log).
- Controlled probes: [runtime-probes.py](runtime-probes.py) exercised guardrails and temporary synthetic snapshots only. [runtime-probes.json](runtime-probes.json) records false passes, Sink B loss on second ingestion/replay, and accepted base/output collision. An initial audit fixture incorrectly used zero videos, which the manifest correctly rejected; the fixture was corrected to one baseline video before the successful product-defect reproductions. This fixture correction is not described as a product failure or fix.
- Packaging checks: base `uv run ... --with . python -c 'import apps.api.app.main'` failed on missing Gradio. A temporary directory reproducing Dockerfile COPY inputs failed wheel packaging because `pipelines` was omitted. Full project wheel construction with extras succeeded. No Linux Docker image was built or deployed.
- Current official Google, Hugging Face and Render pages were read for unstable model/quota/hosting facts; [external-and-runtime-review.md](external-and-runtime-review.md) records dates, direct sources, scope, and account/resource unknowns.
- Independent final audit review was delegated to a fresh agent against uncommitted report artifacts at baseline `cdbc6ed9ccad11db437aa66c68638cf018701fe5`. Its observations and dispositions are recorded in [report-review.md](report-review.md).
- Final reviewer found no Critical/Important factual issues and one minor wording issue: the configured mypy command is not the full `--strict` profile. The main report now calls it project-configured mypy; the recorded passing result is unchanged.
- A preliminary integrity run deliberately exposed the not-yet-generated verification/hash records, pending review file, and in-progress status as failing handoff checks. Those were not product defects. The final run uses the completed bundle and synchronized independent-task index; its machine-readable result is the handoff authority.
- No product fix, status adjustment, data restoration, commit, or deployment was performed. Existing milestone reports and plans remain byte-identical; the milestone index has only an independent-report navigation link. The independent task index and audit bundle are the new deliverables.

## Workflow adaptation and remaining work

The writing-plans skill's code-implementation handoff and the executing-plans skill's TDD/commit/worktree machinery were not applied: the owner authorized investigation and mandatory documentation, and no product implementation was requested. This is explicitly an adapted Superpowers investigation, not a claim of executing the full software-development cycle. Process skills were read in the installed user-level package; none were copied into the repository.

Actual product defects, unavailable data, incomplete collectors/models, scientific-label issues, and hosting/provider decisions remain open. Audit completion means delivery of an evidenced assessment only, without changing milestone statuses or passing gates. Final layout/link/hash/secret checks are recorded in [verification.json](verification.json); their output, not a scaffold alone, determines documentation handoff readiness.
