# Team scope - AI modules and simple demonstration (2026-11-17)

This project (`TikTok_AI_Engine_`) is delivered by two equal contributors, Trần Đình Khương and Nguyễn Việt Nguyên ([NguyenVietNguyen2612](https://github.com/NguyenVietNguyen2612)). Split estimated delivery, evaluation, integration and reciprocal review effort equally across the active plan; do not infer skill tiers from public profiles. Deliver the selected AI modules, serve their results through typed AI APIs, and connect those APIs to one simple UI for demonstration.

- Build the AI logic, relevant data preparation, hybrid retrieval/model workflows, multimodal evaluation, inference serving, bounded failures, and per-module latency measurements (`ms`).
- Use one lightweight Gradio UI (`/demo/`) mounted over ASGI transport to present actual AI outputs, citations, Niche Micro-Benchmarks, ABSA/Seeding diagnostics, errors, and stage timings. Do not add login, accounts, user-role workspaces, or a product session system.
- Product CRUD, creator/merchant billing portals, operational ad-buying actions, enterprise cloud administration, and business-pilot KPI studies are excluded from the active project plan. Both contributors share typed AI API and demo integration work; no separate product-backend handoff guide is required.
- **Dual-Tier Data Preservation & Incremental Discipline:**
  1. **Historical Corpus (`1.50 GB`, `37,840` files, `2023-11` to `2025-03`):** Preserve 100% of original raw/interim/legacy files untouched on local disk (never re-crawl historical videos). Serve downstream analytics and RAG exclusively from immutable, SHA256-verified Gold Parquet snapshots (`data/corpus/<snapshot-id>/`).
  2. **Fresh Rolling 4-Month Stream (`data/raw_incremental/`):** Crawl only the latest 4-month window (`Metadata + 64kbps .mp3 Audio + Comments`) and run the **Dual-Sink Normalization Pipeline** (`pipelines.ingest_incremental_to_gold`) to both (a) append normalized 49-column rows into `fact_videos.parquet` for RAG/Trend freshness and (b) populate `fact_voice_segments.parquet`, `fact_comments.parquet`, and `fact_absa_reviews.parquet` for Voice Prosody, Seeding Detection, and KOC-vs-Viewer ABSA.
- **Zero Paid Spend & Secret Hygiene:** Development and demo run locally on CPU with measured per-stage timing. Online LLM synthesis uses only the owner's Gemini Free-Tier API (`GEMINI_API_KEY` stored solely in gitignored `.env`, enforced by `python3 scripts/check_secrets.py` before every commit). Provider/GPU spend is capped at `USD 0`; enforce `<= 2` LLM calls per turn with sliding-window RPM rate limiting, explicit `QuotaBlockedError` / `ProviderKeyMissingError`, and zero fallback to paid models.
- Deployment must use a genuinely free hosting tier with no paid plan prerequisite, add-ons, overages, or automatic upgrade; record sleep/quota/storage limits honestly.

The current [AI-only milestone plan](docs/planning/TikTok_AI_Engine_Milestone.md) and [resources guide](docs/planning/TikTok_AI_Engine_Resources_and_Deployment.md) define the active scope and supersede legacy coursework documentation archived locally under `archive/legacy_coursework/`.

# Preserve the root README as the project overview

- Keep the root `README.md` focused on the overall project purpose, dual-persona value layers (Creator Script Intelligence + Consumer ABSA/Seeding Trust), system architecture, repository structure, and a practical Quickstart.
- Preserve its overview sections when making targeted updates. Do not replace the overall `README.md` with a single milestone report, implementation checklist, provider incident summary, or current task narrative. A wholesale rewrite requires an explicit owner request.
- Put progress, measured benchmark results, provider observations, blockers, and acceptance evidence in the relevant milestone reports (`docs/reports/milestones/`); keep milestone status in `docs/planning/` and scope/process rules in `AGENTS.md`. Short navigation links from `README.md` are sufficient.
- Update setup/run examples when actual commands change, while retaining the overview.

# Case study storage

- Store every newly authored or revised case study in `docs/reports/Case_Study/<case-study-id>/`. Use the exact `Case_Study` spelling. This location takes precedence over milestone/task report locations for case-study narratives, including studies about a milestone.
- Each case-study directory contains exactly `README.md`, `evidence/`, and `superpowers/` at its top level. `README.md` is the single current narrative; `superpowers/` contains exactly `spec.md` and `plan.md`. Put case-study-specific analysis, verification, workflow provenance, and archived versions in `evidence/`.
- Keep original experiment results with their owning milestone/task and link to them from the case study. Distinguish original measurements from later retrospective analysis; avoid duplicate current narratives.
- Maintain `docs/reports/Case_Study/README.md` as the case-study index when adding or updating a study.
- For every attempted measure, explain the problem, why the measure was tried, what was actually implemented, the observed result, and the remaining limitation. Separate controlled tests from live measurements and implemented changes from proposed remedies.
- Apply the English-language, mandatory planning, workflow-provenance, and evidence-integrity requirements below to case studies. Documentation completion does not change the related milestone or gate status.

# Reporting conventions for milestone tasks

When working on a milestone task, organize its report using these conventions so reviewers can find the results immediately upon opening the task directory. All reports must be written in **English**, prioritizing conclusions, evidence, and outstanding work. This language requirement includes report titles, headings, narrative, table labels, review indexes, and authored supporting documentation. Preserve original Vietnamese source quotations, queries, commands, and raw logs when needed for evidence integrity.

## 1. Required structure

Each task has its own directory at `docs/reports/milestones/<TASK-ID>/`, using the exact ID from the plan, such as `M0.1`, `M1.1`, or `M0.G`.

```text
docs/reports/milestones/
├── README.md                 # Task index and quick review links
├── M0.1/
│   ├── README.md             # M0.1 results report
│   ├── evidence/             # Supporting material for M0.1
│   └── superpowers/
│       ├── spec.md           # Task scope, requirements, and acceptance
│       └── plan.md           # Execution steps and verification plan
└── M1.1/
    ├── README.md             # M1.1 results report
    ├── evidence/             # Supporting material for M1.1
    └── superpowers/
        ├── spec.md
        └── plan.md
```

The task directory must contain exactly two directories and one report at its top level:

1. **`README.md`:** the main report for user review.
2. **`evidence/`:** supporting files such as CSV, JSON, logs, images, check results, manifests, detailed tables, or supplementary documentation (including `workflow.md`).
3. **`superpowers/`:** exactly two files, `spec.md` and `plan.md`, containing the task specification and execution plan. This is a sibling of `evidence/`, not a subdirectory inside it.

Both planning files are mandatory for every started task, including audits, research, and documentation. Do not omit either file or replace it with a "Not applicable" statement. Reports must reside inside their task directory; do not place standalone reports or raw CSV/JSON/log files alongside `README.md`. Create a task directory only when work begins or results need to be reported.

## 2. Main report content

The first few lines of `README.md` must communicate the outcome before presenting details. Include:

- **Task information:** ID, name, actual status, execution date, and requirement source. Include the branch/commit when results are tied to a repository version.
- **Conclusion:** achievements, remaining gaps, and important limitations; distinguish verified results from assumptions.
- **Work performed:** meaningful changes or findings, without reproducing the entire action history.
- **Outputs:** a table of filenames, purposes, and relative links to files in `evidence/`.
- **Planning records:** relative links to `superpowers/spec.md` and `superpowers/plan.md`, with truthful creation dates and approval/execution provenance.
- **Verification:** commands or methods, actual results, scope, and supporting evidence.
- **Open issues:** impact, required follow-up, and the receiving task if identified.
- **Acceptance and next steps:** assessment against task criteria, final task status, and inputs handed over to the next step.

Place long tables, full terminal output, and detailed data in `evidence/`. Keep only what is necessary to assess the outcome in the main report. Use "None" or "Not applicable" with a reason for irrelevant sections; do not invent content to fill the template.

## 3. Task README.md template

````markdown
# <TASK-ID> — <Task name>

- Status: <NOT_STARTED / IN_PROGRESS / BLOCKED / COMPLETE>
- Execution date: <actual date; timezone if needed>
- Requirement source: <link to the task in the milestone plan>
- Repository version: <branch / commit, if applicable>
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

<Summarize the main results, criteria met, and important limitations.>

## Work performed

- <Work completed and the corresponding outcome.>

## Outputs

| File | Purpose |
| --- | --- |
| [Filename](evidence/<filename>) | <What this file demonstrates or provides> |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| <Command or verification method> | <PASS / FAIL / BLOCKED / NOT_RUN> | <Scope and evidence link> |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| <Finding> | <Actual impact> | <Resolution or next action> |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| <Criterion> | <Met / Not met / Not verified> | <Link or check result> |

<State the final task status, related gate status, and inputs for the next step.>
````

## 4. Status and evidence

- Mark a task `COMPLETE` only when its own outputs and acceptance criteria have been satisfied.
- Record `FAIL`, `BLOCKED`, or `NOT_RUN` according to actual verification results. Do not present mock data, hard-coded values, or historical results as fresh measurements.
- Distinguish task status from milestone/gate status. A `COMPLETE` task does not automatically complete the milestone or make its gate `PASS`.
- Use relative links in reports, such as `evidence/checks.txt`; avoid machine-specific absolute paths inside repository reports.
- When renaming or moving files, update affected links and manifest SHA256 hashes where applicable.

## 5. Quick review index

[docs/reports/milestones/README.md](docs/reports/milestones/README.md) is the shared entry point. When adding or updating a report, update its corresponding table row:

| Task | Description | Status | Report |
| --- | --- | --- | --- |
| M0.1 | Legacy repository audit, secret sanitization, and Gold architecture baseline | COMPLETE | `M0.1/README.md` |

The index status must match the task report. Each task must have exactly one current row for quick discovery and review.

## 6. Pre-handoff checks

- `python3 scripts/check_secrets.py` exits with `0` (`Zero secret leaks detected`).
- All report prose, headings, table labels, review index entries, and authored supporting documentation are in English.
- The correct `<TASK-ID>/` directory contains exactly `README.md`, `evidence/`, and `superpowers/` at its top level.
- The `superpowers/` directory contains exactly `spec.md` and `plan.md`, and both are linked from the report.
- The conclusion and task status are clear at the start of the report.
- Supporting files (including `workflow.md`) are stored in `evidence/` and linked where cross-checking is needed.
- Verification results, unresolved issues, and acceptance scope are reported accurately.
- The quick review index (`docs/reports/milestones/README.md`) has been updated.

## 7. Superpowers workflow and artifact locations

Use the installed Superpowers process skills before substantive task work. Start by reading `using-superpowers`, then load the relevant process skill (`brainstorming`, `writing-plans`, `test-driven-development`, `verification-before-completion`) before domain skills.

For every substantive milestone task that creates or changes project deliverables, create or update `docs/reports/milestones/<TASK-ID>/superpowers/spec.md` and `docs/reports/milestones/<TASK-ID>/superpowers/plan.md` before execution, and record actual skill usage, decisions, commands, and verification in `docs/reports/milestones/<TASK-ID>/evidence/workflow.md`:

```text
docs/reports/milestones/<TASK-ID>/
├── README.md
├── evidence/
│   └── workflow.md        # Actual skill usage, decisions, and verification
└── superpowers/
    ├── spec.md
    └── plan.md
```

Do not create a parallel `docs/superpowers/` tree or nest `superpowers/` inside `evidence/`. Use `verification-before-completion` before making any completion claim.
