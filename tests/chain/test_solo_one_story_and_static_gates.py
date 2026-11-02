"""Solo fixes found by the first live E2E job (template-probe:005, 2026-11-02).

1. A solo job is ONE story / ONE PR: PM's slicing and the dual-draft branch are
   both collapsed (the job was split into 4 stacked draft PRs).
2. The solo in-conversation gate runs the app's own lint / format / type
   commands, blocking only on checks that were green on the base commit (all 4
   PRs failed CI ``format:check`` because only the test command ran).
3. ``factory job status`` reports each open PR's CI, so "delivered" is never
   read as "delivered and green".
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from factory import runner as runner_module
from factory.app_config import AppConfig, AppGatesConfig
from factory.chain import solo
from factory.chain.handlers import handle_stories_spawned
from factory.directions.parser import Direction
from factory.jobs.github import summarize_checks


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    import factory.chain.handlers as handlers_mod

    monkeypatch.setattr(handlers_mod, "_author_acceptance_oracle", lambda *a, **k: None)


def _direction(*, pipeline: str | None, explore: bool = False) -> Direction:
    fm: dict[str, Any] = {"title": "Report build version", "explore": explore}
    if pipeline:
        fm["pipeline"] = pipeline
    return Direction(
        id="905",
        slug="report-build-version",
        title="Report build version",
        type_tag=None,
        why="ops",
        has_flow=False,
        has_api_spec=False,
        acceptance=[],
        explore_tag=explore,
        artifacts_paths=[],
        app="probe",
        status="pm-validated",
        raw_frontmatter=fm,
        raw_body="# Report build version",
        dir_path=Path("."),
        state={"tracker_issue": 1},
    )


def _child(title: str, scope: str = "backend", points: int = 2, **est: int) -> dict[str, Any]:
    return {
        "title": title,
        "scope": scope,
        "chain_kind": "tdd",
        "points": points,
        "rationale": f"why {title}",
        **est,
    }


_FOUR = [
    _child("env schema", points=2, estimated_modified_files=2),
    _child("health.live", points=3, estimated_modified_files=2),
    _child("GET route", points=2, estimated_modified_files=1),
    _child("tests", scope="test", points=2),  # no estimates on this one
]


def _cfg() -> AppConfig:
    return AppConfig(name="probe", repo="o/probe", gates=AppGatesConfig())


def _root(tmp_path: Path) -> Path:
    (tmp_path / "state").mkdir(exist_ok=True)
    return tmp_path


def test_solo_job_spawns_exactly_one_story(tmp_path: Path) -> None:
    stories = handle_stories_spawned(
        direction=_direction(pipeline="solo"),
        pm_result={"child_stories": list(_FOUR), "confidence": 0.9},
        app_config=_cfg(),
        software_factory_root=_root(tmp_path),
        dry_run=True,
    )
    assert len(stories) == 1
    s = stories[0]
    assert s.title == "Report build version"
    assert s.pipeline == "solo"
    assert s.chain_kind == "tdd"
    assert s.scope == "backend"  # modal impl scope; "test" never wins
    assert s.points == 13  # 2+3+2+2=9 → next Fibonacci


def test_solo_job_skips_dual_draft(tmp_path: Path) -> None:
    stories = handle_stories_spawned(
        direction=_direction(pipeline="solo", explore=True),
        pm_result={"child_stories": list(_FOUR), "confidence": 0.3},
        app_config=_cfg(),
        software_factory_root=_root(tmp_path),
        dry_run=True,
    )
    assert len(stories) == 1 and stories[0].pipeline == "solo"
    assert "alt-" not in (stories[0].github_branch or "") + stories[0].slug


def test_chain_job_keeps_its_split(tmp_path: Path) -> None:
    stories = handle_stories_spawned(
        direction=_direction(pipeline=None),
        pm_result={"child_stories": list(_FOUR), "confidence": 0.9},
        app_config=_cfg(),
        software_factory_root=_root(tmp_path),
        dry_run=True,
    )
    assert len(stories) == 4


# --------------------------------------------------------------------------- #
# Static gates in the solo conversation
# --------------------------------------------------------------------------- #


def _gate(
    monkeypatch: pytest.MonkeyPatch,
    results: dict[str, bool],
    baseline: dict[str, bool | None],
) -> Any:
    def fake(repo: Path, test_command: str | None = None) -> tuple[bool, str]:
        return results.get(str(test_command), True), f"out of {test_command}"

    monkeypatch.setattr(runner_module, "_run_pytest", fake)
    check = solo.make_gate_check(
        repo_path=Path("."),
        test_command="npm test",
        branch_is_empty=lambda: False,
        static_gates=[("lint", "npm run lint"), ("format_check", "npm run fmt")],
        static_baseline=baseline,
    )
    return check()


def test_static_gate_green_on_base_red_now_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    v = _gate(monkeypatch, {"npm run fmt": False}, {"lint": True, "format_check": True})
    assert not v.passed
    assert "format_check" in v.reason and "npm run fmt" in v.reason
    assert v.output == "out of npm run fmt"  # the formatter's own output reaches the dev
    assert [c["name"] for c in v.checks][-1] == "format_check"


def test_static_gate_already_red_on_base_does_not_block(monkeypatch: pytest.MonkeyPatch) -> None:
    v = _gate(monkeypatch, {"npm run fmt": False}, {"lint": True, "format_check": False})
    assert v.passed
    fmt = [c for c in v.checks if c["name"] == "format_check"][0]
    assert fmt["passed"] and "already red" in fmt["reason"]


def test_static_gate_unknown_baseline_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    v = _gate(monkeypatch, {"npm run lint": False}, {"lint": None, "format_check": True})
    assert not v.passed and "lint" in v.reason


def test_static_gates_all_green_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    v = _gate(monkeypatch, {}, {"lint": True, "format_check": True})
    assert v.passed
    assert [c["name"] for c in v.checks] == [
        "test_command",
        "non_empty_change",
        "lint",
        "format_check",
    ]


def test_static_gate_commands_reads_config() -> None:
    cfg = AppConfig(
        name="p",
        repo="o/p",
        gates=AppGatesConfig(lint_command="L", format_check_command="", type_check_command="T"),
    )
    assert solo.static_gate_commands(cfg) == [("lint", "L"), ("type_check", "T")]
    plan = solo.checks_plan(cfg, None)
    assert plan["in_conversation_checks"][-2:] == ["lint", "type_check"]


def _git(cwd: Path, *a: str) -> str:
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def test_static_baseline_runs_on_the_base_commit_not_the_tree(tmp_path: Path) -> None:
    origin = tmp_path / "o.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    wt = tmp_path / "wt"
    _git(tmp_path, "clone", str(origin), str(wt))
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    (wt / "ok.txt").write_text("clean\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "base")
    _git(wt, "push", "origin", "main")
    _git(wt, "checkout", "-b", "feat")
    (wt / "ok.txt").write_text("dirty\n")  # the dev's uncommitted change
    gates = [("format_check", "grep -q clean ok.txt"), ("lint", "false")]
    base = solo.static_gate_baseline(wt, "main", gates)
    assert base == {"format_check": True, "lint": False}
    # The dev's tree is untouched and no temp worktree is left behind.
    assert (wt / "ok.txt").read_text() == "dirty\n"
    assert _git(wt, "worktree", "list").count("\n") == 1


def test_static_baseline_unknown_without_merge_base(tmp_path: Path) -> None:
    (tmp_path / "r").mkdir()
    _git(tmp_path / "r", "init", "-q")
    assert solo.static_gate_baseline(tmp_path / "r", "main", [("lint", "true")]) == {"lint": None}


# --------------------------------------------------------------------------- #
# CI rollup for job status
# --------------------------------------------------------------------------- #


def test_summarize_checks_states() -> None:
    run = lambda n, st, c: {"__typename": "CheckRun", "name": n, "status": st, "conclusion": c}  # noqa: E731
    ctx = lambda n, s: {"__typename": "StatusContext", "context": n, "state": s}  # noqa: E731
    assert summarize_checks([])["state"] == "none"
    assert (
        summarize_checks([run("a", "COMPLETED", "SUCCESS"), ctx("b", "SUCCESS")])["state"]
        == "passing"
    )
    p = summarize_checks([run("a", "IN_PROGRESS", ""), ctx("b", "SUCCESS")])
    assert p["state"] == "pending" and p["pending"] == ["a"]
    f = summarize_checks([run("lint", "COMPLETED", "FAILURE"), run("x", "IN_PROGRESS", "")])
    assert f["state"] == "failing" and f["failing"] == ["lint"]
    assert summarize_checks([ctx("c", "ERROR")])["state"] == "failing"
    assert summarize_checks([run("s", "COMPLETED", "SKIPPED")])["state"] == "passing"


def test_static_baseline_invocation_failure_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    origin = tmp_path / "o.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    wt = tmp_path / "wt"
    _git(tmp_path, "clone", str(origin), str(wt))
    _git(wt, "config", "user.email", "t@t")
    _git(wt, "config", "user.name", "t")
    (wt / "a").write_text("a\n")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-m", "base")
    _git(wt, "push", "origin", "main")
    monkeypatch.setattr(
        runner_module,
        "_run_pytest",
        lambda repo, test_command=None: (False, "test_command invocation failed: timeout"),
    )
    assert solo.static_gate_baseline(wt, "main", [("lint", "x")]) == {"lint": None}
