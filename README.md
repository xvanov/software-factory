# 🏭 software-factory

**An autonomous software factory: an LLM persona pipeline that turns high-level product directions into reviewed, tested, merged pull requests — unattended, on cheap open-weight models.**

![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Tests](https://github.com/xvanov/software-factory/actions/workflows/test.yml/badge.svg)
![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/xvanov/software-factory/python-coverage-comment-action-data/endpoint.json)
![Test count](https://img.shields.io/badge/tests-2182%20passing-brightgreen)
![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)
![Typed](https://img.shields.io/badge/types-mypy-blue)

The thesis under test: **harness quality beats model size.** A well-instrumented pipeline of small, verifiable steps — each gated by real tests and a live runtime smoke check — ships production code unattended on models ~10× cheaper than frontier subscriptions. It does ship: 117 stories merged and deployed, 24 of them edits to the factory itself.

**The thesis is not proven, and the latest measurement runs against it.** Externally graded on SWE-rebench with a hidden oracle (2026-08-04, five arms, n=19, k=1 — [full result](bench/swebench/results.md)):

Every arm ran **the same 19 instances** and every arm got an oracle verdict on
all 19, so every rate below is out of 19 — no arm gets a smaller denominator
than another.

| harness | model(s) | solved | rate | total $ | **$ per solved** |
|---|---|---:|---:|---:|---:|
| Claude Code CLI | `claude-opus-5` | 15/19 | **79%** | 34.36 | **2.29** |
| Claude Code CLI | `claude-opus-4-8` | 14/19 | **74%** | 23.56 | **1.68** |
| one OpenHands agent, **no chain** | `azure/deepseek-v4-pro` | 10/19 | **53%** | 18.20 † | **1.82** † |
| **this factory's chain** | deepseek-v4-pro + gpt-5.3-codex + gpt-5.4 | 7/19 | **37%** | 35.94 † | **5.13** |
| hand-rolled loop, **no tool calls** | `azure/deepseek-v4-pro` | 1/19 | **5%** | 7.94 | 7.94 |

Reading it:

- **The chain does not beat a single agent on the same model** — 37% vs 53%.
  Across all 19 paired instances the single agent won 4 the chain lost; the chain
  won 1 the agent lost. The gap is **3 instances**, and at this sample size that
  still does not clear significance (McNemar exact **p=0.375**). A 16-point gap
  that cannot reach p<0.05 is exactly what n=19 buys.
- **The chain is also the most expensive way to solve one** — $5.13, versus $1.82
  for the same model with no chain and **$2.29 for Claude Code**, a frontier
  model. ~2.0× the single agent in total, **2.8× per solved instance**, for fewer
  solves.
- **What produces lift is tooling, not orchestration**: 53% with a real editor and
  tool-calling versus 5% with neither — n=18, 0/9 discordant, **p=0.004**. That
  gap is real and significant; the orchestration gap is neither.
- Claude Code roughly doubles the factory (**p=0.008**), but that comparison
  changes the harness *and* the model at once, so it is a reference point, not a
  measurement of the chain.
- The contamination probe came back **clean**: `claude-opus-4-8` (published cutoff
  Jan 2026) 74% vs `claude-opus-5` (May 2026) 79% on an identical harness,
  p=1.000, even though every instance predates opus-5's cutoff. Memorisation is
  not carrying the frontier number.

**† Both Azure figures are floors.** Three OpenHands rows and two factory rows
carry an unmetered session — a crashed sandbox that recorded `cost_usd: 0` and
zero tokens while doing real work. 18 of 19 OpenHands rows are metered at $18.20,
so **$18.20 and $1.82 are floors, not estimates**; the true figures are slightly
higher. Even as floors the ratios above hold. The leak is filed as a harness debt.

**Cost units are not identical either.** The Azure rows are a price-table estimate
over provider-reported tokens — real money, and the cache-read rate in that table
is itself *estimated*. The Claude rows are what the CLI reports at API list prices,
billed in practice against a flat subscription. Same order of magnitude, not the
same meter.

**Three rows were re-run, and it is disclosed.** Three OpenHands rows died on Azure
`429` rate limits recording no cost and no tokens. A provider rate limit is an
infrastructure failure rather than a result, so those three — and only those
three — were repaired once under
[pre-registration Rule 5](bench/swebench/PRE-REGISTRATION-1.6.md). Outcomes:
`jsonpickle-588` resolved twice, `rapid-mlx-289` resolved twice, and
**`keras-22316` flipped from wrong-fix to resolved on the second draw.** So the
conservative reading is 9/19 = 47% and the re-run reading is 10/19 = 53%; the
table shows the latter because it is the metered, graded, audit-valid run, and
both are published. One row in three flipping on a reseed is also the clearest
evidence here that single-seed results at n=19 are unstable.

**What the ± ranges in [`results.md`](bench/swebench/results.md) mean.** 7 solved
of 19 is 37%, but 19 samples cannot pin down true skill: the 95% confidence
interval [16%, 62%] is the band of true rates that would not be surprised by this
result. The factory's band and the single agent's [29%, 76%] overlap almost
entirely — **at n=19 these two arms cannot be told apart.** The smallest
difference this sample could reliably detect is roughly ±38 points, so the finding
is "**no measurable lift**", not "the chain hurts". Running each instance 3+ times
is what would sharpen it.

**A sixth arm, measured a day later: take the reviewer out and nothing measurable
breaks.** `solo-noreview` is the same chain with the reviewer round-trip removed, run
on the same 19 instances, pre-registered before any paid call
([full report](bench/swebench/RESULTS-B1-PHASE1A.md)). It is published separately
from the table above, which still re-derives byte-for-byte from its own archive.

| harness | solved | rate | total $ | **$ per solved** |
|---|---:|---:|---:|---:|
| this factory's chain | 7/19 | 37% | 35.94 | 5.13 |
| the same chain, **no reviewer** | 9/18 | **50%** | 25.49 | **2.83** |

- **The cost win is real — 29% less in total, 45% less per solved instance — and the
  mechanism is not the one we predicted.** The reviewer's own tokens are 1.8% of
  spend. The saving is **9 fewer dev calls and a median story of one tick instead of
  four**: the reviewer was not expensive, it was causing rework.
- **The quality claim is not established.** +13 points sits well inside the ±38-point
  resolution of a 19-instance run (McNemar exact **p=0.688**), so the finding is "no
  measurable change", never "better without a reviewer".
- **It is not a clean single-variable ablation**, and that was written down before the
  data existed: three things differ between those two rows, not one. The next step is
  running both arms in one sweep on one commit.
- **Still 1.6× a single agent** — $2.83 per solved against $1.82. The ablation narrows
  the chain's deficit without closing it.
- It does **not** license removing the reviewer in production, which runs merge gates
  this benchmark never touches.

The July 2026 campaign read the other way, but it graded the factory against
sacrifice's *own* merge gates — tests the factory itself wrote — so it could not
measure correctness at all. Its numbers are **withdrawn**, not merely superseded:
see [the campaign's retraction header](bench/CAMPAIGN-2026-07-17.md).

> **An LLM agent working in this repo?** Read [`CLAUDE.md`](CLAUDE.md) first (or
> [`AGENTS.md`](AGENTS.md) if you're on a non-Claude tool) — it is the short,
> maintained orientation doc: the three loops, the 60-second health check, where
> truth lives, the operator command surface, and the hard guardrails. This
> README is the human-facing pitch; the deep per-subsystem docs live at
> `apps/factory/context/modules/*.md`.

---

## How it works

```mermaid
flowchart LR
    D[Direction<br/>product intent] --> PM[PM<br/>triage + split]
    PM --> SM[SM<br/>story files]
    SM --> DEV[Dev sandbox<br/>code + tests<br/>run-until-green]
    DEV --> REV[Reviewer<br/>different model<br/>proposes concrete edits]
    REV -->|request changes| DEV
    REV -->|approve| GATES[Merge gates<br/>full pytest + live smoke]
    GATES --> PR[PR opened<br/>auto-merged]
    PR --> TW[Tech-writer<br/>context docs]
```

- **Directions** are markdown work orders (`apps/<app>/directions/`) — filed by you, or by the factory's own scanner personas (hourly drift watchdog, bug hunter, weekly security audit, UX auditor).
- **Personas** are prompt-defined roles (`factory/personas/*.md`) executed either as tool-using sandboxes (OpenHands SDK) or single structured-JSON calls. Model routing per persona/difficulty lives in one file: `factory/routes.yaml`.
- **Nothing merges on green unit tests alone.** The `smoke-green` gate boots the PR's own code on an isolated port and drives the core user journey live before auto-merge.
- **Convergence machinery** keeps dev↔review loops short: the reviewer carries memory of its own previous findings, proposes concrete `FIND/REPLACE` edits, and a drift clamp stops goalpost-moving at cycle 3.

## The factory manages itself

A four-tier management pipeline (FMS) watches the factory's own telemetry:

| Tier | Role | Cadence |
|------|------|---------|
| L1 Watcher | summarize event streams, flag anomalies | every 60 s |
| L2 Summarizer | structured concern documents | on escalation |
| L3 Diagnostician | root-cause + unified-diff proposal | on escalation |
| L4 Apply | classify safe/forbidden, branch, test, PR | on proposal |

Blocked stories auto-recover (bounded), stale worktrees get pruned, and a halted factory refuses to burn spend until an operator runs `factory resume`. Every factory self-edit is validated on a cloned staging copy — full suite + import/CLI smoke — before it can touch the live tree; `factory/manager/**` and `bench/**` stay forbidden to self-edit (operator PR only).

## Quickstart

```bash
uv sync --all-extras          # dev extras included — bare `uv sync` omits pytest
uv run pytest -q              # 2182 tests, ~5 min (not the ~30s of the early repo)
uv run factory --help
```

Wire an app (see `apps/sacrifice/config.yaml` for a complete example), then:

```bash
uv run factory pm-sync --app <app>   # triage directions into stories
uv run factory tick --app <app>      # one full pipeline pass
```

Continuous operation runs on two systemd user units: `factory-tick@<app>.timer` (pipeline heartbeat, 5 min) and `factory-manager.service` (FMS L1 daemon). Models and API keys are configured in `factory/routes.yaml` + `.env` (`.env.example` documents every key; Azure OpenAI, DeepSeek, and OpenRouter routing supported out of the box).

Day-to-day operator surface:

```bash
factory inbox                 # everything awaiting a human, across apps
factory status-sync --app X   # pinned [FACTORY] live-status GitHub issue
factory why <story-id>        # per-story event trail
factory resume                # clear an FMS halt (operator-only)
```

## Benchmarks

Two harnesses. Only one of them is evidence about correctness.

**`bench/swebench_adapter.py` — externally graded, five arms, hidden oracle.** Pre-registered tables, archived per-row evidence, and a `report --check` that re-derives the published table byte-for-byte or exits non-zero. The measured result is in the table at the top of this README; the full one with CIs, paired McNemar tests, per-row model ledgers and contamination margins is [`bench/swebench/results.md`](bench/swebench/results.md) ([how it works](bench/swebench/README.md)).

```bash
uv run python bench/swebench_adapter.py report \
  --from-archive bench/swebench/results-archive/2026-08-04T23-19-24.998844Z --check
```

**`bench/bench.py` — convergence only.** It grades the factory on sacrifice's own merge gates, i.e. on tests the factory wrote, so it measures whether the chain drives a story to green unattended and what that costs. It is not evidence about correctness, and its July campaign is superseded. Run it: `uv run python bench/bench.py --help` ([protocol + caveats](bench/README.md)).

## Repository map

```
factory/           the orchestrator
  chain/           state machine, handlers, gates, auto-merge, worktrees
  manager/         FMS tiers (watcher → summarizer → diagnostician → apply)
  personas/        prompt-defined roles (pm, sm, dev, reviewer, …)
  routes.yaml      per-persona model routing — the single model-choice seam
apps/<app>/        per-app config, directions (work orders), stories
bench/             benchmarks
  swebench/        externally graded, five arms, hidden oracle — the real one
  bench.py         convergence harness on the app's own gates
state/             runtime: sqlite db, event streams, worktrees (gitignored)
tests/             1086 tests
```

## Design principles

1. **Verification-first** — a feature is done when it runs live, not when tests pass. (The smoke gate exists because an early version shipped a green-but-unbootable app.)
2. **Decompose by context, not by pipeline stage** — the reviewer sees only the diff + gates + its own review history; the dev owns both code and tests.
3. **Everything loops at most 3–6 times** — retry caps, review-cycle caps, recovery caps. Nothing burns spend unbounded.
4. **The model is a config value** — swapping providers is a YAML edit; missing API keys degrade routes to a working fallback instead of crashing.
