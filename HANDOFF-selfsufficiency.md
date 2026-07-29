# Handoff — make the software factory self-sufficient to finish the sacrifice tasks

_Written 2026-07-23 after a session that got sacrifice `main` green, fixed two factory
bugs, and shipped D110/D111/D112. The factory can now **pick up directions, open PRs, and
(for clean changes) auto-merge them**. It is NOT yet able to **finish backend work
unattended** — a human still has to intervene on lint convergence, story reconciliation,
issue cleanup, and deploy. This doc lists exactly what to close so it runs hands-off._

## READ FIRST
- Memory: `/home/k/.claude/projects/-home-k-sacrifice/memory/` — esp.
  `factory-vacuous-diff-and-deploy-drift.md`, `sacrifice-deploy-model.md`,
  `sacrifice-live-db-isolation.md`, `sacrifice-stack-layout.md`.
- Prior factory handoff: `/home/k/software-factory/HANDOFF.md` (OPEN issues 1–3 there are
  the same rot classes; this doc supersedes their priority ordering).
- Operating rules: work through the factory (create directions; let it implement/merge).
  Do NOT push directly to sacrifice `main` — use CI-gated PRs. Required checks on
  sacrifice main: **lint, pytest, smoke**.

## VERIFIED STATE (2026-07-23, re-verify before acting)
- sacrifice `main` = `fe453b6`, **CI green**. 0 open PRs. 15 open issues (all factory-
  generated trackers/story issues; NOT a work queue — the factory works from local
  `apps/sacrifice/directions/`, never from GitHub issues).
- Shipped this session: `main` lint fix (#339), factory docs-enforcer vacuous-diff fix
  (factory PR #104, deployed), D110 login-verification tests (#349), D111 sign-in tests
  (#350), D112 auto-redeploy script (#351), systemic ruff fix (#352 — root `ruff.toml` +
  pinned `uvx ruff@0.15.22`).
- Factory services: `factory-tick@sacrifice.timer` + `factory-manager.service` both
  **active** (timer = OnUnitInactiveSec=300, i.e. fires 5 min after each tick completes;
  a NEXT of "-" while a tick runs is normal). Tick runs `uv run factory tick --app
  sacrifice` from `/home/k/software-factory`.
- D109 (obsolete lint direction) is quiesced: stories 130/131 = `superseded_by_sibling`;
  its issues #336/#337/#338 closed.

## DEFINITION OF DONE (self-sufficient)
The operator seeds a direction and walks away. The factory: decomposes → dev (converges
on lint/tests WITHOUT a human touching ruff) → reviews → opens PR → CI green → auto-merges
→ marks the story `deployed` and supersedes the losing dual-draft sibling → closes the
tracker/story issues → the deployed app tracks `main`. No stranded stories, no stale-open
issues, no hand-fixed lint, backend backlog drained or explicitly closed.

---

## THE GAPS TO CLOSE (priority order) — each is a factory loop-1 change

### G1 — Dev must converge on lint by itself (the #1 reason humans still intervene)
This session a human hand-fixed `F541`/`E402`/`F841` on #349/#351 because the factory's
pre-PR autoformat only runs `--select I` (isort) + `ruff format` — it never removes
F-class errors, so any dev-authored F401/F541/unused-var lands red and the CI-failure→dev
recovery loop does not reliably converge.
- **Root**: `handlers._autoformat_changed_py_before_pr` is deliberately limited to isort +
  format. Now that #352 unified the ruleset (dev sees the SAME rules as CI via the repo
  `ruff.toml`), it is safe to also run `ruff check --fix` **on the story's own
  newly-added files only** (never pre-existing files — a blanket `--fix` can drop a
  side-effect import). This clears F401/F541/E402/F841 pre-PR.
- **Also**: verify the autoformat actually RUNS for sacrifice (historically its `has_ruff`
  detection required `[tool.ruff]` in pyproject; sacrifice now has a root `ruff.toml`, so
  confirm detection keys off that OR off `app_config.gates.lint_command` containing
  "ruff").
- **Verify**: seed a throwaway backend direction that adds a file with an unused import;
  watch it converge to a green PR with zero human touches.

### G2 — Reconcile merged PRs → mark story deployed → supersede the sibling
Stories 132 (D110, PR #349 MERGED) and 136 (D112, PR #351 MERGED) are still
`pr_open` / `reviewer_requested_changes` in the DB, and their dual-draft siblings
(133, 137) are still `story_created`/live — so the factory can re-dispatch redundant work.
(Contrast 134/D111 which reconciled to `deployed` correctly — so the path works
sometimes; find why the manual-merge / auto-merge paths for 132/136 were missed.)
- **Root**: the reconcile-from-GitHub-at-tick-top (`orchestrator`, PRs #44/#59/#76) that
  detects a merged PR and enqueues deploy + closes the sibling did not fire for these two.
  Likely because they were merged out-of-band (one by a human, one by the factory's own
  auto-merge) in a state the matcher didn't expect.
- **Fix**: make reconcile detect ANY merged PR whose number maps to a non-terminal story,
  regardless of who merged it, mark it `deployed`, and run the dual-draft sibling cleanup
  (`superseded_by_sibling` + close loser PR/issue).
- **Immediate cleanup** (safe DB edit, do in the inter-tick quiet window — a running tick
  clobbers out-of-band edits): set 132→`deployed`, 136→`deployed`, and 133/135/137→
  `superseded_by_sibling`. Then verify the reconcile fix keeps them that way.

### G3 — Auto-close issues for completed/superseded directions
`factory reconcile-issues --app sacrifice` closes 0 because it only closes trackers for
*deployed* directions; D111 is deployed yet its tracker #343 + story issues are still
open, and superseded work never closes. 15 issues linger.
- **Fix**: on story `deployed` AND on `superseded_by_sibling`, close the corresponding
  story issue; on direction completion (all stories terminal), close the tracker. Give the
  reconcile path a real GitHub client (it no-ops without a token in that scope — root cause
  of the historical stale-open issues). Then GC the current 15.
- **Verify**: `gh issue list --repo xvanov/sacrifice --state open` trends to only
  genuinely-in-flight work.

### G4 — Deploy the factory's own code to the running tree (loop-1 deploy drift)
The live factory tree runs on branch `factory-hardening/tier0-manager-hygiene`, **14 ahead
/ 56 behind `origin/main`**. Factory self-improvements merged to its `main` (incl. this
session's #104) are NOT auto-deployed to the running ticks — they're hand-synced per-file
as `deploy:` commits, and there are local-only hotfixes never PR'd (e.g. a manager
concern-spam fix). So the running factory lags its own repo.
- **Fix**: a loop-1 deploy step that, after a factory-repo `main` merge, surgically updates
  the changed `factory/**` files in the live tree and restarts `factory-manager.service`
  (per-file `git checkout origin/main -- <file>`, NEVER `git add -A` in the live tree —
  runtime state churn). Reconcile the 14 local-only commits: PR the real hotfixes to main,
  drop the rest, so the live tree can track main cleanly. `factory/manager/**` and
  `bench/**` remain forbidden to SELF-edit (operator-PR only).

### G5 — Revive the blocked backend backlog so it benefits from the ruff fix
Blocked now (won't self-revive): D092 `blocked_deploy_failed`; D093/096/097/099
`blocked_ci_unresolved`+`blocked_dependency_unmet`; D094 `blocked_tests_need_clarification`;
D098 `blocked_budget_exceeded`. Many are duplicate email-verification / password-reset
directions across sessions.
- **Fix**: after G1 lands, revive these (reset to a dispatchable pre-dev state + zero the
  budget/attempt counters, in the quiet window) and let them re-run under the unified
  ruleset. FIRST dedupe: D093/D097/D107 (email verify) and D094/D098/D108 (password reset)
  look redundant — pick one of each, supersede the rest, so the factory isn't shipping the
  same feature three times.

### G6 — Finish D112: wire + validate auto-redeploy (deployed == main)
#351 added `scripts/auto-redeploy.sh` (idempotent: deploy-gate check → fetch → ff-only on
genuine advance → restart the four `sacrifice-*` user services → health-gate + rollback).
It is NOT wired up and `deploy.enabled` is `false`.
- **Fix**: add a systemd user timer (or cron) invoking the script; flip `deploy.enabled`
  true when ready; do ONE supervised end-to-end run (merge a trivial change → confirm it
  appears on the running instance). NOTE: the operator checkout `/home/k/sacrifice` is on
  branch `backup/pre-sync-local-main`, not `main` — the script ff-only's to origin/main, so
  reconcile the checkout branch first. This also satisfies "local == remote == deployed".

### G7 (optional) — dual-draft robustness + factory self-improvement issues
- Replace the lossy `-alt-*` slug-suffix sibling linkage with a real DB column
  (`dual_draft_group_id`) so detection never depends on a truncatable string (root cause of
  a prior over-fire, #87).
- software-factory issues #96/#99/#100 are loop-1 follow-ups (invalid-enum row reconcile;
  CI genuine-failure guard against duplicate check names; dual-draft dependency-order
  exemption). Turn each into a factory direction or operator PR — they are NOT auto-picked.

---

## METHOD & GUARDRAILS (learned; do not skip)
- **Gate on the real artifact.** Re-run tests at merge; confirm the actual GitHub merge;
  diff the committed tree. Never trust a recorded flag / an `--auto` enable / a green
  test-run without a commit.
- **The factory dev/CI ruleset is now unified** via sacrifice's root `ruff.toml` +
  pinned `uvx ruff@0.15.22` in `.github/workflows/ci.yml`. Keep them in lockstep; if you
  bump the pin, bump both and re-verify format determinism. Ruff config resolves from the
  nearest ancestor, so the repo-root `ruff.toml` shadows software-factory's parent config
  for dev sandboxes running in `state/worktrees/`.
- **Out-of-band DB edits race the tick.** A running tick holds story rows in memory and
  persists them at tick end, clobbering your edit. Make DB edits in the inter-tick quiet
  window (service inactive), or `factory pause` first, then `resume`.
- **CI's `lint` job lints CHANGED files only.** A PR touching a pre-existingly-unformatted
  file must `ruff format` that whole file to pass. Legacy debt is otherwise untouched.
- **Work in worktrees off origin/main; PR → real CI → squash-merge.** For factory (loop-1)
  changes: full `uv run pytest -q` + an INDEPENDENT adversarial review before merge (it
  caught a real empty-diff regression in #104 this session). Then deploy per G4.
- **Spend**: factory ~$30–55/day; daily cap $300 (chain self-stops $180). Notify the
  operator at $50 / $75 / $100 (crossed $50 on 2026-07-23).

## READINESS: ~8/10 (updated 2026-07-23 PM)

**G1–G4 DONE, deployed, and live-validated** (each via scoped work → INDEPENDENT
adversarial review that caught real bugs → CI green → squash-merge → surgical deploy):
- **G1** (factory PR #105): autoformat clears F401/F541/F841 on the story's own added
  lines, per-code gated, with a result-check that reverts on a `ruff --fix` cascade.
- **G2** (#106): reconcile detects a merged PR from ANY non-terminal state; new standing
  `reconcile_dual_draft_winners` supersedes in-flight losers every tick; supersede
  decoupled from the GH client. **Live-validated**: stuck 136 + stranded 133/137 all
  self-healed one tick post-deploy; redundant PRs closed.
- **G3**: already present in `tick()` (rate-gated + pause-guarded issue sweep) — the
  original note was stale. Open issues 15→7 (the 7 are legit recoverable backlog).
- **G4** (#107): `scripts/deploy-factory-from-main.sh` + `scripts/systemd/factory-
  self-deploy.{service,timer}` (enabled) — the factory now auto-syncs its own
  `factory/**` merges from origin/main (excl. manager/bench), import-gated, revert-safe.

**Remaining — OPERATOR DECISIONS (not auto-run this session):**
- **G5** backend backlog: G3 already closed the abandoned dupes' issues. Draining the
  kept features (revive email D107 + password D108) is raw live-DB surgery on
  dual-draft pairs + factory budget + can't validate in-session → green-light needed.
- **G6** deployed sacrifice app tracks main: the operator checkout is on
  `backup/pre-sync-local-main`, **11 ahead / 81 behind, NO merge base** with origin/main;
  the 11 local commits include live mobile/goals fixes possibly not on main. Fast-
  forwarding the LIVE app risks regressing them — reconcile the branch by hand first.

_(original readiness note below, for history)_

## READINESS (original): ~5/10
Directions flow in and clean PRs merge, but backend convergence, story reconciliation,
issue cleanup, and deploy still need a human. Closing G1–G4 should get it to a real
"seed-and-walk-away" 8+.
