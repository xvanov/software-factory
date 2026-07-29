# Software-Factory Handoff — bring loop-1 + loop-2 to a clean "runs unattended" close

_Written 2026-07-21 after a long hardening + soak session. This is the detailed
reference; the short kickoff prompt lives at the bottom (or is pasted separately)._

## What this system is
A self-hosting "software factory" (repo: `/home/k/software-factory`) that autonomously:
- **Loop-1:** improves ITSELF (edits `factory/` code, staging-gated, self-merges to live).
- **Loop-2:** ships work for an app, **sacrifice** (`xvanov/sacrifice`).
Directions (`apps/<app>/directions/<id>/direction.md`) → PM validates → dual-draft stories →
dev (OpenHands sandbox) → reviewer → gates → auto-merge (real CI) → deploy. A manager daemon
(L1–L4 FMS) monitors/­self-heals.

## READ FIRST (memory)
`/home/k/.claude/projects/-home-k-software-factory/memory/`:
1. `MEMORY.md` (index)
2. `factory_selftick_first_cycle_2026_07_21.md` — this session's full record
3. `factory_autonomy_synthesis_2026_07_19.md` — architecture + hardening plan
4. `pm_sync_dry_run_pure_preview_2026_07_20.md`

## Current live state (VERIFY before acting)
- **Loop-1: healthy + self-sustaining.** Scheduled personas (e.g. `ux_auditor`) auto-file factory
  directions each tick (dirs 009, 011 were auto-generated); they build → chain-side staging gate
  (clone + run the factory) → self-merge to live. Dual-draft now ships exactly ONE interpretation
  (validated live: dir 010 over-fired pre-#87; dir 011, same slug shape, clean post-#87).
- **Loop-2 (sacrifice): ships fresh directions, but has a stuck backlog** (see OPEN ISSUE 2).
- **7 fixes shipped this session**, each via scoped-dev → INDEPENDENT adversarial review → real CI →
  squash-merge → surgical deploy: #53 (dry-run purity), #58 (ruff-clean PRs), #59 (auto-merge-enable
  ≠ merged strand), #68 (green-dev-commit churn), #70/#76/#87 (the dual-draft over-fire chain).
- **systemd (user):** `factory-manager.service` (L1 daemon, auto_apply + auto_recover ON) +
  `factory-tick@sacrifice.timer` (5-min) + `factory-tick@factory.timer` (30-min, `self_tick_enabled:
  true`). All active. Deploy of chain code is picked up next tick; manager code needs a service restart.
- **Soak monitor:** a change/alert Monitor runs `scratchpad/soak_alert.py` — pings only on a NEW
  over-fire, a new blocked story, or spend crossing $50/$75/$100. Re-arm it if the session reset it.
- **Spend:** ~$30/day, cap $200. Notify the operator at $50/$75/$100.

---

## THE JOB — close out 3 OPEN issues → "runs healthy unattended"

### OPEN 1 — Issue-lifecycle / auto-close (the biggest lever)
Completed directions/stories leave their GitHub issues OPEN forever. The factory has **8 stale-open
issues** (all completed: direction-trackers D005/D006/D009/D011 + their story issues); sacrifice's
19 include many of the same kind.
- **Root cause:** there is NO mechanism to close a `direction-tracker` issue when the direction
  completes, nor a winner `story` issue when it deploys. `close_abandoned_draft_sibling` DOES close
  dual-draft LOSER issues — but on the reconcile path (`orchestrator._close_dual_draft_sibling_on_reconcile`)
  it builds a client via `build_github_client`, which returns `None` without a token in that context,
  so it closes the loser's PR (via `gh`) but SKIPS the issue-close (that's why #79/#90 are open).
- **Fix:** on story deploy / direction completion, close the corresponding GitHub issue (deduped,
  fail-safe, never breaks the tick). Give the reconcile-path sibling cleanup a real GitHub client.
  Then GC the existing stale-open issues. This is the "detect-without-remediate" rot — the single
  biggest lever for a clean unattended state.

### OPEN 2 — Sacrifice backlog stall
**7 open sacrifice PRs are lint-blocked on ruff `F401` (unused imports)**; ~6 more stories are
`story_created` and never dispatched (17–42h idle). The factory correctly REFUSES to merge a
failing-CI PR (gate-on-real-artifact — do NOT weaken this) — the problem is nothing FIXES the CI.
- **Root cause (three compounding):**
  1. Dev leaves `F401` unused imports in its output.
  2. The pre-PR autoformat (#58, `handlers._autoformat_changed_py_before_pr`) is DELIBERATELY limited
     to `--select I` (import-sort) + `ruff format` — it won't delete imports (F401), because a blanket
     `ruff --fix` can remove a side-effect import and break untested-after code. AND it doesn't run on
     sacrifice at all: its `has_ruff` detection requires `[tool.ruff]` in pyproject/ruff.toml, but
     sacrifice uses default-config ruff via `ruff check .` (no `[tool.ruff]` where it looks).
  3. The **CI-failure→dev recovery loop** (`auto_merge._handle_ci_failure`, fires when
     `_query_ci_state == "failure"`) is NOT converging these — they've sat lint-blocked 17–30h.
  4. Undispatched `story_created` ones likely blocked by in-flight-cap saturation
     (`caps.per_repo_concurrent_agents=10`) held by the stuck PRs, plus ~30-min ticks.
- **Fix (pick ONE coherent approach; all touch the live merge/recovery path → scoped-dev +
  adversarial review + real CI):**
  - Make autoformat run for sacrifice — detect ruff via `app_config.gates.lint_command` containing
    `"ruff"` — AND safely strip `F401` **only on the story's OWN newly-added imports** (not
    pre-existing side-effect imports). Narrow + safe.
  - AND/OR fix the CI-failure→dev loop to reliably re-dispatch + fix lint-blocked PRs (the more
    general fix; investigate WHY it isn't firing/converging — the higher-value root fix).
  - AND bound/GC stories stuck at `pr_open` past a threshold so they stop saturating the cap.

### OPEN 3 — Over-fire residue + dual-draft robustness (low priority)
- Dirs **007/008/010** shipped BOTH dual-draft siblings to `main` pre-#87 (duplicate but CI-green
  code). Decide: leave, or revert the redundant commits.
- Consider making dual-draft sibling-linkage robust: a dedicated DB column (e.g. `dual_draft_group_id`
  / `interpretation`) instead of the lossy `-alt-*` **slug suffix** that silently truncated for long
  titles (root cause of #87). Detection/identity should never depend on a truncatable string.

---

## Full issue ledger

### A) Entered this session already "solved" (prior initiative, PRs #32–#52)
| # | Target | Issue | Solution (PR) | Pattern |
|--|--|--|--|--|
| 1 | factory | FMS re-fired same concern every 60s | stable-sig dedup + cooldown (#32) | detect-without-remediate |
| 2 | both | False-green merges (trusted recorded state) | real-run re-run tests + ablation; drop 6 vestigial gates (#33) | proxy≠real |
| 3 | factory | Unbounded composed loops | per-story budget breaker (#34) + dev-loop accounting (#41) | unbounded loops |
| 4 | both | Dev owns tests → reward-hack risk | dev-blind acceptance oracle (#36) + EARS→property (#48) | verify at outcome layer |
| 5 | factory | Rubric review churn | rubric criterion axis + hardened parse (#35) | — |
| 6 | factory | halt fails OPEN | uniform SAFE fail-direction (#40) | fail-safe |
| 7 | both | Local state drifts from GitHub | reconcile-from-GitHub at tick top (#44) | single source of truth |
| 8 | factory | Config drift (machine wrote operator config) | runtime-state overlay (#43) | one writer per fact |
| 9 | factory | Escalations died silently | deduped GitHub-issue escalation (#47) | no silent sink |
| 10 | factory | Self-edit could brick the factory | staging-clone validation; bench/manager forbidden (#46/#47) | shadow-deploy / DGM |
| 11 | both | CI-failure→dev loop emitted a string finding | dict finding + coercion (#39) | fresh-env caught it |
| 12 | both | New DB cols not migrated | migration list + migrate-after-deploy (#37) | proxy≠real |
| 13 | both | Merge-queue / flaky tests | merge_group + flake quarantine (#49) | real base / no false-green |
| 14 | both | No replay/resume | typed step stream + resume-from-checkpoint (#50) | — |
| 15 | factory | Informal control plane | formalized + invariant tests (#51) | deterministic control plane |
| 16 | factory | Chain could merge unvalidated self-edit | OFF-by-default guard + chain-side staging (#52) | shadow-deploy everywhere |

### B) Fixed THIS session (PRs #53/#58/#59/#68/#70/#76/#87; demos #57/#63)
| # | Target | Issue | Root cause | Solution (PR) | Pattern |
|--|--|--|--|--|--|
| 17 | factory | THE blocker: `pm-sync --dry-run` spawned live dispatchable stories | dry-run wrote state.yaml + persisted StoryRecords | dry-run = pure preview, zero persistent writes (#53) | proxy≠real / dry-run≠real |
| 18 | both | Lint escapes to CI, blocks merge | chain didn't run ruff before opening the PR | pre-PR ruff isort+format on changed files (#58) | gate on real artifact |
| 19 | both | Story stranded at `deploy_pending` | `gh pr merge --auto` ENABLE treated as MERGED | confirm real merge; reconcile records merge + enqueues deploy (#59) | proxy≠real |
| 20 | both | dev↔review churn on green code | green dev path relied on non-deterministic agent self-commit → empty diff | deterministic commit on green + resume paths (#68) | proxy≠real (empty-diff) |
| 21 | both | Dual-draft over-fire — logic | cleanup closed only loser's issue, not its PR/story | close loser PR + terminal `superseded_by_sibling` (#70) | detect-and-remediate |
| 22 | both | Over-fire persisted on async merges | cleanup only on sync merge path; #59's reconcile path bypassed it | reconcile-path cleanup + merge-time self-check + stale-snapshot guard (#76) | proxy≠real / compose |
| 23 | both | Over-fire on long titles (THE root) | `-alt-*` slug suffix truncated by 60-char cap → sibling detection failed SILENTLY | preserve suffix (truncate base) (#87) | silent detection failure |
| — | factory | demo: loop-1 first self-improvement | — | secret redaction shipped self-gated (#57) | — |
| — | factory | demo: loop-1 autonomous (zero-touch) | — | `factory apps` shipped hands-free (#63) | — |

### C) Found this session, NOT yet fixed (the JOB above)
| # | Target | Issue | Root cause | Status |
|--|--|--|--|--|
| 24 | both | Completed directions/stories leave GitHub issues open | no auto-close on completion; reconcile-path issue-close no-ops without a token | OPEN (Job 1) |
| 25 | sacrifice | Backlog stall: 7 PRs lint-blocked (F401), stories undispatched | autoformat won't touch F401 + doesn't run on sacrifice; CI-failure→dev recovery not converging; cap saturation | OPEN (Job 2) |
| 26 | factory | dirs 007/008/010 over-fired before #87 | pre-#87 slug bug | residue (Job 3; harmless dup on main) |

---

## Patterns (why these bugs happen)
1. **`proxy ≠ real` is the dominant class** (2, 12, 17, 19, 20, 22). Whenever the system trusts a
   stand-in — a recorded flag, a dry-run's unwritten intent, an `--auto` *enable*, a green *test-run*
   without a *commit* — it breaks. Cure: always gate on the real artifact.
2. **"Marked solved" ≠ "validated end-to-end unattended."** The strand, the dev-commit churn, and the
   3-iteration dual-draft over-fire all shipped green+reviewed, yet only the SOAK (real loops running
   unattended) surfaced them. Local green + review is necessary, not sufficient.
3. **Compose-bugs between fixes.** #59 (moved merge-detection to reconcile) silently broke #70/#76
   (cleanup lived on the old sync path). Independent fixes to shared control flow don't compose free.
4. **Silent detection failure is the worst kind** (#87). Logic was correct; the substrate (a slug
   suffix) failed quietly for long titles, so everything downstream no-op'd with no error.
5. **Detect-without-fully-remediate is the recurring rot** (1, 9, 24, 25). The factory detects well
   (escalations, CI signals, stall detectors, tracker issues) but its remediation loops don't
   converge/complete → stale state (open issues, stuck PRs, un-GC'd stories). Biggest gap to
   unattended health.
6. **Adversarial review earns its keep** — caught double-deploy, FMS concern-spam, and the
   stale-snapshot clobber that green tests missed.

## Guardrails (learned the hard way)
- Gate on the REAL artifact (re-run tests at merge, confirm the GitHub merge, diff the committed
  tree) — never a recorded flag / an `--auto` enable / a green test-run without a commit.
- Fixes to shared control flow don't compose for free — when you touch merge/reconcile/dispatch,
  re-verify every mechanism that keys off it.
- Validate on the LIVE loops (seed a real direction, watch it ship) — "green + reviewed" ≠ "works
  unattended."
- Work in git worktrees off `origin/main`; PR → real CI → squash-merge; deploy via surgical
  `git checkout origin/main -- factory/<changed files>` + restart `factory-manager.service`. NEVER
  `git add -A` in the live tree (runtime churn). Confirm no drift (`git diff origin/main~1 -- <file>`
  == 0) before checkout.
- `factory/manager/**` and `bench/**` are FORBIDDEN to SELF-edit (DGM anti-gaming) — but the operator
  may edit them via a normal PR. Every self-edit auto-merge surface stays staging-gated.
- Method: scoped-dev subagent (minimal context) → INDEPENDENT adversarial reviewer (make it try to
  break fail-safety) → real CI → squash-merge → deploy. Run the FULL `uv run pytest -q` before
  trusting green — real CI + review caught ~5 prod bugs this session that green tests hid.
- `uv sync --all-extras` then prefix everything with `uv run`. Daily spend cap $200; never stop the
  live factory; fix blockers on the spot; notify operator at $50/$75/$100.
- gotchas: `git checkout` reverts to the STAGED index (stage your edits or they're lost); when a dev
  subagent's `git checkout -b` doesn't stick you get a detached HEAD (re-point the branch before push);
  `uvx ruff` / default-config ruff means "no `[tool.ruff]`" does NOT mean "doesn't use ruff".

## Definition of done
Both loops run a sustained unattended window with: no stranded/stuck stories (all converge OR are
bounded/GC'd); no stale-open issues for completed work; no over-fire; no false-green; sacrifice
backlog drained or explicitly closed. Report a readiness number (1–10) as you progress.
