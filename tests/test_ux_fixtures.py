"""Tests for CLI audit fixture loading, validation, and audit consumption."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from factory.chain.scheduled_tasks import _ux_auditor_fixture_run
from factory.testing.ux_fixtures import (
    load_fixture,
    load_fixtures_for_flow,
    validate_fixture,
    validate_fixture_or_raise,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_fixture_file(
    fixture_dir: Path,
    *,
    flow_source: str = "012-persist-direction-status-in-the-database/flow.md",
    steps: list[dict] | None = None,
) -> Path:
    """Write a minimal valid fixture YAML and return its path."""
    fixture_path = fixture_dir / "test_fixture.yaml"
    doc = {
        "flow_source": flow_source,
        "captured_at": "2026-07-30T00:00:00Z",
        "captured_by": "test",
        "steps": steps or [_minimal_step_dict()],
    }
    fixture_path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return fixture_path


def _minimal_step_dict(**overrides: object) -> dict:
    """Return a minimal valid step dict with command output and state evidence."""
    step: dict = {
        "step": 1,
        "description": "Run factory tick",
        "command": "factory tick --app factory",
        "command_output": {
            "stdout": "Tick completed successfully.",
            "stderr": "",
            "exit_code": 0,
        },
        "state_evidence": [
            {
                "kind": "file_exists",
                "description": "DB exists after tick",
                "path": "state/factory.db",
                "exists": True,
            }
        ],
        "provenance": {
            "captured_at": "2026-07-30T00:00:00Z",
            "runtime_transport": "text_run",
            "deploy_status": "disabled",
        },
    }
    step.update(overrides)
    return step


# --------------------------------------------------------------------------- #
# Happy path: complete fixture with command output and state evidence
# --------------------------------------------------------------------------- #


def test_load_fixture_happy_path(tmp_path):
    """A complete fixture with command output and state evidence loads correctly."""
    fixture_path = _make_fixture_file(tmp_path)

    fixture = load_fixture(fixture_path)

    assert fixture.flow_source == "012-persist-direction-status-in-the-database/flow.md"
    assert fixture.captured_by == "test"
    assert len(fixture.steps) == 1
    step = fixture.steps[0]
    assert step.step == 1
    assert step.command == "factory tick --app factory"
    assert step.command_output.stdout == "Tick completed successfully."
    assert step.command_output.exit_code == 0
    assert len(step.state_evidence) == 1
    assert step.state_evidence[0].kind == "file_exists"


def test_validate_happy_path_is_empty(tmp_path):
    """A complete fixture validates with zero errors."""
    fixture_path = _make_fixture_file(tmp_path)
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert errors == []


def test_validate_or_raise_happy_path_does_not_raise(tmp_path):
    """validate_fixture_or_raise does not raise for a valid fixture."""
    fixture_path = _make_fixture_file(tmp_path)
    fixture = load_fixture(fixture_path)
    validate_fixture_or_raise(fixture)  # should not raise


def test_fixture_with_multiple_steps(tmp_path):
    """A fixture with multiple steps loads all steps in order."""
    fixture_path = _make_fixture_file(
        tmp_path,
        steps=[
            _minimal_step_dict(step=1, command="cmd1"),
            _minimal_step_dict(step=2, command="cmd2"),
            _minimal_step_dict(step=3, command="cmd3"),
        ],
    )
    fixture = load_fixture(fixture_path)
    assert len(fixture.steps) == 3
    assert [s.step for s in fixture.steps] == [1, 2, 3]
    assert [s.command for s in fixture.steps] == ["cmd1", "cmd2", "cmd3"]


def test_fixture_multiple_state_evidence_items(tmp_path):
    """A step can carry multiple state evidence items."""
    step = _minimal_step_dict(
        state_evidence=[
            {
                "kind": "database_query",
                "description": "rows after tick",
                "result": [{"status": "created"}],
            },
            {
                "kind": "file_exists",
                "description": "DB file",
                "path": "state/factory.db",
                "exists": True,
            },
        ]
    )
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    assert len(fixture.steps[0].state_evidence) == 2
    kinds = [se.kind for se in fixture.steps[0].state_evidence]
    assert "database_query" in kinds
    assert "file_exists" in kinds


# --------------------------------------------------------------------------- #
# Failure path: missing command output for a documented step
# --------------------------------------------------------------------------- #


def test_validate_missing_command_output(tmp_path):
    """A step with empty command output (stdout, stderr, exit_code=0) is invalid."""
    step = _minimal_step_dict(command_output={"stdout": "", "stderr": "", "exit_code": 0})
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert len(errors) == 1
    assert errors[0].field == "command_output"
    assert "missing" in errors[0].message.lower()


def test_validate_or_raise_missing_command_output(tmp_path):
    """validate_fixture_or_raise raises ValueError for missing command output."""
    step = _minimal_step_dict(command_output={"stdout": "", "stderr": "", "exit_code": 0})
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    with pytest.raises(ValueError, match="command_output"):
        validate_fixture_or_raise(fixture)


def test_validate_command_output_with_stderr_only_is_valid(tmp_path):
    """A step with only stderr (but nonzero exit code) is valid — output was observed."""
    step = _minimal_step_dict(
        command_output={"stdout": "", "stderr": "error: something failed", "exit_code": 1}
    )
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert errors == []


def test_validate_command_output_with_stdout_only_is_valid(tmp_path):
    """A step with only stdout is valid."""
    step = _minimal_step_dict(
        command_output={"stdout": "some output", "stderr": "", "exit_code": 0}
    )
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert errors == []


# --------------------------------------------------------------------------- #
# Failure path: missing state evidence for a documented step
# --------------------------------------------------------------------------- #


def test_validate_missing_state_evidence(tmp_path):
    """A step with no state evidence items is invalid."""
    step = _minimal_step_dict(state_evidence=[])
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert len(errors) == 1
    assert errors[0].field == "state_evidence"
    assert "missing" in errors[0].message.lower()


def test_validate_or_raise_missing_state_evidence(tmp_path):
    """validate_fixture_or_raise raises ValueError for missing state evidence."""
    step = _minimal_step_dict(state_evidence=[])
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    with pytest.raises(ValueError, match="state_evidence"):
        validate_fixture_or_raise(fixture)


# --------------------------------------------------------------------------- #
# Validation: empty command
# --------------------------------------------------------------------------- #


def test_validate_empty_command(tmp_path):
    """A step with an empty command string is invalid."""
    step = _minimal_step_dict(command="")
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert any(e.field == "command" for e in errors)


# --------------------------------------------------------------------------- #
# Validation: empty flow_source
# --------------------------------------------------------------------------- #


def test_validate_empty_flow_source(tmp_path):
    """A fixture with an empty flow_source is invalid."""
    fixture_path = _make_fixture_file(tmp_path, flow_source="")
    fixture = load_fixture(fixture_path)

    errors = validate_fixture(fixture)
    assert any(e.field == "flow_source" for e in errors)


# --------------------------------------------------------------------------- #
# Loader: missing file
# --------------------------------------------------------------------------- #


def test_load_fixture_file_not_found(tmp_path):
    """load_fixture raises FileNotFoundError for a missing file."""
    with pytest.raises(FileNotFoundError, match="Fixture file not found"):
        load_fixture(tmp_path / "nonexistent.yaml")


# --------------------------------------------------------------------------- #
# Loader: malformed YAML
# --------------------------------------------------------------------------- #


def test_load_fixture_not_a_dict(tmp_path):
    """load_fixture raises ValueError when YAML is not a mapping."""
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="YAML mapping"):
        load_fixture(bad_path)


# --------------------------------------------------------------------------- #
# load_fixtures_for_flow: filtering
# --------------------------------------------------------------------------- #


def test_load_fixtures_for_flow_matches_correct_source(tmp_path):
    """load_fixtures_for_flow returns only fixtures matching the flow source."""
    # Write two fixtures with different flow sources
    _make_fixture_file(tmp_path, flow_source="001-other/flow.md")
    _make_fixture_file(
        tmp_path,
        flow_source="012-persist-direction-status-in-the-database/flow.md",
        steps=[_minimal_step_dict(step=2)],
    )

    fixtures = load_fixtures_for_flow(
        "012-persist-direction-status-in-the-database/flow.md",
        fixtures_dir=tmp_path,
    )
    assert len(fixtures) == 1
    assert fixtures[0].flow_source == "012-persist-direction-status-in-the-database/flow.md"


def test_load_fixtures_for_flow_no_match(tmp_path):
    """load_fixtures_for_flow returns empty list when no fixtures match."""
    _make_fixture_file(tmp_path, flow_source="001-other/flow.md")

    fixtures = load_fixtures_for_flow(
        "999-nonexistent/flow.md",
        fixtures_dir=tmp_path,
    )
    assert fixtures == []


def test_load_fixtures_for_flow_empty_dir(tmp_path):
    """load_fixtures_for_flow returns empty list for empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    fixtures = load_fixtures_for_flow("anything/flow.md", fixtures_dir=empty_dir)
    assert fixtures == []


def test_load_fixtures_for_flow_nonexistent_dir():
    """load_fixtures_for_flow returns empty list for nonexistent directory."""
    fixtures = load_fixtures_for_flow(
        "anything/flow.md",
        fixtures_dir=Path("/nonexistent/dir/12345"),
    )
    assert fixtures == []


# --------------------------------------------------------------------------- #
# Fixture step with provenance
# --------------------------------------------------------------------------- #


def test_fixture_step_includes_provenance(tmp_path):
    """Fixture step provenance fields are loaded correctly."""
    step = _minimal_step_dict(
        provenance={
            "captured_at": "2026-07-30T12:00:00Z",
            "runtime_transport": "text_run",
            "deploy_status": "disabled",
        }
    )
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    prov = fixture.steps[0].provenance
    assert prov.captured_at == "2026-07-30T12:00:00Z"
    assert prov.runtime_transport == "text_run"
    assert prov.deploy_status == "disabled"


# --------------------------------------------------------------------------- #
# StateEvidence data extraction
# --------------------------------------------------------------------------- #


def test_state_evidence_stores_extra_fields_as_data(tmp_path):
    """Extra fields in state_evidence YAML are stored in the data dict."""
    step = _minimal_step_dict(
        state_evidence=[
            {
                "kind": "database_query",
                "description": "rows after tick",
                "query": "SELECT COUNT(*) FROM directions",
                "result": [{"cnt": 15}],
            }
        ]
    )
    fixture_path = _make_fixture_file(tmp_path, steps=[step])
    fixture = load_fixture(fixture_path)

    se = fixture.steps[0].state_evidence[0]
    assert se.kind == "database_query"
    assert se.description == "rows after tick"
    assert se.data.get("query") == "SELECT COUNT(*) FROM directions"
    assert se.data.get("result") == [{"cnt": 15}]
    # kind and description are NOT in data
    assert "kind" not in se.data
    assert "description" not in se.data


# --------------------------------------------------------------------------- #
# Recorded fixture integration: the shipped D012 step 1 fixture
# --------------------------------------------------------------------------- #


def test_shipped_d012_fixture_loads_and_validates():
    """The shipped D012 fixture loads and passes validation."""
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "ux_audit"
        / "012-persist-direction-status-in-the-database.yaml"
    )
    assert fixture_path.is_file(), f"Shipped fixture not found at {fixture_path}"

    fixture = load_fixture(fixture_path)
    assert fixture.flow_source == "012-persist-direction-status-in-the-database/flow.md"
    assert len(fixture.steps) >= 1

    step1 = fixture.steps[0]
    assert step1.step == 1
    assert "factory tick" in step1.command
    assert step1.command_output.stdout.strip() != ""
    assert len(step1.state_evidence) >= 2  # DB query + file_exists at minimum

    validate_fixture_or_raise(fixture)


# --------------------------------------------------------------------------- #
# _ux_auditor_fixture_run integration
# --------------------------------------------------------------------------- #


def test_ux_auditor_fixture_run_produces_findings(tmp_path):
    """_ux_auditor_fixture_run loads fixtures and produces findings."""
    # Set up a minimal factory root with a direction that has flow.md
    root = tmp_path / "factory_root"
    (root / "apps" / "myapp" / "directions" / "012-persist-direction-status-in-the-database").mkdir(
        parents=True
    )
    (
        root
        / "apps"
        / "myapp"
        / "directions"
        / "012-persist-direction-status-in-the-database"
        / "flow.md"
    ).write_text(
        "# User flow\n\n1. Run `factory tick --app factory`\n",
        encoding="utf-8",
    )

    # Override _DEFAULT_FIXTURES_DIR via monkeypatch so load_fixtures_for_flow
    # resolves fixtures from our temp directory instead of the shipped directory.

    import factory.testing.ux_fixtures as uxf

    _orig = uxf._DEFAULT_FIXTURES_DIR
    try:
        uxf._DEFAULT_FIXTURES_DIR = tmp_path / "fixtures"
        (uxf._DEFAULT_FIXTURES_DIR).mkdir(parents=True, exist_ok=True)
        _make_fixture_file(
            uxf._DEFAULT_FIXTURES_DIR,
            flow_source="012-persist-direction-status-in-the-database/flow.md",
        )

        result = _ux_auditor_fixture_run("myapp", root)
    finally:
        uxf._DEFAULT_FIXTURES_DIR = _orig

    assert result.get("fixture_mode") is True
    findings = result.get("findings", [])
    assert isinstance(findings, list)
    assert len(findings) >= 1
    finding = findings[0]
    assert finding["flow"] == "012-persist-direction-status-in-the-database/flow.md"
    assert finding["step"] == 1
    assert finding["kind"] == "cli_audit"
    assert "suggested_direction" in finding


def test_ux_auditor_fixture_run_validates_before_returning(tmp_path):
    """_ux_auditor_fixture_run raises when fixture fails validation."""
    root = tmp_path / "factory_root"
    (root / "apps" / "myapp" / "directions" / "012-persist-direction-status-in-the-database").mkdir(
        parents=True
    )
    (
        root
        / "apps"
        / "myapp"
        / "directions"
        / "012-persist-direction-status-in-the-database"
        / "flow.md"
    ).write_text(
        "# User flow\n",
        encoding="utf-8",
    )

    import factory.testing.ux_fixtures as uxf

    _orig = uxf._DEFAULT_FIXTURES_DIR
    try:
        uxf._DEFAULT_FIXTURES_DIR = tmp_path / "fixtures"
        (uxf._DEFAULT_FIXTURES_DIR).mkdir(parents=True, exist_ok=True)
        # Write a fixture with missing state evidence
        bad_step = _minimal_step_dict(state_evidence=[])
        _make_fixture_file(
            uxf._DEFAULT_FIXTURES_DIR,
            flow_source="012-persist-direction-status-in-the-database/flow.md",
            steps=[bad_step],
        )

        with pytest.raises(ValueError, match="state_evidence"):
            _ux_auditor_fixture_run("myapp", root)
    finally:
        uxf._DEFAULT_FIXTURES_DIR = _orig
