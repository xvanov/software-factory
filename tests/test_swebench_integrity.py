"""Integrity hardening for the SWE-bench harness.

Every test here is an EXPLOIT first and a regression second. The harness's job
is to be un-gameable by the arm it measures, and the four ways it was gameable
were each fail-OPEN: an unparseable diff header merged a test edit into a kept
code block, a pytest-collection config channel escaped the test strip, a
skipped test graded as a pass, and a wiped state root audited clean.

Written against the pure logic — the docker grading path is exercised by a real
run, and a mocked oracle proves nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ADAPTER = Path(__file__).parent.parent / "bench" / "swebench_adapter.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("_swe_integrity_under_test", _ADAPTER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_swe_integrity_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def A() -> Any:  # noqa: N802
    return _load()


@pytest.fixture(autouse=True)
def _isolate_bench_store_paths(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No test may ever touch the REPO's pinned bench artifacts.

    Same guard as ``test_swebench_adapter.py`` and for the same reason: a test
    that wrote its fixture record over the committed ``oracle.json.z`` once
    invalidated a whole live sweep AFTER the model spend.
    """
    if "A" not in request.fixturenames:
        return
    a = request.getfixturevalue("A")
    monkeypatch.setattr(a, "MANIFEST_PATH", tmp_path / "isolated-manifest.json")
    monkeypatch.setattr(a, "ORACLE_PATH", tmp_path / "isolated-oracle.json.z")
    monkeypatch.setattr(a, "SELFTEST_LOG_DIR", tmp_path / "isolated-selftest-logs", raising=False)
    monkeypatch.setenv("SWEBENCH_WORK_ROOT", str(tmp_path / "isolated-work"))


# --------------------------------------------------------------------------- #
# defect 4 — _DIFF_HEADER was fail-OPEN on any path git had to quote
# --------------------------------------------------------------------------- #
#
# `^diff --git a/(\S+) b/(\S+)$` cannot match either form git actually emits
# for an awkward path:
#
#   diff --git a/tests dir/test_a b.py b/tests dir/test_a b.py   (\S+ can't span a space)
#   diff --git "a/test_\303\247.py" "b/test_\303\247.py"          (C-quoted, core.quotePath)
#
# and `split_diff` appended an unmatched line to the PREVIOUS block. So the
# test file's header and hunks merged into a kept code block, survived the
# strip, and survived `assert_no_test_edits` — which uses the same regex.

_SPACED_TEST_EDIT = (
    "diff --git a/src/app.py b/src/app.py\n"
    "index 111..222 100644\n"
    "--- a/src/app.py\n"
    "+++ b/src/app.py\n"
    "@@ -1 +1,2 @@\n"
    " x = 1\n"
    "+y = 2\n"
    "diff --git a/tests dir/test_a b.py b/tests dir/test_a b.py\n"
    "new file mode 100644\n"
    "index 000..333\n"
    "--- /dev/null\n"
    "+++ b/tests dir/test_a b.py\n"
    "@@ -0,0 +1 @@\n"
    "+assert True  # neutered oracle\n"
)

_QUOTED_TEST_EDIT = (
    "diff --git a/src/app.py b/src/app.py\n"
    "index 111..222 100644\n"
    "--- a/src/app.py\n"
    "+++ b/src/app.py\n"
    "@@ -1 +1,2 @@\n"
    " x = 1\n"
    "+y = 2\n"
    'diff --git "a/tests/test_\\303\\247.py" "b/tests/test_\\303\\247.py"\n'
    "new file mode 100644\n"
    "index 000..333\n"
    "--- /dev/null\n"
    '+++ "b/tests/test_\\303\\247.py"\n'
    "@@ -0,0 +1 @@\n"
    "+assert True  # neutered oracle\n"
)


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        (_SPACED_TEST_EDIT, "tests dir/test_a b.py"),
        (_QUOTED_TEST_EDIT, "tests/test_ç.py"),
    ],
    ids=["space-in-path", "c-quoted-path"],
)
def test_awkward_paths_are_parsed_and_stripped(A: Any, diff: str, expected: str) -> None:  # noqa: N803
    """The exploit: a test edit git had to quote must not reach the graded diff."""
    code, kept, stripped = A.split_diff(diff)
    assert stripped == [expected]
    assert kept == ["src/app.py"]
    assert "neutered oracle" not in code
    A.assert_no_test_edits(code)  # must not raise


@pytest.mark.parametrize(
    "diff",
    [_SPACED_TEST_EDIT, _QUOTED_TEST_EDIT],
    ids=["space-in-path", "c-quoted-path"],
)
def test_assert_no_test_edits_sees_awkward_paths(A: Any, diff: str) -> None:  # noqa: N803
    """Grade-time belt-and-braces must catch what run-time strip would have."""
    with pytest.raises(AssertionError, match="test"):
        A.assert_no_test_edits(diff)


def test_a_header_the_parser_cannot_classify_is_refused(A: Any) -> None:  # noqa: N803
    """FAIL CLOSED: an unclassifiable header refuses the row, never merges.

    A RENAME whose paths both contain a ``b/`` fragment is genuinely ambiguous
    — the header alone cannot be split. Refusing is the only safe answer; the
    old code silently glued the block onto the previous file's diff.
    """
    bad = (
        "diff --git a/src/app.py b/src/app.py\n"
        "@@ -1 +1 @@\n"
        "-x\n+y\n"
        "diff --git a/o ld b/x.py b/n ew b/x.py\n"
        "@@ -0,0 +1 @@\n"
        "+import evil\n"
    )
    with pytest.raises(A.DiffRefused, match="cannot be parsed"):
        A.split_diff(bad)
    with pytest.raises(A.DiffRefused, match="cannot be parsed"):
        A.assert_no_test_edits(bad)


@pytest.mark.parametrize(
    "header",
    [
        "diff --git nonsense",
        "diff --git a/only-one-path.py",
        'diff --git "a/unterminated b/x.py',
        "diff --git src/a.py src/b.py",          # missing a/ b/ prefixes
        'diff --git "a/bad\\9escape.py" "b/x.py"',
    ],
)
def test_malformed_headers_are_refused(A: Any, header: str) -> None:  # noqa: N803
    with pytest.raises(A.DiffRefused):
        A.split_diff(header + "\n@@ -0,0 +1 @@\n+x\n")


def test_ordinary_diffs_still_split_unchanged(A: Any) -> None:  # noqa: N803
    """Regression: the whole committed corpus must parse exactly as before."""
    diff = (
        "diff --git a/src/app.py b/src/app.py\n"
        "@@ -1 +1 @@\n-x\n+y\n"
        "diff --git a/tests/test_app.py b/tests/test_app.py\n"
        "@@ -1 +1 @@\n-a\n+b\n"
        "diff --git a/src/other.py b/src/other.py\n"
        "@@ -1 +1 @@\n-z\n+w\n"
    )
    code, kept, stripped = A.split_diff(diff)
    assert kept == ["src/app.py", "src/other.py"]
    assert stripped == ["tests/test_app.py"]
    assert "+b" not in code


def test_rename_of_a_plain_path_is_parsed(A: Any) -> None:  # noqa: N803
    code, kept, stripped = A.split_diff(
        "diff --git a/src/old.py b/src/new.py\n"
        "similarity index 100%\n"
        "rename from src/old.py\n"
        "rename to src/new.py\n"
    )
    assert kept == ["src/new.py"]
    assert stripped == []
    assert code.startswith("diff --git a/src/old.py b/src/new.py")


# --------------------------------------------------------------------------- #
# defect 3 — the pytest-collection config and auto-import channels
# --------------------------------------------------------------------------- #
#
# Measured exploit (verified locally against real pytest): a root `_fixup.py`
# with `pytest_collection_modifyitems` marking every item skipped, plus
# `[tool.pytest.ini_options] addopts = "-p _fixup"` in pyproject.toml, makes
# `python -m pytest <ids>` exit 0 with "2 skipped" — which the exit-code
# grader (defect 2) reads as RESOLVED. Neither file is a test path, so the
# strip kept both.

_CONFIG_CHANNEL_PATHS = [
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "setup.py",
    "noxfile.py",
    "sitecustomize.py",
    "usercustomize.py",
    "src/sitecustomize.py",
    "any/where/foo.pth",
    "mypkg/_my_pytest_plugin.py",
    "conftest.py",
    "src/conftest.py",
]


@pytest.mark.parametrize("path", _CONFIG_CHANNEL_PATHS)
def test_collection_config_channels_are_recognised(A: Any, path: str) -> None:  # noqa: N803
    assert A.is_collection_channel_path(path), path


@pytest.mark.parametrize(
    "path",
    [
        "src/main.py",
        "src/plugin.py",              # a plugin, but not a pytest one
        "docs/pyproject.toml.j2",     # template, not the file
        "src/setup_helpers.py",
        "pkg/path.py",                # ".pth" only as a suffix, not "path.py"
        "requirements.txt",
    ],
)
def test_ordinary_paths_are_not_collection_channels(A: Any, path: str) -> None:  # noqa: N803
    assert not A.is_collection_channel_path(path), path


def test_a_prediction_touching_pyproject_is_refused(A: Any) -> None:  # noqa: N803
    """The exploit: addopts + a root plugin skipping everything.

    Refusing beats stripping: stripping a config edit could break an otherwise
    valid patch, and silently grading a half-patch is the proxy != real class.
    """
    exploit = (
        "diff --git a/src/app.py b/src/app.py\n"
        "@@ -1 +1 @@\n-x\n+y\n"
        "diff --git a/pyproject.toml b/pyproject.toml\n"
        "@@ -1,2 +1,4 @@\n"
        " [tool.pytest.ini_options]\n"
        '+addopts = "-p _fixup"\n'
        "diff --git a/_fixup.py b/_fixup.py\n"
        "@@ -0,0 +1,4 @@\n"
        "+import pytest\n"
        "+def pytest_collection_modifyitems(items):\n"
        "+    for i in items:\n"
        '+        i.add_marker(pytest.mark.skip("fixup"))\n'
    )
    with pytest.raises(A.DiffRefused) as exc:
        A.split_diff(exploit)
    assert "pyproject.toml" in exc.value.paths
    assert exc.value.paths == ["pyproject.toml"]


def test_conftest_stays_a_strip_not_a_refusal(A: Any) -> None:  # noqa: N803
    """conftest.py is a TEST path — the long-standing behaviour is to strip it.

    It is also a collection channel, so the two rules overlap; the test-path
    rule must win or every conftest edit would start refusing rows that used
    to grade fine.
    """
    code, kept, stripped = A.split_diff(
        "diff --git a/src/app.py b/src/app.py\n@@ -1 +1 @@\n-x\n+y\n"
        "diff --git a/conftest.py b/conftest.py\n@@ -0,0 +1 @@\n+import pytest\n"
    )
    assert stripped == ["conftest.py"]
    assert kept == ["src/app.py"]


def test_refusal_can_be_disabled_for_the_gold_patch(A: Any) -> None:  # noqa: N803
    """The maintainers' own fix legitimately edits setup.py; it is not an arm.

    Measured: 0 of the 20 pinned oracle records' gold/test patches touch a
    collection channel today, so this path is belt-and-braces — but a future
    dataset row must not make the CONTROL refuse itself.
    """
    code, kept, stripped = A.split_diff(
        "diff --git a/setup.py b/setup.py\n@@ -1 +1 @@\n-x\n+y\n",
        refuse_collection_channels=False,
    )
    assert kept == ["setup.py"]
    assert stripped == []
    assert "+y" in code


# --------------------------------------------------------------------------- #
# defect 2 — grading was exit-code based, so SKIPPED counted as PASS
# --------------------------------------------------------------------------- #
#
# Verified against real pytest: with a plugin skipping every item,
# `python -m pytest -q <two ids>` prints "2 skipped" and exits 0. The grade
# script's `if ! python -m pytest ...; then fail=1; fi` therefore emitted
# RESOLVED. The official SWE-bench harness requires an explicit PASSED per
# node id, which is what `_parse_node_outcomes` + `evaluate_node_coverage` do.

_ALL_SKIPPED = """\
=========================== short test summary info ============================
SKIPPED [2] tests/test_x.py: fixup
2 skipped in 0.09s
"""

_ALL_PASSED = """\
=========================== short test summary info ============================
PASSED tests/test_x.py::test_a
PASSED tests/test_x.py::test_b
2 passed in 0.08s
"""


def test_all_skipped_is_not_a_pass(A: Any) -> None:  # noqa: N803
    outcomes = A._parse_node_outcomes(_ALL_SKIPPED)
    ok, reasons = A.evaluate_node_coverage(
        ["tests/test_x.py::test_a", "tests/test_x.py::test_b"], outcomes
    )
    assert not ok
    assert len(reasons) == 2
    assert "no PASSED" in reasons[0]


def test_every_id_passed_is_a_pass(A: Any) -> None:  # noqa: N803
    outcomes = A._parse_node_outcomes(_ALL_PASSED)
    ok, reasons = A.evaluate_node_coverage(
        ["tests/test_x.py::test_a", "tests/test_x.py::test_b"], outcomes
    )
    assert ok, reasons


def test_a_parametrised_id_is_satisfied_by_its_params(A: Any) -> None:  # noqa: N803
    """`_repair_truncated_param_ids` widens ids to whole functions, so ONE id
    legitimately selects several nodes (measured: conan-19735 f2p=1 -> 4 passed).
    A literal `count(PASSED) == len(ids)` rule would have flipped that row."""
    text = (
        "=========================== short test summary info ===\n"
        "PASSED tests/test_x.py::test_a[1]\n"
        "PASSED tests/test_x.py::test_a[2]\n"
        "PASSED tests/test_x.py::test_a[a b]\n"
        "3 passed in 0.08s\n"
    )
    ok, reasons = A.evaluate_node_coverage(
        ["tests/test_x.py::test_a"], A._parse_node_outcomes(text)
    )
    assert ok, reasons


def test_a_file_level_id_is_satisfied_by_its_nodes(A: Any) -> None:  # noqa: N803
    """The implicit pass_to_pass set is FILE paths (defect 6)."""
    text = (
        "= short test summary info =\n"
        "PASSED tests/api/test_x.py::test_a\n"
        "1 passed in 0.08s\n"
    )
    ok, _ = A.evaluate_node_coverage(
        ["tests/api/test_x.py"], A._parse_node_outcomes(text)
    )
    assert ok


def test_one_skipped_among_passes_still_fails_its_own_id(A: Any) -> None:  # noqa: N803
    """pytest exits 0 when one selected test skips and the rest pass. The
    skipped id was never demonstrated, so the row is not resolved."""
    text = (
        "= short test summary info =\n"
        "PASSED tests/test_x.py::test_a\n"
        "SKIPPED [1] tests/test_x.py:6: nope\n"
        "1 passed, 1 skipped in 0.08s\n"
    )
    ok, reasons = A.evaluate_node_coverage(
        ["tests/test_x.py::test_a", "tests/test_x.py::test_b"],
        A._parse_node_outcomes(text),
    )
    assert not ok
    assert "test_b" in reasons[0]


def test_a_failed_node_under_a_passing_id_fails(A: Any) -> None:  # noqa: N803
    text = (
        "= short test summary info =\n"
        "PASSED tests/test_x.py::test_a[1]\n"
        "FAILED tests/test_x.py::test_a[2] - AssertionError\n"
        "1 failed, 1 passed in 0.08s\n"
    )
    ok, reasons = A.evaluate_node_coverage(
        ["tests/test_x.py::test_a"], A._parse_node_outcomes(text)
    )
    assert not ok
    assert "FAILED" in reasons[0]


def test_captured_stdout_cannot_forge_a_pass(A: Any) -> None:  # noqa: N803
    """`-rA` echoes a passing test's captured stdout in a PASSES section, so
    arm-authored code could print `PASSED <id>` for an id that never ran. The
    parser reads ONLY the short-summary section, and the script asks for
    `-rpfEsxX` (no captured output) instead of `-rA`."""
    text = (
        "==================================== PASSES ====================================\n"
        "__________________________________ test_a ______________________________________\n"
        "----------------------------- Captured stdout call -----------------------------\n"
        "PASSED tests/test_x.py::test_forged\n"
        "=========================== short test summary info ============================\n"
        "PASSED tests/test_x.py::test_a\n"
        "1 passed in 0.08s\n"
    )
    outcomes = A._parse_node_outcomes(text)
    assert "tests/test_x.py::test_forged" not in outcomes
    ok, _ = A.evaluate_node_coverage(["tests/test_x.py::test_a"], outcomes)
    assert ok
    ok2, _ = A.evaluate_node_coverage(["tests/test_x.py::test_forged"], outcomes)
    assert not ok2


def test_no_node_evidence_at_all_is_refused(A: Any) -> None:  # noqa: N803
    """FAIL CLOSED: a log with no per-node section cannot certify anything."""
    ok, reasons = A.evaluate_node_coverage(["tests/test_x.py::test_a"], {})
    assert not ok
    assert reasons


def test_an_empty_id_set_is_vacuously_covered(A: Any) -> None:  # noqa: N803
    """An empty pass_to_pass is defect 6's problem, not defect 2's — the
    verdict must not hard-fail on it, or every no-p2p instance breaks."""
    ok, reasons = A.evaluate_node_coverage([], {})
    assert ok
    assert reasons == []


def test_node_regions_are_split_out_of_the_human_log(A: Any) -> None:  # noqa: N803
    log = (
        "some pytest chatter\n"
        "SWEBENCH_NODES_abc123: BEGIN fail_to_pass\n"
        "PASSED tests/test_x.py::test_a\n"
        "1 passed in 0.01s\n"
        "SWEBENCH_NODES_abc123: END fail_to_pass\n"
        "SWEBENCH_RESULT_abc123: RESOLVED\n"
    )
    human, regions = A._split_node_regions(log, "abc123")
    assert set(regions) == {"fail_to_pass"}
    assert "PASSED tests/test_x.py::test_a" in regions["fail_to_pass"]
    assert "PASSED" not in human
    assert "SWEBENCH_RESULT_abc123: RESOLVED" in human
    assert "node outcomes for fail_to_pass" in human


def test_an_unterminated_node_region_yields_nothing(A: Any) -> None:  # noqa: N803
    """A truncated/killed run must not certify a partial region as complete."""
    log = (
        "SWEBENCH_NODES_abc123: BEGIN fail_to_pass\n"
        "PASSED tests/test_x.py::test_a\n"
    )
    _, regions = A._split_node_regions(log, "abc123")
    assert regions == {}


def test_the_grade_script_asks_pytest_for_per_node_outcomes(A: Any) -> None:  # noqa: N803
    inst = {
        "instance_id": "x__y-1",
        "repo": "x/y",
        "base_commit": "0" * 40,
        "docker_image": "img@sha256:" + "0" * 64,
        "fail_to_pass": ["tests/test_x.py::test_a"],
        "pass_to_pass": ["tests/test_x.py::test_b"],
        "test_patch": "",
        "gold_patch": "",
        "test_targets": ["tests/test_x.py"],
    }
    script = A._grade_script_for(inst, "diff --git a/s.py b/s.py\n")
    assert "-rpfEsxX" in script
    assert "pytest -q -rA" not in script  # -rA echoes captured stdout
    assert "SWEBENCH_NODES_" in script
    # The nonce must not survive into pytest's environment, or arm-authored
    # test code could read it and forge a marker.
    assert "unset SWEBENCH_NONCE" in script


# --------------------------------------------------------------------------- #
# defect 6 — two instances have an EMPTY pass_to_pass (no regression suite)
# --------------------------------------------------------------------------- #


def test_empty_pass_to_pass_falls_back_to_declared_test_targets(A: Any) -> None:  # noqa: N803
    inst = {
        "instance_id": "line__line-bot-sdk-python-981_interface",
        "profile": "swe-rebench",
        "repo": "line/line-bot-sdk-python",
        "base_commit": "0" * 40,
        "docker_image": "img@sha256:" + "0" * 64,
        "fail_to_pass": ["tests/api/test_x.py::test_a"],
        "pass_to_pass": [],
        "test_patch": "",
        "gold_patch": "",
        "test_targets": ["tests/api/test_x.py"],
    }
    ids, source = A._pass_to_pass_for(inst, A._normalize_oracle(inst))
    assert ids == ["tests/api/test_x.py"]
    assert source == "declared_test_targets"


def test_a_present_pass_to_pass_is_used_verbatim(A: Any) -> None:  # noqa: N803
    inst = {
        "instance_id": "x__y-1",
        "profile": "swe-rebench",
        "repo": "x/y",
        "base_commit": "0" * 40,
        "docker_image": "img@sha256:" + "0" * 64,
        "fail_to_pass": ["tests/test_x.py::test_a"],
        "pass_to_pass": ["tests/test_x.py::test_b"],
        "test_patch": "",
        "gold_patch": "",
        "test_targets": ["tests/test_x.py"],
    }
    ids, source = A._pass_to_pass_for(inst, A._normalize_oracle(inst))
    assert ids == ["tests/test_x.py::test_b"]
    assert source == "dataset"


def test_the_frozen_pro_profile_gets_no_implicit_p2p(A: Any) -> None:  # noqa: N803
    """Pro archives must stay byte-reproducible: no new grading semantics."""
    inst = {
        "instance_id": "instance_ansible__ansible-abc-v1",
        "repo": "ansible/ansible",
        "base_commit": "0" * 40,
        "dockerhub_tag": "t",
        "fail_to_pass": ["test/x.py::test_a"],
        "pass_to_pass": [],
        "selected_test_files_to_run": '["test/x.py::test_a"]',
        "test_patch": "",
        "gold_patch": "",
    }
    ids, source = A._pass_to_pass_for(inst, A._normalize_oracle(inst))
    assert ids == []
    assert source == "dataset"


# --------------------------------------------------------------------------- #
# defect 1 — the oracle store was reachable from the agent's shell
# --------------------------------------------------------------------------- #
#
# THIS ONE FIRED. The dev agent's cwd was
# bench/swebench/runs/<id>/factory/root/state/worktrees/<name>/ — six `..`
# from oracle.json.z, and three from the OTHER arm's run dir. Four factory
# rows in results-archive/2026-08-03T02-21-23.249790Z are `ok: false` with
# "own run's oracle-bearing subdir runs/.../bare".


def test_the_work_root_is_outside_the_repo(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    monkeypatch.delenv("SWEBENCH_WORK_ROOT", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    root = A._work_root()
    assert not root.is_relative_to(A.FACTORY_ROOT)


def test_a_work_dir_has_no_oracle_bearing_ancestor(A: Any) -> None:  # noqa: N803
    work = A._work_dir("x__y-1", "factory")
    A.assert_workspace_isolated(work / "root" / "state" / "worktrees" / "s")
    assert not work.is_relative_to(A.SWE_DIR)


def test_a_workspace_under_the_harness_dir_is_refused(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """The exact pre-fix layout must now be a hard error."""
    bad = A.RUNS_DIR / "x__y-1" / "factory" / "root" / "state" / "worktrees" / "s"
    with pytest.raises(SystemExit, match="reachable"):
        A.assert_workspace_isolated(bad)


def test_an_ancestor_holding_the_oracle_store_is_refused(A: Any, tmp_path: Path) -> None:  # noqa: N803
    (tmp_path / "oracle.json.z").write_text("x", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    with pytest.raises(SystemExit, match="oracle.json.z"):
        A.assert_workspace_isolated(deep)


def test_an_ancestor_holding_a_grade_log_is_refused(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """Another arm's grade.log carries the hidden test ids verbatim."""
    (tmp_path / "grade.log").write_text("PASSED tests/secret.py::test_x\n", encoding="utf-8")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    with pytest.raises(SystemExit, match="grade.log"):
        A.assert_workspace_isolated(deep)


def test_grade_prepares_its_clone_outside_the_repo(A: Any) -> None:  # noqa: N803
    """The graded mount has the ORACLE TEST PATCH applied inside it. Left in
    `runs/<id>/<arm>/grade-repo/` it was three `..` from the next arm's cwd."""
    p = A._grade_mount_dir("x__y-1", "factory")
    assert not p.is_relative_to(A.SWE_DIR)


def test_selftest_prepares_its_clone_outside_the_repo(A: Any) -> None:  # noqa: N803
    """Worse than grade-repo: selftest applies the GOLD patch into its mount."""
    p = A._selftest_mount_dir("x__y-1")
    assert not p.is_relative_to(A.SWE_DIR)


# --------------------------------------------------------------------------- #
# defect 1c — the probe detector's blind spots
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "line",
    [
        "curl -s https://github.com/x/y/pull/981.diff",
        "wget http://example.com/patch",
        "git fetch origin main",
        "git pull --rebase",
        "git ls-remote https://github.com/x/y",
        "gh pr view 981 --json files",
        "urllib.request.urlopen('https://github.com/x/y')",
        "see https://github.com/x/y/commit/deadbeef",
    ],
)
def test_network_retrieval_is_flagged(A: Any, line: str) -> None:  # noqa: N803
    assert A._probe_line_hits(line, "x__y-1", "factory"), line


@pytest.mark.parametrize(
    "line",
    [
        "python -m pytest tests/test_x.py",
        "git status --porcelain",
        "git diff --cached",
        "import requests  # unused",
        "ls -la src/",
        "docker run --rm -v \"$PWD\":/testbed img -lc 'pytest'",
    ],
)
def test_ordinary_commands_are_not_flagged(A: Any, line: str) -> None:  # noqa: N803
    assert not A._probe_line_hits(line, "x__y-1", "factory"), line


def test_an_oracle_bearing_filename_in_the_own_subtree_is_still_flagged(A: Any) -> None:  # noqa: N803
    """The blanket own-subtree exemption let `cat runs/<id>/factory/grade.log`
    through — the arm's OWN grade log is the answer key for the next attempt."""
    hits = A._probe_line_hits(
        "cat bench/swebench/runs/x__y-1/factory/grade.log", "x__y-1", "factory"
    )
    assert hits


def test_the_own_cwd_echo_is_still_exempt(A: Any) -> None:  # noqa: N803
    """Regression: 13/19 factory rows were false-flagged by an own-cwd rule
    that was too strict. Ordinary own-subtree paths must stay clean."""
    assert not A._probe_line_hits(
        "cd bench/swebench/runs/x__y-1/factory/root/state/worktrees/swe-abc",
        "x__y-1",
        "factory",
    )


def test_another_arms_dir_is_still_flagged(A: Any) -> None:  # noqa: N803
    assert A._probe_line_hits(
        "ls bench/swebench/runs/x__y-1/bare", "x__y-1", "factory"
    )


# --------------------------------------------------------------------------- #
# defect 5 — audit.json never looked at the graded patch
# --------------------------------------------------------------------------- #


def _seed_run(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **result: Any) -> Path:  # noqa: N803
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path / "runs")
    run_dir = A._run_dir("x__y-1", "bare")
    (run_dir / "prediction.diff").write_text(
        "diff --git a/s.py b/s.py\n@@ -1 +1 @@\n-x\n+y\n", encoding="utf-8"
    )
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return run_dir


def test_audit_records_the_graded_patch(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:  # noqa: N803
    run_dir = _seed_run(
        A,
        tmp_path,
        monkeypatch,
        arm="bare",
        base_commit="a" * 40,
        test_files_stripped=["tests/test_x.py"],
        refused_paths=[],
        cost_usd=0.0,
        persona_calls=0,
    )
    with pytest.raises(SystemExit):
        # No ledger DB in the fixture, so the audit fails — the payload is
        # written either way, which is the point.
        A.audit("x__y-1", "bare")
    payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    expected = hashlib.sha256(
        (run_dir / "prediction.diff").read_bytes()
    ).hexdigest()
    assert payload["prediction_sha256"] == expected
    assert payload["base_commit"] == "a" * 40
    assert payload["stripped_test_paths"] == ["tests/test_x.py"]
    assert payload["refused_paths"] == []
    assert payload["trajectories_scanned"] == 0
    assert payload["trails_scanned"] == 0


def test_a_factory_run_with_no_action_trail_fails_the_audit(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    """The wiped-state-root hole: `_scan_oracle_probes` was fail-OPEN on an
    empty trajectory dir, so a run whose state root no longer exists audited
    clean — exactly the state the four re-rolled rows are now in."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path / "runs")
    run_dir = A._run_dir("x__y-1", "factory")
    (run_dir / "prediction.diff").write_text("diff --git a/s.py b/s.py\n", encoding="utf-8")
    (run_dir / "result.json").write_text(
        json.dumps({"arm": "factory", "persona_calls": 4, "cost_usd": 1.23}),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        A.audit("x__y-1", "factory")
    payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert any("no action trail" in f for f in payload["failures"]), payload["failures"]


def test_a_run_that_made_no_calls_needs_no_trail(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    """A run that died before the first model call has nothing to scan; the
    missing-artifact checks already fail it, and this must not double-count."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path / "runs")
    failures, scanned, trails = A._scan_oracle_probes(
        tmp_path / "nonexistent-root",
        A._run_dir("x__y-1", "factory"),
        {"arm": "factory", "persona_calls": 0, "cost_usd": 0.0},
        instance_id="x__y-1",
        arm="factory",
    )
    assert failures == []
    assert scanned == 0
    assert trails == 0


# --------------------------------------------------------------------------- #
# defect 7 — the gold-patch control's evidence was being deleted
# --------------------------------------------------------------------------- #


def test_selftest_logs_land_in_a_committed_directory(A: Any) -> None:  # noqa: N803
    """`runs/` is gitignored, so 0 of the 19 published instances kept the
    control log that certified them. The control's evidence has to survive.

    The module DEFAULT is checked on a freshly loaded copy: the autouse
    isolation fixture repoints the live one at tmp_path, which is exactly what
    it is there for.
    """
    fresh = _load()
    assert fresh.SELFTEST_LOG_DIR == fresh.SWE_DIR / "selftest-logs"
    assert not fresh.SELFTEST_LOG_DIR.is_relative_to(fresh.RUNS_DIR)
    assert A._selftest_log_path("x__y-1").parent == A.SELFTEST_LOG_DIR
    assert A._selftest_log_path("x__y-1").name == "x__y-1.log"
    with pytest.raises(SystemExit):
        A._selftest_log_path("../escape")


def test_reset_run_artifacts_clears_the_sweep_logs(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """`grade` printed the oracle's gold_files to stdout, which the sweep
    captured into `sweep-grade.log` next to the result it graded."""
    for name in (
        "sweep-run.log",
        "sweep-grade.log",
        "sweep-audit.log",
        "grade.log",
        "grade-nodes.log",
        "prediction.diff",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")
    A._reset_run_artifacts(tmp_path)
    # ``attempt.json`` is the ONE deliberate survivor: it is the attempt
    # counter, which must outlive the run it counts (see `_bump_attempt`).
    assert sorted(p.name for p in tmp_path.iterdir()) == ["attempt.json"]


# --------------------------------------------------------------------------- #
# regression against the REAL corpus — these fixes must refuse nothing that
# already graded, and must not flip a verdict that was already published
# --------------------------------------------------------------------------- #
#
# The mandatory evidence for defects 2, 3 and 4, kept as tests rather than a
# one-off script so a later change to the parsers cannot quietly break it.
# `runs/` is gitignored, so only `results-archive/` is available here; the
# retained live `runs/` corpus is covered in the PR body.

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ARCHIVE = _REPO_ROOT / "bench" / "swebench" / "results-archive"


def _archived_predictions() -> list[Path]:
    return sorted(_ARCHIVE.rglob("prediction.diff"))


def test_the_committed_prediction_corpus_is_refused_nowhere(A: Any) -> None:  # noqa: N803
    """Defects 3 + 4 refuse rows, so they had to be measured against every
    prediction the harness has ever graded before being switched on.

    Measured 2026-08-03: 119 committed + 69 retained-live = 188 files, zero
    refusals, zero rows with a test-file block to strip. A refusal appearing
    here means a real arm hit the new hard error, and the number it would have
    changed has to be re-derived before anything is published.
    """
    files = _archived_predictions()
    assert len(files) >= 119, f"the committed corpus shrank: {len(files)} files"
    refused: list[tuple[str, list[str]]] = []
    stripped: list[tuple[str, list[str]]] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        try:
            code, _kept, test_paths = A.split_diff(text)
        except A.DiffRefused as exc:
            refused.append((str(f.relative_to(_REPO_ROOT)), exc.paths))
            continue
        if test_paths:
            stripped.append((str(f.relative_to(_REPO_ROOT)), test_paths))
        # The second line of defence must agree with the first on real data.
        A.assert_no_test_edits(code)
    assert refused == [], f"the new refusals would have invalidated: {refused}"
    assert stripped == [], f"unexpected test-file blocks in the corpus: {stripped}"


def test_the_pinned_gold_patches_survive_the_arm_refusal_rules(A: Any) -> None:  # noqa: N803
    """`refuse_collection_channels=False` exists for the gold patch, and this
    records that it is belt-and-braces rather than load-bearing: none of the 20
    pinned gold patches touches a collection channel today. If one starts to,
    the selftest keeps working and only this expectation changes."""
    fresh = _load()  # the autouse fixture repoints the store; read the real one
    store = fresh._load_oracle_store()
    assert len(store) >= 20, f"oracle store shrank to {len(store)} records"
    refused = []
    for iid, rec in store.items():
        try:
            fresh.split_diff(rec.get("patch") or "")
        except fresh.DiffRefused as exc:
            refused.append((iid, exc.paths))
    assert refused == [], refused


_PRE_CHANGE_GRADE_LOG = """\
Checking patch tests/test_reasoning_parsers.py...
Applied patch tests/test_reasoning_parsers.py cleanly.
SWEBENCH_SETUP: test_patch applied
SWEBENCH_BASELINE_673072f0171e06a2: OK (red as expected)
SWEBENCH_APPLY_673072f0171e06a2: OK
============================= test session starts ==============================
collected 2 items

tests/test_reasoning_parsers.py ..                                       [100%]

============================== 2 passed in 0.02s ===============================
SWEBENCH_RESULT_673072f0171e06a2: RESOLVED
"""


def test_a_pre_change_grade_log_passes_through_the_region_peeler(A: Any) -> None:  # noqa: N803
    """Verbatim from `runs/raullenchai__rapid-mlx-289/factory/grade.log`.

    `_split_node_regions` runs over every grade log, including the 59 retained
    ones from before the node-outcome markers existed. It must be a byte-exact
    no-op on them, or re-auditing an old row would corrupt its evidence.
    """
    human, regions = A._split_node_regions(
        _PRE_CHANGE_GRADE_LOG, "673072f0171e06a2"
    )
    assert regions == {}
    assert human == _PRE_CHANGE_GRADE_LOG


# --------------------------------------------------------------------------- #
# the five-arm re-run — nothing may recognise an arm by exact model name
# --------------------------------------------------------------------------- #


def test_a_model_suffixed_claude_arm_is_still_a_claude_arm(A: Any) -> None:  # noqa: N803
    """The next sweep runs the CLI twice (`--model claude-opus-5` and
    `--model claude-opus-4-8`), so the two runs need distinct arm names.

    Every claude-specific certification in `audit` was selected by
    `arm == "claude"`. Under a model-suffixed arm name that equality is False,
    so `_audit_claude_run` (usage/cost certification + hermeticity) and the
    missing-transcript failure would both be SKIPPED — the fail-OPEN
    direction, on the arm with the highest published score.
    """
    for arm in ("claude", "claude-opus-5", "claude-opus-4-8"):
        assert A._is_claude_arm(arm), arm
    for arm in ("factory", "bare", "openhands", "claudette", "clause"):
        assert not A._is_claude_arm(arm), arm


def test_a_claude_arm_with_no_transcript_fails_whatever_its_model_name(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path / "runs")
    for arm in ("claude", "claude-opus-4-8"):
        run_dir = A._run_dir("x__y-1", arm)
        failures, _traj, _trails = A._scan_oracle_probes(
            run_dir,
            run_dir,
            {"arm": arm, "num_turns": 12, "cost_usd": 0.42},
            instance_id="x__y-1",
            arm=arm,
        )
        assert any("left no claude-transcript" in f for f in failures), (arm, failures)


def test_a_clipped_own_arm_segment_is_not_a_probe(A: Any) -> None:  # noqa: N803
    """Regression guard on the stricter own-arm rule: OpenHands truncates an
    observation MID-SEGMENT, and `runs/<id>/fact<response clipped` is the own
    path, not a sibling's. Any OTHER divergence stays flagged."""
    assert A._probe_line_hits(
        "ls bench/swebench/runs/x__y-1/fact<response clipped>", "x__y-1", "factory"
    ) == []
    assert A._probe_line_hits(
        "ls bench/swebench/runs/x__y-1/bar<response clipped>", "x__y-1", "factory"
    )


def test_the_condenser_ellipsis_cannot_hide_an_oracle_file(A: Any) -> None:  # noqa: N803
    """`runs/<id>/.../worktrees/x` is the condenser abbreviating the own path,
    so the ellipsis segment is exempt — but the exemption must not become a
    tunnel: an oracle-bearing BASENAME behind it is still a finding."""
    assert A._probe_line_hits(
        "work done in bench/swebench/runs/x__y-1/.../worktrees/x", "x__y-1", "factory"
    ) == []
    assert A._probe_line_hits(
        "cat bench/swebench/runs/x__y-1/.../grade.log", "x__y-1", "factory"
    )
    assert A._probe_line_hits(
        "cat bench/swebench/runs/x__y-1/.../result.json", "x__y-1", "factory"
    )


def test_a_working_tree_left_inside_the_run_dir_fails_the_audit(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """Backstop for defect 1a that does not depend on a run function calling
    `assert_workspace_isolated`.

    Measured on this branch: `run_factory` and `run_claude` clone into
    `_work_dir` (outside the repo) and assert isolation, but `run_bare` still
    does `repo = run_dir / "repo"; _clone(inst, repo)` — its shell's cwd is
    three `..` from `bench/swebench/oracle.json.z`. `audit` is the one step
    every arm goes through, so the invariant is re-checked from the artifacts.
    """
    run_dir = tmp_path / "runs" / "x__y-1" / "bare"
    run_dir.mkdir(parents=True)
    assert A._audit_workspace_layout(run_dir, "bare") == []
    (run_dir / "repo").mkdir()
    failures = A._audit_workspace_layout(run_dir, "bare")
    assert len(failures) == 1
    assert "inside the harness directory" in failures[0]
    (run_dir / "grade-repo").mkdir()
    assert len(A._audit_workspace_layout(run_dir, "bare")) == 2


def test_every_arm_clones_outside_the_repo(A: Any) -> None:  # noqa: N803
    """Defect 1a, for all four arms.

    Asserted on the source because the alternative is four live clones. The
    behavioural half is `_audit_workspace_layout` (below) plus the arm tests in
    `test_swebench_bare_openhands_arms.py`, which now assert the tree really
    lands under `_work_dir`. `run_bare` and `run_openhands` shipped in #223
    still doing `repo = run_dir / "repo"` — three `..` from `oracle.json.z`.
    """
    import inspect

    for fn_name in ("run_factory", "run_bare", "run_claude", "run_openhands"):
        src = inspect.getsource(getattr(A, fn_name))
        assert '= run_dir / "repo"' not in src, (
            f"{fn_name} puts its live working tree inside bench/swebench/"
        )
        assert "_work_dir(" in src, f"{fn_name} does not use the scratch work root"
        assert "assert_workspace_isolated(" in src, (
            f"{fn_name} never checks its workspace's ancestry before spend"
        )


def test_the_isolation_backstop_covers_every_arm(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """The audit-side check is arm-agnostic on purpose: a fifth arm inherits it
    without anyone remembering to add it."""
    for arm in ("factory", "bare", "claude", "openhands", "claude-opus-4-8", "future"):
        run_dir = tmp_path / arm
        (run_dir / "repo").mkdir(parents=True)
        failures = A._audit_workspace_layout(run_dir, arm)
        assert len(failures) == 1, (arm, failures)
        assert "inside the harness directory" in failures[0]
