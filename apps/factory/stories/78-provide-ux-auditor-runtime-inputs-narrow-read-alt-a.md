# Story

## Title
Provide UX auditor runtime inputs — narrow read

## Story
As the scheduled UX audit pipeline,
I want scheduled UX audit input to carry at least one `flow.md` artifact plus app URL/runtime context,
so that the UX auditor receives concrete runtime inputs instead of guessing the target flow and environment.

## Scope
Backend. Narrow read: scheduler/input-builder path only. This story does not implement auditor citation/parsing behavior beyond ensuring the required artifacts and runtime context are present in scheduled UX audit input.

# Acceptance Criteria

- [ ] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [ ] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

### Testable Claims (EARS)
AC1.1: WHEN a scheduled UX audit input is built, THE scheduled UX audit input SHALL include at least one `flow.md` artifact.
AC1.2: WHEN a scheduled UX audit input is built, THE scheduled UX audit input SHALL include app URL context.
AC1.3: WHEN a scheduled UX audit input is built, THE scheduled UX audit input SHALL include runtime context.
AC2.1: UNTESTABLE-AS-WRITTEN — this narrow-read story is scoped to transport/runtime-input plumbing only; the criterion does not specify the citation mechanism, output surface, or parser behavior required to prove reference to concrete flow filenames and step numbers.

# Tasks / Subtasks

- [ ] Identify scheduled UX audit entrypoint and input-builder path in codebase.
- [ ] Identify existing scheduled audit payload shape and transport boundary.
- [ ] Add required `flow.md` artifact inclusion to scheduled UX audit input.
- [ ] Add app URL context field(s) to scheduled UX audit input.
- [ ] Add runtime context field(s) to scheduled UX audit input.
- [ ] Ensure at least one concrete flow artifact is attached or embedded on scheduled UX audit execution.
- [ ] Preserve backward compatibility for non-UX scheduled audits, if such path exists.
- [ ] Add/extend unit tests for scheduled UX audit input builder.
- [ ] Add/extend integration test covering scheduled UX audit payload contents.
- [ ] Verify story scope excludes auditor citation/parsing changes.
- [ ] Document exact payload/input fields touched in Dev Agent Record.

# Dev Notes

## Scope Boundary
- Implement only the scheduled UX audit input plumbing.
- Do not implement or modify auditor finding citation logic unless strictly required to keep existing interfaces compiling.
- If AC2 remains unmet after this slice, record that gap in Senior Developer Review / Follow-ups for the next slice.

## Flow Artifact
[flow.md: none]

## API Spec
[api_spec.md: none]

## Context Pointers
- No canonical context files were provided in the prelude.
- Repo context is currently unavailable; derive implementation details from inspected code paths only.
- If this run also includes onboarding/context generation elsewhere in the chain, prefer the generated canonical docs once available before coding.

## Direction Acceptance Criteria (verbatim)
- [ ] Scheduled UX audit input includes at least one flow.md plus app URL/runtime context.
- [ ] UX auditor can reference concrete flow filenames and step numbers from supplied artifacts.

## Implementation Notes
- Treat `flow.md` inclusion as a concrete artifact requirement, not a generic text blob requirement.
- “app URL/runtime context” must be transported in the scheduled UX audit input payload or equivalent invocation structure used by the scheduler.
- If the current scheduler supports multiple artifacts, ensure at least one attached artifact is a `flow.md` file for UX audit runs.
- If the current scheduler supports a single artifact bundle, ensure the bundle contains at least one concrete `flow.md` filename and contents plus URL/runtime context.
- Preserve clear traceability so the next backend slice can consume filenames and step numbers from the supplied artifacts.
- Because no `flow.md` or `api_spec.md` sibling files were provided with the direction, do not invent file contents or contracts beyond what the codebase already supports.

# References

- Direction: `D009 provide-ux-auditor-runtime-inputs`
- PM tracker: `D009 provide-ux-auditor-runtime-inputs`
- Child-story decomposition context:
  - `D009 attach flow.md and app runtime context to scheduled UX audits`
  - `D009 make UX auditor cite flow filenames and step numbers`

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
