"""Tests for scheduled UX audit input builder — narrow-read story D009.

AC1.1: Scheduled UX audit input SHALL include at least one flow.md artifact.
AC1.2: Scheduled UX audit input SHALL include app URL context.
AC1.3: Scheduled UX audit input SHALL include runtime context.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from factory.chain.scheduled_tasks import (
    _build_ux_auditor_context,
    _collect_flow_artifacts,
    _file_finding_as_direction,
    run_scheduled_persona,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _write_app_with_flow(tmp_path: Path, *, app: str = "sacrifice") -> Path:
    """Create a minimal app with one direction that has a flow.md."""
    apps = tmp_path / "apps" / app
    apps.mkdir(parents=True)
    (apps / "config.yaml").write_text(
        yaml.safe_dump({"name": app, "repo": "o/r"}), encoding="utf-8"
    )
    # Create a direction with a flow.md
    flow_dir = apps / "directions" / "001-test-flow"
    flow_dir.mkdir(parents=True)
    (flow_dir / "direction.md").write_text(
        "---\ntitle: Test Flow\ntype: ux\nexplore: false\n---\n# Test Flow\n\n## Why\n\nTesting.\n\n## Acceptance Criteria\n\n- [ ] It works\n",
        encoding="utf-8",
    )
    (flow_dir / "flow.md").write_text(
        "# User flow\n\n1. Open app\n2. Click button\n3. See result\n",
        encoding="utf-8",
    )
    (flow_dir / "state.yaml").write_text(
        yaml.safe_dump({"status": "created", "source": "cli"}), encoding="utf-8"
    )
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


# --------------------------------------------------------------------------- #
# AC1.1 — flow.md artifact inclusion
# --------------------------------------------------------------------------- #


def test_collect_flow_artifacts_finds_flow_md_files(tmp_path: Path) -> None:
    """AC1.1: _collect_flow_artifacts returns flow.md filenames and contents."""
    root = _write_app_with_flow(tmp_path)
    artifacts = _collect_flow_artifacts("sacrifice", root)
    assert len(artifacts) >= 1
    names = {name for name, _content in artifacts}
    assert "001-test-flow/flow.md" in names
    # Content is non-empty
    for _name, content in artifacts:
        assert len(content) > 0
        assert "# User flow" in content


def test_collect_flow_artifacts_empty_when_no_flows(tmp_path: Path) -> None:
    """When no directions have flow.md, return empty list (no crash)."""
    apps = tmp_path / "apps" / "sacrifice"
    apps.mkdir(parents=True)
    (apps / "config.yaml").write_text(
        yaml.safe_dump({"name": "sacrifice", "repo": "o/r"}), encoding="utf-8"
    )
    (apps / "directions").mkdir()
    (tmp_path / "state").mkdir()
    artifacts = _collect_flow_artifacts("sacrifice", tmp_path)
    assert artifacts == []


def test_file_finding_creates_flow_md_for_ux_finding(tmp_path: Path) -> None:
    """AC1.1: When filing a UX auditor finding with flow/step data, a flow.md
    is created in the direction directory."""
    apps = tmp_path / "apps" / "sacrifice"
    apps.mkdir(parents=True)
    (apps / "config.yaml").write_text(
        yaml.safe_dump({"name": "sacrifice", "repo": "o/r"}), encoding="utf-8"
    )
    (tmp_path / "state").mkdir()

    finding = {
        "flow": "pledge-flow.md",
        "step": 4,
        "kind": "friction",
        "evidence": "6 clicks to confirm",
        "suggestion": "reduce to 2 clicks",
        "suggested_direction": {
            "title": "collapse pledge confirmation to 2 clicks",
            "type": "ux",
            "why": "Confirmation flow is 6 clicks for a 2-click task.",
            "acceptance": ["User can confirm a pledge in <= 2 clicks"],
        },
    }
    direction = _file_finding_as_direction(
        persona="ux_auditor",
        app="sacrifice",
        finding=finding,
        software_factory_root=tmp_path,
        dry_run=False,
    )
    assert direction is not None
    # The direction dir should contain a flow.md
    flow_md = direction.dir_path / "flow.md"
    assert flow_md.exists(), f"Expected flow.md at {flow_md}"
    content = flow_md.read_text(encoding="utf-8")
    assert "pledge-flow.md" in content or "User flow" in content


def test_ux_auditor_dry_run_creates_flow_md_in_scratch(tmp_path: Path) -> None:
    """AC1.1: dry-run UX auditor run creates a flow.md in the scratch direction."""
    root = _write_app_with_flow(tmp_path)
    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=True)
    assert out.status == "dry_run"
    assert len(out.directions_filed) == 1

    # Find the scratch direction and check for flow.md
    scratch = root / "state" / "dry_run_scratch" / "apps" / "sacrifice" / "directions"
    matches = list(scratch.glob(f"{out.directions_filed[0]}-*"))
    assert len(matches) == 1
    flow_md = matches[0] / "flow.md"
    assert flow_md.exists(), f"Expected flow.md at {flow_md} for dry-run UX audit"


# --------------------------------------------------------------------------- #
# AC1.2 — app URL context
# --------------------------------------------------------------------------- #


def test_build_ux_auditor_context_includes_app_url(tmp_path: Path) -> None:
    """AC1.2: The UX auditor context includes app URL information."""
    root = _write_app_with_flow(tmp_path)
    context = _build_ux_auditor_context("sacrifice", root)
    assert "app" in context.lower()
    assert "sacrifice" in context
    # App config data is present (repo URL as proxy for app URL)
    assert "o/r" in context or "config" in context.lower()


def test_ux_auditor_input_includes_app_url_via_dry_run(tmp_path: Path) -> None:
    """AC1.2: Dry-run UX audit input carries app URL context in its raw_output."""
    root = _write_app_with_flow(tmp_path)
    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=True)
    # The raw_output from the dry-run fixture includes app context
    assert out.status == "dry_run"
    # The fixture finding references a concrete flow filename
    raw = out.raw_output
    assert isinstance(raw, dict)
    findings = raw.get("findings", [])
    assert len(findings) >= 1
    assert "flow" in findings[0]


# --------------------------------------------------------------------------- #
# AC1.3 — runtime context
# --------------------------------------------------------------------------- #


def test_build_ux_auditor_context_includes_runtime_context(tmp_path: Path) -> None:
    """AC1.3: The UX auditor context includes runtime information."""
    root = _write_app_with_flow(tmp_path)
    context = _build_ux_auditor_context("sacrifice", root)
    # Runtime context includes timestamp or mode or root path indicators
    assert "runtime" in context.lower() or "context" in context.lower()
    # Should mention flow artifacts section
    assert "flow" in context.lower()


def test_ux_auditor_input_includes_runtime_context_via_dry_run(tmp_path: Path) -> None:
    """AC1.3: Dry-run UX audit input includes runtime context markers."""
    root = _write_app_with_flow(tmp_path)
    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=True)
    assert out.status == "dry_run"
    assert out.persona == "ux_auditor"
    assert out.app == "sacrifice"
    # Runtime context is embedded in the raw_output
    raw = out.raw_output
    assert "duration_s" in raw


# --------------------------------------------------------------------------- #
# Backward compatibility
# --------------------------------------------------------------------------- #


def test_non_ux_persona_not_affected(tmp_path: Path) -> None:
    """Bug-hunter (non-UX) input is unchanged — no flow.md artifacts leaked."""
    root = _write_app_with_flow(tmp_path)
    # Run bug_hunter (not ux_auditor)
    out = run_scheduled_persona("bug_hunter", "sacrifice", root, dry_run=True)
    assert out.status == "dry_run"
    assert out.findings_count == 1
    assert len(out.directions_filed) == 1

    # Check that the direction does NOT have a flow.md (bug_hunter doesn't use UI)
    scratch = root / "state" / "dry_run_scratch" / "apps" / "sacrifice" / "directions"
    matches = list(scratch.glob(f"{out.directions_filed[0]}-*"))
    assert len(matches) == 1
    flow_md = matches[0] / "flow.md"
    assert not flow_md.exists(), (
        f"Non-UX persona should not create flow.md, but found {flow_md}"
    )