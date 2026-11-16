# Milestone task reports

Each started task has exactly two directories, `evidence/` and `superpowers/`, and one current results report, `README.md`. Open the report to review conclusions, the spec/plan links, actual verification, and outstanding work. `superpowers/` contains exactly `spec.md` and `plan.md`; all supporting data and workflow logs stay in `evidence/`. All authored documentation is in English; preserve original Vietnamese source queries and raw logs when required for evidence integrity.

| Task | Description | Status | Report |
| --- | --- | --- | --- |
| M0.1 | Legacy repository audit, secret sanitization, 1.50 GB data preservation, and Gold RAG monorepo baseline | COMPLETE | [Read results](M0.1/README.md) |

Apply the exact layout defined in [AGENTS.md](../../../AGENTS.md) to all subsequent tasks (`M1.1`, `M2.2`, `M3.1`, etc.):

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
