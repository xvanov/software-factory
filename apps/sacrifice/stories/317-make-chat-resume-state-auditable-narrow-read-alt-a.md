# Story

## Title
Make chat resume state auditable — narrow read

## Scope
frontend

## Summary
Expose deterministic, runnable frontend evidence of persisted chat resume state so the scheduled UX audit has an objective target to inspect under `text_run` without depending on a live app session.

# Acceptance Criteria

- [ ] Scheduled UX audit can leave the chat flow, return later, and verify the session resumes from the last assistant message with objective evidence.

### Testable Claims (EARS)
AC1.1: WHEN the scheduled UX audit leaves the chat flow and later returns, THE runnable frontend audit target or scripted fixture SHALL expose objective evidence showing whether the session resumes from the last assistant message.

# Tasks / Subtasks

- [ ] Identify current frontend chat-session persistence and restore entrypoints
- [ ] Define narrow audit surface for persisted chat resume evidence
- [ ] Implement runnable fixture or debug target consumable under `text_run`
- [ ] Surface persisted session identifier, last assistant message evidence, and restore-state evidence
- [ ] Ensure output is deterministic and readable without a live app session
- [ ] Keep implementation scoped to observability; do not change product resume behavior
- [ ] Document invocation path and expected evidence shape in story-linked code comments or fixture README if created
- [ ] Add or update frontend tests covering evidence generation from persisted state
- [ ] Verify scheduled-audit handoff needs are satisfied for the follow-on test story

# Dev Notes

## Scope Notes
- Narrow read: this story only creates the auditable frontend evidence surface.
- The follow-on test story consumes that surface in the scheduled UX audit runtime.
- Do not broaden into audit-runner assertions here.

## flow.md (verbatim embed)
# User flow

1. Flow: 009-chat-goal-creation/flow.md
2. Step: 6
3. Evidence: Under `text_run` without a live app session, the resume-on-return requirement (`chat session resumes from the last assistant message`) could not be verified because no local session storage, navigation, or restored assistant state was observable.
4. Suggestion: Add a runnable audit target or scripted fixture that exposes persisted chat-session state so resume behavior can be checked empirically.

## api_spec.md
[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

## Direction Acceptance Criteria (verbatim embed)
- [ ] Scheduled UX audit can leave the chat flow, return later, and verify the session resumes from the last assistant message with objective evidence.

## Context Pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]

## Implementation Pointers
- Audit evidence must be inspectable under `text_run` without requiring a live app session.
- Evidence should reflect persisted local session state, navigation/resume state, and restored assistant state if those are part of the existing frontend resume path.
- Prefer a minimal fixture/debug target over production UX changes.
- Preserve existing user-facing behavior; add observability only.
- If no explicit chat-resume module exists in provided context, developer must trace actual implementation from frontend app entry, storage layer, and chat screen state restoration points before coding.

## Gaps / Risks
- No scope-matched module files were provided in this prelude for chat-specific frontend state; implementation must validate actual file ownership before edits.
- `api_spec.md` is explicitly `(none)` in the direction.

# References

- Direction: `direction.md`
- Flow: `flow.md`
- PM tracker: `D105 make-chat-resume-state-auditable`
- Follow-on story dependency: scheduled UX audit consumption of this evidence surface

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
