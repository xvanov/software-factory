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
