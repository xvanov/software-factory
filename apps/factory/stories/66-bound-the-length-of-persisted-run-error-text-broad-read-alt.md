# Story

## Title
Bound the length of persisted run error text — broad read

## Slug
`bound-the-length-of-persisted-run-error-text-broad-read-alt`

## Scope
`infra`

## Summary
Bound persisted run error text in `factory.runner._record_run` via a pure truncation helper so oversized already-redacted errors do not bloat persisted run rows, while preserving unchanged storage for in-bound text and proving both paths with unit coverage.

# Acceptance Criteria

- [ ] A pure helper truncates a string to a bounded max length (default 4000 chars), appending a clear marker like '...[truncated N chars]' when it cuts.
- [ ] `_record_run` applies the bound to the (already-redacted) error before persisting, so no runs row stores an error longer than the bound.
- [ ] Text at or under the bound is returned unchanged; the helper is idempotent.
- [ ] A unit test covers: an over-long error is truncated with the marker on the persistence path, and a short error is stored verbatim.

### Testable Claims (EARS)
AC1.1: WHEN the truncation helper receives a string longer than its bounded max length, THE helper SHALL return a truncated string with a clear truncation marker indicating truncated character count.
AC1.2: WHEN the truncation helper is called without an explicit max length, THE helper SHALL use a default bound of 4000 characters.
AC1.3: WHEN the truncation helper receives a string at or under its bounded max length, THE helper SHALL return the original string unchanged.
AC2.1: WHEN `_record_run` persists an error value, GIVEN the error has already been redacted, THE function SHALL apply the bound before persistence.
AC2.2: WHEN `_record_run` persists an over-long already-redacted error, THE persisted runs row SHALL not store an error longer than the bound.
AC3.1: WHEN the truncation helper receives text at the bound, THE helper SHALL return the text unchanged.
AC3.2: WHEN the truncation helper receives text under the bound, THE helper SHALL return the text unchanged.
AC3.3: WHEN the truncation helper is applied to text that is already the helper's bounded output, THE helper SHALL return the same text unchanged.
AC4.1: WHEN unit tests exercise the persistence path with an over-long error, THE tests SHALL verify the stored error is truncated and includes the truncation marker.
AC4.2: WHEN unit tests exercise the persistence path with a short error, THE tests SHALL verify the stored error is persisted verbatim.

# Tasks / Subtasks

- [ ] Identify the single persistence path in `factory.runner._record_run`
- [ ] Add pure truncation helper with default max length 4000
- [ ] Preserve unchanged return for text at or under the bound
- [ ] Make helper idempotent for already-truncated helper output
- [ ] Apply helper after existing redaction and before DB persistence
- [ ] Keep change scoped to persisted error handling only
- [ ] Add unit test for over-long persistence-path error
- [ ] Assert truncation marker present in persisted over-long error
- [ ] Assert persisted over-long error does not exceed bound
- [ ] Add unit test for short persistence-path error
- [ ] Assert short persisted error matches input verbatim
- [ ] Run targeted test suite covering helper and `_record_run`

# Dev Notes

[flow.md: none]

[api_spec.md: none]

Context status: canonical context files were not provided in this invocation. Dev/Test-Designer must derive implementation pointers from repository code for this run.

Direction acceptance criteria (verbatim):
- [ ] A pure helper truncates a string to a bounded max length (default 4000 chars), appending a clear marker like '...[truncated N chars]' when it cuts.
- [ ] `_record_run` applies the bound to the (already-redacted) error before persisting, so no runs row stores an error longer than the bound.
- [ ] Text at or under the bound is returned unchanged; the helper is idempotent.
- [ ] A unit test covers: an over-long error is truncated with the marker on the persistence path, and a short error is stored verbatim.

Implementation constraints:
- Scope is one vertical infra slice only
- Primary change site is `factory.runner._record_run`
- Helper must be pure and directly unit-testable
- Apply bound after redaction, not before
- Do not broaden into schema, migration, or unrelated persistence changes
- Do not change caller-visible behavior beyond bounding persisted error text

Expected file touch pattern from PM context:
- ~0 new files
- ~2 modified files

# References

- Direction: `direction.md`
- PM tracker: `D007 bound persisted run error text length`
- Target story path: `stories/0-bound-the-length-of-persisted-run-error-text-broad-read-alt.md`

# Dev Agent Record

## Status
Not started

## Agent Notes
- Pending implementation
- Record actual files changed
- Record exact tests added/updated

# Senior Developer Review

## Review Status
Pending

## Review Checklist
- [ ] Helper is pure
- [ ] Default bound is 4000 chars
- [ ] Marker communicates truncation count
- [ ] Helper leaves in-bound text unchanged
- [ ] Helper is idempotent
- [ ] `_record_run` applies helper after redaction
- [ ] Persisted error never exceeds bound
- [ ] Unit tests prove long and short persistence paths
- [ ] No unrelated refactor introduced

# Review Follow-ups

- None yet
