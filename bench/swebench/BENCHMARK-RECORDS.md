# The benchmark record store — `benchmarks.db`

One immutable row per **graded benchmark attempt**, so every run is queryable over
time, reproducible from what is recorded, and auditable end to end.

```bash
# capture what is on disk now (idempotent, read-only over runs/, $0)
uv run python bench/swebench_adapter.py record
#   …or, identically:
uv run python bench/swebench/benchmark_store.py ingest

# ask it things
uv run python bench/swebench/benchmark_store.py rates
uv run python bench/swebench/benchmark_store.py cost
uv run python bench/swebench/benchmark_store.py roles --arm chain
uv run python bench/swebench/benchmark_store.py validity
uv run python bench/swebench/benchmark_store.py campaigns
uv run python bench/swebench/benchmark_store.py diff --a <campaign> --b <campaign>
uv run python bench/swebench/benchmark_store.py show   --instance <id> --arm chain
uv run python bench/swebench/benchmark_store.py replay --instance <id> --arm chain
uv run python bench/swebench/benchmark_store.py verify
uv run python bench/swebench/benchmark_store.py export --out records.jsonl
```

Every verb except `ingest` is read-only. Nothing here calls a model; nothing here
can spend a cent. `--json` (before the subcommand) emits machine-readable output.

---

## STOP — a benchmark run is not the factory building something

**Do not write ordinary factory telemetry into this store.** They are different
kinds of event and mixing them destroys the only thing this store is for.

| | a BENCHMARK row | ordinary factory work |
|---|---|---|
| graded by | a **hidden oracle** (`fail_to_pass` / `pass_to_pass` node sets) the agent never sees, run inside the instance's own official docker image | nobody external. The factory writes the code *and* owns the tests that say the code works |
| the task | a **pinned, immutable** manifest entry: instance id, repo, `base_commit`, `problem_statement_sha256`, chosen by published RNG seed *before* any run | whatever the backlog contains today; it moves |
| the tree | a `--depth 1` clone at `base_commit` in an **isolated state root**, with the test files locked `0444` | the app's real worktree and the real `state/` |
| test edits | **stripped from the diff before grading**, and the strip is asserted — the agent cannot edit the oracle | the dev owns its tests by design (the Loop-4 mechanism) |
| exists to | produce **one comparable measurement** of a (harness, model set) pair | ship a change |
| its cost | attributed to one arm, one instance, one attempt | attributed to a story |

Consequences that follow, and are not negotiable:

* A row in this store means "an arm attempted a pinned instance and a hidden
  oracle judged it". A factory tick, a story, a PR or a live-chain persona call
  means none of that. Writing one here would put an ungraded, unpinned,
  test-owning event into a table whose every query assumes the opposite — and the
  resulting "resolve rate" would be measured over a denominator that includes
  work no oracle ever saw.
* Benchmark runs already keep out of production telemetry (isolated
  `FACTORY_STATE_ROOT`; a prior session lost a week to bench runs writing
  synthetic failures into production telemetry, which the FMS then escalated as
  real). This store is the same boundary in the other direction.
* If you want statistics about ordinary factory work, use the factory's own
  ledger and event streams (`factory why`, `factory trace`, `state/factory.db`).
  Not this.

## Which database is which

There are two sqlite files in play and they are **not** interchangeable.

| file | what it is | written by | lifetime |
|---|---|---|---|
| `bench/swebench/runs/sssf-bench.db` | the **engine execution trace**: `sessions, phases, events, agent_sessions, envelopes, gate_results, processes`. Shared by every sssf run of every arm so the observability UI can watch a sweep live. `sessions.total_cost` is a **running sum across attempts** of the same cell, because `adw_id` is stable per (instance, arm). | `/home/k/sssf/adws/adw_modules/tracer.py`, live, during a run | gitignored scratch under `runs/` |
| `bench/swebench/benchmarks.db` | the **benchmark record**: one row per graded attempt, with figures snapshotted at ingest, provenance to re-run it, and digests of its whole evidence trail. | `bench/swebench/benchmark_store.py`, after a run | durable, tracked |

Never read a published figure out of `sssf-bench.db`. Its cost totals cannot be
split back into per-attempt dollars. `result.json` reads its dollars from the
run's own `events.jsonl`; the shared db is for watching and for a cross-check
(recorded here as `cost_usd_shared_db`, deliberately in its own column so it can
never be mistaken for the row's cost).

## Why the store has to exist

`_sssf_adw_id` is a pure function of `(instance, arm)`, so **attempts overwrite**:

* `_reset_run_artifacts` deletes the run dir's `result.json`, `audit.json`, both
  diffs, the trajectory and the roster at the top of every run;
* `_work_dir(fresh=True)` `rmtree`s the per-run `data_dir`, taking
  `raw_output.jsonl` — the only per-turn record of what was spent — with it;
* the shared tracer db keeps accumulating into the same `sessions` row;
* `sweep-<arm>.json` is overwritten by the next sweep of the same arm, taking the
  `--workers` value and the sweep's own roll-up with it.

Measured on 2026-08-13: `getmoto__moto-9841/chain` is on **attempt 4**,
`keras-team__keras-22316/chain` on **attempt 3**. Attempts 1–3 and 1–2 exist
nowhere on disk, in any database, in any log. Every figure for them is gone, and
nothing recorded that a measurement was destroyed.

So this store keys on **(instance_id, arm, attempt)** and snapshots each
attempt's numbers at ingest. That is the single biggest thing it adds, and it
means:

> **Ingest is the snapshot, not a reporting step. Run it before re-running any
> cell, or that attempt's detail is lost for good.**

`run_all` calls it automatically at the end of every sweep, best-effort and loud
on failure, for exactly that reason.

---

## The schema, and why it is shaped this way

Five tables around one spine, plus two bookkeeping tables. Full rationale is in
the comments above `_SCHEMA` in `benchmark_store.py`; the summary:

### `run_attempt` — the row of record

`UNIQUE(instance_id, arm, attempt)`. Not `(instance, arm)`: that is the identity
the **disk** uses, and it is precisely why attempt history dies. `arm` is the
**run key** (`arm` plus, for a model-selectable arm on an off-default model,
`@model`), matching the run directory.

The whole `result.json` is stored verbatim in `result_json` **beside** the
extracted columns, with `result_sha256` over the exact bytes. Two reasons: no
future question is blocked by a column this schema failed to anticipate, and the
copy is checkable against the file it came from.

Notable columns:

* **composition** — `roster_json`, `roles_run`, `roles_skipped`, `chain_roles`,
  `roster_role_count`, `harness_id`, `has_chain`, and `is_chain`. `is_chain` is
  **derived from the roster's active role count, never from the arm name**: an arm
  called `chain` that ran one role is a solo run and the record must say so.
* **cost** — `cost_usd` with a `NOT NULL cost_source`, and the cross-checks
  (`cost_usd_events`, `cost_usd_shared_db`, `cost_usd_rederived`) in separate
  columns so they can never be summed with it.
* **validity** — `status`, `audit_ok` (tri-state: `NULL` = *not audited*, which is
  not the same as *audit failed*), `budget_exhausted`, `provider_starved`,
  `reportable`, and `invalid_reasons` (a JSON list, `[]` iff reportable).
* **honesty about the attempt number** — `attempt_source` records whether the
  number came from `result.json`, from `attempt.json`, or is `assumed-1` because
  the row predates the counter. An assumption is never presented as a
  measurement.
* **honesty about the trail** — `artifacts_recorded` / `artifacts_skipped`.

### `role_usage` — per (attempt, role)

Tokens, calls, dollars, empty-response turns, peak turn input, the roster's
intended model and the models the trace actually shows. **Skipped roles get a row
too** (`skipped = 1`): "chain minus documenter" is a composition claim, and a
store that recorded only what ran could not distinguish a role skipped by
configuration from a role that silently never fired.

### `artifact` — the audit trail, file by file

`path`, `sha256`, `size_bytes`, `mtime_utc`, `kind`, and `answer_key`. Digests
make the trail verifiable **after the bytes are gone** and make tampering
detectable (`verify`).

The set is the run's *evidence*, defined by the adapter's own archive lists
(top-level files, `_ARCHIVED_ROW_EXTRAS`, `_ARCHIVED_TRAJECTORY_GLOBS`) — not the
whole tree. Recursing the whole tree was tried: it produced **102,106 artifact
rows and a 30 MB store**, because a `factory` run dir contains an entire isolated
state root of rebuildable scratch. What was left out is *counted* in
`artifacts_skipped`, so the omission is stated rather than implied.

`answer_key = 1` marks files that carry the hidden test ids (`grade.log`,
`grade-nodes.log`, `sweep-grade.log`, `oracle.json.z` — the adapter's
`_NEVER_ARCHIVED`). Their **digest** is recorded; their **content** is never
emitted by `export`. Committing the ids would hand the answer key to every later
arm.

### `provenance` — everything needed to re-run, one row per attempt

The pinned task (`manifest_sha256` + the manifest's digest **as it is now**, so a
moved manifest is visible), the roster **YAML verbatim** and the prompt verbatim,
the arm's registry entry, the caps, `max_steps`, `--workers`, `skip_phases`,
`thinking`, the engine entrypoint, the price table's path + live sha + pinned sha
+ `matches_pinned` **and the rates themselves** (a digest alone cannot re-derive a
dollar), and **both repositories' git shas with an explicit dirty flag**.

Then a conclusion, not a hope: `reproducible` plus
`reproducibility_caveats` — a JSON list where each entry is a specific reason the
replay would not be bit-exact. An empty list is the only claim of exactness this
store ever makes.

### `price_rate` — the rates in force, normalised

Per (attempt, model): input / output / cache-read / cache-write per unit, with the
units string. Lets a per-role dollar figure be re-derived from the store alone.

### `campaign` — the time axis

One sweep. `campaign_id` is `"<run_key>@<finished_at>"`: deterministic and
human-readable, so re-ingesting the same `sweep-<arm>.json` is a no-op while the
*next* sweep of the same arm lands as a separate campaign. The summary is stored
verbatim because the file is overwritten.

Attempts join to campaigns on **(instance_id, attempt)** — every sweep record
already carries the attempt number the run wrote, so attribution is exact rather
than a timestamp guess. A row whose sweep summary was already overwritten before
ingest is grouped under `(no campaign)` rather than dropped, and its `--workers`
is recorded as `unrecorded`.

### `ingest_log` — an audit trail for the audit trail

Who ingested what, when, and with what dispositions. A row whose figures changed
between ingests shows `revision > 1`; this says which ingest did it.

### Storage decisions

* **`bench/swebench/benchmarks.db`**, deliberately *not* under `runs/`. `runs/` is
  gitignored scratch the next sweep wipes, and `runs/sssf-bench.db` already lives
  there; a record store whose whole purpose is to outlive the run directory
  cannot sit inside it, and two sqlite files in one directory invite querying the
  wrong one.
* **WAL**, like the engine's tracer db and for the same reason: a query must be
  able to read while a sweep's ingest writes. `foreign_keys=ON`, so a deleted
  attempt cannot orphan its role/artifact rows.
* **The db is tracked; its `-wal`/`-shm` sidecars are gitignored.** It is the only
  place a superseded attempt's figures survive, so ignoring it would put the
  durable record in the one directory git cannot see. It is ~2.5 MB for 141
  attempts and grows ~15 KB per row. If binary churn ever becomes unacceptable,
  `export` writes a deterministic, text-diffable JSONL mirror of the same content
  — commit that instead, and keep the db local.
* **Schema version** is recorded in `schema_meta`. A db written by a *newer*
  writer is refused rather than read partially; older ones are migrated
  additively. This store never drops a column, because a dropped column is
  deleted evidence.

---

## Reuse: the store has no opinions of its own

Nothing about validity, cost bases or arm identity is re-decided here. The
adapter is imported and its own predicates are called: `classify_run`,
`_ungradable_kind`, `_row_provider_starved`, `_attempt_count`, `_ARMS` /
`arm_spec`, `_ARCHIVED_ROW_EXTRAS`, `_ARCHIVED_TRAJECTORY_GLOBS`,
`_NEVER_ARCHIVED`.

A second copy of any of those would be a second answer to "what counts", which is
the exact defect that forced the 2026-08-03 retraction: the sweep roll-up read
its status from the child's exit code while the report read it from
`result.json["error"]`, they disagreed, and two different denominators were
published for the same runs. `tests/test_benchmark_record_store.py` asserts the
delegation structurally.

## Reportable vs invalid

`reportable = 1` means **this row is a measurement of the arm**. Ask for it and
nothing else:

```sql
SELECT arm, COUNT(*), SUM(oracle_resolved) FROM run_attempt
WHERE reportable = 1 GROUP BY arm, cost_source, manifest_sha256;
```

Six ways a row is not that, each named separately in `invalid_reasons` because
they are different failures:

1. **not graded** — no oracle verdict on this attempt;
2. **`task_broken*`** — the *instance* is broken (OpenAI's 2026-07-08 audit found
   ~30% of SWE-bench Pro's public tasks broken);
3. **`grade_parse_failed`** — *this harness* could not read pytest's per-node
   report. A harness defect reported as an arm failure becomes a uniform 0% that
   looks like a finding;
4. **run failed / no result** — a crash is not an attempt;
5. **audit failed / not audited** — an unverifiable trail is not evidence;
6. **`provider-empty-response`** — the deployment refused requests and the engine
   swallowed it, so the row measures somebody else's queue at this sweep's
   concurrency. On 2026-08-11 an 18-wide sweep lost all 18 rows to 429s.

Plus one that is a property of the arm rather than the run: a **superseded run
key** (`ArmSpec.superseded_by`, e.g. `claude` → `claude-5`) is the same (harness,
model) pair re-measured under a later harness. Those rows are *kept* — they are
the "before" evidence for the retraction — and marked unreportable, because
reporting both would double-count one arm.

**A budget cap hit is NOT excluded.** Under pre-registered decision rule 4 a
`cost-cap` / `wall-clock-cap` / `phase-cap` / `turn-cap` hit is a completed,
counted, **flagged** attempt for every arm. The retracted run excluded a Claude
row that hit its turn cap *and passed the oracle*, silently improving its own
denominator; that is the failure the rule exists to prevent. Such rows are
`reportable = 1` and `budget_exhausted = 1`.

**Two things that are never blended, enforced in the queries, not by convention:**

* **cost bases.** `cost_source` is `NOT NULL` and every cost query groups by it.
  Azure price-table dollars (`derived-from-price-table`) and Claude-CLI
  subscription dollars (`claude-cli-reported`) are different units; a single
  `$/resolved` across both is arithmetic on incommensurable numbers. If an arm
  appears twice in `cost`, that is the store telling you its rows have two bases.
* **manifests.** A row from an older manifest is *history*, not an invalid row —
  this store spans datasets on purpose — but two manifests are two benchmarks, so
  `rates` and `cost` group by `manifest_sha256`. The first report after a dataset
  switch blended a SWE-bench-Pro row set with a swe-rebench one into a single
  100% headline; this makes that impossible rather than discouraged.

## Replay

`replay --instance <id> --arm <arm> [--attempt N]` emits an unambiguous record:
the code (both repo shas, with `git checkout` lines and a loud marker if either
was dirty), the pinned task, the configuration (arm, `max_steps`, `--workers`,
`thinking`, `skip_phases`, caps, price-table digest, registry entry), the exact
`run` / `grade` / `audit` commands, the **roster YAML verbatim** with an explicit
`# AGREE:` line comparing its digest to the one the row recorded, and finally
whether the replay is exact.

It does not execute. That is deliberate: executing would spend, and it would also
have to reconstitute a specific engine checkout. A record that hands you the sha,
the roster bytes and the command leaves the spend decision where it belongs.

### When exact replay is impossible, and why

Each of these is recorded as a caveat on the attempt rather than left to the
reader:

* **either checkout was dirty at capture.** Uncommitted code is not addressable by
  a sha, full stop. Both repos were dirty when today's rows were captured, so
  every one of them is `reproducible = 0` — correctly.
* **the git shas were captured at ingest, not at run time.** Rows written before
  provenance stamping existed carry no run-time sha, so the recorded values
  describe the checkout as it was at ingest and only bound the run from above.
  `git_sha_source` says which case a row is in. Fixed going forward:
  `_write_result` now stamps `provenance_stamp` (both repos' sha + dirty flag,
  plus the arm's registry entry) on **every fresh row**, so no arm can forget, and
  the ingester prefers it.
* **`--workers` was not recorded** for an attempt whose `sweep-<arm>.json` had
  already been overwritten. Concurrency drives provider throttling and therefore
  the result, so a missing value is declared, never defaulted.
* **the pinned manifest has moved** since the run (`manifest_sha256` ≠ the
  manifest's digest on disk now). Re-`fetch` the recorded manifest first.
* **the price table did not match its pinned sha256** at run time — the recorded
  dollars came from rates that had already moved.
* **the roster YAML is not on disk** for an sssf row (a later attempt deleted it),
  so the exact role/model wiring cannot be replayed byte-for-byte from the record.
* **the agent itself is not deterministic.** A replay re-runs the same
  configuration; it does not reproduce the same trajectory. It is a repeat of the
  experiment, not a replay of the recording — which is why per-attempt figures
  have to be *stored* rather than recomputed on demand.

## Verifying the trail

```
$ uv run python bench/swebench/benchmark_store.py verify
artifacts verified: 1586 ok, 0 gone (expected for superseded attempts), 0 MISMATCH
```

Three outcomes, and the middle one is the point. `ok` — bytes unchanged. `gone` —
no longer on disk, **expected** for a superseded attempt and the whole reason the
store exists. `MISMATCH` — the file is there and its digest changed, i.e. evidence
was altered after the fact. Only the third is a problem, and without a recorded
digest it would be invisible. `verify` exits non-zero on any mismatch.

Digests are the snapshot taken at first ingest: an unchanged `result.json`
short-circuits before they are re-read, deliberately, because silently refreshing
them would destroy the baseline `verify` compares against.

## Ingesting an archive

`results-archive/<ts>/` has the same `<instance>/<arm>/result.json` layout, so:

```bash
uv run python bench/swebench/benchmark_store.py ingest \
    --runs-dir bench/swebench/results-archive/2026-08-10T21-53-14.959258Z
```

Provenance is resolved against the directory being ingested, so an archive is
compared to its own manifest.

## What the store already says about choosing a model

Two of its columns settle something the decision doc could only project, and the
answer is one query away rather than one sweep away:

```sql
SELECT roster_model, SUM(calls), SUM(input_tokens), SUM(cache_read_tokens),
       ROUND(SUM(cost_usd), 4)
FROM role_usage WHERE skipped = 0 GROUP BY roster_model;
```

| roster_model | calls | fresh input | cached input | spend |
|---|---:|---:|---:|---:|
| `azure/DeepSeek-V3.2` | 1,364 | 51,724,304 | **0** | $30.98 |
| `azure/gpt-5.4` | 61 | 385,156 | 1,588,224 | $2.23 |
| `azure/DeepSeek-V4-Flash` | 122 | 1,195,969 | 3,802,624 | **$0.41** |

**V3.2's cache tier does not exist.** `models.json` prices its `cacheRead` at the
full input rate (0.580 per 1M) because that meter family publishes no cached tier —
and over 1,364 calls the provider reported **not one cached token**, so the pricing
was never even the binding fact. Every re-sent token of a 51.7 M-token pilot was
billed fresh, on a graph whose whole shape is re-sending a growing context to
several roles.

**Flash's is real, and it is most of the bill.** That $0.41 is one attempt —
`jsonpickle__jsonpickle-588` / `full-sdlc` / attempt 1, ran 2026-08-13, all four
roles on `azure/DeepSeek-V4-Flash`
(`show --instance jsonpickle__jsonpickle-588 --arm full-sdlc`, or
`roles --arm full-sdlc` for exactly this table):

| role | calls | fresh | cached | out | $ |
|---|---:|---:|---:|---:|---:|
| builder | 77 | 886,073 | 3,010,560 | 46,248 | 0.3053 |
| reviewer | 19 | 188,827 | 433,664 | 15,084 | 0.0615 |
| planner | 18 | 93,967 | 305,152 | 13,273 | 0.0366 |
| documenter | 8 | 27,102 | 53,248 | 2,805 | 0.0089 |

`steps_used = 13` with nothing skipped, oracle `resolved`, `audit_ok = 1`, 122
calls, **$0.4124**, 1999.8 s, `cost_source = derived-from-price-table`. The builder
was **77% cache-warm** — 3,010,560 cached tokens against 886,073 fresh, billed at
0.031 rather than its own 0.210 — which is the entire reason the most expensive graph
the engine can run (13 phases, four personas, three commits) came to 40 cents.

What it means when the next run has to pick a model:

* **A machinery-coverage run belongs on Flash, and belongs serially.** Its quota
  pools are both at 0 free, so it cannot be widened — but width was never what
  that kind of run needed, and at width 1 it completed the full graph with no 429
  and no empty-response turn (`empty_response_turns = 0` on all four roles).
* **A cost comparison against it is not a capability comparison.** This is
  **one instance, one attempt**. It is a measurement of the price of the graph, not
  of the model's resolve rate, and `reportable = 1` on a single row licenses
  neither. Read it as the cost axis only.
* **Cheap per token is not cheap per run.** V3.2 is 2.8× Flash's input rate and
  cost **75× more in total** across this store, because the pilot re-sent every
  token at V3.2's full 0.580 while Flash re-read three quarters of its context at
  0.031. When a candidate deployment's cached rate is absent or equal to
  its input rate, price the run as if every re-send is fresh — for these graphs
  that is the number that decides it.
* **Check the deployment's `compat` block before routing anything to it.** V3.2,
  `DeepSeek-V4-Flash` and `deepseek-v4-pro` all shipped without
  `compat.supportsDeveloperRole: false`, and without it Azure's DeepSeek serving
  422s every request while `pi` swallows it and returns an empty assistant message
  with all-zero usage — so the arm reports **$0.00 and an empty patch** instead of
  failing, which is a row that looks like a finding.
  `tests/test_benchmark_regressions.py` now asserts the flag for every DeepSeek
  deployment in the price table. The rates were not touched, so no dollar figure in
  this store moves; only the table's sha256 did (`provenance.price_table_sha256`).

## See also

* `bench/swebench/PRE-REGISTRATION-1.6.md` — the five arms, the five tables and
  the decision rules, fixed before the data existed. `report` emits exactly those
  tables; this store is the queryable substrate underneath them, not a substitute.
* `bench/swebench/README.md` — the harness, the arms and the sweep history.
* `/home/k/sssf/ai_docs/research/BENCHMARK-DECISION.md` — the thesis the sssf arms
  exist to test ("a cheap builder under a strong reviewer reaches the strong
  model's quality at a lower total cost than running the strong model alone") and
  why the instrument is SWE-rebench. The `chain` vs `v32-solo` vs `gpt54-solo`
  comparison this store holds is that experiment.
* `/home/k/sssf/ai_docs/research/BENCHMARK-IMPLEMENTATION-BRIEF.md` — the
  execution plan for building and running it.
* `POSTMORTEM-2026-08-11.md` — why the chain lost to one agent, and the four
  corrections. Read it before quoting any rate out of this store.
