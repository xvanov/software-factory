"""A dependent must never defer FOREVER behind a blocked foundation.

Observed 2026-07-28: direction 018 spawned stories 167..171. Story 167 landed in
``blocked_deploy_failed``; 168-171 sat in ``story_created`` emitting
``dependency_deferred waiting_on_story_ids=[167]`` once per tick, forever.
``blocked_deploy_failed`` is (correctly) NOT in ``_DEAD_END_DEP_STATES`` — the FMS
``retry-mergeable-blocked-story`` playbook really does revive it — so the
deadlock guard never fired, nothing escalated, and because the tick dispatched
nothing it printed "No in-flight stories", telling the operator the queue was
empty. Uncapped wait + detect-without-remediate, silent for 2+ hours.

The mechanism under test:
  * a STALLED deferral (every blocker human-blocked) is counted and capped at
    ``_MAX_DEPENDENCY_DEFERRALS``, then parked in ``BLOCKED_DEPENDENCY_UNMET``
    with a marker reason that shows up in ``factory inbox``;
  * a LIVE blocker still defers indefinitely and resets the counter (a story
    waiting out its foundation's real work is never capped);
  * the TickSummary reports deferrals, so a defer-only tick can never read as an
    empty queue;
  * a capped dependent revives itself once its blockers leave the human-blocked
    set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlmodel import Session, SQLModel, create_engine
from typer.testing import CliRunner

from factory.chain import handlers as H
from factory.chain import orchestrator as O
from factory.chain.state_machine import StoryRecord, StoryState


@pytest.fixture
def factory_root(tmp_path: Path) -> Path:
    apps_dir = tmp_path / "apps" / "sacrifice"
    apps_dir.mkdir(parents=True)
    (apps_dir / "config.yaml").write_text(
        "name: sacrifice\nrepo: ssh://placeholder\nrepo_path: /tmp/sacrifice\n",
        encoding="utf-8",
    )
    (tmp_path / "factory_settings.yaml").write_text(
        "caps:\n  global_concurrent_agents: 4\n  per_repo_concurrent_agents: 4\n"
        "  daily_spend_usd: 10\n  hourly_spend_usd: 2\n",
        encoding="utf-8",
    )
    return tmp_path


def _seed_pair(
    db: Path,
    *,
    direction: str,
    blocker_state: str,
    dependent_state: str = StoryState.STORY_CREATED.value,
) -> tuple[int, int]:
    """Seed a (lower-id blocker, higher-id dependent) pair in one direction."""
    eng = create_engine(f"sqlite:///{db}", echo=False)
    SQLModel.metadata.create_all(eng)
    blocker = StoryRecord(
        direction_id=direction,
        app="sacrifice",
        title="foundation",
        slug=f"d{direction}-foundation",
        scope="backend",
        state=blocker_state,
        chain_kind="tdd",
    )
    dependent = StoryRecord(
        direction_id=direction,
        app="sacrifice",
        title="dependent",
        slug=f"d{direction}-dependent",
        scope="backend",
        state=dependent_state,
        chain_kind="tdd",
    )
    with Session(eng) as session:
        session.add(blocker)
        session.add(dependent)
        session.commit()
        session.refresh(blocker)
        session.refresh(dependent)
        assert blocker.id is not None and dependent.id is not None
        assert blocker.id < dependent.id
        return blocker.id, dependent.id


def _get(db: Path, story_id: int) -> StoryRecord:
    eng = create_engine(f"sqlite:///{db}", echo=False)
    with Session(eng) as session:
        row = session.get(StoryRecord, story_id)
    assert row is not None
    return row


def _set_state(db: Path, story_id: int, state: str) -> None:
    story = _get(db, story_id)
    story.state = state
    H.persist_story(story, db)


def _events(root: Path, story_id: int, slug: str) -> list[dict[str, Any]]:
    from factory.chain.event_log import read_story_events

    return read_story_events(story_id, software_factory_root=root, slug_hint=slug)


def _no_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any handler dispatch means the dependency gate let the story through."""

    def _loud_sm(story: StoryRecord, *_a: object, **_k: object) -> H.HandlerResult:
        raise AssertionError("a deferred/parked dependent must never be dispatched")

    monkeypatch.setattr(H, "handle_sm", _loud_sm)


def test_blocked_deploy_failed_blocker_does_not_defer_forever(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact D018 shape: a dependent behind ``blocked_deploy_failed`` is
    capped and parked, not deferred every tick forever."""
    db = factory_root / "factory.db"
    blocker_id, dep_id = _seed_pair(
        db, direction="018", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value
    )
    _no_dispatch(monkeypatch)

    # Bounded, not instant: the first ticks still defer (a human may revive the
    # blocker), so the dependent stays exactly where it was.
    for tick_n in range(1, O._MAX_DEPENDENCY_DEFERRALS):
        summary = O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
        assert summary.errors == []
        dep = _get(db, dep_id)
        assert dep.state == StoryState.STORY_CREATED.value
        assert dep.dependency_defer_count == tick_n

    # The cap tick parks it in the existing sink with the marker reason.
    summary = O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    assert summary.errors == []
    dep = _get(db, dep_id)
    assert dep.state == StoryState.BLOCKED_DEPENDENCY_UNMET.value
    assert (dep.last_rejection_reason or "").startswith(O.DEP_DEFER_CAP_REASON_PREFIX)
    assert str(blocker_id) in (dep.last_rejection_reason or "")

    events = _events(factory_root, dep_id, "d018-dependent")
    capped = [e for e in events if e.get("event") == "dependency_deferral_capped"]
    assert len(capped) == 1, events
    assert capped[0]["cap"] == O._MAX_DEPENDENCY_DEFERRALS
    assert capped[0]["waiting_on_story_ids"] == [blocker_id]

    # And it is reported in the summary, not silently swallowed.
    assert any(slug == "d018-dependent" for slug, _ in summary.deferred), summary.deferred

    # Idempotent: further ticks neither re-park nor re-emit (the row has left
    # story_created, so the gate no longer sees it).
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    events = _events(factory_root, dep_id, "d018-dependent")
    assert len([e for e in events if e.get("event") == "dependency_deferral_capped"]) == 1


def test_live_blocker_defers_without_ever_capping(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dependent waiting on a LIVE foundation must keep deferring forever —
    real foundation work takes many ticks and must never be cap-parked."""
    db = factory_root / "factory.db"
    _blocker_id, dep_id = _seed_pair(
        db, direction="019", blocker_state=StoryState.DEV_IN_PROGRESS.value
    )
    _no_dispatch(monkeypatch)

    for _ in range(O._MAX_DEPENDENCY_DEFERRALS + 3):
        summary = O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
        assert summary.errors == []

    dep = _get(db, dep_id)
    assert dep.state == StoryState.STORY_CREATED.value
    assert dep.dependency_defer_count == 0
    assert dep.last_rejection_reason is None
    # Still visible to the operator every tick, though.
    assert summary.deferred and summary.deferred[0][0] == "d019-dependent"


def test_counter_resets_when_blocker_becomes_live_again(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cap counts CONSECUTIVE stalled deferrals: blocker progress resets it,
    so a flapping-but-progressing foundation cannot accumulate a park."""
    db = factory_root / "factory.db"
    blocker_id, dep_id = _seed_pair(
        db, direction="020", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value
    )
    _no_dispatch(monkeypatch)

    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    assert _get(db, dep_id).dependency_defer_count == 2

    # Blocker revived (e.g. FMS retry-mergeable playbook) -> counter resets.
    _set_state(db, blocker_id, StoryState.DEV_RETRY.value)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    dep = _get(db, dep_id)
    assert dep.dependency_defer_count == 0
    assert dep.state == StoryState.STORY_CREATED.value

    # Stalls again -> fresh bounded window, still not parked after 2.
    _set_state(db, blocker_id, StoryState.BLOCKED_DEPLOY_FAILED.value)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    dep = _get(db, dep_id)
    assert dep.dependency_defer_count == 2
    assert dep.state == StoryState.STORY_CREATED.value


def test_capped_dependent_revives_when_blocker_leaves_the_blocked_set(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once the foundation is un-blocked, the cap-parked dependent re-enters the
    chain by itself — otherwise fixing the blocker leaves its dependents rotting."""
    db = factory_root / "factory.db"
    blocker_id, dep_id = _seed_pair(
        db, direction="021", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value
    )
    _no_dispatch(monkeypatch)

    for _ in range(O._MAX_DEPENDENCY_DEFERRALS):
        O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    assert _get(db, dep_id).state == StoryState.BLOCKED_DEPENDENCY_UNMET.value

    # Still parked while the blocker remains human-blocked (no park/revive churn).
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    assert _get(db, dep_id).state == StoryState.BLOCKED_DEPENDENCY_UNMET.value

    _set_state(db, blocker_id, StoryState.DEPLOY_PENDING.value)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    dep = _get(db, dep_id)
    assert dep.state == StoryState.STORY_CREATED.value
    assert dep.dependency_defer_count == 0
    assert dep.last_rejection_reason is None
    assert any(
        e.get("event") == "dependency_defer_revived"
        for e in _events(factory_root, dep_id, "d021-dependent")
    )


def test_deadlock_parked_dependent_is_not_revived_by_the_cap_pass(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revival is keyed on the CAP marker only: a deadlock-parked dependent
    (blocker definitively dead) keeps its operator-driven revival posture."""
    db = factory_root / "factory.db"
    blocker_id, dep_id = _seed_pair(
        db, direction="022", blocker_state=StoryState.BLOCKED_CI_UNRESOLVED.value
    )
    _no_dispatch(monkeypatch)

    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    dep = _get(db, dep_id)
    assert dep.state == StoryState.BLOCKED_DEPENDENCY_UNMET.value
    assert dep.last_rejection_reason is None  # deadlock park, no cap marker

    # Blocker no longer dead, but the deadlock park is NOT auto-revived here.
    _set_state(db, blocker_id, StoryState.DEV_RETRY.value)
    O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    assert _get(db, dep_id).state == StoryState.BLOCKED_DEPENDENCY_UNMET.value


def test_deps_all_stalled_fails_safe_on_missing_row(factory_root: Path) -> None:
    """Ambiguous evidence must never cap a dependent."""
    db = factory_root / "factory.db"
    blocker_id, _dep_id = _seed_pair(
        db, direction="023", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value
    )
    assert O._deps_all_stalled(db, [blocker_id]) is True
    assert O._deps_all_stalled(db, [blocker_id, 9999]) is False  # missing row
    assert O._deps_all_stalled(db, []) is False


def test_blocked_deploy_failed_is_not_a_dead_end_dependency() -> None:
    """Requirement-1 guard: ``blocked_deploy_failed`` stays OUT of the dead-end
    set (the FMS revives it), so the CAP — not abandonment — is the fix."""
    assert StoryState.BLOCKED_DEPLOY_FAILED.value not in O._DEAD_END_DEP_STATES
    # ...but it IS a state no tick can move, which is what the cap keys off.
    assert StoryState.BLOCKED_DEPLOY_FAILED.value in O._STALLED_DEP_STATES
    assert O._DEAD_END_DEP_STATES <= O._STALLED_DEP_STATES


def test_tick_summary_dict_carries_deferrals(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The webhook/manager view of a tick must see deferrals too."""
    db = factory_root / "factory.db"
    _seed_pair(db, direction="024", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value)
    _no_dispatch(monkeypatch)

    summary = O.tick(factory_root, "sacrifice", db_path=db, max_advances_per_story=1)
    d = O.tick_summary_as_dict(summary)
    assert d["deferred"] == summary.deferred
    assert d["deferred"], "a deferral must be visible in the serialized summary"


# --------------------------------------------------------------------------- #
# Operator-visible surfaces: `factory tick` output and `factory inbox`.
# --------------------------------------------------------------------------- #


def _cli_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "apps" / "sacrifice").mkdir(parents=True)
    (root / "apps" / "sacrifice" / "config.yaml").write_text(
        "name: sacrifice\nrepo: https://github.com/test/sacrifice\ndefault_branch: main\n",
        encoding="utf-8",
    )
    (root / "state").mkdir(parents=True, exist_ok=True)
    return root


def _get_cli(root: Path) -> tuple[CliRunner, Any]:
    import importlib

    import factory.cli as cli_mod

    importlib.reload(cli_mod)
    cli_mod._FACTORY_ROOT = root  # type: ignore[attr-defined]
    return CliRunner(), cli_mod


def test_tick_output_reports_deferrals_instead_of_no_in_flight_stories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tick that only deferred must NOT print "No in-flight stories" — that
    message is what convinced the operator the queue was empty for 2+ hours."""
    root = _cli_root(tmp_path)
    monkeypatch.setenv("COLUMNS", "240")
    monkeypatch.setattr(
        "factory.chain.factory_improver.should_fire_improver",
        lambda *a, **kw: (False, "test"),
    )
    monkeypatch.setattr(
        "factory.chain.orchestrator.tick",
        lambda *a, **kw: O.TickSummary(
            app="sacrifice",
            dry_run=False,
            deferred=[("d018-dependent", "waiting_on=[167] (human-blocked, deferrals 1/3)")],
        ),
    )

    runner, cli_mod = _get_cli(root)
    result = runner.invoke(cli_mod.app, ["tick", "--app", "sacrifice", "--dry-run"])

    assert result.exit_code == 0, result.stdout
    assert "No in-flight stories" not in result.stdout
    assert "d018-dependent" in result.stdout
    assert "167" in result.stdout
    assert "deferred=1" in result.stdout


def test_why_projects_the_deferral_instead_of_would_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``factory why`` must not claim a deferred story "would dispatch" — the
    dependency gate runs before the enforcer it was projecting."""
    monkeypatch.setenv("FACTORY_WEBHOOK_LAZY", "1")
    monkeypatch.setenv("COLUMNS", "240")
    root = _cli_root(tmp_path)
    db = root / "state" / "factory.db"
    blocker_id, dep_id = _seed_pair(
        db, direction="018", blocker_state=StoryState.BLOCKED_DEPLOY_FAILED.value
    )

    runner, cli_mod = _get_cli(root)
    result = runner.invoke(cli_mod.app, ["why", str(dep_id)])

    assert result.exit_code == 0, result.stdout
    assert "would DEFER" in result.stdout
    assert str(blocker_id) in result.stdout
    assert "would dispatch" not in result.stdout


def test_cap_parked_story_appears_in_inbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cap park must reach the operator's inbox; a deadlock park must not
    (it is genuinely resolved-abandoned, and that behaviour is unchanged)."""
    monkeypatch.setenv("FACTORY_WEBHOOK_LAZY", "1")
    monkeypatch.setenv("COLUMNS", "240")
    monkeypatch.setenv("TERM", "xterm-256color")
    root = _cli_root(tmp_path)
    db = root / "state" / "factory.db"
    H.persist_story(
        StoryRecord(
            direction_id="018",
            app="sacrifice",
            title="dependent",
            slug="cap-parked-dependent",
            scope="backend",
            state=StoryState.BLOCKED_DEPENDENCY_UNMET.value,
            last_rejection_reason=(
                f"{O.DEP_DEFER_CAP_REASON_PREFIX}: deferred 3x behind human-blocked "
                "story_ids=[167] in direction 018"
            ),
        ),
        db,
    )
    H.persist_story(
        StoryRecord(
            direction_id="018",
            app="sacrifice",
            title="deadlocked",
            slug="deadlock-parked-dependent",
            scope="backend",
            state=StoryState.BLOCKED_DEPENDENCY_UNMET.value,
        ),
        db,
    )

    runner, cli_mod = _get_cli(root)
    result = runner.invoke(cli_mod.app, ["inbox", "--app", "sacrifice"])

    assert result.exit_code == 0, result.stdout
    assert "cap-parked-dependent" in result.stdout
    assert O.DEP_DEFER_CAP_REASON_PREFIX in result.stdout
    assert "deadlock-parked-dependent" not in result.stdout
