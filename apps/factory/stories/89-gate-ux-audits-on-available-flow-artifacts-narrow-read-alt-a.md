# Story

## Story
As the backend orchestration path that launches replay-based UX auditing,
I want the run skipped or marked not-applicable when no `flow.md` artifacts are available,
so the system does not perform evidence-free UX replay audits.

## Acceptance Criteria
- [ ] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.

### Testable Claims (EARS)
AC1.1: WHEN replay-based UX auditing is about to run, GIVEN zero `flow.md` files are available, THE UX auditor run SHALL be skipped or marked not-applicable.

## Tasks / Subtasks
- [ ] Identify the backend decision point that launches or classifies replay-based UX auditor runs.
- [ ] Detect the available `flow.md` artifact count from invocation context at that decision point.
- [ ] Gate replay-based UX auditing when the available `flow.md` artifact count is zero.
- [ ] Preserve existing replay-based UX auditing behavior when one or more `flow.md` artifacts are available.
- [ ] Record the skipped or not-applicable outcome through the existing run/result classification path.
- [ ] Add automated coverage for zero-`flow.md` gating behavior.
- [ ] Add automated coverage proving replay-based UX auditing is not blocked when `flow.md` is available.
- [ ] Verify no payload-enrichment changes are introduced in this story.

## Dev Notes
### Scope Notes
- Narrow-read scope for this record: implement only the guardrail at the launch/classification point for replay-based UX auditing.
- Exclude payload assembly changes for `flow.md` path/content; that belongs to the separate child story: `D011 include flow.md path and contents in UX audit payload`.
- Direction acceptance criteria not assigned to this story remain out of scope for implementation here.

### flow.md
(none)

### api_spec.md
(none)

### Direction Acceptance Criteria (verbatim)
- [ ] UX auditor run is skipped or marked not-applicable when zero flow.md files are available.
- [ ] Invocation payload includes at least one flow.md path and contents before replay-based auditing runs.

### Context Pointers
- No canonical context files were provided in the prelude for this run.
- Load implementation context from repository code at the UX auditor invocation path, artifact discovery path, and run-status classification path.

### Implementation Constraints
- Gate must evaluate actual available `flow.md` artifacts before replay-based auditing starts.
- Outcome wording may follow existing system terminology so long as behavior is clearly skipped or not-applicable.
- Do not weaken existing successful-path behavior for runs where one or more `flow.md` artifacts are available.
- Do not add payload-content requirements in this story.

## References
- Direction: `Gate UX audits on available flow artifacts`
- PM tracker: `D011 gate UX audits on available flow artifacts`
- Related child story: `D011 skip or mark UX replay audit N/A without flow.md`
- Follow-on child story: `D011 include flow.md path and contents in UX audit payload`

## Dev Agent Record
- Status: Not started
- Agent: TBD
- Branch: TBD
- Notes:
  - TBD

## Senior Developer Review
- Status: Pending
- Reviewer: TBD
- Notes:
  - Verify guardrail sits at the authoritative launch/classification point.
  - Verify zero-`flow.md` behavior is observable and test-covered.
  - Verify no payload-enrichment scope leaked into this slice.

## Review Follow-ups
- None yet.
