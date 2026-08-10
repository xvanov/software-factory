# Pre-registration — 2026-08-10 four-arm sweep (sweep 2 on manifest `923aef05add32124`)

**Written before the run. Committed before the run.** The tables and decision
rules below are fixed now, so the run cannot be reported in whatever framing
happens to flatter the result. Every cell is filled from an archived artifact
or printed as `n/a` with a reason; no cell is filled by hand.

## What this run is

The second sweep over the pinned SWE-rebench manifest `923aef05add32124`
(seed `20260802`, 19 working-oracle instances per the committed
`selftest.json`). Sweep 1 is the published five-arm result of 2026-08-04
(`PRE-REGISTRATION-1.6.md`, `results-archive/2026-08-04T23-19-24.998844Z/`).
Between the two sweeps the factory changed in ways that make the published
`factory` rows a measurement of a configuration that no longer exists:

1. **The chain's independent acceptance oracle is now authored in the factory
   arm** (adapter change #238, 2026-08-05, *after* sweep 1) — every published
   `factory` row was measured **without** the chain's only independence layer.
   This sweep is the first whole-sweep measurement with it active.
2. **Open-weight-only routing (operator decision 2026-08-08):** dev standard
   AND hard are both `azure/deepseek-v4-pro` (the hard-tier escape to
   `gpt-5.3-codex` is a no-op now); reviewer moved `gpt-5.4` →
   `DeepSeek-V4-Flash` → **`azure/Kimi-K2.7-Code`** (#303, on live
   hallucination evidence); acceptance author is `azure/Kimi-K2.7-Code`.
3. **Reviewer rubric fix** (#302): framework-wiring demands are low-severity
   against a green run.
4. **Dev-retry cap default is now 4** (was 3 during sweep 1, change #283).

Because dev standard == dev hard == the openhands arm's model, this sweep's
`factory` vs `openhands` pair is a **cleaner matched-weights comparison than
sweep 1** — no closed-model escape hatch exists in the chain at all.

## Run mechanics — how sweep 2 stays clean

- The sweep runs from a dedicated git worktree (`bench/sweep-2026-08-10`
  branch) with an **empty `runs/`**, the same isolation the B.1 ablation used.
  Every row is therefore `attempt: 1` **within this sweep**; sweep 1's rows
  are untouched in the main checkout and permanently archived.
- Cross-sweep, each (instance, arm) cell measured in both sweeps has **k=2
  draws**, identified by pre-registration document + archive timestamp, never
  by the `attempt` counter (which is per-run-dir and starts fresh here).
- `report` runs in this worktree only after **all** arms complete (a report
  during a sweep silently drops half-reset cells). Publishing = committing
  the new archive + the regenerated `results.md` + this file's outcome
  section together; `report --check` must pass on the result.
- Azure arms run **strictly sequentially** (`factory` → `solo-noreview` →
  `openhands`, `--workers 4` each): they share one `deepseek-v4-pro`
  deployment that lost 3 rows to 429s in sweep 1 under less load.
  `claude-5` runs **concurrently with the factory arm** — different provider,
  different bill, and the shared-cap caveat is disclosed: each `run-all`
  process guards only its own spend against the `factory_settings.yaml` caps
  ($120/h, $300/day). Projected concurrent peak (~$86/h factory + ~$23/h
  claude-5) stays under the hourly cap with margin.

## Arms — harness × model set, stated in full

An arm is a (harness, model set) pair; neither half may be omitted when a
number is quoted. Models below are the *nominal* routes; the report fills its
model column from the per-row ledger, and any drift is reported.

| id | harness | model(s), by role | budget | what it measures |
|---|---|---|---|---|
| `factory` | software-factory chain (story seeded at `SM_DONE`, dev + reviewer, run-until-green, **acceptance oracle authored spec-only before dev dispatch**), dev inside an OpenHands sandbox | dev standard `azure/deepseek-v4-pro` · dev hard `azure/deepseek-v4-pro` (escalation is a no-op) · reviewer `azure/Kimi-K2.7-Code` · acceptance author `azure/Kimi-K2.7-Code` | 16 ticks; 600 OpenHands iterations per dev session; 5400 s wall | **the product**, as currently configured |
| `solo-noreview` | the same chain driver with the reviewer round-trip removed and nothing else (`_FACTORY_DRIVER_MODES`: `{dev}`, green = `tests_green`) | dev `azure/deepseek-v4-pro` · acceptance author `azure/Kimi-K2.7-Code` | identical | **the reviewer's contribution** — this is the clean B.1 re-run (both chain arms, one sweep, one commit) that `STATUS.md` lists as queued |
| `openhands` | ONE OpenHands agent, no chain — same SDK, same default toolset, same story text, same prepared clone | `azure/deepseek-v4-pro` | 600 iterations; 5400 s wall | **the chain's contribution** (matched weights) |
| `claude-5` | Claude Code CLI **2.1.226** (sweep 1 ran 2.1.220 — six patch versions of drift, recorded here because the adapter records but does not enforce the version), hermetic flags unchanged | `claude-opus-5` (+ the CLI's own haiku side-classifier) | 60 turns; 5400 s wall | frontier reference — varies harness AND model; never attributable |

**Omitted, with reasons.** `bare`: its pre-committed cap ("one repaired run,
no iteration") is spent; it anchors no headline and the 40.2% public anchor
stands in for it. `claude-4.8`: the contamination probe it existed for came
back clean in sweep 1 (74% vs 79%, p=1.000, 19/19 instances predating
opus-5's cutoff); nothing in this sweep changes the Claude arms' inputs, so
re-running it would re-answer an answered question at ~$24.

## Deviations from sweep 1, disclosed in advance

1. **Acceptance oracle active in both chain arms.** Authored from the problem
   statement only, by `azure/Kimi-K2.7-Code`, before the dev's first call;
   provenance fields (`ordering`, `trail_scan`, `ledger_author_rows`,
   `in_graded_diff`) recorded per row. The `acceptance-verified` MERGE gate
   is still **not** run (`gate_enforced: false`) — the bench app has no boot
   recipe, so the authoring-time collect smoke (#297) is also skipped
   (audited: gated behind `http_mode`, off for bench by design).
2. **Reviewer and acceptance author share one model** (`Kimi-K2.7-Code`).
   The reviewer-independence guard (reviewer ≠ every dev tier) passes; the
   oracle author ≠ dev also holds. But chain-verdict-maker == oracle-author
   is a weaker independence posture than sweep 1's (`gpt-5.4` reviewer), and
   any Table 5 verdict-quality number must carry this note.
3. **Kimi's 100K-TPM quota is maxed** and serves reviewer + acceptance author
   under `--workers 4`; the runner retries 429s. A row lost to an
   unrecoverable 429 is an infrastructure loss under rule 5.
4. **Dev-retry cap 4** (sweep 1: 3) — a real per-row spend/behaviour change,
   part of "the product as currently configured".
5. **selftest is carried forward, not re-run.** The 2026-08-02 gold-patch
   control certified 19/20 on images that are digest-pinned
   (`repo@sha256:…`) and verified still byte-identical locally (20/20 preset,
   0 bytes to pull). The residual drift channel is `install_cmd` replay
   pulling from PyPI at prepare time; mitigation below.
6. **Free plumbing probes run before any spend**: `--probe-plumbing` on one
   instance for `openhands` and `claude-5` (real clone + real install replay
   + real collect precheck, model scripted, $0) — this exercises the
   prepared-tree topology *today*, which is the honest cheap substitute for
   re-running the full selftest. The factory arms' free check is
   `run-all --dry-run`.

## Tables

Tables 1–5 are emitted by `report` in exactly the shape fixed by
`PRE-REGISTRATION-1.6.md` (headline; per-instance outcome matrix with
contamination margins; pairwise McNemar with attributability labels;
provenance/integrity; chain-verdict quality). This file adds no new table
shapes; the arm set is {factory, solo-noreview, openhands, claude-5}.
`solo-noreview` appears as a first-class pre-registered arm this time —
sweep 1's hazard ("an ablation arm in `runs/` blends into `results.md`")
does not apply to an arm the pre-registration declares.

## Pre-committed decision rules

1. **The product claim is `factory − openhands`**, same wording rule as
   sweep 1: if the difference is ~0, the honest headline remains "our lift
   comes from using a competent agent loop, not from the chain", published in
   those words. A positive difference at n=19 is reported with its exact
   McNemar p and the MDE caveat — at ±38 pp MDE, no delta inside ±38 pp is
   claimed as an improvement, in either direction.
2. **The reviewer claim is `factory − solo-noreview`** (paired, same sweep,
   same commit): resolve rate, $/resolved, and wall clock. If solo-noreview
   is not measurably worse and remains cheaper, the standing B.1 Phase-1a
   finding ("the reviewer round-trip is not measurably load-bearing on this
   suite") is confirmed on a clean design; the routing consequence (whether
   the chain defaults to solo mode) is an operator decision, not this file's.
3. **Cross-sweep deltas (sweep 2 vs sweep 1) are descriptive only.** They
   confound provider drift, CLI drift, retry-cap drift and the oracle layer;
   no cross-sweep delta is quoted as a measured improvement or regression.
   The within-sweep pairs are the only attributable numbers.
4. **Oracle accounting is mandatory reporting.** For every chain-arm row:
   `authored_before_dev_first_call` must be true, `trail_scan.hits` 0,
   `ledger_author_rows` ≥ 1, `in_graded_diff` empty — violations fail the row
   closed (no prediction, bucketed `run_failed`) and are counted in the
   denominator, never silently dropped. The outcome section must report the
   authoring cost share and any refused rows.
5. **Attempts.** A budget-exhausted run is a counted attempt. No re-rolls of
   an outcome. An infrastructure loss (provider 429 that produced no metered
   result, sandbox crash, harness defect) may be re-run **once**, disclosed,
   both outcomes published if they differ (sweep 1's amended rule, adopted
   here *before* the data exists this time).
6. **No blending.** The report is generated in the worktree where only this
   sweep's rows exist. If any foreign or superseded row appears in the
   report's excluded sections, it is listed, never counted.
7. **Claude-arm accounting** stays CLI-reported-vs-subscription and is never
   summed with the Azure price-table estimates.

## Spend projection

From sweep 1 measured costs: factory ~$36, solo-noreview ~$25 (B.1 measured
$2.83/resolved, ~29% under factory), openhands ~$18, claude-5 ~$34
(subscription). Azure total ≈ $79 against caps of $120/h (peak arm ~$86/h)
and $300/day (today's prior spend: $2.64). The sweep guard emits operator
notices at $50/$75/$100 accumulated actual spend per process; because the
guard is per-process, the operator notices for the whole sweep are also
tracked manually in the outcome section.

## What this run cannot show

n=19, k=1 per pair within-sweep: MDE ≈ ±38 pp, unchanged from sweep 1. The
factory-vs-openhands and factory-vs-solo-noreview deltas will almost
certainly land inside it; the deliverable is (a) the first full-sweep
measurement of the chain *with its independence layer on*, on the current
open-weight configuration, (b) the clean reviewer ablation, and (c) the
per-row oracle/dev/reviewer observability trail. Defensible deltas still
require k ≥ 3; this sweep brings the pinned cells to k=2.
