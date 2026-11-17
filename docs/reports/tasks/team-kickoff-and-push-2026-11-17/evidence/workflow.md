# Team kickoff and publication workflow

## Authorization and skills

The owner's direct request on 2026-11-17 authorizes committing/pushing the completed work and writing the kickoff description. This is a new publication task; the completed recovery's earlier no-push boundary describes that earlier execution and is not reused to block this explicit request. No external message/invitation, provider or hosting action is inferred.

Read actual Superpowers 7.0.1 files under `C:/Users/lanph/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/`: `using-superpowers/SKILL.md`, `finishing-a-development-branch/SKILL.md`, `verification-before-completion/SKILL.md`, `writing-plans/SKILL.md` and `systematic-debugging/SKILL.md`. Applied branch/remote inspection and evidence-first publication; the owner already chose push, so no redundant option menu is used. No new feature/design or independent review of unchanged product code is claimed. The existing recovery has its actual independent review/fix-pass records.

The canonical specification and plan were created before writing publication deliverables or changing Git attributes. This task's README is the one current kickoff narrative; commit text and machine receipts stay in evidence.

## Investigation

- `git fetch origin` succeeded. Local `main` and `origin/main` are at `cdbc6ed9ccad11db437aa66c68638cf018701fe5` (ahead/behind 0/0).
- The configured origin is the existing private `khuonglaptri3/TikTok_AI_Engine_` GitHub repository. Git identity and GitHub CLI are already configured; no credentials were printed or changed.
- `core.autocrlf=true` with no attributes changes the stored bytes of CRLF source files. Real `git hash-object --path=... --stdin` probes differed from raw Git blob hashes for `packages/analytics/engine.py`, `packages/retrieval/sparse/bm25.py` and `pipelines/benchmark_retrieval/__main__.py`; the binary UTF-16 test log did not change. This pinpoints the clean-filter boundary, not a product logic defect.
- Scope includes the previously uncommitted audit and recovery bundles, source fixes and small new Gold/benchmark manifests. The largest pending evidence file is the 28,659,635-byte per-input inventory, below GitHub's per-file limit; the 1.50 GB dataset and runtime binary indexes remain local/ignored.
- Ruling: preserve exact receipt-bound source/evidence bytes with scoped `-text` attributes. Historical recorded checksums retain their meaning; normal Python semantics do not change. Cost if wrong: future maintainers must distinguish intentional byte preservation from general repository line-ending preferences.

## Execution and final checks

Actual verification, staged-file inventory and publication receipts are recorded below as they occur. No success is inferred from a prepared description.

- The full byte-filter reproduction checked 129 Git-bound paths and failed for 53; [byte-filter-before.json](byte-filter-before.json) preserves every mismatch. After 48 scoped attribute rules, the same probe passed all 129 paths ([byte-filter-after.json](byte-filter-after.json)); no measured source/evidence bytes changed. The rule set includes unchanged BM25/fusion/reranker source and the old manifest/query/benchmark bytes referenced by historical receipts.
- The kickoff uses the approved M0.2/M0.1/M0.3 owner/reviewer rows, keeps 94/94 totals and explains both source-only startup and local asset requirements. It warns that immutable snapshot collisions and some default-path unit checks make a blind fresh-clone `build-corpus` command insufficient. No new bootstrap feature or task directory for a future milestone was created.
- Fresh full project pytest passed 57 tests in 65.74 seconds ([pytest-pre-push.log](pytest-pre-push.log)); configured mypy passed all 75 source files ([mypy-pre-push.log](mypy-pre-push.log)). These are this publication's actual observations, distinct from the earlier recovery result. Documentation/layout checks passed; scanner and staged-byte checks follow before committing.
- Pre-commit scanner passed with zero leaks. Explicit pathspec staging refreshed only tracked receipt-bound files and the declared pending source/reports; raw/interim/processed/transcript inputs, `.env`, Parquet and runtime indexes were excluded. The staged verifier passed all 164 then-staged blobs, including real byte comparison; subsequent evidence is restaged and rechecked before commit. No application source bytes changed during publication.
- Default `git diff --cached --check` treated intentionally preserved CRLF as trailing whitespace ([staged-diff-check.log](staged-diff-check.log)); raw archived logs also retain original formatting. The source-only check passed using `core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` and excluding `docs/reports/**/evidence/**` ([source-diff-check.log](source-diff-check.log)). No global Git preference or historical evidence was rewritten to suppress a finding. Line-ending-only protected source/old receipt changes have an empty `--ignore-space-at-eol` content diff.
