# Factory vs Claude Code — long-horizon benchmark

Answers: **does the improved factory (open models, no Anthropic) match plain
Claude Code on real backlog tasks, at a fraction of the cost?**

Historical baseline (the "before" picture, from `state/factory.db`): ~0.68
merged stories/day, mean $17/shipped story, median ~17 calendar days/story.

## Arms

| arm | what runs | accounting |
|---|---|---|
| `factory` | improved chain (Azure open models, dev convergence ON) in an **isolated bench root** — own state db/settings/worktrees; production scheduler untouched | tokens from the bench db's `runs` rows; `$` derived from the recorded price table |
| `claude` | one-shot `claude -p` at a **pinned `--model`** in a worktree, same prompt text | tokens + `total_cost_usd` from the CLI JSON |

Both arms get the same frozen `base_sha`, the same prompt (the real
direction/story markdown), and the same done-oracle: sacrifice's own gate
commands run via the factory's `_isolated_test_env`, plus a blind LLM-judge
rubric (judge never sees which arm made the diff).

## Tokens are the metric; dollars are a view

Report and compare **tokens** — they are provider-reported and exact. Dollars
are derived, and the factory arm's rate table carries an **estimated**
deepseek-v4-pro cache-read rate (no Azure meter publishes one for this
deployment, and the account lacks the Cost Management RBAC role to reconcile
against the real bill). Every `result.json` therefore serializes the full price
table plus its content hash, so a later price correction re-derives every past
dollar figure without re-running anything — and only the `$` column moves.

In `summary.md`, `?` means **not reported**. It is not zero.

## Reproducibility invariants

- **`base_sha` is pinned to a literal 40-char SHA.** It used to be `""` and
  resolved `origin/main` at run time, which made the base tree a function of
  *when* an arm ran; two arms a week apart silently compared different code.
  `_base_sha` now refuses an empty or abbreviated value instead of resolving it.
- **The Claude arm pins `--model`.** Without it the CLI picks whatever it
  currently defaults to, so the arm has no stable identity across a campaign.
  Both the requested and the resolved model id land in `result.json`.
- **`clean()` keeps `bench/runs/`.** It used to end in
  `shutil.rmtree(RUNS_DIR)`, which is why all 20 rows in the July 2026
  `summary.md` have no surviving `result.json` — routine cleanup destroyed the
  evidence behind every published number. Use `clean --purge-runs` to delete
  them deliberately. Worktrees and branches are still removed; those are
  reproducible from the pinned SHA.
- **Every `result.json` records its provenance**: `base_sha`, `routes_sha`,
  `price_table_sha` (+ the table itself) and `bench_sha`. `report` surfaces
  these and prints a loud warning if the rows it is tabulating do not share a
  base SHA, because such rows are not comparable.

## Protocol

1. Freeze the campaign: set `base_sha` in `tasks.yaml` to a real 40-char SHA
   (`git -C ../sacrifice rev-parse origin/main`).
2. Per task (see `tasks.yaml`; N=2 for t1–t7, N=1 for the epic t8):
   ```bash
   uv run python bench/bench.py run-claude  --task <id> --run <n> [--model <id>]
   uv run python bench/bench.py run-factory --task <id> --run <n>
   uv run python bench/bench.py gate   --task <id> --arm <arm> --run <n>
   uv run python bench/bench.py rubric --task <id> --arm <arm> --run <n>
   ```
3. `uv run python bench/bench.py report` → `bench/results/summary.md`.

## Preconditions

- Azure credentials in `.env` (the factory arm runs entirely on the
  mv-coding-agent-foundry deployments: gpt-5.4 / gpt-5.3-codex / deepseek-v4-pro).
- `sacrifice-db` container startable (`make -C ../sacrifice up-db`) — the
  smoke gate boots isolated backends against it.
- Claude subscription authed on this machine (`claude -p` works).
- Don't run two arms of the same task concurrently (they share uv/docker).

## Success definition

Parity: factory gates-pass rate ≥ claude on t1–t7 at ≤ 1/5 the token cost.
t8 (epic) measures the remaining long-horizon ceiling gap and is expected
to favor Claude Code.

## Known confounds (accepted + why)

- **Retries**: the factory gets its retry budget inside one invocation
  (convergence loop); claude gets one shot with in-session iteration. This is
  the design difference under test, not a bug — both are "the tool as used".
- **Judge**: gpt-5.4 is also a factory-arm persona model; mitigated by
  blinding (anonymous diffs, no arm labels). No model exists that is in
  neither arm and free of family bias in some direction.
- **Shared db container**: smoke runs of both arms use the sacrifice-db
  container with throwaway rows; journeys are register-fresh each run.
- **Missing third arm**: `factory` vs `claude` confounds *scaffold* with
  *model*. An absolute factory score measures the models in `routes.yaml`,
  which are a config value that gets swapped as cheaper models ship. The number
  that measures the PRODUCT is scaffold lift — the factory versus the same
  weights bare. See `PLAN.md` 1.4 / 2.2 arm B. Never report a factory number
  without the matched bare-model number beside it.
- **Contaminated task pool**: the six directions behind t1–t6 (`023`–`028`) are
  now `closed` — the factory has since shipped them, so they can no longer be
  used as held-out tasks. See `PLAN.md` 2.1.
