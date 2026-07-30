# Story

## Title
D014 add story-148 regression fixture and exact-body coverage

## Story
**As a** maintainer of the slop detector
**I want** regression coverage for the exact story-148 bad test body and its fixed form
**so that** the motivating failure mode stays executable and future detector changes cannot silently stop flagging the bypass pattern.

## Scope
- Add regression coverage for the exact bad-body pattern from Direction 014.
- Add paired coverage showing the fixed form is clean.
- Keep this story limited to regression fixtures/assertions; detector mechanics and gate-path proof stay in sibling stories.

## Acceptance Criteria
- A regression test asserts the exact story-148 test body is flagged, and that its fixed form is not.

### Testable Claims (EARS)
AC1.1: WHEN the detector analyzes a regression fixture containing the exact story-148 test body, THE detector SHALL report a finding.
AC1.2: WHEN the detector analyzes the fixed form of the story-148 test, THE detector SHALL report no finding.

## Tasks / Subtasks
- [ ] Identify the existing slop-detector regression-test location for Python test-body fixtures.
- [ ] Add a regression fixture containing the exact story-148 bad test body from the direction.
- [ ] Assert the bad fixture produces the new direct-bootstrap slop finding.
- [ ] Add the paired fixed-form fixture that drives the application initializer instead of direct bootstrap.
- [ ] Assert the fixed-form fixture produces no finding.
- [ ] Keep assertions scoped to regression behavior; do not duplicate detector-rule implementation coverage owned by sibling stories.
- [ ] Run the targeted regression test file(s).
- [ ] Confirm fixture text remains byte-faithful to the direction for the bad-body case.

## Dev Notes
[flow.md: see d014-add-slop-kind-for-direct-test-db-bootstrap-calls Dev Notes for verbatim embed]

[api_spec.md: see no backend story for verbatim embed; direction states "(none)"]

### Context pointers
- No canonical context files were provided in this invocation.
- Use repository source-of-truth files already present in code for detector tests and fixtures.
- If canonical context is added before implementation, load only files that actually exist, especially:
  - `[Source: context/current-state.md#tests-meaningful]`
  - `[Source: context/current-state.md#slop-detector]`
  - `[Source: context/modules/<detector-module>.md#Regression Tests]`

### Direction acceptance criteria (verbatim)
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

### Regression fixture text to preserve verbatim for the bad-body case
```python
db = tmp_path / "factory.db"
engine = create_engine(f"sqlite:///{db}", echo=False)
SQLModel.metadata.create_all(engine)
assert "directions" in _tables(db)
```

### Story-specific implementation notes
- This story consumes the detector behavior created by the sibling infra story; do not redefine finding shape here.
- The regression should prove the motivating example exactly, not an approximate variant.
- The clean fixture must exercise the app-owned initialization path instead of direct `create_engine` / `create_all` bootstrap.
- Keep fixture naming and assertions stable enough for future diff-based regressions.
- If the existing regression harness snapshots `kind` or `why_slop`, assert only what is necessary to prove this story's bad-vs-fixed coverage without taking ownership of gate plumbing.

## References
- Direction: `D014 detect tests that bypass the app entry point`
- Motivating initializer named by direction: `factory.observability.schema.migrate`
- Story 148 bad-body example: embedded in Dev Notes above
- PM decomposition sibling stories:
  - `D014 add slop kind for direct test DB bootstrap calls`
  - `D014 prove noqa suppression and app-initializer clean path`
  - `D014 verify tests-meaningful gate blocks new bypass findings`
  - `D014 make schema tests green under the new slop rule`

## Dev Agent Record
### Agent Model Used
- TBD

### Debug Log References
- TBD

### Completion Notes List
- TBD

### File List
- TBD

## Senior Developer Review
- TBD

## Review Follow-ups
- TBD
