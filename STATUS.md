# STATUS — measured 2026-08-04, extended 2026-08-05 (Phase 0–1.6 landed; A.1, A.5, A.6 and B.1 Phase 1a landed)

Point-in-time facts. Verify before you rely on them. The commands are in
`CLAUDE.md`. The work queue is `PLAN.md`.

All systemd units are deliberately **stopped**. Run `factory on` to start.

**Read this first.** The clean five-arm benchmark is in. **The chain shows no
measurable lift over a single OpenHands agent on the same model** — 37% vs 53%,
McNemar exact p=0.375 — and it costs 2.8× per resolved instance to get there.
What produces the lift is *tooling*, not orchestration. Details, CIs and
caveats: "The benchmark" below. Nothing in this file supports "the chain is
proven".

**And then read the reviewer ablation.** Measured 2026-08-05, a sixth arm on the
same 19 instances: **removing the reviewer round-trip cost nothing measurable and
saved 29%** — `solo-noreview` 9/18 = 50% at $2.83 per resolved against the chain's
7/19 = 37% at $5.13. The cost win is real; the quality claim is **not** established.
Section: "The reviewer ablation" below, and read its limits with the number.

> **Provenance, read before quoting a number.** Two `report` runs exist for this
> one sweep and they disagree on one arm.
> `results-archive/2026-08-04T04-18-05.349995Z/` reports `openhands`
> **7/16 = 44%**, `$15.37`, McNemar p=0.625, cost ratio **2.3×** — three rows
> were lost to Azure 429s and excluded as invalid. The later
> `results-archive/2026-08-04T23-19-24.998844Z/` re-ran those three rows as
> `attempt: 2` and reports `openhands` **10/19 = 53%**, `$18.20`, p=0.375, cost
> ratio **2.8×**. Both archives are committed to `origin/main` as of `664bcd7d`
> (PR #232), which also amended `PRE-REGISTRATION-1.6.md` to close the
> `attempt > 1` protocol question.
>
> **This file uses the later report**, matching `PLAN.md` §1, `README.md` and the
> committed `bench/swebench/results.md` — which re-derives from the later archive
> byte-for-byte, so that is the archive `report --check` must be pointed at.
> **The conclusion is the same under either report**: both put the chain below
> one agent on the same model, both at p > 0.3, and the cost ratio moves further
> against the chain in the later one. At MDE ≈ ±38 pp this is **"no measurable
> lift", not "the chain hurts"** — nothing here measured harm.

## What works

| Capability | Evidence |
|---|---|
| Loop 1 — builds an app | 91 sacrifice stories deployed |
| Loop 2 — builds itself | 24 factory stories deployed in the last 14 days |
| PR pipeline | 122 stories opened a PR; 118 merged |
| Staging twin | 17 self-edits validated, **3 fatal self-edits rejected** |
| Review convergence | 0 stories hit the cycle cap in 14 days (max 5, one story) |
| CI-failure recovery | Real CI log is fed back to dev as a structured finding. Capped at 3 |
| GitHub loop | 1 open issue, 0 open PRs, 0 blocked stories |
| Spend control | $300/day cap (`caps.daily_spend_usd`), hourly cap, per-story budget |
| Test suite | 2,368 tests, ~5 min |
| SWE-bench measurement pipeline | Five arms, one sweep, no re-rolls, pre-registered tables. Oracle is sha256-pinned upstream `FAIL_TO_PASS`/`PASS_TO_PASS`; test-edit stripping is asserted in code on **every** arm and stripped 96 test files across the 95 published rows; grading is a fresh `--rm` container with `--network none`; manifest frozen and committed *before* the first run; gold-patch control 19/20. `report --check` re-derives the published table byte-for-byte from the committed archive and exits non-zero on drift |
| Integrity gate has teeth | It rejected a row in this very sweep: `bare` on `hiero-ledger__hiero-sdk-python-1914_interface` ran `curl -s https://raw.githubusercontent.com/…/account_info.py` — the upstream source of the exact file under test. That row is published as **invalid and excluded**, not re-rolled |
| Claude-arm provenance | Really executed locally: `claude` CLI 2.1.220, `--model` pinned per arm (`claude-opus-5`, `claude-opus-4-8`), `--depth 1` clone (1 commit, no future refs), MCP disabled, WebFetch/WebSearch removed and proved absent from the CLI's own init event, and **0 network-retrieval actions** in either arm's 38 transcripts |

Do not "fix" anything in this table without a measurement that shows it broke.

## What does not work

| Problem | Evidence | Fix |
|---|---|---|
| **The chain shows no measurable lift over a single agent** | Measured 2026-08-04, n=19, k=1: `factory` 7/19 = 37% [16%, 62%] vs `openhands` 10/19 = 53% [29%, 76%] on the same weights, same prompt, same tools. Paired McNemar exact **p=0.375** (n=19, only-A/only-B = 1/4). Directionally −16 pp, which is well inside the ±38 pp MDE — this is "no measurable lift", **not** "the chain hurts". The earlier archive reports 44% / p=0.625; same conclusion, see the provenance note at the top | `PLAN.md` Phase A (make the verdict mean something) then Phase C (measure where the claim can be expressed) |
| **The chain costs 2.8× per resolved instance for that non-gain** | `factory` $35.94 / 7 = **$5.13 per resolved**; `openhands` $18.20 / 10 = **$1.82**. Same price-table basis, so directly comparable. The factory also burns 1.8× the fresh input tokens (14.3 M vs 7.8 M). On the earlier archive the ratio is 2.3× ($2.20 per resolved) — it moves *against* the chain in the later one | `PLAN.md` Phase B + E.5 |
| The chain's own green verdict is barely better than a coin flip | Chain-verdict precision 6/15 = **40%** [16%, 68%] — the chain said green and the hidden oracle failed it 9 times out of 15. Recall 6/7 = 86% [42%, 100%]. One row went green on a **zero-byte** production patch (`harumiweb__exstruct-113`) | `PLAN.md` Phase A |
| FMS **L4 apply** tier is dead | 163 attempts, 0 PRs, nothing since 2026-07-23 | `PLAN.md` E.5 |
| Manager cost is unjustified | ~52% of all LLM spend | `PLAN.md` E.5 |
| `factory_improver` does not land | 196 proposals, 1 commit. 179 apply failures — but 158 were `dirty_working_tree`, already fixed, so the real payoff is 21 | `PLAN.md` Phase E, "Deferred" |
| L3 re-diagnoses known faults | 165 proposals span 37 distinct classes | `PLAN.md` E.5 |
| The old (`bench.py`) benchmark is retracted | Tasks t1–t6 are shipped, so the pool is contaminated; the 20 reported rows still have no raw artifacts. Its July campaign graded the factory on tests the factory wrote, so it never measured correctness; its numbers are **withdrawn** — see `bench/CAMPAIGN-2026-07-17.md`'s header | `PLAN.md` Phase C |
| Merge-gate precision is unknown | The SWE-bench harness runs dev (+review) only, so what is measured is **chain-verdict** precision — 6/15 = 40% for `factory`, 7/15 = 47% for `solo-noreview` — not the merge gate. The acceptance oracle is now **authored** in the benchmark's factory arm (#238), but its merge gate is enforced in **no** arm (`gate_enforced: false`) and the flag is off in production | `PLAN.md` A.1 |
| The acceptance oracle's green can still be forged **in-process** | Three lines of production code reassigning pytest's test-runner function to a no-op produce a genuine-looking red→green. No file rollback closes it; it needs an out-of-process behavioural oracle. Pinned as an `xfail(strict=True)` whose stated reason is that it is why the flag stays off. Same class: a HEAD dependency registering a pytest plugin entry point via a local-path dependency | `PLAN.md` A.1 — this is why `gates.acceptance_oracle` is off |
| A 4-worker sweep silently loses runs to provider 429s | `openhands` lost 3 of 19 rows to Azure `DeepSeek-V4-Pro` `RateLimitError`. There is **no retry on a provider 429** and the lost row records `cost_usd: 0.0`, so it reads as free rather than as missing | `PLAN.md` 1.6 G |
| The sweep's own aggregate counters disagree with their own rows | `sweep-<arm>.json` reports `resolved` / `audited_valid` / `audit_failed` from in-flight state (pre-#227 detector, pre-grade), so e.g. `sweep-factory.json` says `resolved: 2, audit_failed: 13` while its own `results` rows say 7 resolved and the archived `audit.json` files say 19 ok / 0 invalid. Only `results.md` and the archive are authoritative | `PLAN.md` 1.6 G |
| n=19, k=1 cannot resolve the comparison that matters | MDE ≈ **±38 pp**. `factory` − `openhands` is −16 pp on the later archive, −7 pp on the earlier one — both far inside it. Every arm's CI is ~45 pp wide | `PLAN.md` C.4 — k≥3, larger n, and read why it is demoted |
| Absolute rates on the DeepSeek arms are not contamination-clean | `deepseek-v4-pro` publishes **no** cutoff, so its only defensible bound is its release date 2026-04-24, and **15 of 19** instances sit inside it. (For the Claude arms the question is now *answered* — see conclusion 5 below.) The freshest public SWE-rebench instance anywhere is 2026-05-12 | `PLAN.md` C.4 |
| `SWE-bench-Live` is abandoned | Last modified 2025-09-18, newest instance 2025-09-02, 0 rows after 2025-10-01. The old 30-instance control was not executable | `PLAN.md` C.4 — replaced by a two-stratum design |
| State has no backup | The twin guards source only | `PLAN.md` E.1 |

## The benchmark — measured 2026-08-04, five arms, n=19

Suite: SWE-rebench (Nebius), pinned manifest `923aef05add32124` — 20
post-2026-01-01 python instances, **19 with a working oracle**. One sweep, five
arms, **n=19, k=1, no re-rolls**. Tables and decision rules were fixed in
`bench/swebench/PRE-REGISTRATION-1.6.md` *before* the data existed.

Evidence: `bench/swebench/results.md`, backed row-for-row by
`bench/swebench/results-archive/2026-08-04T23-19-24.998844Z/`. Re-derive it:

```bash
uv run python bench/swebench_adapter.py report \
  --from-archive bench/swebench/results-archive/2026-08-04T23-19-24.998844Z --check
```

That archive — not the earlier `04-18-05` one — is the one the committed
`results.md` reproduces; pointed at `04-18-05`, `--check` correctly exits
non-zero on drift.

**An arm is a (harness, model set) pair.** Never quote half of one.

| arm | harness | model(s) the LEDGER says ran | resolved / valid | rate | 95% CI | $ | $ / resolved |
|---|---|---|---:|---:|---|---:|---:|
| claude-5 | Claude Code CLI 2.1.220 | `claude-opus-5` + the CLI's own `claude-haiku-4-5` classifier | 15/19 | **79%** | [54%, 94%] | 34.36 † | 2.29 † |
| claude-4.8 | the SAME CLI, same flags | `claude-opus-4-8` + haiku-4-5 | 14/19 | **74%** | [49%, 91%] | 23.56 † | 1.68 † |
| openhands | OpenHands single agent, **no chain** | `azure/deepseek-v4-pro` (19 calls) | 10/19 | **53%** | [29%, 76%] | 18.20 | **1.82** |
| factory | software-factory chain on OpenHands | `azure/deepseek-v4-pro` (33 calls) + `azure/gpt-5.3-codex` (6) + `azure/gpt-5.4` (31) | 7/19 | **37%** | [16%, 62%] | 35.94 | **5.13** |
| bare | hand-rolled text loop, **no tool calls** | `azure/deepseek-v4-pro` (727 calls) | 1/18 | **6%** | [0%, 27%] | 7.94 | 7.94 |

† The Claude dollars are the CLI's own report against a **subscription**; the
Azure dollars are a price-table estimate over measured tokens. The two are
different accounting bases — never sum them, and treat the cross-family
`$ / resolved` comparison as indicative only. The `factory` vs `openhands`
comparison is on one basis and is exact.

Paired McNemar exact, over instances where **both** arms have an audited-valid
row:

| comparison | what it isolates | paired n | only-A / only-B | p |
|---|---|---:|---:|---:|
| **factory vs openhands** | **the chain** | 19 | 1 / 4 | **0.375** |
| **bare vs openhands** | **the tooling** | 18 | 0 / 9 | **0.004** |
| bare vs factory | chain + tooling, entangled | 18 | 1 / 7 | 0.070 |
| claude-5 vs factory | nothing attributable — reference only | 19 | 8 / 0 | **0.008** |
| claude-4.8 vs factory | nothing attributable — reference only | 19 | 8 / 1 | 0.039 |
| **claude-4.8 vs claude-5** | **contamination** (same harness, older cutoff) | 19 | 1 / 2 | **1.000** |

Pair order is `results.md`'s, not rearranged: **A is the arm named first**, so
`bare vs openhands` at 0 / 9 means bare resolved nothing openhands missed and
openhands resolved nine bare missed. Never reorder a pair's name without swapping
its two counts — an earlier revision of this table renamed one pair and kept its
counts, which inverted its meaning.

### What this measures

1. **The chain shows no measurable lift.** 37% vs 53%, p=0.375, on the same
   weights, the same prompt and the same tools — the only pair here that holds
   the model fixed and varies the harness. `PRE-REGISTRATION-1.6.md` Rule 1
   pre-committed the wording for exactly this outcome, so it is published in
   exactly those words: **our lift comes from using a competent agent loop, not
   from the chain.** On the earlier archive the same pair is 37% vs 44%, p=0.625
   — the conclusion does not turn on which report you read.
2. **What produces the lift is TOOLING, not orchestration.** `openhands` 53% vs
   `bare` 6%, p=0.004 — the one significant result among the DeepSeek arms. The
   retracted "+58 pp scaffold lift" was measuring the difference between having
   a usable editor and tool-calling API and not having one. Separating that from
   the chain is precisely what the missing `openhands` arm was needed for.
3. **Cost makes it worse, not better.** $5.13 per resolved instance for the
   chain against $1.82 for a single agent — **2.8× for no measurable gain**, on
   the same price-table basis, plus 1.8× the fresh input tokens (14.3 M vs
   7.8 M) and 2.6× the median wall clock (995 s vs 385 s). The earlier archive
   puts this at 2.3× ($2.20 per resolved); the later one is worse for the chain.
4. **Claude Code is roughly twice the factory** — 79% vs 37%, p=0.008 — but that
   arm varies **harness AND model** at once. It is a reference point, not a
   scaffold deficit, and that caveat travels with the number everywhere.
5. **The contamination probe came back CLEAN, and it is the most valuable result
   in the sweep.** `claude-opus-4-8` (published cutoff **Jan 2026**) scores 74%
   against `claude-opus-5`'s 79% (cutoff **May 2026**) on the same harness, same
   flags, p=1.000 — even though **all 19** instances predate opus-5's cutoff.
   Memorization is not carrying Claude's score. This *strengthens* the Claude
   reference rather than undermining it, and it retires the doubt PLAN 2.1
   recorded about publishing an absolute rate for the Claude arms.
6. **n=19, k=1. MDE ≈ ±38 pp.** So the honest phrasing for #1 is "no measurable
   lift", **not** "the chain hurts". −16 pp (−7 pp on the earlier archive) is
   well inside noise. Nothing here measured harm, and no reader should take it
   that way.
7. **The subset relation still holds, and needs no significance test.** The
   factory's 7 passes are a **strict subset** of `claude-opus-5`'s 15 — only-B = 0
   in that pair, i.e. the factory solved nothing Claude Code missed. Against
   `claude-opus-4-8` it wins exactly one instance, `hkuds__openharness-217`.

### Two caveats that cut against the factory — stated, not buried

- **`openhands` was under-counted in the first report, and counting it widens the
  gap.** It lost 3 of 19 rows to Azure `DeepSeek-V4-Pro` 429 rate limits, and
  **2 of those 3 had already produced patches the oracle RESOLVES**
  (`jsonpickle-588`, `rapid-mlx-289`). The conservative reading of the earlier
  archive is 9/19 = 47%; the later archive re-ran all three as `attempt: 2` and
  measures **10/19 = 53%**, which is the number this file uses. Either way the
  gap to the chain widens, never narrows. The underlying harness defect stands:
  there is no retry on a provider 429, and a lost row records `cost_usd: 0.0`, so
  it reads as free rather than as missing (`PLAN.md` 1.6 G).
- **7/19 is exactly the "matched-weights ceiling" the previous retraction
  predicted independently.** The 2026-08-03 audit derived 7/19 = 37% by
  subtracting the hard-tier-assisted resolves from the retracted 11/19. This
  sweep measured 7/19 = 37% directly. Two separate routes agree on the number.

### Integrity

- The retrieval detector caught **one genuine violation**: `bare` on
  `hiero-ledger__hiero-sdk-python-1914_interface` ran
  `curl -s https://raw.githubusercontent.com/…/src/hiero_sdk_python/account/account_info.py`
  — the upstream source of the exact file under test. Published **invalid and
  excluded**, per the no-re-rolls rule.
- **Zero path-based oracle probes anywhere.** The work root is now flat, so no
  arm sits a `..` away from `oracle.json.z` or another arm's logs. The 46
  in-flight audit failures the sweep logged were the pre-#227 detector matching
  hostnames the arms merely *read*; all 95 rows were re-audited under the fixed
  detector before publication, uniformly, with no arm re-run.
- **The repaired `bare` arm genuinely iterates now** — 727 model calls and 16 of
  18 valid rows budget-exhausted, against a mean of 9.2 steps and zero cap hits
  before — and still reaches only 6%. Per `PRE-REGISTRATION-1.6.md`'s
  pre-committed cap, **bare has now had its ONE repaired run.** Whether it stays
  in the suite is an operator decision; it anchors no headline either way.
- The review loop is no longer inert: reviewer cycles were `0×7, 1×9, 2×2, 3×1`
  across the 19 factory rows, versus 0 on every row in the n=6 sweeps. It
  engages and still does not lift the resolve rate.

### The fail-open paths from the retracted run are now closed

Each of these was live on 2026-08-03 and is fixed in this harness:

- Grading is **per-node**, not exit-code. `-rpfEsxX` (that is `-rA` minus `P`, so
  arm-authored code cannot echo a forged `PASSED <id>` into the region the parser
  reads) and every declared `FAIL_TO_PASS` and `PASS_TO_PASS` id must have a
  `PASSED` node and no `FAILED`/`ERROR` node. A module-level `SkipTest` in
  production code no longer scores RESOLVED.
- A prediction touching a pytest-collection or auto-import channel
  (`pyproject.toml`, `pytest.ini`, `tox.ini`, `setup.cfg`, `noxfile.py`,
  `conftest.py`, `sitecustomize.py`, `*.pth`) is **refused**, and `audit.json`
  records `refused_paths`.
- `_DIFF_HEADER` fails CLOSED on any header it cannot classify.
- `audit.json` hashes the graded patch (`prediction_sha256`) and records
  `base_commit`, `stripped_test_paths`, `trajectories_scanned`, `trails_scanned`.
- **No row in this manifest has an empty `PASS_TO_PASS`** — Table 4 reports 0 for
  every arm, so every grade has a regression half.

What remains open is reporting, not measurement: `PLAN.md` 1.6 G.

`PLAN.md` Phase A is the gate on the chain's verdict meaning anything, and Phase C
is the gate on turning any of this into a defensible number. Phase 1.6 G names the
two reporting debts this sweep left open.

## The reviewer ablation — measured 2026-08-05, `solo-noreview` (B.1 Phase 1a)

A sixth arm: the chain with the **reviewer round-trip removed**. Same 19 pinned
instances, same manifest, k=1, `attempt: 1` on every row, pre-registered in
`bench/swebench/PRE-REGISTRATION-B1.md` **before any paid call**. **Actual spend
$25.49.** Full report and evidence:
`bench/swebench/RESULTS-B1-PHASE1A.md` + `bench/swebench/results-b1-phase1a/`.

**It is published separately from the five-arm table on purpose.** `results.md` and
every `results-archive/` root are byte-identical to before the run, and
`report --check` still prints `CHECK OK`.

| arm | resolved / audited-valid | rate | 95% CI | $ | $ / resolved |
|---|---:|---:|---|---:|---:|
| `factory` (archived) | 7/19 | 37% | [16%, 62%] | 35.94 | 5.13 |
| `solo-noreview` | 9/18 | **50%** | [26%, 74%] | 25.49 | **2.83** |

Paired McNemar exact, n=18: only-factory **2**, only-solo **4**, **p = 0.688** —
a descriptive discordance statistic, nothing more. `reviewer_cycles` = 0 on all 19
rows, so the ablation applied everywhere. The pre-committed stop signal
(only-factory ≥ 5 of 19) **did not fire**.

### The interpretation limits, which matter as much as the number

- **The cost win is real; the quality claim is not established.** Δ = +13 pp sits
  well inside the ±38 pp MDE at this n, and p = 0.688.
- **It is not a clean single-variable ablation, and that was recorded in the
  pre-registration before the data existed** (with 1 of 19 outcomes known). The
  baseline rows ran 2026-08-03 and the ablation ran on `6662d062`, so **three things
  differ, not one**: the reviewer, 35 new lines in the dev persona, and the
  acceptance-oracle authoring layer. A.2 and A.5 provably do **not** reach this
  driver — both sit behind the merge-time gate evaluator, which the driver never
  calls. Empirical bound on the persona delta: **no row in either arm ended in
  `blocked_underspecified`.** Phase 1b must run both arms in **one sweep on one
  commit** (~$62).
- **`solo-noreview` at $2.83 per resolved is still 1.6× one OpenHands agent's
  $1.82.** The ablation narrows the chain's deficit against a single agent without
  closing it.
- **The cost mechanism was mispredicted, and the correction is the useful part.**
  The reviewer's own tokens are **$0.65 of $35.94 = 1.8%** of spend. The 29% saving
  comes from **9 fewer dev calls (30 vs 39)** and a median story of **1 tick instead
  of 4**. The reviewer was not expensive — it was causing rework. Optimise for
  round-trips eliminated, not tokens per persona.
- **Both arms certified green on the same zero-byte production diff**
  (`harumiweb__exstruct-113`). So the reviewer was never what caught that class; the
  gate that catches it is a **merge** gate this driver never runs.
- **One row was published invalid and not re-run** — its dev fetched a dependency's
  upstream source over the network. Counting it raw gives 9/19 = 47%, so the
  exclusion did not manufacture the 50%.

Building the arm surfaced three latent harness bugs that would have corrupted or
refused any second chain arm: the factory driver hard-coded the arm name in **nine**
places, `audit` keyed the state root off the arm id, and `main()` asserted the run
key equalled the base arm.

## Fixed 2026-08-05 (Phase A — the verification layers)

| Was broken | Now | PR |
|---|---|---|
| `tests-meaningful` was a **required** merge gate whose mutation branch was broken four ways — wrong symbols ablated, fail-open on infra failure, mutating the live story worktree, failing in dry-run — with one config flag between it and every merge | The ablation branch is **deleted** from the required gate (~200 lines). `tests-meaningful` is the static slop detector and nothing else: it cannot shell out, cannot mutate a checkout, cannot block for 600 s on a timeout. `gates.mutation_testing` survives as an **inert** config field, so there is no flag left to flip | #239 |
| The repaired mutation measurement had nowhere safe to live | `factory/chain/mutation.py` + `factory mutation-score`, **off the merge path**. No gate imports it and a test enforces that. The reasoning generalises: *advisory-by-constant is one edit from blocking every merge; advisory-by-not-being-imported is not* | #239 |
| Nothing could ask "can this check actually fail?" | New primitive `check_can_fail`: ablate the symbol a criterion is about, run only the check, require an **attributable** red. `True` only on an attributable red — green, an unattributable red, a timeout and an un-materializable tree are all `False` **with the reason**, because "we could not prove it" is not "it can" | #239 |
| The benchmark's `factory` arm could not see the acceptance oracle, so the published 37% and the 40% chain-verdict precision were measured with the chain's only independent signal absent | The arm authors the oracle from the instance's problem statement **before the dev's first model call**, through the chain's own authoring code. `result.json` records an `acceptance.ordering` fact a reader **re-derives from the run's own event stream** rather than a boolean the code asserts about itself. Four integrity properties enforced in code; the other four arms asserted byte-identical; story template pinned by sha256 | #238 |
| Independence was conventional, not structural — and a live run proved it | With the oracle stored inside the factory root, **the dev on a real run ran a filesystem search from one level above its worktree and the listing named the acceptance store.** The detector fired and **refused the row**. The store now lives outside the factory root, the in-root copy is deleted with the deletion asserted, and any acceptance-named leftover refuses the row | #238 |
| The oracle's green carried no information: `assert True` scored an authoritative pass, the oracle ran under collection config the dev controlled, and the gate never verified it was testing the merge candidate | Harness-owned red→green (`factory/chain/red_green.py`, A.6 folded in and built once): the oracle must be **red at the merge base** before a green at HEAD is credited, run in a throwaway judge worktree with production code from HEAD and the test surface from BASE, and the checkout must contain the PR head by **ancestry, not SHA equality** — a plain equality check false-blocks, because the story worktree merges `main` in first | #242 |
| Five lower-ranked defects | The pass count is read from the **last** pytest summary and refused on conflicting summaries; the leak sweep deletes **nothing** when git cannot say what is tracked; an unresolvable direction exhausts instead of wedging forever; authoring exhaustion and every unverifiable state appear in `factory inbox`, with `factory acceptance-waive` as the recorded path back; `.pytest_cache` no longer retains the oracle's test names | #242 |
| Gate ordering was load-bearing and untested | `acceptance_verified` running **last** in `evaluate_all_gates` is pinned by a test | #239 |

**Two adversarial passes over two fully-green PRs found 13 defects between them.**
The three that generalise:

- **An errors-only red at the base laundered a tautology into an authoritative
  green.** For a story that *adds* a module, an oracle whose only link to the
  criterion is an import errors at base **whatever it asserts** — and "red" was
  definitive, so it bypassed the ablation check entirely. That is the **common**
  story shape, not an edge case. Fixed: errors-only ⇒ `unknown` ⇒ falls through to
  ablation. A mixed `1 failed, 1 error` stays red.
- **`pyproject.toml` is both a pytest collection channel and the dependency
  manifest.** Rolling it back wholesale authoritatively false-blocked every
  dependency-adding story. The decision was "dependencies from HEAD, pytest config
  from the factory", and the obvious mechanism — run pytest with an empty
  factory-owned config — was **measured wrong**: it kills `asyncio_mode = auto`, so
  every `async def` oracle false-blocks on a FastAPI app. Shipped instead: splice out
  only the `[tool.pytest.*]` tables, re-verified with a TOML parse, which also catches
  a dotted-key evasion. `pyproject.toml` is now a **documented special case**, not the
  clean complement of the production-path classifier.
- **Standing rule:** an import or collection error at HEAD must be
  **non-authoritative** whenever the environment rollback set is non-empty. If we
  perturbed the environment and got an error rather than a failure, we cannot
  distinguish "the dev's code is wrong" from "we broke it", and a gate must never
  authoritatively blame the dev for something it may have caused.

### The acceptance oracle's real status: executable, hardened, and still OFF

- **Executable and demonstrated end to end** on the real sacrifice repo against
  direction 002's real `api_spec.md`: a spec-derived oracle is credited, and a
  tautology for the same story is rejected.
- **`gates.acceptance_oracle` is absent from every app config, deliberately.** Not
  because the listed blockers are open — they closed in #242 — but because of the
  in-process hole in "What does not work" above, which no file rollback closes.
  **The flip is an operator decision.**
- **Flip prerequisites when it happens:** `sacrifice` **only**; all apps currently
  have 0 non-terminal stories, so a flip authors nothing retroactively; the
  `sacrifice-db` container must be up or the gate false-blocks; `hypothesis` is
  missing from sacrifice's backend dev extra, so EARS-form criteria would fail
  collection; and **never flip `template-probe`**, whose app is TypeScript while the
  oracle is pytest-only.

## Fixed 2026-08-02 (Phase 1.1–1.3 + the three bugs that invalidated 2026-08-01)

The four 2026-08-01 benchmark batches (1/6…2/6) are **retracted**: the reviewer
never saw a diff in any review (fail-open error-text-as-diff), openlibrary
instances were unrunnable (uninitialised submodules), and cost was
under-reported 1.62× (onboarder spend invisible). Do not cite them.

| Was broken | Now | PR |
|---|---|---|
| `_fetch_pr_diff_for_review` was FAIL-OPEN — any `gh pr diff`/`git diff` failure returned the error text AS the diff; reviewer reviewed blind (production bug, not bench-only) | Missing diff raises before any model call, routes to `blocked_review_nonconvergent`, burns no cycle; base-ref fallback `origin/<base>` → `<base>`; anchored broken-prompt markers; `errors="replace"` on diff decode | #203 |
| Bench cost summed only story-attributed Run rows (1.62× under-report) | ALL ledger rows counted; unattributed spend reported separately; wall clock from function entry; stale artifacts reset at run start | #202 |
| `_clone` left submodules uninitialised → `ModuleNotFoundError` in 0.8 s | Submodules vendored into the base branch as tracked files (survives `git worktree add`) | #202 |
| Nothing verified the test command WORKS before spending | Pre-dispatch `--collect-only` gate in the real docker env; two modes — strict `existing-targets` / `ancestor-env-check` for legit new-test-file TDD instances | #202, #205 |
| No post-hoc integrity check existed (all three bugs shipped past green tests) | `audit` subcommand: full persona-call ledger, cost cross-check, error-text-in-reviewer-prompt scan, missing artifact = FAIL; wired per-instance into the parallel sweep; `report` counts only audited-valid rows | #202, #204 |
| Benchmark ran one instance at a time | `run-all` parallel sweep (child processes, spend guard on actual mid-sweep cost, pure dry-run, group kill) | #204 |
| Dev invented literals where the story was silent | Persona seeks codebase precedent (measured 2/2 vs 0/2 on the isolating instance) | #201 |

Reported (n=6, `bench/swebench/results.md`, generated 14:01:07Z): **1/6
resolved**, 4 `right_place_wrong_fix`, 1 honestly-blocked empty patch,
chain-verdict precision 1/5, recall 1/1, $3.33.

> **⚠ RETRACTED PENDING RE-DERIVATION — do not cite these numbers.**
> The artifacts on disk are from a **later** sweep (16:23–16:35Z) that reports
> 5 `right_place_wrong_fix` and `cost_usd: 6.7342`, and they disagree per
> instance: `openlibrary-3aeec6af` is published as `empty_patch` at 142,903
> input tokens but on disk shows 2,985,777 in / 50,735 out. **No `grade.json`
> survives anywhere under `bench/swebench/runs/`**, so the oracle PASS/FAIL
> column has no backing artifact. `_reset_run_artifacts` clears state at run
> start (correct) but nothing snapshots a published run first. This is the same
> class as the retraction on line 33, recurring one day later. `PLAN.md` 1.5
> fixes it and must run before 1.4 — a bare-model delta against an unbacked
> factory number measures nothing.

> **RESOLVED later the same day.** PLAN 1.5 shipped in #210: `report` now
> snapshots every row's `result.json`/`audit.json`/`prediction.diff` into
> `bench/swebench/results-archive/` before publishing and refuses unbacked
> rows. (One correction to the note above: no separate `grade.json` exists by
> design — `grade` merges its verdict into `result.json`.) Evidence archives
> are committed in #211. The 14:01Z table ($3.33, precision 1/5) stays
> retracted — its artifacts were destroyed before archival existed. The
> **currently backed** numbers (archives `17-30-31Z` and `17-45-30Z`):
> factory 1/6 = bare 1/6 resolved (same qutebrowser instance, at ~30× tokens),
> and the post-#210 sweep holds 1/6 with the review loop now engaging
> (`reviewer_cycles` on 2/6 vs 0/6 before). Per-instance autopsies live in the
> memory file `swebench_failure_synthesis_2026_08_02`.
>
> **Superseded 2026-08-04** by the five-arm n=19 result at the top of this file.
> That n=6 pair is `factory` vs `bare`, which entangles the chain with the
> tooling; it is not a chain measurement and "scaffold lift" is no longer the
> metric. Keep it only as a Pro-profile plumbing record.

## Fixed 2026-08-01 (Phase 0)

Measurement was impossible before these; everything in Phase 1 depends on them.

| Was broken | Now | PR |
|---|---|---|
| Dev/test_implementer/onboarder had NO prompt telemetry — 45,868 rows, zero for the three personas that write all the code | `sandbox_run` logs metadata; new `prompt_bodies.ndjson` keeps full text + full sha256, hash-chained | #193 |
| Retries were invisible: 0 `retried` rows in `chain_steps` vs 71 real dev retries and 119 review cycles | `retried` / `review_cycle` rows emitted, reconciling with the DB counters | #194 |
| Failing gates' `reason` and `output_tail` were discarded — a blocked merge could not say why | `gates_failed` on `MergeAction`, a `gates_failed_json` column, and a `merge_gates_failed` story event | #195 |
| `StoryRecord.smoke_passed` was read by the smoke gate and written nowhere — fail-closed by accident | Dead reader deleted; the gate is fail-closed structurally | #195 |
| Reviewer shared a model with `dev.hard` (both `azure/gpt-5.3-codex`) | `reviewer` → `azure/gpt-5.4` in both blocks; enforced at router load | #196 |
| Loop caps were 6, contradicting the "nothing loops >3" guardrail | `_MAX_DEV_RETRIES` and `_MAX_REVIEW_CYCLES` → 3; inner guards → 2 to keep early escalation reachable | #196 |

**Behavioural change to watch.** At `_MAX_DEV_RETRIES = 3` the dev
inner-convergence loop gets at most **two** sandbox attempts per invocation, so
`red → red → green` no longer converges in one tick. Four stories in the 14 days
to 2026-08-01 reached 6 retries and would now block at 3. Whether attempts 4–6
produced *passing* work is unmeasured — that is exactly what Phase 1.3's gate
precision number settles. Re-read this row after the first real soak.

Reviewer independence now holds on **both** dev tiers and is enforced in code:
`model_router.check_review_independence` refuses to resolve any route out of a
colliding `routes.yaml`. `test_implementer` still shares `deepseek-v4-pro` with
`dev.standard` — that weakens the acceptance oracle but not the merge decision,
so it warns rather than blocks.

## Cost

July, from the `runs` ledger:

- All-in: $588.78 across 75 deployed stories = **$7.85 per story**
- Excluding the manager: $217.18 = **$2.90 per story**

Input and output rates are verified Azure retail. The **cache-read rate is
estimated** — no Azure meter publishes one for this deployment, and the account
lacks the Cost Management RBAC role. `factory audit` reports ~55% of window
spend as estimated. Treat dollar figures as approximate. Prefer token counts:
they are provider-reported and exact.

## Two self-modification paths — do not confuse them

The chain self-edit path and the FMS L4 apply tier are different subsystems.

- **Chain self-edit** (loop 2): direction → story → dev → review → gates → PR →
  staging twin → merge. **Works.**
- **FMS L4 apply**: the manager diagnoses an operational fault and writes its
  own fix. **0 PRs from 163 attempts.**

Measuring only the second produces the false conclusion that the factory cannot
improve itself. Cross-check any yield claim against GitHub before asserting it.

## Benchmark harness

Two harnesses, do not confuse them.

- **`bench/swebench_adapter.py` — the one that counts.** Externally graded
  against a hidden oracle, five arms, pre-registered tables, archived evidence,
  `report --check`. Everything in "The benchmark" above comes from it. Read
  `bench/swebench/README.md`.
- **`bench/bench.py` — retired for grading.** It scores the factory on
  sacrifice's own gates, i.e. on tests the factory wrote. Its July campaign is
  superseded (`bench/CAMPAIGN-2026-07-17.md`), its raw artifacts are gone and
  its task pool is contaminated. Pinned by `PLAN.md` Phase 0 (#197) — `base_sha` is a
  literal SHA and an empty one is refused, the Claude arm pins `--model`,
  `clean()` no longer deletes `bench/runs/`, every `result.json` records its
  base/routes/price-table provenance — so it is usable as a *convergence*
  harness. It is not evidence about correctness.

Tokens are the reported metric in both; dollars are derived from a hashed price
table and can be re-derived after a price correction.

## Known gaps in the twin

`software-factory-copy` is **public**. Make it private.

It guards source only. Nothing snapshots `state/factory.db`, and runtime state
corruption is what has actually taken the factory down.

## CI cost

`lint`, `typecheck` and `pytest` are required checks, so they always run and
always report. A PR that changes only root-level `*.md` skips their expensive
steps and finishes in about 20 seconds instead of about 4 minutes. Any other
path — including `factory/personas/*.md` and `apps/**/context/*.md`, which are
code — runs the full suite. See the `changes` job in
`.github/workflows/test.yml`.
