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

1. No acceptance oracle is authored from hand-maintained API prose.
2. A malformed oracle is detected at **authoring time**, not at merge time.
3. The information-budget ablation has been run and its numbers are committed.
4. Every open harness defect below is either fixed or explicitly deferred with a
   written reason.
5. **Three fresh stories drive end-to-end, unattended, to `deployed`** with no
   operator intervention, no block, and no repeated-work loop.
6. `factory audit-chain` reports no tampering; `factory inbox` is empty of
   needs-human rows; `uv run pytest -q` exits 0; live tree == `origin/main`.

**None of 1–6 may be claimed from a green test run alone.** Name the commit SHA
or merged PR for every fix (memory: `session_fix_claims_need_git_verification` —
a prior session reported two fixes that were never committed).

---

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

# Workstream A — oracle source of authority

**The defect.** The acceptance author is dev-blind (correct). But it needs route
paths, request schemas and status codes it structurally cannot obtain, so those
come from **hand-written prose** (`gates.acceptance_harness_hint`). The author
cannot detect drift — being unable to check is the point — so a stale fact is
laundered into an authoritative oracle that blocks a correct implementation.
Three instances, three patches at the fact, zero at the mechanism.

**The principle is already right**: `acceptance.build_spec_prompt`'s docstring
already argues the hint is not an independence leak. Total blindness was already
rejected (it produced `No module named 'app'` on 2026-08-05). **Only the delivery
mechanism is broken.** Do not re-litigate the freeze; it is well-supported
(ImpossibleBench arXiv:2510.20270 — but note its mitigation is denying the *dev*
test access, never denying the *author* the API surface).

### A1. Derive the invocation surface at the story's BASE commit

Replace the API-fact portion of the harness hint with a generated artifact.

- **Source**: the app at the story's **base commit** (`origin/main` at authoring
  time). FastAPI exposes `app.openapi()`; `sacrifice` is a plain
  `FastAPI(title="Sacrifice API", ...)`, so both the import path and the
  boot-then-`GET /openapi.json` path work.
- **Content**: routes, methods, required request fields, response status
  vocabulary. Prune descriptions/examples to keep the prompt small.
- **Storage**: beside the oracle, e.g.
  `state/acceptance/<app>/<story>/api_surface.json`, keyed and cached on the base
  sha, frozen with the oracle and hashed like it.
- **Prompt**: `build_spec_prompt` gains an `api_surface` section replacing the
  route/schema half of `harness_hint`.
- **Keep as prose**: environment facts only — shared Postgres with no per-run
  reset, namespace identifiers with `$ACCEPTANCE_RUN_ID`. Those are not API facts
  and do not drift.

**BASE, never HEAD — this is the load-bearing decision.** It does three jobs at
once:
1. at base the story's own endpoint does not exist, so the exclusion falls out of
   the revision choice instead of needing a policy;
2. the artifact is frozen per-story, so it cannot drift into
   *implementation-derived* authority (arXiv:2607.05031's explicit warning);
3. it is generated from a commit already on `main`, outside the dev worktree, so
   the dev cannot edit it — which answers the strongest objection, that every
   information channel is also a leak channel.

**Fail closed.** If the surface cannot be derived, the gate BLOCKS with a named
reason. It must never silently fall back to letting the author guess — that is
today's behaviour and it is the bug.

**Verify A1 by:** authoring an oracle for a story whose criterion needs a
prerequisite `POST`, and confirming the emitted oracle sends the *real* required
fields with no human having typed them anywhere.

### A2. Require the base run to fail for the RIGHT REASON

We have the vacuity control (the oracle must fail against a gutted
implementation). Its dual is missing. `_base_run` in
`factory/chain/gates/acceptance_verified.py` already checks out the merge base
into a worktree and boots the app — the infrastructure exists.

Classify the base failure per criterion:

| Base response | Meaning | Action |
|---|---|---|
| `404` / `501` | feature genuinely absent | **valid red** — proceed |
| `400` / `422` | request malformed | **the ORACLE is broken** — block, re-author |
| `401` / `403` on a setup call | oracle misusing auth | **the ORACLE is broken** |
| `5xx` | app not really up | `unknown` — existing corroboration path (PR #256) |

**This is the highest-value item in the plan and the cheapest.** It would have
caught all three historical incidents *at authoring time, before the dev
started*, instead of at merge time after full spend. Ship it even if A1 slips.

**Verify A2 by:** deliberately planting a malformed oracle (omit a required
field) and confirming the run is classified as oracle-broken, not feature-absent.

### A3. Separate arrange from assert

Setup ("create a goal so the count can increment") is not a behavioural judgment
and carries no independence requirement. Today a `422` on setup is reported as a
verdict on the story — a category error, and exactly what blocked story 179.

Minimum: classify and report setup failures distinctly from assertion failures so
they can never be read as "the feature is wrong". Better: let setup use the app's
own fixtures/factories rather than oracle-authored HTTP bodies. This is inference,
not a cited finding, but it is the split arXiv:2504.07244 found *necessary* in
industry (scenario stage 95% helpful from the story alone; executable stage
required the page HTML, semantic relevance 60% → 92%).

---

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

**This is the acceptance test for the whole plan, and it cannot be shortcut.**

Write **three fresh directions** against `sacrifice`, deliberately spanning the
shapes that have broken before:

| # | Shape | Exercises |
|---|---|---|
| D-1 | a new read endpoint, no setup state | the simple path end-to-end |
| D-2 | a criterion needing **prerequisite state** (create an entity, then observe) | **A1 + A3** — the exact shape that blocked 179 |
| D-3 | a change to an **existing** endpoint's behaviour | base-surface handling when the route already exists |

Use the `new-direction` skill. Then run them through **unattended**:

```bash
factory pm-sync --app sacrifice --dry-run   # PURE preview; verify, then run for real
factory on                                   # or drive with `factory tick --app sacrifice`
```

**Watch for, and treat each as a FAILURE of this plan:**
- any story reaching a `blocked_*` or `superseded_by_sibling` sink
- any story needing an operator to advance
- **any hamster wheel**: repeated identical work with no state change — check
  `factory audit --app sacrifice` for repeated spend on the same persona/story,
  and `factory trace <id>` for a repeating event signature
- any oracle that fails at HEAD on a *correct* implementation (the false block
  this plan exists to remove)
- any gate passing on a story whose implementation is wrong (**false green — stop
  everything and report; this is worse than every other outcome combined**)

**Exit criterion:** all three reach `deployed`, merged on GitHub (verify the merge
commit — never a local flag), with zero operator interventions, and the total
per-story spend within cap.

If a story blocks: diagnose, fix the *class* not the instance, record a memory
file, then **re-run from a fresh story** — a resumed story proves the resume path,
not the unattended path. Both matter; do not confuse them.

---

## Suggested order

1. **A2** — cheapest, highest value, catches the class at authoring time.
2. **C3, C7** — clear the decks so later signal is clean.
3. **A1** — the real fix. **A3** alongside it.
4. **B** — measure. If A1 does not beat the prose control, stop and report.
5. **C1, C2, C4, C5, C6** — remaining harness integrity.
6. **D** — the unattended proof. Last, because everything else is a precondition.

## Reporting

Report honestly and specifically. State what was fixed with SHAs, what was
deferred and why, and what remains unproven. A summary is a self-report until a
commit backs it. If the chain still cannot run three fresh stories unattended,
**say so plainly** — "not ready to benchmark" is a valid and useful outcome, and
far more valuable than a number nobody can trust.

Refresh `apps/factory/context/modules/*.md` for any subsystem touched: manual
loop-3 PRs bypass the chain's `tech_writer` step, which is the only thing keeping
those docs current.
