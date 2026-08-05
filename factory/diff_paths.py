"""ONE path classifier for "is this file part of the oracle, or the fix?".

Two subsystems have to answer that question and they must never disagree:

* ``bench/swebench_adapter.py`` strips test edits out of a prediction before
  the hidden suite grades it, and REFUSES a prediction that edits a pytest
  collection channel;
* the ``production-tree-changed`` merge gate (``factory/chain/gates/``) blocks
  a story whose diff contains no production-code change at all.

The bench harness owned these regexes first and they were measured against
real pytest behaviour (see the comments below). They live here so the gate
reuses the SAME definition instead of growing a second, drifting one — a
divergence would mean the benchmark and the chain disagree about what a
"production change" is, and the number the benchmark reports would stop
describing the thing the chain gates on.

Definitions
-----------
* **test path** — test code, and the fixtures that shape it (``conftest.py``).
* **collection channel** — a file that decides WHICH tests run, or WHETHER
  they run, without being test code.
* **production path** — anything else. Docs, config that is not a collection
  channel, and source all count: this predicate answers "did the arm change
  something other than the oracle", not "is this file interesting".

There is a THIRD, narrower test-path matcher in ``factory/chain/branch.py``
(``is_test_file`` / ``_TEST_FILE_PATTERNS``). It is deliberately left alone:
it drives the legacy "dev must not modify frozen tests" diff check, and
widening it would change unrelated enforcement. Do not add a fourth.
"""

from __future__ import annotations

import re

# A tests?/ or test/ directory anywhere, test_foo.py, foo_test.go, conftest.py
# (fixtures shape the oracle too), *.spec.tsx, a testing/ directory.
_TEST_PATH = re.compile(
    r"(^|/)tests?(/|$)"           # a tests/ or test/ directory anywhere
    r"|(^|/)test_[^/]+$"          # test_foo.py
    r"|_test\.[a-z]+$"            # foo_test.go
    r"|(^|/)conftest\.py$"        # pytest fixtures shape the oracle too
    r"|\.spec\.[jt]sx?$"
    r"|(^|/)testing(/|$)"
)

# Files that decide WHICH tests run and WHETHER they run, without being test
# files themselves. ``_TEST_PATH`` matches test code; these are the collection
# and auto-import channels that reach the same outcome sideways:
#
#   * ``pyproject.toml`` / ``setup.cfg`` / ``tox.ini`` / ``pytest.ini`` —
#     ``[tool.pytest.ini_options] addopts``, ``-p <plugin>``, markers,
#     ``collect_ignore``;
#   * ``setup.py`` / ``noxfile.py`` — run at build/test time;
#   * ``sitecustomize.py`` / ``usercustomize.py`` / ``*.pth`` — imported by
#     the interpreter itself, before pytest starts;
#   * ``*pytest*plugin*.py`` — an entry-point plugin.
#
# Measured against real pytest: a root ``_fixup.py`` with
# ``pytest_collection_modifyitems`` marking every item skipped plus
# ``addopts = "-p _fixup"`` makes ``python -m pytest <ids>`` exit 0 with
# "2 skipped". Under exit-code grading that was RESOLVED. The plugin file
# itself is ordinary production-looking code, so the CONFIG edit is the
# chokepoint worth refusing on.
_COLLECTION_CHANNEL = re.compile(
    r"(^|/)(pyproject\.toml|setup\.cfg|tox\.ini|pytest\.ini|setup\.py"
    r"|noxfile\.py|sitecustomize\.py|usercustomize\.py|conftest\.py)$"
    r"|\.pth$"
    r"|(^|/)[^/]*pytest[^/]*plugin[^/]*\.py$"
    r"|(^|/)[^/]*plugin[^/]*pytest[^/]*\.py$"
)


def _normalize(path: str) -> str:
    """``a/b`` form, no leading ``./``, backslashes folded to ``/``."""
    norm = path.strip().replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.lstrip("/")


def is_test_path(path: str) -> bool:
    """True for test code (and the fixtures that shape it)."""
    return bool(_TEST_PATH.search(_normalize(path)))


def is_collection_channel_path(path: str) -> bool:
    """True for a file that can change which tests run, or whether they run."""
    return bool(_COLLECTION_CHANNEL.search(_normalize(path)))


def is_production_path(path: str) -> bool:
    """True when changing ``path`` changes the code under test.

    Neither a test path nor a collection channel. A story whose whole diff is
    test files plus ``pyproject.toml`` changed no production code, however many
    lines it moved.
    """
    norm = _normalize(path)
    if not norm:
        return False
    return not is_test_path(norm) and not is_collection_channel_path(norm)


def production_paths(paths: list[str]) -> list[str]:
    """The subset of ``paths`` that is production code, order preserved."""
    return [p for p in paths if is_production_path(p)]
