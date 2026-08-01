# STATUS — measured 2026-08-01 (Phase 0 landed same day)

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
| Test suite | 2,182 tests, ~5 min |

Do not "fix" anything in this table without a measurement that shows it broke.

## What does not work

| Problem | Evidence | Fix |
|---|---|---|
| FMS **L4 apply** tier is dead | 163 attempts, 0 PRs, nothing since 2026-07-23 | `PLAN.md` Phase 4 |
| Manager cost is unjustified | ~52% of all LLM spend | `PLAN.md` Phase 4 |
| `factory_improver` does not land | 196 proposals, 1 commit. 179 apply failures | `PLAN.md` 3.1 |
| L3 re-diagnoses known faults | 165 proposals span 37 distinct classes | `PLAN.md` 3.3 |
| The benchmark is retracted | Tasks t1–t6 are shipped, so the pool is contaminated; the 20 reported rows still have no raw artifacts | `PLAN.md` Phases 1–2 |
| Gate precision is unknown | The merge gate runs the dev's own tests | `PLAN.md` 1.3 |
| State has no backup | The twin guards source only | `PLAN.md` 3.4 |

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
