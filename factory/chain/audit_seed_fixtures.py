"""Deterministic audit seed fixtures for blocked-story revival scenarios."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlmodel import Session, create_engine, select

from factory.chain.auto_merge import MergeActionRecord
from factory.chain.handlers import persist_story
from factory.chain.state_machine import StoryRecord, StoryState
from factory.deploy.models import DeployQueueEntry
from factory.observability.schema import migrate


@dataclass(frozen=True)
class AuditRevivalFixture:
    fixture_id: str
    direction_id: str
    slug: str
    app: str
    pr_number: int
    merge_sha: str


@dataclass(frozen=True)
class RevivalStepEvidence:
    fixture_id: str
    story_id: int | None
    story_state: str
    pr_number: int
    pr_merged: bool
    merge_sha: str | None


AUDIT_REVIVAL_FIXTURE = AuditRevivalFixture(
    fixture_id="ux-audit-revival-blocked-story-v1",
    direction_id="099",
    slug="audit-seed-blocked-ci",
    app="sacrifice",
    pr_number=142,
    merge_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
)


def _engine(db_path: Path) -> Any:
    migrate(db_path)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def _get_seed_story(db_path: Path) -> StoryRecord | None:
    eng = _engine(db_path)
    with Session(eng) as session:
        return session.exec(
            select(StoryRecord)
            .where(
                StoryRecord.app == AUDIT_REVIVAL_FIXTURE.app,
                StoryRecord.direction_id == AUDIT_REVIVAL_FIXTURE.direction_id,
                StoryRecord.slug == AUDIT_REVIVAL_FIXTURE.slug,
                StoryRecord.github_pr_number == AUDIT_REVIVAL_FIXTURE.pr_number,
            )
            .order_by(StoryRecord.id)
        ).first()


def seed_recoverable_blocked_story_fixture(db_path: Path) -> StoryRecord:
    """Seed or normalize the blocked-story + merged-PR audit fixture.

    The fixture is deterministic and idempotent: repeated calls keep one stable
    story row for the fixture identity and ensure the linked merge/deploy
    context rows exist for the same PR/sha pair.
    """
    story = _get_seed_story(db_path)
    if story is None:
        story = StoryRecord(
            direction_id=AUDIT_REVIVAL_FIXTURE.direction_id,
            app=AUDIT_REVIVAL_FIXTURE.app,
            title="Audit seed: blocked CI story with merged PR",
            slug=AUDIT_REVIVAL_FIXTURE.slug,
            scope="backend",
            state=StoryState.BLOCKED_CI_UNRESOLVED.value,
            github_pr_number=AUDIT_REVIVAL_FIXTURE.pr_number,
            dev_retries=3,
            reviewer_cycles=2,
            error="ci_fix_exhausted: identical_failure_signature",
        )
    else:
        story.state = StoryState.BLOCKED_CI_UNRESOLVED.value
        story.github_pr_number = AUDIT_REVIVAL_FIXTURE.pr_number
        story.error = "ci_fix_exhausted: identical_failure_signature"

    story = persist_story(story, db_path)

    eng = _engine(db_path)
    with Session(eng) as session:
        merge_row = session.exec(
            select(MergeActionRecord)
            .where(
                MergeActionRecord.app == AUDIT_REVIVAL_FIXTURE.app,
                MergeActionRecord.pr_number == AUDIT_REVIVAL_FIXTURE.pr_number,
                MergeActionRecord.head_sha == AUDIT_REVIVAL_FIXTURE.merge_sha,
            )
            .order_by(MergeActionRecord.id)
        ).first()
        if merge_row is None:
            merge_row = MergeActionRecord(
                app=AUDIT_REVIVAL_FIXTURE.app,
                pr_number=AUDIT_REVIVAL_FIXTURE.pr_number,
                head_sha=AUDIT_REVIVAL_FIXTURE.merge_sha,
                merged=True,
                reason="operator_merged_out_of_band",
                gates_passed_json=json.dumps([]),
                blocking_labels_json=json.dumps([]),
            )
        else:
            merge_row.merged = True
            merge_row.reason = "operator_merged_out_of_band"
        session.add(merge_row)

        deploy_row = session.exec(
            select(DeployQueueEntry)
            .where(
                DeployQueueEntry.app == AUDIT_REVIVAL_FIXTURE.app,
                DeployQueueEntry.merged_pr_number == AUDIT_REVIVAL_FIXTURE.pr_number,
                DeployQueueEntry.sha == AUDIT_REVIVAL_FIXTURE.merge_sha,
            )
            .order_by(DeployQueueEntry.id)
        ).first()
        if deploy_row is None:
            deploy_row = DeployQueueEntry(
                app=AUDIT_REVIVAL_FIXTURE.app,
                sha=AUDIT_REVIVAL_FIXTURE.merge_sha,
                merged_pr_number=AUDIT_REVIVAL_FIXTURE.pr_number,
            )
            session.add(deploy_row)

        session.commit()

    return story


def capture_revival_step_evidence(db_path: Path) -> RevivalStepEvidence | None:
    """Return capturable status evidence for the revival fixture."""
    story = _get_seed_story(db_path)
    if story is None:
        return None

    eng = _engine(db_path)
    with Session(eng) as session:
        merge_row = session.exec(
            select(MergeActionRecord)
            .where(
                MergeActionRecord.app == AUDIT_REVIVAL_FIXTURE.app,
                MergeActionRecord.pr_number == AUDIT_REVIVAL_FIXTURE.pr_number,
            )
            .order_by(MergeActionRecord.id.desc())
        ).first()

    return RevivalStepEvidence(
        fixture_id=AUDIT_REVIVAL_FIXTURE.fixture_id,
        story_id=story.id,
        story_state=story.state,
        pr_number=AUDIT_REVIVAL_FIXTURE.pr_number,
        pr_merged=bool(merge_row and merge_row.merged),
        merge_sha=merge_row.head_sha if merge_row else None,
    )


__all__ = [
    "AUDIT_REVIVAL_FIXTURE",
    "AuditRevivalFixture",
    "RevivalStepEvidence",
    "capture_revival_step_evidence",
    "seed_recoverable_blocked_story_fixture",
]
