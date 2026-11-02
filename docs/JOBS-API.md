# Factory ⇄ Personal Assistant job contract (v1, 2026-11-02)

The one interface between the personal assistant (PA, dev-tools/personal-assistant) and the
software factory (software-factory). The PA never imports factory code or reads its sqlite; it
runs these CLI commands on the factory's machine (locally, or typed into a termhub session on
that machine) and parses the JSON they print. Both sides build against this file in parallel.

All commands: `uv run factory <cmd>` from the factory checkout. Every `--json` command prints
exactly ONE JSON object on stdout and nothing else (logs go to stderr). Exit code 0 = the JSON
is a success shape; non-zero = stdout is `{"error": "<code>", "message": "..."}`.

## Delivery levels (shared vocabulary, ordered least → most autonomous)

`none` < `branch` < `draft_pr` < `pr` < `auto_merge` < `push_to_main`

- `none`      — work stays in the factory's worktree/local branch; nothing pushed.
- `branch`    — push the branch; open no PR.
- `draft_pr`  — push + open a DRAFT PR; never mark ready, never merge.
- `pr`        — open a ready PR; never merge.
- `auto_merge`— today's behaviour: merge when chain gates (+ required CI) pass.
- `push_to_main` — gates pass → fast-forward the default branch directly (no PR).

Per-app config (`apps/<app>/config.yaml`) sets only `delivery.default`. There is NO per-app
ceiling: a job's requested level wins in either direction (operator decision 2026-11-02 — the
operator tells the personal assistant the end state, and the assistant passes it on every job).
`delivery.max` in a config is refused at load. A malformed request resolves to `none`. Existing
apps with no `delivery` block behave exactly as today (`auto_merge`).

The PA always sends `--delivery` explicitly, chosen from what the operator asked for; the app
default applies only when a job omits it.

How the factory enforces it (see `factory/chain/delivery_gate.py`):

- The level is resolved ONCE when the job's story is spawned and recorded on the story
  (`StoryRecord.delivery_level` + a `delivery_level_resolved` event). Later app-config edits
  never change an in-flight story's level. An unknown/unreadable level resolves to `none`. A
  story with NO recorded level predates stamping and is backfilled with the pre-existing
  default, `auto_merge`.
- Every level runs the same chain (dev, review, tech_writer, docs enforcer) up to the point
  where work would leave the factory. Story end states, all terminal:
  `none` → `delivered_local` (committed on the local `story/<n>-<slug>` branch, nothing
  pushed); `branch` → `delivered_branch`; `draft_pr` / `pr` → `delivered_pr` (with the PR
  number); `auto_merge` / `push_to_main` → `deployed` (via `deploy_pending`).
- `push_to_main` first checks GitHub (`delivery_gate.push_to_main_preflight`):
  - if the default branch's own CI is red or still running, or GitHub cannot be read, the story
    is HELD (the same main-green hold PR merges get): untouched, re-checked every tick, with a
    `ci_hold_main_red:` reason visible in `factory inbox`. This is checked first: a red base
    holds even when it is also protected.
  - if the (green) default branch requires status checks or a pull request (branch protection
    or a ruleset), the factory never pushes directly and never forces. It FALLS BACK to
    `auto_merge` for that story (operator decision 2026-11-02): it opens a ready PR, re-stamps
    the story's level as `auto_merge`, and from then on the normal auto-merge path applies —
    main-green hold, the repo's required checks, the full gate set, then `gh pr merge --auto`.
    The fallback is recorded as a `push_to_main_fell_back_to_pr` story event with reason
    `push_to_main_fell_back_to_pr:<why>`, and `factory job status` reports it per story as
    `delivery_note`. When that PR merges, the push_to_main job is `done`. If opening the PR
    fails twice, the story parks in `blocked_deploy_failed`.
  - a hold is capped at 24 h: after that the story falls back to level `pr` (a ready PR for a
    human, ending `delivered_pr`), recorded the same way (`push_to_main_fell_back_to_pr:held
    since …`).
  Then it runs the full merge gate set against the worktree commit and pushes that exact
  commit to the default branch without force. Gate failures are capped at 3 per STORY (not per
  commit), then the story parks in `blocked_ci_unresolved`. If the push is not a fast-forward
  (or is rejected) it falls back to `pr`: the story's level is recorded as `pr`, a ready PR is
  opened, and the story ends in `delivered_pr`. Factory self-edits (`apps/factory`) are always
  treated as `pr` instead of `push_to_main`, because they must pass the PR staging gate.
- Whenever a story with a PR settles below `auto_merge`, the factory disarms any GitHub
  auto-merge on that PR (`gh pr merge --disable-auto`), so an earlier `--auto` cannot merge it
  behind the job's back. `factory job cancel` does the same.
- A `delivered_pr` story whose PR a human merges is picked up by the factory's GitHub
  reconciliation and continues to `deploy_pending` → `deployed` like any merged work. If the
  human CLOSES it unmerged, the story settles to `closed_by_operator`.
- The `delivered_*` states never close the story's GitHub issue (the change is not on the
  default branch yet). They DO count as finished for the direction: once every story of a job
  is `delivered_*` (or otherwise resolved), the direction is complete and its tracker issue is
  closed by the factory's hourly issue hygiene.
- Multi-story jobs below `auto_merge`: a later story does not wait for an earlier sibling to
  deploy (it never will without a human); a sibling in `delivered_*` satisfies the ordering.
  The later story is STACKED: its branch is cut from the latest delivered sibling's branch (the
  local branch at `none`, `origin/<branch>` once pushed), so it builds on that work. Its PR still
  targets the default branch and its body says `Stacked on <branch> (PR #n)` — merge in order.
- Cancel vs. merge: the final merge / fast-forward and its `deploy_pending` write run under a
  per-story lock (`state/locks/story-<id>.lock`) that `factory job cancel` also takes, after a
  re-read of the story; a story cancelled while its gates ran is never merged or pushed.
- Known gap: at `none`, the factory still opens the story's GitHub ISSUE (no code is pushed).

PA mode → delivery mapping (PA side owns this): plan→(not a factory job), local→none,
branch→branch, mr→draft_pr, full→draft_pr.

## Pipelines

`chain` (PM→SM→dev→reviewer→gates), `solo` (single dev agent + gates, B.1 solo mode), `auto`
(factory decides; v1: = app default, else `chain`).

Sharpened 2026-11-02 (`factory/job_routing.py`):
- Written to the direction frontmatter as `pipeline:`; absent = `auto`. `auto` resolves to the
  app's `pipeline_default` (`apps/<app>/config.yaml`; `chain | solo | auto`, default `chain`;
  an app default of `auto` also means `chain`). Change it with `factory app set <app>
  --pipeline-default`.
- Resolved ONCE at story spawn and stamped on the story (`StoryRecord.pipeline`); editing the
  direction or app config afterwards does not change an in-flight story.
- **`solo` is refused today** with `{"error": "pipeline_unavailable"}` — at submit and again at
  spawn. B.1 solo exists only as a bench arm; the production chain cannot yet skip the
  reviewer, so accepting `solo` would silently run `chain`. An `auto` job on an app whose
  `pipeline_default` is `solo` is refused the same way (never downgraded to chain). Once the
  engine lands, `solo` additionally requires the app to have `gates.acceptance_oracle: true`
  AND a `gates.acceptance_boot` recipe (B.1: with no reviewer, the oracle is the only signal
  the dev cannot influence); otherwise `pipeline_unavailable`.

## Model overrides

`--model <persona>=<model_id>` (repeatable) is written to the direction frontmatter as
`models: {persona: model_id}`.
- Keys: a persona name (`dev`, `reviewer`, `sm`, `pm`, `acceptance_author`, …) or
  `<persona>.<difficulty>` (`dev.hard`); the tiered key wins over the bare one.
- Values: `<provider>/<model>` LiteLLM ids. Providers: `azure/`, `azure_ai/`, `deepseek/`,
  `anthropic/` (ANTHROPIC_API_KEY), `openrouter/` (OPENROUTER_API_KEY), `openai/`,
  `openai_compat/` (generic OpenAI-compatible endpoint; OPENAI_COMPAT_API_KEY +
  OPENAI_COMPAT_API_BASE, both required). Full table: `factory/routes.yaml` header.
- **Precedence per key: job (`models:`) > app (`config.yaml::models`) > `factory/routes.yaml`.**
- Resolved at spawn and stamped on the story (`StoryRecord.model_overrides_json`); every run
  row records the model actually used, so cost/audit attribution follows the override.
- A model whose provider key (or required base URL) is not set degrades to the routes.yaml
  fallback with a warning, like a routes.yaml entry does — it is not an error.
- **Reviewer independence**: the reviewer must not share a model with any dev tier, checked on
  the MERGED map, and again on the models that will actually run here after missing-key
  degradation — both an override degrading onto the dev model and a routes.yaml dev tier
  degrading onto a job-named reviewer. A collision is refused with
  `{"error": "review_independence"}` — never auto-fixed; `FACTORY_ALLOW_REVIEW_COLLISION`
  does not apply to job/app overrides.
- Other refusals: `bad_model_flag` (not `persona=id`, or a persona given twice),
  `unknown_persona`, `bad_model_id` (no `<provider>/` prefix), `bad_pipeline`.
- Submit should call `factory.job_routing.resolve_job_routing(app_cfg, job_models=…,
  pipeline=…)` before writing the direction. A direction that reaches triage with a bad
  request anyway is set to `needs-direction` with `state.yaml::job_routing_error: {code,
  message}` before any PM call is spent.

## Commands

### `factory job submit --json`
```
--app <app>                      required unless --repo given
--repo <owner/name>              resolve to the registered app for that repo; error `unknown_repo` if none
--title <text>                   required
--ask-file <path> | --ask <text> required; the ask, in the requester's words + context (markdown)
--done <text>                    repeatable; acceptance criteria (one per flag)
--pipeline chain|solo|auto       default auto
--delivery <level>               optional request (clamped, see above)
--model <persona>=<model_id>     repeatable; per-job route override
--source <name>                  default "pa"; recorded on the direction
--external-id <id>               the PA's run id; idempotency key per (source, external-id):
                                 a resubmit returns the existing job, does not create a second
```
Creates an OPERATOR-sourced (pre-approved) direction so auto_pm_sync triages it on the next tick.
Success: `{"job_id": "<app>:<direction_id>", "app": "...", "direction_id": "...",
"direction_path": "...", "pipeline": "...", "delivery": "<effective>",
"delivery_requested": "<or null>", "created": true|false}`

### `factory job status <job_id> --json`
```
{"job_id", "app", "title", "source", "external_id",
 "state": "queued|triaging|in_progress|blocked|needs_human|done|failed|cancelled",
 "terminal": bool, "pipeline", "delivery",
 "stories": [{"id", "state", "pr_url", "pr_state": "open|merged|closed|null", "branch"}],
 "pr_urls": [...], "merged": bool, "cost_usd": number, "updated_at": ISO-8601 UTC,
 "why": "<one line: why blocked / what is happening, or null>"}
```
`done` = every story reached its delivery level's end (merged for auto_merge/push_to_main,
PR open for pr/draft_pr, branch pushed for branch, committed for none). Truth comes from
GitHub where it can (merge reality), per the factory's own guardrail.

### `factory job list --json [--source pa] [--active]`
`{"jobs": [<status object>, ...]}`

### `factory job follow <job_id>`
Human-readable, NOT JSON. Streams the job's events (story transitions, handler runs, gate
results, PR links, cost) as they happen, and exits 0 when the job is terminal. This is what a
termhub session runs so the user can "walk into" a factory job.

### `factory job cancel <job_id> --json`
Stops further dispatch for the job's stories (park/close), never deletes evidence.
`{"job_id", "state": "cancelled"}`

### `factory app add --json`
```
--repo <owner/name>          required
--path <local clone>         optional; clones to ../<name> (sibling of the factory) if absent
--name <app>                 optional; default = the repo name, slugged
--delivery-default <level>   default draft_pr for newly added repos (any level allowed)
--pipeline-default chain|solo|auto   default chain
--enable-tick / --force      optional
```
Registers any repo as a factory app: writes `apps/<app>/config.yaml` with detected gate commands
(deterministic toolchain detection: Makefile, Python, Node/TS, Go, Rust, .NET, JVM, Ruby, PHP;
an unrecognised repo still registers, with empty gates listed in `missing_gates`), creates
`directions/`.
`{"app", "repo", "path", "config_path", "gates": {...}, "delivery": {"default"},
"pipeline_default", "missing_gates": [...], "toolchains": [...], "notes": [...], "cloned", "tick"}`
Errors: `invalid_repo`, `invalid_name`, `invalid_delivery`, `invalid_pipeline`, `app_exists`,
`repo_already_registered`, `not_a_git_repo`, `repo_mismatch`, `clone_failed`, `enable_tick_failed`.

### `factory app set <app> --json`
```
--delivery-default <level>           optional
--pipeline-default chain|solo|auto   optional (at least one of the two)
```
Changes a registered app's defaults in place (only those lines of `config.yaml`; comments kept).
`{"app", "config_path", "delivery": {"default"}, "pipeline_default", "changed": [...],
"comments_preserved": bool}`
Errors: `unknown_app`, `invalid_name`, `nothing_to_set`, `invalid_delivery`, `invalid_pipeline`,
`invalid_config` (the result would not load, e.g. a leftover `delivery.max`).

### `factory app list --json`
`{"apps": [{"app", "repo", "path", "delivery": {"default"}, "pipeline_default"}]}`
