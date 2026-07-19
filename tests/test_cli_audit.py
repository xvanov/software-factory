"""Tests for the ``factory audit`` CLI command (D003)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlmodel import Session
from typer.testing import CliRunner

from factory.runner import Run, _engine


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    apps = tmp_path / "apps" / "sacrifice"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / "config.yaml").write_text("name: sacrifice\nrepo: x/y\n", encoding="utf-8")
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    db = tmp_path / "state" / "factory.db"
    eng = _engine(db)
    now = datetime.now(UTC).isoformat()
    with Session(eng) as session:
        session.add(
            Run(
                ts=now,
                persona="dev",
                model="azure/deepseek-v4-pro",
                mode="sandbox",
                tokens_in=1000,
                tokens_out=200,
                cost_usd=0.15,
                duration_s=42.0,
                success=True,
                story_id=9,
                direction_id="d-9",
                app="sacrifice",
            )
        )
        session.add(
            Run(
                ts=now,
                persona="dev",
                model="azure/deepseek-v4-pro",
                mode="sandbox",
                tokens_in=500,
                tokens_out=100,
                cost_usd=0.05,
                duration_s=10.0,
                success=False,
                story_id=None,
                direction_id=None,
                app=None,
            )
        )
        session.commit()
    return tmp_path


def _runner_with_root(root: Path) -> tuple[CliRunner, object]:
    import importlib

    import factory.cli as cli_mod

    importlib.reload(cli_mod)
    cli_mod._FACTORY_ROOT = root  # type: ignore[attr-defined]
    return CliRunner(), cli_mod


def test_audit_shows_rollups_and_unattributed(seeded_root: Path) -> None:
    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["audit"])
    assert result.exit_code == 0, result.stdout
    assert "total_cost_usd=$0.2000" in result.stdout
    assert "by story" in result.stdout
    assert "by direction" in result.stdout
    assert "by app" in result.stdout
    assert "9" in result.stdout  # story_id row
    assert "d-9" in result.stdout  # direction_id row
    assert "sacrifice" in result.stdout
    # The unattributed dev run (NULL story_id) is surfaced.
    assert "unattributed" in result.stdout
    assert "runs=1" in result.stdout
    assert "cost_usd=$0.0500" in result.stdout
    assert "dev=1" in result.stdout


def test_audit_reconcile_flag_prints_note(seeded_root: Path) -> None:
    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["audit", "--reconcile"])
    assert result.exit_code == 0, result.stdout
    assert "reconciliation" in result.stdout
    assert "Azure Cost" in result.stdout
    assert "DeepSeek dashboard" in result.stdout


def test_audit_days_option_narrows_window(seeded_root: Path) -> None:
    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["audit", "--days", "1"])
    assert result.exit_code == 0, result.stdout
    assert "window=1d" in result.stdout
