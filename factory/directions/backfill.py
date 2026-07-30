"""Reconciliation between on-disk direction directories and the ``directions`` table.

Two commands, one per data direction:

* ``factory directions-backfill --app <app> [--dry-run]`` — disk → DB. Imports an
  on-disk direction that has no row yet, so a direction hand-written between
  clones is not lost. Dry-run is the DEFAULT: it writes the authoritative table.
* ``factory directions-regenerate-state --app <app> [--dry-run]`` — DB → disk.
  Rewrites a MISSING ``state.yaml`` projection from its row. ``state.yaml`` is
  gitignored (direction 018), so a fresh clone has none; this rebuilds them.
  Writing is the DEFAULT here: the output is a gitignored, never-overwritten
  projection, so there is nothing to lose.

Both are idempotent — safe to run twice.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlmodel import Session

from factory.directions.parser import list_direction_dirs, parse_direction_dir
from factory.directions.schema import DirectionRecord


@dataclass
class BackfillResult:
    imported: int
    skipped: int


@dataclass
class RegenerateResult:
    """Outcome of a ``state.yaml`` regeneration pass.

    written: projections written (or, in dry-run, that would be written).
    present: direction dirs that already have a ``state.yaml`` — left untouched.
    no_row: direction dirs with no ``directions`` row to project from. Run
        ``factory directions-backfill --real-run`` to import those first.
    """

    written: int
    present: int
    no_row: int


def _resolve_tracker_issue(state: dict[str, Any]) -> int | None:
    raw = state.get("tracker_issue")
    if isinstance(raw, int) and raw > 0:
        return raw
    return None


def _resolve_updated_by(state: dict[str, Any]) -> str | None:
    audit = state.get("audit")
    if isinstance(audit, list) and audit:
        for entry in reversed(audit):
            if not isinstance(entry, dict):
                continue
            by = entry.get("by")
            if isinstance(by, str) and by.strip():
                return by.strip()
            break
    return None


def _parse_timestamp(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_created_at(state: dict[str, Any]) -> datetime:
    created = _parse_timestamp(state.get("created_at"))
    if created is not None:
        return created
    return datetime.now(UTC)


def _resolve_updated_at(state: dict[str, Any], *, fallback: datetime) -> datetime:
    audit = state.get("audit")
    if isinstance(audit, list) and audit:
        for entry in reversed(audit):
            if not isinstance(entry, dict):
                continue
            ts = _parse_timestamp(entry.get("ts"))
            if ts is not None:
                return ts
            break
    return fallback


def _existing_direction_ids(session: Session, app: str) -> set[str]:
    from sqlmodel import select

    rows = session.exec(
        select(DirectionRecord.direction_id).where(DirectionRecord.app == app)
    ).all()
    return {str(direction_id) for direction_id in rows if direction_id is not None}


def _existing_direction_ids_read_only(db_path: Path, app: str) -> set[str]:
    if not db_path.exists():
        return set()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='directions'"
        ).fetchone()
        if table is None:
            return set()
        rows = conn.execute(
            "SELECT direction_id FROM directions WHERE app = ?",
            (app,),
        ).fetchall()
        return {str(row[0]) for row in rows if row and row[0] is not None}
    finally:
        conn.close()


def directions_backfill(
    app: str,
    software_factory_root: Path,
    state_db_path: Path,
    *,
    dry_run: bool = True,
) -> BackfillResult:
    """Import on-disk directions that have no row yet into the ``directions`` table.

    Args:
        app: App name (e.g. ``"factory"``).
        software_factory_root: Repository root.
        state_db_path: Path to the SQLite database file.
        dry_run: If True, report what would happen without writing.

    Returns:
        ``BackfillResult`` with counts of imported and skipped rows.
    """
    from sqlmodel import SQLModel, create_engine

    db_path = Path(state_db_path)
    directions = [
        parse_direction_dir(app, dir_path, software_factory_root=software_factory_root)
        for dir_path in list_direction_dirs(app, software_factory_root)
    ]

    if dry_run:
        existing_ids = _existing_direction_ids_read_only(db_path, app)
        imported = sum(1 for direction in directions if direction.id not in existing_ids)
        skipped = len(directions) - imported
        return BackfillResult(imported=imported, skipped=skipped)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)

    imported = 0
    skipped = 0
    with Session(engine) as session:
        existing_ids = _existing_direction_ids(session, app)

        for direction in directions:
            if direction.id in existing_ids:
                skipped += 1
                continue

            tracker_issue = _resolve_tracker_issue(direction.state)
            updated_by = _resolve_updated_by(direction.state)
            created_at = _resolve_created_at(direction.state)
            updated_at = _resolve_updated_at(direction.state, fallback=created_at)

            session.add(
                DirectionRecord(
                    app=app,
                    direction_id=direction.id,
                    slug=direction.slug,
                    status=direction.status,
                    tracker_issue=tracker_issue,
                    created_at=created_at,
                    updated_at=updated_at,
                    updated_by=updated_by,
                )
            )
            imported += 1
            existing_ids.add(direction.id)

        session.commit()

    return BackfillResult(imported=imported, skipped=skipped)


def _projection_from_row(row: DirectionRecord) -> dict[str, Any]:
    """Render the ``state.yaml`` projection of a ``directions`` row.

    Only what the row actually holds. The richer keys a live transition
    accumulates (``pm_result``, the full ``audit`` history, ``source``) are not
    in the table and are NOT invented here — ``regenerated_from: database``
    tells the operator reading the file that this is the reduced projection.
    """
    state: dict[str, Any] = {
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "regenerated_from": "database",
        "audit": [
            {
                "ts": row.updated_at.isoformat(),
                "by": row.updated_by or "factory.directions.backfill",
                "event": f"status -> {row.status}",
                "details": {"regenerated": True},
            }
        ],
    }
    if row.tracker_issue is not None:
        state["tracker_issue"] = row.tracker_issue
    return state


def regenerate_state_files(
    app: str,
    software_factory_root: Path,
    state_db_path: Path,
    *,
    dry_run: bool = False,
) -> RegenerateResult:
    """Write a ``state.yaml`` projection for every direction that is missing one.

    ``state.yaml`` is a gitignored projection of the authoritative ``directions``
    row (direction 018), so a fresh clone has direction.md but no state.yaml.
    This rebuilds them.

    An EXISTING ``state.yaml`` is never overwritten. That is deliberate on two
    counts: the on-disk file carries strictly more than the row (``pm_result``,
    the real audit trail), and it makes the command a no-op on a tree that
    already has its projections — so running it produces no diff.

    Args:
        app: App name (e.g. ``"factory"``).
        software_factory_root: Repository root.
        state_db_path: Path to the SQLite database file.
        dry_run: If True, report what would be written without touching disk.

    Returns:
        ``RegenerateResult`` with per-direction outcome counts.
    """
    from sqlmodel import SQLModel, create_engine

    from factory.directions.schema import get_direction

    db_path = Path(state_db_path)
    dir_paths = list_direction_dirs(app, software_factory_root)

    written = 0
    present = 0
    no_row = 0

    if not db_path.exists():
        # No database at all: nothing to project from. Every direction dir that
        # lacks a state.yaml is reported as ``no_row`` rather than silently
        # counted as done.
        for dir_path in dir_paths:
            if (dir_path / "state.yaml").exists():
                present += 1
            else:
                no_row += 1
        return RegenerateResult(written=written, present=present, no_row=no_row)

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for dir_path in dir_paths:
            state_path = dir_path / "state.yaml"
            if state_path.exists():
                present += 1
                continue

            direction = parse_direction_dir(
                app, dir_path, software_factory_root=software_factory_root
            )
            row = get_direction(session, app, direction.id)
            if row is None:
                no_row += 1
                continue

            written += 1
            if dry_run:
                continue
            state_path.write_text(
                yaml.safe_dump(_projection_from_row(row), sort_keys=False),
                encoding="utf-8",
            )

    return RegenerateResult(written=written, present=present, no_row=no_row)
