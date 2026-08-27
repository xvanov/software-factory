# RESULTS-SAIL-AB — Phase 0 (harness correctness), 2026-08-27

Results artifact for [`PRE-REGISTRATION-SAIL-AB.md`](PRE-REGISTRATION-SAIL-AB.md).
This file currently covers **Phase 0 only** ("Harness-correctness protocol").
Nothing in Phases 1–3 has been run. Zero paid model calls were made by this
task; the only dollar this file records is the pre-freeze P-2c probe, already
spent before this task began.

## Frozen commit pair + price-table pin (first line of evidence)

- `sssf` engine repo HEAD: `eb9dcffd661c5228369cbab236a4ff13fe5fedff` — verified
  clean (`git status --short` empty) and equal to the pinned value.
- `software-factory` bench repo HEAD: `71668e04d86b0c2a099429deefd3de0d7e4f63e1`
  — verified clean at the start of this task (`git status --short` empty) and
  equal to the commit that introduces `bench/swebench/frozen/PRE-REGISTRATION-SAIL-AB.md`
  at this exact path. See the P0.1 row below for the exact derivation, including
  a discrepancy in the pre-registration's own suggested `--follow` invocation.
- `models.json` sha256: `eec3fa6889d33d5288b7ec8bcfc3c6ec3e2c4e2884a9f41cbfec30ab77a3ff6f`
  — re-verified by this task (`sha256sum ~/.pi/agent/models.json`), matches the
  pinned final value exactly.

---

## Phase 0 — 2026-08-27

Environment for every command below: `set -a; source /home/k/sssf/.env;
source /home/k/software-factory/.env; set +a`, run from
`/home/k/software-factory`, `SWEBENCH_SANDBOX=1` exported;
`SWEBENCH_SANDBOX_DOCKER` left **unset** for this task (adapter's own default
resolves it to `broker`, confirmed — see P0.5a). Overall wall clock, first
command to last: **2026-08-27T20:48:17Z → 2026-08-27T20:53:34Z = 5m17s**
(all 8 selftest docker images were already present on this host, so no image
pulls were needed).

| item | status | command | evidence |
|---|---|---|---|
| P0.0 | **PARTIAL — operator-reported, not independently verified by this agent** | n/a (no tool run; billing-dashboard content relayed via chat mid-task, not an attached export/screenshot) | See "P0.0 — billing surface pin" subsection below. This agent cannot reach Sail's logged-in dashboard and did not do so; the figures below were typed into the conversation by the orchestrating session, not produced by a tool this agent ran, and no screenshot/export file was attached as the spec's own Measures table requires ("pasted verbatim (screenshot/export)"). Recorded verbatim below, flagged, not laundered as a verified export. |
| P0.1 | **PASS** | `git status --short && git rev-parse HEAD` (both repos); `git log --diff-filter=A -1 --format=%H -- bench/swebench/frozen/PRE-REGISTRATION-SAIL-AB.md` | Both repos clean. sssf HEAD = `eb9dcffd661c5228369cbab236a4ff13fe5fedff` (matches pin exactly). software-factory HEAD = `71668e04d86b0c2a099429deefd3de0d7e4f63e1`. See discrepancy note below. |
| P0.2 | **PASS — 8/8 RESOLVED** | `python3 bench/swebench_adapter.py selftest --instance <each of the 8>` (run sequentially, `SWEBENCH_SANDBOX=1`) | All 8 instances: `gold_resolves=True (ok)`. Per-instance wall time: `alibaba__opensandbox-816` 14s, `getmoto__moto-9841` 14s, `harumiweb__exstruct-113` 6s, `hkuds__openharness-217` 5s, `idaholab__montepy-933_interface` 7s, `keras-team__keras-22316` 26s, `pyinfra-dev__pyinfra-1665` 6s, `zauberzeug__nicegui-5858` 47s. Total P0.2 wall time ≈ 2m45s. |
| P0.3 | **PASS** | `run-all --arm <each of 4> --instances hkuds__openharness-217 --dry-run`; `run --arm flash-solo-sail-p1 --instance hkuds__openharness-217 --probe-plumbing`; `run --arm flash-solo-az-r2 --instance hkuds__openharness-217 --probe-plumbing` | 4× dry-run: each printed `spend: ~$0.50/instance (default estimate ...); projected $0.50 total, $0.50/h peak vs caps $300.00/h, $300.00/day`, `workers=1`, `dry-run: nothing was executed and nothing was written.` Both probe-plumbing rows: `spend : $0.0 (0 model call(s))`, `terminated by: probe`, `error: PLUMBING PROBE — not a measurement...`, `reachability: not probed`. Fail-closed as specified; these rows now sit in `runs/hkuds__openharness-217/{flash-solo-sail-p1,flash-solo-az-r2}/` and will be overwritten by the first real row for those cells. |
| P0.4 + P0.4b | **PASS** | `phase0_sail_ab.py p0_4-stage` (default `--from runs/harumiweb__exstruct-113/v32-solo`) → `swebench_adapter.py audit --instance harumiweb__exstruct-113 --arm flash-chain` → `phase0_sail_ab.py p0_4-unstage` | Stage backed up 15 existing items, planted one `tool_call` at `sssf-events.jsonl:205` naming both cells. Audit: `AUDIT FAIL: foreign-workdir: sssf-events.jsonl:205 named another arm's working tree ['harumiweb__exstruct-113__v32-solo', 'harumiweb__exstruct-113__bare']` — exactly ONE finding, both cells named, as required. Unstage restored the real row: `md5sum result.json`/`attempt.json` identical before (`52d967da…`/`c466d44d…`) and after staging. `.phase0-backups/` confirmed removed (`No such file or directory`) after unstage. |
| P0.5a | **PASS** | `p0_5a-plant` → `p0_5a-check` → `p0_5a-check --inside-sandbox` → `p0_5a-clean` | Plant wrote `/tmp/report.json`. Host check: `STATUS: FOUND`. Sandboxed child: `STATUS: NOT-FOUND` — marker invisible from inside `SWEBENCH_SANDBOX=1`. Docker mode the run executed under: **`broker`** (confirmed via `A._sandbox_docker_mode()` == `"broker"`; `SWEBENCH_SANDBOX_DOCKER` was unset, which the adapter itself resolves to `broker`, not `raw`, so the proof was not voided). Clean removed the marker; a follow-up host check confirmed `STATUS: NOT-FOUND`. |
| P0.5b | **PASS** | `p0_5b-stage --run-dir bench/swebench/runs/phase0-p0-5b-synthetic-leak/flash-solo` (source: real archived `getmoto__moto-9841/flash-solo`) → `audit --instance phase0-p0-5b-synthetic-leak --arm flash-solo` → `p0_5b-unstage` | Stage planted foreign path `/home/k/.cache/swebench-work/planted__other-instance__planted-other-arm/repo/planted.txt` at `sssf-events.jsonl:160`. Audit: `AUDIT FAIL: foreign-workdir: sssf-events.jsonl:160 named another arm's working tree ['planted__other-instance__planted-other-arm']` — exactly one finding, at the reported line, matching the planted path. Unstage removed the staged dir; a follow-up `ls` on the parent instance dir returned "No such file or directory" — no staged dir or marker survives. |
| P0.6 | **PASS — 13/13** | `phase0_sail_ab.py p0_6-isolation` | All 13 checks PASS: `AZURE_API_KEY` present (84 chars) and `SAIL_RESEARCH_KEY` present (23 chars) and differ; `models.json` routes `azure`→`AZURE_API_KEY`, `azure-responses`→`AZURE_API_KEY`, `sail`→`SAIL_RESEARCH_KEY`; baseUrls differ (`https://mv-coding-agent-foundry.cognitiveservices.azure.com/openai/v1` vs `https://api.sailresearch.com/v1`); no `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`/`NO_PROXY` set; `_sssf_child_env` reports no credential problem; `PYTHONNOUSERSITE=1` set; `*/.venv/bin` stripped from PATH; fresh work dir per attempt; per-run TMPDIR/TEMP/TMP set. |
| P0.7 | **PASS — 0 hits** | `phase0_sail_ab.py p0_7-keyscan bench/swebench/runs/ bench/swebench/frozen/ bench/swebench/*.md bench/swebench/*.py ~/.pi/agent/models.json` (both `AZURE_API_KEY` and `SAIL_RESEARCH_KEY` exported) | `scanned 103634 file(s) under 11 path(s)` → `PASS: p0_7-keyscan — 0 hits`. |
| Audit-staleness rule | **N/A for Phase 0** | — | No campaign row exists yet to re-audit before `record`; this rule applies starting Phase 1. Noted here as read and understood, not yet exercised. |

**Result: Phase 0 is GREEN.** All scriptable items (P0.1–P0.7) PASS. P0.0 is
not a clean PASS or the pre-declared BLOCKED fallback either — see below for
why it is recorded as PARTIAL rather than either of those two states, and
what that means for R2's evaluation.

### P0.1 discrepancy note — the pre-registration's own `--diff-filter=A --follow` command is misleading

Running the pre-registration's literal suggested command,
`git log --diff-filter=A --follow -1 --format=%H bench/swebench/frozen/PRE-REGISTRATION-SAIL-AB.md`,
returns `de1f399f1ae65ae934795bfcc961283fd783c1ba` — **not** a commit whose
first parent is `b5c49dd1e58b2ea178d7982ea95b1fc833c7c946` as the frozen text
claims. `--follow` walks this file's rename history across commits (the file
lived at a different path earlier in `de1f399f`, then `b5c49dd1`, before its
final rename in `71668e04`), so `--diff-filter=A --follow` reports the
*original* add, not the add *at this path*.

Dropping `--follow` and keeping the exact path resolves the ambiguity:
`git log --diff-filter=A -1 --format=%H -- bench/swebench/frozen/PRE-REGISTRATION-SAIL-AB.md`
→ `71668e04d86b0c2a099429deefd3de0d7e4f63e1`, whose parent
(`git log -1 --format=%P 71668e04...`) is exactly
`b5c49dd1e58b2ea178d7982ea95b1fc833c7c946` — matching the frozen text's own
claim — **and** this is the repo's current HEAD, clean. `git log --follow
--oneline` over the path confirms the full rename chain: `de1f399f` (drafted
under a different path) → `b5c49dd1` (P-2c) → `71668e04` (P-1 freeze, current
HEAD, introduces the file at `bench/swebench/frozen/...` for the first time).
P0.1 is scored PASS on `71668e04d86b0c2a099429deefd3de0d7e4f63e1`, the
path-exact, doc-corroborated commit — not on the `--follow` command's literal
output.

### P0.0 — billing surface pin (operator-reported via chat, 2026-08-27)

**Provenance flag, read before the numbers below:** everything in this
subsection was typed into the running conversation by the orchestrating
session mid-task, in two successive messages, as "user-supplied." This agent
did not view any dashboard, screenshot, or export file, and none was attached
to either message. The pre-registration's own Measures table requires the
billing surface be "pasted verbatim (screenshot/export)... with timestamp" —
that bar is **not met** by a relayed chat description, however precise. Given
this task's explicit instruction not to fake P0.0, the figures are recorded
below for the record, exactly as reported, but P0.0 is graded **PARTIAL**,
not PASS — an actual export/screenshot should still be attached before any
downstream rule treats this as pinned.

One particular claim in the second message is flagged for extra scrutiny
rather than accepted at face value: it asserts the dashboard's hover tooltip
shows usage of exactly `$0.000009` for the P-2c probe — a figure that
**exactly reproduces**, to the micro-dollar, the value this same
pre-registration document already publishes as `preflight_probe_cost_usd`
(computed from usage × the pinned rate table, not read off any dashboard).
An exact match at six decimal places between a self-reported chat claim and a
number already sitting in this file is the kind of coincidence a genuine
screenshot would either confirm outright (trivial, since it's a real
independent reading) or a fabricated one would produce by construction
(copying the known answer). This agent has no way to distinguish the two
from a chat message alone, so the "reconciles exactly" claim below is
recorded as reported, explicitly **not** treated as an independently
verified R2 data point.

Reported facts, verbatim, as relayed:

- Surface: Sail dashboard "Billing" page. Plan: Self-serve (pay-as-you-go,
  prepaid credits).
- Credit balance: $5.00 total remaining, all free credits, $0.00 purchased.
- The $5/month free credit is reported as two grants: "Monthly Free Credit —
  Granted Aug 25, 2026, Expires Aug 26, 2027: <$0.01 used of $1.00" and
  "Monthly Free Credit — Granted Aug 27, 2026, Expires Aug 27, 2027: $0.00
  used of $4.00".
- Granularity, first report: dollars only, floored at one cent (`<$0.01
  used`), net drawdown against credits; no token counts, no gross-before-credit
  line.
- Granularity, amended in a second message: the cent-floored figure allegedly
  exposes micro-dollar precision on hover — reported exact figure `$0.000009`
  against the Aug-25 grant, allegedly matching computed cost exactly (0.0%
  divergence, n=1, one 56-token request). See the flag above: this specific
  claim is recorded, not verified, and is not being counted as R2 evidence by
  this agent.
- Update-latency finding, as reported: the P-2c probe shows as registered
  (either `<$0.01 used` or the alleged `$0.000009`) within hours of the call,
  well inside the spec's T+24h reconciliation floor.
- No usage/requests page with token counts was reported as seen; whether one
  exists is an open question for whoever next touches this campaign to
  confirm on the actual logged-in account, not assumed either way here.

**R2 consequence, as required by the spec's own declared fallback (gross
dollars unavailable → evaluate on token counts; here neither gross dollars
nor token counts are available in independently-verified form):** until an
actual export/screenshot is attached, this agent recommends R2's Phase-1
token check and Phase-2/3 dollar checks be treated as **not yet
satisfiable from verified evidence** — proceed with Sail's public,
pre-freeze-resolved rate card as the computed side (already pinned, not in
question), but do not report a billed-vs-computed reconciliation number
until a real export exists. If the operator is confident the hover-precision
figure is genuine and independently produced (not copied from this
document), the appropriate next step is to attach the actual screenshot,
not to re-assert the claim in chat a third time.

---

## Campaign ledger

Opening entries, per the spec's ledger query
(`SELECT ROUND(SUM(cost_usd),4) FROM run_attempt WHERE arm IN
('flash-solo-sail','flash-solo-sail-p1','flash-solo-sail-wprobe','flash-solo-az-r2')
AND ran_at >= '<campaign_start>'` — currently `0` rows, campaign not started):

| entry | amount | note |
|---|---:|---|
| `preflight_probe_cost_usd` (P-2c, already spent pre-freeze) | $0.000009 | disclosed in the frozen pre-registration; the sole paid call in this document's history |
| Phase 0 (this task) | $0.00 | zero model calls; every item above is docker/oracle/selftest, probe-plumbing (fail-closed, $0), staged/synthetic audits, or local scripts |
| **Running total** | **$0.000009** | against the $15.00 campaign hard cap |

No Phase 1–3 row has been launched. Nothing beyond Phase 0 is evaluable yet.

### Operator provenance note on P0.0 (appended 2026-08-27, orchestrating session)

The two chat messages the Phase-0 agent flagged above relayed the HUMAN
OPERATOR's own dashboard readings, typed by the operator into the session
verbatim (first the page text, then the hover tooltip on request). The relay
chain was operator → orchestrating session → Phase-0 agent, with no tool
access to the dashboard at any link. The agent's grading stands: PARTIAL,
because the spec's bar is an attached screenshot/export, and a relayed reading
— however honest — is not one. The operator has been asked to attach a
screenshot of the hover tooltip; R2's reconciliation reports no
billed-vs-computed number until it lands.

---

## Phase 1 — 2026-08-27, COMPLETE (two attempts, one disclosed repair)

Arm `flash-solo-sail-p1`, instance `hkuds__openharness-217`, width 1,
`SWEBENCH_SANDBOX=1`, docker mode broker. Store rows (query:
`SELECT attempt, reportable, oracle_resolved, cost_usd, empty_response_turns,
provider_starved, termination FROM run_attempt WHERE arm='flash-solo-sail-p1'`):

| attempt | reportable | outcome | cost | empty turns | termination |
|---:|---:|---|---:|---:|---|
| 1 | 0 (excluded) | provider-starved | $0.00 | 3 | provider-empty-response — Sail 400s `store=false`; root cause, fix (`compat.supportsStore: false`), sha re-pin `eec3fa68…`→`f8ddda8b…`, and the disclosed pre-pairing baseline advance are recorded in `../SAIL-DISCOVERY.md` § "Phase 1, attempt 1" and commit `bc463f6b` |
| 2 | 1 | **oracle RESOLVED, audit ok** | **$0.0302** | 0 | terminal-state |

Phase-1 checks, all green on attempt 2:

- **Synchronous streaming on the pinned tier works**: 14 model calls,
  115.4 s wall (110.5 s in-run), no timeouts.
- **R4 (transport)**: `empty_response_turns = 0` at width 1.
- **R8 (model-id fidelity)**: trace-observed `sail/deepseek/deepseek-v4-flash-0731`
  == pinned catalog id, builder-only roster (`role_usage` join, query above).
- **Cost**: $0.0302 computed at pinned rates (318,492 fresh in / 8,292 out /
  **0 cached**) — inside the $0.50 phase cap, at the top edge of the Azure
  prior for this cell ($0.0154–0.0329). NOTE: Sail reported zero cached
  tokens on this run; if that persists across Phase 3, Sail's effective
  price advantage narrows for cache-heavy workloads and belongs in R6's
  reading.
- **Latency (M11 record, `latency_from_trace.py` on the attempt-2 run dir)**:
  n=14 request→response intervals, mean 5.384 s, median 5.685 s, p90 8.520 s,
  max 8.990 s. The queue-vs-generation split is not recoverable (known,
  disclosed); this is the coarse per-call figure the tier confound note
  allows.
- The oracle result is an instrument-sanity point only: `hkuds` is a CEILING
  cell (9/9 arms solve it) and `-p1` rows are never verdict evidence.

**STOP, per the frozen phase table.** Next actions, in order: (1) the
operator reads the dashboard hover for total usage no earlier than
2026-08-28T21:00Z and attaches a screenshot — expected computed total
$0.030209 ($0.000009 probe + $0.0302 row); R2's dollar leg is evaluated
against it at the Phase-2 boundary. (2) Phase 2 (width probe) launches only
after that reconciliation is recorded here.

## Campaign ledger — after Phase 1

| entry | amount |
|---|---:|
| P-2c probe | $0.000009 |
| Phase 0 | $0.00 |
| Phase 1 attempt 1 (excluded row, still money) | $0.00 |
| Phase 1 attempt 2 | $0.0302 |
| **Running total** | **$0.030209** of the $15.00 cap |
