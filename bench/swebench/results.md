# SWE-rebench — externally graded

Generated 2026-08-03T05:12:08.813897+00:00.

Every row here is backed by the evidence snapshot in
`bench/swebench/results-archive/2026-08-03T05-12-08.813897Z/`, and
`report --check` asserts that this table is still byte-for-byte
re-derivable from it.

> ## RETRACTED — do not quote these numbers
>
> This run's rows are kept as evidence and as the regression corpus for the
> report code. They are **not** a result, for reasons that are properties of the
> run, not of the table:
>
> 1. **The prompt was not matched.** The factory, openhands and claude arms were
>    told to run a test command over the `FAIL_TO_PASS` files at `base_commit`
>    without being told those tests already pass there and do not cover the task.
>    16 of 19 instances contain zero of the relevant test functions. Only the
>    bare arm had the honest note (#223). Every arm has it as of 2026-08-03, which
>    makes the five-arm re-run a **fresh baseline**, not a before/after.
> 2. **No `openhands` arm ran.** `factory − bare` varies the chain AND the
>    tooling at once, so the headline could not be attributed to either. The
>    product claim is `factory − openhands`, and that number does not exist here.
> 3. **The published table was not this table.** It reported 16/18 for the claude
>    arm because it excluded a row that hit its turn cap and PASSED the oracle,
>    while `sweep-claude.json` said 17 — two classifiers, two denominators. It
>    mixed fresh and cached input tokens into one column (cache share ranged
>    0%-97%). It named excluded passes but not excluded failures. It printed
>    "claude recall 0/16 = 0%" for an arm with no chain verdict. It disclosed no
>    attempt counts and no contamination margins.
>
> What the rows below ARE good for: they are the fixture the honest-column fixes
> are tested against, and the reason each column exists is a defect visible in
> them.

Tables 1-5 are the shape fixed in `bench/swebench/PRE-REGISTRATION-1.6.md`
before the run. Every cell is filled from an archived artifact or printed
as `n/a` with a reason; no cell is filled by hand.

**An arm is a (harness, model set) pair.** Neither half may be omitted
when a number from this run is quoted: a score is never a property of the
model alone and never of the harness alone.

`task_broken` is reported SEPARATELY from `wrong_patch`. This dataset execution-validates every instance upstream, so a non-trivial `task_broken` rate means THIS harness's plumbing broke, not the tasks.

## Table 1 — headline, one row per arm

Harness and models are repeated per row, not cross-referenced. The model
column is filled **from the per-row ledger, not from `routes.yaml`** —
config is intent, the ledger is what happened.

`fresh in` and `cache read` are separate columns on purpose: one blended
"tokens in" column mixed them last time and cache share differed 0%-97%
across arms, which made the published "34x tokens" claim wrong by 4.5x.

| arm | harness | model(s) actually used | resolved / audited-valid | rate | 95% CI (Clopper-Pearson) | invalid rows | budget-exhausted | fresh in | cache read | out | wall s (median) | $ | cost source |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| bare | hand-rolled text loop, no tool calls | `azure/deepseek-v4-pro` (19 rows, calls not recorded) | 0/19 | 0/19 = 0% | [0%, 18%] | 0 | 0 | 1,584,203 | 0 | 369,563 | 133.1 | 3.58 | price-table estimate |
| claude | Claude Code CLI | `claude-opus-5` (19 rows, calls not recorded) | 17/19 | 17/19 = 89% | [67%, 99%] | 0 | 1 | 1,034,198 | 30,799,286 | 379,427 | 276.0 | 34.85 | CLI-reported, subscription |
| factory | software-factory chain on OpenHands | n/a (no model recorded in any row) | 11/19 | 11/19 = 58% | [33%, 80%] | 0 | 0 | 10,504,314 | 36,759,936 | 483,904 | 641.9 | 29.19 | price-table estimate |

## Table 2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken · `X` audit-invalid or run-failed · `!` budget-exhausted (counted as an attempt, not excluded) · `*` attempt > 1 · `·` no row

A POSITIVE margin means the instance was created after that model's
bound, i.e. it cannot have been memorised. Bound TYPE is in Table 4's
footnote: a published cutoff and a release-date proxy are different
claims.

| instance | created_at | margin vs `claude-opus-5` (2026-05-31) | margin vs `deepseek-v4-pro` (2026-04-24) | bare | claude | factory |
|---|---|---:|---:|:-:|:-:|:-:|
| vyperlang__vyper-4801 | 2026-01-03 21:33:22 | -148 | -111 | E | R | R |
| jsonpickle__jsonpickle-588 | 2026-01-12 16:20:27 | -139 | -102 | E | R | R |
| pandas-dev__pandas-63945 | 2026-01-30 04:30:20 | -121 | -84 | F | R | F |
| keras-team__keras-22316 | 2026-03-01 00:54:12 | -91 | -54 | F | R | E |
| hiero-ledger__hiero-sdk-python-1914_interface | 2026-03-06 14:12:44 | -86 | -49 | F | R | F |
| zauberzeug__nicegui-5858 | 2026-03-09 16:34:24 | -83 | -46 | E | R | R |
| getmoto__moto-9841 | 2026-03-09 23:11:49 | -83 | -46 | F | R | R |
| conan-io__conan-19735_interface | 2026-03-10 10:33:02 | -82 | -45 | E | R | F |
| conan-io__conan-19750 | 2026-03-13 10:20:23 | -79 | -42 | F | F | F |
| idaholab__montepy-933_interface | 2026-03-20 15:47:06 | -72 | -35 | F | R | R |
| harumiweb__exstruct-113 | 2026-03-21 08:53:23 | -71 | -34 | F | R! | E |
| ucfopen__canvasapi-716 | 2026-03-31 19:11:13 | -61 | -24 | E | R | F |
| line__line-bot-sdk-python-981_interface | 2026-04-01 07:44:57 | -60 | -23 | F | R | R |
| keras-team__keras-22642 | 2026-04-06 21:57:28 | -55 | -18 | F | R | R |
| pyinfra-dev__pyinfra-1665 | 2026-04-14 07:06:21 | -47 | -10 | F | R | R |
| alibaba__opensandbox-816 | 2026-04-29 07:35:36 | -32 | **+5** | E | F | F |
| hkuds__openharness-217 | 2026-04-30 00:28:27 | -31 | **+6** | F | R | R |
| tox-dev__tox-3931 | 2026-05-01 15:37:40 | -30 | **+7** | F | R | R |
| raullenchai__rapid-mlx-289 | 2026-05-07 19:33:12 | -24 | **+13** | F | R | R |

## Table 3 — the comparisons, and which ones may mean anything

Paired over instances where BOTH arms have an audited-valid row.
`only-A / only-B` are the discordant cells McNemar's exact test uses;
the concordant cells carry no information about a difference.

| comparison | harness varies? | model varies? | paired n | only-A / only-B | McNemar exact p | what it isolates |
|---|---|---|---:|---:|---:|---|
| bare vs claude | yes | yes | 19 | 0 / 17 | <0.001 | **nothing attributable** — reference point only |
| bare vs factory | yes | n/a (nominal model not recorded) | 19 | 0 / 11 | <0.001 | **n/a — one half of the pair is unrecorded** |
| claude vs factory | yes | n/a (nominal model not recorded) | 19 | 6 / 0 | 0.031 | **n/a — one half of the pair is unrecorded** |

† nominal models match but the observed ledgers differ — the chain
escalates a stuck dev to a harder tier, so a matched-weights claim must
be checked against Table 4's per-tier call counts, not against config.

### High-margin stratum, within each arm

Descriptive only: the stratum is whatever instances post-date the arm's
OWN nominal model's bound, and at this n it is a handful of rows.

| arm | bound | high-margin | rest |
|---|---|---:|---:|
| bare | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 0/4 = 0% | 0/15 = 0% |
| claude | `claude-opus-5` after 2026-05-31 (published-cutoff) | n/a (0 in denominator) | 17/19 = 89% |
| factory | n/a (no bound for an unrecorded model) | n/a | n/a |

## Table 4 — provenance and integrity, per arm

`attempts` exists because the retracted run published 4 second attempts
after the integrity gate invalidated the first, disclosed nowhere. Any
value > 1 is a protocol violation, not a data point.

| arm | resolved model id(s) | per-tier call counts | max attempt | audit ok / invalid | action trails present | test files stripped | oracle-probe hits | p2p empty rows | p2p source(s) |
|---|---|---|---:|---|---|---:|---:|---:|---|
| bare | `azure/deepseek-v4-pro` | n/a (not recorded by these rows) | 1 | 19 ok / 0 invalid | n/a (not recorded) | 0 | n/a (not recorded) | 2 | n/a |
| claude | `claude-opus-5` | n/a (not recorded by these rows) | 1 | 19 ok / 0 invalid | n/a (not recorded) | 23 | n/a (not recorded) | 2 | n/a |
| factory | n/a (none recorded) | n/a (not recorded by these rows) | 1 | 19 ok / 0 invalid | n/a (not recorded) | 19 | n/a (not recorded) | 2 | n/a |

An `p2p empty rows` count above 0 is a real property of the suite, not a
harness fault: those instances declare NO PASS_TO_PASS, so their grade
has no regression half and a patch cannot be caught breaking anything.

Model bounds used for the margin columns:

| model | bound | type |
|---|---|---|
| `claude-opus-4-8` | 2026-01-31 | published-cutoff |
| `claude-opus-5` | 2026-05-31 | published-cutoff |
| `deepseek-v4-pro` | 2026-04-24 | release-date-proxy |
| `gpt-5.3-codex` | 2025-08-31 | published-cutoff |
| `gpt-5.4` | 2025-08-31 | published-cutoff |

## Table 5 — chain-verdict quality

`factory says green` is the chain's OWN verdict (it reached
`reviewer_done`: dev got its tests green and the reviewer approved).
These are **chain-verdict** precision/recall, NOT merge-gate precision —
this harness drives dev+review only; no merge gate runs.

| arm | quantity | value | 95% CI |
|---|---|---|---|
| bare | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| bare | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| factory | chain-verdict precision (oracle passes \| chain said green) | 11/16 = 69% | [41%, 89%] |
| factory | chain-verdict recall (chain said green \| oracle passes) | 11/11 = 100% | [72%, 100%] |
| factory | reviewer cycles, distribution | 0x15, 1x4 | — |
| factory | dev retries, distribution | 0x14, 1x4, 3x1 | — |

## bare — gate accounting

- harness: hand-rolled text loop, no tool calls
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **0/19 = 0% audited-valid**, 95% CI [0%, 18%]

## claude — gate accounting

- harness: Claude Code CLI
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 1 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **17/19 = 89% audited-valid**, 95% CI [67%, 99%]

## factory — gate accounting

- harness: software-factory chain on OpenHands
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **11/19 = 58% audited-valid**, 95% CI [33%, 80%]

## Discarded runs (attempt > 1)

None — every published row is its cell's first attempt.

## Per-row ledger

The row-level evidence every table above is derived from. `p2p` is the
instance's PASS_TO_PASS count: a **0** means the grade has no regression
half at all, so nothing there can catch a patch breaking the suite.

| instance | arm | model(s) | attempt | budget | factory says | oracle | audit | outcome | p2p | fresh in | cache read | tokens out | wall s | $ |
|---|---|---|---:|:-:|---|---|---|---|---:|---:|---:|---:|---:|
| alibaba__opensandbox-816 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 108 | 503,319 | 0 | 77,755 | 1039.6 | 1.12 |
| alibaba__opensandbox-816 | claude | claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 108 | 66,404 | 1,241,268 | 25,880 | 375.9 | 1.92 |
| alibaba__opensandbox-816 | factory | ? | 1 | — | green | FAIL | ok | wrong_place | 108 | 311,767 | 1,621,504 | 15,629 | 641.9 | 0.93 |
| conan-io__conan-19735_interface | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 14 | 4,118 | 0 | 369 | 15.6 | 0.01 |
| conan-io__conan-19735_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 14 | 15,462 | 224,784 | 4,095 | 74.3 | 0.36 |
| conan-io__conan-19735_interface | factory | ? | 1 | — | green | FAIL | ok | right_place_wrong_fix | 14 | 209,894 | 417,792 | 6,044 | 447.3 | 0.50 |
| conan-io__conan-19750 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | wrong_place | 18 | 238,763 | 0 | 60,701 | 818.3 | 0.52 |
| conan-io__conan-19750 | claude | claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 18 | 25,002 | 466,400 | 6,514 | 150.2 | 0.62 |
| conan-io__conan-19750 | factory | ? | 1 | — | green | FAIL | ok | right_place_wrong_fix | 18 | 520,464 | 1,702,656 | 19,814 | 1133.8 | 1.37 |
| getmoto__moto-9841 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 149 | 7,937 | 0 | 1,114 | 30.2 | 0.02 |
| getmoto__moto-9841 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 149 | 32,280 | 631,480 | 9,641 | 227.6 | 0.86 |
| getmoto__moto-9841 | factory | ? | 1 | — | green | PASS | ok | resolved | 149 | 288,279 | 1,190,400 | 14,823 | 266.8 | 0.81 |
| harumiweb__exstruct-113 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | wrong_place | 6 | 15,388 | 0 | 4,011 | 59.4 | 0.04 |
| harumiweb__exstruct-113 | claude | claude-opus-5 | 1 | ! | n/a | PASS | ok | resolved | 6 | 110,744 | 5,393,092 | 43,109 | 633.3 | 4.86 |
| harumiweb__exstruct-113 | factory | ? | 1 | — | not green | FAIL | ok | empty_patch | 6 | 1,199,430 | 1,582,336 | 26,497 | 1101.9 | 2.67 |
| hiero-ledger__hiero-sdk-python-1914_interface | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 9 | 3,234 | 0 | 1,176 | 21.0 | 0.01 |
| hiero-ledger__hiero-sdk-python-1914_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 9 | 50,337 | 920,558 | 19,097 | 270.5 | 1.42 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | ? | 1 | — | green | FAIL | ok | right_place_wrong_fix | 9 | 981,971 | 3,599,104 | 49,016 | 1279.4 | 2.70 |
| hkuds__openharness-217 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 2 | 32,136 | 0 | 3,653 | 114.7 | 0.04 |
| hkuds__openharness-217 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 33,655 | 193,947 | 6,409 | 94.4 | 0.58 |
| hkuds__openharness-217 | factory | ? | 1 | — | green | PASS | ok | resolved | 2 | 284,270 | 284,416 | 7,250 | 159.4 | 0.63 |
| idaholab__montepy-933_interface | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 40 | 17,003 | 0 | 2,333 | 41.4 | 0.02 |
| idaholab__montepy-933_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 40 | 66,393 | 2,411,185 | 19,644 | 353.9 | 2.34 |
| idaholab__montepy-933_interface | factory | ? | 1 | — | green | PASS | ok | resolved | 40 | 705,664 | 3,487,616 | 45,129 | 1417.7 | 2.45 |
| jsonpickle__jsonpickle-588 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 82 | 3,745 | 0 | 49 | 12.6 | 0.00 |
| jsonpickle__jsonpickle-588 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 82 | 99,373 | 3,981,358 | 51,944 | 825.3 | 4.26 |
| jsonpickle__jsonpickle-588 | factory | ? | 1 | — | green | PASS | ok | resolved | 82 | 1,662,075 | 5,452,288 | 87,747 | 2078.4 | 4.55 |
| keras-team__keras-22316 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | wrong_place | 8 | 51,997 | 0 | 22,269 | 393.8 | 0.17 |
| keras-team__keras-22316 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 8 | 62,961 | 2,167,543 | 23,081 | 619.8 | 2.28 |
| keras-team__keras-22316 | factory | ? | 1 | — | not green | FAIL | ok | empty_patch | 8 | 48,714 | 114,688 | 5,772 | 160.1 | 0.13 |
| keras-team__keras-22642 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 16 | 339,249 | 0 | 104,182 | 1413.2 | 0.84 |
| keras-team__keras-22642 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 16 | 28,752 | 723,701 | 9,543 | 172.5 | 0.87 |
| keras-team__keras-22642 | factory | ? | 1 | — | green | PASS | ok | resolved | 16 | 294,493 | 1,164,288 | 11,189 | 530.0 | 0.80 |
| line__line-bot-sdk-python-981_interface | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | **0 (no regression half)** | 10,718 | 0 | 2,377 | 107.6 | 0.02 |
| line__line-bot-sdk-python-981_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | **0 (no regression half)** | 81,094 | 2,896,280 | 33,081 | 477.2 | 3.07 |
| line__line-bot-sdk-python-981_interface | factory | ? | 1 | — | green | PASS | ok | resolved | **0 (no regression half)** | 807,015 | 2,557,696 | 34,806 | 641.9 | 2.12 |
| pandas-dev__pandas-63945 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | **0 (no regression half)** | 18,889 | 0 | 6,732 | 164.4 | 0.05 |
| pandas-dev__pandas-63945 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | **0 (no regression half)** | 31,086 | 769,217 | 11,065 | 284.4 | 0.95 |
| pandas-dev__pandas-63945 | factory | ? | 1 | — | not green | FAIL | ok | right_place_wrong_fix | **0 (no regression half)** | 277,464 | 1,434,880 | 24,671 | 709.3 | 1.05 |
| pyinfra-dev__pyinfra-1665 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 33 | 33,699 | 0 | 9,202 | 133.1 | 0.06 |
| pyinfra-dev__pyinfra-1665 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 33 | 47,018 | 571,977 | 7,584 | 133.8 | 0.92 |
| pyinfra-dev__pyinfra-1665 | factory | ? | 1 | — | green | PASS | ok | resolved | 33 | 550,546 | 669,696 | 8,844 | 296.1 | 1.21 |
| raullenchai__rapid-mlx-289 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 122 | 65,346 | 0 | 18,142 | 208.4 | 0.14 |
| raullenchai__rapid-mlx-289 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 122 | 125,764 | 4,335,697 | 62,922 | 812.4 | 4.94 |
| raullenchai__rapid-mlx-289 | factory | ? | 1 | — | green | PASS | ok | resolved | 122 | 955,071 | 3,434,240 | 48,780 | 1467.4 | 2.69 |
| tox-dev__tox-3931 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 2 | 32,099 | 0 | 15,721 | 171.4 | 0.10 |
| tox-dev__tox-3931 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 45,370 | 572,785 | 6,973 | 127.6 | 0.90 |
| tox-dev__tox-3931 | factory | ? | 1 | — | green | PASS | ok | resolved | 2 | 502,601 | 2,263,808 | 19,021 | 513.9 | 1.41 |
| ucfopen__canvasapi-716 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 60 | 161,477 | 0 | 11,563 | 169.4 | 0.27 |
| ucfopen__canvasapi-716 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 60 | 24,681 | 455,012 | 7,496 | 125.4 | 0.65 |
| ucfopen__canvasapi-716 | factory | ? | 1 | — | green | FAIL | ok | right_place_wrong_fix | 60 | 292,284 | 704,256 | 9,031 | 273.7 | 0.71 |
| vyperlang__vyper-4801 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 1 | 38,966 | 0 | 27,504 | 322.9 | 0.14 |
| vyperlang__vyper-4801 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 1 | 50,606 | 1,636,959 | 17,841 | 1909.1 | 1.75 |
| vyperlang__vyper-4801 | factory | ? | 1 | — | green | PASS | ok | resolved | 1 | 499,065 | 4,236,800 | 39,474 | 1246.8 | 2.06 |
| zauberzeug__nicegui-5858 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 3 | 6,120 | 0 | 710 | 37.0 | 0.01 |
| zauberzeug__nicegui-5858 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 3 | 37,216 | 1,206,043 | 13,508 | 276.0 | 1.29 |
| zauberzeug__nicegui-5858 | factory | ? | 1 | — | green | PASS | ok | resolved | 3 | 113,247 | 841,472 | 10,367 | 260.2 | 0.40 |

## Excluded-row disclosure

n/a (archive predates `report-meta.json` version 1.6, which is the first to PERSIST the refused
and foreign row lists). Rows refused or excluded when this archive was
made cannot be recovered from it — that gap is exactly why the lists
are persisted now.

> **n=19 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on; k>=3 is required before any delta from this suite is quoted as a result.

> Cost columns are NOT comparable across arms and must never be summed: the Azure arms' dollars are a price-table estimate over measured tokens, the Claude arms' are the CLI's own report against a subscription.
