# STATUS — measured 2026-08-04, independently audited 2026-08-07

Point-in-time facts. Verify before you rely on them. The commands are in
`CLAUDE.md`. The forward work queue is the **Exteroception v1 direction**
(`apps/factory/directions/` — the newest direction); the retired long-form plan
is archived at `docs/archive/PLAN-2026-08-07-retired.md`.

All systemd units are deliberately **stopped**. Run `factory on` to start.

**Read this first.** The clean five-arm benchmark is in. **The chain shows no
measurable lift over a single OpenHands agent on the same model** — 37% vs 53%,
McNemar exact p=0.375 — at 2.8× the cost per resolved instance. What produces
the lift is *tooling*, not orchestration. Nothing in this file supports "the
chain is proven".

**The 2026-08-07 audit.** A four-agent independent audit re-derived the sensor
report's claims (report: the "Sensor Problem" artifact; summary in memory
`sensor_report_audit_2026_08_07`). The sensing thesis survived; six claims were
corrected — they are folded into the tables below. The audit also found that a
prior session's fix for two live sacrifice bugs **was never committed**; both
were re-fixed and merged as **sacrifice PR #378** (2026-08-07).

## Operator decisions — 2026-08-07 (do not re-litigate)

1. **Cheap-model thesis stays, reframed**: the claim is "buy throughput the
   subscription can't sell", success = tasks/day at acceptable defect rate,
   not $/task.
2. **Commit0-Lite runs LAST** — only after Exteroception P0–P2 are complete and
   soaked. No experiments while the verifier is broken.
3. **Operator ratification budget: ~2 h/day.** The always-on vision is in scope.
4. **Sacrifice is a benchmark corpus + sensor testbed, not a product.** Its 45
   held-out pm-validated directions are the SacrificeBench pool; the app is the
   bootable target the out-of-process oracle is developed against.
5. **PLAN.md is retired** into the Exteroception direction; its correction
   ledger is archived, not deleted. **E.5's pre-committed "one honest L1→L4
   cycle before deleting" is explicitly retired** — the manager's four LLM
   tiers are scheduled for deletion (operator PR) in favor of the
   detector-ratchet design.

## The benchmark — measured 2026-08-04, five arms, n=19

Suite: SWE-rebench (Nebius), pinned manifest `923aef05add32124` — 19
working-oracle instances, one sweep, k=1, no re-rolls, tables pre-registered in
`bench/swebench/PRE-REGISTRATION-1.6.md` before the data existed.

> **Provenance.** Two `report` runs exist for this sweep; this file uses the
> later archive (`results-archive/2026-08-04T23-19-24.998844Z/`), which re-ran
> three rows lost to Azure 429s. The earlier archive reports `openhands`
> 44% / p=0.625 / 2.3×. **The conclusion is the same under either report** —
> chain below one agent on the same model, p > 0.3, and at MDE ≈ ±38 pp that is
> "no measurable lift", **not** "the chain hurts". Re-derive:
> `uv run python bench/swebench_adapter.py report --from-archive bench/swebench/results-archive/2026-08-04T23-19-24.998844Z --check`

| arm | harness × model | resolved / valid | rate | 95% CI | $ | $ / resolved |
|---|---|---:|---:|---|---:|---:|
| claude-5 | Claude Code CLI × `claude-opus-5` | 15/19 | **79%** | [54%, 94%] | 34.36 † | 2.29 † |
| claude-4.8 | same CLI × `claude-opus-4-8` | 14/19 | **74%** | [49%, 91%] | 23.56 † | 1.68 † |
| openhands | one OpenHands agent × `deepseek-v4-pro` | 10/19 | **53%** | [29%, 76%] | 18.20 | **1.82** |
| factory | the chain × deepseek-v4-pro + gpt-5.3-codex + gpt-5.4 | 7/19 | **37%** | [16%, 62%] | 35.94 | **5.13** |
| bare | text loop, no tools × deepseek-v4-pro | 1/18 | 6% | [0%, 27%] | 7.94 | 7.94 |

† CLI-reported against a subscription vs Azure price-table estimates — different
accounting bases; never sum them. `factory` vs `openhands` is one basis, exact.

Key pairs (McNemar exact): **factory vs openhands p=0.375** (the chain — no
measurable lift); **bare vs openhands p=0.004** (the tooling — the only
significant result); claude-4.8 vs claude-5 p=1.000 (**contamination probe
clean**). The factory's 7 passes are a strict subset of claude-5's 15.
Chain-verdict precision **6/15 = 40%**; one row went green on a **zero-byte
production patch** (`harumiweb__exstruct-113`).

**Reviewer ablation (2026-08-05, `solo-noreview`):** removing the reviewer
round-trip = 9/18 = 50% at **$2.83/resolved** vs the chain's 7/19 = 37% at
$5.13 — the 29% cost saving is real (9 fewer dev calls, 1 tick vs 4; reviewer
tokens were only 1.8% of spend); the quality delta is inside the ±38 pp MDE
(p=0.688) and the ablation is confounded three ways. Clean re-run (both arms,
one sweep, one commit, ~$62) is queued in the Exteroception direction.
Evidence: `bench/swebench/RESULTS-B1-PHASE1A.md`.

## What works

| Capability | Evidence |
|---|---|
| Loop 1 — builds an app | 91 sacrifice stories reached the `deployed` state; 71 of 84 merged sacrifice PRs are chain branches |
| Loop 2 — builds itself | 24 factory stories deployed; staging twin 17 validated / **3 fatal self-edits rejected**. Scale caveat (audit): those 24 chain PRs are ~14% of the factory repo's 173 merged PRs — the operator authored ~148 |
| PR pipeline | 122 stories opened a PR; 118 merged |
| Review convergence | 0 stories hit the cycle cap in 14 days |
| CI-failure recovery | Real CI log fed back to dev as a structured finding, capped at 3 |
| Spend control | Daily cap in `factory_settings.yaml`, hourly cap, per-story budget |
| Test suite | 2,368 tests, ~5 min |
| SWE-bench measurement pipeline | Hidden sha256-pinned oracle, test-edit stripping asserted on every arm, `--network none` grading, gold-patch control 19/20, `report --check` byte-stable. Four retractions paid for it — do not "improve" it without a failing case |
| The one exteroceptive gate | `smoke-green` blocked 578 merge *evaluations* (10 distinct PRs; 2 PRs = 86%) — the most active gate blocker. The seed of the target architecture |

Note (audit): **"deployed" is a state name, not a deploy.** All 102
`deploy_actions` rows skipped (`deploy_disabled_in_config`) or errored;
`smoke_passed`/`health_check_passed`/`rollback_triggered` are 0 on every row.

## What does not work

| Problem | Evidence | Where the fix lives |
|---|---|---|
| **No measurable chain lift, at 2.8× cost** | The table above | Exteroception direction (verify first, then B-phase collapse) |
| Chain green ≈ coin flip | Verdict precision 6/15 = 40%; zero-byte green | Direction P1–P2 |
| **The acceptance oracle's green is forgeable in-process** | 3 lines of production code patch pytest's runner; no file rollback closes it; pinned as `xfail(strict=True)`. This is why `gates.acceptance_oracle` is off everywhere | Direction P2 — out-of-process runner |
| Manager LLM tiers: cost without yield | All three LLM personas = **$1,028.58 = 52.0%** of all-time spend (watcher alone $972.23 = 49.2%, 44,127 runs); 262 concerns → 165 proposals (48 titles / ~37 root causes, 107 escalate-to-human) → **0 applied fixes**, 1 GitHub issue (via staging, not apply). L4: 163 attempts, 0 PRs | Direction P0 — delete the four tiers (operator PR); E.5 soak retired by operator decision |
| `factory_improver` | 196 proposals → **1 landed commit ever** (PR #5); 179 apply failures, 158 `dirty_working_tree` | Direction P0 — retire |
| Detector coverage is partial | 11 registered detectors; the watcher hard-codes 9 — `conformance_breach` and `fms_yield` have **never run** | Direction P0 — detector ratchet |
| Scanner personas manufacture noise | `bug_hunter` 705 runs, 0 findings; `ralph` 7,024 runs, 95.8% rate-limited; 70% of the sacrifice backlog was machine-filed, one direction re-filed 33× | Direction P0 — delete scanners; goal supply becomes human-ratified |
| Merge-gate precision is unknown | Every published precision number is chain-verdict precision; `gate_enforced: false` in all six bench arms | Direction P2 |
| A sweep silently loses runs to provider 429s; sweep aggregates contradict their rows | See archive notes | Bench queue (operator PR): 429 retry, aggregate recompute |
| State has no backup | The twin guards source only | Direction P0 (E.1 carried over) |
| `software-factory-copy` is public | It receives every candidate self-edit diff | Operator action (E.3 carried over) |

## Sacrifice — current state (2026-08-07)

- **PR #378 merged**: the wrongful-charge path (`inconclusive_reason` dropped in
  `api_check.py`) and the unvalidated dev-sandbox clone URL are **fixed**, with
  wire-level regression tests. Clone-URL policy: validate the **host**, never
  the scheme (ssh/scp-style remotes are a supported feature).
- Deployment is down (`sacrifice-backend.service` failed, `/api/health` → 502)
  and stays down until the direction's testbed work needs it.
- Gates are hollow: CI typecheck force-exits 0 over 208 real mypy errors; lint
  is changed-files-only over 100 whole-tree errors; Jest (267 tests) and the
  clean `tsc --noEmit` are not in CI; Playwright collects 35 tests of which 21
  self-skip on `E2E_HARNESS_READY` (set nowhere) and none run in CI. In-process
  to out-of-process test ratio ≈ **300:1**. Un-hollowing is direction P0.
- Authorship (audit): the product skeleton is 26 direct human commits
  (2026-05-18/19); the factory's share of surviving lines is **≤ 37.7%** (upper
  bound; the worker commits under the operator's identity); 25 of 72 merged
  factory PRs touched zero production code.

## Two self-modification paths — do not confuse them

- **Chain self-edit (loop 2): works.** direction → story → dev → gates → PR →
  staging twin → merge. 24 factory stories deployed this way.
- **FMS L4 apply: dead** (0/163) and scheduled for deletion.
Measuring only the second produces "the factory cannot improve itself" — false.
Measuring only the first produces "the chain built the factory" — also false
(audit: ~25 of 173 merged factory-repo PRs are chain PRs).

## Cost

July, from the `runs` ledger: $588.78 all-in across 75 deployed stories =
**$7.85/story**; excluding the manager $217.18 = **$2.90/story**. Dollar figures
are partly estimated (cache-read rate unverifiable); prefer token counts.

## Benchmark harnesses — two, do not confuse them

- **`bench/swebench_adapter.py` — the one that counts.** Externally graded,
  archived, `report --check` byte-stable. `bench/swebench/results.md` and
  `results-archive/**` are generated/archival records — **never hand-edit**.
- **`bench/bench.py` — retired for grading** (scores the factory on tests the
  factory wrote). Usable only as a convergence harness.

## Standing evidence locations

- Sensor report (audited v5): claude.ai artifact `2c5bbaef-…` — the strategic
  review this direction implements; corrections marked ⟲.
- Reviewer replay corpus backup: `/home/k/sf-reviewer-corpus-2026-08-05/`
  (bench run dirs are gitignored and wiped by every sweep).
- Failure ledger: memory files (`MEMORY.md` index) + the archived plan's
  correction log (`docs/archive/PLAN-2026-08-07-retired.md`).

## CI cost

Root-level `*.md`-only PRs skip the expensive steps (~20 s); everything else —
including `factory/personas/*.md` and `apps/**/context/*.md`, which are code —
runs the full suite (~4 min). See `.github/workflows/test.yml`.
