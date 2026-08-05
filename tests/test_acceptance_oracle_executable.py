"""The acceptance oracle, made EXECUTABLE (2026-08-05).

``factory/chain/acceptance.py`` + the ``acceptance-verified`` gate had never run
once in production (``acceptance_expected`` 0/165 stories, ``state/acceptance/``
absent, ``gates.acceptance_oracle`` set in no app config). Driving it for real
against a sacrifice direction found the defects covered here:

  (1) the author guessed module paths and produced a test that could not import
      the app — a 100% FALSE BLOCK; the gate now runs in a configured
      directory/cwd and the author gets the app's harness facts;
  (2) nothing validated the author's output, so prose or a markdown fence would
      be stored as the story's oracle and only fail at merge time;
  (3) an all-skipped run exits 0 — exit-0-means-pass credited a verification
      that never happened;
  (4) the copy the gate drops into the checkout lands in the story's own DEV
      WORKTREE, which the chain later ``git add -A``s — a crash mid-run leaked
      the hidden oracle to the dev and into the PR;
  (5) required-ness read a DB flag written by a best-effort write, so a lost
      write shipped a story un-gated;
  (6) any infrastructure error inside the gate escaped and aborted the whole
      merge evaluation;
  (7) authoring could re-fire forever, and could re-author over a frozen oracle.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from factory.app_config import AppConfig, AppGatesConfig
from factory.chain.acceptance import (
    ORACLE_COPY_PREFIX,
    OracleSourceError,
    acceptance_dir,
    author_acceptance_test,
    build_spec_prompt,
    normalize_oracle_source,
    reauthor_missing_oracles,
    sweep_leaked_oracles,
)
from factory.chain.gates import acceptance_verified
from factory.chain.gates.evaluator import PRContext
from factory.chain.state_machine import StoryRecord, StoryState
from factory.directions.parser import Direction

_GOOD_ORACLE = (
    "from app.mod import normalize_email\n"
    "\n"
    "def test_ac1_email_is_lowercased():\n"
    "    assert normalize_email('User@Example.COM') == 'user@example.com'\n"
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _story(
    *,
    story_id: int | None = 7,
    ref: str | None = None,
    expected: bool = True,
    state: str = StoryState.PR_OPEN.value,
) -> StoryRecord:
    return StoryRecord(
        id=story_id,
        direction_id="002",
        app="sacrifice",
        title="lowercase the email",
        slug="lowercase-email",
        scope="backend",
        state=state,
        acceptance_test_ref=ref,
        acceptance_expected=expected,
    )


def _direction(tmp_path: Path, acceptance: list[str]) -> Direction:
    d = tmp_path / "dir"
    d.mkdir(parents=True, exist_ok=True)
    return Direction(
        id="002",
        slug="emails",
        title="Email handling",
        type_tag=None,
        why=None,
        has_flow=False,
        has_api_spec=False,
        acceptance=acceptance,
        explore_tag=False,
        artifacts_paths=[],
        app="sacrifice",
        status="pm-validated",
        raw_frontmatter={},
        raw_body="",
        dir_path=d,
    )


def _cfg(
    *,
    on: bool = True,
    command: str | None = None,
    test_dir: str | None = None,
    cwd: str | None = None,
    hint: str | None = None,
) -> AppConfig:
    return AppConfig(
        name="sacrifice",
        repo="o/r",
        gates=AppGatesConfig(
            acceptance_oracle=on,
            acceptance_test_command=command,
            acceptance_test_dir=test_dir,
            acceptance_test_cwd=cwd,
            acceptance_harness_hint=hint,
        ),
    )


def _nested_checkout(repo: Path, *, correct: bool = True) -> None:
    """A checkout shaped like a real app: the package lives under ``backend/``.

    Importable only with ``cwd=backend`` — which is exactly why an oracle dropped
    at the repo root and run from the repo root cannot import it.
    """
    (repo / "backend" / "app").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "backend" / "app" / "__init__.py").write_text("", encoding="utf-8")
    impl = (
        "def normalize_email(e):\n    return e.lower()\n"
        if correct
        else "def normalize_email(e):\n    return e.strip()\n"
    )
    (repo / "backend" / "app" / "mod.py").write_text(impl, encoding="utf-8")


def _store_oracle(root: Path, *, story_id: int, content: str = _GOOD_ORACLE) -> str:
    out = acceptance_dir(root, "sacrifice", story_id)
    out.mkdir(parents=True, exist_ok=True)
    (out / "test_acceptance.py").write_text(content, encoding="utf-8")
    return str((out / "test_acceptance.py").relative_to(root))


def _pr(root: Path, repo: Path | None, story: StoryRecord) -> PRContext:
    return PRContext(
        pr_number=1,
        head_sha="abc",
        base_branch="main",
        story=story,
        repo_root=repo,
        software_factory_root=root,
        dry_run=False,
    )


def _write_direction_dir(root: Path, *, acceptance: list[str], direction_id: str = "002") -> None:
    ddir = root / "apps" / "sacrifice" / "directions" / f"{direction_id}-emails"
    ddir.mkdir(parents=True, exist_ok=True)
    block = (
        "\n## Acceptance Criteria\n\n" + "\n".join(f"- {a}" for a in acceptance) + "\n"
        if acceptance
        else ""
    )
    (ddir / "direction.md").write_text(
        f"---\ntitle: emails\n---\n\n# emails\n\n## Why\n\nx.\n{block}", encoding="utf-8"
    )


def _write_app_config(root: Path, *, on: bool = True) -> None:
    p = root / "apps" / "sacrifice"
    p.mkdir(parents=True, exist_ok=True)
    (p / "config.yaml").write_text(
        f"name: sacrifice\nrepo: o/r\ngates:\n  acceptance_oracle: {str(on).lower()}\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# (1) the false block: WHERE the oracle runs
# --------------------------------------------------------------------------- #


def test_default_root_placement_cannot_import_a_real_app(tmp_path: Path) -> None:
    """Reproduces the first real run: repo-root placement → import error → block."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(_pr(root, repo, _story(ref=ref)), _cfg())
    assert not r.passed
    assert r.details["exit_code"] != 0


def test_configured_dir_and_cwd_make_the_same_oracle_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(test_dir="backend/tests", cwd="backend"),
    )
    assert r.passed, r.details.get("output_tail")
    assert r.details["authoritative"] is True
    assert r.details["test_file"] == f"tests/{ORACLE_COPY_PREFIX}7.py"
    assert str(r.details["cwd"]).endswith("backend")
    assert r.details["tests_passed"] == 1


def test_configured_placement_still_fails_a_violating_implementation(tmp_path: Path) -> None:
    """The gate must keep FAILING on a real AC violation, not merely run."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo, correct=False)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(test_dir="backend/tests", cwd="backend"),
    )
    assert not r.passed
    assert r.details["authoritative"] is True


def test_test_dir_outside_the_checkout_blocks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="../escape")
    )
    assert not r.passed
    assert "acceptance_test_dir" in str(r.details.get("infra_error", "")) or "outside" in r.reason


def test_missing_test_dir_blocks_instead_of_raising(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="backend/tests")
    )
    assert not r.passed
    assert r.details["authoritative"] is True


# --------------------------------------------------------------------------- #
# (2) the author's output is validated before it becomes the oracle
# --------------------------------------------------------------------------- #


def test_normalize_strips_a_markdown_fence() -> None:
    fenced = "```python\ndef test_ac1():\n    assert 1 == 1\n```"
    out = normalize_oracle_source(fenced)
    assert out.startswith("def test_ac1():")
    assert "```" not in out


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "I'm sorry, I cannot write this test without seeing the code.",
        "def helper():\n    return 1\n",  # no test_* function
        "def test_ac1(:\n    pass\n",  # syntax error
    ],
)
def test_normalize_rejects_unusable_output(bad: str) -> None:
    with pytest.raises(OracleSourceError):
        normalize_oracle_source(bad)


def test_unusable_author_output_is_a_failed_attempt_not_a_stored_oracle(
    tmp_path: Path,
) -> None:
    story = _story(story_id=13)
    root = tmp_path / "factory"
    calls = {"n": 0}

    def _prose(_spec: str, _s: StoryRecord) -> str:
        calls["n"] += 1
        return "Sure! Here is a plan for the acceptance test."

    ref = author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db", author_fn=_prose,
    )
    assert ref is None
    assert story.acceptance_test_ref is None
    assert story.acceptance_expected is True  # blocks, never silently ships
    assert calls["n"] == 3  # retried inside the pass
    assert not (acceptance_dir(root, "sacrifice", 13) / "test_acceptance.py").exists()


def test_fenced_author_output_is_stored_unfenced_and_runs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    story = _story(story_id=7, ref=None)
    ref = author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db",
        author_fn=lambda _s, _st: f"```python\n{_GOOD_ORACLE}```",
    )
    assert ref is not None
    r = acceptance_verified.evaluate(
        _pr(root, repo, story), _cfg(test_dir="backend/tests", cwd="backend")
    )
    assert r.passed, r.details.get("output_tail")


# --------------------------------------------------------------------------- #
# (3) a run that verifies nothing is not a pass
# --------------------------------------------------------------------------- #


_ALL_SKIPPED = (
    "import pytest\n"
    "\n"
    "def test_ac1_untestable():\n"
    "    pytest.skip('criterion is too vague to assert')\n"
)


def test_all_skipped_oracle_exits_zero_but_gate_blocks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7, content=_ALL_SKIPPED)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="backend/tests", cwd="backend")
    )
    assert r.details["exit_code"] == 0  # pytest is happy
    assert not r.passed, "an all-skipped oracle verifies nothing and must not pass"
    assert r.details["tests_passed"] == 0
    assert "vacuous" in r.reason


# --------------------------------------------------------------------------- #
# (4) the copy must never survive in the dev's worktree
# --------------------------------------------------------------------------- #


def test_stale_copy_anywhere_in_the_checkout_is_swept(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    stale = repo / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}999.py"
    stale.write_text("def test_leaked():\n    assert True\n", encoding="utf-8")
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="backend/tests", cwd="backend")
    )
    assert r.passed
    assert r.details["swept_before_run"] == [f"backend/tests/{ORACLE_COPY_PREFIX}999.py"]
    assert not stale.exists()
    assert sweep_leaked_oracles(repo) == []


def test_gate_excludes_the_oracle_pattern_from_git(tmp_path: Path) -> None:
    """Even a leaked copy must be un-committable: the chain does ``git add -A``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="backend/tests", cwd="backend")
    )
    excl = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert f"{ORACLE_COPY_PREFIX}*" in excl
    # Prove it: plant a leak — source AND the compiled copy pytest leaves behind,
    # which is what actually got staged before this test existed — and stage
    # everything the way the chain's dev commit does.
    leak = repo / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}7.py"
    leak.write_text(_GOOD_ORACLE, encoding="utf-8")
    pyc_dir = repo / "backend" / "tests" / "__pycache__"
    pyc_dir.mkdir(exist_ok=True)
    (pyc_dir / f"{ORACLE_COPY_PREFIX}7.cpython-312.pyc").write_bytes(b"\x00compiled")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert ORACLE_COPY_PREFIX not in staged


def test_reused_worktree_ensure_sweeps_a_leaked_oracle(tmp_path: Path) -> None:
    from factory.chain.worktree import ensure_worktree_for_story

    src = tmp_path / "app"
    src.mkdir()
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *args], cwd=src, check=True, capture_output=True)
    (src / "README.md").write_text("app\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "i"], cwd=src, check=True, capture_output=True)

    root = tmp_path / "factory"
    root.mkdir()
    wt = ensure_worktree_for_story(
        src, software_factory_root=root, app="sacrifice", story_id=7,
        slug="lowercase-email", base_branch="main",
    )
    leak = wt / f"{ORACLE_COPY_PREFIX}7.py"
    leak.write_text(_GOOD_ORACLE, encoding="utf-8")

    # The dev's next dispatch goes through the same ensure → the leak is gone
    # before the dev (or its ``git add -A``) can ever see it.
    again = ensure_worktree_for_story(
        src, software_factory_root=root, app="sacrifice", story_id=7,
        slug="lowercase-email", base_branch="main",
    )
    assert again == wt
    assert not leak.exists()


# --------------------------------------------------------------------------- #
# (5)/(6) fail-closed wiring
# --------------------------------------------------------------------------- #


def test_a_pr_label_cannot_substitute_for_an_oracle_run() -> None:
    from factory.chain.auto_merge import _RESULT_ONLY_GATE_LABELS

    assert "acceptance-verified" in _RESULT_ONLY_GATE_LABELS


def test_stray_braces_in_the_command_template_block_rather_than_crash(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    # ``str.format`` would raise KeyError('foo') here and abort the whole merge
    # evaluation; literal substitution keeps it a normal (failing) command.
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(command="echo {foo} {test_file} && exit 3", test_dir="backend/tests", cwd="backend"),
    )
    assert not r.passed
    assert r.details["exit_code"] == 3


def test_unexpected_gate_error_blocks_authoritatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)

    def _boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(acceptance_verified.shutil, "copyfile", _boom)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)), _cfg(test_dir="backend/tests", cwd="backend")
    )
    assert not r.passed
    assert r.details["authoritative"] is True
    assert "disk on fire" in str(r.details["infra_error"])


def test_command_that_never_names_the_oracle_blocks(tmp_path: Path) -> None:
    """A config typo that drops ``{test_file}`` would otherwise produce a green
    gate for a command that never ran the oracle."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(command="pytest -q", test_dir="backend/tests", cwd="backend"),
    )
    assert not r.passed
    assert r.details["authoritative"] is True
    assert "{test_file}" in str(r.details["infra_error"])


def test_unreadable_non_pytest_runner_records_weaker_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(command="true {test_file}", test_dir="backend/tests", cwd="backend"),
    )
    assert r.passed  # exit 0 is all an unreadable runner gives us
    assert r.details["tests_passed"] is None
    assert "skipped" in str(r.details["vacuity_check"])


def test_wrapper_command_is_still_vacuity_checked(tmp_path: Path) -> None:
    """A wrapper (``make acceptance``) never mentions pytest, but still prints its
    summary — the check must read the OUTPUT, not the command string, or every
    wrapper-command app silently loses the anti-vacuity protection."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7, content=_ALL_SKIPPED)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(
            command=f"{sys.executable} -B -m pytest {{test_file}} -q -p no:cacheprovider"
            " | cat",  # the word 'pytest' is there, but prove output-driven below
            test_dir="backend/tests",
            cwd="backend",
        ),
    )
    assert not r.passed
    assert r.details["tests_passed"] == 0


def test_pytest_command_with_no_summary_blocks(tmp_path: Path) -> None:
    """Exit 0 with no readable pytest summary is not evidence of anything."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    r = acceptance_verified.evaluate(
        _pr(root, repo, _story(ref=ref)),
        _cfg(command="echo pytest ran {test_file}; true", test_dir="backend/tests", cwd="backend"),
    )
    assert not r.passed
    assert "no pytest result summary" in r.reason


def test_sweep_never_deletes_a_tracked_file(tmp_path: Path) -> None:
    """The sweep must not become a destructive mechanism: a COMMITTED app test whose
    name matches the pattern stays put (deleting it would be committed by the
    chain's later ``git add -A``)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _nested_checkout(repo)
    tracked = repo / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}regression.py"
    tracked.write_text("def test_kept():\n    assert True\n", encoding="utf-8")
    for args in (
        ["init", "-b", "main"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["add", "-A"],
        ["commit", "-m", "app test"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    untracked = repo / "backend" / "tests" / f"{ORACLE_COPY_PREFIX}999.py"
    untracked.write_text("def test_leaked():\n    assert True\n", encoding="utf-8")

    removed = sweep_leaked_oracles(repo)
    assert removed == [f"backend/tests/{ORACLE_COPY_PREFIX}999.py"]
    assert tracked.exists()
    assert not untracked.exists()


# --------------------------------------------------------------------------- #
# (7) authoring is bounded, idempotent, and never anonymous
# --------------------------------------------------------------------------- #


def test_author_refuses_a_story_without_an_id(tmp_path: Path) -> None:
    """An id-less story would write into the shared ``…/0/`` directory, so one
    story would end up gated by another story's oracle."""
    story = _story(story_id=None)
    root = tmp_path / "factory"
    calls: list[str] = []
    ref = author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db",
        author_fn=lambda _s, _st: (calls.append("x"), _GOOD_ORACLE)[1],
    )
    assert ref is None
    assert calls == []
    assert story.acceptance_expected is True  # still blocks
    assert not (acceptance_dir(root, "sacrifice", None) / "test_acceptance.py").exists()


def test_frozen_oracle_is_never_re_authored(tmp_path: Path) -> None:
    root = tmp_path / "factory"
    ref = _store_oracle(root, story_id=7)
    story = _story(story_id=7, ref=ref)
    calls: list[str] = []
    out = author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db",
        author_fn=lambda _s, _st: (calls.append("x"), "def test_new():\n    assert 1\n")[1],
    )
    assert out == ref
    assert calls == []  # no LLM call, no overwrite of the pre-dev freeze
    assert (root / ref).read_text(encoding="utf-8") == _GOOD_ORACLE
    # ...unless explicitly forced.
    author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db", force=True,
        author_fn=lambda _s, _st: "def test_new():\n    assert 1\n",
    )
    assert "test_new" in (root / ref).read_text(encoding="utf-8")


def test_authoring_stops_after_three_failed_passes_and_the_gate_says_so(
    tmp_path: Path,
) -> None:
    root = tmp_path / "factory"
    story = _story(story_id=9, ref=None)
    calls = {"n": 0}

    def _boom(_spec: str, _s: StoryRecord) -> str:
        calls["n"] += 1
        raise RuntimeError("provider down")

    for _ in range(3):
        author_acceptance_test(
            story, _direction(tmp_path, ["ac"]), _cfg(), root,
            dry_run=False, db_path=root / "state" / "factory.db", author_fn=_boom,
        )
    assert calls["n"] == 9  # 3 passes x 3 in-pass attempts
    sidecar = json.loads(
        (acceptance_dir(root, "sacrifice", 9) / "attempts.json").read_text(encoding="utf-8")
    )
    assert sidecar["passes"] == 3

    # A fourth pass must not call the model again — unbounded retries burn spend
    # every five minutes forever.
    author_acceptance_test(
        story, _direction(tmp_path, ["ac"]), _cfg(), root,
        dry_run=False, db_path=root / "state" / "factory.db", author_fn=_boom,
    )
    assert calls["n"] == 9

    # ...and the story stays BLOCKED, with the exhaustion named for the operator.
    r = acceptance_verified.evaluate(_pr(root, tmp_path / "repo", story), _cfg())
    assert not r.passed
    assert r.details["author_exhausted"] is True
    assert r.details["author_passes"] == 3
    assert "EXHAUSTED" in r.reason


# --------------------------------------------------------------------------- #
# self-heal: bounded, and able to catch up after the operator opts an app in
# --------------------------------------------------------------------------- #


def test_reauthor_ignores_already_shipped_stories(tmp_path: Path) -> None:
    """Opting an app in must not fire an LLM call for each historical story."""
    from factory.chain.handlers import persist_story

    root = tmp_path
    (root / "state").mkdir(parents=True, exist_ok=True)
    _write_app_config(root)
    _write_direction_dir(root, acceptance=["the email is lowercased"])
    db = root / "state" / "factory.db"
    for state in (StoryState.DEPLOYED, StoryState.SUPERSEDED_BY_SIBLING,
                  StoryState.BLOCKED_BUDGET_EXCEEDED):
        persist_story(_story(story_id=None, expected=True, state=state.value), db)

    calls: list[str] = []
    healed = reauthor_missing_oracles(
        "sacrifice", root, dry_run=False, db_path=db,
        author_fn=lambda _s, _st: (calls.append("x"), _GOOD_ORACLE)[1],
    )
    assert healed == 0
    assert calls == []


def test_reauthor_heals_an_inflight_story_whose_flag_was_never_set(tmp_path: Path) -> None:
    """After the operator flips the flag, in-flight stories spawned before the
    flip must get an oracle — otherwise they block forever with no way to heal."""
    from factory.chain.handlers import get_story, persist_story

    root = tmp_path
    (root / "state").mkdir(parents=True, exist_ok=True)
    _write_app_config(root)
    _write_direction_dir(root, acceptance=["the email is lowercased"])
    db = root / "state" / "factory.db"
    story = persist_story(_story(story_id=None, expected=False, state=StoryState.PR_OPEN.value), db)

    healed = reauthor_missing_oracles(
        "sacrifice", root, dry_run=False, db_path=db,
        author_fn=lambda _s, _st: _GOOD_ORACLE,
    )
    assert healed == 1
    refreshed = get_story(story.id, db)
    assert refreshed is not None and refreshed.acceptance_test_ref is not None
    assert refreshed.acceptance_expected is True


def test_reauthor_is_capped_per_pass(tmp_path: Path) -> None:
    from factory.chain.handlers import persist_story

    root = tmp_path
    (root / "state").mkdir(parents=True, exist_ok=True)
    _write_app_config(root)
    _write_direction_dir(root, acceptance=["the email is lowercased"])
    db = root / "state" / "factory.db"
    for _ in range(5):
        persist_story(_story(story_id=None, expected=True), db)

    calls: list[str] = []
    healed = reauthor_missing_oracles(
        "sacrifice", root, dry_run=False, db_path=db, max_per_pass=2,
        author_fn=lambda _s, _st: (calls.append("x"), _GOOD_ORACLE)[1],
    )
    assert healed == 2
    assert len(calls) == 2


def test_reauthor_noop_when_the_app_has_not_opted_in(tmp_path: Path) -> None:
    from factory.chain.handlers import persist_story

    root = tmp_path
    (root / "state").mkdir(parents=True, exist_ok=True)
    _write_app_config(root, on=False)
    _write_direction_dir(root, acceptance=["the email is lowercased"])
    db = root / "state" / "factory.db"
    persist_story(_story(story_id=None, expected=True), db)

    calls: list[str] = []
    assert reauthor_missing_oracles(
        "sacrifice", root, dry_run=False, db_path=db,
        author_fn=lambda _s, _st: (calls.append("x"), _GOOD_ORACLE)[1],
    ) == 0
    assert calls == []


# --------------------------------------------------------------------------- #
# the harness hint reaches the author, and stays spec-only
# --------------------------------------------------------------------------- #


def test_harness_hint_is_handed_to_the_author(tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def _capture(spec: str, _s: StoryRecord) -> str:
        seen["spec"] = spec
        return _GOOD_ORACLE

    author_acceptance_test(
        _story(story_id=21), _direction(tmp_path, ["the email is lowercased"]),
        _cfg(hint="The ASGI app is `app` in `app.main`. Drive it with TestClient."),
        tmp_path / "factory",
        dry_run=False, db_path=tmp_path / "factory" / "state" / "factory.db",
        author_fn=_capture,
    )
    assert "app.main" in seen["spec"]
    assert "Harness" in seen["spec"]
    # Still spec-only: the hint is layout, and the ACs are verbatim.
    assert "the email is lowercased" in seen["spec"]


def test_no_harness_section_without_a_hint(tmp_path: Path) -> None:
    prompt = build_spec_prompt(_story(), _direction(tmp_path, ["ac"]), harness_hint=None)
    assert "Harness" not in prompt


# --------------------------------------------------------------------------- #
# the real spawn path writes both artifacts (the thing that had never happened)
# --------------------------------------------------------------------------- #


def test_real_spawn_path_writes_the_oracle_and_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``handle_stories_spawned`` — the actual pm-sync entry point — must leave a
    persisted ``acceptance_expected`` AND a readable oracle outside the app repo.
    In production both were empty for all 165 stories; this pins the path that was
    supposed to fill them. Only the LLM call is faked."""
    from factory.app_config import load_app_config
    from factory.chain.handlers import handle_stories_spawned
    from factory.directions.parser import parse_direction_dir

    root = tmp_path
    (root / "state").mkdir(parents=True, exist_ok=True)
    (root / "apps" / "sacrifice").mkdir(parents=True, exist_ok=True)
    (root / "apps" / "sacrifice" / "config.yaml").write_text(
        "name: sacrifice\nrepo: o/r\ngates:\n  acceptance_oracle: true\n"
        "  acceptance_harness_hint: 'The app object is `app` in `app.main`.'\n",
        encoding="utf-8",
    )
    _write_direction_dir(root, acceptance=["the email is lowercased before storing"])
    direction = parse_direction_dir(
        "sacrifice",
        root / "apps" / "sacrifice" / "directions" / "002-emails",
        software_factory_root=root,
    )
    app_config = load_app_config("sacrifice", root)

    seen: dict[str, object] = {}

    def _fake_llm(spec_prompt: str, story: StoryRecord, **kwargs: object) -> str:
        seen["spec"] = spec_prompt
        seen["root"] = kwargs.get("software_factory_root")
        return _GOOD_ORACLE

    monkeypatch.setattr("factory.chain.acceptance._llm_author", _fake_llm)

    db = root / "state" / "factory.db"
    stories = handle_stories_spawned(
        direction,
        {"child_stories": [{"title": "Lowercase the email", "scope": "backend"}],
         "confidence": 0.9},
        app_config,
        root,
        dry_run=False,
        db_path=db,
        github_client=None,
    )
    assert len(stories) == 1

    from factory.chain.handlers import get_story

    row = get_story(stories[0].id, db)
    assert row is not None
    assert row.acceptance_expected is True
    assert row.acceptance_test_ref == f"state/acceptance/sacrifice/{row.id}/test_acceptance.py"
    assert (root / row.acceptance_test_ref).read_text(encoding="utf-8") == _GOOD_ORACLE
    # Independence: stored under state/acceptance, never under state/worktrees.
    assert "worktrees" not in row.acceptance_test_ref
    # The spec-only prompt carried the ACs and the app's harness facts, no code.
    assert "the email is lowercased before storing" in str(seen["spec"])
    assert "app.main" in str(seen["spec"])
    # ...and the call was attributed to this factory root, not to the process cwd.
    assert Path(str(seen["root"])) == root
