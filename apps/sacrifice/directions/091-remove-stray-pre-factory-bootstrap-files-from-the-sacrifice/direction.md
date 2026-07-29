---
title: Remove stray pre-factory bootstrap files from the sacrifice repository
type: chore
priority: p2
explore: true
created_at: '2026-07-19T05:14:41.518833+00:00'
---

<!-- Optional sibling files: flow.md (user flow), api_spec.md (API contract), artifacts/ (binaries) -->

# Remove stray pre-factory bootstrap files from the sacrifice repository

## Why

Several tracked files are dead weight from a pre-factory bootstrap phase and confuse readers. WHAT TO DO: remove these tracked files from the sacrifice repo: HANDOFF.md (stale one-off handoff note), activity.md (unmaintained dev-session log), ralph.sh, opencode.json, .opencode/ (early 'ralph'/OpenCode looping-agent artifacts predating the factory), PROMPT.md, and the in-repo stories/ directory (out of sync + duplicate-numbered vs the factory's canonical software-factory/apps/sacrifice/stories/; not referenced by any backend/test code). Verify with grep that nothing in backend/ or frontend/ imports/references them before removing. SCOPE: deletions + any strictly-required reference cleanup only — do NOT reformat or restructure unrelated code. The test suite and `make smoke` must still pass after removal.

## Acceptance Criteria

- [ ] Listed stray files are removed (git ls-files no longer lists them).
- [ ] grep confirms no backend/frontend code references the removed files.
- [ ] Backend pytest suite and `make smoke` still pass after removal.
- [ ] Diff is deletions (+ minimal necessary reference cleanup) only — no unrelated reformatting.
