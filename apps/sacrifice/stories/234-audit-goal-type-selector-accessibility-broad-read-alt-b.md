# Story

## Story
As a quality engineer,
I want reproducible axe-core coverage for the goal creation screen,
so that any label, role, or accessible-name violations affecting the goal-type selector are detected and constrained before frontend remediation ships.

## Acceptance Criteria
- [ ] Run axe-core on the goal creation screen and resolve any label, role, or name violations affecting the goal-type selector.

### Testable Claims (EARS)
AC1.1: WHEN axe-core is executed against the goal creation screen, THE test harness SHALL produce an observable audit result for that screen.
AC1.2: WHEN the audit result includes a label violation affecting the goal-type selector, THE system SHALL require that violation to be resolved.
AC1.3: WHEN the audit result includes a role violation affecting the goal-type selector, THE system SHALL require that violation to be resolved.
AC1.4: WHEN the audit result includes an accessible-name violation affecting the goal-type selector, THE system SHALL require that violation to be resolved.

## Tasks / Subtasks
- [ ] Identify the live-browser test entry point that can render the goal creation screen.
- [ ] Add an axe-core audit covering the goal creation screen.
- [ ] Scope assertions to violations affecting the goal-type selector.
- [ ] Ensure audit output is reproducible in local and CI-style execution.
- [ ] Capture current failing findings, if any, as regression-driving evidence.
- [ ] Document selector-targeting assumptions in test comments or helper naming.
- [ ] Confirm unrelated screen violations do not expand this story's assertion scope unless they block selector validation.

## Dev Notes
- Scope intent from PM decomposition: this story is the reproducible audit slice that precedes frontend remediation; broad-read interpretation permits covering the whole goal creation screen audit path so long as assertions remain traceable to selector-specific label/role/name findings.
- `flow.md` not provided by direction.
- Verbatim `api_spec.md` embed for test scope:

```md
(none)
```

- Load these context files before implementation and test design:
  - [Source: context/project.md#Identity]
  - [Source: context/project.md#Active constraints]
  - [Source: context/navigation.md#When working on auth or token lifecycle]
  - [Source: context/modules/frontend.md]
  - [Source: context/modules/auth.md]
  - [Source: context/modules/security.md]
  - [Source: context/current-state.md#Goal creation flow]
  - [Source: context/current-state.md#Testing and quality signals]

- Verbatim direction acceptance criteria:

```md
- [ ] Run axe-core on the goal creation screen and resolve any label, role, or name violations affecting the goal-type selector.
```

- Story-level test boundary:
  - Create the audit and regression guard.
  - Do not perform unrelated goal creation UX cleanup.
  - If the audit exposes unrelated violations elsewhere on the screen, keep assertions and reported blockers focused on selector validation unless those unrelated violations prevent the selector audit from executing.
- Expected downstream handoff:
  - This story should leave a failing or passing automated audit artifact that clearly identifies whether selector-specific remediation is required.
  - The frontend follow-up story consumes those findings and fixes only selector label/role/name issues.

## References
- `factory/artifacts/story_template.md`
- `backend/tests/test_auth.py`
- `backend/tests/test_email_auth.py`
- `frontend/App.tsx`
- `frontend/package.json`
- `frontend/AGENTS.md`

## Dev Agent Record
- Agent Model Used: 
- Debug Log References: 
- Completion Notes: 
- File List: 

## Senior Developer Review
- Review Status: Pending
- Reviewer: 
- Review Notes: 

## Review Follow-ups
- [ ] None yet.
