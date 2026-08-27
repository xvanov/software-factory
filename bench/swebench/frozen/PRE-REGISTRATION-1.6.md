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

## Arms — harness × model, stated in full

**Every arm is a (harness, model set) pair. Neither half may be omitted when a
number from this run is quoted.** An arm's score is a property of the pair, never
of the model alone and never of the harness alone.

| id | harness (the thing under test) | model(s), by role | tool interface | budget | what it measures |
|---|---|---|---|---|---|
| `factory` | **software-factory chain** — story seeded at `SM_DONE`, dev + reviewer personas, merge gates, run-until-green; the dev runs inside an **OpenHands sandbox** | dev standard `azure/deepseek-v4-pro` · dev hard-tier escape `azure/gpt-5.3-codex` · reviewer `azure/gpt-5.4` | native tool calls + real file editor (via OpenHands) | 16 orchestrator ticks; OpenHands `max_iterations` 600 per dev session; 5400 s wall | **the product** |
| `openhands` | **OpenHands 1.22.1, single agent, no chain** — no PM/SM, no reviewer, no gates, identical prompt | `azure/deepseek-v4-pro` only | native tool calls + real file editor | step cap matched to the factory's effective budget; 5400 s wall | **the chain's contribution** — weights, prompt and tools held constant, chain removed |
| `bare` | **hand-rolled ~100-line text loop** — one flat string per turn, `BASH:` markers scraped from prose, one shell command per turn, observations truncated at 4,000 chars, edits by `sed`/heredoc | `azure/deepseek-v4-pro` only | **none** — no tool-calling API, no editor tool | 40 steps; 300 s per command; 5400 s wall | the floor of *our own minimal protocol* |
| `claude-5` | **Claude Code CLI 2.1.220** — the CLI *is* the harness (its own tool set, its own agent loop); subscription-billed, `--safe-mode`, MCP disabled, WebFetch/WebSearch removed | `claude-opus-5` | Claude Code's own tools | 60 CLI turns; 5400 s wall | frontier reference |
| `claude-4.8` | **Claude Code CLI 2.1.220**, identical invocation | `claude-opus-4-8` | Claude Code's own tools | 60 CLI turns; 5400 s wall | **contamination probe** — same harness, older cutoff (Jan 2026 vs May 2026) |

Three things this table is designed to stop being misread:

1. **`bare`'s weakness is our harness, not the model.** `deepseek-v4-pro`
   supports tool calling — proven by the fact that the `factory` arm's dev
   already drives that same deployment through OpenHands. The bare arm simply
   does not *use* tool calling: it parses markers out of prose, which is why 34
   of 182 replies were unparseable and 13 were native ```bash fences the parser
   discarded. Treat `bare` as a floor on the protocol, never as a statement
   about the weights.
2. **The three DeepSeek arms are a ladder on identical weights** — no tools
   (`bare`) → real tools (`openhands`) → real tools + the chain (`factory`).
   Only adjacent rungs are attributable: `factory − openhands` is the chain,
   `openhands − bare` is the tooling. `factory − bare` is both at once, which is
   why the retracted "+58 pp scaffold lift" could not be assigned to either.
3. **For the Claude arms, Claude Code IS the harness.** It is not a model call
   and not an Azure or API route — it is the `claude` CLI binary on this machine
   on a subscription, with its own agent loop and tool set. `--model` is a flag
   on that binary, so `claude-5` and `claude-4.8` are the *same harness* twice.
   Consequently `factory vs claude-*` varies harness **and** model
   simultaneously and is not attributable to either; it is a reference point,
   not a scaffold measurement.

`openhands` is the arm the previous run lacked, and the reason its headline was
unattributable.

### `bare` is demoted, capped, and on probation

It was the incumbent baseline and the basis of the retracted "+58 pp". With
`openhands` in the suite it is **no longer a baseline for anything the product
claims**, because the only question it uniquely answers — how much value comes
from merely having usable tools — is one no decision depends on. We are never
shipping a no-tools harness.

It stays for exactly two reasons, both cheap:

1. **A ~$5 sanity canary.** If `bare` ≈ `openhands` ≈ `factory`, the tasks are
   too easy or the oracle is broken. That failure mode has bitten this harness
   before and deserves a tripwire.
2. **Public comparability.** Minimal-scaffold numbers are the leaderboard
   convention. Nebius publishes this same `deepseek-v4-pro` deployment at
   **40.2%** under a minimal scaffold; without our own bare row we cannot place
   our model against that figure *on our instances* — only against their pool,
   which is not paired with ours.

For the record, a minimal loop is not inherently useless: mini-SWE-agent is a
~100-line bash-only loop with no tool-calling API, and its authors report it in
the mid-60s% on SWE-bench Verified with a frontier model (their published claim,
not our measurement). Our arm's 0/19 was a defect, not a refutation of the
design — 10 of its 19 rows located the correct file and then fumbled the fix.

**Pre-committed cap: ONE repaired run, no iteration.** If the repaired arm reads
0/19 again, **delete the arm** and cite the published 40.2% as the external
anchor instead. Debugging a number no decision depends on is not a good use of
the budget. Under no circumstances does `bare` anchor a headline again.

## Table 1 — headline, one row per arm

Harness and models are repeated here, not cross-referenced — a headline row torn
out of this file must still say what produced it.

| arm | harness | model(s) actually used (from `result.json`, not from config) | resolved / audited-valid | rate | 95% CI (Clopper-Pearson) | invalid rows | fresh in | cache read | out | wall s (median) | $ | cost source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| factory | software-factory chain on OpenHands | dev `azure/deepseek-v4-pro` (n calls) + hard `azure/gpt-5.3-codex` (n) + reviewer `azure/gpt-5.4` (n) | / | % | [ , ] | | | | | | | price-table estimate |
| openhands | OpenHands 1.22.1 single agent | `azure/deepseek-v4-pro` (n) | / | % | [ , ] | | | | | | | price-table estimate |
| bare | hand-rolled text loop, no tool calls | `azure/deepseek-v4-pro` (n) | / | % | [ , ] | | | | | | | price-table estimate |
| claude-5 | Claude Code CLI 2.1.220 | `claude-opus-5` (+ the CLI's own `claude-haiku-4-5` side-classifier) | / | % | [ , ] | | | | | | | CLI-reported, subscription |
| claude-4.8 | Claude Code CLI 2.1.220 | `claude-opus-4-8` (+ side-classifier) | / | % | [ , ] | | | | | | | CLI-reported, subscription |

The model column is filled **from the per-row artifacts, not from
`routes.yaml`** — the retracted run's config said one thing while the ledger
showed 7 escalations to the hard tier, 4 of them behind resolved rows. Config is
intent; the ledger is what happened.

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

Each row names what is held constant and what varies. A comparison that varies
both halves of the (harness, model) pair is a reference point, not a measurement.

| comparison | harness varies? | model varies? | contingency (only-A / only-B) | McNemar exact p | what it isolates | may we act on it? |
|---|---|---|---|---|---|---|
| factory vs **openhands** | yes (chain vs none) | **no** — both `deepseek-v4-pro` | / | | **the chain** | **this is the product number** |
| openhands vs bare | yes (tool calls + editor vs text markers) | **no** — both `deepseek-v4-pro` | / | | the tooling | secondary; tells us how much of any lift is just having usable tools |
| factory vs bare | yes (both chain and tooling) | no | / | | chain **+** tooling, entangled | floor only, and only once bare is plausible vs the 40.2% public anchor |
| factory vs claude-5 | yes | **yes** | / | | nothing attributable | reference point, never a scaffold deficit |
| claude-5 vs claude-4.8 | **no** — same CLI, same flags | yes (May-2026 vs Jan-2026 cutoff) | / | | **contamination** | a gap favouring opus-5 on low-margin rows is the memorization signal |
| high-margin stratum (n=4) vs rest (n=15), within each arm | no | no | | | contamination, within arm | n=4 — descriptive only |

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
5. **No re-rolls of an OUTCOME. Repairing an INFRASTRUCTURE loss is allowed,
   once, and must be disclosed.** *(Amended 2026-08-04, after the fact — see the
   honesty note below.)* The distinction:
   - **Audit-invalid** (integrity: oracle-probe, retrieval, refused paths) →
     published as invalid, **never re-run**. Re-running it would be selecting on
     the integrity gate, which is what the 2026-08-03 retraction was about.
   - **Budget-exhausted** (turn cap, wall cap) → a completed attempt. Counted,
     flagged, **never re-run**.
   - **Infrastructure loss** (provider 429, sandbox crash, harness defect — the
     run produced no metered result through no fault of the arm) → **may be
     re-run once.** Both attempts must be recorded, the re-run must be flagged in
     the table, and **if the outcome differs between attempts, both outcomes must
     be published** with the re-run's used as the headline and the first stated
     beside it. One repair per row, ever; a second infrastructure loss on the
     same row is published as lost.

   **Honesty note, because this rule was amended after it was applied.** On
   2026-08-04 three `openhands` rows died on Azure 429s recording zero cost and
   zero tokens. They were re-run under the reasoning above — which was sound but
   was not written down first, so the generated report ended up counting three
   `attempt: 2` rows while its own "Discarded runs" section called `attempt > 1`
   "a protocol violation, not a data point". That contradiction is the reason this
   rule now exists in this form. Outcomes: `jsonpickle-588` resolved twice,
   `rapid-mlx-289` resolved twice, **`keras-22316` flipped wrong-fix → resolved on
   the second draw.** Conservative reading 9/19 = 47%; re-run reading
   10/19 = 53%. Both are published. A rule invented after seeing the data is worth
   less than one fixed in advance, and this one is recorded as such.
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

---

# Outcome — recorded 2026-08-04, after the run

**Nothing above this line was edited after the data existed.** Everything above
is the pre-registration as committed; this section is the only addition.

Result: `bench/swebench/results.md`, backed by
`results-archive/2026-08-04T04-18-05.349995Z/` and re-derivable with
`report --check`. Five arms, one sweep, n=19, k=1, no re-rolls, `attempt: 1` on
all 95 rows.

| arm | resolved / audited-valid | rate | 95% CI | $ |
|---|---:|---:|---|---:|
| claude-5 | 15/19 | 79% | [54%, 94%] | 34.36 |
| claude-4.8 | 14/19 | 74% | [49%, 91%] | 23.56 |
| openhands | 7/16 | 44% | [20%, 70%] | 15.37 |
| factory | 7/19 | 37% | [16%, 62%] | 35.94 |
| bare | 1/18 | 6% | [0%, 27%] | 7.94 |

## Rule 1 fired, and is honoured in its own words

> **1. The product claim is `factory − openhands`.** If that difference is ~0, the
> chain adds nothing on this suite and the honest headline is "our lift comes from
> using a competent agent loop, not from the chain". That outcome gets published
> in the same words.

Measured: **37% vs 44%, McNemar exact p=0.625** over the 16 instances where both
arms are audited-valid (only-A/only-B = 1/3). That is ~0 — indeed directionally
negative. So, in the pre-committed words: **our lift comes from using a competent
agent loop, not from the chain.** `STATUS.md`, `PLAN.md`, `bench/README.md` and
the repo `README.md` all now lead with that sentence.

Two things the rule does *not* license. At the pre-stated MDE (±38 pp, "What this
run cannot show" above) a −7 pp
difference is **no measurable lift**, not measured harm — no doc may imply the
chain hurts. And the chain's cost penalty is separate from and larger than its
resolve-rate difference: **$5.13 per resolved instance vs $2.20**, i.e. 2.3× for
no measurable gain, on one price-table basis.

## Rule 2 — `bare` has consumed its one repaired run

> **Pre-committed cap: ONE repaired run, no iteration.** If the repaired arm reads
> 0/19 again, **delete the arm** …

It did not read 0/19; it read **1/18 = 6%** [0%, 27%], and the repair demonstrably
worked: **727 model calls** and **16 of 18 valid rows budget-exhausted**, against
a mean of 9.2 steps and zero cap hits in the void run. The arm now genuinely
iterates and still resolves 6%, well under the 40.2% public anchor for the same
deployment under a minimal scaffold.

So the literal deletion trigger did not fire, but **the one repaired run is
spent** and the cap's intent binds: no further debugging of this arm. Whether
`bare` stays in the suite is now an operator decision. Either way it anchors no
headline, and `openhands` — not `bare` — is the matched baseline for every
product claim.

Its one useful contribution this run was as a canary in the other direction:
`openhands − bare` = +38 pp at **p=0.031** is the sweep's only significant result
among the three DeepSeek arms, and it is what the retracted "+58 pp scaffold lift"
had actually been measuring — usable tools, not orchestration.

## Rules 3–6

- **3 (no absolute rate without its margin column)** — honoured. Table 2 prints
  `margin_days` per model bound; Table 4 names the bound TYPE.
  `deepseek-v4-pro` is still `release-date-proxy` with 15 of 19 instances inside
  it. **The Claude half of the contamination question is now answered:**
  `claude-opus-4-8` (published cutoff Jan 2026) 74% vs `claude-opus-5` (May 2026)
  79%, same harness, same flags, **p=1.000**, on a manifest where 19/19 instances
  predate opus-5's cutoff. Memorization is not carrying the reference arm.
- **4 (a budget-exhausted run is a counted attempt for every arm)** — honoured.
  16 bare rows and 1 claude-4.8 row are counted and flagged, none excluded.
- **5 (no re-rolls)** — honoured. The one audit-invalid row is published as
  invalid: `bare` on `hiero-ledger__hiero-sdk-python-1914_interface` ran
  `curl -s https://raw.githubusercontent.com/…/account_info.py`, the upstream
  source of the exact file under test. Zero path-based oracle probes anywhere.
- **6 (report the subset relation)** — honoured, and it still holds: the
  factory's 7 passes are a **strict subset** of `claude-opus-5`'s 15 (only-B = 0
  in that pair). Against `claude-opus-4-8` the factory wins exactly one instance,
  `hkuds__openharness-217`.

## "What this run cannot show" was right

The MDE was pre-stated at **±38 pp** and the product delta came in at −7 pp. The
design could not have answered its own question at any outcome. **k ≥ 3 is now
the top priority in Phase 2**, ahead of growing the manifest — see `PLAN.md` 2.1.

One honest note against this file: the ±38 pp figure was computed against a 58%
baseline, which the run then measured at 37%. At n=19 that does not narrow the
MDE to anything that would change the conclusion.

## Debts this run left open

Reporting, not measurement; neither moves a published number. Tracked as
`PLAN.md` 1.6 G.

- **No retry on a provider 429.** `openhands` lost 3 of 19 rows to Azure
  `DeepSeek-V4-Pro` rate limits, and **2 of the 3 had already produced patches the
  oracle RESOLVES** — counted, `openhands` is 9/19 = 47% and the gap to the chain
  widens. A dropped row records `cost_usd: 0.0`, which reads as free rather than
  as missing.
- **`sweep-<arm>.json` aggregates contradict their own rows.** They are in-flight
  snapshots written before grading and before the #227 detector fix, so
  `sweep-factory.json` reports `resolved: 2, audit_failed: 13` while its own
  `results` list says 7 resolved and the archived `audit.json` files say 19 ok /
  0 invalid. Only `results.md` and the archive are authoritative.
- The 04-18 archive carries only `sweep-bare.json` and `sweep-factory.json`, not
  all five arms' sweep summaries.
