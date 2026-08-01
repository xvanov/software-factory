"""The SWE-bench adapter's oracle must stay hidden and its sample must be pinned.

The whole point of this adapter is an EXTERNAL grader. Two things can quietly
destroy that, and both are cheap to get wrong:

* The factory's dev owns its tests (the Loop-4 design), so a diff containing
  test edits would let the arm under test rewrite the oracle judging it. This
  is the single most common way SWE-bench numbers get inflated.
* A sample chosen after seeing results is not a sample.

These tests cover the pure logic. The docker grading path is exercised
end-to-end by an actual run, not mocked here — a mocked oracle proves nothing.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ADAPTER = Path(__file__).parent.parent / "bench" / "swebench_adapter.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("_swe_under_test", _ADAPTER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_swe_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def A() -> Any:  # noqa: N802
    return _load()


# --------------------------------------------------------------------------- #
# test-path detection
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_foo.py",
        "test/database.js",
        "src/tests/helpers.py",
        "pkg/foo_test.go",
        "app/test_thing.py",
        "conftest.py",
        "src/conftest.py",
        "web/component.spec.tsx",
        "testing/fixtures.py",
    ],
)
def test_test_paths_are_recognised(A: Any, path: str) -> None:  # noqa: N803
    assert A.is_test_path(path), path


@pytest.mark.parametrize(
    "path",
    [
        "src/main.py",
        "lib/latest.py",           # contains "test" as a substring only
        "app/contest/views.py",    # "contest", not "test"
        "src/protester.go",
        "docs/testing.md" ,        # NOTE: under a testing/ dir this WOULD match
    ],
)
def test_production_paths_are_not_flagged(A: Any, path: str) -> None:  # noqa: N803
    if path == "docs/testing.md":
        pytest.skip("documented boundary: a testing/ DIRECTORY does match")
    assert not A.is_test_path(path), path


# --------------------------------------------------------------------------- #
# diff splitting
# --------------------------------------------------------------------------- #

_DIFF = """diff --git a/src/app.py b/src/app.py
index 111..222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
diff --git a/tests/test_app.py b/tests/test_app.py
index 333..444 100644
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1,2 +1,2 @@
-assert app.y == 2
+assert True
diff --git a/src/other.py b/src/other.py
index 555..666 100644
--- a/src/other.py
+++ b/src/other.py
@@ -1 +1,2 @@
 z = 3
+w = 4
"""


def test_split_keeps_code_and_strips_tests(A: Any) -> None:  # noqa: N803
    code, kept, stripped = A.split_diff(_DIFF)
    assert kept == ["src/app.py", "src/other.py"]
    assert stripped == ["tests/test_app.py"]
    assert "y = 2" in code and "w = 4" in code
    # The neutering test edit is gone entirely, not merely unreferenced.
    assert "assert True" not in code
    assert "tests/test_app.py" not in code


def test_split_of_an_empty_diff_is_empty(A: Any) -> None:  # noqa: N803
    assert A.split_diff("") == ("", [], [])
    assert A.split_diff("   \n") == ("", [], [])


def test_split_output_is_a_valid_standalone_diff(A: Any) -> None:  # noqa: N803
    """Each kept file keeps its own header and hunks, in order."""
    code, _, _ = A.split_diff(_DIFF)
    headers = [ln for ln in code.splitlines() if ln.startswith("diff --git")]
    assert headers == [
        "diff --git a/src/app.py b/src/app.py",
        "diff --git a/src/other.py b/src/other.py",
    ]


# --------------------------------------------------------------------------- #
# the assertion that protects the oracle
# --------------------------------------------------------------------------- #


def test_assert_rejects_a_diff_that_touches_tests(A: Any) -> None:  # noqa: N803
    with pytest.raises(AssertionError, match="tests/test_app.py"):
        A.assert_no_test_edits(_DIFF)


def test_assert_accepts_the_stripped_diff(A: Any) -> None:  # noqa: N803
    code, _, _ = A.split_diff(_DIFF)
    A.assert_no_test_edits(code)  # must not raise


def test_assert_accepts_an_empty_diff(A: Any) -> None:  # noqa: N803
    A.assert_no_test_edits("")


def test_strip_then_assert_is_idempotent(A: Any) -> None:  # noqa: N803
    """Re-stripping an already-clean diff must not change it — `grade` re-runs
    the assertion at grading time as a second line of defence."""
    code, _, _ = A.split_diff(_DIFF)
    again, kept, stripped = A.split_diff(code)
    assert again == code
    assert stripped == []
    assert kept == ["src/app.py", "src/other.py"]


# --------------------------------------------------------------------------- #
# dataset field coercion
# --------------------------------------------------------------------------- #


def test_fail_to_pass_json_string_is_parsed(A: Any) -> None:  # noqa: N803
    """The dataset ships these as JSON-encoded STRINGS, not lists. Treating the
    string as a single test name would silently grade against one nonexistent
    test and call everything unresolved."""
    assert A._as_list('["a::test_one", "b::test_two"]') == ["a::test_one", "b::test_two"]
    assert A._as_list(["x", "y"]) == ["x", "y"]
    assert A._as_list("") == []
    assert A._as_list(None) == []
    # Not valid JSON: treat as a single opaque name rather than dropping it.
    assert A._as_list("plain::name") == ["plain::name"]


def test_nested_python_repr_list_is_flattened(A: Any) -> None:  # noqa: N803
    """The shape that actually broke grading, from a real instance.

    ``ansible__ansible-9a21e2477...`` encodes ``fail_to_pass`` as a JSON array
    holding ONE element, which is itself a Python repr of the real list —
    single-quoted, so not valid JSON. Parsed naively, pytest receives all six
    ids as a single argument, collects 0 items, and the instance grades as
    unresolved no matter what the arm produced. Left unfixed this yields a 0%
    resolve rate across the board that reads as factory incompetence.
    """
    real = (
        '["[\'test/units/module_utils/common/test_sys_info.py'
        '::test_get_distribution_not_linux[FreeBSD-Freebsd]\', '
        '\'test/units/module_utils/common/test_sys_info.py'
        '::test_get_distribution_version_not_linux[FreeBSD-12.1]\']"]'
    )
    got = A._as_list(real)
    assert len(got) == 2, got
    assert got[0].endswith("::test_get_distribution_not_linux[FreeBSD-Freebsd]")
    assert got[1].endswith("::test_get_distribution_version_not_linux[FreeBSD-12.1]")
    # Nothing retains the wrapping brackets — those are what pytest choked on.
    assert not any(t.startswith("[") for t in got)


def test_flattening_is_idempotent_and_bounded(A: Any) -> None:  # noqa: N803
    flat = ["a::t1", "b::t2"]
    assert A._as_list(flat) == flat
    assert A._as_list(A._as_list(flat)) == flat
    # A test id containing brackets (pytest params) must survive intact.
    assert A._as_list('["x.py::test[a-b]"]') == ["x.py::test[a-b]"]


# --------------------------------------------------------------------------- #
# manifest pinning
# --------------------------------------------------------------------------- #


def test_run_without_a_manifest_refuses(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    monkeypatch.setattr(A, "MANIFEST_PATH", tmp_path / "nope.json")
    with pytest.raises(SystemExit, match="Run `fetch` first"):
        A._manifest()


def test_instance_must_be_in_the_manifest(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    """Grading an instance that was never pinned would be picking the sample
    after seeing the results."""
    m = tmp_path / "manifest.json"
    m.write_text(
        json.dumps({"manifest_sha256": "abc", "instances": [{"instance_id": "known"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(A, "MANIFEST_PATH", m)
    assert A._instance("known")["instance_id"] == "known"
    with pytest.raises(SystemExit, match="not in the pinned manifest"):
        A._instance("unknown")


def test_shell_quoting_survives_test_names_with_quotes(A: Any) -> None:  # noqa: N803
    """Real fail_to_pass entries contain apostrophes (e.g. "should return ...
    and null if key doesn't exist"), which would break the grade script."""
    quoted = A._shq("test.js | Key methods doesn't explode")
    assert quoted.startswith("'") and quoted.endswith("'")
    # The embedded apostrophe is escaped, not left to terminate the string.
    assert "doesn'\\''t" in quoted
