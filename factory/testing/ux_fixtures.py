"""CLI audit fixture contract, loader, and validator.

Delivers the test-facing story for D015: recorded fixture path for documented
``factory`` CLI UX flows, capturing command output plus state evidence per step,
and enabling audit consumption of that evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# --------------------------------------------------------------------------- #
# Fixture contract (dataclasses)
# --------------------------------------------------------------------------- #


@dataclass
class CommandOutput:
    """Captured output from a CLI command execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


@dataclass
class StateEvidence:
    """A single piece of state evidence linked to a step."""

    kind: str  # e.g. "database_query", "file_exists", "file_content"
    description: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepProvenance:
    """Metadata about when and how a step was captured."""

    captured_at: str = ""
    runtime_transport: str = ""
    deploy_status: str = ""


@dataclass
class FixtureStep:
    """One step in a recorded CLI audit fixture."""

    step: int
    description: str
    command: str
    command_output: CommandOutput = field(default_factory=CommandOutput)
    state_evidence: list[StateEvidence] = field(default_factory=list)
    provenance: StepProvenance = field(default_factory=StepProvenance)


@dataclass
class CliAuditFixture:
    """A complete recorded fixture for a documented CLI flow."""

    flow_source: str  # e.g. "012-persist-direction-status-in-the-database/flow.md"
    captured_at: str = ""
    captured_by: str = ""
    steps: list[FixtureStep] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Validation errors
# --------------------------------------------------------------------------- #


@dataclass
class FixtureValidationError:
    """A single validation problem with a fixture."""

    step_index: int
    step_number: int
    field: str
    message: str


# --------------------------------------------------------------------------- #
# Default fixture directory
# --------------------------------------------------------------------------- #

_DEFAULT_FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "ux_audit"


def _resolve_fixture_dir(fixtures_dir: Path | None = None) -> Path:
    """Return the resolved fixture directory, creating it if needed."""
    return fixtures_dir or _DEFAULT_FIXTURES_DIR


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def load_fixture(fixture_path: Path) -> CliAuditFixture:
    """Load and parse a single CLI audit fixture from a YAML file.

    Args:
        fixture_path: Path to a ``.yaml`` fixture file.

    Returns:
        A parsed ``CliAuditFixture``.

    Raises:
        FileNotFoundError: If the fixture file does not exist.
        ValueError: If the YAML is malformed or missing required fields.
    """
    if not fixture_path.is_file():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    raw = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Fixture {fixture_path} must be a YAML mapping, got {type(raw).__name__}")

    fixture = CliAuditFixture(
        flow_source=str(raw.get("flow_source", "")),
        captured_at=str(raw.get("captured_at", "")),
        captured_by=str(raw.get("captured_by", "")),
    )

    for i, step_raw in enumerate(raw.get("steps", [])):
        if not isinstance(step_raw, dict):
            raise ValueError(
                f"Fixture {fixture_path}: step at index {i} must be a mapping, "
                f"got {type(step_raw).__name__}"
            )

        cmd_raw = step_raw.get("command_output", {}) or {}
        command_output = CommandOutput(
            stdout=str(cmd_raw.get("stdout", "")),
            stderr=str(cmd_raw.get("stderr", "")),
            exit_code=int(cmd_raw.get("exit_code", 0)),
        )

        state_evidence: list[StateEvidence] = []
        for se in step_raw.get("state_evidence", []) or []:
            state_evidence.append(
                StateEvidence(
                    kind=str(se.get("kind", "")),
                    description=str(se.get("description", "")),
                    data={k: v for k, v in se.items() if k not in ("kind", "description")},
                )
            )

        prov_raw = step_raw.get("provenance", {}) or {}
        provenance = StepProvenance(
            captured_at=str(prov_raw.get("captured_at", "")),
            runtime_transport=str(prov_raw.get("runtime_transport", "")),
            deploy_status=str(prov_raw.get("deploy_status", "")),
        )

        fixture.steps.append(
            FixtureStep(
                step=int(step_raw.get("step", i + 1)),
                description=str(step_raw.get("description", "")),
                command=str(step_raw.get("command", "")),
                command_output=command_output,
                state_evidence=state_evidence,
                provenance=provenance,
            )
        )

    return fixture


def load_fixtures_for_flow(
    flow_source: str,
    fixtures_dir: Path | None = None,
) -> list[CliAuditFixture]:
    """Load all recorded fixtures matching a given flow source.

    Args:
        flow_source: The flow filename to match (e.g.
            ``"012-persist-direction-status-in-the-database/flow.md"``).
        fixtures_dir: Directory containing fixture YAML files. Defaults to
            ``tests/fixtures/ux_audit/``.

    Returns:
        A list of ``CliAuditFixture`` objects matching the flow source.
    """
    resolved_dir = _resolve_fixture_dir(fixtures_dir)
    if not resolved_dir.is_dir():
        return []

    fixtures: list[CliAuditFixture] = []
    for fixture_file in sorted(resolved_dir.glob("*.yaml")):
        try:
            fixture = load_fixture(fixture_file)
            if fixture.flow_source == flow_source:
                fixtures.append(fixture)
        except Exception:
            continue
    return fixtures


# --------------------------------------------------------------------------- #
# Validator
# --------------------------------------------------------------------------- #


def validate_fixture(fixture: CliAuditFixture) -> list[FixtureValidationError]:
    """Validate a loaded fixture for required evidence per step.

    Every step in a recorded CLI audit fixture MUST include:
    * A non-empty ``command`` field.
    * Command output (non-empty ``stdout`` or ``stderr``, or a non-zero exit code
      — i.e. evidence that the command was executed and something was observed).
    * At least one piece of state evidence.

    Args:
        fixture: A loaded ``CliAuditFixture``.

    Returns:
        A list of ``FixtureValidationError`` objects; empty if valid.
    """
    errors: list[FixtureValidationError] = []

    if not fixture.flow_source:
        errors.append(
            FixtureValidationError(
                step_index=-1, step_number=-1, field="flow_source", message="flow_source is empty"
            )
        )

    for i, step in enumerate(fixture.steps):
        if not step.command:
            errors.append(
                FixtureValidationError(
                    step_index=i,
                    step_number=step.step,
                    field="command",
                    message="command is empty",
                )
            )

        # Command output is missing if stdout AND stderr are both empty AND
        # exit_code is 0 (which would mean nothing observable happened).
        if (
            not step.command_output.stdout.strip()
            and not step.command_output.stderr.strip()
            and step.command_output.exit_code == 0
        ):
            errors.append(
                FixtureValidationError(
                    step_index=i,
                    step_number=step.step,
                    field="command_output",
                    message="command output is missing (empty stdout, stderr, exit_code=0)",
                )
            )

        if not step.state_evidence:
            errors.append(
                FixtureValidationError(
                    step_index=i,
                    step_number=step.step,
                    field="state_evidence",
                    message="state evidence is missing for step",
                )
            )

    return errors


def validate_fixture_or_raise(fixture: CliAuditFixture) -> None:
    """Validate a fixture and raise ``ValueError`` if any errors are found.

    Args:
        fixture: A loaded ``CliAuditFixture``.

    Raises:
        ValueError: If validation errors are found.
    """
    errors = validate_fixture(fixture)
    if errors:
        messages = [
            f"step {e.step_number} (idx {e.step_index}): {e.field}: {e.message}"
            for e in errors
        ]
        raise ValueError(
            f"Fixture validation failed for {fixture.flow_source}:\n  "
            + "\n  ".join(messages)
        )
