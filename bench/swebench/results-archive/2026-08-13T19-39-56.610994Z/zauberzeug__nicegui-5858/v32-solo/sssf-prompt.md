# zauberzeug__nicegui-5858

## Problem

communicate terminal size to pty after fit on xterm
### First Check

- [x] I added a very descriptive title here.
- [x] This is not a security issue (those should be reported via the [security advisory](https://github.com/zauberzeug/nicegui/security/advisories/new) instead).
- [x] This is not a Q&A. I am sure something is wrong with NiceGUI or its documentation.
- [x] I used the GitHub search to find a similar [issue](https://github.com/zauberzeug/nicegui/issues) and came up empty.

### Example Code

```python

```

### Description

More like a feature request than a bug.

Using the `ui.xterm` example [from this same repo](https://github.com/zauberzeug/nicegui/blob/main/examples/xterm/main.py) I found that the terminal cannot correctly detect its own size:

```bash
$ python
>>> import os
>>> os.get_terminal_size()
os.terminal_size(columns=0, lines=0)
```

the docstring of the xterm component [mentions](https://github.com/zauberzeug/nicegui/blob/main/nicegui/elements/xterm/xterm.py#L41) that there is a `fit` method but it resizes the `xterm` in the client to the container, while the `pty` remains unaware of the size change.

I found that that the terminal size can be communicated by modifying the example like this:

```python

terminal = ui.xterm({"cols": 130, "rows": 40})
[...]
if pty_pid == pty.CHILD:
    os.execv(
        "/bin/bash", ("bash",)
    )  # child process of the fork gets replaced with "bash"
else:
    winsize = struct.pack("HHHH", 40, 130, 0, 0)
    fcntl.ioctl(pty_fd, termios.TIOCSWINSZ, winsize)
```
that is, first I pass 140x30 to the frontend component and then send the control codes to the terminal file itself so it is in sync.

I tested it and it works with the `os.terminal_size` function and also with a more sophisticated TUI app.

Is there a way to automate this and let the terminal always know its own size upon `fit` (and perhaps once at initialization)? I am not familiar with the internals of nicegui to do it, but it seems an useful feature to have.

### NiceGUI Version

3.8.0

### Python Version

3.14

### Browser

Firefox

### Operating System

Linux

### Additional Context

_No response_

## Additional acceptance criteria
- `ui.xterm()` exposes an `on_resize(handler)` API for terminal resize events.
- Resize handlers receive an event object with integer `cols` and `rows` attributes matching the fitted terminal size.
- Calling `fit()` after the terminal size changes emits the resize event with the current dimensions.
- Existing bell and data event behavior remains unchanged; resize handlers are not called unless a resize occurs.


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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.zauberzeug_1776_nicegui-5858@sha256:0774c1c1d9caf26fc590c840482c262c82a76ccc5150c9dd58501114371bc2d2 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/test_xterm.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
