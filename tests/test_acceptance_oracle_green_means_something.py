"""The acceptance oracle's GREEN must mean something (2026-08-05).

PR #236 made the oracle executable. An adversarial review then found that the two
properties which make its green mean anything were the two things nothing checked:

* **D1** — nothing verified the oracle CAN FAIL. ``def test_ac1(): assert True``
  was stored, ran, reported "1 passed" and produced a merge-AUTHORITATIVE green
  against an implementation that violated the criterion.
* **H1/H2** — the oracle ran under collection config the DEV controls. Two 7-line
  attacks (a ``pytest_runtest_call`` hookwrapper; ``addopts = "-p _fixup"``)
  forced a pass.
* **D2** — the gate never checked it was testing the merge candidate.

Plus H3 (a forgeable "N passed" count), H4 (a destructive sweep, a
``.pytest_cache`` leak), D3/H6 (a permanent wedge with a lying message, and
exhaustion nobody surfaces).

Every test here FAILED before the fix. The tests are written against real git
repositories on purpose: the fix is "grade the merge candidate in a tree the diff
does not control", which is not expressible against a bare directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from factory.app_config import AppConfig, AppGatesConfig
from factory.chain import red_green
from factory.chain.acceptance import (
    _AUTHOR_ATTEMPTS,
    _MAX_AUTHOR_PASSES,
    ORACLE_COPY_PREFIX,
    acceptance_dir,
    author_passes,
    oracle_sha256,
    pending_acceptance_attention,
    reauthor_missing_oracles,
    sweep_leaked_oracles,
    write_waiver,
)
from factory.chain.gates import acceptance_verified
from factory.chain.gates.evaluator import PRContext
from factory.chain.state_machine import StoryRecord, StoryState

# --------------------------------------------------------------------------- #
# fixtures: a real git repo with a merge base, shaped like a real app
# --------------------------------------------------------------------------- #

_GOOD_IMPL = "def normalize_email(e):\n    return e.lower()\n"
_BAD_IMPL = "def normalize_email(e):\n    return e.strip()\n"

_ORACLE = (
    "from app.mod import normalize_email\n"
    "\n"
    "def test_ac1_email_is_lowercased():\n"
    "    assert normalize_email('User@Example.COM') == 'user@example.com'\n"
)
_TAUTOLOGY = (
    "def test_ac1_email_is_lowercased():\n"
    "    # the author never imported the app at all\n"
    "    assert True\n"
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(  # noqa: S603,S607
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _write_app(repo: Path, impl: str) -> None:
    (repo / "backend" / "app").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "backend" / "app" / "mod.py").write_text(impl, encoding="utf-8")
    # ``tests/`` must be tracked for a judge worktree to contain it.
    keep = repo / "backend" / "tests" / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")


def _repo(
    tmp_path: Path,
    *,
    base_impl: str = _BAD_IMPL,
    head_impl: str | None = _GOOD_IMPL,
    base_files: dict[str, str] | None = None,
    head_files: dict[str, str] | None = None,
) -> tuple[Path, str, str]:
    """A repo with ``main`` at the base commit and a feature branch checked out.

    Returns ``(repo, base_sha, head_sha)``. This is the shape the gate sees in
    production: the story's worktree on a feature branch whose merge base against
    ``main`` is the code the story started from.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _write_app(repo, base_impl)
    for rel, body in (base_files or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(body, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base_sha = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "-q", "-b", "feat/story")
    if head_impl is not None:
        _write_app(repo, head_impl)
    # Always leave SOME diff against the base, so the story branch is a real
    # branch even in the tests where base and head implementations are identical
    # (the ones that ask "does a passing oracle prove anything about this diff?").
    (repo / "backend" / "app" / "story_marker.py").write_text("MARKER = 1\n", encoding="utf-8")
    for rel, body in (head_files or {}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(body, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "story work")
    return repo, base_sha, _git(repo, "rev-parse", "HEAD")


def _story(
    *, story_id: int | None = 7, ref: str | None = None, expected: bool = True,
    state: str = StoryState.PR_OPEN.value, direction_id: str = "002",
    slug: str = "lowercase-email",
) -> StoryRecord:
    return StoryRecord(
        id=story_id, direction_id=direction_id, app="sacrifice",
        title="lowercase the email", slug=slug, scope="backend",
        state=state, acceptance_test_ref=ref, acceptance_expected=expected,
    )


def _cfg(
    *, on: bool = True, command: str | None = None,
    test_dir: str | None = "backend/tests", cwd: str | None = "backend",
) -> AppConfig:
    return AppConfig(
        name="sacrifice", repo="o/r",
        gates=AppGatesConfig(
            acceptance_oracle=on, acceptance_test_command=command,
            acceptance_test_dir=test_dir, acceptance_test_cwd=cwd,
        ),
    )


def _pr(root: Path, repo: Path | None, story: StoryRecord | None, sha: str) -> PRContext:
    return PRContext(
        pr_number=1, head_sha=sha, base_branch="main", story=story,
        repo_root=repo, software_factory_root=root, dry_run=False,
    )


def _store(root: Path, *, story_id: int = 7, content: str = _ORACLE) -> str:
    out = acceptance_dir(root, "sacrifice", story_id)
    out.mkdir(parents=True, exist_ok=True)
    (out / "test_acceptance.py").write_text(content, encoding="utf-8")
    return str((out / "test_acceptance.py").relative_to(root))


# =========================================================================== #
# D1 — the oracle must be able to FAIL
# =========================================================================== #


def test_D1_tautological_oracle_is_rejected_not_credited(tmp_path: Path) -> None:
    """``assert True`` passes at HEAD **and at the merge base**, so it discriminates
    nothing. Before the fix this was ``passed=True, authoritative=True`` against a
    violating implementation."""
    repo, _base, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=_TAUTOLOGY)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["verified"] is False
    assert r.details["unverifiable_kind"] == "oracle_not_discriminating"
    assert r.details["base_run"]["verdict"] == "green"
    # ...and it is NOT an accusation against the dev.
    assert r.details["authoritative"] is False


def test_D1_self_referential_assertion_is_rejected(tmp_path: Path) -> None:
    """The persona is told not to compare a response to itself. Now something checks."""
    repo, _base, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=(
        "from app.mod import normalize_email\n"
        "\n"
        "def test_ac1():\n"
        "    got = normalize_email('User@Example.COM')\n"
        "    assert got == normalize_email('User@Example.COM')\n"
    ))
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details["unverifiable_kind"] == "oracle_not_discriminating"


def test_D1_real_oracle_red_at_base_green_at_head_passes(tmp_path: Path) -> None:
    """The good case must still merge: red at base, green at HEAD → authoritative."""
    repo, base, head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.details.get("output_tail")
    assert r.details["verified"] is True
    assert r.details["authoritative"] is True
    assert r.details["tests_passed"] == 1
    assert r.details["base_run"]["verdict"] == "red"
    assert r.details["base_sha"] == base[:12]


def _new_module_repo(tmp_path: Path, impl: str) -> tuple[Path, str]:
    """A story that ADDS ``backend/app/mod.py``, with ``backend/tests`` ALREADY at base.

    The acceptance harness therefore resolves at the merge base and the base run
    really happens — it just cannot IMPORT the module. This is the common story
    shape (any story adding a module to an app past its first commit), and it is
    the one that distinguishes an errors-only base red from a real one.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "backend" / "tests").mkdir(parents=True)
    (repo / "backend" / "tests" / ".gitkeep").write_text("", encoding="utf-8")
    (repo / "backend" / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", "utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base without the module")
    _git(repo, "checkout", "-q", "-b", "feat/story")
    _write_app(repo, impl)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add the module")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_D1_new_module_story_with_a_REAL_oracle_still_merges(tmp_path: Path) -> None:
    """The good case for a story that adds the module its oracle imports.

    The base run is an errors-only red, which is NOT credited as failability (see
    the next test for why) — so this goes through ABLATION, and must still merge.
    If this ever blocks, the errors-only rule has become a false block on the most
    common story shape there is.
    """
    repo, head = _new_module_repo(tmp_path, _GOOD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["base_run"]["summary"]["errors"] >= 1
    assert r.details["base_run"]["verdict"] == "unknown"
    assert r.details["failability_route"] == "ablation"
    assert r.details["verified"] is True


def test_D1_importing_tautology_for_a_new_module_is_NOT_credited(tmp_path: Path) -> None:
    """THE NINTH DEFECT (found 2026-08-05 by the adversarial pass on this PR).

    ``base_verdict`` counted an ERROR as red. For a story that ADDS a module, an
    oracle whose only link to the criterion is ``from app.mod import thing`` errors
    at the merge base whatever it asserts — so this tautology was red at base,
    green at HEAD, and credited ``verified=True, authoritative=True`` against an
    implementation that VIOLATES the criterion. The whole D1 family (``assert
    True``, a self-referential assertion, an assertion inside ``try/except``) rode
    that route, and it bypassed ablation entirely because ``red`` is definitive.

    Errors-only reds are now ``unknown``, so this falls through to ablation, which
    correctly proves nothing about a tautology and leaves the block standing.
    """
    repo, head = _new_module_repo(tmp_path, _BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=(
        "from app.mod import normalize_email\n"
        "\n"
        "def test_ac1_email_is_lowercased():\n"
        "    assert True\n"
    ))
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, f"credited a tautology via a base collection error: {r.reason}"
    assert r.details["verified"] is False
    assert r.details["unverifiable_kind"] == "failability_unverified"
    assert r.details["base_run"]["verdict"] == "unknown"
    assert r.details["base_run"]["summary"]["errors"] >= 1
    # the green at HEAD was really observed — it is just not credited
    assert r.details["head_status"] == "pass"
    assert all(a["proven"] is False for a in r.details["failability_ablation"]["attempts"])


def test_D1_new_module_oracle_that_swallows_its_assertion_is_NOT_credited(
    tmp_path: Path,
) -> None:
    """Same route, a different way of asserting nothing: the only assertion sits in
    a ``try/except`` that swallows it.

    Worth its own test because the ablation half exercises a distinct mechanism —
    the ``except`` also swallows the sentinel exception the ablation splices in, so
    the mutant SURVIVES and nothing is proven. An oracle that cannot report a
    failure is not failable, however faithfully it calls the code.
    """
    repo, head = _new_module_repo(tmp_path, _BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=(
        "from app.mod import normalize_email\n"
        "\n"
        "def test_ac1_email_is_lowercased():\n"
        "    try:\n"
        "        assert normalize_email('User@Example.COM') == 'user@example.com'\n"
        "    except Exception:\n"
        "        pass\n"
    ))
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, f"credited an oracle that swallows its own assertion: {r.reason}"
    assert r.details["unverifiable_kind"] == "failability_unverified"
    assert r.details["base_run"]["verdict"] == "unknown"


def _no_base_harness_repo(tmp_path: Path, *, impl: str = _GOOD_IMPL) -> tuple[Path, str]:
    """A story that CREATES the whole backend, so the base run cannot happen.

    ``acceptance_test_dir=backend/tests`` does not exist at the merge base, which
    is a ``_ConfigError`` there — an honest "the harness could not run", i.e.
    ``unknown``, never a red. This is the realistic shape of the ``unknown``
    verdict, and it is why the ablation fallback exists.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("app\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "empty base")
    _git(repo, "checkout", "-q", "-b", "feat/story")
    _write_app(repo, impl)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "everything")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_D1_an_untrustworthy_base_run_falls_back_to_ABLATION_not_to_a_block(
    tmp_path: Path,
) -> None:
    """THE COMPOSITION. The base run is ``unknown`` (the harness dir does not exist
    at the merge base), so ``red_green`` has no answer — and ``mutation.check_can_fail``
    supplies one without needing a usable base: gut ``normalize_email`` and the
    oracle goes red, so its green at HEAD carries information after all.

    Before this, every story that created its own test tree blocked here forever.
    """
    repo, head = _no_base_harness_repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["base_run"]["verdict"] == "unknown"
    assert r.details["failability_route"] == "ablation"
    assert r.details["verified"] is True
    assert r.details["authoritative"] is True
    abl = r.details["failability_ablation"]
    assert abl["proven_by"] == "backend/app/mod.py::normalize_email"
    assert "ablation" in r.reason


def test_D1_the_ablation_fallback_still_refuses_a_tautology(tmp_path: Path) -> None:
    """The fail-safety half, and the one that matters: the SAME unknown-base story
    with ``assert True`` for an oracle must still block. Gutting the story's own
    code changes nothing the tautology can see, so nothing is proven and the block
    stands. If this ever passes, the fallback has become a fail-open."""
    repo, head = _no_base_harness_repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root, content=_TAUTOLOGY)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["unverifiable_kind"] == "failability_unverified"
    assert r.details["verified"] is False
    assert r.details["base_run"]["verdict"] == "unknown"
    # a green at HEAD was observed and is recorded — but it is not credited
    assert r.details["head_status"] == "pass"
    abl = r.details["failability_ablation"]
    assert "proven_by" not in abl
    assert abl["attempts"] and all(a["proven"] is False for a in abl["attempts"])


def test_D1_ablation_never_overturns_a_DEFINITIVE_green_base_verdict(
    tmp_path: Path,
) -> None:
    """ORDER IS THE ARGUMENT. ``red_green`` is the stronger instrument, so a base run
    that came back ``green`` — "this oracle does not discriminate this diff" — is
    never re-litigated by ablation.

    The oracle here would PASS an ablation check: it calls the story's own code, so
    gutting it turns the oracle red. But it also passes at the merge base, which is
    the definitive answer that its green says nothing about this story. The gate
    must report ``oracle_not_discriminating``, and must not have run any ablation.
    """
    repo, _base, head = _repo(tmp_path, base_impl=_GOOD_IMPL, head_impl=_GOOD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)  # real oracle, but the base already satisfies it
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["base_run"]["verdict"] == "green"
    assert r.details["unverifiable_kind"] == "oracle_not_discriminating"
    assert "failability_ablation" not in r.details
    assert "failability_route" not in r.details


def test_D1_ablation_refuses_a_scratch_tree_that_is_not_the_graded_commit(
    tmp_path: Path,
) -> None:
    """``mutation._materialize_tree`` falls back to COPYING THE WORKING TREE when it
    cannot clone — and a copy carries the dev's UNTRACKED files while carrying no
    ``.git``, so the collection-channel rollback would silently have nothing to roll
    back. The ``prepare`` hook checks the tree is a real checkout at the graded sha,
    so that fallback can never produce a proof."""
    repo, head = _no_base_harness_repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)

    import factory.chain.mutation as mutation_mod

    real = mutation_mod._materialize_tree

    def _copy_only(repo_root: Path, head_ref: str, dest: Path) -> str | None:
        # Force the non-git path the real function falls back to.
        import shutil as _sh

        try:
            _sh.copytree(repo_root, dest, ignore=mutation_mod._COPY_IGNORE, symlinks=True)
        except OSError:
            return None
        return "worktree-copy (forced)"

    mutation_mod._materialize_tree = _copy_only  # type: ignore[assignment]
    try:
        r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    finally:
        mutation_mod._materialize_tree = real  # type: ignore[assignment]

    assert not r.passed, r.reason
    assert r.details["unverifiable_kind"] == "failability_unverified"
    attempts = r.details["failability_ablation"]["attempts"]
    assert attempts and all(a["proven"] is False for a in attempts)
    assert "not the graded commit" in attempts[0]["detail"]


_FORCING_CONFTEST = (
    "import pytest\n"
    "\n"
    "@pytest.hookimpl(hookwrapper=True)\n"
    "def pytest_runtest_call(item):\n"
    "    outcome = yield\n"
    "    outcome.force_result(None)\n"
)


def _hostile_unknown_base_repo(tmp_path: Path, *, impl: str) -> tuple[Path, str]:
    """The unknown-base story, plus a COMMITTED force-every-test-to-pass conftest."""
    repo, _head = _no_base_harness_repo(tmp_path, impl=impl)
    (repo / "backend" / "tests" / "conftest.py").write_text(
        _FORCING_CONFTEST, encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "hostile collection channel")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_D1_the_ablation_tree_also_rolls_back_a_committed_hostile_conftest(
    tmp_path: Path,
) -> None:
    """H1 applied to the FALLBACK, layer one. The dev commits a conftest that forces
    every test to pass and the base run is ``unknown``, so ablation is the deciding
    route — and its scratch clone rolls that conftest back to the merge base exactly
    like the judge tree does. The code here is honest, so the story merges; the point
    is that the diff's own collection config never got a vote in either tree."""
    repo, head = _hostile_unknown_base_repo(tmp_path, impl=_GOOD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["failability_route"] == "ablation"
    # The conftest does not exist at the merge base, so rolling back DELETES it.
    assert "backend/tests/conftest.py" in r.details["channels_removed"]


def test_D1_a_forced_pass_buys_nothing_even_with_the_channel_rollback_DISABLED(
    tmp_path: Path,
) -> None:
    """H1 applied to the FALLBACK, layer two — defence in depth.

    Disable the collection-channel rollback entirely (the H1 fix) and let the dev's
    force-every-test-to-pass conftest survive into both trees. The HEAD run now goes
    green off a lie, and the base run is ``unknown``, so the ablation fallback is the
    only thing standing between a WRONG implementation and an authoritative green.

    It holds, and for a structural reason: a conftest that forces every test to pass
    also forces the ABLATED run to pass, so the mutant survives and nothing is
    proven. A forced pass cannot be turned into a proof of failability — it is
    exactly the wrong shape.
    """
    repo, head = _hostile_unknown_base_repo(tmp_path, impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)

    import factory.chain.gates.acceptance_verified as gate_mod

    real = gate_mod.restore_paths_from
    gate_mod.restore_paths_from = lambda tree, sha, paths: ([], [], [])  # type: ignore[assignment]
    try:
        r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    finally:
        gate_mod.restore_paths_from = real  # type: ignore[assignment]

    # The lie worked on the HEAD run — that is the premise, not the bug.
    assert r.details["head_status"] == "pass"
    # ...and it still does not merge.
    assert not r.passed, r.reason
    assert r.details["unverifiable_kind"] == "failability_unverified"
    attempts = r.details["failability_ablation"]["attempts"]
    assert attempts and all(a["proven"] is False for a in attempts)
    assert "stayed green" in attempts[0]["detail"]


def test_D1_base_run_verdict_is_cached_per_base_sha_and_oracle(tmp_path: Path) -> None:
    """One base run per (base sha, oracle, command) — not one per tick per PR."""
    repo, base, head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    first = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert first.passed
    assert first.details["base_run"].get("cached") is not True
    cache = acceptance_dir(root, "sacrifice", 7) / "base_runs.json"
    assert cache.exists()
    second = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert second.passed
    assert second.details["base_run"]["cached"] is True
    assert base[:12] == second.details["base_run"]["base_sha"]


def test_D1_an_unknown_base_verdict_is_never_cached(tmp_path: Path) -> None:
    """Caching an infra fault would make a fixable environment problem permanent.

    The oracle is a TAUTOLOGY so the ablation fallback cannot prove failability
    either — otherwise the forced ``unknown`` would be rescued and the gate would
    pass before the second base run happened.
    """
    repo, _base, head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root, content=_TAUTOLOGY)
    calls = {"n": 0}
    real = red_green.base_verdict

    def _unknown(exit_code: int, output: str):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        real(exit_code, output)
        return "unknown", "forced", None

    import factory.chain.gates.acceptance_verified as gate_mod

    orig = gate_mod.base_verdict
    gate_mod.base_verdict = _unknown  # type: ignore[assignment]
    try:
        for _ in range(2):
            r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
            assert not r.passed
        assert calls["n"] == 2  # re-ran, i.e. was not cached
    finally:
        gate_mod.base_verdict = orig


# =========================================================================== #
# D1 end-to-end on sacrifice direction 002's real spec shape
# =========================================================================== #

_D002_BASE = (
    "def handle(method, path):\n"
    "    if path == '/healthz' and method == 'GET':\n"
    "        return 200, {'status': 'ok', 'version': '1'}\n"
    "    return 405, {}\n"
)
_D002_HEAD = (
    "def handle(method, path):\n"
    "    if path == '/healthz' and method in ('GET', 'POST'):\n"
    "        return 200, {'status': 'ok', 'version': '1'}\n"
    "    return 405, {}\n"
)
# What an author writes from ``apps/sacrifice/directions/002-add-healthz-endpoint``:
# api_spec.md says ``POST /healthz`` → 200 with ``{"version","status"}``. The real
# authored oracle failed authoritatively on ``assert 405 == 200`` because the
# shipped code served GET.
_D002_ORACLE = (
    "from app.mod import handle\n"
    "\n"
    "def test_ac1_endpoint_returns_200():\n"
    "    status, _body = handle('POST', '/healthz')\n"
    "    assert status == 200\n"
    "\n"
    "def test_ac2_body_contains_version_and_status():\n"
    "    _status, body = handle('POST', '/healthz')\n"
    "    assert 'version' in body and 'status' in body\n"
)


def test_D1_direction_002_real_oracle_passes_and_a_tautology_for_it_does_not(
    tmp_path: Path,
) -> None:
    """Direction 002, both ways round, in one test.

    The spec-derived oracle (POST /healthz → 200) is RED at a base that serves only
    GET and green once POST is served → the gate credits it. A tautological oracle
    for the SAME criteria is now rejected instead of credited, which is the whole
    point of D1.
    """
    repo, _b, head = _repo(tmp_path, base_impl=_D002_BASE, head_impl=_D002_HEAD)
    root = tmp_path / "factory"

    real = _store(root, story_id=7, content=_D002_ORACLE)
    ok = acceptance_verified.evaluate(_pr(root, repo, _story(ref=real), head), _cfg())
    assert ok.passed, ok.details.get("output_tail")
    assert ok.details["verified"] is True
    assert ok.details["tests_passed"] == 2

    fake = _store(root, story_id=8, content=(
        "def test_ac1_endpoint_returns_200():\n    assert True\n"
        "\n"
        "def test_ac2_body_contains_version_and_status():\n    assert 200 == 200\n"
    ))
    bad = acceptance_verified.evaluate(
        _pr(root, repo, _story(story_id=8, ref=fake), head), _cfg()
    )
    assert not bad.passed
    assert bad.details["unverifiable_kind"] == "oracle_not_discriminating"


# =========================================================================== #
# H1/H2 — the dev must not control the environment that judges it
# =========================================================================== #

_FORCE_PASS_CONFTEST = (
    "import pytest\n"
    "\n"
    "@pytest.hookimpl(hookwrapper=True)\n"
    "def pytest_runtest_call(item):\n"
    "    outcome = yield\n"
    "    if 'test_acceptance_oracle_' in item.nodeid:\n"
    "        outcome.force_result(None)\n"
)


def test_H1_committed_conftest_hookwrapper_no_longer_forces_a_pass(tmp_path: Path) -> None:
    """The measured attack: 7 lines in ``backend/tests/conftest.py``. The judge tree
    restores that path from the merge base, so the hookwrapper is not loaded."""
    repo, _b, head = _repo(
        tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL,
        base_files={"backend/tests/conftest.py": "# benign\n"},
        head_files={"backend/tests/conftest.py": _FORCE_PASS_CONFTEST},
    )
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["authoritative"] is True  # the implementation really does violate it
    assert "backend/tests/conftest.py" in r.details["channels_restored"]


def test_H1b_committed_autouse_fixture_no_longer_stubs_the_unit_under_test(
    tmp_path: Path,
) -> None:
    """Same hole, less obviously hostile: an autouse fixture monkeypatches the app."""
    repo, _b, head = _repo(
        tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL,
        base_files={"backend/tests/conftest.py": "# benign\n"},
        head_files={"backend/tests/conftest.py": (
            "import pytest\n"
            "import app.mod\n"
            "\n"
            "@pytest.fixture(autouse=True)\n"
            "def _shim(monkeypatch):\n"
            "    monkeypatch.setattr(app.mod, 'normalize_email', lambda e: e.lower())\n"
        )},
    )
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details["authoritative"] is True


def test_H1c_committed_pyproject_addopts_plugin_no_longer_neuters_the_run(
    tmp_path: Path,
) -> None:
    """``addopts = "-p _fixup"`` + a root plugin — the channel the bench harness
    REFUSES a prediction for. ``pyproject.toml`` is restored from the base, so the
    plugin is never loaded even though ``_fixup.py`` is still in the tree."""
    repo, _b, head = _repo(
        tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL,
        base_files={"backend/pyproject.toml": "[project]\nname='x'\nversion='0'\n"},
        head_files={
            "backend/pyproject.toml": (
                "[project]\nname='x'\nversion='0'\n"
                "[tool.pytest.ini_options]\naddopts = \"-p _fixup\"\n"
            ),
            "backend/_fixup.py": (
                "import pytest\n"
                "@pytest.hookimpl(hookwrapper=True)\n"
                "def pytest_runtest_call(item):\n"
                "    outcome = yield\n"
                "    outcome.force_result(None)\n"
            ),
        },
    )
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert "backend/pyproject.toml" in r.details["channels_restored"]


def test_H1d_an_added_collection_channel_is_deleted_in_the_judge_tree(
    tmp_path: Path,
) -> None:
    """A channel the diff ADDS has nothing to restore from — it must be removed."""
    repo, _b, head = _repo(
        tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL,
        head_files={"backend/tests/conftest.py": _FORCE_PASS_CONFTEST},
    )
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert "backend/tests/conftest.py" in r.details["channels_removed"]


def test_H1e_uncommitted_hostile_conftest_is_absent_from_the_judge_tree(
    tmp_path: Path,
) -> None:
    """A judge worktree contains only TRACKED content, so an untracked plant — the
    cheapest attack of all, and one no diff-based check can see — cannot load."""
    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    (repo / "backend" / "tests" / "conftest.py").write_text(_FORCE_PASS_CONFTEST, "utf-8")
    (repo / "backend" / "sitecustomize.py").write_text("import os\n", "utf-8")
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details["authoritative"] is True
    assert r.details["collection_channels_in_diff"] == []


def test_H1f_a_tests_package_init_cannot_repair_a_violating_implementation(
    tmp_path: Path,
) -> None:
    """THE NINTH DEFECT, found by the adversarial pass on this very fix — and it was
    a WORKING forced-pass attack, not a theoretical one.

    The oracle is copied into ``backend/tests/``, so pytest's prepend import mode
    imports it as ``tests.<name>`` and executes ``backend/tests/__init__.py`` first.
    Two lines there rebind the function under test to a correct implementation, and a
    violating implementation goes green. Worse than the conftest attacks: the file
    does not exist at the merge base, so the base run is genuinely RED and the
    forgery arrives wearing a perfect red→green.

    ``__init__.py`` under ``tests/`` is test CODE, not a "collection channel", so it
    used to pass straight through from HEAD. The rollback set is now
    ``is_collection_channel_path`` ∪ ``is_test_code_path``.
    """
    repo, _base, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    (repo / "backend" / "tests" / "__init__.py").write_text(
        "import app.mod\napp.mod.normalize_email = lambda e: e.lower()\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a helpful tests package")
    head = _git(repo, "rev-parse", "HEAD")

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["verified"] is False
    # The rollback DELETED it (it does not exist at the base), and the honest run of
    # the violating implementation is then red.
    assert "backend/tests/__init__.py" in r.details["rolled_back_to_base"]
    assert r.details["channels_removed"] == ["backend/tests/__init__.py"]
    assert r.details["head_status"] == "fail"


def test_H1g_the_rollback_set_is_the_whole_test_surface_not_just_config(
    tmp_path: Path,
) -> None:
    """The invariant in one assertion: PRODUCTION CODE FROM HEAD, THE WHOLE TEST
    SURFACE FROM BASE. Every test-code path and every collection channel the diff
    touched is rolled back; production code is not.

    The gate defines the set as ``not is_production_path`` — the exact complement —
    so this test also pins that the complement really is the union it is supposed to
    be, and that a future widening of either classifier cannot silently leave the
    gate behind."""
    repo, _base, _head = _repo(
        tmp_path,
        head_files={
            "backend/tests/__init__.py": "",
            "backend/tests/helpers.py": "X = 1\n",
            "backend/tests/test_dev_own.py": "def test_d():\n    assert True\n",
            "backend/tests/conftest.py": "",
            "backend/pyproject.toml": "[tool.pytest.ini_options]\n",
            "backend/app/extra.py": "Y = 2\n",
        },
    )
    head = _git(repo, "rev-parse", "HEAD")

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    rolled = set(r.details["rolled_back_to_base"])
    assert rolled == {
        "backend/pyproject.toml",
        "backend/tests/__init__.py",
        "backend/tests/conftest.py",
        "backend/tests/helpers.py",
        "backend/tests/test_dev_own.py",
    }
    # The story's own production code is NOT rolled back — that is the thing being
    # judged, and rolling it back would make every oracle green at "HEAD".
    assert not any(p.startswith("backend/app/") for p in rolled)
    assert r.passed, r.reason


_FORCE_PASS_PLUGIN = (
    "import pytest\n"
    "\n"
    "@pytest.hookimpl(hookwrapper=True)\n"
    "def pytest_runtest_call(item):\n"
    "    outcome = yield\n"
    "    outcome.force_result(None)\n"
)


@pytest.mark.parametrize(
    ("label", "head_files"),
    [
        (
            # pytest honours the DOT-prefixed inifile and it OUTRANKS pyproject.toml.
            # Every name in _COLLECTION_CHANNEL was anchored on ``(^|/)``, which the
            # leading dot walked past — so this was H1c's attack, routed around the
            # pyproject.toml rollback, and it produced a full authoritative green.
            "dot_pytest_ini",
            {
                "backend/.pytest.ini": "[pytest]\npythonpath = .\naddopts = -p devhelper_hook\n",
                "backend/devhelper_hook.py": _FORCE_PASS_PLUGIN,
            },
        ),
        (
            # ``importlib.metadata`` scans every sys.path entry for ``*.dist-info``
            # and pytest calls ``load_setuptools_entrypoints("pytest11")``. A
            # committed entry_points.txt auto-loads a dev plugin with NO config edit.
            "dist_info_entry_point",
            {
                "backend/devhelper-1.0.dist-info/METADATA": "Name: devhelper\nVersion: 1.0\n",
                "backend/devhelper-1.0.dist-info/entry_points.txt": (
                    "[pytest11]\ndevhelper = devhelper_hook\n"
                ),
                "backend/devhelper_hook.py": _FORCE_PASS_PLUGIN,
            },
        ),
        (
            # ``python -m pytest`` puts the run cwd at sys.path[0], so a ``pytest.py``
            # there IS the whole "pytest run" — print a summary and exit 0. The gate's
            # DEFAULT command is ``-m pytest``, so this hit the default configuration.
            "runner_shadow",
            {
                "backend/pytest.py": (
                    "import sys\nprint('.  [100%]')\nprint('1 passed in 0.02s')\nsys.exit(0)\n"
                )
            },
        ),
    ],
)
def test_H1h_three_more_collection_channels_that_were_classified_PRODUCTION(
    tmp_path: Path, label: str, head_files: dict[str, str]
) -> None:
    """Three MORE forced-pass attacks, all confirmed executing, all found by the
    adversarial pass on this fix. Each one was classified as PRODUCTION code by
    ``factory.diff_paths``, so the "whole test surface from base" rollback passed it
    straight through from HEAD and the gate returned ``verified=True`` against a
    violating implementation.

    They are completeness bugs in ``_COLLECTION_CHANNEL``, not design bugs: widening
    it closes all three, and widening it is the safe direction everywhere it is used
    (the bench refuses more predictions; ``production-tree-changed`` counts fewer
    files as production).
    """
    repo, _base, _h = _repo(
        tmp_path,
        base_impl=_BAD_IMPL,
        head_impl=_BAD_IMPL,
        base_files={"backend/pyproject.toml": "[tool.pytest.ini_options]\n"},
        head_files=head_files,
    )
    head = _git(repo, "rev-parse", "HEAD")
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, f"{label} forced a pass: {r.reason}"
    assert r.details["verified"] is False
    assert r.details["rolled_back_to_base"], f"{label} was not rolled back at all"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KNOWN OPEN, and the reason the acceptance_oracle flag stays OFF. The oracle "
        "imports the diff's PRODUCTION code, which therefore executes inside the same "
        "interpreter that grades the oracle, and can replace pytest's test-execution "
        "machinery: `if 'pytest' in sys.modules: _pytest.python.Function.runtest = "
        "lambda self: None`. No rollback set closes this — the attack does not live in "
        "any file a rollback could reach. Closing it needs the verdict computed OUTSIDE "
        "that process (an out-of-process behavioural oracle, like smoke-green's HTTP "
        "checks) or a tampering detector over production paths, which would false-block "
        "the `factory` app wholesale because its production code IS test infrastructure. "
        "When this test starts XPASSing, the hole is closed: delete the marker and "
        "update the module docstring's 'bounded by' paragraph."
    ),
)
def test_KNOWN_OPEN_production_code_can_patch_pytest_in_process(tmp_path: Path) -> None:
    """This test asserts the property we WANT and currently do not have, so it is
    expected to fail. It exists in the tree rather than only in a PR description
    because a hole recorded in prose is a hole nobody re-checks."""
    attack = (
        "import sys\n"
        "if 'pytest' in sys.modules:\n"
        "    import _pytest.python\n"
        "    _pytest.python.Function.runtest = lambda self: None\n"
        "\n"
        "\n"
        "def normalize_email(e):\n"
        "    return e.strip()\n"  # still violates the criterion
    )
    repo, _base, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=attack)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, (
        "production code disabled pytest's runtest and the gate credited the green: "
        f"{r.reason}"
    )


def test_H2_the_oracle_never_enters_the_dev_worktree(tmp_path: Path) -> None:
    """No copy, no ``__pycache__`` sibling, and no ``.pytest_cache`` naming its
    tests — H4.2. The whole run happens in a throwaway tree."""
    repo, _b, head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref), head),
        # deliberately WITHOUT -p no:cacheprovider, like the shipped sacrifice config
        _cfg(command=f"{sys.executable} -m pytest {{test_file}} -q"),
    )
    assert r.passed, r.reason
    assert not list(repo.rglob(f"{ORACLE_COPY_PREFIX}*"))
    assert not list(repo.rglob("nodeids")), "the oracle's test names leaked into a cache"
    assert not list(repo.rglob("lastfailed"))


def test_H2b_no_stray_judge_worktrees_are_left_registered(tmp_path: Path) -> None:
    repo, _b, head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    listed = _git(repo, "worktree", "list")
    assert "factory-oracle" not in listed, listed


# =========================================================================== #
# H3 — the forged pass count
# =========================================================================== #


def test_H3_summary_parse_takes_the_last_line_and_flags_a_forgery() -> None:
    """``_PASSED_RE.search`` took the FIRST '<n> passed'. A conftest can print one
    before pytest's own summary; the count must come from the LAST summary, and two
    different summaries must poison the result entirely."""
    forged = "7 passed in 0.01s\n....\n1 skipped in 0.02s\n"
    s = red_green.parse_pytest_summary(forged)
    assert s is not None
    assert s.passed == 0
    assert s.skipped == 1
    assert s.conflicting is True
    status, _ = red_green.classify_pytest_run(0, forged)
    assert status == "conflicting"

    honest = "..                                     [100%]\n2 passed in 0.03s\n"
    s2 = red_green.parse_pytest_summary(honest)
    assert s2 is not None and s2.passed == 2 and s2.conflicting is False
    assert red_green.classify_pytest_run(0, honest)[0] == "pass"


def test_H3b_a_preexisting_conftest_forgery_is_refused_not_credited(
    tmp_path: Path,
) -> None:
    """The residual H3 surface: a hostile conftest that is NOT part of this diff is
    restored-from-base unchanged (it IS the base). It can still skip every oracle
    test and print a forged summary — and the gate now refuses to grade that
    output instead of reporting ``tests_passed=7``."""
    forger = (
        "import sys, pytest\n"
        "def pytest_collection_modifyitems(items):\n"
        "    for it in items:\n"
        "        if 'test_acceptance_oracle_' in it.nodeid:\n"
        "            it.add_marker(pytest.mark.skip(reason='env'))\n"
        "def pytest_configure(config):\n"
        "    print('7 passed in 0.01s', file=sys.stderr)\n"
    )
    repo, _b, head = _repo(
        tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL,
        base_files={"backend/tests/conftest.py": forger},
    )
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["tests_passed"] != 7
    assert r.details["unverifiable_kind"] == "conflicting_summaries"
    assert "waived" not in r.details  # tampering is NEVER waivable


def test_H3c_a_conflicting_summary_cannot_be_waived(tmp_path: Path) -> None:
    forger = (
        "import sys\n"
        "def pytest_configure(config):\n"
        "    print('9 passed in 0.01s', file=sys.stderr)\n"
    )
    repo, _b, head = _repo(
        tmp_path, base_files={"backend/tests/conftest.py": forger},
    )
    root = tmp_path / "factory"
    ref = _store(root)
    write_waiver(root, "sacrifice", 7, oracle_sha=oracle_sha256(_ORACLE),
                 reason="operator says ship it")
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details.get("waived") is not True


# =========================================================================== #
# D2 — the gate must be testing the merge candidate
# =========================================================================== #


def test_D2_a_checkout_that_does_not_contain_the_pr_head_is_not_graded(
    tmp_path: Path,
) -> None:
    """The fetch-failure path: ``_story_worktree`` resets to origin/<feat> only when
    ``git fetch`` returned 0. Before the fix an unrelated commit could earn an
    AUTHORITATIVE PASS."""
    repo, _b, _head = _repo(tmp_path)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), "0" * 40), _cfg())
    assert not r.passed
    assert r.details["authoritative"] is False
    assert r.details["unverifiable_kind"] == "provenance_unverified"


def test_D2b_a_head_sha_that_is_a_real_non_ancestor_is_refused(tmp_path: Path) -> None:
    """A commit that EXISTS but is not in this checkout's history."""
    repo, base, head = _repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "other", base)
    (repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "other work")
    other = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "feat/story")
    assert head != other

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), other), _cfg())
    assert not r.passed
    assert r.details["unverifiable_kind"] == "wrong_commit"
    assert r.details["authoritative"] is False


def test_D2c_a_real_merge_of_the_base_branch_does_not_false_block(tmp_path: Path) -> None:
    """THE production shape. ``_story_worktree`` merges ``origin/main`` in before gates
    run, so the checkout HEAD is a MERGE COMMIT whose ancestor is the PR head. SHA
    equality would false-block every such PR.

    The merge here is a REAL ``git merge``, not a plain commit standing in for one:
    an earlier version of this test faked it, and the fake passed while hiding the
    hole ``extra_commits_beyond`` closes below.
    """
    repo, _base, head = _repo(tmp_path)
    _git(repo, "checkout", "-q", "main")
    (repo / "sibling.md").write_text("a sibling story merged\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "sibling work on main")
    _git(repo, "checkout", "-q", "feat/story")
    _git(repo, "merge", "--no-edit", "-q", "main")
    merged_head = _git(repo, "rev-parse", "HEAD")
    assert merged_head != head
    assert len(_git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()) == 3, "not a merge"

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["verified"] is True


def test_D2e_a_checkout_AHEAD_of_the_pr_head_is_refused(tmp_path: Path) -> None:
    """The hole ancestry alone leaves, found by the adversarial pass on the D2 fix.

    ``git fetch origin <feature>`` fails, so ``_story_worktree`` never resets — and
    the worktree still holds a commit the chain made and could not push. The PR head
    IS an ancestor of that HEAD, so the ancestry check is satisfied, and the gate
    would have returned an AUTHORITATIVE verdict about code nobody is merging."""
    repo, _base, head = _repo(tmp_path)
    (repo / "backend" / "app" / "mod.py").write_text(
        "def normalize_email(e):\n    return e.lower()\n# never pushed\n", encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "unpushed local work")
    assert _git(repo, "merge-base", "--is-ancestor", head, "HEAD") == ""  # ancestry holds

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed, r.reason
    assert r.details["unverifiable_kind"] == "checkout_ahead_of_pr_head"
    assert r.details["authoritative"] is False
    # and it is NOT waivable: an operator must not be able to wave through a
    # verdict about the wrong code.
    assert "waived" not in r.details


def _linked_worktree(repo: Path, at: Path, branch: str = "feat/story") -> Path:
    """``PRContext.repo_root`` in production is a LINKED git worktree.

    ``auto_merge._story_worktree`` hands the gates ``state/worktrees/<issue>-<slug>``,
    created with ``git worktree add``, so its ``.git`` is a FILE pointing at a shared
    gitdir. Every git operation this gate performs — ``worktree add`` for the judge
    tree, ``rev-list`` for provenance, and ``clone --local`` inside
    ``mutation.check_can_fail`` — has to work against that, and none of it was
    exercised until this fixture existed. The subsystem's first real execution
    false-blocked 100% of stories on exactly this class of substrate mismatch
    (repo layout, wrong interpreter), so it gets a fixture rather than a comment.
    """
    _git(repo, "checkout", "-q", "main")
    at.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-q", str(at), branch)
    return at


def test_D2f_the_gate_works_against_a_LINKED_worktree_the_production_shape(
    tmp_path: Path,
) -> None:
    """Red-at-base, green-at-HEAD, judged from a linked worktree — and the parent
    checkout is left exactly as it was."""
    repo, base, head = _repo(tmp_path)
    wt = _linked_worktree(repo, tmp_path / "worktrees" / "7-story")
    assert (wt / ".git").is_file(), "not a linked worktree"
    before = _git(repo, "rev-parse", "HEAD")

    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, wt, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["verified"] is True
    assert r.details["base_sha"] == base[:12]
    # No stray judge worktree registrations, and the parent is untouched.
    assert "factory-oracle" not in _git(repo, "worktree", "list")
    assert _git(repo, "rev-parse", "HEAD") == before
    assert red_green.head_sha(wt) == head


def test_D2g_the_ablation_fallback_works_against_a_LINKED_worktree(
    tmp_path: Path,
) -> None:
    """``mutation._materialize_tree`` does ``git clone --local`` of ``repo_root``.
    Cloning from a linked worktree is the case that had never run."""
    repo, head = _no_base_harness_repo(tmp_path)
    wt = _linked_worktree(repo, tmp_path / "worktrees" / "7-story")
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, wt, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["failability_route"] == "ablation"
    assert r.details["failability_ablation"]["proven_by"] == (
        "backend/app/mod.py::normalize_email"
    )


def test_D2d_a_non_git_checkout_can_no_longer_produce_a_pass(tmp_path: Path) -> None:
    """No git, no provenance, no judge tree, no base run — so no green. This is a
    deliberate tightening: the old gate graded a bare directory happily."""
    repo = tmp_path / "plain"
    _write_app(repo, _GOOD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), "a" * 40), _cfg())
    assert not r.passed
    assert r.details["unverifiable_kind"] == "provenance_unverified"


# =========================================================================== #
# the operator waiver — the ONLY path from skipped-with-reason to a merge
# =========================================================================== #


def test_waiver_clears_a_non_discriminating_oracle_but_never_claims_verification(
    tmp_path: Path,
) -> None:
    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=_TAUTOLOGY)
    blocked = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not blocked.passed

    write_waiver(
        root, "sacrifice", 7, oracle_sha=oracle_sha256(_TAUTOLOGY),
        reason="AC already satisfied by sibling story 6",
    )
    waived = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert waived.passed
    assert waived.details["waived"] is True
    assert waived.details["verified"] is False  # a waiver is not a verification
    assert waived.details["authoritative"] is False
    assert "WAIVER" in waived.reason


def test_waiver_is_scoped_to_the_oracle_content(tmp_path: Path) -> None:
    """Re-authoring the oracle invalidates the operator's decision about the old one."""
    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    write_waiver(root, "sacrifice", 7, oracle_sha=oracle_sha256("something else"),
                 reason="stale decision")
    ref = _store(root, content=_TAUTOLOGY)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details.get("waived") is not True


def test_waiver_cannot_clear_a_failing_oracle(tmp_path: Path) -> None:
    """The waiver exists for un-gradeable states only. A real red must never be
    waivable, or the gate becomes advisory."""
    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root)  # a real oracle; HEAD violates the criterion
    write_waiver(root, "sacrifice", 7, oracle_sha=oracle_sha256(_ORACLE), reason="ship it")
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert not r.passed
    assert r.details["authoritative"] is True
    assert r.details.get("waived") is not True


def test_waiver_without_a_reason_is_not_a_waiver(tmp_path: Path) -> None:
    root = tmp_path / "factory"
    with pytest.raises(ValueError, match="reason"):
        write_waiver(root, "sacrifice", 7, oracle_sha="abc", reason="   ")


# =========================================================================== #
# H4.1 — the sweep must not be destructive when git cannot answer
# =========================================================================== #


def test_H41_sweep_refuses_to_delete_when_git_cannot_say_what_is_tracked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_git_tracked`` returned an EMPTY SET when git could not answer and the
    sweep then deleted every match — including git-TRACKED app files, which the
    docstring promises it never does."""
    repo = tmp_path / "repo"
    (repo / "backend" / "tests").mkdir(parents=True)
    victim = repo / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}contract.py"
    victim.write_text("def test_real_dev_test():\n    assert True\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    assert sweep_leaked_oracles(repo) == []
    assert victim.exists()

    import factory.chain.acceptance as acc

    monkeypatch.setattr(
        acc.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("no git"))
    )
    assert sweep_leaked_oracles(repo) == []  # refuses, rather than guessing
    assert victim.exists()


def test_H41b_an_UNTRACKED_copy_the_sweep_could_not_remove_blocks_the_gate(
    tmp_path: Path,
) -> None:
    """Refusing to delete must not become a silent pass: a real oracle copy sitting
    in the dev's worktree is an independence breach and blocks.

    A leak is UNTRACKED by construction. Deletion is made to fail by taking write
    permission off the directory, which is how an unremovable leak actually happens.
    """
    repo, _b, head = _repo(tmp_path)
    leak_dir = repo / "backend" / "tests"
    (leak_dir / f"{ORACLE_COPY_PREFIX}999.py").write_text(
        "def test_leaked():\n    assert True\n", encoding="utf-8"
    )
    root = tmp_path / "factory"
    ref = _store(root)
    leak_dir.chmod(0o555)
    try:
        r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    finally:
        leak_dir.chmod(0o755)
    assert not r.passed
    assert r.details["authoritative"] is True
    assert "dev-blindness" in r.reason
    assert r.details["leaked_copies"] == [f"backend/tests/{ORACLE_COPY_PREFIX}999.py"]


def test_H41c_a_git_TRACKED_file_matching_the_prefix_is_not_a_leak(
    tmp_path: Path,
) -> None:
    """A second defect from the adversarial pass, and a self-inflicted one.

    An app may legitimately commit a test called ``test_acceptance_oracle_smoke.py``.
    ``sweep_leaked_oracles`` correctly refused to delete it — logging "TRACKED by
    git, leaving it alone (a leaked oracle copy is never tracked)" — and the gate
    then blocked on that very file, AUTHORITATIVELY, forever, unwaivably, for every
    story in the app. Two functions, opposite conclusions about the same file.

    A leak is untracked by construction, so a tracked match is the app's own file.
    """
    repo, _b, _h = _repo(
        tmp_path,
        base_files={
            f"backend/tests/{ORACLE_COPY_PREFIX}smoke.py": "def test_s():\n    assert True\n"
        },
    )
    head = _git(repo, "rev-parse", "HEAD")
    root = tmp_path / "factory"
    ref = _store(root)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    assert r.passed, r.reason
    assert r.details["verified"] is True
    assert r.details.get("leaked_copies") is None


def test_H41d_an_unanswerable_tracked_set_treats_every_match_as_a_leak(
    tmp_path: Path,
) -> None:
    """Fail-safe direction for the fix above: when git cannot say what is tracked,
    a match must count as a leak and BLOCK. The permissive reading of "unknowable"
    is what made the sweep destructive in the first place; the permissive reading
    here would wave a real breach through."""
    from factory.chain import acceptance as acc

    tree = tmp_path / "notarepo"
    (tree / "backend" / "tests").mkdir(parents=True)
    (tree / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}5.py").write_text("", encoding="utf-8")
    # Not a git repository at all → _git_tracked returns None.
    assert acc.sweep_leaked_oracles(tree) == []
    assert acc.unremovable_oracle_leaks(tree) == [
        f"backend/tests/{ORACLE_COPY_PREFIX}5.py"
    ]


# =========================================================================== #
# D3 / H6 — the wedge that never exhausted, and the silent sink
# =========================================================================== #


def _app_with_config(root: Path, *, direction: bool) -> Path:
    (root / "apps" / "sacrifice").mkdir(parents=True, exist_ok=True)
    (root / "apps" / "sacrifice" / "config.yaml").write_text(
        "name: sacrifice\nrepo: o/r\ngates:\n  acceptance_oracle: true\n", encoding="utf-8"
    )
    if direction:
        d = root / "apps" / "sacrifice" / "directions" / "002-emails"
        d.mkdir(parents=True, exist_ok=True)
        (d / "direction.md").write_text(
            "---\ntitle: emails\n---\n\n# emails\n\n## Why\n\nx.\n\n"
            "## Acceptance Criteria\n\n- the email is lowercased\n",
            encoding="utf-8",
        )
    db = root / "state" / "factory.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    return db


def test_D3_missing_direction_records_a_failed_pass_and_exhausts(tmp_path: Path) -> None:
    """``reauthor_missing_oracles`` used to ``continue`` without recording a pass,
    so ``author_exhausted`` never became True and the gate blocked forever saying
    "self-heals next tick" — a promise a deleted direction dir cannot keep."""
    from sqlmodel import Session

    from factory.chain.handlers import _engine

    root = tmp_path / "factory"
    db = _app_with_config(root, direction=False)
    story = _story(story_id=41, ref=None, expected=True, direction_id="999")
    with Session(_engine(db)) as s:
        s.add(story)
        s.commit()

    calls = {"n": 0}

    def _author(_spec: str, _s: StoryRecord) -> str:
        calls["n"] += 1
        return _TAUTOLOGY

    for _ in range(10):
        reauthor_missing_oracles("sacrifice", root, dry_run=False, db_path=db, author_fn=_author)
    assert calls["n"] == 0  # still never fires the model for a missing spec
    assert author_passes(root, "sacrifice", 41) == _MAX_AUTHOR_PASSES  # ...but it EXHAUSTS

    fresh = _story(story_id=41, ref=None, expected=True, direction_id="999")
    r = acceptance_verified.evaluate(_pr(root, None, fresh, "a" * 40), _cfg())
    assert not r.passed
    assert r.details["author_exhausted"] is True
    assert "EXHAUSTED" in r.reason
    assert "self-heals next tick" not in r.reason


def test_H6_exhaustion_is_surfaced_for_a_human(tmp_path: Path) -> None:
    root = tmp_path / "factory"
    db = _app_with_config(root, direction=False)
    story = _story(story_id=41, ref=None, expected=True, direction_id="999")
    from sqlmodel import Session

    from factory.chain.handlers import _engine

    with Session(_engine(db)) as s:
        s.add(story)
        s.commit()
    assert pending_acceptance_attention(root, "sacrifice") == []
    for _ in range(_MAX_AUTHOR_PASSES):
        reauthor_missing_oracles("sacrifice", root, dry_run=False, db_path=db)
    items = pending_acceptance_attention(root, "sacrifice")
    assert [i["kind"] for i in items] == ["author_exhausted"]
    assert items[0]["story_id"] == 41


def test_H6b_a_non_authoritative_gate_block_is_surfaced_for_a_human(
    tmp_path: Path,
) -> None:
    """A story stuck on ``oracle_not_discriminating`` sits at ``pr_open`` with no
    rejection reason: without this it appears in NO operator surface."""
    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    ref = _store(root, content=_TAUTOLOGY)
    acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref), head), _cfg())
    items = pending_acceptance_attention(root, "sacrifice")
    assert [i["kind"] for i in items] == ["oracle_not_discriminating"]


def test_H6c_a_recorded_block_is_cleared_once_the_gate_passes(tmp_path: Path) -> None:
    repo, _b, head = _repo(tmp_path)
    root = tmp_path / "factory"
    bad_ref = _store(root, content=_TAUTOLOGY)
    acceptance_verified.evaluate(_pr(root, repo, _story(ref=bad_ref), head), _cfg())
    assert pending_acceptance_attention(root, "sacrifice")
    good_ref = _store(root, content=_ORACLE)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=good_ref), head), _cfg())
    assert r.passed
    assert pending_acceptance_attention(root, "sacrifice") == []


def test_H6d_the_inner_author_guard_is_strictly_below_the_outer_cap() -> None:
    """Repo convention: caps at 3, inner guards at 2 — an inner guard equal to the
    cap makes the early signal unreachable."""
    assert _AUTHOR_ATTEMPTS < _MAX_AUTHOR_PASSES == 3


def test_reauthor_bounds_ATTEMPTS_not_just_successes(tmp_path: Path) -> None:
    """``max_per_pass`` counted successes, so the failure case it exists to bound
    was unbounded: 25 live stories × the inner attempts in ONE pass."""
    from factory.chain.handlers import persist_story

    root = tmp_path / "factory"
    db = _app_with_config(root, direction=True)
    for i in range(1, 26):
        persist_story(_story(story_id=None, slug=f"story-{i}", expected=True), db)

    calls = {"n": 0}

    def _always_fails(_spec: str, _st: StoryRecord) -> str:
        calls["n"] += 1
        raise RuntimeError("provider 500")

    healed = reauthor_missing_oracles(
        "sacrifice", root, dry_run=False, db_path=db,
        author_fn=_always_fails, max_per_pass=10,
    )
    assert healed == 0
    assert calls["n"] == 10 * _AUTHOR_ATTEMPTS  # bounded by the cap, not by 25 stories


def test_H6e_the_cli_lists_and_records_the_operator_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``factory acceptance-waive`` with no argument LISTS what is stuck; with a
    story id it records the decision — and refuses without a reason."""
    from typer.testing import CliRunner

    from factory.chain.handlers import persist_story
    from factory.cli import app as cli_app

    repo, _b, head = _repo(tmp_path, base_impl=_BAD_IMPL, head_impl=_BAD_IMPL)
    root = tmp_path / "factory"
    db = _app_with_config(root, direction=True)
    row = persist_story(_story(story_id=None, expected=True), db)
    ref = _store(root, story_id=row.id or 0, content=_TAUTOLOGY)
    blocked = acceptance_verified.evaluate(
        _pr(root, repo, _story(story_id=row.id, ref=ref), head), _cfg()
    )
    assert not blocked.passed

    monkeypatch.setattr("factory.cli._FACTORY_ROOT", root)
    runner = CliRunner()
    listed = runner.invoke(cli_app, ["acceptance-waive"])
    assert listed.exit_code == 0
    assert "oracle_not_discriminating" in listed.stdout

    no_reason = runner.invoke(
        cli_app, ["acceptance-waive", str(row.id), "--app", "sacrifice"]
    )
    assert no_reason.exit_code == 2

    ok = runner.invoke(
        cli_app,
        ["acceptance-waive", str(row.id), "--app", "sacrifice",
         "--reason", "AC delivered by sibling story 6"],
    )
    assert ok.exit_code == 0, ok.stdout
    after = acceptance_verified.evaluate(
        _pr(root, repo, _story(story_id=row.id, ref=ref), head), _cfg()
    )
    assert after.passed
    assert after.details["verified"] is False

    cleared = runner.invoke(
        cli_app, ["acceptance-waive", str(row.id), "--app", "sacrifice", "--clear"]
    )
    assert cleared.exit_code == 0
    again = acceptance_verified.evaluate(
        _pr(root, repo, _story(story_id=row.id, ref=ref), head), _cfg()
    )
    assert not again.passed


# =========================================================================== #
# H4.2 — the shipped sacrifice command must not leave a cache naming the oracle
# =========================================================================== #


def test_H42_sacrifice_acceptance_command_disables_the_pytest_cache() -> None:
    import yaml

    cfg = yaml.safe_load(
        Path("apps/sacrifice/config.yaml").read_text(encoding="utf-8")
    )
    cmd = cfg["gates"]["acceptance_test_command"]
    assert "-p no:cacheprovider" in cmd, cmd


# =========================================================================== #
# D7/H8 — ordering: the acceptance gate must stay LAST
# =========================================================================== #


def test_H8_acceptance_gate_is_last_in_the_evaluator_tuple() -> None:
    """``tests_meaningful`` would otherwise score the copied oracle as one of the
    dev's tests, and ``production_tree_changed`` reads the tree too. This was a
    comment with no test."""
    src = Path("factory/chain/gates/evaluator.py").read_text(encoding="utf-8")
    body = src.split("for mod in (", 1)[1].split("):", 1)[0]
    mods = [
        m.strip().rstrip(",")
        for m in body.strip().splitlines()
        if m.strip() and not m.strip().startswith("#")
    ]
    assert mods[-1] == "acceptance_verified", mods


# =========================================================================== #
# red_green unit coverage (the A.6 machinery itself)
# =========================================================================== #


@pytest.mark.parametrize(
    ("exit_code", "output", "expected"),
    [
        (0, "1 passed in 0.01s", "pass"),
        (1, "1 failed in 0.01s", "fail"),
        (2, "1 error in 0.01s", "fail"),
        (0, "1 skipped in 0.01s", "vacuous"),
        (5, "no tests ran in 0.01s", "vacuous"),
        (0, "1 xfailed in 0.01s", "vacuous"),
        (127, "bash: uv: command not found", "unreadable"),
        (124, "command timed out after 600s\n1 passed in 0.01s", "unreadable"),
        (0, "", "unreadable"),
    ],
)
def test_classify_pytest_run(exit_code: int, output: str, expected: str) -> None:
    assert red_green.classify_pytest_run(exit_code, output)[0] == expected


@pytest.mark.parametrize(
    ("exit_code", "output", "expected"),
    [
        (1, "1 failed, 2 passed in 0.1s", "red"),   # PARTIAL red is enough (the caveat)
        # An ERRORS-ONLY red is NOT proof of failability: an oracle that cannot be
        # collected at the base is red whatever it asserts. ``unknown`` → ablation.
        (2, "1 error in 0.1s", "unknown"),
        (2, "3 errors in 0.1s", "unknown"),
        # ...but a run where an assertion DID fail is red even if something also
        # errored. Demanding an all-clean red would reject good work (the caveat).
        (1, "1 failed, 1 error in 0.1s", "red"),
        # Non-zero exit with no reported outcome is not an attributable red either.
        (1, "3 passed in 0.1s", "unknown"),
        (0, "3 passed in 0.1s", "green"),
        (0, "2 skipped in 0.1s", "unknown"),
        (124, "timed out", "unknown"),
        (127, "not found", "unknown"),
        (0, "5 passed in 0.1s\n1 skipped in 0.2s", "unknown"),  # conflicting
    ],
)
def test_base_verdict(exit_code: int, output: str, expected: str) -> None:
    assert red_green.base_verdict(exit_code, output)[0] == expected


def test_judge_worktree_cleans_up_even_when_the_body_raises(tmp_path: Path) -> None:
    repo, _b, _h = _repo(tmp_path)
    seen: list[Path] = []
    with pytest.raises(RuntimeError):
        with red_green.judge_worktree(repo, "HEAD") as (tree, err):
            assert tree is not None and err == ""
            seen.append(tree)
            raise RuntimeError("boom")
    assert not seen[0].exists()
    assert "factory-judge" not in _git(repo, "worktree", "list")


def test_judge_worktree_reports_failure_instead_of_raising(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with red_green.judge_worktree(plain, "HEAD") as (tree, err):
        assert tree is None
        assert err


def test_base_run_cache_only_keeps_the_newest_entries(tmp_path: Path) -> None:
    p = tmp_path / "base_runs.json"
    for i in range(15):
        red_green.cache_put(p, f"k{i}", {"verdict": "red", "n": i}, keep=5)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert len(raw) == 5
