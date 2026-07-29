# Story

## Title
D001 show item counts in dashboard Items card and refresh on changes

## Slug
`d001-show-item-counts-in-dashboard-items-card-and-refresh-on`

## Scope
`frontend`

## Summary
Consume `items.count` in the web dashboard Items card, render the workspace-scoped counts next to the heading, suppress count text for the zero-items state, and keep the displayed counts current after add/complete/delete item actions without regressing the existing end-to-end journey.

# Acceptance Criteria

- `items.count` returns `{total, open, done}` for the caller's workspace only.
- A second workspace's items never affect the first workspace's numbers.
- The counts appear on the dashboard and update after adding, completing or
  deleting an item.
- The existing end-to-end journey still passes.

### Testable Claims (EARS)
AC1.1: WHEN the dashboard consumes `items.count`, THE web dashboard SHALL use `{total, open, done}` for the caller's workspace only.
AC2.1: WHEN the caller views dashboard item counts, THE web dashboard SHALL display numbers unaffected by a second workspace's items.
AC3.1: WHEN the dashboard renders and the workspace has items, THE Items card SHALL show the counts.
AC3.2: WHEN an item is added from the dashboard flow, THE displayed counts SHALL update.
AC3.3: WHEN an item is completed from the dashboard flow, THE displayed counts SHALL update.
AC3.4: WHEN an item is deleted from the dashboard flow, THE displayed counts SHALL update.
AC4.1: WHEN the existing end-to-end journey is executed, THE system SHALL still pass it.

# Tasks / Subtasks

- [ ] Locate the web dashboard Items card component and current item query/mutation wiring.
- [ ] Add client consumption of `items.count` via the existing tRPC client path used by the web dashboard.
- [ ] Render count text adjacent to the Items heading when `total > 0`.
- [ ] Suppress count text when `total === 0`.
- [ ] Format heading-adjacent text from `open` and `done` values.
- [ ] Ensure add-item success causes count data refresh.
- [ ] Ensure set-done success causes count data refresh.
- [ ] Ensure remove-item success causes count data refresh.
- [ ] Preserve existing item list and empty-state behavior.
- [ ] Add/update frontend tests covering visible counts and zero-items suppression.
- [ ] Add/update integration or E2E coverage for count refresh after add/complete/delete.
- [ ] Run the existing end-to-end journey and confirm no regression.

# Dev Notes

## Direction context

[flow.md: see first-story-slug Dev Notes for verbatim embed]

[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

## Acceptance criteria from direction (verbatim)

- `items.count` returns `{total, open, done}` for the caller's workspace only.
- A second workspace's items never affect the first workspace's numbers.
- The counts appear on the dashboard and update after adding, completing or
  deleting an item.
- The existing end-to-end journey still passes.

## Direction constraints

- Web dashboard only.
- Consume existing tRPC catch-all route; no new route file.
- No schema change, no migration, no new table.
- Out of scope: counting anything other than items.
- Out of scope: mobile app changes.
- Out of scope: pagination or filtering.

## Implementation notes

- Treat the backend `items.count` contract as a dependency from the prior backend story; do not redefine the API in frontend code beyond consuming its typed output.
- The zero-items presentation requirement is UI-specific: when `total === 0`, show no extra heading text rather than a `0 open · 0 done` string.
- Keep refresh behavior aligned with the existing dashboard item actions; use the established query invalidation/refetch pattern already present in the web app for item list freshness.
- The display requirement is scoped to the Items card heading area on the web dashboard only.

## Context pointers

No canonical context files were provided in this invocation. Derive implementation context from the direction anchors and repository code:

- `apps/web/src/app/api/trpc/[trpc]/route.ts`
- `packages/api/src/routers/items.ts`
- Dashboard page/component owning the web "Items" card
- Existing web tRPC hooks/utilities for items list/create/setDone/remove
- Existing E2E journey covering dashboard item CRUD

## Verbatim api_spec.md reference text relevant to frontend consumption

[api_spec.md: see <first-backend-story-slug> Dev Notes for verbatim embed]

# References

- Direction: D001 item-count-endpoint: org-scoped item counts on dashboard
- Router anchor: `packages/api/src/routers/items.ts`
- Existing tRPC route handler: `apps/web/src/app/api/trpc/[trpc]/route.ts`
- Story dependency: backend child story introducing `items.count`

# Dev Agent Record

## Agent Model Used

TBD

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
