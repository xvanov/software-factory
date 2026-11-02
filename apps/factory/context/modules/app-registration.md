# App registration — `factory app add` / `factory app list`

## Overview

Registers any GitHub repo as a factory app: writes `apps/<app>/config.yaml`,
creates `apps/<app>/directions/`, and (optionally) enables the tick timer.
The contract the personal assistant builds against is `docs/JOBS-API.md`.

| File | Role |
|------|------|
| `factory/app_detect.py` | Pure, read-only toolchain detection → proposed gate commands |
| `factory/cli_apps.py` | `add_app()` / `list_registered_apps()` + the `factory app` Typer sub-app |
| `factory/cli.py` | Registration line only (`app.add_typer(apps_app, name="app")`) |
| `tests/test_cli_app_add.py` | Fixture repos per toolchain, refusal paths, JSON shapes |

Detection is deterministic. It makes no model calls. The `onboarder` persona
is not used: it writes `context/` docs, not gate commands.

## `app add` flow

1. Validate `--repo owner/name`, the app name (default: repo name, slugged),
   and the delivery flags (`DeliveryConfig`; default ceiling
   `NEW_APP_DEFAULT = draft_pr`).
2. Refuse, writing nothing, when:
   - `apps/<app>/config.yaml` exists (`app_exists`), unless `--force`.
   - another app already registers the same repo (`repo_already_registered`),
     unless `--force`.
   - the local path exists but is not a git checkout (`not_a_git_repo`).
   - the checkout's `origin` is not that repo (`repo_mismatch`), unless `--force`.
3. Clone when the path is absent (`gh repo clone`, else `git clone https://…`).
   Default path: `<factory root>/../<app>`, the `load_app_config` convention.
4. Detect gates, render a commented YAML, validate it through `AppConfig`, and
   write it. `app_repo_path` is `../<dir>` for a sibling, absolute otherwise.
5. Create `apps/<app>/directions/` and `<repo>/context/` (empty; the context
   loader reads `<repo>/context/`).
6. `--enable-tick` runs `systemctl --user enable --now factory-tick@<app>.timer`
   (the installed template units). Failure here is `enable_tick_failed`, and the
   config is already written.

`--json` prints one object. Success:
`{app, repo, path, config_path, gates, delivery, missing_gates, toolchains,
smoke_command, notes, cloned, tick}`. Failure, exit 1:
`{"error": "<code>", "message": "..."}`.

## Detection rules

Per gate, first hit wins:

1. **Makefile targets**: `lint`; `format-check`/`fmt-check`/…;
   `typecheck`/`type-check`/`types`/`mypy`; `test`/`tests`.
2. **Toolchains at the root and one directory down.** Per gate and per family
   (python, node, go, rust, .net), the shallowest provider wins. Different
   families are joined with `&&`, so all must pass. Example (sacrifice's
   shape): `ruff check . && (cd frontend && npm run lint)`.
3. `scripts/ensure-deps.sh` present → every gate gets that prefix
   (template-derived repos; see `apps/template-probe/config.yaml`).

| Toolchain | Signal | Gates |
|-----------|--------|-------|
| Python | `pyproject.toml` / `setup.py` / `requirements*.txt`; `uv.lock`→`uv run [--extra dev]`, `poetry.lock`→`poetry run`, else `python -m` | ruff (or flake8/black), mypy (or pyright), pytest |
| Python (ruff only) | root `ruff.toml` without a manifest | `ruff check .`, `ruff format --check .` |
| Node/TS | `package.json`; PM from `packageManager`, then lockfile | scripts `lint`, `format:check`…, `typecheck`…, `test` (npm's placeholder test ignored); fallbacks `tsc --noEmit`, `prettier --check .` |
| Go | `go.mod` | `golangci-lint run` (if configured) or `go vet ./...`, gofmt, `go build ./...`, `go test ./...` |
| Rust | `Cargo.toml` | clippy `-D warnings`, `cargo fmt --check`, `cargo check`, `cargo test` |
| .NET | `*.sln`/`*.slnx`/`*.csproj`/`*.fsproj` at the root | `dotnet format analyzers/whitespace --verify-no-changes` (csharpier if in `dotnet-tools.json`), `dotnet build`, `dotnet test`; the target is named when unambiguous |

Smoke: `make smoke` or `scripts/smoke.sh` fills `smoke_command`, but
`smoke_harness_ready` stays `false`. Flipping it makes `smoke-green` a
required gate.

## Empty gates — what they mean to the chain

An undetected gate is written as `""` with a `NOT DETECTED` comment. It is
listed in `missing_gates`.

- **`test_command`** is the only gate command the chain runs. If it is empty:
  - The dev sandbox's `_run_pytest` falls back to `python -m pytest` when a
    `tests/` dir exists. Otherwise it returns failed (`no tests directory`).
  - The `tests-green` merge gate falls back to the live CI state. With no CI
    state, it fails.

  Either way the story blocks. It never passes on an empty command. This is
  fail-safe, but a repo with no detectable test runner cannot converge until
  someone fills in the gate.
- **`lint_command` / `format_check_command` / `type_check_command`** are never
  executed by the chain. The pre-PR ruff check only reads them to decide
  whether ruff applies. Empty or filled, they block nothing. These checks are
  enforced only by the repo's own required CI checks.

## Known gaps

- The detector only looks at the root and one directory down. Deeper
  workspaces (`packages/*/…`) are covered only through a root script.
- Makefile targets are used verbatim. A target that assumes a pre-built
  `.venv` or `node_modules` fails in the chain's fresh worktree. The command
  prints a note when it uses one.
- Once an app has a `config.yaml`, `factory on` enables its tick timer.
  `power.discover_units` derives units from `apps/*/config.yaml`, so
  registering an app opts it into the next `factory on`.
