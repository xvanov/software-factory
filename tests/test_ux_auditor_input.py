"""Tests for scheduled UX audit runtime inputs (story D009 narrow-read)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.chain.scheduled_tasks import (
    _build_ux_auditor_context,
    _collect_flow_artifacts,
    _file_finding_as_direction,
    _live_run,
    run_scheduled_persona,
)


def _write_app(
    tmp_path: Path,
    *,
    app: str = "sacrifice",
    with_flow: bool = True,
    health_check_command: str | None = None,
) -> Path:
    apps = tmp_path / "apps" / app
    apps.mkdir(parents=True)
    config: dict[str, Any] = {"name": app, "repo": "o/r"}
    if health_check_command is not None:
        config["deploy"] = {
            "enabled": True,
            "health_check_command": health_check_command,
        }
    (apps / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    directions = apps / "directions"
    directions.mkdir(parents=True, exist_ok=True)
    if with_flow:
        flow_dir = directions / "001-checkout-flow"
        flow_dir.mkdir(parents=True)
        (flow_dir / "direction.md").write_text(
            "---\ntitle: Checkout flow\ntype: ux\nexplore: false\n---\n# Checkout\n",
            encoding="utf-8",
        )
        (flow_dir / "flow.md").write_text(
            "# checkout-flow.md\n\n1. Open app\n2. Choose plan\n3. Confirm purchase\n",
            encoding="utf-8",
        )
        (flow_dir / "state.yaml").write_text(
            yaml.safe_dump({"status": "created", "source": "cli"}),
            encoding="utf-8",
        )

    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_collect_flow_artifacts_returns_filename_and_steps(tmp_path: Path) -> None:
    root = _write_app(tmp_path)

    artifacts = _collect_flow_artifacts("sacrifice", root)

    assert artifacts == [
        (
            "001-checkout-flow/flow.md",
            "# checkout-flow.md\n\n1. Open app\n2. Choose plan\n3. Confirm purchase",
        )
    ]


def test_build_context_requires_at_least_one_flow_artifact(tmp_path: Path) -> None:
    root = _write_app(tmp_path, with_flow=False)

    with pytest.raises(ValueError, match="flow.md"):
        _build_ux_auditor_context("sacrifice", root)


def test_build_context_includes_app_url_context(tmp_path: Path) -> None:
    root = _write_app(
        tmp_path,
        health_check_command="curl -fsS https://app.example.test/healthz",
    )

    context = _build_ux_auditor_context("sacrifice", root)

    assert "### App URL Context" in context
    assert "https://app.example.test/healthz" in context


def test_build_context_includes_runtime_context_fields(tmp_path: Path) -> None:
    root = _write_app(tmp_path)

    context = _build_ux_auditor_context("sacrifice", root)

    assert "### Runtime Context" in context
    assert f"- Software factory root: `{root}`" in context
    assert "- Target app: `sacrifice`" in context


def test_live_run_ux_prompt_contains_flow_and_runtime_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_app(
        tmp_path,
        health_check_command="curl -fsS https://app.example.test/healthz",
    )
    captured: dict[str, Any] = {}

    def _fake_prelude(*_args: Any, **_kwargs: Any) -> str:
        return "PRELUDE"

    def _fake_text_run(
        _persona: str,
        prompt: str,
        _model: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        captured["prompt"] = prompt
        return {"findings": [], "duration_s": 0.2}

    monkeypatch.setattr("factory.context.loader.compose_context_prelude", _fake_prelude)
    monkeypatch.setattr("factory.runner.text_run", _fake_text_run)
    monkeypatch.setattr("factory.chain.scheduled_tasks.route", lambda _persona: "fake-model")

    out = _live_run("ux_auditor", "sacrifice", root)

    assert out == {"findings": [], "duration_s": 0.2}
    prompt = str(captured["prompt"])
    assert "## Scheduled UX Audit Runtime Inputs" in prompt
    assert "001-checkout-flow/flow.md" in prompt
    assert "1. Open app" in prompt
    assert "https://app.example.test/healthz" in prompt
    assert "### Runtime Context" in prompt
    assert "# Context prelude\n\nPRELUDE" in prompt


def test_live_run_non_ux_prompt_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_app(tmp_path)
    captured: dict[str, Any] = {}

    def _fake_prelude(*_args: Any, **_kwargs: Any) -> str:
        return "PRELUDE"

    def _fake_text_run(
        _persona: str,
        prompt: str,
        _model: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        captured["prompt"] = prompt
        return {}

    monkeypatch.setattr("factory.context.loader.compose_context_prelude", _fake_prelude)
    monkeypatch.setattr("factory.runner.text_run", _fake_text_run)
    monkeypatch.setattr("factory.chain.scheduled_tasks.route", lambda _persona: "fake-model")

    _live_run("bug_hunter", "sacrifice", root)

    assert "Scheduled UX Audit Runtime Inputs" not in str(captured["prompt"])


def test_run_scheduled_persona_skips_when_ux_live_run_has_no_flow_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_app(tmp_path, with_flow=False)

    monkeypatch.setattr("factory.chain.scheduled_tasks.route", lambda _persona: "fake-model")
    monkeypatch.setattr(
        "factory.context.loader.compose_context_prelude",
        lambda *_args, **_kwargs: "PRELUDE",
    )
    monkeypatch.setattr(
        "factory.runner.text_run",
        lambda *_args, **_kwargs: pytest.fail("text_run should not execute without flow.md"),
    )

    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=False)

    assert out.status == "rejected"
    assert out.findings_count == 0
    assert out.error == "ux_auditor_no_flow_artifacts"


def test_file_finding_creates_flow_md_for_ux_finding(tmp_path: Path) -> None:
    root = _write_app(tmp_path, with_flow=False)

    finding = {
        "flow": "checkout-flow.md",
        "step": 2,
        "kind": "friction",
        "evidence": "Too many confirmation clicks",
        "suggestion": "Collapse to one confirmation",
        "suggested_direction": {
            "title": "simplify checkout confirmation",
            "type": "ux",
            "why": "Checkout requires redundant confirmations.",
            "acceptance": ["Checkout completes in <= 2 clicks after selecting plan"],
        },
    }

    direction = _file_finding_as_direction(
        persona="ux_auditor",
        app="sacrifice",
        finding=finding,
        software_factory_root=root,
        dry_run=False,
    )

    assert direction is not None
    flow_md = direction.dir_path / "flow.md"
    assert flow_md.exists()
    flow_text = flow_md.read_text(encoding="utf-8")
    assert "Flow: checkout-flow.md" in flow_text
    assert "Step: 2" in flow_text


def test_live_run_is_not_blocked_when_flow_md_is_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """UX auditor live run proceeds normally when flow.md artifacts exist."""
    root = _write_app(tmp_path, with_flow=True)

    monkeypatch.setattr("factory.chain.scheduled_tasks.route", lambda _persona: "fake-model")
    monkeypatch.setattr(
        "factory.context.loader.compose_context_prelude",
        lambda *_args, **_kwargs: "PRELUDE",
    )
    monkeypatch.setattr(
        "factory.runner.text_run",
        lambda *_args, **_kwargs: {"findings": [], "duration_s": 0.1},
    )

    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=False)

    assert out.status == "ok"
    assert out.findings_count == 0


def test_dry_run_does_not_require_flow_md_artifacts(tmp_path: Path) -> None:
    """Dry-run uses fixtures and should not be gated on flow.md availability."""
    root = _write_app(tmp_path, with_flow=False)

    out = run_scheduled_persona("ux_auditor", "sacrifice", root, dry_run=True)

    assert out.status == "dry_run"
    assert out.findings_count == 1


# --------------------------------------------------------------------------- #
# tests-meaningful finding artifact fixture (D017 narrow-read)
# --------------------------------------------------------------------------- #


def test_tests_meaningful_fixture_exposes_rule_id() -> None:
    """AC1.1: the reproducible fixture SHALL show rule id."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    assert finding.kind == "direct_db_bootstrap"


def test_tests_meaningful_fixture_exposes_file() -> None:
    """AC1.2: the reproducible fixture SHALL show file."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    assert finding.path == "tests/test_example.py"


def test_tests_meaningful_fixture_exposes_line() -> None:
    """AC1.3: the reproducible fixture SHALL show line."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    assert finding.line == 3


def test_tests_meaningful_fixture_exposes_remediation_text() -> None:
    """AC1.4: the reproducible fixture SHALL show remediation text."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    assert "factory.observability.schema.migrate" in finding.why_slop
    assert len(finding.why_slop) > 50, "remediation text must be substantive"


def test_tests_meaningful_fixture_is_reproducible() -> None:
    """The fixture returns identical values across repeated calls."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    a = make_tests_meaningful_fixture_finding()
    b = make_tests_meaningful_fixture_finding()
    assert a.as_dict() == b.as_dict()


def test_tests_meaningful_fixture_field_set_is_complete() -> None:
    """The artifact SHALL contain all four required fields and nothing less."""
    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    d = finding.as_dict()
    required_fields = {"path", "line", "kind", "why_slop"}
    assert required_fields <= d.keys(), f"missing required fields: {required_fields - d.keys()}"


def test_tests_meaningful_fixture_dict_is_json_serializable() -> None:
    """The artifact dict form must be suitable for serialization to the UX audit input."""
    import json

    from factory.chain.slop_detector import make_tests_meaningful_fixture_finding

    finding = make_tests_meaningful_fixture_finding()
    d = finding.as_dict()
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    # Round-trip: deserialized values match the original dict
    rt = json.loads(serialized)
    assert rt == d
