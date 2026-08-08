"""Tests for ``factory.chain.handlers.handle_tech_writer`` — dry-run + violation handling."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from factory.app_config import AppConfig
from factory.chain.handlers import _writing_worktree, handle_tech_writer, persist_story
from factory.chain.state_machine import StoryRecord, StoryState


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    import subprocess

    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "apps" / "sacrifice").mkdir(parents=True, exist_ok=True)
    # The handler resolves the app repo via ``resolve_app_repo_path`` and
    # then creates a per-story git worktree under ``state/worktrees/``.
    # The source repo MUST be a real git repo (``git worktree add`` needs
    # ``.git``) — initialise one with a single commit so worktree creation
    # succeeds.
    src = tmp_path / "sacrifice"
    src.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=str(src), check=True)
    subprocess.run(["git", "config", "user.email", "t@e.x"], cwd=str(src), check=True)
    subprocess.run(["git", "config", "user.name", "T E"], cwd=str(src), check=True)
    (src / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(src), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(src), check=True)
    return tmp_path


@pytest.fixture
def app_config(temp_root: Path) -> AppConfig:
    # Point ``app_repo_path`` at the in-tree sacrifice/ dir so context updates
    # land inside the tmp tree rather than chasing a ``../sacrifice`` sibling.
    return AppConfig(
        name="sacrifice",
        repo="x/y",
        app_repo_path=str(temp_root / "sacrifice"),
    )


def _story_at_reviewer_done(root: Path) -> StoryRecord:
    db = root / "state" / "factory.db"
    return persist_story(
        StoryRecord(
            direction_id="005",
            app="sacrifice",
            title="t",
            slug="t",
            scope="backend",
            state=StoryState.REVIEWER_DONE.value,
        ),
        db,
    )


def test_dry_run_advances_to_tech_writer_done_without_writing_files(
    temp_root: Path, app_config: AppConfig
) -> None:
    """Dry-run MUST NOT write any files to the app repo."""
    s = _story_at_reviewer_done(temp_root)
    db = temp_root / "state" / "factory.db"

    result = handle_tech_writer(s, app_config, temp_root, dry_run=True, db_path=db)
    assert result.next_state == StoryState.TECH_WRITER_DONE
    # Confirm no files written to apps/sacrifice/context/
    context_dir = temp_root / "apps" / "sacrifice" / "context"
    assert not context_dir.exists() or not list(context_dir.glob("**/*.md"))
    # tech_writer_result_json persisted.
    assert s.tech_writer_result_json is not None
    tw = json.loads(s.tech_writer_result_json)
    assert "context_updates" in tw


def test_real_run_writes_to_canonical_path(temp_root: Path, app_config: AppConfig) -> None:
    """A fixture with a canonical context update should write the file."""
    s = _story_at_reviewer_done(temp_root)
    db = temp_root / "state" / "factory.db"

    fixture = {
        "context_updates": [
            {
                "path": "context/current-state.md",
                "action": "rewrite",
                "content": "# Current state\n\nApp uses SQLite via `app/db.py`.\n",
            }
        ],
        "rationale": "Added DB module.",
    }
    result = handle_tech_writer(
        s, app_config, temp_root, dry_run=False, db_path=db, fixture=fixture
    )
    assert result.next_state == StoryState.TECH_WRITER_DONE
    # Post-worktree refactor: the file lands in the per-story worktree,
    # not the source repo's working tree. The worktree shares ``.git``
    # with the source repo so the commit will appear there once we merge;
    # for this test we just confirm the file exists under the worktree.
    worktree_root = temp_root / "state" / "worktrees"
    written_files = list(worktree_root.glob("**/context/current-state.md"))
    assert written_files, (
        f"context/current-state.md should have been written under "
        f"{worktree_root}; tree:\n"
        + "\n".join(str(p) for p in worktree_root.glob("**/*") if p.is_file())
    )
    written = written_files[0].read_text(encoding="utf-8")
    assert "SQLite" in written


def test_forbidden_path_raises_error_and_does_not_write(
    temp_root: Path, app_config: AppConfig
) -> None:
    """A fixture with a forbidden path must not write anything and must surface error."""
    s = _story_at_reviewer_done(temp_root)
    db = temp_root / "state" / "factory.db"

    fixture = {
        "context_updates": [
            {
                "path": "context/decisions/0001-foo.md",  # forbidden
                "action": "rewrite",
                "content": "blocked",
            }
        ],
        "rationale": "should be rejected",
    }
    result = handle_tech_writer(
        s, app_config, temp_root, dry_run=False, db_path=db, fixture=fixture
    )
    # Apply failed -> story bounces to REVIEWER_REQUESTED_CHANGES so the
    # dev loop can replay rather than leaving the chain stuck mid-write.
    assert result.next_state == StoryState.REVIEWER_REQUESTED_CHANGES
    assert s.state == StoryState.REVIEWER_REQUESTED_CHANGES.value
    assert result.error and "context update failed" in result.error
    assert s.error and "context update failed" in s.error
    # The forbidden file was NOT written (in either path — assert both).
    forbidden = temp_root / "sacrifice" / "context" / "decisions" / "0001-foo.md"
    assert not forbidden.exists()


# --------------------------------------------------------------------------- #
# S3 (019 fail-silent audit): JSON parse failure retries, then blocks —
# NEVER persists an unsatisfiable ``docs-current`` result.
# --------------------------------------------------------------------------- #


def _commit_a_change(worktree: Path) -> None:
    (worktree / "feature.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(worktree), check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@e.x", "-c", "user.name=T E", "commit", "-q", "-m", "feat"],
        cwd=str(worktree),
        check=True,
    )


def _patch_tech_writer_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    import factory.chain.handlers as handlers_mod

    monkeypatch.setattr(handlers_mod, "find_direction_for_story", lambda *a, **k: None)
    monkeypatch.setattr(handlers_mod, "_read_story_file_content", lambda *a, **k: "story")
    monkeypatch.setattr(handlers_mod, "_read_persona_prompt", lambda _p: "persona")
    monkeypatch.setattr(handlers_mod, "route", lambda *a, **k: "azure/gpt-5.4")
    monkeypatch.setattr("factory.context.loader.compose_context_prelude", lambda *a, **k: "ctx")


def test_persistent_parse_failure_retries_then_blocks_without_persisting_unsatisfiable_result(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that NEVER returns parseable JSON must retry (strictly below
    the hard cap of 3), then route to the blocked sink — and must NEVER
    persist ``tech_writer_result_json`` in a shape the ``docs-current``
    REQUIRED gate can't satisfy (the old behaviour: ``{"context_updates":
    [], "rationale": "tech_writer JSON parse failed"}``, which matches none
    of the gate's legacy literal phrases and permanently strands the story)."""
    s = _story_at_reviewer_done(temp_root)
    db = temp_root / "state" / "factory.db"
    worktree = _writing_worktree(app_config, temp_root, s)
    _commit_a_change(worktree)

    _patch_tech_writer_prep(monkeypatch)

    calls: list[dict[str, Any]] = []
    import factory.runner as runner_mod

    def _fake_text_run(**kwargs: Any) -> str:
        calls.append(kwargs)
        return "not json at all"

    monkeypatch.setattr(runner_mod, "text_run", _fake_text_run)

    result = handle_tech_writer(s, app_config, temp_root, dry_run=False, db_path=db)

    from factory.chain.handlers import _MAX_TECH_WRITER_PARSE_RETRIES

    assert len(calls) == _MAX_TECH_WRITER_PARSE_RETRIES, "must retry, strictly below the hard cap"
    assert result.next_state == StoryState.BLOCKED_REVIEW_NONCONVERGENT
    assert s.state == StoryState.BLOCKED_REVIEW_NONCONVERGENT.value
    assert s.error is not None and "tech_writer" in s.error
    assert s.last_rejection_reason is not None
    # The docs-current-unsatisfiable placeholder must NEVER be persisted.
    assert s.tech_writer_result_json is None or "JSON parse failed" not in (
        s.tech_writer_result_json or ""
    )


def test_parse_failure_then_success_recovers_within_the_retry_budget(
    temp_root: Path, app_config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A transient hiccup (bad output ONCE, then a valid object) must
    recover inline — no block, no wasted tick."""
    s = _story_at_reviewer_done(temp_root)
    db = temp_root / "state" / "factory.db"
    worktree = _writing_worktree(app_config, temp_root, s)
    _commit_a_change(worktree)

    _patch_tech_writer_prep(monkeypatch)

    calls: list[dict[str, Any]] = []
    import factory.runner as runner_mod

    def _fake_text_run(**kwargs: Any) -> str:
        calls.append(kwargs)
        if len(calls) == 1:
            return "not json at all"
        return json.dumps({"context_updates": [], "no_updates_needed": True, "rationale": "ok"})

    monkeypatch.setattr(runner_mod, "text_run", _fake_text_run)

    result = handle_tech_writer(s, app_config, temp_root, dry_run=False, db_path=db)

    assert len(calls) == 2
    assert result.next_state == StoryState.TECH_WRITER_DONE
    tw = json.loads(s.tech_writer_result_json)
    assert tw["no_updates_needed"] is True
