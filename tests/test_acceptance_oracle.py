"""Tests for the WS1.2 independent acceptance oracle.

Covers the four properties the design promises:

  (a) the acceptance gate PASSES when delivered code satisfies the ACs and
      FAILS when it violates one — EVEN when the dev's own suite is green (the
      core anti-reward-hack case);
  (b) the authored acceptance test lands OUTSIDE the dev worktree (independence);
  (c) the gate + required-wiring are per-app opt-in (off by default);
  (d) dry-run / no-ref / missing-file are non-authoritative, never a false pass.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from factory.app_config import AppConfig, AppGatesConfig
from factory.chain.acceptance import (
    acceptance_dir,
    author_acceptance_test,
    build_spec_prompt,
)
from factory.chain.gates import acceptance_verified
from factory.chain.gates.evaluator import (
    ALL_GATE_LABELS,
    LOOP4_REQUIRED_GATE_LABELS,
    PRContext,
    required_gate_labels,
)
from factory.chain.state_machine import StoryRecord, StoryState
from factory.chain.worktree import ensure_worktree_for_story, worktree_path
from factory.directions.parser import Direction

# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def _story(*, story_id: int | None = 7, ref: str | None = None) -> StoryRecord:
    s = StoryRecord(
        id=story_id,
        direction_id="002",
        app="sacrifice",
        title="lowercase the email",
        slug="lowercase-email",
        scope="backend",
        state=StoryState.PR_OPEN.value,
        acceptance_test_ref=ref,
    )
    return s


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


def _oracle_cfg(*, on: bool = True, command: str | None = None) -> AppConfig:
    return AppConfig(
        name="sacrifice",
        repo="o/r",
        gates=AppGatesConfig(acceptance_oracle=on, acceptance_test_command=command),
    )


# The acceptance test the oracle would author from a spec like
# "the app lowercases the email before storing it". Behavioral, blind to impl.
_ACCEPTANCE_TEST_SRC = (
    "from mod import normalize_email\n"
    "\n"
    "def test_ac1_email_is_lowercased():\n"
    "    assert normalize_email('User@Example.COM') == 'user@example.com'\n"
)


def _make_app_checkout(repo_root: Path, *, correct: bool) -> None:
    """A tiny runnable app checkout. ``correct`` decides whether it satisfies
    the acceptance criterion. When incorrect, the app's OWN unit tests still
    pass (they assert the buggy behaviour) — the oracle is what catches it."""
    (repo_root / "conftest.py").write_text("", encoding="utf-8")  # repo on sys.path
    if correct:
        impl = "def normalize_email(e):\n    return e.lower()\n"
    else:
        # Reward-hack shape: only strips whitespace, never lowercases — but the
        # dev's own test below asserts exactly this buggy behaviour, so the
        # dev suite is green.
        impl = "def normalize_email(e):\n    return e.strip()\n"
    (repo_root / "mod.py").write_text(impl, encoding="utf-8")
    (repo_root / "tests").mkdir(exist_ok=True)
    dev_assert = "'user@example.com'" if correct else "'User@Example.COM'"
    (repo_root / "tests" / "test_dev_own.py").write_text(
        "from mod import normalize_email\n"
        "def test_dev():\n"
        f"    assert normalize_email('User@Example.COM ') == {dev_assert}\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# (a) core anti-reward-hack: oracle catches a spec violation the dev suite hides
# --------------------------------------------------------------------------- #


def test_gate_passes_when_code_satisfies_acs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_app_checkout(repo, correct=True)
    root = tmp_path / "factory"
    ref = _write_stored_oracle(root, story_id=7)

    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(story_id=7, ref=ref),
        repo_root=repo,
        software_factory_root=root,
        dry_run=False,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=True))
    assert r.passed, r.reason
    assert r.details["authoritative"] is True


def test_gate_fails_on_ac_violation_even_when_dev_tests_green(tmp_path: Path) -> None:
    """The whole point: the dev's OWN suite is green (it asserts the buggy
    behaviour), but the independent oracle fails because an AC is violated."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_app_checkout(repo, correct=False)
    # Sanity: the dev's own suite really is green on the buggy code.
    dev_run = subprocess.run(
        ["python", "-m", "pytest", "tests/test_dev_own.py", "-q"],
        cwd=repo, capture_output=True, text=True,
    )
    assert dev_run.returncode == 0, dev_run.stdout + dev_run.stderr

    root = tmp_path / "factory"
    ref = _write_stored_oracle(root, story_id=7)
    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(story_id=7, ref=ref),
        repo_root=repo,
        software_factory_root=root,
        dry_run=False,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=True))
    assert not r.passed, "oracle must fail when an AC is violated"
    assert r.details["authoritative"] is True
    # And the copied-in test was cleaned up (never left to be committed).
    assert not any(p.name.startswith("test_acceptance_oracle_") for p in repo.iterdir())


def _write_stored_oracle(root: Path, *, story_id: int) -> str:
    out_dir = acceptance_dir(root, "sacrifice", story_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "test_acceptance.py").write_text(_ACCEPTANCE_TEST_SRC, encoding="utf-8")
    return str((out_dir / "test_acceptance.py").relative_to(root))


# --------------------------------------------------------------------------- #
# (b) independence: authored oracle is NOT in the dev worktree
# --------------------------------------------------------------------------- #


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_authored_oracle_not_in_dev_worktree(tmp_path: Path) -> None:
    """The dev sandbox runs against a per-story worktree of the APP repo under
    state/worktrees/. The authored oracle lands under state/acceptance/ — a
    sibling tree the worktree never contains."""
    # A real source app repo so ensure_worktree_for_story can build a worktree.
    src = tmp_path / "app"
    src.mkdir()
    _git(src, "init", "-b", "main")
    _git(src, "config", "user.email", "t@t")
    _git(src, "config", "user.name", "t")
    (src / "README.md").write_text("app\n", encoding="utf-8")
    _git(src, "add", "-A")
    _git(src, "commit", "-m", "init")

    root = tmp_path / "factory"
    root.mkdir()
    story = _story(story_id=7)

    # Author the oracle (fake author fn — no LLM).
    direction = _direction(tmp_path, ["the email is lowercased before storing"])
    ref = author_acceptance_test(
        story,
        direction,
        _oracle_cfg(on=True),
        root,
        dry_run=False,
        db_path=root / "state" / "factory.db",
        author_fn=lambda _spec, _s: _ACCEPTANCE_TEST_SRC,
    )
    assert ref is not None
    stored = root / ref
    assert stored.exists()

    # Build the dev worktree exactly as the chain does.
    wt = ensure_worktree_for_story(
        src,
        software_factory_root=root,
        app="sacrifice",
        story_id=7,
        slug="lowercase-email",
        base_branch="main",
    )

    # The independence guarantee: no acceptance test anywhere in the worktree.
    assert wt == worktree_path(root, "sacrifice", 7, "lowercase-email")
    worktree_files = {p.name for p in wt.rglob("*") if p.is_file()}
    assert "test_acceptance.py" not in worktree_files
    assert not any("acceptance" in name for name in worktree_files)
    # And the stored oracle lives under state/acceptance/, not state/worktrees/.
    assert "state/acceptance/" in stored.as_posix()
    assert "worktrees" not in stored.relative_to(root).as_posix()


def test_spec_prompt_is_spec_only(tmp_path: Path) -> None:
    """The author prompt carries the ACs (spec) and never any implementation."""
    story = _story()
    direction = _direction(tmp_path, ["returns 404 when the goal is missing"])
    prompt = build_spec_prompt(story, direction)
    assert "returns 404 when the goal is missing" in prompt
    assert "Acceptance criteria" in prompt
    # No implementation channel exists in the prompt builder's inputs at all.
    assert "def " not in prompt


# --------------------------------------------------------------------------- #
# (c) per-app opt-in (off by default)
# --------------------------------------------------------------------------- #


def test_gate_skips_when_not_opted_in(tmp_path: Path) -> None:
    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(ref="state/acceptance/sacrifice/7/test_acceptance.py"),
        software_factory_root=tmp_path,
        dry_run=False,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=False))
    assert r.passed and "not enabled" in r.reason
    assert r.details["acceptance_oracle"] is False


def test_acceptance_verified_label_present_in_all_gates() -> None:
    assert "acceptance-verified" in ALL_GATE_LABELS


def test_not_required_without_opt_in() -> None:
    story = _story(ref="state/acceptance/sacrifice/7/test_acceptance.py")
    assert required_gate_labels(_oracle_cfg(on=False), story) == LOOP4_REQUIRED_GATE_LABELS
    assert "acceptance-verified" not in required_gate_labels(_oracle_cfg(on=False), story)


def test_not_required_when_opted_in_but_no_ref() -> None:
    """Opt-in app, but this story has no authored oracle (legacy / no ACs) —
    the gate must NOT be required for it, so it never blocks such stories."""
    story = _story(ref=None)
    labels = required_gate_labels(_oracle_cfg(on=True), story)
    assert "acceptance-verified" not in labels


def test_required_when_opted_in_and_ref_present() -> None:
    story = _story(ref="state/acceptance/sacrifice/7/test_acceptance.py")
    labels = required_gate_labels(_oracle_cfg(on=True), story)
    assert "acceptance-verified" in labels
    for base in LOOP4_REQUIRED_GATE_LABELS:
        assert base in labels


def test_not_required_without_story() -> None:
    """App-level query (no story): the gate can't be required — nothing to
    verify against yet."""
    assert "acceptance-verified" not in required_gate_labels(_oracle_cfg(on=True))


# --------------------------------------------------------------------------- #
# (d) non-authoritative, never a false pass
# --------------------------------------------------------------------------- #


def test_dry_run_is_non_authoritative(tmp_path: Path) -> None:
    ref = _write_stored_oracle(tmp_path, story_id=7)
    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(story_id=7, ref=ref),
        software_factory_root=tmp_path,
        repo_root=None,
        dry_run=True,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=True))
    assert not r.passed
    assert r.details["authoritative"] is False


def test_opted_in_no_ref_is_non_authoritative_not_pass(tmp_path: Path) -> None:
    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(ref=None),
        software_factory_root=tmp_path,
        dry_run=False,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=True))
    assert not r.passed
    assert r.details["authoritative"] is False


def test_missing_stored_file_is_non_authoritative(tmp_path: Path) -> None:
    pr = PRContext(
        pr_number=1,
        head_sha="a",
        base_branch="main",
        story=_story(ref="state/acceptance/sacrifice/7/test_acceptance.py"),
        software_factory_root=tmp_path,  # file does not exist under here
        repo_root=tmp_path / "repo",
        dry_run=False,
    )
    r = acceptance_verified.evaluate(pr, _oracle_cfg(on=True))
    assert not r.passed
    assert r.details["authoritative"] is False


# --------------------------------------------------------------------------- #
# authoring guards
# --------------------------------------------------------------------------- #


def test_author_returns_none_when_not_opted_in(tmp_path: Path) -> None:
    story = _story()
    direction = _direction(tmp_path, ["some AC"])
    ref = author_acceptance_test(
        story, direction, _oracle_cfg(on=False), tmp_path,
        author_fn=lambda _s, _st: _ACCEPTANCE_TEST_SRC,
    )
    assert ref is None
    assert story.acceptance_test_ref is None


def test_author_returns_none_without_acceptance_criteria(tmp_path: Path) -> None:
    story = _story()
    direction = _direction(tmp_path, [])
    ref = author_acceptance_test(
        story, direction, _oracle_cfg(on=True), tmp_path,
        author_fn=lambda _s, _st: _ACCEPTANCE_TEST_SRC,
    )
    assert ref is None


def test_author_skips_llm_in_dry_run(tmp_path: Path) -> None:
    story = _story()
    direction = _direction(tmp_path, ["some AC"])
    calls: list[str] = []

    def _fake(_spec: str, _st: StoryRecord) -> str:
        calls.append("called")
        return _ACCEPTANCE_TEST_SRC

    ref = author_acceptance_test(
        story, direction, _oracle_cfg(on=True), tmp_path,
        dry_run=True, author_fn=_fake,
    )
    assert ref is None
    assert calls == []  # no author call in dry-run → gate stays non-authoritative


def test_author_writes_outside_repo_and_sets_ref(tmp_path: Path) -> None:
    story = _story(story_id=42)
    direction = _direction(tmp_path, ["the email is lowercased"])
    root = tmp_path / "factory"
    ref = author_acceptance_test(
        story, direction, _oracle_cfg(on=True), root,
        dry_run=False, db_path=root / "state" / "factory.db",
        author_fn=lambda _s, _st: _ACCEPTANCE_TEST_SRC,
    )
    assert ref == story.acceptance_test_ref
    assert (root / ref).read_text() == _ACCEPTANCE_TEST_SRC
    assert ref.startswith("state/acceptance/sacrifice/42/")
