# SWE-bench Pro — externally graded

`bench/bench.py` grades the factory on sacrifice's backlog using sacrifice's
own gates: the factory writes the code **and** owns the tests that say the code
works. That measures convergence, not correctness. This harness swaps in a
hidden oracle the factory never sees.

## Run it in this order

```bash
uv run python bench/swebench_adapter.py fetch --language python --limit 10 --seed 20260801
uv run python bench/swebench_adapter.py selftest          # validate the ORACLE
uv run python bench/swebench_adapter.py run   --instance <id> --arm bare
uv run python bench/swebench_adapter.py grade --instance <id> --arm bare
uv run python bench/swebench_adapter.py audit --instance <id> --arm bare
uv run python bench/swebench_adapter.py report
```

`selftest` is not optional. It grades each instance's **gold patch**, which
must come back `RESOLVED`. Any instance where it does not is excluded — a score
computed over broken instances measures the harness, not the arm.

## Sweeping in parallel

One instance at a time is fine for six and impractical for a hundred.
`run-all` fans the same run+grade+audit pipeline out over a worker pool:

```bash
uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 \
    --only-working --dry-run     # ALWAYS preview first
uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 --only-working
```

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

## What selftest caught (2026-08-01)

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

## Results so far

| arm | graded | resolved | note |
|---|---:|---:|---|
| bare (`azure/deepseek-v4-pro`, minimal bash loop) | 6 | **1 (17%)** | real number |
| factory | 0 | — | **blocked, see below** |

n=6. This says "the harness runs". It does not support any comparison yet.

## The factory arm is blocked

`run --arm factory` clones the repo but does **not install its dependencies**,
so the test command dies with `ModuleNotFoundError` before dev writes anything.
On `ansible__ansible-9a21e2477...` dev burned two attempts on an identical
`No module named 'ansible'` signature, hit the same-signature guard, and
blocked with an **empty diff** after 870k tokens.

That measures this adapter, not the factory, and must not be reported as a
factory score. Run-until-green is the factory's core mechanism; denying it a
working test environment removes the thing under test. The bare arm is
unaffected only because it never needs to run tests to emit a patch — which is
precisely why the two arms are **not comparable today**.

The fix is to give the dev sandbox an environment with dependencies installed.
The instance's own image already has them, so running the arm inside it is the
obvious route.

## Guardrails built in

- **Test edits are stripped and the strip is asserted** in code, at run time
  and again at grade time. The factory's dev owns its tests, so an unstripped
  diff would let the arm rewrite the oracle judging it.
- **`--depth 1` clone**, no history: Cursor found Pro scores collapse when
  agents lose git history because some were retrieving the gold patch.
- **`--network none`** during grading.
- **Isolated `FACTORY_STATE_ROOT`** per run — a prior session lost a week to
  bench runs writing synthetic failures into production telemetry.
- **Pinned manifest** with a published seed and a per-instance
  problem-statement hash, frozen before any run.

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

## Reporting rule

Never report a factory number without the matched bare-model number beside it.
The model is a config value in `routes.yaml` that gets swapped as cheaper
models ship, so an absolute score measures the model. The number that measures
the product is scaffold lift: factory − bare, on the same instances.
