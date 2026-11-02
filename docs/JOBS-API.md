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
- `push_to_main` — gates pass → fast-forward the default branch directly (no PR). Only valid on
  repos whose config explicitly allows it.

Per-app config (`apps/<app>/config.yaml`) sets `delivery.max` (ceiling) and `delivery.default`.
A job may request a level; the EFFECTIVE level is `min(requested or default, max)`. A job can
only lower autonomy below the app ceiling, never raise it (fail safe). Existing apps with no
`delivery` block behave exactly as today (`auto_merge`).

PA mode → delivery mapping (PA side owns this): plan→(not a factory job), local→none,
branch→branch, mr→draft_pr, full→draft_pr.

## Pipelines

`chain` (PM→SM→dev→reviewer→gates), `solo` (single dev agent + gates, B.1 solo mode), `auto`
(factory decides; v1: = app default, else `chain`).

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
--repo <owner/name>      required
--path <local clone>     optional; clones under the factory's repos root if absent
--delivery-max <level>   default draft_pr for newly added repos (safe default)
--delivery-default <level>
```
Registers any repo as a factory app: writes `apps/<app>/config.yaml` with detected gate commands
(language/toolchain detection; may use the onboarder persona), creates `directions/`.
`{"app", "repo", "path", "config_path", "gates": {...}, "delivery": {"max", "default"}}`

### `factory app list --json`
`{"apps": [{"app", "repo", "path", "delivery": {"max", "default"}, "pipeline_default"}]}`
