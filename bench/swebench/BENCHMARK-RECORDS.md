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
