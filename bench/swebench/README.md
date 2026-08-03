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

## The four arms

| arm | agent | models | cost ledger |
|---|---|---|---|
| `factory` | the chain's dev+review handlers | `azure/deepseek-v4-pro` dev + `azure/gpt-5.4` reviewer (`routes.yaml`) | isolated factory DB, priced from the Azure price table |
| `bare` | minimal bash loop | the SAME dev deployment | isolated factory DB, same price table |
| `openhands` | ONE OpenHands agent, no chain | the SAME dev deployment, same SDK + default toolset the chain's dev runs in | isolated factory DB, same price table |
| `claude` | local Claude Code CLI, headless | pinned `claude-opus-5` (the CLI default discovered 2026-08-02; the exact ids the CLI reports land in `result.json`) | **the CLI's own report** (`cost_source: "claude-cli-reported"`) |

Each arm subtracts one thing, and only that thing:

- `factory` − `openhands` = **the chain** (PM/SM decomposition, a reviewer on
  different weights, retries, merge gates). This is the product claim.
- `openhands` − `bare` = **real tools** (file editor, search, a managed agent
  loop) at identical weights.
- `claude` − `factory` = **frontier weights in a frontier harness**, the
  external ceiling.

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
uv run python bench/swebench_adapter.py run --arm bare      --instance getmoto__moto-9841 --probe-plumbing
uv run python bench/swebench_adapter.py run --arm openhands --instance getmoto__moto-9841 --probe-plumbing

# THIS COSTS MONEY. One instance, one arm.
uv run python bench/swebench_adapter.py run   --arm bare      --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py grade --arm bare      --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py audit --arm bare      --instance getmoto__moto-9841

uv run python bench/swebench_adapter.py run   --arm openhands --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py grade --arm openhands --instance getmoto__moto-9841
uv run python bench/swebench_adapter.py audit --arm openhands --instance getmoto__moto-9841
```

`--probe-plumbing` (bare and openhands only) exercises clone → install replay →
collect precheck → prompt assembly → command parse → tool loop → diff capture →
`split_diff` → `assert_no_test_edits` → ledger read-back → `result.json` →
summary, with the provider **replaced by a fixed reply script**. It spends
nothing. For the openhands arm it still really builds the agent (SDK import, key
resolution, Azure endpoint resolution, `routes.yaml` `llm_params`) — only
`conversation.run()` is skipped — so a missing key or a broken endpoint surfaces
for free instead of as a $3 zero.

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
| `claude` | `runs/<id>/claude/claude-transcript.ndjson` | the CLI's full stream-json session |

`result.json` names its own trail in `trajectory`, and records `model` (the
nominal route), `models_used` + `model_calls` + `model_escalated_calls`
(measured from the run's own ledger), `steps_used` / `step_cap`, `termination`
(`done` / `done-empty-diff` / `step-cap` / `wall-clock-cap` /
`model-call-error` / `agent-error` / …) and `diff_bytes`.

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
  actually happened. Live trees now go under `$XDG_CACHE_HOME/swebench-work`
  (override with `SWEBENCH_WORK_ROOT`) and only finished artifacts are copied
  back into `runs/<id>/<arm>/` after the arm has stopped. The prepared trees
  that `grade` and `selftest` mount are worse than reachable — the grade script
  applies the test patch, and the control applies the GOLD patch, *into* them —
  so they get an unguessable `mkdtemp` name and are deleted the moment grading
  ends. `assert_workspace_isolated` refuses any workspace with an
  oracle-bearing ancestor, before spend.
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
  for any reference to the harness paths, and for retrieval-shaped network
  activity (`curl`/`wget` with a URL, `git fetch/pull/ls-remote`, `gh pr|api`,
  `urlopen`, a github.com URL that is not the instance's own origin) — every
  instance is a merged public PR, so fetching the answer is easier than
  decoding it. A hit invalidates the run. The
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
   declared DONE with a 0-byte diff. The bare prompt now says plainly that those
   tests pass at base and do not cover the task. **This defect is identical for
   the factory and claude prompts** and is fixed for bare only so far — see the
   `TODO(operator)` on `_BARE_BASE_TESTS_NOTE`. Do not publish a run as "matched
   prompt" until it is lifted into `_TEST_POLICY` for all arms.
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

Never report a factory number without the matched bare-model number beside it,
and never report either without checking `models_used` against `model` on every
row (see "Which weights actually ran").
The model is a config value in `routes.yaml` that gets swapped as cheaper
models ship, so an absolute score measures the model. The number that measures
the product is scaffold lift: factory − bare, on the same instances.
