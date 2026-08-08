"""Tests for ``factory inbox`` CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from factory.chain.handlers import persist_story
from factory.chain.state_machine import StoryRecord, StoryState


@pytest.fixture
def seeded_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway software-factory root with an apps/sacrifice/ config and
    a few seeded stories + a needs-direction direction."""
    monkeypatch.setenv("FACTORY_WEBHOOK_LAZY", "1")
    # Prevent Rich from truncating table cells under small TTY widths.
    monkeypatch.setenv("COLUMNS", "240")
    monkeypatch.setenv("TERM", "xterm-256color")
    apps = tmp_path / "apps" / "sacrifice"
    apps.mkdir(parents=True, exist_ok=True)
    (apps / "config.yaml").write_text(
        "name: sacrifice\nrepo: x/y\ndefault_branch: main\n", encoding="utf-8"
    )

    # Direction in needs-direction status.
    direction = apps / "directions" / "010-vague"
    direction.mkdir(parents=True, exist_ok=True)
    (direction / "direction.md").write_text(
        "---\ntitle: vague thought\n---\n\n# vague\n",
        encoding="utf-8",
    )
    (direction / "state.yaml").write_text(
        "status: needs-direction\nmissing: [user_flow, api_spec]\n",
        encoding="utf-8",
    )

    db = tmp_path / "state" / "factory.db"
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    persist_story(
        StoryRecord(
            direction_id="002",
            app="sacrifice",
            title="t",
            slug="story-blocked-by-cap",
            scope="backend",
            state=StoryState.STORY_CREATED.value,
            last_rejection_reason="daily_spend_cap_exceeded",
        ),
        db,
    )
    persist_story(
        StoryRecord(
            direction_id="002",
            app="sacrifice",
            title="t",
            slug="story-in-blocked-state",
            scope="backend",
            state=StoryState.BLOCKED_TESTS_NEED_CLARIFICATION.value,
        ),
        db,
    )
    return tmp_path


def _runner_with_root(root: Path) -> tuple[CliRunner, object]:
    """Re-import the CLI module with _FACTORY_ROOT pinned to ``root``."""
    import importlib

    import factory.cli as cli_mod

    importlib.reload(cli_mod)
    cli_mod._FACTORY_ROOT = root  # type: ignore[attr-defined]
    return CliRunner(), cli_mod


def test_inbox_lists_rejection_reasons_and_needs_direction(seeded_root: Path) -> None:
    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["inbox"])
    assert result.exit_code == 0
    # Stories with rejection / blocked appear:
    assert "story-blocked-by-cap" in result.stdout
    assert "daily_spend_cap_exceeded" in result.stdout
    assert "story-in-blocked-state" in result.stdout
    # needs-direction tracker is listed:
    assert "010-vague" in result.stdout


def test_inbox_app_filter(seeded_root: Path) -> None:
    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["inbox", "--app", "sacrifice"])
    assert result.exit_code == 0
    assert "story-blocked-by-cap" in result.stdout


def test_inbox_surfaces_a_gate_block_parked_story(seeded_root: Path) -> None:
    """019 blocker S2: a story parked by ``auto_merge._park_gate_block_exhausted``
    sets ``last_rejection_reason``, and MUST reach the inbox despite
    ``blocked_ci_unresolved`` sitting on the tracker-closer's resolved-states
    allowlist — that allowlist is correct for the real-CI-failure park (which
    closes the PR), not for a gate-block park that leaves the PR open."""
    db = seeded_root / "state" / "factory.db"
    persist_story(
        StoryRecord(
            direction_id="019",
            app="sacrifice",
            title="t",
            slug="story-gate-block-parked",
            scope="backend",
            state=StoryState.BLOCKED_CI_UNRESOLVED.value,
            last_rejection_reason=(
                "gate_block_exhausted: required gate(s) ['smoke-green'] never "
                "passed after 3 consecutive evaluations of head cafe1234"
            ),
            error="auto-merge: gate_block_exhausted: ...",
        ),
        db,
    )
    # Regression pin: the REAL-CI-FAILURE park (no last_rejection_reason) must
    # stay invisible — that park already closed the PR, so there is nothing
    # left pending, and the tracker-closer / inbox must keep agreeing on that.
    persist_story(
        StoryRecord(
            direction_id="019",
            app="sacrifice",
            title="t",
            slug="story-ci-failure-parked",
            scope="backend",
            state=StoryState.BLOCKED_CI_UNRESOLVED.value,
        ),
        db,
    )

    runner, cli_mod = _runner_with_root(seeded_root)
    result = runner.invoke(cli_mod.app, ["inbox"])
    assert result.exit_code == 0
    assert "story-gate-block-parked" in result.stdout
    assert "gate_block_exhausted" in result.stdout
    assert "story-ci-failure-parked" not in result.stdout
