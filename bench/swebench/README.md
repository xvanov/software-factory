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
