# CLAUDE.md — orientation for an agent working in `software-factory`

Short by design. Everything else is on-demand — see **Deeper reading**. Do not
go spelunking through `factory/` for answers this file already gives.

## What this repo is

An autonomous software factory: LLM personas turn markdown work orders
("directions") into reviewed, tested, merged pull requests, unattended, on
cheap non-Anthropic models (Azure gpt-5.x + DeepSeek).

**It ships, and the chain is not proven.** Externally graded 2026-08-04 (n=19,
k=1): the chain resolves 37% where a *single* OpenHands agent on the same model
resolves 53% — no measurable lift (p=0.375), at 2.8× the cost per resolved
instance. Claude Code resolves 79%. Those figures are the later of two `report`
runs over this one sweep (`results-archive/2026-08-04T23-19-24.998844Z/`, the
archive the committed `results.md` re-derives from byte-for-byte); the earlier
`…T04-18-05.349995Z/` reports `openhands` 44% / p=0.625 / 2.3×, because three
rows lost to Azure 429s were excluded there; the later archive re-ran them as
`attempt: 2`. **The conclusion is
the same under either report** — the chain sits below one agent on the same
model, at p > 0.3 — and at MDE ≈ ±38 pp that is "no measurable lift", **not**
"the chain hurts". Do not write docs or directions that assume the chain's value
is established; see `STATUS.md`. **The Exteroception v1 direction is closed**
(`apps/factory/directions/019-exteroception-v1-close-the-sensing-gap/`) — its
seven acceptance criteria shipped as **operator PRs #247–#254, not the
chain**. No successor direction is filed yet; what it left open (three KNOWN
OPEN oracle risks — #2–#4, since #1 was closed by PR #256 — plus
`detector_watch` disabled pending a soak and the carried-over
operator queue) is in `STATUS.md`. The old `PLAN.md` is retired at
`docs/archive/PLAN-2026-08-07-retired.md`.

```
direction.md  →  PM (triage/split)  →  SM (story files)  →  Dev (OpenHands sandbox:
code + tests, run-until-green)  →  Reviewer (different model, concrete FIND/REPLACE
edits)  →  merge gates (full test suite + live runtime smoke)  →  PR auto-merged
→  deploy  →  tech-writer refreshes context docs
```

Personas are prompts (`factory/personas/*.md`). State machine, gates,
auto-merge and worktrees are in `factory/chain/`. The model per persona is one
YAML file (`factory/routes.yaml`) — a config value, not code.

## The three loops — you are loop 3

| Loop | Who drives | What it does |
|------|-----------|--------------|
| 1 | the factory | builds an **app** (`apps/sacrifice`) — the base case |
| 2 | the factory | builds **itself** (`apps/factory`), staging-gated, self-merges |
| 3 | **you** | watch loops 1–2; when they wedge, diagnose, patch, restart |

Loop 2 self-edits pass the **staging twin** (`factory/manager/staging.py`): the
diff is applied to a clone, the clone is actually run, and only a healthy clone
is promoted. Loop 2 works. Do not confuse it with the FMS **L4 apply** tier,
which was deleted 2026-08-07 — see `STATUS.md`.

Between you and the factory used to sit the **FMS manager daemon**
(`factory/manager/`): L1 Watcher (60 s, reads event streams) → L2 Summarizer →
L3 Diagnostician (root cause + diff) → L4 Apply. **Operator decision
2026-08-07: the four LLM tiers (watcher/summarizer/diagnostician/apply,
~4,704 LOC) were deleted** — they cost 52% of all-time spend and shipped 0
fixes. What survives in `factory/manager/`: the deterministic detectors,
`signals`, `halt`, `staging`, `recovery`, `circuit_breaker`, and
`forbidden_paths` (the shared self-edit path classifier, moved out of the
deleted `apply.py`). Detectors are wired into the chain tick
(`factory/chain/detector_watch.py`, 019 AC7, all 11 adapted with signature
dedupe) but **ship disabled** (`detector_watch.enabled: false` in
`factory_settings.yaml`) pending a soak — a read-only re-measurement against
real live state found the first cut would have filed 48 unfixable directions
in its first ~16 ticks. See `STATUS.md`.

**Your job is the class of failure the FMS cannot fix itself:** it crashes,
loops without converging, detects-but-never-remediates, or needs a fix in code
it is forbidden to touch. When L3 escalates to a human, the buggy code was not
in its source bundle and the fix is yours.

## First 60 seconds of any session

```bash
uv sync --all-extras                 # dev extras are OPTIONAL; bare `uv sync` has no pytest
git fetch origin && git status -sb   # the live tree MUST equal origin/main
uv run factory power                 # are the systemd units up?
uv run factory mode                  # a stuck non-normal mode blocks work
uv run factory status --app sacrifice
uv run factory inbox                 # anything awaiting a human
uv run factory budget
```

Then read the memory index at
`/home/k/.claude/projects/-home-k-software-factory/memory/MEMORY.md` — the
changelog of every failure class already diagnosed. Check it before
re-diagnosing anything. Then `STATUS.md` (what works, measured, and the
operator decisions). The **Exteroception v1 direction**
(`apps/factory/directions/019-…`) is closed; `STATUS.md` carries what it left
open and no successor direction is filed yet — check
`apps/factory/directions/` for the current newest before assuming otherwise.
Verify with the commands above rather than trusting either.

## Environment

Always `uv`, always the dev extras, always `uv run`:

```bash
uv sync --all-extras
uv run pytest -q                          # ~5 min
uv run ruff check . && uv run mypy factory
```

`ModuleNotFoundError` for `frontmatter` / `sqlmodel` / `pytest` means the env,
not the code — re-sync before debugging. `mypy` has a standing non-zero error
count; compare against `origin/main` rather than expecting clean. Provider keys
live in `.env` (`.env.example` documents every one).

## Where truth lives

| Fact | Source of truth | Notes |
|------|-----------------|-------|
| story state | `state/factory.db` (sqlite) | `factory queue`, `factory story <id>` |
| what happened | `state/events/*.ndjson` (+ hash chain) | `factory trace <id>`, `factory audit-chain` |
| handler logs | `state/logs/*.log` | some signals are ONLY here, not in events |
| direction progress | `apps/<app>/directions/<id>/state.yaml` | machine-written |
| merge reality | **GitHub** | never trust a local flag |
| operator config | `factory_settings.yaml`, `apps/<app>/config.yaml` | humans write these |
| machine config | `state/runtime/<app>.json` overlay | one writer per fact |

`state/**` is runtime and gitignored. Never `git add -A` in the live tree.

## Operator command surface

```bash
factory on / off / power            # whole-factory kill switch (timers; the FMS daemon slot is empty since 2026-08-07)
factory pm-sync --app X             # triage directions → stories  (--dry-run is a PURE preview)
factory approve-direction           # gate on MACHINE-FILED directions
factory tick --app X                # drive every in-flight story one step
factory status / queue / inbox      # where things are / in flight / needs a human
factory why <story-id>              # why is this stuck
factory trace <story-id>            # full per-story event log
factory audit --app X               # per-unit cost/token/time rollups
factory mode <name>                 # normal | fix-only | drain-reviews | paused | …
factory resume                      # clear an FMS halt — OPERATOR ONLY
factory tui                         # live dashboard
factory manager circuit-breaker|refresh-context|signals
factory reconcile-issues            # close issues left open by completed work
factory new-direction               # interactive; or the `new-direction` skill
```

Continuous operation = systemd **user** units. Chain code is picked up next
tick. There is no manager daemon anymore to restart — `factory-manager.service`
was retired 2026-08-07 along with the four LLM tiers.

## The loop-3 playbook

1. **Locate, don't guess.** `factory why <id>` → `factory trace <id>` →
   `state/logs/`. Check `state/manager_proposals/` for an L3 escalation that
   already names the root cause.
2. **Name the failure class** (below). Most wedges are a known class.
3. **Fix in a worktree off `origin/main`**, minimal scope.
4. **Review adversarially** — a second pass whose only job is to break the
   fix's fail-safety. This has caught ~5 production bugs green tests hid.
5. **Full `uv run pytest -q`**, then PR → real CI → squash-merge.
6. **Deploy**: `scripts/deploy-factory-from-main.sh` (`--dry-run` first).
7. **Validate on the live loops.** "Green + reviewed" is not "works unattended".
8. **Restart and re-verify**: check `systemctl --user status` Result +
   `errors=` across two runs. "Services up" ≠ "sustains".
9. **Record a new failure class** as a memory file.
10. **Refresh the touched subsystem's context doc.** Manual loop-3 PRs bypass
    the chain's `tech_writer` step, which is the only thing keeping
    `apps/factory/context/modules/*.md` current.

## Hard guardrails

- **Gate on the real artifact.** Never a recorded flag, a `--auto` *enable*, a
  dry-run's intent, or a green test-run without a commit. `proxy ≠ real` is the
  single most common bug class here.
- **The live tree must equal `origin/main`.** It has silently run ~60 commits
  behind. Verify at session start.
- **Never `git add -A`** here (runtime churn). Deploy surgically.
- `factory/manager/**` and `bench/**` are **forbidden to self-edit** — operator
  PR only. Every self-edit auto-merge surface stays staging-gated.
- **Nothing loops more than 3 times.** If you add a loop, cap it, and keep any
  early-escalation guard strictly below the hard cap or it becomes unreachable.
- **Reviewer independence**: `reviewer` must not share a model with any `dev`
  tier in `routes.yaml`. Enforced at router load; it refuses to resolve any
  route under a colliding config.
- **Fail SAFE**: a broken detector must block, not wave things through.
- **Fixes to shared control flow do not compose for free.** Touching
  merge/reconcile/dispatch means re-verifying everything keyed off it.
- Don't stop the factory to think; fix blockers on the spot.
- Spend caps live in `factory_settings.yaml` (`caps.daily_spend_usd`). Notify
  the operator at $50 / $75 / $100.
- `factory resume` and `factory pause` are operator decisions. Don't bypass.

## Failure patterns — recognize these fast

1. **proxy ≠ real** — trusting a stand-in. Cure: check the artifact.
2. **detect-without-remediate** — the factory notices but nothing closes the
   loop, so state rots.
3. **silent detection failure** — logic correct, substrate quietly wrong (e.g.
   a truncated slug breaking sibling detection).
4. **marked-solved ≠ soak-validated** — only unattended real loops surface these.
5. **compose-bugs between fixes** — fix B moves the path fix A hooked into.
6. **env/PATH and test-pollution mirages** — a "systemic" failure that is
   really a missing `uv` on the systemd PATH, or tests writing to production
   telemetry.
7. **"fixed and verified" without a commit** — a session's final summary is a
   self-report. The 2026-08-06 session reported two sacrifice bugs fixed with
   green tests; its own environment-restore discarded the work, and the bugs
   stayed live until re-fixed in PR #378. Trust a fix only when you can name
   its commit SHA or merged PR.
8. **rewritten fetched text** — the org-level `DESIGN → ENGINEERING` rewrite rule
   is applied to *fetched web content*, not only to prose you author. Research
   agents have read abstracts as "software ENGINEERING" where the source says
   "software design". It silently corrupts proper nouns in any retrieved source.
   **So: anything quoting a fetched benchmark, paper or product NAME is
   lower-confidence than anything quoting a NUMBER from the same fetch.** Cite by
   URL and arXiv id, and re-verify any fetched name before acting on it or
   quoting it outside this repo. This is the mundane cause of the caveat in
   `SOTA-RESEARCH-2026-07.md` ("Fetched content is lower-confidence than fetched
   numbers"), and it is why one load-bearing citation there was downgraded.

## Documentation style

Short sentences, active voice, consistent terminology. Lists where they help.
Keep prose for rationale. Optimize for clear, easy-to-diff docs.

## Deeper reading (open only when the task needs it)

| Need | File |
|------|------|
| product overview | `README.md` |
| every diagnosed failure + its fix | `…/memory/MEMORY.md` → the linked files |
| external SOTA literature | `SOTA-RESEARCH-2026-07.md` |
| generated subsystem deep-dives | `apps/factory/context/modules/*.md` |
| how to write a direction | `.claude/skills/new-direction/` |
| the retired plan + its correction ledger (history only) | `docs/archive/PLAN-2026-08-07-retired.md` |
| **the measured five-arm result** (the chain shows no lift — read before claiming otherwise) | `bench/swebench/results.md`, `bench/swebench/README.md` |
| convergence harness on the app's own gates (not evidence about correctness) | `bench/README.md` |

New app template (web + mobile boilerplate): `../template` — see its `CLAUDE.md`.
