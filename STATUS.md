# STATUS — measured 2026-08-01

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
| Dev has no prompt telemetry | `_log_prompt_metadata` is called only from `text_run` | `PLAN.md` 0.1 |
| Retry outcomes are not recorded | 0 `retried` rows in `chain_steps`; 41 in `dev_retries` | `PLAN.md` 0.2 |
| Smoke-gate diagnostics are discarded | `auto_merge.py` keeps passing labels only | `PLAN.md` 0.5 |
| `StoryRecord.smoke_passed` is never assigned | Declared at `state_machine.py:302` | `PLAN.md` 0.5 |
| The benchmark is retracted | Unpinned base SHA, 19 of 20 artifacts deleted, tasks now shipped | `PLAN.md` Phases 1–2 |
| Gate precision is unknown | The merge gate runs the dev's own tests | `PLAN.md` 1.3 |
| State has no backup | The twin guards source only | `PLAN.md` 3.4 |
| Review is not independent on the hard tier | `azure_routes.dev.hard` and `azure_routes.reviewer` are both `azure/gpt-5.3-codex` | `PLAN.md` 0.6 |

Read the last row carefully. Cross-family review is the only structural defence
against a model approving its own reasoning. It holds on the standard tier
(`deepseek-v4-pro` dev vs `gpt-5.3-codex` reviewer). It **collapses on the hard
tier** — the tier a story escalates to when it is difficult, which is when
independent review matters most. This is an operator decision, not a bug to
patch blindly: changing it changes cost and quality together.

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
