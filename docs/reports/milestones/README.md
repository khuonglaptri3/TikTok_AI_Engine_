# Milestone task reports

Each started task has exactly two directories, `evidence/` and `superpowers/`, and one current results report, `README.md`. Open the report to review conclusions, the spec/plan links, actual verification, and outstanding work. `superpowers/` contains exactly `spec.md` and `plan.md`; all supporting data and workflow logs stay in `evidence/`. All authored documentation is in English; preserve original Vietnamese source queries and raw logs when required for evidence integrity.

| Task | Description | Status | Report |
| --- | --- | --- | --- |
| M0.1 | Historical asset preservation, pinned recovery (`37,840` files), Gold `20261117_recovered_v1` & `bm25-v2` provenance baseline | COMPLETE | [Read results](M0.1/README.md) |
| M0.2 | Contracts, bounded settings, finite ms timings, and error/log credential redaction | COMPLETE | [Read results](M0.2/README.md) |
| M0.3 | Installable API/demo foundation and real-corpus `offline_grounded` `/demo/` verification | COMPLETE | [Read results](M0.3/README.md) |
| M0.G | G0 foundation gate decision across `M0.1`–`M0.3`, packaging limits, and baseline verification | IN_PROGRESS | [Read results](M0.G/README.md) |
| M1.1 | Taxonomy, per-field lineage/coverage audit, disambiguation fixes, and 120-record sample (`K_*` 30-row human overlap + `N` review) | COMPLETE | [Read results](M1.1/README.md) |
| M1.2 | Immutable taxonomy-corrected historical Gold snapshot (`20261118_taxonomy_fix_v1`) with verified parent lineage | COMPLETE | [Read results](M1.2/README.md) |
| M2.1 | Descriptive niche benchmarks, cohort/missingness provenance, sparse abstention, and 100-request latency verification | COMPLETE | [Read results](M2.1/README.md) |
| M2.3 | Qualified scripts, structural guardrails, bounded provider timeout/calls, and 15-brief offline audit | IN_PROGRESS | [Read results](M2.3/README.md) |
| M3.1 | Repeated Dual-Sink ingestion repair, missing-modality schemas, and interrupted publication tests | IN_PROGRESS | [Read results](M3.1/README.md) |

Independent cross-project assessments are listed in [task reports](../tasks/README.md). Their conclusions do not change milestone status or pass a gate.

Apply the exact layout defined in [AGENTS.md](../../../AGENTS.md) to all subsequent tasks (`M0.G`, `M1.G`, `M2.2`, `M3.1`, etc.):

```text
milestones/
├── README.md
└── <TASK-ID>/
    ├── README.md       # Results, verification, open issues, and next steps
    ├── evidence/       # JSON, CSV, logs, workflow.md, and supporting documentation
    └── superpowers/
        ├── spec.md     # Task specification and acceptance
        └── plan.md     # Execution steps and verification plan
```
