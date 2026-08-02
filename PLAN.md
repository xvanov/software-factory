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

## Phase 1 — first real number — **1.1–1.3 DONE 2026-08-02; 1.4 remains**

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

### 1.4 — Run the SAME 10 instances against the bare model

- [ ] **What:** run a minimal scaffold (mini-SWE-agent, ~100 lines of bash loop)
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
- **Corollary for every later phase:** never report a factory number without the
  matched bare-model number beside it. Absolute scores measure the model;
  the delta measures the product.
- **Done looks like:** a two-column table, factory vs bare, on the same 10
  instances, with the lift stated in percentage points and tokens.
- **Effort:** ~3 h, ~$10 (the bare arm is far cheaper per instance).

---

## Phase 2 — the trustworthy benchmark

**Effort ~2 weeks. Cost ~$510.** **[OPERATOR-PR-ONLY throughout — `bench/**`]**

### 2.1 — Pre-registered paired suite

- [ ] 120 tasks, **frozen before the first run**: a published RNG seed, a
      hash-pinned manifest (task id → repo → base SHA → problem statement
      hash), committed and tagged.
- [ ] Plus 30 post-cutoff instances from SWE-bench-Live as a contamination
      control.
- [ ] **Do not reuse the July task pool.** All six directions behind bench
      tasks t1–t6 (`023`–`028`) are now `closed` — the factory has shipped
      them, so they are contaminated. The held-out pool is the **45
      `pm-validated`** directions under `apps/sacrifice/directions/` (76 total,
      31 closed).
- **Done looks like:** `bench/manifest-<date>.yaml` committed with a manifest
  hash, and a `PRE-REGISTRATION.md` stating hypotheses and the analysis plan
  *before* any run.

### 2.2 — Three arms

- [ ] **A = factory**, on its own routes.
- [ ] **B = mini-SWE-agent on IDENTICAL Azure models** (`azure/deepseek-v4-pro`
      for coding, `azure/gpt-5.3-codex` for review). This is the arm the July
      campaign lacked, and without it every result confounds *scaffold* with
      *model*.
- [ ] **C = Claude Code on API billing** with caps matched to arm A's token
      budget. **Change from July:** that campaign used `claude -p` on a
      *subscription*, and lost 4 of 13 attempts to usage-window trips
      (`bench/CAMPAIGN-2026-07-17.md:33,51`). API billing removes that
      confound. Pin `--model` (Phase 0.3).

### 2.3 — Statistics stated up front

- [ ] Report **resolve@1**, **pass^k**, **paired bootstrap CIs**, and
      **McNemar** on the paired A-vs-C outcomes.
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
