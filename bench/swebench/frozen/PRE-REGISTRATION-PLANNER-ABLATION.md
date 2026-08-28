# Pre-registration — the planner ablation, isolated on DeepSeek V4 Flash (Sail)

**Status: FROZEN 2026-08-28.** Decision rule and instance set locked before any
paid call. Same discipline as `PRE-REGISTRATION-SAIL-AB.md`: every number
carries the query that re-derives it, nothing is quoted forward without its
arm id.

## The question

E5.4 measured that adding a planning step before the builder made results
*worse* (5/8 vs 6/8, at 1.6× the cost) — but that arm (`chain`) confounded the
planner with a reviewer (planner V3.2 · builder V3.2 · reviewer gpt-5.4 vs
bare V3.2 builder). The best available outside evidence (a larger, more
rigorous study, arXiv 2604.12147 — see
`ai_docs/research/PIPELINE-ARCHITECTURE-RESEARCH-2026-08-28.md` §1) found the
opposite: removing the plan consistently *hurt* performance, on the same
general shape of task this project benchmarks on. This experiment isolates
the planner alone — same model in both roles, no reviewer in either arm — on
the model this factory actually runs in production, at a scale (n=25 pairs)
big enough to clear real statistical significance if the effect is there.

## Treatment definition

| | no-planner control | planner treatment |
|---|---|---|
| arm id | `flash-noplan-sail` | `flash-plan-sail` |
| planner | — | `sail/deepseek/deepseek-v4-flash-0731` |
| builder | `sail/deepseek/deepseek-v4-flash-0731` | `sail/deepseek/deepseek-v4-flash-0731` |
| reviewer | — | — |
| width | 2 (registry-capped; see below) | 2 (registry-capped) |
| k | 1 (single run per instance per arm) | 1 |

**Why width 2, not higher, and why it's a registry cap, not an operator flag.**
The Sail A/B (`frozen/PRE-REGISTRATION-SAIL-AB.md`, R5) measured this exact
deployment clean at width 2 with zero empty turns and zero starvation; width
> 2 was never probed. Both new arms declare `max_workers=2` directly in the
registry rather than relying on `--workers 2` at launch, so no invocation —
today's or a re-run months from now — can silently drift to the unmeasured
range. Verified live: `run-all --workers 3 --dry-run` on this arm reports
`workers=2` — the registry cap overrides the request.

**Same model, both roles, on purpose.** This isolates the STRUCTURAL question
(does splitting one call into two help) from a CAPABILITY question (would a
smarter planner help) — the same discipline `chain`'s confound argues for.

## Instances — 25, freshly drawn, isolated from the shared manifest

**Not drawn via `fetch`, and not added to `bench/swebench/manifest.json`.**
`fetch` overwrites the shared manifest wholesale; `random.Random(seed).sample`
gives no guarantee that a bigger `--limit` at the same seed keeps a smaller
draw as a prefix; and the shared manifest is cited by exact sha in multiple
FROZEN documents this project never edits. Editing it for one experiment
risks corrupting all of them.

Instead: a **separate manifest + oracle store**, in their own directory,
selected via one environment variable that every existing caller of
`_manifest()`/`_load_oracle_store()` ignores when unset (verified: the full
adapter test suite is green with the mechanism present and unused).

```
export SWEBENCH_MANIFEST_DIR=/home/k/software-factory/bench/swebench/planner-ablation
```

Drawn 2026-08-28 by `/tmp/planner-ablation-scratch/draw_planner_ablation_instances.py`
(reuses `_all_rows`/`_row_to_instance`/`_resolve_image_digest` — the exact
functions `fetch` itself calls — writing to the alt directory instead):
dataset `swe-rebench`, language `python`, `created_at_after=2026-01-01` (the
same conservative cutoff `fetch` defaults to), **seed 20260828**, pool 215.

**`manifest_sha256=d59df2d806bd2287`** — re-derive with:
```
SWEBENCH_MANIFEST_DIR=bench/swebench/planner-ablation python3 -c \
  "import json; print(json.load(open('bench/swebench/planner-ablation/manifest.json'))['manifest_sha256'])"
```

The 25 instances (alphabetical): `allenneuraldynamics__aind-data-schema-1677`,
`chaoss__augur-3512`, `cs-si__eodag-2176`, `harumiweb__exstruct-113`,
`hiero-ledger__hiero-sdk-python-1914_interface`,
`hiero-ledger__hiero-sdk-python-2007_interface`,
`jlowin__fastmcp-3237_interface`, `jmcgeheeiv__pyfakefs-1286`,
`koxudaxi__datamodel-code-generator-3070`, `marimo-team__marimo-8401`,
`meltano__meltano-9929`, `microsoft__qcodes-8039`,
`open-telemetry__opentelemetry-python-4891`, `pandas-dev__pandas-64104`,
`psf__black-4952`, `pypa__build-1027`, `pypa__twine-1309`,
`pypsa__pypsa-1653`, `pytest-dev__pyfakefs-1269`, `pytest-dev__pyfakefs-1286`,
`raullenchai__rapid-mlx-341_interface`, `scipy__scipy-24282`,
`scrapy__scrapy-7255`, `tox-dev__tox-3666`, `tox-dev__tox-3683`.

No overlap-avoidance with the E5/Sail-A/B instance sets was applied or is
needed — a shared `instance_id` across unrelated arms is normal (many arms
already run against the same pinned pool by design); what matters is that
BOTH arms of THIS comparison run on the SAME 25, which they do by
construction.

## Isolation — proven live, today, on the current code

Per the operator's explicit requirement: every run must be independent of
every other, with no way to see prior work. Re-verified today (not assumed
from the Sail A/B campaign, since the harness changed since — the structured-
output fix landed the same day):

- `tests/test_swebench_sandbox_isolation.py`: 55/55 green on today's code.
- **Live planted-leak proof, run today**: a marker written to the shared
  `/tmp/report.json` path (the name 13 different adw_ids collided on during
  E5) is `FOUND` on the host and **`NOT-FOUND`** from inside
  `SWEBENCH_SANDBOX=1` — proven, not assumed.
- **Live detector proof, run today**: a synthesized cross-run reference
  staged into a run's own trace is caught by `audit` with exactly one
  `foreign-workdir` finding, and the row is refused (`audit_ok=0`), never
  silently counted.
- Every campaign row runs under `SWEBENCH_SANDBOX=1`; the audit step re-runs
  immediately before any row is recorded (closes the "stale green audit"
  gap the Sail A/B also had to account for).

## Execution — single run, resubmit once on infrastructure failure

Per the operator's instruction: **k=1** (one run per instance per arm, not
the Sail A/B's k≥2 recommendation for marginal-cell noise — accepted as a
simplification for this bigger-effect-size question, revisited if the result
comes back ambiguous). An **infrastructure failure** (provider-starved /
empty-turn / audit-invalid / engine crash) is not a measurement — it is
repaired **once**, disclosed, both attempts kept in the store (same rule as
the Sail A/B). A second failure on the same cell is left as-is and reported,
never retried indefinitely. An oracle FAIL with a valid audit is a real
result and is never re-rolled.

Every `run-all` invocation is followed by committing the campaign-record
files it touched (`sweep-flash-noplan-sail.json`, `sweep-flash-plan-sail.json`,
this results section) before the next invocation launches — the same
row-validity discipline the Sail A/B's supersession note established.

## Budget

Computed-at-pinned-rates estimate: ~$0.03–0.08/task for the no-planner arm
(the Sail A/B's own `flash-solo-sail` cells), plausibly up to ~2× that for
the planner arm (one extra full model call). 50 runs, ballpark **$3–8
computed total** — a small fraction of the $60 the operator approved, with
headroom for the one-time repair of any infrastructure failure.

## Decision rule — pre-declared, before any data exists

**Primary: exact two-sided sign test on discordant pairs.** For each of the
25 instances, did the two arms agree or disagree (resolved/not-resolved)?
Only disagreements carry information. If all 25 instances were discordant,
18 or more leaning one way would clear p<0.05 (exact binomial: k=18/25 gives
p=0.0433) — the real threshold depends on how many pairs are actually
discordant, which is not known in advance; re-derive it from the observed
count before reading a result as significant. If fewer than ~10 pairs are
discordant, this experiment is honestly underpowered and will be reported as
such rather than stretched to a conclusion.

**Secondary, post-hoc, zero additional cost, and specifically NOT used to
select or stratify instances beforehand:** after all 50 runs are graded and
locked, pull each instance's real gold-patch size (files/lines changed) via
the same oracle access `grade` already uses — never before locking results,
since the oracle is deliberately hidden from instance selection to avoid
biasing the draw. Check whether the planner's effect differs between larger/
messier tasks and small clean ones, per Claude Code's own published guidance
(plan mode recommended for "uncertain, multi-file" work, skipped for small
clear tasks — see the research doc §1) and the outside study's specific
finding that plan QUALITY moderates the effect. Read the actual planner
transcripts from the 25 `flash-plan-sail` runs and judge plan quality
directly — inspectable at zero cost, and the single best way to tell "planning
hurts" from "this planner writes bad plans" apart.

**What this does NOT answer:** planner effects on any other model; planner
combined with a reviewer; different planner prompts; anything about
capability differences between providers (out of scope — this is a
same-provider, same-model comparison).

## Re-derivation query (verdicts, once run)

```sql
SELECT instance_id, arm, attempt, oracle_resolved, cost_usd, empty_response_turns
FROM run_attempt
WHERE reportable = 1 AND arm IN ('flash-noplan-sail', 'flash-plan-sail')
ORDER BY instance_id, arm;
```
