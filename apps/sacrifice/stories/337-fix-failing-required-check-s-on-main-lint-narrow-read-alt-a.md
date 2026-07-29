# Story

## Title
Fix failing required check(s) on main: lint — narrow read

## Slug
`fix-failing-required-check-s-on-main-lint-narrow-read-alt-a`

## Scope
`backend`

## Acceptance Criteria
- [x] lint passes on sacrifice's main branch

### Testable Claims (EARS)
AC1.1: WHEN the lint required check runs against the relevant changed Python files on sacrifice's main branch, THE lint job SHALL pass

## Tasks / Subtasks
- [x] Inspect `backend/app/routes/auth.py` import list at the reported Ruff failure line
- [x] Remove or otherwise resolve the unused `decode_access_token` import without changing unrelated auth behavior
- [x] Confirm `backend/app/routes/auth.py` remains Ruff-clean for `F401`
- [x] Run the repo's targeted changed-file lint command or equivalent Ruff check for the affected Python files
- [x] Run `uvx ruff format --check` for the affected Python files
- [x] Record exact verification commands and results in Dev Agent Record

## Dev Notes
### Scope constraints
- Narrow-read corrective slice only
- Fix the explicit Ruff `F401` failure in `backend/app/routes/auth.py`
- Do not bundle broader auth hardening, refactors, or unrelated lint cleanup
- Direction provides no `flow.md`
- Direction provides no `api_spec.md`

### flow.md
(none)

### api_spec.md
(none)

### Direction acceptance criteria (verbatim)
- [ ] lint passes on sacrifice's main branch

### Direction evidence / failure signature
```text
=== lint ===
.3156953Z [36;1m  echo "No changed Python files — skipping ruff."[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3157293Z [36;1m  exit 0[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3157513Z [36;1mfi[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3157842Z [36;1m# GUARD: only ever call ruff with an explicit, non-empty file list.[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3158560Z [36;1m# Bare `ruff check` would lint the whole legacy tree and false-red.[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3158951Z [36;1mmapfile -t FILES < changed_py.txt[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3159298Z [36;1mecho "Linting ${#FILES[@]} changed Python file(s):"[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3159641Z [36;1mprintf '  %s\n' "${FILES[@]}"[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3159933Z [36;1muvx ruff check "${FILES[@]}"[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3160223Z [36;1muvx ruff format --check "${FILES[@]}"[0m
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3207936Z shell: /usr/bin/bash -e {0}
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3208259Z env:
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3208462Z   UV_PYTHON: 3.12
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3208758Z   VIRTUAL_ENV: /home/runner/work/sacrifice/sacrifice/.venv
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3209151Z   UV_CACHE_DIR: /home/runner/work/_temp/setup-uv-cache
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3209468Z ##[endgroup]
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3296280Z Linting 2 changed Python file(s):
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3296903Z   backend/app/routes/auth.py
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.3297335Z   backend/tests/test_csrf.py
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.6463154Z Downloading ruff (10.9MiB)
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.7625777Z  Downloaded ruff
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.7647460Z Installed 1 package in 1ms
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8151491Z F401 [*] `app.services.auth.decode_access_token` imported but unused
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8152170Z   --> backend/app/routes/auth.py:25:5
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8152592Z    |
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8153187Z 23 |     create_access_token,
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8153602Z 24 |     create_auth_code,
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8154000Z 25 |     decode_access_token,
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8154441Z    |     ^^^^^^^^^^^^^^^^^^^
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8154851Z 26 |     decode_auth_code,
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8155208Z 27 |     exchange_github_code,
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8155602Z    |
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8156069Z help: Remove unused import: `app.services.auth.decode_access_token`
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8156534Z 
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8156672Z Found 1 error.
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8157034Z [*] 1 fixable with the `--fix` option.
lint	Ruff lint + format (changed Python only)	2026-07-23T10:06:40.8191982Z ##[error]Process completed with exit code 1.
```

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/modules/auth.md]
- [Source: context/modules/security.md]
- [Source: context/modules/backend.md]
- [Source: context/current-state.md#auth-and-session-hardening]

### Implementation notes
- Preserve existing auth-route behavior; prefer deleting the unused import if no live usage exists
- Verification should match CI intent: explicit file-targeted Ruff lint and format check on affected Python files
- Avoid invoking bare repo-wide Ruff commands that may lint unrelated legacy files

## References
- `backend/app/routes/auth.py`
- `backend/tests/test_csrf.py`
- `backend/app/services/auth.py`
- `context/project.md`
- `context/navigation.md`
- `context/modules/auth.md`
- `context/modules/security.md`
- `context/modules/backend.md`
- `context/current-state.md`

## Dev Agent Record
### Agent Model Used
- OpenHands (GPT-5 via Codex runtime)

### Debug Log References
- `cd /home/k/sacrifice && uvx ruff check backend/app/routes/auth.py && uvx ruff format --check backend/app/routes/auth.py`
  - Result: `All checks passed!` and `1 file already formatted`
- `cd /home/k/sacrifice && FILES=(backend/app/routes/auth.py); if [ -f backend/tests/test_csrf.py ]; then FILES+=(backend/tests/test_csrf.py); fi; echo "Linting ${#FILES[@]} file(s):"; printf '  %s\n' "${FILES[@]}"; uvx ruff check "${FILES[@]}"; uvx ruff format --check "${FILES[@]}"`
  - Result: `Linting 1 file(s): backend/app/routes/auth.py`, `All checks passed!`, `1 file already formatted`

### Completion Notes
- Removed the unused `decode_access_token` import from `backend/app/routes/auth.py` to resolve Ruff `F401` at the reported import block.
- Preserved auth-route behavior; no runtime logic changes were introduced beyond import cleanup and formatter-only line wrapping.
- Verified changed-file Ruff lint and Ruff format checks pass for the affected file in this checkout.
- `backend/tests/test_csrf.py` was not present in this local checkout, so the changed-file verification command was run with an existence guard and linted the available affected file list.

### File List
- `backend/app/routes/auth.py`
- `stories/337-fix-failing-required-check-s-on-main-lint-narrow-read-alt-a.md`

## Senior Developer Review
- TBD

## Review Follow-ups
- TBD
