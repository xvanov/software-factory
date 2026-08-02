# SWE-bench harness — externally graded

`bench/bench.py` grades the factory on sacrifice's backlog using sacrifice's
own gates: the factory writes the code **and** owns the tests that say the code
works. That measures convergence, not correctness. This harness swaps in a
hidden oracle the factory never sees.

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

## Results so far (Pro profile, final before the freeze)

| arm | graded (audited-valid) | resolved | chain-verdict precision | recall |
|---|---:|---:|---:|---:|
| bare (`azure/deepseek-v4-pro`, minimal bash loop) | 6 | **1 (17%)** | n/a (never claims green) | — |
| factory | 6 | **1 (17%)** | 1/5 = 20% | 1/1 |

n=6, Pro, from `results-archive/2026-08-02T17-30-31.638850Z`. This says "the
harness runs end-to-end on both arms". The SWE-rebench pilot replaces Pro as
the measurement bed.

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
  diff would let the arm rewrite the oracle judging it.
- **Oracle material is never greppable.** Both arms execute on this host
  filesystem, so the gold patch, test patch and hidden test ids live in
  `oracle.json.z` (zlib+base64 — defeats text-scavenging, NOT cryptography;
  a determined process that knows the format can still decode it), with only
  sha256 digests in the manifest. Every consumer verifies the digest; a
  tampered store refuses. `audit` additionally scans the arms' action trails
  (OpenHands trajectories; the bare arm's untruncated `bare-commands.ndjson`)
  for any reference to the harness paths — a hit invalidates the run. The
  scan discriminates: the run's OWN `runs/<instance>/` subtree is the arm's
  cwd and echoes constantly (commands, tracebacks, listings, clipped
  observations, condensed summaries — every flagged row of the first live
  sweep was such an echo), so it is exempt — EXCEPT its `selftest/` and
  other-arm subdirs, whose logs carry the hidden test ids. Harness-authored
  trajectory events (the system prompt, the task message) are not arm
  actions and are not scanned.
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

## Reporting rule

Never report a factory number without the matched bare-model number beside it.
The model is a config value in `routes.yaml` that gets swapped as cheaper
models ship, so an absolute score measures the model. The number that measures
the product is scaffold lift: factory − bare, on the same instances.
