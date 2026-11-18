## Result

The Windows full-suite collection/type blocker is fixed: both M6.1 pipelines now use a shared OS-backed process peak-memory helper instead of importing Unix-only resource at module import. Windows PeakWorkingSetSize bytes and Unix peak RSS are normalized to MiB, with explicit unit/process-lifetime metadata and no fake-zero fallback.

The PR also includes the G0 settings/client two-call ceiling, invalid/copied-budget regressions, and clean lint. Original corpus/index/benchmark bytes and earlier failed verification receipts are preserved. Equivalent UTC aliases make the declared full pipeline lint scope clean.

## Verified final source

- 120 full tests and 11 contract/smoke tests pass.
- Configured mypy passes 81 source files for Windows and Linux static targets.
- Ruff passes packages/apps/pipelines and changed tests; secret/dependency checks pass.
- 38 asserting G0 runtime checks and clean wheel/installed-ASGI validation pass.
- Eight resource regressions include a native Windows OS measurement; fresh read-only review reports no Critical/Important/Minor issues.
- No live provider/crawler calls, spend, original data changes or benchmark rewrites.

The owner explicitly authorized readying and merging this verified PR into main. Formal G0 remains NOT_RUN for the owner decision; M6.1 remains IN_PROGRESS for independent human qrels and scientific acceptance. Native Linux/macOS execution, actual Docker container/browser interaction and public hosting are not inferred from these checks.

Current reports: docs/reports/milestones/M0.G/README.md and M6.1/README.md. Post-merge source identity and full tests will be recorded separately.
