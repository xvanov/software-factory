# Story
**Title:** Enable UX auditor flow replay inputs — narrow read  
**Slug:** enable-ux-auditor-flow-replay-inputs-narrow-read-alt-a  
**Scope:** backend

## Acceptance Criteria
1. Verbatim direction ACs in scope for this narrow-read backend story:
   - [ ] UX auditor invocation includes extracted flow.md files in its input payload.
2. Out-of-scope direction ACs for this story; satisfy via sibling stories, do not implement here:
   - [ ] UX auditor can access a live app URL in a browser-enabled sandbox and execute semantic Playwright locators against it.
   - [ ] A scheduled run returns evidence from observed steps rather than reporting missing runtime inputs.

### Testable Claims (EARS)
AC1.1: WHEN the UX auditor invocation payload is constructed for a direction that has extracted flow.md files, THE backend invocation path SHALL include the extracted flow.md files in its input payload.
AC2.1: UNTESTABLE-AS-WRITTEN — scoped to sibling story; this backend narrow-read story does not own browser-enabled sandbox access or semantic Playwright execution.
AC3.1: UNTESTABLE-AS-WRITTEN — scoped to sibling story; this backend narrow-read story does not own scheduled-run evidence reporting behavior.

## Tasks / Subtasks
- [ ] Identify UX auditor invocation entrypoint and payload-shaping boundary.
- [ ] Trace current direction artifact extraction path for flow.md availability.
- [ ] Add flow.md extracted-content field(s) to auditor input payload contract.
- [ ] Preserve existing payload fields and backward-compatible behavior for directions without flow.md.
- [ ] Ensure no fabricated flow content when direction has no flow.md.
- [ ] Add/adjust backend tests at payload boundary.
- [ ] Verify tests assert inclusion of extracted flow.md content when present.
- [ ] Verify tests assert omission or empty-handling when flow.md is absent.
- [ ] Document touched interfaces in Dev Agent Record.

## Dev Notes
### Scope Notes
- Narrow read = only the first PM child-story value slice: wire extracted `flow.md` content into the UX auditor invocation payload and prove it at the boundary where the auditor consumes inputs.
- Do not solve live URL provisioning, browser sandbox setup, Playwright execution, or scheduled evidence formatting in this story.
- Direction provides no sibling `flow.md`; therefore no verbatim flow embed is possible for this story.
- Direction provides no sibling `api_spec.md`; therefore no verbatim API embed is possible for this story.
- Because the direction acceptance criteria span multiple slices, only the in-scope AC is implementation-targeted here; remaining direction ACs are explicitly deferred to sibling stories.

### flow.md
(none)

### api_spec.md
(none)

### Context Pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/current-state.md#UX auditor]
- [Source: context/current-state.md#Directions and artifacts]
- [Source: context/modules/backend.md#Background jobs and service boundaries]
- [Source: context/modules/backend.md#Testing]
- [Source: context/modules/security.md#Runtime input handling]

### Verbatim Direction Acceptance Criteria
- [ ] UX auditor invocation includes extracted flow.md files in its input payload.
- [ ] UX auditor can access a live app URL in a browser-enabled sandbox and execute semantic Playwright locators against it.
- [ ] A scheduled run returns evidence from observed steps rather than reporting missing runtime inputs.

### Implementation Notes for Dev/Test Design
- Treat `flow.md` as extracted direction input, not handwritten fixture prose.
- Assert presence at the invocation boundary the auditor consumes, not only in an upstream intermediate object.
- Preserve current explore-mode behavior noted by PM: this direction is actionable without sibling `flow.md`; the path must handle absence explicitly rather than failing ambiguously.
- If the existing auditor payload already carries generic artifacts, tests must prove `flow.md` extraction is included in the effective input payload delivered to the auditor, not merely stored nearby.
- Any contract changes must remain compatible with later sibling stories that add live URL/runtime fields.
- If direction/artifact extraction behavior is undocumented or unclear in code, capture exact observed source of truth in Dev Agent Record for reviewer traceability.

## References
- Direction: `direction.md`
- PM decomposition context: `pm_result.child_stories`
- Story template: `factory/artifacts/story_template.md`
- Canonical docs: `context/project.md`, `context/navigation.md`, `context/current-state.md`, `context/modules/backend.md`, `context/modules/security.md`

## Dev Agent Record
- Status: Not started
- Agent:
- Branch:
- PR:
- Changed files:
  - 
- Notes:
  - 

## Senior Developer Review
- Reviewer:
- Review date:
- Outcome:
- Notes:
  - Verify payload inclusion at the actual auditor-consumption boundary.
  - Verify no accidental coupling to sandbox/browser provisioning fields.
  - Verify absent-`flow.md` behavior is explicit and tested.

## Review Follow-ups
- [ ] None yet.