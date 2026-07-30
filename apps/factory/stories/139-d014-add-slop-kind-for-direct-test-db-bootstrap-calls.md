# Story

## Title
D014 add slop kind for direct test DB bootstrap calls

## Slug
`d014-add-slop-kind-for-direct-test-db-bootstrap-calls`

## Scope
`infra`

## Summary
Add the detector rule that reports a stable new slop `kind` when Python test files directly bootstrap database/schema infrastructure via `SQLModel.metadata.create_all`, `sqlmodel.create_engine`, or `sqlalchemy.create_engine`. Route the finding through the existing `tests-meaningful` path by reusing current finding plumbing and single-test `# noqa: slop` suppression behavior.

## Acceptance Criteria
- The detector reports a finding with a stable new `kind` when a test file calls
  `SQLModel.metadata.create_all` or a `create_engine` variant directly.
- The finding carries a `why_slop` explanation naming the app initializer the
  test should have called, so the message teaches rather than just blocks.
- A test that obtains its database through the application's initializer produces
  NO finding, so the fixed form of the story-148 test passes cleanly.
- The existing `# noqa: slop` escape hatch suppresses the new finding on a single
  test, for the case where exercising the raw engine IS the subject — for example
  a test of `migrate()` itself.
- `factory/observability/schema.py`'s own tests, which legitimately construct
  engines, either pass or carry the escape hatch — the repository's own suite must
  be green with the new pattern enabled.
- The `tests-meaningful` gate blocks a PR whose diff introduces the new finding,
  through the existing path, with no new gate label.
- A regression test asserts the exact story-148 test body is flagged, and that its
  fixed form is not.

### Testable Claims (EARS)
AC1.1: WHEN a Python test file calls `SQLModel.metadata.create_all`, THE detector SHALL report a finding with a stable new `kind`
AC1.2: WHEN a Python test file calls `sqlmodel.create_engine` directly, THE detector SHALL report a finding with a stable new `kind`
AC1.3: WHEN a Python test file calls `sqlalchemy.create_engine` directly, THE detector SHALL report a finding with a stable new `kind`
AC2.1: WHEN the detector reports this new finding, THE finding SHALL carry a `why_slop` explanation naming `factory.observability.schema.migrate`
AC3.1: WHEN a test obtains its database through the application's initializer, THE detector SHALL produce no finding for this rule
AC4.1: WHEN a single test that would otherwise trigger this rule carries `# noqa: slop`, THE detector SHALL suppress the new finding for that test
AC5.1: WHEN the repository's own `factory/observability/schema.py` tests are evaluated with the new pattern enabled, THE suite SHALL either pass cleanly or use the existing `# noqa: slop` escape hatch on legitimate raw-engine tests
AC6.1: WHEN a PR diff introduces the new finding, THE `tests-meaningful` gate SHALL block it through the existing path
AC6.2: WHEN the new finding reaches gate enforcement, THE system SHALL use no new gate label
AC7.1: WHEN regression coverage evaluates the exact story-148 bad test body, THE detector SHALL flag it
AC7.2: WHEN regression coverage evaluates the fixed form of the story-148 test, THE detector SHALL not flag it

## Tasks / Subtasks
- [ ] Identify detector entrypoint and finding model used by existing slop patterns
- [ ] Add one narrow rule for Python test files only
- [ ] Match direct calls to `SQLModel.metadata.create_all`
- [ ] Match direct calls to `sqlmodel.create_engine`
- [ ] Match direct calls to `sqlalchemy.create_engine`
- [ ] Assign a stable new `kind` for this rule
- [ ] Set `why_slop` text that explicitly names `factory.observability.schema.migrate`
- [ ] Reuse existing finding emission path consumed by `tests-meaningful`
- [ ] Reuse existing single-test `# noqa: slop` suppression path
- [ ] Avoid adding any new gate label or special-case route
- [ ] Keep detector scope narrow; no broad “meaningful test” heuristics
- [ ] Leave non-Python test scanners unchanged
- [ ] Add or update unit-level detector coverage for each forbidden call shape
- [ ] Verify no finding for app-initializer-driven setup path
- [ ] Verify no regression to existing slop kinds

## Dev Notes
### flow.md
# Operator flow — catching a test that cannot fail

1. **A story ships a test that bypasses the app.** A dev writes a test that calls
   `SQLModel.metadata.create_all` directly and asserts a table exists.

2. **The gate blocks the PR.** The operator sees `tests-meaningful` red on that
   PR, with a slop finding naming the file, the line, and the offending call —
   not a generic "test quality" complaint.

3. **The message says what to do.** The finding's explanation names the
   application initializer the test should have driven
   (`factory.observability.schema.migrate`), so the fix is obvious without
   reading the detector's source.

4. **The dev fixes it and the gate clears.** The rewritten test drives the app's
   initializer, produces no finding, and the PR goes green — and now genuinely
   fails when production is broken.

5. **A legitimate raw-engine test is not blocked.** The operator marks a test
   whose actual subject IS the engine or `migrate()` itself with `# noqa: slop`,
   and the gate accepts it.

6. **The existing suite stays green.** The operator runs the full suite with the
   new pattern enabled and sees no new failures, so enabling the rule does not
   itself become a migration project.

### api_spec.md
(none)

### Direction Acceptance Criteria (verbatim)
- The detector reports a finding with a stable new `kind` when a test file calls
  `SQLModel.metadata.create_all` or a `create_engine` variant directly.
- The finding carries a `why_slop` explanation naming the app initializer the
  test should have called, so the message teaches rather than just blocks.
- A test that obtains its database through the application's initializer produces
  NO finding, so the fixed form of the story-148 test passes cleanly.
- The existing `# noqa: slop` escape hatch suppresses the new finding on a single
  test, for the case where exercising the raw engine IS the subject — for example
  a test of `migrate()` itself.
- `factory/observability/schema.py`'s own tests, which legitimately construct
  engines, either pass or carry the escape hatch — the repository's own suite must
  be green with the new pattern enabled.
- The `tests-meaningful` gate blocks a PR whose diff introduces the new finding,
  through the existing path, with no new gate label.
- A regression test asserts the exact story-148 test body is flagged, and that its
  fixed form is not.

### Context pointers
No canonical context files were provided in this invocation (`context/project.md`, `context/navigation.md`, `context/current-state.md`, `context/modules/*.md` unavailable). Dev must derive implementation targets from the codebase and preserve existing detector/gate conventions already present in-repo.

### Scope notes
- Primary implementation story for the new detector `kind`
- This story owns finding shape, message content, and detector wiring
- Follow-on stories own dedicated proof for suppression, regression fixture body, gate verification, and repo-suite cleanup
- Respect current `tests-meaningful` path; do not create a parallel enforcement path
- Restrict matching to direct bootstrap calls named in direction
- Treat this as setup-bypasses-subject slop, distinct from vacuous-assertion patterns

## References
- Direction: `D014 detect tests that bypass the app entry point`
- Target app initializer named by direction: `factory.observability.schema.migrate`
- Related motivating bug: story-148 / direction 012
- Output story path: `stories/0-d014-add-slop-kind-for-direct-test-db-bootstrap-calls.md`

## Dev Agent Record
- Status: Not started
- Agent Model: _TBD_
- Branch: _TBD_
- PR: _TBD_
- Notes:
  - _TBD by implementation agent_

## Senior Developer Review
- Reviewer: _TBD_
- Review date: _TBD_
- Decision: _TBD_
- Notes:
  - Verify new `kind` stability and naming consistency
  - Verify `why_slop` explicitly names `factory.observability.schema.migrate`
  - Verify no new gate label or alternate routing was introduced
  - Verify suppression behavior was reused, not reimplemented ad hoc
  - Verify detector remains limited to named Python bootstrap calls

## Review Follow-ups
- [ ] _TBD after review_