# Story

## Title
Accurate, complete, auditable per-unit cost/token/time accounting — narrow read

## Slug
accurate-complete-auditable-per-unit-cost-token-time-account

## Scope
backend

## Acceptance Criteria
- [ ] Every chain-persona run (sm/dev/reviewer/tech_writer/onboarder/test_implementer/docs_enforcer) records story_id, direction_id, and app; a completeness metric shows ~0 unattributed chain runs.
- [ ] No chain run has NULL/zero cost unless explicitly flagged as cache-only/failed-pre-model, with a reason.
- [ ] Cache-aware cost math is verified per model/provider with unit tests pinning the price (cached input at the discounted read rate).
- [ ] An operator command rolls up tokens_in, tokens_out, cost_usd, and wall-time per story / per direction / per app, and flags any unattributed spend.
- [ ] A reconciliation check compares summed cost_usd against the real provider bill for a window and documents the variance.

### Testable Claims (EARS)
AC1.1: WHEN a chain-persona run is recorded for sm, THE runs recording path SHALL record story_id
AC1.2: WHEN a chain-persona run is recorded for sm, THE runs recording path SHALL record direction_id
AC1.3: WHEN a chain-persona run is recorded for sm, THE runs recording path SHALL record app
AC1.4: WHEN a chain-persona run is recorded for dev, THE runs recording path SHALL record story_id
AC1.5: WHEN a chain-persona run is recorded for dev, THE runs recording path SHALL record direction_id
AC1.6: WHEN a chain-persona run is recorded for dev, THE runs recording path SHALL record app
AC1.7: WHEN a chain-persona run is recorded for reviewer, THE runs recording path SHALL record story_id
AC1.8: WHEN a chain-persona run is recorded for reviewer, THE runs recording path SHALL record direction_id
AC1.9: WHEN a chain-persona run is recorded for reviewer, THE runs recording path SHALL record app
AC1.10: WHEN a chain-persona run is recorded for tech_writer, THE runs recording path SHALL record story_id
AC1.11: WHEN a chain-persona run is recorded for tech_writer, THE runs recording path SHALL record direction_id
AC1.12: WHEN a chain-persona run is recorded for tech_writer, THE runs recording path SHALL record app
AC1.13: WHEN a chain-persona run is recorded for onboarder, THE runs recording path SHALL record story_id
AC1.14: WHEN a chain-persona run is recorded for onboarder, THE runs recording path SHALL record direction_id
AC1.15: WHEN a chain-persona run is recorded for onboarder, THE runs recording path SHALL record app
AC1.16: WHEN a chain-persona run is recorded for test_implementer, THE runs recording path SHALL record story_id
AC1.17: WHEN a chain-persona run is recorded for test_implementer, THE runs recording path SHALL record direction_id
AC1.18: WHEN a chain-persona run is recorded for test_implementer, THE runs recording path SHALL record app
AC1.19: WHEN a chain-persona run is recorded for docs_enforcer, THE runs recording path SHALL record story_id
AC1.20: WHEN a chain-persona run is recorded for docs_enforcer, THE runs recording path SHALL record direction_id
AC1.21: WHEN a chain-persona run is recorded for docs_enforcer, THE runs recording path SHALL record app
AC1.22: WHEN completeness is reported for chain runs, THE system SHALL show a metric for unattributed chain runs
AC1.23: UNTESTABLE-AS-WRITTEN — the threshold for "~0 unattributed chain runs" is not numerically defined
AC2.1: WHEN a chain run is recorded, GIVEN the run is not explicitly flagged as cache-only or failed-pre-model, THE runs recording path SHALL NOT store NULL cost
AC2.2: WHEN a chain run is recorded, GIVEN the run is not explicitly flagged as cache-only or failed-pre-model, THE runs recording path SHALL NOT store zero cost
AC2.3: WHEN a chain run is recorded with NULL cost, THE runs recording path SHALL explicitly flag the run as cache-only or failed-pre-model
AC2.4: WHEN a chain run is recorded with zero cost, THE runs recording path SHALL explicitly flag the run as cache-only or failed-pre-model
AC2.5: WHEN a chain run is explicitly flagged as cache-only or failed-pre-model, THE runs recording path SHALL record a reason
AC3.1: WHEN cache-aware cost math is computed for a model/provider in model_router, THE system SHALL price cached input at the discounted read rate
AC3.2: WHEN unit tests run for cost math, THE test suite SHALL verify cache-aware cost math per model/provider
AC3.3: WHEN unit tests run for cost math, THE test suite SHALL pin the price for each model/provider case covered by model_router
AC4.1: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_in per story
AC4.2: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_out per story
AC4.3: WHEN an operator invokes the audit command, THE command SHALL roll up cost_usd per story
AC4.4: WHEN an operator invokes the audit command, THE command SHALL roll up wall-time per story
AC4.5: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_in per direction
AC4.6: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_out per direction
AC4.7: WHEN an operator invokes the audit command, THE command SHALL roll up cost_usd per direction
AC4.8: WHEN an operator invokes the audit command, THE command SHALL roll up wall-time per direction
AC4.9: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_in per app
AC4.10: WHEN an operator invokes the audit command, THE command SHALL roll up tokens_out per app
AC4.11: WHEN an operator invokes the audit command, THE command SHALL roll up cost_usd per app
AC4.12: WHEN an operator invokes the audit command, THE command SHALL roll up wall-time per app
AC4.13: WHEN an operator invokes the audit command, THE command SHALL flag unattributed spend
AC5.1: WHEN a reconciliation check is run for a window, THE system SHALL compare summed cost_usd against the real provider bill for that window
AC5.2: WHEN a reconciliation check is run for a window, THE system SHALL document the variance

## Tasks / Subtasks
- [ ] Identify run-record creation path(s) for all chain personas listed in AC1.
- [ ] Thread story_id through chain dispatch to run persistence.
- [ ] Thread direction_id through chain dispatch to run persistence.
- [ ] Thread app through chain dispatch to run persistence.
- [ ] Enforce attribution population for chain-persona runs before/at persistence.
- [ ] Add completeness metric/report for unattributed chain runs.
- [ ] Identify all branches that currently write NULL/zero cost.
- [ ] Add explicit zero-cost reason handling for cache-only cases.
- [ ] Add explicit zero-cost reason handling for failed-pre-model cases.
- [ ] Prevent unflagged NULL cost on chain runs.
- [ ] Prevent unflagged zero cost on chain runs.
- [ ] Review model_router pricing inputs for each model/provider.
- [ ] Verify cached-input pricing uses discounted cache-read rate.
- [ ] Fix pricing math where cached-input handling is wrong.
- [ ] Add unit tests pinning per-model/provider cost math.
- [ ] Implement operator audit command or extend existing spend command.
- [ ] Support rollups by story.
- [ ] Support rollups by direction.
- [ ] Support rollups by app.
- [ ] Include tokens_in/tokens_out/cost_usd/wall-time in output.
- [ ] Flag unattributed spend in audit output.
- [ ] Implement reconciliation check for a time window.
- [ ] Compare summed cost_usd to provider bill for the same window.
- [ ] Document reconciliation variance in operator-facing output or note.
- [ ] Add/update tests covering attribution completeness, zero-cost reasons, audit rollups, and reconciliation behavior.

## Dev Notes
[flow.md]
(none)

[api_spec.md]
(none)

### Context pointers
No canonical context files were provided in this invocation. Derive implementation pointers from repository code paths actually present at execution time.

### Direction acceptance criteria (verbatim)
- [ ] Every chain-persona run (sm/dev/reviewer/tech_writer/onboarder/test_implementer/docs_enforcer) records story_id, direction_id, and app; a completeness metric shows ~0 unattributed chain runs.
- [ ] No chain run has NULL/zero cost unless explicitly flagged as cache-only/failed-pre-model, with a reason.
- [ ] Cache-aware cost math is verified per model/provider with unit tests pinning the price (cached input at the discounted read rate).
- [ ] An operator command rolls up tokens_in, tokens_out, cost_usd, and wall-time per story / per direction / per app, and flags any unattributed spend.
- [ ] A reconciliation check compares summed cost_usd against the real provider bill for a window and documents the variance.

### Implementation boundaries
- Narrow-read scope: backend-only accounting pipeline, pricing math, persistence, reporting command, and reconciliation support.
- No UI/UX work.
- No doc rewrites outside this story file.
- Preserve PM-declared single-story backend scope.

### Ambiguities to surface during implementation/review
- "~0 unattributed chain runs" lacks a strict numeric threshold.
- "real provider bill" source and ingestion path are unspecified.
- Reconciliation note destination is unspecified; implementation must use an existing operator-facing surface or clearly scoped output.
- "cache-only" and "failed-pre-model" need concrete storage shape if none exists yet.

## References
- Direction: Accurate, complete, auditable per-unit cost/token/time accounting
- PM tracker: [DIRECTION] Accurate, complete, auditable per-unit cost/token/time...
- Story slug: `accurate-complete-auditable-per-unit-cost-token-time-account`
- Target path: `stories/0-accurate-complete-auditable-per-unit-cost-token-time-account.md`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes: TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Notes: TBD

## Review Follow-ups
- None yet
