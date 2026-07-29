# User flow

1. Flow: 008-camera-capture-pipeline/flow.md
2. Step: 2
3. Evidence: Deploy is disabled and scheduler transport is text_run, so the permission-denied branch for getByRole('button', { name: 'Record proof' }) could not be exercised against a running app; expected copy 'Camera access is required to submit this proof', 'Open settings', and 'Cancel' was not observable.
4. Suggestion: Provision a stable live audit target with browser/device permissions enabled so the camera permission-denied path can be replayed and verified end-to-end.
