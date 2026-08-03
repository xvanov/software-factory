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
| SWE-bench measurement pipeline | Oracle is sha256-pinned upstream `FAIL_TO_PASS`/`PASS_TO_PASS`; test-edit stripping is asserted in code at all three arms and fired on 36/57 rows; grading is a fresh `--rm` container with `--network none`; manifest frozen and committed *before* the first run; gold-patch control 19/20 and red-baseline verified 18/19. Adversarially audited 2026-08-03 — see "Audited and retracted" below |
| Claude-arm provenance | Really executed locally: `claude` CLI 2.1.220, `--model claude-opus-5` pinned, `--depth 1` clone (1 commit, no future refs), WebFetch/WebSearch removed and proved absent from the CLI's own init event, **0 of 321 recorded shell commands attempted any network retrieval** |

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
| The bare arm measures its own bugs, not the model | Bare is *forbidden* to write tests while factory/claude are *instructed* to; its DONE gate targets tests that pass at base commit; no empty-diff guard; roleless prompt echoes fabricated tool output back as real. External anchor for the same deployment is 40.2% — P(0/19 \| p=.402) = 5.7e-5 | `PLAN.md` 1.6 |
| No arm isolates "no chain" from "no tools" | The bare loop lacks both, so an unknown share of the measured lift is OpenHands' tooling rather than the chain | `PLAN.md` 1.6 — OpenHands single-agent arm |
| No arm's absolute rate is contamination-clean | Measured 2026-08-03: `gpt-5.4`/`gpt-5.3-codex` cutoff 2025-08-31 (published), `deepseek-v4-pro` **unpublished** (release-date bound 2026-04-24), `claude-opus-5` May 2026. Margins on the pinned 19: 0/19 negative vs the OpenAI models, **15/19** vs deepseek, **19/19** vs opus-5. The freshest public SWE-rebench instance anywhere is 2026-05-12, so no positive-margin manifest for opus-5 exists today | `PLAN.md` 1.6 F + 2.1 |
| `SWE-bench-Live` is abandoned | Last modified 2025-09-18, newest instance 2025-09-02, 0 rows after 2025-10-01. PLAN 2.1's 30-instance control was not executable | `PLAN.md` 2.1 — replaced by a two-stratum design |
| The agent's shell can reach the oracle store | `oracle.json.z` sits six `..` above the dev's cwd; arms can read each other's run dirs. **This fired: 4 factory runs were audit-invalidated for oracle-probing and silently re-rolled** | `PLAN.md` 1.6 |
| State has no backup | The twin guards source only | `PLAN.md` 3.4 |

## The benchmark, as of 2026-08-03 (Phase 1 complete)

Suite: SWE-rebench (Nebius), pinned manifest `923aef05` — 20 post-2026-01-01
python instances, 19 with a working oracle under the same mounted-clone
topology the arms run in (selftest is the control; SWE-bench Pro is frozen
after OpenAI's ~30%-broken audit; Pro archives remain readable).

| Arm | Models | Resolved | 95% CP CI | Status |
|---|---|---|---|---|
| factory | dev `azure/deepseek-v4-pro` **+ 7 escalations to `azure/gpt-5.3-codex`**, reviewer `azure/gpt-5.4` | 11/19 = 58% | [33.5, 79.7] | **provisional** — 4 of 19 rows are second attempts (below) |
| bare | `azure/deepseek-v4-pro`, minimal loop, 40 steps | 0/19 | [0.0, 17.6] | **VOID** — arm defective, see below |
| openhands | `azure/deepseek-v4-pro`, single agent, no chain | not yet run | — | the arm that actually isolates the chain |
| claude | Claude Code CLI, `claude-opus-5`, hermetic (no MCP/web), 60 turns | 17/19 = 89% | [66.9, 98.7] | provenance verified; **model+scaffold swap, not a scaffold measurement** |

### Audited and retracted 2026-08-03

Four independent adversarial audits attacked this result. The **measurement
pipeline held**; the **headline did not**. Retracted, do not cite:

- **"+58 pp scaffold lift at matched weights."** Two independent defects. (a) The
  bare arm is broken in eight ways — most decisively, its system prompt forbids
  writing tests while the factory's and Claude's *instruct* it, so the arm
  anchoring the lift is prompt-blocked from building the run-until-green loop the
  factory's whole thesis rests on; and its DONE gate targets FAIL_TO_PASS *files
  at base commit*, where in 16 of 19 instances zero such tests exist (one row
  printed "28 passed" against an empty diff and stopped at step 6; another
  reverted its own correct fix because the pre-existing tests asserted the old
  behaviour). 6 of 19 rows shipped a 0-byte diff with no empty-diff guard, and no
  run came near its 40-step cap (mean 9.2). (b) Weights were not matched: the
  factory escalated 7 dev calls to `azure/gpt-5.3-codex` and **4 of its 11
  resolves used that tier**, which bare can never reach — matched-weights factory
  ceiling is 7/19 = 37%.
- **"The remaining gap to frontier is 31 pp."** McNemar exact on the 18 paired
  instances: **p = 0.0625** — not significant. And the arm swaps model *and*
  scaffold, so the gap is not attributable to the harness at all; `results.md`'s
  own rule ("a number without the matched-weights number measures the MODEL")
  was applied to bare and not to Claude. Also every instance (`created_at`
  2026-01-03 → 05-07) predates `claude-opus-5`'s knowledge cutoff, so that arm
  additionally carries a contamination confound the other two may not.
- **"Every row audit-valid."** True of the published rows and materially
  incomplete: the superseded `results-archive/2026-08-03T02-21-23Z` snapshot
  records the first factory sweep at `audit failed: 4`, all four the harness's
  most serious verdict (*"the arm went looking for the answer; the run is
  invalid"* — oracle-probe). Those four were re-run 30 min later under
  byte-identical code, passed, and the second attempt is what is published; 2 of
  them are among the 11 passes. Outcomes were identical in all 4 pairs, so 11/19
  holds — but selecting on the integrity gate is not disclosed anywhere, and the
  root cause (each arm can read its siblings' oracle-bearing files) is unfixed.
- **"Every number is re-derivable."** False for the `audit` column: the archive
  copies `result.json`/`audit.json`/`prediction.diff` but no trajectories, so the
  audit verdict is *attested*, not re-derivable. And `report --from-archive`
  **overwrites the file it is verifying** and silently drops the excluded-rows
  disclosure — that bug produced an undetected 20-line deletion of committed
  evidence.
- **`~$34/sweep`** — the archive of record sums to **$29.19**; $33.58 belongs to
  the superseded archive; actual factory burn across both sweeps was **$38.66**.

What the evidence does support, stated honestly: **the factory solved nothing
Claude Code missed — its 11 passes are a strict subset of Claude's 16.** That
needs no significance test and is the more useful framing than any pp gap.

Newly quantified variance: the archives already contain 10 same-condition
factory replications nobody reported. 0/10 oracle flips (95% upper bound on
per-instance flip probability 25.9% ⇒ ±3 instances at n=19), 1/10 chain-verdict
flips, and cost varying up to 2.6× on the same instance. k≥3 is required before
any delta means anything.

Also unexploited but live, all fail-open: grading is exit-code based so a
module-level `SkipTest` in production code would score RESOLVED; the test-strip
path logic keeps `pyproject.toml`/`pytest.ini`/`sitecustomize.py`/plugin
channels; `_DIFF_HEADER` is fail-open on git-quoted paths, merging an
unparseable test hunk into a kept block past both the stripper and the assert;
`audit.json` never hashes the graded patch; 2 instances have an empty
`PASS_TO_PASS`. Verified not exploited in this run (all 28 PASS rows have real
passed counts; 0 of 57 graded diffs touch a config path; 0 unparsed headers).

Fixes are in flight as operator PRs; `PLAN.md` 1.6 is the gate on any re-publish.

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
