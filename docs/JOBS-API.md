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
