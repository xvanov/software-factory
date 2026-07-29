---
title: 'Fix failing required check(s) on main: lint'
type: bug
priority: p2
explore: true
created_at: '2026-07-23T10:41:47.690370+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Fix failing required check(s) on main: lint

## Why

Post-merge CI-health monitor: the required check(s) lint are failing on sacrifice's main branch AFTER merge (the pre-merge required-check gate is unchanged and remains the primary defense; this is the post-merge safety net). Fix the exact failure below so main goes green again.

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

<!-- ci-health-signature: 8906d968dfe6faf09a5b279c173ff4d8020ff1ef271f6a62df73721ae35d1398 -->

## Acceptance Criteria

- [ ] lint passes on sacrifice's main branch
