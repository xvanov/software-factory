"""The production ``solo`` pipeline (``factory/chain/solo.py``).

Pinned here, all without a model call (the OpenHands SDK and ``sandbox_run``
are faked):

* spawn stamping — the mode is read once at spawn and lives on the row;
* state machine — ONE new edge (TESTS_GREEN → tech_writer), no new state,
  solo-only dispatch, and a chain story can never take the edge;
* retry cap — solo stops at 3 dev conversations, chain is untouched, and the
  early stall guard stays reachable;
* gate feedback — a red gate's REASON is sent back into the SAME conversation,
  and becomes the attempt's error (no more "tests not green after run");
* no-progress aborts (first write, between rounds) and the soft wall clock that
  still grades the tree;
* usage — a multi-round run books its spend;
* delivery handoff — a green solo story flows into the shared tech_writer →
  docs_enforcer path (the PR-open / delivery-level site), not a private merge;
* the oracle leak check — a blocking precondition only when the app enables
  the oracle, fail-safe when it cannot run.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import time
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, select

from factory import runner as runner_module
from factory.app_config import AppConfig, AppGatesConfig
from factory.chain import handlers as handlers_module
from factory.chain import orchestrator as orch
from factory.chain import solo
from factory.chain.event_log import read_story_events
from factory.chain.handlers import (
    _MAX_DEV_SAME_SIGNATURE,
    _dev_retry_cap,
    _max_dev_retries,
    get_story,
    handle_dev,
    handle_tech_writer,
    persist_story,
)
from factory.chain.state_machine import (
    EVENT_REVIEWER_STARTED,
    EVENT_TECH_WRITER_STARTED,
    IllegalTransitionError,
    StoryRecord,
    StoryState,
    advance,
    is_terminal,
)
from factory.runner import GateVerdict, LLMConfig, Run, RunResult, _engine, sandbox_run

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "--initial-branch=main")
    _git(path, "config", "user.email", "t@e.x")
    _git(path, "config", "user.name", "T E")
    (path / "README.md").write_text("# init\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture
def temp_root(tmp_path: Path) -> Path:
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "apps" / "sacrifice" / "stories").mkdir(parents=True, exist_ok=True)
    (tmp_path / "apps" / "sacrifice" / "stories" / "1-x.md").write_text(
        "# story\n", encoding="utf-8"
    )
    _init_repo(tmp_path / "sacrifice")
    return tmp_path


def _app(root: Path, **gates: Any) -> AppConfig:
    return AppConfig(
        name="sacrifice",
        repo="x/y",
        default_branch="main",
        app_repo_path=str(root / "sacrifice"),
        gates=AppGatesConfig(**gates),
    )


def _story_at(state: StoryState, root: Path, **kw: Any) -> StoryRecord:
    fields: dict[str, Any] = {
        "id": None,
        "direction_id": "099",
        "app": "sacrifice",
        "title": "t",
        "slug": "z",
        "scope": "backend",
        "state": state.value,
        "github_issue_number": 1,
        "story_file_path": "stories/1-x.md",
        "pipeline": "solo",
    }
    fields.update(kw)
    return persist_story(StoryRecord(**fields), root / "state" / "factory.db")


def _events(story: StoryRecord, root: Path, name: str) -> list[dict[str, Any]]:
    assert story.id is not None
    return [
        e
        for e in read_story_events(story.id, software_factory_root=root, slug_hint=story.slug)
        if e.get("event") == name
    ]


# --------------------------------------------------------------------------- #
# Mode: read once, stamped on the row
# --------------------------------------------------------------------------- #


def test_is_solo_reads_only_the_row_stamp() -> None:
    assert solo.is_solo(
        StoryRecord(direction_id="1", app="a", title="t", slug="s", pipeline="solo")
    )
    assert not solo.is_solo(StoryRecord(direction_id="1", app="a", title="t", slug="s"))
    # A docs-chain story has no dev/review loop: pipeline is meaningless there.
    assert not solo.is_solo(
        StoryRecord(
            direction_id="1", app="a", title="t", slug="s", pipeline="solo", chain_kind="docs"
        )
    )


def test_spawn_stamps_solo_from_the_app_default(tmp_path: Path) -> None:
    from factory.chain.handlers import handle_stories_spawned
    from factory.directions.parser import Direction

    (tmp_path / "state").mkdir()
    direction = Direction(
        id="901",
        slug="route-me",
        title="Route me",
        type_tag=None,
        why="because",
        has_flow=False,
        has_api_spec=False,
        acceptance=[],
        explore_tag=False,
        artifacts_paths=[],
        app="sacrifice",
        status="pm-validated",
        raw_frontmatter={"title": "Route me"},
        raw_body="# Route me",
        dir_path=Path("."),
        state={"tracker_issue": 1},
    )
    cfg = AppConfig(name="sacrifice", repo="x/y", pipeline_default="solo")
    stories = handle_stories_spawned(
        direction=direction,
        pm_result={
            "child_stories": [{"title": "do it", "scope": "backend", "points": 2}],
            "confidence": 0.9,
        },
        app_config=cfg,
        software_factory_root=tmp_path,
        dry_run=True,
    )
    assert [s.pipeline for s in stories] == ["solo"]


# --------------------------------------------------------------------------- #
# State machine + dispatch
# --------------------------------------------------------------------------- #


def test_one_new_edge_and_no_new_state() -> None:
    s = StoryRecord(
        direction_id="1", app="a", title="t", slug="s", state=StoryState.TESTS_GREEN.value
    )
    assert advance(s, EVENT_TECH_WRITER_STARTED) is StoryState.TECH_WRITER_IN_PROGRESS
    # The chain edge is untouched.
    assert advance(s, EVENT_REVIEWER_STARTED) is StoryState.REVIEWER_IN_PROGRESS
    assert not is_terminal(StoryState.TESTS_GREEN)
    assert {st.value for st in StoryState} >= {"tests_green", "tech_writer_in_progress"}
    assert "solo" not in {st.value for st in StoryState}


def test_dispatch_routes_tests_green_by_pipeline() -> None:
    chain = StoryRecord(
        direction_id="1", app="a", title="t", slug="s", state=StoryState.TESTS_GREEN.value
    )
    solo_s = StoryRecord(
        direction_id="1",
        app="a",
        title="t",
        slug="s",
        state=StoryState.TESTS_GREEN.value,
        pipeline="solo",
    )
    assert orch._dispatch_for_story(chain) == "review"
    assert orch._dispatch_for_story(solo_s) == "tech_writer"
    # Every other state dispatches identically for both pipelines.
    for st in orch._DISPATCH:
        if st is StoryState.TESTS_GREEN:
            continue
        a = StoryRecord(direction_id="1", app="a", title="t", slug="s", state=st.value)
        b = StoryRecord(
            direction_id="1", app="a", title="t", slug="s", state=st.value, pipeline="solo"
        )
        assert orch._dispatch_for_story(a) == orch._dispatch_for_story(b), st


def test_tech_writer_refuses_tests_green_for_a_chain_story(temp_root: Path) -> None:
    story = _story_at(StoryState.TESTS_GREEN, temp_root, pipeline="chain")
    with pytest.raises(IllegalTransitionError):
        handle_tech_writer(
            story,
            _app(temp_root),
            temp_root,
            dry_run=True,
            db_path=temp_root / "state" / "factory.db",
        )
    assert get_story(story.id or 0, temp_root / "state" / "factory.db").state == "tests_green"


def test_green_solo_story_hands_off_to_the_shared_delivery_path(temp_root: Path) -> None:
    """TESTS_GREEN → tech_writer → TECH_WRITER_DONE → docs_enforcer: the same
    PR-open / delivery-level site (``handle_docs_enforcer``) the chain uses."""
    db = temp_root / "state" / "factory.db"
    story = _story_at(StoryState.TESTS_GREEN, temp_root)
    assert orch._dispatch_for_story(story) == "tech_writer"
    res = handle_tech_writer(story, _app(temp_root), temp_root, dry_run=True, db_path=db)
    assert res.next_state is StoryState.TECH_WRITER_DONE
    after = get_story(story.id or 0, db)
    assert after is not None
    assert orch._dispatch_for_story(after) == "docs_enforcer"
    # Never reached a reviewer state on the way.
    assert after.reviewer_cycles == 0


def test_stale_solo_tech_writer_rolls_back_to_tests_green(temp_root: Path) -> None:
    db = temp_root / "state" / "factory.db"
    old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    s_solo = _story_at(StoryState.TECH_WRITER_IN_PROGRESS, temp_root, slug="a", updated_at=old)
    s_chain = _story_at(
        StoryState.TECH_WRITER_IN_PROGRESS, temp_root, slug="b", pipeline="chain", updated_at=old
    )
    # persist_story stamps updated_at=now; force it back.
    for s in (s_solo, s_chain):
        with Session(_engine(db)) as session:
            row = session.get(StoryRecord, s.id)
            assert row is not None
            row.updated_at = old
            session.add(row)
            session.commit()
    orch._prune_stale_in_progress(db, "sacrifice", settings=None, root=temp_root)
    assert get_story(s_solo.id or 0, db).state == "tests_green"  # type: ignore[union-attr]
    assert get_story(s_chain.id or 0, db).state == "reviewer_done"  # type: ignore[union-attr]


# --------------------------------------------------------------------------- #
# Retry cap
# --------------------------------------------------------------------------- #


def test_solo_cap_is_three_and_keeps_the_stall_guard_reachable(temp_root: Path) -> None:
    assert solo.SOLO_MAX_DEV_ATTEMPTS <= 3
    assert solo.SOLO_MAX_GATE_ROUNDS <= 3
    assert solo.SOLO_MAX_DEV_ATTEMPTS > _MAX_DEV_SAME_SIGNATURE
    s = _story_at(StoryState.SM_DONE, temp_root)
    c = _story_at(StoryState.SM_DONE, temp_root, pipeline="chain", slug="c")
    assert _dev_retry_cap(s, temp_root) == min(3, _max_dev_retries(temp_root))
    assert _dev_retry_cap(c, temp_root) == _max_dev_retries(temp_root)


def test_solo_exhausts_after_three_red_conversations(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = temp_root / "state" / "factory.db"
    story = _story_at(StoryState.SM_DONE, temp_root)
    calls: list[dict[str, Any]] = []

    async def _red(*args: Any, **kwargs: Any) -> RunResult:
        calls.append(kwargs)
        n = len(calls)
        # Distinct, test-result-free tails so the same-signature guard stays out
        # of the way: this pins the HARD cap.
        return RunResult(
            success=False,
            files_changed=["src/x.py"],
            test_run_passed=False,
            summary=f"collection error variant {n}",
            error=f"gate red #{n}",
            cost_usd=0.5,
            tokens_out=10,
            gate_rounds=[{"round": 1, "passed": False}],
            gate_stop_reason="rounds_exhausted",
        )

    monkeypatch.setattr(runner_module, "sandbox_run", _red, raising=True)
    monkeypatch.setattr(handlers_module, "route", lambda *a, **kw: "azure/gpt-5.4")
    monkeypatch.setattr(handlers_module, "_post_factory_needs_redesign_comment", lambda **kw: None)
    app = _app(temp_root)
    for _ in range(5):
        cur = get_story(story.id or 0, db)
        assert cur is not None
        if orch._dispatch_for_story(cur) != "dev":
            break
        handle_dev(cur, app, temp_root, dry_run=False, db_path=db)
    final = get_story(story.id or 0, db)
    assert final is not None
    assert final.state == StoryState.BLOCKED_TESTS_NEED_CLARIFICATION.value
    assert len(calls) == 3 == final.dev_retries
    # The gate's REAL reason reached the attempt record (gates_speak lesson).
    attempts = json.loads(final.dev_attempts_json or "[]")
    assert [a["summary"] for a in attempts] == ["gate red #1", "gate red #2", "gate red #3"]


# --------------------------------------------------------------------------- #
# Handler: what a solo dispatch passes, logs and records
# --------------------------------------------------------------------------- #


def test_solo_dispatch_uses_long_horizon_gate_loop_and_brief(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = temp_root / "state" / "factory.db"
    story = _story_at(
        StoryState.SM_DONE,
        temp_root,
        reviewer_result_json=json.dumps({"findings": [{"what": "ci red"}]}),
    )
    seen: dict[str, Any] = {}

    async def _green(*args: Any, **kwargs: Any) -> RunResult:
        seen.update(kwargs)
        return RunResult(
            success=True,
            files_changed=["src/x.py"],
            test_run_passed=True,
            summary="3 passed",
            cost_usd=1.25,
            tokens_out=100,
            gate_rounds=[
                {"round": 1, "passed": False, "reason": "red"},
                {"round": 2, "passed": True, "reason": "green"},
            ],
            gate_stop_reason="green",
        )

    monkeypatch.setattr(runner_module, "sandbox_run", _green, raising=True)
    monkeypatch.setattr(handlers_module, "route", lambda *a, **kw: "azure/gpt-5.4")

    handle_dev(story, _app(temp_root), temp_root, dry_run=False, db_path=db)

    assert seen["wall_clock_timeout_s"] == solo.SOLO_DEV_WALL_CLOCK_S == 5400
    assert seen["max_gate_rounds"] == solo.SOLO_MAX_GATE_ROUNDS
    assert seen["no_progress_abort_s"] == solo.SOLO_NO_PROGRESS_ABORT_S
    assert callable(seen["gate_check"])
    assert "Find and reuse existing code first" in seen["brief_addendum"]
    assert "Write or extend tests" in seen["brief_addendum"]
    # The CI-fix finding that brought dev back still rides the same channel.
    assert seen["reviewer_findings"]["findings"][0]["what"] == "ci red"

    after = get_story(story.id or 0, db)
    assert after is not None
    assert after.state == StoryState.TESTS_GREEN.value
    assert orch._dispatch_for_story(after) == "tech_writer"
    assert after.reviewer_result_json is None  # consumed; nothing will overwrite it

    plan = _events(after, temp_root, "solo_checks")
    assert len(plan) == 1
    p = plan[0]
    assert p["reviewer"].startswith("skipped")
    assert p["in_conversation_checks"] == ["test_command", "non_empty_change"]
    assert "disabled" in p["acceptance_oracle"]
    assert p["oracle_leak_precheck"].startswith("not applicable")
    assert "tests-green" in p["merge_gates_required"]
    rounds = _events(after, temp_root, "solo_dev_rounds")
    assert rounds and rounds[0]["stop_reason"] == "green" and len(rounds[0]["rounds"]) == 2


def test_chain_dispatch_is_unchanged(temp_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = temp_root / "state" / "factory.db"
    story = _story_at(StoryState.SM_DONE, temp_root, pipeline="chain")
    seen: dict[str, Any] = {}

    async def _green(*args: Any, **kwargs: Any) -> RunResult:
        seen.update(kwargs)
        return RunResult(success=True, files_changed=["a"], test_run_passed=True, summary="ok")

    monkeypatch.setattr(runner_module, "sandbox_run", _green, raising=True)
    monkeypatch.setattr(handlers_module, "route", lambda *a, **kw: "azure/gpt-5.4")
    handle_dev(story, _app(temp_root), temp_root, dry_run=False, db_path=db)
    for k in ("gate_check", "max_gate_rounds", "no_progress_abort_s", "brief_addendum"):
        assert k not in seen
    assert seen["wall_clock_timeout_s"] == 1800
    after = get_story(story.id or 0, db)
    assert after is not None and orch._dispatch_for_story(after) == "review"
    assert not _events(after, temp_root, "solo_checks")


def test_oracle_leak_blocks_solo_dispatch_without_spending(
    temp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = temp_root / "state" / "factory.db"
    story = _story_at(StoryState.SM_DONE, temp_root)
    import factory.chain.acceptance as acc

    monkeypatch.setattr(acc, "sweep_leaked_oracles", lambda tree: [])
    monkeypatch.setattr(acc, "unremovable_oracle_leaks", lambda tree: ["tests/test_oracle_x.py"])

    async def _boom(*a: Any, **k: Any) -> RunResult:
        raise AssertionError("sandbox must not run when the oracle leaked")

    monkeypatch.setattr(runner_module, "sandbox_run", _boom, raising=True)
    monkeypatch.setattr(handlers_module, "route", lambda *a, **kw: "azure/gpt-5.4")
    handle_dev(story, _app(temp_root, acceptance_oracle=True), temp_root, dry_run=False, db_path=db)
    after = get_story(story.id or 0, db)
    assert after is not None
    assert after.state == StoryState.BLOCKED_TESTS_NEED_CLARIFICATION.value
    assert after.dev_retries == 0
    assert "acceptance-oracle copy" in (after.error or "")
    assert _events(after, temp_root, "solo_oracle_leak_blocked")
    assert "required merge gate" in _events(after, temp_root, "solo_checks")[0]["acceptance_oracle"]


def test_leak_check_fails_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import factory.chain.acceptance as acc

    def _raise(tree: Path) -> list[str]:
        raise OSError("disk gone")

    monkeypatch.setattr(acc, "sweep_leaked_oracles", _raise)
    cfg = AppConfig(name="a", repo="x/y", gates=AppGatesConfig(acceptance_oracle=True))
    leaks = solo.oracle_leak_precheck(cfg, tmp_path)
    assert leaks and "leak check failed" in leaks[0]
    assert solo.oracle_leak_precheck(AppConfig(name="a", repo="x/y"), tmp_path) is None


# --------------------------------------------------------------------------- #
# The gate check itself
# --------------------------------------------------------------------------- #


def _gate(
    monkeypatch: pytest.MonkeyPatch, *, tests: bool, empty: Any, delta: Any = "skip"
) -> GateVerdict:
    monkeypatch.setattr(
        runner_module,
        "_run_pytest",
        lambda repo, test_command=None: (tests, "1 passed" if tests else "1 failed"),
    )
    check = solo.make_gate_check(
        repo_path=Path("."),
        test_command="pytest -q",
        branch_is_empty=lambda: empty,
        production_delta=None if delta == "skip" else (lambda: delta),
    )
    return check()


def test_gate_check_order_and_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    red = _gate(monkeypatch, tests=False, empty=False)
    assert not red.passed and "pytest -q" in red.reason and red.output == "1 failed"
    assert [c["name"] for c in red.checks] == ["test_command"]

    empty = _gate(monkeypatch, tests=True, empty=True)
    assert not empty.passed and "NO change" in empty.reason

    unknown = _gate(monkeypatch, tests=True, empty=None)
    assert unknown.passed  # fail open on unknown, like the chain's own check

    tests_only = _gate(monkeypatch, tests=True, empty=False, delta=False)
    assert not tests_only.passed and "ONLY test files" in tests_only.reason

    ok = _gate(monkeypatch, tests=True, empty=False, delta=True)
    assert ok.passed
    assert [c["name"] for c in ok.checks] == [
        "test_command",
        "non_empty_change",
        "production_delta",
    ]


# --------------------------------------------------------------------------- #
# sandbox_run's in-conversation loop (fake SDK, real git repo)
# --------------------------------------------------------------------------- #


class _Conv:
    """A fake OpenHands conversation. ``script[i]`` runs on the i-th ``run()``."""

    instances: list[_Conv] = []
    script: list[Any] = []

    def __init__(self, **kwargs: Any) -> None:
        self.messages: list[str] = []
        self.runs = 0
        self.paused = threading.Event()
        _Conv.instances.append(self)

    def send_message(self, msg: Any, *_: Any, **__: Any) -> None:
        self.messages.append(str(msg))

    def run(self) -> None:
        step = _Conv.script[min(self.runs, len(_Conv.script) - 1)]
        self.runs += 1
        step(self)

    def pause(self) -> None:
        self.paused.set()

    def close(self) -> None:
        pass

    @property
    def state(self) -> Any:
        return types.SimpleNamespace(events=[])

    @property
    def conversation_stats(self) -> Any:
        runs = self.runs

        class _S:
            def get_combined_metrics(self) -> Any:
                return types.SimpleNamespace(
                    accumulated_token_usage=types.SimpleNamespace(
                        prompt_tokens=1000 * runs,
                        completion_tokens=100 * runs,
                        cache_read_tokens=0,
                    ),
                    accumulated_cost=0.5 * runs,
                )

        return _S()


@pytest.fixture
def fake_sdk(monkeypatch: pytest.MonkeyPatch) -> type[_Conv]:
    _Conv.instances = []
    _Conv.script = []
    sdk = types.ModuleType("openhands.sdk")
    sdk.LLM = type("_L", (), {"__init__": lambda self, **kw: None})  # type: ignore[attr-defined]
    sdk.Conversation = _Conv  # type: ignore[attr-defined]
    sdk.LocalWorkspace = type(  # type: ignore[attr-defined]
        "_W", (), {"__init__": lambda self, **kw: None}
    )
    monkeypatch.setitem(sys.modules, "openhands.sdk", sdk)
    tools = types.ModuleType("openhands.tools.preset.default")
    tools.get_default_agent = lambda **_: object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openhands.tools.preset.default", tools)
    pyd = types.ModuleType("pydantic")
    pyd.SecretStr = lambda s: s  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pydantic", pyd)
    monkeypatch.setenv("AZURE_API_KEY", "k")
    # A dev run never ends on prose in these fakes.
    monkeypatch.setattr(runner_module, "_ended_on_prose", lambda conv, persona: False)
    monkeypatch.setattr(
        runner_module, "_extract_conversation_memory", lambda conv: ("SELF_SUMMARY: done", [], "")
    )
    monkeypatch.setattr(runner_module, "_WATCHDOG_POLL_S", 0.02)
    return _Conv


def _write(name: str) -> Any:
    def _step(conv: _Conv) -> None:
        p = _REPO["path"] / name
        p.write_text(f"{p.read_text() if p.exists() else ''}x{conv.runs}\n", encoding="utf-8")

    return _step


def _idle(conv: _Conv) -> None:
    return None


def _block_until_paused(conv: _Conv) -> None:
    conv.paused.wait(timeout=10)


_REPO: dict[str, Path] = {}


def _sandbox(tmp_path: Path, gate: Any, **kw: Any) -> RunResult:
    repo = _init_repo(tmp_path / "repo")
    _REPO["path"] = repo
    story = tmp_path / "story.md"
    story.write_text("# story\n", encoding="utf-8")
    return asyncio.run(
        sandbox_run(
            persona="dev",
            story_path=story,
            repo_path=repo,
            llm_config=LLMConfig(model="azure/deepseek-v4-pro", api_key="x"),
            dry_run=False,
            db_path=tmp_path / "state" / "factory.db",
            gate_check=gate,
            **kw,
        )
    )


def _seq(*verdicts: GateVerdict) -> Any:
    it = iter(verdicts)
    last: dict[str, GateVerdict] = {}

    def _check() -> GateVerdict:
        try:
            last["v"] = next(it)
        except StopIteration:
            pass
        return last["v"]

    return _check


RED = GateVerdict(
    passed=False,
    reason="the test command is not green: test_foo failed",
    output="FAILED tests/test_foo.py::test_foo - AssertionError\n1 failed",
    checks=[{"name": "test_command", "passed": False, "reason": "exit 1"}],
)
GREEN = GateVerdict(passed=True, reason="all green", output="2 passed")


def test_gate_reason_is_fed_back_into_the_same_conversation(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    fake_sdk.script = [_write("a.py"), _write("a.py")]
    res = _sandbox(tmp_path, _seq(RED, GREEN), max_gate_rounds=3, brief_addendum="# SOLO BRIEF")
    assert len(fake_sdk.instances) == 1, "one continuous conversation"
    conv = fake_sdk.instances[0]
    assert len(conv.messages) == 2 and conv.runs == 2
    assert "# SOLO BRIEF" in conv.messages[0]
    fb = conv.messages[1]
    assert "round 1/3" in fb and RED.reason in fb and "AssertionError" in fb
    assert "[FAIL] test_command" in fb
    assert res.test_run_passed is True and res.error is None
    assert res.gate_stop_reason == "green" and len(res.gate_rounds) == 2


def test_red_after_all_rounds_reports_the_gate_reason_and_books_spend(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    fake_sdk.script = [_write("a.py"), _write("b.py"), _write("c.py")]
    res = _sandbox(tmp_path, _seq(RED), max_gate_rounds=3)
    conv = fake_sdk.instances[0]
    assert conv.runs == 3 and len(conv.messages) == 3
    assert res.test_run_passed is False
    assert res.error == RED.reason  # not "tests not green after run"
    assert res.gate_stop_reason == "rounds_exhausted"
    assert [r["round"] for r in res.gate_rounds] == [1, 2, 3]
    # Spend across all three rounds is booked on ONE runs row.
    with Session(_engine(tmp_path / "state" / "factory.db")) as s:
        rows = list(s.exec(select(Run)).all())
    assert len(rows) == 1 and rows[0].cost_usd == pytest.approx(1.5)
    assert rows[0].error == RED.reason
    assert res.cost_usd == pytest.approx(1.5)


def test_a_round_that_changes_nothing_ends_the_conversation(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    fake_sdk.script = [_write("a.py"), _idle, _idle]
    res = _sandbox(tmp_path, _seq(RED), max_gate_rounds=3)
    assert fake_sdk.instances[0].runs == 2
    assert res.gate_stop_reason == "no_progress_between_rounds"
    assert len(res.gate_rounds) == 2 and res.test_run_passed is False


def test_no_first_write_watchdog_pauses_and_still_grades(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    fake_sdk.script = [_block_until_paused]
    t0 = time.monotonic()
    res = _sandbox(tmp_path, _seq(RED), max_gate_rounds=3, no_progress_abort_s=1)
    assert time.monotonic() - t0 < 8
    assert fake_sdk.instances[0].paused.is_set()
    assert res.gate_stop_reason == "no_progress_first_write"
    assert len(res.gate_rounds) == 1 and res.test_run_passed is False
    assert res.premodel_infra is False  # a graded attempt, not a free infra bounce


def test_a_write_defuses_the_no_first_write_watchdog(tmp_path: Path, fake_sdk: type[_Conv]) -> None:
    def _write_then_wait(conv: _Conv) -> None:
        _write("a.py")(conv)
        conv.paused.wait(timeout=1.5)

    fake_sdk.script = [_write_then_wait]
    res = _sandbox(tmp_path, _seq(GREEN), max_gate_rounds=3, no_progress_abort_s=1)
    assert not fake_sdk.instances[0].paused.is_set()
    assert res.test_run_passed is True and res.gate_stop_reason == "green"


def test_soft_wall_clock_pauses_and_grades_instead_of_timing_out(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    def _write_then_block(conv: _Conv) -> None:
        _write("a.py")(conv)
        _block_until_paused(conv)

    fake_sdk.script = [_write_then_block]
    res = _sandbox(tmp_path, _seq(GREEN), max_gate_rounds=3, wall_clock_timeout_s=1)
    assert fake_sdk.instances[0].paused.is_set()
    # The green tree was GRADED — the old hard timeout threw it away.
    assert res.test_run_passed is True and res.gate_stop_reason == "green"


def test_a_crashing_gate_check_is_red_not_green(tmp_path: Path, fake_sdk: type[_Conv]) -> None:
    def _boom() -> GateVerdict:
        raise RuntimeError("pytest exploded")

    fake_sdk.script = [_write("a.py"), _write("a.py")]
    res = _sandbox(tmp_path, _boom, max_gate_rounds=2)
    assert res.test_run_passed is False
    assert "gate check crashed" in (res.error or "")


def test_without_a_gate_check_the_chain_path_is_unchanged(
    tmp_path: Path, fake_sdk: type[_Conv], monkeypatch: pytest.MonkeyPatch
) -> None:
    graded: list[str] = []

    def _pytest(repo: Path, test_command: str | None = None) -> tuple[bool, str]:
        graded.append(str(repo))
        return False, "1 failed"

    monkeypatch.setattr(runner_module, "_run_pytest", _pytest)
    fake_sdk.script = [_write("a.py")]
    res = _sandbox(tmp_path, None)
    assert len(fake_sdk.instances[0].messages) == 1
    assert graded and res.error == "tests not green after run"
    assert res.gate_rounds == [] and res.gate_stop_reason == ""


def test_a_pause_that_lands_during_grading_is_not_lost(
    tmp_path: Path, fake_sdk: type[_Conv]
) -> None:
    """The soft deadline fires while the gate is grading: no further round may
    start (``run()`` would resume a paused conversation and lose the pause)."""

    def _slow_red() -> GateVerdict:
        time.sleep(1.3)  # the 1 s soft wall clock fires mid-grading
        return RED

    fake_sdk.script = [_write("a.py"), _write("b.py")]
    res = _sandbox(tmp_path, _slow_red, max_gate_rounds=3, wall_clock_timeout_s=1)
    assert fake_sdk.instances[0].runs == 1
    assert res.gate_stop_reason == "wall_clock"
    assert len(res.gate_rounds) == 1 and res.test_run_passed is False
