# User flow

1. Flow: 009-chat-goal-creation/flow.md
2. Step: 6
3. Evidence: Under text_run with no live app session, the requirement that chat resumes from the last assistant message after leaving and returning could not be observed; no navigation state, local session storage, or restored assistant message was available to inspect.
4. Suggestion: Provide a runnable audit fixture or live app target that preserves and exposes chat session state across navigation so resume behavior can be checked empirically.
