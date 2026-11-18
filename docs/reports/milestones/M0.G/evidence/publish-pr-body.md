## Summary

Enforce the project-wide two-call LLM ceiling at settings and client boundaries, including copied nonfinite settings and invalid consumed counts. Resolve the two G0 lint violations and add 25 budget regression cases. Keep formal G0 NOT_RUN for the owner decision.

This branch is based on current main ad7eb92f and preserves its M3.1/M6.1 changes. The repository currently uses main plus topic PRs; develop is absent, so this publication is GitHub flow rather than classic Gitflow.

## Validation and draft blocker

- PASS: 38 focused budget/provider tests; 11 contract/smoke tests; 38 asserting G0 runtime checks; required Ruff; dependency check; source/staged secret checks.
- FAIL on updated main (Windows): full pytest exits 2 during collection because M6.1 imports Unix-only resource; configured mypy reports four getrusage/RUSAGE_SELF errors in the unchanged M6.1 pipeline files.
- Earlier G0-only repair validation passed 100 tests and configured mypy across 76 files; these are dated results, not the updated-tree full-suite outcome.
- No live provider/crawler calls, spend, data changes, deployment, or gate approval.

Keep this PR draft until the upstream M6.1 Windows issue is addressed and full checks pass. Evidence and the current report: docs/reports/milestones/M0.G/README.md.
