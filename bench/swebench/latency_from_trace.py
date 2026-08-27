#!/usr/bin/env python3
"""Per-model-call latency, read from one run's archived ``sssf-events.jsonl``.

Written for M11 / the "per-call latency" row of ``PRE-REGISTRATION-SAIL-AB-
DRAFT.md``'s Measures table: separating a completion-window tier's QUEUE
latency from its GENERATION time needs finer granularity than
``result.json.wall_clock_s``, and the pre-registration names exactly one
source of truth for it — "the row's archived ``sssf-events.jsonl``" — and
exactly one re-derivation command: ``bench/swebench/latency_from_trace.py
<run_dir>``. $0, read-only, no network, no model call: it only ever opens a
file that already exists on disk.

WHAT THE TRACE ACTUALLY RECORDS, measured against a real archived trace
(``runs/getmoto__moto-9841/flash-solo/sssf-events.jsonl``, 2026-08-14) before
writing a single line of parsing logic here — the reason this docstring is as
long as it is:

* one ``ts`` per event, millisecond resolution, and the engine writes ONE
  ``thinking`` and/or ``agent_message`` event per model TURN, immediately
  followed by however many ``tool_call`` events that turn's response
  requested (0 for a final turn, 1-2 typically observed). There is NO event
  for "first streamed token" or "last streamed token" — ``pi`` drives
  synchronous streaming calls, but the ENGINE's tracer records a turn only
  once it has fully landed;
* ``tool_call`` events DO carry non-null ``started_at``/``ended_at`` — but
  measured against the surrounding timestamps, that pair brackets the TOOL's
  OWN execution (a few ms to tens of ms for read/grep/bash), not the model
  call: ``started_at`` lands within ~1ms of the preceding ``thinking``
  event's ``ts``, and ``ended_at`` matches the ``tool_call`` event's own
  ``ts``. Reusing it as model latency would silently mislabel tool
  execution time as generation time.

CONSEQUENCE, stated rather than worked around: **request-to-first-token and
first-token-to-last-token, as literally named in the pre-registration's
Measures row, are NOT separable from this trace.** The finest interval this
file can honestly re-derive per model call is the gap between the END of the
previous turn (its last tool_call, or the agent's ``agent_start``/prior
``phase_start`` for the first call of a phase) and the timestamp of THIS
turn's first content event (``thinking`` or ``agent_message``, whichever is
earlier — both are typically emitted at the same ts). That combined interval
covers Sail's queue wait AND the full generation together; it cannot be split
further without a change to what the engine's tracer records. This is
recorded as a correction in ``frozen/PRE-REGISTRATION-SAIL-AB.md``'s Resolved
review notes rather than silently reinterpreted, and every output row below
carries ``request_to_first_token_s`` and ``first_token_to_last_token_s`` as
explicit ``null`` (never a guessed split) alongside the one real figure,
``request_to_response_s``, so a reader who only skims field NAMES cannot
mistake a null for a zero.

Tool-execution time (the ``tool_call`` ``started_at``/``ended_at`` pair) is
reported separately, per call and aggregated, because it IS real and useful
context for wall-clock accounting even though it answers a different question
than model latency.

Grouped by phase (one phase == one agent invocation == one row of
``sssf-roster.yaml``'s roster), because a chain-shaped arm's events file holds
more than one role and blending their calls together would average two
different deployments' latencies into one meaningless number.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

_EVENTS_NAME = "sssf-events.jsonl"
_SSSF_TURNS_NAME = "sssf-turns.jsonl"
_CONTENT_TYPES = ("thinking", "agent_message")
_BOUNDARY_TYPES = frozenset({"agent_start", "agent_end", *_CONTENT_TYPES, "tool_call"})


def _parse_ts(value: Any) -> float | None:
    """ISO-8601 with an explicit offset -> POSIX seconds, or ``None``.

    ``datetime.fromisoformat`` handles the ``+00:00`` suffix the tracer always
    writes; a malformed or missing timestamp is a skipped event, not a crash —
    one bad line must not blank out an otherwise-readable trace.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def _read_events(events_path: Path) -> list[dict[str, Any]]:
    """Every JSON-object line, in file order. A bad line is skipped, not fatal.

    Read-only, no network — the whole point of re-deriving from an ARCHIVED
    file is that it costs nothing and cannot be wrong about what happened,
    only about what got written.
    """
    out: list[dict[str, Any]] = []
    with events_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(ev, dict):
                out.append(ev)
    return out


def _phase_role(events: list[dict[str, Any]]) -> dict[str, str]:
    """``phase_id -> role name``, from each phase's ``agent_start`` event.

    ``agent_start.name`` is the role (``builder``, ``reviewer``, ...) — the
    same field ``_sssf_usage_by_role`` reads in the adapter itself, so a
    latency row can be joined against a cost row by the same key.
    """
    roles: dict[str, str] = {}
    for ev in events:
        if ev.get("type") == "agent_start":
            phase_id = str(ev.get("phase_id") or "")
            name = str(ev.get("name") or "") or "unknown"
            if phase_id:
                roles[phase_id] = name
    return roles


def calls_for_run(run_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Every model call in ``run_dir``'s events file. ``(calls, warnings)``.

    One call == one model turn, bounded as described in the module docstring.
    A phase with an ``agent_start`` but no ``agent_end`` (a killed or crashed
    run) still yields whatever calls landed before the cut; its last call's
    tool time (if any) is simply not followed by a next request.
    """
    warnings: list[str] = []
    events_path = run_dir / _EVENTS_NAME
    if not events_path.exists():
        return [], [f"no {_EVENTS_NAME} under {run_dir} — nothing to derive"]
    events = _read_events(events_path)
    if not events:
        return [], [f"{events_path} exists but contains no parseable event lines"]
    role_of = _phase_role(events)

    # Bucket the events that matter for latency, per phase, preserving order —
    # everything else (config/log/gate_pass/handoff/phase_start/phase_end/
    # tree_digest) is irrelevant to a model call's timing and would only add
    # noise to the boundary-finding walk below.
    by_phase: dict[str, list[dict[str, Any]]] = {}
    phase_start_ts: dict[str, float] = {}
    for ev in events:
        t = ev.get("type")
        phase_id = str(ev.get("phase_id") or "")
        if not phase_id:
            continue
        if t == "phase_start" and phase_id not in phase_start_ts:
            ts = _parse_ts(ev.get("ts"))
            if ts is not None:
                phase_start_ts[phase_id] = ts
        if t in _BOUNDARY_TYPES:
            by_phase.setdefault(phase_id, []).append(ev)

    calls: list[dict[str, Any]] = []
    for phase_id, phase_events in by_phase.items():
        # A phase with NO agent_start never invoked an agent — e.g. the
        # harness's own `test_1` phase, whose single tool_call is the test
        # command, not a model call. Deriving a "call" from it puts a ~1 ms
        # non-model interval into the latency distribution AND makes the
        # turn-count cross-check below understate the real loss by one.
        if phase_id not in role_of:
            continue
        role = role_of.get(phase_id, "unknown")
        # The clock starts at this phase's agent_start (when the role's very
        # first request could have been sent); phase_start is the fallback
        # for a trace written before agent_start carried its own ts.
        clock: float | None = None
        for ev in phase_events:
            if ev.get("type") == "agent_start":
                clock = _parse_ts(ev.get("ts"))
                break
        if clock is None:
            clock = phase_start_ts.get(phase_id)
        if clock is None:
            warnings.append(
                f"phase {phase_id!r} ({role}): no usable start timestamp — its "
                "calls are skipped rather than latency-zeroed"
            )
            continue

        call_index = 0
        i = 0
        n = len(phase_events)
        while i < n:
            ev = phase_events[i]
            ev_type = ev.get("type")
            if ev_type not in _CONTENT_TYPES and ev_type != "tool_call":
                i += 1
                continue
            # One call/turn's group STARTS at its first event, whichever type
            # that is. A turn whose response was tool-calls-only — no
            # preceding ``thinking``/``agent_message`` at all — used to fall
            # through the old ``type not in _CONTENT_TYPES: skip`` branch one
            # tool_call at a time and never open its own group, silently
            # folding its whole duration into whatever call came next.
            # MEASURED on the reference row (getmoto__moto-9841/flash-solo):
            # 47 calls derived vs 51 ``assistant_turns`` declared in
            # sssf-turns.jsonl before this fix — see the cross-check below,
            # which stays in place even after the fix so a future format
            # drift cannot silently reintroduce the gap.
            if ev_type in _CONTENT_TYPES:
                response_ts = _parse_ts(ev.get("ts"))
                j = i + 1
                while j < n and phase_events[j].get("type") in _CONTENT_TYPES:
                    j += 1
            else:  # ev_type == "tool_call": the turn's response WAS the call(s)
                response_ts = _parse_ts(ev.get("started_at")) or _parse_ts(ev.get("ts"))
                j = i  # re-scanned by the tool_call loop below, from ev itself
            tool_durations: list[float] = []
            tool_call_count = 0
            last_event_ts = response_ts
            while j < n and phase_events[j].get("type") == "tool_call":
                tc = phase_events[j]
                s = _parse_ts(tc.get("started_at")) or _parse_ts(tc.get("ts"))
                e = _parse_ts(tc.get("ended_at")) or _parse_ts(tc.get("ts"))
                tool_call_count += 1
                if s is not None and e is not None:
                    tool_durations.append(max(0.0, e - s))
                if e is not None:
                    last_event_ts = e
                j += 1
            if response_ts is None or clock is None:
                warnings.append(
                    f"phase {phase_id!r} ({role}) call #{call_index}: unparseable "
                    "timestamp, skipped"
                )
                i = j
                continue
            request_to_response_s = round(max(0.0, response_ts - clock), 6)
            # SUMMED per-call durations, not the wall-clock SPAN from the
            # first tool's start to the last tool's end — a turn's tool calls
            # in this trace run sequentially, never overlapping, so the span
            # would silently include any gap between them as "execution".
            tool_exec_s = round(sum(tool_durations), 6) if tool_durations else None
            calls.append(
                {
                    "phase_id": phase_id,
                    "role": role,
                    "call_index": call_index,
                    "request_ts": clock,
                    "response_ts": response_ts,
                    # NEVER a guessed split — see the module docstring for why
                    # this trace format cannot support one.
                    "request_to_first_token_s": None,
                    "first_token_to_last_token_s": None,
                    "request_to_response_s": request_to_response_s,
                    "tool_calls_in_turn": tool_call_count,
                    "tool_exec_s": tool_exec_s,
                }
            )
            call_index += 1
            clock = last_event_ts if last_event_ts is not None else response_ts
            i = j
    calls.sort(key=lambda c: (c["phase_id"], c["call_index"]))

    # THE CROSS-CHECK, kept in place even after fixing the tool-call-only-turn
    # loss above — so a future format drift (or a bug this fix didn't catch)
    # can never be read as clean just because it produced SOME number of
    # calls. ``sssf-turns.jsonl``'s ``assistant_turns`` is the engine's own
    # per-role count, independent of anything this script derives.
    #
    # PER-ROLE, not a single campaign-wide total: a spurious call in one
    # phase/role (e.g. the harness's own non-agent phase, before the guard
    # above excluded it) could otherwise offset a real loss in another role
    # and the sum would read clean while a role's own count was still wrong.
    turns_path = run_dir / _SSSF_TURNS_NAME
    declared_by_role: dict[str, int] = {}
    if turns_path.exists():
        for ln in turns_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(ln)
                declared_by_role[str(row.get("role") or "unknown")] = (
                    declared_by_role.get(str(row.get("role") or "unknown"), 0)
                    + int(row.get("assistant_turns") or 0)
                )
            except (ValueError, AttributeError):
                pass
    for role, want in declared_by_role.items():
        got = sum(1 for c in calls if c["role"] == role)
        if got != want:
            warnings.append(
                f"role {role!r}: derived {got} calls but sssf-turns.jsonl "
                f"declares {want} assistant turns — {want - got} turn(s) are "
                "folded into a neighbouring call; per-call stats are NOT per-call"
            )
    return calls, warnings


def _aggregate(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    return {
        "count": len(values),
        "sum_s": round(sum(values), 6),
        "mean_s": round(statistics.fmean(values), 6),
        "median_s": round(statistics.median(values), 6),
        "min_s": round(ordered[0], 6),
        "max_s": round(ordered[-1], 6),
        "p90_s": round(ordered[int(0.9 * (len(ordered) - 1))], 6),
    }


def report(run_dir: Path) -> dict[str, Any]:
    calls, warnings = calls_for_run(run_dir)
    by_role: dict[str, list[dict[str, Any]]] = {}
    for c in calls:
        by_role.setdefault(c["role"], []).append(c)
    per_role_agg = {
        role: {
            "request_to_response_s": _aggregate(
                [c["request_to_response_s"] for c in rows]
            ),
            "tool_exec_s": _aggregate(
                [c["tool_exec_s"] for c in rows if c["tool_exec_s"] is not None]
            ),
        }
        for role, rows in by_role.items()
    }
    overall = _aggregate([c["request_to_response_s"] for c in calls])
    return {
        "run_dir": str(run_dir),
        "events_file": str(run_dir / _EVENTS_NAME),
        "warnings": warnings,
        "note": (
            "request_to_first_token_s and first_token_to_last_token_s are "
            "ALWAYS null: sssf-events.jsonl has no token-level streaming "
            "timestamps, only one landed-turn timestamp per model call, so "
            "the two legs the pre-registration names cannot be separated "
            "from this trace format. request_to_response_s is the one real, "
            "measured interval per call (queue wait + full generation, "
            "combined) — see this script's module docstring and "
            "frozen/PRE-REGISTRATION-SAIL-AB.md's Resolved review notes."
        ),
        "calls": calls,
        "per_role": per_role_agg,
        "overall_request_to_response_s": overall,
    }


def _print_table(data: dict[str, Any]) -> None:
    print(f"=== latency: {data['run_dir']} ===")
    if data["warnings"]:
        for w in data["warnings"]:
            print(f"  WARN: {w}")
    print(f"  {data['note']}")
    if not data["calls"]:
        print("  no model calls found")
        return
    print()
    header = f"{'role':<12} {'#':>3} {'req->resp (s)':>14} {'tools':>6} {'tool_exec (s)':>14}"
    print(header)
    print("-" * len(header))
    for c in data["calls"]:
        tool_exec = "-" if c["tool_exec_s"] is None else f"{c['tool_exec_s']:.3f}"
        print(
            f"{c['role']:<12} {c['call_index']:>3} "
            f"{c['request_to_response_s']:>14.3f} {c['tool_calls_in_turn']:>6} "
            f"{tool_exec:>14}"
        )
    print()
    print("per-role aggregates (request_to_response_s):")
    for role, agg in data["per_role"].items():
        r = agg["request_to_response_s"]
        if r.get("count"):
            print(
                f"  {role:<12} n={r['count']:<4} mean={r['mean_s']:.3f} "
                f"median={r['median_s']:.3f} p90={r['p90_s']:.3f} "
                f"max={r['max_s']:.3f}"
            )
    o = data["overall_request_to_response_s"]
    if o.get("count"):
        print(
            f"\noverall: n={o['count']} mean={o['mean_s']:.3f} "
            f"median={o['median_s']:.3f} p90={o['p90_s']:.3f} max={o['max_s']:.3f}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "run_dir",
        type=Path,
        help="a run directory containing an archived sssf-events.jsonl, e.g. "
             "bench/swebench/runs/<instance>/<arm> or a results-archive/<ts>/"
             "<instance>/<arm> snapshot",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="emit the full machine-readable report instead of the table",
    )
    args = ap.parse_args()
    run_dir: Path = args.run_dir
    if not run_dir.is_dir():
        print(f"not a directory: {run_dir}", file=sys.stderr)
        return 2
    data = report(run_dir)
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        _print_table(data)
    return 0 if data["calls"] or not data["warnings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
