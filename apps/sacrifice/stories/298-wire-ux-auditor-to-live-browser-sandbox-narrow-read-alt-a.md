# Story

## Title
Wire UX auditor to live browser sandbox — narrow read

## Slug
wire-ux-auditor-to-live-browser-sandbox-narrow-read-alt-a

## Scope
infra

## Summary
Enable the existing UX auditor execution path to run inside a browser-capable sandbox runtime. Narrow read: this story stops at infrastructure/runtime wiring and an observable proof that the sandbox can launch browser-backed UX auditor runs; it does not redesign finding generation semantics beyond what is needed to prove the runtime path exists.

# Acceptance Criteria

- [ ] ux_auditor runs with browser access and can emit findings citing Playwright locator actions, response timings, or axe rule ids.

### Testable Claims (EARS)
AC1.1: WHEN ux_auditor is executed through the intended sandbox path, THE sandbox/runtime SHALL provide browser access to that run.
AC1.2: WHEN ux_auditor produces findings through that browser-capable path, THE ux_auditor output SHALL include citations grounded in Playwright locator actions, response timings, or axe rule ids.

# Tasks / Subtasks

- [ ] Identify the existing ux_auditor execution entrypoint used by the sandbox path.
- [ ] Add browser-capable runtime wiring for ux_auditor runs.
- [ ] Keep the change scoped to runtime enablement; do not redesign unrelated auditor logic.
- [ ] Ensure required browser dependencies/bootstrap steps are available in the sandbox execution environment.
- [ ] Ensure the sandbox path can launch a browser session non-interactively.
- [ ] Add or update a minimal smoke execution proving the ux_auditor path can run with browser access.
- [ ] Capture an observable artifact/log/assertion showing the browser-backed path executed.
- [ ] Verify the wired path is suitable for downstream evidence-emission work.
- [ ] Confirm no forbidden doc paths are touched.

# Dev Notes

## Scope guard
- This is the infra dependency slice from PM decomposition.
- Implement runtime/browser sandbox wiring only.
- Do not broaden into full evidence-format redesign or operator documentation beyond inline developer-facing execution notes required for this story.
- Because this is an `infra` story, downstream evidence-shaping work belongs to the later backend slice.

## Flow
[flow.md: none]

## API spec
[api_spec.md: none]

## Direction acceptance criteria (verbatim)
- [ ] ux_auditor runs with browser access and can emit findings citing Playwright locator actions, response timings, or axe rule ids.

## Context pointers
- [Source: context/project.md#Identity]
- [Source: context/project.md#Stack]
- [Source: context/project.md#Top-level layout]
- [Source: context/project.md#Active constraints]
- [Source: context/navigation.md#When working on auth or token lifecycle]

## Implementation notes
- Repo context is app-focused; verify the ux_auditor runtime location before changing files.
- Preferred outcome for this story: existing sandbox invocation path gains the capability to launch a live browser session needed by ux_auditor.
- Proof should be objective and automation-friendly: command success, smoke test, or runtime assertion indicating browser-backed execution occurred.
- Keep interfaces stable where possible so the subsequent backend story can focus on emitting compliant finding citations.
- If browser binaries or sandbox permissions are required, wire them in the narrowest place that serves ux_auditor runs.
- If a fixture/example target is needed for smoke validation, use the smallest deterministic target already available in repo tooling.
- If no explicit current-state module exists for this factory/runtime area, document the concrete touched paths in the Dev Agent Record.

# References

- Direction: D100 Wire UX auditor to live browser sandbox
- PM tracker: D100 wire-ux-auditor-to-live-browser-sandbox
- Follow-on story dependency: D100 emit live-browser UX findings with objective evidence cites
- Follow-on story dependency: D100 document live-browser ux_auditor invocation and evidence

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

- [ ] Runtime wiring is limited to enabling browser-capable sandbox execution for ux_auditor.
- [ ] Browser launch path is exercised by an automated or repeatable smoke check.
- [ ] Evidence-emission semantics were not overbuilt in this infra slice.
- [ ] Any new dependency/bootstrap requirement is explicit in changed files or execution notes.
- [ ] Changes avoid unrelated app auth/frontend/backend behavior.

# Review Follow-ups

- None yet.
