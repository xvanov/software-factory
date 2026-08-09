"""Pre-PR lint bounce — see handlers._residual_changed_py_lint / handle_docs_enforcer.

Sacrifice story 183 (2026-08-09) died like this, and took two of three fresh
stories with it:

  dev leaves an F401 on a MODIFIED line of a PRE-EXISTING file
    → ``_autoformat_changed_py_before_pr`` is deliberately conservative (it only
      deletes imports the BRANCH ITSELF added) and leaves it
    → no chain gate runs lint at all (an app's ``lint_command`` is decorative
      config; nothing executes it)
    → the PR opens, and GitHub's required lint check fails
    → the ci-fix redispatch runs dev, whose local loop is TESTS-only, so nothing
      forces a diff and NO new commit appears
    → the next evaluation sees the identical failure signature and terminally
      parks the story at ``blocked_ci_unresolved``, PR closed.

The fix: run the app's own ruff over the branch's own changed ``.py`` files
BEFORE the PR exists and, once, send the story back through the dev loop with
the exact violations. Capped at one bounce — a second red opens the PR and lets
the (unchanged) CI path adjudicate.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from factory.app_config import AppConfig
from factory.chain.handlers import (
    _residual_changed_py_lint,
    handle_docs_enforcer,
    persist_story,
)
from factory.chain.state_machine import StoryRecord, StoryState

# --------------------------------------------------------------------------- #
# Real-git / real-ruff tests for the helper itself.
# --------------------------------------------------------------------------- #


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=str(cwd), capture_output=True, text=True, check=True, timeout=60
    )


def _init_repo_with_origin(app_dir: Path) -> Path:
    """Working repo pushed to a bare 'origin', so ``origin/main`` resolves —
    the same topology the chain uses against a real remote."""
    origin = app_dir.parent / f"{app_dir.name}-origin.git"
    _run(["git", "init", "-q", "--bare", "--initial-branch=main", str(origin)], cwd=app_dir.parent)
    app_dir.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "--initial-branch=main"], cwd=app_dir)
    _run(["git", "config", "user.email", "t@e.x"], cwd=app_dir)
    _run(["git", "config", "user.name", "T E"], cwd=app_dir)
    (app_dir / "pyproject.toml").write_text(
        '[tool.ruff.lint]\nselect = ["E", "F", "I"]\n', encoding="utf-8"
    )
    # A PRE-EXISTING module whose import block is already there. The branch will
    # modify it — which is the shape the autoformat refuses to clean up.
    (app_dir / "legacy.py").write_text(
        '"""Legacy module."""\n\nimport os\n\nHOME = os.getcwd()\n', encoding="utf-8"
    )
    _run(["git", "add", "."], cwd=app_dir)
    _run(["git", "commit", "-q", "-m", "init"], cwd=app_dir)
    _run(["git", "remote", "add", "origin", str(origin)], cwd=app_dir)
    _run(["git", "push", "-u", "-q", "origin", "main"], cwd=app_dir)
    return app_dir


def _commit_branch(repo: Path, name: str, rel: str, content: str) -> None:
    _run(["git", "checkout", "-q", "-b", name], cwd=repo)
    (repo / rel).write_text(content, encoding="utf-8")
    _run(["git", "add", rel], cwd=repo)
    _run(["git", "commit", "-q", "-m", f"edit {rel}"], cwd=repo)


def test_residual_lint_reports_the_violation_autoformat_will_not_fix(tmp_path: Path) -> None:
    """Story 183's exact shape. The branch edits ONE line of a pre-existing file
    and, in doing so, orphans a PRE-EXISTING import. ``_autoformat_changed_py_
    before_pr`` refuses to touch it by design — it only deletes imports on lines
    the BRANCH ITSELF added — so nothing in the chain caught this and CI did.

    Both halves are asserted: the autoformat leaves the import alone (the
    premise), and the residual check reports it (the fix).
    """
    from factory.chain.handlers import _autoformat_changed_py_before_pr

    repo = _init_repo_with_origin(tmp_path / "app")
    # Only the LAST line changes; ``import os`` stays exactly where main has it,
    # and is now unused.
    _commit_branch(
        repo,
        "story/183-x",
        "legacy.py",
        '"""Legacy module."""\n\nimport os\n\nHOME = "/tmp"\n',
    )

    _autoformat_changed_py_before_pr(repo, "main")

    # Premise: the conservative autoformat did NOT (and must not) remove it.
    assert "import os" in (repo / "legacy.py").read_text(encoding="utf-8")

    residual = _residual_changed_py_lint(repo, "main")
    assert residual is not None, "an unused pre-existing import must not reach the PR silently"
    assert "F401" in residual
    assert "legacy.py" in residual


def test_residual_lint_is_none_when_the_branch_is_clean(tmp_path: Path) -> None:
    repo = _init_repo_with_origin(tmp_path / "app")
    _commit_branch(
        repo,
        "story/1-clean",
        "feat.py",
        '"""Feature."""\n\nimport os\n\nHOME = os.getcwd()\n',
    )
    assert _residual_changed_py_lint(repo, "main") is None


def test_residual_lint_fails_open_when_ruff_cannot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-OPEN is the correct direction here, and it is a deliberate exception
    to the usual fail-safe rule: GitHub CI is the authoritative lint backstop,
    so this check is only an optimisation that saves a doomed PR round-trip.
    Blocking PR creation because the LOCAL ruff is missing or wedged would trade
    a bounded, already-handled failure for a brand-new unbounded one.
    """
    repo = _init_repo_with_origin(tmp_path / "app")
    _commit_branch(
        repo, "story/1-x", "feat.py", '"""F."""\n\nimport os\nimport sys\n\nH = os.getcwd()\n'
    )
    # Sanity: it IS red before we break the runner, so the None below is caused
    # by the failure and not by a clean branch.
    assert _residual_changed_py_lint(repo, "main") is not None

    real_run = subprocess.run

    def _boom(args, *a, **k):  # type: ignore[no-untyped-def]
        # Only ``uv run ruff`` disappears; git still works, so the helper gets
        # all the way to the ruff invocation before it fails.
        if list(args)[:2] == ["uv", "run"]:
            raise FileNotFoundError("uv")
        return real_run(args, *a, **k)

    monkeypatch.setattr(subprocess, "run", _boom)
    assert _residual_changed_py_lint(repo, "main") is None


# --------------------------------------------------------------------------- #
# Handler-level: the bounce, the cap, and the clean path.
# --------------------------------------------------------------------------- #


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(name="sacrifice", repo="x/y")


def _story_ready_for_pr(root: Path) -> StoryRecord:
    db = root / "state" / "factory.db"
    s = persist_story(
        StoryRecord(
            direction_id="183",
            app="sacrifice",
            title="t",
            slug="story-183",
            scope="backend",
            state=StoryState.TECH_WRITER_DONE.value,
        ),
        db,
    )
    s.github_branch = "factory/story-183-x"
    # An already-approved story arrives here with review cycles on the clock.
    s.reviewer_cycles = 3
    s.dev_retries = 2
    persist_story(s, db)
    return s


_RUFF_OUT = "legacy.py:3:8: F401 [*] `os` imported but unused\nFound 1 error."


def test_residual_lint_bounces_the_story_back_to_dev_with_the_violations(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from factory.chain import handlers as H

    s = _story_ready_for_pr(temp_root)
    db = temp_root / "state" / "factory.db"

    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["legacy.py"])
    monkeypatch.setattr(H, "_residual_lint_for_story", lambda *a, **k: _RUFF_OUT)

    def _should_not_open(*a, **k):  # pragma: no cover - asserts non-invocation
        raise AssertionError("a lint-red branch must not reach _open_pr_for_story")

    monkeypatch.setattr(H, "_open_pr_for_story", _should_not_open)

    result = handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)

    assert result.next_state == StoryState.REVIEWER_REQUESTED_CHANGES
    assert s.github_pr_number is None
    assert result.payload["lint_bounce"] is True
    assert result.payload["residual_lint"] == _RUFF_OUT

    # The dev cycle reads findings out of reviewer_result_json (see
    # _handle_dev_once's reviewer_findings plumbing) — the violations must be
    # THERE, in the shape every consumer indexes with ``.get(...)``.
    payload = json.loads(s.reviewer_result_json or "{}")
    findings = payload["findings"]
    assert isinstance(findings, list) and isinstance(findings[0], dict)
    assert _RUFF_OUT in findings[0]["what"]
    assert findings[0]["severity"] == "high"
    assert payload["source"] == "pre_pr_lint"

    # Counters reset, same as the CI-fix re-dispatch: an approved story can sit
    # at the review cap, and the follow-up pass must not read as non-convergence.
    assert s.reviewer_cycles == 0
    assert s.dev_retries == 0


def test_second_red_opens_the_pr_anyway_the_bounce_is_capped(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exactly one bounce per story. The second red ships the PR and lets the
    (unchanged) CI path adjudicate — a repeating bounce would be a new uncapped
    loop, which the guardrails forbid."""
    from factory.chain import handlers as H

    s = _story_ready_for_pr(temp_root)
    db = temp_root / "state" / "factory.db"

    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["legacy.py"])
    monkeypatch.setattr(H, "_residual_lint_for_story", lambda *a, **k: _RUFF_OUT)
    monkeypatch.setattr(H, "_open_pr_for_story", lambda *a, **k: None)

    first = handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)
    assert first.next_state == StoryState.REVIEWER_REQUESTED_CHANGES

    # The story goes round the dev → review → tech_writer loop and arrives back
    # at the enforcer. Ruff is STILL red (the dev didn't fix it).
    s.state = StoryState.TECH_WRITER_DONE.value
    persist_story(s, db)
    monkeypatch.setattr(H, "_open_pr_for_story", lambda *a, **k: 1830)

    second = handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)

    assert second.next_state == StoryState.PR_OPEN
    assert s.github_pr_number == 1830
    # Loud, not silent: the trace says we knowingly shipped a lint-red branch.
    assert second.payload["lint_bounce_capped"] is True
    assert second.payload["residual_lint"] == _RUFF_OUT
    assert H._MAX_LINT_BOUNCES == 1


def test_bounce_count_survives_a_fresh_story_object(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cap is derived from the story's on-disk event stream, not from an
    in-memory field — so it survives a process restart (the whole reason the
    ``_gate_block_history`` precedent was chosen over a counter column, every
    candidate column being reset somewhere on this very loop)."""
    from factory.chain import handlers as H
    from factory.chain.resume import load_story

    s = _story_ready_for_pr(temp_root)
    db = temp_root / "state" / "factory.db"

    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["legacy.py"])
    monkeypatch.setattr(H, "_residual_lint_for_story", lambda *a, **k: _RUFF_OUT)
    monkeypatch.setattr(H, "_open_pr_for_story", lambda *a, **k: None)
    handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)

    # Re-read the row exactly as a later tick in a new process would.
    assert s.id is not None
    fresh = load_story(db, s.id)
    assert fresh is not None
    assert H._lint_bounces_so_far(fresh, temp_root) == 1


def test_clean_branch_opens_the_pr_as_before(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from factory.chain import handlers as H

    s = _story_ready_for_pr(temp_root)
    db = temp_root / "state" / "factory.db"

    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["legacy.py"])
    monkeypatch.setattr(H, "_residual_lint_for_story", lambda *a, **k: None)
    monkeypatch.setattr(H, "_open_pr_for_story", lambda *a, **k: 4242)

    result = handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)

    assert result.next_state == StoryState.PR_OPEN
    assert s.github_pr_number == 4242
    assert "lint_bounce" not in result.payload
    assert "lint_bounce_capped" not in result.payload
    # An untouched story keeps its counters — the reset belongs to the bounce.
    assert s.reviewer_cycles == 3


def test_lint_check_failure_does_not_block_pr_creation(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Helper unavailable (ruff missing / timeout / no worktree) → ``None`` →
    the PR opens exactly as it did before this feature existed. Fail-open is
    justified because GitHub CI is the authoritative backstop; see
    ``_residual_changed_py_lint``'s docstring."""
    from factory.chain import handlers as H

    s = _story_ready_for_pr(temp_root)
    db = temp_root / "state" / "factory.db"
    # Point at a repo path that definitively does not exist, so the REAL
    # ``_residual_lint_for_story`` runs and takes its production fail-open path
    # (no worktree) — a stub of the helper would prove nothing here.
    app_config = AppConfig(
        name="sacrifice", repo="x/y", app_repo_path=str(temp_root / "no-such-repo")
    )

    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["legacy.py"])
    monkeypatch.setattr(H, "_open_pr_for_story", lambda *a, **k: 77)

    result = handle_docs_enforcer(s, app_config, temp_root, dry_run=False, db_path=db)

    assert result.next_state == StoryState.PR_OPEN
    assert s.github_pr_number == 77
    assert "lint_bounce" not in result.payload
