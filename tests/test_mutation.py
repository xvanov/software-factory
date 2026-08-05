"""Diff-scoped mutation scoring — the rewrite of the ablation branch.

Each test here corresponds to one of the four defects the old
``tests_meaningful`` ablation branch had. All four were reproduced against the
old code before it was deleted; the reproductions are recorded in the module
docstring of ``factory/chain/gates/tests_meaningful.py``. These tests pin the
behaviour that replaced them, so a regression cannot re-open any of them
silently.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from factory.chain import mutation
from factory.chain.mutation import (
    GREEN,
    INFRA,
    RED,
    STATUS_BASELINE_INFRA,
    STATUS_BASELINE_RED,
    STATUS_MEASURED,
    STATUS_NO_REPO,
    STATUS_NO_SYMBOLS,
    STATUS_NO_TEST_COMMAND,
    _run_suite,
    cache_path,
    measure,
    mutate_source,
    select_symbols,
)

PY = sys.executable
PYTEST_CMD = f"{PY} -m pytest -q"


# --------------------------------------------------------------------------- #
# Fixtures: real two-commit git repos
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return proc.stdout


def _init(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")


_Z_LAST_OLD = (
    "def target():\n"
    "    # CANARY-COMMENT do not strip me\n"
    "    return 'old'\n"
    "\n\n"
    "def untouched():\n"
    "    return 0\n"
)
_Z_LAST_NEW = _Z_LAST_OLD.replace("'old'", "'new'")


def _repo(
    tmp_path: Path,
    *,
    exercised: bool = True,
    red: bool = False,
) -> tuple[Path, str]:
    """A repo shaped like the ``e13d98e0`` case: the diff touches ONE symbol in
    the alphabetically-LAST file, while the alphabetically-FIRST file is
    untouched and full of public symbols.

    ``exercised`` controls whether the suite asserts on the touched symbol —
    i.e. whether its mutant should be killed or survive.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    (repo / "conftest.py").write_text("", encoding="utf-8")
    (repo / "a_first.py").write_text(
        "\n\n".join(f"def alpha{i}():\n    return {i}" for i in range(1, 7)) + "\n",
        encoding="utf-8",
    )
    (repo / "z_last.py").write_text(_Z_LAST_OLD, encoding="utf-8")
    (repo / "tests").mkdir()
    body = [
        "from a_first import alpha1, alpha2, alpha3, alpha4, alpha5, alpha6",
        "from z_last import target, untouched",
        "",
        "def test_alphas():",
        "    assert [alpha1(), alpha2(), alpha3(), alpha4(), alpha5(), alpha6()] == "
        "[1, 2, 3, 4, 5, 6]",
        "",
        "def test_untouched():",
        "    assert untouched() == 0",
    ]
    if exercised:
        body += ["", "def test_target():", "    assert target() == 'new'"]
    else:
        # Imports the symbol (so the module loads) but never calls it.
        body += ["", "def test_target_is_importable():", "    assert callable(target)"]
    if red:
        body += ["", "def test_broken():", "    assert False"]
    (repo / "tests" / "test_all.py").write_text("\n".join(body) + "\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "story")

    # HEAD commit: change ONLY z_last.target's body.
    (repo / "z_last.py").write_text(_Z_LAST_NEW, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _measure(
    repo: Path,
    head: str,
    tmp_path: Path,
    test_command: str = PYTEST_CMD,
    **kwargs: object,
) -> mutation.MutationReport:
    return measure(
        repo_root=repo,
        head_sha=head,
        base_branch="main",
        test_command=test_command,
        app="toy",
        software_factory_root=tmp_path / "factory-root",
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# Defect 1 — selection must follow the diff
# --------------------------------------------------------------------------- #


def test_selection_is_scoped_to_the_diff_hunks(tmp_path: Path) -> None:
    """The old selector enumerated every public symbol of every changed file and
    took the first five by ``(path, lineno)`` — on this fixture:
    ``a_first.py::alpha1..alpha5``, zero overlap with what changed."""
    repo, head = _repo(tmp_path)
    selection = select_symbols(repo, "main", head)
    assert selection is not None
    sample, candidates, _notes = selection
    assert [s.key for s in sample] == ["z_last.py::target"]
    assert candidates == 1


def test_selection_ignores_test_code_and_collection_channels(tmp_path: Path) -> None:
    """Path classification is delegated to ``factory.diff_paths``; a diff in a
    test file or in ``pyproject.toml`` yields no ablation candidate."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_x.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (repo / "conftest.py").write_text("def pytest_configure(config):\n    return None\n", "utf-8")
    (repo / "pyproject.toml").write_text("[tool.x]\na = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "story")
    (repo / "tests" / "test_x.py").write_text(
        "def test_a():\n    assert 1 == 1\n", encoding="utf-8"
    )
    (repo / "conftest.py").write_text(
        "def pytest_configure(config):\n    return True\n", encoding="utf-8"
    )
    (repo / "pyproject.toml").write_text("[tool.x]\na = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD").strip()

    selection = select_symbols(repo, "main", head)
    assert selection is not None
    sample, candidates, _notes = selection
    assert sample == [] and candidates == 0


def test_selection_skips_bodies_that_are_already_no_ops(tmp_path: Path) -> None:
    """An ``...``/``pass``/``raise NotImplementedError`` body produces a mutant
    identical to the original — the suite CANNOT go red, so reporting it
    "survived" would be a finding from a measurement that never happened."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    (repo / "m.py").write_text("def stub():\n    ...\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "story")
    (repo / "m.py").write_text(
        "def stub():\n    ...\n\n\ndef real():\n    return 1\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD").strip()

    (repo / "m.py").write_text(
        "def stub():\n    pass\n\n\ndef real():\n    return 1\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head2")
    head = _git(repo, "rev-parse", "HEAD").strip()

    selection = select_symbols(repo, "main", head)
    assert selection is not None
    sample, _candidates, notes = selection
    assert [s.key for s in sample] == ["m.py::real"]
    assert any("equivalent mutant" in n for n in notes)


def test_selection_ranks_the_most_changed_symbol_first(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    (repo / "m.py").write_text(
        "def small():\n    return 1\n\n\ndef big():\n    return 2\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "story")
    (repo / "m.py").write_text(
        "def small():\n    return 11\n\n\ndef big():\n"
        + "".join(f"    x{i} = {i}\n" for i in range(8))
        + "    return 22\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    head = _git(repo, "rev-parse", "HEAD").strip()

    selection = select_symbols(repo, "main", head, max_symbols=1)
    assert selection is not None
    sample, candidates, _notes = selection
    assert [s.key for s in sample] == ["m.py::big"]
    assert candidates == 2


# --------------------------------------------------------------------------- #
# Defect 2 — no green baseline, and infra read as "exercised"
# --------------------------------------------------------------------------- #


def test_broken_test_command_never_certifies_coverage(tmp_path: Path) -> None:
    """The old gate answered "ablation: all 2 sampled symbol(s) exercised by
    tests" when ``test_command`` was a nonexistent binary."""
    repo, head = _repo(tmp_path)
    report = _measure(repo, head, tmp_path, test_command="definitely-not-a-command-xyz")
    assert report.status == STATUS_BASELINE_INFRA
    assert report.score is None
    assert report.baseline == INFRA
    assert report.killed == [] and report.survived == []


def test_an_already_red_suite_never_certifies_coverage(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path, red=True)
    report = _measure(repo, head, tmp_path)
    assert report.status == STATUS_BASELINE_RED
    assert report.score is None
    assert "baseline suite is red" in report.reason


def test_pytest_internal_error_is_infra_not_a_red(tmp_path: Path) -> None:
    """pytest exits 2/3/4/5 for interrupted / internal error / usage error / no
    tests collected. None of those is a test failure, and none may read as
    "the suite noticed"."""
    repo, head = _repo(tmp_path)
    report = _measure(repo, head, tmp_path, test_command="exit 5")
    assert report.status == STATUS_BASELINE_INFRA
    assert report.score is None


def test_a_timeout_is_infra_not_a_red(tmp_path: Path) -> None:
    """``_run_pytest`` returned ``False`` on a 600 s timeout, indistinguishable
    from a genuine failure. Three outcomes, not two."""
    outcome, output = _run_suite(tmp_path, f"{PY} -c \"import time; time.sleep(30)\"", 1)
    assert outcome == INFRA
    assert "timed out" in output


def test_run_suite_distinguishes_green_red_infra(tmp_path: Path) -> None:
    assert _run_suite(tmp_path, "exit 0", 30)[0] == GREEN
    assert _run_suite(tmp_path, "exit 1", 30)[0] == RED
    assert _run_suite(tmp_path, "exit 127", 30)[0] == INFRA


def test_a_red_we_cannot_attribute_is_skipped_not_killed(tmp_path: Path) -> None:
    """A run that goes red for a reason other than the mutation must not be
    scored as a kill. Here the second invocation of the "suite" fails without
    ever importing the mutated module."""
    repo, head = _repo(tmp_path)
    counter = tmp_path / "invocations"
    cmd = (
        f'{PY} -c "import pathlib,sys; p=pathlib.Path({str(counter)!r}); '
        "n=int(p.read_text()) if p.exists() else 0; p.write_text(str(n + 1)); "
        'sys.exit(1 if n >= 1 else 0)"'
    )
    report = _measure(repo, head, tmp_path, test_command=cmd)
    assert report.status == STATUS_MEASURED
    assert report.baseline == GREEN
    assert report.killed == [] and report.survived == []
    assert report.score is None
    assert any("not attributable" in s["why"] for s in report.skipped)


# --------------------------------------------------------------------------- #
# Defect 3 — the live checkout must never be written to
# --------------------------------------------------------------------------- #


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


def test_the_source_checkout_is_never_written_to(tmp_path: Path) -> None:
    """The old branch mutated ``repo_root`` — the very checkout the chain pushes
    from — and restored it in a ``finally``. Nothing outside the scratch tree
    may be touched at all, not even its mtimes."""
    repo, head = _repo(tmp_path)
    seen = tmp_path / "seen.py"
    cmd = (
        f'{PY} -c "import shutil; shutil.copy(\'z_last.py\', {str(seen)!r})"'
        f" && {PYTEST_CMD}"
    )
    before = _snapshot(repo)
    report = _measure(repo, head, tmp_path, test_command=cmd)
    assert _snapshot(repo) == before, "the source checkout was written to"

    # ...and the mutation really did reach the suite, in the scratch tree.
    assert seen.exists(), "the suite never ran"
    mutated = seen.read_text(encoding="utf-8")
    assert "NotImplementedError" in mutated
    # Defect 3's other half: the ast.unparse round-trip stripped every comment.
    assert "CANARY-COMMENT" in mutated, "the mutation stripped comments"
    assert report.tree_source.startswith("git-clone")


def test_mutate_source_only_rewrites_the_target_body() -> None:
    source = (
        "import os  # keep me\n"
        "\n\n"
        "def before():\n"
        "    return 1  # also keep me\n"
        "\n\n"
        "class Widget:\n"
        "    # a comment inside the class\n"
        "    def render(self):\n"
        "        # the body we replace\n"
        "        return 'x'\n"
        "\n"
        "    def other(self):\n"
        "        return 'y'\n"
    )
    out = mutate_source(source, "Widget.render", sentinel=Path("/tmp/sentinel"))
    assert out is not None
    assert "import os  # keep me" in out
    assert "return 1  # also keep me" in out
    assert "# a comment inside the class" in out
    assert "def other(self):\n        return 'y'" in out
    # Only STATEMENTS are replaced, so a comment leading the body survives too —
    # the point is that nothing outside the target's statements is rewritten.
    assert "# the body we replace" in out
    assert "return 'x'" not in out
    assert "NotImplementedError('FACTORY_ABLATION Widget.render')" in out
    # Still valid Python and still the same set of definitions.
    import ast

    tree = ast.parse(out)
    assert [n.name for n in tree.body if hasattr(n, "name")] == ["before", "Widget"]


def test_mutate_source_handles_a_one_line_def() -> None:
    out = mutate_source("def f(): return 1\n", "f", sentinel=Path("/tmp/s"))
    assert out is not None and out.startswith("def f(): __import__")
    import ast

    ast.parse(out)


def test_mutate_source_returns_none_for_an_unknown_symbol() -> None:
    assert mutate_source("def f():\n    return 1\n", "nope", sentinel=Path("/tmp/s")) is None


# --------------------------------------------------------------------------- #
# The measurement itself
# --------------------------------------------------------------------------- #


def test_an_unexercised_symbol_survives_and_scores_zero(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path, exercised=False)
    report = _measure(repo, head, tmp_path)
    assert report.status == STATUS_MEASURED
    assert report.baseline == GREEN
    assert report.survived == ["z_last.py::target"]
    assert report.killed == []
    assert report.score == 0.0


def test_an_exercised_symbol_is_killed_and_scores_one(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path, exercised=True)
    report = _measure(repo, head, tmp_path)
    assert report.status == STATUS_MEASURED
    assert report.killed == ["z_last.py::target"]
    assert report.survived == []
    assert report.score == 1.0


def test_survived_says_whether_the_symbol_was_even_reached(tmp_path: Path) -> None:
    """"Never invoked" and "invoked but not asserted on" are different kinds of
    illusory coverage; the sentinel tells them apart."""
    repo, head = _repo(tmp_path, exercised=False)
    report = _measure(repo, head, tmp_path)
    assert report.survived == ["z_last.py::target"]
    cached = json.loads(cache_path(tmp_path / "factory-root", "toy", head).read_text())
    assert cached["symbols"]["z_last.py::target"]["detail"] == "never invoked by the suite"


def test_no_symbols_when_the_diff_touches_no_production_code(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-qb", "docs")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "docs")
    head = _git(repo, "rev-parse", "HEAD").strip()
    report = _measure(repo, head, tmp_path)
    assert report.status == STATUS_NO_SYMBOLS
    assert report.score is None


def test_missing_preconditions_are_reported_not_guessed(tmp_path: Path) -> None:
    assert (
        measure(
            repo_root=None, head_sha="x", base_branch="main", test_command="pytest"
        ).status
        == STATUS_NO_REPO
    )
    assert (
        measure(
            repo_root=tmp_path, head_sha="x", base_branch="main", test_command=None
        ).status
        == STATUS_NO_TEST_COMMAND
    )


def test_head_sha_that_does_not_resolve_falls_back_and_says_so(tmp_path: Path) -> None:
    repo, _head = _repo(tmp_path)
    report = _measure(repo, "deadbeef" * 5, tmp_path)
    assert any("used HEAD" in n for n in report.notes)
    assert report.status == STATUS_MEASURED


# --------------------------------------------------------------------------- #
# The cache — without it the gate could not be afforded at all
# --------------------------------------------------------------------------- #


def test_the_cache_makes_a_second_measurement_free(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path)
    first = _measure(repo, head, tmp_path)
    assert first.cache_hits == 0
    assert first.tree_source.startswith("git-clone")

    cache_file = cache_path(tmp_path / "factory-root", "toy", head)
    assert cache_file.is_file()
    stored = json.loads(cache_file.read_text(encoding="utf-8"))
    assert stored["symbols"]["z_last.py::target"]["outcome"] == "killed"

    started = time.monotonic()
    second = _measure(repo, head, tmp_path)
    elapsed = time.monotonic() - started
    assert second.cache_hits == 1
    assert second.tree_source == "cache"
    assert second.score == first.score
    # No tree materialized and no suite run: the whole point of the cache.
    assert elapsed < first.elapsed_s


def test_the_cache_is_keyed_on_the_head_sha(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path)
    _measure(repo, head, tmp_path)
    (repo / "z_last.py").write_text(_Z_LAST_NEW + "\n# another change\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head2")
    head2 = _git(repo, "rev-parse", "HEAD").strip()
    report = _measure(repo, head2, tmp_path)
    assert report.cache_hits == 0, "a new commit must be re-measured"


def test_a_non_green_baseline_never_populates_the_cache(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path, red=True)
    report = _measure(repo, head, tmp_path)
    assert report.status == STATUS_BASELINE_RED
    assert not cache_path(tmp_path / "factory-root", "toy", head).exists()


def test_no_cache_forces_a_re_measurement(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path)
    _measure(repo, head, tmp_path)
    report = _measure(repo, head, tmp_path, use_cache=False)
    assert report.cache_hits == 0
    assert report.score == 1.0


def test_the_budget_truncates_instead_of_blocking(tmp_path: Path) -> None:
    repo, head = _repo(tmp_path)
    report = _measure(repo, head, tmp_path, budget_s=0)
    assert report.budget_exhausted
    assert report.score is None
    assert report.skipped == [{"symbol": "z_last.py::target", "why": "budget_exhausted"}]


# --------------------------------------------------------------------------- #
# Coupling that must fail loudly rather than degrade
# --------------------------------------------------------------------------- #


def test_the_base_ref_resolver_is_the_chain_s_own(tmp_path: Path) -> None:
    """``_resolve_base_ref`` deliberately imports the chain's single
    implementation instead of growing a second copy. The import is not
    defensive: if it is renamed, this fails loudly here rather than turning
    every measurement into a silent ``skipped``."""
    from factory.chain.handlers import _resolve_diff_base  # noqa: F401

    repo, _head = _repo(tmp_path)
    assert mutation._resolve_base_ref(repo, "main") == "main"
    assert mutation._resolve_base_ref(repo, "no-such-branch") is None


def test_no_gate_imports_the_mutation_module() -> None:
    """The structural guarantee that keeps this advisory: there is no path from
    a merge decision to this code. If a gate ever imports it, that is a
    deliberate decision an operator must make, not a drive-by edit."""
    gates_dir = Path(mutation.__file__).parent / "gates"
    offenders = [
        p.name
        for p in gates_dir.glob("*.py")
        if "chain.mutation" in p.read_text(encoding="utf-8")
        or "chain import mutation" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"gates importing the mutation measurement: {offenders}"


@pytest.mark.parametrize("status", [STATUS_BASELINE_RED, STATUS_BASELINE_INFRA])
def test_skipped_statuses_never_carry_a_score(status: str) -> None:
    report = mutation.MutationReport(status=status, reason="x")
    assert report.score is None
    assert not report.measured
