"""Integration/smoke test for the UX audit revival fixture (D016).

Covers: load seeded blocked-story fixture → capture before status → advance
one tick → capture after status → assert the revival transition occurred.

No browser, no deploy, no real GitHub calls.
"""

from __future__ import annotations

from pathlib import Path

from factory.chain.audit_fixtures import (
    FIXTURE_BLOCKED_STORY_SLUG,
    AuditEvidence,
    capture_before_after,
    capture_story_evidence,
    run_one_revival_tick,
    seed_blocked_story_db,
)
from factory.chain.state_machine import StoryState


def test_seed_produces_blocked_ci_unresolved_story(tmp_path: Path) -> None:
    """AC1.1: Loading the seeded fixture provides a blocked story."""
    db = tmp_path / "state" / "factory.db"
    seed_blocked_story_db(db)

    evidence = capture_story_evidence(db, FIXTURE_BLOCKED_STORY_SLUG)
    assert evidence["state"] == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert evidence["pr_number"] == 999
    assert "identical CI failure" in (evidence["error"] or "")


def test_one_tick_advances_blocked_to_deploy_pending(tmp_path: Path) -> None:
    """AC1.2: Advancing runtime by one tick executes the revival transition."""
    db = tmp_path / "state" / "factory.db"
    seed_blocked_story_db(db)

    transitions = run_one_revival_tick(db, root=tmp_path)

    assert len(transitions) == 1
    slug, from_state, to_state = transitions[0]
    assert slug == FIXTURE_BLOCKED_STORY_SLUG
    assert from_state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert to_state == StoryState.DEPLOY_PENDING.value


def test_before_after_evidence_is_capturable(tmp_path: Path) -> None:
    """AC1.3: Before/after status evidence is capturable for the revival step."""
    db = tmp_path / "state" / "factory.db"
    seed_blocked_story_db(db)

    evidence = capture_before_after(db, root=tmp_path)

    assert isinstance(evidence, AuditEvidence)
    assert evidence.slug == FIXTURE_BLOCKED_STORY_SLUG
    assert evidence.state_before == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert evidence.state_after == StoryState.DEPLOY_PENDING.value
    assert evidence.transition_occurred is True
    # The error that caused the block is preserved in the before snapshot.
    assert "identical CI failure" in (evidence.error_before or "")
    # The error is preserved across revival (the story carries its history).
    assert "identical CI failure" in (evidence.error_after or "")


def test_full_load_tick_evidence_path(tmp_path: Path) -> None:
    """End-to-end: load fixture → capture before → tick once → capture after."""
    db = tmp_path / "state" / "factory.db"

    # Load the seeded fixture
    seed_blocked_story_db(db)

    # Capture pre-tick observable story status
    before = capture_story_evidence(db, FIXTURE_BLOCKED_STORY_SLUG)
    assert before["state"] == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert before["pr_number"] == 999

    # Advance exactly one tick
    transitions = run_one_revival_tick(db, root=tmp_path)
    assert len(transitions) == 1

    # Capture post-tick observable story status
    after = capture_story_evidence(db, FIXTURE_BLOCKED_STORY_SLUG)
    assert after["state"] == StoryState.DEPLOY_PENDING.value

    # The story transitioned — the revival step occurred.
    assert before["state"] != after["state"]


def test_fixture_is_deterministic(tmp_path: Path) -> None:
    """The seeded fixture produces identical state on every load."""
    db1 = tmp_path / "a" / "state" / "factory.db"
    db2 = tmp_path / "b" / "state" / "factory.db"

    s1 = seed_blocked_story_db(db1)
    s2 = seed_blocked_story_db(db2)

    # Same slug, same state, same PR number.
    assert s1.slug == s2.slug == FIXTURE_BLOCKED_STORY_SLUG
    assert s1.state == s2.state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert s1.github_pr_number == s2.github_pr_number == 999


def test_fixture_executes_without_browser_or_deploy_dependencies(tmp_path: Path) -> None:
    """The fixture path requires no browser, no deploy URL, no network."""
    db = tmp_path / "state" / "factory.db"
    seed_blocked_story_db(db)

    # Runs without any external dependency — pure DB + in-process stub.
    transitions = run_one_revival_tick(db, root=tmp_path)
    assert len(transitions) == 1
    assert transitions[0][2] == StoryState.DEPLOY_PENDING.value