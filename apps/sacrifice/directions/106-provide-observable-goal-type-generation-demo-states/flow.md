# User flow

1. Flow: 010-goal-type-generator/flow.md
2. Step: 6
3. Evidence: The status-banner progression (`queued` → `in progress` → `pull request open` → `merging`) depends on background factory updates, but the provided runtime has no live application endpoint or event stream, so the user-visible transition behavior could not be observed.
4. Suggestion: Expose a deterministic demo or staging flow for goal-type generation status updates so the audit can verify each banner transition and notification handoff.
