# Story

## Title
Enable executable UX audit target for camera proof flow — broad read

## Scope
infra

## Summary
Provision and verify a stable live app target that the UX audit harness can open from a browser/mobile sandbox so the documented camera proof flow branches become executable against a running app.

# Acceptance Criteria

- [ ] UX audit can open the app in a live browser/mobile sandbox and execute the camera proof flow branches with observable UI evidence.

### Testable Claims (EARS)
AC1.1: WHEN the UX audit is run, THE app SHALL be openable in a live browser/mobile sandbox.
AC1.2: WHEN the app is opened in the live browser/mobile sandbox, THE camera proof flow branches SHALL be executable.
AC1.3: WHEN the camera proof flow branches are executed in the live browser/mobile sandbox, THE system SHALL provide observable UI evidence.

# Tasks / Subtasks

- [ ] Identify the canonical live target path for audit runs
  - [ ] Choose reserved live-browser sandbox path or stable deploy URL
  - [ ] Ensure target is reachable without manual local port ownership steps
  - [ ] Define required runtime/config inputs for audit environment
- [ ] Provision the executable target
  - [ ] Add infra/config needed to expose the app at the canonical target
  - [ ] Ensure target serves the camera proof flow entry path used by audit
  - [ ] Keep provisioning minimal to this direction's scope
- [ ] Add target verification hook
  - [ ] Add a smoke-level reachability check for the live target
  - [ ] Verify browser-openable behavior from audit context assumptions
  - [ ] Record expected invocation surface for downstream test story
- [ ] Capture operational constraints for downstream agents
  - [ ] Note any environment variables, secrets, or deploy prerequisites
  - [ ] Note any platform limitations affecting camera permission replay
  - [ ] Point docs story to canonical invocation path

# Dev Notes

## flow.md
# User flow

1. Flow: 008-camera-capture-pipeline/flow.md
2. Step: 2
3. Evidence: App URL is unavailable in the provided runtime context (`Deploy: disabled`) and the scheduler transport is `text_run`, so the documented permission-denied branch (`"Camera access is required to submit this proof"`, `"Open settings"`, `"Cancel"`) could not be exercised or observed against a running target.
4. Suggestion: Provision the reserved live-browser sandbox path or a stable deploy URL so the camera permission flows can be replayed and verified end-to-end.

## api_spec.md
[api_spec.md: see none; direction states `(none)`]

## Direction acceptance criteria (verbatim)
- [ ] UX audit can open the app in a live browser/mobile sandbox and execute the camera proof flow branches with observable UI evidence.

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]

## Implementation notes for Dev/Test-Designer
- This broad-read infra story covers the provisioning boundary needed to make downstream executable audit work possible.
- The live target must be stable enough that a later test story can open it without relying on unavailable local app URLs.
- The direction evidence explicitly identifies `Deploy: disabled` and `text_run` as blockers; the implementation should remove the live-target blocker without expanding into unrelated UX or product changes.
- Because this is an infra story, include cross-story handoff details for the test stories that will prove camera proof entry and permission-denied branch behavior on the live target.

# References

- PM tracker: `D104 enable executable UX audit target for camera proof flow`
- Related child-story decomposition context:
  - `D104 provision a stable live app target for UX audit runs`
  - `D104 add executable smoke check for camera proof audit target`
  - `D104 cover permission-denied camera proof branch in live audit`
  - `D104 document how to run camera proof UX audit on live target`
- Canonical output path: `stories/0-enable-executable-ux-audit-target-for-camera-proof-flo-alt-b.md`

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
