# harumiweb__exstruct-113

## Problem

Package import optimization: lighten exstruct.__init__ and introduce lazy exports
### Before submitting

- [x] I understand that this project is maintained in spare time and that not all issues may result in changes.

### Description

### Summary

`exstruct/__init__.py` currently re-exports multiple public APIs for convenience.
However, this also makes `import exstruct` relatively heavy, and in the CLI path it contributes to early loading of transitive dependencies through imports such as `from exstruct import process_excel`.

To reduce package import overhead, we should **lighten `exstruct/__init__.py` and introduce lazy exports for public APIs**.

### Problem

Heavy imports in `__init__.py` cause several issues:

* `import exstruct` itself becomes slower
* the CLI pays broad import cost just to access `process_excel`
* convenience re-exports negatively impact startup performance
* Python API consumers also pay unnecessary initial import cost

This becomes especially costly when imports eventually pull in dependencies such as `pandas`, `numpy`, `xlwings`, or rendering-related modules.

### Proposal

Adopt one of the following approaches, or a combination of them:

#### Option 1: Wrapper-function exports

Expose public functions such as `process_excel` via thin wrappers in `__init__.py`, and import the real implementation inside the wrapper body.

#### Option 2: PEP 562 lazy exports

Use module-level `__getattr__` so symbols are imported only when accessed.

#### Option 3: Reduce re-export surface

Keep `__init__.py` minimal and require heavier APIs to be imported from submodules directly.

### Expected benefits

* Faster `import exstruct`
* Lower startup cost for CLI code paths that currently rely on `from exstruct import process_excel`
* Clearer package boundaries
* Better import-time performance for Python API consumers

### Scope

Potential files:

* `src/exstruct/__init__.py`
* possibly `src/exstruct/engine.py`
* possibly related render/core import-path cleanup

### Acceptance criteria

* `import exstruct` shows measurable improvement in import time
* Public API compatibility is preserved as much as possible
* CLI startup cost related to importing `process_excel` is reduced
* Type-checking and documentation tooling remain usable with acceptable impact

### Notes

This change benefits not only the CLI but also Python API users, so it has broader architectural value.
However, because it touches the public package surface, it should be handled a bit more carefully than A/B.


### Minimal example (optional)

_No response_

### Additional notes (optional)

_No response_

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.harumiweb_1776_exstruct-113@sha256:a3234ba6d5ca57a07137b6e70c870111a00d4ca638329745ef65bde1a75c865e -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/cli/test_cli_lazy_imports.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
