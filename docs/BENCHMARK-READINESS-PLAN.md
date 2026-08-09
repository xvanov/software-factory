# Benchmark-readiness plan — oracle authority, harness integrity, end-to-end proof

**Written** 2026-08-09, after factory PR #279 (`factory resume-story`) and the
oracle-authority research in `SOTA-RESEARCH-2026-08-oracle-authority.md`.

**Audience.** A loop-3 agent (you). Read `CLAUDE.md` first, then the memory index,
then `STATUS.md`. This plan assumes all three.

**Objective.** Make the factory *pristine* for a benchmark run: every gate
truthful, no false blocks from stale config, no hamster wheels, no terminal sink
without a path back. The benchmark must measure the chain's capability, not the
harness's drift.

> **Why this is urgent and not cosmetic.** OpenAI's own SWE-Bench Pro audit names
> **"overly strict tests — hidden tests require implementation details not in the
> prompt → correct solutions fail"** as its single largest defect category
> (**14.4%** of 731 tasks), and SWE-bench Verified filtered **68.3%** of the
> original benchmark, flagging **61.1%** of samples for tests that unfairly fail
> valid solutions. **That is our current failure mode.** If we benchmark before
> fixing it, our numbers contain an unknown, unseparable false-block component
> and cannot be compared to anything. See the research file for citations.

---

## Definition of done

All of these, verified against **real artifacts**, never a recorded flag:

1. Every route path and required field in `acceptance_harness_hint` is
   mechanically cross-checked against the app's real surface by a CI test, so a
   drifted API fact cannot reach an oracle author undetected. (The semantic facts
   — plugin-type enums, error vocabulary, response bodies — stay prose. That is
   an accepted limit, not an oversight; see A1.)
2. Base-run status observation is recorded as **advisory diagnosis only**, with
   ≥20 runs of data accumulated before any classification is proposed.
3. The `explore` + AC-scope decision (A4) is made and implemented.
4. The information-budget ablation has been run and its numbers are committed,
   including the **waiver / `oracle_not_discriminating` rate** (A1 can make
   oracles WEAKER, and that is the dangerous direction — see B).
5. Every open harness defect below is either fixed or explicitly deferred with a
   written reason.
6. **Three fresh stories drive end-to-end, unattended, each to a MERGE COMMIT on
   GitHub** with `acceptance-verified` in `merge_actions.gates_passed_json` and
   `stub_runs.json` + `base_runs.json` on disk — no operator intervention, no
   block, no repeated-work loop. **Not "deployed":** `deploy.enabled: false` on
   sacrifice, so `deployed` is a STATE NAME, not a deploy (`STATUS.md`: all 102
   `deploy_actions` rows skipped or errored). Using it as evidence is `proxy ≠
   real`, this repo's most common bug class, in its own readiness plan.
7. `factory audit-chain` reports no tampering; `factory inbox` is empty of
   needs-human rows; `uv run pytest -q` exits 0; live tree == `origin/main`.

**None of 1–6 may be claimed from a green test run alone.** Name the commit SHA
or merged PR for every fix (memory: `session_fix_claims_need_git_verification` —
a prior session reported two fixes that were never committed).

---

---

# How to execute this — be efficient, parallelise, but ground everything in a running factory

**Two rules that fight each other, and the second one wins.** Fan out
aggressively for anything that is *reading, searching, or implementing in
isolation*. Serialise ruthlessly for anything that *touches the live factory*.
Getting this backwards produces fast, confident, wrong answers.

### Delegate by difficulty — pick the cheapest model that can do the job

Pass `model` explicitly on every `Agent` call. Do not let everything inherit Opus;
most of this plan's work does not need it.

| Model | Use for | Examples from this plan |
|---|---|---|
| **haiku** | mechanical, verifiable, low-judgment | grep sweeps for a pattern; listing routes/config keys; collecting `factory trace` output; checking for leaked docker networks; tallying spend from `factory audit` |
| **sonnet** | standard implementation and analysis with a clear spec | C3 (resume the two parked stories); C7 (environment hygiene); writing the D-1/D-2/D-3 directions; most test-writing; doc refreshes |
| **opus** | design judgment, adversarial review, anything where being wrong is expensive | A1's cross-check design; **A4's `explore`/AC-scope call**; C1 (shared control flow); the adversarial pass on every fix; interpreting B's ablation numbers |

Rule of thumb: **if the task has one right answer that can be checked by running
something, go cheaper. If it involves a trade-off, an invariant, or a safety
direction, go to opus.** The adversarial review pass is always opus — it has
caught ~5 production bugs that green tests hid.

### Parallelise these (independent, no shared mutable state)

Send them in **one message with multiple `Agent` calls** so they actually run
concurrently:

- **Investigation fan-out**: C2 (tech_writer JSON), C4 (oracle KNOWN OPEN #2–#4),
  C6 (the config-fact sweep) are three independent read-only questions. One agent
  each, in parallel, at the tier the question deserves.
- **Independent implementation**, with a caveat found by adversarial review:
  A1 and A2 look independent (`acceptance.py` authoring vs
  `acceptance_verified.py` base run) but **do collide**. Both are referenced by
  `tests/test_acceptance_oracle.py` and `tests/test_acceptance_oracle_executable.py`;
  A2 needs a `RUNNER_VERSION` bump (`oracle_run.py:73`) that is in BOTH the
  stub-run and base-run cache keys; and A1 changes the prompt, so `oracle_sha256`
  changes, invalidating every cached run **and every `waiver.json`** (waivers are
  scoped to oracle content, `acceptance.py:652`). **Serialise A1 and A2**, or
  scope A1 to production code and land its test changes in an integration pass.
  After either lands: delete `state/acceptance/*/*/[base|stub]_runs.json` and
  re-check waivers — a stale cache keyed on an old `RUNNER_VERSION` is the classic
  `compose-bugs between fixes` shape.
- **Direction drafting**: D-1, D-2, D-3 are three separate documents — draft
  concurrently, review together.
- **Research**: any external-literature question. Warn every research agent about
  the fetched-text corruption (see below).

### Do NOT parallelise these

- **Anything writing `state/factory.db`.** One writer per fact. Two agents
  ticking, resuming, or repairing stories at once will corrupt state, and a DB
  edit races a live tick.
- **`factory tick` / `factory on` / deploys.** Serialise. The tick is the
  factory's single-threaded heartbeat; running two is not a speedup, it is a race.
- **The Workstream D proof itself.** It is a *measurement of unattended
  behaviour*. Running three stories concurrently is fine **only if that is the
  real configuration you intend to benchmark** — otherwise you have measured
  something you will not ship. Decide, then keep it constant.
- **The full test suite.** ~17–19 min locally. Run it once, at the end of a batch
  of changes, not per-agent. Concurrent pytest runs contend and produce mirages
  (memory: `red_test_can_mean_nothing_too`).
- **Docs stories.** Running D-1/D-2/D-3 concurrently produces three concurrent
  `tech_writer` docs stories; parallel docs PRs conflict and only one docs story
  may be in flight per app (memory: `docs_chain_serialization`). This matters
  doubly because C1/C2 are *about* tech_writer failures.

### Ground everything in a running factory — nothing counts until the factory did it

This is the part that cannot be delegated away. Subagents produce *claims*; the
factory produces *evidence*. Every claim in this plan is closed by an artifact,
not by a report:

| Claim | What actually closes it |
|---|---|
| "the fix is in" | a commit SHA or merged PR — a session's summary is a self-report, and one prior session reported two fixes that were never committed (memory: `session_fix_claims_need_git_verification`) |
| "the oracle is correct now" | a real gate run: `state/acceptance/<app>/<id>/stub_runs.json` + `base_runs.json`. **The gate emits NO events** — those files are the only proof it ran (memory: `acceptance_oracle_validated_live_2026_08_08`) |
| "the story merged" | GitHub's merge commit. Never a local flag |
| "it deployed" | the change present on `origin/main`. **`deployed` the STATE is not a deploy** — `deploy.enabled: false` on sacrifice, so every `deploy_actions` row is skipped |
| "no hamster wheel" | `factory audit --app <app>` showing no repeated spend on the same persona/story, and `factory trace <id>` with no repeating event signature |
| "the services sustain" | `systemctl --user status` Result + `errors=` across **two** runs. "Services up" ≠ "sustains" |

**Therefore: after every fix, run the factory and watch it.** Do not batch six
changes and then look. The repo's own history is a list of fixes that were green,
reviewed, and still did not work unattended — that is failure pattern
`marked-solved ≠ soak-validated`, and it is the single most repeated mistake here.

**Never take a subagent's result at face value.** If an agent reports a story
merged, check GitHub. If it reports a gate passing, read the artifact. Agents
report incorrect or misleading results, and a confident summary is not evidence.

### Two standing hazards when delegating

1. **Research agents and fetched text.** The org-level `DESIGN → ENGINEERING`
   rewrite is applied to *fetched web content*, not only authored prose — it was
   **confirmed live** during this plan's research. Instruct every research agent:
   cite by URL + arXiv id, treat a fetched **name** as lower-confidence than a
   fetched **number**, and flag any suspicious title rather than reporting it as
   fact.
2. **Wait-loops that never exit.** `until ! pgrep -f "<pattern>"` matches the
   waiting shell's **own argv** and loops forever (three such loops were left
   running during this session's work). Wait on a *file* or an exit code, or match
   a pattern that cannot match the watcher itself.

## Guardrails that bind this whole plan

- **Gate on the real artifact.** Never a recorded flag, an `--auto` *enable*, a
  dry-run's intent, or a green test run with no commit. `proxy ≠ real` is the
  most common bug class here.
- **Fail SAFE.** A broken detector/gate must BLOCK, not wave things through. When
  changing the oracle, the direction of any new failure must be false-block, never
  false-green — the latter is unrecoverable, the former merely costs a resume.
- **Nothing loops more than 3 times**, and any early-escalation guard stays
  strictly below the hard cap or it is unreachable.
- **Never `git add -A`** in the live tree. Deploy surgically.
- `factory/manager/**` and `bench/**` are operator-PR only.
- **Fixes to shared control flow do not compose for free.** Touching
  merge/reconcile/dispatch means re-verifying everything keyed off it.
- Spend caps in `factory_settings.yaml`. **Notify the operator at $50 / $75 / $100.**
- Do not weaken an existing test to make new code pass. Two tests in
  `test_cli_inbox.py` / `test_dependency_deferral_cap.py` pin deliberate
  invariants; PR #279 made a new feature opt-in rather than relax them. Do the same.

---

> **REVISED 2026-08-09 after adversarial review.** The first draft of this
> workstream rested on two premises that are FALSE against this codebase, and
> shipping it would have made the gate worse. Both are recorded here rather than
> quietly deleted, because the next person will have the same two ideas:
>
> **False premise 1 — "OpenAPI carries the missing facts."** It does not.
> `grep -n "responses=" backend/app/routes/*.py` returns **zero hits** in
> sacrifice; every non-2xx is raised via bare `HTTPException`. Measured directly:
> `POST /api/goals` declares only `['201', '422']` — **no 401**. Key routes
> (`GET /api/auth/me`, `POST /api/goals`) have no `response_model`, so OpenAPI
> reports an untyped `{}`. And the constraint that actually blocked story 179 —
> `goal_type` must be a REGISTERED PLUGIN TYPE, and `"youtube_video"` expects
> `criteria: {min_duration_seconds, video_description}` — lives in a
> `field_validator` (`backend/app/schemas/goal.py:33-48`) and the plugin
> registry, **invisible to the schema**. The current prose carries facts the
> derived surface does not (`config.yaml`: "a duplicate email is
> `409 {"error": "account_exists"}`; a weak password is `400`"). Replacing prose
> with OpenAPI is a NET LOSS of exactly the facts that caused the incidents.
>
> **False premise 2 — "the base run can classify HTTP status."** It cannot.
> `_base_run` sees only junit `{nodeid: PASS|FAIL|ERROR|SKIP}`
> (`oracle_run.py:208-232`; `OracleRun` carries no HTTP data), plus
> `boot.probe_paths`, which is explicitly *"a BLIND replay — no request body, no
> auth headers"* (`boot.py:358-397`). A blind `POST /api/auth/email/register` is
> **422 by construction, always** — as recorded in story 179's own
> `base_runs.json`.

# Workstream A — oracle source of authority

**The defect.** The acceptance author is dev-blind (correct — that is the
anti-reward-hack freeze). But it needs route paths, request schemas and status
codes it *structurally cannot obtain*, so those come from **hand-written prose**
(`gates.acceptance_harness_hint`). The author cannot detect drift — being unable
to check is the point — so a stale fact is laundered into an authoritative oracle
that blocks a correct implementation. Three instances, three patches at the fact,
zero at the mechanism.

**The principle is already right**: `acceptance.build_spec_prompt`'s docstring
already argues the hint is not an independence leak. Total blindness was rejected
in practice (it produced `No module named 'app'`, 2026-08-05). Do not re-litigate
the freeze; it is well-supported (ImpossibleBench arXiv:2510.20270 — whose
mitigation is denying the **dev** test access, never denying the **author** the
API surface).

**But the prose is not going away.** The honest conclusion from the review is
that a machine-derived surface cannot carry the semantic facts (plugin-type
enums, error vocabulary, response bodies). So the goal changes from *replace the
prose* to **make the prose impossible to drift undetected.**

### A1. Derive the surface as an ADDITIVE CROSS-CHECK on the prose (not a replacement)

Keep `acceptance_harness_hint` as the source of semantic truth. Add a derived
artifact and a **consistency test** between them.

- **Derive** the OpenAPI surface, scoped to **the routes the direction's
  `api_spec.md` names, plus auth** — never all 55 routes. sacrifice has 55 route
  decorators and 31 schema classes; an unpruned dump is 10–20× the current
  2,895-char hint and would dilute the acceptance criteria in a 4096-token
  authoring call. Add a size assertion.
- **Cross-check**: every route path and required field named in the prose hint
  must exist in the derived surface. Extend
  `tests/test_sacrifice_acceptance_harness_hint.py`, which already pins the auth
  routes as a deliberate invariant (*"that coupling is the point"*). **Do not
  weaken that test** — extend it.
- **This catches incidents 1 and 3-part-A mechanically at CI time**, with no boot,
  no per-story cost, and no new terminal sink. It does not catch the semantic
  half; that stays prose, and that is an accepted limit, stated here rather than
  wished away.
- **Optional app-side follow-up:** file a direction adding `responses=`
  declarations to sacrifice's routes. That is what would make the error
  vocabulary genuinely derivable. Until then it is prose by necessity.

**If a per-story derived surface is later fed to the author** (beyond the
cross-check), these become binding:

- **Base sha must be verified, not assumed.** Authoring runs at spawn
  (`handlers.py:373`, during pm-sync, before any branch exists); the gate computes
  `base_sha = merge-base(origin/<base>, HEAD)` (`red_green.py:426-439`) from a
  branch created later at dispatch. `auto_merge.enabled: true` with
  `per_repo_concurrent_agents: 10` means **main routinely moves between those two
  moments** — story 179's graded base (`679c091a4219`) was a commit merged in the
  same session. So: record the surface's sha and have the gate **BLOCK on
  `api_surface.base_sha != base_sha`**. Silent drift becomes a named block.
- **Never re-derive on a `force=True` re-author.** Two `explore: true` alternates
  are competing full attempts, not slices (memory:
  `oracle_grades_direction_acs_not_story_scope` — 23 pairs, 20 superseded). If a
  loser's oracle is re-authored later, re-deriving from a *current* origin/main
  would hand it the winner's implementation of the same spec — a genuine
  implementation leak into the channel this design asserts cannot leak. Reuse the
  stored surface, or refuse.
- **Fail-closed must keep a path back.** The "expected but no oracle" gate branch
  (`acceptance_verified.py:495-507`) returns a `GateResult` directly with
  `authoritative: True` and never calls `_unverifiable`, so there is **no
  `waiver_sha` and `factory acceptance-waive` cannot touch it** — operator-only,
  forever. Before adding any new way to reach it: route it through
  `_unverifiable(..., waiver_sha=oracle_sha)` or add `factory
  acceptance-rederive`. Also call `boot.check_prerequisite` first and treat
  "prerequisite down" as **not a failed authoring pass** — a down `sacrifice-db`
  must never burn one of the three `_MAX_AUTHOR_PASSES`. Cap derivation at **1
  per tick**, not `max_per_pass: 10`.

### A2. Base-run status observation — ADVISORY INSTRUMENTATION ONLY

> **The first draft made this the "cheapest, highest-value, ship-it-regardless"
> item. It was the opposite on all three counts, and it would have blocked story
> 179 — the correct, deployed story this plan cites as its success case.**

The proposed taxonomy was *404/501 = feature absent (valid red); 400/422 =
malformed oracle (block)*. It inverts on this app. Story 179's own
`base_runs.json` records, at a base where `goal_count.py` did not exist:

```json
{"method":"GET","path":"/api/goals/count","status":401}
```

`GET /api/goals/count` is shadowed at base by `@router.get("/{goal_id}")`
(`goals.py:163`), whose `Depends(get_current_user)` fires **before** a 404 can be
produced. In a FastAPI app with parameterised routes behind an auth dependency —
most of sacrifice's 55 — **"feature absent" presents as 401/403, and 404 is the
exception.** A blocking taxonomy here is a false-block *generator*, shipped into a
live required merge gate in the name of curing false blocks.

**So: record, classify nothing, block on nothing.**

- Add observed base statuses to the gate's `details` for diagnosis.
- Accumulate **≥20 base runs** before proposing any classification.
- A future blocking version needs per-request statuses out of the oracle
  process — a new channel from `run_oracle`, whose entire design point is that
  nothing crosses back except junit (`oracle_run.py:1-52`), plus a
  `RUNNER_VERSION` bump (`oracle_run.py:73`) that **invalidates every cached stub
  and base run**. That is the most invasive item in this plan, not the cheapest.
- **Strike the claim that this catches anything "at authoring time".**
  `_base_run` is called from `_evaluate` (`acceptance_verified.py:890`) — the
  merge gate, after full dev spend. Of the three incidents it would have caught
  at most one, and only at merge time: incident 1 yields 404 → "valid red,
  proceed"; incident 2 is body-level and the gate has no body data at all.

A cheaper diagnostic that carries **no route-topology assumption**, using data the
gate already holds (`stub_criteria_by_variant`, `acceptance_verified.py:665`):
flag when a credited criterion's base failure is **identical to its failure
against the `200 {}` stub**. That is suspicious without asserting what any status
code means.

### A3. Separate arrange from assert — MOVED BEFORE A2

Setup ("create a goal so the count can increment") is not a behavioural judgment
and carries no independence requirement. Today a `422` on setup is reported as a
verdict on the story — a category error, and what blocked story 179.

**A2 depends on this, which is why it now comes first.** The proposed
"401/403 *on a setup call*" row presupposes an arrange/assert distinction that
does not exist yet: in 179's oracle (`test_acceptance.py:63-67`) the 401 arrives
on the *assertion* call while `_register` (setup) succeeds — one criterion, two
roles, one junit verdict.

Minimum: classify and report setup failures distinctly from assertion failures so
they can never be read as "the feature is wrong". Better: let setup use the app's
own fixtures/factories rather than oracle-authored HTTP bodies. Inference, not a
cited finding — but it is the split arXiv:2504.07244 found *necessary* in industry
(scenario stage 95% helpful from the story alone; executable stage required the
page HTML, semantic relevance 60% → 92%).

### A4. Decide the `explore` + AC-scope block — NEW, and it will dominate D

Memory `oracle_grades_direction_acs_not_story_scope` (2026-08-08/09) documents
three mechanisms that **jointly guarantee** a block: `explore: true` emits
competing alternates; SM writes them as if they were slices and descopes ACs to
"siblings" that never exist; and the author grades against `direction.acceptance`
(`acceptance.py:422`), not the story's scope. The memory ends *"Not yet decided —
needs an operator call."* **That call is still outstanding, and it is the
structural cause of the 173/177/178 family** — not the shape A1/A3 address.

Pick one and implement it: scope the oracle to the story, forbid SM descoping
under `explore`, or make `explore` emit real slices plus an integration story.
Until then every AC-carrying `explore` direction carries a ~50% structural block
rate that would swamp Workstream D's signal.

# Workstream B — measure before benchmarking

The research found a **genuine published gap**: nobody has run a controlled
ablation of oracle-author information budget. We can, cheaply — we already have a
vacuity control, a reviewer-replay corpus, and a per-run cost meter.

**Arms** (same stories, same models, `k` repeats):
1. **no surface** — criteria only (today's nominal design)
2. **prose hint** — today's actual behaviour, as a control
3. **derived base surface** — A1
4. *(optional, expect it to be bad)* **HEAD surface** — to demonstrate the
   false-green risk that justifies choosing base

**Measure**: false-block rate (correct implementation rejected), false-green rate
(gutted implementation accepted — the stub control already gives this), authoring
cost, and time-to-merge.

**AND the metric adversarial review says is the real risk — pre-register a
threshold on it.** More base information means more oracles that MIRROR the base
contract. Such an oracle **passes at base**, so `verdict_over` returns `green` →
`oracle_not_discriminating` (`acceptance_verified.py:896-905`) → which is
**waivable** (`waiver_sha=oracle_sha`) → and `_unverifiable` then returns
`passed=True` with the text *"the oracle did NOT verify this story"*. Under a
2 h/day ratification budget, a rising waiver rate is a **false-green pipeline**.
The first draft of this plan asserted "false-block is recoverable, false-green is
not" and never noticed that its recovery mechanism for false blocks IS the
false-green channel. So: track `oracle_not_discriminating` + waivers-granted per
arm, add a waiver counter to `factory inbox`, and **if that rate rises versus the
prose control, A1 has made oracles weaker regardless of what the false-block
number does.**

**Pre-register the arms and the metric before running** — the ablation gate has
been misused before (memory: `ablation_gate_dormant_and_broken`; never flip
`mutation_testing` as an experiment). Archive artifacts per run; **re-running a
sweep destroys published-number artifacts** (memory:
`bench_artifacts_overwritten_2026_08_02`).

Expected outcome: arm 3 ≥ arm 2 on false-block with no false-green regression. If
arm 3 does *not* beat arm 2, **stop and report that** — do not ship A1 on faith.

---

# Workstream C — harness and plumbing defects

Each of these is known and open. Fix or explicitly defer with a written reason.

### C1. Late-stage failure rebuilds from `SM_DONE`
`orchestrator._recover_blocked_stories` re-enters `BLOCKED_REVIEW_NONCONVERGENT`
at `SM_DONE`, re-running SM + dev + review to retry a **tech_writer** step. Story
177 burned **$5.96** over two recoveries rediscovering that its tech_writer model
would not emit parseable JSON. PR #279 added `--at tech_writer` for the operator;
the automatic path is still blunt. Re-enter at the failed step's own predecessor.
*Shared control flow — re-verify everything keyed off it.*

### C2. tech_writer JSON-parse fragility
Story 177's model never returned a parseable JSON object in 2 attempts, then
burned 2 full recoveries. Establish whether this is prompt, model routing, or
parser strictness. A persona that cannot emit its output format is a benchmark
confound.

### C3. Resolve the two remaining parked stories
177 (`blocked_review_nonconvergent`, $5.96) and 178 (`blocked_budget_exceeded`,
$12.41 vs a $12.00 cap). Use `factory resume-story`; 178 needs either a cap
raise or `--force` (never zero the ledger). The inbox must be empty before the
benchmark.

### C4. Oracle runner KNOWN OPEN #2–#4
From `factory/chain/gates/acceptance_verified.py`'s module docstring. #1 was
closed by PR #256. Each open one has a named v1.1 candidate — read them before
any soak. Decide per risk: fix, or accept with a written justification.

### C5. `detector_watch` soak
Ships disabled (`detector_watch.enabled: false`). The first cut would have filed
**48 unfixable directions in ~16 ticks**; liveness+recency scoping was added but
has **never run in production**. Either soak it read-only against live state and
enable, or leave disabled and say so. Do not enable it untested during a
benchmark.

### C6. Sweep for the same class as A1
The defect class is "a hand-maintained fact the consumer cannot verify." Grep the
config surface for others: `acceptance_boot`, gate commands, route tables,
`app_repo_path`. Anything a persona is told and cannot check is a latent false
block. Report what you find even if you fix nothing.

### C7. Environment hygiene
- Leaked docker networks/containers make host-only test gates red invisibly
  (sacrifice #394). Verify none are leaked before the run.
- The dirty-app-tree redeploy failure (memory:
  `dirty_app_tree_fails_the_redeploy_timer`) — `unit-active ≠ unit-working`.
- Establish the local suite baseline *before* blaming any diff (memory:
  `red_test_can_mean_nothing_too`): CI `pytest` has a 25-min cap and the local
  suite runs ~17–19 min.

---

# Workstream D — end-to-end proof

**The necessary condition for benchmarking. Not, on its own, a readiness proof —
see the power note at the end.**

Write **three fresh directions** against `sacrifice`, all with **`explore: false`,
stated explicitly in each direction and justified there.** Under `explore: true`
SM emits two competing alternates and `superseded_by_sibling` is the NORMAL,
CORRECT outcome for half of them (measured: 23 pairs → 23 deployed / 20
superseded, memory `oracle_grades_direction_acs_not_story_scope`). The first draft
listed that sink as a plan failure, which would have auto-failed on correct
behaviour. The trade-off is explicit: `explore: false` is not the shipping
configuration, so D tests the chain's *mechanics*, and the explore path is
covered by A4 instead.

| # | Shape | Exercises | Constraint |
|---|---|---|---|
| D-1 | a new read endpoint, no setup state | the simple path end-to-end | purely additive |
| D-2 | a criterion needing **prerequisite state** (create an entity, then observe) | **A1 + A3** — the setup-vs-assert split | purely additive; see the KNOWN OPEN #2 note below |
| D-3 | a change to an **existing** endpoint's behaviour | how the harness handles a route that already exists | **blast-radius bounded — see below** |

**D-3 is the shape that has already killed a direction.** Direction 117 gated an
existing route (`POST /api/goals`), broke ~40 sibling tests, exhausted both
alternates and 6 dev attempts, burned ~$14, and terminated as story 177
(`blocked_review_nonconvergent`) + 178 (`blocked_budget_exceeded`) — measured
2026-08-09, the same day as this plan (memory:
`direction_117_was_oversized_for_one_story`). And `caps.per_story_spend_usd: 12.0`
is a **terminal** breaker. So: before filing D-3, run
`grep -rl "<route>" backend/tests/` and **pre-register the number in the
direction**; require ≤3 files. Prefer adding a field to an existing response over
changing existing behaviour. **Decide in advance** whether a
`blocked_budget_exceeded` on D-3 falsifies the plan or is out of scope — do not
decide after seeing the result.

**KNOWN OPEN #2 and D-2.** `acceptance_boot.env` points at the **shared** dev
Postgres (`config.yaml`, and its own comment says so), and D-2 is precisely the
shape that trips cross-run contamination. Either close #2 before D-2 (run the HEAD
oracle twice, require both green), or state in the direction that a D-2 red will
be re-run before being believed.

Use the `new-direction` skill. Then run them through **unattended**:

```bash
factory pm-sync --app sacrifice --dry-run   # PURE preview; verify, then run for real
factory on                                   # or drive with `factory tick --app sacrifice`
```

**Watch for, and treat each as a FAILURE of this plan:**
- any story reaching a `blocked_*` sink, or `superseded_by_sibling` **given
  `explore: false`** (under `explore: true` it would be normal)
- any story needing an operator to advance
- **any hamster wheel**: repeated identical work with no state change — check
  `factory audit --app sacrifice` for repeated spend on the same persona/story,
  and `factory trace <id>` for a repeating event signature
- any oracle that fails at HEAD on a *correct* implementation (the false block
  this plan exists to remove)
- any gate passing on a story whose implementation is wrong (**false green — stop
  everything and report; this is worse than every other outcome combined**)
- a rising **waiver / `oracle_not_discriminating`** rate (the false-green channel
  identified in B)

**Exit criterion — artifacts, not state names.** For each of the three:
1. a **merge commit on GitHub** (never a local flag);
2. `acceptance-verified` present in `merge_actions.gates_passed_json`;
3. `state/acceptance/sacrifice/<id>/stub_runs.json` **and** `base_runs.json` on
   disk, showing a credited `K` and a corroborated base — **the gate emits no
   events, so these files are the only proof it ran**;
4. zero rows in `factory inbox`; zero operator interventions; spend within cap.

**`deployed` is NOT an exit criterion.** `deploy.enabled: false` on sacrifice, so
it is a state name and every `deploy_actions` row is skipped.

**ABORT TRIGGER.** `gates.acceptance_oracle: true` is live. If A1/A3/A4 regress,
every AC-carrying story blocks and this phase becomes unrunnable. So:
**if two consecutive fresh stories block for an acceptance reason, set
`gates.acceptance_oracle: false`, stop, and diagnose.** Do not push through.

If a story blocks: diagnose, fix the *class* not the instance, record a memory
file, then **re-run from a fresh story** — a resumed story proves the resume path,
not the unattended path. Both matter; do not confuse them.

**What D can and cannot establish.** Three stories, k=1, three different shapes is
**n=1 per shape**. This repo's own MDE is ±38 pp at n=19 (`STATUS.md`); the 95% CI
on 3/3 is roughly [29%, 100%], i.e. 3/3 is consistent with a true per-story
success rate of 30%. So: **3/3 is a necessary condition for benchmarking, not
evidence of a rate.** 0/3 or 1/3 is decisive evidence *against* readiness. If you
want a rate, the 45 held-out pm-validated sacrifice directions (`STATUS.md`) are
the pool — run 10 and pre-register the threshold.

---

## Suggested order — sequential phases, parallel inside each

Everything inside a phase runs concurrently; phases are barriers because each one
needs the previous phase's *observed* result, not its predicted one.

**Phase 0 — look before touching (all parallel, mostly cheap)**
- `haiku`: environment sweep — leaked docker networks/containers, `factory power`,
  `factory mode`, live tree == `origin/main`, local suite baseline timing (C7)
- `haiku`: collect current parked/blocked state, spend rollups, open PRs
- `sonnet`: C2 tech_writer JSON diagnosis — **read `factory trace 177` FIRST.**
  This plan's C1/C2 attribute 177 to a tech_writer parse failure, while memory
  `direction_117_was_oversized_for_one_story` attributes it to contract ambiguity
  at review. Resolve the discrepancy before designing any fix around tech_writer.
- `sonnet`: C6 sweep for other unverifiable config facts
- `opus`: C4 read the oracle's KNOWN OPEN #2–#4 and recommend fix/accept —
  **#2 gates D-2, so this is on the critical path**

**Phase 1 — the decision that dominates everything downstream**
- `opus`: **A4** — make the `explore`/AC-scope call the memory has been waiting
  for, and implement it. Until this lands, every AC-carrying `explore` direction
  carries a ~50% structural block rate that would swamp D's signal.
- `sonnet` (serialise the actual `resume-story` calls — they write the DB): **C3**,
  resume stories 177/178.
- Then: full suite, adversarial `opus` review, PR, CI, merge, deploy.
- **Observe**: run a tick and watch real stories move.

**Phase 2 — the cheap mechanical guard**
- `sonnet`: **A1's cross-check test** — hint-vs-derived-surface consistency in CI.
  No boot, no per-story cost, no new terminal sink. Extends
  `tests/test_sacrifice_acceptance_harness_hint.py`; **do not weaken it**.
- `haiku`: **A2's advisory instrumentation** — record base statuses in `details`.
  Classify nothing. Block on nothing.
- These two are genuinely independent. Everything richer in A1 (a per-story
  derived surface fed to the author) is **deferred** until the cross-check has
  been live and the A1 preconditions — base-sha verification, no re-derive on
  `force`, `_unverifiable` path back — are all implemented.

**Phase 3 — A3, then measure (B)**
- `opus`: **A3** arrange/assert split. **A3 precedes any blocking version of A2**,
  which presupposes the distinction A3 creates.
- `sonnet`: draft D-1/D-2/D-3 concurrently, with blast-radius numbers
  pre-registered and `explore: false` justified in each.
- Then **B**: pre-register arms and metric *including the waiver /
  `oracle_not_discriminating` rate*. Archive artifacts per run — re-running a
  sweep destroys published-number artifacts. `opus` interprets.
  **If the derived surface does not beat the prose control on false-block, OR the
  waiver rate rises, STOP and report.**

**Phase 4 — remaining harness integrity (parallel)**
- `opus`: C1 (shared control flow — re-verify everything keyed off it)
- `sonnet`: C5 detector_watch read-only soak, then decide
- `sonnet`: C2 fix, if Phase 0 identified a real cause

**Phase 5 — the unattended proof (D) — SERIAL, and the point of all of it**
Run the three directions through the real factory and watch. No agent may
"conclude" this phase from a summary; it is closed by the four artifacts listed in
D. Honour the abort trigger.

## Reporting

Report honestly and specifically. State what was fixed with SHAs, what was
deferred and why, and what remains unproven. A summary is a self-report until a
commit backs it. If the chain still cannot run three fresh stories unattended,
**say so plainly** — "not ready to benchmark" is a valid and useful outcome, and
far more valuable than a number nobody can trust.

Refresh `apps/factory/context/modules/*.md` for any subsystem touched: manual
loop-3 PRs bypass the chain's `tech_writer` step, which is the only thing keeping
those docs current.
