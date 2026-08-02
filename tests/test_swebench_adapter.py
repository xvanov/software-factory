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


# --------------------------------------------------------------------------- #
# the factory arm's test environment
# --------------------------------------------------------------------------- #


_INST = {
    "instance_id": "instance_x__y-abc",
    "dockerhub_tag": "x.y-abc",
    "selected_test_files_to_run": (
        '["test/units/test_sys_info.py::test_get_distribution[SunOS-Solaris]", '
        '"test/units/test_sys_info.py::test_get_distribution[Darwin-Darwin]", '
        '"test/units/test_other.py::test_thing"]'
    ),
}


def test_test_command_runs_inside_the_instance_image(A: Any) -> None:  # noqa: N803
    """A bare clone has no dependencies: plain pytest dies with
    ModuleNotFoundError and dev — whose mechanism is run-until-green — blocks
    with an empty diff. The image has the deps, so mount the tree over /app."""
    cmd = A.instance_test_command(_INST)
    assert cmd.startswith("docker run --rm")
    assert '-v "$PWD":/app' in cmd, "must mount the CURRENT worktree, not a baked path"
    assert "-w /app" in cmd
    assert "jefzda/sweap-images:x.y-abc" in cmd
    assert "python -m pytest" in cmd


def test_test_command_does_not_leak_oracle_test_names(A: Any) -> None:  # noqa: N803
    """``selected_test_files_to_run`` holds the oracle's fail_to_pass NODE IDS
    despite its name. Passing them to dev leaks the hidden suite AND asks for
    tests that do not exist in dev's tree (they arrive with the test patch),
    so every run died on `ERROR: not found` and dev never got a green signal."""
    cmd = A.instance_test_command(_INST)
    assert "::" not in cmd, cmd
    assert "test_get_distribution" not in cmd
    assert "test/units/test_sys_info.py" in cmd
    assert "test/units/test_other.py" in cmd


def test_node_ids_reduce_to_distinct_files(A: Any) -> None:  # noqa: N803
    assert A._test_file_paths(
        ["a/b.py::t1", "a/b.py::t2[x-y]", "c/d.py", "a/b.py::t3"]
    ) == ["a/b.py", "c/d.py"]
    assert A._test_file_paths([]) == []


def test_container_cannot_litter_the_host_with_root_owned_files(A: Any) -> None:  # noqa: N803
    """Root-owned `.pytest_cache` left by the container made the next run
    unable to delete its own workspace ("Permission denied")."""
    cmd = A.instance_test_command(_INST)
    assert '--user "$(id -u):$(id -g)"' in cmd
    assert "-p no:cacheprovider" in cmd
    assert "PYTHONDONTWRITEBYTECODE=1" in cmd


# --------------------------------------------------------------------------- #
# result.json integrity — a fresh run must not inherit a previous run's keys
# --------------------------------------------------------------------------- #


def test_fresh_run_result_drops_stale_keys(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """`_write_result` used to MERGE unconditionally, so keys from a previous
    run in the same dir (context_*, an old grade) persisted forever."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    A._write_result("i1", "factory", {"cost_usd": 1.0, "context_files": ["stale.md"]})
    A._write_result("i1", "factory", {"grade": {"oracle_resolved": True}}, merge=True)
    A._write_result("i1", "factory", {"cost_usd": 2.0})  # a NEW run
    data = json.loads((tmp_path / "i1" / "factory" / "result.json").read_text())
    # Nothing survives from the previous run: not the context keys, and not the
    # grade — that verdict was for a prediction that no longer exists.
    assert data == {"cost_usd": 2.0}


def test_grade_still_merges_onto_the_run_result(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    A._write_result("i1", "factory", {"cost_usd": 2.0, "arm": "factory"})
    A._write_result("i1", "factory", {"grade": {"oracle_resolved": False}}, merge=True)
    data = json.loads((tmp_path / "i1" / "factory" / "result.json").read_text())
    assert data["cost_usd"] == 2.0, "grade must not clobber the run payload"
    assert data["grade"] == {"oracle_resolved": False}


# --------------------------------------------------------------------------- #
# ledger totals — every Run row counts, attribution gaps stay visible
# --------------------------------------------------------------------------- #


def test_ledger_totals_count_every_row_and_expose_unattributed(A: Any) -> None:  # noqa: N803
    """Summing only story_id-attributed rows hid onboarder/setup persona spend
    (measured 1.62x cost under-reporting). The state root is per-run isolated,
    so EVERY row in the DB belongs to the run."""
    from types import SimpleNamespace as R  # noqa: N814

    runs = [
        R(story_id=7, tokens_in=100, tokens_out=10, cached_input_tokens=5, cost_usd=1.0),
        # An onboarder-style row with NO story attribution — previously invisible.
        R(story_id=None, tokens_in=200, tokens_out=20, cached_input_tokens=0, cost_usd=0.62),
        R(story_id=9, tokens_in=50, tokens_out=5, cached_input_tokens=None, cost_usd=0.38),
    ]
    t = A._ledger_totals(runs, 7)
    assert t["cost_usd"] == 2.0
    assert t["tokens_in"] == 350
    assert t["tokens_out"] == 35
    assert t["cached_input_tokens"] == 5
    assert t["persona_calls"] == 3
    assert t["unattributed_persona_calls"] == 2
    assert t["unattributed_cost_usd"] == 1.0


# --------------------------------------------------------------------------- #
# wall clock — reported wall_clock_s must include clone/setup time
# --------------------------------------------------------------------------- #


def test_wall_clock_starts_before_clone_and_setup(A: Any) -> None:  # noqa: N803
    """The clock used to start AFTER _clone/_build_bench_root, silently
    excluding setup from wall_clock_s. Contract: the entry clock (`entered`)
    is assigned before any statement that calls _clone."""
    import ast

    tree = ast.parse(_ADAPTER.read_text(encoding="utf-8"))
    for fname in ("run_factory", "run_bare"):
        fn = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname
        )

        def _stmt_index(pred: Any, fn: ast.FunctionDef = fn) -> int:
            for i, stmt in enumerate(fn.body):
                if pred(stmt):
                    return i
            raise AssertionError(f"pattern not found in {fn.name}")

        entered_at = _stmt_index(
            lambda s: isinstance(s, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "entered" for t in s.targets)
        )
        clone_at = _stmt_index(
            lambda s: any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "_clone"
                for n in ast.walk(s)
            )
        )
        assert entered_at < clone_at, (
            f"{fname}: the wall clock must start before _clone (entered at "
            f"stmt {entered_at}, _clone at stmt {clone_at})"
        )


# --------------------------------------------------------------------------- #
# stale artifacts — a new run must never inherit a previous run's outputs
# --------------------------------------------------------------------------- #


def test_reset_run_artifacts_deletes_stale_outputs_and_ledger(
    A: Any, tmp_path: Path  # noqa: N803
) -> None:
    """Run #2 failing early (precheck/timeout/crash) must not leave run #1's
    prediction.diff for `grade` to certify, nor run #1's Run rows for the
    bare arm's sum-all totals to absorb."""
    for name in ("prediction.diff", "raw.diff", "grade.log", "result.json", "audit.json"):
        (tmp_path / name).write_text("stale", encoding="utf-8")
    (tmp_path / "state" / "events").mkdir(parents=True)
    (tmp_path / "state" / "factory.db").write_text("stale-ledger", encoding="utf-8")
    A._reset_run_artifacts(tmp_path)
    for name in ("prediction.diff", "raw.diff", "grade.log", "result.json", "audit.json"):
        assert not (tmp_path / name).exists(), name
    assert not (tmp_path / "state").exists(), "bare-arm ledger must not accumulate"
    # Idempotent on a clean dir.
    A._reset_run_artifacts(tmp_path)


def test_run_functions_reset_artifacts_before_any_exit_path(A: Any) -> None:  # noqa: N803
    """Contract (AST): both run functions call _reset_run_artifacts before
    _clone — and run_factory before _ensure_image, its earliest SystemExit —
    so no early exit can strand a previous run's prediction beside a fresh
    result."""
    import ast

    tree = ast.parse(_ADAPTER.read_text(encoding="utf-8"))
    for fname, must_precede in (
        ("run_factory", ("_ensure_image", "_clone")),
        ("run_bare", ("_clone",)),
    ):
        fn = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname
        )

        def _call_index(callee: str, fn: ast.FunctionDef = fn, fname: str = fname) -> int:
            for i, stmt in enumerate(fn.body):
                if any(
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == callee
                    for n in ast.walk(stmt)
                ):
                    return i
            raise AssertionError(f"{fname} never calls {callee}")

        reset_at = _call_index("_reset_run_artifacts")
        for callee in must_precede:
            assert reset_at < _call_index(callee), (
                f"{fname}: _reset_run_artifacts must run before {callee}"
            )


# --------------------------------------------------------------------------- #
# clone — submodules must be initialised, and loudly fail when they cannot be
# --------------------------------------------------------------------------- #


def _mk_git_repo(path: Path, files: dict[str, str]) -> str:
    import subprocess as sp

    path.mkdir(parents=True)
    def g(*args: str) -> None:
        sp.run(
            ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True, text=True,
        )
    g("init", "-q")
    for rel, content in files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    g("add", ".")
    g("commit", "-q", "-m", "init")
    out = sp.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


@pytest.fixture
def submodule_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, str]:
    """(main_repo, sub_repo, base_commit) — main has `vendor/infogami` as a
    real git submodule, like openlibrary."""
    import subprocess as sp

    # git >= 2.38 blocks file-path submodule clones by default.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")

    sub = tmp_path / "upstream-sub"
    _mk_git_repo(sub, {"infogami_mod.py": "VALUE = 1\n"})
    main = tmp_path / "upstream-main"
    _mk_git_repo(main, {"app.py": "import vendor.infogami\n"})
    sp.run(
        ["git", "-C", str(main), "-c", "user.email=t@t", "-c", "user.name=t",
         "submodule", "add", str(sub), "vendor/infogami"],
        check=True, capture_output=True, text=True,
    )
    sp.run(
        ["git", "-C", str(main), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "add submodule"],
        check=True, capture_output=True, text=True,
    )
    sha = sp.run(
        ["git", "-C", str(main), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return main, sub, sha


def test_clone_initialises_submodules(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # noqa: N803
    submodule_fixture: tuple[Path, Path, str],
) -> None:
    """openlibrary's `infogami` symlink points into an uninitialised submodule:
    without init, the mounted tree import-fails in <1s, deterministically."""
    import subprocess as sp

    main, _sub, sha = submodule_fixture
    monkeypatch.setattr(A, "_clone_url", lambda inst: f"file://{main}")
    inst = {"instance_id": "local__main-abc", "repo": "local/main", "base_commit": sha}
    dest = tmp_path / "clone"
    A._clone(inst, dest)
    assert (dest / "vendor" / "infogami" / "infogami_mod.py").exists(), (
        "submodule content missing — the mounted tree would import-fail"
    )
    # The content must be TRACKED (vendored), not a gitlink: the chain builds
    # per-story worktrees with `git worktree add`, which never populates
    # submodules — a gitlink would pass this precheck on the clone while dev's
    # actual worktree import-fails (proxy != real).
    tracked = sp.run(
        ["git", "-C", str(dest), "ls-files", "vendor/infogami/infogami_mod.py"],
        capture_output=True, text=True,
    ).stdout.strip()
    assert tracked == "vendor/infogami/infogami_mod.py"
    wt = tmp_path / "story-worktree"
    sp.run(
        ["git", "-C", str(dest), "worktree", "add", "-b", "swebench-95000-x", str(wt)],
        check=True, capture_output=True, text=True,
    )
    assert (wt / "vendor" / "infogami" / "infogami_mod.py").exists(), (
        "a worktree derived from the clone lost the submodule content"
    )


def test_clone_fails_loudly_when_a_submodule_cannot_fetch(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # noqa: N803
    submodule_fixture: tuple[Path, Path, str],
) -> None:
    """A submodule that cannot fetch must be a hard error, not a silent skip —
    a silently-partial clone would reintroduce the exact bug this fixes."""
    import shutil as _shutil

    main, sub, sha = submodule_fixture
    _shutil.rmtree(sub)  # the submodule's upstream is now unreachable
    monkeypatch.setattr(A, "_clone_url", lambda inst: f"file://{main}")
    inst = {"instance_id": "local__main-abc", "repo": "local/main", "base_commit": sha}
    with pytest.raises(RuntimeError, match="submodule init failed"):
        A._clone(inst, tmp_path / "clone")


def test_clone_creates_the_remote_tracking_base_ref(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,  # noqa: N803
    submodule_fixture: tuple[Path, Path, str],
) -> None:
    """The reviewer's diff helper runs `git diff origin/<default_branch>...HEAD`,
    which was rc=128 without a remote-tracking ref — the reviewer then saw an
    error string instead of the diff."""
    import subprocess as sp

    main, _sub, sha = submodule_fixture
    monkeypatch.setattr(A, "_clone_url", lambda inst: f"file://{main}")
    inst = {"instance_id": "local__main-abc", "repo": "local/main", "base_commit": sha}
    dest = tmp_path / "clone"
    A._clone(inst, dest)
    ref = sp.run(
        ["git", "-C", str(dest), "rev-parse", "refs/remotes/origin/swebench-base"],
        capture_output=True, text=True,
    )
    assert ref.returncode == 0
    head = sp.run(
        ["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    # Points at the FINAL base commit (after submodule vendoring), so a
    # worktree branched from it diffs empty against it.
    assert ref.stdout.strip() == head
    diff = sp.run(
        ["git", "-C", str(dest), "diff", "origin/swebench-base...HEAD"],
        capture_output=True, text=True,
    )
    assert diff.returncode == 0, diff.stderr
    assert diff.stdout.strip() == "", "base ref must match HEAD — a non-empty diff pollutes review"


def test_vendoring_forces_files_the_superproject_ignores(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """A superproject .gitignore matching files INSIDE a submodule (tracked in
    the submodule's own repo, so its ignores never applied) must not make them
    silently vanish from the vendored tree — that would recreate the
    clone-passes/worktree-fails gap for exactly those paths."""
    import subprocess as sp

    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")

    sub = tmp_path / "upstream-sub"
    _mk_git_repo(sub, {"infogami_mod.py": "VALUE = 1\n", "data.generated": "payload\n"})
    main = tmp_path / "upstream-main"
    # The superproject ignores *.generated — the submodule legitimately tracks one.
    _mk_git_repo(main, {"app.py": "import vendor\n", ".gitignore": "*.generated\n"})
    for args in (
        ["submodule", "add", str(sub), "vendor/infogami"],
        ["commit", "-q", "-m", "add submodule"],
    ):
        sp.run(
            ["git", "-C", str(main), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True, text=True,
        )
    sha = sp.run(
        ["git", "-C", str(main), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    monkeypatch.setattr(A, "_clone_url", lambda inst: f"file://{main}")
    inst = {"instance_id": "local__main-ign", "repo": "local/main", "base_commit": sha}
    dest = tmp_path / "clone"
    A._clone(inst, dest)
    tracked = sp.run(
        ["git", "-C", str(dest), "ls-files", "vendor/infogami/data.generated"],
        capture_output=True, text=True,
    ).stdout.strip()
    assert tracked == "vendor/infogami/data.generated", (
        "ignore-matched submodule file was dropped from the vendored tree"
    )


# --------------------------------------------------------------------------- #
# pre-dispatch collect gate — test_command must WORK, not merely be set
# --------------------------------------------------------------------------- #


def test_collect_only_command_keeps_the_real_environment(A: Any) -> None:  # noqa: N803
    """The gate must test the REAL environment (image + mount), so the collect
    command is the same docker invocation dev runs, plus --collect-only."""
    cmd = A.instance_test_command(_INST, collect_only=True)
    assert "--collect-only -q" in cmd
    assert cmd.startswith("docker run --rm")
    assert '-v "$PWD":/app' in cmd
    assert "jefzda/sweap-images:x.y-abc" in cmd
    # And the default command is unchanged.
    assert "--collect-only" not in A.instance_test_command(_INST)


def test_precheck_fails_loudly_when_collection_fails(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """Mocked at the subprocess boundary: a non-zero collect exit must come
    back as a failure carrying the output tail."""
    from types import SimpleNamespace

    seen: dict[str, Any] = {}

    def fake_run(cmd: Any, **kw: Any) -> Any:
        seen["cmd"], seen["kw"] = cmd, kw
        return SimpleNamespace(
            returncode=2,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'infogami'",
        )

    monkeypatch.setattr(A.subprocess, "run", fake_run)
    ok, tail, duration = A._precheck_collect(_INST, tmp_path)
    assert ok is False
    assert "infogami" in tail
    assert duration >= 0
    assert "--collect-only" in seen["cmd"]
    assert seen["kw"]["shell"] is True, "must run the docker command verbatim"
    assert seen["kw"]["cwd"] == str(tmp_path), "must mount the run's own clone"


def test_precheck_passes_when_collection_succeeds(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        A.subprocess,
        "run",
        lambda cmd, **kw: SimpleNamespace(returncode=0, stdout="12 tests collected", stderr=""),
    )
    ok, tail, _ = A._precheck_collect(_INST, tmp_path)
    assert ok is True
    assert "collected" in tail


# --------------------------------------------------------------------------- #
# audit — a run whose trail is broken or missing must FAIL, not pass
# --------------------------------------------------------------------------- #

_RUNS_DDL = (
    "CREATE TABLE runs (id INTEGER PRIMARY KEY, ts TEXT, persona TEXT, model TEXT, "
    "story_id INTEGER, tokens_in INTEGER, tokens_out INTEGER, "
    "cached_input_tokens INTEGER, cost_usd REAL, duration_s REAL, "
    "success INTEGER, error TEXT)"
)


def _mk_audit_run(
    runs_root: Path,
    *,
    arm: str = "factory",
    rows: list[tuple[Any, ...]] | None = None,
    result: dict[str, Any] | None = None,
    bodies: list[dict[str, Any]] | None = None,
    write_db: bool = True,
    write_bodies: bool = True,
) -> None:
    """Fabricate a run directory shaped like a real one."""
    import sqlite3

    run_dir = runs_root / "inst1" / arm
    state_root = run_dir / "root" if arm == "factory" else run_dir
    (state_root / "state" / "events").mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    default_rows = [
        ("t0", "dev", "m", 1, 100, 10, 0, 1.25, 90.0, 1, None),
        ("t1", "reviewer", "m", 1, 50, 5, 0, 0.75, 30.0, 1, None),
    ]
    if write_db:
        con = sqlite3.connect(state_root / "state" / "factory.db")
        con.execute(_RUNS_DDL)
        con.executemany(
            "INSERT INTO runs (ts, persona, model, story_id, tokens_in, tokens_out, "
            "cached_input_tokens, cost_usd, duration_s, success, error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows if rows is not None else default_rows,
        )
        con.commit()
        con.close()

    if result is None:
        result = {"cost_usd": 2.0, "tokens_in": 150, "tokens_out": 15}
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")

    if write_bodies:
        if bodies is None:
            bodies = [
                {"event": "prompt_body", "persona": "dev", "prompt": "fix it", "prompt_hash": "a" * 16},
                {"event": "prompt_body", "persona": "reviewer", "prompt": "diff --git a/x b/x", "prompt_hash": "b" * 16},
            ]
        (state_root / "state" / "events" / "prompt_bodies.ndjson").write_text(
            "\n".join(json.dumps(b) for b in bodies) + "\n", encoding="utf-8"
        )


def _audit_json(runs_root: Path, arm: str = "factory") -> dict[str, Any]:
    return json.loads((runs_root / "inst1" / arm / "audit.json").read_text(encoding="utf-8"))


def test_audit_passes_a_coherent_run_and_writes_audit_json(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path)
    A.audit("inst1", "factory")  # must not raise
    data = _audit_json(tmp_path)
    assert data["ok"] is True
    assert data["failures"] == []
    assert len(data["persona_calls"]) == 2
    assert data["ledger_cost_usd"] == 2.0


def test_audit_fails_on_cost_mismatch(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The 1.62x under-reporting class: result.json says less than the ledger."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path, result={"cost_usd": 1.25, "tokens_in": 150, "tokens_out": 15})
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("cost mismatch" in f for f in failures), failures


def test_audit_fails_when_a_reviewer_prompt_saw_an_error_instead_of_a_diff(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        bodies=[
            {
                "event": "prompt_body",
                "persona": "reviewer",
                "prompt": "(git diff origin/swebench-base...HEAD returned rc=128; stderr_tail='fatal')",
                "prompt_hash": "c" * 16,
            },
        ],
    )
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("broken-diff markers" in f for f in failures), failures


def test_audit_ignores_error_strings_in_non_reviewer_prompts(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """A dev prompt legitimately quotes test output, which can contain
    arbitrary strings; only the REVIEWER seeing them invalidates the run."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        bodies=[
            {"event": "prompt_body", "persona": "dev",
             "prompt": "prior attempt: command returned rc=1", "prompt_hash": "d" * 16},
            {"event": "prompt_body", "persona": "reviewer",
             "prompt": "diff --git a/x b/x", "prompt_hash": "e" * 16},
        ],
    )
    A.audit("inst1", "factory")  # must not raise
    assert _audit_json(tmp_path)["ok"] is True


def test_audit_fails_when_prompt_bodies_are_missing(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """FAIL SAFE: an unauditable run is an invalid run, not a pass."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path, write_bodies=False)
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("prompt_bodies" in f for f in failures), failures


def test_audit_fails_when_the_run_ledger_is_missing(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path, write_db=False, result={"cost_usd": 0.0})
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("factory.db" in f for f in failures), failures


def test_audit_flags_a_fast_failing_first_dev_run(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """A first dev call that failed in under ~5s never tested anything — the
    unrunnable-environment signature (e.g. ModuleNotFoundError in 0.8s)."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        rows=[("t0", "dev", "m", 1, 10, 1, 0, 0.01, 0.8, 0, "boom")],
        result={"cost_usd": 0.01, "tokens_in": 10, "tokens_out": 1},
    )
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("unrunnable-environment" in f for f in failures), failures


def test_audit_fails_on_empty_result_json(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """`{}` used to skip the whole ledger<->result section via truthiness and
    audit-pass a run that reported nothing. Fail safe instead."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path, result={})
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("empty or not a JSON object" in f for f in failures), failures


def test_audit_fails_on_non_object_result_json(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(tmp_path)
    (tmp_path / "inst1" / "factory" / "result.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("empty or not a JSON object" in f for f in failures), failures


def test_audit_detects_the_worktree_resolution_failure_marker(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The fifth handlers.py fallback string — `(could not resolve writing
    worktree: ...)` — is also an error-instead-of-diff reviewer prompt."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        bodies=[
            {
                "event": "prompt_body",
                "persona": "reviewer",
                "prompt": "(could not resolve writing worktree: OSError('gone'))",
                "prompt_hash": "f" * 16,
            },
        ],
    )
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("broken-diff markers" in f for f in failures), failures


def test_audit_fails_when_reviewer_prompts_were_rotated_away(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The ledger shows a reviewer ran, but zero reviewer prompt bodies are
    scannable (rotated away / never captured): the marker scan finds nothing
    only because there is nothing to scan — silence must not read as clean."""
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        bodies=[
            {"event": "prompt_body", "persona": "dev",
             "prompt": "fix it", "prompt_hash": "a" * 16},
        ],
    )
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("reviewer input is unauditable" in f for f in failures), failures


def test_audit_fails_a_run_with_a_recorded_failed_precheck(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path)
    _mk_audit_run(
        tmp_path,
        rows=[],
        result={
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "precheck": {"collect_ok": False, "duration_s": 0.9},
            "error": "precheck: test command does not collect: ...",
        },
    )
    with pytest.raises(SystemExit, match="audit FAILED"):
        A.audit("inst1", "factory")
    failures = _audit_json(tmp_path)["failures"]
    assert any("precheck" in f for f in failures), failures


def test_story_slug_is_stable_across_processes(A: Any) -> None:  # noqa: N803
    """Was ``abs(hash(instance_id))``, which Python salts per process — every
    run produced a different worktree name, orphaning the previous one, and
    the diff capture could then grade the WRONG run's tree."""
    import subprocess as sp
    import sys as _sys

    code = (
        "import importlib.util,sys;"
        f"spec=importlib.util.spec_from_file_location('A',{str(_ADAPTER)!r});"
        "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
        "print(m._story_slug('instance_x__y-abc'))"
    )
    outs = {
        sp.run(
            [_sys.executable, "-c", code],
            capture_output=True, text=True, check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    assert len(outs) == 1, f"slug varies with PYTHONHASHSEED: {outs}"


# --------------------------------------------------------------------------- #
# run-all — the parallel sweep
#
# Nothing here executes a real sweep: a run costs real money and needs API
# keys. Every test below replaces the child-process layer with a fake, which is
# the correct seam — the whole design is "the parent orchestrates, children do
# the work", so faking the child tests the orchestration and nothing else.
# --------------------------------------------------------------------------- #


class _FakeChild:
    """Stands in for ``_bench_subprocess``: records calls, fabricates artifacts.

    Also measures how many calls were in flight at once, which is the only way
    to prove the pool actually fans out rather than quietly running in series.
    """

    def __init__(self, A: Any, *, fail: dict[str, str] | None = None, delay: float = 0.0):
        self.A = A
        self.fail = fail or {}
        self.delay = delay
        self.calls: list[list[str]] = []
        self.log_paths: list[Path] = []
        self.live = 0
        self.max_live = 0
        self._lock = __import__("threading").Lock()

    def __call__(self, argv: list[str], *, timeout_s: int, log_path: Path) -> tuple[int, str]:
        import time as _time

        with self._lock:
            self.calls.append(list(argv))
            self.log_paths.append(log_path)
            self.live += 1
            self.max_live = max(self.max_live, self.live)
        try:
            if self.delay:
                _time.sleep(self.delay)
            cmd = argv[2]
            iid = argv[argv.index("--instance") + 1]
            arm = argv[argv.index("--arm") + 1]
            mode = self.fail.get(iid)

            if cmd == "run":
                if mode == "raise":
                    raise RuntimeError("worker exploded")
                if mode == "no_image":
                    return 1, "image for X is unavailable"
                if mode == "timeout":
                    return -9, "timeout after 1s"
                d = self.A._run_dir(iid, arm)
                (d / "prediction.diff").write_text("diff --git a/x.py b/x.py\n", encoding="utf-8")
                (d / "result.json").write_text(
                    json.dumps(
                        {
                            "arm": arm,
                            "instance_id": iid,
                            "final_state": "reviewer_done",
                            "tokens_in": 1000,
                            "tokens_out": 100,
                            "cost_usd": 0.5,
                            "factory_says_green": True,
                        }
                    ),
                    encoding="utf-8",
                )
                if mode == "late_fail":
                    # A run that failed LATE: prediction + result already
                    # written, then the run exits non-zero.
                    return 1, "run crashed after writing its prediction"
                return 0, "factory arm done"

            if cmd == "audit":
                d = self.A._run_dir(iid, arm)
                if mode == "audit_fail":
                    (d / "audit.json").write_text(
                        json.dumps(
                            {"ok": False, "failures": ["cost mismatch: ledger vs result.json"]}
                        ),
                        encoding="utf-8",
                    )
                    return 1, "audit FAILED (1 finding(s))"
                # Mirror the real audit's fail-safety: a run that left no
                # result.json is an audit FAILURE, never a pass.
                if not (d / "result.json").exists():
                    (d / "audit.json").write_text(
                        json.dumps({"ok": False, "failures": ["missing artifact: result.json"]}),
                        encoding="utf-8",
                    )
                    return 1, "audit FAILED (missing artifact)"
                (d / "audit.json").write_text(
                    json.dumps({"ok": True, "failures": []}), encoding="utf-8"
                )
                return 0, "audit OK"

            # grade
            if mode == "grade_fail":
                return 2, "docker died"
            d = self.A._run_dir(iid, arm)
            existing = json.loads((d / "result.json").read_text(encoding="utf-8"))
            existing["grade"] = {"oracle_resolved": True, "outcome": "resolved"}
            (d / "result.json").write_text(json.dumps(existing), encoding="utf-8")
            return 0, "graded"
        finally:
            with self._lock:
                self.live -= 1


def _sweep_env(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ids: list[str]
) -> None:
    """Point every path the sweep writes at ``tmp_path`` and pin a manifest."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_sha256": "deadbeef",
                "instances": [{"instance_id": i, "dockerhub_tag": "t"} for i in ids],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(A, "MANIFEST_PATH", manifest)
    monkeypatch.setattr(A, "SWE_DIR", tmp_path)
    monkeypatch.setattr(A, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(A, "load_spend_caps", lambda *a, **k: (1000.0, 10000.0))


_IDS = [f"instance_repo__x-{n}" for n in range(6)]


def test_sweep_fans_out_and_grades_every_instance(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every instance is run AND graded, and the work genuinely overlaps."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    fake = _FakeChild(A, delay=0.05)
    monkeypatch.setattr(A, "_bench_subprocess", fake)

    A.run_all(
        arm="factory", workers=3, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )

    ran = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "run"}
    graded = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "grade"}
    audited = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "audit"}
    assert ran == set(_IDS)
    assert graded == set(_IDS), "grade must follow each run, in the same pool"
    assert audited == set(_IDS), "every instance must be audited, in the same pool"
    assert fake.max_live > 1, "workers ran strictly in series — the pool is not fanning out"

    out = capsys.readouterr().out
    for iid in _IDS:
        assert iid in out
    assert "6 ok, 0 failed" in out
    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    assert summary["instances"] == 6 and summary["resolved"] == 6
    assert summary["audited_valid"] == 6 and summary["audit_failed"] == 0
    assert summary["tokens_in"] == 6000 and summary["tokens_out"] == 600


def test_sweep_runs_children_as_separate_processes(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unsafe work MUST happen behind a process boundary.

    ``run_factory`` sets ``os.environ['FACTORY_STATE_ROOT']``, mutates
    ``sys.path`` and relies on ``factory.settings.loader``'s module-global
    cache. Two of those in one interpreter cross-contaminate, and the losing
    run writes synthetic telemetry into the other's root — or into production
    ``state/``. So the pool must never call ``run_factory`` in-process.
    """
    import sys as _sys

    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    fake = _FakeChild(A)
    monkeypatch.setattr(A, "_bench_subprocess", fake)

    def _boom(*a: Any, **k: Any) -> None:
        raise AssertionError("run_factory called IN-PROCESS — that is not thread-safe")

    monkeypatch.setattr(A, "run_factory", _boom)
    monkeypatch.setattr(A, "run_bare", _boom)
    monkeypatch.setattr(A, "grade", _boom)
    monkeypatch.setattr(A, "audit", _boom)

    A.run_all(
        arm="factory", workers=2, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    assert fake.calls
    for argv in fake.calls:
        assert argv[0] == _sys.executable, argv
        assert argv[1].endswith("swebench_adapter.py"), argv


def test_no_two_workers_write_the_same_path(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic, collision-free result files.

    Two workers sharing a ``result.json`` would let the last writer silently
    win, and the sweep would report a score for a run that never happened.
    """
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    fake = _FakeChild(A)
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=4, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    assert len(fake.log_paths) == len(set(fake.log_paths)), "two workers shared a log path"
    results = sorted((tmp_path / "runs").glob("*/factory/result.json"))
    assert len(results) == len(_IDS)
    assert len({p.parent.parent.name for p in results}) == len(_IDS)


def test_duplicate_instances_are_collapsed(A: Any) -> None:  # noqa: N803
    """The same instance twice would be two workers on one result path."""
    assert A.select_instances(["a", "b"], requested=["a", "a", "b"]) == ["a", "b"]
    assert A.select_instances(["a", "a", "b"]) == ["a", "b"]


def test_requesting_an_unpinned_instance_refuses(A: Any) -> None:  # noqa: N803
    with pytest.raises(SystemExit, match="not in the pinned manifest"):
        A.select_instances(["a", "b"], requested=["a", "zzz"])


# --------------------------------------------------------------------------- #
# --only-working
# --------------------------------------------------------------------------- #


def test_only_working_keeps_instances_with_a_resolving_gold_patch(A: Any) -> None:  # noqa: N803
    """``gold_resolves: None`` means "could not check", which is NOT evidence
    of a working oracle — it must be filtered out just like an explicit
    failure, or a score gets computed over instances nobody validated."""
    working = {"ok1", "ok2"}
    got = A.select_instances(
        ["ok1", "broken", "unchecked", "ok2"], only_working=True, working=working
    )
    assert got == ["ok1", "ok2"]


def test_only_working_reads_selftest_json(A: Any, tmp_path: Path) -> None:  # noqa: N803
    p = tmp_path / "selftest.json"
    p.write_text(
        json.dumps(
            {
                "results": [
                    {"instance_id": "good", "gold_resolves": True},
                    {"instance_id": "bad", "gold_resolves": False},
                    {"instance_id": "unknown", "gold_resolves": None},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert A.selftest_working_instances(p) == {"good"}


def test_only_working_without_a_selftest_refuses(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """Fail SAFE: no control run means we cannot know which oracles work, so
    refuse rather than silently sweep everything."""
    with pytest.raises(SystemExit, match="Run `selftest` first"):
        A.selftest_working_instances(tmp_path / "absent.json")


def test_only_working_with_nothing_left_refuses(A: Any) -> None:  # noqa: N803
    with pytest.raises(SystemExit, match="no instances left after --only-working"):
        A.select_instances(["a", "b"], only_working=True, working=set())


def test_sweep_honours_only_working_end_to_end(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    (tmp_path / "selftest.json").write_text(
        json.dumps(
            {
                "results": [
                    {"instance_id": i, "gold_resolves": i in (_IDS[0], _IDS[3])}
                    for i in _IDS
                ]
            }
        ),
        encoding="utf-8",
    )
    fake = _FakeChild(A)
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=4, instances=None, only_working=True,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    ran = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "run"}
    assert ran == {_IDS[0], _IDS[3]}


# --------------------------------------------------------------------------- #
# failure isolation
# --------------------------------------------------------------------------- #


def test_one_bad_instance_does_not_kill_the_sweep(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A crash, a timeout, a missing image and a failed grade — all four are
    recorded and the other instances still finish."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    fake = _FakeChild(
        A,
        fail={
            _IDS[0]: "raise",
            _IDS[1]: "timeout",
            _IDS[2]: "no_image",
            _IDS[3]: "grade_fail",
        },
    )
    monkeypatch.setattr(A, "_bench_subprocess", fake)

    A.run_all(
        arm="factory", workers=3, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )

    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    assert summary["instances"] == 6, "the sweep must visit every instance"
    assert summary["ok"] == 2 and summary["failed"] == 4
    by_id = {r["instance_id"]: r for r in summary["results"]}
    assert by_id[_IDS[0]]["status"] == "crashed"
    assert "worker exploded" in by_id[_IDS[0]]["error"]
    assert by_id[_IDS[1]]["status"] == "run_failed"
    assert "timeout" in by_id[_IDS[1]]["error"]
    assert by_id[_IDS[2]]["status"] == "run_failed"
    assert by_id[_IDS[3]]["status"] == "grade_failed"
    # The two healthy instances still produced a real graded verdict.
    assert by_id[_IDS[4]]["oracle_resolved"] is True
    assert by_id[_IDS[5]]["outcome"] == "resolved"
    # Audit tri-state: a crashed worker never audits (None); a run that left
    # no result.json FAILS its audit (missing artifact, fail safe); healthy
    # rows pass.
    assert by_id[_IDS[0]]["audit_ok"] is None
    assert by_id[_IDS[1]]["audit_ok"] is False
    assert by_id[_IDS[2]]["audit_ok"] is False
    assert by_id[_IDS[4]]["audit_ok"] is True
    assert summary["audited_valid"] == 3  # grade_failed row still audits clean
    assert summary["audit_failed"] == 2 and summary["not_audited"] == 1
    assert summary["resolved"] == 2
    out = capsys.readouterr().out
    assert "failures (isolated — the sweep continued)" in out


def test_a_failed_run_is_not_graded(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No prediction.diff means nothing to grade; grading anyway would only
    stack a confusing second error on top of the real one."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    fake = _FakeChild(A, fail={_IDS[0]: "no_image"})
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=2, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    graded = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "grade"}
    assert graded == {_IDS[1]}


# --------------------------------------------------------------------------- #
# the per-instance audit gate
#
# Every benchmark run must be fully auditable (the operator's standing
# requirement); the sweep is where that becomes automatic. A row whose audit
# fails is INVALID and must never be silently averaged into a score.
# --------------------------------------------------------------------------- #


def test_a_failed_run_is_still_audited(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit runs UNCONDITIONALLY after run+grade — the real audit treats a
    missing artifact as a finding (fail safe), so skipping it for failed runs
    would let exactly the suspicious rows dodge scrutiny."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    fake = _FakeChild(A, fail={_IDS[0]: "no_image"})
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=2, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    audited = {c[c.index("--instance") + 1] for c in fake.calls if c[2] == "audit"}
    assert audited == set(_IDS[:2]), "failed runs must be audited too"
    # And within one instance, audit is the LAST step.
    order = [c[2] for c in fake.calls if c[c.index("--instance") + 1] == _IDS[1]]
    assert order == ["run", "grade", "audit"]


def test_audit_failure_marks_the_row_invalid(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run can look perfect (green, graded, resolved) and still be invalid —
    the audit found its trail does not support its numbers. The row keeps its
    status but is flagged ``audit_ok: false`` with the reasons, and the
    summary separates audited-valid results from invalid ones."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    fake = _FakeChild(A, fail={_IDS[1]: "audit_fail"})
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=3, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    by_id = {r["instance_id"]: r for r in summary["results"]}
    row = by_id[_IDS[1]]
    assert row["status"] == "ok", "audit failure must not rewrite what the run did"
    assert row["audit_ok"] is False
    assert any("cost mismatch" in f for f in row["audit_failures"])
    assert summary["audited_valid"] == 5 and summary["audit_failed"] == 1
    # The invalid row's oracle pass is visible but flagged — never in the
    # headline number.
    assert summary["resolved"] == 5
    assert summary["resolved_but_audit_failed"] == 1
    out = capsys.readouterr().out
    assert "audit failures (rows are INVALID" in out
    assert "audit: 5 valid, 1 failed" in out


def test_a_sweep_where_every_row_fails_audit_exits_nonzero(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rc=0 means "results are in". A sweep with zero audited-valid rows has
    no results, and anything scripted on top of it must see that."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    fake = _FakeChild(A, fail={i: "audit_fail" for i in _IDS[:2]})
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    with pytest.raises(SystemExit, match="every sweep row FAILED audit"):
        A.run_all(
            arm="factory", workers=2, instances=None, only_working=False,
            max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
        )
    # The summary is still written — it is the evidence of WHY it failed.
    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    assert summary["audit_failed"] == 2 and summary["audited_valid"] == 0
    assert summary["resolved"] == 0


def test_audit_reasons_fall_back_to_child_output(  # noqa: N803
    A: Any, tmp_path: Path
) -> None:
    """An invalid row must always say WHY: if the audit child died without
    writing audit.json, the child's last line is the reason."""
    d = tmp_path / "run"
    d.mkdir()
    assert A._audit_failure_reasons(d, "audit blew up") == ["audit blew up"]
    (d / "audit.json").write_text(
        json.dumps({"ok": False, "failures": ["finding A", "finding B"]}), encoding="utf-8"
    )
    assert A._audit_failure_reasons(d, "ignored") == ["finding A", "finding B"]


def test_resolved_but_run_failed_is_flagged_not_conflated(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that failed LATE can still have written a prediction that
    resolves the oracle (safe to grade only because ``_reset_run_artifacts``
    guarantees the prediction is THIS run's). That pass is recorded — but in
    its own flagged counter, never in the headline ``resolved``."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    fake = _FakeChild(A, fail={_IDS[0]: "late_fail"})
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    A.run_all(
        arm="factory", workers=2, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )
    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    by_id = {r["instance_id"]: r for r in summary["results"]}
    assert by_id[_IDS[0]]["status"] == "run_failed"
    assert by_id[_IDS[0]]["oracle_resolved"] is True, "the late prediction WAS graded"
    assert summary["resolved"] == 1, "only the clean run counts"
    assert summary["resolved_but_run_failed"] == 1
    out = capsys.readouterr().out
    assert "resolved but run FAILED" in out


def test_bench_subprocess_turns_a_timeout_into_a_return_code(  # noqa: N803
    A: Any, tmp_path: Path
) -> None:
    """A wedged child must become a row in the summary, not an exception that
    unwinds the pool."""
    import sys as _sys

    log = tmp_path / "t.log"
    rc, tail = A._bench_subprocess(
        [_sys.executable, "-c", "import time; time.sleep(30)"], timeout_s=1, log_path=log
    )
    assert rc == -9
    assert "timeout" in tail
    assert "TIMEOUT" in log.read_text(encoding="utf-8")


def test_bench_subprocess_leaves_no_orphan_after_a_timeout(  # noqa: N803
    A: Any, tmp_path: Path
) -> None:
    """A timed-out child must be DEAD, not detached.

    ``subprocess.run(timeout=…)`` kills only the direct child; a ``run`` child
    spawns git, pytest and an OpenHands agent, and an orphaned dev run keeps
    calling the model — i.e. keeps spending, unattended. Killing the process
    GROUP is the fix, and this asserts the grandchild dies too.
    """
    import os as _os
    import sys as _sys

    marker = tmp_path / "grandchild.pid"
    script = (
        "import os,subprocess,sys,time;"
        f"p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']);"
        f"open({str(marker)!r},'w').write(str(p.pid));"
        "time.sleep(120)"
    )
    rc, _ = A._bench_subprocess(
        [_sys.executable, "-c", script], timeout_s=3, log_path=tmp_path / "t.log"
    )
    assert rc == -9
    grandchild = int(marker.read_text())
    for _ in range(50):
        try:
            _os.kill(grandchild, 0)
        except OSError:
            break
        __import__("time").sleep(0.1)
    else:
        _os.kill(grandchild, 9)
        pytest.fail(f"grandchild {grandchild} survived the timeout — orphaned spend")


def test_abort_all_kills_running_children(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """``abort_all`` is what makes Ctrl-C actually stop the spend."""
    import sys as _sys
    import threading as _threading
    import time as _time

    result: list[tuple[int, str]] = []

    def _worker() -> None:
        result.append(
            A._bench_subprocess(
                [_sys.executable, "-c", "import time; time.sleep(120)"],
                timeout_s=300,
                log_path=tmp_path / "a.log",
            )
        )

    t = _threading.Thread(target=_worker)
    t.start()
    try:
        for _ in range(50):  # wait for the child to register as live
            if A._LIVE_CHILDREN:
                break
            _time.sleep(0.1)
        assert A._LIVE_CHILDREN, "child never registered; abort could not reach it"
        started = _time.monotonic()
        assert A.abort_all() == 1
        t.join(timeout=30)
        assert not t.is_alive()
        assert _time.monotonic() - started < 30, "abort did not actually stop the child"
        assert A._ABORT.is_set()
        # A queued instance must not start once abort is set.
        assert A._bench_subprocess(["/bin/true"], timeout_s=5, log_path=tmp_path / "b.log") == (
            -2,
            "aborted before start",
        )
    finally:
        A._ABORT.clear()
        t.join(timeout=5)
    assert result and result[0][0] != 0


def test_interrupt_writes_a_partial_summary_and_stops(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ctrl-C mid-sweep: kill the children, keep what finished, do not raise."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    killed: list[int] = []
    monkeypatch.setattr(A, "abort_all", lambda: (killed.append(1), 2)[1])

    fake = _FakeChild(A)
    real_call = fake.__call__

    def _interrupting(argv: list[str], **kw: Any) -> tuple[int, str]:
        if argv[argv.index("--instance") + 1] == _IDS[2] and argv[2] == "run":
            raise KeyboardInterrupt
        return real_call(argv, **kw)

    monkeypatch.setattr(A, "_bench_subprocess", _interrupting)

    A.run_all(  # must NOT propagate
        arm="factory", workers=1, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
    )

    assert killed, "the interrupt handler did not abort in-flight children"
    out = capsys.readouterr().out
    assert "INTERRUPTED" in out
    summary = json.loads((tmp_path / "sweep-factory.json").read_text(encoding="utf-8"))
    # The two that completed before the interrupt are kept, not thrown away.
    assert summary["ok"] == 2
    assert any(r["status"] == "aborted" for r in summary["results"])


def test_bench_subprocess_survives_an_unspawnable_command(A: Any, tmp_path: Path) -> None:  # noqa: N803
    rc, tail = A._bench_subprocess(
        ["/nonexistent/binary/xyzzy"], timeout_s=5, log_path=tmp_path / "s.log"
    )
    assert rc == -1
    assert "Error" in tail or "error" in tail


# --------------------------------------------------------------------------- #
# the spend guard
# --------------------------------------------------------------------------- #


def test_caps_come_from_factory_settings(A: Any, tmp_path: Path) -> None:  # noqa: N803
    p = tmp_path / "factory_settings.yaml"
    p.write_text("caps:\n  hourly_spend_usd: 40\n  daily_spend_usd: 300\n", encoding="utf-8")
    assert A.load_spend_caps(p) == (40.0, 300.0)


def test_unreadable_settings_fall_back_to_the_TIGHT_caps(A: Any, tmp_path: Path) -> None:  # noqa: N803
    """Fail SAFE. A guard that cannot read its limits must assume the strict
    ones — treating a missing file as "no cap" is how an unattended sweep
    spends four figures."""
    assert A.load_spend_caps(tmp_path / "absent.yaml") == (2.0, 10.0)
    bad = tmp_path / "broken.yaml"
    bad.write_text("caps: [this is not a mapping\n", encoding="utf-8")
    assert A.load_spend_caps(bad) == (2.0, 10.0)


def test_a_small_sweep_is_allowed(A: Any) -> None:  # noqa: N803
    """6 instances at $3 is $18 total: it cannot breach a $40/h cap however
    many workers run it, because the whole sweep costs less than the cap."""
    total, peak, refusal = A.spend_guard(
        n_instances=6, workers=4, usd_per_instance=3.0, hours_per_instance=0.05,
        hourly_cap=40.0, daily_cap=300.0,
    )
    assert refusal is None
    assert total == 18.0 and peak == 18.0


def test_a_big_parallel_sweep_is_refused_on_the_hourly_cap(A: Any) -> None:  # noqa: N803
    total, peak, refusal = A.spend_guard(
        n_instances=100, workers=4, usd_per_instance=3.0, hours_per_instance=0.05,
        hourly_cap=40.0, daily_cap=1000.0,
    )
    assert refusal is not None
    assert "hourly_spend_usd" in refusal
    assert peak > 40.0 and total == 300.0


def test_the_daily_cap_is_checked_too(A: Any) -> None:  # noqa: N803
    _, _, refusal = A.spend_guard(
        n_instances=100, workers=1, usd_per_instance=3.0, hours_per_instance=0.05,
        hourly_cap=10_000.0, daily_cap=250.0,
    )
    assert refusal is not None and "daily_spend_usd" in refusal


def test_refusal_says_when_fewer_workers_would_not_help(A: Any) -> None:  # noqa: N803
    """An instance costing $60/h all by itself is not a parallelism problem.
    Advising "--workers 0" would be nonsense; say the true thing instead."""
    _, _, refusal = A.spend_guard(
        n_instances=100, workers=8, usd_per_instance=3.0, hours_per_instance=0.05,
        hourly_cap=40.0, daily_cap=1000.0,
    )
    assert refusal is not None
    assert "even ONE worker" in refusal
    assert "--workers 0" not in refusal


def test_refusal_suggests_a_worker_count_that_fits(A: Any) -> None:  # noqa: N803
    _, _, refusal = A.spend_guard(
        n_instances=100, workers=16, usd_per_instance=1.0, hours_per_instance=0.25,
        hourly_cap=12.0, daily_cap=1000.0,
    )
    assert refusal is not None and "--workers 3" in refusal


def test_sweep_refuses_to_start_over_cap_and_spends_nothing(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The refusal must happen BEFORE the pool starts. A guard that fires after
    the first worker has already burned $3 is not a guard."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    monkeypatch.setattr(A, "load_spend_caps", lambda *a, **k: (0.5, 1.0))
    fake = _FakeChild(A)
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    with pytest.raises(SystemExit, match="REFUSING TO START"):
        A.run_all(
            arm="factory", workers=4, instances=None, only_working=False,
            max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
        )
    assert fake.calls == [], "the guard let work start before refusing"


def test_force_over_cap_is_explicit_and_loud(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exceeding a cap is allowed only by a deliberate flag, and never quietly."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS[:2])
    monkeypatch.setattr(A, "load_spend_caps", lambda *a, **k: (0.5, 1.0))
    monkeypatch.setattr(A, "_bench_subprocess", _FakeChild(A))
    A.run_all(
        arm="factory", workers=2, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=True,
    )
    out = capsys.readouterr().out
    assert "WARNING" in out and "proceeding over cap" in out


def test_cost_estimate_prefers_measured_runs_and_errs_high(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gate on the real artifact: use what prior runs actually cost. Take the
    MAX cost and the MIN duration, because both push the projected burn rate
    up, which is the fail-safe direction for a guard that refuses."""
    runs = tmp_path / "runs"
    for n, (cost, wall) in enumerate([(1.0, 600.0), (4.0, 120.0)]):
        d = runs / f"inst{n}" / "factory"
        d.mkdir(parents=True)
        (d / "result.json").write_text(
            json.dumps({"cost_usd": cost, "wall_clock_s": wall}), encoding="utf-8"
        )
    monkeypatch.setattr(A, "RUNS_DIR", runs)
    usd, hours, source = A.estimate_instance_cost("factory")
    assert usd == 4.0
    assert hours == pytest.approx(120.0 / 3600.0)
    assert "measured" in source

    # No prior runs for this arm -> the documented conservative default.
    usd, hours, source = A.estimate_instance_cost("bare")
    assert usd == A._DEFAULT_COST_USD["bare"]
    assert "default" in source


# --------------------------------------------------------------------------- #
# readable interleaved output
# --------------------------------------------------------------------------- #


def test_progress_lines_never_interleave_partially(A: Any) -> None:  # noqa: N803
    """Workers finish concurrently, so the ONLY guarantee that matters is that
    a line is written whole. Assert it at the write layer: every ``_emit`` must
    reach stdout as a single ``write`` call."""
    import threading as _threading

    writes: list[str] = []

    class _Spy:
        def write(self, s: str) -> int:
            writes.append(s)
            return len(s)

        def flush(self) -> None:
            pass

    import sys as _sys

    real, _sys.stdout = _sys.stdout, _Spy()  # type: ignore[assignment]
    try:
        threads = [
            _threading.Thread(target=A._emit, args=(f"line-{i}" * 20,)) for i in range(40)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        _sys.stdout = real
    assert len(writes) == 40, "a line was split across multiple writes"
    assert all(w.endswith("\n") and w.count("\n") == 1 for w in writes)


def test_progress_line_reports_the_four_required_fields(A: Any) -> None:  # noqa: N803
    line = A._progress_line(
        3,
        6,
        {
            "instance_id": "instance_qutebrowser__qutebrowser-0833b5f6",
            "status": "ok",
            "final_state": "reviewer_done",
            "tokens_in": 560580,
            "tokens_out": 4998,
            "oracle_resolved": True,
            "outcome": "resolved",
            "sweep_wall_s": 102.7,
        },
    )
    assert "\n" not in line
    assert "instance_qutebrowser__qutebrowser-0833b5f6" in line
    assert "reviewer_done" in line
    assert "560,580" in line and "4,998" in line
    assert "PASS" in line and "resolved" in line
    assert "[  3/6" in line


def test_cli_wires_run_all_through(A: Any, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    """Guards against argparse drift — a flag that parses but reaches nothing."""
    seen: dict[str, Any] = {}
    monkeypatch.setattr(A, "_load_env", lambda: None)
    monkeypatch.setattr(A, "run_all", lambda **kw: seen.update(kw))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "swebench_adapter.py", "run-all", "--arm", "bare", "--workers", "7",
            "--instances", "a, b ,", "--only-working", "--force-over-cap",
            "--timeout-s", "11", "--grade-timeout-s", "12", "--max-steps", "3",
            "--dry-run",
        ],
    )
    A.main()
    assert seen == {
        "arm": "bare",
        "workers": 7,
        "instances": ["a", "b"],
        "only_working": True,
        "max_steps": 3,
        "run_timeout_s": 11,
        "grade_timeout_s": 12,
        "force_over_cap": True,
        "dry_run": True,
    }


def test_cli_run_all_defaults_are_safe(A: Any, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: N803
    """Never over-cap by default, and never invent an instance list."""
    seen: dict[str, Any] = {}
    monkeypatch.setattr(A, "_load_env", lambda: None)
    monkeypatch.setattr(A, "run_all", lambda **kw: seen.update(kw))
    monkeypatch.setattr(sys, "argv", ["swebench_adapter.py", "run-all"])
    A.main()
    assert seen["force_over_cap"] is False
    assert seen["only_working"] is False
    assert seen["instances"] is None
    assert seen["arm"] == "factory"
    assert seen["dry_run"] is False


# --------------------------------------------------------------------------- #
# --dry-run must be a PURE preview
# --------------------------------------------------------------------------- #


def test_dry_run_spawns_nothing_and_writes_nothing(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """This repo has been bitten by a "dry-run" that did real work (pm-sync,
    2026-07-20 — it spawned live dispatchable stories). Assert the absence of
    side effects, not just the presence of output."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    fake = _FakeChild(A)
    monkeypatch.setattr(A, "_bench_subprocess", fake)
    before = sorted(p.name for p in tmp_path.iterdir())

    A.run_all(
        arm="factory", workers=3, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
        dry_run=True,
    )

    assert fake.calls == []
    assert sorted(p.name for p in tmp_path.iterdir()) == before, "dry-run wrote to disk"
    assert not (tmp_path / "runs").exists(), "dry-run created run directories"
    assert not (tmp_path / "sweep-factory.json").exists()
    out = capsys.readouterr().out
    assert "nothing was executed and nothing was written" in out
    for iid in _IDS:
        assert iid in out


def test_dry_run_previews_a_refusal_instead_of_raising(  # noqa: N803
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """You must be able to preview a sweep that would be refused — that is
    exactly when you most want to see the numbers."""
    _sweep_env(A, tmp_path, monkeypatch, _IDS)
    monkeypatch.setattr(A, "load_spend_caps", lambda *a, **k: (0.5, 1.0))
    monkeypatch.setattr(A, "_bench_subprocess", _FakeChild(A))
    A.run_all(
        arm="factory", workers=4, instances=None, only_working=False,
        max_steps=1, run_timeout_s=10, grade_timeout_s=10, force_over_cap=False,
        dry_run=True,
    )
    out = capsys.readouterr().out
    assert "WOULD REFUSE TO START" in out


def test_progress_line_surfaces_a_failure(A: Any) -> None:  # noqa: N803
    line = A._progress_line(
        1,
        2,
        {
            "instance_id": "instance_x",
            "status": "run_failed",
            "error": "image unavailable",
            "final_state": "—",
            "tokens_in": 0,
            "tokens_out": 0,
            "oracle_resolved": None,
            "outcome": "—",
            "sweep_wall_s": 1.0,
        },
    )
    assert "!run_failed" in line and "image unavailable" in line
    assert "\n" not in line
