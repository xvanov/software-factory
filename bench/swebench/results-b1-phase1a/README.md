# Evidence — B.1 Phase 1a, the `solo-noreview` reviewer ablation

**Immutable. Do not edit a row, an audit or a verdict in here.** If this run is
ever retracted, that is recorded by ADDING a `DISCLAIMER.md` beside the evidence,
never by rewriting it — the same rule
`results-archive/2026-08-03T05-12-08.813897Z/` is held to.

- Report: [`../RESULTS-B1-PHASE1A.md`](../RESULTS-B1-PHASE1A.md)
- Pre-registration: [`../PRE-REGISTRATION-B1.md`](../PRE-REGISTRATION-B1.md)
- Manifest: `923aef05add32124`, 19 working-oracle instances, k=1, `attempt: 1` on
  every row. Run 2026-08-05 on `6662d062`.

## Why this is a separate directory and not `results-archive/`

Two reasons, both structural:

1. `report --check` re-derives the committed `results.md` from the **latest**
   directory under `results-archive/`. Minting one there would silently re-point
   that check at rows `results.md` was never built from.
2. `results.md` is the report output for the five-arm run. `solo-noreview` is not
   part of that result and must never appear in it.

## Why it exists at all

`runs/` is gitignored scratch and `_reset_run_artifacts` deletes a row's whole
subtree at the top of every run. That has already destroyed published evidence in
this repo once — an n=6 headline lost every `grade.json` behind it, and 0 of the
19 published swe-rebench instances retained the selftest log that certified them.
So the artifacts are copied out and committed while they exist.

## Per row

| file | what it is |
|---|---|
| `result.json` | the run record **and** the hidden oracle's verdict (merged in by `grade`) |
| `audit.json` | the integrity verdict: ledger↔result reconciliation, oracle-probe scan, trail coverage |
| `prediction.diff` | the exact bytes that were graded, after test edits were stripped |
| `grade.log` / `grade-nodes.log` | the oracle run, readable and per-node |
| `spec_prompt.md` | verbatim, what the acceptance author was shown (spec only) |
| `acceptance-events.ndjson` | the chain's own acceptance stream for the row |
| `attempt.json` | which attempt at this cell this was — must read 1 everywhere |
| `root/state/events/prompt_bodies.ndjson` | verbatim persona prompts |
| `root/state/events/response_bodies.ndjson` | verbatim persona responses, joinable on `prompt_hash` |
| `root/state/events/runs.ndjson` | the isolated ledger: per-call model, tokens, cost, duration |

`sweep-solo-noreview.json` is the sweep roll-up. **Do not read numbers out of
it** — sweep aggregates are in-flight snapshots and have contradicted their own
rows before (`sweep-factory.json` said `resolved: 2` where its rows said 7). The
per-row `result.json` files and `../RESULTS-B1-PHASE1A.md` are authoritative.

## One row is INVALID and is here on purpose

`vyperlang__vyper-4801/solo-noreview` failed its audit on an oracle-probe hit (a
`curl` of a third-party dependency's source on GitHub raw) and also hit its
5400 s wall cap. It is excluded from every rate in the report and was **not
re-run** — re-running an audit-invalid row is selection on the integrity gate.
Its artifacts are kept so the finding is checkable.
