# Story
Provide observable goal-type generation demo states — broad read

## Acceptance Criteria
- [ ] A runnable environment or fixture lets the UX audit observe each documented status-banner state and the final notification-driven return path.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit runs the provided demo environment or fixture, THE system SHALL expose each documented status-banner state for observation.
AC1.2: WHEN the UX audit runs the provided demo environment or fixture, THE system SHALL expose the final notification-driven return path for observation.

## Tasks / Subtasks
- [ ] Confirm current goal-type generation status surfaces and auth requirements.
- [ ] Define deterministic demo-state source covering documented banner sequence.
- [ ] Implement backend fixture/config path that does not require real background factory work.
- [ ] Implement one runnable app-facing runtime path for consuming demo states.
- [ ] Ensure runtime path can drive final notification-driven return-path state.
- [ ] Add backend automated coverage for demo-state sequence and terminal return-path exposure.
- [ ] Verify fixture/demo behavior is deterministic across repeated runs.
- [ ] Document runtime toggles, seed inputs, and operational constraints in story record notes for downstream docs story.

## Dev Notes
### Flow Embed
# User flow

1. Flow: 010-goal-type-generator/flow.md
2. Step: 6
3. Evidence: The status-banner progression (`queued` → `in progress` → `pull request open` → `merging`) depends on background factory updates, but the provided runtime has no live application endpoint or event stream, so the user-visible transition behavior could not be observed.
4. Suggestion: Expose a deterministic demo or staging flow for goal-type generation status updates so the audit can verify each banner transition and notification handoff.

### API Spec Embed
(none)

### Direction Acceptance Criteria Embed
- [ ] A runnable environment or fixture lets the UX audit observe each documented status-banner state and the final notification-driven return path.

### Scope Notes
- Broad-read scope covers the enabling backend work needed for the PM-declared backend slices: deterministic fixture state source plus one runnable app-facing demo path.
- Prefer deterministic fixture/demo behavior over real long-running orchestration.
- Do not require live background factory updates or event-stream infrastructure if a narrower backend hook can satisfy observability.
- Keep auth and security expectations aligned with current backend patterns; do not bypass shared auth dependencies without an explicit demo-only boundary.
- If current code lacks goal-type generation primitives, introduce the smallest isolated backend contract that downstream frontend/demo stories can consume.

### Context Pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/current-state.md#Goal-type generation observability gap]
- [Source: context/current-state.md#Auth and token lifecycle]
- [Source: context/modules/backend.md#API patterns]
- [Source: context/modules/backend.md#Testing]
- [Source: context/modules/auth.md#Bearer and session flows]
- [Source: context/modules/security.md#Demo and fixture safety]

### Implementation Constraints for Dev
- The audit target is observability, not production orchestration fidelity.
- The documented banner sequence is fixed for this direction: `queued` → `in progress` → `pull request open` → `merging`.
- The final notification-driven return path must be representable from the backend demo state contract, even if the visual handoff is completed by a frontend story.
- Any demo toggle/fixture path must be runnable in local audit conditions without depending on unavailable live application event streams.
- Preserve a clean separation between demo data paths and normal production behavior.
- If backend/runtime discoverability needs endpoint documentation, leave precise run instructions to the later docs story but ensure the implemented path is stable enough to document.

## References
- Direction: `direction.md`
- Flow: `flow.md`
- PM decomposition context: `pm_result.child_stories`
- Story template: `factory/artifacts/story_template.md`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch/PR: TBD
- Notes:
  - TBD

## Senior Developer Review
- Reviewer: TBD
- Review status: Pending
- Notes:
  - Verify deterministic sequence matches direction wording exactly.
  - Verify runnable backend path exists independent of real background work.
  - Verify backend contract includes enough signal for notification return-path demo.
  - Verify tests fail if a documented state becomes unobservable.

## Review Follow-ups
- None yet.
