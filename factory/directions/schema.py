"""``directions`` table schema and persistence primitives.

Storage contract for direction rows — the foundation that later stories
(read-path, write-path, backfill CLI, ancestor-story context) consume.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel, select as _select


class DirectionRecord(SQLModel, table=True):
    """One row per direction, keyed by app + direction_id.

    Surrogate ``id`` primary key; unique on ``(app, direction_id)``.
    Hot-read index on ``(app, status)`` for "pending directions for this app".
    """

    __tablename__ = "directions"

    id: int | None = Field(default=None, primary_key=True)
    app: str = Field(nullable=False)
    direction_id: str = Field(nullable=False)
    slug: str = Field(nullable=False)
    status: str = Field(nullable=False)
    tracker_issue: int | None = Field(default=None, nullable=True)
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        nullable=False,
    )
    updated_by: str | None = Field(default=None, nullable=True)

    __table_args__ = (
        UniqueConstraint("app", "direction_id", name="uq_directions_app_direction_id"),
        Index("ix_directions_app_status", "app", "status"),
    )


# ---------------------------------------------------------------------------
# Persistence skeleton — primitives consumed by later stories
# ---------------------------------------------------------------------------


def get_direction(
    session, app: str, direction_id: str
) -> DirectionRecord | None:
    """Return the direction row for *app* + *direction_id*, or *None*."""
    return session.exec(
        _select(DirectionRecord).where(
            DirectionRecord.app == app,
            DirectionRecord.direction_id == direction_id,
        )
    ).first()


def upsert_direction(
    session,
    app: str,
    direction_id: str,
    slug: str,
    status: str,
    tracker_issue: int | None = None,
    updated_by: str | None = None,
) -> DirectionRecord:
    """Insert-or-update a direction row, returning the row.

    If a row for *(app, direction_id)* already exists its fields are
    overwritten; otherwise a new row is created.
    """
    existing = get_direction(session, app, direction_id)
    now = datetime.now(UTC).isoformat()

    if existing is not None:
        existing.slug = slug
        existing.status = status
        existing.tracker_issue = tracker_issue
        existing.updated_at = now
        existing.updated_by = updated_by
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = DirectionRecord(
        app=app,
        direction_id=direction_id,
        slug=slug,
        status=status,
        tracker_issue=tracker_issue,
        created_at=now,
        updated_at=now,
        updated_by=updated_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_directions(
    session,
    app: str,
    status: str | None = None,
) -> list[DirectionRecord]:
    """Return direction rows for *app*, optionally filtered by *status*."""
    stmt = _select(DirectionRecord).where(DirectionRecord.app == app)
    if status is not None:
        stmt = stmt.where(DirectionRecord.status == status)
    return list(session.exec(stmt).all())