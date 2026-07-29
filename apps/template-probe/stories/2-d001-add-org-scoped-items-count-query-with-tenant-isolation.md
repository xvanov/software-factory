# Story

## Title
D001 add org-scoped items.count query with tenant isolation tests

## Slug
`d001-add-org-scoped-items-count-query-with-tenant-isolation`

## Scope
`backend`

## Summary
Add `items.count` to `packages/api/src/routers/items.ts` as an `orgProcedure` query with no input and `{ total, open, done }` output, implemented with database-side counting scoped to `ctx.organizationId`, and cover tenant isolation plus count-splitting behavior with tests.

# Acceptance Criteria

- `items.count` returns `{total, open, done}` for the caller's workspace only.
- A second workspace's items never affect the first workspace's numbers.
- The counts appear on the dashboard and update after adding, completing or
  deleting an item.
- The existing end-to-end journey still passes.

### Testable Claims (EARS)
AC1.1: WHEN `items.count` is invoked, GIVEN a caller authenticated into a workspace, THE `items.count` procedure SHALL return an object containing `total`, `open`, and `done` for the caller's workspace only.
AC2.1: WHEN items exist in a second workspace, GIVEN `items.count` is invoked by a caller from the first workspace, THE `items.count` procedure SHALL exclude the second workspace's items from the first workspace's returned numbers.
AC3.1: UNTESTABLE-AS-WRITTEN — dashboard rendering and update triggers are frontend behavior outside this backend story's implementation scope.
AC4.1: WHEN the existing end-to-end journey is executed after this change, THE system SHALL continue to pass that journey.

# Tasks / Subtasks

- [ ] Add `items.count` query to `packages/api/src/routers/items.ts`
- [ ] Use `orgProcedure`
- [ ] Accept no input
- [ ] Filter all counts by `ctx.organizationId`
- [ ] Return `{ total, open, done }`
- [ ] Keep `total === open + done`
- [ ] Perform counting in the database layer
- [ ] Do not fetch rows for JavaScript-side counting
- [ ] Do not modify `items.list`, `items.create`, `items.setDone`, or `items.remove`
- [ ] Add backend tests covering per-workspace isolation
- [ ] Add backend tests covering `open` vs `done` split
- [ ] Add backend tests covering unchanged auth/org failure behavior
- [ ] Run existing relevant end-to-end journey to confirm no regression

# Dev Notes

## Flow
[flow.md: not provided]

## API Spec
# API contract — items.count

One new tRPC procedure. No schema change, no new table, no migration.

## `items.count`

Transport — tRPC over HTTP, which is what the browser actually issues:

```
GET /api/trpc/items.count
```

A tRPC *query* is served by the `GET` handler in
`apps/web/src/app/api/trpc/[trpc]/route.ts`; batched calls arrive as
`GET /api/trpc/items.count,items.list?batch=1&input=...`. There is no new route
file and no new HTTP endpoint to register — the existing catch-all serves it.

Responses are the standard tRPC envelope: `200` with
`{"result":{"data":{"json":{…}}}}` on success, `200` with an `error` member and a
JSON-RPC code on failure (tRPC does not map procedure errors onto HTTP status
codes by default).

- Router: `packages/api/src/routers/items.ts`
- Kind: **query** (hence `GET`, not `POST`)
- Procedure builder: `orgProcedure` (NOT `protectedProcedure`) — it must receive
  `ctx.organizationId` and filter on it.
- Input: none.

Output:

```ts
{
  total: number;  // every item in the caller's workspace
  open:  number;  // done === false
  done:  number;  // done === true
}
```

`total` always equals `open + done`.

## Implementation note

Use a single grouped query or two `count` calls scoped by `organizationId`; do not
fetch rows and count in JavaScript, which reads the whole table to produce three
integers.

## Errors

| Condition | Result |
|---|---|
| No session | `UNAUTHORIZED`, as every other procedure in this router |
| Session with no resolvable organization | `FORBIDDEN` |

## Explicitly unchanged

- No change to `items.list`, `items.create`, `items.setDone`, `items.remove`.
- No new environment variable, dependency or database column.

## Context Pointers

No canonical context files were provided in this invocation. Use direction anchors directly:
- `packages/api/src/routers/items.ts`
- `apps/web/src/app/api/trpc/[trpc]/route.ts`

## Direction Acceptance Criteria (verbatim)

- `items.count` returns `{total, open, done}` for the caller's workspace only.
- A second workspace's items never affect the first workspace's numbers.
- The counts appear on the dashboard and update after adding, completing or
  deleting an item.
- The existing end-to-end journey still passes.

## Direction Constraints

- No schema change, no migration, no new route file.
- Must be `orgProcedure`.
- Must filter on `ctx.organizationId`.
- Web dashboard consumption is out of scope for this story.
- Out of scope: counting anything other than items.
- Out of scope: mobile app changes.
- Out of scope: pagination or filtering.

# References

- Direction: `D001 item-count-endpoint: org-scoped item counts on dashboard`
- Router anchor: `packages/api/src/routers/items.ts`
- tRPC route anchor: `apps/web/src/app/api/trpc/[trpc]/route.ts`
- Story dependency context: frontend story consumes this contract after backend lands

# Dev Agent Record

## Implementation Notes
- Pending

## Files Touched
- Pending

## Commands Run
- Pending

## Test Evidence
- Pending

# Senior Developer Review

- Pending

# Review Follow-ups

- Pending
