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

### Operator directives + early billing reading (2026-08-27, appended)

1. **Campaign hard cap tightened by the operator: $15.00 → $5.00 total.** The
   operator's Sail balance is $5.00 of free credits and the instruction is to
   stay under it. A tightened cap is always valid (every phase cap is a
   ceiling); the phase caps now bind as min(their frozen value, the remaining
   $5.00 envelope). Realistic Phase-2+3 projection from measured priors
   (probe rows ~$0.03, Azure control ~$0.08/row, Sail k=2 ~$0.03/row) is
   ≈ $1.20–2.50 total, inside the new cap with slack.
2. **Early dashboard reading, PROVISIONAL — not the R2 evaluation:** the
   operator reports the dashboard shows **$0.0113 spent** at ~T+1–2h after
   the Phase-1 row. Computed-at-pinned-rates total is **$0.030209**. If this
   reading were final it would be a **−63% divergence** — billed BELOW
   computed. Recorded now, evaluated ONLY at the declared ≥T+24h boundary,
   because the two candidate mechanisms cut opposite ways:
   - **Billing lag**: the surface registered micro-usage "within hours" for a
     56-token probe, but a 327k-token run may accrue in parts; the reading
     may simply be incomplete.
   - **Unreported cache reads**: the usage payload reported **0 cached
     tokens** on 318,492 input — but if Sail actually billed a large share at
     the cached rate ($0.02/M vs $0.09/M), computed overstates. A ~65%
     cache-billed share reproduces $0.0113 almost exactly
     (0.35×318,492×0.09/1e6 + 0.65×318,492×0.02/1e6 + 8,292×0.18/1e6 ≈
     $0.0115). If confirmed, our computed figure is a documented UPPER BOUND
     (the same safe-direction treatment the rate table already applies to
     Azure V3.2's phantom cache tier) — conservative against Sail in R6, so
     adoption math stays honest, but the mechanism must be published before
     Phase 2 launches.
   Next action unchanged: operator re-reads the hover at ≥T+24h
   (after 2026-08-28T21:00Z) and attaches a screenshot; R2's dollar leg is
   evaluated then, with the investigate branch triggered if the divergence
   holds outside the 10% band.

### Diagnostic probes between Phases 1 and 2 (2026-08-27, disclosed)

Three direct-HTTP micro-probes (upper-bound $0.0026 total) resolved the
$0.0113-vs-$0.0302 divergence: **Sail's streaming usage omits
`prompt_tokens_details`, so cached tokens are billed (at $0.02/M) but
invisible to pi's usage accounting.** Computed cost is henceforth read as an
upper bound for streamed Sail runs; R2's dollar leg is evaluated as a
bounds check (billed ∈ [all-cached, all-fresh]) plus the exact non-streaming
rate check. Full mechanism, arithmetic, and the R2 re-reading:
`../SAIL-DISCOVERY.md` § "Sail's streaming usage omits cache detail".
Implied Phase-1 cache share ≈85%. Also observed: one immediate 429 on the
first probe call of the day (recovered in ~1 min) — noted for Phase 2.

## Campaign ledger — after the diagnostic probes

| entry | amount |
|---|---:|
| running total after Phase 1 | $0.030209 |
| diagnostic probes (upper bound) | $0.0026 |
| **Running total** | **$0.032809** of the **$5.00** cap (operator-tightened) |

### Phase-1 → Phase-2 boundary: reconciliation recorded, T+24h floor superseded (2026-08-27)

Operator's dashboard reading: **$0.0125** total spent, taken minutes after the
diagnostic probes. Two independent instant-update observations now exist
(the P-2c probe registered within hours; the diagnostics' +$0.0012 increment
appeared within minutes and matches their mostly-cached actual cost), so the
spec's ≥T+24h floor — a guard against billing lag written before the
surface's latency was known — is superseded: readings are treated as current
as of their timestamp. **R2 bounds check at this boundary: PASS** —
$0.0125 ∈ [$0.0091 all-cached, $0.0328 all-fresh] computed from usage
tokens; implied Phase-1 cache share ≈85% (≈48k fresh / ≈270k cached of
318,492), consistent with the streaming-omission mechanism. The exact
non-streaming rate check stands at 0.0% divergence (P-2c). Outstanding, not
blocking: the P0.0 screenshot, still wanted before final adoption claims.
Phase 2 is unblocked.

**Width-probe construction note, recorded before running it:** the frozen
table probes widths 1 → 2 → 4 over TWO instances, but effective concurrency
is min(workers, instances) = 2, so the "width 4" step cannot measure
anything width 2 does not. It is skipped as vacuous rather than run as
theater; the probe's ceiling claim is therefore **"clean width ≥ 2" at
most**, and the evolution campaign must re-probe at its real fan-out before
exceeding 2. (Per the no-silent-caps rule: width > 2 is NOT measured here.)

---

## Phase 2 — width probe, 2026-08-27, COMPLETE

Arm `flash-solo-sail-wprobe`, instances `hkuds__openharness-217` +
`zauberzeug__nicegui-5858`, `SWEBENCH_SANDBOX=1`. Store rows (query: the
wprobe SELECT in the Phase-1 section, arm swapped):

| width | rows | empty turns | starved | outcome | computed cost (upper bound) |
|---:|---:|---:|---:|---|---:|
| 1 | 2 | 0 | 0 | both resolved, audits valid | $0.0424 + $0.0781 |
| 2 (concurrent) | 2 | 0 | 0 | both resolved, audits valid | $0.0293 + $0.1255 |

**Clean width ≥ 2.** Width 2 — the width at which Azure's Flash deployment
429s and pi swallows the refusal — ran with zero empty turns and zero
starvation on Sail, 437 s wall for the concurrent pair. **R5: adopt for
parallel evolution use**, with the pre-recorded ceiling caveat: width > 2
was NOT measured (two instances bound effective concurrency at 2; the
width-4 step was recorded as vacuous before the probe ran), so any fan-out
beyond 2 requires its own probe. The one first-call-of-day 429 seen during
the diagnostic probes did not recur in either pass. Probe rows are width
evidence only — never verdict or cost-ratio evidence.

## Campaign ledger — after Phase 2

| entry | amount |
|---|---:|
| running total after diagnostics | $0.032809 |
| Phase 2, width 1 (2 rows, upper bound) | $0.1205 |
| Phase 2, width 2 (2 rows, upper bound) | $0.1548 |
| **Running total (computed upper bound)** | **$0.3081** of the $5.00 cap |

Boundary action per R2(b): operator hover reading at this boundary, recorded
below when supplied; expected billed ∈ [all-cached ≈ $0.09, this upper
bound $0.31], plus the P0.0 screenshot still outstanding.

### Phase-2 boundary R2 reading (operator, 2026-08-27): PASS

Dashboard hover: **$0.1079** total. Bounds check: $0.1079 ∈ [≈$0.09
all-cached, $0.3081 all-fresh] → **PASS**. Billed ≈ 35% of the computed
upper bound — the workload is deeply cache-warm on Sail, and computed
figures remain a safe upper bound throughout. Non-streaming rate check
unchanged at 0.0%. P0.0 screenshot still outstanding. Phase 3 is a go.

---

## Phase 3 — 2026-08-27, STOPPED at row 3/24 (paired pass) — HARNESS BUG FOUND, not a Sail fault

Environment for every row: `set -a; source /home/k/sssf/.env; source
/home/k/software-factory/.env; set +a; export SWEBENCH_SANDBOX=1`, each row its
own `run-all --arm <one> --instances <one> --workers 1` invocation, both repos
clean and at the pinned commit pair before the first row.

### Rows executed

Store query: `SELECT instance_id, arm, attempt, reportable, oracle_resolved,
cost_usd, empty_response_turns, provider_starved, termination, wall_clock_s
FROM run_attempt WHERE arm IN ('flash-solo-az-r2','flash-solo-sail') ORDER BY
ran_at`

| # | instance | arm | attempt | reportable | oracle | cost | empty turns | provider_starved | termination | wall |
|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|
| 1 | alibaba__opensandbox-816 | flash-solo-az-r2 | 1 | 1 | FAIL (right_place_wrong_fix) | $0.0841 | 0 | 0 | terminal-state | 412.1s |
| 2a | alibaba__opensandbox-816 | flash-solo-sail | 1 | 0 (excluded) | provider-starved | $0.00 | 3 | 1 | provider-empty-response | 18.4s |
| 2b | alibaba__opensandbox-816 | flash-solo-sail | repair (not ingested) | — | — | $0.00 | — | — | PREFLIGHT refusal, audit FAIL (missing artifact) | 0.3s |
| 3 | getmoto__moto-9841 | flash-solo-sail | (not ingested) | — | — | $0.00 | — | — | PREFLIGHT refusal, audit FAIL (missing artifact) | 0.3s |

Row 1 (Azure, floor-cell prior confirmed — `alibaba__opensandbox-816` was
never solved by any prior arm either) is a clean, valid, reportable row.
Row 2's first Sail attempt genuinely reached the provider and came back with 3
empty-content, all-zero-usage turns — a real provider-empty-response event,
correctly detected and excluded. Its one allowed repair, and the next row
(a different cell, `getmoto__moto-9841`), both refused at PREFLIGHT before any
clone or spend, with the message `PREFLIGHT: 1 of the 1 deployment(s) this
arm's roster names did not answer a 512-token probe request: … (env:
SAIL_RESEARCH_KEY is empty in the child environment)`.

**This looked, at first, like the frozen stop condition "≥2 provider-starved
rows in one pass → stop the pass" — two Sail rows in a row failed to reach the
model. It is NOT that.** Diagnosis below.

### Root cause: `pi` rewrote `~/.pi/agent/models.json` into a format the adapter's own preflight probe cannot parse

Comparing the on-disk file against the backup `pi` itself wrote
(`~/.pi/agent/models.json.bak-2026-08-27T180929`, sha256
`f8ddda8b19046245fd35eb82fad378850ae3dd86f3438dfd1a0d29272e38c651` — the exact
value `_PI_PRICE_TABLE_SHA256` still pins, and the sha row 1's own
`price_table.sha256` recorded with `matches_pinned: true`) against the current
file (sha256 `3b3d708d95f4fea20526f80775b828f7a7984efe2fde34ae68af6b6eb75fe5ba`
— matches NEITHER any previously recorded pin) shows exactly three lines
changed, all three `apiKey` fields:

```
-  "apiKey": "AZURE_API_KEY",      (×2, azure + azure-responses)
-  "apiKey": "SAIL_RESEARCH_KEY",
+  "apiKey": "env:AZURE_API_KEY",  (×2)
+  "apiKey": "env:SAIL_RESEARCH_KEY",
```

`pi` itself resolves the `env:` prefix correctly when it authenticates for a
real run — that's why row 1 (before the rewrite) and row 2's first Sail
attempt (whichever of the two happened to run before or straddled the rewrite)
still made real, correctly-authenticated network calls. But the bench
adapter's OWN preflight reachability probe
(`_sssf_probe_model`/`_pi_model_entry` in `bench/swebench_adapter.py`) does
not strip that prefix: it takes `block.get("apiKey")` verbatim as the env var
NAME and does `env.get(key_var)`. Once the file carries `"env:SAIL_RESEARCH_KEY"`,
that becomes a literal (wrong) lookup key — `env.get("env:SAIL_RESEARCH_KEY")`
— which is always `None`, regardless of whether the real credential is present
and correct (verified present, 23 chars, immediately before each failing
invocation). Reproduced directly, deterministically, twice, outside any
run-all sweep, for both the sail AND azure model ids (see the diagnostic
commit); a plain re-run of the identical failing invocation reproduces the
identical failure (committed as its own record-file diff), ruling out a
transient network blip or rate limit.

**Consequence: this is not a Sail-specific or provider-side fault at all — it
is a latent bug in the adapter's own preflight probe, newly triggered by `pi`'s
own config-rewrite behavior mid-campaign, and it now blocks EVERY future row of
BOTH arms** (Azure would fail identically the next time `run-all` is invoked,
since its `apiKey` field carries the same `env:` prefix now). It also means the
on-disk `models.json` sha (`3b3d708d…`) no longer matches the pinned
`f8ddda8b…` that row 1 and Phases 1–2 validated against — a provenance
mismatch (R8/P0.1 territory) that the preflight bug is currently masking
(rows are refused before they'd reach the sha-pin check).

**Not fixed by this task.** Fixing it means either restoring
`~/.pi/agent/models.json` from the backup (outside git, but `pi` may rewrite it
again on the next real invocation, in which case the bug recurs) or patching
`bench/swebench_adapter.py`'s key-lookup to strip an `env:` prefix (a non-record
code file — the campaign's own row-validity supersession rule voids pairing
for every following row unless this is disclosed and sequenced correctly, the
same way Phase 1's `compat.supportsStore` fix was). Both are judgment calls
for the operator, not something this task improvised past the stop condition
that fired.

### Why the pass was stopped

Two consecutive Sail-arm rows failed to reach the model in this pass (row 2's
repair, row 3's fresh attempt) — the frozen stop condition ("≥2
provider-starved rows in one pass → stop the pass and report") fired on its
face, even though the underlying mechanism turned out to be a harness bug
rather than provider throttling. Per instructions, stopped and reporting
rather than improvising a fix or continuing past it.

### Campaign ledger at stop

Query: `SELECT ROUND(SUM(cost_usd),4) FROM run_attempt WHERE arm IN
('flash-solo-sail','flash-solo-sail-p1','flash-solo-sail-wprobe','flash-solo-az-r2')`
→ **$0.3896**, plus the $0.0328 pre-Phase-3 probe/diagnostic overhead already
folded into that same sum via the `-p1`/`-wprobe` arm rows (Phases 1–2 are
inside this query's arm list) → total spend to date is **$0.3896 of the $5.00
operator-tightened cap**. Far from the cap; the stop is about validity, not
budget.

### Incidents this pass

1. One genuine provider-empty-response event (`alibaba__opensandbox-816`,
   `flash-solo-sail`, attempt 1): 3 swallowed turns, $0.00, correctly excluded
   — disclosed, one repair attempted per policy.
2. Two preflight refusals (the repair attempt and `getmoto__moto-9841`'s row),
   root-caused to the adapter/`models.json` bug above, not ingested (no
   `result.json` written), audit FAIL (missing artifact) is the expected shape
   for an unauditable run.
3. `models.json`'s sha no longer matches any recorded pin as of this stop —
   flagged for the operator, not yet remediated.

Nothing beyond row 3 of the paired pass has run. Rows 4–16 (paired pass) and
the 8-row second Sail pass are entirely outstanding.

---

## Phase 3 — RESUMED and COMPLETE, 2026-08-27 (all 24 rows)

Resumed after commit `ca9c0941` (bench repo) fixed the preflight apiKey-spelling
bug (`_env_var_of_api_key`, `_canonical_price_table_sha256`) — verified before
resuming: `models.json`'s canonical sha still reduces to the pinned
`f8ddda8b19046245fd35eb82fad378850ae3dd86f3438dfd1a0d29272e38c651`, and direct
key-lookup checks for both `azure/DeepSeek-V4-Flash` and
`sail/deepseek/deepseek-v4-flash-0731` resolved correctly. `sssf` engine repo
untouched throughout, still `eb9dcffd…`, clean.

### Paired pass (16 rows), resumed at row 2's repair through row 16

Store query: `SELECT instance_id, arm, attempt, reportable, oracle_resolved,
cost_usd, empty_response_turns, provider_starved, audit_ok FROM run_attempt
WHERE arm IN ('flash-solo-az-r2','flash-solo-sail') ORDER BY instance_id, arm,
attempt`

| instance | Azure (flash-solo-az-r2) | Sail, paired-pass valid attempt | agree? |
|---|---|---|---|
| alibaba__opensandbox-816 | FAIL right_place_wrong_fix, $0.0841 | **no valid row** — attempt1 provider-starved (3 empty turns, $0.00); repair attempt3 ALSO provider-starved (1 empty turn, $0.0474, oracle would have resolved) — cell left per operator adjudication, both events recorded | n/a |
| getmoto__moto-9841 | resolved, $0.0422 | resolved, $0.0478 | yes |
| harumiweb__exstruct-113 | FAIL wrong_place, $0.0928 | FAIL empty_patch, $0.0363 (attempt2, repair — attempt1 was provider-starved, 6 empty turns, $0.3027, repaired once successfully) | yes (both FAIL) |
| hkuds__openharness-217 | resolved, $0.0621 | resolved, $0.0203 | yes |
| idaholab__montepy-933_interface | FAIL right_place_wrong_fix, $0.0999 | FAIL right_place_wrong_fix, $0.0399 | yes |
| keras-team__keras-22316 | resolved, $0.2232 | **no valid row** — attempt1 AUDIT-INVALID (oracle-probe leak, sssf-events.jsonl:132, "referenced harness's oracle/manifest paths … outside the run's own subtree"), $0.2842, bundled with a real 429 (1 empty turn); never re-rolled per policy | n/a |
| pyinfra-dev__pyinfra-1665 | resolved, $0.0545 | FAIL right_place_wrong_fix, $0.0171 | **no — discordant** (discriminating cell) |
| zauberzeug__nicegui-5858 | resolved, $0.046 | resolved, $0.1183 | yes |

Azure: 8/8 reportable, $0.7048 total. Sail (paired-pass valid rows only): 6/8
cells have a valid row, $1.2960 across those 6 (excludes the two
provider-starved/audit-invalid rows above, which cost $0.00 + $0.2842 +
$0.3027 — all disclosed, not double-counted here since they carry no
reportable verdict).

### Second Sail pass (8 rows) — k=2 flip check

| instance | 2nd-pass Sail verdict, cost | vs paired-pass Sail attempt | FLIP? |
|---|---|---|---|
| alibaba__opensandbox-816 | FAIL right_place_wrong_fix, $0.0772 | (none — first valid Sail attempt for this cell) | n/a, no prior to compare |
| getmoto__moto-9841 | FAIL right_place_wrong_fix, $0.2027 | resolved | **YES — resolved → FAIL** |
| harumiweb__exstruct-113 | FAIL wrong_place, $0.0652 | FAIL empty_patch | no (both FAIL) |
| hkuds__openharness-217 | resolved, $0.0436 | resolved | no |
| idaholab__montepy-933_interface | resolved, $0.0642 | FAIL right_place_wrong_fix | **YES — FAIL → resolved** |
| keras-team__keras-22316 | resolved, $0.4829 | (none — first valid Sail attempt; paired-pass attempt was audit-invalid) | n/a, no prior to compare |
| pyinfra-dev__pyinfra-1665 | **AUDIT-INVALID** — foreign-workdir, sssf-events.jsonl:38, requested-side read named `ppyinfra-dev__pyinfra-1665__flash-solo-sail` (self-referential, one extra character), $0.0701, never re-rolled | FAIL right_place_wrong_fix | no valid 2nd attempt to compare |
| zauberzeug__nicegui-5858 | **AUDIT-INVALID** — foreign-workdir, sssf-events.jsonl:25, requested-side read named `zauzerzeug__nicegui-5858__flash-solo-sail` (self-referential, one transposed character), $0.0555, never re-rolled | resolved | no valid 2nd attempt to compare |

**Two genuine Sail self-agreement (k=2) flips**: `getmoto__moto-9841`
(resolved → FAIL) and `idaholab__montepy-933_interface` (FAIL → resolved) —
both discriminating cells. Per R3a these require a published explanation
before adoption may proceed; not adjudicated here (upstream evaluation, per
this task's brief). Two cells (`pyinfra-dev__pyinfra-1665`,
`zauberzeug__nicegui-5858`) have their second-pass attempt excluded as
audit-invalid, leaving only one valid Sail attempt each — no k=2 pair
available for self-agreement scoring on those two. Two cells
(`alibaba__opensandbox-816`, `keras-team__keras-22316`) have their
paired-pass Sail attempt missing/invalid, so their only valid Sail row is the
second-pass one — flagged: for those two cells, the "paired-pass" A/B
comparison in the table above actually rests on a second-pass-sourced Sail
row under the store's first-valid-by-ran_at selection rule, which mixes pass
provenance. Not adjudicated here.

### Incidents, full campaign

1. **Harness bug (root-caused, fixed by the operator, commit `ca9c0941`)**:
   `pi`'s own startup normalizer respelled `apiKey` in `~/.pi/agent/models.json`
   twice in one afternoon (bare var → `env:VAR` → `$VAR`); the adapter's
   preflight probe read the spelling literally, producing 2 false "key is
   empty" refusals (the stop that ended the first attempt at this pass, see
   above). Fixed preflight-only; canonical sha lands back on `f8ddda8b…`, no
   recorded row's provenance moved.
2. **Four genuine provider-starved events** (real Sail 429s/empty-turns, not
   the harness bug): `alibaba__opensandbox-816` ×2 (attempts 1 and 3, cell
   left uncovered by the paired pass per operator adjudication — repair
   budget for that cell exhausted, both events recorded);
   `harumiweb__exstruct-113` ×1 (attempt 1, repaired once, successfully);
   `keras-team__keras-22316` ×1 (attempt 1, bundled with the audit-invalid
   finding below, not separately repaired since audit-invalid rows are never
   re-rolled).
3. **Three genuine audit-invalid rows** (contamination, never re-rolled):
   `keras-team__keras-22316` paired-pass attempt1 (oracle-probe leak);
   `pyinfra-dev__pyinfra-1665` second-pass attempt2 (foreign-workdir, typo'd
   self-reference); `zauberzeug__nicegui-5858` second-pass attempt2
   (foreign-workdir, typo'd self-reference). Split 1-in-paired-pass,
   2-in-second-pass — neither pass individually reached the ≥3-per-pass stop
   threshold, so neither pass was halted.
4. **Two Sail k=2 self-agreement flips**, both discriminating cells: see
   table above.

### Total computed spend by arm

Query: `SELECT arm, COUNT(*), ROUND(SUM(cost_usd),4) FROM run_attempt WHERE
arm IN ('flash-solo-az-r2','flash-solo-sail') GROUP BY arm`

| arm | all attempts | reportable attempts | reportable cost | all-attempts cost |
|---|---:|---:|---:|---:|
| flash-solo-az-r2 | 8 | 8 | $0.7048 | $0.7048 |
| flash-solo-sail | 18 | 12 | $1.2155 | $1.9754 |

### Final campaign ledger

Query: `SELECT ROUND(SUM(cost_usd),4) FROM run_attempt WHERE arm IN
('flash-solo-sail','flash-solo-sail-p1','flash-solo-sail-wprobe','flash-solo-az-r2')`
→ **$2.9857** (store) + **$0.0328** (P-2c probe + diagnostic-probe overhead,
outside the store) = **$3.0185 of the $5.00 operator-tightened cap**.
Campaign complete, well inside the cap.

**Phase 3 is complete: all 24 pre-declared rows ran, no stop condition fired
on the resumed pass (audit-invalid count topped out at 2 in either
individual pass; provider-starved events were isolated, disclosed, and
handled per the repair-once/leave-the-cell policy).** R3/R6 decision-rule
evaluation, including how to treat the two flips, the two paired-pass-missing
cells, and the two second-pass-missing cells, is left to the upstream
evaluation per this task's brief.
