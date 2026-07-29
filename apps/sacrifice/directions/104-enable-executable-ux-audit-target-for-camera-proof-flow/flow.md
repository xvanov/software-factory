# User flow

1. Flow: 008-camera-capture-pipeline/flow.md
2. Step: 2
3. Evidence: App URL is unavailable in the provided runtime context (`Deploy: disabled`) and the scheduler transport is `text_run`, so the documented permission-denied branch (`"Camera access is required to submit this proof"`, `"Open settings"`, `"Cancel"`) could not be exercised or observed against a running target.
4. Suggestion: Provision the reserved live-browser sandbox path or a stable deploy URL so the camera permission flows can be replayed and verified end-to-end.
