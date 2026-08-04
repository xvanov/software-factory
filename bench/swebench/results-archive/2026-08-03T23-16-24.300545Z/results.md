# SWE-rebench — externally graded

Generated 2026-08-03T23:16:24.300545+00:00.

Every row here is backed by the evidence snapshot in
`bench/swebench/results-archive/2026-08-03T23-16-24.300545Z/`, and
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
| bare | hand-rolled text loop, no tool calls | `azure/deepseek-v4-pro` (727 calls) | 1/13 | 1/13 = 8% | [0%, 36%] | 6 | 11 | 5,115,484 | 0 | 195,740 | 147.2 | 7.94 | price-table estimate |
| claude | Claude Code CLI | `claude-opus-5` (18 rows, calls not recorded) | 16/18 | 16/18 = 89% | [65%, 99%] | 0 | 1 | 1,001,918 | 30,167,806 | 369,786 | 280.2 | 33.98 | CLI-reported, subscription |
| claude-4.8 | Claude Code CLI | `claude-haiku-4-5-20251001` (19 rows, calls not recorded), `claude-opus-4-8` (19 rows, calls not recorded) | 8/9 | 8/9 = 89% | [52%, 100%] | 10 | 1 | 795,380 | 19,525,695 | 308,128 | 169.0 | 23.56 | CLI-reported, subscription |
| claude-5 | Claude Code CLI | `claude-haiku-4-5-20251001` (19 rows, calls not recorded), `claude-opus-5` (19 rows, calls not recorded) | 5/5 | 5/5 = 100% | [48%, 100%] | 14 | 0 | 1,032,242 | 28,972,582 | 397,852 | 266.0 | 34.36 | CLI-reported, subscription |
| factory | software-factory chain on OpenHands | `azure/deepseek-v4-pro` (33 calls), `azure/gpt-5.3-codex` (6 calls), `azure/gpt-5.4` (31 calls) | 2/6 | 2/6 = 33% | [4%, 78%] | 13 | 0 | 14,349,408 | 33,195,520 | 486,506 | 921.6 | 35.94 | price-table estimate |
| openhands | OpenHands single agent, no chain | `azure/deepseek-v4-pro` (19 calls) | 3/8 | 3/8 = 38% | [9%, 76%] | 11 | 0 | 6,796,481 | 9,724,160 | 180,598 | 380.4 | 15.37 | price-table estimate |

## Table 2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken · `X` audit-invalid or run-failed · `!` budget-exhausted (counted as an attempt, not excluded) · `*` attempt > 1 · `·` no row

A POSITIVE margin means the instance was created after that model's
bound, i.e. it cannot have been memorised. Bound TYPE is in Table 4's
footnote: a published cutoff and a release-date proxy are different
claims.

| instance | created_at | margin vs `claude-opus-4-8` (2026-01-31) | margin vs `claude-opus-5` (2026-05-31) | margin vs `deepseek-v4-pro` (2026-04-24) | bare | claude | claude-4.8 | claude-5 | factory | openhands |
|---|---|---:|---:|---:|:-:|:-:|:-:|:-:|:-:|:-:|
| vyperlang__vyper-4801 | 2026-01-03 21:33:22 | -28 | -148 | -111 | E! | R | X | X | X | E |
| jsonpickle__jsonpickle-588 | 2026-01-12 16:20:27 | -19 | -139 | -102 | F! | R | R! | X | X | X |
| pandas-dev__pandas-63945 | 2026-01-30 04:30:20 | -1 | -121 | -84 | F | R | X | X | X | X |
| keras-team__keras-22316 | 2026-03-01 00:54:12 | **+29** | -91 | -54 | X! | R | X | X | X | X |
| hiero-ledger__hiero-sdk-python-1914_interface | 2026-03-06 14:12:44 | **+34** | -86 | -49 | X! | R | R | X | X | F |
| zauberzeug__nicegui-5858 | 2026-03-09 16:34:24 | **+37** | -83 | -46 | X! | R | X | X | X | X |
| getmoto__moto-9841 | 2026-03-09 23:11:49 | **+37** | -83 | -46 | F! | · | R | R | R | R |
| conan-io__conan-19735_interface | 2026-03-10 10:33:02 | **+38** | -82 | -45 | E! | R | X | X | X | X |
| conan-io__conan-19750 | 2026-03-13 10:20:23 | **+41** | -79 | -42 | E! | F | X | X | X | X |
| idaholab__montepy-933_interface | 2026-03-20 15:47:06 | **+48** | -72 | -35 | F! | R | R | R | X | F |
| harumiweb__exstruct-113 | 2026-03-21 08:53:23 | **+49** | -71 | -34 | E! | R! | R | X | E | F |
| ucfopen__canvasapi-716 | 2026-03-31 19:11:13 | **+59** | -61 | -24 | R! | R | R | R | F | R |
| line__line-bot-sdk-python-981_interface | 2026-04-01 07:44:57 | **+60** | -60 | -23 | X! | R | X | X | X | X |
| keras-team__keras-22642 | 2026-04-06 21:57:28 | **+65** | -55 | -18 | E! | R | R | R | R | R |
| pyinfra-dev__pyinfra-1665 | 2026-04-14 07:06:21 | **+73** | -47 | -10 | X! | R | X | X | X | X |
| alibaba__opensandbox-816 | 2026-04-29 07:35:36 | **+88** | -32 | **+5** | F! | F | F | X | F | F |
| hkuds__openharness-217 | 2026-04-30 00:28:27 | **+89** | -31 | **+6** | X! | R | X | X | X | X |
| tox-dev__tox-3931 | 2026-05-01 15:37:40 | **+90** | -30 | **+7** | F | R | X | X | X | X |
| raullenchai__rapid-mlx-289 | 2026-05-07 19:33:12 | **+96** | -24 | **+13** | F! | R | R | R | F | X |

## Table 3 — the comparisons, and which ones may mean anything

Paired over instances where BOTH arms have an audited-valid row.
`only-A / only-B` are the discordant cells McNemar's exact test uses;
the concordant cells carry no information about a difference.

| comparison | harness varies? | model varies? | paired n | only-A / only-B | McNemar exact p | what it isolates |
|---|---|---|---:|---:|---:|---|
| bare vs claude | yes | yes | 12 | 0 / 9 | 0.004 | **nothing attributable** — reference point only |
| bare vs claude-4.8 | yes | yes | 8 | 0 / 6 | 0.031 | **nothing attributable** — reference point only |
| bare vs claude-5 | yes | yes | 5 | 0 / 4 | 0.125 | **nothing attributable** — reference point only |
| bare vs factory | yes | no (nominal) † | 6 | 1 / 2 | 1.000 | the harness |
| bare vs openhands | yes | no | 7 | 0 / 2 | 0.500 | the harness |
| claude vs claude-4.8 | no | yes | 8 | 0 / 0 | 1.000 | the model (same harness) |
| claude vs claude-5 | no | no (nominal) † | 4 | 0 / 0 | 1.000 | nothing — the arms are the same pair |
| claude vs factory | yes | yes | 5 | 3 / 0 | 0.250 | **nothing attributable** — reference point only |
| claude vs openhands | yes | yes | 7 | 4 / 0 | 0.125 | **nothing attributable** — reference point only |
| claude-4.8 vs claude-5 | no | yes | 5 | 0 / 0 | 1.000 | the model (same harness) |
| claude-4.8 vs factory | yes | yes | 6 | 3 / 0 | 0.250 | **nothing attributable** — reference point only |
| claude-4.8 vs openhands | yes | yes | 7 | 3 / 0 | 0.250 | **nothing attributable** — reference point only |
| claude-5 vs factory | yes | yes | 4 | 2 / 0 | 0.500 | **nothing attributable** — reference point only |
| claude-5 vs openhands | yes | yes | 4 | 1 / 0 | 1.000 | **nothing attributable** — reference point only |
| factory vs openhands | yes | no (nominal) † | 5 | 0 / 1 | 1.000 | the harness |

† nominal models match but the observed ledgers differ — the chain
escalates a stuck dev to a harder tier, so a matched-weights claim must
be checked against Table 4's per-tier call counts, not against config.

### High-margin stratum, within each arm

Descriptive only: the stratum is whatever instances post-date the arm's
OWN nominal model's bound, and at this n it is a handful of rows.

| arm | bound | high-margin | rest |
|---|---|---:|---:|
| bare | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 0/3 = 0% | 1/10 = 10% |
| claude | `claude-opus-5` after 2026-05-31 (published-cutoff) | n/a (0 in denominator) | 16/18 = 89% |
| claude-4.8 | `claude-opus-4-8` after 2026-01-31 (published-cutoff) | 7/8 = 88% | 1/1 = 100% |
| claude-5 | `claude-opus-5` after 2026-05-31 (published-cutoff) | n/a (0 in denominator) | 5/5 = 100% |
| factory | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 0/2 = 0% | 2/4 = 50% |
| openhands | `azure/deepseek-v4-pro` after 2026-04-24 (release-date-proxy) | 0/1 = 0% | 3/7 = 43% |

## Table 4 — provenance and integrity, per arm

`attempts` exists because the retracted run published 4 second attempts
after the integrity gate invalidated the first, disclosed nowhere. Any
value > 1 is a protocol violation, not a data point.

| arm | resolved model id(s) | per-tier call counts | max attempt | audit ok / invalid | action trails present | test files stripped | oracle-probe hits | p2p empty rows | p2p source(s) |
|---|---|---|---:|---|---|---:|---:|---:|---|
| bare | `azure/deepseek-v4-pro` | —=727 | 1 | 13 ok / 6 invalid | 19/19 | 12 | 24 | 0 | dataset, declared_test_targets |
| claude | `claude-opus-5` | n/a (not recorded by these rows) | 1 | 18 ok / 0 invalid | n/a (not recorded) | 20 | n/a (not recorded) | 2 | n/a |
| claude-4.8 | `claude-haiku-4-5-20251001`, `claude-opus-4-8` | —=0 | 1 | 9 ok / 10 invalid | 19/19 | 19 | 26 | 0 | dataset, declared_test_targets |
| claude-5 | `claude-haiku-4-5-20251001`, `claude-opus-5` | —=0 | 1 | 5 ok / 14 invalid | 19/19 | 23 | 47 | 0 | dataset, declared_test_targets |
| factory | `azure/deepseek-v4-pro`, `azure/gpt-5.3-codex`, `azure/gpt-5.4` | hard=6, standard=33, —=31 | 1 | 6 ok / 13 invalid | 19/19 | 23 | 85 | 0 | dataset, declared_test_targets |
| openhands | `azure/deepseek-v4-pro` | standard=19 | 1 | 10 ok / 9 invalid | 19/19 | 19 | 39 | 0 | dataset, declared_test_targets |

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
| claude-4.8 | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude-4.8 | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude-5 | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| claude-5 | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| factory | chain-verdict precision (oracle passes \| chain said green) | 1/5 = 20% | [1%, 72%] |
| factory | chain-verdict recall (chain said green \| oracle passes) | 1/2 = 50% | [1%, 99%] |
| factory | reviewer cycles, distribution | 0x3, 1x2, 3x1 | — |
| factory | dev retries, distribution | 0x6 | — |
| openhands | chain-verdict precision | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |
| openhands | chain-verdict recall | n/a (arm has no chain verdict) | n/a (arm has no chain verdict) |

## bare — gate accounting

- harness: hand-rolled text loop, no tool calls
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **13 audited-valid** of 19 gradable (audit failed: 6, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 11 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **1/13 = 8% audited-valid**, 95% CI [0%, 36%]
- **6 row(s) EXCLUDED from the denominator, passes AND failures named**: hiero-ledger__hiero-sdk-python-1914_interface [FAIL]: audit failed; hkuds__openharness-217 [FAIL]: audit failed; keras-team__keras-22316 [FAIL]: audit failed; line__line-bot-sdk-python-981_interface [FAIL]: audit failed; pyinfra-dev__pyinfra-1665 [FAIL]: audit failed; zauberzeug__nicegui-5858 [FAIL]: audit failed

## claude — gate accounting

- harness: Claude Code CLI
- graded instances: **18** (0 excluded as `task_broken`, leaving 18)
- audit gate: **18 audited-valid** of 18 gradable (audit failed: 0, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 1 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **16/18 = 89% audited-valid**, 95% CI [65%, 99%]

## claude-4.8 — gate accounting

- harness: Claude Code CLI
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **9 audited-valid** of 19 gradable (audit failed: 10, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 1 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **8/9 = 89% audited-valid**, 95% CI [52%, 100%]
- **10 row(s) EXCLUDED from the denominator, passes AND failures named**: conan-io__conan-19735_interface [PASS]: audit failed; conan-io__conan-19750 [FAIL]: audit failed; hkuds__openharness-217 [FAIL]: audit failed; keras-team__keras-22316 [PASS]: audit failed; line__line-bot-sdk-python-981_interface [PASS]: audit failed; pandas-dev__pandas-63945 [FAIL]: audit failed; pyinfra-dev__pyinfra-1665 [PASS]: audit failed; tox-dev__tox-3931 [PASS]: audit failed; vyperlang__vyper-4801 [FAIL]: audit failed; zauberzeug__nicegui-5858 [PASS]: audit failed

## claude-5 — gate accounting

- harness: Claude Code CLI
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **5 audited-valid** of 19 gradable (audit failed: 14, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **5/5 = 100% audited-valid**, 95% CI [48%, 100%]
- **14 row(s) EXCLUDED from the denominator, passes AND failures named**: alibaba__opensandbox-816 [FAIL]: audit failed; conan-io__conan-19735_interface [PASS]: audit failed; conan-io__conan-19750 [FAIL]: audit failed; harumiweb__exstruct-113 [FAIL]: audit failed; hiero-ledger__hiero-sdk-python-1914_interface [PASS]: audit failed; hkuds__openharness-217 [PASS]: audit failed; jsonpickle__jsonpickle-588 [PASS]: audit failed; keras-team__keras-22316 [PASS]: audit failed; line__line-bot-sdk-python-981_interface [PASS]: audit failed; pandas-dev__pandas-63945 [FAIL]: audit failed; pyinfra-dev__pyinfra-1665 [PASS]: audit failed; tox-dev__tox-3931 [PASS]: audit failed; vyperlang__vyper-4801 [PASS]: audit failed; zauberzeug__nicegui-5858 [PASS]: audit failed

## factory — gate accounting

- harness: software-factory chain on OpenHands
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **6 audited-valid** of 19 gradable (audit failed: 13, not audited: 0, run failed: 0)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **2/6 = 33% audited-valid**, 95% CI [4%, 78%]
- **13 row(s) EXCLUDED from the denominator, passes AND failures named**: conan-io__conan-19735_interface [FAIL]: audit failed; conan-io__conan-19750 [FAIL]: audit failed; hiero-ledger__hiero-sdk-python-1914_interface [FAIL]: audit failed; hkuds__openharness-217 [PASS]: audit failed; idaholab__montepy-933_interface [FAIL]: audit failed; jsonpickle__jsonpickle-588 [PASS]: audit failed; keras-team__keras-22316 [PASS]: audit failed; line__line-bot-sdk-python-981_interface [PASS]: audit failed; pandas-dev__pandas-63945 [FAIL]: audit failed; pyinfra-dev__pyinfra-1665 [FAIL]: audit failed; tox-dev__tox-3931 [FAIL]: audit failed; vyperlang__vyper-4801 [FAIL]: audit failed; zauberzeug__nicegui-5858 [PASS]: audit failed

## openhands — gate accounting

- harness: OpenHands single agent, no chain
- graded instances: **19** (0 excluded as `task_broken`, leaving 19)
- audit gate: **8 audited-valid** of 19 gradable (audit failed: 9, not audited: 0, run failed: 3)
- budget-exhausted, COUNTED as attempts: 0 (one rule, every arm: a turn-cap or wall-cap hit is a completed, counted, flagged attempt)
- resolve rate: **3/8 = 38% audited-valid**, 95% CI [9%, 76%]
- **11 row(s) EXCLUDED from the denominator, passes AND failures named**: conan-io__conan-19735_interface [FAIL]: audit failed; conan-io__conan-19750 [FAIL]: audit failed; hkuds__openharness-217 [FAIL]: audit failed; jsonpickle__jsonpickle-588 [PASS]: run failed (openhands conversation failed: ConversationRunError: Conversation run failed for); keras-team__keras-22316 [FAIL]: run failed (openhands conversation failed: ConversationRunError: Conversation run failed for), audit failed; line__line-bot-sdk-python-981_interface [PASS]: audit failed; pandas-dev__pandas-63945 [FAIL]: audit failed; pyinfra-dev__pyinfra-1665 [PASS]: audit failed; raullenchai__rapid-mlx-289 [PASS]: run failed (openhands conversation failed: ConversationRunError: Conversation run failed for); tox-dev__tox-3931 [PASS]: audit failed; zauberzeug__nicegui-5858 [PASS]: audit failed

## Discarded runs (attempt > 1)

None — every published row is its cell's first attempt.

## Per-row ledger

The row-level evidence every table above is derived from. `p2p` is the
instance's PASS_TO_PASS count: a **0** means the grade has no regression
half at all, so nothing there can catch a patch breaking the suite.

| instance | arm | model(s) | attempt | budget | factory says | oracle | audit | outcome | p2p | fresh in | cache read | tokens out | wall s | $ |
|---|---|---|---:|:-:|---|---|---|---|---:|---:|---:|---:|---:|
| alibaba__opensandbox-816 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | wrong_place | 108 | 232,591 | 0 | 6,130 | 177.7 | 0.39 |
| alibaba__opensandbox-816 | claude | claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 108 | 66,404 | 1,241,268 | 25,880 | 375.9 | 1.92 |
| alibaba__opensandbox-816 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | FAIL | ok | wrong_place | 108 | 33,658 | 621,387 | 10,336 | 169.0 | 0.89 |
| alibaba__opensandbox-816 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 108 | 68,392 | 1,828,330 | 23,224 | 352.4 | 2.16 |
| alibaba__opensandbox-816 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | ok | wrong_place | 108 | 610,561 | 793,856 | 10,501 | 823.5 | 1.35 |
| alibaba__opensandbox-816 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | wrong_place | 108 | 486,021 | 663,296 | 9,296 | 389.6 | 1.08 |
| conan-io__conan-19735_interface | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | empty_patch | 14 | 165,844 | 0 | 7,441 | 156.3 | 0.26 |
| conan-io__conan-19735_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 14 | 15,462 | 224,784 | 4,095 | 74.3 | 0.36 |
| conan-io__conan-19735_interface | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 14 | 12,347 | 202,966 | 3,651 | 60.4 | 0.28 |
| conan-io__conan-19735_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 14 | 13,750 | 191,246 | 3,336 | 54.9 | 0.30 |
| conan-io__conan-19735_interface | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | FAIL | right_place_wrong_fix | 14 | 135,917 | 292,864 | 5,505 | 202.1 | 0.33 |
| conan-io__conan-19735_interface | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 14 | 80,367 | 149,504 | 3,902 | 110.0 | 0.19 |
| conan-io__conan-19750 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | empty_patch | 18 | 424,440 | 0 | 4,818 | 114.2 | 0.64 |
| conan-io__conan-19750 | claude | claude-opus-5 | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 18 | 25,002 | 466,400 | 6,514 | 150.2 | 0.62 |
| conan-io__conan-19750 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 18 | 25,850 | 651,941 | 6,629 | 112.7 | 0.66 |
| conan-io__conan-19750 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 18 | 32,097 | 804,370 | 8,750 | 174.6 | 0.91 |
| conan-io__conan-19750 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | FAIL | right_place_wrong_fix | 18 | 543,768 | 2,483,456 | 19,552 | 742.5 | 1.53 |
| conan-io__conan-19750 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 18 | 788,943 | 1,001,472 | 14,319 | 870.1 | 1.74 |
| getmoto__moto-9841 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | right_place_wrong_fix | 149 | 213,392 | 0 | 12,568 | 291.2 | 0.37 |
| getmoto__moto-9841 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 149 | 26,071 | 461,609 | 6,396 | 132.3 | 0.56 |
| getmoto__moto-9841 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 149 | 45,669 | 1,232,262 | 16,332 | 266.0 | 1.46 |
| getmoto__moto-9841 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | not green | PASS | ok | resolved | 149 | 844,353 | 2,000,512 | 29,570 | 1054.1 | 2.09 |
| getmoto__moto-9841 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | ok | resolved | 149 | 338,730 | 626,432 | 10,863 | 371.1 | 0.80 |
| harumiweb__exstruct-113 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | empty_patch | 6 | 237,417 | 0 | 2,952 | 106.4 | 0.36 |
| harumiweb__exstruct-113 | claude | claude-opus-5 | 1 | ! | n/a | PASS | ok | resolved | 6 | 110,744 | 5,393,092 | 43,109 | 633.3 | 4.86 |
| harumiweb__exstruct-113 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 6 | 107,194 | 4,475,304 | 58,864 | 862.6 | 4.58 |
| harumiweb__exstruct-113 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 6 | 86,687 | 3,558,322 | 42,234 | 599.1 | 3.68 |
| harumiweb__exstruct-113 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | ok | empty_patch | 6 | 1,086,973 | 1,469,696 | 24,396 | 1702.8 | 2.45 |
| harumiweb__exstruct-113 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 6 | 1,045,149 | 1,095,680 | 22,606 | 888.5 | 2.28 |
| hiero-ledger__hiero-sdk-python-1914_interface | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | right_place_wrong_fix | 9 | 579,670 | 0 | 45,359 | 503.2 | 0.84 |
| hiero-ledger__hiero-sdk-python-1914_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 9 | 50,337 | 920,558 | 19,097 | 270.5 | 1.42 |
| hiero-ledger__hiero-sdk-python-1914_interface | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 9 | 42,274 | 671,647 | 19,895 | 264.3 | 1.11 |
| hiero-ledger__hiero-sdk-python-1914_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 9 | 58,129 | 1,258,148 | 24,238 | 343.3 | 1.80 |
| hiero-ledger__hiero-sdk-python-1914_interface | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | not green | FAIL | FAIL | right_place_wrong_fix | 9 | 1,315,392 | 3,755,776 | 46,886 | 1167.5 | 3.37 |
| hiero-ledger__hiero-sdk-python-1914_interface | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 9 | 150,641 | 584,192 | 16,728 | 239.8 | 0.45 |
| hkuds__openharness-217 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | right_place_wrong_fix | 2 | 290,877 | 0 | 13,414 | 238.8 | 0.47 |
| hkuds__openharness-217 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 33,655 | 193,947 | 6,409 | 94.4 | 0.58 |
| hkuds__openharness-217 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 2 | 29,989 | 170,014 | 3,981 | 60.0 | 0.47 |
| hkuds__openharness-217 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 2 | 34,040 | 193,891 | 6,120 | 87.7 | 0.57 |
| hkuds__openharness-217 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | FAIL | resolved | 2 | 1,263,398 | 935,168 | 26,147 | 1404.7 | 2.70 |
| hkuds__openharness-217 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 2 | 217,903 | 363,008 | 11,922 | 228.1 | 0.52 |
| idaholab__montepy-933_interface | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | right_place_wrong_fix | 40 | 185,973 | 0 | 5,962 | 108.6 | 0.28 |
| idaholab__montepy-933_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 40 | 66,393 | 2,411,185 | 19,644 | 353.9 | 2.34 |
| idaholab__montepy-933_interface | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 40 | 18,955 | 581,226 | 5,594 | 109.1 | 0.56 |
| idaholab__montepy-933_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 40 | 66,692 | 1,860,755 | 16,768 | 280.2 | 2.00 |
| idaholab__montepy-933_interface | factory | azure/deepseek-v4-pro, azure/gpt-5.3-codex, azure/gpt-5.4 | 1 | — | not green | FAIL | FAIL | right_place_wrong_fix | 40 | 670,420 | 4,690,432 | 61,628 | 1667.0 | 2.84 |
| idaholab__montepy-933_interface | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 40 | 322,663 | 727,296 | 9,624 | 343.7 | 0.78 |
| jsonpickle__jsonpickle-588 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | right_place_wrong_fix | 82 | 197,368 | 0 | 2,425 | 81.1 | 0.25 |
| jsonpickle__jsonpickle-588 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 82 | 99,373 | 3,981,358 | 51,944 | 825.3 | 4.26 |
| jsonpickle__jsonpickle-588 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | ! | n/a | PASS | ok | resolved | 82 | 75,383 | 3,274,528 | 39,300 | 599.0 | 3.10 |
| jsonpickle__jsonpickle-588 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 82 | 93,286 | 3,159,820 | 49,350 | 702.6 | 3.72 |
| jsonpickle__jsonpickle-588 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | FAIL | resolved | 82 | 760,746 | 3,096,064 | 41,234 | 1365.1 | 2.14 |
| jsonpickle__jsonpickle-588 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | ok | resolved | 82 | 0 | 0 | 0 | 1078.4 | 0.00 |
| keras-team__keras-22316 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | empty_patch | 8 | 216,858 | 0 | 10,866 | 234.0 | 0.36 |
| keras-team__keras-22316 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 8 | 62,961 | 2,167,543 | 23,081 | 619.8 | 2.28 |
| keras-team__keras-22316 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 8 | 47,499 | 992,877 | 27,846 | 451.5 | 1.63 |
| keras-team__keras-22316 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 8 | 59,622 | 2,040,628 | 24,511 | 744.1 | 2.21 |
| keras-team__keras-22316 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | FAIL | resolved | 8 | 532,333 | 1,221,888 | 26,163 | 811.7 | 1.33 |
| keras-team__keras-22316 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 8 | 0 | 0 | 0 | 2054.3 | 0.00 |
| keras-team__keras-22642 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | empty_patch | 16 | 291,008 | 0 | 13,359 | 253.2 | 0.47 |
| keras-team__keras-22642 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 16 | 28,752 | 723,701 | 9,543 | 172.5 | 0.87 |
| keras-team__keras-22642 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 16 | 27,592 | 546,836 | 6,588 | 124.8 | 0.62 |
| keras-team__keras-22642 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 16 | 30,319 | 837,423 | 11,716 | 226.6 | 1.00 |
| keras-team__keras-22642 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | ok | resolved | 16 | 431,014 | 809,472 | 11,130 | 518.0 | 1.01 |
| keras-team__keras-22642 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | ok | resolved | 16 | 1,214,845 | 1,572,608 | 25,782 | 913.7 | 2.70 |
| line__line-bot-sdk-python-981_interface | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | empty_patch | 1 | 320,281 | 0 | 9,319 | 192.2 | 0.55 |
| line__line-bot-sdk-python-981_interface | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | **0 (no regression half)** | 81,094 | 2,896,280 | 33,081 | 477.2 | 3.07 |
| line__line-bot-sdk-python-981_interface | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 1 | 64,029 | 831,402 | 19,292 | 215.6 | 1.31 |
| line__line-bot-sdk-python-981_interface | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 1 | 55,086 | 1,190,793 | 23,066 | 274.1 | 1.71 |
| line__line-bot-sdk-python-981_interface | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | FAIL | resolved | 1 | 1,889,320 | 2,128,128 | 44,437 | 1321.4 | 4.18 |
| line__line-bot-sdk-python-981_interface | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | FAIL | resolved | 1 | 309,912 | 546,048 | 12,520 | 323.6 | 0.73 |
| pandas-dev__pandas-63945 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 14 | 121,990 | 0 | 3,960 | 191.6 | 0.16 |
| pandas-dev__pandas-63945 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | **0 (no regression half)** | 31,086 | 769,217 | 11,065 | 284.4 | 0.95 |
| pandas-dev__pandas-63945 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 14 | 18,800 | 242,845 | 2,644 | 125.5 | 0.35 |
| pandas-dev__pandas-63945 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 14 | 31,717 | 872,086 | 11,128 | 292.3 | 1.01 |
| pandas-dev__pandas-63945 | factory | azure/deepseek-v4-pro, azure/gpt-5.3-codex | 1 | — | not green | FAIL | FAIL | right_place_wrong_fix | 14 | 311,160 | 2,281,856 | 33,108 | 1278.6 | 1.34 |
| pandas-dev__pandas-63945 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | FAIL | right_place_wrong_fix | 14 | 173,476 | 140,800 | 4,074 | 385.4 | 0.37 |
| pyinfra-dev__pyinfra-1665 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | right_place_wrong_fix | 33 | 254,916 | 0 | 8,686 | 187.8 | 0.38 |
| pyinfra-dev__pyinfra-1665 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 33 | 47,018 | 571,977 | 7,584 | 133.8 | 0.92 |
| pyinfra-dev__pyinfra-1665 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 33 | 18,955 | 311,507 | 4,626 | 76.2 | 0.43 |
| pyinfra-dev__pyinfra-1665 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 33 | 42,623 | 475,938 | 8,232 | 135.8 | 0.84 |
| pyinfra-dev__pyinfra-1665 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | FAIL | right_place_wrong_fix | 33 | 530,514 | 717,312 | 12,118 | 586.1 | 1.20 |
| pyinfra-dev__pyinfra-1665 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | FAIL | resolved | 33 | 255,073 | 348,416 | 5,773 | 146.7 | 0.57 |
| raullenchai__rapid-mlx-289 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | right_place_wrong_fix | 122 | 615,478 | 0 | 32,415 | 393.8 | 0.95 |
| raullenchai__rapid-mlx-289 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 122 | 125,764 | 4,335,697 | 62,922 | 812.4 | 4.94 |
| raullenchai__rapid-mlx-289 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 122 | 93,549 | 1,915,212 | 38,043 | 533.6 | 2.70 |
| raullenchai__rapid-mlx-289 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 122 | 133,470 | 4,927,704 | 68,885 | 910.8 | 5.46 |
| raullenchai__rapid-mlx-289 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | ok | right_place_wrong_fix | 122 | 973,519 | 1,987,072 | 32,373 | 1019.7 | 2.35 |
| raullenchai__rapid-mlx-289 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | ok | resolved | 122 | 0 | 0 | 0 | 919.7 | 0.00 |
| tox-dev__tox-3931 | bare | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | right_place_wrong_fix | 2 | 102,151 | 0 | 4,232 | 94.2 | 0.15 |
| tox-dev__tox-3931 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 2 | 45,370 | 572,785 | 6,973 | 127.6 | 0.90 |
| tox-dev__tox-3931 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 2 | 40,353 | 422,364 | 5,430 | 89.5 | 0.74 |
| tox-dev__tox-3931 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 2 | 48,445 | 698,811 | 9,604 | 181.9 | 1.06 |
| tox-dev__tox-3931 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | FAIL | right_place_wrong_fix | 2 | 1,107,755 | 1,409,280 | 23,814 | 995.1 | 2.47 |
| tox-dev__tox-3931 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | FAIL | resolved | 2 | 521,991 | 478,720 | 8,507 | 531.2 | 1.12 |
| ucfopen__canvasapi-716 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | PASS | ok | resolved | 60 | 186,394 | 0 | 5,240 | 147.2 | 0.32 |
| ucfopen__canvasapi-716 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 60 | 24,681 | 455,012 | 7,496 | 125.4 | 0.65 |
| ucfopen__canvasapi-716 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | ok | resolved | 60 | 16,676 | 201,853 | 5,273 | 77.7 | 0.39 |
| ucfopen__canvasapi-716 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 60 | 26,600 | 407,924 | 7,749 | 119.5 | 0.65 |
| ucfopen__canvasapi-716 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | ok | right_place_wrong_fix | 60 | 200,516 | 348,672 | 5,418 | 252.8 | 0.47 |
| ucfopen__canvasapi-716 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | ok | resolved | 60 | 126,547 | 314,624 | 5,158 | 179.1 | 0.31 |
| vyperlang__vyper-4801 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | ok | empty_patch | 1 | 196,429 | 0 | 1,654 | 77.4 | 0.29 |
| vyperlang__vyper-4801 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 1 | 50,606 | 1,636,959 | 17,841 | 1909.1 | 1.75 |
| vyperlang__vyper-4801 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | FAIL | FAIL | wrong_place | 1 | 76,464 | 2,555,718 | 38,214 | 605.5 | 2.72 |
| vyperlang__vyper-4801 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 1 | 78,632 | 2,725,049 | 34,332 | 1354.1 | 2.99 |
| vyperlang__vyper-4801 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | FAIL | FAIL | wrong_place | 1 | 860,991 | 1,938,944 | 19,149 | 965.4 | 2.05 |
| vyperlang__vyper-4801 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | FAIL | ok | empty_patch | 1 | 527,729 | 792,064 | 14,536 | 558.3 | 1.20 |
| zauberzeug__nicegui-5858 | bare | azure/deepseek-v4-pro | 1 | ! | n/a | FAIL | FAIL | empty_patch | 3 | 282,407 | 0 | 4,940 | 161.6 | 0.45 |
| zauberzeug__nicegui-5858 | claude | claude-opus-5 | 1 | — | n/a | PASS | ok | resolved | 3 | 37,216 | 1,206,043 | 13,508 | 276.0 | 1.29 |
| zauberzeug__nicegui-5858 | claude-4.8 | claude-haiku-4-5-20251001, claude-opus-4-8 | 1 | — | n/a | PASS | FAIL | resolved | 3 | 19,742 | 394,459 | 5,526 | 103.2 | 0.47 |
| zauberzeug__nicegui-5858 | claude-5 | claude-haiku-4-5-20251001, claude-opus-5 | 1 | — | n/a | PASS | FAIL | resolved | 3 | 26,986 | 709,082 | 8,277 | 160.9 | 0.81 |
| zauberzeug__nicegui-5858 | factory | azure/deepseek-v4-pro, azure/gpt-5.4 | 1 | — | green | PASS | FAIL | resolved | 3 | 280,758 | 835,072 | 13,377 | 451.0 | 0.74 |
| zauberzeug__nicegui-5858 | openhands | azure/deepseek-v4-pro | 1 | — | n/a | PASS | FAIL | resolved | 3 | 236,491 | 320,000 | 4,988 | 224.6 | 0.53 |

## Excluded rows (other manifest/profile)

These runs did not run under the pinned manifest `923aef05add32124`,
so they are NOT table rows and count in NO rate above — merging
runs from two manifests (e.g. a previous dataset's leftovers in
`runs/`) would blend incomparable numbers into one headline.

- `instance_ansible__ansible-34db57a47f875d11c4068567b9ec7ace174ec4cf-v1055803c3a812189a1133297f7f5468579283f86/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-34db57a47f875d11c4068567b9ec7ace174ec4cf-v1055803c3a812189a1133297f7f5468579283f86/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-9a21e247786ebd294dafafca1105fcd770ff46c6-v67cdaa49f89b34e42b69d5b7830b3c3ad3d8803f/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-9a21e247786ebd294dafafca1105fcd770ff46c6-v67cdaa49f89b34e42b69d5b7830b3c3ad3d8803f/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-e22e103cdf8edc56ff7d9b848a58f94f1471a263-v1055803c3a812189a1133297f7f5468579283f86/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_ansible__ansible-e22e103cdf8edc56ff7d9b848a58f94f1471a263-v1055803c3a812189a1133297f7f5468579283f86/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-3aeec6afed9198d734b7ee1293f03ca94ff970e1-v13642507b4fc1f8d234172bf8129942da2c2ca26/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-3aeec6afed9198d734b7ee1293f03ca94ff970e1-v13642507b4fc1f8d234172bf8129942da2c2ca26/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-798055d1a19b8fa0983153b709f460be97e33064-v13642507b4fc1f8d234172bf8129942da2c2ca26/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_internetarchive__openlibrary-798055d1a19b8fa0983153b709f460be97e33064-v13642507b4fc1f8d234172bf8129942da2c2ca26/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_qutebrowser__qutebrowser-0833b5f6f140d04200ec91605f88704dd18e2970-v059c6fdc75567943479b23ebca7c07b5e9a7f34c/bare` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124
- `instance_qutebrowser__qutebrowser-0833b5f6f140d04200ec91605f88704dd18e2970-v059c6fdc75567943479b23ebca7c07b5e9a7f34c/factory` — ran under manifest 0255c86da946722f, report is pinned to 923aef05add32124

> **n=19 — preliminary.** Do not draw conclusions beyond "the harness runs". The MDE at this size is far wider than any difference worth acting on; k>=3 is required before any delta from this suite is quoted as a result.

> Cost columns are NOT comparable across arms and must never be summed: the Azure arms' dollars are a price-table estimate over measured tokens, the Claude arms' are the CLI's own report against a subscription.
