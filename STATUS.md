# STATUS — measured 2026-08-02 (Phase 0 + Phase 1.1–1.3 landed)

Point-in-time facts. Verify before you rely on them. The commands are in
`CLAUDE.md`. The work queue is `PLAN.md`.

All systemd units are deliberately **stopped**. Run `factory on` to start.

## What works

| Capability | Evidence |
|---|---|
| Loop 1 — builds an app | 91 sacrifice stories deployed |
| Loop 2 — builds itself | 24 factory stories deployed in the last 14 days |
| PR pipeline | 122 stories opened a PR; 118 merged |
| Staging twin | 17 self-edits validated, **3 fatal self-edits rejected** |
| Review convergence | 0 stories hit the cycle cap in 14 days (max 5, one story) |
| CI-failure recovery | Real CI log is fed back to dev as a structured finding. Capped at 3 |
| GitHub loop | 1 open issue, 0 open PRs, 0 blocked stories |
| Spend control | $200/day cap, hourly cap, per-story budget |
| Test suite | 2,368 tests, ~5 min |
| SWE-bench harness | Three-arm, execution-validated suite (SWE-rebench, 19 instances, selftest 19/20), every row audit-valid, evidence archived. **Factory 11/19 = 58% vs bare 0/19 vs Claude Code 16/18 = 89%** (2026-08-03) |
| Scaffold lift | **+58 pp at matched weights** — factory (dev=azure/deepseek-v4-pro + reviewer=azure/gpt-5.4) vs the same deepseek bare with a docker test loop and 40 steps |

Do not "fix" anything in this table without a measurement that shows it broke.

## What does not work

| Problem | Evidence | Fix |
|---|---|---|
| FMS **L4 apply** tier is dead | 163 attempts, 0 PRs, nothing since 2026-07-23 | `PLAN.md` Phase 4 |
| Manager cost is unjustified | ~52% of all LLM spend | `PLAN.md` Phase 4 |
| `factory_improver` does not land | 196 proposals, 1 commit. 179 apply failures | `PLAN.md` 3.1 |
| L3 re-diagnoses known faults | 165 proposals span 37 distinct classes | `PLAN.md` 3.3 |
| The old (`bench.py`) benchmark is retracted | Tasks t1–t6 are shipped, so the pool is contaminated; the 20 reported rows still have no raw artifacts. SWE-bench Pro (below) replaces it for external grading | `PLAN.md` Phase 2 |
| Merge-gate precision is unknown | The SWE-bench harness runs dev+review only, so 1.3 measured **chain-verdict** precision (1/5), not the merge gate | `PLAN.md` Phase 2 |
| Bare-model arm not yet run | A factory number alone measures the model, not the harness | `PLAN.md` 1.4 — next |
| State has no backup | The twin guards source only | `PLAN.md` 3.4 |

## The benchmark, as of 2026-08-03 (Phase 1 complete)

Suite: SWE-rebench (Nebius), pinned manifest `923aef05` — 20 post-2026-01-01
python instances, 19 with a working oracle under the same mounted-clone
topology the arms run in (selftest is the control; SWE-bench Pro is frozen
after OpenAI's ~30%-broken audit; Pro archives remain readable).

| Arm | Models | Resolved | Notes |
|---|---|---|---|
| factory | dev `azure/deepseek-v4-pro`, reviewer `azure/gpt-5.4` | **11/19 = 58%** | precision 11/16, recall 11/11; ~$34/sweep |
| bare | `azure/deepseek-v4-pro`, minimal loop + docker test loop, 40 steps | **0/19** | honest baseline (post-#217); pre-fix bare rows not comparable |
| claude | Claude Code CLI, `claude-opus-5`, hermetic (no MCP/web), 60 turns | **16/18 = 89%** | 1 oracle-pass excluded (run failed); $34.85 Anthropic-side |

Read: the harness turns a 0%-bare model into 58% (+58 pp scaffold lift, the
product thesis's first direct evidence); the frontier-agent reference sits at
89%, so the remaining gap to frontier is 31 pp on this sample. n=19, single
seed — k-sampling and the 120-task Phase-2 manifest are what make these
defensible. Every number is re-derivable: `report --from-archive` over the
committed `results-archive/` snapshots.

## Fixed 2026-08-02 (Phase 1.1–1.3 + the three bugs that invalidated 2026-08-01)

The four 2026-08-01 benchmark batches (1/6…2/6) are **retracted**: the reviewer
never saw a diff in any review (fail-open error-text-as-diff), openlibrary
instances were unrunnable (uninitialised submodules), and cost was
under-reported 1.62× (onboarder spend invisible). Do not cite them.

| Was broken | Now | PR |
|---|---|---|
| `_fetch_pr_diff_for_review` was FAIL-OPEN — any `gh pr diff`/`git diff` failure returned the error text AS the diff; reviewer reviewed blind (production bug, not bench-only) | Missing diff raises before any model call, routes to `blocked_review_nonconvergent`, burns no cycle; base-ref fallback `origin/<base>` → `<base>`; anchored broken-prompt markers; `errors="replace"` on diff decode | #203 |
| Bench cost summed only story-attributed Run rows (1.62× under-report) | ALL ledger rows counted; unattributed spend reported separately; wall clock from function entry; stale artifacts reset at run start | #202 |
| `_clone` left submodules uninitialised → `ModuleNotFoundError` in 0.8 s | Submodules vendored into the base branch as tracked files (survives `git worktree add`) | #202 |
| Nothing verified the test command WORKS before spending | Pre-dispatch `--collect-only` gate in the real docker env; two modes — strict `existing-targets` / `ancestor-env-check` for legit new-test-file TDD instances | #202, #205 |
| No post-hoc integrity check existed (all three bugs shipped past green tests) | `audit` subcommand: full persona-call ledger, cost cross-check, error-text-in-reviewer-prompt scan, missing artifact = FAIL; wired per-instance into the parallel sweep; `report` counts only audited-valid rows | #202, #204 |
| Benchmark ran one instance at a time | `run-all` parallel sweep (child processes, spend guard on actual mid-sweep cost, pure dry-run, group kill) | #204 |
| Dev invented literals where the story was silent | Persona seeks codebase precedent (measured 2/2 vs 0/2 on the isolating instance) | #201 |

Reported (n=6, `bench/swebench/results.md`, generated 14:01:07Z): **1/6
resolved**, 4 `right_place_wrong_fix`, 1 honestly-blocked empty patch,
chain-verdict precision 1/5, recall 1/1, $3.33.

> **⚠ RETRACTED PENDING RE-DERIVATION — do not cite these numbers.**
> The artifacts on disk are from a **later** sweep (16:23–16:35Z) that reports
> 5 `right_place_wrong_fix` and `cost_usd: 6.7342`, and they disagree per
> instance: `openlibrary-3aeec6af` is published as `empty_patch` at 142,903
> input tokens but on disk shows 2,985,777 in / 50,735 out. **No `grade.json`
> survives anywhere under `bench/swebench/runs/`**, so the oracle PASS/FAIL
> column has no backing artifact. `_reset_run_artifacts` clears state at run
> start (correct) but nothing snapshots a published run first. This is the same
> class as the retraction on line 33, recurring one day later. `PLAN.md` 1.5
> fixes it and must run before 1.4 — a bare-model delta against an unbacked
> factory number measures nothing.

> **RESOLVED later the same day.** PLAN 1.5 shipped in #210: `report` now
> snapshots every row's `result.json`/`audit.json`/`prediction.diff` into
> `bench/swebench/results-archive/` before publishing and refuses unbacked
> rows. (One correction to the note above: no separate `grade.json` exists by
> design — `grade` merges its verdict into `result.json`.) Evidence archives
> are committed in #211. The 14:01Z table ($3.33, precision 1/5) stays
> retracted — its artifacts were destroyed before archival existed. The
> **currently backed** numbers (archives `17-30-31Z` and `17-45-30Z`):
> factory 1/6 = bare 1/6 resolved (same qutebrowser instance; scaffold lift
> 0 pp at ~30× tokens), and the post-#210 sweep holds 1/6 with the review
> loop now engaging (`reviewer_cycles` on 2/6 vs 0/6 before). Per-instance
> autopsies live in the memory file `swebench_failure_synthesis_2026_08_02`.

## Fixed 2026-08-01 (Phase 0)

Measurement was impossible before these; everything in Phase 1 depends on them.

| Was broken | Now | PR |
|---|---|---|
| Dev/test_implementer/onboarder had NO prompt telemetry — 45,868 rows, zero for the three personas that write all the code | `sandbox_run` logs metadata; new `prompt_bodies.ndjson` keeps full text + full sha256, hash-chained | #193 |
| Retries were invisible: 0 `retried` rows in `chain_steps` vs 71 real dev retries and 119 review cycles | `retried` / `review_cycle` rows emitted, reconciling with the DB counters | #194 |
| Failing gates' `reason` and `output_tail` were discarded — a blocked merge could not say why | `gates_failed` on `MergeAction`, a `gates_failed_json` column, and a `merge_gates_failed` story event | #195 |
| `StoryRecord.smoke_passed` was read by the smoke gate and written nowhere — fail-closed by accident | Dead reader deleted; the gate is fail-closed structurally | #195 |
| Reviewer shared a model with `dev.hard` (both `azure/gpt-5.3-codex`) | `reviewer` → `azure/gpt-5.4` in both blocks; enforced at router load | #196 |
| Loop caps were 6, contradicting the "nothing loops >3" guardrail | `_MAX_DEV_RETRIES` and `_MAX_REVIEW_CYCLES` → 3; inner guards → 2 to keep early escalation reachable | #196 |

**Behavioural change to watch.** At `_MAX_DEV_RETRIES = 3` the dev
inner-convergence loop gets at most **two** sandbox attempts per invocation, so
`red → red → green` no longer converges in one tick. Four stories in the 14 days
to 2026-08-01 reached 6 retries and would now block at 3. Whether attempts 4–6
produced *passing* work is unmeasured — that is exactly what Phase 1.3's gate
precision number settles. Re-read this row after the first real soak.

Reviewer independence now holds on **both** dev tiers and is enforced in code:
`model_router.check_review_independence` refuses to resolve any route out of a
colliding `routes.yaml`. `test_implementer` still shares `deepseek-v4-pro` with
`dev.standard` — that weakens the acceptance oracle but not the merge decision,
so it warns rather than blocks.

## Cost

July, from the `runs` ledger:

- All-in: $588.78 across 75 deployed stories = **$7.85 per story**
- Excluding the manager: $217.18 = **$2.90 per story**

Input and output rates are verified Azure retail. The **cache-read rate is
estimated** — no Azure meter publishes one for this deployment, and the account
lacks the Cost Management RBAC role. `factory audit` reports ~55% of window
spend as estimated. Treat dollar figures as approximate. Prefer token counts:
they are provider-reported and exact.

## Two self-modification paths — do not confuse them

The chain self-edit path and the FMS L4 apply tier are different subsystems.

- **Chain self-edit** (loop 2): direction → story → dev → review → gates → PR →
  staging twin → merge. **Works.**
- **FMS L4 apply**: the manager diagnoses an operational fault and writes its
  own fix. **0 PRs from 163 attempts.**

Measuring only the second produces the false conclusion that the factory cannot
improve itself. Cross-check any yield claim against GitHub before asserting it.

## Benchmark harness

Pinned as of `PLAN.md` 0.3/0.4: `base_sha` is a literal SHA and an empty one is
refused, the Claude arm pins `--model`, `clean()` no longer deletes
`bench/runs/`, and every `result.json` records tokens plus its
base/routes/price-table provenance. Tokens are the reported metric; dollars are
derived from a hashed price table and can be re-derived after a price
correction. This fixes the HARNESS. The July results stay retracted: their raw
artifacts are still gone and their task pool is still contaminated.

## Known gaps in the twin

`software-factory-copy` is **public**. Make it private.

It guards source only. Nothing snapshots `state/factory.db`, and runtime state
corruption is what has actually taken the factory down.

## CI cost

`lint`, `typecheck` and `pytest` are required checks, so they always run and
always report. A PR that changes only root-level `*.md` skips their expensive
steps and finishes in about 20 seconds instead of about 4 minutes. Any other
path — including `factory/personas/*.md` and `apps/**/context/*.md`, which are
code — runs the full suite. See the `changes` job in
`.github/workflows/test.yml`.
