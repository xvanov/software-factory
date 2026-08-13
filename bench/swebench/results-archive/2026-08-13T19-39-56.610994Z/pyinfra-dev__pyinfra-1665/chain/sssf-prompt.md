# pyinfra-dev__pyinfra-1665

## Problem

server.reboot fails to wait for the server to come back if _sudo_password is used
## Describe the bug

I'm seeing `server.reboot` crashing pyinfra after `delay` seconds like this:

```
--> Starting operation: NBDE client | Reboot to apply NBDE changes
    Traceback (most recent call last):
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/api/operations.py", line 106, in _run_host_op
    status = command.execute(state, host, connector_arguments)
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/api/command.py", line 237, in execute
    return self.function(state, host, *self.args, **self.kwargs)
           ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/operations/server.py", line 94, in wait_and_reconnect
    host.disconnect()  # make sure we are properly disconnected
    ~~~~~~~~~~~~~~~^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/api/host.py", line 429, in disconnect
    remove_any_sudo_askpass_file(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/connectors/util.py", line 238, in remove_any_sudo_askpass_file
    host.run_shell_command("rm -f {0}".format(sudo_askpass_path))
    ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/api/host.py", line 439, in run_shell_command
    return self.connector.run_shell_command(*args, **kwargs)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/connectors/ssh.py", line 419, in run_shell_command
    return_code, combined_output = execute_command_with_sudo_retry(
                                   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        self.host,
        ^^^^^^^^^^
        arguments,
        ^^^^^^^^^^
        execute_command,
        ^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/connectors/util.py", line 203, in execute_command_with_sudo_retry
    return_code, output = execute_command()
                          ~~~~~~~~~~~~~~~^^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/pyinfra/connectors/ssh.py", line 395, in execute_command
    stdin_buffer, stdout_buffer, stderr_buffer = self.client.exec_command(
                                                 ~~~~~~~~~~~~~~~~~~~~~~~~^
        actual_command,
        ^^^^^^^^^^^^^^^
        get_pty=_get_pty,
        ^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/paramiko/client.py", line 560, in exec_command
    chan = self._transport.open_session(timeout=timeout)
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/paramiko/transport.py", line 994, in open_session
    return self.open_channel(
           ~~~~~~~~~~~~~~~~~^
        "session",
        ^^^^^^^^^^
    ...<2 lines>...
        timeout=timeout,
        ^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/yacoob/workarea/homelab/.venv/lib/python3.14/site-packages/paramiko/transport.py", line 1088, in open_channel
    raise SSHException("SSH session not active")
paramiko.ssh_exception.SSHException: SSH session not active

    [vm-tentakl] Unexpected error in Python callback: SSHException('SSH session not active',)
```

This happens *only* if i have both `_sudo = True` and `_sudo_password` set. This doesn't happen when I have `_sudo = True` and no `_sudo_password` set and the user is allowed to run sudo without a need for password. 

As far as I can tell, this crash is related to the askpass file, and the sequence is as follows:

1. `reboot()` yields `FunctionCommand(remove_any_askpass_file)` — clears askpass path
2. `reboot()` yields `StringCommand("reboot")` — runs with sudo, re-creates askpass file
3. Host reboots, SSH connection dies
4. `reboot()` yields `FunctionCommand(wait_and_reconnect)` which after `sleep(delay)` calls: `host.disconnect()` → `remove_any_sudo_askpass_file()` → `host.run_shell_command("rm -f ...")` → `SSHException('SSH session not active')`

A clear and concise description of what the bug is.

## To Reproduce
```python
# group_data/all.py
_sudo = True
_sudo_password = "anything"

# deploy.py
from pyinfra.operations import server
server.reboot(name="Reboot", delay=20, reboot_timeout=300)
```

```shell
pyinfra my-host deploy.py
```


## Meta
```
    System: Linux
      Platform: Linux-6.19.9-200.fc43.x86_64-x86_64-with-glibc2.42
      Release: 6.19.9-200.fc43.x86_64
      Machine: x86_64
    pyinfra: v3.7
      click: v8.3.1
      distro: v1.9.0
      gevent: v25.9.1
      jinja2: v3.1.6
      packaging: v26.0
      paramiko: v3.5.1
      pydantic: v2.12.5
      python-dateutil: v2.9.0.post0
      typeguard: v4.5.1
      typing-extensions: v4.15.0
    Executable: /home/yacoob/workarea/homelab/.venv/bin/pyinfra
    Python: 3.14.3 (CPython, Clang 21.1.4 )
```
installed via `uv`.

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.pyinfra-dev_1776_pyinfra-1665@sha256:138a496547f392c77a1d472fd259e3c3fff6dd20bf5cba084335888857f395a3 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/test_connectors/test_util.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
