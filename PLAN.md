# PLAN.md — measurement-first hardening of the software factory

**Written 2026-08-01. Every number and every `file:line` below was re-verified
against this working tree on that date.** If you are a fresh agent: read
`CLAUDE.md` first (it is short and authoritative), then this file top to bottom,
then start at Phase 0. Do not skip Phase 0 — every later phase depends on
measurement that does not exist yet.

---

## 0. Environment and guardrails (read before touching anything)

```bash
uv sync --all-extras          # dev extras are OPTIONAL; bare `uv sync` has no pytest
uv run pytest -q              # 2182 tests collected (verified 2026-08-01), ~5 min
uv run ruff check . && uv run mypy factory
git fetch origin && git status -sb    # live tree MUST equal origin/main
```

`ModuleNotFoundError` for `frontmatter` / `sqlmodel` / `pytest` means the env,
not the code — re-sync before debugging.

**Hard guardrails (from `CLAUDE.md`, non-negotiable):**

- **Gate on the real artifact.** Never a recorded flag, an `--auto` *enable*, a
  dry-run's intent, or a green test run without a commit. `proxy ≠ real` is the
  single most common bug class in this repo.
- **The live tree must equal `origin/main`.** It has silently run ~60 commits
  behind before.
- **Never `git add -A`** here (`state/**` is runtime churn). Deploy surgically
  with `scripts/deploy-factory-from-main.sh` (`--dry-run` first).
- **`factory/manager/**` and `bench/**` are forbidden to self-edit** — operator
  PR only (DGM anti-gaming). Enforced in code at
  `factory/manager/apply.py:67-71`. Steps below that touch those trees are
  flagged **[OPERATOR-PR-ONLY]**.
- **Chain code is picked up next tick; manager code needs a service restart**
  (`systemctl --user restart factory-manager.service`).
- Daily spend cap **$200**; notify the operator at $50 / $75 / $100.
- `factory resume` / `factory pause` are operator decisions. Never automate.
- Nothing loops more than ~3 times. **Note the code does not currently honor
  this** — see "Corrections" #11.

---

## 1. Current state — verified numbers

All re-verified 2026-08-01 against `state/factory.db`, `state/events/*`, and the
GitHub API.

### The chain (loop 1 + loop 2) — healthy

| Fact | Value | How verified |
|---|---|---|
| Stories with a `github_pr_number` | **122** of 165 | `stories` table |
| …by app | factory 32, sacrifice 88, template-probe 2 | `stories` table |
| PRs merged on `xvanov/software-factory` | **118** | `gh pr list --state merged` |
| Factory stories `deployed` (all-time) | **24** | `stories` where `app='factory'` |
| All stories `deployed` (all-time) | **117** (sacrifice 91, factory 24, probe 2) | `stories` |
| Staging gate outcomes | **17 validated / 3 rejected** | `state/events/manager_staging.ndjson` |
| Open PRs | **0** | `gh pr list --state open` |
| Open issues | **1** (#122, the D002 Karpathy direction) | `gh issue list --state open` |
| Blocked stories | **0** — every row is `deployed` (117), `superseded_by_sibling` (37), or `closed_by_operator` (11) | `stories.state` |

### Cost

| Fact | Value |
|---|---|
| All-time LLM spend | **$1,976.91** (50,849 runs, 2026-05-25 → 2026-07-31) |
| All-time manager (`persona LIKE 'manager%'`) spend | **$1,028.58 = 52.0%** |
| July 2026 all-in | **$588.78** / 75 stories deployed = **$7.85 per story** |
| July 2026 excluding manager | **$217.18** / 75 = **$2.90 per story** |
| Top persona by spend | `manager_watcher` — 44,127 runs, **$972.23** |

`factory/manager/detectors/fms_yield.py:10-16` is the in-repo record of this:
it documents 163 apply attempts, 0 `pr_number`, "$1,028 (53% of all factory LLM
spend)". The docstring literal is 53%; the currently-measured share is 52.0%.

### The FMS (manager daemon) — L4 apply tier is dead

| Fact | Value | Source |
|---|---|---|
| L4 apply attempts | **163** | `state/.manager_apply_history.json` |
| …that ever set a `pr_number` | **0** | same |
| Newest attempt | `20260723T174823` (oldest `20260527T135919`) | same |
| Classification split | escalate_to_human 105, risky 40, safe 17, forbidden 1 | same |
| Status split | escalation_acknowledged 105, abandoned 53, staging_rejected 3, test_failed 1, forbidden 1 | same |
| L3 proposals on disk | **165** files | `state/manager_proposals/*.json` |
| …with `escalate_to_human: true` | **107** | proposal JSON's own flag |
| Distinct raw `concern_title`s | **48** | proposal JSON |
| …normalized (story numbers → N, drop repeat/continuation/persists) | **37 → 78% redundant** | see Corrections #3 |

**This is distinct from the chain path above. Do not conflate them.** The chain
opens and merges real PRs (118 merged). The FMS L4 tier has never opened one.

### `factory_improver` (the older, separate self-improvement seam)

| Fact | Value |
|---|---|
| Proposal files / proposals | 84 files, **196 proposals** (`state/improvements/`) |
| Landed commits | **1** — `6bd463a3` "auto: factory_improver applies prompt_edit (#5)", 2026-05-27, +10 lines to `factory/personas/test_implementer.md` |
| Apply-log outcomes | **179 `apply_failed`** + 2 `proposal_invalid` + 1 `self_test_failed` (`state/logs/_factory_improver_apply.log`, 182 lines) |
| Failure reasons | `dirty_working_tree` **158**, `corrupt patch` **16**, `patch failed` **5**, `self_test_regression` 1 |

### Telemetry gaps (this is what Phase 0 fixes)

- `_log_prompt_metadata` (`factory/runner.py:86`) is called from **exactly one
  place**: `factory/runner.py:1734`, inside `text_run` (`def text_run` at
  `:1703`). `sandbox_run` (`:1205`) never calls it. Confirmed empirically:
  `state/events/prompts.ndjson{,.1}` has 45,868 rows across 14 personas and
  **zero rows for `dev`, `test_implementer`, or `onboarder`** — the three
  sandbox personas, and the ones that write all the code.
- What is recorded is metadata only: `prompt_length_total`,
  `prompt_section_lengths`, `placeholder_markers_found`, and a **16-char**
  sha256 prefix (`factory/runner.py:117`). Never the prompt text. The
  docstring at `:94-96` says so explicitly.
- `state/events/chain_steps.ndjson`: **410 rows, outcomes `advanced` 400 /
  `error` 10 — zero `retried` rows**, while 41 stories have `dev_retries > 0`
  (71 retries all-time, 119 reviewer cycles all-time). Dev retries and reviewer
  cycles happen *inside* a single handler invocation, so they never reach
  `emit_chain_step`.

### Pricing accuracy

`factory/providers/azure_foundry.py`:

- `:130-131` — input **$1.93 / 1M**, output **$3.83 / 1M**, both marked
  "Azure retail, eastus2", verified 2026-07-18.
- `:152` — `_DEEPSEEK_V4_PRO_CACHE_READ_PER_TOKEN = 1.61e-7` (~**$0.161 / 1M**),
  **ESTIMATED**, derived at `:145-151` by scaling the
  `fireworks_ai/deepseek-v4-pro` cache/input ratio (8.33%) onto the verified
  Azure input rate. No Azure retail meter publishes a cached-token rate for
  this deployment, and the account lacks the Cost Management RBAC role needed
  to reconcile against the real bill.
- `uv run factory audit` (default 7-day window) reports
  **"55.4% of window spend ($25.81) used a model whose LiteLLM price
  registration is flagged estimated (azure/deepseek-v4-pro)"**. Over
  `--days 60` the same caveat reports **33.9% ($515.90)**. The percentage is
  window-dependent — always state the window.
- `db_path` **is** threaded through `runner._record` (`factory/runner.py:1751`
  wraps `_record_run`; `db_path=db_path` is passed at every call site). The old
  bench-cost-leaks-into-production ledger bug is fixed.

### The benchmark

- `bench/tasks.yaml:11` — `base_sha: ""  # resolved at setup time when empty`.
  **Unpinned.** `bench/bench.py:65-66` (`_base_sha`) resolves it at run time.
- `bench/bench.py:459-500` (`clean()`) ends with
  `shutil.rmtree(RUNS_DIR, ignore_errors=True)` at `:499`. `bench/results/`
  contains only `summary.md`; `bench/runs/` contains exactly **one**
  `result.json` (`bench/runs/t3_csrf/factory-2/result.json`), which is **not**
  one of the 20 rows in `summary.md`. The raw per-run artifacts behind every
  reported number are gone.
- Claude arm: `bench/bench.py:163` invokes `"claude", "-p", prompt` with **no
  `--model`** — unpinned, and on **subscription** billing.
  `bench/CAMPAIGN-2026-07-17.md:33,51` records **4 of 13** Claude attempts lost
  to usage-window trips.
- All six directions behind bench tasks t1–t6 (`023`–`028`) are now
  **`closed`** — contaminated, the factory has since shipped them.
  `apps/sacrifice/directions/` holds 76 directions: **31 closed, 45
  `pm-validated`** — the 45 are the held-out candidate pool.
- `bench/bench.py:260-270` seeds a `StoryRecord` directly at
  `StoryState.SM_DONE.value` (`:267`) in an isolated bench root — this is the
  pattern the Phase-1 adapter mirrors.

### The twin repo

`factory/manager/staging.py:72`:
`DEFAULT_COPY_URL = "git@github.com:xvanov/software-factory-copy.git"`.
The canary/shadow deploy (`staging.py` docstring + `:519-635`) syncs the copy to
`origin/main`, applies the candidate diff on a staging branch **of the copy**,
then actually runs the clone (uv sync → full pytest → import smoke → `factory
--help` → dry-run tick) and promotes only if healthy. Timeouts at `:79-84`.

`gh repo view xvanov/software-factory-copy` → **`"visibility":"PUBLIC"`**.
(So is `xvanov/software-factory` itself.) The twin guards **source only** —
nothing anywhere in `factory/**` snapshots `state/factory.db` (verified: no
backup/snapshot code exists; `state/factory.db.bak-1784662396` is a one-off
manual copy).

---

## 2. What is NOT broken — do not go fix these

A fresh agent's biggest risk here is re-diagnosing something already solved.
All four of these were checked on 2026-08-01 and are working.

1. **Chain self-edit works.** 122 stories carry a PR number, 118 PRs are merged,
   24 factory stories reached `deployed`, and the staging gate has a real
   17-validated / 3-rejected record. Loop 1 is proven zero-touch. Nothing to fix.

2. **CI-failure recovery works.** `factory/chain/auto_merge.py:1640-1830`
   (`_handle_ci_failure`) fetches the CI log digest, emits a well-formed finding
   *dict*, re-enters at `REVIEWER_REQUESTED_CHANGES` (deliberately not
   `DEV_IN_PROGRESS`, which has no dispatch-table entry), and resets both
   counters. It is capped at `_MAX_CI_FIX_CYCLES = 3` (`auto_merge.py:72`) plus
   an identical-failure-signature bail (`:1759-1766`). A previous session
   already misdiagnosed this as broken — the `ci_fix` events live in
   `state/logs/*.log`, **not** `state/events/*.ndjson`. Look in the right place
   before concluding it is dead.

3. **Reviewer non-convergence is fixed.** Last 14 days (122 stories):
   `reviewer_cycles` = {0: 101, 1: 18, 4: 2, 5: 1} — **zero stories at 6+**, max
   5. All-time there were 11 stories at 6–7. The convergence guard holds.

4. **The GitHub loop is clean.** 0 open PRs, 1 open issue (#122, a real backlog
   direction), 0 blocked stories. Issue lifecycle / auto-close was fixed in a
   prior session and is holding.

Also already fixed, so do not re-fix:

- **`dirty_working_tree` in both apply paths.** Both
  `factory/manager/apply.py:882-897` and
  `factory/chain/factory_improver_apply.py:418-436` are now **path-scoped**
  (`git diff --quiet HEAD -- <patch target paths>`, falling back to repo-wide
  only when the patch is unparseable). The 158 historical
  `dirty_working_tree` failures in the improver log all predate this. See
  Corrections #10 — this materially shrinks Phase 3.1's payoff.
- **`db_path` threading in `runner._record`** — done.

---

## Phase 0 — make measurement possible — **DONE 2026-08-01**

**Actual: one session, $0 (no LLM calls).** Shipped as PRs #193 #194 #195 #196
#197, each with real CI. Start at Phase 1.

Corrections this work produced — the plan was right about every defect, and
wrong or silent about four consequences:

1. **0.1 needed a persona scope the plan did not anticipate.** Storing every
   prompt body would have been 1.58 GB from `manager_watcher` alone (43,561 of
   45,868 rows; 93% of all prompt text), rolling the stream every few hours and
   evicting exactly the dev/reviewer bodies it exists to retain. Bodies are
   captured for chain personas only, `FACTORY_PROMPT_BODIES` overrides.
2. **0.2's suggested `extra={"attempt": n}` would have shadowed a field.**
   `emit_chain_step`'s payload already carries `attempt` (= `total_attempts`)
   and merges `extra` last. Used `retry_attempt`/`retry_cap`.
3. **0.5 Bug B changes no behaviour today.** `smoke_passed` is always None, so
   the dry-run branch was already unreachable and the gate already fail-closed
   — by accident. Deleting the reader makes it structural. Do not expect a
   measurable difference; expect a removed trap.
4. **Correction #11's caps could not simply be set to 3.** `_MAX_DEV_RETRIES`
   and `_MAX_REVIEW_CYCLES` at 3 equal the inner guards
   (`_MAX_DEV_SAME_SIGNATURE`, `_MAX_REVIEW_STUCK`, both 3), making the
   early-escalation layer unreachable and deleting "findings that CHANGE are
   progress". The inner guards moved to 2 to preserve the gap. Consequence:
   the dev inner loop now gets at most TWO sandbox attempts per invocation.

Each sub-step's original text is kept below for its file references.

### 0.1 — Wire `_log_prompt_metadata` into `sandbox_run` — **DONE (#193)**

- [x] **Files:** `factory/runner.py` (`_log_prompt_metadata` at `:86`,
      `sandbox_run` at `:1205`, existing call site at `:1734`),
      `factory/manager/signals.py` (`write_event`, already hash-chains).
- **What:** call `_log_prompt_metadata` from `sandbox_run` at the point the
  initial message is composed, with the same kwargs the `text_run` site uses
  (`persona`, `prompt`, `model_id`, `story_id`, `software_factory_root`). Then
  add a second, separate stream — `state/events/prompt_bodies.ndjson` — that
  stores the **full prompt text** plus the full sha256 (not the 16-char prefix
  at `:117`), hash-chained the same way `write_event` already chains
  `chain_steps`.
- **Why a second stream:** `prompts.ndjson` is already 45,868 rows and is read
  by the `placeholder_prompts` detector; do not bloat it. Bodies are large and
  want their own rotation.
- **Watch out:** the `manager_*` marker-scan carve-out at `factory/runner.py:104-112`
  exists to stop a self-sustaining false-positive escalation loop. Preserve it
  verbatim. Also keep the best-effort `try/except` — a telemetry failure must
  never break an LLM call.
- **Done looks like:** after one real dev story, `prompts.ndjson` contains rows
  with `persona: "dev"`, and `prompt_bodies.ndjson` contains the matching full
  text with a verifiable `prev_hash`/`entry_hash` chain.
- **Verify:**
  ```bash
  python3 -c "
  import json,collections
  c=collections.Counter(json.loads(l)['persona'] for l in open('state/events/prompts.ndjson') if l.strip())
  print(c)"   # must now include dev / test_implementer / onboarder
  uv run factory audit-chain    # chain integrity still green
  ```
- **Effort:** ~3 h. Chain code — self-editable, deploys next tick.

### 0.2 — Emit `chain_step` events for retries and review cycles — **DONE (#194)**

- [x] **Files:** `factory/chain/handlers.py` (`story.dev_retries += 1` at
      `:1930`; `story.reviewer_cycles += 1` at `:2906`),
      `factory/chain/step_events.py` (`emit_chain_step` at `:72`, `outcome`
      param documented at `:84`), `factory/chain/orchestrator.py` (existing
      emit sites at `:3013` and `:3073`).
- **What:** the only two emit sites today are in the orchestrator, and `:3073`
  hardcodes `outcome="error" if result.error else "advanced"`. Retries and
  review cycles happen *inside* a single handler invocation and are therefore
  invisible. Add `emit_chain_step(..., outcome="retried")` next to the
  `dev_retries` increment and `outcome="review_cycle"` next to the
  `reviewer_cycles` increment, with `extra={"attempt": n, "cap": _MAX_*}`.
- **Done looks like:** `chain_steps.ndjson` grows `retried` / `review_cycle`
  rows, and their per-story counts reconcile exactly with
  `stories.dev_retries` / `stories.reviewer_cycles`.
- **Verify:**
  ```bash
  python3 -c "
  import json,collections,sqlite3
  c=collections.Counter()
  for l in open('state/events/chain_steps.ndjson'):
      if l.strip(): c[json.loads(l)['outcome']]+=1
  print(c)
  db=sqlite3.connect('state/factory.db')
  print('db sum dev_retries', list(db.execute('select sum(dev_retries) from stories')))"
  ```
  (Historical rows won't backfill; reconcile only on stories that ran *after*
  the change.)
- **Effort:** ~2 h. Chain code.

### 0.3 — Pin the bench — **DONE (#197)** **[OPERATOR-PR-ONLY]**

- [x] **Files:** `bench/tasks.yaml` (`:11`), `bench/bench.py`
      (`_base_sha` `:65-66`, `run_claude` `:155-193` incl. the
      `"claude","-p",prompt` invocation at `:163`, `clean()` `:459-500`, the
      `shutil.rmtree(RUNS_DIR)` at `:499`), `bench/README.md`.
- **What:**
  1. Write a real SHA into `base_sha` (`git -C ../sacrifice rev-parse
     origin/main`) and make `_base_sha` **raise** on empty rather than
     resolving live. Unpinned is the whole problem.
  2. Add `--model <pinned id>` to the `claude -p` invocation and record the
     resolved model id in every `result.json`.
  3. Record, in each `result.json`, the git SHA of `factory/routes.yaml` and of
     the price table (`factory/providers/azure_foundry.py`) at run time.
  4. Delete the `shutil.rmtree(RUNS_DIR, ...)` line. Replace with an explicit
     `--purge-runs` flag that is off by default. Raw results are the evidence;
     `clean()` currently destroys them (all 20 reported rows' `result.json` are
     already gone).
- **Done looks like:** a fresh `bench.py setup` fails loudly if `base_sha` is
  empty; a completed run leaves a `result.json` that names the base SHA, the
  Claude model, the routes SHA and the price-table SHA; `clean()` leaves
  `bench/runs/` intact.
- **Verify:** `grep -n 'base_sha' bench/tasks.yaml` shows a 40-char hex;
  `uv run python bench/bench.py clean` then `find bench/runs -name result.json`
  still returns the files.
- **Effort:** ~4 h. **Operator PR — do not self-merge.**

### 0.4 — Make TOKENS the benchmark primitive — **DONE (#197)**

- [x] **Files:** `bench/bench.py` (`_write_result` `:114`, `report()` `:502+`)
      **[OPERATOR-PR-ONLY]**; `factory/providers/azure_foundry.py` (price
      constants `:130-152`); `factory/cli.py` (`audit` at `:2320`, the
      estimated-cost caveat at `:2342-2345` and `:2388-2395`).
- **What:** dollars in this repo are ~55% derived from an *estimated* cache-read
  rate (default 7-day window; 33.9% over 60 days). Tokens are exact and
  provider-reported (`runs.tokens_in`, `runs.tokens_out`,
  `runs.cached_input_tokens`). Report tokens as the primary comparison metric.
  Emit dollars only as a **presentation layer**, computed from a price table
  serialized into the result with its own content hash, so a later price
  correction can re-derive every past number without re-running anything.
- **Done looks like:** `bench/results/summary.md` leads with
  `tokens_in / tokens_out / cached_in` per arm; the `$` column is annotated with
  the price-table hash; re-running `report()` with a corrected price table
  changes only the `$` column.
- **Verify:** change one constant in the price table, re-run `report()`, confirm
  token columns are byte-identical and only dollars moved.
- **Effort:** ~4 h. **Operator PR** for the `bench/**` half.

### 0.5 — Fix the two smoke-gate bugs — **DONE (#195)**

- [x] **Bug A — failing gates' diagnostics are discarded.**
      `factory/chain/gates/smoke_green.py:51-56` returns
      `GateResult(..., reason=f"smoke_command exit={code}",
      details={"exit_code": code, "output_tail": output})`. But
      `factory/chain/auto_merge.py:880` keeps only
      `gates_passed = [label for label, r in results.items() if r.passed]` —
      the failing results, with their `reason` and `output_tail`, are thrown
      away. `MergeAction` persists only `gates_passed_json`
      (`auto_merge.py:120`, `:198`; the `merge_actions` table has no
      failed-gate column). So when the smoke gate blocks a merge, *nobody can
      see why*.
      **Fix:** compute `gates_failed = [r.as_dict() for r in results.values()
      if not r.passed]` alongside line 880 and (a) log it via
      `log_story_event` / an `alerts` event, and (b) add a
      `gates_failed_json` column to `MergeAction` + the `merge_actions`
      migration. `GateResult.as_dict()` already exists at
      `factory/chain/gates/evaluator.py:127`.
- [x] **Bug B — `smoke_passed` is write-never.**
      `StoryRecord.smoke_passed` (`factory/chain/state_machine.py:302`) is
      declared and is **read** at `factory/chain/gates/smoke_green.py:62`
      (`if story is not None and getattr(story, "smoke_passed", False)`) — but
      a repo-wide grep finds **no chain handler that ever assigns it**. (The
      `smoke_passed` writes at `factory/deploy/orchestrator.py:608` are on
      `DeployAction`, a different object.) The dry-run branch at
      `smoke_green.py:58-67` therefore trusts a flag that is always `None`.
      **Fix — pick one, do not leave it ambiguous:** either assign
      `story.smoke_passed = True` in the dev handler after the smoke journey
      actually runs green in the sandbox (the documented intent, per the
      comment at `:59-61`), **or** delete the dead dry-run branch entirely and
      make the gate fail-closed without a real run. Deleting is the fail-safe
      option and is the default recommendation; a flag that is never written is
      textbook `proxy ≠ real`.
- **Done looks like:** a deliberately-failing smoke command produces a story
  event containing the `output_tail`; and `grep -rn "smoke_passed" factory/`
  shows either a real writer or no dry-run reader.
- **Verify:** `uv run pytest -q tests/ -k "smoke or gate or auto_merge"`, then
  seed one story with a broken smoke command and read `factory trace <id>`.
- **Effort:** ~4 h. Chain code. **Fail-safe review required** — this touches
  merge control flow, so re-verify everything keyed off `gates_passed`
  (`auto_merge.py:892` builds `present_labels` from it).

### 0.6 — Reviewer/dev model independence — **DONE (#196)**

- [x] **Files:** `factory/model_router.py` (`route()` at `:114`; existing
      validation raises at `:89` and `:172`), `factory/routes.yaml`.
- **⚠ This assertion FIRES TODAY as naively specified.** Verified in
  `factory/routes.yaml`:
  - `azure_routes.dev.standard: azure/deepseek-v4-pro`,
    `azure_routes.reviewer: azure/gpt-5.3-codex` — different. ✅
  - `azure_routes.dev.hard: azure/gpt-5.3-codex` — **identical to `reviewer`.**
    This is deliberate (the comment at that line calls the hard tier "a
    genuinely different model family" from the *standard* dev, i.e. the escape
    hatch from deepseek's content-filter blocks) but it collapses reviewer
    independence exactly when a story is hardest.
  - `azure_routes.test_implementer: azure/deepseek-v4-pro` — **identical to
    `dev.standard`**, despite the `acceptance_author` comment (`routes.yaml`,
    direct block) asserting "the test author and the implementer never share a
    model".
- **What to do:** implement the check at router load, but scope it correctly:
  1. **Hard error** if `reviewer` == `dev.standard` for the active provider
     block.
  2. **Hard error** if `reviewer` == `dev.hard`, and *resolve the existing
     collision* — either move `reviewer` to `azure/gpt-5.4` or give `dev.hard`
     a distinct deployment. This is an operator decision; surface it, do not
     silently pick.
  3. **Warn-once** if `test_implementer` == `dev.*`.
- **Done looks like:** `uv run factory --help` fails fast with a clear message
  on a colliding `routes.yaml`, and passes on the corrected one.
- **Verify:** temporarily set `reviewer` to `azure/deepseek-v4-pro`, confirm
  `uv run factory --help` exits non-zero with the assertion message; revert.
- **Effort:** ~2 h code + one operator decision on the `dev.hard` collision.

---

## Phase 1 — first real number — **1.1–1.5 DONE 2026-08-02**

**⚠ Read 1.5 before citing any 1.3 number.** The committed `results.md` table
and the artifacts now on disk are from different sweeps and disagree, and no
`grade.json` survives. Do 1.5 before 1.4. *(Resolved: the paired 2026-08-02
factory+bare sweep in 1.4 is the run of record, and `report` is now
artifact-backed — see 1.5.)*

**Effort ~1.5 days. Cost ~$40.** Goal: one honest, externally-graded datapoint
plus the matched bare-model number,
using a corpus the factory has never seen.

**2026-08-02 status:** 1.1–1.3 shipped (#199, #200, #202, #204, #205) after the
2026-08-01 batches were retracted for three harness bugs (#202/#203/#205 fixed
them; see `STATUS.md`). Valid numbers, n=6 audited-valid: 1/6 resolved,
chain-verdict precision 1/5, recall 1/1. **Start at 1.4.**

### 1.1 — SWE-bench Pro adapter  **[OPERATOR-PR-ONLY — new file under `bench/`]** — **DONE (#199, #200)**

- [x] **New file:** `bench/swebench_adapter.py`. **Pattern to mirror:**
      `bench/bench.py:240-300` — it constructs a `StoryRecord` with
      `state=StoryState.SM_DONE.value` (`:267`), an isolated bench root, and a
      restricted handler set (`allowed = {"dev", "review"}` at `:278`).
- **What:** given a SWE-bench Pro public instance (`repo`, `base_commit`,
  `problem_statement`), clone at `base_commit` into an isolated bench root,
  write the problem statement as the story file, seed a `StoryRecord` at
  `SM_DONE`, and drive `orchestrator` with the same restricted handler set.
- **Watch out:** there is **no existing SWE-bench code in this repo** —
  `grep -ril swebench` hits only `SOTA-RESEARCH-2026-07.md`. This is greenfield.
  Use an isolated `FACTORY_STATE_ROOT` so bench runs never write to production
  telemetry (a prior session lost a week to exactly that pollution).
- **Done looks like:** `uv run python bench/swebench_adapter.py run
  --instance <id>` produces a git diff in the bench root and a `result.json`.
- **Effort:** ~4 h.

### 1.2 — Grade with the official harness, stripping test edits — **DONE (#199, #202)**

- [x] **What:** run the official SWE-bench evaluation harness against the
      produced patch. **Before grading, strip every edit to a test file from
      the graded diff.** The factory's dev owns tests (the Loop-4 design), so
      an unstripped diff would let it edit the oracle — the single most common
      way SWE-bench numbers get inflated.
- **⚠ Know your suite's noise floor before you read any result.**
  `SOTA-RESEARCH-2026-07.md:119-123` records that OpenAI's 2026-07-08 audit found
  **~30% of SWE-bench Pro's public tasks broken** and retracted its
  recommendation, and that Cursor found Pro scores collapse when agents lose
  internet and git history — some agents were retrieving gold patches. This does
  not disqualify the suite (it is still the best structural fit and the only one
  publishing baselines for our exact models), but it means: clone `--depth 1`,
  block egress except the model API, expect a substantial unsolvable floor rather
  than reading it as factory failure, and record per instance whether a failure
  was "wrong patch" or "task broken".
- **Done looks like:** the graded diff provably contains zero `tests/` or
  `test_*.py` hunks (assert it in code, do not eyeball it).
- **Effort:** ~3 h.

### 1.3 — Run 10 instances; report gate precision and recall — **DONE (#204, #206) — n=6 audited-valid of 10 pinned (4 excluded by selftest: gold patch does not resolve)**

- [x] **What:** 10 instances. Report the two numbers that actually matter:
  - **gate precision** = P(hidden oracle passes | the factory said tests-green)
  - **gate recall** = P(the factory said tests-green | hidden oracle passes)
- **Why these:** the factory's merge gate runs the dev's *own* tests. Precision
  against a hidden oracle is the only way to know whether that gate means
  anything. A high resolve rate with low gate precision would mean the gates are
  decorative.
- **⚠ Do NOT justify this with the July campaign's "verification discipline"
  finding.** That claim (`CAMPAIGN-2026-07-17.md`, Finding #2: "Claude declared
  done without running its own new tests to green") was **falsified** by the
  recovered Claude CLI transcripts: t3 ended on three consecutive `460 passed`
  runs, and t5's last recorded run was `446 passed` before a subscription limit
  killed it. Neither was a verification failure. Measure gate precision because
  it is unmeasured, not to confirm a retracted result — that is how you get a
  benchmark that agrees with you.
- **Done looks like:** a table of 10 rows (instance, factory verdict, oracle
  verdict, tokens, wall clock) plus the two rates, with n=10 stated as
  preliminary. **Do not draw conclusions from n=10** beyond "the harness runs".
- **Effort:** ~2 h of babysitting, ~$30.

### 1.4 — Run the SAME 10 instances against the bare model — **DONE 2026-08-02**

- [x] **What:** run a minimal scaffold (mini-SWE-agent, ~100 lines of bash loop)
      on the **identical Azure deployments** the factory uses — same
      `azure/deepseek-v4-pro` and `azure/gpt-5.3-codex`, same instances, same
      oracle. Report `scaffold lift = factory − bare model`, in resolve rate and
      in tokens.
- **Why this is not optional, and why it moves ahead of Phase 2:** the product
  thesis is a **model-agnostic harness that gets frontier-competitive output from
  non-frontier models**. The model is a config value that will be swapped monthly
  as cheaper models ship. Therefore the only number that measures *the harness*
  is the delta between the harness and the same weights bare. A factory resolve
  rate on its own is unattributable — the public SWE-rebench board already
  reports what these models do with a trivial scaffold, and a skeptical reader
  will say so.
- **Corollary for every later phase — CORRECTED 2026-08-04.** The matched
  baseline is **`openhands`**, not `bare`. `factory − bare` varies the chain *and*
  the tool interface at once, which is why the retracted "+58 pp" was
  unattributable; 1.6 measured `openhands − bare` at p=0.031, i.e. most of that
  delta was simply having usable tools. So: **never report a factory number
  without the matched `openhands` number beside it.** Absolute scores measure the
  model; only `factory − openhands` measures the product.
- **Done looks like:** a two-column table, factory vs bare, on the same 10
  instances, with the lift stated in percentage points and tokens.
- **Effort:** ~3 h, ~$10 (the bare arm is far cheaper per instance).
- **Result (2026-08-02):** both arms ran the same n=6 audited-valid instances.
  Factory 1/6 resolved = bare 1/6 resolved at ~34× the tokens, and both arms
  resolved the SAME qutebrowser instance. The lift fixes derived from the four
  trajectory autopsies ship in the 1.5 commit. **Superseded by 1.6** — "scaffold
  lift" is no longer the metric and this pair is not a chain measurement.

### 1.5 — Re-derive the 1.3 numbers, then make `report` artifact-backed  **[OPERATOR-PR-ONLY]** — **DONE 2026-08-02 (the lift-fixes commit)**

- [x] **The 1.3 headline is not reproducible from this tree.**
      *Done: `report` now snapshots every consumed artifact into
      `bench/swebench/results-archive/<generated-at>/` (committed, not
      gitignored) and refuses any row whose artifacts are missing.*
      `bench/swebench/results.md` (committed in #206, generated
      `2026-08-02T14:01:07Z`) reports 6 rows — 4 `right_place_wrong_fix`, 1
      `empty_patch`, 1 `resolved`. The artifacts on disk now are from a **later**
      sweep (`result.json` mtimes 16:23–16:30Z; untracked `sweep-factory.json`
      finished `16:35:29Z`) reporting **5 `right_place_wrong_fix` + 1 `resolved`,
      `cost_usd: 6.7342`**. Per instance the two disagree: `ansible-34db57`
      published 2,299,905 in / 23,472 out / 419.0 s vs on-disk 1,827,811 /
      15,913 / 408.8 s; `openlibrary-3aeec6af` published `empty_patch`,
      142,903 in / 70.6 s vs on-disk 2,985,777 in / 50,735 out / 847.9 s.
      **No `grade.json` exists anywhere under `bench/swebench/runs/`**, so the
      oracle PASS/FAIL column behind the published table has no backing
      artifact at all.
- [x] **This is the July retraction class, recurring one day later.**
      `STATUS.md:33` retracted the old benchmark partly because "the 20 reported
      rows still have no raw artifacts". #202 added `_reset_run_artifacts`
      (`bench/swebench_adapter.py:848`), which correctly clears stale state at
      run start — but nothing snapshots a *published* run first, so re-running
      the sweep destroys the evidence for numbers already committed.
      *Done: the archive snapshot happens at `report` time, before any later
      sweep can wipe `runs/`; `report --from-archive <dir>` re-derives the
      table from the snapshot alone.*
- [x] **Do first:** decide which run is the run of record and say so in
      `results.md`. Until one is re-derived from artifacts that still exist,
      treat `STATUS.md:55-59` ("1/6 resolved … $3.33") as **unbacked** — do not
      cite it, and do not use it as the baseline any later change is compared
      against.
      *Done: the paired 2026-08-02 factory+bare sweep (1.4) is the run of
      record; every later table must come from an archived `report` run.*
- **Then fix the harness:** `report` must (a) copy every `result.json` /
  `grade.json` / `audit.json` it consumed into a dated
  `bench/swebench/results-<ISO>/` committed alongside the markdown, and
  (b) **refuse to emit a row whose artifacts are missing** rather than
  reporting it. Same fail-closed posture as the audit gate.
  *(Shipped as `bench/swebench/results-archive/<generated-at>/` holding
  `result.json` + `audit.json` + `prediction.diff` per row — there is no
  standalone `grade.json`; `grade` merges its verdict into `result.json`.)*
- **Done looks like:** a second `report` run re-derives the committed table
  byte-for-byte from the committed artifacts, with no live sweep.
- **Effort:** ~3 h. **Blocks 1.4 from being interpretable** — a bare-model delta
  measured against an unbacked factory number measures nothing.

---

### Phase 1 outcome (2026-08-04, five arms, n=19) — **the chain shows no measurable lift**

Clean five-arm sweep on the SWE-rebench pinned manifest `923aef05add32124`, 19
working-oracle instances, **n=19, k=1, no re-rolls**, tables pre-registered in
`bench/swebench/PRE-REGISTRATION-1.6.md`. Evidence:
`bench/swebench/results.md` + `results-archive/2026-08-04T04-18-05.349995Z/`,
re-derivable with `report --check`.

| arm | harness × model | resolved / valid | rate | 95% CI | $ | $ / resolved |
|---|---|---:|---:|---|---:|---:|
| claude-5 | Claude Code CLI × `claude-opus-5` | 15/19 | 79% | [54%, 94%] | 34.36 † | 2.29 † |
| claude-4.8 | the SAME CLI × `claude-opus-4-8` | 14/19 | 74% | [49%, 91%] | 23.56 † | 1.68 † |
| openhands | OpenHands single agent × `azure/deepseek-v4-pro` | 7/16 | 44% | [20%, 70%] | 15.37 | 2.20 |
| factory | the chain on OpenHands × deepseek-v4-pro + gpt-5.3-codex + gpt-5.4 | 7/19 | 37% | [16%, 62%] | 35.94 | 5.13 |
| bare | hand-rolled text loop, no tool calls × deepseek-v4-pro | 1/18 | 6% | [0%, 27%] | 7.94 | 7.94 |

† subscription-reported by the CLI; the Azure rows are price-table estimates.
Different bases — never summed. `factory` vs `openhands` is one basis and exact.

Paired McNemar exact: **factory vs openhands n=16, 1/3, p=0.625** · **openhands
vs bare n=15, 0/6, p=0.031** · bare vs factory n=18, 1/7, p=0.070 · **claude-5
vs factory n=19, 8/0, p=0.008** · claude-4.8 vs factory n=19, 8/1, p=0.039 ·
**claude-4.8 vs claude-5 n=19, 1/2, p=1.000**.

**The headline, in the words Rule 1 of the pre-registration committed to before
the data existed: our lift comes from using a competent agent loop, not from the
chain.** 37% vs 44% on identical weights, prompt and tools, p=0.625.

What the sweep establishes:

1. **No measurable chain lift** (above). At MDE ≈ ±38 pp, −7 pp is noise: this is
   "no measurable lift", **not** "the chain hurts". Do not let any doc imply harm
   was measured.
2. **The lift is TOOLING, not orchestration.** `openhands` 44% vs `bare` 6%,
   p=0.031 — the only significant result among the three DeepSeek arms. The
   retracted "+58 pp scaffold lift" was measuring editor-and-tool-calling versus
   none. Separating that from the chain is exactly why the `openhands` arm was
   mandatory.
3. **Cost moves the wrong way.** $5.13 per resolved instance for the chain vs
   $2.20 for one agent — **2.3× for no measurable gain** — plus 2.1× the fresh
   input tokens (14.3 M vs 6.8 M) and 2.8× the median wall clock.
4. **Claude Code is ~2× the factory** (79% vs 37%, p=0.008) but varies harness
   **and** model at once. Reference point, never a scaffold deficit. That caveat
   travels with the number.
5. **The contamination probe came back CLEAN** — the single most valuable result
   here. `claude-opus-4-8` (cutoff Jan 2026) 74% vs `claude-opus-5` (cutoff May
   2026) 79%, same harness, p=1.000, on a manifest where **19/19** instances
   predate opus-5's cutoff. Memorization is not carrying Claude's score. This
   *strengthens* the Claude reference and closes 2.1's opus-4-8 hedge.
6. **Two caveats that cut against the factory.** (a) `openhands` lost 3 rows to
   Azure `DeepSeek-V4-Pro` 429s and **2 of the 3 had already produced patches the
   oracle RESOLVES** — counted, it is 9/19 = 47% and the gap widens; there is no
   retry on a provider 429 and the lost row records `cost_usd: 0.0`. (b) 7/19 is
   *exactly* the matched-weights ceiling the 2026-08-03 retraction derived
   independently by subtracting hard-tier-assisted resolves from 11/19. Two
   routes, same number.
7. **Integrity.** One genuine violation: `bare` on
   `hiero-ledger__hiero-sdk-python-1914_interface` ran
   `curl -s https://raw.githubusercontent.com/…/account_info.py`, the upstream
   source of the file under test — published invalid and excluded, not re-rolled.
   Zero path-based oracle probes anywhere. The 46 in-flight audit failures the
   sweep logged were the pre-#227 detector matching hostnames the arms merely
   *read*; all 95 rows were re-audited under the fixed detector, uniformly, with
   no arm re-run.
8. **`bare` has consumed its one repaired run.** It genuinely iterates now — 727
   model calls, 16 of 18 valid rows budget-exhausted, against a mean of 9.2 steps
   and zero cap hits before — and still reaches 6%. Per the pre-registration's
   pre-committed cap, no further debugging: keeping or deleting the arm is an
   operator decision, and it anchors no headline either way.
9. **The review loop is no longer inert.** Reviewer cycles `0×7, 1×9, 2×2, 3×1`
   across the 19 factory rows, versus 0 on every row in the n=6 sweeps. It
   engages, and the resolve rate does not move. Chain-verdict precision is
   6/15 = 40% [16%, 68%], recall 6/7 = 86% [42%, 100%].

Phase 2 adjustments this implies:

- **`openhands` is mandatory in every sweep from now on.** It is the only pair
  that holds the model fixed and varies the harness, so it is the only arm that
  can measure the product. A factory number published without it measures the
  model.
- **k ≥ 3 is now the top priority**, ahead of growing the manifest. The two arms
  that matter differ by 7 pp and the MDE is ±38 pp — n=19 k=1 physically cannot
  answer the only question the roadmap turns on.
- **Keep both Claude arms; the probe came back clean** (see 5). 2.1's "pick (a)
  opus-4-8 or (b) label opus-5 an upper bound" is settled: run both, and the
  absolute rate is publishable for the Claude arms. Their marginal cost is
  subscription-billed and near zero.
- Build the 120-task manifest from SWE-rebench monthly splits, NOT SWE-bench Pro
  (frozen — see STATUS).
- The DeepSeek arms still carry a contamination confound: `deepseek-v4-pro`
  publishes no cutoff and 15 of 19 instances sit inside its release-date bound.
  The two-stratum design in 2.1 is still required for those arms.
- Known harness debts, still open: **no retry on a provider 429** (a 4-worker
  sweep silently drops runs and records them at $0.00); `sweep-<arm>.json`'s
  aggregate counters are in-flight snapshots that contradict their own `results`
  rows and `results.md`; the archive of the 04-18 report carries only
  `sweep-bare.json` and `sweep-factory.json`, not all five; systemd-unit sweeps
  need PATH set explicitly (uv, claude).

### 1.6 — Arm parity and integrity repair, then one clean n=19 re-run — **DONE 2026-08-04**  **[OPERATOR-PR-ONLY]**

**Gate cleared.** The five-arm re-run happened, `report --check` is green against
the committed archive, and the result is published above and in `STATUS.md`.
Actual cost of the sweep: **$59.25** Azure price-table estimate (factory $35.94 +
openhands $15.37 + bare $7.94) plus $57.92 CLI-reported against the Anthropic
subscription. Estimate was ~$50 Azure — close.

- [x] **A — integrity hardening.** Every arm's live tree moved under a flat
      `SWEBENCH_WORK_ROOT` keyed by (instance, arm, model), so no arm is a `..`
      away from `oracle.json.z` or a sibling's `grade.log`; only finished
      artifacts are copied back. Per-node `PASSED` grading replaced
      exit-code-only grading: `-rpfEsxX` (that is `-rA` minus `P`, so
      arm-authored code cannot echo a forged `PASSED <id>` into the region the
      parser reads) and every declared `FAIL_TO_PASS` and `PASS_TO_PASS` id must
      have a `PASSED` node and no `FAILED`/`ERROR` node. `_DIFF_HEADER` fails
      CLOSED. `audit.json` now carries `prediction_sha256`, `base_commit`,
      `stripped_test_paths`, `refused_paths`, `trajectories_scanned`,
      `trails_scanned`. **Result: zero path-based oracle probes in the sweep**,
      versus 4 audit-invalidated factory rows before.
- [x] **B — arm parity.** One `_BASE_TESTS_NOTE`, byte-identical, reaches
      `_STORY_TEMPLATE` (factory/openhands/claude) and `_BARE_TASK` (bare), so
      "matched prompt" is now true rather than asserted. Bare got the
      test-writing instruction, an empty-diff DONE guard, a real message list,
      the parsed command echoed into history, bash-fence tolerance,
      `TimeoutExpired` handling and persisted observations. **The `openhands` arm
      exists and produced the sweep's most important number.** Every arm records
      `model`, `models_used`, `model_calls`, `model_escalated_calls` — which is
      how the factory's 6 hard-tier `gpt-5.3-codex` calls are visible in Table 1
      instead of hidden.
- [x] **C — reporting honesty, mostly.** `--from-archive` prints and never
      overwrites; `--check` diffs and exits non-zero on drift (verified green);
      `report-meta.json` persists `foreign`/`refused`; one budget rule for every
      arm (a cap hit is a counted, flagged attempt); `fresh in` and `cache read`
      are separate columns; cost source is labelled per arm; `attempt` column and
      a "Discarded runs" section; `n/a (arm has no chain verdict)` instead of a
      division artifact; `pass_to_pass_count == 0` flagged;
      `estimate_instance_cost` filtered by `manifest_sha256`.
      **Not closed — see G:** the sweep and the report still disagree, now
      *within one file*.
- [x] **D0 — probe before you sweep.** Stubbed-model plumbing probe
      (`--probe-plumbing`) for every non-factory arm plus one paid single-instance
      run per new arm. It earned its keep: the probes are why the sweep did not
      re-discover a six-step-giveup arm for $50.
- [x] **D — one clean re-run, n=19, k=1, five arms**, one sweep, no re-rolls. The
      one audit-invalid row (`bare` / `hiero…-1914_interface`, a real `curl` of
      upstream source) is published as invalid. `attempt` is 1 on all 95 rows.
- [x] **E — caveats are structural, not prose.** Per-arm Clopper-Pearson CIs,
      paired McNemar exact per pair with `harness varies?` / `model varies?`
      columns, the ±38 pp MDE stated, the per-row model mix, and the subset
      relation: **the factory's 7 passes are still a strict subset of
      `claude-opus-5`'s 15** (only-B = 0). Against `claude-opus-4-8` the factory
      wins exactly one instance, `hkuds__openharness-217`.
- [x] **F — contamination margin per arm, printed.** Table 2 carries
      `margin_days` per model bound and Table 4 names the bound TYPE.
      `deepseek-v4-pro` remains `release-date-proxy` (no published cutoff; 15 of
      19 instances inside it). **The Claude half of this question is now
      answered** — the opus-4.8/opus-5 pair scored 74% vs 79%, p=1.000, so
      memorization is not carrying the reference arm. See Phase 1 outcome #5.
- [ ] **G — the two debts D–F did not close.** Both are reporting, not
      measurement; neither moves a published number, and both would mislead the
      next reader.
      - **No retry on a provider 429.** `openhands` lost 3 of 19 rows to Azure
        `DeepSeek-V4-Pro` `RateLimitError` under `--workers 4`. Two of the three
        had already produced oracle-RESOLVING patches, so the loss cost the arm
        ~3 pp *against its own favour*. Worse, a lost row records
        `cost_usd: 0.0`, which reads as free rather than as missing. Retry with
        backoff, or fail the sweep loudly — never both silently.
      - **`sweep-<arm>.json` aggregates contradict their own rows.** The
        `resolved` / `audited_valid` / `audit_failed` counters are in-flight
        snapshots taken before grading and before the #227 detector fix, so
        `sweep-factory.json` says `resolved: 2, audit_failed: 13` while its own
        `results` list says 7 resolved and the archived `audit.json` files say
        19 ok / 0 invalid. This is the same "the sweep and the report disagree"
        class C was meant to kill, one level deeper. Either recompute the
        aggregates from the rows at write time or delete them.
      - Minor, same family: the 04-18 archive carries only `sweep-bare.json` and
        `sweep-factory.json`, not all five, so three arms' sweep summaries are
        committed only at `bench/swebench/sweep-<arm>.json` and not inside the
        archive of record.

## Phase 2 — the trustworthy benchmark

**Effort ~2 weeks. Cost ~$510.** **[OPERATOR-PR-ONLY throughout — `bench/**`]**

**Re-pointed 2026-08-04 by the 1.6 result.** Three things changed:

1. **`openhands` is a mandatory arm in every sweep.** It is the only pair that
   holds the model fixed and varies the harness, so it is the only arm that can
   measure the product. Any sweep without it publishes a number about the model.
2. **k ≥ 3 is the top priority, ahead of growing the manifest.** The two arms the
   roadmap turns on differ by 7 pp against an MDE of ±38 pp. More instances at
   k=1 buys less than repetitions do, because instance-level variance is what is
   swamping the signal. 2.3 already commits to `pass^k`; make it the first thing
   built, not the last.
3. **The contamination question is CLOSED for the Claude arms.** The opus-4.8 /
   opus-5 probe returned 74% vs 79%, p=1.000, on a manifest where 19/19 instances
   predate opus-5's cutoff. Keep both Claude arms, publish their absolute rates,
   and stop hedging them. The DeepSeek arms are a different matter — see the
   two-stratum design below, which is still required for those.

- [ ] 120 tasks, **frozen before the first run**: a published RNG seed, a
      hash-pinned manifest (task id → repo → base SHA → problem statement
      hash), committed and tagged.
- [ ] **k ≥ 3 per instance per arm** (moved here from 2.3 because it now gates
      everything). Report `pass^k` and `resolve@1` separately. Measured
      variance to budget against: 0/10 oracle flips over 10 same-condition
      factory replications (95% upper bound on per-instance flip probability
      25.9%, i.e. ±3 instances at n=19), 1/10 chain-verdict flips, and cost
      varying up to 2.6× on the same instance.
- [ ] ~~Plus 30 post-cutoff instances from SWE-bench-Live as a contamination
      control.~~ **NOT EXECUTABLE — measured 2026-08-03.**
      `SWE-bench-Live/SWE-bench-Live` was last modified 2025-09-18, its newest
      instance is `created_at` **2025-09-02**, and it holds **0 rows after
      2025-10-01**. It cannot clear even the *2025-08-31* OpenAI cutoff by more
      than 3 instances. Replace with the two-stratum design below.
- [ ] **Two-stratum design (this is the contamination control that exists).**
      Measured supply in `nebius/SWE-rebench-leaderboard` (860 test rows) by
      `created_at`: `>2026-01-01` = 215 (this is exactly the current manifest's
      `pool_size`), `>2026-02-01` = **167**, `>2026-04-24` = **30**,
      `>2026-06-01` = **0**; corpus max is **2026-05-12**. So pin:
      - **main stratum: 120 tasks from `created_at > 2026-02-01`** — clears both
        OpenAI deployments' published 2025-08-31 cutoff with 167 available.
      - **high-margin stratum: the 30 tasks from `created_at > 2026-04-24`** —
        additionally clears `deepseek-v4-pro`'s release-date bound (its cutoff is
        published nowhere; see below). Report every arm **per stratum**. A rate
        that holds across strata says memorization is not carrying it; a rate
        that drops on the high-margin stratum says it is. At n=30 that resolves a
        large effect (~±9 pp at 50%), not a subtle one.
- [ ] **Filter on `created_at`, never on split label.** SWE-rebench's `2026_03`
      split (110 rows) is exactly `created_at > 2026-03-01` — it aggregates
      March, April *and* May PRs.
- [ ] **The suite of record is SWE-rebench, and it is healthy.**
      `nebius/SWE-rebench-leaderboard`, last modified 2026-07-28: 860
      execution-validated Python instances, docker image and oracle shipped
      in-row, monthly splits through 2026-05-12. Every instance the factory has
      ever been graded on comes from it. SWE-bench-Live was only ever a *bonus*
      freshness control layered on top; losing it costs the add-on, not the
      benchmark. Alternatives considered and rejected: **SWE-bench Verified** (the
      comparability standard, but 2023 instances and the most contaminated corpus
      in the field — use only if a public-leaderboard-comparable number is the
      goal), **SWE-bench Pro** (frozen after OpenAI's ~30%-broken audit),
      **SWE-rebench V2** (nothing after 2026-01), **MultiLang** (no Python).
- [ ] **The reference arm is the Claude Code CLI, on a subscription — never an
      API or Azure route.** Verified: `claude -p <prompt> --model <id>
      --max-turns 60 --output-format stream-json`, `apiKeySource: "none"`, cwd =
      the instance clone. `--model` is a flag on that same binary, so "a second
      claude arm" means running Claude Code twice with different `--model`
      values. `claude --model claude-opus-4-8` was confirmed working on this
      machine 2026-08-03. Do not read the cutoff table below as a provider
      choice; it is only about which Claude model the CLI is pinned to.
- [x] **Keep both Claude arms — the probe came back clean.** *Settled 2026-08-04;
      this was the hedge, and it is no longer needed.* No positive-margin manifest
      for `claude-opus-5` exists (cutoff May 2026 per the Opus 5 system card §1.1;
      the freshest public instance in the family is 2026-05-12, so 19/19 of the
      current manifest sits inside its window). The plan offered two ways out —
      (a) run the reference arm on `claude-opus-4-8` instead, or (b) keep opus-5
      and label it an upper bound — and recommended running both as the probe.
      **Both ran. `claude-opus-4-8` (published cutoff Jan 2026) scored 14/19 = 74%
      against `claude-opus-5`'s 15/19 = 79%, same harness, same flags, McNemar
      exact p=1.000.** Memorization is not carrying the reference arm's score, so
      neither hedge applies: run both, publish both absolute rates. The second arm
      is subscription-billed and near-free, and the pair is the cheapest
      contamination control in the suite — keep it in every sweep.
- [ ] **Record the bound, not just the date.** `deepseek-v4-pro` publishes **no**
      cutoff — absent from the model card and from arXiv 2606.19348 (full text
      grepped) — so its only defensible bound is its **release date,
      2026-04-24**, and 15 of the current 19 instances are inside it. Azure's
      catalog metadata is *not* a source: Microsoft published Oct 2024 for
      GPT-5.2 whose real cutoff is 2025-08-31 (MS Q&A 5667726). Print, per row,
      `margin_days` against each arm's newest model **and** which bound was used
      (`published-cutoff` vs `release-date-proxy`).
- [ ] **State what a positive margin does not buy.** `created_at` is the
      *merge-PR* creation date; the issue text, its pre-solution comments (the
      dataset ships `hints_text`) and the repository wholesale all predate it.
      arXiv 2506.12286 shows models name the file to edit from repo name + issue
      text alone far above their accuracy on equally-popular non-benchmark repos;
      arXiv 2410.06992 found 32.67% of SWE-bench issues carry the solution in the
      issue or comments and 31.08% of passing patches pass only because the tests
      are weak — together dropping SWE-agent+GPT-4 from 12.47% to 3.97%. A date
      filter touches neither. This is why the strata are a *measurement* and the
      date is only a *bound*.
- [ ] **If you want a genuinely post-cutoff suite, the options are wait or
      build.** Nebius's cadence is ~40–55 validated instances/month with a
      ~10–12 week publication lag, so a 120-row `>2026-05-31` pool should exist
      around **Oct–Nov 2026**. Minting your own (SWE-Bench++ style, arXiv
      2512.17419) means owning docker images and oracle extraction — a multi-week
      build, and `swebench_harness_selftest` is the reason to respect that: the
      gold-patch control caught three harness bugs that each faked a 0% score.
- [ ] **Do not reuse the July task pool.** All six directions behind bench
      tasks t1–t6 (`023`–`028`) are now `closed` — the factory has shipped
      them, so they are contaminated. The held-out pool is the **45
      `pm-validated`** directions under `apps/sacrifice/directions/` (76 total,
      31 closed).
- **Done looks like:** `bench/manifest-<date>.yaml` committed with a manifest
  hash, and a `PRE-REGISTRATION.md` stating hypotheses and the analysis plan
  *before* any run.

### 2.2 — Five arms, not three — **the arm list is settled, `_ARMS` is the registry**

Superseding the original three-arm sketch. 1.6 proved that a three-arm design
(factory / minimal / Claude) cannot attribute its own headline, because the
minimal arm varies the chain and the tool interface at once.

- [ ] **`factory`**, on its own routes. The product.
- [ ] **`openhands` — MANDATORY.** ONE OpenHands agent on the *same* dev
      deployment, same SDK, same toolset, same prompt, no chain. `factory −
      openhands` is the only comparison in the suite that measures the chain.
      Never publish a factory number without it.
- [ ] **`bare`** — hand-rolled text loop, no tool-calling API. Its ONE repaired
      run is spent (1.6 D) and it reads 6%. It is a ~$8 sanity canary and the only
      row comparable to the leaderboard convention; it anchors nothing. Keeping it
      is an operator decision.
- [ ] **`claude-5`** — Claude Code CLI on `claude-opus-5`, frontier reference.
      **Subscription, never API/Azure** — 1.6 ran 38 CLI rows on a subscription
      with zero usage-window losses, so July's "API billing removes that confound"
      (`bench/CAMPAIGN-2026-07-17.md:33,51`) is no longer a reason to switch.
- [ ] **`claude-4.8`** — the SAME CLI on `claude-opus-4-8`. Contamination probe.
      Near-free and it already paid for itself once (Phase 1 outcome #5).

Reporting rule, non-negotiable: **an arm is a (harness, model set) pair**, and a
comparison that varies both halves — every `factory` vs `claude-*` pair — is a
reference point, not a scaffold measurement.

### 2.3 — Statistics stated up front

- [ ] Report **resolve@1**, **pass^k**, **paired bootstrap CIs**, and exact
      **McNemar** on every pair, each labelled with what it holds constant.
- [ ] **k ≥ 3 is the binding constraint, not n.** See 2.1. 1.6 ran n=19 k=1 at an
      MDE of ±38 pp and measured the product delta at −7 pp: the design could not
      have answered the question at any outcome.
- [ ] **State the MDE before running: ±13pp at n=120.** Anything smaller than
      that is noise, and saying so in advance is what makes the result
      trustworthy. `SOTA-RESEARCH-2026-07.md:34` notes DeepSeek-Coder-V2 went
      15.9%@1 → 56%@250 on SWE-bench Lite — sampling budget dominates, so
      pass^k with a fixed k is mandatory, not optional.

---

## Phase 3 — structural wins (parallel; any time after Phase 0)

### 3.1 — Port Hermes `fuzzy_match.py` to replace strict `git apply`

- [ ] **Source (verified):** `/home/k/hermes-agent/tools/fuzzy_match.py` —
      **967 lines**, imports only `re`, `typing`, `difflib.SequenceMatcher`
      (`:32-34`). License: **MIT**, `/home/k/hermes-agent/LICENSE`
      ("Copyright (c) 2025 Nous Research"). Zero third-party deps — safe to
      vendor.
- [ ] **Targets:** `factory/chain/factory_improver_apply.py:490` and
      `factory/manager/apply.py:958`. Both run
      `["git", "apply", "--whitespace=nowarn", tmp.name]` — strict, no `-3`,
      no fuzz.
- **⚠ Expected payoff is much smaller than it looks.** Of the 179 improver
  apply failures, **158 were `dirty_working_tree`, which is already fixed**
  (path-scoped checks landed 2026-07-24 at
  `factory/manager/apply.py:882-897` and
  `factory/chain/factory_improver_apply.py:418-436`). Fuzzy matching addresses
  only the **21** genuine patch-application failures (16 `corrupt patch`, 5
  `patch failed`). Cheap intermediate step worth trying first: add `-3`
  (`--3way`) to both `git apply` calls and re-measure before porting 967 lines.
  `SOTA-RESEARCH-2026-07.md:164` reports 69.1% → <1.5% apply-failure rates from
  changing diff transport, so the ceiling is real — just measure the floor first.
- **[OPERATOR-PR-ONLY]** — both halves. `factory/manager/apply.py:67-69`
  forbids self-edits to `factory/manager/**` *and* explicitly to
  `factory/chain/factory_improver_apply.py`.
- **Done looks like:** a replay of the 21 failed patches against their
  historical base commits shows a measured improvement; report the exact
  before/after count.
- **Effort:** 1 h for the `-3` experiment; ~1 day for the full port.

### 3.2 — Dev runs lint/typecheck/format locally before handing to review

- [ ] **Current state (verified):**
      `factory/chain/handlers.py:3592` `_autoformat_changed_py_before_pr` runs
      `ruff check --fix --select F401` (branch-added imports only), then
      `ruff check --fix --select I` + `ruff format`, gated on the repo actually
      using ruff (`:3621-3647`). That is **format-only**. There is:
      - **no `ruff check` (full ruleset) gate**,
      - **no typecheck (`mypy`) step at all**,
      - **no lint gate in `factory/chain/gates/`** — the directory holds only
        `acceptance_verified.py`, `canonical_paths_only.py`, `docs_current.py`,
        `smoke_green.py`, `tests_green.py`, `tests_meaningful.py`.
- [ ] **Dead columns to reuse or drop:** the `stories` table has
      `lint_passed`, `format_passed`, `types_passed`, `coverage_passed` — and a
      repo-wide grep finds **zero references to any of them anywhere in
      `factory/**`**. They are not `StoryRecord` fields and are not in
      `_MIGRATION_COLUMNS` (`factory/chain/handlers.py:195+`). Either wire them
      as the persistence for this step, or drop them. Do not leave four
      write-never columns sitting next to the `smoke_passed` bug from 0.5.
- **What:** after the dev sandbox reaches green and before the review handoff,
  run the app's configured lint + typecheck commands in the worktree, record
  the result, and feed failures back to the dev as findings (reusing the
  `reviewer_result_json` findings-dict path that `_handle_ci_failure` already
  uses — `auto_merge.py:1777-1806`). Cap the loop.
- **Done looks like:** a story with a deliberate `mypy` error never reaches
  review; the failure shows up in `factory trace <id>` as a dev-visible finding.
- **Effort:** ~1 day. Chain code. Cap the new loop (guardrail).

### 3.3 — Typed block kinds + recurrence counter reset only on merge

- [ ] **Source (verified):** `/home/k/hermes-agent/hermes_cli/kanban_db.py`
      `:104-134` defines
      `VALID_BLOCK_KINDS = {"dependency", "needs_input", "capability",
      "transient"}` and `BLOCK_RECURRENCE_LIMIT = 2`, with the rationale that
      an undifferentiated `blocked` bucket produces a cron-unblocks →
      worker-re-blocks retry storm. `:5847-5856` is the load-bearing half: the
      unblock path **deliberately does not reset** `block_recurrences` or
      `block_kind` — "resetting the recurrence counter on unblock is exactly
      the amnesia that let [the] loop run unbounded"; it resets only on
      successful completion.
- [ ] **Target:** `factory/chain/state_machine.py` (the `BLOCKED_*` states) and
      the recovery paths in `factory/manager/recovery.py`
      **[OPERATOR-PR-ONLY for the recovery half]**.
- **Why this matters here:** this repo's #2 named failure pattern is
  *detect-without-remediate*, and its recorded history includes
  `blocked_ci_unresolved` being terminal with no path back. A typed block kind
  routes `dependency` blocks back to the ready queue automatically instead of
  parking them for a human.
- **Done looks like:** every `BLOCKED_*` transition records a typed kind; the
  recurrence counter survives an unblock and resets only on merge.
- **Effort:** ~1 day.

### 3.4 — Snapshot `state/factory.db` before each tick

- [ ] **Verified gap:** no snapshot/backup mechanism exists anywhere in
      `factory/**`. `state/factory.db.bak-1784662396` is a one-off manual copy.
      The staging twin (`factory/manager/staging.py`) guards **source only**.
- [ ] **Files:** `factory/chain/orchestrator.py` (tick entry), or the
      `factory tick` CLI wrapper in `factory/cli.py`.
- **What:** before the tick's first write, `sqlite3` **backup API** (not
  `shutil.copy` — the manager daemon writes concurrently) into
  `state/db-snapshots/factory-<ISO>.db`, keeping the last N (10 is plenty).
- **Why:** a prior session lost a whole run to 6 poisoned invalid-enum `closed`
  rows that failed every tick, and there was no clean rollback point. Cheap
  insurance.
- **Done looks like:** `ls state/db-snapshots/` shows a rolling window after a
  few ticks; restoring one produces a DB that `factory queue` reads cleanly.
- **Effort:** ~2 h. Add `state/db-snapshots/` to `state/.gitignore` coverage
  (`state/**` is already gitignored — confirm, don't assume).

### 3.5 — Make `software-factory-copy` private  **[OPERATOR ACTION]**

- [ ] **Verified:** `gh repo view xvanov/software-factory-copy --json visibility`
      → `PUBLIC`. It is the staging twin
      (`factory/manager/staging.py:72`) and receives **every candidate self-edit
      diff** on a staging branch before promotion — including diffs the staging
      gate later rejects (3 of 20 so far).
- **Command:** `gh repo edit xvanov/software-factory-copy --visibility private
  --accept-visibility-change-consequences`
- **Then verify the twin still works:** the staging flow clones over SSH
  (`git@github.com:…`), so a private repo is fine provided the deploy key /
  SSH identity used by the manager has access. **Run one staging validation
  end-to-end after flipping it** — `staging.py` failing closed would silently
  block every self-edit.
- **Effort:** 5 min + one validation cycle.

### 3.6 — Ratchet the package-wide `mypy` count, per file

- [ ] **Verified gap:** `.github/workflows/test.yml:145-154` runs two mypy
      steps. `mypy factory/chain/gates/` is a real zero-tolerance gate and is
      currently clean — **leave it alone**. The package-wide step pipes to
      `|| true`, counts with `grep -c "error:"`, and emits a `::warning::`.
      Advisory, no baseline, no comparison. No test asserts a count.
- [ ] **The drift is real and larger than the docs claim.** The only number in
      the repo is `test.yml:143-144` ("~85 pre-existing findings"). Measured on
      this tree: `uv run mypy factory/` → **99 errors in 29 files**.
      `CLAUDE.md:75` says only "compare against `origin/main`" — a manual
      instruction, which is precisely how it drifted.
- **What:** commit `mypy-baseline.json` mapping **file → error count**. Not a
  single integer — a scalar lets you add three errors in one file, delete three
  in another, and stay green. CI fails when any file exceeds its entry. Count
  from `--output json` or the `Found N errors` summary line, **not**
  `grep -c "error:"`, which counts lines containing the substring and can be
  inflated by mypy's own code excerpts.
- **Ship standalone.** It blocks unrelated PRs the moment it lands, so it must
  not ride along with type-debt work. mypy is pinned in `uv.lock` and CI runs
  `uv sync --all-extras`, so drift is bounded — but any lockfile bump must
  re-baseline in the same PR or main goes red. Say that in the job.
- **Also fix the doc:** `CLAUDE.md:75` should name the baseline file instead of
  "compare against `origin/main`".
- **Done looks like:** a PR adding one deliberate mypy error to an existing file
  fails CI; a PR that fixes one and lowers the baseline passes.
- **Effort:** ~1 h.

### 3.7 — Isolate gate exceptions, and make a scan error GLOBALLY blocking

- [ ] **Verified:** `factory/chain/gates/evaluator.py:188-197` calls
      `mod.evaluate(...)` with no `try`. Its docstring (`:175-176`) promises
      "failure of one gate does not short-circuit the others" — true for a
      *returned* failure, false for a *raise*.
- [ ] **What actually happens today — checked, do not re-diagnose.** Both
      orchestrator call sites already catch (`orchestrator.py:2591`, `:3117`),
      so the tick does **not** crash and the merge is **not** waved through
      (`_record_merge_action` is never reached). `summary.errors` non-empty →
      `factory tick` exits 1. It is already fail-safe by accident. The real
      costs are that one raise aborts merge evaluation for **every remaining
      fixture** on that tick, and that `factory/cli.py:2480`
      (`factory auto-merge`) is unwrapped. **Zero gate raises have occurred in
      production** (441 ticks at `errors=0`; the 3 non-zero ticks were worktree
      errors from the story loop).
- **⚠ The naive fix is a fail-OPEN regression.** `missing_labels` is computed
  only over `required_gate_labels(...)` (`auto_merge.py:948-954`). A raise in a
  **non-required** gate (`smoke-green` on either app; `acceptance-verified` when
  not expected) that becomes a non-required blocking `GateResult` is filtered
  out and **the merge proceeds** — strictly weaker than today. Therefore:
  1. `scan_error` results are **globally blocking**, evaluated alongside
     `missing_labels` and **not** filtered through `required_gate_labels`.
  2. Keep it loud: append to `summary.errors` so the tick still exits non-zero.
     Do not trade a loud abort for a silent block that re-evaluates every five
     minutes forever — that is failure pattern #2, and `blocked_ci_unresolved`
     already burned us exactly that way.
  3. Wrap `cli.py:2480` too.
- **Adopt the precedence rule while you are there:** can't-run > found-something
  > clean.
- **Done looks like:** force each of the 6 gates to raise in turn; each time the
  merge is blocked, the other 5 still report, and the tick exits non-zero.
- **Effort:** ~2 h. This is robustness, **not** a closed failure class. Sell it
  as such.

### 3.8 — Fix or delete the dormant ablation path in `tests-meaningful`

- [ ] **Context:** `factory/chain/gates/tests_meaningful.py:63-138` implements
      real mutation testing (no-op a symbol, re-run the suite, fail if it stays
      green). It has **never run** — `mutation_testing: false` in all three app
      configs. But `tests-meaningful` **is** in `LOOP4_REQUIRED_GATE_LABELS`, so
      that flag is the only thing between this code and every merge.
- [ ] **Do not simply flip the flag.** Four independent verified defects:
  1. **It ablates the wrong symbols.** `_changed_public_symbols` (`:140-172`)
     parses each changed file *whole* and returns every public symbol, not the
     ones the diff touched; with `_MAX_ABLATION_SYMBOLS = 5` and a
     `(path, lineno)` sort it takes the top five of the alphabetically-first
     file. Over the last 40 commits: median 21 candidates, 77% hit the cap. For
     `e13d98e0` the five chosen symbols have **zero overlap** with the four the
     commit changed.
  2. **Fail-OPEN on infrastructure failure.** `_run_pytest` returns `False` on a
     600 s timeout or `FileNotFoundError`, and `survived == False` is read as
     "exercised → good" (`:104-107`). There is no green-baseline run before
     mutating, so an already-red suite, a flaky red, or a failed `uv sync` in
     the worktree certifies coverage that was never measured. Violates
     fail-SAFE.
  3. **It mutates the live story worktree.** `repo_root` is the
     `state/worktrees/` checkout the chain later pushes from, and
     `_mutate_source` round-trips the whole file through `ast.unparse` — on
     `handlers.py` that is 4,804 → 2,113 lines with **all 756 comments
     stripped**. Restore sits in a `finally`, which does not run on `SIGKILL`,
     and the tick unit has `TimeoutStartSec=3h`.
  4. **It fails in dry-run, which is the default.** `:68-75` returns
     `passed=False` when `dry_run`, and `factory auto-merge` defaults to
     `--dry-run` (`cli.py:2464`). Worse, `auto_merge.py:928-942` writes a
     `merge_gates_failed` story event **unconditionally, including dry-run** —
     so flipping the flag manufactures false gate-failure events into the exact
     substrate L1→L2→L3 escalate on.
- **Decide:** delete the ablation branch (leaving the static slop detector,
  which is the layer that actually runs), or rewrite it — diff-hunk-scoped
  symbol selection, a green baseline with non-green ⇒ `skipped`, timeout/infra
  distinguished from a real red, mutation in a throwaway copy, per-`(head_sha,
  symbol)` caching, and **advisory until measured**. Deleting is the cheaper
  honest option; `evaluator.py:18-29` already sets the precedent that a gate
  detached from a real check is worse than no gate.
- **Effort:** 30 min to delete, ~2 days to rewrite. Cost context if you rewrite:
  the full factory suite is **5m36s** warm, so five ablations is ~28 min per
  merge evaluation, re-run every tick per open PR.

### 3.9 — Wire or drop `gates_failed_json`

- [ ] **Verified dead surface:** #195 added `MergeAction.gates_failed` and the
      `gates_failed_json` column (`auto_merge.py:126`, `:200`, `:234`) plus the
      `merge_gates_failed` story event (`:933`). Repo-wide there is **one writer
      and zero readers** for both. The diagnosis is durable and reaches a human
      via `factory trace` — and nothing else.
- **Pick one:** feed `gates_failed` into the dev re-dispatch findings path the
  way `_handle_ci_failure` already does (`auto_merge.py:1777-1806`) — **and cap
  that loop** — or drop the column. Do not leave it sitting beside the four
  write-never `stories` columns from 3.2.
- **Effort:** ~2 h either way. Same class as 3.2; do them in one PR.

---

## Phase 4 — decide the FMS on evidence

### 4.1 — Bring units up, watch one cycle, measure L4 yield

- [ ] **Start:** `uv run factory on`, then confirm
      `systemctl --user status factory-manager.service factory-tick@sacrifice.timer`.
      Check `Result=` and `errors=` **across two runs** — "services up" is not
      "sustains".
- [ ] **Watch one full L1→L4 cycle.** L1 fires every 60 s.
- [ ] **Measure:** re-read `state/.manager_apply_history.json` and count
      entries with a non-null `pr_number`. The baseline is **163 attempts, 0
      PRs, newest 20260723**.
- [ ] **Decision rule, pre-committed:** if after one full cycle *and* one
      genuine concern reaching L4 the yield is still **0 PRs**, delete the L4
      tier. Keep `factory/manager/recovery.py` (the auto-fix layer for known
      operational faults — that one demonstrably works) and keep
      `fms_yield.py` as the detector. **[OPERATOR-PR-ONLY]**
- **The cost case for deleting:** the manager has consumed **$1,028.58 = 52.0%
  of all-time LLM spend** ($972.23 of it `manager_watcher` alone, 44,127 runs at
  a 60 s cadence) for **zero shipped PRs**. In July it was $371.60 of $588.78 —
  deleting it takes per-story cost from **$7.85 to $2.90**. Also note 165 L3
  proposals collapse to **37 distinct concern classes (78% redundant)** and 107
  carry `escalate_to_human: true`: the tier is mostly re-reporting the same
  handful of problems to a human.
- **Do not delete before measuring.** The wiring bugs were fixed in PR #113
  (2026-07-24) and the newest apply attempt predates parts of that work, so the
  tier has arguably never been run in its fixed form. One honest cycle first.
- **Effort:** ~half a day of watching, plus the deletion PR if the rule trips.

---

## Phase 5 — later (do not start before Phase 2 reports)

### 5.1 — GEPA on the reviewer against the PR replay corpus

- [ ] Corpus: **118 merged PRs** plus their review history
      (`stories.reviewer_history_json`, `review_events` table,
      `state/events/chain_steps.ndjson`).
- [ ] ~150 rollouts ≈ **$6** at current reviewer rates
      (`reviewer` = `azure/gpt-5.3-codex`, 936 runs / $25.03 all-time ⇒ ~$0.027
      per call).
- [ ] **Blocked on 0.1**: prompt-optimization needs full prompt bodies, which do
      not exist today (only 16-char hashes). Do not attempt this before 0.1
      ships and has accumulated a corpus.

### 5.2 — Evaluate migrating merge gates to GitHub Actions + Projects v2

- [ ] Today the gates run in-process (`factory/chain/gates/evaluator.py`,
      `evaluate_all_gates`) and the board is `state/factory.db`. Moving gates to
      required GH checks would make `proxy ≠ real` structurally impossible for
      the merge decision (GitHub becomes the only source of truth, which
      `CLAUDE.md` already declares it to be for merge reality).
- [ ] **Evaluate, don't commit.** Cost: loses the local dry-run fast path and
      couples every gate to Actions minutes. Write the trade-off up before
      building anything.

### 5.3 — Extend the persona contract-collision validator

- [ ] **Verified:** `factory/personas/validator.py:59-62` `_ENUM_CONTRACTS`
      covers only `scope` and `chain_kind`. The check itself already runs in CI
      (`tests/test_persona_loader.py:60`, `:296` call `validate_all`).
- **Why this instead of a persona prompt audit:** the story-14 non-convergence
  was caused by a prompt *example literal* colliding with a live contract value.
  `_check_contract_collisions` catches that mechanically; a stylistic trim would
  not have. See "Rejected" below for why the personas are not the bloat they
  look like.
- **What:** extend `_ENUM_CONTRACTS` to every field whose values are enumerated
  in code.
- **Effort:** ~2 h.

---

## Rejected — LifeOS-derived proposals, adversarially reviewed 2026-08-02

A survey of `danielmiessler/LifeOS` (cloned at `/home/k/LifeOS`) produced 11
candidate additions. Three adversarial reviews rejected **nine**. Recorded so
they are not re-proposed. Each entry is the refutation, not the proposal.

1. **`evidence-corroborated` gate** — classify the dev's completion claim,
   corroborate it against the ledger. There is no prose claim in the merge path
   to classify: `runner.py:2107-2108` runs pytest and scans git *itself*, and
   `RunResult.test_run_passed` is the factory's own observation, never the
   model's word. `gates/tests_green.py:69-83` already re-derives the truth at
   merge time and its docstring states that as the design intent. The
   corroborating ledger does not exist — there is **no `sandbox_run` table**,
   `prompt_bodies.ndjson` has **zero production rows** (#193 merged 2026-08-01;
   units stopped since ~07-30), `chain_steps.ndjson` still has zero `retried` /
   `review_cycle` rows, and `runs` carries no diff, file list, or exit code. The
   proposed 118-PR replay corpus is fiction (and the count is 138).
2. **Gate-reason lint** — require a problem *and* a remedy in every failing
   `reason`. Roughly 15 strings across 6 files; "names a remedy" is not
   statically decidable, so any implementation is a keyword heuristic — a proxy
   gate, in the repo whose #1 failure pattern is `proxy ≠ real`. The loop it
   claims to prevent does not exist: nothing reads the string (see 3.9).
3. **"L4 falsify, not L4 apply"** — have the manager emit a red replay fixture
   instead of a diff. The premise is false. Of 163 apply attempts only **58 ever
   carried a patch**, and **53 of those died on `dirty_working_tree`**, an
   environment bug fixed 2026-07-24 — `apply.py:864-869` records exactly this.
   Not one attempt was ever rejected for diff quality; zero reached review. The
   107 escalations are **information** failures (84 are "source bundle
   insufficient"), and a model that cannot see `tick()` cannot write a fixture
   for it either. Run 4.1 instead.
4. **Detector graduation lifecycle** — log-only → counterfactual corpus →
   blocking. Manager detectors are already advisory by construction
   (`factory/manager/detectors/__init__.py:1-6`: "Detectors never make
   decisions"); the only blocking path is `halt.py`, which is L3, not a
   detector. The motivating episode (SM-truncation) was **test pollution** — a
   counterfactual corpus built from those same contaminated streams scores
   FP = 0 and passes the very case it was designed to catch. And no adjudicator
   is specified for up to 190 observations per detector.
5. **Turn on the ablation gate** — superseded by 3.8. The gate is broken four
   ways; the flag flip is not the adoption path.
6. **Property tests in the dev persona** — already ships in a better seam.
   `hypothesis>=6` is a dev dependency, `acceptance_author.md:52-72` authors
   Hypothesis property tests from EARS criteria, and `acceptance.py:101-194`
   injects that automatically. The cited evidence does not support it either:
   `right_place_wrong_fix` is defined at `swebench_adapter.py:1349` as **file
   overlap only**, and `STATUS.md:56-58` reads those failures as
   unstated-convention failures — which #201 already addressed.
7. **"Bitter Pill" audit of the 22 personas** — the trim already happened.
   `27008931` (2026-06-11) cut `dev.md` 177→108 and `reviewer.md` 158→102,
   citing the same story-14 incident this proposal cites. Genuinely cuttable
   today is ~25 lines (`pm.md:242-251`, `sm.md:127-135`, two role preambles) —
   5–8%, not bloat — while several lines that *look* cuttable are measured
   load-bearing (`dev.md:54-64`, 2/2 vs 0/2). The "no regression" guard is
   statistically fake: on a 5-instance precision denominator it fires only at
   0/5, which occurs **32.8%** of the time when nothing changed.
8. **Per-persona A/B with a no-persona arm** — the SWE-bench harness runs
   `allowed = {"dev", "review"}` (`swebench_adapter.py:933`) and seeds the story
   at `SM_DONE`, so **20 of 22 personas never execute**. Of the two reachable,
   the reviewer had `reviewer_cycles = 0` on 5/5 — it modified nothing, so
   ablating it is a guaranteed null result at full cost. `run_bare` is a
   separate agent, not the factory-minus-a-persona
   (`bench/swebench/README.md:126-128` says the arms are not comparable). Cost
   at a detectable n: **$673 at n=33, $2,591 at n=127**, against Phase 2's
   entire $510 budget.
9. **AC-ID stability + falsifier test** — already shipped. `sm.md:46-57`
   mandates `AC<n>.<m>` EARS IDs and 93 of the 139 stories with an
   `sm_result_json` carry them; `acceptance_author.md:37-38` names generated
   tests off those IDs. The guarded failure has never occurred (0 hits across
   326 review/dev blobs). The measurement has no data source: story markdown has
   been gitignored since #181 and the DB stores one `sm_result_json`, not a
   revision series. The falsifier test already exists in triplicate
   (`pm.md:231-236`, `sm.md:55-57`, `acceptance_author.md:39-42`).

**Adopted from the same survey:** 3.6 (mypy ratchet), 3.7 (gate exception
isolation, in inverted form), 5.3 (validator extension). **1.5, 3.8 and 3.9 were
found *by* the review, not proposed to it** — they are the session's real yield.

---

## Corrections to the briefing this plan was written from

Every claim in the source briefing was re-checked. Nine needed correcting; the
rest verified exactly.

1. **Manager spend share — 52.0%, and the in-repo docstring says 53%.**
   `factory/manager/detectors/fms_yield.py:12` reads
   "$1,028 (53% of all factory LLM spend)". Measured today:
   $1,028.58 / $1,976.91 = **52.0%**. The briefing's "52%" matches the current
   measurement; the code literal says 53%. Not a bug — the denominator grew.

2. **L3 `escalate_to_human` — 107 is right, but only in the proposals.**
   107 of the 165 proposal files carry `escalate_to_human: true`. The
   *classification* field in `state/.manager_apply_history.json` records
   **105** `escalate_to_human`. Two proposals set the flag but never reached L4
   classification. Cite whichever you mean.

3. **"37 distinct concern classes" is normalization-dependent.** Raw distinct
   `concern_title` values: **48**. Normalizing story numbers only: **40**.
   Normalizing story numbers *and* dropping the words
   repeat/repeated/continuation/continued/persists/again/still: **37 (78%
   redundant)**. The briefing's 37/78% reproduces exactly under the third
   normalization. State the normalization when you quote it.

4. **`factory audit` estimated share is window-dependent.** Default 7-day
   window: **55.4%** ($25.81). `--days 60`: **33.9%** ($515.90). The briefing's
   "~55%" is correct for the default window only.

5. **"`stories.dev_retries` shows 41" — 41 is a story count, not a retry
   count.** 41 stories have `dev_retries > 0`. Total retries all-time = **71**
   (61 in the last 14 days). The comparison against "zero `retried` rows in
   `chain_steps.ndjson`" holds either way.

6. **`smoke_green.py` line ref off by three.** The `details={"exit_code",
   "output_tail"}` dict is at **`:55`** (the `GateResult` spans `:51-56`), not
   `:52`. `auto_merge.py:880` and `state_machine.py:302` are both exact.

7. **`bench/bench.py` SM_DONE seed is at `:267`**, inside the `StoryRecord`
   block spanning `:260-270`, not `:266`.

8. **Claude-arm usage limits: 4 of 13, on a subscription — not 6 of 12, not org
   billing.** `bench/CAMPAIGN-2026-07-17.md:33` ("Attempts lost to provider
   usage limits | 4 | 0") and `:51` ("4 of 13 attempts died on usage-window
   trips"). The arm was one-shot `claude -p` on subscription billing.
   `summary.md` holds 20 rows (12 Claude attempts, 8 factory).

9. **`clean()` destroyed the raw artifacts for *all 20* reported runs, not 19 of
   20.** `bench/runs/` holds exactly one `result.json`
   (`t3_csrf/factory-2`) and it is **not** among the 20 rows in
   `bench/results/summary.md`. Every reported number is unbacked by raw data.

10. **The 158 `dirty_working_tree` failures are already fixed — Phase 3.1's
    payoff is 21, not 179.** Both apply paths were made path-scoped on
    2026-07-24 (`factory/manager/apply.py:882-897` documents the fix and the
    "53 of 163 lifetime apply attempts died here" measurement;
    `factory/chain/factory_improver_apply.py:418-436` mirrors it). Fuzzy
    matching only addresses the 16 `corrupt patch` + 5 `patch failed` cases.
    Try `git apply -3` first.

11. **The retry caps are 6, not 3.** RESOLVED 2026-08-01 (#196): operator chose
    to lower the caps. `_MAX_DEV_RETRIES = 3`, `_MAX_REVIEW_CYCLES = 3`, and
    the inner guards `_MAX_DEV_SAME_SIGNATURE` / `_MAX_REVIEW_STUCK` moved 3 ->
    2 so early escalation still fires *before* the hard cap. Keep that gap.

12. **Phase 0.6's assertion fires on today's `routes.yaml`.** RESOLVED
    2026-08-01 (#196): `reviewer` moved to `azure/gpt-5.4` in BOTH blocks (the
    `direct` block had the same collision, which this note missed). The
    `test_implementer` overlap remains, as a warning.
    `azure_routes.dev.hard` and `azure_routes.reviewer` are both
    `azure/gpt-5.3-codex`, and `azure_routes.test_implementer` equals
    `azure_routes.dev.standard` (`azure/deepseek-v4-pro`). The step is written
    above to account for this; a naive "dev ≠ reviewer" assert would break
    startup on the first run.

13. **Four more write-never columns exist alongside `smoke_passed`.**
    `stories.lint_passed`, `format_passed`, `types_passed`, `coverage_passed`
    have **zero references anywhere in `factory/**`**. Folded into Phase 3.2.

Verified exactly as stated, no correction needed: the 122/118/24 chain counts;
17-validated/3-rejected staging; 1 open issue / 0 open PRs / 0 blocked; L4's
163 attempts / 0 `pr_number` / newest `20260723`; the $1,028 figure; reviewer
convergence (0 stories at 6+ in 14 days, max 5, 101 of 122 at zero, 11 all-time
at 6–7); dev retries `{0:86, 1:27, 2:5, 6:4}`; 196 improver proposals → 1 landed
commit `6bd463a3`; 179 apply_failed split 158/16/5; Azure $1.93/$3.83 verified
and $0.161 cache-read estimated; `db_path` threading fixed; July $588.78 / 75 =
$7.85 and $217.18 / 75 = $2.90; `_log_prompt_metadata` single call site at
`runner.py:1734` in `text_run` with no dev/test_implementer/onboarder rows in
`prompts.ndjson`; zero `retried` rows in `chain_steps.ndjson`;
`StoryRecord.smoke_passed` never assigned; CI recovery works and is capped at 3;
the twin at `staging.py:72` is a real run-the-clone canary and is **PUBLIC**;
`bench/tasks.yaml:11` unpinned; the Claude arm unpinned; tasks 023–028 all
`closed`; 45 non-closed sacrifice directions; Hermes `fuzzy_match.py` = 967
lines, MIT, `re`/`typing`/`difflib` only; Hermes `kanban_db.py:104-134` and
`:5847-5856`; `bench/**` and `factory/manager/**` forbidden to self-edit.
