# Story

## Story
As a UX auditor,
I want the goal-creation chat resume state to be observable after leaving and returning,
so that I can confirm the last assistant message and in-progress draft state are restored.

## Acceptance Criteria
- [ ] A scheduled UX audit can leave the chat mid-flow, return later, and confirm the last assistant message and draft state are restored.

### Testable Claims (EARS)
AC1.1: WHEN a scheduled UX audit leaves the chat mid-flow and later returns, THE goal-creation chat SHALL restore the last assistant message.
AC1.2: WHEN a scheduled UX audit leaves the chat mid-flow and later returns, THE goal-creation chat SHALL restore the draft state.

## Tasks / Subtasks
- [ ] Identify the goal-creation chat entry, exit, and re-entry path in the Expo app.
- [ ] Define the minimal persisted session snapshot shape needed for audit-visible resume behavior.
- [ ] Persist chat resume state when the user leaves mid-flow.
- [ ] Rehydrate persisted resume state when the user returns to the goal-creation chat.
- [ ] Render the restored last assistant message from persisted state.
- [ ] Reapply the restored in-progress draft state from persisted state.
- [ ] Ensure the restored state is observable through the normal UX audit flow without developer-only tooling.
- [ ] Add/adjust frontend tests covering leave, return, and restored visible state.
- [ ] Document any unresolved ambiguity in Dev Agent Record if exact chat state boundaries are discovered in code.

## Dev Notes
### Scope notes
- Narrow read: deliver the smallest frontend implementation that makes the resume behavior observable to the UX audit.
- Use the PM decomposition as sequencing guidance only; this story may span persistence plus visible restoration because this invocation is for a single audit-focused story file.
- No backend/API work is in scope unless existing frontend code already depends on it for local session restore.

### flow.md (verbatim)
# User flow

1. Flow: 009-chat-goal-creation/flow.md
2. Step: 6
3. Evidence: Under text_run with no live app session, the requirement that chat resumes from the last assistant message after leaving and returning could not be observed; no navigation state, local session storage, or restored assistant message was available to inspect.
4. Suggestion: Provide a runnable audit fixture or live app target that preserves and exposes chat session state across navigation so resume behavior can be checked empirically.

### api_spec.md
(api_spec.md: none)

### Direction acceptance criteria (verbatim)
- [ ] A scheduled UX audit can leave the chat mid-flow, return later, and confirm the last assistant message and draft state are restored.

### Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on mobile or web login UX]
- [Source: context/current-state.md#Goal creation chat and resume state]
- [Source: context/modules/frontend.md#Navigation and screen state]
- [Source: context/modules/frontend.md#Local persistence]
- [Source: context/modules/auth.md#Client session handling]
- [Source: context/modules/security.md#Local token and client-state handling]

### Implementation constraints
- Prefer existing Expo/React Native client persistence patterns already used in the app.
- Preserve current auth/session boundaries; do not redirect raw access tokens or expand auth scope.
- Resume state must be inspectable in the normal app flow used by an auditor leaving and returning later.
- If no explicit goal-chat persistence module exists, add the minimal local persistence path required for this story.
- Do not rely on ephemeral in-memory navigation state alone.

## References
- `prd.md`
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/frontend.md`
- `context/modules/auth.md`
- `context/modules/security.md`
- Direction: `direction.md`

## Dev Agent Record
- Status: Not started
- Implementation notes:
  - TBD by Dev
- Test evidence:
  - TBD by Dev
- File list:
  - TBD by Dev

## Senior Developer Review
- Status: Pending
- Reviewer:
- Review notes:
  - Verify the leave/return path is auditable without hidden debug affordances.
  - Verify both restored assistant output and restored draft state are visible after re-entry.
  - Verify persistence survives navigation away and later return within expected client session behavior.

## Review Follow-ups
- None yet.
