# hkuds__openharness-217

## Problem

[Bug]: Windows browser-open in DeviceCodeFlow uses shell=True with externally-supplied URL
### What happened?

`DeviceCodeFlow._try_open_browser` in `src/openharness/auth/flows.py` opens the browser on Windows by calling:

```python
subprocess.Popen(
    ["start", "", url],
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

Because `shell=True` routes the call through `cmd.exe`, characters like `&`, `|`, and `^` inside the URL are interpreted as **command separators**, not as URL data. The `url` argument here is **externally supplied** — it is the `verification_uri` returned by the GitHub device-flow endpoint, or for users who pass `enterprise_url` to the flow, it is a value derived from a user-configured (and potentially compromised) GitHub Enterprise host.

A device-flow endpoint that returned `verification_uri` like:

```
https://github.com/login/device&calc.exe
```

…would launch `calc.exe` alongside the browser the next time a user ran `oh setup` / Copilot login on Windows.

The macOS and Linux/WSL branches in the same function correctly pass argv lists with `shell=False`, so this only affects Windows.

### Steps to reproduce

The call site is reached during any GitHub OAuth device-code login (`oh setup`, Copilot login). To demonstrate the underlying primitive on a Windows machine without a real malicious server, run:

```python
# windows-repro.py — run on Windows with `python windows-repro.py`
import subprocess

malicious_url = "https://example.com&calc.exe"
subprocess.Popen(
    ["start", "", malicious_url],
    shell=True,
)
```

This both opens the browser **and** launches Calculator. Replace `calc.exe` with `cmd /c <anything>` to demonstrate arbitrary command execution.

To trigger it through OpenHarness end-to-end you would need a GitHub Enterprise endpoint (or a man-in-the-middle on the device-flow response) that returns a poisoned `verification_uri`; the call chain is `oh auth ... -> DeviceCodeFlow.run -> request_device_code -> _try_open_browser(dc.verification_uri)`.

### Expected behavior

A URL returned by the device-flow endpoint should never be parsed as a shell command line. The Windows branch should use a launcher that does not go through `cmd.exe` — e.g. `os.startfile(url)`, which calls `ShellExecuteW` directly and hands the full URL to the registered protocol handler verbatim. Non-`http(s)` schemes should also be rejected up front so `file:` / `javascript:` / a bare executable name cannot reach the launcher.

### Environment

- File: `src/openharness/auth/flows.py:84-91`
- Affected platform: Windows (any Python)
- Reachable code paths: `oh setup` (Copilot/GitHub OAuth), any caller of `DeviceCodeFlow` with a non-default `enterprise_url`, and `BrowserFlow` (which delegates to `DeviceCodeFlow._try_open_browser`).

### Relevant logs or screenshots

n/a — the bug is in the call construction itself.

---

Happy to send a PR replacing the Windows branch with `os.startfile` and adding a scheme guard plus regression tests for the four platform branches.

## Definition of done

Change the production code in this repository so the described behaviour is
correct.

Work exactly as you normally do: write tests that express the required
behaviour, then make them pass. A separate held-out test suite, written by the
project's maintainers and which you will never see, is the final judge.

## Where to put tests

Put new tests in the files or directories the test command below already
targets, so your own runs execute them.

Your test edits are removed from the diff before the held-out suite runs, so
they cannot affect the verdict either way — they are your feedback loop, not
the grade. Only your production-code changes are judged. This means a test
that merely asserts whatever your implementation happens to do buys nothing:
make the tests encode what the TASK requires.

## Running the tests

This checkout has NO dependencies installed, so a bare `pytest` fails with
`ModuleNotFoundError`. Run this exact command from the repo root — it executes
inside an image that has the dependencies, with your working tree mounted so it
tests YOUR edits:

```
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.hkuds_1776_openharness-217@sha256:ad0997cf2e90f0a31f3e6f8fd5cba18ced7f364ae3a62bd59f4c9e1d88b7678d -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/test_auth'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
