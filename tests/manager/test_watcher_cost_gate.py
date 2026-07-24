"""Cover the two watcher fixes from the 2026-07-24 audit.

Bug A: the daemon called ``apply_manager_proposals`` without ``repo=``, so
``apply.py``'s ``if open_prs and repo and push:`` was permanently False and the
autonomous path could never open a PR (0 of 163 lifetime attempts set a
pr_number). ``_self_repo_slug`` resolves it.

L1 cost gate: the watcher fired unconditionally every 60s, producing 87% of all
run rows and 50% of lifetime spend at a 7.2% escalation rate.
``_streams_have_new_events`` ties the paid cycle to actual activity.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from factory.manager.watcher import _self_repo_slug, _streams_have_new_events

NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)


def _write_stream(root: Path, stream: str, tss: list[str]) -> None:
    d = root / "state" / "events"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stream}.ndjson").write_text(
        "\n".join(json.dumps({"ts": t, "event": "x"}) for t in tss) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# _self_repo_slug
# --------------------------------------------------------------------------- #


def test_self_repo_slug_reads_factory_app_config(tmp_path: Path) -> None:
    cfg = tmp_path / "apps" / "factory"
    cfg.mkdir(parents=True)
    (cfg / "config.yaml").write_text(
        "name: factory\nrepo: owner/software-factory\napp_repo_path: .\n", encoding="utf-8"
    )
    assert _self_repo_slug(tmp_path) == "owner/software-factory"


def test_self_repo_slug_returns_none_when_config_missing(tmp_path: Path) -> None:
    """Must degrade to the old no-PR behaviour, never raise — a config problem
    must not take down the L1 daemon."""
    assert _self_repo_slug(tmp_path) is None


def test_self_repo_slug_returns_none_on_corrupt_config(tmp_path: Path) -> None:
    cfg = tmp_path / "apps" / "factory"
    cfg.mkdir(parents=True)
    (cfg / "config.yaml").write_text("{[not yaml", encoding="utf-8")
    assert _self_repo_slug(tmp_path) is None


# --------------------------------------------------------------------------- #
# _streams_have_new_events
# --------------------------------------------------------------------------- #


def test_no_prior_note_always_observes(tmp_path: Path) -> None:
    assert _streams_have_new_events(tmp_path, None) is True


def test_idle_factory_is_gated(tmp_path: Path) -> None:
    """Nothing newer than the last note → skip the paid cycle."""
    _write_stream(tmp_path, "ticks", ["2026-07-24T10:00:00+00:00"])
    assert _streams_have_new_events(tmp_path, NOW) is False


def test_new_event_reopens_the_gate(tmp_path: Path) -> None:
    _write_stream(tmp_path, "ticks", ["2026-07-24T11:00:00+00:00"])
    since = datetime(2026, 7, 24, 10, 0, 0, tzinfo=UTC)
    assert _streams_have_new_events(tmp_path, since) is True


def test_gate_checks_every_raw_stream_not_just_the_first(tmp_path: Path) -> None:
    """Activity in any one stream must reopen the gate — a busy 'spend' stream
    with a quiet 'runs' stream still means something happened."""
    _write_stream(tmp_path, "runs", ["2026-07-24T09:00:00+00:00"])
    _write_stream(tmp_path, "spend", ["2026-07-24T11:30:00+00:00"])
    since = datetime(2026, 7, 24, 10, 0, 0, tzinfo=UTC)
    assert _streams_have_new_events(tmp_path, since) is True


def test_missing_streams_are_not_activity(tmp_path: Path) -> None:
    (tmp_path / "state" / "events").mkdir(parents=True)
    assert _streams_have_new_events(tmp_path, NOW) is False


def test_gate_fails_open_on_read_error(tmp_path: Path, monkeypatch) -> None:
    """Silently not watching is worse than one redundant paid cycle."""
    _write_stream(tmp_path, "ticks", ["2026-07-24T11:00:00+00:00"])

    def _boom(*_a: object, **_k: object) -> list[dict]:
        raise OSError("disk gone")

    monkeypatch.setattr("factory.manager.watcher._read_stream_since", _boom)
    since = datetime(2026, 7, 24, 10, 0, 0, tzinfo=UTC)
    assert _streams_have_new_events(tmp_path, since) is True


def test_gate_tolerates_a_future_dated_note(tmp_path: Path) -> None:
    """A clock skew that puts the last note ahead of every event must gate
    (not crash) — the next real event still reopens it."""
    _write_stream(tmp_path, "ticks", ["2026-07-24T11:00:00+00:00"])
    assert _streams_have_new_events(tmp_path, NOW + timedelta(days=1)) is False
