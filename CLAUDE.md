# CLAUDE.md — orientation for an agent working in `software-factory`

Read this whole file (it is short by design). Everything else is on-demand —
see **Deeper reading** at the bottom. Do not go spelunking through `factory/`
to answer questions this file already answers.

## What this repo is

An autonomous software factory: a pipeline of LLM personas that turns
markdown work orders ("directions") into reviewed, tested, merged pull
requests, unattended, on cheap non-Anthropic models (Azure gpt-5.x +
DeepSeek — see `factory/routes.yaml`).

```
direction.md  →  PM (triage/split)  →  SM (story files)  →  Dev (OpenHands sandbox:
code + tests, run-until-green)  →  Reviewer (different model, concrete FIND/REPLACE
edits)  →  merge gates (full test suite + live runtime smoke)  →  PR auto-merged
→  deploy  →  tech-writer refreshes context docs
```

Personas are prompts (`factory/personas/*.md`). The state machine, gates,
auto-merge and worktrees are in `factory/chain/`. Model choice per persona is
one YAML file (`factory/routes.yaml`) — the model is a config value, not code.

## The three loops — you are loop 3

| Loop | Who drives | What it does |
|------|-----------|--------------|
| 1 | the factory | builds an **app** (`apps/sacrifice` today) — the base case |
| 2 | the factory | builds **itself** (`apps/factory`), staging-gated, self-merges |
| 3 | **you** | watch loops 1–2; when they wedge, diagnose, patch, restart |

Loop 2 self-edits pass the **staging twin** (`factory/manager/staging.py` →
`xvanov/software-factory-copy`): the diff is applied to a clone, the clone is
actually run, and only a healthy clone is promoted. Loop 2 works. Do not confuse
it with the FMS **L4 apply** tier, which is dead — see `STATUS.md`.

Between you and the factory sits the **FMS manager daemon** (`factory/manager/`),
a four-tier self-healing pipeline: L1 Watcher (60 s, cheap, reads event
streams) → L2 Summarizer (concern docs) → L3 Diagnostician (root cause +
unified diff) → L4 Apply (classify safe/forbidden, branch, test, PR). Plus
`recovery.py`, which auto-fixes known operational faults.

**Your job is the class of failure the FMS cannot fix itself:** it crashes,
it loops forever without converging, it detects-but-never-remediates, or the
fix it needs lives in code it is forbidden to touch (`factory/manager/**`,
`bench/**` — DGM anti-gaming). Be proactive: when L3 escalates to a human,
that means the buggy code was not in its source bundle, and the fix is yours.

## First 60 seconds of any session

```bash
uv sync --all-extras           # dev extras are OPTIONAL; bare `uv sync` has no pytest
git fetch origin && git status -sb   # the live tree MUST be at origin/main (see Guardrails)
uv run factory power           # are the systemd units up?  on / off / half-up
uv run factory mode            # normal | fix-only | paused | …  (a stuck non-normal mode blocks work)
uv run factory status --app sacrifice   # where every in-flight story is RIGHT NOW
uv run factory inbox           # everything across apps awaiting a human
uv run factory budget          # today's spend, projected end-of-day
```

Then read the memory index at
`/home/k/.claude/projects/-home-k-software-factory/memory/MEMORY.md` — it is
the changelog of every failure class already diagnosed. Check it before
re-diagnosing anything.

Then read `STATUS.md` (what is working, what is not, measured) and `PLAN.md`
(the current work queue). Verify with the commands above rather than trusting
either file.

## Environment

Always `uv`, always the `dev` extras, always `uv run` (no manual venv activate):

```bash
uv sync --all-extras
uv run pytest -q          # 2182 tests, ~5 min
uv run ruff check . && uv run mypy factory
```

`ModuleNotFoundError` for `frontmatter` / `sqlmodel` / `pytest` means the env,
not the code — re-sync before debugging. Provider keys live in `.env`
(`.env.example` documents every one).

## Where truth lives

| Fact | Source of truth | Notes |
|------|-----------------|-------|
| story state | `state/factory.db` (sqlite, `StoryRecord`) | `factory queue`, `factory story <id>` |
| what happened | `state/events/*.ndjson` (+ hash chain) | `factory trace <id>`, `factory audit-chain` |
| handler logs | `state/logs/*.log` | some signals are ONLY here, not in events |
| direction progress | `apps/<app>/directions/<id>/state.yaml` | machine-written |
| merge reality | **GitHub** | reconciled at tick top; never trust a local flag |
| operator config | `factory_settings.yaml`, `apps/<app>/config.yaml` | humans write these |
| machine config | `state/runtime/<app>.json` overlay | one writer per fact |

`state/**` is runtime and gitignored. Never `git add -A` in the live tree.

## Operator command surface

```bash
factory on / off / power            # whole-factory kill switch (timers + FMS daemon)
factory pm-sync --app X             # triage directions → stories  (--dry-run is a PURE preview)
factory approve-direction           # list/approve/--reject MACHINE-FILED directions (gate)
factory tick --app X                # drive every in-flight story one step
factory status / queue / inbox      # where things are / what's in flight / what needs a human
factory why <story-id>              # why is this stuck
factory trace <story-id>            # full per-story event log
factory audit --app X               # per-unit cost/token/time rollups
factory mode <name>                 # normal | fix-only | drain-reviews | paused | deploy-frozen | …
factory resume                      # clear an FMS halt — OPERATOR ONLY, never automate
factory tui                         # live dashboard
factory manager watch|diagnose|apply    # drive an FMS tier by hand
factory reconcile-issues            # close GitHub issues left open by completed/closed work
factory new-direction               # interactive; or use the `new-direction` skill
```

Continuous operation = systemd **user** units: `factory-tick@<app>.timer`,
`factory-manager.service`, `factory-self-deploy.timer`. Chain code is picked
up next tick; **manager code needs a service restart**.

## The loop-3 playbook

When a loop wedges, this is the method that has worked (and the shortcuts
that have burned us are in Guardrails):

1. **Locate, don't guess.** `factory why <id>` → `factory trace <id>` →
   `state/logs/`. Check `state/manager_proposals/` for an L3 escalation that
   already names the root cause.
2. **Name the failure class** (next section). Most wedges are a known class.
3. **Fix in a worktree off `origin/main`**, minimal scope. Spawn a scoped dev
   only for the edit; keep its context small.
4. **Review adversarially and independently** — a second pass whose only job
   is to break the fix's fail-safety. This has caught ~5 production bugs that
   green tests hid.
5. **Full `uv run pytest -q`**, then PR → real CI → squash-merge.
6. **Deploy**: `scripts/deploy-factory-from-main.sh` (surgical per-file sync of
   `factory/**` only, import-gated, auto-reverts on failure, restarts the
   manager). `--dry-run` first.
7. **Validate on the live loops** — seed a real direction and watch it ship.
   "Green + reviewed" is not "works unattended".
8. **Restart and re-verify**: `factory on`, then check `systemctl --user status`
   Result + `errors=` across two runs. "Services up" ≠ "sustains".
9. **Record the class** as a memory file if it is new.
10. **Refresh the touched subsystem's context doc.** Manual loop-3 PRs (this
    playbook) bypass the chain's `tech_writer` step, which is the only thing
    that keeps `apps/factory/context/modules/*.md` current — that's why they
    went stale for 2+ months despite ~180 merges. If your fix materially
    changed a documented subsystem, hand-update its module doc in the same PR.

## Hard guardrails

- **Gate on the real artifact.** Never a recorded flag, a `--auto` *enable*, a
  dry-run's intent, or a green test-run without a commit. `proxy ≠ real` is the
  single most common bug class in this repo.
- **The live tree must equal `origin/main`.** It has silently run ~60 commits
  behind. Verify at session start.
- **Never `git add -A`** here (runtime churn). Deploy surgically.
- `factory/manager/**` and `bench/**` are **forbidden to self-edit** — operator
  PR only. Every self-edit auto-merge surface stays staging-gated.
- **Nothing loops more than 3 times** (review cycles, retries, recovery).
  If you add a loop, cap it. As of 2026-08-01 the code honours this:
  `_MAX_DEV_RETRIES = 3`, `_MAX_REVIEW_CYCLES = 3`, `_MAX_CI_FIX_CYCLES = 3`.
  The inner early-escalation guards sit one below, at 2
  (`_MAX_DEV_SAME_SIGNATURE`, `_MAX_REVIEW_STUCK`), so they still fire *before*
  the hard cap — keep that gap if you retune either number.
- **Reviewer independence**: `reviewer` must not share a model with any `dev`
  tier in `factory/routes.yaml`. Enforced at router load
  (`model_router.check_review_independence`); it refuses to resolve any route
  under a colliding config. Override with `FACTORY_ALLOW_REVIEW_COLLISION=1`.
- **Fail SAFE**: a broken detector must block, not wave things through.
- **Fixes to shared control flow do not compose for free.** Touching
  merge/reconcile/dispatch means re-verifying everything keyed off it.
- Don't stop the factory to think; fix blockers on the spot. Daily spend cap
  **$200** — notify the operator at $50 / $75 / $100.
- `factory resume` and `factory pause` are operator decisions. Don't bypass.

## Documentation style

Write documentation in an ASD-STE100-inspired style: short sentences, active
voice, consistent terminology, concise paragraphs. Use lists where they improve
readability. Keep natural prose for concepts, rationale, and design discussion.
Do not force strict ASD-STE100 if it reduces clarity. Prioritize clear,
easy-to-diff documentation.

## Failure patterns — recognize these fast

1. **proxy ≠ real** — trusting a stand-in for the real thing. Cure: check the artifact.
2. **detect-without-remediate** — the factory notices (escalation, stall
   detector, tracker issue) but nothing closes the loop, so state rots.
3. **silent detection failure** — logic correct, substrate quietly wrong (e.g. a
   truncated slug breaking sibling detection). Identity must never ride on a
   truncatable string.
4. **marked-solved ≠ soak-validated** — only unattended real loops surface these.
5. **compose-bugs between fixes** — fix B moves the path fix A hooked into.
6. **env/PATH and test-pollution mirages** — a "systemic" failure that is
   really a missing `uv` on the systemd PATH, or tests writing to production
   telemetry.

## Deeper reading (open only when the task needs it)

| Need | File |
|------|------|
| product overview, benchmarks | `README.md` |
| every diagnosed failure + its fix | `…/memory/MEMORY.md` → the linked files |
| SOTA research reference (external literature, not internal status) | `SOTA-RESEARCH-2026-07.md` |
| generated subsystem deep-dives | `apps/factory/context/modules/*.md` |
| how to write a direction | `.claude/skills/new-direction/` (skill), `apps/<app>/directions/` |
| factory-vs-Claude-Code benchmark | `bench/README.md` |

New app template (web + mobile boilerplate the factory bootstraps from):
`../template` — see its own `CLAUDE.md`.
