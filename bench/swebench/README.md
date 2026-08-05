# SWE-bench harness — externally graded

`bench/bench.py` grades the factory on sacrifice's backlog using sacrifice's
own gates: the factory writes the code **and** owns the tests that say the code
works. That measures convergence, not correctness. This harness swaps in a
hidden oracle the factory never sees.

**Before running or reading a sweep, read
[`PRE-REGISTRATION-1.6.md`](PRE-REGISTRATION-1.6.md).** It fixes the five arms,
the five tables and the decision rules *before* the data exists, so a run cannot
be reported in whatever framing happens to flatter the result. `report` emits
exactly those tables.

## The measured result — 2026-08-04, five arms, n=19, k=1

Full table: [`results.md`](results.md). Evidence:
`results-archive/2026-08-04T04-18-05.349995Z/`, re-derivable byte-for-byte:

```bash
uv run python bench/swebench_adapter.py report \
  --from-archive bench/swebench/results-archive/2026-08-04T04-18-05.349995Z --check
```

| arm | harness × model(s) the LEDGER says ran | resolved / valid | rate | 95% CI | $ | $ / resolved |
|---|---|---:|---:|---|---:|---:|
| claude-5 | Claude Code CLI × `claude-opus-5` (+ its own haiku-4-5 classifier) | 15/19 | **79%** | [54%, 94%] | 34.36 † | 2.29 † |
| claude-4.8 | the SAME CLI, same flags × `claude-opus-4-8` | 14/19 | **74%** | [49%, 91%] | 23.56 † | 1.68 † |
| openhands | OpenHands single agent, no chain × `azure/deepseek-v4-pro` (19 calls) | 7/16 | **44%** | [20%, 70%] | 15.37 | **2.20** |
| factory | the chain on OpenHands × deepseek-v4-pro (33) + gpt-5.3-codex (6) + gpt-5.4 (31) | 7/19 | **37%** | [16%, 62%] | 35.94 | **5.13** |
| bare | hand-rolled text loop, no tool calls × deepseek-v4-pro (727 calls) | 1/18 | **6%** | [0%, 27%] | 7.94 | 7.94 |

† CLI-reported against a subscription; the Azure rows are price-table estimates.
Different bases — never summed, and the cross-family `$ / resolved` is indicative
only. `factory` vs `openhands` is one basis and exact.

Paired McNemar exact, over instances where both arms are audited-valid:

| comparison | isolates | n | only-A / only-B | p |
|---|---|---:|---:|---:|
| **factory vs openhands** | **the chain** | 16 | 1 / 3 | **0.625** |
| **openhands vs bare** | **the tooling** | 15 | 0 / 6 | **0.031** |
| bare vs factory | both, entangled | 18 | 1 / 7 | 0.070 |
| claude-5 vs factory | nothing attributable | 19 | 8 / 0 | **0.008** |
| claude-4.8 vs factory | nothing attributable | 19 | 8 / 1 | 0.039 |
| **claude-4.8 vs claude-5** | **contamination** | 19 | 1 / 2 | **1.000** |

1. **The chain shows no measurable lift.** 37% vs 44% on identical weights, prompt
   and tools, p=0.625. `PRE-REGISTRATION-1.6.md` Rule 1 pre-committed the wording:
   **our lift comes from using a competent agent loop, not from the chain.**
2. **What produces the lift is TOOLING, not orchestration** — `openhands` 44% vs
   `bare` 6%, p=0.031, the only significant result among the three DeepSeek arms.
   The retracted "+58 pp scaffold lift" was measuring the difference between
   having a usable editor and tool-calling API and not having one.
3. **Cost makes it worse.** $5.13 per resolved instance for the chain against
   $2.20 for one agent — **2.3× for no measurable gain** — plus 2.1× the fresh
   input tokens and 2.8× the median wall clock.
4. **Claude Code is roughly twice the factory** (p=0.008) but varies harness AND
   model. Reference point, never a scaffold deficit. That caveat travels with it.
5. **The contamination probe came back CLEAN** — the most valuable result here.
   `claude-opus-4-8` (published cutoff Jan 2026) 74% vs `claude-opus-5` (May 2026)
   79%, same harness, p=1.000, on a manifest where **19/19** instances predate
   opus-5's cutoff. Memorization is not carrying Claude's score, which
   *strengthens* the reference arm.
6. **n=19, k=1, MDE ≈ ±38 pp.** −7 pp is inside noise: "no measurable lift", not
   "the chain hurts". Nothing here measured harm.
7. **Two caveats against the factory.** `openhands` lost 3 rows to Azure 429s and
   2 of those 3 had already produced oracle-RESOLVING patches — counted it is
   9/19 = 47%, widening the gap. And 7/19 is exactly the "matched-weights ceiling"
   the 2026-08-03 retraction derived independently from the old 11/19.
8. **Integrity.** One genuine violation, published invalid and excluded: `bare` on
   `hiero-ledger__hiero-sdk-python-1914_interface` ran
   `curl -s https://raw.githubusercontent.com/…/account_info.py`. Zero path-based
   oracle probes. The repaired `bare` arm now genuinely iterates (727 calls, 16 of
   18 rows budget-exhausted, vs mean 9.2 steps and no cap hits before) and still
   reaches 6% — its one pre-committed repaired run is spent.

**Do not read the sweep files for these numbers.** `sweep-<arm>.json`'s aggregate
counters are in-flight snapshots and contradict their own `results` rows —
`sweep-factory.json` says `resolved: 2`, its rows say 7, the archive says 7. Only
`results.md` and `results-archive/` are authoritative. Tracked as `PLAN.md` 1.6 G.

## Datasets are profiles — SWE-rebench is primary, Pro is FROZEN

The upstream dataset is a **profile** (`PROFILES` in the adapter), selected
once at `fetch --dataset <name>` and pinned into the manifest; every later
command reads the profile back from the manifest, so a run can never mix
profiles.

- **`swe-rebench`** (`nebius/SWE-rebench-leaderboard`) — the primary dataset.
  Every instance is execution-validated upstream; contamination is controlled
  by filtering `created_at` past the model cutoff (default 2026-01-01 —
  DeepSeek-V4 Pro's training cutoff is **undocumented**, that date is a
  conservative stand-in, recorded in the manifest); the gold patch and the
  per-instance docker image ship in-row, so there is no rate-limited HF lookup
  at selftest/grade time. Nebius publishes DeepSeek-V4 Pro at 40.2% under a
  minimal scaffold — an external anchor for the bare arm.
- **`swebench-pro`** (`ScaleAI/SWE-bench_Pro`) — **frozen, do not extend.**
  OpenAI's 2026-07-08 audit found ~30% of its public tasks broken with no fix
  or broken-ID list; our own selftest measured 6/10 usable; and the selftest
  is structurally blind to the dominant failure class (an overly-strict hidden
  test passes the gold-patch control *by construction*). Existing Pro
  manifests, run dirs and results-archives still load and render — regression
  tests pin that — but no new Pro work should happen.

Only **harness plumbing** varies by profile (fetch, image selection, container
layout, test-command derivation, gold-patch sourcing, grade setup). The
factory chain — real `StoryRecord` seeded at `SM_DONE`, real dev+review
handlers, real worktrees, real gates, personas untouched — is identical across
profiles: the benchmark exercises the factory exactly as it runs in the wild.

## Run it in this order

```bash
uv run python bench/swebench_adapter.py fetch --dataset swe-rebench --language python --limit 20 --seed 20260802
uv run python bench/swebench_adapter.py selftest          # validate the ORACLE
uv run python bench/swebench_adapter.py run   --instance <id> --arm bare
uv run python bench/swebench_adapter.py grade --instance <id> --arm bare
uv run python bench/swebench_adapter.py audit --instance <id> --arm bare
uv run python bench/swebench_adapter.py report
```

`selftest` is not optional. It grades each instance's **gold patch**, which
must come back `RESOLVED`. Any instance where it does not is excluded — a score
computed over broken instances measures the harness, not the arm.

## The five arms

**An arm is a (harness, model set) pair.** Neither half may be omitted when a
number is quoted: a score is never a property of the model alone and never of
the harness alone. Every arm is one entry in `_ARMS`, the single registry that
`--arm` choices, step budgets, cost guards, trajectory expectations and the
report's headline labels all read.

| arm | harness | models | cost source |
|---|---|---|---|
| `factory` | the chain's dev+review handlers, dev inside an OpenHands sandbox | `azure/deepseek-v4-pro` dev + `azure/gpt-5.3-codex` hard-tier escape + `azure/gpt-5.4` reviewer (`routes.yaml`) | isolated factory DB, price-table estimate |
| `openhands` | ONE OpenHands agent, no chain | the SAME dev deployment, same SDK + default toolset the chain's dev runs in | isolated factory DB, price-table estimate |
| `bare` | minimal bash loop, no tool-calling API | the SAME dev deployment | isolated factory DB, price-table estimate |
| `claude-5` | local Claude Code CLI, headless | `claude-opus-5` | **the CLI's own report**, against a subscription |
| `claude-4.8` | the SAME CLI, same flags | `claude-opus-4-8` | **the CLI's own report**, against a subscription |

`claude` remains as an alias for the CLI on its default model
(`claude-opus-5`); `--model <id>` overrides it and keys its own run directory.

Each adjacent pair subtracts one thing, and only that thing:

- `factory` − `openhands` = **the chain** (PM/SM decomposition, a reviewer on
  different weights, retries, merge gates). This is the product claim, and the
  only comparison here that varies the harness while holding the model fixed.
- `openhands` − `bare` = **real tools** (file editor, search, a managed agent
  loop) at identical weights.
- `claude-5` − `claude-4.8` = **contamination**: same harness, same flags, an
  older published cutoff (2026-01-31 vs 2026-05-31). Every pinned instance
  predates opus-5's cutoff, so a gap favouring opus-5 on the low-margin rows is
  the memorization signal.
- `factory` vs any `claude-*` varies harness **and** model at once. It is a
  reference point, never a scaffold measurement, and the report labels it
  `nothing attributable`.

### Two runs of one arm cannot overwrite each other

Run directories, report rows and sweep roll-ups are keyed by
**(instance, arm, model)**, not (instance, arm). They were not, and the two
Claude runs would have shared `runs/<instance>/claude/` — the second run's
`_reset_run_artifacts` deleting the first's `result.json`, `prediction.diff` and
transcript, with nothing anywhere saying a measurement had been destroyed. An
off-default `--model` appends `@<model>` to the key; the pre-registered
`claude-5` / `claude-4.8` ids need no flag at all.

The old back-compatible `claude` id is therefore **superseded by `claude-5`** —
same harness, same model, measured before the model-keyed dirs existed. Its 18
pre-fix rows are still in `runs/*/claude/` on purpose (they are the *before*
evidence for that fix, and `results-archive/2026-08-03T05-12-08.813897Z/` holds
committed copies), so `report` segregates them into an "Excluded rows
(superseded run key)" section rather than emitting a sixth arm beside
`claude-5`. The pinned-manifest filter cannot catch them — both ran under the
same manifest — so the run key carries the flag (`ArmSpec.superseded_by`).
`run` and `run-all` refuse a superseded arm outright, so no sweep can spend
money on rows no table will ever show.

### Every per-arm budget and guard fails loud

`_resolve_max_steps`, `_DEFAULT_COST_USD` and `_DEFAULT_HOURS` used to fall back
silently on an unknown arm — for the Claude CLI that meant 16 turns instead of
60, a quarter of the pre-registered budget, reported as if it were the budget.
All three now raise on an arm that is not in `_ARMS`.

## Probe ONE instance before you sweep

A four-arm sweep over 19 instances is the expensive commitment; a single run is
the cheap one. Every arm runs standalone, no sweep required, and prints a
one-screen summary (model, steps used / cap, why the loop stopped, diff bytes
and files touched, and a loud warning when the graded diff is EMPTY).

```bash
# what is pinned right now
uv run python -c "import json,pathlib; \
print('\n'.join(i['instance_id'] for i in json.loads(pathlib.Path('bench/swebench/manifest.json').read_text())['instances']))"

# FREE, no model, no docker, no network — the whole pipeline on fixtures
uv run pytest -q tests/test_swebench_bare_openhands_arms.py

# FREE, real clone + real install replay + real collect precheck, model replaced
# by a fixed script. Writes a row whose `error` marks it as not-a-measurement.
uv run python bench/swebench_adapter.py run --arm bare       --instance getmoto__moto-9841 --probe-plumbing
uv run python bench/swebench_adapter.py run --arm openhands  --instance getmoto__moto-9841 --probe-plumbing
uv run python bench/swebench_adapter.py run --arm claude-5   --instance getmoto__moto-9841 --probe-plumbing
uv run python bench/swebench_adapter.py run --arm claude-4.8 --instance getmoto__moto-9841 --probe-plumbing

# The factory arm has no probe (its dry-run surface is `factory pm-sync
# --dry-run`); the free check that covers it is the sweep preview:
uv run python bench/swebench_adapter.py run-all --arm factory --only-working --dry-run

# THIS COSTS MONEY. One instance, one arm.
uv run python bench/swebench_adapter.py run   --arm bare      --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py grade --arm bare      --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py audit --arm bare      --instance getmoto__moto-9841

uv run python bench/swebench_adapter.py run   --arm openhands --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py grade --arm openhands --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py audit --arm openhands --instance getmoto__moto-9841
```

`--probe-plumbing` (every arm but `factory`) exercises clone → install replay →
collect precheck → prompt assembly → command parse → tool loop → diff capture →
`split_diff` → `assert_no_test_edits` → ledger read-back → `result.json` →
summary, with the provider **replaced by a fixed reply script**. It spends
nothing. For the openhands arm it still really builds the agent (SDK import, key
resolution, Azure endpoint resolution, `routes.yaml` `llm_params`) — only
`conversation.run()` is skipped — so a missing key or a broken endpoint surfaces
for free instead of as a $3 zero. For the claude arms it builds the hermetic
argv and probes the CLI version, skipping only the spawn, so the run-dir key,
the prompt and the transcript path are all exercised without a subscription
call.

The probe row is **fail-closed**: it records an `error`, so `report` buckets it
as a failed run, `estimate_instance_cost` refuses it as a cost sample, and no
headline can absorb it. Re-running the instance for real wipes it
(`_reset_run_artifacts`).

### What a single run leaves on disk

| arm | trajectory | contents |
|---|---|---|
| `factory` | `runs/<id>/factory/root/state/events/trajectories/*.ndjson` | the OpenHands event stream per dev call |
| `openhands` | `runs/<id>/openhands/state/events/trajectories/nostory-1.ndjson` | the OpenHands event stream, copied out whole |
| `bare` | `runs/<id>/bare/bare-commands.ndjson` | one row per turn: untruncated command, exit code, and the OUTPUT the model saw |
| `claude-5` / `claude-4.8` | `runs/<id>/<arm>/claude-transcript.ndjson` | the CLI's full stream-json session |

`result.json` names its own trail in `trajectory`, and records `model` (the
nominal route), `models_used` + `model_calls` + `model_escalated_calls`
(measured from the run's own ledger), `steps_used` / `step_cap`, `termination`
(`done` / `done-empty-diff` / `step-cap` / `tick-cap` / `turn-cap` /
`wall-clock-cap` / `model-call-error` / `agent-error` / …), `diff_bytes`,
`attempt` (which try at this cell this is) and `budget_exhausted` +
`budget_exhausted_reason`.

**One budget rule, every arm:** a turn-cap or wall-cap hit is a **completed,
counted, flagged** attempt — never an excluded run. The retracted 2026-08-03 run
excluded a Claude row that hit its turn cap *and passed the oracle*
(`harumiweb__exstruct-113`: `num_turns 61`, `turn_cap 60`, `error: "claude CLI
exited 1: "`), which silently improved its own denominator from 19 to 18. One
shared classifier, `classify_run`, now answers "did this run complete?" for both
the sweep roll-up and the report; they used to answer it from different facts and
published different numbers for the same sweep (`sweep-claude.json` said 17
resolved, `results.md` said 16 of 18).

The claude arm gets the SAME preparation (pinned-manifest `--depth 1` clone,
install replay, collect precheck) and the SAME task text (the shared story
template: statement + test command + the test-edits-are-stripped note). The
CLI runs hermetically — `--safe-mode --strict-mcp-config --setting-sources ""
--disallowedTools WebFetch WebSearch --no-session-persistence
--dangerously-skip-permissions --max-turns 60`, `CLAUDE*`/`ANTHROPIC*` env
scrubbed — so none of the operator's MCP servers, skills, memory or project
state leak in, and it cannot browse the web for the (public, post-cutoff)
gold PR. Its full stream-json transcript is persisted as
`claude-transcript.ndjson` and audited like the bare arm's command log.
Residual risk, shared with the bare arm: shell-level network (a `curl` or
`git fetch` from the Bash tool) is not technically blocked, only forbidden by
the prompt — the transcript preserves any such command for review.

**Spend warning:** the claude arm bills the operator's **Anthropic
subscription/API** — it never appears in the Azure ledger or the factory's own
spend enforcer. The sweep's spend guard still counts its CLI-reported
`cost_usd` against the `factory_settings.yaml` caps, which is conservative but
means one shared budget covers two different bills.

## Sweeping in parallel

One instance at a time is fine for six and impractical for a hundred.
`run-all` fans the same run+grade+audit pipeline out over a worker pool:

```bash
uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 \
    --only-working --dry-run     # ALWAYS preview first
uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 --only-working
```

The full five-arm sweep is five of those, one arm at a time (each writes its own
`sweep-<arm>.json`), then ONE report over all the rows:

```bash
for arm in factory openhands bare claude-5 claude-4.8; do
  uv run python bench/swebench_adapter.py run-all --arm "$arm" --workers 4 \
      --only-working --dry-run                     # preview + projected spend
done
for arm in factory openhands bare claude-5 claude-4.8; do
  uv run python bench/swebench_adapter.py run-all --arm "$arm" --workers 4 --only-working
done
uv run python bench/swebench_adapter.py report
```

Run the two Claude arms sequentially, not in one sweep: they are the same
subscription and the same rate limit.

- **`--dry-run` is a pure preview.** It prints the work list and the projected
  spend, spawns nothing, writes nothing, costs nothing. Use it every time.
- **`--only-working`** restricts the sweep to instances whose gold patch
  resolves, per `selftest.json`. Without it you are averaging in tasks that
  nothing can solve.
- **Workers are child processes, not threads.** `run` sets
  `FACTORY_STATE_ROOT`, mutates `sys.path` and depends on a module-global
  settings cache, so two runs in one interpreter would cross-contaminate — and
  the loser writes synthetic telemetry into somebody else's state root. Each
  worker shells out to `swebench_adapter.py run`, then `… grade`, then
  `… audit`, so an instance is graded and audited the moment its own run
  finishes.
- **Failure is isolated.** A crash, a wall-clock timeout, a missing docker
  image or a failed grade becomes a row in the summary; the sweep continues.
- **Every row is audited.** Each instance's `audit` runs after run+grade —
  failed runs included, because the audit treats a missing artifact as a
  finding. A failed audit marks the row `audit_ok: false` with the audit's
  reasons; the summary separates audited-valid results from invalid ones, and
  a sweep where **every** row fails audit exits non-zero. The headline
  `resolved` counts only rows that are clean end-to-end (run ok + audit ok);
  an oracle pass from a late-failed run or an audit-failed run stays visible
  in `resolved_but_run_failed` / `resolved_but_audit_failed`, never in the
  headline.
- **`Ctrl-C` really stops it.** The interrupt kills each in-flight child's
  whole process group and still writes a partial summary. Killing the *parent*
  from another terminal does not — those children are detached by design, so
  they survive; interrupt the sweep, don't kill it. (Docker containers already
  started are owned by dockerd and outlive either route.)
- **The spend guard can refuse — and can stop a running sweep.** `run-all`
  reads `caps.hourly_spend_usd` and `caps.daily_spend_usd` from
  `factory_settings.yaml` and will not start a sweep whose projected burn
  breaches either. This matters here more than anywhere else in the factory:
  bench runs write to an isolated state root, so the chain's own spend
  enforcer never sees them and will never throttle them. Because a projection
  can be wrong, **actual** accumulated `cost_usd` is re-checked after every
  completed instance: on breach the sweep launches no new children, lets
  in-flight ones finish (residual overshoot is therefore bounded by
  `workers × the true per-instance cost`), records
  `stopped_reason: "spend cap: …"` in the summary, and exits non-zero. The
  $50/$75/$100 operator notices are emitted on actual accumulated spend as
  rows complete, not on the projection. `--force-over-cap` overrides both the
  refusal and the mid-sweep stop, loudly and on purpose.

Per-instance cost is estimated from previous **clean** runs of the same arm
(runs that completed normally — a failed run's partial spend is not a sample),
floored at the documented conservative default (~$3/instance for the factory
arm) unless there are at least two clean runs to measure. Results land in the
usual per-instance `runs/<instance>/<arm>/`, plus a `sweep-<arm>.json`
roll-up. Then run `report` — its headline counts only audited-valid rows and
loudly buckets `audit failed` / `not audited` / `run failed` oracle passes.

## What selftest caught (2026-08-01, Pro — kept as the argument for the control)

Three harness bugs, each of which would have produced a plausible-looking but
false number. This is the whole argument for having a control:

1. **`fail_to_pass` decoding.** Some instances encode the list as a JSON array
   containing ONE Python-repr string. Parsed naively, pytest gets all six ids
   as a single argument, collects 0 items, and *every* instance grades
   unresolved — a 0% resolve rate that reads as factory incompetence.
2. **Oracle setup order.** `before_repo_set_cmd` already checks out the oracle
   test files from the fix commit, so applying `test_patch` on top conflicts.
   The test patch is now a fallback used only when the ids do not collect.
3. **A false "broken" detector.** Grepping `--collect-only` output for
   "no tests ran" flags healthy instances, because collect-only prints that
   line on every successful collection. It scored 6 of 10 instances unusable
   when 4 of those 6 were fine.

Measured noise floor after those fixes: **6 of 10 instances have a working
oracle**. Of the 4 excluded, 3 are `fail_to_pass_ids_do_not_collect` and 1 is
`gold_patch_does_not_resolve`. Broadly consistent with OpenAI's ~30% finding,
at n=10.

## Historical: Pro profile, final before the freeze

| arm | graded (audited-valid) | resolved | chain-verdict precision | recall |
|---|---:|---:|---:|---:|
| bare (`azure/deepseek-v4-pro`, minimal bash loop) | 6 | **1 (17%)** | n/a (never claims green) | — |
| factory | 6 | **1 (17%)** | 1/5 = 20% | 1/1 |

n=6, Pro, from `results-archive/2026-08-02T17-30-31.638850Z`. This says "the
harness runs end-to-end on both arms" and nothing else. SWE-rebench replaced Pro
as the measurement bed; the current result is at the top of this file.

## SWE-rebench pilot selftest (2026-08-02)

Pinned: seed 20260802, 20 instances from a pool of 215 with
`created_at > 2026-01-01`, `manifest_sha256=923aef05add32124`.

**19/20 instances have a working oracle (95%)** — vs Pro's 6/10 (60%). The one
exclusion is `google__flax-5171`: its image's jax raises a
DeprecationWarning-as-error at import, so the oracle tests cannot even be
collected — environment drift no patch can fix (the images are `:latest`
tags, i.e. mutable upstream).

Getting there caught three harness bugs and one upstream data defect, each of
which the gold-patch control surfaced before any model spend:

1. **argv overflow.** The grade script (test patch + prediction + every hidden
   test id) was one `bash -lc` argv string; Linux caps a single argv element
   at ~128KB and `pandas-63945` (16k fail_to_pass ids) exceeds it. The script
   now goes in on stdin.
2. **TDD instances misread as broken.** The oracle test module can
   legitimately import-error until the fix lands; for **swe-rebench** pre-patch
   no-collect is a red baseline (official SWE-bench semantics), and the
   broken-instance signal moved post-patch, where only the gold patch can
   decide it. Pro keeps its frozen origin/main semantics (persistent
   no-collect = hard `task_broken_no_collect`), so old archives' outcome
   labels stay reproducible.
3. **False `BROKEN_ALREADY_GREEN`.** Applying `test_patch` only as a
   collect-fallback (the Pro flow) skips it when the fail_to_pass test NAMES
   exist at base with old assertions (`nicegui-5858`). swe-rebench applies it
   unconditionally; Pro keeps the fallback.
4. **Upstream truncated ids.** SWE-rebench's log parser splits parametrized
   ids on whitespace (`test_sign_happy[some` for `…[some message]`), leaving
   unclosed brackets that can never match. Repaired at fetch by selecting the
   whole test function — a strict superset, so grading can only get stricter.

## Guardrails built in

- **Test edits are stripped and the strip is asserted** in code, at run time
  and again at grade time. The factory's dev owns its tests, so an unstripped
  diff would let the arm rewrite the oracle judging it. The `diff --git` parser
  handles every form git emits (C-quoted paths, paths with spaces) and
  **hard-refuses** any header it cannot classify: an unparseable header used to
  be appended to the PREVIOUS file's block, which merged a test edit into a
  kept code block and survived both the strip and the assertion.
- **Collection-config edits refuse the row.** Stripping test code is not
  enough: `pyproject.toml` (`addopts`, `-p <plugin>`), `setup.cfg`, `tox.ini`,
  `pytest.ini`, `setup.py`, `noxfile.py`, `sitecustomize.py`, `*.pth` and
  `*pytest*plugin*.py` decide *which* tests run and *whether* they run. A root
  `_fixup.py` plus `addopts = "-p _fixup"` makes pytest exit 0 with everything
  skipped. Those paths are refused rather than stripped — stripping a config
  edit could break an otherwise valid patch, and grading the remainder as the
  arm's answer is `proxy != real`. Measured: 0 of the 188 retained
  `prediction.diff` files and 0 of the 20 pinned oracle patches touch one.
- **Test files are read-only while the arm runs** (`lock_test_files`, added
  2026-08-04). ImpossibleBench (ICLR 2026, arXiv 2510.20270) measured that
  making test files read-only "significantly reduces cheating while maintaining
  performance"; hiding them entirely drove cheating to zero but *degraded*
  legitimate work, so read-only is the setting worth having — the arm still
  reads and RUNS its tests, it just cannot quietly rewrite what judges it. Every
  tracked test file in the arm's tree is `chmod 0444`; directories stay writable
  (pytest writes `__pycache__`, git replaces files by unlinking). Applied to
  **every arm**, because an intervention on one arm of a comparison is a
  confound. For the factory arm the lock is applied to the dev's per-story git
  worktree on each dispatch — `git worktree add` materialises fresh files, so
  locking the source clone would not reach it.
  **Honest limit:** every arm runs as the uid owning those files and has a
  shell, so `chmod u+w` (or `git checkout`) defeats the lock. This is a strong
  default plus a measurement, not a sandbox boundary. `result.json.test_readonly`
  therefore separates `refused` (writes the OS actually rejected, scanned from
  the arm's own tool output) from `bypassed_count` (files whose content changed
  anyway). A non-zero `bypassed_count` means the lock needs real enforcement (a
  different uid, or a read-only mount) before anyone claims the tests were
  unwritable; `refused: null` means that arm's output was not scanned, which is
  not the same as zero attempts.
  **The lock can also LAPSE, which is not the same as being bypassed.** Measured:
  `git apply` and `git checkout --` onto a `0444` tracked file both succeed and
  leave it at `0664`, because git replaces the file rather than writing through
  it. So one git-mediated write early in a run would silently unlock every test
  file for the rest of it, and `bypassed_count: 0` would still read as clean. Two
  consequences, both visible in `test_readonly`:
  - `unlocked_mode` / `lock_lapsed_count` — files still byte-identical but no
    longer read-only. That covers *both* "an attempt is in flight" and "an edit
    landed and was reverted", so it is **not** proof that nothing was written.
    A zero `bypassed_count` only means "the tests were unwritable" when
    `lock_lapsed_count` is `0` as well. Read the two together or neither.
  - The bare arm **re-locks after every command** (the factory arm already
    re-locks on each dispatch). The chmod is idempotent and cheap, and the
    digests `bypassed` is measured against are the ones from the *first* lock,
    so re-locking cannot paper over an edit that already landed.
  Two more fields exist so that a *silent* failure of the measurement cannot
  masquerade as a clean result — the countermeasure-stops-applying class:
  - `git_ok: false` — `git ls-files` could not answer, so the list of files to
    lock was never built. `files: 0, bypassed_count: 0` then says nothing about
    the tree; it is an unmeasured run, not a clean one.
  - `scan_truncated: true` — the arm's output exceeded the 64 MB scan cap, so
    `refused` is an undercount. Reported rather than swallowed, because a low
    number that looks like a real one is worse than a missing one.
- **Grading is per-node, not per-exit-code.** `pytest` exits 0 when every
  selected test SKIPS, so `if ! pytest -q <ids>` graded a fully-skipped run as
  RESOLVED. Both sets now run with `-rpfEsxX` and every declared
  `fail_to_pass`/`pass_to_pass` id must have at least one `PASSED` node and no
  `FAILED`/`ERROR` node, exactly as the official SWE-bench harness decides it.
  `-rA` is deliberately NOT used: it echoes a passing test's captured stdout,
  which would let arm-authored code print a forged `PASSED <id>` line into the
  section the parser reads. A missing per-node report refuses the row.
  Per-node output lands in `grade-nodes.log`; `grade.log` keeps the readable
  log. Measured against the 59 retained `grade.log` files: of the 28 that
  graded RESOLVED, 27 show every selected node explicitly passing and are
  unaffected. The 28th — `pandas-dev__pandas-63945` / claude — reported
  **274 skipped and 1 collection error** inside the graded selection and still
  scored RESOLVED on the exit code. That row is not reproducible either way
  from its log, because the old script never asked for a per-node report; it is
  the defect firing in published data, and the re-run decides it on evidence.
- **No arm's working tree lives inside the repo.** Every arm's shell runs on
  this host, so the working tree's ANCESTRY is part of the threat model — and
  it was not: the factory arm's dev ran with cwd
  `runs/<id>/factory/root/state/worktrees/<name>/`, six `..` from
  `oracle.json.z` and three from the other arms' `grade.log`. Four factory rows
  in `results-archive/2026-08-03T02-21-23.249790Z` are `ok: false` because that
  actually happened. **Every arm's** live tree now goes under
  `$XDG_CACHE_HOME/swebench-work/<instance>__<run-key>/` (override with
  `SWEBENCH_WORK_ROOT`) — flat, not nested, so no arm is a sibling `..` away, and
  keyed by (instance, arm, model) so two runs of one arm never share a tree —
  and only finished artifacts are copied back into `runs/<id>/<arm>/` after the
  arm has stopped. `state/` stays under the run dir: it is where `audit` reads
  the ledger and trajectory from, and it is not an ancestor of the agent's cwd.
  The prepared trees
  that `grade` and `selftest` mount are worse than reachable — the grade script
  applies the test patch, and the control applies the GOLD patch, *into* them —
  so they get an unguessable `mkdtemp` name and are deleted the moment grading
  ends. `assert_workspace_isolated` refuses any workspace with an
  oracle-bearing ancestor, before spend. Because that check only runs in the
  arms that call it, `audit` re-derives the invariant from the artifacts: a
  live working tree left at `runs/<id>/<arm>/repo` or `.../grade-repo` is an
  audit FAILURE, so a new arm cannot quietly opt out.
- **Oracle material is never greppable.** All arms execute on this host
  filesystem, so the gold patch, test patch and hidden test ids live in
  `oracle.json.z` (zlib+base64 — defeats text-scavenging, NOT cryptography;
  a determined process that knows the format can still decode it), with only
  sha256 digests in the manifest. Every consumer verifies the digest; a
  tampered store refuses. `grade` never prints the oracle's `gold_files` to
  stdout (the sweep captured it into `runs/<id>/<arm>/sweep-grade.log`, i.e.
  the answer key next to the answer sheet); they stay in `result.json`.
  `audit` additionally scans the arms' action trails
  (OpenHands trajectories; the bare arm's untruncated `bare-commands.ndjson`;
  the claude arm's `claude-transcript.ndjson`)
  for any reference to the harness paths, and for retrieval ACTIONS
  (`curl`/`wget` with a URL, `git fetch/pull/ls-remote`, `git clone` from a
  URL, `gh pr|api|issue`, `urlopen`/`requests.get`/`httpx.get` on a URL, `pip
  install` from a URL or `git+`, any `api.`/`raw.githubusercontent.com` URL,
  and a `WebFetch`/`WebSearch` tool call or a non-zero server-side web-tool
  counter) — every instance is a merged public PR, so fetching the answer is
  easier than decoding it. A hit invalidates the run.

  **The two scans read different things, deliberately.** The harness-path scan
  reads the WHOLE trail line, both sides: a run has no business so much as
  printing the oracle store's path. The retrieval scan reads only the COMMAND
  side — each format's own action/observation split (OpenHands `ActionEvent`
  vs `ObservationEvent`, a claude `tool_use` input vs its `tool_result`,
  `bare-commands.ndjson`'s `command` vs its `output`), minus the fields that
  carry authored file text (`file_text`, `old_str`/`new_str`,
  `content`, …). **What the agent ran, not what the agent saw.** A bare
  `https://github.com/...` used to be a hit on any line, and it was a false-
  positive machine: on the completed five-arm sweep it flagged 218 lines
  across 46 rows, every one of them a hostname the arm merely read — a URL
  literal in conan's own test fixture, an `$id` in tox's JSON schema, a
  docstring, a `git remote -v` echo of the clone's legitimate origin. Verb
  anchoring plus the command-side split cleared all 218 and kept the one real
  hit (a bare-arm `curl` of `raw.githubusercontent.com/<the instance's own
  repo>/main/<the file under test>`). There is no own-repo exemption on the
  retrieval side: fetching your own origin's `main` IS the fix. The
  scan discriminates: the run's OWN `runs/<instance>/` subtree is the arm's
  cwd and echoes constantly (commands, tracebacks, listings, clipped
  observations, condensed summaries — every flagged row of the first live
  sweep was such an echo), so it is exempt — EXCEPT its `selftest/` and
  other-arm subdirs, whose logs carry the hidden test ids, and the
  oracle-bearing FILENAMES inside its own subtree (`grade.log`,
  `grade-nodes.log`, `result.json`, …). Harness-authored
  trajectory events (the system prompt, the task message) are not arm
  actions and are not scanned. An arm that reports model calls and left NO
  scannable trail fails the audit: the scan used to return no findings when it
  had nothing to scan, so a wiped state root audited clean.
- **`audit.json` certifies the graded patch, not just the ledger.** It records
  `prediction_sha256`, `base_commit`, `stripped_test_paths`, `refused_paths`,
  `trajectories_scanned` and `trails_scanned`, so a published verdict is tied
  to the bytes that produced it.
- **Every instance is graded against a regression suite.** Two pinned
  instances ship an empty `pass_to_pass`
  (`line__line-bot-sdk-python-981_interface`, `pandas-dev__pandas-63945`) and
  the p2p invocation was skipped entirely for them, so a patch that fixed the
  target test by breaking everything around it scored the same as a correct
  one. When `pass_to_pass` is empty, the instance's declared `test_targets`
  files are used as an implicit set and `pass_to_pass_source` records which it
  was. Pro (frozen) gets no implicit set.
- **The control's log is committed.** `selftest` writes
  `bench/swebench/selftest-logs/<instance>.log`, outside gitignored `runs/`.
  It used to write into `runs/<id>/selftest/`, which is why 0 of the 19
  published swe-rebench instances retain the log that certified them.
- **`selftest`/`run`/`run-all` refuse BEFORE spend if the oracle store
  cannot serve every pinned instance** (digest-verified per instance).
  `grade` — the last step — used to be the first consumer to notice a
  broken store, after $24.78 of model spend had already happened. Unit
  tests are hard-isolated from the repo's pinned artifacts by an autouse
  fixture (a test once clobbered the committed store with one fixture
  record — the exact test-pollution class this repo has been bitten by
  before).
- **Control = measurement topology (swe-rebench).** `selftest`, `run` and
  `grade` all operate on a MOUNTED fresh clone prepared by replaying the
  dataset's own `install_cmd` inside the instance image (generated build
  artifacts — setuptools-scm version files, compiled extensions — are then
  committed onto `swebench-base` so per-story worktrees and in-container
  resets keep them). Grading the image's baked `/testbed` while running a
  fresh mount let three instances pass the control and die at the run's
  collect gate (proxy ≠ real). An instance whose install step cannot
  succeed in this topology is excluded by selftest before any model spend.
  Pro (frozen) keeps its baked-tree behavior.
- **The verdict channel is not forgeable or swallowable.** The grade script
  travels on stdin (argv caps at ~128KB), is drained to a container-local
  file and exec'd with stdin at `/dev/null`, so arm-authored test code can
  neither eat the trailing verdict echo nor replay the script text; verdict
  markers carry an env-injected per-invocation nonce, so no static text can
  match the checked string.
- **Images are digest-pinned.** Upstream `:latest` tags are mutable; fetch
  resolves each image to `repo@sha256:…` so every later pull is byte-identical
  to what the selftest certified.
- **Reports are pinned to one manifest.** Every `result.json` records the
  `manifest_sha256` it ran under; `report` counts only rows matching the
  pinned manifest and lists any other manifest's leftovers under an explicit
  "excluded" section — two datasets can never blend into one headline.
- **`--depth 1` clone**, no history: Cursor found Pro scores collapse when
  agents lose git history because some were retrieving the gold patch.
- **`--network none`** during grading.
- **Isolated `FACTORY_STATE_ROOT`** per run — a prior session lost a week to
  bench runs writing synthetic failures into production telemetry.
- **Pinned manifest** with a published seed and a per-instance
  problem-statement hash, frozen before any run. The `--after` cutoff is
  parsed as a date and excludes the whole cutoff DAY (strictly after).

## Auditing

Every run leaves a complete trail in its isolated state root: Run rows in
`state/factory.db`, event streams in `state/events/*.ndjson`, and verbatim
prompt bodies in `prompt_bodies.ndjson`. The `audit` subcommand verifies one
run against that trail:

```bash
uv run python bench/swebench_adapter.py audit --instance <id> --arm factory
```

It lists every persona/LLM call (persona, story, tokens, cost, timestamp),
cross-checks the ledger's cost/token sums against `result.json`, scans
reviewer prompts for error strings where the diff should have been (`returned
rc=`, `(diff is empty`, …), and flags a first dev call that failed in under
~5 s — the unrunnable-environment signature. Any finding exits non-zero.
FAIL SAFE: a missing artifact (no DB, no prompt bodies) is an audit failure,
not a pass. The findings are written to `audit.json` next to `result.json`.

The claude arm has no factory ledger, so its audit certifies `result.json`
against the CLI's stream-json transcript instead (per-model usage and
`total_cost_usd` from the `result` event) and additionally proves the
hermetic config actually loaded (the `init` event must show zero MCP servers
and no WebFetch/WebSearch). A transcript missing when the run made calls is
an oracle-probe failure, same as the bare arm's missing command log.

## The bare arm

The bare arm is a deliberately minimal bash loop on the same model deployment:
one shell command per turn, truncated output, a 40-step budget, and the same
docker test one-liner the factory's dev gets, so it can check its fix before
declaring DONE. It deliberately lacks everything else the factory adds —
review by a second model, retries, structured tools, planning — because it is
the floor the factory must beat, not a second agent framework.

**"Minimal" means few affordances, not a broken substrate.** Every bare row
produced before 2026-08-03 measured this loop's bugs, not the model, and the
published `bare 0/19` column (and with it the "+58pp scaffold lift at matched
weights" headline) is **retracted**. The external anchor makes that
unambiguous: Nebius publishes the same deployment at 40.2% under its own minimal
scaffold, so P(0 of 19 | p = 0.402) = 5.7e-5. What was wrong, and is now fixed:

1. **Prompt asymmetry (invalidating).** The bare system prompt said *"Do NOT
   create, edit or delete test files. Test edits are stripped before grading, so
   they are wasted effort"* while the shared story template told the factory and
   claude arms to *"write tests that express the required behaviour, then make
   them pass … they are your feedback loop, not the grade."* Identical stripping
   mechanic, opposite instruction, on the arm the headline rests on. All arms now
   share one `_TEST_POLICY` block, byte-identical.
2. **The gated test command cannot fail (invalidating).** It targets the
   `fail_to_pass` FILES at `base_commit` — before the withheld gold test patch
   adds the tests. Over the 19 pinned instances: 3 target a file that does not
   exist, 11 more contain ZERO `fail_to_pass` functions, and the other 5 contain
   them asserting the OLD behaviour. So "N passed" is the default state of the
   tree. `conan-19735` ran a `sed` that matched nothing, saw "28 passed" and said
   DONE at step 6 with a 0-byte diff; `nicegui-5858` the same;
   `ucfopen__canvasapi-716` wrote a correct fix, saw a pre-existing test assert
   the old behaviour, restored the original file out of the docker image and
   declared DONE with a 0-byte diff. **Fixed for EVERY arm** as of 2026-08-03:
   one `_BASE_TESTS_NOTE`, byte-identical, reaches `_STORY_TEMPLATE` (factory,
   openhands, claude) and `_BARE_TASK` (bare), so the "matched prompt" claim is
   actually true. #223 had fixed it for bare alone, deliberately, to avoid
   confounding two axes at once; applying it everywhere makes the five-arm re-run
   a **fresh baseline**, not a before/after against the retracted run.
3. **No collect precheck.** Bare was the one arm that could be handed an
   unrunnable test command and still burn its whole budget. It now runs the same
   pre-dispatch gate, and `instance_test_command` finally honours its `repo`
   argument, so a target that does not exist at base falls back to its nearest
   existing ancestor directory — for every arm.
4. **DONE was unconditional.** 6 of 19 rows (32%) shipped 0 bytes. A DONE with
   no production-code change in the tree now gets one observation saying so, at
   most twice (below this repo's hard loop cap of 3), and the outcome is recorded
   as `termination: "done-empty-diff"`.
5. **Roleless flat-string prompting.** The loop sent `"\n\n".join(history[-24:])`
   as ONE user string and echoed the model's RAW reply into it, so the model
   could not tell its own text from the environment's: 76 of 231 measured replies
   contained a fabricated `Exit N` / `Exit code:` / `Output:` / `Result:` line,
   and `_BARE_STOP` caught only two of those four shapes. `conan-19750` produced
   an 11,890-character reply with 8 fenced blocks, executed ZERO commands, and
   said "The tests now pass. DONE". It is now a real role-tagged message list,
   and only the PARSED COMMAND is ever echoed back — a fabricated observation is
   unrepresentable in the context, not merely discouraged.
6. **The context window evicted the task.** `history[-24:]` over a list that
   started at 2 and grew by 2 per step dropped the system prompt and the task
   after step 11 — and invalid-format replies clustered at exactly steps 12-24,
   in the four longest runs, all four of which ended wrong or empty. The
   system+task prefix is now pinned; only the tail slides.
7. **Protocol tax.** 34 of 231 replies had no `BASH` marker; 12 were plain
   ```` ```bash ```` fences thrown away as "Invalid reply". deepseek's native
   output is fenced markdown, so a tagged shell fence is now accepted as
   equivalent.
8. **An uncaught command timeout** propagated out of `run_bare` and killed the
   run with no `result.json` at all. A timeout is now an observation.
9. **No observation trail.** `bare-commands.ndjson` held commands only, so
   reconstructing what the arm SAW meant hand-joining `prompt_bodies.ndjson`.
   Exit code and output now land there too — which also means the audit's
   oracle-probe scan finally sees command OUTPUT, not just commands.

## The openhands arm

The bare arm isolates "cheap weights with almost no scaffold"; the claude arm
isolates "frontier weights in a frontier harness". Neither isolates the thing
being sold, which is **the chain**. This arm does: ONE OpenHands agent, the
factory's own `route("dev","standard")` deployment, the same SDK and default
toolset (`get_default_agent(cli_mode=True)` — real file editor, real bash, real
search) that the chain's dev runs inside, the same `_STORY_TEMPLATE` task text,
the same prepared clone, the same collect precheck, the same 5400 s wall clock,
the same prediction path. No PM, no SM, no reviewer, no gates, no retries.

Its iteration cap (600) is exactly the factory dev's own per-attempt cap
(`sandbox_run`'s signature default), so the arms cannot differ on inner budget —
a test pins the two together. The factory arm may open up to three such
conversations across its 16 ticks; in practice the shared wall clock binds first
for both.

**Deliberately excluded:** the dev persona prompt and the context prelude.
They are part of the harness under test, so this arm carries the story file
alone — the factory arm's advantage therefore includes its persona engineering,
which is the honest attribution.

Accounting: one `Run` row is written into the run's own isolated ledger from the
conversation's own usage totals, and `result.json` reports the numbers read BACK
from that ledger — so `audit` certifies this arm through the same code path as
the factory and bare arms, with no per-arm special case. OpenHands' persisted
event stream is copied out whole (via the chain's own `_capture_trajectory`) as
this arm's trajectory, and the audit's oracle-probe scan reads it.

The wall-clock cap ABANDONS the conversation rather than killing it — an
in-process agent loop cannot be killed, the same trade-off `sandbox_run` makes —
and grades the tree as it stands. That is why the trajectory is persisted
incrementally rather than at the end.

## Which weights actually ran

`result.json` used to carry no `model` at all on the factory arm. That hid a
finding: across the 19 pinned instances the factory arm escalated 7 dev calls to
`azure/gpt-5.3-codex` (the HARD tier) on 5 instances, and 4 of its 11 resolves
used that tier — so "matched weights vs the bare arm" was false, and nothing in
the artifact said so. Every arm now records:

- `model` — the NOMINAL route, i.e. what "matched weights" claims;
- `models_used` — every model id that actually produced a call, measured from
  the run's own `state/events/runs.ndjson`;
- `model_calls` — calls and spend per (persona, model, tier);
- `model_escalated_calls` — how many calls ran on something other than `model`.

Compare the first two before quoting any cross-arm delta.

## Reporting rule

Never report a factory number without the matched **`openhands`** number beside
it — that is the only pair here that holds the model fixed and varies the
harness, so it is the only one that measures the chain. Never report either
without checking `models_used` against `model` on every row (see "Which weights
actually ran"). The model is a config value in `routes.yaml` that gets swapped as
cheaper models ship, so an absolute score measures the model.

## The report: five tables, and what each column exists to prevent

`report` emits Tables 1-5 in the shape fixed by
`bench/swebench/PRE-REGISTRATION-1.6.md` **before** the run. Every cell comes
from an archived artifact or prints `n/a` with a reason; no cell is filled by
hand.

| table | contents |
|---|---|
| 1 | headline per arm: harness + the models the LEDGER says ran, resolved/audited-valid, rate, exact Clopper-Pearson CI, invalid rows, budget-exhausted count, `fresh in`, `cache read`, out, median wall, $, cost source |
| 2 | per-instance outcome matrix with a contamination margin column per model bound |
| 3 | every pair with `harness varies?` / `model varies?`, the discordant cells, and exact McNemar p |
| 4 | provenance and integrity per arm: model ids, per-tier call counts, max attempt, audit ok/invalid, action trails, stripped test files, oracle-probe hits, empty-PASS_TO_PASS rows |
| 5 | chain-verdict precision/recall — `n/a (arm has no chain verdict)` for every arm that has no chain |

Each of those columns replaces a specific way the retracted run misled:

- **`fresh in` / `cache read` are separate.** Cache share was 0% (bare) / 78%
  (factory) / 97% (claude); one blended "tokens in" column made the published
  "34× tokens" claim wrong by 4.5×.
- **The cost column names its source per arm** and the two are never summed: the
  Azure arms' dollars are a price-table estimate over measured tokens, the Claude
  arms' are the CLI's own report against a subscription.
- **The exclusion line names passes AND failures**, each with its verdict. It
  named only excluded passes, so an excluded failure vanished with no verdict
  shown and a reader could not tell which way the exclusions moved the rate.
- **`attempt` and a "Discarded runs" section.** The retracted run published 4
  second attempts after the integrity gate invalidated the first, disclosed
  nowhere. Under the no-re-rolls rule any `attempt > 1` is a protocol violation.
- **`n/a (arm has no chain verdict)` for both rates.** The retracted table
  published "claude recall 0/16 = 0%", a division artifact on a column that does
  not exist for that arm, and it read as a finding about Claude.
- **`pass_to_pass_count` is surfaced and empties are flagged.** Two pinned
  instances declare NO PASS_TO_PASS, so their grade has no regression half at all
  and nothing there can catch a patch breaking the suite.
- **Confidence intervals and McNemar are exact and in-repo** (`math.comb`, no new
  dependency). At n=19 a normal approximation is wrong in exactly the direction
  that flatters a small sample.
- **Margins name their bound TYPE.** `deepseek-v4-pro` publishes no cutoff, so
  its bound is its release date (`release-date-proxy`) — a weaker guarantee than
  the published cutoffs used for the gpt-5.x and claude models.

### Re-derivation is verifiable, and verifying does not mutate

```bash
uv run python bench/swebench_adapter.py report                        # live: archives evidence, writes results.md
uv run python bench/swebench_adapter.py report --from-archive <dir>   # STDOUT only, writes nothing
uv run python bench/swebench_adapter.py report --check                # diff vs the committed results.md; exit != 0 on drift
```

`--from-archive` used to **overwrite the very `results.md` it was verifying**,
and in doing so silently deleted a 20-line disclosure section from committed
evidence. It now prints to stdout and writes nothing; `--check` is the executable
form of "a second report run re-derives the committed table byte-for-byte", which
was previously unfalsifiable because the re-derivation overwrote its own
reference.

To publish from an archive there is one explicit, opt-in flag — never a shell
redirect, which adds a trailing newline and then fails its own `--check`:

```bash
uv run python bench/swebench_adapter.py report --from-archive <dir> --publish
uv run python bench/swebench_adapter.py report --check      # must print CHECK OK
```

### What the archive contains

`results-archive/<generated-at>/` holds, per row, `result.json` + `audit.json` +
`prediction.diff`; plus `sweep-<arm>.json` for every arm that produced a row,
`selftest.json` and `selftest-logs/` (the gold-patch control, which previously
rested on a summary the next selftest overwrote), the rendered `results.md`, and
`report-meta.json`.

An archive may also carry an operator-written `DISCLAIMER.md`, emitted verbatim
at the top of any table re-derived from it. That is how a run is marked
**retracted**: by ADDING a file beside the evidence, never by rewriting rows,
audits or the original meta. `results-archive/2026-08-03T05-12-08.813897Z/` has
one — its three-way numbers (factory 58% / bare 0% / claude 89%) are
**RETRACTED** and survive only as the report code's regression corpus. The
current result is at the top of this file: factory 37%, openhands 44%,
claude-opus-5 79%. Never quote the 05-12 archive as a measurement.

`report-meta.json` also **persists the refused and foreign row lists** and each
instance's `created_at`. Those were recomputed from `runs/` at report time, so
from an archive they were always empty and a re-derivation silently dropped the
disclosure. An archive written before meta version 1.6 says
`n/a (archive predates …)` rather than printing an empty section that reads as
"nothing was excluded".

### Cost projections are pooled within ONE manifest

`estimate_instance_cost` filters samples by `manifest_sha256`. Pooling across
manifests poisons the spend guard: SWE-bench-Pro instances are far larger than
SWE-rebench ones, and their MINIMUM wall clock became the rebench sweep's
projected per-instance duration — the denominator of the hourly burn rate. A row
that records no sha is unverifiable provenance and is never a sample.
