"""Idle becomes a ping (019 AC6 / Flow C).

``factory/chain/idle.py`` (deleted 2026-08-07, 019 AC5) detected a drained app
and rotated through scanner personas to manufacture more work — it fired 957
times and reached a human zero times. This module replaces that whole shape:
when an app has no dispatchable work and no live human-filed direction, it
writes exactly ONE deduplicated ``operator_ping`` per **idle episode** and
files NO machine-authored direction. The operator decides what happens next
(file a direction, or ignore it).

Idle episode, precisely
------------------------
An idle episode STARTS the first tick where both hold:

  * zero dispatchable stories (``factory.chain.handlers.stories_in_flight``
    returns an empty list for the app) — see the note below on why this
    source, not ``factory_status._TERMINAL_STATES``, is authoritative.
  * zero LIVE human-filed directions (see ``_has_live_human_direction``).

The episode ENDS the first tick where either condition flips: a story gets
dispatched/advanced (``stories_in_flight`` becomes non-empty) or a human
files a new direction (or an existing one is still pending). Ending the
episode is entirely implicit — the next non-idle tick simply finds no reason
to ping and clears the persisted marker; there is no separate "work happened"
timestamp to track, because ``stories_in_flight`` and the human-direction
scan are themselves fresh, authoritative reads of "has anything happened"
every single tick.

Exactly one ping is written per episode: the FIRST idle tick writes the
marker (and the ``app_idle`` event); every subsequent idle tick, while the
marker is still present, is a no-op. A second episode (idle -> work -> idle
again) gets a second ping.

Why ``stories_in_flight``, not ``factory_status._TERMINAL_STATES``
--------------------------------------------------------------------
The deleted ``idle.py::_stories_in_flight`` counted stories using
``factory_status._TERMINAL_STATES``, which additionally treats
``blocked_review_nonconvergent`` and ``blocked_underspecified`` as terminal
(so those stories did NOT count as "in flight" -> the app could read as idle
even while a story sat in one of those states). ``factory.chain.handlers.
stories_in_flight`` is narrower: it is the literal list
``factory.chain.orchestrator.tick`` iterates to decide what to dispatch this
tick (see ``orchestrator.tick``'s ``stories = H.stories_in_flight(app, db)``
call). Using it here means "dispatchable work" in the ping can never disagree
with what the tick itself just did or didn't do — a re-derived terminal-state
set is exactly the kind of drift-prone duplication that caused silent-
detection-failure bugs elsewhere in this codebase. The tradeoff: an app whose
only story sits in ``blocked_review_nonconvergent`` / ``blocked_underspecified``
will NOT be pinged as idle here (those states are absent from ``handlers.
stories_in_flight``'s terminal set, so the story still counts as "in flight").
That story is not silently lost, though — it already surfaces via
``factory inbox``'s "Needs human action" table and ``factory why``.

Fail-safe direction: toward silence, not noise
-------------------------------------------------
This whole module exists because a detector that fires constantly and is
never acted on is worse than one that occasionally stays quiet a tick too
long. So every ambiguous case here resolves to "don't ping":

  * Ping-state file missing -> no active episode (normal case).
  * Ping-state file present and parses -> already pinged this episode,
    stay quiet.
  * Ping-state file present but UNREADABLE/CORRUPT (bad JSON, wrong shape)
    -> treated as "already pinged" (suppressed), and the read failure is
    surfaced as an error the caller can record (never silently swallowed,
    but never spammed either).
  * Cannot determine whether a live human direction exists (DB/parse error)
    -> assume one exists, i.e. do not ping this tick.

A write failure when *setting* the marker is best-effort (mirrors the
``idle_generator.json`` / issue-hygiene-marker precedent elsewhere in the
chain): the ``app_idle`` event still fires so ``stalled_stories``' consumer
keeps working, but a persistently failing filesystem could theoretically
re-ping on the next tick. That residual risk is accepted here exactly as it
is for the pre-existing markers this module's persistence follows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class IdlePingResult:
    """Outcome of one idle-ping evaluation for a single app."""

    fired: bool
    reason: str = ""
    idle_since: str | None = None
    last_delivered_unit: str | None = None
    error: str | None = None


def _ping_state_dir(software_factory_root: Path) -> Path:
    return Path(software_factory_root) / "state" / "idle_ping"


def _ping_state_path(software_factory_root: Path, app: str) -> Path:
    return _ping_state_dir(software_factory_root) / f"{app}.json"


def _load_ping_state(software_factory_root: Path, app: str) -> tuple[dict[str, Any] | None, str | None]:
    """Read the per-app ping marker.

    Returns ``(state, None)`` when no marker exists (no active episode) or
    the marker was read and parsed fine. Returns ``(None, error)`` when the
    marker EXISTS but is unreadable/malformed — the fail-safe case the
    caller must treat as "already pinged" (suppress), never as "no episode
    yet" (which would re-fire).
    """
    path = _ping_state_path(software_factory_root, app)
    if not path.exists():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"idle_ping state unreadable for app={app}: {exc!r}"
    if not isinstance(data, dict) or not isinstance(data.get("idle_since"), str):
        return None, f"idle_ping state malformed for app={app}"
    return data, None


def _write_ping_state(
    software_factory_root: Path,
    app: str,
    *,
    idle_since: str,
    pinged_at: str,
    last_delivered_unit: str | None,
) -> None:
    """Persist the marker. Best-effort — never raises."""
    path = _ping_state_path(software_factory_root, app)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "idle_since": idle_since,
                    "pinged_at": pinged_at,
                    "last_delivered_unit": last_delivered_unit,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    except OSError:
        return


def _clear_ping_state(software_factory_root: Path, app: str) -> None:
    """Delete the marker (the idle episode ended). Best-effort."""
    path = _ping_state_path(software_factory_root, app)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _last_delivered_unit(app: str, db_path: Path) -> str | None:
    """Return a short human-readable tag for the most recently touched story.

    "Last delivered unit" is shown in ``factory inbox`` so an operator who
    sees a ping has SOME context on what the factory was last doing before it
    went quiet, without needing to run ``factory queue``. Not restricted to
    terminal/deployed stories: any story's most recent ``updated_at`` is a
    reasonable proxy for "the last thing that happened", and an app that has
    never had a story yet correctly returns ``None``.
    """
    from sqlmodel import Session, select

    from factory.chain.handlers import _engine
    from factory.chain.state_machine import StoryRecord

    try:
        eng = _engine(db_path)
        with Session(eng) as session:
            rows = session.exec(select(StoryRecord).where(StoryRecord.app == app)).all()
    except Exception:  # noqa: BLE001 - a DB hiccup must never crash the ping
        return None
    if not rows:
        return None
    newest = max(rows, key=lambda r: (r.updated_at or "", r.id or 0))
    return f"{newest.slug} ({newest.state})"


def _has_live_human_direction(app: str, software_factory_root: Path, db_path: Path) -> bool:
    """True when a human-filed direction is still pending triage/decomposition.

    "Live" = status in ``PENDING_STATUSES`` (``created`` / ``needs-direction``)
    AND ``source`` resolves to one of ``approval._HUMAN_SOURCE_PREFIXES``
    (operator/cli/user/human), resolved DB-first exactly the way the
    operator-approval gate resolves it (``watcher.pending_directions`` already
    applies ``hydrate_direction_source`` before returning). A direction that
    has been pm-validated into stories is NOT re-checked here — if it still
    has stories in flight, rule 1 (``stories_in_flight``) already covers it;
    if it doesn't, it isn't "live" work waiting on anyone.

    Fail-safe: any lookup failure (missing DB, parse error) returns True —
    "assume a human direction exists" — so the ambiguous case never fires a
    ping, matching this module's fail-toward-silence design.
    """
    from factory.directions.approval import _HUMAN_SOURCE_PREFIXES, direction_source
    from factory.directions.watcher import pending_directions

    try:
        pendings = pending_directions(app, software_factory_root, db_path)
    except Exception:  # noqa: BLE001 - fail-safe: assume live human work exists
        return True
    for d in pendings:
        if direction_source(d).startswith(_HUMAN_SOURCE_PREFIXES):
            return True
    return False


def run_idle_ping_tick(
    software_factory_root: Path,
    app: str,
    db_path: Path,
    *,
    now: datetime | None = None,
) -> IdlePingResult:
    """Evaluate + (at most once per episode) fire the idle ping for ``app``.

    Caller contract: this function NEVER files a direction and never touches
    anything but the ``idle_ping`` marker + the ``app_idle`` event stream. It
    is safe to call every tick; the dedup lives entirely in the marker file.
    """
    from factory.chain.handlers import stories_in_flight
    from factory.manager.signals import write_event

    root = Path(software_factory_root)
    moment = now or datetime.now(UTC)

    state, corrupt_error = _load_ping_state(root, app)
    if corrupt_error is not None:
        # Fail SAFE toward silence: an unreadable marker must never be
        # treated as "no episode yet" (that would re-fire every tick — the
        # exact 957-fires class this module exists to end).
        return IdlePingResult(fired=False, reason="corrupt_state", error=corrupt_error)

    in_flight = stories_in_flight(app, db_path)
    idle_now = not in_flight and not _has_live_human_direction(app, root, db_path)

    if not idle_now:
        if state is not None:
            _clear_ping_state(root, app)
        return IdlePingResult(fired=False, reason="not_idle")

    if state is not None:
        # Already pinged for this episode — no new ping.
        return IdlePingResult(
            fired=False,
            reason="already_pinged",
            idle_since=state.get("idle_since"),
            last_delivered_unit=state.get("last_delivered_unit"),
        )

    # First idle tick of a NEW episode.
    idle_since = moment.isoformat()
    last_unit = _last_delivered_unit(app, db_path)
    pinged_at = moment.isoformat()
    _write_ping_state(
        root, app, idle_since=idle_since, pinged_at=pinged_at, last_delivered_unit=last_unit
    )
    # Re-emit ``app_idle`` on the same stream/key ``stalled_stories.
    # _last_idle_ts`` reads (``state/events/idle.ndjson``, ``event ==
    # "app_idle"``) — AC5 deleted the only writer; healthy_drain needs it
    # back or stall alarms lose their drain-suppression signal.
    write_event(
        "idle",
        {
            "event": "app_idle",
            "app": app,
            "idle_since": idle_since,
            "last_delivered_unit": last_unit,
        },
        software_factory_root=root,
    )
    return IdlePingResult(
        fired=True, reason="pinged", idle_since=idle_since, last_delivered_unit=last_unit
    )


def active_pings(software_factory_root: Path, apps: list[str]) -> list[dict[str, Any]]:
    """Return ``{"app", "idle_since", "last_delivered_unit"}`` for every app
    currently carrying an active (already-pinged) idle episode marker.

    Used by ``factory inbox``. Tolerant per-app: a corrupt marker for one app
    is skipped rather than hiding every other app's ping (mirrors the
    per-section try/except style the rest of ``inbox_cmd`` already uses).
    """
    root = Path(software_factory_root)
    out: list[dict[str, Any]] = []
    for app in apps:
        state, error = _load_ping_state(root, app)
        if error is not None or state is None:
            continue
        out.append(
            {
                "app": app,
                "idle_since": state.get("idle_since"),
                "last_delivered_unit": state.get("last_delivered_unit"),
            }
        )
    return out
