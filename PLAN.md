# PLAN.md — reordered around the measured result

**Rewritten 2026-08-04, after the five-arm benchmark.** The chain shows no
measurable lift over a single agent on the same model. Every phase below is
ordered by the evidence for it, cheapest first, and the old ordering
(measurement → bigger benchmark → structural wins) is gone: we already have the
measurement, and the next dollar does not belong to a bigger version of it.

Read order for a fresh agent: `CLAUDE.md` (short, authoritative) → §1 here (the
baseline, do not re-derive it) → §2 (the research premises the phases follow) →
§3 (what is NOT broken) → Phase A. Phases A–E are ordered; do not start B before
A ships, and the reason is in Phase B's warning.

---

## 0. Environment and guardrails (read before touching anything)

```bash
uv sync --all-extras          # dev extras are OPTIONAL; bare `uv sync` has no pytest
uv run pytest -q              # 2,368 tests, ~5 min
uv run ruff check . && uv run mypy factory
git fetch origin && git status -sb    # live tree MUST equal origin/main
```

`ModuleNotFoundError` for `frontmatter` / `sqlmodel` / `pytest` means the env,
not the code — re-sync before debugging.

**Hard guardrails (from `CLAUDE.md`, non-negotiable):**

- **Gate on the real artifact.** Never a recorded flag, an `--auto` *enable*, a
  dry-run's intent, or a green test run without a commit. `proxy ≠ real` is the
  single most common bug class in this repo.
- **The live tree must equal `origin/main`.** It has silently run ~60 commits
  behind before.
- **Never `git add -A`** here (`state/**` is runtime churn). Deploy surgically
  with `scripts/deploy-factory-from-main.sh` (`--dry-run` first).
- **`factory/manager/**` and `bench/**` are forbidden to self-edit** — operator
  PR only (DGM anti-gaming). Enforced in code at
  `factory/manager/apply.py:67-71`. Steps below that touch those trees are
  flagged **[OPERATOR-PR-ONLY]**.
- **Chain code is picked up next tick; manager code needs a service restart**
  (`systemctl --user restart factory-manager.service`).
- Daily spend cap **$300** (`factory_settings.yaml`); notify the operator at
  $50 / $75 / $100.
- `factory resume` / `factory pause` are operator decisions. Never automate.
- Nothing loops more than 3 times, and an early-escalation guard stays strictly
  below the hard cap. Current: `_MAX_DEV_RETRIES = 3`
  (`factory/chain/handlers.py:1244`), `_MAX_REVIEW_CYCLES = 3` (`:1305`), inner
  guards `_MAX_DEV_SAME_SIGNATURE = 2` (`:1259`) and `_MAX_REVIEW_STUCK = 2`
  (`:1304`).

---

## 1. The measured baseline — published, do not re-derive

Suite: SWE-rebench (Nebius), pinned manifest `923aef05add32124`, 19
working-oracle instances, **k = 1**, one sweep, tables pre-registered in
`bench/swebench/PRE-REGISTRATION-1.6.md` before the data existed.

> **Provenance, read before quoting a number.** Two `report` runs exist for this
> sweep and they disagree on one arm. The run committed to `origin/main` is
> `results-archive/2026-08-04T04-18-05.349995Z/` and reports `openhands`
> **7/16 = 44%**, `$15.37`, McNemar p=0.625 — three rows lost to Azure 429s. A
> later run, `results-archive/2026-08-04T23-19-24.998844Z/`, re-ran those three
> rows as `attempt: 2` and reports `openhands` **10/19 = 53%**, `$18.20`,
> p=0.375. **That later archive exists in the live tree and is NOT committed to
> `origin/main`** — commit it (operator bench PR) before 53% is quoted outside
> this repo, and resolve the protocol question in `1.6 G` first: the report's own
> "Discarded runs" section calls `attempt > 1` "a protocol violation, not a data
> point" while the headline counts three such rows.
>
> **The conclusion is the same under either report**, which is why this plan
> uses the later one. Both put the chain below one agent on the same model, both
> at p > 0.3, and the cost ratio moves further against the chain in the later
> one.

| arm | harness × model(s) the ledger says ran | resolved / valid | rate | 95% CI | $ | $ / resolved |
|---|---|---:|---:|---|---:|---:|
| claude-5 | Claude Code CLI × `claude-opus-5` | 15/19 | 79% | [54%, 94%] | 34.36 † | 2.29 † |
| claude-4.8 | the SAME CLI × `claude-opus-4-8` | 14/19 | 74% | [49%, 91%] | 23.56 † | 1.68 † |
| **openhands** | **one OpenHands agent, no chain × `azure/deepseek-v4-pro`** | **10/19** | **53%** | [29%, 76%] | 18.20 | **1.82** |
| **factory** | **the chain on OpenHands × deepseek-v4-pro (33 calls) + gpt-5.3-codex (6) + gpt-5.4 (31)** | **7/19** | **37%** | [16%, 62%] | 35.94 | **5.13** |
| bare | hand-rolled text loop, no tool calls × deepseek-v4-pro (727 calls) | 1/18 | 6% | [0%, 27%] | 7.94 | 7.94 |

† CLI-reported against a subscription; the Azure rows are price-table estimates
over measured tokens. Different accounting bases — never summed, and the
cross-family `$ / resolved` is indicative only. **`factory` vs `openhands` is one
basis and exact.**

Paired McNemar exact, over instances where both arms have an audited-valid row:

| comparison | isolates | paired n | only-A / only-B | p |
|---|---|---:|---:|---:|
| **factory vs openhands** | **the chain** | 19 | 1 / 4 | **0.375** |
| **bare vs openhands** | **the tooling** | 18 | 0 / 9 | **0.004** |
| bare vs factory | chain + tooling, entangled | 18 | 1 / 7 | 0.070 |
| claude-5 vs factory | nothing attributable — reference only | 19 | 8 / 0 | 0.008 |
| claude-4.8 vs factory | nothing attributable — reference only | 19 | 8 / 1 | 0.039 |
| **claude-4.8 vs claude-5** | **contamination** (same harness, older cutoff) | 19 | 1 / 2 | **1.000** |

Pair order is `results.md`'s, not rearranged: **A is the arm named first**, so
`bare vs openhands` at 0 / 9 means bare resolved nothing openhands missed and
openhands resolved nine bare missed. Never reorder a pair's name without
swapping its two counts — the old `STATUS.md` needed a footnote for exactly
that.

What this establishes, in the pre-registration's own pre-committed words: **our
lift comes from using a competent agent loop, not from the chain.**

1. **No measurable chain lift.** 37% vs 53% on identical weights, prompt and
   tools, p=0.375. At MDE ≈ ±38 pp this is **"no measurable lift", not "the
   chain hurts"** — nothing here measured harm, and no doc may imply it did.
2. **The lift is TOOLING, not orchestration.** `openhands` 53% vs `bare` 6%,
   p=0.004 — the only significant result among the three DeepSeek arms. The
   retracted "+58 pp scaffold lift" was measuring having an editor and a
   tool-calling API versus not having one.
3. **Cost moves the wrong way.** $5.13 per resolved instance vs $1.82 — **2.8×
   for no measurable gain** — plus 1.8× the fresh input tokens (14.3 M vs 7.8 M)
   and 2.6× the median wall clock (995 s vs 385 s).
4. **The chain's own verdict is barely better than a coin flip.** Chain-verdict
   precision **6/15 = 40%** [16%, 68%], recall 6/7 = 86% [42%, 100%].
5. **One row went green on a zero-byte production patch.**
   `harumiweb__exstruct-113 / factory`: the chain said green, the reviewer
   approved, and the graded patch was empty —
   `prediction_sha256: e3b0c442…7852b855` (the sha256 of the empty string) with
   `stripped_test_paths: ["tests/cli/test_cli_lazy_imports.py"]` in
   `results-archive/2026-08-04T04-18-05.349995Z/harumiweb__exstruct-113/factory/audit.json`.
   The dev's entire diff was one test file. This single row is the plan's
   cheapest, hardest evidence for Phase A.
6. **The review loop is no longer inert, and it does not help.** Reviewer cycles
   `0×7, 1×9, 2×2, 3×1` across the 19 factory rows, versus 0 on every row in the
   n=6 sweeps. It engages; the resolve rate does not move.
7. **Claude Code is ~2× the factory** (79% vs 37%, p=0.008) but varies harness
   **and** model at once. Reference point, never a scaffold deficit — that
   caveat travels with the number. The factory's 7 passes are a **strict subset**
   of `claude-opus-5`'s 15 (only-B = 0). Against `claude-opus-4-8` it wins
   exactly one instance, `hkuds__openharness-217`.
8. **The contamination probe came back CLEAN.** `claude-opus-4-8` (published
   cutoff Jan 2026) 74% vs `claude-opus-5` (May 2026) 79%, same harness,
   p=1.000, on a manifest where 19/19 instances predate opus-5's cutoff.
   Memorization is not carrying Claude's score. The DeepSeek arms still carry the
   confound: `deepseek-v4-pro` publishes no cutoff and 15 of 19 instances sit
   inside its release-date bound.
9. **Integrity held.** One genuine violation, published invalid and excluded:
   `bare` on `hiero-ledger__hiero-sdk-python-1914_interface` ran
   `curl -s https://raw.githubusercontent.com/…/account_info.py`, the upstream
   source of the exact file under test. Zero path-based oracle probes anywhere.

---

## 2. The research premises this plan follows

Four external research reports, condensed. Each phase names the premises it
rests on. Citations live in `SOTA-RESEARCH-2026-07.md`.

**P1 — Role decomposition has never won at single-issue patching, and that is
not a bug in our implementation.** No entry in the SWE-bench Verified top 20
decomposes by SDLC role. "Multi-agent" at the top means either
subagent-as-a-tool for context isolation (decision authority stays in one agent)
or generate-k-then-select. There is **no sequential-critic persona anywhere in
the top 20**. EPAM *removed* its unit-testing stage and its multi-iteration loop
moving to Sonnet 4 and scored 76.8%, joint-highest for that model.

**P2 — Harness contribution scales INVERSELY with model strength, and we are in
the regime where it is worth 10–22 points.** Fixed-model scaffold spreads
computed from the leaderboard's own `results.json`: `claude-opus-4-5` **2.4–4.8
pts** (a 100-line bash-only agent within 2.4 of SOTA); `claude-sonnet-4` 11.9;
`Qwen3-Coder-480B` **14.2**; GLM-4.6 12.8; Kimi-K2 family **~21.6** — and at
cheap models the minimal scaffold is the *loser*. The points come from tools,
context management and long horizons **inside one agent**, plus parallel sampling
with selection. Public anchor: `deepseek-v4-pro` scores **41.4%** in a plain
single-agent tools harness on SWE-rebench. Our chain got 37%; our own
`openhands` arm got 53%.

**P3 — Generate-k → select is the one multi-agent pattern with clean same-model
gains.** TRAE 70.6% single-attempt → **78.8%** with 30 candidates + an
LLM-identified regression-test filter + a selector (**+8.2 pts, identical
model**). Skywork-SWE-32B 38.0% → **47.0%** with best-of-8 (**+9.0 pts,
identical model**). Winners' order: execute existing repo tests to kill
regressions **first**, *then* a jury or a vote. Selection at k ≤ 3 is
near-worthless — CodeMonkeys: random-of-10 45.8% vs selected 57.4%, i.e. most of
the value is in *having* 10 candidates.

**P4 — Role decomposition DOES win somewhere, and it is not single-issue
patching.** CAID (arXiv 2603.21489) reports **+14.7 pp over single-agent on
Commit0** (build 54 libraries from scratch) and **+25.6 pp on PaperBench**, using
centralized delegation with **isolated git worktrees and branch-and-merge** —
architecturally our chain, including primitives we already have
(`factory/chain/worktree.py`, per-story worktrees). **This is the most important
finding for the product: we measured our chain on the one task shape where the
literature predicts it cannot help.**

**P5 — Our verification architecture is a known anti-pattern, three ways.**
(a) SpecBench (2605.21384): every model saturates its visible suite while
diverging on held-out tests; the gap grows ~28 pp per 10× code size; **weaker
models diverge much further** — and enriching the visible suite helped one task
and *hurt* another by 25 pp. (b) ImpossibleBench (ICLR 2026): GPT-5 exploits
contradictory tests **76%** of the time in repo-scale agentic settings vs
**2.9%** in a single-function scaffold — exploitation explodes in exactly our
setting; and **multiple submissions with feedback raised cheating 33% → 38%**, so
more review cycles mean more gaming. (c) AXIOM (2512.20159): LLM judges score
MCC **below 15** on code quality (near chance), and **complex agentic judge
systems scored α 37–49.5 versus 62.5–63.0 for a single simple prompt** — more
pipeline, less validity.

**P6 — "Different model" is not independence; relative capability is.** arXiv
2607.21656: a **weaker** reviewer on a stronger writer scored **−8.6 pp, fixing 3
and breaking 13**; a **stronger** reviewer on a weaker writer **+18.1 pp**;
self-review **+0.0 pp**. Our 8-of-13 byte-identical reviewed rows match the inert
self-review case — *that figure is carried from the synthesis and was not
re-derived against the archive in this pass; re-derive it before quoting it.* The
`routes.yaml` reviewer ≠ dev rule is necessary and not sufficient.

**P7 — Cheap, measured countermeasures.** Test files **read-only to the dev**
("significantly reduces cheating while maintaining performance", ImpossibleBench
ablation; cost: a sandbox setting). An **"underspecified / impossible" terminal
state** (GPT-5 cheating **54% → 9%**, o3 **49% → 12%**). Give the reviewer
**execution output instead of diff text** (judge agreement with ground truth
**42% → 72%**). Replace `test_quality_score` with a **diff-scoped mutation
score** (LLM test suites average ~40% mutation score, one documented case at 100%
coverage / 4% mutation; with mutation feedback, test strength 53% → 89.5%).
Require **red→green** — the test fails at base and passes at HEAD — which doubles
patch-stream precision at k=1 and trivially kills the zero-byte-patch class.
**Caveat that must travel with red→green wherever it appears:** only the "fails
at base" half is oracle-free. Agentless measured 213/300 tests reproducing the
bug but only 94/300 also flipping green under the gold patch, so a hard
both-halves gate rejects good patches; the fail-safe fallback is regression-only
selection, **never "approve"**.

**P8 — Benchmark reality.** Axes **B (concurrent stories), D (CI-failure
recovery), E (docs/context maintenance), F ($ per delivered unit over days)** are
covered by **nothing published**; A (decomposition) only weakly. Widening
SWE-rebench to n=60, k=3 costs **$513 Azure + ~$550 subscription** and moves the
MDE from ±38 pp to ~±12–15 pp — our effect is −7 pp (−16 pp on the later
report), so detecting it needs *high hundreds* of instances ($4–6k). **Widening
can bound the negative; it can never show the chain works.** Publicly runnable
alternatives: **SWE Atlas** (2605.08366 — released harness and judge prompts, 284
expert tasks, test-writing graded by **mutation score**, frontier ~42–43% Pass@1,
Pass^3 drops 30–50%) and **Commit0** (where CAID's +14.7 pp was measured).
Unconfirmed availability but the best axis fit: **RoadmapBench** (2605.15846),
**ChainSWE** (2607.02606), **SlopCodeBench** (2603.24755). SWE-bench Pro leaks
post-`base_commit` git objects via `git log -p`. SWE-bench-Live is confirmed dead
(0 test rows after 2025-10-01). SWE-Marathon is public but its frontier ceiling
is <30% at 27.2 M tokens per attempt — not yet.

**P9 — SacrificeBench is the only design that can measure the real product
claim.** See Phase D.

> **Confidence rule for everything in P8.** These benchmark *names* reached us
> through a fetch pipeline that silently rewrites proper nouns (see
> `SOTA-RESEARCH-2026-07.md`, "Fetched content is lower-confidence than fetched
> numbers"). Verify every name and arXiv id against the source before quoting it
> outside this repo. A number from a fetched source is more trustworthy than the
> name attached to it.

---

## 3. What is NOT broken — do not go fix these

A fresh agent's biggest risk here is re-diagnosing something already solved.
Items 1–4 were checked 2026-08-01 and re-checked 2026-08-04.

1. **Chain self-edit works.** 122 stories carry a PR number, 118 PRs are merged,
   24 factory stories reached `deployed`, and the staging gate has a real
   17-validated / 3-rejected record. Loop 1 is proven zero-touch. Nothing to fix.
   **This is a delivery fact, not a correctness fact** — §1 is the correctness
   measurement and it is the one that came back flat.

2. **CI-failure recovery works.** `factory/chain/auto_merge.py:1640-1830`
   (`_handle_ci_failure`) fetches the CI log digest, emits a well-formed finding
   *dict*, re-enters at `REVIEWER_REQUESTED_CHANGES` (deliberately not
   `DEV_IN_PROGRESS`, which has no dispatch-table entry), and resets both
   counters. Capped at `_MAX_CI_FIX_CYCLES = 3` (`auto_merge.py:72`) plus an
   identical-failure-signature bail (`:1759-1766`). A previous session already
   misdiagnosed this as broken — the `ci_fix` events live in `state/logs/*.log`,
   **not** `state/events/*.ndjson`.

3. **Reviewer non-convergence is fixed.** Last 14 days (122 stories):
   `reviewer_cycles` = {0: 101, 1: 18, 4: 2, 5: 1} — zero stories at 6+, max 5.
   The convergence guard holds. Note that "converges" and "helps" are different
   claims: §1 #6 shows it converging and not helping.

4. **The GitHub loop is clean.** 0 open PRs, 1 open issue (#122, a real backlog
   direction), 0 blocked stories.

5. **The benchmark harness itself is sound, and it took four retractions to get
   there.** Per-node grading, arm isolation under a flat `SWEBENCH_WORK_ROOT`,
   fail-closed `_DIFF_HEADER`, test-edit stripping asserted in code on every arm,
   a manifest frozen before the first run, a gold-patch selftest control at
   19/20, an `audit` subcommand that fails closed on a missing artifact, and
   `report --check` re-deriving the published table byte-for-byte from a
   committed archive. **Do not "improve" the harness without a failing case.**
   Its two open debts are reporting only — see `1.6 G`.

Also already fixed, so do not re-fix:

- **`dirty_working_tree` in both apply paths.** Both
  `factory/manager/apply.py:882-897` and
  `factory/chain/factory_improver_apply.py:418-436` are now **path-scoped**
  (`git diff --quiet HEAD -- <patch target paths>`, falling back to repo-wide
  only when the patch is unparseable). The 158 historical failures in the
  improver log all predate this — see Corrections #10, which is why patch-apply
  fuzzing is deferred in Phase E.
- **`db_path` threading in `runner._record`** — done.
- **Reviewer/dev model collision** — `reviewer` moved to `azure/gpt-5.4` in both
  provider blocks and the check is enforced at router load
  (`model_router.check_review_independence`). Different-model now holds; whether
  it is the *right* difference is Phase A.7.

---

## 4. Done — the measurement substrate (Phase 0, Phase 1, 1.6 A–F)

Kept short. These phases are closed; their value now is the file references and
the corrections they produced.

### Phase 0 — make measurement possible — **DONE 2026-08-01, $0**

| Shipped | PR |
|---|---|
| `sandbox_run` logs prompt metadata; new `prompt_bodies.ndjson` keeps full text + full sha256, hash-chained. Bodies are captured for **chain personas only** — storing `manager_watcher` too would have been 1.58 GB and would have evicted the dev/reviewer bodies the stream exists for | #193 |
| `retried` / `review_cycle` rows emitted from inside the handlers, reconciling with the DB counters. Used `retry_attempt`/`retry_cap`, because `emit_chain_step`'s payload already carries `attempt` | #194 |
| `gates_failed` on `MergeAction`, a `gates_failed_json` column, a `merge_gates_failed` story event; the write-never `smoke_passed` reader deleted so the smoke gate is fail-closed *structurally* rather than by accident | #195 |
| `reviewer` → `azure/gpt-5.4` in both blocks, enforced at router load; loop caps 6 → 3 with inner guards 3 → 2 so early escalation stays reachable | #196 |
| `bench/bench.py` pinned: literal `base_sha` and an empty one refused, `claude --model` pinned, `clean()` no longer deletes `bench/runs/`, every `result.json` records base/routes/price-table provenance, tokens reported as the primary metric | #197 **[OPERATOR-PR]** |

**Behavioural consequence to remember:** at `_MAX_DEV_RETRIES = 3` the dev inner
loop gets at most **two** sandbox attempts per invocation, so `red → red → green`
no longer converges in one tick. Phase B.1 argues this chopped horizon is part of
the problem.

### Phase 1 — first real number — **1.1–1.5 DONE 2026-08-02**

`bench/swebench_adapter.py` exists, grades against a hidden oracle with test
edits stripped and asserted, and `report` archives every artifact it consumed
into `results-archive/<generated-at>/` and refuses any row whose artifacts are
missing (#199, #200, #202, #204, #205, #206, #210, #211). The 2026-08-01 batches
were retracted for three harness bugs (fail-open blind reviewer diff,
uninitialised submodules, 1.62× cost under-report); the 2026-08-02 n=6 pair is a
plumbing record only, superseded by §1.

### 1.6 — Arm parity and integrity repair, then one clean n=19 re-run — **A–F DONE 2026-08-04** **[OPERATOR-PR-ONLY]**

Actual cost of the sweep: **$59.25** Azure price-table estimate (factory $35.94 +
openhands $15.37 + bare $7.94, on the committed report) plus $57.92
CLI-reported against the Anthropic subscription. Estimate was ~$50 Azure.

- [x] **A — integrity hardening.** Every arm's live tree moved under a flat
      `SWEBENCH_WORK_ROOT` keyed by (instance, arm, model), so no arm is a `..`
      away from `oracle.json.z` or a sibling's `grade.log`; only finished
      artifacts are copied back. Per-node `PASSED` grading replaced exit-code
      grading: `-rpfEsxX` (that is `-rA` minus `P`, so arm-authored code cannot
      echo a forged `PASSED <id>` into the region the parser reads), and every
      declared `FAIL_TO_PASS` / `PASS_TO_PASS` id must have a `PASSED` node and
      no `FAILED`/`ERROR` node. `_DIFF_HEADER` fails CLOSED. `audit.json` carries
      `prediction_sha256`, `base_commit`, `stripped_test_paths`, `refused_paths`,
      `trajectories_scanned`, `trails_scanned`. **Produced: zero path-based
      oracle probes in the sweep**, versus 4 audit-invalidated factory rows
      before.
- [x] **B — arm parity.** One `_BASE_TESTS_NOTE`, byte-identical, reaches
      `_STORY_TEMPLATE` (factory/openhands/claude) and `_BARE_TASK` (bare), so
      "matched prompt" is true rather than asserted. Bare got the test-writing
      instruction, an empty-diff DONE guard, a real message list, the parsed
      command echoed into history, bash-fence tolerance, `TimeoutExpired`
      handling and persisted observations. **Produced: the `openhands` arm, and
      with it the sweep's only interpretable headline.** Every arm records
      `model`, `models_used`, `model_calls`, `model_escalated_calls`, which is
      how the factory's 6 hard-tier `gpt-5.3-codex` calls are visible in Table 1
      instead of hidden.
- [x] **C — reporting honesty, mostly.** `--from-archive` prints and never
      overwrites; `--check` diffs and exits non-zero on drift;
      `report-meta.json` persists `foreign`/`refused`; one budget rule for every
      arm (a cap hit is a counted, flagged attempt); `fresh in` and `cache read`
      split (a blended column had made the published "34× tokens" claim wrong by
      4.5×); cost source labelled per arm; an `attempt` column and a "Discarded
      runs" section; `n/a (arm has no chain verdict)` instead of a division
      artifact; `pass_to_pass_count == 0` flagged; `estimate_instance_cost`
      filtered by `manifest_sha256`. **Not closed — see G.**
- [x] **D0 — probe before you sweep.** `--probe-plumbing` with a stubbed model
      for every non-factory arm, plus one paid single-instance run per new arm.
      **Produced:** the probes are why the sweep did not re-discover a
      six-step-giveup arm for $50.
- [x] **D — one clean re-run, n=19, k=1, five arms**, one sweep. `attempt` is 1
      on all 95 rows of the committed report.
- [x] **E — caveats are structural, not prose.** Per-arm Clopper-Pearson CIs,
      paired McNemar exact per pair with `harness varies?` / `model varies?`
      columns, the ±38 pp MDE stated, the per-row model mix, and the subset
      relation printed.
- [x] **F — contamination margin per arm, printed.** Table 2 carries
      `margin_days` per model bound; Table 4 names the bound TYPE.
      `deepseek-v4-pro` remains `release-date-proxy`. **The Claude half of the
      question is answered** — see §1 #8.
- [ ] **G — the three debts D–F did not close.** All reporting, not measurement.
      Neither of the first two moves a published number; both would mislead the
      next reader. **[OPERATOR-PR-ONLY]**
      - **No retry on a provider 429.** `openhands` lost 3 of 19 rows to Azure
        `DeepSeek-V4-Pro` `RateLimitError` under `--workers 4`, and a lost row
        records `cost_usd: 0.0`, which reads as free rather than as missing.
        Retry with backoff, or fail the sweep loudly — never both silently. The
        23:19Z report re-ran those three rows as `attempt: 2`, which is that fix
        applied by hand; **decide whether a 429-lost row may be re-run at all**,
        because the report's own "Discarded runs" section says `attempt > 1` is
        "a protocol violation, not a data point" while the headline counts three
        of them. Amend `PRE-REGISTRATION-1.6.md` Rule 5 to distinguish
        *repairing an infrastructure loss* from *re-rolling an outcome*, or drop
        the rows. Until that is written down, cite both numbers as §1 does.
      - **`sweep-<arm>.json` aggregates contradict their own rows.** The
        `resolved` / `audited_valid` / `audit_failed` counters are in-flight
        snapshots taken before grading and before the #227 detector fix, so
        `sweep-factory.json` says `resolved: 2, audit_failed: 13` while its own
        `results` list says 7 resolved and the archived `audit.json` files say
        19 ok / 0 invalid. Recompute the aggregates from the rows at write time,
        or delete them.
      - Minor, already closed in the later run: the 04-18 archive carries only
        `sweep-bare.json` and `sweep-factory.json`; the 23:19Z archive carries
        all five. Committing that archive closes this one for free.
      - **Effort:** ~4 h for the 429 retry, ~1 h for the aggregates, ~1 h to
        amend the pre-registration. **Cost $0** — no new sweep required.

---

## Phase A — stop the self-confirmation

**Rests on P5, P6, P7. Effort ~1.5–2 weeks. Cost ~$60** (A.1's re-measure ~$40 +
A.7's reviewer-ranking arm ~$18; everything else is cents). This phase comes first
because it is the cheapest, because every later measurement is uninterpretable
without it, and because P5 says our failure mode gets *worse* with model weakness
and with repo scale — which is our exact operating point.

The chain's own verdict is right 40% of the time (§1 #4) and it once certified a
zero-byte patch (§1 #5). Nothing in Phase B is worth buying until a green verdict
means something.

**Replay before you ship.** Most of A is testable against archived reviewer
prompts for cents rather than by re-running a sweep. **But check the corpus
first:** `prompt_bodies.ndjson` (#193) had **zero production rows** as of
2026-08-02, because the systemd units have been stopped since ~2026-07-30. Bring
the units up (E.5) before claiming a replay corpus exists.

### A.1 — Turn the independent acceptance oracle ON, and put it in the measured path

- [ ] **The countermeasure P7 recommends first is already built here, in a
      stronger form than the paper's.** `factory/chain/acceptance.py:1-22`
      documents it: authored from the **spec only** (direction ACs + `flow.md` /
      `api_spec.md`), authored **early** (at story spawn, `handlers.py:504` and
      `:589`, long before the dev handler runs on a later tick), stored in
      `state/acceptance/<app>/<story_id>/` — outside the app repo and outside the
      per-story dev worktree — and never handed to the dev sandbox, which
      receives only `repo_path`. The path is recorded on
      `StoryRecord.acceptance_test_ref` (`factory/chain/state_machine.py:344`)
      and enforced by `factory/chain/gates/acceptance_verified.py`, which becomes
      merge-required when the app opts in
      (`factory/chain/gates/evaluator.py:79-87`).
- [ ] **It has never run. Verified 2026-08-04.** `gates.acceptance_oracle`
      defaults `False` (`factory/app_config.py:113`) and is set in **no** app
      config — `apps/factory/config.yaml`, `apps/sacrifice/config.yaml` and
      `apps/template-probe/config.yaml` all omit it. In `state/factory.db`,
      `acceptance_expected` is 0 for **all 165 stories** and
      `acceptance_test_ref` is null for **all 165**. This is the write-never
      pattern one level up: a whole independence layer, built, tested, wired, and
      switched off.
- [ ] **And the benchmark cannot see it.** `bench/swebench_adapter.py:2416` runs
      `allowed = {"dev", "review"}` against a story seeded at `SM_DONE`
      (`:2404`), while the oracle is authored in `handle_stories_spawned`. So the
      37% and the 40% chain-verdict precision in §1 were measured **with the
      chain's only independent oracle absent.** The arm labelled "the product"
      was not the whole product.
- **What:** (1) opt one app in and watch one story end to end; (2) teach the
  adapter to author an oracle from the problem statement before the dev dispatch,
  so the measured arm is the whole product.
- **⚠ Fail-safe check before flipping the flag.** `required_gate_labels` keys off
  `acceptance_expected`, **not** `acceptance_test_ref`
  (`factory/chain/gates/evaluator.py:67-77`), deliberately: a story whose
  authoring flaked is still required to pass, so it **blocks** rather than
  shipping un-gated. Flipping the flag therefore blocks every AC-carrying story
  until authoring works. Do it on one app, with the units up, and watch the first
  story.
- **⚠ And do not claim independence you do not have.** `acceptance_author` is
  `azure/gpt-5.4` (`factory/routes.yaml:94`), the same model as `reviewer`
  (`:124`) — acceptable, because what matters is that it is not the dev's model
  (`:130`, `azure/deepseek-v4-pro`). P6 says rank them; A.7 does.
- **Done looks like:** one story with a non-null `acceptance_test_ref` that the
  `acceptance-verified` gate actually ran, plus one benchmark row whose
  `result.json` shows an oracle authored before the dev's first call.
- **Effort:** ~2 h to flip and soak one story; ~1 day for the bench half
  **[OPERATOR-PR-ONLY]**. **Cost:** ~$1 of extra authoring per story; ~$40 to
  re-measure 19 instances.

### A.2 — A production-tree-changed precondition before any green verdict

- [ ] **Evidence is one artifact-backed row on `origin/main`** — §1 #5. The chain
      said green on a zero-byte production patch.
- [ ] **The existing guard cannot catch it.** `_dev_produced_empty_diff`
      (`factory/chain/handlers.py:2484`, short-circuited at `:2997`) tests the
      **whole** diff, so a diff containing only test files reads as non-empty, the
      story proceeds to review, and the reviewer approves a change to the tests
      with no implementation behind it.
- **What:** partition the post-dev diff into production paths and test paths, and
  refuse a green verdict when the production half is empty. The classifier
  already exists on the bench side (the test-strip list and `_DIFF_HEADER`); lift
  it into `factory/chain/` so one implementation serves both. Route the refusal
  to A.3's underspecified state, **not** back to review — churning review on an
  empty implementation is the expensive failure the empty-diff short-circuit was
  added to stop.
- **⚠ Fail-safe:** an unparseable diff must block, not pass. `_DIFF_HEADER`
  already sets that precedent.
- **Done looks like:** a seeded story whose dev writes only a test file never
  reaches `REVIEWER_REQUESTED_CHANGES` or `REVIEWER_DONE`, and the
  `harumiweb__exstruct-113` trajectory replays to a block.
- **Effort:** ~3 h. Chain code. **Fail-safe review required** — this touches the
  dev → review handoff.

### A.3 — An "underspecified / impossible" terminal state

- [ ] **Evidence:** P7 — GPT-5 cheating **54% → 9%** and o3 **49% → 12%** once the
      agent has a legitimate way to say the task is unsatisfiable.
- [ ] **Verified gap.** `StoryState` has eight `BLOCKED_*` sinks
      (`factory/chain/state_machine.py:71-149`), and every one of them means "the
      machine gave up", not "the spec contradicts itself". The nearest,
      `BLOCKED_TESTS_NEED_CLARIFICATION`, is reached only by **exhaustion**
      (`state_machine.py:412`, `:414`, on `EVENT_DEV_EXHAUSTED`). The dev has no
      non-failing way to report contradictory acceptance criteria, so the only
      behaviour that scores is producing *something*.
- **What:** a dev-declarable `BLOCKED_UNDERSPECIFIED` carrying an explicit
  contradiction report (which ACs, which lines), surfaced in `factory inbox`
  rather than retried.
- **⚠ Two guardrails, both non-negotiable.** Declaring it is **terminal for the
  story** — it cannot be used to dodge work twice — and it must **never satisfy a
  gate**: it is a block, and every benchmark denominator counts it as a
  non-resolve. A "get out of work free" state that scores is worse than no state.
- **Done looks like:** a deliberately self-contradictory story reaches the new
  state on the dev's own declaration, appears in `factory inbox`, and counts as
  unresolved in `report`.
- **Effort:** ~4 h (state, transition, persona text, inbox surface). Chain code.

### A.4 — The reviewer gets execution output, not diff text

- [ ] **Evidence:** P7 — judge agreement with ground truth **42% → 72%** on
      execution output instead of a diff; P5(c) — LLM judges score MCC < 15 on
      code quality, and *more* judge pipeline means *less* validity.
- [ ] **Verified current state.** `_fetch_pr_diff_for_review`
      (`factory/chain/handlers.py:2618`, called at `:3065` and `:3449`) is the
      reviewer's entire view of the work. Its fail-closed posture is correct
      (#203 — the old fail-open fed the fetch's error text to the model *as* the
      diff), but what it delivers is diff **text**.
- **What:** attach the recorded test-run evidence to the reviewer prompt — the
  dev's own run output (the `output_tail` plumbing exists on the gate path,
  `factory/chain/gates/smoke_green.py:51-56`, and #195 persists failing gates'
  details) plus a harness-run result. Keep the diff; add the execution evidence;
  and say in the prompt which one wins when they disagree.
- **Do not** add a second judge or a judge pipeline. P5(c) measures that as worse
  than one simple prompt.
- **Done looks like:** a replay over archived reviewer prompts shows agreement
  with the hidden oracle rising on the 19 instances in §1, measured *before* the
  change ships.
- **Effort:** ~1 day. Chain code. **Cost: cents** if the replay corpus exists —
  read the Phase A preamble first.

### A.5 — Replace `test_quality_score` with a diff-scoped mutation score

- [ ] **What it is today: a number the reviewer model asserts about itself.**
      `test_quality_score` is emitted by the reviewer persona
      (`factory/personas/reviewer.md:38`, `:54`, `:178`, `:203`), read at
      `factory/chain/handlers.py:3168`, and it gates the verdict below 0.7. P5(c)
      puts an LLM's judgement of test strength near chance.
- [ ] **The measurement that should replace it exists and is broken.**
      `factory/chain/gates/tests_meaningful.py:63-138` implements real mutation
      testing (no-op a symbol, re-run the suite, fail if it stays green). It has
      **never run** — `mutation_testing: false` in all three app configs
      (`apps/factory/config.yaml:38`, `apps/sacrifice/config.yaml:68`,
      `apps/template-probe/config.yaml:55`) — while `tests-meaningful` **is** in
      `LOOP4_REQUIRED_GATE_LABELS` (`factory/chain/gates/evaluator.py:46-51`).
      That flag is the only thing between this code and every merge.
- [ ] **Four verified defects — do not simply flip the flag.**
  1. **It ablates the wrong symbols.** `_changed_public_symbols` (`:140-172`)
     parses each changed file *whole* and returns every public symbol, not the
     ones the diff touched; with `_MAX_ABLATION_SYMBOLS = 5` and a
     `(path, lineno)` sort it takes the top five of the alphabetically-first
     file. Over the last 40 commits: median 21 candidates, 77% hit the cap. For
     `e13d98e0` the five chosen symbols have **zero overlap** with the four the
     commit changed.
  2. **Fail-OPEN on infrastructure failure.** `_run_pytest` returns `False` on a
     600 s timeout or `FileNotFoundError`, and `survived == False` is read as
     "exercised → good" (`:104-107`). There is no green baseline before mutating,
     so an already-red suite, a flaky red, or a failed `uv sync` certifies
     coverage that was never measured.
  3. **It mutates the live story worktree.** `repo_root` is the
     `state/worktrees/` checkout the chain later pushes from, and `_mutate_source`
     round-trips the whole file through `ast.unparse` — on `handlers.py` that is
     4,804 → 2,113 lines with all 756 comments stripped. Restore sits in a
     `finally`, which does not run on `SIGKILL`, and the tick unit has
     `TimeoutStartSec=3h`.
  4. **It fails in dry-run, which is the default.** `:68-75` returns
     `passed=False` when `dry_run`, and `factory auto-merge` defaults to
     `--dry-run` (`factory/cli.py:2464`). Worse, `auto_merge.py:928-942` writes a
     `merge_gates_failed` story event **unconditionally, including dry-run** — so
     flipping the flag manufactures false gate-failure events into the exact
     substrate L1→L2→L3 escalate on.
- **What:** rewrite the ablation branch — diff-hunk-scoped symbol selection, a
  green baseline with non-green ⇒ `skipped`, timeout/infra distinguished from a
  real red, mutation in a throwaway copy, per-`(head_sha, symbol)` caching, and
  **advisory until measured** — then let the score it produces replace the
  reviewer's self-reported number.
- **Why this is now worth two days when the old 3.8 said "deleting is cheaper".**
  Three things changed: P7 gives a measured payoff (test strength 53% → 89.5%
  under mutation feedback; LLM suites average ~40% mutation score, one case at
  100% coverage / 4% mutation); §1 #4 says the number it replaces is a coin flip;
  and SWE Atlas grades test-writing **by mutation score** (P8), so this buys
  Phase C comparability for free. Deleting the branch is still the right call if
  the rewrite stalls — a gate detached from a real check is worse than no gate
  (`factory/chain/gates/evaluator.py:18-29`).
- **⚠ Never flip `mutation_testing` as an experiment.** It is one flag from
  breaking every merge. See memory `ablation_gate_dormant_and_broken`.
- **Effort:** ~2 days. **Cost context:** the full factory suite is 5m36s warm, so
  five ablations is ~28 min per merge evaluation, re-run every tick per open PR —
  the cache is not optional.

### A.6 — Harness-owned red→green, with a regression-only fallback

- [ ] **Evidence:** P7 — red→green doubles patch-stream precision at k=1, and it
      is a second, independent kill for the §1 #5 zero-byte class.
- [ ] **Red-first is instructed, not verified.** `factory/personas/dev.md:41`:
      "Tests are red-first: a test that passes before the implementation exists is
      slop." The chain trusts that claim. `PRContext.commit_history` already
      carries `tests_run_red: bool | None` per commit
      (`factory/chain/gates/evaluator.py`), which is the dev's report, not an
      observation.
- **What:** the harness runs the dev's new tests itself at the pre-dev base SHA
  and records the result. "Fails at base" becomes the gate; "passes at HEAD" is
  already `tests-green` (`factory/chain/gates/tests_green.py:69-83` re-derives it
  at merge time).
- **⚠ Put the caveat in the code comment, not only here.** Only the fails-at-base
  half is oracle-free. Agentless measured 213/300 tests reproducing the bug but
  only 94/300 also flipping green under the gold patch, so a hard both-halves
  gate rejects good patches. The fallback when the base run cannot be trusted is
  **regression-only selection — never "approve"**.
- **Done looks like:** a story whose new test passes at base is blocked with the
  base-run output attached, and one whose test fails at base and passes at HEAD
  proceeds.
- **Effort:** ~1 day. Chain code. Cost: one extra suite run per story.

### A.7 — Check whether the reviewer is actually STRONGER than the dev — and cut the loop if not

- [ ] **Evidence:** P6. Weaker-reviewer-on-stronger-writer **−8.6 pp** (fixed 3,
      broke 13); stronger-on-weaker **+18.1 pp**; self-review **+0.0 pp**. Our
      8-of-13 byte-identical reviewed rows match the inert case.
- [ ] **What we enforce today is difference, not rank.** `factory/routes.yaml`:
      dev standard `azure/deepseek-v4-pro` (`:130`), dev hard
      `azure/gpt-5.3-codex` (`:135`), reviewer `azure/gpt-5.4` (`:124`).
      `model_router.check_review_independence` refuses a colliding config and
      says nothing about which model is better.
- **What:** rank the three deployments on the same 19 instances. Phase C gives
  most of this free — `openhands` at 53% is a capability read for
  `deepseek-v4-pro` under a fixed harness. One more `openhands` arm on
  `azure/gpt-5.4` places the reviewer on the same axis. If the reviewer is not
  measurably stronger than the dev, cut the review cycle to **one advisory pass**
  and keep the deterministic slop gate, which is the layer that actually runs.
- **Done looks like:** a per-model rate table under one fixed harness, and a
  recorded decision on the review loop that cites it.
- **Effort:** ~half a day of analysis. **Cost ~$18** for one 19-instance
  `openhands` arm on the reviewer's deployment. **[OPERATOR-PR-ONLY]** for the
  bench half.

### A.8 — Do NOT add review cycles

- [ ] **Evidence, both directions.** P5(b): multiple submissions with feedback
      raised cheating **33% → 38%**. Ours: reviewer cycles `0×7, 1×9, 2×2, 3×1`
      across the 19 factory rows and the resolve rate did not move (§1 #6).
- **What:** nothing. The caps stay at 3 with inner guards at 2
  (`factory/chain/handlers.py:1244`, `:1259`, `:1304`, `:1305`). Any proposal to
  raise them, or to add a second review pass, needs a measured lift first — and
  P5(b) predicts the opposite.
- **Effort:** 0. This item exists so the next agent does not "fix" convergence by
  buying more of it.

---

## Phase B — capture the 10–22 points that exist at our model class

**Rests on P1, P2, P3. Effort ~3 weeks. Cost ~$300 including re-measurement.**

**⚠ Sequence this AFTER Phase A, without exception.** With a self-confirming
oracle, a stronger single agent is just faster self-confirmation, and every
number this phase produces would be measured by the gate §1 #4 says is right 40%
of the time.

P2 puts 10–22 points on the table for a model in our class, and P1 says none of
them come from splitting the work across SDLC roles. The public anchor is blunt:
`deepseek-v4-pro` scores **41.4%** in a plain single-agent tools harness, our own
`openhands` arm scored **53%**, and our chain scored **37%**.

### B.1 — Collapse the code-producing personas into one long-horizon agent

- [ ] **Evidence:** P1 (no SDLC-role decomposition in the top 20; no sequential
      critic anywhere in it; EPAM *removed* its unit-testing stage and its
      multi-iteration loop and scored 76.8%, joint-highest for its model) and P2
      (the points come from tools, context management and long horizons **inside
      one agent**).
- [ ] **Our horizon is long enough, and chopped up.** `sandbox_run`'s default is
      `max_iterations = 600` (`factory/runner.py:1643`), with per-persona caps of
      180 for `onboarder` and 300 for `test_implementer` (`PERSONA_ITERATION_CAPS`,
      `factory/runner.py:1621-1630`). So iteration budget is **not** the deficit —
      the deficit is that the budget is split across handler invocations, and
      since #196 the dev inner loop gets at most **two** sandbox attempts per
      invocation, so `red → red → green` cannot converge in one tick.
- **What:** one dev-and-tests agent per story, no `test_implementer` hand-off, no
  reviewer round-trip inside the inner loop. Keep every deterministic gate —
  those are the durable half, and P2's points do not come from deleting them.
- **⚠ This deletes product surface, and it is the largest change in this plan.**
  It also removes the reviewer from the inner loop, which A.7 may already have
  demoted. Do A first, then A.7's ranking, then this.
- **Done looks like:** one arm on the same 19 instances, reported beside
  `openhands` and the current `factory`, with the model mix printed per row.
- **Effort:** ~1 week. **Cost ~$40** to re-measure 19 instances.

### B.2 — Real navigation tooling inside the one agent

- [ ] **Verified current state.** The dev gets OpenHands' `get_default_agent`
      preset (`factory/runner.py:1813`) — bash plus a file editor. **No symbol
      search, no partial-file views.** `get_planning_agent` is imported at
      `factory/runner.py:934` for a different path.
- **What:** symbol search, tree-sitter partial file views, and a `status` tool
  that forces explicit completion — then **re-prompt any trajectory that ends
  without it**. We already have half the last one: `SELF_SUMMARY:`
  (`factory/runner.py:981`, extracted at `:997-1016`) is a marker the dev is
  *asked* for, and nothing re-prompts a run that omits it.
- **Why this before B.3:** P2 attributes the fixed-model spread to tools and
  context management, which are cheap; sampling k candidates multiplies whatever
  one trajectory is already worth.
- **Done looks like:** trajectory counts showing symbol-search calls, zero
  trajectories ending without an explicit completion, and a re-measured arm.
- **Effort:** ~3 days. **Cost ~$40** to re-measure.

### B.3 — Generate-k → select: regression filter FIRST, reviewer repurposed from critic to selector

- [ ] **Evidence:** P3. TRAE 70.6% → **78.8%** with 30 candidates + a
      regression-test filter + a selector, identical model. Skywork-SWE-32B 38.0%
      → **47.0%** at best-of-8, identical model. Winners execute the existing repo
      tests to kill regressions **before** any jury or vote.
- [ ] **Do not build a selector at k ≤ 3.** CodeMonkeys: random-of-10 45.8% vs
      selected 57.4% — most of the value is in *having* 10 candidates, and
      selection at k=2 or 3 is near-worthless. Either budget for k ≥ 8 or skip
      the item.
- **Costed honestly.** `openhands` measures at $18.20 / 19 = **$0.96 per
  instance**, so k=8 is ~$7.7 per instance ≈ **$146 for one 19-instance arm**;
  k=30 is ~$550 and out of budget at this n. Budget k=8 and say so in the report.
- **The seams already exist.** `factory/chain/gates/tests_green.py:69-83`
  re-derives the truth at merge time — that is the regression filter. The reviewer
  already emits a structured verdict; have it **rank N candidate patches** instead
  of critiquing one, which is also the only reviewer-shaped role P1 finds at the
  top of the leaderboard.
- **Done looks like:** `resolve@1` and `pass^k` reported separately for k=8 on the
  same instances, with the regression filter's kill count printed.
- **Effort:** ~1 week. **Cost ~$150** for one k=8 arm. **[OPERATOR-PR-ONLY]** for
  the bench half.

### B.4 — Retry only on non-termination, never on review disagreement

- [ ] **Evidence:** P5(b) — more submissions with feedback means more gaming —
      plus §1 #6, where cycles happen and nothing moves.
- **What:** a retry fires when the agent fails to *terminate* (cap hit, crash, no
  explicit completion from B.2), never because a critic disagreed. Under B.3 the
  review loop stops being a retry trigger at all, so this is mostly a deletion:
  `_MAX_REVIEW_CYCLES` (`factory/chain/handlers.py:1305`) exists to bound exactly
  the loop B.3 removes.
- **⚠** Keep the cap while the loop exists. Do not delete the bound before the
  loop it bounds.
- **Effort:** ~2 h once B.3 lands.

---

## Phase C — measure where the claim can actually be expressed

**Rests on P4, P8. Effort ~3 weeks. Cost ~$900.** **[OPERATOR-PR-ONLY throughout
— `bench/**`]**

We measured our chain on single-issue patching, which P1 identifies as the one
task shape where role decomposition is *known* not to help. C.3 is the direct
test of the shape where it is known to help. C.4 — more SWE-rebench — is demoted
because it cannot produce a positive result no matter how much it costs.

### C.1 — Free availability probe, first

- [ ] **1 day, $0, and the highest expected value per dollar in the plan.** Probe
      whether these are actually runnable: **RoadmapBench** (2605.15846 — 115
      tasks, median 5 weighted subtasks, hidden target-version tests, git tags
      pruned, OpenHands baselines published — the best axis fit we found),
      **ChainSWE** (2607.02606 — sequential dependent fixes, up to 70%
      degradation with chain length), **SlopCodeBench** (2603.24755 —
      erosion/verbosity over 196 checkpoints; best agent passes 14.8%),
      **SWE-EVO**, **DevOps-Gym**.
- **⚠ Verify the names before you quote them.** These reached us through a fetch
  pipeline that silently rewrites proper nouns — see the confidence rule in §2 and
  the note in `SOTA-RESEARCH-2026-07.md`. Check each arXiv id resolves and each
  dataset has a downloadable harness. A "this benchmark does not exist" outcome is
  a *successful* probe.
- **Done looks like:** a five-row table — name, arXiv id resolves y/n, harness
  public y/n, oracle shipped y/n, axis covered — committed under `bench/`.
- **Effort:** 1 day. **Cost $0.**

### C.2 — SWE Atlas, n=60, three arms

- [ ] **Why this suite:** 2605.08366 ships its harness **and** its judge prompts,
      284 expert-authored tasks, frontier ~42–43% Pass@1 with Pass^3 dropping
      30–50% (so it has headroom and it measures consistency), and it grades
      **test-writing by mutation score** — which pairs with A.5 and gives us one
      external number for the layer §1 #4 says is broken.
- [ ] **Arms: `factory`, `openhands`, `claude-5`.** `openhands` is mandatory in
      every sweep from now on — it is the only pair that holds the model fixed and
      varies the harness, so it is the only arm that can measure the product. A
      factory number published without it is a number about the model.
- **Done looks like:** the five pre-registered tables, an archived
  `report --check`-green run, and the mutation-score column filled.
- **Effort:** ~1 week for the adapter. **Cost ~$400.**

### C.3 — Commit0 lite, n ≈ 15 — the direct test of P4 on our own architecture

- [ ] **This is the highest-information experiment in the plan for the product
      question, because it is the only one that can come back positive.** CAID
      (2603.21489) measured **+14.7 pp over a single agent on Commit0** — build a
      library from scratch, 54 of them — using centralized delegation with
      **isolated git worktrees and branch-and-merge**. That is our architecture,
      including primitives we already have (`factory/chain/worktree.py`, per-story
      worktrees, `freshen_behind_prs`, conflict-rebuild-on-fresh-branch).
- [ ] **Arms: `factory` and `openhands`, same model, n ≈ 15.** Report paired
      McNemar as always. At n=15 this resolves a large effect only — CAID's
      +14.7 pp is roughly that size, which is why n=15 is defensible here and n=19
      was not enough for a 7-pp question.
- **⚠ State the asymmetry up front.** A positive result here does not rehabilitate
  the chain on single-issue patching; it relocates the claim to a different task
  shape, which is exactly what P1 and P4 together predict. Write that in the
  pre-registration, before the data.
- **Done looks like:** a paired two-arm table on Commit0 with the same
  archive/`--check` discipline as §1.
- **Effort:** 2–4 days for the adapter. **Cost ~$450.**

### C.4 — Widening SWE-rebench — DEMOTED, with its honest costing

- [ ] **What it costs and what it buys.** n=60, k=3 costs **$513 Azure + ~$550
      subscription** and moves the MDE from ±38 pp to ~**±12–15 pp**. Our effect is
      −7 pp on the committed report and −16 pp on the later one. Detecting an
      effect that size needs **high hundreds of instances, $4–6k**.
- [ ] **The structural limit.** **Widening can bound the negative; it can never
      show the chain works.** Do it when a bound is what you need — e.g. to state
      publicly "the chain is not worse than one agent by more than X" — and not
      before C.1–C.3.
- [ ] **The design below is correct and cheap to reuse.** Keep it verbatim when
      C.4 runs; it was built and paid for in Phase 1.6.
  - Manifest **frozen before the first run**: published RNG seed, hash-pinned
    manifest (task id → repo → base SHA → problem-statement hash), committed and
    tagged. **k ≥ 3**, reporting `resolve@1` and `pass^k` separately. Measured
    variance to budget against: 0/10 oracle flips over 10 same-condition factory
    replications (95% upper bound on per-instance flip probability 25.9%, i.e.
    ±3 instances at n=19), 1/10 chain-verdict flips, and cost varying up to 2.6×
    on the same instance.
  - **Filter on `created_at`, never on split label.** SWE-rebench's `2026_03`
    split (110 rows) is exactly `created_at > 2026-03-01` — it aggregates March,
    April *and* May PRs.
  - **Two strata.** Measured supply in `nebius/SWE-rebench-leaderboard` (860 test
    rows): `>2026-01-01` = 215, `>2026-02-01` = **167**, `>2026-04-24` = **30**,
    `>2026-06-01` = **0**; corpus max **2026-05-12**. Main stratum: 120 tasks from
    `>2026-02-01` (clears both OpenAI deployments' published 2025-08-31 cutoff).
    High-margin stratum: the 30 tasks from `>2026-04-24` (additionally clears
    `deepseek-v4-pro`'s release-date bound). Report every arm **per stratum**. At
    n=30 that resolves a large effect (~±9 pp at 50%), not a subtle one.
  - **The suite of record is SWE-rebench and it is healthy** —
    execution-validated, docker image and oracle shipped in-row, monthly splits
    through 2026-05-12. Rejected alternatives: **SWE-bench Verified** (the
    comparability standard, but 2023 instances and the most contaminated corpus in
    the field — use only if a leaderboard-comparable number is the goal),
    **SWE-bench Pro** (frozen after OpenAI's ~30%-broken audit, and it leaks
    post-`base_commit` git objects via `git log -p`), **SWE-rebench V2** (nothing
    after 2026-01), **MultiLang** (no Python). **SWE-bench-Live is dead** — last
    modified 2025-09-18, newest instance 2025-09-02, 0 rows after 2025-10-01, so
    the old 30-instance freshness control was never executable.
  - **Five arms, `_ARMS` is the registry.** `factory`; `openhands`
    (**mandatory**); `bare` (its one pre-committed repaired run is spent, it reads
    6%, keeping it is an operator decision and it anchors nothing); `claude-5` and
    `claude-4.8` on the **Claude Code CLI on a subscription, never an API or Azure
    route** — verified invocation `claude -p <prompt> --model <id> --max-turns 60
    --output-format stream-json`, `apiKeySource: "none"`, cwd = the instance clone.
    Keep both: the probe came back clean (§1 #8) and the second arm is near-free.
  - **Record the bound, not just the date.** `deepseek-v4-pro` publishes **no**
    cutoff — absent from the model card and from arXiv 2606.19348 (full text
    grepped) — so its only defensible bound is its **release date, 2026-04-24**.
    Azure catalog metadata is *not* a source: Microsoft published Oct 2024 for
    GPT-5.2 whose real cutoff is 2025-08-31 (MS Q&A 5667726). Print `margin_days`
    per row **and** the bound type.
  - **State what a positive margin does not buy.** `created_at` is the *merge-PR*
    date; the issue text, its pre-solution comments (the dataset ships
    `hints_text`) and the repository wholesale all predate it. arXiv 2506.12286
    shows models name the file to edit from repo name + issue text alone far above
    their accuracy on equally-popular non-benchmark repos; arXiv 2410.06992 found
    32.67% of SWE-bench issues carry the solution in the issue or comments and
    31.08% of passing patches pass only because the tests are weak — together
    dropping SWE-agent+GPT-4 from 12.47% to 3.97%. A date filter touches neither.
    The strata are a *measurement*; the date is only a *bound*.
  - **If you want a genuinely post-cutoff public suite, wait or build.** Nebius
    ships ~40–55 validated instances/month with a ~10–12 week publication lag, so
    a 120-row `>2026-05-31` pool should exist around **Oct–Nov 2026**. Minting
    your own (SWE-Bench++ style, arXiv 2512.17419) means owning docker images and
    oracle extraction — multi-week, and `swebench_harness_selftest` is why to
    respect that: the gold-patch control caught three harness bugs that each faked
    a 0% score.
- **Effort:** ~2 weeks. **Cost ~$1,060** all in. Not before C.1–C.3.

---

## Phase D — SacrificeBench

**Rests on P9. Effort 2–3 person-weeks, dominated by human test authoring. Cost
~$400.** **[OPERATOR-PR-ONLY — `bench/**`]**

**The only design in this plan that can measure the real product claim.** Every
public suite scores single-issue patching. Our claim is a chain that turns a
written direction into merged, deployed software over days, and the axes that
would test it — **B** concurrent stories, **D** CI-failure recovery, **E** docs
and context maintenance, **F** dollars per delivered unit over days — are covered
by **nothing published** (P8).

- [ ] **Corpus: the held-out directions.** Verified 2026-08-04 against
      `state/factory.db`: `apps/sacrifice/directions/` holds **76** directions,
      **45 `pm-validated`** and **31 `closed`**. The 45 are the pool; the 31 are
      contaminated (the factory has shipped them). Filter to behaviourally
      testable and **expect 20–25 tasks**.
- [ ] **Oracle: acceptance tests authored by a HUMAN from the direction text
      alone.** Never by the factory, and never by an LLM. An LLM-authored oracle
      reintroduces the self-consistency bias *as the oracle* — ProdCodeBench
      (2604.01527) found ~65% of its retained diffs were AI-authored and flagged
      exactly this. This is the line item that costs the person-weeks, and it is
      the line item that makes the benchmark worth anything.
- [ ] **Mandatory red-baseline control.** The test must **FAIL at the
      pre-direction base SHA** or the task is void. Same principle as A.6, and the
      only cheap protection against a task that was already satisfied.
- [ ] **Reuse `bench/swebench_adapter.py`'s guardrails wholesale** — encrypted
      oracle stored outside the repo, test-edit stripping asserted in code,
      collection-config refusal (`pyproject.toml`, `pytest.ini`, `tox.ini`,
      `setup.cfg`, `noxfile.py`, `conftest.py`, `sitecustomize.py`, `*.pth`),
      `--network none` grading in a fresh `--rm` container, per-node `PASSED`
      grading, flat workspace isolation, `audit.json` with `prediction_sha256`. Do
      not re-derive any of it; four retractions paid for that code.
- [ ] **Uniquely post-cutoff by construction.** The corpus is private, so no
      public instance can postdate it — and no public instance postdates
      `claude-opus-5`'s May-2026 cutoff either, with Nebius supply not reaching
      that until ~Oct–Nov 2026.
- **⚠ It cannot produce a leaderboard-comparable number.** Report it as a paired
  within-corpus comparison — `factory` vs `openhands` vs `claude-5` on the same
  directions — and never as a rate comparable to anything published.
- **⚠ It is the one place axes B/D/E/F can be scored at all**, so design the
  scoring for them up front: stories in flight concurrently, CI failures injected
  and recovered, context docs refreshed, and dollars per delivered unit measured
  over days rather than per instance.
- **Done looks like:** a pre-registration committed before the first run, 20–25
  tasks with human-authored oracles, a red-baseline control pass on every task,
  and a paired three-arm table.
- **Effort:** 2–3 person-weeks. **Cost ~$400** of compute.

---

## Phase E — cheap safety, and the FMS decision

**Effort ~1 day of work plus the FMS soak. Cost ~$0.** These are the items from
the old Phase 3 that survive on their own merits, plus one decision now justified
on cost alone.

### E.1 — Snapshot `state/factory.db` before each tick — ~2 h

- [ ] **Verified gap:** no snapshot mechanism exists anywhere in `factory/**`.
      `state/factory.db.bak-1784662396` is a one-off manual copy. The staging twin
      (`factory/manager/staging.py`) guards **source only**.
- **What:** before the tick's first write, use the sqlite3 **backup API** (not
  `shutil.copy` — the manager daemon writes concurrently) into
  `state/db-snapshots/factory-<ISO>.db`, keeping the last 10.
- **Why:** a prior session lost a whole run to 6 poisoned invalid-enum `closed`
  rows that failed every tick, with no clean rollback point.
- **Files:** `factory/chain/orchestrator.py` (tick entry) or the `factory tick`
  wrapper in `factory/cli.py`. Confirm `state/**` gitignore coverage; don't
  assume.

### E.2 — Ratchet the package-wide `mypy` count, per file — ~1 h

- [ ] **Verified:** `.github/workflows/test.yml:145-154` runs two mypy steps.
      `mypy factory/chain/gates/` is a real zero-tolerance gate and is clean —
      **leave it alone**. The package-wide step pipes to `|| true`, counts with
      `grep -c "error:"` and emits a `::warning::`. Advisory, no baseline.
- [ ] **The drift is larger than the docs claim.** `test.yml:143-144` says "~85
      pre-existing findings"; measured 2026-08-01: **99 errors in 29 files**.
- **What:** commit `mypy-baseline.json` mapping **file → error count** (not a
  scalar — a scalar lets you add three errors in one file and delete three in
  another and stay green). CI fails when any file exceeds its entry. Count from
  `--output json` or the `Found N errors` line, **not** `grep -c "error:"`, which
  counts substring matches and is inflated by mypy's own excerpts.
- **Ship standalone.** It blocks unrelated PRs the moment it lands. Any lockfile
  bump must re-baseline in the same PR. Also fix `CLAUDE.md` to name the baseline
  file instead of "compare against `origin/main`".

### E.3 — Make `software-factory-copy` private — 5 min **[OPERATOR ACTION]**

- [ ] **Verified:** `gh repo view xvanov/software-factory-copy --json visibility`
      → `PUBLIC`. It is the staging twin (`factory/manager/staging.py:72`) and
      receives **every candidate self-edit diff** on a staging branch before
      promotion — including the 3 of 20 the gate later rejected.
- **Command:** `gh repo edit xvanov/software-factory-copy --visibility private
  --accept-visibility-change-consequences`
- **Then run one staging validation end to end.** The flow clones over SSH, so a
  private repo is fine provided the manager's identity has access — and
  `staging.py` failing closed would silently block every self-edit.

### E.4 — Isolate gate exceptions, and make a scan error GLOBALLY blocking — ~2 h

- [ ] **Verified:** `factory/chain/gates/evaluator.py:188-197` calls
      `mod.evaluate(...)` with no `try`, while its docstring (`:175-176`) promises
      "failure of one gate does not short-circuit the others" — true for a
      *returned* failure, false for a *raise*.
- [ ] **What actually happens today — checked, do not re-diagnose.** Both
      orchestrator call sites catch (`orchestrator.py:2591`, `:3117`), so the tick
      does not crash and the merge is not waved through; `summary.errors`
      non-empty makes `factory tick` exit 1. It is fail-safe by accident. The real
      costs are that one raise aborts merge evaluation for **every remaining
      fixture** on that tick, and `factory/cli.py:2480` (`factory auto-merge`) is
      unwrapped. **Zero gate raises have occurred in production** (441 ticks at
      `errors=0`).
- **⚠ The naive fix is a fail-OPEN regression.** `missing_labels` is computed only
  over `required_gate_labels(...)` (`auto_merge.py:948-954`), so a raise in a
  **non-required** gate that becomes a non-required blocking `GateResult` is
  filtered out and **the merge proceeds** — strictly weaker than today. So:
  `scan_error` results are **globally blocking**, evaluated alongside
  `missing_labels` and **not** filtered through `required_gate_labels`; append to
  `summary.errors` so the tick still exits non-zero; wrap `cli.py:2480`. Adopt the
  precedence rule while you are there: **can't-run > found-something > clean**.
- **This is robustness, not a closed failure class.** Sell it as such.

### E.5 — Bring the units up, watch one cycle, and decide the FMS on cost — **promoted**

- [ ] **Start:** `uv run factory on`, then confirm
      `systemctl --user status factory-manager.service factory-tick@sacrifice.timer`.
      Check `Result=` and `errors=` **across two runs** — "services up" is not
      "sustains".
- [ ] **Watch one full L1→L4 cycle** (L1 fires every 60 s), then re-read
      `state/.manager_apply_history.json` and count entries with a non-null
      `pr_number`. Baseline: **163 attempts, 0 PRs, newest 20260723**.
- [ ] **Decision rule, pre-committed:** if after one full cycle *and* one genuine
      concern reaching L4 the yield is still **0 PRs**, delete the L4 tier. Keep
      `factory/manager/recovery.py` (the auto-fix layer for known operational
      faults — that one demonstrably works) and keep `fms_yield.py` as the
      detector. **[OPERATOR-PR-ONLY]**
- **The cost case, which is now the strongest argument in this phase.** The
  manager has consumed **$1,028.58 = 52.0% of all-time LLM spend** ($972.23 of it
  `manager_watcher` alone, 44,127 runs at a 60 s cadence) for **zero shipped
  PRs**. In July it was $371.60 of $588.78 — deleting it takes per-story cost from
  **$7.85 to $2.90**. And 165 L3 proposals collapse to **37 distinct concern
  classes (78% redundant)** with 107 carrying `escalate_to_human: true`: the tier
  mostly re-reports the same handful of problems to a human. Set against §1's
  finding that orchestration is not what produces value here, a self-improvement
  tier that has never shipped is the easiest $1,000 in the repo.
- **Do not delete before measuring.** The wiring bugs were fixed in PR #113
  (2026-07-24) and the newest apply attempt predates parts of that work, so the
  tier has arguably never run in its fixed form. One honest cycle first.
- **This step is also a prerequisite for Phase A's replay corpus** —
  `prompt_bodies.ndjson` has no production rows while the units are stopped.
- **Effort:** ~half a day of watching, plus the deletion PR if the rule trips.

### E.6 — Extend the persona contract-collision validator — ~2 h

- [ ] **Verified:** `factory/personas/validator.py:59-62` `_ENUM_CONTRACTS` covers
      only `scope` and `chain_kind`. The check already runs in CI
      (`tests/test_persona_loader.py:60`, `:296` call `validate_all`).
- **Why this and not a persona prompt audit:** the story-14 non-convergence was a
  prompt *example literal* colliding with a live contract value.
  `_check_contract_collisions` catches that mechanically. See "Rejected" #7 for
  why the personas are not the bloat they look like.
- **What:** extend `_ENUM_CONTRACTS` to every field whose values are enumerated in
  code.

### Deferred — named, costed, and not scheduled

Each of these was in the old plan and does not survive the new ordering. Listed so
nobody re-proposes them without new evidence.

- **Patch-apply fuzzing (old 3.1 — port Hermes `fuzzy_match.py`).** **Payoff is 21
  historical failures**, not 179: of the improver's 179 apply failures, 158 were
  `dirty_working_tree`, already fixed (Corrections #10). Fuzzy matching addresses
  only 16 `corrupt patch` + 5 `patch failed`. If it is ever revisited, try
  `git apply -3` on both call sites first
  (`factory/chain/factory_improver_apply.py:490`, `factory/manager/apply.py:958`)
  and re-measure before porting 967 lines. **[OPERATOR-PR-ONLY]** — both halves.
- **Lint/typecheck before review (old 3.2).** `_autoformat_changed_py_before_pr`
  (`factory/chain/handlers.py:3592`) is format-only; there is no full `ruff check`
  gate, no `mypy` step and no lint gate in `factory/chain/gates/`. Deferred because
  it buys style, not correctness, and Phase A/B may move the handoff it hooks
  into. **While deferring it, do not forget the four write-never columns it was
  going to use** — `stories.lint_passed`, `format_passed`, `types_passed`,
  `coverage_passed` have zero references anywhere in `factory/**`. Drop them or
  wire them; do not leave them next to the `smoke_passed` bug #195 removed.
- **Typed block kinds + recurrence counter reset only on merge (old 3.3).** Hermes
  `kanban_db.py:104-134` / `:5847-5856` is a good design — the unblock path
  deliberately does not reset `block_recurrences`, because "resetting the
  recurrence counter on unblock is exactly the amnesia that let the loop run
  unbounded" — and the motivating failure (`blocked_ci_unresolved` terminal with
  no path back) is real. Deferred because no story is currently blocked and A.3
  adds the one new block kind the evidence demands. Revisit if blocked stories
  reappear. **[OPERATOR-PR-ONLY]** for the `recovery.py` half.
- **Wire or drop `gates_failed_json` (old 3.9).** #195 added
  `MergeAction.gates_failed`, the column (`auto_merge.py:126`, `:200`, `:234`) and
  the `merge_gates_failed` story event (`:933`) — with **one writer and zero
  readers**. The diagnosis reaches a human via `factory trace` and nothing else.
  Deferred, not resolved: pick "feed it into the dev re-dispatch findings path
  (and cap that loop)" or "drop the column" the next time this area is open.
- **GEPA on the reviewer (old 5.1).** ~150 rollouts ≈ $6, corpus = 118 merged PRs
  plus review history (`stories.reviewer_history_json`, the `review_events` table,
  `state/events/chain_steps.ndjson`). Deferred twice over: it is blocked on prompt
  bodies that have **zero production rows**, and it optimizes a critic that A.7
  may demote and B.3 may repurpose. Do not tune a component you may delete.
- **Merge gates → GitHub Actions + Projects v2 (old 5.2).** Still worth
  *evaluating* — moving gates to required GH checks would make `proxy ≠ real`
  structurally impossible for the merge decision, and `CLAUDE.md` already declares
  GitHub the only source of truth for merge reality. Cost: loses the local dry-run
  fast path and couples every gate to Actions minutes. Write the trade-off up
  before building anything.

---

## Rejected — LifeOS-derived proposals, adversarially reviewed 2026-08-02

A survey of `danielmiessler/LifeOS` (cloned at `/home/k/LifeOS`) produced 11
candidate additions. Three adversarial reviews rejected **nine**. Recorded so
they are not re-proposed. Each entry is the refutation, not the proposal.

1. **`evidence-corroborated` gate** — classify the dev's completion claim,
   corroborate it against the ledger. There is no prose claim in the merge path
   to classify: `runner.py:2107-2108` runs pytest and scans git *itself*, and
   `RunResult.test_run_passed` is the factory's own observation, never the
   model's word. `gates/tests_green.py:69-83` already re-derives the truth at
   merge time and its docstring states that as the design intent. The
   corroborating ledger does not exist — there is **no `sandbox_run` table**,
   `prompt_bodies.ndjson` has **zero production rows** (#193 merged 2026-08-01;
   units stopped since ~07-30), `chain_steps.ndjson` still has zero `retried` /
   `review_cycle` rows, and `runs` carries no diff, file list, or exit code. The
   proposed 118-PR replay corpus is fiction (and the count is 138).
2. **Gate-reason lint** — require a problem *and* a remedy in every failing
   `reason`. Roughly 15 strings across 6 files; "names a remedy" is not
   statically decidable, so any implementation is a keyword heuristic — a proxy
   gate, in the repo whose #1 failure pattern is `proxy ≠ real`. The loop it
   claims to prevent does not exist: nothing reads the string (see the deferred
   `gates_failed_json` item).
3. **"L4 falsify, not L4 apply"** — have the manager emit a red replay fixture
   instead of a diff. The premise is false. Of 163 apply attempts only **58 ever
   carried a patch**, and **53 of those died on `dirty_working_tree`**, an
   environment bug fixed 2026-07-24 — `apply.py:864-869` records exactly this.
   Not one attempt was ever rejected for diff quality; zero reached review. The
   107 escalations are **information** failures (84 are "source bundle
   insufficient"), and a model that cannot see `tick()` cannot write a fixture
   for it either. Run E.5 instead.
4. **Detector graduation lifecycle** — log-only → counterfactual corpus →
   blocking. Manager detectors are already advisory by construction
   (`factory/manager/detectors/__init__.py:1-6`: "Detectors never make
   decisions"); the only blocking path is `halt.py`, which is L3, not a
   detector. The motivating episode (SM-truncation) was **test pollution** — a
   counterfactual corpus built from those same contaminated streams scores
   FP = 0 and passes the very case it was designed to catch. And no adjudicator
   is specified for up to 190 observations per detector.
5. **Turn on the ablation gate** — superseded by A.5. The gate is broken four
   ways; the flag flip is not the adoption path, and flipping it as an experiment
   would break every merge.
6. **Property tests in the dev persona** — already ships in a better seam.
   `hypothesis>=6` is a dev dependency, `acceptance_author.md:52-72` authors
   Hypothesis property tests from EARS criteria, and `acceptance.py:101-194`
   injects that automatically. The cited evidence does not support it either:
   `right_place_wrong_fix` is defined at `swebench_adapter.py:1349` as **file
   overlap only**, and those failures read as unstated-convention failures —
   which #201 already addressed. **Amended 2026-08-04:** the better seam this
   refutation points at has never been switched on — see A.1.
7. **"Bitter Pill" audit of the 22 personas** — the trim already happened.
   `27008931` (2026-06-11) cut `dev.md` 177→108 and `reviewer.md` 158→102,
   citing the same story-14 incident this proposal cites. Genuinely cuttable
   today is ~25 lines (`pm.md:242-251`, `sm.md:127-135`, two role preambles) —
   5–8%, not bloat — while several lines that *look* cuttable are measured
   load-bearing (`dev.md:54-64`, 2/2 vs 0/2). The "no regression" guard is
   statistically fake: on a 5-instance precision denominator it fires only at
   0/5, which occurs **32.8%** of the time when nothing changed.
8. **Per-persona A/B with a no-persona arm** — the SWE-bench harness runs
   `allowed = {"dev", "review"}` (`swebench_adapter.py:2416`) and seeds the story
   at `SM_DONE`, so **20 of 22 personas never execute**. Of the two reachable,
   the reviewer had `reviewer_cycles = 0` on 5/5 — it modified nothing, so
   ablating it was a guaranteed null result at full cost. `run_bare` is a
   separate agent, not the factory-minus-a-persona. Cost at a detectable n:
   **$673 at n=33, $2,591 at n=127**. **Amended 2026-08-04:** the reviewer is no
   longer inert (§1 #6), and the `openhands` arm now does the ablation this
   proposal wanted, correctly and for $18 — see A.7 and Phase B.
9. **AC-ID stability + falsifier test** — already shipped. `sm.md:46-57`
   mandates `AC<n>.<m>` EARS IDs and 93 of the 139 stories with an
   `sm_result_json` carry them; `acceptance_author.md:37-38` names generated
   tests off those IDs. The guarded failure has never occurred (0 hits across
   326 review/dev blobs). The measurement has no data source: story markdown has
   been gitignored since #181 and the DB stores one `sm_result_json`, not a
   revision series. The falsifier test already exists in triplicate
   (`pm.md:231-236`, `sm.md:55-57`, `acceptance_author.md:39-42`).

**Adopted from the same survey:** E.2 (mypy ratchet), E.4 (gate exception
isolation, in inverted form), E.6 (validator extension). **1.5, A.5 and the
`gates_failed_json` item were found *by* the review, not proposed to it.**

### Rejected 2026-08-04, from the research synthesis this plan was rewritten around

10. **"Make test files read-only to the dev", taken literally.** P7's
    ImpossibleBench ablation cannot be applied as written here, because there is
    **no separate test author**: `factory/personas/dev.md:38` — "You own code AND
    its tests — there is no separate test author" — is the Loop-4 design, and
    `tests/test_dev_no_test_modification.py:111`
    (`test_dev_modifying_test_file_is_allowed`) asserts the permission. Freezing
    the dev out of test files would invert the design that shipped 91 sacrifice
    stories. **What survives is A.1**: an independently authored oracle the dev
    never sees, which is the stronger form of the same countermeasure and is
    already built. *(Note for the next reader: that test module's docstring still
    describes the pre-Loop-4 prohibition and is stale — the tests below it assert
    the opposite.)*
11. **Raising the dev/review caps to buy convergence.** P5(b) measures more
    submissions-with-feedback as *more* gaming, and §1 #6 shows our own cycles
    rising with no change in resolve rate. See A.8.
12. **A second reviewer, a judge panel, or any additional critic stage.** P5(c):
    complex agentic judge systems scored α 37–49.5 against 62.5–63.0 for a single
    simple prompt, and P1 finds no sequential critic anywhere in the SWE-bench
    Verified top 20. More judge is less validity.

---

## Corrections to the briefing this plan was written from

Every claim in the original 2026-08-01 briefing was re-checked. Nine needed
correcting; the rest verified exactly. Corrections 14–19 were added 2026-08-04,
when the plan was rewritten around the research synthesis.

1. **Manager spend share — 52.0%, and the in-repo docstring says 53%.**
   `factory/manager/detectors/fms_yield.py:12` reads
   "$1,028 (53% of all factory LLM spend)". Measured: $1,028.58 / $1,976.91 =
   **52.0%**. Not a bug — the denominator grew.

2. **L3 `escalate_to_human` — 107 is right, but only in the proposals.**
   107 of the 165 proposal files carry `escalate_to_human: true`. The
   *classification* field in `state/.manager_apply_history.json` records
   **105**. Two proposals set the flag but never reached L4 classification.

3. **"37 distinct concern classes" is normalization-dependent.** Raw distinct
   `concern_title` values: **48**. Normalizing story numbers only: **40**.
   Normalizing story numbers *and* dropping
   repeat/repeated/continuation/continued/persists/again/still: **37 (78%
   redundant)**. State the normalization when you quote it.

4. **`factory audit` estimated share is window-dependent.** Default 7-day
   window: **55.4%** ($25.81). `--days 60`: **33.9%** ($515.90).

5. **"`stories.dev_retries` shows 41" — 41 is a story count, not a retry
   count.** 41 stories have `dev_retries > 0`; total retries all-time = **71**.

6. **`smoke_green.py` line ref off by three.** The `details={"exit_code",
   "output_tail"}` dict is at **`:55`** (the `GateResult` spans `:51-56`).

7. **`bench/bench.py` SM_DONE seed is at `:267`**, inside the `StoryRecord`
   block spanning `:260-270`.

8. **Claude-arm usage limits: 4 of 13, on a subscription — not 6 of 12, not org
   billing.** `bench/CAMPAIGN-2026-07-17.md:33`, `:51`. `summary.md` holds 20
   rows (12 Claude attempts, 8 factory).

9. **`clean()` destroyed the raw artifacts for *all 20* reported runs, not 19 of
   20.** `bench/runs/` holds exactly one `result.json` (`t3_csrf/factory-2`) and
   it is **not** among the 20 rows in `bench/results/summary.md`.

10. **The 158 `dirty_working_tree` failures are already fixed — the patch-apply
    payoff is 21, not 179.** Both apply paths were made path-scoped 2026-07-24
    (`factory/manager/apply.py:882-897`,
    `factory/chain/factory_improver_apply.py:418-436`). Try `git apply -3` first.

11. **The retry caps are 6, not 3.** RESOLVED 2026-08-01 (#196):
    `_MAX_DEV_RETRIES = 3`, `_MAX_REVIEW_CYCLES = 3`, inner guards
    `_MAX_DEV_SAME_SIGNATURE` / `_MAX_REVIEW_STUCK` 3 → **2** so early escalation
    still fires before the hard cap. Keep that gap.

12. **Phase 0.6's assertion fired on the then-current `routes.yaml`.** RESOLVED
    2026-08-01 (#196): `reviewer` moved to `azure/gpt-5.4` in BOTH blocks (the
    `direct` block had the same collision, which the original note missed). The
    `test_implementer` overlap remains, as a warning.

13. **Four more write-never columns exist alongside `smoke_passed`.**
    `stories.lint_passed`, `format_passed`, `types_passed`, `coverage_passed`
    have **zero references anywhere in `factory/**`**. Now tracked in the
    deferred lint/typecheck item.

14. **The `openhands` number depends on which `report` run you read, and any doc
    quoting it must say which.** The archive committed to `origin/main`
    (`2026-08-04T04-18-05.349995Z`) reports **7/16 = 44%**, `$15.37`, McNemar
    p=0.625, with 3 rows lost to 429s. A later, **uncommitted** archive
    (`2026-08-04T23-19-24.998844Z`, present in the live tree) re-ran those three
    rows as `attempt: 2` and reports **10/19 = 53%**, `$18.20`, p=0.375. §1 uses
    the later one and labels it. Two consequences for numbers already in circulation:
    the cost ratio is **2.8×** ($5.13 / $1.82), not 2.3×; and the fresh-input
    token ratio is **1.8×** (14.3 M / 7.8 M), not 2.1×. `CLAUDE.md`, `README.md`,
    `STATUS.md`, `bench/swebench/README.md` and
    `bench/swebench/PRE-REGISTRATION-1.6.md`'s outcome section all still carry the
    44% / p=0.625 pair. They are **consistent with the committed archive**, so they
    are not wrong today — update them in the same PR that commits the later
    archive, not before, or the docs will cite a number the tree cannot re-derive.
    (`SOTA-RESEARCH-2026-07.md` carries both, with the provenance stated.)

15. **The `openhands − bare` tooling result is stronger than previously
    published, not weaker.** The committed report has the pair at n=15,
    `bare vs openhands` 0 / 6, p=0.031; the later report has n=18, 0 / 9,
    **p=0.004**. Either way it is the only significant result among the three
    DeepSeek arms.

16. **"Make test files read-only to the dev" contradicts the shipped design.**
    The dev owns its tests (`factory/personas/dev.md:38`), and
    `tests/test_dev_no_test_modification.py:111` asserts that modifying a test
    file is *allowed*. The countermeasure that does apply is the independent
    acceptance oracle — see A.1 and Rejected #10. **That module's docstring is
    stale**: it still describes a prohibition the tests below it contradict.

17. **The independence layer the research recommends is already built here and
    has never run.** `factory/chain/acceptance.py` authors an oracle from the
    spec only, before the dev, outside the dev's worktree; it is enforced by
    `gates/acceptance_verified.py` and becomes merge-required on opt-in. Measured
    2026-08-04: `gates.acceptance_oracle` is set in **no** app config
    (`factory/app_config.py:113` defaults it False), and in `state/factory.db`
    **0 of 165 stories** carry `acceptance_expected` or `acceptance_test_ref`.
    The 37% in §1 was therefore measured without it twice over — the flag is off
    in production *and* the bench runs only `{"dev", "review"}` from `SM_DONE`
    (`bench/swebench_adapter.py:2404`, `:2416`).

18. **Iteration horizon is not our deficit.** The synthesis notes "OpenHands runs
    500 iterations; mini 250 steps/$3"; `sandbox_run`'s default is already
    `max_iterations = 600` (`factory/runner.py:1643`). The deficit is that the
    horizon is split across handler invocations — at `_MAX_DEV_RETRIES = 3` the
    dev inner loop gets **two** sandbox attempts per invocation. *(Minor: the
    comment at `factory/runner.py:1604` still says "dev keeps the default
    200" while the signature and the `PERSONA_ITERATION_CAPS` comment both say
    600. Fix in passing.)*

19. **The `SOTA-RESEARCH-2026-07.md` line reference in the old 3.1 was stale, and
    the claim behind it is now downgraded.** The "69.1% → <1.5% apply failures
    from changing diff transport" claim was never at `:164`; it now sits at
    **`SOTA-RESEARCH-2026-07.md:225`**, struck through, because the citation it
    rests on (`Claw-SWE-Bench`, arXiv 2606.12344) **could not be verified to
    exist**. The design intuition — collect file state, not model-emitted unified
    diffs — stands; the number does not. Do not lean on it.

Verified exactly as stated, no correction needed: the 122/118/24 chain counts;
17-validated/3-rejected staging; 1 open issue / 0 open PRs / 0 blocked; L4's
163 attempts / 0 `pr_number` / newest `20260723`; the $1,028 figure; reviewer
convergence (0 stories at 6+ in 14 days, max 5, 101 of 122 at zero, 11 all-time
at 6–7); dev retries `{0:86, 1:27, 2:5, 6:4}`; 196 improver proposals → 1 landed
commit `6bd463a3`; 179 apply_failed split 158/16/5; Azure $1.93/$3.83 verified
and $0.161 cache-read estimated; `db_path` threading fixed; July $588.78 / 75 =
$7.85 and $217.18 / 75 = $2.90; the twin at `staging.py:72` is a real
run-the-clone canary and is **PUBLIC**; **45 `pm-validated` and 31 `closed`
sacrifice directions of 76** (re-verified against `state/factory.db`
2026-08-04); Hermes `fuzzy_match.py` = 967 lines, MIT, `re`/`typing`/`difflib`
only; Hermes `kanban_db.py:104-134` and `:5847-5856`; `bench/**` and
`factory/manager/**` forbidden to self-edit.
