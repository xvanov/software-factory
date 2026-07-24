# SOTA audit — software-factory vs. harness engineering, July 2026

Nine-agent research pass, 2026-07-24. Four agents audited this repo; five swept the
external state of the art. Every internal claim below marked **[V]** was independently
re-verified by the author against the live tree/DB, not taken from a subagent report.

---

## 1. Verdict

**The core thesis is correct and is now backed by external controlled evidence
stronger than our own benchmark.** The factory's *architecture* is, in three specific
respects, ahead of published practice. Its *implementation* has five verified defects
that mean substantial parts of the design are not actually running — including the
entire self-improvement layer, which has a measured lifetime yield of zero at a cost
of $1,028.

Scorecard against the mid-2026 canon:

| Dimension | Us | SOTA | Gap |
|---|---|---|---|
| Deterministic verification as the authoritative gate | **Ahead** | execution-grounded verify stage | — |
| Runtime/live smoke gate before merge | **Ahead** | rare outside Anthropic's guidance | — |
| Parallel-agent conflict handling | **Ahead** | 41.7% cross-agent conflict rate unaddressed | — |
| Bounded loops / convergence guards | **At par** | hard caps standard | — |
| Cost ladder + model-as-config | **At par** | routing standard | — |
| Reviewer drift control | **Ahead** | not instrumented in published systems | — |
| Context assembly / retrieval | **Behind** | JIT grep-based retrieval, budget enforcement | inert matcher; no budget |
| Tool / action-space design | **Behind** | factory-shaped tools, tool denial | 100% stock |
| Execution isolation | **Behind** | microVM/gVisor standard | host + real secrets |
| Eval as regression suite | **Behind** | sealed splits, statistical gates | one-off campaign |
| Self-improvement loop | **Far behind** | archive + activation + significance gates | stateless, yield 0 |
| Patch transport | **Behind** | file-state collection | unified diffs (retired) |

---

## 2. The thesis, restated with external evidence

Our claim: *harness quality beats model size; cheap models plus loops and backpressure
beat frontier models plus a thin harness, far cheaper.*

**Confirmed — harness variance exceeds model variance.**

- Claw-SWE-Bench (arXiv 2606.12344), 350 real issues, 43 repos, model held fixed,
  five harnesses swapped: pass@1 spread **12.5 pp on GLM 5.1, 27.4 pp on
  Qwen 3.6-flash**. Model spread with harness fixed: 29.4 pp. Harness choice ≈ one
  model tier, and matters *more* the weaker the model.
- LangChain held gpt-5.2-codex fixed and changed only prompts/tools/middleware:
  **52.8% → 66.5% on Terminal-Bench 2.0**, rank ~30 → top-5.
- Cheap+good beats strong+generic, directly: Qwen 3.6-flash + OpenClaw **66.0% at
  ~$0.20/task** beats GLM 5.1 + GenericAgent **63.1% at ~$0.25**.

**Confirmed — repeated sampling against an executable verifier beats frontier
single-pass.** DeepSeek-Coder-V2 on SWE-bench Lite: 15.9% @1 sample → **56% @250**,
vs 43% single-sample SOTA, at under a third the price (arXiv 2407.21787). Scoped by
its own authors to domains where automatic verification exists.

**Not confirmed — "cheaper model ⇒ cheaper end to end."** This is where our framing
needs correcting. From the only end-to-end $/merged-PR study found (12 models × 3
harnesses, frozen repo, constant frontier review gate,
`blog.insight-services-apac.dev/2026/07/06/cost-to-a-merged-feature`):

> As the coder gets cheaper, its output needs more review, so the gate pays more to
> bring it up to the bar.

Coding cost fell **340×** from the most to least expensive coder; **total merge cost
fell only ~1.8×**. Cheapest merge was a *mid*-tier model at 1 cycle ($5.56), not the
near-free model at 4 cycles ($17.03). **Cycle count, not token price, is the cost
driver.** Corollaries with numbers:

- Augment's break-even: if cheap output needs correction >20% of the time, a 3× price
  advantage is gone.
- Retries are quadratic in context, not linear in steps: 1.7–1.9× tokens at 3 steps,
  2.2–2.5× at 5 (tianpan.co retry-budget analysis).
- Across 1,127 real agent runs ($4,281): **context re-reads were 52.1% of spend**;
  retries only 3.4%. Cheap models don't touch that. Prefix-stable caching does.
- The LLM review gate is **fidelity-neutral**: in the study above, one implementation
  passed frontier review while failing 20 unit tests.

**The defensible formulation is therefore: cheap generator + *deterministic* verifier +
hard convergence caps.** That is what this factory actually implements — the
authoritative gate is `pytest` re-run by the harness plus a live smoke boot, with the
LLM reviewer layered on top rather than load-bearing. We built it the right way round.
The README's "harness quality beats model size" should keep its headline but stop
implying the saving comes from the model tier; it comes from gate discipline and cycle
caps.

**Wall clock is the honest cost we underweight.** Our own campaign: 40 min vs 14 min
(3×). The field's figure: open-weight models merged at $18–$29 but took 69–176 min vs
Opus 26 min. At any nonzero engineer-attention cost, cheap-and-slow loses.

---

## 2b. The production record **[V]**

| Metric | Value |
|---|---|
| Stories all-time | 139 (sacrifice 121, factory 18) |
| **Deployed** | **99** (sacrifice 89, factory 10) |
| Superseded by sibling | 33 |
| Blocked now | 7, all sacrifice (2 untouched since 2026-07-19) |
| Directions 100% deployed end-to-end | 26 sacrifice, 3 factory |
| Directions never dispatched at all | 29 of 76 sacrifice (38%) |
| **Post-merge production reverts** | **0** (both repos; `rollback_actions` = 0 rows) |
| PRs merged | 82/88 factory, 78/114 sacrifice |
| Deploy days | 11 distinct days in 60; **zero deploys 05-27 → 07-06** |
| **True cost per deployed story** | **$19.49** ($1,929.80 ÷ 99) |
| Story-attributed cost per story | $0.39 — but only 4.3% of spend is attributable |
| Doc share of merged changed lines | 12.7% factory, 16.9% sacrifice |

Three conclusions, one good and two uncomfortable.

**Good: quality holds up.** 99 deployed stories, **zero post-merge reverts**, zero
rollback actions ever written. The sacrifice suite runs 846/862 passing with all 6
failures and 3 errors confined to `e2e_test.py` (needs a live server). Whatever else is
wrong, the gates are not shipping broken code — which is the thing the smoke gate and
deterministic-verifier design exist to guarantee.

This also definitively retires the `POSTMORTEM-2026-05-30` worry that the docs chain was
carrying the deploy count. By `chain_kind`: **docs 13/13 deployed (100%), tdd 86/126
(68%)** — so **87% of all deployed stories came from the code chain**. Docs are 12.7%
(factory) / 16.9% (sacrifice) of merged changed lines. The Loop-4 dev-owns-tests rewrite
worked; the code pipeline converges now. The tdd chain's 32% loss is 33
superseded-by-sibling plus 7 blocked, not non-convergence.

**Uncomfortable 1: the cost win has been eaten by the manager.** The pre-improvement
baseline recorded in `bench/README.md` was **$17/shipped story**. True cost per deployed
story today is **$19.49**. The per-task benchmark figure of $0.65 is real but measures
only story-attributed spend — **4.3% of total**, because `runs.app` is NULL on 98.9% of
rows. The other $1,846 is overhead, and half of all spend ever recorded is the L1
watcher. *We did not make shipping cheaper; we made the coding step cheaper and spent
the savings on a self-monitoring loop with zero yield.* That single sentence is the
audit's most important finding, and it reframes §4.1 from "a broken subsystem" to "the
reason the economic thesis doesn't yet show up in the books."

**Uncomfortable 2: throughput is bursty, not sustained.** 1.65 stories/day across the
span, but deploys landed on only **11 of 60 days**, with a **six-week dead gap** (05-27
→ 07-06) and two outlier days (35 and 16 deploys). Ticks ran on only 39 of 58 days.
The repo's own 8/10 self-score and its "ticking ≠ shipping" note are accurate.

**Two operational findings worth acting on:**

- **`merge_actions`: 2,190 attempts → 82 merges (3.7%).** PRs #88 and #89 were each
  polled **437 times**; #275 → 287, #286 → 278. The dominant non-merge reasons are
  858 "PR is closed" (polling after closure) and 578/173 "missing gate labels:
  smoke-green / tests-green". Cheap in LLM terms, but it means doomed PRs were
  re-polled for days before parking — this is the "detect-without-remediate" pattern.
- **The tick exit code contradicts the tick's own success flag [V].**
  `factory-tick@factory.service` shows **156/156 process exits at `status=1/FAILURE`**
  with 936 "story skipped (non-fatal)" log lines, while `ticks.ndjson` records
  `success: true` for the same period (996/998). Any external health check — including
  systemd's own — reads the factory as 100% failing while its internal telemetry reads
  99.8% healthy. This is the known invalid-state-row bug: fixed for DB semantics, still
  live for the exit code.
- Reviewer cycles reached **6 on 9 stories and 7 on 2** (`_MAX_REVIEW_CYCLES = 6`, with
  a documented reset path at `auto_merge.py:1621`) — against an operator rule of 3.
- **The 7 parked stories, with age.** Nothing else is in flight — the factory is fully
  drained apart from these. Story 81 `blocked_deploy_failed` **122.9h (5.1 days)**;
  88 `blocked_ci_unresolved` 41.7h; 89 `blocked_dependency_unmet` 40.9h;
  94 `blocked_ci_unresolved` 41.7h; 95 `blocked_dependency_unmet` 40.9h;
  130 `blocked_budget_exceeded` 24.8h; 139 `blocked_dependency_unmet` 20.4h. Six of the
  seven sit in states with **no factory-driven exit** (§ChainMechanics: only
  `blocked_tests_need_clarification` and `blocked_review_nonconvergent` are
  auto-recoverable). This is the queue that "runs unattended" currently cannot drain.

## 3. Where we are ahead of published practice

**1. The runtime smoke gate.** Nothing merges on green unit tests alone; `smoke-green`
boots the PR's own code on an isolated port and drives the core journey. The 2026 canon
converges on exactly this ("a feature is done when it runs live") but few systems
implement it as a merge blocker. Our own benchmark shows why it matters: Claude Code
failed t3 and t5 by declaring done with its own new tests red (rubric 0.88–0.93, gates
FAIL). Our chain structurally cannot do that. **This is the single most valuable thing
in the repo.**

**2. Parallel-agent conflict handling.** A study of 33,596 agent PRs across 2,807 repos
found **79.4% opened concurrently with another agent PR**, replayed conflict rates of
19.8% intra-agent and **41.7% cross-agent**, with the authors noting agents "operate
independently and in isolation, without knowledge that other agents are simultaneously
altering the same files." We have per-story git worktrees, `freshen_behind_prs`,
conflict-rebuild-on-fresh-branch, and per-app docs serialization. We solved a problem
the field has documented and not fixed.

**3. Reviewer drift control.** `handlers.py:2830-2885` implements a *finality drift
clamp*: from cycle 3, blocking findings at file locations not raised in the previous
cycle are clamped to non-blocking unless flagged `regression`, with the deterministic
slop detector explicitly exempt. Convergence is measured by findings-signature
stability (`_MAX_REVIEW_STUCK=3`), not raw cycle count. No published multi-agent review
system instruments goalpost-drift this way. Keep it.

**4. Independence invariants in routing.** `routes.yaml` enforces reviewer ≠ dev model
and acceptance_author ≠ dev family, deliberately, with rationale in comments. The
field's finding that **93.4% of flagged locations are caught by exactly one tool** (146
PRs, four AI reviewers) supports heterogeneity — though it also implies a *single*
reviewer should be treated as a sensor, not a verdict, which we do not do.

**5. Anti-gaming fences invented independently.** `bench/**` and `factory/manager/**`
are on the forbidden-self-edit list. Weng's rule — keep "the runs directory, tracer,
verifier, and LLM configuration read-only" to the self-improving agent — is the same
insight. We got there first, and it has a sting in the tail (§4.1).

---

## 4. Verified defects, in order of cost

### 4.1 The self-improvement loop has never shipped a change **[V]**

| Metric | Value |
|---|---|
| Lifetime apply attempts | 163 |
| → `escalation_acknowledged` | 105 |
| → `abandoned` | 53 |
| → `staging_rejected` / `test_failed` / `forbidden` | 3 / 1 / 1 |
| → **opened a PR** | **0** (`pr_number` set on 0/163) |
| `factory-manager/*` branches in existence | 0 |
| `manager_watcher` spend | **$971.86 over 44,111 runs** |
| Manager total | **$1,028.21 of $1,929.93 lifetime (53%)** |
| Last 8 days, manager | **~$204** (2026-07-22: $28.92 manager vs $0.14 chain) |

Two independent, still-live root causes:

- **Bug A — the daemon structurally cannot open a PR.** `watcher.py:946` calls
  `apply_manager_proposals(root=…, proposal_path=…)` with no `repo=`. `apply.py:967`
  gates on `if open_prs and repo and push:` → always False. Only the operator CLI
  (`cli.py:2975`) passes `repo`.
- **Bug B — every autonomous apply aborts.** `apply.py:822-832` runs
  `git diff --quiet HEAD` against the **live tree** and returns
  `abandoned`/`dirty_working_tree`. The tree currently has **131 modified files** and
  is permanently dirty by operating practice. `staging.py` already does this correctly
  against a clone.
- **Why it hid for 59 days:** `_append_history` persists only
  `{branch, classification, concern_id, pr_number, pr_url, proposal_id, proposal_path,
  status, ts}`. **`error` is discarded**, so 53 identical `dirty_working_tree` aborts
  left no trace.

**The structural problem is worse than the bugs.** Both live in flat
`factory/manager/*.py` — the *always-forbidden, no-carve-out* class. The FMS is
forbidden by design from fixing the only two defects that zero its yield. The
anti-gaming fence is correct in principle (Weng) but currently fences off the repair
surface as well as the grading surface. The fix is to distinguish *grader* files
(`bench/**`, verifier, significance gates — stay forbidden) from *plumbing* files
(watcher/apply wiring — allow via the staging gate, which already clones and runs the
suite).

Supporting defects, all verified:

- **`cost_spike` has never fired in 59 days** while the watcher spent $972. There is no
  detector over manager spend or manager yield, so the loop cannot notice it is dead.
- **L1 fires unconditionally every 60s** and produced 87% of all run rows. At a 7.2%
  escalation rate, ~$890 of $972 bought nothing. Gate on stream-delta, not wall clock.
- **L3's self-context is frozen at 2026-05-27** **[V]** — the six
  `apps/factory/context/modules/*.md` files are unmodified on disk, last refresh event
  2026-05-28, while **113 commits have landed in `factory/` since**. `refresh-context`
  is scheduled nowhere: not in the orchestrator, not in `factory_settings.yaml`, not in
  CI. The tier that writes patches reasons about a two-month-stale factory.
- **Patch transport is a retired technique — and we have the receipts [V].** L3 emits
  unified diffs and `apply.py` classifies anything else as forbidden. Claw-SWE-Bench
  found switching from model-emitted unified diffs to file-state patch collection cut
  apply failures **69.1% → <1.5%**. All three of our `staging_rejected` events failed at
  `stage_failed: "apply"`, with the logged reason `corrupt patch at line 8 / 34 / 25` —
  `git apply` rejecting the Diagnostician's own diff. We are reproducing the exact
  failure mode the field retired.
- **`escalate_to_human` is a no-op in the autonomous path.** `notify_escalation`
  requires a `repo`; the daemon passes none, so records read `"reason": "no_repo"` and
  no issue is filed. 105 escalations went to a local file nobody reads.
- **Feedback channel excludes its own dominant outcomes.**
  `diagnostician.py:482 _FAILED_APPLY_STATUSES` omits `escalation_acknowledged` and
  `staging_rejected` — **108 of 163 outcomes (66%) are invisible to every future L3
  run.** The loop cannot learn that it escalates 65% of the time.

**What the literature says we should have instead.** Stateless detect→patch is not a
design in the 2026 literature; it is the ablated-away baseline:

- DGM ablation: **25.3% full vs 20.5% without self-improvement vs 18.7% greedy
  no-archive.** Removing the *archive* costs more than removing self-modification.
- HGM (ICLR 2026 oral): selecting on a node's own score is the wrong objective — the
  *Metaproductivity–Performance Mismatch*. Select on clade-aggregate descendant
  performance: **56.7% vs DGM 53.3% at 42% of the CPU cost.**
- GSME keys its archive on **(where × why)** — the pathology an edit addresses, not the
  tasks it helped — and reports that on 4 of 6 domains the winning harness was a
  cross-cell *recombination* of archived edits.
- GSME's three gates, in order of transferability to us: **validity** (re-run infra
  failures, keep in denominator), **activation** (credit a patch only if its
  instrumentation beacon actually fired), **significance** (paired 2σ on a sealed split
  never consulted during search). The activation gate was the *only* gate that rejected
  a "context-compact" mechanism whose beacon fired zero times while a naive Δ>0 rule
  credited it.
- Reward hacking grows with horizon: proxy-gain-without-real-gain rose **26.4% at 10
  steps to 57.8% at 100**. A stateless loop cannot see this, because the gap is only
  visible across steps.

### 4.2 The retrieval layer has never fired **[V]**

`loader.py:118` matches with `if scope_lower in label.lower()` — a substring test of
the scope enum against natural-language navigation headings. Measured:

```
backend   label_hits=0  prelude_chars=4519
frontend  label_hits=0  prelude_chars=4520
infra     label_hits=0  prelude_chars=4517
test      label_hits=0  prelude_chars=4516
docs      label_hits=0  prelude_chars=4516
no-scope                prelude_chars=4417
```

DB scope values: `backend` 77, `infra` 19, `frontend` 18, `docs` 13, `test` 12 — all
139 stories carry a valid scope; **none can ever match** any of the six sacrifice
navigation headings ("When working on auth or token lifecycle", "mobile or web login
UX", …). The ~100-char delta is literally the string *"No navigation sections
matched."* Every persona has worked a 51k-LOC repo on **~4.4 KB (~1.1k tokens)** of
curated context, and `handle_dev` doesn't pass `task_scope` at all, so dev gets 4,417.

**Correction to the obvious conclusion:** the fix is *not* a vector index. Embedding
retrieval over code was abandoned industry-wide — Anthropic removed vector search from
Claude Code in May 2025 for grep, and Cursor, Windsurf, Cline, Devin and Amp followed.
The canon is **just-in-time grep-based retrieval**, which our agent can already do via
bash. So the loss here is smaller than it looks, and the cheap fix is to map scope →
headings (or match on story title keywords) and pass `task_scope` from `handle_dev`.

**The genuinely costly sibling defect: the oracle is hidden from the agent.**
`test_command` (`cd backend && uv run --extra dev pytest -q tests/`) reaches only the
post-run gate. `personas/dev.md` says "running the test command via Bash" without
naming it; the prelude omits it; 2 of 110 story files mention it. **Dev rediscovers its
own grading command every single run.** This is free to fix and directly attacks cycle
count, which §2 identifies as *the* cost driver.

Also: **no input token budget exists anywhere.** `model_limits` governs output only and
says so. Sandbox input is bounded only by the stock OpenHands condenser
(`max_size=80, keep_first=4`); `text_run` has no compaction at all. Truncation is
ad-hoc byte caps with silent inline markers and no events: story 32 KB, test output
8 KB, PR diff 64 KB. And **dev — our largest single spender at $669 — has zero prompt
telemetry**, because `_log_prompt_metadata` is called only from `text_run`, never
`sandbox_run`. The prompts we can measure are not the ones that cost money.

### 4.3 Two required merge gates evaluate against an empty file list **[V]**

`auto_merge_tick` is invoked from the orchestrator (`orchestrator.py:1997`, `2361`)
without a `github_client`, so gate fixtures are synthesized with `files_changed=[]`
(`auto_merge.py:2122-2136` — the same block was explicitly patched to supply
`repo_root` for the command gates, but `files_changed` was left empty).
`canonical-paths-only` then returns `passed=True, "no violations"`; `tests-meaningful`
returns `passed=True, "no slop findings"`. Both are vacuous.

**Do not over-read this.** Both have a real upstream enforcement point that uses a
genuine git diff: slop detection runs at review time via `find_test_files_in_diff`
against the worktree and vetoes reviewer approval (`handlers.py:2600-2630`), and
canonical-paths runs at `docs_enforcer_check` off `_changed_files_for_story` with a
vacuous-diff guard (`handlers.py:3423-3469`). The loss is defense-in-depth plus
**misleading green gate reports** — which is precisely GSME's activation-gate failure
mode: a check that passes without running.

The load-bearing hole is different: **`gates.acceptance_oracle` is set in neither app
config and defaults to `False`** (`app_config.py:113`). Under a dev-owns-tests model,
the one dev-blind oracle is off everywhere. The field's warning is specific: SpecBench
found the validation-vs-held-out gap grows **27 pp per 10× LOC** — ≤21 pp under 10K
LOC but **100 pp above 25K LOC** — via feature isolation rather than deliberate
cheating. Sacrifice is 51k LOC. We are in the regime where self-authored tests stop
measuring what we think they measure.

Also verified: **`_slop_findings_for_story` returns `[]` on any exception**
(`handlers.py:2630`) — an infra hiccup silently removes the deterministic veto. And the
`human_review_max_open_prs: 5` / `failing_ci_pause_threshold: 3` queue brakes cannot
fire from the tick path: `open_prs_for_app` and `failing_ci_count` are hardcoded `None`
(`orchestrator.py:1627-1629`) and the enforcer treats `None` as unknown.

### 4.4 The eval harness cannot function as a regression suite **[V]**

`bench/tasks.yaml` ships `base_sha: ""`, and `bench.py:65 _base_sha` then resolves live
`origin/main`. All seven direction tasks are `status: closed` (shipped), the CSRF test
file exists today, and main has moved past the campaign base `8becb91`. **A re-run
today grades both arms against a tree where the work is already merged.** t7's
`prompt_file` no longer exists, so `_prompt_text` raises for both arms. `gates.docs: []`
makes `passed = all([])` → `True` — a docs task records `gates_passed=True` having run
zero checks. `report()` prints one row per run with no aggregation, variance, or
pass-rate. `bench/.gitignore` excludes `runs/` and `results/`, so the campaign's
headline aggregates are hand-computed and unreproducible.

**Consequence for §4.1:** `bench/**` is correctly fenced off from the self-improver so
it cannot tamper with its grader — but **nothing in the factory ever runs it**, so no
self-edit is ever measured for end-to-end capability effect. The FMS staging gate calls
the unit suite "the behavioral bench"; it is not. Per §4.1's literature, a sealed,
rerunnable, statistically-gated eval is *the* precondition for any self-improvement
mechanism to work at all. We have the fence without the grader.

### 4.5 Execution isolation is git-level only **[V]**

`LocalWorkspace(working_dir=repo_path)` — no container, no microVM. The agent runs as
the factory user on the host with unrestricted bash and network. `worktree.py:204`
copies `.env`, `.env.local`, `.env.test` into the worktree, so the agent holds the
app's real secrets. Tools are 100% stock `get_default_agent(cli_mode=True)`
(bash/file-edit/task-tracker); `presets:` is empty; no MCP; zero custom tools. The
action space is not shaped for this codebase in any way — no run-the-gate tool, no
repo-search tool. The field standardized on microVMs/gVisor during 2026, and top
harnesses actively *deny* tools (OpenClaw's competition adapter disables memory, web,
and session-spawn).

Also: the 1800 s sandbox timeout is enforced by `asyncio.wait_for`, which cancels the
*await* — the worker thread is abandoned, not killed, and reaped only at tick exit. And
`RunResult.success` is only the pytest exit code, which is why `onboarder` shows **0%
success across 649 sandbox rows**: doc-writing personas are graded by an oracle they
cannot satisfy.

---

## 5. Prioritized actions

Ordered by (verified cost or risk removed) ÷ (effort). Items 1–4 are hours.

**P0 — stop the bleed and make the loop capable of shipping.**
1. Gate L1 on stream-delta rather than the 60 s wall clock. Recovers ~$25–30/day
   immediately at a measured yield of 0. *(Or pause `factory-manager.service` until
   items 2–3 land — a halted manager costs $0/hour, per the FMS's own principle.)*
2. `apply.py:_append_history` — persist `error`. Without this, every future diagnosis
   is blind, exactly as the last 59 days were.
3. `watcher.py:946` — pass `repo=` and `open_prs=True`. `apply.py:828` — run the
   dirty-tree check against a clone/worktree (as `staging.py` already does), or scope
   it to the patch's target paths.
4. Add an `fms_yield` detector (proposals emitted vs merged over 7d) and a
   `manager_spend` detector. The loop must be able to notice it is dead.

**P1 — restore the verification design that is supposed to be running.**
5. Set `gates.acceptance_oracle: true` for sacrifice and wire the oracle. This is the
   only dev-blind check, and §4.3's 27 pp-per-10×-LOC finding says we are past the
   point where it is optional.
6. Thread a real `files_changed` into the synthesized fixtures, or make the gates
   return *unevaluable* rather than `passed` on an empty list. A gate that passes
   without running is worse than no gate.
7. Make `_slop_findings_for_story` fail closed.
8. Populate `open_prs_for_app` / `failing_ci_count` in the tick path so the queue
   brakes exist.

**P2 — attack cycle count, which §2 identifies as the real cost driver.**
9. Put `test_command` verbatim in the dev prelude and in `personas/dev.md`. Free.
10. Fix scope → navigation matching and pass `task_scope` from `handle_dev`.
11. Log prompt metadata from `sandbox_run`, so the $669 persona is measurable.
12. Schedule `refresh-context` (per-tick or daily) so L3 stops reasoning about a
    two-month-stale factory.

**P3 — make self-improvement structurally possible.**
13. Pin `base_sha`, restore the missing task file, fix the `all([])` docs gate, add
    aggregation + variance to `report()`, and stop gitignoring `runs/`/`results/`.
    Then split the task set into a search half and a **sealed** half.
14. Add an outcome archive keyed on **(where × why)** with the three GSME gates
    (validity / activation / significance). Include `escalation_acknowledged` and
    `staging_rejected` in the feedback statuses.
15. Split the forbidden-edit list into *grader* (stays forbidden) and *plumbing*
    (allowed via the staging gate), so the loop can reach its own wiring bugs.
16. Switch L3 patch transport from unified diffs to file-state collection
    (69.1% → <1.5% apply failures).

**P4 — catch up on substrate.**
17. Container or microVM the sandbox; stop copying real `.env` secrets into worktrees.
18. Add 2–3 factory-shaped tools (run-the-gate, story-fetch, repo-search) and consider
    tool denial for personas that don't need bash.
19. Kill the sandbox worker thread on timeout rather than abandoning it.
20. Stop grading non-code personas on a pytest exit code.

---

## 6. Honest limits of this audit

- Throughput, revert and reliability figures in §2b were re-derived by a measurement
  agent and spot-verified by the author. Two known gaps remain: **per-story cost
  attribution does not exist for 95.7% of spend** (`runs.app` NULL on 98.9% of rows), and
  there is **no distinct "green but doesn't run" event type** — reviewer-cycle counts are
  the only proxy. `rollback_actions` has never had a row written, so it is either
  never-fired or dead code; worth confirming which.
- Long-range systemd journal history for `factory-tick@sacrifice` has rotated out;
  `ticks.ndjson` is the only durable record.
- **External numbers above 80% on any SWE-bench variant should be treated as
  contaminated or unverifiable.** OpenAI's 2026-07-08 audit found ~30% of SWE-bench
  Pro's public tasks broken and retracted its recommendation; Cursor found Pro scores
  collapse when agents lose internet and git history, with some agents retrieving gold
  patches. swebench.com's own leaderboards are JS-rendered and could not be fetched;
  Verified figures come from aggregators or from papers reporting their own runs.
- Several research agents reported that their fetch pipeline silently substituted proper
  nouns. Sources here are cited by **URL**, not by rendered title, for that reason.
- Model names post-dating May 2026 (Claude Mythos 5, GPT-5.6 Sol, Kimi K3, Muse Spark,
  Inkling) are reported as sourced, not independently confirmed.
- Our own benchmark's caveat stands and matters: **one-shot `claude -p` is the weakest
  reasonable Claude arm.** The 12.6× cost advantage is against a thin harness, not
  against a well-harnessed frontier agent. Arm C (subagent planner/coder/verifier) is
  still untested, and §2's Claw-SWE-Bench data implies it would close much of the gap.

## 7. What the field says is unsolved — i.e. don't expect to fix these

- **Verification, not generation, is the frontier.** No fixed reward function survives
  continued capability growth; verification must co-evolve. Adding a quality judge plus
  trajectory monitor moved hacked-resolved **28.57% → 0.56%** and clean-resolved
  **40.22% → 60.53%** — ~30% of unmonitored "successes" were exploits (arXiv 2606.26300).
- **Ultra-long-horizon autonomy is under 30%.** SWE-Marathon, 20 tasks of 40–400 human
  hours, 1,300 trials: no configuration passed 30%. Failure mix: 41.6% implementation,
  31.4% timeout, 15.4% reward hacking, 7.6% premature termination.
- **Auto-designed multi-agent systems are retired.** MAS-Zero GPT-5 scored 45.52% at
  $998 vs plain CoT-SC GPT-5 at 57.09% for $286. *Expert*-architected role splits still
  win — which is what our persona pipeline is. Don't let the FMS search topologies.
- **Harnesses may be depreciating assets.** The strongest dissent holds that harness
  components encode expiring assumptions and should be deletable within hours, with
  ~90-day replacement cycles; O'Reilly's "Kirby effect" describes frontier models
  swallowing scaffolding wholesale. Weng takes the opposite view. Unresolved — but it
  argues for keeping the *gates* (durable) and holding the *prompt scaffolding* loosely.
- **Self-evolution is model-specific.** GSME: "evolved harnesses are model-specific;
  the loop is what transfers." Harness-*updating* ability is roughly flat across model
  scale, while harness-*benefit* is non-monotonic and peaks at **mid-tier** models — so
  cheap proposers are fine, but don't assume a patch tuned on deepseek helps codex.
