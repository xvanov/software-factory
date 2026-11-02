"""``factory job status | list | cancel`` — a job's state, from the real artifacts.

Read paths are READ-ONLY: the sqlite DB is opened ``mode=ro`` (a status call
must never create or migrate the live DB), and PR state / merged come from
GitHub via :mod:`factory.jobs.github`. When ``gh`` fails the job is reported
from the local view and ``why`` says so.

State mapping (docs/JOBS-API.md), first match wins:

* ``cancelled`` — ``factory job cancel`` ran AND no story is still live.
* no stories yet: direction ``created`` → ``queued`` (or ``needs_human`` when
  the approval gate parks it); ``pm-validated`` → ``triaging``;
  ``needs-direction`` → ``needs_human``; ``closed`` → ``failed``.
* every story delivered at the job's effective delivery level → ``done`` —
  but only when GitHub CONFIRMED it (PR merged / PR open / branch exists);
  a delivery only the local view claims stays ``in_progress`` with a ``why``.
* any story waiting on a human (the orchestrator's pending-human sinks, or a
  dependency-cap park) → ``needs_human``.
* any story still live → ``in_progress``, or ``blocked`` when the factory is
  halted / paused or every live story is waiting on a dependency.
* otherwise (everything terminal, something undelivered) → ``failed``.

Dual-draft losers (``superseded_by_sibling``) are ignored: only one of the two
interpretations is meant to ship.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.app_config import AppConfig, load_app_config
from factory.chain.state_machine import (
    StoryState,
    is_dependency_cap_parked,
    is_terminal,
)
from factory.delivery import DeliveryLevel, effective_level
from factory.directions.approval import (
    approval_blocked_reason,
    awaiting_operator_approval,
)
from factory.jobs.common import (
    JobError,
    JobRef,
    find_job,
    iter_jobs,
    read_state_yaml,
    state_db_path,
)
from factory.jobs.github import GitHubCache, GitHubView, PRInfo
from factory.jobs.submit import effective_pipeline

JOB_STATES: tuple[str, ...] = (
    "queued",
    "triaging",
    "in_progress",
    "blocked",
    "needs_human",
    "done",
    "failed",
    "cancelled",
)
TERMINAL_JOB_STATES: frozenset[str] = frozenset({"done", "failed", "cancelled"})

#: ``state.yaml`` key ``factory job cancel`` writes.
CANCEL_KEY = "job_cancelled"

_S = StoryState
#: Mirrors ``orchestrator._PENDING_HUMAN_STATES`` (kept in sync by a test).
HUMAN_STATES: frozenset[str] = frozenset(
    {
        _S.BLOCKED_DEPLOY_FAILED.value,
        _S.BLOCKED_BUDGET_EXCEEDED.value,
        _S.BLOCKED_TESTS_NEED_CLARIFICATION.value,
        _S.BLOCKED_REVIEW_NONCONVERGENT.value,
        _S.BLOCKED_UNDERSPECIFIED.value,
    }
)
#: Terminal sinks that mean "this story will not deliver".
FAILED_STATES: frozenset[str] = frozenset(
    {
        _S.BLOCKED_CI_UNRESOLVED.value,
        _S.BLOCKED_DEPENDENCY_UNMET.value,  # deadlock park; cap park is human
        _S.QUARANTINED_INVALID_STATE.value,
        _S.CLOSED_BY_OPERATOR.value,
    }
)
IGNORED_STATES: frozenset[str] = frozenset({_S.SUPERSEDED_BY_SIBLING.value})
#: Local evidence that a merge happened (used only when GitHub can't be asked).
LOCAL_MERGED_STATES: frozenset[str] = frozenset({_S.DEPLOY_PENDING.value, _S.DEPLOYED.value})
#: Local evidence that a PR exists.
LOCAL_PR_STATES: frozenset[str] = frozenset(
    {
        _S.PR_OPEN.value,
        _S.CI_PENDING.value,
        _S.CI_GREEN.value,
        _S.READY_FOR_MERGE.value,
    }
    | LOCAL_MERGED_STATES
)


def _is_live(state: str) -> bool:
    try:
        return not is_terminal(StoryState(state))
    except ValueError:
        # Unknown state: not provably finished, so not terminal (and the
        # job is reported in_progress with the raw state visible).
        return True


# --------------------------------------------------------------------------- #
# Read-only DB access
# --------------------------------------------------------------------------- #


def _ro_connect(db: Path) -> sqlite3.Connection | None:
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return None
    conn.row_factory = sqlite3.Row
    return conn


def _query(conn: sqlite3.Connection | None, sql: str, args: tuple[Any, ...]) -> list[sqlite3.Row]:
    if conn is None:
        return []
    try:
        return list(conn.execute(sql, args).fetchall())
    except sqlite3.Error:
        return []


@dataclass
class _Ctx:
    root: Path
    conn: sqlite3.Connection | None
    github: GitHubCache
    factory_block: str | None


def _factory_block_reason(root: Path, conn: sqlite3.Connection | None) -> str | None:
    """Why the factory as a whole is not dispatching, or ``None``."""
    try:
        from factory.manager.halt import is_halted

        if is_halted(root=root):
            return "factory is halted (operator must run 'factory resume')"
    except Exception:  # noqa: BLE001
        pass
    rows = _query(conn, "SELECT mode FROM factory_state WHERE id = 1", ())
    if rows and str(rows[0]["mode"]) == "paused":
        return "factory mode is 'paused'"
    return None


def _direction_status(ctx: _Ctx, ref: JobRef, state_yaml: dict[str, Any]) -> str:
    rows = _query(
        ctx.conn,
        "SELECT status FROM directions WHERE app = ? AND direction_id = ?",
        (ref.app, ref.direction_id),
    )
    if rows and rows[0]["status"]:
        return str(rows[0]["status"])
    status = state_yaml.get("status")
    return str(status) if isinstance(status, str) and status else "created"


def _stories(ctx: _Ctx, ref: JobRef) -> list[dict[str, Any]]:
    rows = _query(
        ctx.conn,
        "SELECT * FROM stories WHERE app = ? AND direction_id = ? ORDER BY id",
        (ref.app, ref.direction_id),
    )
    return [dict(r) for r in rows]


def _cost(ctx: _Ctx, ref: JobRef, story_ids: list[int]) -> float:
    clauses = ["(app = ? AND direction_id = ?)"]
    args: list[Any] = [ref.app, ref.direction_id]
    if story_ids:
        clauses.append(f"story_id IN ({','.join('?' * len(story_ids))})")
        args += story_ids
    rows = _query(
        ctx.conn,
        f"SELECT COALESCE(SUM(cost_usd), 0) AS c FROM runs WHERE {' OR '.join(clauses)}",
        tuple(args),
    )
    if not rows and story_ids:
        # Older DB without runs.app/direction_id columns: story-attributed only.
        rows = _query(
            ctx.conn,
            "SELECT COALESCE(SUM(cost_usd), 0) AS c FROM runs "
            f"WHERE story_id IN ({','.join('?' * len(story_ids))})",
            tuple(story_ids),
        )
    return round(float(rows[0]["c"]), 4) if rows else 0.0


# --------------------------------------------------------------------------- #
# Story classification
# --------------------------------------------------------------------------- #


@dataclass
class _StoryView:
    row: dict[str, Any]
    pr: PRInfo | None
    pr_number: int | None
    pr_url: str | None
    pr_state: str | None
    delivered: bool
    merged: bool
    kind: str  # delivered | unverified | human | failed | live | ignored


def _classify(
    row: dict[str, Any], level: DeliveryLevel, repo: str, gh: GitHubView | None
) -> _StoryView:
    state = str(row.get("state") or "")
    pr_number = row.get("github_pr_number")
    pr_number = int(pr_number) if pr_number else None
    pr = gh.pr(pr_number) if (gh is not None and pr_number) else None
    gh_known = pr is not None

    if pr is not None:
        pr_state: str | None = pr.state
        pr_url: str | None = pr.url or f"https://github.com/{repo}/pull/{pr_number}"
    elif pr_number:
        # Local view only — say nothing about merge state we did not observe.
        pr_state = None
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
    else:
        pr_state, pr_url = None, None

    if gh_known:
        merged = pr_state == "merged"
        has_pr = pr_state in ("open", "merged")
    else:
        merged = state in LOCAL_MERGED_STATES
        has_pr = bool(pr_number) and state in LOCAL_PR_STATES

    live = _is_live(state)
    settled_ok = not live and state not in FAILED_STATES | HUMAN_STATES | IGNORED_STATES
    # ``verified``: GitHub confirmed the delivery fact (or none is needed).
    # A delivery only the LOCAL view claims never yields a terminal ``done``.
    verified = True
    if level in (DeliveryLevel.AUTO_MERGE,):
        delivered = merged
        verified = gh_known
    elif level is DeliveryLevel.PUSH_TO_MAIN:
        # No PR on this path: the default branch IS the delivery.
        delivered = merged or state in LOCAL_MERGED_STATES
        merged = delivered
    elif level in (DeliveryLevel.PR, DeliveryLevel.DRAFT_PR):
        delivered = has_pr
        verified = gh_known
    elif level is DeliveryLevel.BRANCH:
        branch = row.get("github_branch")
        exists = gh.branch_exists(branch) if (gh is not None and branch) else None
        delivered = settled_ok and (exists if exists is not None else True)
        verified = exists is not None
    else:  # NONE: committed locally, nothing pushed
        delivered = settled_ok

    if state in IGNORED_STATES:
        kind = "ignored"
    elif delivered:
        kind = "delivered" if verified else "unverified"
    elif state in HUMAN_STATES or is_dependency_cap_parked(state, row.get("last_rejection_reason")):
        kind = "human"
    elif live:
        kind = "live"
    else:
        kind = "failed"
    return _StoryView(row, pr, pr_number, pr_url, pr_state, delivered, merged, kind)


def _story_reason(row: dict[str, Any]) -> str:
    reason = row.get("last_rejection_reason") or row.get("error") or ""
    reason = " ".join(str(reason).split())
    return f": {reason[:160]}" if reason else ""


def _latest_ts(values: list[Any]) -> str:
    best: datetime | None = None
    for v in values:
        if not v:
            continue
        try:
            dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        if best is None or dt > best:
            best = dt
    return (best or datetime.now(UTC)).astimezone(UTC).isoformat()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def _status_for(ctx: _Ctx, ref: JobRef) -> dict[str, Any]:
    cfg: AppConfig = load_app_config(ref.app, ctx.root)
    meta = ref.meta
    level = effective_level(cfg.delivery, meta.get("delivery"))
    state_yaml = read_state_yaml(ref.dir_path)
    dir_status = _direction_status(ctx, ref, state_yaml)
    rows = _stories(ctx, ref)
    gh = ctx.github.view(cfg.repo)
    views = [_classify(r, level, cfg.repo, gh) for r in rows]
    counted = [v for v in views if v.kind != "ignored"]
    cancel = state_yaml.get(CANCEL_KEY) if isinstance(state_yaml.get(CANCEL_KEY), dict) else None

    why: str | None = None
    live = [v for v in counted if v.kind == "live"]
    human = [v for v in counted if v.kind == "human"]
    failed = [v for v in counted if v.kind == "failed"]

    if cancel is not None and not live:
        state = "cancelled"
        why = f"cancelled at {cancel.get('at', '?')} by {cancel.get('by', '?')}"
    elif not counted:
        if views:
            state, why = "failed", "every story was superseded by a sibling"
        elif dir_status == "created":
            from factory.directions.parser import parse_direction_dir

            direction = parse_direction_dir(ref.app, ref.dir_path)
            direction.status = dir_status
            if awaiting_operator_approval(direction):
                state = "needs_human"
                why = f"awaiting operator approval: {approval_blocked_reason(direction)}"
            else:
                state = "queued"
                why = "waiting for pm-sync on the next factory tick"
        elif dir_status == "pm-validated":
            state, why = "triaging", "PM validated the direction; stories are being created"
        elif dir_status == "needs-direction":
            missing = state_yaml.get("missing") or []
            state = "needs_human"
            why = "PM marked the job needs-direction" + (
                f" (missing: {', '.join(map(str, missing))})" if missing else ""
            )
        else:
            state, why = "failed", f"direction is '{dir_status}' with no stories"
    elif all(v.kind in ("delivered", "unverified") for v in counted):
        unverified = [v for v in counted if v.kind == "unverified"]
        if unverified:
            state = "in_progress"
            why = (
                f"story {unverified[0].row.get('id')} looks delivered locally "
                f"({unverified[0].row.get('state')}) but GitHub could not confirm it"
            )
        else:
            state = "done"
    elif human:
        v = human[0]
        state = "needs_human"
        why = f"story {v.row.get('id')} is {v.row.get('state')}{_story_reason(v.row)}"
    elif live:
        state = "in_progress"
        # ``dependency_defer_count`` is not reset when the blocker clears, so
        # only a story that has never left ``story_created`` counts as waiting.
        deferred = [
            v
            for v in live
            if v.row.get("state") == StoryState.STORY_CREATED.value
            and int(v.row.get("dependency_defer_count") or 0) > 0
        ]
        if ctx.factory_block:
            state, why = "blocked", ctx.factory_block
        elif deferred and len(deferred) == len(live):
            state = "blocked"
            why = f"story {deferred[0].row.get('id')} is waiting on a dependency"
        else:
            v = live[0]
            why = f"story {v.row.get('id')} is {v.row.get('state')}"
        if cancel is not None:
            why = (
                f"cancel requested at {cancel.get('at', '?')} but story "
                f"{live[0].row.get('id')} is still {live[0].row.get('state')} "
                "(an in-flight handler wrote it back); re-run 'factory job cancel'"
            )
    else:
        state = "failed"
        v = failed[0] if failed else counted[0]
        why = f"story {v.row.get('id')} ended {v.row.get('state')}{_story_reason(v.row)}"

    if gh is not None and gh.errors:
        note = "GitHub unavailable, local view: " + gh.errors[0]
        why = f"{why}; {note}" if why else note

    stories = [
        {
            "id": v.row.get("id"),
            "state": v.row.get("state"),
            "pr_url": v.pr_url,
            "pr_state": v.pr_state,
            "branch": v.row.get("github_branch"),
        }
        for v in views
    ]
    raw_audit = state_yaml.get("audit")
    audit: list[Any] = raw_audit if isinstance(raw_audit, list) else []
    return {
        "job_id": ref.job_id,
        "app": ref.app,
        "title": str(meta.get("title") or ref.dir_path.name),
        "source": meta.get("source"),
        "external_id": meta.get("external_id"),
        "state": state,
        "terminal": state in TERMINAL_JOB_STATES,
        "pipeline": effective_pipeline(ctx.root, ref.app, meta.get("pipeline")),
        "delivery": level.value,
        "stories": stories,
        "pr_urls": [v.pr_url for v in views if v.pr_url],
        "merged": bool(counted) and all(v.merged for v in counted),
        "cost_usd": _cost(ctx, ref, [int(r["id"]) for r in rows if r.get("id") is not None]),
        "updated_at": _latest_ts(
            [r.get("updated_at") for r in rows]
            + [a.get("ts") for a in audit if isinstance(a, dict)]
            + [state_yaml.get("created_at"), (cancel or {}).get("at")]
        ),
        "why": why,
    }


def _ctx(root: Path, github: bool) -> _Ctx:
    conn = _ro_connect(state_db_path(root))
    return _Ctx(Path(root), conn, GitHubCache(enabled=github), _factory_block_reason(root, conn))


def job_status(root: Path, job_id: str, *, github: bool = True) -> dict[str, Any]:
    ref = find_job(root, job_id)
    ctx = _ctx(root, github)
    try:
        return _status_for(ctx, ref)
    finally:
        if ctx.conn is not None:
            ctx.conn.close()


def list_jobs(
    root: Path,
    *,
    source: str | None = None,
    active: bool = False,
    app: str | None = None,
    github: bool = True,
) -> dict[str, Any]:
    ctx = _ctx(root, github)
    jobs: list[dict[str, Any]] = []
    try:
        for ref in iter_jobs(root, app=app):
            if source and str(ref.meta.get("source") or "") != source:
                continue
            status = _status_for(ctx, ref)
            if active and status["terminal"]:
                continue
            jobs.append(status)
    finally:
        if ctx.conn is not None:
            ctx.conn.close()
    return {"jobs": jobs}


def cancel_job(root: Path, job_id: str, *, by: str = "factory job cancel") -> dict[str, Any]:
    """Stop dispatch for the job: park live stories, close the direction.

    Never deletes evidence: worktrees, branches, PRs, logs and spend stay.
    Live stories move to ``closed_by_operator`` (terminal, not mergeable, not
    auto-recoverable — so the chain stops driving them and auto-merge will not
    merge their PRs). Already-terminal stories are left exactly as they are.
    Idempotent: re-running re-parks anything an in-flight handler wrote back.
    """
    from factory.chain.handlers import get_story, persist_story
    from factory.directions.parser import parse_direction_dir
    from factory.directions.watcher import mark_direction_status, merge_state

    ref = find_job(root, job_id)
    db = state_db_path(root)
    now = datetime.now(UTC).isoformat()
    direction = parse_direction_dir(ref.app, ref.dir_path)

    state_yaml = read_state_yaml(ref.dir_path)
    if not isinstance(state_yaml.get(CANCEL_KEY), dict):
        merge_state(direction, {CANCEL_KEY: {"at": now, "by": by}})

    parked: list[int] = []
    ctx = _ctx(root, github=False)
    try:
        rows = _stories(ctx, ref)
    finally:
        if ctx.conn is not None:
            ctx.conn.close()
    for row in rows:
        if not _is_live(str(row.get("state") or "")):
            continue
        story = get_story(int(row["id"]), db)
        if story is None or not _is_live(story.state):
            continue
        from_state = story.state
        story.state = StoryState.CLOSED_BY_OPERATOR.value
        story.error = (
            f"cancelled via 'factory job cancel' ({job_id}) at {now} while in {from_state}"
        )
        persist_story(story, db_path=db)
        parked.append(int(row["id"]))

    try:
        if direction.status != "closed":
            mark_direction_status(direction, "closed", by=by, details={"job_cancelled": now})
    except Exception as exc:  # noqa: BLE001
        raise JobError("cancel_failed", f"could not close direction: {exc}") from exc
    return {"job_id": ref.job_id, "state": "cancelled", "stories_parked": parked}


__all__ = [
    "CANCEL_KEY",
    "JOB_STATES",
    "JobError",
    "cancel_job",
    "job_status",
    "list_jobs",
]
