"""Delivery-level ENFORCEMENT across the chain (``factory/chain/delivery_gate.py``).

``tests/test_delivery_levels.py`` pins the pure vocabulary/resolution rules. This
file pins what each level actually DOES to finished work:

* spawn resolves + records the level once (the job's request wins — there is no
  per-app ceiling; garbage fails safe to ``none``; a legacy app stays
  ``auto_merge``);
* a later change to the app's default never moves an in-flight story;
* ``handle_docs_enforcer`` (the PR-open site) per level: ``none`` commits and
  never pushes, ``branch`` pushes without a PR, ``draft_pr`` / ``pr`` open a
  draft / ready PR and stop, ``auto_merge`` is unchanged, ``push_to_main``
  pushes and reaches PR_OPEN with no PR;
* ``auto_merge_tick`` never merges a draft PR nor a story whose level does not
  merge, fast-forwards the default branch for ``push_to_main`` (real git,
  local bare origin), and on a refused fast-forward falls back to ``pr``.

No network: gh is never invoked (PR opening is monkeypatched or ``subprocess``
is faked); git runs only against repos under ``tmp_path``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, create_engine, select

from factory.app_config import AppConfig
from factory.chain import auto_merge as am
from factory.chain import delivery_gate
from factory.chain import handlers as H
from factory.chain.delivery_gate import (
    fast_forward_default_branch,
    resolve_for_direction,
    story_level,
)
from factory.chain.event_log import read_story_events
from factory.chain.state_machine import (
    DELIVERED_UNMERGED_STATES,
    StoryRecord,
    StoryState,
    is_terminal,
)
from factory.delivery import DeliveryConfig
from factory.delivery import DeliveryLevel as L
from factory.directions.parser import Direction

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _repo_with_origin(tmp_path: Path) -> tuple[Path, Path]:
    """A bare ``origin`` with one commit on ``main`` and a clone of it."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    _git(tmp_path, "clone", str(origin), str(seed))
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(seed, "config", k, v)
    (seed / "README.md").write_text("seed\n")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "seed")
    _git(seed, "push", "origin", "HEAD:main")
    wt = tmp_path / "wt"
    _git(tmp_path, "clone", str(origin), str(wt))
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(wt, "config", k, v)
    return origin, wt


def _cfg(level: L | None) -> AppConfig:
    if level is None:
        return AppConfig(name="sacrifice", repo="o/r")  # legacy: no delivery block
    return AppConfig(name="sacrifice", repo="o/r", delivery=DeliveryConfig(default=level))


def _direction(fm: dict[str, Any]) -> Direction:
    return Direction(
        id="900",
        slug="x",
        title="X",
        type_tag=None,
        why=None,
        has_flow=False,
        has_api_spec=False,
        acceptance=[],
        explore_tag=False,
        artifacts_paths=[],
        app="sacrifice",
        status="pm-validated",
        raw_frontmatter={"title": "X", **fm},
        raw_body="# X",
    )


def _root(tmp_path: Path) -> Path:
    (tmp_path / "state").mkdir(exist_ok=True)
    return tmp_path


def _story(db: Path, state: StoryState, level: L | None, **kw: Any) -> StoryRecord:
    return H.persist_story(
        StoryRecord(
            direction_id="900",
            app="sacrifice",
            title="t",
            slug="t",
            scope="backend",
            state=state.value,
            github_branch=kw.pop("github_branch", "story/1-t"),
            delivery_level=None if level is None else level.value,
            **kw,
        ),
        db,
    )


def _reload(db: Path, sid: int | None) -> StoryRecord:
    with Session(create_engine(f"sqlite:///{db}")) as ses:
        return ses.exec(select(StoryRecord).where(StoryRecord.id == sid)).one()


def _events(root: Path, story: StoryRecord) -> list[str]:
    assert story.id is not None
    return [
        str(e.get("event"))
        for e in read_story_events(story.id, software_factory_root=root, slug_hint=story.slug)
    ]


# --------------------------------------------------------------------------- #
# resolution: spawn, no ceiling, fail-safe, no mid-flight drift
# --------------------------------------------------------------------------- #


def test_spawn_records_requested_level_no_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job asking for MORE than the app default gets exactly what it asked
    for (no per-app ceiling), recorded on the story and in its event log."""
    monkeypatch.setattr(H, "_author_acceptance_oracle", lambda *a, **k: None)
    root = _root(tmp_path)
    stories = H.handle_stories_spawned(
        _direction({"delivery": "push_to_main"}),
        {"child_stories": [{"title": "do x", "scope": "backend"}], "confidence": 0.9},
        _cfg(L.DRAFT_PR),
        root,
        dry_run=False,
    )
    assert len(stories) == 1
    s = _reload(root / "state" / "factory.db", stories[0].id)
    assert s.delivery_level == L.PUSH_TO_MAIN.value
    ev = read_story_events(s.id or 0, software_factory_root=root, slug_hint=s.slug)
    resolved = [e for e in ev if e.get("event") == "delivery_level_resolved"]
    assert resolved and resolved[0].get("requested") == "push_to_main"
    assert resolved[0].get("reason") == "requested"
    assert "ceiling" not in resolved[0] and "clamped" not in resolved[0]


def test_request_below_default_wins_too() -> None:
    level, info = resolve_for_direction(_cfg(L.AUTO_MERGE), _direction({"delivery": "branch"}))
    assert level is L.BRANCH and info["reason"] == "requested"


def test_absent_request_uses_app_default() -> None:
    level, info = resolve_for_direction(_cfg(L.PR), _direction({}))
    assert level is L.PR and info["reason"] == "app_default"


def test_legacy_app_spawns_auto_merge() -> None:
    level, info = resolve_for_direction(_cfg(None), _direction({}))
    assert level is L.AUTO_MERGE
    assert info["app_opted_in"] is False


def test_garbage_request_fails_safe_to_none() -> None:
    level, info = resolve_for_direction(_cfg(L.AUTO_MERGE), _direction({"delivery": "yolo"}))
    assert level is L.NONE
    assert "fail_safe" in info["reason"]


def test_resolution_error_fails_safe_to_none() -> None:
    level, info = resolve_for_direction(object(), _direction({}))
    assert level is L.NONE
    assert "fail_safe" in info["reason"]


@pytest.mark.parametrize(
    ("recorded", "new_default"), [(L.PR, L.PUSH_TO_MAIN), (L.AUTO_MERGE, L.BRANCH)]
)
def test_app_default_change_never_moves_in_flight(
    tmp_path: Path, recorded: L, new_default: L
) -> None:
    """The recorded level is the story's level: editing the app's default
    mid-flight neither raises nor lowers it (there is no ceiling to clamp to)."""
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.DEV_IN_PROGRESS, recorded)
    assert story_level(s, _cfg(new_default), root, db) is recorded
    assert _reload(db, s.id).delivery_level == recorded.value
    assert "delivery_level_lowered" not in _events(root, s)


def test_unrecorded_legacy_row_resolves_to_today(tmp_path: Path) -> None:
    """A row that predates per-story recording in an app that never opted in
    keeps today's behaviour — legacy in-flight work is unchanged."""
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, None)
    assert story_level(s, _cfg(None), root, db) is L.AUTO_MERGE
    assert _reload(db, s.id).delivery_level == L.AUTO_MERGE.value


def test_unrecorded_row_in_opted_in_app_without_direction_is_none(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, None)
    assert story_level(s, _cfg(L.AUTO_MERGE), root, db) is L.NONE


def test_unreadable_recorded_level_is_none(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, None)
    s.delivery_level = "merge-it-all"
    assert story_level(s, _cfg(L.AUTO_MERGE), root, db) is L.NONE


def test_dry_run_resolution_writes_nothing(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, None)
    story_level(s, _cfg(None), root, db, persist=False)
    assert _reload(db, s.id).delivery_level is None
    assert "delivery_level_resolved" not in _events(root, s)


def test_factory_self_edit_push_to_main_lowered_to_pr(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    cfg = AppConfig(
        name="factory",
        repo=am.FACTORY_REPO,
        delivery=DeliveryConfig(default=L.PUSH_TO_MAIN),
    )
    assert story_level(s, cfg, root, db) is L.PR


def test_delivered_states_are_terminal() -> None:
    for st in DELIVERED_UNMERGED_STATES:
        assert is_terminal(StoryState(st))


# --------------------------------------------------------------------------- #
# handle_docs_enforcer — the PR-open site
# --------------------------------------------------------------------------- #


class _Calls:
    def __init__(self) -> None:
        self.open_pr: list[dict[str, Any]] = []
        self.push: int = 0


@pytest.fixture
def enforcer_env(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    calls = _Calls()
    monkeypatch.setattr(H, "_changed_files_for_story", lambda *a, **k: ["src/a.py"])
    monkeypatch.setattr(H, "_residual_lint_for_story", lambda *a, **k: None)

    def _open(*_a: Any, **k: Any) -> int:
        calls.open_pr.append(k)
        return 4242

    def _push(*_a: Any, **_k: Any) -> bool:
        calls.push += 1
        return True

    monkeypatch.setattr(H, "_open_pr_for_story", _open)
    monkeypatch.setattr(H, "_push_story_branch", _push)
    return calls


def _run_enforcer(tmp_path: Path, level: L | None, cfg_level: L | None) -> tuple:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.TECH_WRITER_DONE, level)
    res = H.handle_docs_enforcer(s, _cfg(cfg_level), root, dry_run=False, db_path=db)
    return root, db, s, res


def test_level_none_commits_locally_never_pushes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, enforcer_env: _Calls
) -> None:
    origin, wt = _repo_with_origin(tmp_path)
    _git(wt, "checkout", "-b", "story/1-t")
    (wt / "feature.py").write_text("x = 1\n")  # uncommitted work
    monkeypatch.setattr(H, "_writing_worktree", lambda *a, **k: wt)

    root, db, s, res = _run_enforcer(tmp_path, L.NONE, L.AUTO_MERGE)

    assert res.next_state == StoryState.DELIVERED_LOCAL
    assert enforcer_env.open_pr == [] and enforcer_env.push == 0
    # The work is COMMITTED on the local story branch...
    assert _git(wt, "status", "--porcelain") == ""
    assert "feature.py" in _git(wt, "show", "--name-only", "--format=", "HEAD")
    # ...and nothing reached origin.
    assert _git(origin, "branch", "--list", "story/1-t") == ""
    assert _reload(db, s.id).state == StoryState.DELIVERED_LOCAL.value
    assert "delivered" in _events(root, s)


def test_level_branch_pushes_without_pr(tmp_path: Path, enforcer_env: _Calls) -> None:
    _, db, s, res = _run_enforcer(tmp_path, L.BRANCH, L.AUTO_MERGE)
    assert res.next_state == StoryState.DELIVERED_BRANCH
    assert enforcer_env.push == 1 and enforcer_env.open_pr == []
    assert _reload(db, s.id).github_pr_number is None


def test_level_draft_pr_opens_draft_and_stops(tmp_path: Path, enforcer_env: _Calls) -> None:
    _, db, s, res = _run_enforcer(tmp_path, L.DRAFT_PR, L.AUTO_MERGE)
    assert res.next_state == StoryState.DELIVERED_PR
    assert enforcer_env.open_pr == [{"draft": True, "will_auto_merge": False}]
    row = _reload(db, s.id)
    assert row.github_pr_number == 4242 and row.state == StoryState.DELIVERED_PR.value


def test_level_pr_opens_ready_pr_and_stops(tmp_path: Path, enforcer_env: _Calls) -> None:
    _, _db, _s, res = _run_enforcer(tmp_path, L.PR, L.AUTO_MERGE)
    assert res.next_state == StoryState.DELIVERED_PR
    assert enforcer_env.open_pr == [{"draft": False, "will_auto_merge": False}]


def test_legacy_app_auto_merge_unchanged(tmp_path: Path, enforcer_env: _Calls) -> None:
    """No delivery block, no recorded level: exactly today's path to PR_OPEN."""
    _, db, s, res = _run_enforcer(tmp_path, None, None)
    assert res.next_state == StoryState.PR_OPEN
    assert enforcer_env.open_pr == [{"draft": False, "will_auto_merge": True}]
    assert _reload(db, s.id).delivery_level == L.AUTO_MERGE.value


def test_level_push_to_main_pushes_and_reaches_pr_open_without_pr(
    tmp_path: Path, enforcer_env: _Calls
) -> None:
    _, db, s, res = _run_enforcer(tmp_path, L.PUSH_TO_MAIN, L.PUSH_TO_MAIN)
    assert res.next_state == StoryState.PR_OPEN
    assert enforcer_env.push == 1 and enforcer_env.open_pr == []
    assert _reload(db, s.id).github_pr_number is None


def test_branch_push_failure_is_bounded_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, enforcer_env: _Calls
) -> None:
    monkeypatch.setattr(H, "_push_story_branch", lambda *a, **k: False)
    _, db, s, res = _run_enforcer(tmp_path, L.BRANCH, L.AUTO_MERGE)
    assert res.next_state == StoryState.DOCS_ENFORCER_CHECK
    row = _reload(db, s.id)
    assert row.pr_create_retries == 1 and "git push failed" in (row.error or "")


def test_open_pr_draft_flag_reaches_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The real ``_open_pr_for_story`` passes ``--draft`` for draft_pr and
    never for an auto-merge PR (gh faked at the subprocess boundary)."""
    seen: list[list[str]] = []

    def _fake_run(cmd: list[str], *a: Any, **k: Any) -> subprocess.CompletedProcess[str]:
        seen.append(list(cmd))
        out = "https://github.com/o/r/pull/77\n" if cmd[:3] == ["gh", "pr", "create"] else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr(H, "_writing_worktree", lambda *a, **k: tmp_path)
    monkeypatch.setattr(H, "_autoformat_changed_py_before_pr", lambda *a, **k: None)
    s = StoryRecord(
        direction_id="9",
        app="sacrifice",
        title="t",
        slug="t",
        scope="b",
        github_branch="story/1-t",
        delivery_level="draft_pr",
    )
    assert (
        H._open_pr_for_story(s, _cfg(L.DRAFT_PR), tmp_path, draft=True, will_auto_merge=False) == 77
    )
    gh = [c for c in seen if c[:3] == ["gh", "pr", "create"]]
    assert gh and "--draft" in gh[-1]
    assert "will NOT mark this PR ready or merge it" in gh[-1][gh[-1].index("--body") + 1]
    seen.clear()
    assert H._open_pr_for_story(s, _cfg(None), tmp_path) == 77
    gh = [c for c in seen if c[:3] == ["gh", "pr", "create"]]
    assert gh and "--draft" not in gh[-1]
    assert not any(c[:3] == ["gh", "pr", "ready"] for c in seen)


# --------------------------------------------------------------------------- #
# auto_merge_tick
# --------------------------------------------------------------------------- #


@pytest.fixture
def am_root(tmp_path: Path) -> Path:
    root = _root(tmp_path)
    (root / "apps" / "sacrifice").mkdir(parents=True)
    return root


def _write_cfg(root: Path, level: L | None) -> None:
    body = "name: sacrifice\nrepo: o/r\n"
    if level is not None:
        body += f"delivery:\n  default: {level.value}\n"
    (root / "apps" / "sacrifice" / "config.yaml").write_text(body, encoding="utf-8")


def _merge_must_not_run(**_kw: Any) -> str | None:
    raise AssertionError("gh pr merge must never run for this story")


@pytest.fixture
def gates_green(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(am, "evaluate_all_gates", lambda *a, **k: {})
    monkeypatch.setattr(am, "required_gate_labels", lambda *a, **k: [])


def test_draft_pr_never_merged(am_root: Path, gates_green: None) -> None:
    _write_cfg(am_root, None)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.AUTO_MERGE, github_pr_number=7)
    fx = am.FixturePR(pr_number=7, head_sha="ab" * 20, base_branch="main", story=s, is_draft=True)
    actions = am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[fx],
        db_path=db,
        merge_fn=_merge_must_not_run,
        pr_merged_query=lambda **k: False,
    )
    assert len(actions) == 1 and not actions[0].merged
    assert "draft" in actions[0].reason
    assert _reload(db, s.id).state == StoryState.PR_OPEN.value


@pytest.fixture
def disarms(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Record every ``gh pr merge --disable-auto`` the chain asks for."""
    seen: list[int] = []

    def _disarm(_cfg: Any, pr_number: int | None, **_k: Any) -> str | None:
        seen.append(int(pr_number or 0))
        return None

    monkeypatch.setattr(delivery_gate, "disable_auto_merge", _disarm)
    return seen


@pytest.mark.parametrize("level", [L.DRAFT_PR, L.PR])
def test_non_merging_level_is_settled_never_merged(
    am_root: Path, gates_green: None, disarms: list[int], level: L
) -> None:
    """A mergeable-state story whose RECORDED level does not merge is settled
    to DELIVERED_PR — never merged, gh is never asked to mark anything ready,
    and any auto-merge armed on an earlier tick is DISARMED (finding 2)."""
    _write_cfg(am_root, L.AUTO_MERGE)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, level, github_pr_number=8)
    fx = am.FixturePR(pr_number=8, head_sha="cd" * 20, base_branch="main", story=s)
    actions = am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[fx],
        db_path=db,
        merge_fn=_merge_must_not_run,
        pr_merged_query=lambda **k: False,
    )
    assert not actions[0].merged
    row = _reload(db, s.id)
    assert row.state == StoryState.DELIVERED_PR.value
    assert row.delivery_level == level.value
    assert disarms == [8]


def test_finding2_disarm_failure_is_recorded_and_story_still_settles(
    am_root: Path, gates_green: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(delivery_gate, "disable_auto_merge", lambda *a, **k: "gh exit=1: boom")
    _write_cfg(am_root, L.AUTO_MERGE)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PR, github_pr_number=18)
    fx = am.FixturePR(pr_number=18, head_sha="cd" * 20, base_branch="main", story=s)
    am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[fx],
        db_path=db,
        merge_fn=_merge_must_not_run,
        pr_merged_query=lambda **k: False,
    )
    row = _reload(db, s.id)
    assert row.state == StoryState.DELIVERED_PR.value
    assert "could not disarm" in (row.error or "")
    assert "auto_merge_disarm_failed" in _events(am_root, s)


def _fake_run(rc: int, stderr: str = "", stdout: str = ""):
    calls: list[list[str]] = []

    def _run(cmd: list[str], *a: Any, **k: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)

    return _run, calls


def test_finding2_disable_auto_merge_command_and_noop() -> None:
    run, calls = _fake_run(0)
    assert delivery_gate.disable_auto_merge(_cfg(L.PR), 12, run=run) is None
    assert calls == [["gh", "pr", "merge", "12", "--disable-auto", "--repo", "o/r"]]
    run, _ = _fake_run(1, stderr="GraphQL: Auto-merge is not enabled for this pull request")
    assert delivery_gate.disable_auto_merge(_cfg(L.PR), 12, run=run) is None
    run, _ = _fake_run(1, stderr="HTTP 403: forbidden")
    assert "exit=1" in (delivery_gate.disable_auto_merge(_cfg(L.PR), 12, run=run) or "")
    # No PR -> nothing to disarm, gh never called.
    run, calls = _fake_run(0)
    assert delivery_gate.disable_auto_merge(_cfg(L.PR), None, run=run) is None and calls == []


def test_legacy_auto_merge_story_still_merges(am_root: Path, gates_green: None) -> None:
    _write_cfg(am_root, None)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, None, github_pr_number=9)
    merged: list[int] = []

    def _merge(**kw: Any) -> None:
        merged.append(kw["pr_number"])
        return None

    fx = am.FixturePR(pr_number=9, head_sha="ef" * 20, base_branch="main", story=s)
    actions = am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[fx],
        db_path=db,
        merge_fn=_merge,
        pr_merged_query=lambda **k: False,
        wait_for_ci=False,
    )
    assert merged == [9] and actions[0].merged
    assert _reload(db, s.id).state == StoryState.DEPLOY_PENDING.value


def _preflight_ok(_cfg: Any, _base: str) -> tuple[str, str]:
    return delivery_gate.PREFLIGHT_OK, "unprotected and green"


def _p2m_fixture(s: StoryRecord, wt: Path) -> am.FixturePR:
    return am.FixturePR(
        pr_number=-(s.id or 0),
        head_sha=_git(wt, "rev-parse", "HEAD"),
        base_branch="main",
        ci_state=None,
        story=s,
        repo_root=wt,
    )


def test_push_to_main_fast_forwards_default_branch(
    am_root: Path, tmp_path: Path, gates_green: None
) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    origin, wt = _repo_with_origin(tmp_path)
    _git(wt, "checkout", "-b", "story/1-t")
    (wt / "f.py").write_text("y = 2\n")
    _git(wt, "add", "f.py")
    _git(wt, "commit", "-m", "work")
    head = _git(wt, "rev-parse", "HEAD")
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)

    actions = am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[_p2m_fixture(s, wt)],
        db_path=db,
        merge_fn=_merge_must_not_run,
        push_to_main_preflight_fn=_preflight_ok,
    )
    assert actions[0].merged, actions[0].reason
    assert _git(origin, "rev-parse", "main") == head
    assert _reload(db, s.id).state == StoryState.DEPLOY_PENDING.value
    # The deploy can find the fast-forward's sha under the placeholder number.
    assert H._lookup_merged_sha("sacrifice", -(s.id or 0), db) == head


def test_push_to_main_refused_falls_back_to_pr(
    am_root: Path, tmp_path: Path, gates_green: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    origin, wt = _repo_with_origin(tmp_path)
    # main moves on origin AFTER the story branched: no longer a fast-forward.
    other = tmp_path / "other"
    _git(tmp_path, "clone", str(origin), str(other))
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(other, "config", k, v)
    (other / "z.txt").write_text("z\n")
    _git(other, "add", "z.txt")
    _git(other, "commit", "-m", "elsewhere")
    _git(other, "push", "origin", "HEAD:main")
    origin_main_before = _git(origin, "rev-parse", "main")
    _git(wt, "checkout", "-b", "story/1-t")
    (wt / "f.py").write_text("y = 2\n")
    _git(wt, "add", "f.py")
    _git(wt, "commit", "-m", "work")

    opened: list[dict[str, Any]] = []

    def _open(*_a: Any, **k: Any) -> int:
        opened.append(k)
        return 555

    monkeypatch.setattr(H, "_open_pr_for_story", _open)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)

    actions = am.auto_merge_tick(
        am_root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[_p2m_fixture(s, wt)],
        db_path=db,
        merge_fn=_merge_must_not_run,
        push_to_main_preflight_fn=_preflight_ok,
    )
    assert not actions[0].merged
    assert "push_to_main refused" in actions[0].reason
    assert _git(origin, "rev-parse", "main") == origin_main_before  # untouched
    row = _reload(db, s.id)
    assert row.state == StoryState.DELIVERED_PR.value
    assert row.github_pr_number == 555 and row.delivery_level == L.PR.value
    assert opened == [{"draft": False, "will_auto_merge": False}]


def test_fast_forward_refuses_when_head_moved(tmp_path: Path) -> None:
    _, wt = _repo_with_origin(tmp_path)
    ok, why = fast_forward_default_branch(worktree=wt, base="main", expected_sha="0" * 40)
    assert not ok and "not the gated commit" in why


# --------------------------------------------------------------------------- #
# merge reality: a human merging a delivered PR flows into deploy
# --------------------------------------------------------------------------- #


def _q(value: str):
    def _query(*, app_config: AppConfig, pr_number: int) -> str | None:
        return value

    return _query


def test_human_merge_of_delivered_pr_reconciles_to_deploy_pending(tmp_path: Path) -> None:
    from factory.chain.orchestrator import reconcile_from_github

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.DELIVERED_PR, L.PR, github_pr_number=31)
    out = reconcile_from_github(
        db, "sacrifice", cfg=_cfg(L.PR), root=root, query_pr_state=_q("MERGED")
    )
    assert out and out[0][2] == StoryState.DEPLOY_PENDING.value
    assert _reload(db, s.id).state == StoryState.DEPLOY_PENDING.value


def test_finding11_closed_delivered_pr_settles_to_closed_by_operator(tmp_path: Path) -> None:
    """A delivered PR a human CLOSES unmerged is a ruling: the story settles to
    the terminal operator-closed sink instead of being polled forever."""
    from factory.chain.orchestrator import reconcile_from_github

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.DELIVERED_PR, L.DRAFT_PR, github_pr_number=32)
    out = reconcile_from_github(
        db, "sacrifice", cfg=_cfg(L.PR), root=root, query_pr_state=_q("CLOSED")
    )
    assert out and out[0][2] == StoryState.CLOSED_BY_OPERATOR.value
    row = _reload(db, s.id)
    assert row.state == StoryState.CLOSED_BY_OPERATOR.value
    assert "closed on GitHub without merging" in (row.last_rejection_reason or "")
    # Settled: a second pass does not query it again.
    seen: list[int] = []

    def _count(*, app_config: AppConfig, pr_number: int) -> str | None:
        seen.append(pr_number)
        return "CLOSED"

    reconcile_from_github(db, "sacrifice", cfg=_cfg(L.PR), root=root, query_pr_state=_count)
    assert seen == []


def test_finding11_open_delivered_pr_untouched(tmp_path: Path) -> None:
    from factory.chain.orchestrator import reconcile_from_github

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.DELIVERED_PR, L.PR, github_pr_number=33)
    assert (
        reconcile_from_github(db, "sacrifice", cfg=_cfg(L.PR), root=root, query_pr_state=_q("OPEN"))
        == []
    )
    assert _reload(db, s.id).state == StoryState.DELIVERED_PR.value


def test_delivered_states_never_close_tracker_issues() -> None:
    """Merge reality: unmerged work must not close its story issue / tracker."""
    from factory.directions.tracker_issue import _RESOLVED_STORY_STATES

    assert not (DELIVERED_UNMERGED_STATES & _RESOLVED_STORY_STATES)


def test_delivered_states_hold_no_concurrency_slot_and_await_a_human() -> None:
    from factory.chain.orchestrator import _NON_CAP_COUNTING_STATES, _PENDING_HUMAN_STATES

    assert DELIVERED_UNMERGED_STATES <= _NON_CAP_COUNTING_STATES
    assert DELIVERED_UNMERGED_STATES <= _PENDING_HUMAN_STATES


# --------------------------------------------------------------------------- #
# adversarial review 2026-11-02 — push_to_main gate-block cap + preflight
# --------------------------------------------------------------------------- #


@pytest.fixture
def gates_red(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    from factory.chain.gates.evaluator import GateResult

    evals: list[int] = []

    def _eval(*_a: Any, **_k: Any) -> dict[str, Any]:
        evals.append(1)
        return {"tests-green": GateResult(label="tests-green", passed=False, reason="red")}

    monkeypatch.setattr(am, "evaluate_all_gates", _eval)
    monkeypatch.setattr(am, "required_gate_labels", lambda *a, **k: ["tests-green"])
    return evals


def _p2m_tick(root: Path, db: Path, sid: int | None, head: str, **kw: Any) -> list[Any]:
    s = _reload(db, sid)
    fx = am.FixturePR(
        pr_number=-(s.id or 0), head_sha=head, base_branch="main", ci_state=None, story=s
    )
    return am.auto_merge_tick(
        root,
        "sacrifice",
        dry_run=False,
        fixture_prs=[fx],
        db_path=db,
        merge_fn=_merge_must_not_run,
        fast_forward_fn=lambda **k: (_ for _ in ()).throw(AssertionError("must not push")),
        **kw,
    )


def test_finding3_push_to_main_gate_block_cap_is_per_story(
    am_root: Path, gates_red: list[int]
) -> None:
    """The worktree sha moves every tick; the cap must still bite at 3 and park
    the story, instead of re-running the gate set forever."""
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    for i in range(3):
        _p2m_tick(am_root, db, s.id, f"{i:040d}", push_to_main_preflight_fn=_preflight_ok)
    row = _reload(db, s.id)
    assert row.state == StoryState.BLOCKED_CI_UNRESOLVED.value
    assert "push_to_main" in (row.last_rejection_reason or "")
    assert len(gates_red) == 3
    assert "gate_block_exhausted" in _events(am_root, s)
    # BLOCKED_CI_UNRESOLVED is not a mergeable state, so the real tick never
    # builds a fixture for it again (fixture injection here bypasses that query).
    assert row.state not in am._MERGEABLE_STATES


def test_finding3_per_story_history_ignores_sha_but_reuses_only_same_sha(
    tmp_path: Path,
) -> None:
    from factory.chain.event_log import log_story_event

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    for sha in ("a" * 40, "b" * 40):
        log_story_event(
            s.id,
            "merge_gates_failed",
            {"head_sha": sha, "missing_labels": ["tests-green"], "dry_run": False},
            software_factory_root=root,
            slug_hint=s.slug,
        )
    kw: dict[str, Any] = {"story_id": s.id, "root": root, "slug": s.slug}
    assert am._gate_block_history(head_sha="c" * 40, per_story=True, **kw) == (2, None)
    n, last = am._gate_block_history(head_sha="b" * 40, per_story=True, **kw)
    assert n == 2 and last is not None and last["head_sha"] == "b" * 40
    # The PR path keeps its per-sha semantics.
    assert am._gate_block_history(head_sha="c" * 40, **kw) == (0, None)


def test_finding4_push_to_main_holds_on_red_main(am_root: Path, gates_red: list[int]) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    for _ in range(4):  # more ticks than the gate-block cap: a hold never counts
        actions = _p2m_tick(
            am_root,
            db,
            s.id,
            "a" * 40,
            push_to_main_preflight_fn=lambda c, b: (delivery_gate.PREFLIGHT_HOLD, "main is red"),
        )
        assert actions[0].reason.startswith("held:")
    row = _reload(db, s.id)
    assert row.state == StoryState.PR_OPEN.value  # untouched
    assert gates_red == []  # no gate ran, nothing counted
    assert (row.last_rejection_reason or "").startswith(am._HOLD_REASON_PREFIX)


def test_finding4_hold_reason_cleared_when_main_turns_green(
    am_root: Path, gates_red: list[int]
) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    _p2m_tick(
        am_root,
        db,
        s.id,
        "a" * 40,
        push_to_main_preflight_fn=lambda c, b: (delivery_gate.PREFLIGHT_HOLD, "red"),
    )
    _p2m_tick(am_root, db, s.id, "a" * 40, push_to_main_preflight_fn=_preflight_ok)
    assert not (_reload(db, s.id).last_rejection_reason or "").startswith(am._HOLD_REASON_PREFIX)
    assert len(gates_red) == 1  # evaluated once main was green


def test_finding4_push_to_main_refused_on_protected_branch(
    am_root: Path, gates_red: list[int]
) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)
    _p2m_tick(
        am_root,
        db,
        s.id,
        "a" * 40,
        push_to_main_preflight_fn=lambda c, b: (
            delivery_gate.PREFLIGHT_REFUSE,
            "main requires status checks ['ci']",
        ),
    )
    row = _reload(db, s.id)
    assert row.state == StoryState.BLOCKED_DEPLOY_FAILED.value
    assert (row.last_rejection_reason or "").startswith("push_to_main_refused:")
    assert gates_red == []
    assert "push_to_main_refused" in _events(am_root, s)


def test_finding4_preflight_error_is_a_hold(am_root: Path, gates_red: list[int]) -> None:
    _write_cfg(am_root, L.PUSH_TO_MAIN)
    db = am_root / "state" / "factory.db"
    s = _story(db, StoryState.PR_OPEN, L.PUSH_TO_MAIN)

    def _boom(*_a: Any) -> tuple[str, str]:
        raise RuntimeError("gh exploded")

    _p2m_tick(am_root, db, s.id, "a" * 40, push_to_main_preflight_fn=_boom)
    assert _reload(db, s.id).state == StoryState.PR_OPEN.value
    assert gates_red == []


def _gh_api_fake(responses: dict[str, Any]):
    import json as _json

    def _run(cmd: list[str], *a: Any, **k: Any) -> subprocess.CompletedProcess[str]:
        path = cmd[2]
        for key, val in responses.items():
            if key in path:
                if isinstance(val, int):
                    return subprocess.CompletedProcess(cmd, val, stdout="", stderr="HTTP 500")
                return subprocess.CompletedProcess(cmd, 0, stdout=_json.dumps(val), stderr="")
        raise AssertionError(f"unexpected gh api {path}")

    return _run


_GREEN = {
    "branches/main": {"protected": False, "protection": {"enabled": False}},
    "rules/branches/main": [],
    "check-runs": {"check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]},
    "/status": {"state": "success", "statuses": []},
}


@pytest.mark.parametrize(
    ("override", "verdict"),
    [
        ({}, delivery_gate.PREFLIGHT_OK),
        (
            {
                "branches/main": {
                    "protected": True,
                    "protection": {"required_status_checks": {"contexts": ["main-green"]}},
                }
            },
            delivery_gate.PREFLIGHT_REFUSE,
        ),
        ({"rules/branches/main": [{"type": "pull_request"}]}, delivery_gate.PREFLIGHT_REFUSE),
        (
            {
                "check-runs": {
                    "check_runs": [{"name": "ci", "status": "completed", "conclusion": "failure"}]
                }
            },
            delivery_gate.PREFLIGHT_HOLD,
        ),
        (
            {"check-runs": {"check_runs": [{"name": "ci", "status": "in_progress"}]}},
            delivery_gate.PREFLIGHT_HOLD,
        ),
        (
            {"/status": {"statuses": [{"context": "x", "state": "error"}]}},
            delivery_gate.PREFLIGHT_HOLD,
        ),
        ({"branches/main": 1}, delivery_gate.PREFLIGHT_HOLD),
        ({"rules/branches/main": 1}, delivery_gate.PREFLIGHT_HOLD),
    ],
)
def test_finding4_preflight_classification(override: dict[str, Any], verdict: str) -> None:
    # Order matters for substring matching: the more specific keys first.
    responses = {
        "rules/branches/main": override.get("rules/branches/main", _GREEN["rules/branches/main"]),
        "branches/main": override.get("branches/main", _GREEN["branches/main"]),
        "check-runs": override.get("check-runs", _GREEN["check-runs"]),
        "/status": override.get("/status", _GREEN["/status"]),
    }
    got, why = delivery_gate.push_to_main_preflight(
        _cfg(L.PUSH_TO_MAIN), "main", run=_gh_api_fake(responses)
    )
    assert got == verdict, why


# --------------------------------------------------------------------------- #
# finding 10 — multi-story jobs below auto_merge finish
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("level", [L.NONE, L.BRANCH, L.DRAFT_PR, L.PR])
def test_finding10_delivered_sibling_is_not_a_pending_dep_below_auto_merge(
    tmp_path: Path, level: L
) -> None:
    from factory.chain.orchestrator import _direction_deps_pending

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    first = _story(db, StoryState.DELIVERED_PR, level, github_branch="story/1-a")
    second = _story(db, StoryState.STORY_CREATED, level, github_branch="story/2-b")
    assert first.id is not None and second.id is not None and first.id < second.id
    assert _direction_deps_pending(db, second) == []


@pytest.mark.parametrize("level", [L.AUTO_MERGE, L.PUSH_TO_MAIN, None])
def test_finding10_merging_dependent_still_waits(tmp_path: Path, level: L | None) -> None:
    from factory.chain.orchestrator import _direction_deps_pending

    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    first = _story(db, StoryState.DELIVERED_PR, L.PR, github_branch="story/1-a")
    second = _story(db, StoryState.STORY_CREATED, level, github_branch="story/2-b")
    assert _direction_deps_pending(db, second) == [first.id]


def test_finding10_direction_completes_when_every_child_is_delivered() -> None:
    from types import SimpleNamespace

    from factory.directions.tracker_issue import _direction_is_complete

    rows = [
        SimpleNamespace(state=st, last_rejection_reason=None)
        for st in ("delivered_pr", "delivered_branch", "delivered_local", "deployed")
    ]
    assert _direction_is_complete(rows)
    rows.append(SimpleNamespace(state="pr_open", last_rejection_reason=None))
    assert not _direction_is_complete(rows)


# --------------------------------------------------------------------------- #
# finding 8 + the compose-bug class: every terminal/settled state set knows
# about the delivered_* states
# --------------------------------------------------------------------------- #


def test_finding8_stalled_detector_treats_delivered_as_terminal() -> None:
    from factory.manager.detectors.stalled_stories import _TERMINAL_STATES

    assert DELIVERED_UNMERGED_STATES <= _TERMINAL_STATES


def test_delivered_states_in_every_terminal_set() -> None:
    from factory.chain import factory_status
    from factory.chain.detector_watch import _WORKTREE_ORPHAN_DB_STATES
    from factory.observability import queries

    assert DELIVERED_UNMERGED_STATES <= set(factory_status._TERMINAL_STATES)
    assert DELIVERED_UNMERGED_STATES <= set(queries._TERMINAL_STATES_FOR_PROGRESS)
    assert DELIVERED_UNMERGED_STATES <= set(queries._NOT_IN_FLIGHT_STATES)
    assert DELIVERED_UNMERGED_STATES <= set(_WORKTREE_ORPHAN_DB_STATES)


def test_delivered_rows_are_not_in_flight(tmp_path: Path) -> None:
    root = _root(tmp_path)
    db = root / "state" / "factory.db"
    for i, st in enumerate(sorted(DELIVERED_UNMERGED_STATES)):
        _story(db, StoryState(st), L.PR, github_branch=f"story/{i}-x")
    assert H.stories_in_flight("sacrifice", db) == []
