# Jobs — `factory job …`, the interface a personal assistant drives

## Overview

`factory job submit | status | list | follow | cancel` is how an outside
caller (the personal assistant, "PA") hands the factory work and tracks it.
The contract is `docs/JOBS-API.md`; the code is `factory/jobs/` plus the
Typer sub-app `factory/cli_jobs.py` (registered in `factory/cli.py` as
`job`).

**A job is a direction.** `submit` writes an ordinary
`apps/<app>/directions/<id>-<slug>/` directory. Everything downstream —
pm-sync, the backpressure gate, the chain, the merge gates — sees a normal
direction. The job id is `<app>:<direction_id>` (e.g. `sacrifice:021`).

## Modules

| Module | Role |
|---|---|
| `factory/jobs/common.py` | `JobError(code, message)`, job-id parse/format, discovery (`iter_jobs`, `find_job`). |
| `factory/jobs/submit.py` | validation, `--repo` → app, idempotency, atomic write, approval record, `directions` row. |
| `factory/jobs/github.py` | cached, fail-soft `gh` reads (one `gh pr list` per repo per call). |
| `factory/jobs/status.py` | state mapping, `list`, `cancel`. Read-only DB access (`mode=ro`). |
| `factory/jobs/follow.py` | plain-line live stream for a TermHub terminal. |
| `factory/cli_jobs.py` | the CLI; one JSON object on stdout with `--json`; everything else goes to stderr. |

## What a submit writes

- `direction.md` — built by `creator._build_direction_md`. The frontmatter also
  carries `source`, `external_id`, `pipeline` (as requested: `chain|solo|auto`),
  `delivery` (as requested, or null) and `models` (persona → model id).
  **The frontmatter `source` key is what marks a direction as a job.** The
  classic creators record `source` only in `state.yaml`.
- The ask goes under `## Why` with markdown headings demoted to bold lines, so
  they cannot end the section early or open a fake `## Acceptance Criteria`.
  The verbatim ask is kept in `artifacts/ask.md`.
- `--done` → `## Acceptance Criteria` bullets.
- Optional `flow.md` / `api_spec.md` from `--flow-file` / `--api-spec-file`.
- `state.yaml` — `status: created`, `source`, and a signed `operator_approval`
  record (`approved_by: "factory job submit:<source>"`).
- A `directions` row with `status=created` and `source`. This row is the
  approval gate's first source of truth. Writing it is best-effort, because
  `state.yaml` carries the same facts.

The directory is staged under `.job-staging-<hex>` and `rename`d into place.
A concurrent tick's pm-sync only lists `NNN-…` directories, so it can never
triage a half-written job. Submits are serialised by an `fcntl` lock on
`state/jobs-submit.lock`, so the id allocation, the idempotency scan and the
write happen as one step.

## Approval: why a job auto-builds

`factory.directions.approval` parks machine-filed directions until an
operator approves them. That gate exists to stop the factory filing work for
itself. A job is different: a human files it through an operator CLI, or the
PA files it after its human approved that exact plan. So:

- `pa` is in `approval._DELEGATED_HUMAN_SOURCES` (exact match). The PA's filing
  is operator intent, relayed. This keeps a PA job buildable even if
  `state.yaml` is lost (it is gitignored, D018) and only the row's `source`
  survives.
- Every job, whatever its `--source`, also gets the signed `operator_approval`
  record in `state.yaml`.

## Validation

- `--delivery` goes through `factory.delivery.parse_level`. Garbage is an
  `invalid_delivery` error. The reported `delivery` is
  `effective_level(app.delivery, requested)`, the request clamped to the
  app's ceiling.
- `--pipeline auto` resolves to the app's `pipeline_default` (raw config key,
  or `pipeline: {default: …}`), else `chain`. The frontmatter keeps the
  request; the JSON reports the resolved value.
- `--model persona=model`: the persona must be known to `routes.yaml`
  (`dev.standard` / `dev.hard` allowed). Overrides that make the reviewer
  share a model with any dev tier are refused (`invalid_model`). Reviewer
  independence is a hard guardrail, and a per-job override must not bypass it.
- Backpressure is checked at submit time (`validate_direction`). A job with no
  flow, no api spec and no explore tag deterministically lands in
  `needs-direction` at pm-sync. Submit still creates the job, but returns a
  `warnings` entry saying so.

Other modules decide how to honour `pipeline` / `delivery` / `models`. This
module only records, validates and reports them.

## Status mapping

First match wins (`status.py` docstring):

1. `cancelled`: a `job_cancelled` marker is present AND no story is live.
2. No stories: the direction status decides. `created` → `queued` (or
   `needs_human` if the approval gate parks it); `pm-validated` → `triaging`;
   `needs-direction` → `needs_human` (the `why` lists what is missing);
   `closed` → `failed`.
3. Every counted story is delivered at the effective level → `done`. This
   holds only when GitHub CONFIRMED each delivery (PR merged, PR open, or
   branch exists). A delivery that only the local view claims stays
   `in_progress`, with a `why` saying GitHub could not confirm it.
4. Any story is in a pending-human sink (mirrors
   `orchestrator._PENDING_HUMAN_STATES`, kept in sync by a test) or is
   dependency-cap parked → `needs_human`.
5. Any story is live → `in_progress`. It is `blocked` instead when the factory
   is halted or in `paused` mode, or when every live story is
   still in `story_created` with a dependency deferral recorded.
6. Otherwise → `failed`.

`superseded_by_sibling` (the dual-draft loser) is ignored.

"Delivered" per level:

- `auto_merge`: GitHub says the PR is merged.
- `push_to_main`: merged, or locally deployed.
- `pr` / `draft_pr`: GitHub says the PR is open or merged.
- `branch`: the story settled successfully and the branch exists on GitHub.
- `none`: the story settled successfully.

**Merge reality comes from GitHub, never a local flag.** If `gh` fails, the
status uses the local view (`deploy_pending`/`deployed` = merged) for
everything except a terminal `done`, reports `pr_state: null`, and appends `GitHub unavailable, local view: …` to `why`.
`cost_usd` is the sum of `runs.cost_usd` where
`(app, direction_id)` matches or `story_id` is one of the job's stories.

## Cancel

Sets `state.yaml: job_cancelled`, moves every LIVE story to
`closed_by_operator`, and closes the direction (`mark_direction_status`).
`closed_by_operator` is terminal, not mergeable and not auto-recoverable.
Nothing is deleted: worktrees, branches, PRs, logs and spend all stay. Cancel
does not close PRs or issues; `factory reconcile-issues` closes the issues of
a closed direction.

There is no tick lock. An in-flight handler can write a parked story back to
a live state. When that happens, status does NOT report `cancelled`, and its
`why` says to re-run cancel. Cancel is idempotent.

## Follow

`follow` polls `job_status` every `--interval` seconds (GitHub at most every
15 s) and each story's `state/logs/<id>-<slug>.log` (the `factory trace`
stream). It prints one plain line per new event, story transition, PR link,
cost change or job-state change. It exits 0 when the job is terminal. A
terminal verdict is always re-confirmed with GitHub before it exits.

## Tests

`tests/test_jobs_cli.py`: everything runs against a `tmp_path` factory root
(`cli_jobs._FACTORY_ROOT` is patched), with `gh` mocked at
`factory.jobs.github._run_gh`.
