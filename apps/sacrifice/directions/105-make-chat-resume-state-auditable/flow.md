# User flow

1. Flow: 009-chat-goal-creation/flow.md
2. Step: 6
3. Evidence: Under `text_run` without a live app session, the resume-on-return requirement (`chat session resumes from the last assistant message`) could not be verified because no local session storage, navigation, or restored assistant state was observable.
4. Suggestion: Add a runnable audit target or scripted fixture that exposes persisted chat-session state so resume behavior can be checked empirically.
