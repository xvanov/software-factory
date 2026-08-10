# SWE-rebench — externally graded

Generated 2026-08-10T21:53:14.959258+00:00.

Every row here is backed by the evidence snapshot in
`bench/swebench/results-archive/2026-08-10T21-53-14.959258Z/`, and
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
| claude-5 | Claude Code CLI | `claude-haiku-4-5-20251001` (17 rows, calls not recorded), `claude-opus-5` (18 rows, calls not recorded) | 11/14 | 11/14 = 79% | [49%, 95%] | 4 | 2 | 944,351 | 25,938,972 | 325,108 | 263.6 | 30.18 | CLI-reported, subscription |
| factory | software-factory chain on OpenHands | `azure/Kimi-K2.7-Code` (45 calls), `azure/deepseek-v4-pro` (35 calls) | 10/19 | 10/19 = 53% | [29%, 76%] | 0 | 0 | 21,104,155 | 26,849,792 | 1,262,586 | 1038.0 | 50.18 | price-table estimate |
| solo-noreview | software-factory chain, dev only (no reviewer round-trip) | `azure/Kimi-K2.7-Code` (19 calls), `azure/deepseek-v4-pro` (26 calls) | 9/19 | 9/19 = 47% | [24%, 71%] | 0 | 0 | 22,392,133 | 22,805,760 | 744,760 | 976.0 | 49.89 | price-table estimate |

## Table 2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken · `X` audit-invalid or run-failed · `!` budget-exhausted (counted as an attempt, not excluded) · `*` attempt > 1 · `·` no row

A POSITIVE margin means the instance was created after that model's
bound, i.e. it cannot have been memorised. Bound TYPE is in Table 4's
footnote: a published cutoff and a release-date proxy are different
claims.

| instance | created_at | margin vs `claude-opus-5` (2026-05-31) | margin vs `deepseek-v4-pro` (2026-04-24) | claude-5 | factory | solo-noreview |
|---|---|---:|---:|:-:|:-:|:-:|
| vyperlang__vyper-4801 | 2026-01-03 21:33:22 | -148 | -111 | X | E | F |
| jsonpickle__jsonpickle-588 | 2026-01-12 16:20:27 | -139 | -102 | X | F | R |
| pandas-dev__pandas-63945 | 2026-01-30 04:30:20 | -121 | -84 | F | F | F |
| keras-team__keras-22316 | 2026-03-01 00:54:12 | -91 | -54 | R | R | R |
| hiero-ledger__hiero-sdk-python-1914_interface | 2026-03-06 14:12:44 | -86 | -49 | · | R | F |
| zauberzeug__nicegui-5858 | 2026-03-09 16:34:24 | -83 | -46 | X | R | R |
| getmoto__moto-9841 | 2026-03-09 23:11:49 | -83 | -46 | R* | R | R |
| conan-io__conan-19735_interface | 2026-03-10 10:33:02 | -82 | -45 | R* | R | F |
| conan-io__conan-19750 | 2026-03-13 10:20:23 | -79 | -42 | F | E | F |
| idaholab__montepy-933_interface | 2026-03-20 15:47:06 | -72 | -35 | R | F | F |
| harumiweb__exstruct-113 | 2026-03-21 08:53:23 | -71 | -34 | R! | F | F |
| ucfopen__canvasapi-716 | 2026-03-31 19:11:13 | -61 | -24 | R | F | F |
| line__line-bot-sdk-python-981_interface | 2026-04-01 07:44:57 | -60 | -23 | X | R | R |
| keras-team__keras-22642 | 2026-04-06 21:57:28 | -55 | -18 | R | R | R |
| pyinfra-dev__pyinfra-1665 | 2026-04-14 07:06:21 | -47 | -10 | R | R | R |
| alibaba__opensandbox-816 | 2026-04-29 07:35:36 | -32 | **+5** | F | F | F |
| hkuds__openharness-217 | 2026-04-30 00:28:27 | -31 | **+6** | R | R | R |
| tox-dev__tox-3931 | 2026-05-01 15:37:40 | -30 | **+7** | R | E | R |
| raullenchai__rapid-mlx-289 | 2026-05-07 19:33:12 | -24 | **+13** | R! | R | F |

## Table 3 — the comparisons, and which ones may mean anything

Paired over instances where BOTH arms have an audited-valid row.
`only-A / only-B` are the discordant cells McNemar's exact test uses;
the concordant cells carry no information about a difference.

| comparison | harness varies? | model varies? | paired n | only-A / only-B | McNemar exact p | what it isolates |
|---|---|---|---:|---:|---:|---|
| claude-5 vs factory | yes | yes | 14 | 4 / 0 | 0.125 | **nothing attributable** — reference point only |
| claude-5 vs solo-noreview | yes | yes | 14 | 5 / 0 | 0.062 | **nothing attributable** — reference point only |
| factory vs solo-noreview | yes | no | 19 | 3 / 2 | 1.000 | the harness |

† nominal models match but the observed ledgers differ — the chain
escalates a stuck dev to a harder tier, so a matched-weights claim must
be checked against Table 4's per-tier call counts, not against config.

### High-margin stratum, within each arm

Descriptive only: the stratum is whatever instances post-date the arm's
OWN nominal model's bound, and at this n it is a handful of rows.

| arm | bound | high-margin | rest |
|---|---|---:|---:|
| claude-5 | `claude-opus-5` after 2026-05-31 (published-cutoff) | n/a (0 in denominator) | 11/14 = 79% |
| factory | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 2/4 = 50% | 8/15 = 53% |
| solo-noreview | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 2/4 = 50% | 7/15 = 47% |

## Table 4 — provenance and integrity, per arm

`attempts` exists because the retracted run published 4 second attempts
after the integrity gate invalidated the first, disclosed nowhere. Any
value > 1 is a protocol violation, not a data point.

| arm | resolved model id(s) | per-tier call counts | max attempt | audit ok / invalid | action trails present | test files stripped | oracle-probe hits | p2p empty rows | p2p source(s) |
|---|---|---|---:|---|---|---:|---:|---:|---|
| claude-5 | `claude-haiku-4-5-20251001`, `claude-opus-5` | —=0 | 2 | 18 ok / 0 invalid | 18/18 | 43 | 0 | 0 | dataset, declared_test_targets |
| factory | `azure/Kimi-K2.7-Code`, `azure/deepseek-v4-pro` | hard=8, standard=27, —=45 | 1 | 19 ok / 0 invalid | 19/19 | 44 | 0 | 0 | dataset, declared_test_targets |
| solo-noreview | `azure/Kimi-K2.7-Code`, `azure/deepseek-v4-pro` | hard=7, standard=19, —=19 | 1 | 19 ok / 0 invalid | 19/19 | 46 | 0 | 0 | dataset, declared_test_targets |

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
| claude-5 | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude-5 | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| factory | chain-verdict precision (oracle passes \| chain said green) | 10/14 = 71% | [42%, 92%] |
| factory | chain-verdict recall (chain said green \| oracle passes) | 10/10 = 100% | [69%, 100%] |
| factory | reviewer cycles, distribution | 0x10, 1x7, 2x2 | — |
| factory | dev retries, distribution | 0x15, 1x2, 2x1, 4x1 | — |
| solo-noreview | chain-verdict precision (oracle passes \| chain said green) | 9/17 = 53% | [28%, 77%] |
| solo-noreview | chain-verdict recall (chain said green \| oracle passes) | 9/9 = 100% | [66%, 100%] |
| solo-noreview | reviewer cycles, distribution | 0x19 | — |
| solo-noreview | dev retries, distribution | 0x15, 1x1, 2x2, 4x1 | — |

## claude-5 — gate accounting

- harness: Claude Code CLI
- graded instances: **18** (0 excluded as `task_broken`, leaving 18)
- audit gate: **14 audited-valid** of 18 gradable (audit failed: 0, not audited: 0, run failed: 4)
- budget-exhausted, COUNTED as attempts: 2 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **11/14 = 79% audited-valid**, 95% CI [49%, 95%]
- **4 row(s) EXCLUDED from the denominator, passes AND failures named**: jsonpickle__jsonpickle-588 [PASS]: run failed (claude CLI exited 1:); line__line-bot-sdk-python-981_interface [FAIL]: run failed (claude CLI exited 1:); vyperlang__vyper-4801 [FAIL]: run failed (claude CLI exited 1:); zauberzeug__nicegui-5858 [PASS]: run failed (claude CLI exited 1:)

## factory — gate accounting

- harness: software-factory chain on OpenHands
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **10/19 = 53% audited-valid**, 95% CI [29%, 76%]

## solo-noreview — gate accounting

- harness: software-factory chain, dev only (no reviewer round-trip)
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **19 audited-valid** of 19 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **9/19 = 47% audited-valid**, 95% CI [24%, 71%]

## Discarded runs (attempt > 1)

Each row below is a RE-RUN of a cell that had already been attempted.
The retracted run published 4 second attempts after the integrity gate
invalidated the first, disclosed nowhere; under the no-re-rolls rule any
row here is a protocol violation, not a data point.

- `conan-io__conan-19735_interface/claude-5` — attempt 2
- `getmoto__moto-9841/claude-5` — attempt 2

## Per-row ledger

The row-level evidence every table above is derived from. `p2p` is the
instance's PASS_TO_PASS count: a **0** means the grade has no regression
half at all, so nothing there can catch a patch breaking the suite.

| instance | arm | model(s) | attempt | budget | factory says | oracle | audit | outcome | p2p | fresh in | cache read | tokens out | wall s | $ |
|---|---|---|---:|:-:|---|---|---|---|---:|---:|---:|---:|---:|
| alibaba__opensandbox-816 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 108 | 62,802 | 1,281,009 | 22,030 | 310.5 | 1.80 |
| alibaba__opensandbox-816 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | wrong_place | 108 | 3,402,901 | 1,881,408 | 109,477 | 2545.8 | 7.32 |
| alibaba__opensandbox-816 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 108 | 894,379 | 1,001,344 | 25,373 | 1026.7 | 1.99 |
| conan-io__conan-19735_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 2 | — | n/a | PASS | ok | resolved | 14 | 30,839 | 206,109 | 3,796 | 85.9 | 0.49 |
| conan-io__conan-19735_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 14 | 261,698 | 568,832 | 15,363 | 243.1 | 0.66 |
| conan-io__conan-19735_interface | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 14 | 304,995 | 175,552 | 6,108 | 254.6 | 0.64 |
| conan-io__conan-19750 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 18 | 33,726 | 802,211 | 9,586 | 271.6 | 0.95 |
| conan-io__conan-19750 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | empty_patch | 18 | 315,857 | 233,984 | 15,248 | 402.2 | 0.71 |
| conan-io__conan-19750 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 18 | 1,522,692 | 507,072 | 35,085 | 1187.2 | 3.16 |
| getmoto__moto-9841 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 2 | — | n/a | PASS | ok | resolved | 149 | 51,471 | 679,573 | 11,468 | 232.8 | 1.12 |
| getmoto__moto-9841 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 149 | 1,036,213 | 2,200,256 | 155,076 | 2417.5 | 3.00 |
| getmoto__moto-9841 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 149 | 758,742 | 581,504 | 63,671 | 839.7 | 1.83 |
| harumiweb__exstruct-113 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | ! | n/a | PASS | ok | resolved | 6 | 128,166 | 5,800,718 | 55,455 | 780.1 | 5.55 |
| harumiweb__exstruct-113 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | wrong_place | 6 | 1,025,331 | 1,053,056 | 40,013 | 840.0 | 2.31 |
| harumiweb__exstruct-113 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | wrong_place | 6 | 1,098,130 | 1,157,312 | 26,422 | 1045.8 | 2.41 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 9 | 1,310,931 | 2,547,456 | 74,052 | 1482.3 | 3.23 |
| hiero-ledger__hiero-sdk-python-1914_interface | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 9 | 1,418,068 | 1,701,312 | 63,327 | 976.0 | 3.27 |
| hkuds__openharness-217 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 33,592 | 190,556 | 5,573 | 82.0 | 0.55 |
| hkuds__openharness-217 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 2 | 451,105 | 809,728 | 77,415 | 1005.2 | 1.32 |
| hkuds__openharness-217 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 2 | 560,976 | 815,616 | 18,756 | 557.9 | 1.29 |
| idaholab__montepy-933_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 40 | 58,966 | 1,905,171 | 16,990 | 289.1 | 1.95 |
| idaholab__montepy-933_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 40 | 767,656 | 976,896 | 74,273 | 1004.0 | 1.95 |
| idaholab__montepy-933_interface | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 40 | 1,329,751 | 1,534,976 | 68,614 | 1287.7 | 3.10 |
| jsonpickle__jsonpickle-588 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 82 | 80,846 | 2,083,568 | 36,696 | 507.9 | 2.74 |
| jsonpickle__jsonpickle-588 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | right_place_wrong_fix | 82 | 849,683 | 1,098,176 | 33,784 | 743.1 | 1.95 |
| jsonpickle__jsonpickle-588 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 82 | 1,806,258 | 1,655,296 | 71,021 | 1983.0 | 4.04 |
| keras-team__keras-22316 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 8 | 47,366 | 1,439,893 | 18,990 | 696.7 | 1.65 |
| keras-team__keras-22316 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 8 | 1,338,699 | 700,288 | 70,421 | 1568.7 | 2.99 |
| keras-team__keras-22316 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 8 | 1,006,362 | 1,088,384 | 36,401 | 1081.7 | 2.26 |
| keras-team__keras-22642 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 16 | 21,794 | 373,940 | 5,111 | 107.3 | 0.52 |
| keras-team__keras-22642 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 16 | 1,125,206 | 2,012,608 | 43,874 | 1264.4 | 2.66 |
| keras-team__keras-22642 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 16 | 983,602 | 1,040,064 | 15,438 | 696.9 | 2.13 |
| line__line-bot-sdk-python-981_interface | claude-5 | claude-opus-5 | 1 | — | n/a | FAIL | ok | empty_patch | 1 | 0 | 0 | 0 | 11.5 | 0.00 |
| line__line-bot-sdk-python-981_interface | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 1 | 1,045,266 | 2,291,328 | 203,915 | 2508.9 | 3.24 |
| line__line-bot-sdk-python-981_interface | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 1 | 1,308,962 | 895,104 | 52,725 | 1114.6 | 2.89 |
| pandas-dev__pandas-63945 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 14 | 33,496 | 780,403 | 8,900 | 255.7 | 0.93 |
| pandas-dev__pandas-63945 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | right_place_wrong_fix | 14 | 1,017,239 | 486,848 | 18,924 | 1038.0 | 2.12 |
| pandas-dev__pandas-63945 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | right_place_wrong_fix | 14 | 595,572 | 744,064 | 21,515 | 724.7 | 1.35 |
| pyinfra-dev__pyinfra-1665 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 33 | 45,583 | 481,903 | 6,331 | 113.7 | 0.83 |
| pyinfra-dev__pyinfra-1665 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 33 | 363,838 | 519,872 | 23,433 | 370.7 | 0.88 |
| pyinfra-dev__pyinfra-1665 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 33 | 453,976 | 877,248 | 13,773 | 315.9 | 1.07 |
| raullenchai__rapid-mlx-289 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | ! | n/a | PASS | ok | resolved | 122 | 150,996 | 6,511,459 | 75,928 | 996.2 | 6.61 |
| raullenchai__rapid-mlx-289 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 122 | 2,451,314 | 968,192 | 79,788 | 1488.3 | 5.20 |
| raullenchai__rapid-mlx-289 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | right_place_wrong_fix | 122 | 3,867,734 | 4,291,392 | 118,074 | 4457.7 | 8.61 |
| tox-dev__tox-3931 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 50,104 | 949,246 | 10,443 | 190.1 | 1.22 |
| tox-dev__tox-3931 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | empty_patch | 2 | 1,571,026 | 1,576,960 | 58,949 | 1198.1 | 3.52 |
| tox-dev__tox-3931 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 2 | 978,029 | 767,040 | 25,374 | 754.7 | 2.11 |
| ucfopen__canvasapi-716 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 60 | 45,144 | 1,245,167 | 20,140 | 283.8 | 1.56 |
| ucfopen__canvasapi-716 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 60 | 283,572 | 566,400 | 25,549 | 375.8 | 0.74 |
| ucfopen__canvasapi-716 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | right_place_wrong_fix | 60 | 424,363 | 680,832 | 13,344 | 439.4 | 0.98 |
| vyperlang__vyper-4801 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | ok | empty_patch | 1 | 46,307 | 752,861 | 11,979 | 189.9 | 1.12 |
| vyperlang__vyper-4801 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | not green | FAIL | ok | empty_patch | 1 | 2,206,894 | 5,543,040 | 98,678 | 3327.4 | 5.53 |
| vyperlang__vyper-4801 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | FAIL | ok | wrong_place | 1 | 2,673,952 | 2,876,288 | 51,314 | 2479.9 | 5.83 |
| zauberzeug__nicegui-5858 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 3 | 23,153 | 455,185 | 5,692 | 106.4 | 0.58 |
| zauberzeug__nicegui-5858 | factory | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 3 | 279,726 | 814,464 | 44,354 | 678.1 | 0.86 |
| zauberzeug__nicegui-5858 | solo-noreview | azure/Kimi-K2.7-Code, azure/deepseek-v4-pro | 1 | — | green | PASS | ok | resolved | 3 | 405,590 | 415,360 | 18,425 | 481.3 | 0.92 |

> **n=19 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on; k>=3 is required before any delta from this suite is quoted as a result.

> Cost columns are NOT comparable across arms and must never be summed: the Azure arms' dollars are a price-table estimate over measured tokens, the Claude arms' are the CLI's own report against a subscription.
