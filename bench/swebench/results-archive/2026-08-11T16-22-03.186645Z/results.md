# SWE-rebench — externally graded

Generated 2026-08-11T16:22:03.186645+00:00.

Every row here is backed by the evidence snapshot in
`bench/swebench/results-archive/2026-08-11T16-22-03.186645Z/`, and
`report --check` asserts that this table is still byte-for-byte
re-derivable from it.

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
| factory | software-factory chain on OpenHands | `azure/Kimi-K2.7-Code` (44 calls), `azure/deepseek-v4-pro` (40 calls) | 10/17 | 10/17 = 59% | [33%, 82%] | 1 | 0 | 34,632,647 | 46,529,792 | 1,652,985 | 1510.5 | 81.00 | price-table estimate |

## Table 2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken · `X` audit-invalid or run-failed · `!` budget-exhausted (counted as an attempt, not excluded) · `*` attempt > 1 · `·` no row

A POSITIVE margin means the instance was created after that model's
bound, i.e. it cannot have been memorised. Bound TYPE is in Table 4's
footnote: a published cutoff and a release-date proxy are different
claims.

| instance | created_at | margin vs `deepseek-v4-pro` (2026-04-24) | factory |
|---|---|---:|:-:|
| vyperlang__vyper-4801 | 2026-01-03 21:33:22 | -111 | X! |
| jsonpickle__jsonpickle-588 | 2026-01-12 16:20:27 | -102 | R |
| keras-team__keras-22316 | 2026-03-01 00:54:12 | -54 | R |
| hiero-ledger__hiero-sdk-python-1914_interface | 2026-03-06 14:12:44 | -49 | F |
| zauberzeug__nicegui-5858 | 2026-03-09 16:34:24 | -46 | R |
| getmoto__moto-9841 | 2026-03-09 23:11:49 | -46 | R |
| conan-io__conan-19735_interface | 2026-03-10 10:33:02 | -45 | R |
| conan-io__conan-19750 | 2026-03-13 10:20:23 | -42 | F |
| idaholab__montepy-933_interface | 2026-03-20 15:47:06 | -35 | F |
| harumiweb__exstruct-113 | 2026-03-21 08:53:23 | -34 | E |
| ucfopen__canvasapi-716 | 2026-03-31 19:11:13 | -24 | R |
| line__line-bot-sdk-python-981_interface | 2026-04-01 07:44:57 | -23 | F |
| keras-team__keras-22642 | 2026-04-06 21:57:28 | -18 | R |
| pyinfra-dev__pyinfra-1665 | 2026-04-14 07:06:21 | -10 | R |
| alibaba__opensandbox-816 | 2026-04-29 07:35:36 | **+5** | F |
| hkuds__openharness-217 | 2026-04-30 00:28:27 | **+6** | F |
| tox-dev__tox-3931 | 2026-05-01 15:37:40 | **+7** | R |
| raullenchai__rapid-mlx-289 | 2026-05-07 19:33:12 | **+13** | R |

## Table 3 — the comparisons, and which ones may mean anything

Paired over instances where BOTH arms have an audited-valid row.
`only-A / only-B` are the discordant cells McNemar's exact test uses;
the concordant cells carry no information about a difference.

| comparison | harness varies? | model varies? | paired n | only-A / only-B | McNemar exact p | what it isolates |
|---|---|---|---:|---:|---:|---|

† nominal models match but the observed ledgers differ — the chain
escalates a stuck dev to a harder tier, so a matched-weights claim must
be checked against Table 4's per-tier call counts, not against config.

### High-margin stratum, within each arm

Descriptive only: the stratum is whatever instances post-date the arm's
OWN nominal model's bound, and at this n it is a handful of rows.

| arm | bound | high-margin | rest |
|---|---|---:|---:|
| factory | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 2/4 = 50% | 8/13 = 62% |

## Table 4 — provenance and integrity, per arm

`attempts` exists because the retracted run published 4 second attempts
after the integrity gate invalidated the first, disclosed nowhere. Any
value > 1 is a protocol violation, not a data point.

| arm | resolved model id(s) | per-tier call counts | max attempt | audit ok / invalid | action trails present | test files stripped | oracle-probe hits | p2p empty rows | p2p source(s) |
|---|---|---|---:|---|---|---:|---:|---:|---|
| factory | `azure/Kimi-K2.7-Code`, `azure/deepseek-v4-pro` | hard=15, standard=25, —=44 | 1 | 17 ok / 1 invalid | 18/18 | 33 | 3 | 0 | dataset, declared_test_targets |

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
| factory | chain-verdict precision (oracle passes \| chain said green) | 7/12 = 58% | [28%, 85%] |
| factory | chain-verdict recall (chain said green \| oracle passes) | 7/10 = 70% | [35%, 93%] |
| factory | reviewer cycles, distribution | 0x7, 1x7, 2x2, 3x1 | — |
| factory | dev retries, distribution | 0x12, 1x1, 2x3, 4x1 | — |

## factory — gate accounting

- harness: software-factory chain on OpenHands
- graded instances: **18** (0 excluded as `task_broken`, leaving 18)
- audit gate: **17 audited-valid** of 18 gradable (audit failed: 1, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **10/17 = 59% audited-valid**, 95% CI [33%, 82%]
- **1 row(s) EXCLUDED from the denominator, passes AND failures named**: vyperlang__vyper-4801 [FAIL]: audit failed

## Discarded runs (attempt > 1)

None — every published row is its cell's first attempt.

## Per-row ledger

The row-level evidence every table above is derived from. `p2p` is the
instance's PASS_TO_PASS count: a **0** means the grade has no regression
half at all, so nothing there can catch a patch breaking the suite.

| instance | arm | model(s) | attempt | budget | factory says | oracle | audit | outcome | p2p | fresh in | cache read | tokens out | wall s | $ |
|---|---|---|---:|:-:|---|---|---|---|---:|---:|---:|---:|---:|
| alibaba__opensandbox-816 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | right_place_wrong_fix | 108 | 1,522,164 | 3,178,624 | 154,461 | 2369.3 | 4.10 |
| conan-io__conan-19735_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 14 | 336,079 | 876,288 | 21,988 | 377.3 | 0.88 |
| conan-io__conan-19750 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 18 | 778,096 | 1,428,928 | 50,768 | 1013.4 | 1.94 |
| getmoto__moto-9841 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 149 | 1,708,014 | 1,747,776 | 97,871 | 2253.1 | 3.97 |
| harumiweb__exstruct-113 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | empty_patch | 6 | 3,958,803 | 5,019,264 | 97,591 | 4710.0 | 8.83 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 9 | 1,611,004 | 1,442,048 | 161,250 | 1803.6 | 4.01 |
| hkuds__openharness-217 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 2 | 253,081 | 457,600 | 35,082 | 562.9 | 0.71 |
| idaholab__montepy-933_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 40 | 1,465,837 | 1,663,360 | 64,928 | 1510.5 | 3.36 |
| jsonpickle__jsonpickle-588 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | PASS | ok | resolved | 82 | 4,535,016 | 5,585,408 | 193,416 | 4774.0 | 10.43 |
| keras-team__keras-22316 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 8 | 2,240,820 | 3,926,208 | 161,172 | 4278.7 | 5.62 |
| keras-team__keras-22642 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 16 | 1,077,550 | 1,040,512 | 32,011 | 957.0 | 2.37 |
| line__line-bot-sdk-python-981_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | patch_did_not_apply | 1 | 2,110,565 | 2,164,544 | 90,486 | 2022.3 | 4.77 |
| pyinfra-dev__pyinfra-1665 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 33 | 404,921 | 794,304 | 27,044 | 522.4 | 1.01 |
| raullenchai__rapid-mlx-289 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 122 | 3,870,241 | 5,190,464 | 192,223 | 4443.1 | 9.06 |
| tox-dev__tox-3931 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | PASS | ok | resolved | 2 | 907,616 | 2,881,024 | 39,442 | 1120.0 | 2.37 |
| ucfopen__canvasapi-716 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | PASS | ok | resolved | 60 | 212,464 | 776,768 | 40,182 | 518.9 | 0.70 |
| vyperlang__vyper-4801 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | ! | not green | FAIL | FAIL | empty_patch | 1 | 6,154,233 | 7,271,360 | 117,804 | 6341.2 | 13.50 |
| zauberzeug__nicegui-5858 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 3 | 1,486,143 | 1,085,312 | 75,266 | 1487.0 | 3.36 |

> **n=18 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on; k>=3 is required before any delta from this suite is quoted as a result.

> Cost columns are NOT comparable across arms and must never be summed: the Azure arms' dollars are a price-table estimate over measured tokens, the Claude arms' are the CLI's own report against a subscription.
