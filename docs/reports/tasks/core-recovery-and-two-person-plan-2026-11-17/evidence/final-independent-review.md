# Independent recovery review — 2026-11-17

- Reviewer: `/root/final_recovery_review`, fresh context using `gpt-6-astra`, high reasoning; explicitly required by Superpowers inline execution/review skills.
- Scope: current main-checkout diff against `cdbc6ed9ccad11db437aa66c68638cf018701fe5`, untracked snapshot helper/regressions, canonical spec/plan, workflow, allocation and existing evidence. Review was read-only; no source/data/index/branch mutation or further delegation occurred.
- Initial verdict: **changes required before local handoff**. No Critical findings; three Important findings; no Minor findings.
- Review-time evidence: one cached Python 3.12, temporary synthetic-data probe exited 0 and reproduced all three issues. Allocation was independently parsed: 24 rows, K=94 / N=94, distinct owner/reviewer on all rows. Existing focused/mypy/package outputs were inspected, not independently rerun.

## Findings and executor disposition

| Finding | Reviewer observation | Required behavior / disposition |
| --- | --- | --- |
| Offline draft manufactures citation associations | `service.py` assigned available IDs to every beat, including an empty-text evidence card; the probe returned `passed=True` and coverage 1.0. Beat 2/3 included unused second/third IDs. | Cite only a source whose excerpt is incorporated and retained through shortening. Empty source text remains uncited and cannot pass structural validation. |
| Repeated video records discard enrichment | `converter.py` skipped later same-video JSONL records; c1 followed by c2 published only c1, including with explicit updates enabled. | Coalesce records before either sink: later supplied fields win, omitted fields stay, distinct comment IDs survive. |
| Initial comment identities are not deduplicated | Initial `[c1, c1]` published duplicate comment keys and could distort diagnostics. | Normalize comment IDs for new and existing videos using identical sparse-field merge rules before seeding/ABSA. |

All seven added cases first failed for these reasons; see [final-review-red.log](final-review-red.log). The executor owns the one TDD fix pass and subsequent focused/full verification. The original review verdict is preserved here rather than rewritten as an independently repeated approval.

Executor's final disposition: all three findings are fixed. The focused post-fix run passed 42 tests ([final-review-green.log](final-review-green.log)), and the complete project suite passed 57 tests after rebuilding actual artifacts ([final-full-suite.log](final-full-suite.log)). No second independent review was performed or required by the inline execution skill's single fix-pass contract. The final task report separately records the exhaustive data verification, actual API results and bundle/hash checks.

The reviewer also confirmed staged collision-safe publication, ordinary-failure lock release, the three earlier snapshot fixes, parent-manifest lineage, corrected metrics, aligned defaults/package sources, qualified weak labels and balanced ownership. Those observations do not substitute for the executor's final data-backed checks.

## Behaviors the reviewer declined to judge

| Behavior / reason | Executor disposition |
| --- | --- |
| Full historical restoration and checksum equality were still running | Finish the exhaustive restoration/preservation receipt before completion. |
| Final Gold schema/keys, index contents and benchmark values did not yet exist | Build and validate them against actual recovered inputs before completion. |
| Recovered API/Gradio outputs and timings remained pending | Run local ASGI integration and retain actual outputs/timings. |
| Full suite, final scanner and link/hash integrity remained pending | Require these final checks before handoff. |
| Entailment accuracy and independent relevance quality require human evaluation | Retain the approved M2.2/M2.3 follow-up; structural/weak-label results cannot satisfy it. |
| Live collection, audio, dense and calibrated trust diagnostics are future gated work | Preserve those acceptance boundaries; no synthetic result completes a live-data gate. |
| Provider/hosting eligibility, data rights and public deployment are outside offline review | Keep them unresolved and conditional, with zero provider/deployment actions. |
| Actual availability and equal hours are unknown | Claim only independently checked equal estimates, with actual capacity still unknown. |
| Filesystem enforcement against arbitrary writers, hostile concurrent mutation and power-loss durability are outside the application publisher guarantee | Describe application-level staging/collision checks only; no physical immutability/durability claim. |
| Arbitrary external table schema semantics exceed this checksum/coverage repair | Validate the generated corpus schema/keys explicitly; do not claim arbitrary manifest semantics are validated by hashes. |
| Historical M0.1 assertions were retained historical evidence | Do not revise or freshly endorse that earlier acceptance; current gates remain NOT_RUN. |
| Final report/status reconciliation was assigned to the executor | Finalize the report/index after evidence exists. |

The reviewer did not run providers, network collection, the full suite or deployment, and did not write this report. This English record transcribes the delivered findings and review boundaries; executor verification and rulings are recorded separately in [workflow.md](workflow.md).
