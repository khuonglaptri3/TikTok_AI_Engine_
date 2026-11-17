# Balanced plan rewrite: decisions and provenance

- Authored: 2026-11-17 (Asia/Saigon), during the authorized recovery task.
- Scope: active milestone plan, resources/deployment guide, refactor execution companion, limited opening team/scope lines in project `AGENTS.md`, and this task's planning evidence.
- Status: documentation revision authored and scoped integrity checks passed. Product fixes, source recovery, independent final review and overall acceptance remain handled by the parent execution task.
- Authority: [task specification](../superpowers/spec.md) and [execution plan](../superpowers/plan.md), especially required outcomes 6–7 and implementation step 6. The owner approved the recovery-first approach and explicitly requested an equal split. This is execution of the agreed documentation scope, not a request for a new approval.

## Inputs and actual workflow

The documentation worker read the repository `AGENTS.md`, both canonical task planning files, both previous active planning guides, the original refactor implementation plan, the completed [audit report](../../docs-refactor-feasibility-2026-11-17/README.md) and its [detailed documentation review](../../docs-refactor-feasibility-2026-11-17/evidence/docs-review.md). The parent supplied the profile's identity-only finding and explicit instruction not to infer ability or availability. No additional profile research, invitation, contact, live crawl, provider call, deployment, commit or push occurred in this subtask.

Actual Superpowers sources read were all from installed version `7.0.1` under `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`:

| Skill file read | Application in this documentation subtask |
| --- | --- |
| `using-superpowers/SKILL.md` | Read before project investigation; its specific subagent instruction delegates the dispatched task's workflow. The owner-required initial skill check and announcement were still performed. |
| `writing-plans/SKILL.md` | Applied task sizing, explicit dependencies/outputs, checkable acceptance and self-review to the revised milestone plan. Mandatory project task paths override default `docs/superpowers/` paths; the parent already created and authorized the canonical spec/plan before this execution. |
| `executing-plans/SKILL.md` | Read for the parent's selected method and continuous-execution/evidence principles. This worker executed only its delegated documentation brief; it does not claim to have run the full standalone implementation/worktree/TDD/branch workflow. |
| `verification-before-completion/SKILL.md` | Applied fresh arithmetic/source-preservation/link/layout checks before documentation handoff. No product completion or quality is inferred from those checks. |
| `systematic-debugging/SKILL.md` | Read and applied after the first authored-link check failed: inspected the exact failed targets, reproduced the three AGENTS template links, and confirmed they are inside a fenced example. A minimal fence-exclusion change fixes the checker's source parsing without changing preserved AGENTS policy. |

The parent is responsible for the overall workflow ledger, production-fix TDD, worktree integration, independent final review and complete verification. This note supplies the documentation worker's actual provenance for that ledger. No new brainstorming approval gate was invented: the owner's agreed recovery design and explicit equal-allocation correction are already recorded in the canonical specification. No mirrored implementation tests were added for this reversible documentation work.

## Exact preservation before rewriting

Four exact source copies were made before edits. [prior-plan-preservation.json](prior-plan-preservation.json) records original relative paths, copied byte lengths and SHA256. The archive is raw historical evidence: its old language, relative links, completion assertions and measurements were not revised or newly verified.

| Preserved source | Exact historical copy |
| --- | --- |
| Active milestone plan | [prior-milestone-plan.md](prior-milestone-plan.md) |
| Resources/deployment guide | [prior-resources-and-deployment.md](prior-resources-and-deployment.md) |
| Refactor implementation plan | [prior-refactor-implementation-plan.md](prior-refactor-implementation-plan.md) |
| Project scope/rules | [prior-project-agents.md](prior-project-agents.md) |

The initial preservation command confirmed four copies with matching bytes before writing the new documents. The ordinary `python` command resolved to an unavailable Windows application alias; subsequent stdlib commands used the existing uv-managed interpreter. No new Python installation or project dependency was introduced by this worker.

## Decisions and their implications

| Decision | Reason and review implication |
| --- | --- |
| Keep M0–M6 and every existing task ID; define all seven gate tasks | Preserve traceability while repairing missing detailed gate definitions. Reports remain `docs/reports/milestones/<ID>/README.md`; future paths are code text until tasks actually begin, avoiding empty future bundles/broken links. |
| Allocate every task to a primary owner and the other person as peer reviewer | Equal work includes delivery, annotation, verification, integration, report preparation and gates. Both people lead substantial implementation/evaluation across stages; no AI/backend skill segregation is inferred. |
| Use estimated half-day points | Allows auditable arithmetic while distinguishing estimates from equal actual hours or known human capacity. The machine-checkable allocation is [two-person-allocation.json](two-person-allocation.json). |
| Keep recovery/core IN_PROGRESS, all gate decisions NOT_RUN and future pilot/model/hosting unaccepted | Existing source code and past reports do not establish fresh acceptance. Parent recovery results may be linked later without implying independent annotations or future gate execution happened. |
| Make the historical core first, with relative W1–W12+ windows | The eight-week promise lacked bounded acquisition/annotation/CPU evidence. Actual availability is unknown; windows are indicative and a smaller accepted local core remains useful if fresh acquisition fails. |
| Cap real capture and require early transcripts before searchability | Maximum cohort/audio/comment/time caps prevent an unbounded four-month crawl. A minimum of five real transcribed searchable fresh videos closes the vertical slice; synthetic fixtures cannot substitute. Further work is gated by observed throughput/yield. |
| Replace hidden sponsorship intent with observed flags and qualified promotional wording | `is_ad`/commerce flags do not label undisclosed sponsorship. Hidden-intent training is deferred without independently verified labels, unknowns stay unknown and no unsupported historical audio join is assumed. |
| Name observable duplicate/contact/noise labels and sentiment discrepancies | Duplicates cannot prove bots/seeding, commenters cannot be presumed verified diners, and sentiment gaps cannot prove deception or hygiene truth. Preserve originals, source spans and missing aspects; evaluate filter sensitivity. |
| Correct standard recall and require independently authored, blinded judged queries | Keyword-derived qrels remain weak-label regression. A top-10 pooled pilot must disclose incomplete judgments and report pooled recall as such rather than exhaustive corpus coverage. Hybrid/reranker superiority is not predetermined. |
| Treat thresholds as prospective pilot decisions | Sample sizes, quality/resource limits and abstention rules are implementer planning choices for review, not claimed owner-provided research constants, measured results or population guarantees. Failure is preserved and scope may shrink. |
| Measure audio errors and preserve estimated provenance | ASR boundaries are estimates and historical interpolation is weaker still. Enforce duration bounds and evaluate boundary/CER/WER/resource error before precise playback claims. |
| Keep CPU/offline baseline and separately gate current provider/hosting eligibility | Former model/RPM/free-host assumptions are time-sensitive. No host is selected or deployed; current official terms, no-billing path, artifact rights/privacy, measured RAM/disk/cold-start fit and sleep/quota limits remain required. |
| Edit only AGENTS opening team/scope content | The rest of project preservation, zero-spend and reporting policy remains intact. The contradictory single-contributor/no-backend-assumption lines were replaced with two equal contributors sharing typed API/demo integration. |

An early draft summary incorrectly expected 198 points; the first executable arithmetic assertion found **188 points**, already balanced at 94 each. The task rows were retained and every aggregate corrected to 188 total / 94 each / 47 estimated days each before verification. The core is 40 points each; conditional work is 54 points each. This is a caught draft error, not a change to the owner's equal-allocation requirement or a measured labor result.

## Validation scope and commands

Run from the repository root with an available Python 3 interpreter:

```powershell
& 'C:/Users/lanph/AppData/Roaming/uv/python/cpython-3.13-windows-x86_64-none/python.exe' docs/reports/tasks/core-recovery-and-two-person-plan-2026-11-17/evidence/verify-plan-rewrite.py
& 'C:/Users/lanph/AppData/Roaming/uv/python/cpython-3.13-windows-x86_64-none/python.exe' scripts/check_secrets.py
git diff --check
```

The [stdlib verification script](verify-plan-rewrite.py) checks all 24 IDs, reciprocal owner/reviewer assignments, every row against JSON, exact equal totals/days/share, balanced core/future phases, task definition/report-path coverage, all seven gates NOT_RUN, unchecked companion, four source archive hashes/bytes, limited AGENTS changes, authored local links and canonical task layout. [plan-rewrite-verification.json](plan-rewrite-verification.json) records fresh actual results and current document hashes. Archived raw source links and fenced template examples are preserved as historical/example text and excluded from authored-link checks. Planned future task paths are intentionally not clickable links.

| Fresh check | Actual result | Scope |
| --- | --- | --- |
| `verify-plan-rewrite.py` | PASS; 14 checks, zero failures; K 94 points, N 94 points | Arithmetic, all task IDs/assignments/definitions, JSON agreement, archives, authored links, limited AGENTS edit and existing canonical bundle layout. |
| `scripts/check_secrets.py` | PASS; exit 0, `Zero secret leaks detected across workspace` | Workspace scanner at the documentation handoff; parent reruns after code integration. |
| `git diff --check` | PASS; exit 0 | No whitespace-error findings; Git emitted informational LF-to-CRLF conversion warnings for rewritten files. |

The first link-check run found three template destinations inside AGENTS' unchanged fenced report example and the verification output that had not yet been written on the first run. The output now exists, and a reproduced, minimal fenced-example exclusion fixed the parser. The next full verification passed all 14 checks. No document policy/template was weakened to make that check pass.

Product tests, real-data restoration, current performance/accuracy, human annotation, actual capacity, live provider eligibility, public hosting and future gate reviews remain outside this worker's completion claim. The root README, milestone index, other refactor documents, data and code are owned by the parent/other workers and were not edited here.
