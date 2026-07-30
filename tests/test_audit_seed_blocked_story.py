"""Audit fixture: seeded blocked-story + merged-PR state for revival-step UX audit.

Provides a deterministic, re-runnable seeded fixture that encodes two facts
together: a story is currently blocked (``blocked_ci_unresolved``) AND its
associated PR is already merged. The fixture is loadable by any test or
integration path and exposes stable identifiers so the follow-up one-tick
revival story can target it.

Fixture identifiers (stable contract for downstream consumers):
    AUDIT_FIXTURE_DIRECTION_ID = "099"
    AUDIT_FIXTURE_SLUG = "audit-seed-blocked-ci"
    AUDIT_FIXTURE_PR_NUMBER = 142
    AUDIT_FIXTURE_APP = "sacrifice"
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from factory.chain.auto_merge import MergeActionRecord
from factory.chain.handlers import persist_story
from factory.chain.state_machine import StoryRecord, StoryState
from factory.deploy.models import DeployQueueEntry

# -- Stable fixture identifiers (contract for downstream audit consumers) --
AUDIT_FIXTURE_DIRECTION_ID = "099"
AUDIT_FIXTURE_SLUG = "audit-seed-blocked-ci"
AUDIT_FIXTURE_PR_NUMBER = 142
AUDIT_FIXTURE_APP = "sacrifice"
AUDIT_FIXTURE_MERGE_SHA = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"


def _seed_db(tmp_path: Path) -> Path:
    """Create an empty factory.db with all tables under ``tmp_path``."""
    db = tmp_path / "state" / "factory.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db}", echo=False))
    return db


def _seed_blocked_story_with_merged_pr(db: Path) -> StoryRecord:
    """Seed a blocked-ci story + merged-PR records into ``db``.

    Returns the persisted ``StoryRecord`` with stable identifiers so callers
    can assert on its shape and consumers can target it for one-tick execution.
    """
    story = persist_story(
        StoryRecord(
            direction_id=AUDIT_FIXTURE_DIRECTION_ID,
            app=AUDIT_FIXTURE_APP,
            title="Audit seed: blocked CI story with merged PR",
            slug=AUDIT_FIXTURE_SLUG,
            scope="backend",
            state=StoryState.BLOCKED_CI_UNRESOLVED.value,
            github_pr_number=AUDIT_FIXTURE_PR_NUMBER,
            dev_retries=3,
            reviewer_cycles=2,
            error="ci_fix_exhausted: identical_failure_signature",
        ),
        db,
    )

    eng = create_engine(f"sqlite:///{db}", echo=False)

    # Record the merge action — the PR was merged out-of-band by an operator.
    merge_rec = MergeActionRecord(
        app=AUDIT_FIXTURE_APP,
        pr_number=AUDIT_FIXTURE_PR_NUMBER,
        head_sha=AUDIT_FIXTURE_MERGE_SHA,
        merged=True,
        reason="operator_merged_out_of_band",
        gates_passed_json=json.dumps([]),
        blocking_labels_json=json.dumps([]),
    )
    with Session(eng) as session:
        session.add(merge_rec)
        session.commit()

    # Record the deploy queue entry from the merged PR.
    deploy_entry = DeployQueueEntry(
        app=AUDIT_FIXTURE_APP,
        sha=AUDIT_FIXTURE_MERGE_SHA,
        merged_pr_number=AUDIT_FIXTURE_PR_NUMBER,
    )
    with Session(eng) as session:
        session.add(deploy_entry)
        session.commit()

    return story


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_seeded_fixture_loads_blocked_story(tmp_path: Path) -> None:
    """AC1.1: Loading the seeded fixture provides a blocked story for the
    revival step scenario."""
    db = _seed_db(tmp_path)
    story = _seed_blocked_story_with_merged_pr(db)

    assert story.id is not None
    assert story.state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert story.github_pr_number == AUDIT_FIXTURE_PR_NUMBER
    assert story.direction_id == AUDIT_FIXTURE_DIRECTION_ID
    assert story.slug == AUDIT_FIXTURE_SLUG
    assert story.app == AUDIT_FIXTURE_APP


def test_seeded_fixture_has_merged_pr_record(tmp_path: Path) -> None:
    """The fixture encodes both facts: story is blocked AND PR is merged."""
    db = _seed_db(tmp_path)
    _seed_blocked_story_with_merged_pr(db)

    eng = create_engine(f"sqlite:///{db}", echo=False)
    with Session(eng) as session:
        merge_rows = session.exec(
            select(MergeActionRecord).where(
                MergeActionRecord.pr_number == AUDIT_FIXTURE_PR_NUMBER,
                MergeActionRecord.app == AUDIT_FIXTURE_APP,
            )
        ).all()

    assert len(merge_rows) >= 1
    assert any(r.merged for r in merge_rows)


def test_seeded_fixture_has_deploy_queue_entry(tmp_path: Path) -> None:
    """The merged PR is enqueued for deploy — the same outcome as the normal
    reconciled-merge path."""
    db = _seed_db(tmp_path)
    _seed_blocked_story_with_merged_pr(db)

    eng = create_engine(f"sqlite:///{db}", echo=False)
    with Session(eng) as session:
        deploy_rows = session.exec(
            select(DeployQueueEntry).where(
                DeployQueueEntry.merged_pr_number == AUDIT_FIXTURE_PR_NUMBER,
                DeployQueueEntry.app == AUDIT_FIXTURE_APP,
            )
        ).all()

    assert len(deploy_rows) >= 1
    assert deploy_rows[0].sha == AUDIT_FIXTURE_MERGE_SHA


def test_seeded_story_is_in_blocked_terminal_state(tmp_path: Path) -> None:
    """The seeded story is in a blocked state — the 'before' capture point
    for the revival step evidence."""
    db = _seed_db(tmp_path)
    story = _seed_blocked_story_with_merged_pr(db)

    assert story.state == StoryState.BLOCKED_CI_UNRESOLVED.value

    # Verify the state is recognized as a valid StoryState enum value.
    parsed = StoryState(story.state)
    assert parsed == StoryState.BLOCKED_CI_UNRESOLVED


def test_seeded_fixture_exposes_stable_identifiers(tmp_path: Path) -> None:
    """The fixture identifiers are stable and discoverable — downstream
    consumers (one-tick revival, audit runbook) can target them."""
    db = _seed_db(tmp_path)
    story = _seed_blocked_story_with_merged_pr(db)

    # These are the contract identifiers the follow-up story consumes.
    assert story.direction_id == AUDIT_FIXTURE_DIRECTION_ID
    assert story.slug == AUDIT_FIXTURE_SLUG
    assert story.github_pr_number == AUDIT_FIXTURE_PR_NUMBER
    assert story.app == AUDIT_FIXTURE_APP


def test_seeded_fixture_is_rerunnable(tmp_path: Path) -> None:
    """The fixture is deterministic: seeding twice produces two distinct
    stories with the same stable shape (idempotent identifiers)."""
    db = _seed_db(tmp_path)

    s1 = _seed_blocked_story_with_merged_pr(db)
    s2 = _seed_blocked_story_with_merged_pr(db)

    assert s1.id != s2.id  # distinct rows
    assert s1.slug == s2.slug == AUDIT_FIXTURE_SLUG
    assert s1.direction_id == s2.direction_id == AUDIT_FIXTURE_DIRECTION_ID
    assert s1.github_pr_number == s2.github_pr_number == AUDIT_FIXTURE_PR_NUMBER
    assert s1.state == s2.state == StoryState.BLOCKED_CI_UNRESOLVED.value


def test_tick_does_not_error_on_seeded_fixture(tmp_path: Path) -> None:
    """AC1.2: The fixture supports next-tick execution — a tick targeting the
    seeded story completes without error (the story is skipped because it's
    in a terminal state, but no crash / invalid-state / schema error)."""
    db = _seed_db(tmp_path)
    _seed_blocked_story_with_merged_pr(db)

    # Write minimal app config so the tick can resolve the app.
    apps = tmp_path / "apps" / AUDIT_FIXTURE_APP
    apps.mkdir(parents=True, exist_ok=True)
    import yaml

    (apps / "config.yaml").write_text(
        yaml.safe_dump({"name": AUDIT_FIXTURE_APP, "repo": "o/r"}), encoding="utf-8"
    )
    (tmp_path / "factory_settings.yaml").write_text(
        "modes:\n  default: normal\n  available: [normal, paused]\n"
        "auto_merge:\n  enabled: false\n"
        "ci_health:\n  enabled: false\n",
        encoding="utf-8",
    )
    from factory.settings.loader import reload_settings

    reload_settings(tmp_path)

    from factory.chain.orchestrator import tick

    summary = tick(tmp_path, AUDIT_FIXTURE_APP, db_path=db)

    # The seeded story is terminal (blocked_ci_unresolved) so it won't be
    # advanced, but the tick must not error.
    assert summary.stories_advanced == 0


def test_before_state_is_capturable(tmp_path: Path) -> None:
    """AC1.3: Before/after status evidence is capturable — the fixture's
    initial state can be observed and compared."""
    db = _seed_db(tmp_path)
    story = _seed_blocked_story_with_merged_pr(db)

    # Capture "before" evidence: the story state + PR merge status.
    before_state = story.state
    before_pr = story.github_pr_number

    eng = create_engine(f"sqlite:///{db}", echo=False)
    with Session(eng) as session:
        merge_record = session.exec(
            select(MergeActionRecord).where(
                MergeActionRecord.pr_number == AUDIT_FIXTURE_PR_NUMBER
            )
        ).first()

    assert before_state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert before_pr == AUDIT_FIXTURE_PR_NUMBER
    assert merge_record is not None and merge_record.merged is True

    # The "before" evidence is a plain dict — capturable by any audit tooling.
    before_evidence = {
        "story_slug": story.slug,
        "story_state": before_state,
        "pr_number": before_pr,
        "pr_merged": merge_record.merged if merge_record else False,
        "merge_sha": merge_record.head_sha if merge_record else None,
    }
    assert before_evidence["story_state"] == "blocked_ci_unresolved"
    assert before_evidence["pr_merged"] is True