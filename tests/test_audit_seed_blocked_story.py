"""Integration tests for the recoverable blocked-story audit seed fixture."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from factory.chain.audit_seed_fixtures import (
    AUDIT_REVIVAL_FIXTURE,
    capture_revival_step_evidence,
    seed_recoverable_blocked_story_fixture,
)
from factory.chain.orchestrator import tick
from factory.chain.state_machine import StoryState
from factory.observability.schema import migrate
from factory.settings.loader import reload_settings


def _seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "state" / "factory.db"
    migrate(db)
    return db


def _write_runtime_files(root: Path) -> None:
    app_dir = root / "apps" / AUDIT_REVIVAL_FIXTURE.app
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "config.yaml").write_text(
        yaml.safe_dump({"name": AUDIT_REVIVAL_FIXTURE.app, "repo": "o/r"}),
        encoding="utf-8",
    )
    (root / "factory_settings.yaml").write_text(
        "modes:\n  default: normal\n  available: [normal, paused]\n"
        "auto_merge:\n  enabled: false\n"
        "ci_health:\n  enabled: false\n",
        encoding="utf-8",
    )


def _scalar(db: Path, sql: str, params: tuple[object, ...] = ()) -> object | None:
    with sqlite3.connect(db) as conn:
        row = conn.execute(sql, params).fetchone()
    return None if row is None else row[0]


def test_seed_fixture_loads_blocked_story_for_revival(tmp_path: Path) -> None:
    """AC1.1: loading fixture yields seeded blocked story for revival."""
    db = _seeded_db(tmp_path)
    story = seed_recoverable_blocked_story_fixture(db)

    assert story.state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert story.app == AUDIT_REVIVAL_FIXTURE.app
    assert story.direction_id == AUDIT_REVIVAL_FIXTURE.direction_id
    assert story.slug == AUDIT_REVIVAL_FIXTURE.slug
    assert story.github_pr_number == AUDIT_REVIVAL_FIXTURE.pr_number


def test_seed_fixture_persists_merged_pr_recovery_context(tmp_path: Path) -> None:
    db = _seeded_db(tmp_path)
    seed_recoverable_blocked_story_fixture(db)

    merged_count = _scalar(
        db,
        "SELECT COUNT(*) FROM merge_actions WHERE app=? AND pr_number=? AND head_sha=? AND merged=1",
        (
            AUDIT_REVIVAL_FIXTURE.app,
            AUDIT_REVIVAL_FIXTURE.pr_number,
            AUDIT_REVIVAL_FIXTURE.merge_sha,
        ),
    )
    queued_count = _scalar(
        db,
        "SELECT COUNT(*) FROM deploy_queue WHERE app=? AND merged_pr_number=? AND sha=?",
        (
            AUDIT_REVIVAL_FIXTURE.app,
            AUDIT_REVIVAL_FIXTURE.pr_number,
            AUDIT_REVIVAL_FIXTURE.merge_sha,
        ),
    )

    assert merged_count == 1
    assert queued_count == 1


def test_seed_fixture_is_rerunnable_and_idempotent(tmp_path: Path) -> None:
    db = _seeded_db(tmp_path)
    first = seed_recoverable_blocked_story_fixture(db)
    second = seed_recoverable_blocked_story_fixture(db)

    assert first.id == second.id

    story_count = _scalar(
        db,
        "SELECT COUNT(*) FROM stories WHERE app=? AND direction_id=? AND slug=? AND github_pr_number=?",
        (
            AUDIT_REVIVAL_FIXTURE.app,
            AUDIT_REVIVAL_FIXTURE.direction_id,
            AUDIT_REVIVAL_FIXTURE.slug,
            AUDIT_REVIVAL_FIXTURE.pr_number,
        ),
    )
    assert story_count == 1


def test_seed_fixture_supports_next_tick_execution(tmp_path: Path) -> None:
    """AC1.2: one orchestrator tick can execute against seeded fixture."""
    db = _seeded_db(tmp_path)
    seed_recoverable_blocked_story_fixture(db)
    _write_runtime_files(tmp_path)
    reload_settings(tmp_path)

    summary = tick(tmp_path, AUDIT_REVIVAL_FIXTURE.app, db_path=db)

    assert summary.errors == []
    assert summary.stories_advanced == 0


def test_before_after_evidence_is_capturable(tmp_path: Path) -> None:
    """AC1.3: fixture provides capturable before/after status evidence."""
    db = _seeded_db(tmp_path)
    seed_recoverable_blocked_story_fixture(db)
    _write_runtime_files(tmp_path)
    reload_settings(tmp_path)

    before = capture_revival_step_evidence(db)
    tick(tmp_path, AUDIT_REVIVAL_FIXTURE.app, db_path=db)
    after = capture_revival_step_evidence(db)

    assert before is not None
    assert after is not None
    assert before.story_state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert after.story_state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert before.pr_merged is True
    assert after.pr_merged is True
    assert before.story_id == after.story_id
