# Pre-registration — Phase 1.6 five-arm re-run

**Written before the run. Committed before the run.** The point of this file is
that the tables below are fixed *now*, so the run cannot be reported in whatever
framing happens to flatter the result. Every cell is either filled from an
archived artifact or printed as `n/a` with a reason. No cell is filled by hand.

- Suite: **SWE-rebench**, pinned manifest `923aef05add32124`, the same 19
  working-oracle instances as the retracted 2026-08-03 run. Reusing them is
  deliberate: it makes this a before/after on the parity fixes, not a new
  experiment.
- n = 19, **k = 1**. This run's job is to prove the plumbing, not to establish a
  defensible delta. See "What this run cannot show".
- Five arms, one sweep, **no re-rolls**. A row the integrity gate rejects is
  published as invalid.

## Arms

| id | what it is | model(s) | what it measures |
|---|---|---|---|
| `factory` | the full chain, dev+review, gates | dev `azure/deepseek-v4-pro`, hard-tier escape `azure/gpt-5.3-codex`, reviewer `azure/gpt-5.4` | the product |
| `openhands` | OpenHands single agent, no chain, identical prompt | `azure/deepseek-v4-pro` | **the chain's contribution** — same weights, same prompt, same tools, minus the chain |
| `bare` | minimal shell loop, 40 steps | `azure/deepseek-v4-pro` | the floor at matched weights |
| `claude-5` | Claude Code CLI, subscription | `claude-opus-5` | frontier reference |
| `claude-4.8` | Claude Code CLI, subscription | `claude-opus-4-8` | **contamination probe** (cutoff Jan 2026 vs May 2026) |

`openhands` is the arm the previous run lacked and the reason its "+58 pp
scaffold lift" was unattributable: `bare` lacks both the chain *and* real editor
tools, so it could not separate the two.

## Table 1 — headline, one row per arm

| arm | resolved / audited-valid | rate | 95% CI (Clopper-Pearson) | invalid rows | fresh in | cache read | out | wall s (median) | $ | cost source |
|---|---|---|---|---|---|---|---|---|---|---|
| factory | / | % | [ , ] | | | | | | | price-table estimate |
| openhands | / | % | [ , ] | | | | | | | price-table estimate |
| bare | / | % | [ , ] | | | | | | | price-table estimate |
| claude-5 | / | % | [ , ] | | | | | | | CLI-reported, subscription |
| claude-4.8 | / | % | [ , ] | | | | | | | CLI-reported, subscription |

`fresh in` and `cache read` are separate columns on purpose. Last run's single
"tokens in" column mixed them, and cache share differed 0% / 78% / 97% across
arms — which made the published "34× tokens" claim wrong by 4.5×.

## Table 2 — per-instance outcome matrix

`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken ·
`X` audit-invalid · `!` budget-exhausted (counted as an attempt, not excluded)

| instance | created_at | margin vs deepseek (rel. 2026-04-24) | margin vs opus-5 | factory | openhands | bare | claude-5 | claude-4.8 |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|
| vyperlang__vyper-4801 | 2026-01-03 | −110 | −147 | | | | | |
| jsonpickle__jsonpickle-588 | 2026-01-12 | −101 | −138 | | | | | |
| pandas-dev__pandas-63945 | 2026-01-30 | −84 | −121 | | | | | |
| keras-team__keras-22316 | 2026-03-01 | −54 | −91 | | | | | |
| hiero-ledger__hiero-sdk-python-1914_interface | 2026-03-06 | −48 | −85 | | | | | |
| zauberzeug__nicegui-5858 | 2026-03-09 | −45 | −82 | | | | | |
| getmoto__moto-9841 | 2026-03-09 | −45 | −82 | | | | | |
| conan-io__conan-19735_interface | 2026-03-10 | −45 | −82 | | | | | |
| conan-io__conan-19750 | 2026-03-13 | −42 | −79 | | | | | |
| idaholab__montepy-933_interface | 2026-03-20 | −34 | −71 | | | | | |
| harumiweb__exstruct-113 | 2026-03-21 | −34 | −71 | | | | | |
| ucfopen__canvasapi-716 | 2026-03-31 | −23 | −60 | | | | | |
| line__line-bot-sdk-python-981_interface | 2026-04-01 | −23 | −60 | | | | | |
| keras-team__keras-22642 | 2026-04-06 | −17 | −54 | | | | | |
| pyinfra-dev__pyinfra-1665 | 2026-04-14 | −10 | −47 | | | | | |
| **alibaba__opensandbox-816** | 2026-04-29 | **+5** | −32 | | | | | |
| **hkuds__openharness-217** | 2026-04-30 | **+6** | −31 | | | | | |
| **tox-dev__tox-3931** | 2026-05-01 | **+8** | −29 | | | | | |
| **raullenchai__rapid-mlx-289** | 2026-05-07 | **+14** | −23 | | | | | |

The four bold rows are the only instances in this manifest with a positive
margin against `deepseek-v4-pro`'s release-date bound. No instance has a
positive margin against `claude-opus-5` — that is why `claude-4.8` exists.

## Table 3 — the comparisons, and which ones are allowed to mean anything

| comparison | contingency (only-A / only-B) | McNemar exact p | what it measures | may we act on it? |
|---|---|---|---|---|
| factory vs **openhands** | / | | **the chain, at matched weights, matched prompt, matched tools** | this is the product number |
| factory vs bare | / | | the floor | only if bare is now plausible vs the 40.2% public anchor |
| factory vs claude-5 | / | | model **+** scaffold — not attributable to either | report as a gap, never as a scaffold deficit |
| claude-5 vs claude-4.8 | / | | contamination | a large gap favouring opus-5 on low-margin rows is the memorization signal |
| high-margin stratum (n=4) vs rest (n=15), per arm | | | contamination, within arm | n=4 is descriptive only |

## Table 4 — provenance and integrity, per arm

Filled from `result.json` / `audit.json`. Any blank here is a bug, not a result.

| arm | resolved model id(s) recorded | per-tier call counts | attempts (must be 1) | audit ok / invalid | trajectories present | test files stripped | oracle-probe hits | p2p empty rows |
|---|---|---|---|---|---|---|---|---|
| factory | | | | | | | | |
| openhands | | | | | | | | |
| bare | | | | | | | | |
| claude-5 | | | | | | | | |
| claude-4.8 | | | | | | | | |

`attempts` exists because the retracted run published 4 second attempts after
the integrity gate invalidated the first. Any value > 1 in this run is a
protocol violation, not a data point.

## Table 5 — chain-verdict quality (factory arm only)

| quantity | value | 95% CI |
|---|---|---|
| chain-verdict precision — P(oracle passes \| chain said green) | / | [ , ] |
| chain-verdict recall — P(chain said green \| oracle passes) | / | [ , ] |
| reviewer cycles, distribution | | — |
| dev retries, distribution | | — |

Printed as `n/a (arm has no chain verdict)` for every other arm. Last run
published "claude recall 0/16 = 0%", which was a division artifact on a column
that does not exist for that arm.

## Pre-committed decision rules

Stated before seeing the data, so they cannot be chosen afterwards.

1. **The product claim is `factory − openhands`.** If that difference is ~0, the
   chain adds nothing on this suite and the honest headline is "our lift comes
   from using a competent agent loop, not from the chain". That outcome gets
   published in the same words.
2. **`bare` is a sanity check on the harness, not a baseline**, until it is
   plausible against the 40.2% public anchor for the same deployment. If the
   repaired bare arm still scores 0/19, the arm is still broken — do not publish
   a lift against it.
3. **No absolute rate is published without its margin column.** 15 of 19 rows are
   inside `deepseek-v4-pro`'s release bound and 19 of 19 inside `claude-opus-5`'s
   cutoff.
4. **A budget-exhausted run is a counted attempt for every arm.** Last run
   excluded a Claude row that hit its turn cap *and passed the oracle*, which
   silently improved its denominator. One rule, all arms.
5. **No re-rolls.** An audit-invalid row is published as invalid.
6. **Report the subset relation.** Last run's most useful finding needed no test:
   the factory's 11 passes were a strict subset of Claude's 16.

## What this run cannot show

At n=19, k=1 the MDE is roughly **±38 pp** against a 58% baseline (Fisher, 80%
power, α=.05). The archives already contain 10 same-condition factory
replications: 0/10 oracle flips (95% upper bound on per-instance flip
probability = 25.9%, i.e. ±3 instances at n=19), 1/10 chain-verdict flips, and
cost varying up to 2.6× on the same instance. So:

- differences smaller than ~38 pp are **not** measurable here;
- the precision/recall figures in Table 5 are the least stable numbers on the
  page;
- **k ≥ 3 is required before any delta from this suite is quoted as a result.**

This run's deliverable is a working five-arm harness with honest columns. Phase 2
is where the numbers become defensible.
