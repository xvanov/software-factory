"""Deterministic seeded fixtures for UX audit evidence capture.

Provides a stable, importable fixture path so the UX audit can load a seeded
blocked story, advance exactly one tick, and capture before/after status
evidence for the revival step (D013 step 5: ``blocked_ci_unresolved`` →
``deploy_pending``).

No browser, no deploy, no real GitHub calls — the ``query_pr_state`` injection
seam keeps the fixture deterministic and CI-safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from factory.app_config import AppConfig
from factory.chain.handlers import persist_story
from factory.chain.orchestrator import reconcile_from_github
from factory.chain.state_machine import StoryRecord, StoryState

# Stable app config for the seeded fixture (no network calls).
FIXTURE_APP_CONFIG = AppConfig(name="sacrifice", repo="acme/sacrifice")

# Canonical slug for the seeded blocked story so downstream docs/tests can
# reference it by name.
FIXTURE_BLOCKED_STORY_SLUG = "audit-fixture-blocked-ci"
FIXTURE_PR_NUMBER = 999


@dataclass
class AuditEvidence:
    """Before/after snapshot of a single story's observable state."""
    slug: str
    state_before: str
    state_after: str
    pr_number: int | None
    error_before: str | None
    error_after: str | None
    transition_occurred: bool


def seed_blocked_story_db(db_path: Path) -> StoryRecord:
    """Create a fresh DB and seed it with one ``blocked_ci_unresolved`` story.

    The story carries a positive ``github_pr_number`` so
    ``reconcile_from_github`` considers it a candidate for revival.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(create_engine(f"sqlite:///{db_path}", echo=False))

    return persist_story(
        StoryRecord(
            direction_id="099",
            app="sacrifice",
            title="Seeded blocked story for UX audit revival step",
            slug=FIXTURE_BLOCKED_STORY_SLUG,
            scope="backend",
            state=StoryState.BLOCKED_CI_UNRESOLVED.value,
            github_pr_number=FIXTURE_PR_NUMBER,
            github_branch=f"factory/{FIXTURE_BLOCKED_STORY_SLUG}",
            error="dev exhausted retries (6): identical CI failure",
        ),
        db_path,
    )


def capture_story_evidence(db_path: Path, slug: str) -> dict[str, Any]:
    """Return observable status fields for a story by slug."""
    with Session(create_engine(f"sqlite:///{db_path}")) as ses:
        story = ses.exec(select(StoryRecord).where(StoryRecord.slug == slug)).one()
    return {
        "slug": story.slug,
        "state": story.state,
        "pr_number": story.github_pr_number,
        "error": story.error,
    }


def run_one_revival_tick(
    db_path: Path,
    *,
    app: str = "sacrifice",
    root: Path | None = None,
) -> list[tuple[str, str, str]]:
    """Execute exactly one reconciliation pass — the revival tick.

    Uses a ``query_pr_state`` stub that reports the seeded PR as MERGED so
    the ``blocked_ci_unresolved`` story advances to ``deploy_pending``
    without any real GitHub call.
    """
    if root is None:
        root = db_path.parent.parent

    return reconcile_from_github(
        db_path,
        app,
        cfg=FIXTURE_APP_CONFIG,
        root=root,
        query_pr_state=lambda *, app_config, pr_number: (
            "MERGED" if pr_number == FIXTURE_PR_NUMBER else "OPEN"
        ),
    )


def capture_before_after(
    db_path: Path,
    *,
    slug: str = FIXTURE_BLOCKED_STORY_SLUG,
    app: str = "sacrifice",
    root: Path | None = None,
) -> AuditEvidence:
    """Load fixture, capture before, tick once, capture after.

    Returns an ``AuditEvidence`` with the full before/after snapshot.
    """
    before = capture_story_evidence(db_path, slug)
    transitions = run_one_revival_tick(db_path, app=app, root=root)
    after = capture_story_evidence(db_path, slug)

    return AuditEvidence(
        slug=slug,
        state_before=before["state"],
        state_after=after["state"],
        pr_number=before["pr_number"],
        error_before=before["error"],
        error_after=after["error"],
        transition_occurred=len(transitions) > 0,
    )


__all__ = [
    "AuditEvidence",
    "FIXTURE_APP_CONFIG",
    "FIXTURE_BLOCKED_STORY_SLUG",
    "FIXTURE_PR_NUMBER",
    "capture_before_after",
    "capture_story_evidence",
    "run_one_revival_tick",
    "seed_blocked_story_db",
]