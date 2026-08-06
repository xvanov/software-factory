# B.1 Phase 1a — the reviewer ablation, n=19, k=1

Pre-registered in [`PRE-REGISTRATION-B1.md`](PRE-REGISTRATION-B1.md) **before any
paid call**, with an addendum recorded mid-run (1 of 19 outcomes known) that names
a confound the original file missed. Read that file first. Nothing in it was
edited after the data existed.

Run 2026-08-05. Same pinned manifest `923aef05add32124`, the same 19
working-oracle instances, `attempt: 1` on every row, no re-rolls.
**Actual spend: $25.49** against a ~$35 target and a $50 hard stop.

Evidence: [`results-b1-phase1a/`](results-b1-phase1a/) — per row `result.json` +
`audit.json` + `prediction.diff`, plus each row's acceptance provenance and its
verbatim prompt/response bodies. `bench/swebench/results.md` is **unchanged** and
still re-derives byte-for-byte from its own archive
(`report --check` prints `CHECK OK`); `solo-noreview` appears in no table there.

---

## The answer, in one paragraph

Removing the reviewer round-trip did not lower the resolve rate. It **raised** it
by 13 pp — **9/18 = 50%** against the published **7/19 = 37%** — which at this
design's ±38 pp MDE means **no measurable change**, in the direction the
pre-registration predicted would be flat. It cost **29% less** ($25.49 vs
$35.94), landing inside the pre-committed $25–30 band, and **45% less per
resolved instance** ($2.83 vs $5.13). `only-factory` is **2 of 18** — far below
the pre-committed stop signal of 5 — so **B.1's premise survives.** The chain's
own verdict did not get worse without the critic: precision 47% vs 40%, also
inside noise.

**Three things this does not say.** It is not a clean single-variable ablation —
the baseline rows predate the current commit by three changes, one of which is a
35-line dev-prompt addition (see "Confounds"). It does not license removing the
reviewer in production. And `solo-noreview` at $2.83 per resolved instance is
still **1.6× the cost** of one OpenHands agent at $1.82, so this ablation
narrows the chain's deficit against a single agent without closing it.

---

## Prediction versus outcome

The pre-registration's three predictions, scored as written:

| # | pre-registered | measured | verdict |
|---|---|---|---|
| 1 | no material change in resolve rate: **5–9 of 19** resolved (26–47%), point estimate 7/19 = 37% | **9 resolved**, 9/18 = **50%** | **count inside the band, rate 3 pp above its top.** The denominator fell to 18 because one row published invalid, which the band did not anticipate. Δ = **+13 pp**, well inside the ±38 pp MDE |
| 2 | **~25% lower cost**, point estimate ~$27, band **$25–30** | **$25.49**, **−29%** | **inside the band.** The *mechanism* was mispredicted, and that was recorded in the addendum before the data existed: the reviewer's own tokens are $0.65 of $35.94 (1.8%). The saving is fewer dev calls, not reviewer tokens |
| 3 | `reviewer_cycles = 0` on every row | `0`×19 | **held.** The ablation applied on every row |

Prediction 1's direction was right and its magnitude was inside the design's
resolution. Prediction 2's number was right for the wrong reason, which is worth
less than a right number for the right reason and is labelled as such.

### Where the 29% came from

| | `factory` | `solo-noreview` | Δ |
|---|---:|---:|---:|
| orchestrator ticks, total / median | 68 / **4** | 27 / **1** | −60% / −75% |
| dev model calls (standard + hard tier) | 39 | 30 | −23% |
| dev spend | $35.29 | $25.17 | −29% |
| reviewer spend | $0.65 | **$0** | −100% |
| acceptance-author spend | n/a (layer absent) | $0.33 | — |
| **total** | **$35.94** | **$25.49** | **−29%** |
| wall clock, median per row | 995 s | **1040 s** | +5% |

The reviewer costs almost nothing to run. What it costs is **dev re-work**: each
review cycle sends the dev back, and the published run's 12 rows with non-zero
cycles (16 cycles in total) are most of the gap between 39 dev calls and 30.
Removing it collapsed the median story from four ticks to one.

**It did not make a row finish faster.** Median wall clock is flat (995 → 1040 s):
the single dev conversation simply runs longer than the first of four. Anyone
selling this as a latency win would be wrong.

---

## Table B1-1 — headline

| arm | harness | resolved / audited-valid | rate | 95% CI (Clopper-Pearson) | invalid | budget-exhausted | fresh in | cache read | out | wall s (median) | $ | $ / resolved |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `factory` | software-factory chain on OpenHands | 7/19 | **37%** | [16%, 62%] | 0 | 0 | 14,349,408 | 33,195,520 | 486,506 | 995.1 | 35.94 | **5.13** |
| `solo-noreview` | software-factory chain, dev only (no reviewer round-trip) | 9/18 | **50%** | [26%, 74%] | 1 | 1 | 9,866,201 | 27,028,224 | 366,462 | 1039.7 | 25.49 | **2.83** |

Both arms' dollars are the **same basis** — a price-table estimate over measured
tokens from each run's own isolated ledger — so the ratio between them is exact
in the way a cross-family ratio is not.

Models the ledger says ran, both arms: `azure/deepseek-v4-pro` (nominal dev) +
`azure/gpt-5.3-codex` (dev hard-tier escape). `factory` adds
`azure/gpt-5.4` as the reviewer; `solo-noreview` uses `azure/gpt-5.4` for the
acceptance author instead. **The nominal weights are identical.**

### Descriptive context, NOT pre-registered

From the same archive, on the same 19 instances and the same cost basis:
`openhands` (one agent, no chain) is **10/19 = 53%** [29%, 76%] at **$1.82** per
resolved instance. `solo-noreview` sits at 50% and $2.83. No test is computed for
that pair because it was not pre-registered, and it varies more than one thing.
It is here because the reporting rule in `bench/swebench/README.md` says a chain
number is never published without the matched single-agent number beside it.

## Table B1-2 — per-instance outcome matrix

`R` resolved · `F` wrong patch (right place or not) · `E` empty patch ·
`X` audit-invalid · `!` budget-exhausted (counted, never excluded)

| instance | factory | solo-noreview | discordant | solo $ | solo ticks | solo final state |
|---|:-:|:-:|:-:|---:|---:|---|
| alibaba__opensandbox-816 | F | F |  | 1.0525 | 2 | `tests_green` |
| conan-io__conan-19735_interface | F | F |  | 0.2935 | 1 | `tests_green` |
| conan-io__conan-19750 | F | F |  | 1.9989 | 1 | `tests_green` |
| getmoto__moto-9841 | **R** | **R** |  | 0.759 | 1 | `tests_green` |
| harumiweb__exstruct-113 | E | E |  | 1.2704 | 1 | `tests_green` |
| hiero-ledger__hiero-sdk-python-1914_interface | F | F |  | 2.2935 | 1 | `tests_green` |
| hkuds__openharness-217 | **R** | F | **only-factory** | 0.6414 | 1 | `tests_green` |
| idaholab__montepy-933_interface | F | **R** | only-solo | 1.5565 | 1 | `blocked_tests_need_clarification` |
| jsonpickle__jsonpickle-588 | **R** | **R** |  | 2.7575 | 1 | `tests_green` |
| keras-team__keras-22316 | **R** | **R** |  | 1.1043 | 1 | `tests_green` |
| keras-team__keras-22642 | **R** | **R** |  | 2.77 | 1 | `tests_green` |
| line__line-bot-sdk-python-981_interface | **R** | F | **only-factory** | 2.14 | 1 | `tests_green` |
| pandas-dev__pandas-63945 | F | F |  | 1.2132 | 2 | `blocked_tests_need_clarification` |
| pyinfra-dev__pyinfra-1665 | F | **R** | only-solo | 0.6765 | 2 | `tests_green` |
| raullenchai__rapid-mlx-289 | F | **R** | only-solo | 1.5226 | 4 | `tests_green` |
| tox-dev__tox-3931 | F | **R** | only-solo | 2.2685 | 1 | `blocked_tests_need_clarification` |
| ucfopen__canvasapi-716 | F | F |  | 0.6247 | 1 | `tests_green` |
| vyperlang__vyper-4801 | F | **X!** |  | 0.017 | 3 | `dev_retry` |
| zauberzeug__nicegui-5858 | **R** | **R** |  | 0.5323 | 1 | `tests_green` |

Terminal states, both arms: `factory` ended `reviewer_done` 15, **`blocked_review_nonconvergent` 2**,
`blocked_tests_need_clarification` 2. `solo-noreview` ended `tests_green` 15,
`blocked_tests_need_clarification` 3, `dev_retry` 1 (the wall-capped invalid row).
The two non-convergent blocks are a failure mode `solo-noreview` cannot have by
construction — the dev↔reviewer loop is the thing that fails to converge.

**Two** `solo-noreview` rows resolved *from a blocked state*
(`idaholab__montepy-933_interface`, `tox-dev__tox-3931`): the dev exhausted its
inner retries, the chain said NOT green, and the patch it left behind passed the
hidden oracle anyway. Same verdict-channel error as the green-but-wrong rows,
pointing the other way — and both arms have plenty of both (Table B1-5).

## Table B1-3 — the paired comparison

| comparison | harness varies? | model varies? | paired n | only-factory / only-solo | McNemar exact p (descriptive) | isolates |
|---|---|---|---:|---:|---:|---|
| `factory` vs `solo-noreview` | yes (reviewer round-trip) | no — both nominal `azure/deepseek-v4-pro` | 18 | **2 / 4** | **0.688** | the reviewer round-trip **plus 3 disclosed confounds** |

**The p value is reported because the pre-registered table has a column for it,
and for no other reason.** At MDE ≈ ±38 pp no decision rule in this run is a
significance test, which the pre-registration fixed in advance.

- **`only-factory` = 2 of 18** — `hkuds__openharness-217`,
  `line__line-bot-sdk-python-981_interface`. Both went `right_place_wrong_fix`
  without the reviewer.
- **`only-solo` = 4 of 18** — `idaholab__montepy-933_interface`,
  `pyinfra-dev__pyinfra-1665`, `raullenchai__rapid-mlx-289`,
  `tox-dev__tox-3931`.

**The pre-committed stop signal did not fire.** Decision rule 1 said
`only-factory ≥ 5 of 19` would mean the reviewer is doing real work on this task
shape and would halt B.1. It is 2.

## Table B1-4 — provenance and integrity, per arm

| arm | per-persona calls and spend (from the LEDGER) | attempts | audit ok / invalid | test files stripped | oracle-probe hits | reviewer cycles | dev retries | green-on-empty-diff rows |
|---|---|---|---|---:|---:|---|---|---:|
| `factory` | `dev`/standard `deepseek-v4-pro` — 33 calls, $32.81<br>`dev`/hard `gpt-5.3-codex` — 6 calls, $2.48<br>`reviewer` `gpt-5.4` — 31 calls, $0.65 | all 1 | 19 ok / 0 invalid | 23 | 0 | `0`×7, `1`×9, `2`×2, `3`×1 | `0`×17, `3`×2 | **1** (`harumiweb__exstruct-113`) |
| `solo-noreview` | `acceptance_author` `gpt-5.4` — 21 calls, $0.33<br>`dev`/standard `deepseek-v4-pro` — 26 calls, $23.50<br>`dev`/hard `gpt-5.3-codex` — 4 calls, $1.67 | all 1 | 18 ok / **1 invalid** | 50 | **1** | `0`×19 | `0`×16, `2`×2, `3`×1 | **1** (`harumiweb__exstruct-113`) |

`dev_retries` is unchanged in shape. The ablation removed the **outer** review
loop; the dev's own inner retry loop is untouched and still fires.

### The one invalid row, published rather than repaired

`vyperlang__vyper-4801 / solo-noreview` is **audit-invalid** and excluded from the
denominator. Two things happened on it, and the integrity finding is the
disqualifying one:

- **oracle-probe hit.** The dev ran
  `curl -sL https://raw.githubusercontent.com/pcaversaccio/snekmate/main/src/snekmate/tokens/mocks/erc20_mock.vy | head -100`
  (`trajectory 1-1-1785978149345.ndjson:27`, an `ActionEvent`). That is a
  third-party dependency's source, **not** the instance's own gold patch — but
  the retrieval scan is verb-anchored on the command side and has **no own-repo
  exemption**, deliberately, because fetching your own origin's `main` *is* the
  fix. The rule is applied as written: the row is invalid.
- **budget-exhausted.** It also hit the 5400 s wall cap (6370 s wall, terminal
  state `dev_retry`). Per the one budget rule, a cap hit is a counted, flagged
  attempt, never an exclusion — so had the audit passed, this row would have been
  counted as an unresolved attempt.

**Not re-run.** `PRE-REGISTRATION-1.6.md` Rule 5, adopted by reference: an
audit-invalid row is published invalid and never re-run, because re-running it
would be selecting on the integrity gate — the subject of the 2026-08-03
retraction. Its oracle verdict, for the record, was `wrong_place` (it would not
have resolved either way), and it is stated here so a reader can see which way
the exclusion moved the rate: **excluding it did not manufacture the 50%.**
Counting it raw as an unresolved attempt gives 9/19 = 47%, still above the
factory arm's 37%.

This is the second oracle-probe violation this harness has caught in a live
sweep. The first was `bare` on `hiero-ledger__hiero-sdk-python-1914_interface`.
Zero path-based oracle probes in either.

### Green on an empty production diff — the class still exists

Pre-committed rule 6 required this count either way. It is **1 in each arm, the
same instance**: `harumiweb__exstruct-113` produced a **zero-byte** production
diff in both, with the whole dev diff being one test file
(`tests/cli/test_cli_lazy_imports.py`, stripped), and **both arms certified it
green** — `reviewer_done` for `factory`, `tests_green` for `solo-noreview`.

So the reviewer is not what was catching this, and removing the reviewer did not
make it worse. The merge gate that now blocks it —
`factory/chain/gates/production_tree_changed.py` (A.2) — is a **merge** gate, and
this driver has no merge step, so neither arm exercised it. That gate's coverage
is therefore still unmeasured by this benchmark; what is measured is that the
class survives all the way to the chain's green verdict on both arms.

## Table B1-5 — chain-verdict quality, per arm

| arm | green means | said green | precision — P(oracle passes \| said green) | 95% CI | recall — P(said green \| oracle passes) | 95% CI |
|---|---|---:|---:|---|---:|---|
| `factory` | `reviewer_done` | 15 | 6/15 = **40%** | [16%, 68%] | 6/7 = **86%** | [42%, 100%] |
| `solo-noreview` | `tests_green` | 15 | 7/15 = **47%** | [21%, 73%] | 7/9 = **78%** | [40%, 97%] |

**The reviewer was not buying verdict precision on this suite.** Both arms say
green on 15 of their rows; the arm *without* a critic is right slightly more
often. The CIs overlap almost entirely and this is the least stable pair of
numbers on the page — `PRE-REGISTRATION-1.6.md` said so of Table 5 before either
run existed, and it is still true. Read it as "no evidence the critic improves
the verdict channel", never as "removing the critic improves it".

Every `solo-noreview` row records `green_state: tests_green` and
`chain_personas: ["dev"]`, so no reader has to infer which claim a row was
making.

---

## Confounds — this bounds the reviewer's contribution, it does not measure it

The comparison rows for `factory` come from the committed archive
`results-archive/2026-08-04T23-19-24.998844Z/`, whose rows ran **2026-08-03
19:42–20:59 UTC**. `solo-noreview` ran on `6662d062`. **Three things differ, not
one:**

1. **the reviewer round-trip** — intended;
2. **the dev persona prompt.** `7a2d7a68` added **35 lines** to
   `factory/personas/dev.md` ("Declaring the story underspecified", the
   ImpossibleBench escape hatch of P7), plus the `blocked_underspecified` edge.
   This is a difference on the primary metric's own path;
3. **the acceptance-oracle authoring layer** — present in `solo-noreview` (21
   calls, $0.33), absent from the archived `factory` rows.

Two later chain changes were checked and **do not** reach this driver, verified
rather than assumed: **A.2** (`production_tree_changed`) and **A.5** (the
diff-scoped mutation score) both live behind `auto_merge` / the gate evaluator,
and `bench/swebench_adapter.py` calls neither.

Empirical bound on confound 2: **no row in either arm terminated in
`blocked_underspecified`.** The escape hatch the dev prompt gained was never
taken, so its observable effect on this suite is nil — though the 35 lines still
perturb the dev's context on every call, and that is not measurable from here.

Confound 3 runs **against** `solo-noreview`: it adds $0.33 of spend the baseline
never paid, and its fail-closed refusal path can only cost this arm rows.

**Consequence, stated plainly: this run bounds the reviewer's contribution rather
than measuring it.** It is enough for decision rule 1 (a gross effect of five
discordant instances is not manufactured by a 35-line prompt addition) and enough
for the cost comparison. It is **not** a clean single-variable ablation, and no
sentence anywhere should call it one. **B.1 Phase 1b must run both arms on ONE
commit, in one sweep.** Re-running only the discordant instances would be
selection on the outcome and is forbidden.

## Interpretation limits

- **One task shape.** This is single-issue patching against a hidden oracle. P1
  is exactly the premise that role decomposition has never won *there*. Loop 1
  builds an app from a backlog, and that is the shape where role decomposition
  has published support — CAID (arXiv 2603.21489) measures **+6.0 pp** at
  Claude Sonnet 4.5 and **+14.7 pp** at MiniMax 2.5 on Commit0-Lite using
  centralized delegation with isolated git worktrees and branch-and-merge, which
  is architecturally our chain. **Nothing here transfers to that shape.**
- **This does not license removing the reviewer in production.** The production
  merge path runs gates this driver never touches — full suite, runtime smoke,
  CI, auto-merge, and A.2's production-diff precondition. Removing a reviewer
  there is a different change with a different risk surface, and it would remove
  the only step that reads the diff on different weights before a self-merge.
- **±38 pp.** Nothing smaller is measurable at n=19, k=1. The +13 pp measured
  here is inside that, so "the ablation is better" is **not** a supported reading.
- **k=1.** Two of the six discordant cells could plausibly be draw noise; the
  archives' own replication data puts the per-instance flip bound at ±3 instances
  at this n.
- **No navigation-tooling change.** B.2 remains unmeasured and deliberately
  separate.
- **The acceptance oracle's merge gate is not enforced** in either arm
  (`gate_enforced: false`), so nothing here says anything about it.

## What B.1 Phase 1b should do, in order

1. **Run `factory` and `solo-noreview` in ONE sweep on ONE commit** — the
   confound above is the only thing between this probe and a real ablation.
   ~$62 for both arms at n=19, or fold it into a k≥3 design.
2. **Then, and only then, consider the collapse.** The measured case for it is
   currently a **cost** case: −29% total, −45% per resolved instance, at a
   resolve rate this design cannot distinguish from the chain's. The pre-committed
   words for that outcome (rule 5) are that it is a cost finding, not a quality
   finding.
3. **Do not delete `_MAX_REVIEW_CYCLES` while the loop exists** (B.4's warning).
4. **Carry the empty-diff row forward.** Both arms certified green on a zero-byte
   production patch. That is a verdict-channel defect the reviewer does not fix
   and the ablation does not worsen; it is A.2's job, and A.2 is unexercised by
   this benchmark.

## Iterations disclosed

**One.** The arm was written, probed free (unit tests + `run-all --dry-run`), run
once on one paid instance (`conan-io__conan-19735_interface`, $0.2935, verified
run → grade → audit end to end), then swept over the other 18. **No arm code
changed after the first paid row.** Nothing was tuned, no row was re-run, and
`attempt` is 1 on all 19. Had the arm been iterated, every iteration would appear
here with its own number.

## Reproduce

```bash
# the tables above, from artifacts only — never `report`, which would rewrite
# results.md and mint a new results-archive
uv run python bench/swebench_adapter.py audit --arm solo-noreview --instance <id>

# the published factory column is unchanged and still self-checking
uv run python bench/swebench_adapter.py report --check    # must print CHECK OK
```
