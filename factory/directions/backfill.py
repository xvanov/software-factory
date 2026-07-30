"""One-time backfill: import on-disk directions into the ``directions`` table.

Operator command: ``factory directions-backfill --app <app> [--dry-run]``

Dry-run is the default. The backfill is idempotent — safe to run twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

from factory.directions.parser import list_direction_dirs, parse_direction_dir
from factory.directions.schema import DirectionRecord, get_direction


@dataclass
class BackfillResult:
    imported: int
    skipped: int


def _resolve_tracker_issue(state: dict) -> int | None:
    raw = state.get("tracker_issue")
    if isinstance(raw, int) and raw > 0:
        return raw
    return None


def _resolve_updated_by(state: dict) -> str | None:
    audit = state.get("audit")
    if isinstance(audit, list) and audit:
        last = audit[-1]
        if isinstance(last, dict):
            by = last.get("by")
            if isinstance(by, str) and by.strip():
                return by.strip()
    return None


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
    from sqlmodel import create_engine

    db_path = Path(state_db_path)
    imported = 0
    skipped = 0

    if dry_run:
        # No database access at all
        for dir_path in list_direction_dirs(app, software_factory_root):
            imported += 1
        return BackfillResult(imported=imported, skipped=skipped)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    # Ensure tables exist (idempotent)
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for dir_path in list_direction_dirs(app, software_factory_root):
            d = parse_direction_dir(app, dir_path, software_factory_root=software_factory_root)

            existing = get_direction(session, app, d.id)
            if existing is not None:
                skipped += 1
                continue

            tracker_issue = _resolve_tracker_issue(d.state)
            updated_by = _resolve_updated_by(d.state)

            row = DirectionRecord(
                app=app,
                direction_id=d.id,
                slug=d.slug,
                status=d.status,
                tracker_issue=tracker_issue,
                updated_by=updated_by,
            )
            session.add(row)
            imported += 1

        session.commit()

    return BackfillResult(imported=imported, skipped=skipped)