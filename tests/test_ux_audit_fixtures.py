"""Tests for recorded-fixture contract and loader (story D015 narrow read)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory.testing.fixtures import (
    RecordedFixture,
    StateEvidence,
    StepEvidence,
    load_audit_fixture,
    load_audit_fixture_for_flow,
)


def _write_fixture_file(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Valid fixture loads successfully (AC1.1 + AC1.2 + AC1.3 combined)
# --------------------------------------------------------------------------- #


def test_valid_fixture_loads_all_fields(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "012-persist-direction-status-in-the-database/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "factory tick --app factory",
                "command_output": "tick complete",
                "state_evidence": {
                    "description": "state after tick",
                    "state_snapshot": {"status": "ok", "direction_id": "012"},
                },
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    result = load_audit_fixture(fixture_path)

    assert isinstance(result, RecordedFixture)
    assert result.flow == "012-persist-direction-status-in-the-database/flow.md"
    assert result.source_path == fixture_path
    assert len(result.steps) == 1

    step = result.steps[0]
    assert isinstance(step, StepEvidence)
    assert step.step == 1
    assert step.command == "factory tick --app factory"
    assert step.command_output == "tick complete"

    se = step.state_evidence
    assert isinstance(se, StateEvidence)
    assert se.description == "state after tick"
    assert se.state_snapshot == {"status": "ok", "direction_id": "012"}


def test_valid_fixture_loads_real_sample() -> None:
    """The real sample fixture under apps/factory/directions/012-.../ parses cleanly."""
    fixture_path = (
        Path(__file__).resolve().parent.parent
        / "apps"
        / "factory"
        / "directions"
        / ("012-persist-direction-status-in-the-database")
        / "fixture.json"
    )

    result = load_audit_fixture(fixture_path)

    assert result.flow == "012-persist-direction-status-in-the-database/flow.md"
    assert len(result.steps) == 1
    assert result.steps[0].step == 1
    assert result.steps[0].command == "factory tick --app factory"
    # command_output must be non-empty
    assert len(result.steps[0].command_output) > 0
    # state_evidence must include description and snapshot
    assert len(result.steps[0].state_evidence.description) > 0
    assert isinstance(result.steps[0].state_evidence.state_snapshot, dict)


def test_load_fixture_for_flow_reads_repository_fixture() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    result = load_audit_fixture_for_flow(
        repo_root,
        app="factory",
        flow="012-persist-direction-status-in-the-database/flow.md",
    )

    assert result.flow == "012-persist-direction-status-in-the-database/flow.md"
    assert result.source_path == (
        repo_root
        / "apps"
        / "factory"
        / "directions"
        / "012-persist-direction-status-in-the-database"
        / "fixture.json"
    )
    assert result.steps[0].step == 1


def test_load_fixture_for_flow_missing_fixture_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="fixture file not found"):
        load_audit_fixture_for_flow(
            tmp_path,
            app="factory",
            flow="012-persist-direction-status-in-the-database/flow.md",
        )


def test_load_fixture_for_flow_rejects_non_flow_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="flow.md"):
        load_audit_fixture_for_flow(
            tmp_path,
            app="factory",
            flow="012-persist-direction-status-in-the-database/not-flow.txt",
        )


def test_load_fixture_for_flow_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid flow path"):
        load_audit_fixture_for_flow(
            tmp_path,
            app="factory",
            flow="../012-persist-direction-status-in-the-database/flow.md",
        )


def test_multiple_steps_preserve_order(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "some-flow/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd1",
                "command_output": "out1",
                "state_evidence": {"description": "d1", "state_snapshot": {"a": 1}},
            },
            {
                "step": 2,
                "command": "cmd2",
                "command_output": "out2",
                "state_evidence": {"description": "d2", "state_snapshot": {"b": 2}},
            },
            {
                "step": 3,
                "command": "cmd3",
                "command_output": "out3",
                "state_evidence": {"description": "d3", "state_snapshot": {"c": 3}},
            },
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    result = load_audit_fixture(fixture_path)

    assert len(result.steps) == 3
    assert [s.step for s in result.steps] == [1, 2, 3]
    assert [s.command for s in result.steps] == ["cmd1", "cmd2", "cmd3"]
    assert [s.command_output for s in result.steps] == ["out1", "out2", "out3"]


# --------------------------------------------------------------------------- #
# Flow/step mapping is preserved (AC requirement)
# --------------------------------------------------------------------------- #


def test_flow_field_preserves_flow_identity(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "042-some-other-flow/flow.md",
        "steps": [
            {
                "step": 5,
                "command": "factory status --app x",
                "command_output": "ok",
                "state_evidence": {"description": "desc", "state_snapshot": None},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    result = load_audit_fixture(fixture_path)

    assert result.flow == "042-some-other-flow/flow.md"
    assert result.steps[0].step == 5


def test_state_snapshot_can_be_null(tmp_path: Path) -> None:
    """state_snapshot can be any JSON value including null."""
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"description": "desc", "state_snapshot": None},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    result = load_audit_fixture(fixture_path)

    assert result.steps[0].state_evidence.state_snapshot is None


# --------------------------------------------------------------------------- #
# Missing command output is rejected
# --------------------------------------------------------------------------- #


def test_missing_command_output_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="command_output"):
        load_audit_fixture(fixture_path)


def test_empty_command_output_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "   ",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="command_output"):
        load_audit_fixture(fixture_path)


# --------------------------------------------------------------------------- #
# Missing state evidence is rejected
# --------------------------------------------------------------------------- #


def test_missing_state_evidence_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="state_evidence"):
        load_audit_fixture(fixture_path)


def test_missing_state_evidence_description_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="description"):
        load_audit_fixture(fixture_path)


def test_missing_state_snapshot_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"description": "desc"},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="state_snapshot"):
        load_audit_fixture(fixture_path)


# --------------------------------------------------------------------------- #
# Malformed / edge cases
# --------------------------------------------------------------------------- #


def test_missing_flow_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="flow"):
        load_audit_fixture(fixture_path)


def test_missing_steps_rejected(tmp_path: Path) -> None:
    fixture_data = {"flow": "f/flow.md"}
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="steps"):
        load_audit_fixture(fixture_path)


def test_empty_steps_rejected(tmp_path: Path) -> None:
    fixture_data = {"flow": "f/flow.md", "steps": []}
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="must not be empty"):
        load_audit_fixture(fixture_path)


def test_step_not_a_dict_rejected(tmp_path: Path) -> None:
    fixture_data = {"flow": "f/flow.md", "steps": ["not-a-dict"]}
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="must be a dict"):
        load_audit_fixture(fixture_path)


def test_not_json_rejected(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text("not json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_audit_fixture(fixture_path)


def test_root_not_object_rejected(tmp_path: Path) -> None:
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", ["list", "root"])

    with pytest.raises(ValueError, match="JSON object"):
        load_audit_fixture(fixture_path)


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_audit_fixture(Path("/nonexistent/fixture.json"))


def test_missing_step_number_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="step"):
        load_audit_fixture(fixture_path)


def test_missing_command_rejected(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command_output": "out",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    with pytest.raises(ValueError, match="command"):
        load_audit_fixture(fixture_path)


def test_snapshot_can_be_empty_dict(tmp_path: Path) -> None:
    fixture_data = {
        "flow": "f/flow.md",
        "steps": [
            {
                "step": 1,
                "command": "cmd",
                "command_output": "out",
                "state_evidence": {"description": "d", "state_snapshot": {}},
            }
        ],
    }
    fixture_path = _write_fixture_file(tmp_path / "fixture.json", fixture_data)

    result = load_audit_fixture(fixture_path)
    assert result.steps[0].state_evidence.state_snapshot == {}
