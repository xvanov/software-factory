# Story

## Title
Bound the length of persisted run error text — narrow read

## Slug
`bound-the-length-of-persisted-run-error-text-narrow-read-alt`

## Scope
`infra`

## Summary
Bound persisted run error text in `factory.runner._record_run` with a pure truncation helper and focused unit coverage for long vs short persistence behavior.

# Acceptance Criteria

- [ ] A pure helper truncates a string to a bounded max length (default 4000 chars), appending a clear marker like '...[truncated N chars]' when it cuts.
- [ ] `_record_run` applies the bound to the (already-redacted) error before persisting, so no runs row stores an error longer than the bound.
- [ ] Text at or under the bound is returned unchanged; the helper is idempotent.
- [ ] A unit test covers: an over-long error is truncated with the marker on the persistence path, and a short error is stored verbatim.

### Testable Claims (EARS)

AC1.1: WHEN the helper receives text longer than its configured maximum length, THE helper SHALL return truncated text with a clear truncation marker indicating characters were removed.
AC1.2: WHEN the helper is called without an explicit maximum length, THE helper SHALL use a default maximum length of 4000 characters.
AC2.1: WHEN `_record_run` persists an error, GIVEN the error has already been redacted, THE `_record_run` persistence path SHALL apply the length bound before writing the error to storage.
AC2.2: WHEN `_record_run` persists an error, THE persisted runs row SHALL not store an error longer than the bound.
AC3.1: WHEN the helper receives text whose length is at or under the bound, THE helper SHALL return the text unchanged.
AC3.2: WHEN the helper is applied to text that is already within the bound, THE helper SHALL return the same text on repeated application.
AC3.3: WHEN the helper is applied repeatedly to previously truncated output, THE helper SHALL return the same output unchanged.
AC4.1: WHEN unit tests exercise the persistence path with an over-long error, THE tests SHALL verify that the stored value is truncated and includes the truncation marker.
AC4.2: WHEN unit tests exercise the persistence path with a short error, THE tests SHALL verify that the stored value matches the original text verbatim.

# Tasks / Subtasks

- [ ] Identify existing helper/module location appropriate for pure string truncation logic near `factory.runner` persistence utilities.
- [ ] Add pure helper with default max length `4000`.
- [ ] Preserve unchanged return for input at or under bound.
- [ ] Append truncation marker only when truncation occurs.
- [ ] Ensure helper behavior is idempotent.
- [ ] Update `factory.runner._record_run` to apply helper after redaction and before DB persistence.
- [ ] Keep change scoped to persisted run error handling only.
- [ ] Add unit coverage for over-long error on persistence path.
- [ ] Add unit coverage for short error on persistence path.
- [ ] Assert persisted long error includes truncation marker.
- [ ] Assert persisted short error remains verbatim.

# Dev Notes

- [flow.md: none]
- [api_spec.md: none]
- No canonical context files were provided in this invocation (`context/project.md`, `context/navigation.md`, module files unavailable). Dev/Test-Designer must derive exact file targets and current behavior from repository code.
- Inspect implementation and tests around `factory.runner._record_run` and runs-table persistence path.
- Keep this story to the narrow read: one pure helper, one `_record_run` call site, focused unit tests, no broader schema/query/refactor work.

## Direction Acceptance Criteria (verbatim)

- [ ] A pure helper truncates a string to a bounded max length (default 4000 chars), appending a clear marker like '...[truncated N chars]' when it cuts.
- [ ] `_record_run` applies the bound to the (already-redacted) error before persisting, so no runs row stores an error longer than the bound.
- [ ] Text at or under the bound is returned unchanged; the helper is idempotent.
- [ ] A unit test covers: an over-long error is truncated with the marker on the persistence path, and a short error is stored verbatim.

# References

- Direction: `direction.md`
- PM tracker title: `D007 bound persisted run error text length`
- Target story path: `stories/0-bound-the-length-of-persisted-run-error-text-narrow-read-alt.md`

# Dev Agent Record

- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes: TBD

# Senior Developer Review

- Reviewer: TBD
- Outcome: TBD
- Notes: TBD

# Review Follow-ups

- [ ] TBD
