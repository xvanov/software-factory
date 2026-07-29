# Story

## Title
Pass flow narratives into UX auditor runs — narrow read

## Slug
`pass-flow-narratives-into-ux-auditor-runs-narrow-read-alt-a`

## Scope
`backend`

## Summary
Update the backend path that assembles UX auditor input so each discovered `flow.md` for the target app contributes its filename and ordered step list to the payload delivered to the auditor. Keep scope limited to payload-building behavior; do not expand into runtime app UX changes.

# Acceptance Criteria

- [ ] UX auditor input includes each flow.md filename and ordered step list for the target app.

### Testable Claims (EARS)
AC1.1: WHEN the backend assembles UX auditor input for a target app, THE UX auditor input payload SHALL include each discovered `flow.md` filename for that target app.
AC1.2: WHEN the backend assembles UX auditor input for a target app, THE UX auditor input payload SHALL include the ordered step list from each discovered `flow.md` for that target app.

# Tasks / Subtasks

- [ ] Identify backend entrypoint that assembles UX auditor run input.
- [ ] Trace current source loading for direction artifacts and app context.
- [ ] Add flow narrative extraction for discovered `flow.md` files.
- [ ] Preserve filename-to-step-list pairing in payload structure.
- [ ] Preserve ordered step sequence exactly as loaded.
- [ ] Limit change to UX auditor input-shaping path.
- [ ] Avoid changes to unrelated auditor prompts or app runtime code.
- [ ] Confirm absent `flow.md` handling remains non-breaking.
- [ ] Document payload field expectations in Dev Agent Record during implementation.

# Dev Notes

## Scope notes
- Narrow read: implement only the backend payload assembly change required to pass flow narratives into UX auditor runs.
- Excludes frontend UX updates, auditor rubric changes, issue-routing changes, and broad pipeline redesign.
- PM decomposition context indicates a separate `test` story will lock the regression contract; this story owns the behavior slice only.

## flow.md
[flow.md: none]

## api_spec.md
[api_spec.md: none]

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Top-level layout]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/current-state.md#UX Auditor Pipeline]
- [Source: context/current-state.md#Direction Intake and Artifact Loading]
- [Source: context/modules/backend.md#Automation and agent-facing backend surfaces]
- [Source: context/modules/backend.md#File and service hotspots]

## Direction acceptance criteria (verbatim)
- [ ] UX auditor input includes each flow.md filename and ordered step list for the target app.

## Implementation guidance for Dev
- Load only existing flow narrative inputs associated with the target app/direction scope.
- Emit both filename and ordered steps in the UX auditor input payload.
- Preserve source ordering from each `flow.md`; do not collapse into unordered summaries.
- Keep payload shape deterministic so the paired regression story can assert the contract cleanly.
- If the current pipeline already serializes other direction artifacts, extend that same assembly point rather than introducing a parallel path.

# References

- PM tracker: `D099 pass flow narratives into UX auditor runs`
- Direction: `Pass flow narratives into UX auditor runs`
- Child story context: `D099 include flow.md narratives in UX auditor input payload`
- Related child story handled separately: `D099 add regression test for flow narrative injection`

# Dev Agent Record

- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes:
  - Record exact backend files changed.
  - Record payload field names used for flow filename and ordered steps.
  - Record any no-`flow.md` fallback behavior preserved.

# Senior Developer Review

- Reviewer: TBD
- Review status: Pending
- Checklist:
  - [ ] Change is confined to UX auditor input assembly.
  - [ ] Payload includes both `flow.md` filename and ordered steps.
  - [ ] Step ordering is preserved from source.
  - [ ] No unrelated prompt/pipeline churn introduced.
  - [ ] Implementation aligns exactly to AC1.

# Review Follow-ups

- None yet.
