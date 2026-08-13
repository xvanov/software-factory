# alibaba__opensandbox-816

## Problem

SECURITY: symbolic link within a whitelisted path that points to the host root directory `/`, and then request a mount using the symlink path.
The `allowed_host_paths` configuration option in OpenSandbox is intended to restrict sandbox containers to a whitelist of host paths that may be mounted. However, when validating paths, `_validate_host_volume` only uses `os.path.normpath` for lexical normalization and never calls `os.path.realpath` to resolve symbolic links.

An attacker can create a symbolic link within a whitelisted path that points to the host root directory `/`, and then request a mount using the symlink path. The lexical validation passes because the path begins with the whitelisted prefix, but Docker resolves the symbolic link when performing the bind mount, so the actual mounted path can be any host path chosen by the attacker.

This vulnerability remains exploitable even when the administrator has correctly configured the `allowed_host_paths` whitelist, rendering the security mechanism completely ineffective.

# FIXES
1. Add symbolic link detection in `ensure_valid_host_path`: check whether each intermediate path component is a symbolic link, and reject any path that contains symlinks.

2. Align the security validation logic for PVC volumes: `_validate_pvc_volume` already uses `os.path.realpath(strict=True)`, and host volumes should enforce the same standard.

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.alibaba_1776_opensandbox-816@sha256:eb2223e2f7957ad3f8bf3a69946fed4ca7b9abc309ec9c14f388786785d02ea0 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''server/tests/test_docker_service.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
