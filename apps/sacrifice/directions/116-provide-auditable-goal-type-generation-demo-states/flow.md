# User flow

1. Flow: 010-goal-type-generator/flow.md
2. Step: 6
3. Evidence: The status banner progression 'queued' → 'in progress' → 'pull request open' → 'merging' depends on background factory events, but with deploy disabled and text_run transport there is no live endpoint or event stream to observe these user-visible transitions.
4. Suggestion: Expose a deterministic demo or staging path for goal-type generation progress so each banner transition and notification handoff can be audited.
