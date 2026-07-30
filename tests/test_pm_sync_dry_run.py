"""End-to-end pm_sync test in dry-run mode.

Exercises the real ``pm_sync`` function (no monkeypatching the entry point).
The only thing mocked is the LLM call (skipped via ``dry_run=True``) and the
GitHub client (None; pm_sync does not call it in dry-run).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from factory.chain.pm_sync import pm_sync
from factory.directions.creator import create_direction


def _seed_app_config(tmp_path: Path) -> None:
    apps_dir = tmp_path / "apps" / "sacrifice"
    apps_dir.mkdir(parents=True)
    (apps_dir / "config.yaml").write_text(
        "name: sacrifice\nrepo: xvanov/sacrifice\ndefault_branch: main\n"
        "context_dir: context\ndeploy:\n  enabled: false\nmodels: {}\n",
        encoding="utf-8",
    )


def test_pm_sync_dry_run_two_complete_one_vague(tmp_path: Path) -> None:
    _seed_app_config(tmp_path)

    # 001 — complete with API spec.
    create_direction(
        app="sacrifice",
        title="Add healthz endpoint",
        type_tag="feature",
        why="Smoke test wants a stable endpoint.",
        has_ui=False,
        flow_steps=None,
        has_api=True,
        api_spec_lines=['- `POST /healthz` -> 200 {"status":"ok"}'],
        acceptance=["Returns 200", "JSON body has status"],
        explore=False,
        attach_files=None,
        software_factory_root=tmp_path,
    )

    # 002 — complete with a UI flow.
    create_direction(
        app="sacrifice",
        title="Celebration screen",
        type_tag="feature",
        why="Users want a moment of joy after pledging.",
        has_ui=True,
        flow_steps=[
            "User completes pledge",
            "App displays celebration screen with confetti",
            "User dismisses; returns to dashboard",
        ],
        has_api=False,
        api_spec_lines=None,
        acceptance=["Confetti renders", "Screen dismisses on click"],
        explore=False,
        attach_files=None,
        software_factory_root=tmp_path,
    )

    # 003 — vague. No flow, no api_spec, no explore tag.
    create_direction(
        app="sacrifice",
        title="Vague thought",
        type_tag=None,
        why="I have a feeling.",
        has_ui=False,
        flow_steps=None,
        has_api=False,
        api_spec_lines=None,
        acceptance=[],
        explore=False,
        attach_files=None,
        software_factory_root=tmp_path,
    )

    state_db = tmp_path / "state" / "factory.db"
    summary = pm_sync(
        app="sacrifice",
        software_factory_root=tmp_path,
        dry_run=True,
        state_db_path=state_db,
    )

    assert summary.processed == 3
    assert summary.validated == 2
    assert summary.needs_direction == 1
    assert summary.errors == []

    # Dry-run is a PURE PREVIEW: the summary reflects exactly what the real
    # run would decide (2 validated, 1 needs-direction) but NOTHING on disk is
    # mutated. Every direction must remain exactly as created — no status flip,
    # no pm_result blob, no status-transition audit entry. Regression guard for
    # the 2026-07-20 self-tick incident, where a dry-run that mutated state let
    # a "safe" preview spawn live dispatchable rebuild-stories.
    directions_dir = tmp_path / "apps" / "sacrifice" / "directions"
    for entry in sorted(directions_dir.iterdir()):
        if not entry.is_dir():
            continue
        state = yaml.safe_load((entry / "state.yaml").read_text(encoding="utf-8"))
        assert state["status"] == "created", f"{entry.name} status mutated by dry-run"
        assert "pm_result" not in state, f"{entry.name} got a pm_result in dry-run"
        assert not any(
            e.get("event", "").startswith("status -> ") for e in state.get("audit", [])
        ), f"{entry.name} recorded a status transition in dry-run"

    # And no StoryRecord rows leaked into the DB from the preview.
    import sqlite3

    conn = sqlite3.connect(str(state_db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    finally:
        conn.close()
    assert n == 0, f"dry-run persisted {n} dispatchable stories — must be a pure preview"


def test_pm_sync_gc_pass_closes_stale_scheduled_direction(tmp_path: Path) -> None:
    """pm_sync's end-of-pass GC (factory.directions.gc) closes a scheduler-filed
    direction that's been stuck at needs-direction well past the threshold —
    the fix for audit 2026-07-18 leak 2 of 4 (directions filed by scheduler
    personas that never got operator follow-up rotted at needs-direction
    forever)."""
    from datetime import UTC, datetime, timedelta

    from factory.directions.gc import GC_BY, MAX_AGE_DAYS

    _seed_app_config(tmp_path)
    created = create_direction(
        app="sacrifice",
        title="rate-limit pledge endpoint",
        type_tag="security",
        why="pledge flooding",
        has_ui=False,
        flow_steps=None,
        has_api=False,
        api_spec_lines=None,
        acceptance=["429 after 5/min"],
        explore=True,
        attach_files=None,
        software_factory_root=tmp_path,
        source="scheduled-security",
    )
    state_path = created.dir_path / "state.yaml"
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    old = (datetime.now(UTC) - timedelta(days=MAX_AGE_DAYS + 1)).isoformat()
    state["created_at"] = old
    state["status"] = "needs-direction"
    state["audit"] = [{"event": "status -> needs-direction"}]
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    summary = pm_sync(
        app="sacrifice",
        software_factory_root=tmp_path,
        dry_run=True,
        state_db_path=tmp_path / "state" / "factory.db",
        # Narrow to "created" so this stale needs-direction entry is not
        # re-validated by the normal pm loop — only the GC pass should
        # touch it, mirroring the automated (maybe_auto_pm_sync) caller.
        pending_statuses=frozenset({"created"}),
    )

    # Dry-run PREVIEWS which directions would be GC-closed (via the returned
    # gc_closed list) but must not mutate state.yaml on disk.
    assert summary.gc_closed == [created.direction.id]
    final_state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    assert final_state["status"] == "needs-direction", "dry-run must not close on disk"
    assert not any(e.get("by") == GC_BY for e in final_state.get("audit", []))


def test_pm_sync_gc_pass_leaves_fresh_directions_alone(tmp_path: Path) -> None:
    """A freshly-filed scheduled direction (or one from the main test fixture)
    must not be touched by the GC pass."""
    _seed_app_config(tmp_path)
    create_direction(
        app="sacrifice",
        title="fresh scheduled finding",
        type_tag="security",
        why="just filed",
        has_ui=False,
        flow_steps=None,
        has_api=False,
        api_spec_lines=None,
        acceptance=["fixed"],
        explore=True,
        attach_files=None,
        software_factory_root=tmp_path,
        source="scheduled-bug_hunter",
    )
    summary = pm_sync(
        app="sacrifice",
        software_factory_root=tmp_path,
        dry_run=True,
        state_db_path=tmp_path / "state" / "factory.db",
    )
    assert summary.gc_closed == []


def test_pm_sync_dry_run_is_idempotent(tmp_path: Path) -> None:
    """Two consecutive dry-runs return the IDENTICAL summary, because a pure
    preview never consumes the direction it previews. Before the 2026-07-20
    fix the first dry-run flipped the direction to ``pm-validated`` and spawned
    dispatchable stories, so the second dry-run reported ``validated=0`` — a
    dry-run!=real-run divergence that made a "safe" preview into a live action.
    """
    _seed_app_config(tmp_path)
    create_direction(
        app="sacrifice",
        title="Add healthz endpoint",
        type_tag="feature",
        why="Smoke test wants a stable endpoint.",
        has_ui=False,
        flow_steps=None,
        has_api=True,
        api_spec_lines=['- `POST /healthz` -> 200 {"status":"ok"}'],
        acceptance=["Returns 200", "JSON body has status"],
        explore=False,
        attach_files=None,
        software_factory_root=tmp_path,
    )
    state_db = tmp_path / "state" / "factory.db"
    first = pm_sync(
        app="sacrifice", software_factory_root=tmp_path, dry_run=True, state_db_path=state_db
    )
    second = pm_sync(
        app="sacrifice", software_factory_root=tmp_path, dry_run=True, state_db_path=state_db
    )
    assert first.validated == second.validated == 1
    assert first.processed == second.processed == 1


def test_pm_sync_dry_run_no_directions_empty_summary(tmp_path: Path) -> None:
    _seed_app_config(tmp_path)
    # Need at least the directions directory to exist.
    (tmp_path / "apps" / "sacrifice" / "directions").mkdir(exist_ok=True)
    summary = pm_sync(
        app="sacrifice",
        software_factory_root=tmp_path,
        dry_run=True,
        state_db_path=tmp_path / "state" / "factory.db",
    )
    assert summary.processed == 0
    assert summary.validated == 0
    assert summary.needs_direction == 0


# ---------------------------------------------------------------------------
# D012 regression: deleted state.yaml does not cause re-triage
# ---------------------------------------------------------------------------


def test_deleted_state_yaml_survives_pm_sync_without_retriage(tmp_path: Path) -> None:
    """AC1.1 + AC1.2 + AC2.1 + AC2.2 — Integration regression test.

    Proves that a direction whose ``state.yaml`` is deleted keeps its status
    across a fresh read-path (factory restart simulation), ``pm_sync`` does
    NOT re-triage it, and ``state.yaml`` is regenerated from the database
    without status drift.
    """
    from sqlmodel import Session, SQLModel, create_engine

    from factory.directions.schema import get_direction, upsert_direction
    from factory.directions.watcher import mark_direction_status

    _seed_app_config(tmp_path)

    # -- create direction on disk (status = "created" in state.yaml) ---------
    created = create_direction(
        app="sacrifice",
        title="Add healthz endpoint",
        type_tag="feature",
        why="Smoke test wants a stable endpoint.",
        has_ui=False,
        flow_steps=None,
        has_api=True,
        api_spec_lines=['- `POST /healthz` -> 200 {"status":"ok"}'],
        acceptance=["Returns 200", "JSON body has status"],
        explore=False,
        attach_files=None,
        software_factory_root=tmp_path,
    )
    dir_id = created.direction.id
    state_yaml = created.dir_path / "state.yaml"
    assert state_yaml.exists()

    # -- insert authoritative DB row at a non-pending status ----------------
    state_db = tmp_path / "state" / "factory.db"
    state_db.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{state_db}", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        upsert_direction(
            session,
            app="sacrifice",
            direction_id=dir_id,
            slug=created.direction.slug,
            status="pm-validated",
        )

    # -- delete state.yaml (simulate operator action from flow step 5) ------
    state_yaml.unlink()
    assert not state_yaml.exists()

    # -- simulate factory restart: fresh engine to verify DB persistence ----
    fresh_engine = create_engine(f"sqlite:///{state_db}", echo=False)
    with Session(fresh_engine) as session:
        row = get_direction(session, "sacrifice", dir_id)
        assert row is not None
        assert row.status == "pm-validated", (
            "AC1.1: status must survive state.yaml deletion across fresh read-path"
        )

    # -- run pm-sync --------------------------------------------------------
    summary = pm_sync(
        app="sacrifice",
        software_factory_root=tmp_path,
        dry_run=True,
        state_db_path=state_db,
    )

    # AC1.2: direction is NOT re-triaged — pm_sync must not see it as pending
    assert summary.processed == 0, (
        "AC1.2: pm-sync processed a direction whose DB status is pm-validated — "
        "it should have been excluded from pending"
    )

    # AC1.1 again: DB status still unchanged after pm-sync
    with Session(fresh_engine) as session:
        row = get_direction(session, "sacrifice", dir_id)
        assert row is not None
        assert row.status == "pm-validated"

    # -- regenerate state.yaml from DB (AC2.1 + AC2.2) ----------------------
    # mark_direction_status is the authoritative write path that projects
    # state.yaml. Calling it with the same status regenerates the file.
    mark_direction_status(
        created.direction,
        "pm-validated",
        by="regression-test",
    )

    # AC2.1: state.yaml is written for human inspection
    assert state_yaml.exists(), (
        "AC2.1: state.yaml must be regenerated for human inspection"
    )

    # AC2.2: regenerated state.yaml carries the same status as the DB row
    regenerated = yaml.safe_load(state_yaml.read_text(encoding="utf-8"))
    assert regenerated["status"] == "pm-validated", (
        f"AC2.2: regenerated state.yaml status is {regenerated.get('status')!r}, "
        f"expected 'pm-validated'"
    )

    # Confirm DB still authoritative — no drift
    with Session(fresh_engine) as session:
        row = get_direction(session, "sacrifice", dir_id)
        assert row is not None
        assert row.status == "pm-validated"
