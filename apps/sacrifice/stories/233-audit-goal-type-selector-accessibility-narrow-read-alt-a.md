# Story

## Title
Audit goal type selector accessibility — narrow read

## Story
As the team validating D023,
I want reproducible axe-core coverage on the goal creation screen focused on the goal-type selector,
so that selector-specific label, role, or accessible-name violations are detected before frontend remediation lands.

## Acceptance Criteria
- [ ] Run axe-core on the goal creation screen and resolve any label, role, or name violations affecting the goal-type selector.

### Testable Claims (EARS)
AC1.1: WHEN axe-core is run on the goal creation screen, THE test coverage SHALL evaluate the rendered goal-type selector for label violations
AC1.2: WHEN axe-core is run on the goal creation screen, THE test coverage SHALL evaluate the rendered goal-type selector for role violations
AC1.3: WHEN axe-core is run on the goal creation screen, THE test coverage SHALL evaluate the rendered goal-type selector for accessible-name violations
AC1.4: WHEN axe-core reports a label, role, or accessible-name violation affecting the goal-type selector, THE failing audit SHALL surface that violation as an observable test failure

## Tasks / Subtasks
- [ ] Identify the goal creation screen entry point exercised in current frontend tests
- [ ] Add or extend live-browser accessibility audit coverage for the goal creation screen
- [ ] Scope assertions to selector-affecting label, role, and accessible-name violations
- [ ] Make the audit fail on selector-specific violations
- [ ] Keep unrelated screen violations out of story scope unless they block selector validation
- [ ] Document the exact test command/location in the Dev Agent Record

## Dev Notes
- Scope boundary: this story creates the reproducible audit path only. UI remediation belongs to the follow-on frontend story.
- Narrow-read interpretation: do not broaden into full-screen accessibility cleanup. Guard only selector-affecting label, role, or accessible-name failures.
- No `flow.md` provided by direction.
- Verbatim `api_spec.md` embed for backend/test scope:

```md
(none)
```

- Context files to load:
  - [Source: context/project.md#Identity]
  - [Source: context/project.md#Active constraints]
  - [Source: context/navigation.md#When working on auth or token lifecycle]
- Additional context pointers: no scope-matched module files were provided in this invocation prelude; use repository discovery for exact frontend test locations.
- Verbatim direction acceptance criteria:

```md
- [ ] Run axe-core on the goal creation screen and resolve any label, role, or name violations affecting the goal-type selector.
```
- Story-prep note: the direction carries a combined audit+resolve AC. For this test-scoped story, implement the audit/repro path that can fail on selector issues and hand remediation to the dependent frontend story without expanding scope.

## References
- Direction: D023 Audit goal type selector accessibility
- PM tracker: D023 audit goal type selector accessibility
- Target story sequence dependency: `D023 fix selector label/role/name accessibility violations`

## Dev Agent Record
- Status: Not started
- Commands run:
  - _TBD by Dev_
- Files touched:
  - _TBD by Dev_
- Notes:
  - Record the exact audit entry point, test command, and any selector locator assumptions.

## Senior Developer Review
- Status: Pending
- Reviewer:
- Review notes:
  - Confirm audit scope remains limited to goal-type selector accessibility signals.
  - Confirm regression coverage is reproducible in live-browser execution.

## Review Follow-ups
- None yet.
