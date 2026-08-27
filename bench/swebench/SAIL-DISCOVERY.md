# Sail Research discovery — P-2a/P-2b evidence, P0 verification log

Written while implementing the pre-freeze machinery for
`frozen/PRE-REGISTRATION-SAIL-AB.md`. Every number below carries where it came
from; nothing here is a paid call — two free metadata/docs fetches (task 1),
one free `GET /v1/models`, and everything else is local file reads, `$0`
adapter verbs, and real (free) `bwrap` sandbox exercises.

## Catalog id and rates (P-2a)

**`GET https://api.sailresearch.com/v1/models`**, `Authorization: Bearer
$SAIL_RESEARCH_KEY` (a free, OpenAI-compatible list endpoint — no
chat/completions/responses POST was made). HTTP 200, 8 models listed. The
DeepSeek V4 Flash family entry, verbatim:

```
"id": "deepseek/deepseek-v4-flash-0731"
```

No quant suffix — contrast `zai-org/GLM-5.2-FP8` on the same list, which does
carry one. So `deepseek/deepseek-v4-flash-0731` is the exact, verbatim
catalog id.

**`https://docs.sailresearch.com/pricing.md`** (public, unauthenticated) lists
this model under exactly ONE completion window:

| tier | input $/1M | cached input $/1M | output $/1M |
|---|---:|---:|---:|
| Default (asap) | 0.09 | 0.02 | 0.18 |

No Balanced or Flex row exists for this model — contrast GLM-5.2, Kimi-K2.6
and Gemma 4 31B IT, which each publish those two additional tiers on the same
page. **`docs.sailresearch.com/completion-windows.md`** confirms this is
expected, not an omission: "Not every core model supports every completion
window yet. Check Pricing for current per-model availability." So the
pre-registration's Treatment-definition tier cell ("`balanced` if docs
confirm, else `asap`") resolves to **`asap`, by elimination — it is the only
tier this model offers**, not a latency choice made on this model's behalf.

**`docs.sailresearch.com/models.md`** (public) gives the catalog entry:
Context 1M, 284B params (13B active, MoE), Reasoning: yes. No separate
max-output-tokens figure is published anywhere in the docs.

## What `models.json` and the adapter now carry

- `models.json`'s new `sail` provider: `baseUrl
  https://api.sailresearch.com/v1`, `api: openai-completions`, `apiKey:
  SAIL_RESEARCH_KEY`, one model (`deepseek/deepseek-v4-flash-0731`),
  `contextWindow: 1000000` (the documented figure), `maxTokens: 16384` (**not**
  discovered — a deliberate conservative default mirroring Azure's own
  DeepSeek-V4-Flash deployment, disclosed as such in the file's own
  `_comment`, chosen because no Sail page publishes a distinct output-token
  ceiling and an unbounded request against an undocumented limit is the wrong
  default). `compat` left **unset** — P-2c's live probe sets it, not this
  commit.
- `_PI_PRICE_TABLE_SHA256` in `bench/swebench_adapter.py` re-pinned (INTERIM —
  see note 17 / P-2d: a second re-pin is still required after P-2c sets
  `compat`) to
  `dd22d0f5270386daed59d7afde1269c3e02357e8608ff7752ddc44337643cf8a` (was
  `fbab9ac067086c6a6d89925302a3e4c9e87b780100a82e59684a40c98687c45a`).
  Reproducible recipe, not a claimed-but-unverifiable "byte-for-byte" diff:
  `models.json` round-trips EXACTLY through `json.dumps(indent=2)` with no
  trailing newline (`json.dumps(json.loads(raw), indent=2).encode() == raw`,
  verified). Deleting exactly the `sail` provider block
  (`del d["providers"]["sail"]`) plus the `sail` `_comment` entries
  (`del d["_comment"][54:105]`) and re-serialising the same way reproduces
  the PRIOR pin, `fbab9ac0…c45a`, exactly — i.e. the only bytes that moved
  are the ones this diff added, confirmed by reversing the diff and
  re-hashing rather than by eyeballing a comment. Also verified: every
  azure/azure-responses `id`/`cost` pair reads back unchanged (see the
  constant's own comment and `test_every_deepseek_deployment_...` in
  `tests/test_benchmark_regressions.py`).
- Four new `_ARMS` registry entries: `flash-solo-az-r2`, `flash-solo-sail-p1`,
  `flash-solo-sail-wprobe`, `flash-solo-sail` — all `default_cost_usd=0.50`,
  `max_workers=1` except `-wprobe` at `4`. New roster entries in
  `_SSSF_ROSTERS` and a new model constant `_SSSF_FLASH_SAIL =
  "sail/deepseek/deepseek-v4-flash-0731"`.

## Billing surface and rate limits (context for R2 / Threats, not rate-card facts)

**`docs.sailresearch.com/usage.md`** (public): the Usage API reports BOTH
token counts and dollars — "Monetary fields are fractional USD cents
(floats), and token fields are raw token counts" — plus credit balance and
burn rate (so gross-vs-net is derivable), and "Usage data may have a slight
delay and is not real-time. Billing-derived fields ... can lag the most
recent minutes more than the operational activity and latency endpoints" —
consistent with, not shorter than, the pre-registration's T+24h
reconciliation floor. `docs.sailresearch.com/billing` (guessed path) is a
404 — there is no separate "billing" doc page; `usage.md` is the one that
covers it.

**`docs.sailresearch.com/rate-limits.md`** (public): Sail does **not** claim
"no rate limits". It documents a real per-model token-bucket limiter: "Sail
can limit input tokens per minute for each public model. Each configured
model has two limits: One limit for all organizations together. One limit
for each organization." One-minute bucket, continuous refill, "A single
large prompt can use the full bucket. There is no extra burst limit."
**429** when the organization's bucket is exhausted, **529** when the GLOBAL
model bucket is exhausted. Does not apply to the Batch API. **Correction
recorded in the pre-registration's Resolved review notes**: Prediction 1's
parenthetical treats "no rate limits" as a vendor claim under test; it is
this repo's own paraphrase, not something Sail's docs say — the actual
claim under test is narrower ("clean at width 2" against a *documented*
token-bucket limiter, not an undocumented one).

**`docs.sailresearch.com/api-reference/chat-completions-api/create-a-chat-completion.md`**
(public): base URL `https://api.sailresearch.com/v1`, path
`/chat/completions`; the request schema's `role` enum lists `system`, `user`,
`assistant`, `tool`, `function`, `developer`. This is a SCHEMA listing, not
proof the serving stack honours the `developer` role in practice (Azure's own
schema presumably lists it too, and every DeepSeek deployment there still
422s on it) — P-2c's live probe is what actually resolves
`compat.supportsDeveloperRole`, and it is explicitly out of scope for this
work (zero paid calls).

## P0.4 — the historical incident is real; its bytes were overwritten by attempt 3

**CORRECTED** (this section previously claimed the incident might be a
conflation with a different, unrelated contamination class — that claim was
wrong and has been deleted; see below for what actually happened).

`benchmarks.db` holds the row **verbatim**: (harumiweb__exstruct-113,
flash-chain, attempt 2), with its recorded audit finding —

```
audit failed: foreign-workdir: sssf-events.jsonl:152 named another arm's
working tree ['harumiweb__exstruct-113__v32-solo', 'harumiweb__exstruct-113__bare']
```

— and artifact digests from that attempt: `sssf-events.jsonl` 786,524 bytes,
sha256 `a2dccb282fd9…`; `audit.json` 2,421 bytes. This is the real,
historical foreign-workdir positive the pre-registration's P0.4 names.

**The bytes themselves are gone.** Searched, before writing
`p0_4-stage`/`p0_4-unstage`:

- every `bench/swebench/results-archive/<ts>/` snapshot (11 snapshots) —
  none contains a `harumiweb__exstruct-113/flash-chain` subdirectory;
- the live `bench/swebench/runs/harumiweb__exstruct-113/flash-chain/`
  directory — holds attempt 3, clean (`attempt.json: {"attempts": 3}`,
  `audit.json: {"ok": true, "failures": []}`). **Attempt 3 overwrote attempt
  2's files on disk** before this task started — `runs/<instance>/<arm>/`
  is a single directory that the next attempt of the same cell destroys
  (documented adapter behaviour, not a surprise);
- git history for both `runs/` and `results-archive/` — both are gitignored
  (`bench/.gitignore: runs/`), so there is no history to recover the deleted
  bytes from either.

A fresh scan (this cycle) over every currently-archived `sssf-events.jsonl`
in `runs/` found **zero command-side foreign-workdir hits** — confirming the
bytes are gone, not that the incident never happened; the store row is the
surviving record of it.

**Why this is the SAME detector as the `.pth`-leak incident documented
beside `_foreign_workdir_hits`/`_WORKDIR_CELL`** (bench/swebench_adapter.py,
~line 12920), not a different one: that comment documents the ROOT CAUSE —
an earlier arm's editable pip install left a `.pth` file
(`/home/k/sacrifice/backend/.venv/lib/python3.12/site-packages/
exstruct.pth`) pointing at `…__bare/repo/src`, so a later arm's own
`python3 -c "import exstruct"` silently resolved into another arm's tree —
and the foreign-workdir detector is what CAUGHT the resulting read, which is
exactly the mechanism the recorded finding string names. The `.pth` leak is
WHY the read happened; the foreign-workdir detector is WHAT recorded it. Two
halves of one incident, not two incidents.

**`p0_4-stage` reconstructs the positive** from the store row's own recorded
cells (`_P0_4_FOREIGN_CELLS` in `phase0_sail_ab.py`) rather than requiring
the lost bytes verbatim: it copies a real archived same-instance trace
(default `runs/harumiweb__exstruct-113/v32-solo/`), rewrites the copy's own
self-references to the `flash-chain` identity, and plants **ONE** `tool_call`
event whose command names BOTH `harumiweb__exstruct-113__v32-solo` and
`harumiweb__exstruct-113__bare` — not two events naming one each (a cycle-2
design, corrected in cycle 3; see below). The real historical positive was
one command (line 152) that touched both other arms' trees at once, and
`_foreign_workdir_hits`'s multi-match dedup path — returning every distinct
cell it finds in ONE command's text — is exactly what that historical row
exercised; two separate single-cell events would never reach it.
Deterministic regardless of which source is used. `--from PATH` remains
available to override the default source. See "Local verification, Cycle 3"
below for the resulting audit output (one finding, both cells).

## The real foreign-workdir detector pattern (correction to the draft)

The pre-registration's P0.4/P0.5b prose gives the planted path shape as
`runs/<other-instance>/<other-arm>/planted.txt`. **That does not match what
the live detector matches on.** Read from `bench/swebench_adapter.py`:

```python
_WORKDIR_CELL = re.compile(r"swebench-work/([A-Za-z0-9_.\-]+?__[A-Za-z0-9_.\-]+)")
```

`_foreign_workdir_hits` fires on the scratch-root cell naming convention —
`/home/k/.cache/swebench-work/<instance>__<arm>/...` — confirmed against a
real archived trace (every `read`/`grep`/`edit` tool call in
`runs/getmoto__moto-9841/flash-solo/sssf-events.jsonl` names paths of exactly
that shape). A planted `runs/...` path would not trip the detector at all,
which would make P0.4/P0.5b's proof worthless as literally specified. Both
`p0_4-stage`'s synthetic test source and `p0_5b-stage`'s planted event use
the REAL pattern instead (see each command's own docstring/`--help`).
**Corrected in the pre-registration's Resolved review notes.**

## P0.5a — no `--probe-plumbing` reply-script hook exists for sssf arms

The pre-registration's P0.5a describes running the sandbox proof "via a
`--probe-plumbing` row ... whose scripted reply reads that literal path".
`run_sssf`'s own docstring says otherwise: `probe_plumbing=True` means "the
ADW is never invoked at all" — no model, no reply script, nothing to inject a
`cat /tmp/...` command into. The fixed-reply mechanism that DOES exist
(`_BARE_PROBE_REPLIES`) belongs to the unrelated `bare` arm and answers a
fixed, hardcoded four-line script written to exercise specific bare-arm
parser branches — not a general-purpose probe hook.

`p0_5a-check --inside-sandbox` instead drives the adapter's own
`_sandbox_argv`/`_sandbox_probe` primitives directly — the exact same ones
`tests/test_swebench_sandbox_isolation.py::test_slash_tmp_is_private_and_must_exist`
already exercises for this property — spawning a small inline `python3 -c`
check inside a real `bwrap` namespace. **Corrected in the pre-registration's
Resolved review notes.**

**Second bug found on review, fixed:** the sandbox invocation originally
hardcoded `docker_mode="none"`, unconditionally, regardless of the campaign
environment's actual `SWEBENCH_SANDBOX_DOCKER` setting. A real campaign run
defaults to `broker`, and `SWEBENCH_SANDBOX_DOCKER=raw` binds the REAL
`/var/run/docker.sock` into the namespace — with that socket present, a
container can `docker run -v /tmp:/x ...` and reach the HOST's `/tmp` from
inside, which is exactly the channel this proof exists to close. A proof
that always wrapped `"none"` could never observe the one mode that defeats
it. Fixed: `cmd_p0_5a_check` now reads `A._sandbox_docker_mode()` and passes
that through; if it reads `raw`, the command FAILS outright with an
explanation rather than running a proof that cannot hold under that setting.
## `latency_from_trace.py` — the trace has no token-level streaming timestamps

`sssf-events.jsonl` records one landed-turn timestamp per model call
(`thinking`/`agent_message`), not first-token/last-token streaming chunks —
confirmed by inspecting a real archived trace event-by-event. The only
non-null `started_at`/`ended_at` pair anywhere in the file belongs to
`tool_call` events, and it brackets the TOOL's own execution (a few ms to
tens of ms for read/grep/bash), not the model call — measured: a
`tool_call`'s `started_at` lands within ~1ms of the preceding `thinking`
event's `ts`, and its `ended_at` matches its own `ts`. So
**request-to-first-token and first-token-to-last-token, as literally named in
the pre-registration's Measures row, are not separable from this trace
format.** `latency_from_trace.py` reports both fields as explicit `null` on
every call (never a guessed split) alongside the one real, measured interval,
`request_to_response_s` (queue wait + full generation, combined) — see the
script's own module docstring for the full reasoning. **Corrected in the
pre-registration's Resolved review notes.**

**A second, independent bug in the SAME script, found on review (cycle 2)
and fixed:** the original turn-grouping loop only opened a call on a
`thinking`/`agent_message` event; a turn whose response was tool-calls-only
(no preceding content event at all) was skipped one `tool_call` at a time and
its whole duration silently folded into the NEXT call. The cycle-2 fix (open
a call on the FIRST event of a turn group, content or `tool_call`) went from
47 to 48 derived calls against 51 declared in `sssf-turns.jsonl`.

**A THIRD bug, found on the cycle-2 review of that fix: the recovered 48th
"call" was never a model call at all.** Per-(phase, role) grouping showed
`{('c96a78f8_12_build', 'builder'): 47, ('c96a78f8_13_test_1', 'unknown'):
1}` — the second group is the harness's OWN `test_1` phase (the
deterministic test-execution step, not an agent invocation at all), whose
one `tool_call` is the test command. That phase has no `agent_start`, so
`role_of` never covers it and it was falling through to `role = "unknown"`
and being derived as a "call" — injecting a spurious ~1ms non-model interval
into `overall_request_to_response_s` AND, because the OLD cross-check summed
across every phase/role, masking the real per-role loss: it read "3 lost"
when the real number for role `builder` was still 4. **The "genuine,
honest limit of the trace format" sentence this section previously carried
about a 3-turn gap was FALSE and has been deleted along with the reasoning
that produced it.**

Fixed: `calls_for_run` now skips any phase absent from `role_of` outright
(`if phase_id not in role_of: continue`) before deriving anything from it,
and the cross-check is PER-ROLE rather than a single campaign-wide sum, so a
spurious call in one phase/role can no longer offset a real loss in another.
Re-measured on the same reference row:

| | derived calls (role `builder`) | `sssf-turns.jsonl` declares | gap |
|---|---:|---:|---:|
| cycle-1 (original bug) | 47 | 51 | 4 |
| cycle-2 (recovered a spurious non-model call) | 48 | 51 | 3 (miscounted — really still 4) |
| cycle-3 (this fix) | 47 | 51 | 4 |

The gap is back to 4 and is now the HONEST number — cycle 2's "recovery" was
illusory. **The cause of the remaining 4-turn gap is NOT YET IDENTIFIED.**
It is mitigated, not explained, by the per-role warning
(`role 'builder': derived 47 calls but sssf-turns.jsonl declares 51
assistant turns — 4 turn(s) are folded into a neighbouring call`), which is
now permanent in the script's output for any run, not just this reference
row, so the gap is always VISIBLE rather than silently absorbed or
misattributed to a plausible-sounding but unverified explanation.

Also fixed on review: `tool_exec_s` previously computed
`max(ended) - min(started)` across a turn's tool calls — a wall-clock SPAN,
which silently counted any gap BETWEEN sequential tool calls as "execution".
It now sums each call's own `ended - started` duration instead.

## Local verification (all $0, run 2026-08-27)

Environment: `AZURE_API_KEY` and `SAIL_RESEARCH_KEY` both supplied by
`/home/k/sssf/.env` (that file carries both; `/home/k/software-factory/.env`
also carries its own `AZURE_API_KEY` — either satisfies `p0_6-isolation`'s
Azure check, but only `/home/k/sssf/.env` has `SAIL_RESEARCH_KEY`, so
sourcing it alone is sufficient and is what every command below used).

| # | command | result |
|---|---|---|
| a | `uv run pytest -q tests/test_benchmark_regressions.py tests/test_swebench_sssf_arms.py tests/test_swebench_adapter.py tests/test_swebench_sandbox_isolation.py` | **PASS** — 295 passed, 1 skipped (a `--brokered` docker fixture skip, pre-existing, unrelated) |
| a | same command range, plus `test_swebench_acceptance_oracle.py`, `test_swebench_five_arm_report.py`, `test_swebench_archive_diagnostics.py`, `test_benchmark_record_store.py`, `test_bench_pinning.py`, `test_swebench_integrity.py`, `test_swebench_bare_openhands_arms.py`, `test_swebench_solo_noreview_arm.py` | **1 pre-existing FAIL**, unrelated to this work: `test_swebench_solo_noreview_arm.py::test_the_pre_registration_exists_and_binds_the_mde` — `FileNotFoundError: bench/swebench/PRE-REGISTRATION-B1.md` (the working tree already had that file moved to `frozen/` and the old path deleted, in the pre-existing dirty state, before this session touched anything). Not fixed here — out of scope. |
| b | `bench/swebench/phase0_sail_ab.py p0_6-isolation` | **PASS** — all 10 checks (both keys present and differ, models.json routes azure*/sail to the right vars, baseUrls differ, no proxy vars, `PYTHONNOUSERSITE=1`, `.venv/bin` stripped from PATH) |
| c | `run-all --arm <each of the 4> --instances hkuds__openharness-217 --dry-run` | **PASS** ×4 — each resolves `spend: ~$0.50/instance`, `-> bench/swebench/runs/hkuds__openharness-217/<arm>/`, "nothing was executed and nothing was written" |
| d | `p0_5b-stage --run-dir bench/swebench/runs/phase0-p0-5b-synthetic-leak/flash-solo` (source: real archived `getmoto__moto-9841/flash-solo`) → `uv run python bench/swebench_adapter.py audit --instance phase0-p0-5b-synthetic-leak --arm flash-solo` → `p0_5b-unstage` | **PASS** — audit emitted exactly ONE finding, `AUDIT FAIL: foreign-workdir: sssf-events.jsonl:160 named another arm's working tree ['planted__other-instance__planted-other-arm'] ...`, matching the planted line reported by `p0_5b-stage`; `audit FAILED (1 finding(s))`; unstage removed the staged dir cleanly |
| e | `p0_4-stage --from <synthetic source>` (built by hand — see "P0.4" above for why no real archive exists) → real `audit --instance harumiweb__exstruct-113 --arm flash-chain` → `p0_4-unstage` | **PASS** — staged over the LIVE attempt-3 row with a full backup first; audit emitted exactly ONE finding, `AUDIT FAIL: foreign-workdir: sssf-events.jsonl:160 named another arm's working tree ['OTHERINSTANCE__OTHERARM'] ...`; unstage restored the real row — file list and `md5sum` of `result.json`/`attempt.json` verified byte-identical to before staging, no backup dir left behind |
| — | `p0_5a-plant` → `p0_5a-check` (host control) → `p0_5a-check --inside-sandbox` → `p0_5a-clean` | **PASS** — plant writes `/tmp/report.json`; host-side control reports `STATUS: FOUND`; the `--inside-sandbox` child (spawned via the adapter's real `_sandbox_argv`/`_sandbox_probe`, `bwrap` 0.9.0) reports `STATUS: NOT-FOUND` — the planted marker is invisible from inside `SWEBENCH_SANDBOX=1`; clean removes it and a follow-up check confirms `NOT-FOUND` on the host too |
| — | `p0_7-keyscan` self-test | **PASS** — 0 hits scanning the two new `.py` files; a deliberately planted key value in a scratch file was correctly caught as exactly 1 hit, reported as `path:line` only, never the matched text |

### Deviation encountered and adapted, not silently

`p0_5a-check --inside-sandbox` originally re-invoked its own script file
(`sys.executable ... phase0_sail_ab.py p0_5a-check`) inside the namespace.
Both failed: `sys.executable` resolves to this shell's project-venv
interpreter (`/home/k/sacrifice/backend/.venv/bin/python3`), a path
`_sandbox_argv` never mounts, and even switching to `/usr/bin/python3` (which
IS reachable) still could not open the script file itself — `bench/
swebench/` is not among the namespace's bound paths. Fixed by inlining the
marker check as a `python3 -c` one-liner instead of re-invoking the file —
functionally identical, no adapter change required, and now proven working
(see row above). Not a weakening of the proof: the same `os.path.exists`/
content check runs either way.

## Open TBDs only the user (logged-in dashboard) can resolve

- **Absolute rates were found via free, public docs and are NOT a TBD** —
  contrary to the pre-registration's assumption that they require the
  logged-in dashboard. `docs.sailresearch.com/pricing.md` publishes them
  outright.
- P-2c's compat probe (`compat.supportsDeveloperRole` for the `sail`
  provider) — explicitly not run here (zero paid calls); left unset in
  `models.json` per instructions.
- Whether the billing dashboard's numbers (once real rows exist) reconcile
  with computed dollars within R2's thresholds — cannot be evaluated before
  any row exists.
- The exact free-credit balance/expiry on this specific Sail account — not
  exposed by any endpoint reachable without authentication beyond the bare
  key (the `/v1/models` call used here carries no balance field), and the
  usage/billing endpoints that would show it are POST-authenticated account
  surfaces this task was not authorized to call beyond the one free GET.

## Cycle 2 verification (post-review fixes, run 2026-08-27)

Adversarial review returned fixes-required (8 CRITICAL/MAJOR findings, 10
MINOR). Every finding applied; this section re-runs the full local
verification suite against the fixed code. Environment: same as Cycle 1
(`/home/k/sssf/.env`, both keys).

| # | command | result |
|---|---|---|
| a | `uv run pytest -q tests/test_benchmark_regressions.py tests/test_swebench_sssf_arms.py tests/test_swebench_adapter.py tests/test_swebench_sandbox_isolation.py` | **PASS** — full suite green, including the two new tests (`test_the_sail_rate_card_is_the_one_discovered_pre_freeze`, the `harness_id`-pin assertion) and the corrected `sail`-compat/coverage/cost-default assertions |
| b | `p0_6-isolation` | **PASS** — now 13 checks (was 10): added per-run TMPDIR/fresh-workdir structural checks, `_sssf_child_env`'s `problem` now surfaces as a named FAIL/PASS, proxy-var check now prints names only. Manually verified: `HTTP_PROXY=http://user:secret@evil.example:8080` → FAIL naming `['HTTP_PROXY']`, value never printed; `AZURE_API_KEY` unset → both the presence check AND the surfaced `_sssf_child_env` problem FAIL with the real message |
| — | `p0_7-keyscan` | **PASS** — with only one key exported, FAILS closed (`FAIL: both key values available to scan for`) instead of the old partial-scan PASS; with both keys, 0-hit clean scan still PASSes; an unreadable (chmod 000) file now FAILs the whole scan instead of being silently skipped |
| c | `run-all --arm <each of 4> --instances hkuds__openharness-217 --dry-run` | **PASS** ×4, unchanged from Cycle 1 |
| d | `p0_5b-stage` → real `audit` → `p0_5b-unstage` | **PASS** — exactly one finding at the planted line; `result.json` now confirmed rewritten (`instance_id: phase0-p0-5b-synthetic-leak`, `attempt: 0`); planted event's payload keys confirmed `['agent', 'args', 'duration_ms', 'ok', 'result_snippet', 'tool', 'tool_call_id']`; `p0_5b-unstage` now also removes the emptied `<instance>/` parent (confirmed absent afterward) |
| e | `p0_4-stage` (cycle 2: two events, one cell each) | **SUPERSEDED — see Cycle 3 below.** Cycle-2's two-event design produced two findings on two lines, which never exercised the real historical shape (one command naming both cells in one line); the mechanism was reworked in cycle 3 per NEW-3 |
| — | `p0_5a-plant` → refuse-on-foreign-marker → `p0_5a-check` (control) → `p0_5a-check --inside-sandbox` (broker mode) → `p0_5a-check --inside-sandbox` under `SWEBENCH_SANDBOX_DOCKER=raw` → `p0_5a-clean` → refuse-on-foreign-marker | **PASS** — plant refuses to overwrite a marker that exists without the sentinel (`FAIL: ... NOT this script's own marker`); control reports `FOUND`; sandboxed child (now run under the REAL detected docker mode, `broker`, not a hardcoded `none`) reports `NOT-FOUND`; the same check under `SWEBENCH_SANDBOX_DOCKER=raw` correctly REFUSES outright (`FAIL: ... This proof cannot hold under raw`) rather than running a proof that would not hold; clean removes only its own sentinel and refuses on a foreign one, same as plant |
| — | `latency_from_trace.py` re-run on the reference row (cycle 2) | **SUPERSEDED — see Cycle 3 below.** Reported "48 calls derived, 3-turn gap, genuine trace-format limit" — the 48th call was a spurious non-model interval from the harness's own `test_1` phase and the 3-turn figure was a miscount; both claims were false and are corrected in Cycle 3 |

All staging artifacts and scratch files removed after verification; `runs/`
and `bench/swebench/.phase0-backups/` confirmed empty of leftovers.

## Cycle 3 verification (post-review fixes, run 2026-08-27)

Reviewer verified all 19 cycle-2 fixes as real, then found four NEW issues
in the cycle-2 work itself (one MAJOR — the cycle-2 latency fix recovered a
spurious non-model call, not a real turn; one MAJOR — the phase-0 staging
backup dir was not gitignored and could publish hidden test ids; two MINOR).
All four applied; re-verified below.

| # | command | result |
|---|---|---|
| NEW-1 | `latency_from_trace.py` on the reference row, `runs/getmoto__moto-9841/flash-solo` | **PASS (fixed)** — `calls_for_run` now skips any phase absent from `role_of` (no `agent_start` ⇒ not an agent invocation, e.g. the harness's own `test_1` phase) before deriving anything from it; the cross-check is now per-role. Re-measured: **47 calls derived for role `builder`, `sssf-turns.jsonl` declares 51** — one per-role warning (`role 'builder': derived 47 calls but sssf-turns.jsonl declares 51 assistant turns — 4 turn(s) are folded into a neighbouring call`); `min(request_to_response_s)` across all calls is now 1.245s, confirming the spurious ~0.001s non-model interval is gone from the distribution. The cause of the 4-turn gap is NOT identified — only mitigated by the warning; SAIL-DISCOVERY.md's earlier "genuine trace-format limit, not a bug" sentence (cycle 2) was false and has been deleted (see the corrected `latency_from_trace.py` section above) |
| NEW-2 | `git check-ignore -v bench/swebench/.phase0-backups/probe/x.txt` | **PASS** — `.gitignore:140:bench/swebench/.phase0-backups/	bench/swebench/.phase0-backups/probe/x.txt`; entry added to the ROOT `.gitignore` beside the existing `bench/swebench/runs/` line (not `bench/.gitignore`, which is a different, nested file) |
| NEW-3 | `p0_4-stage` (default source) → real `audit --instance harumiweb__exstruct-113 --arm flash-chain` → `p0_4-unstage` | **PASS (reworked)** — now plants ONE `tool_call` event (`tool: bash`, `args.command` a single shell command naming both cells) instead of two single-cell events. Audit output: **exactly ONE finding**, `AUDIT FAIL: foreign-workdir: sssf-events.jsonl:205 named another arm's working tree ['harumiweb__exstruct-113__v32-solo', 'harumiweb__exstruct-113__bare']` — the multi-match dedup path of `_foreign_workdir_hits` is now actually exercised, matching the real historical row's shape (one command, one line, both cells). Unstage restored the real attempt-3 row — file list and `md5sum` of `result.json`/`attempt.json` verified byte-identical to before staging |
| NEW-4a | `p0_4-unstage`, then check for the backups parent | **PASS (fixed)** — `_PHASE0_BACKUPS_DIR.rmdir()` (suppressing `OSError`) now runs at the end of unstage; confirmed `bench/swebench/.phase0-backups/` no longer exists after the cycle above (`ls`: "No such file or directory") |
| NEW-4b | `_neutralize_result_json` docstring | **DONE** — now states precisely that only `instance_id`/`attempt` are rewritten, and explains (citing `benchmark_store.py::ingest_row`'s `key = run_dir.name` / arm-mismatch skip) that a stale `arm` field is an ACTIVE third guard causing `record` to refuse the row outright, not merely "harmless" |
| — | full regression suite (`tests/test_benchmark_regressions.py tests/test_swebench_sssf_arms.py tests/test_swebench_adapter.py tests/test_swebench_sandbox_isolation.py`) | **PASS** — unaffected by this cycle's fixes, still fully green |

All staging artifacts, the `.phase0-backups/` probe directory, and scratch
files removed after verification.

## P-2c — compat reachability probe (2026-08-27, the one disclosed pre-freeze paid call)

Run via `_sssf_reachability_report(['sail/deepseek/deepseek-v4-flash-0731'], …)`
with the live price table, `SAIL_RESEARCH_KEY` from `/home/k/sssf/.env`.

- **Result: reachable, HTTP 200, `system_role_sent: "developer"`, non-empty
  reply** — Sail's serving accepts the `developer` role, so
  `compat.supportsDeveloperRole: true` was written to the sail entry in
  `~/.pi/agent/models.json`. MEASURED, not assumed.
- Usage: 12 input / 44 output / 0 cached tokens.
  **`preflight_probe_cost_usd = $0.000009`** (12×0.09 + 44×0.18 per M),
  re-derived through `_sssf_rederive_cost` with the roster-built rate table —
  under the $0.01 cap. This constant enters the campaign ledger and R2's
  computed side.
- **Disclosed misfire, $0.00:** a first invocation used
  `sail/deepseek-v4-flash-0731` (dropping the model id's own slash) and was
  refused at the catalog layer (`provider 'sail' declares no deployment …`)
  before any network call. The ledger counts attempts; this one cost nothing.
- **Instrument note:** calling `_sssf_rederive_cost` with the RAW models.json
  instead of the flattened `_sssf_price_table(models)` output returns $0.0 with
  the model listed in `models_missing_a_rate` — disclosure, not discount,
  working as designed. The run path builds the flattened table itself; only
  standalone invocations can make this mistake.

### P-2d — final sha re-pin (2026-08-27)

The compat write moved the whole-file hash `dd22d0f5…3cf8a` →
`eec3fa6889d33d5288b7ec8bcfc3c6ec3e2c4e2884a9f41cbfec30ab77a3ff6f`;
`_PI_PRICE_TABLE_SHA256` re-pinned to it (the FINAL pin — P-1 freezes against
this value). Re-verified post-edit: the delete-sail-and-rehash recipe above
still reproduces `fbab9ac0…c45a`, so no azure byte moved. Test suite green,
including `test_the_sail_rate_card_is_the_one_discovered_pre_freeze` and the
compat-boolean branch of the DeepSeek compat test.

## Campaign row validity — supersession of the frozen P-1 sha rule (2026-08-27)

The frozen pre-registration requires every campaign row to stamp the freeze
commit (`71668e04…`) with a clean tree. Phase 0 proved that rule
unsatisfiable as written, for three mechanical reasons:

1. `_repo_state` counts ANY `git status --porcelain` line as dirty —
   including untracked files — so the results artifact
   (`frozen/RESULTS-SAIL-AB.md`), which must exist during the campaign,
   would mark every row dirty.
2. P0.2's selftest rewrites tracked artifacts (`selftest.json`,
   `selftest-logs/*.log`) as a normal side effect.
3. Every `run-all` invocation writes `sweep-<arm>.json` at sweep end, so a
   multi-invocation campaign cannot hold one sha with a clean tree between
   invocations.

Frozen records are never edited; per the standing rule the frozen text is
superseded HERE and linked back. **The superseding validity rule:** a campaign
row is provenance-valid iff

- its stamped `sssf` sha is exactly `eb9dcffd661c5228369cbab236a4ff13fe5fedff`, and
- its stamped bench sha is `71668e04…` **or a descendant** whose cumulative
  diff from `71668e04…` touches ONLY campaign-record files —
  `bench/swebench/frozen/RESULTS-SAIL-AB.md`, `bench/swebench/selftest.json`,
  `bench/swebench/selftest-logs/*`, `bench/swebench/sweep-flash-solo-az-r2.json`,
  `bench/swebench/sweep-flash-solo-sail*.json`, and this file — and no code,
  config, prompt, or registry file, and
- the tree was CLEAN at stamp time (`dirty: false` in the row's provenance).

Operationally: campaign-record files are committed after every `run-all`
invocation, before the next one launches. Any commit touching any non-record
file voids pairing for all rows that follow it, per the frozen spec's own
engine-drift threat. The audit query that re-checks this:
`git diff --name-only 71668e04..<row sha>` must be a subset of the record
list above, for every distinct sha the campaign's rows carry.

## Phase 1, attempt 1 — Sail rejects `store=false` (2026-08-27)

The first real Sail row (`flash-solo-sail-p1`, `hkuds__openharness-217`,
width 1) terminated `provider-empty-response` in 9.8 s: **3 assistant turns
with empty content and all-zero usage**, $0.00 metered. The captured provider
reason — recorded verbatim in the row thanks to the engine's stderr-drain and
EmptyResponse fixes — was:

> `400 store=false is not supported. Responses are always stored.`

Root cause: pi sends the OpenAI `store: false` field on chat-completions
requests when it detects a standard OpenAI-shaped provider; Sail's compat
layer rejects the field outright. The P-2c probe passed because the probe
never sends `store` — so "the probe sends what pi sends" held for the ROLE
layout it was designed around, not for every field. Fix: pi's documented
`compat.supportsStore: false` (send-only-if-supported,
`pi-ai/dist/providers/openai-completions.js:370`) — set on the sail entry;
models.json sha re-pinned `eec3fa68…` → `f8ddda8b…`; the
delete-sail-and-rehash recipe still reproduces `fbab9ac0…c45a`.

Two findings beyond the fix:

1. **Baseline advance, disclosed:** this touched a code file (the adapter's
   pin), which the row-validity supersession above only tolerates before any
   paired row exists. None did — the failed row is probe-arm, never verdict
   or cost evidence — so the campaign baseline advances to the commit carrying
   this note, and Phase 3's two arms both run entirely after it. The failed
   attempt stays in the store, flagged provider-starved, as the disclosed
   infrastructure loss; the spec's one-repair-per-cell rule covers the re-run.
2. **Privacy finding for the operator:** Sail's API states outright that
   responses are ALWAYS stored, while the vendor's public materials claim
   ZDR by default. Whatever the resolution, code sent to Sail during this
   campaign should be assumed retained. Worth raising with the vendor before
   the evolution campaign ships anything sensitive there.
