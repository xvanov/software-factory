# Story

## Title
Add abuse controls for proof and verification endpoints — narrow read

## Slug
`add-abuse-controls-for-proof-and-verification-endpoints-narr`

## Scope
backend

## Summary
Prepare the narrow backend slice for D057 by decomposing the direction into ordered implementation work centered on reusable JSON payload guards, proof-route adoption, verification timeout/concurrency controls, and public-route abuse protections. This story is the single source of truth for sequencing and acceptance traceability across the backend slices declared by PM.

## Dependencies
- Direction D057 acceptance criteria
- PM child story decomposition in `pm_result.child_stories`

## Out of Scope
- Frontend UX changes
- CLI credential handling changes
- New product requirements beyond D057 acceptance criteria
- Threshold values not stated by direction

## Story Statement
As the backend team,
I want the proof submission, verification, and public auth/OAuth routes protected by explicit abuse controls,
so that unbounded payloads and downstream verification cannot be used as a straightforward DoS path.

# Acceptance Criteria
- [ ] Proof-related endpoints reject oversized or deeply nested payloads
- [ ] External verification paths have explicit timeout and concurrency limits
- [ ] Rate limiting or equivalent abuse controls protect public-facing API routes

### Testable Claims (EARS)
AC1.1: WHEN a proof-related endpoint receives an oversized payload, THE endpoint SHALL reject the request
AC1.2: WHEN a proof-related endpoint receives a deeply nested payload, THE endpoint SHALL reject the request
AC2.1: WHEN an external verification path executes, THE verification path SHALL enforce an explicit timeout limit
AC2.2: WHEN external verification work executes concurrently, THE verification path SHALL enforce an explicit concurrency limit
AC3.1: WHEN requests reach a public-facing API route, THE route SHALL be protected by rate limiting or equivalent abuse controls

# Tasks / Subtasks
- [ ] Confirm scope boundary for narrow read against PM child stories
- [ ] Implement reusable JSON payload guard utility
- [ ] Add tests covering oversized payload rejection
- [ ] Add tests covering deeply nested payload rejection
- [ ] Wire payload guard into proof submission routes
- [ ] Add route-level tests for proof submission rejection behavior
- [ ] Add timeout wrapper around external verification calls
- [ ] Add tests proving timeout enforcement on verification paths
- [ ] Add concurrency cap around external verification executions
- [ ] Add tests proving saturation/concurrency-limit behavior
- [ ] Add rate limiting or equivalent abuse controls to public auth routes
- [ ] Add tests proving abuse protection on login/register routes
- [ ] Add rate limiting or equivalent abuse controls to public OAuth entry/exchange routes
- [ ] Add tests proving abuse protection on OAuth public routes
- [ ] Verify no unstated thresholds are hard-coded into story requirements
- [ ] Document any implementation-selected thresholds in code/tests, not as story ACs

# Dev Notes
## Direction acceptance criteria — verbatim
- [ ] Proof-related endpoints reject oversized or deeply nested payloads
- [ ] External verification paths have explicit timeout and concurrency limits
- [ ] Rate limiting or equivalent abuse controls protect public-facing API routes

## flow.md
(none)

## api_spec.md
(none)

## Scope and sequencing notes
- Narrow read follows PM decomposition as the authoritative execution sequence.
- Payload guard utility lands before proof-route adoption.
- Verification timeout lands before verification concurrency cap.
- Public auth-route abuse controls land before public OAuth entry/exchange abuse controls.
- This story prepares backend-only work; do not expand into frontend, docs, or CLI implementation unless directly required by backend tests.
- Direction does not prescribe concrete size, depth, timeout, concurrency, or rate-limit thresholds. Implementation may choose values under `explore: true`, but the story does not invent them.

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]
- [Source: context/navigation.md#When working on replay defenses or session invalidation]
- [Source: context/navigation.md#When working on pledge-abuse surfaces after auth]
- [Source: context/current-state.md#auth-and-session-surfaces]
- [Source: context/current-state.md#api-and-backend-shape]
- [Source: context/current-state.md#known-risks-and-open-gaps]
- [Source: context/modules/auth.md#Backend routes and services]
- [Source: context/modules/auth.md#Security constraints]
- [Source: context/modules/security.md#Abuse-sensitive surfaces]
- [Source: context/modules/security.md#Existing controls and gaps]
- [Source: context/modules/backend.md#FastAPI routes]
- [Source: context/modules/backend.md#Testing patterns]

## Implementation boundary hints for Dev/Test Designer
- Proof-related endpoints means the proof submission surface, not all authenticated JSON endpoints.
- External verification paths means downstream verification execution paths that can stall or saturate workers.
- Public-facing API routes means unauthenticated auth/OAuth routes identified by PM decomposition for this direction.
- If a context section named above is absent in the loaded prelude, use the nearest matching section in that canonical file and record the exact heading used during implementation.
- If current-state docs do not yet reflect route names or verification call sites, inspect backend route/service modules named in `context/project.md` and update tests to target actual production paths.

# References
- `context/project.md`
- `context/navigation.md`
- `context/current-state.md`
- `context/modules/auth.md`
- `context/modules/security.md`
- `context/modules/backend.md`
- PM tracker: `D057 abuse controls for proof and verification endpoints`

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
