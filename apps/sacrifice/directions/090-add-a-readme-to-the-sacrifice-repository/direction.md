---
title: Add a README to the sacrifice repository
type: docs
priority: p2
explore: true
created_at: '2026-07-19T05:14:41.517417+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Add a README to the sacrifice repository

## Why

The sacrifice repo has no README.md — a new contributor or operator has no entry point for what the app is or how to run it. WHAT TO BUILD: a top-level README.md covering: what Sacrifice is (one paragraph — a goal-commitment app: pledge, submit proof, get verified/charged); local dev quickstart using the REAL Makefile targets that actually exist (`make up`/`make down`/`make test`/`make smoke` — verify each exists before documenting it); architecture (FastAPI + Celery + Postgres/Redis backend, Expo/React Native frontend); where deeper docs live (context/); and the relationship to the software-factory (directions/stories live in software-factory/apps/sacrifice/, CI runs via .github/workflows/ci.yml). SCOPE: add README.md only — do not modify code or reformat anything. No invented commands.

## Acceptance Criteria

- [ ] README.md exists at repo root and documents running the app with REAL Makefile targets (no invented commands).
- [ ] Covers what the app is, dev quickstart, architecture, and the factory relationship.
- [ ] Diff is README.md only — no code/reformat changes.
