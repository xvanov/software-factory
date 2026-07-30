"""Recorded-fixture contract + loader for CLI UX audit evidence.

The contract defines what a recorded fixture must contain so the UX audit
runtime can consume step-by-step command output and state evidence without
requiring live CLI execution.

Schema (JSON):

.. code-block:: json

    {
      "flow": "012-persist-direction-status-in-the-database/flow.md",
      "steps": [
        {
          "step": 1,
          "command": "factory tick --app factory",
          "command_output": "...",
          "state_evidence": {
            "description": "...",
            "state_snapshot": {}
          }
        }
      ]
    }

Fields
------

* ``flow`` (str, required) — identifies the flow file the evidence belongs to,
  matching the label used in ``_collect_flow_artifacts``.
* ``steps`` (list, required, non-empty) — ordered per-step evidence entries.
* ``steps[].step`` (int, required) — 1-based step number within the flow.
* ``steps[].command`` (str, required) — the CLI command executed for this step.
* ``steps[].command_output`` (str, required) — captured command output
  (stdout+stderr).
* ``steps[].state_evidence`` (dict, required) — evidence of state observed at
  the step.
* ``steps[].state_evidence.description`` (str, required) — human-readable
  description of the state evidence.
* ``steps[].state_evidence.state_snapshot`` (any, required) — structured state
  data captured after the command.

Loader behaviour
----------------

* ``load_audit_fixture(path)`` reads and validates a fixture file, returning a
  ``RecordedFixture`` dataclass.
* Validation fails closed: missing or malformed fields raise ``ValueError``
  with a message naming the offending path and field.
* The loader does NOT execute any CLI command; it only reads recorded evidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass
class StateEvidence:
    """State evidence recorded after a single audit step."""

    description: str
    state_snapshot: Any


@dataclass
class StepEvidence:
    """Command output + state evidence for one step in a flow."""

    step: int
    command: str
    command_output: str
    state_evidence: StateEvidence


@dataclass
class RecordedFixture:
    """A complete recorded fixture for one flow."""

    flow: str
    steps: list[StepEvidence]
    source_path: Path


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #


def _require_str(raw: dict[str, Any], key: str, *, path: Path) -> str:
    val = raw.get(key)
    if val is None:
        raise ValueError(f"{path}: missing required field {key!r}")
    if not isinstance(val, str):
        raise ValueError(f"{path}: {key!r} must be a string, got {type(val).__name__}")
    stripped = val.strip()
    if not stripped:
        raise ValueError(f"{path}: {key!r} must not be empty")
    return stripped


def _require_int(raw: dict[str, Any], key: str, *, path: Path) -> int:
    val = raw.get(key)
    if val is None:
        raise ValueError(f"{path}: missing required field {key!r}")
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    if isinstance(val, float) and val.is_integer():
        return int(val)
    raise ValueError(f"{path}: {key!r} must be an integer, got {type(val).__name__}")


def _require_dict(raw: dict[str, Any], key: str, *, path: Path) -> dict[str, Any]:
    val = raw.get(key)
    if val is None:
        raise ValueError(f"{path}: missing required field {key!r}")
    if not isinstance(val, dict):
        raise ValueError(f"{path}: {key!r} must be a dict, got {type(val).__name__}")
    return val


def _require_list(raw: dict[str, Any], key: str, *, path: Path) -> list[Any]:
    val = raw.get(key)
    if val is None:
        raise ValueError(f"{path}: missing required field {key!r}")
    if not isinstance(val, list):
        raise ValueError(f"{path}: {key!r} must be a list, got {type(val).__name__}")
    return val


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def fixture_path_for_flow(
    software_factory_root: Path,
    *,
    app: str,
    flow: str,
) -> Path:
    """Resolve the canonical recorded-fixture path for ``app`` + ``flow``.

    ``flow`` is the flow identity label used by the UX-auditor context
    (for example ``012-persist-direction-status-in-the-database/flow.md``).
    """
    app_name = app.strip()
    if not app_name:
        raise ValueError("app must not be empty")

    flow_path = PurePosixPath(flow)
    if flow_path.is_absolute() or ".." in flow_path.parts:
        raise ValueError(f"invalid flow path: {flow!r}")
    if flow_path.name != "flow.md":
        raise ValueError(f"flow identity must end with 'flow.md', got: {flow!r}")

    return (
        Path(software_factory_root)
        / "apps"
        / app_name
        / "directions"
        / Path(*flow_path.parent.parts)
        / "fixture.json"
    )


def load_audit_fixture_for_flow(
    software_factory_root: Path,
    *,
    app: str,
    flow: str,
) -> RecordedFixture:
    """Load recorded fixture data for a documented flow identity."""
    return load_audit_fixture(fixture_path_for_flow(software_factory_root, app=app, flow=flow))



def load_audit_fixture(path: Path) -> RecordedFixture:
    """Load and validate a recorded CLI audit fixture from *path*.

    Returns a ``RecordedFixture`` with all steps parsed and validated.
    Raises ``ValueError`` on any malformation or missing required field.
    Raises ``FileNotFoundError`` if *path* does not exist.
    Raises ``json.JSONDecodeError`` if *path* is not valid JSON.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"fixture file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: fixture root must be a JSON object, got {type(raw).__name__}")

    flow = _require_str(raw, "flow", path=path)
    steps_raw = _require_list(raw, "steps", path=path)
    if not steps_raw:
        raise ValueError(f"{path}: 'steps' must not be empty")

    steps: list[StepEvidence] = []
    for i, step_raw in enumerate(steps_raw):
        if not isinstance(step_raw, dict):
            raise ValueError(
                f"{path}: steps[{i}] must be a dict, got {type(step_raw).__name__}"
            )
        step_num = _require_int(step_raw, "step", path=path)
        command = _require_str(step_raw, "command", path=path)
        command_output = _require_str(step_raw, "command_output", path=path)
        se_raw = _require_dict(step_raw, "state_evidence", path=path)
        se_description = _require_str(se_raw, "description", path=path)
        # state_snapshot is required but can be any JSON value (including null).
        if "state_snapshot" not in se_raw:
            raise ValueError(f"{path}: steps[{i}].state_evidence missing required field 'state_snapshot'")

        steps.append(
            StepEvidence(
                step=step_num,
                command=command,
                command_output=command_output,
                state_evidence=StateEvidence(
                    description=se_description,
                    state_snapshot=se_raw["state_snapshot"],
                ),
            )
        )

    return RecordedFixture(flow=flow, steps=steps, source_path=path)


__all__ = [
    "RecordedFixture",
    "StepEvidence",
    "StateEvidence",
    "fixture_path_for_flow",
    "load_audit_fixture",
    "load_audit_fixture_for_flow",
]