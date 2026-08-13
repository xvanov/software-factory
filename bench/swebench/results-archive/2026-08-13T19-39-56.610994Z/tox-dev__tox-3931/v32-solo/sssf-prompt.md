# tox-dev__tox-3931

## Problem

tox.toml Schema does not align with implementation for env deps property
## Issue

I am using the [Even Better TOML VS Code extension](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) for a small project, which uses [the tox SchemaStore schema](https://catalog.lintel.tools/schemas/schemastore/tox/) to validate tox.toml.
The [currently-deployed schema](https://raw.githubusercontent.com/tox-dev/tox/main/src/tox/tox.schema.json) specifies that the `env_run_base` tox.toml table property `deps` only accepts strings, but the tox CLI processes arrays of dependencies and requirements file arguments without issue, and using an array [is demonstrated in the tox documentation](https://tox.wiki/en/stable/reference/config.html#deps).
It appears tox is designed to treat this as either a string or an array, so the TOML configuration schema should reflect that.

<img width="787" height="389" alt="Image" src="https://github.com/user-attachments/assets/af1e5de3-c505-4d15-ac2a-5298a10ef261" />

## Environment

- OS: Any

This is not related to the tox application itself, but to the current and published schema for tox.toml

## Output of running tox

Not relevant to the bug, as this is related to the published TOML configuration schema, not the tox application.

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.tox-dev_1776_tox-3931@sha256:6c44571aa2f3c2e01be2ba54b3330efcb4b5ba0d00983aa4a309d27853804896 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/session/cmd/test_schema.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
