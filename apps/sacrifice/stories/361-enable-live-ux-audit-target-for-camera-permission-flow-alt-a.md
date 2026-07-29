# Story

## Title
Enable live UX audit target for camera permission flow — narrow read

## Slug
`enable-live-ux-audit-target-for-camera-permission-flow-alt-a`

## Scope
`infra`

## Outcome
Provision the minimum stable live audit target needed so scheduled UX audits can run against a reachable app instance with permission automation enabled for the documented camera-permission-denied branch.

# Acceptance Criteria

1. Verbatim direction AC:
   - A scheduled UX audit can open the app, trigger Record proof, deny camera permission, and verify the expected error text plus Open settings and Cancel actions.

### Testable Claims (EARS)
AC1.1: WHEN a scheduled UX audit runs against the provisioned live target, THE app/audit environment SHALL allow the audit to open the app.
AC1.2: WHEN a scheduled UX audit runs against the provisioned live target, THE app/audit environment SHALL allow the audit to trigger Record proof.
AC1.3: WHEN the audit denies camera permission on the provisioned live target, THE app/audit environment SHALL expose the permission-denied branch for verification.
AC1.4: WHEN the permission-denied branch is exposed during the scheduled UX audit, THE app SHALL present the expected error text.
AC1.5: WHEN the permission-denied branch is exposed during the scheduled UX audit, THE app SHALL present an Open settings action.
AC1.6: WHEN the permission-denied branch is exposed during the scheduled UX audit, THE app SHALL present a Cancel action.

# Tasks / Subtasks

- [ ] Identify the scheduler/runtime gap blocking live UX audit execution for camera permission denial.
- [ ] Provision a stable live audit target reachable by scheduled UX runs.
- [ ] Enable browser/device permission automation needed to drive camera denial on that target.
- [ ] Keep scope to deployment/runtime wiring only; no unrelated frontend copy or flow changes.
- [ ] Document target URL, required runtime flags, and scheduler hookup in repo-owned config/docs touched by this story.
- [ ] Validate the target can host the documented Record proof path under scheduled execution.
- [ ] Capture the handoff constraint for the follow-up test story: consume this live target rather than re-provisioning infrastructure.

# Dev Notes

## Scope notes
- Narrow-read boundary: this story is limited to provisioning/runtime wiring for a stable live audit target.
- Do not change the documented UX copy unless the follow-up audit story proves the UI diverges.
- Do not broaden into unrelated deploy/auth/environment refactors.
- Because this is the primary flow exerciser for the direction's deploy/runtime gap, embed `flow.md` verbatim here.
- No `api_spec.md` content exists for this direction.

## Verbatim flow.md embed

# User flow

1. Flow: 008-camera-capture-pipeline/flow.md
2. Step: 2
3. Evidence: Deploy is disabled and scheduler transport is text_run, so the permission-denied branch for getByRole('button', { name: 'Record proof' }) could not be exercised against a running app; expected copy 'Camera access is required to submit this proof', 'Open settings', and 'Cancel' was not observable.
4. Suggestion: Provision a stable live audit target with browser/device permissions enabled so the camera permission-denied path can be replayed and verified end-to-end.

## Verbatim api_spec.md embed

(none)

## Verbatim direction acceptance criteria

- [ ] A scheduled UX audit can open the app, trigger Record proof, deny camera permission, and verify the expected error text plus Open settings and Cancel actions.

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#Navigation]

## Implementation pointers for Dev/Test-Designer
- Scheduled audits currently cannot exercise the branch because deploy is disabled and scheduler transport is `text_run` per `flow.md` evidence.
- Treat this story as environment enablement for a later scheduled audit; the follow-up test story should add the actual scenario/assertions.
- Preserve the documented UI branch expectations from `flow.md`: `Record proof`, `Camera access is required to submit this proof`, `Open settings`, `Cancel`.
- If explicit runtime/config files for scheduler/live target are discovered during implementation, keep edits minimal and story-scoped.
- If no existing deploy path can satisfy the AC without architecture changes, record the concrete blocker in the Dev Agent Record instead of improvising a broader platform rewrite.

# References

- Direction: `direction.md`
- Flow: `flow.md`
- PM decomposition context: `pm_result.child_stories`
- Canonical story path: `stories/0-enable-live-ux-audit-target-for-camera-permission-flow-alt-a.md`

# Dev Agent Record

## Agent Model Used
- TBD

## Debug Log References
- TBD

## Completion Notes List
- TBD

## File List
- TBD

# Senior Developer Review

- TBD

# Review Follow-ups

- TBD
