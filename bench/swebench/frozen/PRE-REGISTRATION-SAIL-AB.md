# Pre-registration — Sail Research vs Azure AI Foundry, provider A/B on the flash-solo shape

**Status: FROZEN 2026-08-27 (P-1). Never edited after this commit; supersede in
a living document and link back if anything here proves wrong.** Every TBD is
resolved; the one disclosed pre-freeze paid call (P-2c, $0.000009) is recorded
in the pre-freeze sequence below and in `../SAIL-DISCOVERY.md`. This document
was drafted, adversarially reviewed, reworked (CHANGELOG at the bottom), and
implemented over three dev/reviewer cycles before freezing.

**The frozen commit pair every campaign row must stamp
(`provenance_stamp`):**

- `sssf` engine repo: `eb9dcffd661c5228369cbab236a4ff13fe5fedff`
  (clean at freeze time).
- `software-factory` bench repo: **the commit that introduces this file at
  this path** (`git log --diff-filter=A --follow -1
  bench/swebench/frozen/PRE-REGISTRATION-SAIL-AB.md`); its first parent is
  `b5c49dd1e58b2ea178d7982ea95b1fc833c7c946`. Recorded as a rule rather than a
  hash because a commit cannot contain its own id; rows stamp the freeze
  commit itself, and `RESULTS-SAIL-AB.md` names it verbatim as its first line
  of evidence.
- `models.json` sha (final, post-P-2c):
  `eec3fa6889d33d5288b7ec8bcfc3c6ec3e2c4e2884a9f41cbfec30ab77a3ff6f`. Same discipline as `frozen/PRE-REGISTRATION-1.6.md` and
`frozen/PRE-REGISTRATION-B1.md` (paths as of this draft — both now live under
`frozen/`, not the bare `bench/swebench/` root): decision rules before data,
predictions falsifiable, every number carrying the query that re-derives it.

- Suite: **SWE-rebench**, pinned manifest `923aef05add32124` (seed 20260802,
  pool 215, 20 instances pinned, 19 working-oracle).
- Instance set: the **8-instance E5 subset** (listed below), n = 8.
- Arm vehicle: the **builder-only DeepSeek-V4-Flash shape** (`flash-solo`), no
  reviewer. A Sail-hosted reviewer arm is **out of scope**.
- Campaign hard cap: **$15.00 total**, enforced as described in "Budget",
  because the harness's spend guard is **per-sweep** and this campaign is many
  sweeps.
- Results artifact, named now: **`frozen/RESULTS-SAIL-AB.md`**. The frozen copy
  of this pre-registration is never edited after the freeze; everything
  measured lands there.

## Purpose

Qualify **Sail Research** (api.sailresearch.com, OpenAI- and
Anthropic-compatible, open-weight catalog) as the cheap inference substrate for
a later, much larger Genetic-Pareto pipeline-evolution campaign — **before**
spending anything real there. Three questions, in order, each gating the next:

1. **Is the harness correct on Sail?** No cross-run leakage, no shared state
   between arms/providers, validity detectors proven live against a planted
   leak — not assumed from green audits.
2. **What does Sail actually cost and tolerate?** Cost computed from usage ×
   pinned rates AND reconciled against Sail's own billing surface (tokens and
   dollars); per-call latency split out of wall time; rate-limit/width behavior
   measured, not assumed. **CORRECTED (note 12): Sail does not, in fact,
   claim "no rate limits"** — its public docs
   (`docs.sailresearch.com/rate-limits.md`) document a real per-model,
   per-organization-AND-global token-bucket limiter (429 org-exhausted, 529
   global-exhausted). "No rate limits" was this draft's own paraphrase, not a
   vendor claim; measured against a DOCUMENTED limiter, not an undocumented
   one. See `SAIL-DISCOVERY.md`.
3. **Does the same arm shape produce the same verdicts** as the Azure control,
   both re-run fresh on the current engine commit?

## Non-goals, stated before anyone quotes a cell

- **This is NOT a capability comparison.** n=8; only 4 of the 8 instances
  discriminate on the existing record; a paired test at n=8 needs 6 one-way
  discordant pairs to clear p<0.05. A 1-cell verdict difference between
  providers is **within instrument noise** and may not be quoted as a model or
  provider-quality finding. This is an infrastructure and cost qualification.
- The `flex` completion window is **deferred**: it requires background/Batch
  semantics and the harness drives synchronous streaming calls through `pi`.
- A Sail-hosted reviewer arm, and any multi-role graph on Sail, are out of
  scope.
- E5 rows (2026-08-14/15) are **priors, not comparators**: the engine changed
  since (stderr-drain deadlock fix, `EmptyResponse` handling, gate fixes), so
  every comparison row in this campaign is run fresh on one frozen commit pair.

## Treatment definition

**The treatment is the provider as a whole** — weights-as-served (including
quantization, e.g. an `-FP8` suffix), serving stack, completion-window tier,
price card, and rate limits — never price alone. Sail serves the same DeepSeek
V4 Flash **family** as Azure's `DeepSeek-V4-Flash` deployment, but the serving
details may differ; a verdict flip is therefore attributable to "provider", not
to any single component. Every row records the **exact model id as served** in
the roster and provenance, and any row whose trace-observed model id differs
from the pinned catalog id is invalid (rule R8).

| | control | treatment |
|---|---|---|
| paired-sweep arm id | `flash-solo-az-r2` | `flash-solo-sail` |
| probe arm ids | — | `flash-solo-sail-p1` (Phase 1), `flash-solo-sail-wprobe` (Phase 2) |
| provider | `azure` (`mv-coding-agent-foundry…/openai/v1`) | `sail` (base URL from docs, pinned in models.json) |
| model id | `DeepSeek-V4-Flash` | `deepseek/deepseek-v4-flash-0731` — RESOLVED pre-freeze via `GET /v1/models` (free), verbatim, no quant suffix; see `SAIL-DISCOVERY.md` |
| tier | n/a | `asap` — RESOLVED pre-freeze: `docs.sailresearch.com/pricing.md` lists exactly ONE completion window for this model, "Default (asap)"; no `balanced` or `flex` row exists for it (contrast GLM-5.2/Kimi-K2.6/Gemma, which publish both). Not a latency choice — the model's only tier. Still confirmed LIVE in Phase 1 per the compat/tier probe below; recorded per row |
| API key env | `AZURE_API_KEY` | `SAIL_RESEARCH_KEY` (new; never written to any roster, trace, or archived file) |
| width | 1 (measured ceiling, `max_workers=1`) | 1 for `-p1` and the paired sweep; `-wprobe` declares `max_workers=4`, deliberately, because measuring width is its whole job |
| sandbox | `SWEBENCH_SANDBOX=1` on **every** campaign run, all phases, both providers | identical |
| roster | builder only, planner/reviewer/documenter = None | identical (all four arm ids share one roster shape) |
| everything else | identical: engine commit, bench commit, manifest, story template, caps, wall clock, TMPDIR/workdir isolation, grading, audit | identical |

**Why THREE Sail arm ids and a NEW Azure id.** The store's row-selection rule
is **first valid attempt by `ran_at`** per (instance, arm). One shared Sail id
would make the Phase-1 compat/tier row and the Phase-2 width rows the
*selected* rows for their cells in every later query — probe rows deciding R3
and R6. So: `flash-solo-sail-p1` and `flash-solo-sail-wprobe` are probe arms
whose rows are **never verdict or cost-ratio evidence**, and the first rows
ever written under `flash-solo-sail` are Phase 3's. Likewise fresh control
rows under the old `flash-solo` id would lose first-valid selection to the
2026-08-14 rows and mix engine builds inside one arm; `flash-solo-az-r2` is a
new registry entry with its own cells, and the old `flash-solo` rows stay
untouched as the prior. All four new registry entries declare
`default_cost_usd = 0.50` (the spend guard's fallback with no measured rows —
~3× the most expensive measured flash-solo cell, fail-safe upward) and
`max_workers = 1`, except `-wprobe` at 4 with a loud registry comment.

**Sandbox mandate.** Two contamination channels are known-open outside the
sandbox and E5 left them open only for comparability with completed cells —
a reason that does not apply here, where everything reruns fresh: literal
`/tmp` (the role prompts instruct agents to use it; per-run `TMPDIR` does not
cover literal paths; nothing detects reads there) and the shared trace/ledger
db. The built bubblewrap sandbox (`SWEBENCH_SANDBOX=1`) closes both: private
tmpfs `/tmp`, blanked `$HOME` but for `~/.pi/agent/models.json`, relocated
ledger. Every campaign row must record the sandbox flag in its provenance; the
harness already refuses to run unisolated under a provenance that says
isolated, and P0.5(a) proves the closure empirically before any paid call.
**`SWEBENCH_SANDBOX_DOCKER` must be `broker` (the default) or `none` on every
campaign run; `raw` voids P0.5a** (note 16) — `raw` binds the real
`/var/run/docker.sock` into the namespace, and a container can then
`docker run -v /tmp:/x ...` to reach the HOST's `/tmp` from inside, defeating
the private-tmpfs closure this whole mandate rests on.

## Instances

The 8 E5 instances, re-derived by
`sqlite3 benchmarks.db "SELECT DISTINCT instance_id FROM run_attempt WHERE arm='flash-solo' AND reportable=1 ORDER BY instance_id"`:

`alibaba__opensandbox-816`, `getmoto__moto-9841`, `harumiweb__exstruct-113`,
`hkuds__openharness-217`, `idaholab__montepy-933_interface`,
`keras-team__keras-22316`, `pyinfra-dev__pyinfra-1665`,
`zauberzeug__nicegui-5858`.

Prior on this arm shape (prior only, not a comparator): 16 reportable
`flash-solo` rows over these 8 cells, **unanimous within every cell**
(published headline 4/8). On that prior the cells split three ways, and the
split is load-bearing for R3:

- **ceiling** (always solved): `hkuds__openharness-217`,
  `zauberzeug__nicegui-5858`;
- **floor** (never solved): `alibaba__opensandbox-816`,
  `harumiweb__exstruct-113`;
- **discriminating** (the only cells that can carry information):
  `getmoto__moto-9841`, `idaholab__montepy-933_interface`,
  `keras-team__keras-22316`, `pyinfra-dev__pyinfra-1665`.

## Measures — each with its source of truth and re-derivation

| measure | source of truth | re-derivation |
|---|---|---|
| **verdict** | hidden oracle on the stripped production diff; `reportable = 1` rows only; **paired-sweep arm ids only** | `SELECT instance_id, arm, attempt, oracle_resolved FROM run_attempt WHERE reportable=1 AND arm IN ('flash-solo-az-r2','flash-solo-sail') ORDER BY instance_id, arm, attempt` |
| **computed cost** | `result.json.cost_usd` = measured usage × pinned `models.json` rates (`cost_source = derived-from-price-table`); rates snapshotted per attempt in `price_rate`; plus the fixed `preflight_probe_cost_usd` constant from P-2 | `SELECT arm, ROUND(SUM(cost_usd),4) FROM run_attempt WHERE reportable=1 AND arm IN ('flash-solo-az-r2','flash-solo-sail','flash-solo-sail-p1','flash-solo-sail-wprobe') GROUP BY arm, cost_source, manifest_sha256` — cost tables always name the arm, so probe spend never blends into the R6 ratio |
| **billed usage (Sail)** | Sail's billing surface as pinned in P0.0 — **token counts AND dollars, gross before free-credit netting**, captured no earlier than T+24h after the rows, pasted verbatim (screenshot/export) into `RESULTS-SAIL-AB.md` with timestamp | manual; deltas per rule R2 |
| **wall time** | `result.json.wall_clock_s` per row (durable, coarse) | `SELECT arm, instance_id, attempt, wall_clock_s FROM run_attempt WHERE …` |
| **per-call latency** | the row's archived `sssf-events.jsonl`: per model call, `request_to_response_s` (queue wait + generation, combined), extracted for the Phase-1 row and one full Phase-3 Sail pass. **CORRECTED (note 13): request→first-token and first-token→last-token, as this row originally named them, are NOT separable from this trace format** — `sssf-events.jsonl` records one landed-turn timestamp per model call, not token-level streaming chunks; a `tool_call` event's `started_at`/`ended_at` pair brackets the TOOL's own execution, not the model's. `latency_from_trace.py` reports both legs as explicit `null` on every call rather than a guessed split, alongside the one real, measured interval. See `SAIL-DISCOVERY.md` for the trace-level evidence. | `bench/swebench/latency_from_trace.py <run_dir>` (committed to the bench repo before the P0.1 freeze; operates only on archived event streams, $0) |
| **width behavior** | `empty_response_turns`, `provider_starved`, `termination = 'provider-empty-response'` per row of the width-probe arm | `SELECT arm, instance_id, attempt, empty_response_turns, provider_starved, termination FROM run_attempt WHERE arm='flash-solo-sail-wprobe'` |
| **validity accounting** | `reportable`, `invalid_reasons`, `audit_ok`, `env_leak`, `budget_exhausted` — every excluded row named with its class, none silently dropped | `benchmark_store.py validity` |

Cost bases are never blended: Azure and Sail dollars are both
`derived-from-price-table` but under **different rate cards**; every cost table
groups by arm. Billed-vs-computed reconciliation exists precisely because a
pinned rate card for a new vendor is a **self-reported claim until reconciled**.

## Pre-freeze sequence (P-2 → P-1) — resolves compat vs sha-pin vs freeze

The compat flag, the whole-file models.json sha pin, and the repo freeze would
otherwise be mutually inconsistent (a post-freeze compat edit moves the sha →
`matches_pinned=false` on every later row; re-pinning violates the freeze). So
compat is resolved **before** the freeze, in this order:

1. **P-2a Rate card + billing surface. RESOLVED pre-freeze, via free calls
   only — no logged-in dashboard was needed.** `GET /v1/models` (free,
   bearer-authed) gave the exact catalog id verbatim:
   `deepseek/deepseek-v4-flash-0731` (no quant suffix). The PUBLIC docs
   (`docs.sailresearch.com/pricing.md`, `/completion-windows.md`) gave the
   synchronous tier — `asap`, the model's ONLY completion window, not a
   latency choice — and **absolute** rates for it: input $0.09, cached input
   $0.02, output $0.18, all per 1M tokens. `docs.sailresearch.com/usage.md`
   pins the billing surface's shape: BOTH token counts and dollars
   ("Monetary fields are fractional USD cents (floats), and token fields are
   raw token counts"), gross spend alongside credit balance/burn rate (so net
   is derivable), with billing fields lagging operational ones by an
   undisclosed amount ("may have a slight delay") — consistent with, not
   shorter than, this draft's T+24h reconciliation floor. A
   screenshot/export of the actual account dashboard once real rows exist
   still belongs in `frozen/RESULTS-SAIL-AB.md` per the Measures table; the
   RATE CARD and the billing surface's REPORTED FIELDS did not require it.
   Full evidence trail, including exactly which free call produced which
   number: `SAIL-DISCOVERY.md`.
2. **P-2b models.json entries.** New `sail` provider block: `baseUrl`,
   `api: openai-completions`, `apiKey: SAIL_RESEARCH_KEY`, the model entry with its
   `cost` block. `compat` left unset for one step.
3. **P-2c Compat reachability probe — the one disclosed pre-freeze paid call.**
   The adapter's existing preflight reachability probe, which sends exactly
   the role layout `pi` sends (i.e. it exercises the `developer` role), against
   the Sail endpoint. Cost ~$0.000001, hard cap **$0.01**, recorded as
   `preflight_probe_cost_usd` and added to the campaign ledger and to R2's
   computed side. Set `compat.supportsDeveloperRole` from the result.
   **RUN 2026-08-27 via `_sssf_reachability_report` on
   `sail/deepseek/deepseek-v4-flash-0731`: HTTP 200, `system_role_sent:
   developer`, reachable, non-empty reply — so `compat.supportsDeveloperRole:
   true`, MEASURED. Usage 12 in / 44 out / 0 cached;
   `preflight_probe_cost_usd = $0.000009` at the pinned rates (under the $0.01
   cap). One earlier invocation misspelled the id (`sail/deepseek-v4-flash…`,
   missing the model id's own slash) and was refused at the catalog layer for
   $0.00 — disclosed here because the ledger counts attempts, not successes.
   Full record: `SAIL-DISCOVERY.md` § P-2c.**
4. **P-2d Re-pin `_PI_PRICE_TABLE_SHA256`. DONE 2026-08-27 — the FINAL pin.**
   After P-2c wrote the measured `compat.supportsDeveloperRole: true`, the
   whole-file hash moved to
   `eec3fa6889d33d5288b7ec8bcfc3c6ec3e2c4e2884a9f41cbfec30ab77a3ff6f` and the
   adapter constant was re-pinned to it. Re-verified after the compat edit:
   the delete-sail-and-rehash recipe (SAIL-DISCOVERY.md) still reproduces the
   original `fbab9ac0…c45a`, so the edit touched only the sail entry and every
   archived dollar figure stands. **This is the pin P-1's freeze binds to.**
   The interim history below is kept as the record of the ordering:
   (was) PENDING — interim pin only, FINAL
   re-pin happens after P-2c (note 17). This ordering is the one C2 set —
   rate card → models.json (rates + compat) → sha re-pin → registry →
   commit → freeze — and pinning before P-2c set compat would invert it:
   `compat` is still unset on the `sail` entry, so the hash below covers a
   models.json that P-2c is guaranteed to edit, and P-1's freeze must not
   happen against this interim value. Current INTERIM state: was
   `fbab9ac067086c6a6d89925302a3e4c9e87b780100a82e59684a40c98687c45a`, now
   `dd22d0f5270386daed59d7afde1269c3e02357e8608ff7752ddc44337643cf8a` — adding
   the `sail` provider (rates, no compat yet) moved the whole-file hash while
   changing no Azure rate; every azure/azure-responses id and rate verified
   byte-for-byte before this interim re-pin
   (`tests/test_benchmark_regressions.py::
   test_every_deepseek_deployment_declares_supportsdeveloperrole_false` and
   friends, green — that test's own `sail` branch now accepts EITHER no
   compat block OR one with a real boolean `supportsDeveloperRole`, never a
   guess). The four registry entries and `latency_from_trace.py` are added;
   **not yet committed** — left in the working tree for review per this
   task's instructions. **A second re-pin is required once P-2c runs and
   sets `compat.supportsDeveloperRole`, before P-1's freeze** — this
   document's own commit is not that freeze.
5. **P-1 Freeze.** Both repos (`sssf` engine, `software-factory` bench)
   committed and **clean** — the store marks dirty-checkout rows
   `reproducible = 0`, and both repos are dirty as of this draft. The two shas
   are written into the frozen copy of this document and stamped on every row
   via `provenance_stamp`; any row carrying a different or dirty sha is
   invalid. Every row must record `provenance.matches_pinned = true`.

## Harness-correctness protocol — Phase 0, zero paid calls

All of Phase 0 is $0 and blocks everything after it.

- **P0.0 Billing-surface pin** — done in P-2a; re-verify the export is attached.
- **P0.1 Freeze verification.** Both shas clean and equal to the frozen values.
- **P0.2 `selftest` per instance, for the 8 campaign instances only** (the
  manifest's 20 include a known non-working oracle that would stall a
  whole-manifest selftest). Gold patch must grade RESOLVED on all 8 (docker +
  oracle only, no model).
- **P0.3 Free plumbing check, unconditional**: `run-all --dry-run` for all four
  arm ids (work list + projected spend, spawns nothing), and
  `--probe-plumbing` for `flash-solo-sail-p1` and `flash-solo-az-r2` —
  implemented for sssf arms (`probe_plumbing` in `run_sssf`).
  **CORRECTED (note 15): `--probe-plumbing` does NOT exercise key or
  endpoint resolution for sssf arms, and there is no reply script.** For
  these arms it exercises clone, prepare, collect precheck, roster
  synthesis/validation and the `result.json` write; it calls no model and
  does NOT resolve the Sail key or base URL — reachability is explicitly
  SKIPPED under `probe_plumbing=True` (`run_sssf`, ~10559-10563), and the
  credential precheck `_sssf_child_env` runs regardless is hardcoded to
  `AZURE_API_KEY` (~5894, ~7966-7974), so it cannot surface a missing
  `SAIL_RESEARCH_KEY` or a wrong Sail base URL either way. Sail key/endpoint
  resolution is proven ONLY by the P-2c reachability probe, whose ≤$0.01 is
  already disclosed above. The probe row is fail-closed (records an `error`)
  and is wiped by the first real run.
- **P0.4 Detector regression — staged replay of the real contamination.**
  `audit` only reads live `runs/<instance>/<arm>/`, so: copy the archived
  `harumiweb__exstruct-113 / flash-chain` attempt-2 artifacts into
  `runs/harumiweb__exstruct-113/flash-chain/`, run `audit`, and assert it fails
  with the known finding (`audit failed: foreign-workdir: sssf-events.jsonl:152 …`).
  A detector that no longer catches the historical positive has regressed →
  ABORT. **CORRECTED (note 10): those attempt-2 BYTES are gone, but the
  incident is REAL and confirmed.** `benchmarks.db` holds the row verbatim
  — (harumiweb__exstruct-113, flash-chain, attempt 2) — with its recorded
  audit finding: `audit failed: foreign-workdir: sssf-events.jsonl:152 named
  another arm's working tree ['harumiweb__exstruct-113__v32-solo',
  'harumiweb__exstruct-113__bare']`, plus artifact digests
  (`sssf-events.jsonl` 786,524 B, sha256 `a2dccb282fd9…`; `audit.json` 2,421
  B). The bytes themselves were overwritten on disk by attempt 3 before this
  task started (`runs/` is gitignored, so there is no history to recover them
  from), and a re-scan of every currently-archived events file finds zero
  command-side foreign hits — confirming the bytes are gone, not that the
  incident didn't happen. `bench/swebench/phase0_sail_ab.py p0_4-stage`
  RECONSTRUCTS the positive from the store row's own recorded cells
  (`_P0_4_FOREIGN_CELLS`) rather than requiring the lost bytes verbatim; see
  `SAIL-DISCOVERY.md` for the full reconstruction rationale.
- **P0.4b Delete the staged dir** `runs/harumiweb__exstruct-113/flash-chain/`
  — its own checklist step, completed **before any `record`** so the staged
  copy can never be ingested.
- **P0.5a Sandbox proof — the run must be UNABLE to see a planted /tmp file.**
  Write a marker file at a literal `/tmp` path (e.g.
  `/tmp/report.json`, the name 13 different adw_ids collided on in E5), run a
  `--probe-plumbing` row under `SWEBENCH_SANDBOX=1` whose scripted reply reads
  that literal path, and require the read to come back **not found** (private
  tmpfs). If the marker is visible inside the sandbox, the known-open channel
  is still open → ABORT. **CORRECTED (note 14): no `--probe-plumbing`
  scripted-reply hook exists for sssf arms** — `run_sssf`'s own docstring: a
  probe-plumbing row "spends NOTHING and calls no model: the ADW is never
  invoked at all" — nothing runs a reply script, scripted or otherwise, for
  these arms. (The fixed-reply mechanism that DOES exist,
  `_BARE_PROBE_REPLIES`, belongs to the unrelated `bare` arm and answers a
  hardcoded four-line script written for that arm's own parser branches.)
  `bench/swebench/phase0_sail_ab.py p0_5a-check --inside-sandbox` instead
  drives the adapter's own `_sandbox_argv`/`_sandbox_probe` directly — the
  same primitives `tests/test_swebench_sandbox_isolation.py::
  test_slash_tmp_is_private_and_must_exist` already exercises for this
  property. Verified: PASS, see `SAIL-DISCOVERY.md`.
- **P0.5b Detector proof — the audit must catch a leak we insert.**
  `--probe-plumbing` for sssf arms never invokes an agent, so the leak is
  synthesized at the trace layer: stage a run dir from a copy of a real
  archived `sssf-events.jsonl`, append a read event naming a planted foreign
  path (`runs/<other-instance>/<other-arm>/…`), run the auditor over the staged
  dir, and require the finding string
  `audit failed: foreign-workdir: sssf-events.jsonl:<line>` naming the planted
  path. **CORRECTED (note 11): the planted path shape above does not match
  what the live detector matches on.** `_foreign_workdir_hits`/
  `_WORKDIR_CELL` in `bench/swebench_adapter.py` fires on
  `swebench-work/<instance>__<arm>/...` (the scratch-root cell naming
  convention, confirmed against a real archived trace), not on a `runs/...`
  path — a planted `runs/<other-instance>/<other-arm>/…` path would not trip
  the detector at all. `bench/swebench/phase0_sail_ab.py p0_5b-stage` plants
  `/home/k/.cache/swebench-work/<foreign-cell>/repo/planted.txt` instead.
  Verified end to end: PASS, exactly one finding at the planted line, see
  `SAIL-DISCOVERY.md`. If the audit passes the planted leak, **no green audit
  in this campaign
  means anything: ABORT, fix the detector, restart Phase 0.** Delete the staged
  dir (same rule as P0.4b) before any `record`.
- **P0.6 Provider-isolation preflight — only what is checkable.** Assert with a
  $0 script: the two key values differ; `models.json` routes each provider to
  its own key var (`azure*` → `AZURE_API_KEY`, `sail` → `SAIL_RESEARCH_KEY`); no
  `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` / `NO_PROXY` in the operator
  shell; the two providers' `baseUrl`s differ; per-run `TMPDIR`, PATH stripped
  of `*/.venv/bin`, `PYTHONNOUSERSITE=1`, fresh workdir per attempt — carried
  over from E5's closures and re-asserted. **NOTE:** `_sssf_child_env` copies
  the full parent env, so **both keys reach both arms' children**; per-arm
  key scoping is a desirable harness change but is out of scope here. The
  residual risk is accepted, recorded under Threats, and backstopped by P0.7.
- **P0.7 Key-hygiene scan**, run again at every ingest: grep every archived
  artifact and trace of this campaign for the literal `SAIL_RESEARCH_KEY` value and
  the Azure key value. **Zero hits required**; any hit aborts the campaign and
  rotates the key before anything else happens.

**Audit staleness rule (the E5 structural weakness, closed for this campaign
by the cheaper of the two options):** `audit_ok` is read from the archived
`audit.json` at ingest, not re-derived, so a row audited before a detector
existed keeps a stale green. For every row of this campaign, **`audit` is
re-run immediately before `record`** (a $0 local re-derivation over artifacts
that still exist at that moment) so `audit_ok` reflects the frozen detector
set; the frozen bench sha on the row identifies that detector set. This is
procedure for THIS campaign, not the structural fix, which stays open.

## Phased execution — budgets and stop conditions

The engine-side caps (`_BENCH_ROOT_CAPS` $40/$40) and the run-all spend guard
are **per-sweep**: an N-sweep campaign gets N× whatever they allow. They stay
as backstops; the binding cap is the **campaign ledger** below.
**The operator-visible number is `factory_settings.yaml`'s hourly/daily
caps** — every `run-all --dry-run` prints them (verified: `spend: ...
projected $0.50 total, $0.50/h peak vs caps $300.00/h, $300.00/day`) —
**$300.00/h, $300.00/day, PER SWEEP.** That is 20× this campaign's entire
$15.00 hard cap, so seeing a dry-run's "vs caps" line come back green proves
only that one sweep would not trip the engine's own backstop; it is
explicitly NOT a bound for this campaign, which is why the campaign ledger
below exists as a separate, operator-enforced check.

**Budget.** Campaign hard cap **$15.00 computed**. Phases 1–2 are targeted to
fit inside Sail's $5 monthly free credits — but the free credits are a
**masking threat**, so every reconciliation uses gross usage, and adoption math
uses computed-at-pinned-rates dollars, never the netted bill. Enforcement:
after **every** sweep, every phase boundary, and every 4 rows of Phase 3, run
`sqlite3 benchmarks.db "SELECT ROUND(SUM(cost_usd),4) FROM run_attempt WHERE arm IN ('flash-solo-sail','flash-solo-sail-p1','flash-solo-sail-wprobe','flash-solo-az-r2') AND ran_at >= '<campaign_start>'"`,
add `preflight_probe_cost_usd` and any spend visible in `runs/` not yet
ingested, and record the total in `RESULTS-SAIL-AB.md`. Total ≥ $15.00 → the
campaign stops, whatever phase it is in.

| phase | arm id | what | paid calls | phase cap (computed) | stop condition |
|---|---|---|---|---:|---|
| 0 | — | harness verification above | **zero** (P-2c's ≤$0.01 probe is pre-freeze overhead, already spent) | $0 | any P0 item fails → ABORT |
| 1 | `flash-solo-sail-p1` | ONE instance on Sail at width 1: `hkuds__openharness-217` (cheapest known cell: $0.0154–0.0329 across 3 reportable Azure attempts) — run, grade, audit, ingest; confirms the tier accepts plain synchronous streaming and that the trace-observed model id equals the pinned catalog id; then **STOP and reconcile**: token counts immediately, dollars no earlier than T+24h per R2. Never verdict evidence. | 1 row | $0.50 | token reconciliation outside R2 → stop; empty turns > 0 at width 1 → stop and investigate; model-id mismatch → stop and re-pin (R8) |
| 2 | `flash-solo-sail-wprobe` | width probe on Sail: `hkuds__openharness-217` + `zauberzeug__nicegui-5858` at width 1 → 2 → 4, watching `empty_response_turns` / `provider_starved` / 429 signatures. Width w is "clean" iff every row at w has zero empty turns and no provider-starved refusal. Stop ascending at first non-clean width. Rows are width evidence, **never** verdict or cost-ratio evidence. Dollar band of R2 re-evaluated at this boundary. | ≤ 6 rows | $1.50 | first non-clean width ends the probe; ≥2 provider-starved rows in one pass → stop the pass |
| 3 | `flash-solo-az-r2`, `flash-solo-sail` | the paired sweep: all 8 instances, Azure k=1 and Sail k=2 (flip check), **both at width 1** regardless of Phase 2 (comparability with the Azure control, which is hard-capped at 1). Interleaved, pre-declared: walk the 8 instances in the alphabetical order above; for even-indexed instances (0-based) run Azure-then-Sail, for odd-indexed Sail-then-Azure; the second Sail attempt runs as a separate full pass after the paired pass completes. **Every row is launched as `run-all --arm <one arm> --instances <one instance>`** — never bare `run` — so the spend guard's projection + actual-spend recheck engages on every row. Ledger check every 4 rows. Ingest (with re-audit) after every pass. R2's dollar leg re-evaluated at the final boundary. | 24 rows | $10.00 | campaign ledger ≥ $15 → stop; ≥ 3 audit-invalid rows in any single pass → stop and investigate; ≥ 2 provider-starved rows in one pass → stop the pass |

Re-run policy: `frozen/PRE-REGISTRATION-1.6.md` Rule 5 by reference — an audit-invalid
row is published invalid, never re-rolled; a budget-cap row is a counted,
flagged attempt; an infrastructure loss (429/starved row, sandbox crash) may be
repaired **once** per cell, disclosed, both attempts recorded. `record` runs
after every pass because attempts overwrite on disk.

## Predictions (falsifiable, written before any Sail call)

1. Sail width behavior differs from Azure's: **clean at width 2** (Azure Flash
   429s there). If Sail also fails at width 2 — i.e. its documented
   per-organization token bucket (see note 12) binds this workload that
   early — R5's serial-only constraint applies.
2. Sail agrees with the fresh Azure control on **4/4 discriminating cells** and
   flips **no** floor/ceiling cell; Sail's own k=2 is unanimous on 8/8 cells.
3. Computed-vs-billed token counts reconcile exactly; dollar divergence ≤ 10%
   at the Phase-2 boundary, against the rate card resolved pre-freeze from
   public docs (note 8/`SAIL-DISCOVERY.md`) and reconciled at Phase 1/2
   against the account's own billing surface.
4. Sail $/task lands within **0.5×–2×** of the fresh Azure control's $/task.

## Decision rules — pre-declared, numeric

The adoption claim under test: **"Sail is qualified as the substrate for the
evolution campaign."** Evaluated only after Phase 3 ingest, in this order; the
first failing rule decides. Shared definitions, declared once: every
agreement/cost figure is computed on the **first valid attempt per
(instance, arm)** within the named arm id; a cell lacking a valid row on
either side drops from numerator AND denominator; thresholds are fractions of
evaluable cells.

1. **R1 — harness correctness (gate).** P0.4, P0.5a and P0.5b all caught (or
   were blinded to) their planted leaks as specified, every campaign row ran
   under `SWEBENCH_SANDBOX=1` (asserted in provenance), and zero campaign rows
   carry `env_leak = 1` or a foreign-workdir finding. Fail → **abort**; nothing
   downstream is evaluable.
2. **R2 — cost integrity.** (a) **Tokens** (evaluated at Phase 1): billing-
   surface token counts equal usage-reported token counts within ±1% per
   category, read no earlier than T+24h. (b) **Dollars** (evaluated at the
   Phase-2 and Phase-3 boundaries, where the base is large enough for a
   percentage to mean something — 10% of the Phase-1 row alone is $0.002–0.005
   and decides nothing): |billed_gross − computed| / computed **≤ 10%**.
   10–25% → **investigate** before the next phase (wrong rate pinned, hidden
   tier multiplier, cache-read metering mismatch); the divergence is itself a
   finding and is published either way. > 25% → **do not adopt** until the rate
   card is fixed and Phase 1 is repeated. If gross dollars are unavailable
   (per the P-2a pin), R2 is evaluated on token counts and the dollar check
   moves to the final boundary, against whatever dollar figure the surface does
   expose, labeled as such.
3. **R3 — verdict agreement**, on `flash-solo-sail` vs `flash-solo-az-r2` rows
   only. Evaluable only if **≥ 6 cells are evaluable, of which ≥ 3
   discriminating**; otherwise the campaign stops short of any adoption
   sentence. (a) Sail self-agreement: k=2 unanimous on all evaluable cells;
   any split cell → investigate that cell's traces; adoption may then proceed
   **only with a published explanation of the split in
   `RESULTS-SAIL-AB.md`** — no explanation, no adoption. (b) Cross-provider
   agreement is scored on the **discriminating cells only**
   (`getmoto__moto-9841`, `idaholab__montepy-933_interface`,
   `keras-team__keras-22316`, `pyinfra-dev__pyinfra-1665`): **4/4 → pass;
   3/4 → investigate (same terminating branch as R3a); ≤ 2/4 → do not adopt**
   — the provider-as-served is behaving as a different model and must be
   re-qualified as one. Floor/ceiling cells are instrument-sanity checks: any
   flip there is a loud anomaly → investigate before anything else is read.
   *Why the previous ≥6/8 rule was replaced:* with 4 cells at floor/ceiling
   agreeing structurally, a provider flipping each discriminating cell by a
   fair coin still passed ≥6/8 with probability **≈ 0.69** — a rule that a
   coin passes two times in three is not a rule. No individual flip is quoted
   as a capability finding (see Non-goals).
4. **R4 — transport cleanliness.** **0 unexplained `empty_response_turns`**
   across all width-1 campaign rows on Sail. Any empty turn at width 1 →
   investigate (compat flag? tier timeout?) before adoption; the affected row
   is already refused by the existing detector.
5. **R5 — width.** Minimum clean width from Phase 2: **≥ 2** → adopt for
   parallel evolution use; **= 1** → **adopt-with-constraint** (serial-only,
   which multiplies evolution-campaign wall clock and must be priced into that
   campaign's own pre-registration, exactly as Azure Flash's ceiling was).
6. **R6 — cost ratio**, `flash-solo-sail` vs `flash-solo-az-r2` rows only
   (probe-arm spend excluded by arm id): Sail $/task ≤ **1.5×** the fresh
   Azure control's $/task at equal-or-better R3 outcome → adopt on cost;
   1.5×–3× → adopt-with-constraint (no cost-advantage claim may be made);
   > 3× → do not adopt on cost grounds, whatever R3 says.
7. **R7 — key hygiene.** P0.7's scan at final ingest: zero hits, or abort +
   rotate.
8. **R8 — model-id fidelity.** Any row whose trace-observed model id differs
   from the pinned catalog id is **invalid**, the pass stops, and the pin is
   re-derived before anything else runs.

Failure handling is per-rule as written; "investigate" outcomes suspend
adoption until the investigation is appended to `RESULTS-SAIL-AB.md` with its
own evidence paths, and terminate in adopt-with-published-explanation or
do-not-adopt — never in silence. No rule may be re-thresholded after data
exists.

## Threats to validity

- **Same family ≠ same model.** Sail may serve a quantized (e.g. FP8) or
  otherwise differently-configured build of the V4 Flash family. The design
  treats provider as the whole treatment; no result here separates weights
  from serving stack. A verdict disagreement is a provider-level finding only.
- **Completion-window tier confound.** Tier trades latency for price; the
  tier is on every row for exactly this reason, and cost/latency claims do
  not transfer across tiers. **CORRECTED (note 18): the per-call split this
  bullet used to promise (request→first-token vs generation) is NOT
  recoverable from `sssf-events.jsonl`** (note 13) — the trace records one
  landed-turn timestamp per model call, not streaming chunks. What IS
  measured, per call, is `request_to_response_s` (queue wait + full
  generation, combined), via `latency_from_trace.py`; that combined figure
  is what separates tiers here, not a first-token/generation split.
- **Free credits mask real cost.** $5/month free credit nets the bill toward
  zero; all reconciliation uses gross usage where exposed (pinned in P-2a),
  all adoption math uses computed dollars at pinned rates.
- **Self-reported price card.** The Sail rates are the vendor's claim until R2
  reconciles them. **CORRECTED (note 19): resolved from public docs, not the
  logged-in account** — `docs.sailresearch.com/pricing.md` is the vendor's
  own PUBLISHED rate card for this tier, the same kind of source Azure's
  table in `models.json` was originally re-verified against
  (`prices.azure.com`, a public retail API); a public price page is not a
  weaker claim than a dashboard screenshot, only a differently-shaped one.
  It is still self-reported until R2's billed-vs-computed reconciliation
  converts the claim into a fact — which is what "self-reported" names here,
  not the absence of a login.
- **Per-sweep spend guard multiplies.** The harness cap is per-sweep; this
  campaign is ≥ 6 sweeps. The campaign ledger above is the only campaign-level
  bound, and it is operator-enforced, which is a weakness disclosed here.
- **Both API keys reach both arms' children.** `_sssf_child_env` copies the
  full parent env and the key var is hardcoded; per-arm scoping is out of
  scope. Accepted residual risk, backstopped by P0.7's artifact scan.
- **Stale audits.** `audit_ok` is not re-derived at ingest; closed for this
  campaign by procedural re-audit before `record`, not structurally.
- **Engine drift.** E5 numbers are priors only; both comparators are fresh on
  one frozen commit pair, and any mid-campaign engine fix voids completed
  passes for pairing purposes (disclosed, re-run under the re-run policy).
- **`pi` swallows provider refusals** (429s and 422s become empty turns with
  all-zero usage). The empty-turn detector is the only guard; Phase 0 proves
  the audit path, P-2c proves the compat flag, and no row with empty turns is
  ever reportable.

## What this experiment cannot establish

- Any capability difference between providers or models: n=8, MDE far above
  any plausible provider effect; two instances sit at floor and two at ceiling
  on the prior, so only four cells carry information at all.
- Anything about `flex`/batch semantics, Anthropic-compatible endpoints, other
  Sail catalog models, or reviewer-bearing graphs on Sail.
- Sail behavior at evolution-campaign scale (sustained load, monthly quota
  behavior, price stability). This qualifies the instrument, not the campaign.
- Where Sail's documented token-bucket limiter (note 12) actually binds above
  width 4 — Phase 2 stops there.

## Reporting rule

No Sail number is reported without the fresh Azure control beside it; no
number without its store query and its arm id; probe-arm rows are reported in
their own tables, never beside verdict evidence. `RESULTS-SAIL-AB.md` names
the frozen commit pair, the models.json sha, `preflight_probe_cost_usd`, the
billing-surface export, and the per-phase ledger totals. Excluded rows are
listed by `invalid_reasons` class, counts including zero.

---

## Resolved review notes

1. **The manifest pins 20 instances, not 8** (`limit: 20`, sha
   `923aef05add32124`, 19 working-oracle). The 8 are the E5 campaign subset,
   pinned here by explicit id list. Verified correct by review.
2. **The flash-solo prior is 16 reportable rows** over the 8 cells (26 total
   attempts), unanimous within every cell; the decision doc's "12 attempts
   across 5 cells" counts only repeated cells. Verified correct by review.
3. **Adapter path**: `bench/swebench_adapter.py`, not
   `bench/swebench/swebench_adapter.py`. Verified correct by review.
4. **`_BENCH_ROOT_CAPS` ($40/$40) is not the spend guard** — it is the child
   bench-root's settings caps, deliberately non-binding. The real guard is
   `run_all`'s projection + actual-spend recheck against
   `factory_settings.yaml` caps, per-sweep. Verified correct by review.
5. **CORRECTED (was stale):** `--probe-plumbing` **is implemented for sssf
   arms** (`probe_plumbing` in `run_sssf`). P0.3 is now unconditional and the
   fallback caveat is dropped.
6. **Azure's `developer`-role rejection is a 422, not a 429** (both swallowed
   by `pi` identically as empty turns); the compat probe (P-2c) and the width
   probe (Phase 2) test the two failure modes separately.
7. **Both repos are currently dirty**; P-1 makes freezing them a hard
   precondition, after the P-2 models.json/registry commits land.
8. **Sail rates, model id, tier, and billing surface are TBD by design** and
   are the only permitted edits between this draft and the frozen copy, all
   resolved in P-2 before the freeze. **RESOLVED 2026-08-27, via two free
   calls (`GET /v1/models` and the public docs — no logged-in dashboard, no
   paid call): model id `deepseek/deepseek-v4-flash-0731`; tier `asap` (its
   only completion window); rates 0.09/0.18/0.02 (input/output/cached-input,
   $ per 1M tokens); billing surface reports both tokens and dollars, gross
   derivable via credit balance/burn rate, with an undisclosed lag on billing
   fields specifically. Full trail: `SAIL-DISCOVERY.md`.**
9. **`SAIL_API_KEY` was never the real env var name** — the value lives in
   `/home/k/sssf/.env` under `SAIL_RESEARCH_KEY`, and every occurrence of
   `SAIL_API_KEY` in this document has been replaced. `p0_6-isolation`
   verified both `AZURE_API_KEY` and `SAIL_RESEARCH_KEY` present, differing,
   and correctly routed by `models.json`.
10. **P0.4's named historical incident is REAL and confirmed, but its bytes
    are gone.** `benchmarks.db` holds the row verbatim —
    (harumiweb__exstruct-113, flash-chain, attempt 2) — with its recorded
    audit finding, `audit failed: foreign-workdir: sssf-events.jsonl:152
    named another arm's working tree ['harumiweb__exstruct-113__v32-solo',
    'harumiweb__exstruct-113__bare']`, and artifact digests
    (`sssf-events.jsonl` 786,524 B sha256 `a2dccb282fd9…`, `audit.json` 2,421
    B). Attempt 3 overwrote the actual files on disk before this task
    started, and `runs/`/`results-archive/` are gitignored, so the bytes
    cannot be recovered — but the incident is not a conflation with anything
    else: the `.pth`-leak mechanism documented beside
    `_foreign_workdir_hits` in the adapter (an editable install's leaked
    `sys.path` entry) is precisely WHY the agent's own tooling read into
    those two other arms' trees for this instance, and the foreign-workdir
    detector is what caught it. `p0_4-stage` reconstructs the positive from
    the store row's own recorded cells (`_P0_4_FOREIGN_CELLS` in
    `phase0_sail_ab.py`) rather than requiring the lost bytes verbatim,
    planting them onto a real archived same-instance trace. See
    `SAIL-DISCOVERY.md`.
11. **The real foreign-workdir detector does not match the planted-path shape
    P0.4/P0.5b originally described.** `_foreign_workdir_hits`/
    `_WORKDIR_CELL` (`bench/swebench_adapter.py`) fires on
    `swebench-work/<instance>__<arm>/...` — the scratch-root cell naming
    convention, confirmed against a real archived trace — not on a
    `runs/<other-instance>/<other-arm>/…` path, which would not trip the
    detector at all. Both P0.4's and P0.5b's descriptions above, and
    `bench/swebench/phase0_sail_ab.py`'s `p0_4-stage`/`p0_5b-stage`, use the
    real pattern. Verified end to end for P0.5b: exactly one finding, at the
    planted line, matching the expected substring.
12. **Sail does not, in fact, claim "no rate limits".** Its public docs
    (`docs.sailresearch.com/rate-limits.md`) document a real per-model,
    per-organization-AND-global token-bucket limiter (429
    organization-exhausted, 529 global-exhausted; does not apply to the Batch
    API). "No rate limits" throughout this draft (Purpose, Prediction 1,
    "What this experiment cannot establish") was this repo's own paraphrase,
    never a vendor claim, and every occurrence above has been corrected to
    reference the documented limiter instead.
13. **Request→first-token and first-token→last-token, as the per-call
    latency Measures row originally named them, are not separable from
    `sssf-events.jsonl`.** The trace records one landed-turn timestamp per
    model call (`thinking`/`agent_message`), not token-level streaming
    chunks; a `tool_call` event's own `started_at`/`ended_at` pair brackets
    that TOOL's execution, not the model's, confirmed against a real archived
    trace. `latency_from_trace.py` reports both legs as explicit `null` on
    every call — never a guessed split — alongside the one real, measured
    interval, `request_to_response_s` (queue wait + generation, combined).
    See `SAIL-DISCOVERY.md` for the full trace-level evidence.
14. **`p0_5a`'s sandbox proof does not run through `--probe-plumbing`'s
    "scripted reply"** — no such hook exists for sssf arms; `run_sssf`'s
    docstring is explicit that a probe-plumbing row "spends NOTHING and
    calls no model: the ADW is never invoked at all." `p0_5a-check
    --inside-sandbox` drives the adapter's own `_sandbox_argv`/
    `_sandbox_probe` primitives directly instead — the same ones
    `tests/test_swebench_sandbox_isolation.py` already exercises for this
    exact property. Verified: the planted `/tmp` marker is invisible from
    inside the sandbox.
15. **P0.3's claim that `--probe-plumbing` exercises key/endpoint resolution
    for sssf arms was false on all three counts** — no reply script exists
    for these arms; `run_sssf` SKIPS the reachability probe entirely under
    `probe_plumbing=True` (~10559-10563); and the credential precheck
    `_sssf_child_env` still runs, but is hardcoded to `AZURE_API_KEY`
    (~5894, ~7966-7974), so it cannot see a missing `SAIL_RESEARCH_KEY` or a
    wrong Sail base URL either way. Sail key/endpoint resolution is proven
    ONLY by P-2c's live probe. Corrected in P0.3 above.
16. **`SWEBENCH_SANDBOX_DOCKER=raw` voids P0.5a's sandbox proof** — it binds
    the real docker socket, and a container can then bind-mount the HOST's
    `/tmp`, defeating the private-tmpfs closure the proof certifies.
    `p0_5a-check --inside-sandbox` now detects `raw` and refuses (FAIL) rather
    than silently wrapping `docker_mode="none"` regardless of what the
    campaign environment is actually set to. The Sandbox-mandate paragraph
    now states the requirement (`broker` or `none` only) explicitly.
17. **P-2d's sha re-pin was sequenced BEFORE P-2c, inverting C2's own
    ordering** (rate card → models.json → sha re-pin → registry → commit →
    freeze). The current pin covers a `sail` entry whose `compat` is still
    unset by design — that is an INTERIM pin, not the final one; a second
    re-pin is required after P-2c sets `compat.supportsDeveloperRole`, before
    P-1's freeze. `test_every_deepseek_deployment_declares_
    supportsdeveloperrole_false`'s `sail` branch now accepts either no
    `compat` block (pre-P-2c) or one carrying a real boolean value — never a
    guess copied from Azure — so the suite stays green through the P-2c edit
    instead of going red exactly at freeze time.
18. **The Threats section's per-call latency claim was stale**: "the split
    is measured" is corrected to name what is actually measured
    (`request_to_response_s`, combined) and point at note 13 for why the
    split itself is unrecoverable.
19. **The Threats section's price-card claim was stale**: "MUST come from
    the logged-in account" is corrected — the rate card was resolved from
    `docs.sailresearch.com/pricing.md`, the vendor's own PUBLISHED card, the
    same kind of public source Azure's own table was re-verified against.
    Still self-reported until R2 reconciles it against billed usage; that
    reconciliation, not the login, is what converts the claim into fact.
20. **The Budget section did not name the operator-visible per-sweep caps**
    a campaign operator actually sees on every `run-all --dry-run`:
    `factory_settings.yaml`'s $300.00/h, $300.00/day — 20× this campaign's
    entire $15.00 hard cap. Now stated explicitly as NOT a bound for this
    campaign, so a green "vs caps" dry-run line cannot be misread as
    campaign-level headroom.

## CHANGELOG — review findings applied

- **C1**: split Sail work across three arm ids (`-p1`, `-wprobe`, paired
  `flash-solo-sail` whose first-ever rows are Phase 3); all decision-rule and
  measure queries restated to name the intended arm id.
- **C2 / M15**: compat resolved pre-freeze via the adapter's preflight
  reachability probe (≤$0.01, disclosed, `preflight_probe_cost_usd`); ordering
  fixed: rate card → models.json (rates + compat) → sha re-pin → registry →
  commit → freeze (new "Pre-freeze sequence" section).
- **C3**: `SWEBENCH_SANDBOX=1` mandated on every run, sandbox flag asserted in
  provenance; P0.5 split into sandbox proof (planted literal-/tmp marker must
  be invisible) and detector proof.
- **M4**: detector proof implemented by synthesizing the trace — append a read
  event naming the planted path to a copied real `sssf-events.jsonl`, run the
  auditor over the staged dir, expect
  `audit failed: foreign-workdir: sssf-events.jsonl:<line>`.
- **M5**: P0.4 restaged into live `runs/`, with deletion of the staged dir as
  its own numbered step (P0.4b) before any `record`.
- **M6**: billing surface pinned in P-2a with export/screenshot; token-count
  reconciliation at Phase 1; dollar band moved to Phase-2/3 boundaries;
  T+24h minimum; declared fallback when gross dollars are unavailable.
- **M7**: P0.6 rewritten to checkable assertions only; dual-key exposure of
  child envs accepted, noted, and listed under Threats; P0.7 is the backstop.
- **M8**: Phase 3 rows launched via `run-all --arm <one> --instances <one>` so
  the spend guard engages per row; ledger check every 4 rows;
  `default_cost_usd = 0.50` declared for all four new registry entries.
- **M9**: R3(b) rescored on the 4 discriminating cells (4/4 / 3/4 / ≤2/4);
  floor/ceiling flips are anomaly triggers; the old ≥6/8 rule's ≈0.69
  coin-flip false-pass probability recorded as the justification.
- **M10**: first-valid-per-cell scoring, drop-from-both-sides for missing
  cells, ≥6 evaluable (≥3 discriminating) evaluability floor, terminating
  investigate branches, ≥2 provider-starved rows stops a pass (new), R8
  model-id fidelity rule (new).
- **M11**: per-call latency extracted from archived event streams for the
  Phase-1 row and one Phase-3 Sail pass, via
  `bench/swebench/latency_from_trace.py` (committed pre-freeze). **UPDATED
  post-implementation (note 13): the request→first-token/first-token→
  last-token split this item originally specified is not recoverable from
  `sssf-events.jsonl`** — the trace has no token-level streaming timestamps.
  The script reports `request_to_response_s` (queue wait + generation,
  combined) per call instead, with both legs left explicit `null` rather
  than guessed.
- **M12**: note 5 corrected; P0.3 unconditional.
- **M13**: `preflight_probe_cost_usd` added to the ledger query and R2.
- **M14**: P0.2 selftest per-instance over the 8.
- **M16**: results artifact named: `frozen/RESULTS-SAIL-AB.md`.
