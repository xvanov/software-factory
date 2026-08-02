"""Persona runners.

Two entry points:

* ``sandbox_run`` — launches an OpenHands SDK ``Conversation`` against a real
  repo on local disk. Used for personas that need to read/write code (Dev,
  Test-Implementer, Onboarder, Reviewer-in-repo-mode, etc.).

* ``text_run`` — single ``litellm.completion()`` call with no tools. Used for
  text-only personas (PM classification, Reviewer-of-diff, Tech-Writer
  patches, etc.). Supports JSON-schema validation.

Both runners record a row in ``state/factory.db.runs`` keyed on persona +
timestamp + token usage + cost.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlmodel import Field, Session, SQLModel, create_engine

# Heavy SDK imports are deferred to inside sandbox_run() so the CLI can import
# this module without paying the OpenHands SDK import cost (and so tests that
# don't touch sandbox_run never need OpenHands installed).

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "state" / "factory.db"
_PERSONAS_DIR = Path(__file__).parent / "personas"

# Wall-clock ceiling for a single sandbox conversation run. The SDK's
# ``max_iteration`` bounds the number of tool calls but NOT a stalled LLM call,
# so a hung request (network stall, provider deadlock) could block a handler
# indefinitely — one dev tick was observed stuck for 51 minutes at ~0% CPU. A
# normal sandbox run finishes in 1-15 min; this ceiling is generous enough not
# to false-kill legitimate long runs (e.g. a ~15 min test_implementer) while
# still reaping a true hang. On timeout the run returns the same infra-retryable
# shape as any other pre-model failure (success=False, test_run_passed=None,
# zero cost), so handle_dev's infra circuit breaker re-dispatches without
# burning the retry budget. Override via FACTORY_SANDBOX_TIMEOUT_S.
_SANDBOX_WALL_CLOCK_TIMEOUT_S = int(os.environ.get("FACTORY_SANDBOX_TIMEOUT_S", "1800"))


# Markers that indicate a persona prompt was assembled with literal
# placeholders instead of real fetched data. Kept in sync with
# ``factory.chain.handlers._BROKEN_PROMPT_MARKERS`` — duplicated here so
# the logger has no chain->runner dependency. New markers should be added
# in BOTH places, and ideally added with a corresponding contract test.
_BROKEN_PROMPT_MARKERS: tuple[str, ...] = (
    "(fetched from GitHub by the chain",
    "placeholder for real-run",
    "(see {",
    # Diff-fetch failure text (see handlers._BROKEN_PROMPT_MARKERS for the
    # full rationale): the fetch is fail-closed now, so these must never
    # appear in a prompt; the scan catches a regression to fail-open.
    # Anchored on plumbing-specific prefixes (never generic prose like a bare
    # "returned rc=", which legitimate code/test output can contain) and
    # built by CONCATENATION so the contiguous literal never appears in this
    # repo's own source (a self-edit diff would otherwise trip the scan).
    "(gh pr diff " + "#",
    "...HEAD " + "returned rc=",
    "(gh pr diff " + "failed",
    "(git diff worktree " + "failed",
    "(could not resolve " + "writing worktree",
)


def _summarize_prompt_sections(prompt: str) -> dict[str, int]:
    """Return ``{section_header: char_count}`` for ``## `` headed sections.

    Lightweight markdown-style parser: every line starting with ``"## "`` is
    a section start; content until the next ``"## "`` (or end-of-string) is
    that section's body. Header lines themselves are excluded from the count.
    """
    sections: dict[str, int] = {}
    current_header: str | None = None
    current_chars = 0
    for line in prompt.splitlines():
        if line.startswith("## "):
            if current_header is not None:
                sections[current_header] = sections.get(current_header, 0) + current_chars
            current_header = line[3:].strip() or "(unnamed)"
            current_chars = 0
        elif current_header is not None:
            current_chars += len(line) + 1  # +1 for the newline
    if current_header is not None:
        sections[current_header] = sections.get(current_header, 0) + current_chars
    return sections


def _log_prompt_metadata(
    *,
    persona: str,
    prompt: str,
    model_id: str,
    story_id: int | None,
    software_factory_root: Path | None,
) -> None:
    """Best-effort: append one record to ``state/events/prompts.ndjson``.

    Records ONLY metadata (lengths, section header names, placeholder
    markers found, sha256 prefix) — never the prompt content itself.
    A failure here MUST NOT break the LLM call.
    """
    try:
        import hashlib

        from factory.manager.signals import write_event

        # The marker scan catches CHAIN personas (dev/review/tech_writer)
        # shipping literal placeholders in place of real fetched data. It does
        # NOT apply to the FMS's own manager_* personas: their prompts echo the
        # placeholder_prompts detector's flagged rows — marker strings and all —
        # back as analysis input, so scanning them produces guaranteed false
        # positives that the detector then re-escalates in a self-sustaining
        # loop. Never stamp markers on a manager_* prompt at the source.
        if persona.startswith("manager_"):
            markers_found: list[str] = []
        else:
            markers_found = [m for m in _BROKEN_PROMPT_MARKERS if m in prompt]
        section_lengths = _summarize_prompt_sections(prompt)
        digest = hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:16]
        write_event(
            "prompts",
            {
                "event": "prompt",
                "persona": persona,
                "story_id": story_id,
                "model_id": model_id,
                "prompt_length_total": len(prompt),
                "prompt_section_lengths": section_lengths,
                "placeholder_markers_found": markers_found,
                "prompt_hash": digest,
            },
            software_factory_root=software_factory_root,
        )
    except Exception:  # noqa: BLE001 — logging must never break the call
        pass


# Prompt BODIES are a separate stream from prompt metadata, with a separate
# retention policy, because they are ~3 orders of magnitude larger per row.
#
# Rotation window: 100 MB x 3 segments. Sized against measured production
# volume (`state/events/prompts.ndjson`, 45,868 rows): chain personas average
# 6 KB (ralph) to 190 KB (factory_improver) per prompt and total ~127 MB of
# body text across all history, so this window retains months of chain
# prompts. See ``_prompt_bodies_scope`` for why the manager personas — 1.58 GB
# on their own, 93% of all prompt text ever composed — are excluded by default.
_PROMPT_BODY_MAX_BYTES = 100_000_000
_PROMPT_BODY_KEEP = 3


def _prompt_bodies_scope() -> str:
    """Return the configured prompt-body capture scope.

    ``chain`` (default) captures every persona EXCEPT ``manager_*``; ``all``
    captures everything; ``off`` disables body capture entirely.

    The default excludes the manager personas deliberately, and the reason is
    volume, not privacy. ``manager_watcher`` alone accounts for 43,561 of the
    45,868 recorded prompts and 1.58 GB of prompt text — it runs on a 60 s
    cadence forever, while a chain persona runs a few times per story. Capturing
    manager bodies would roll the stream every few hours and evict exactly the
    dev/reviewer bodies the stream exists to retain (prompt optimization, retry
    forensics). An unbounded firehose that evicts the signal is worse than no
    stream at all.
    """
    scope = os.environ.get("FACTORY_PROMPT_BODIES", "chain").strip().lower()
    return scope if scope in ("chain", "all", "off") else "chain"


def _log_prompt_body(
    *,
    persona: str,
    prompt: str,
    model_id: str,
    story_id: int | None,
    software_factory_root: Path | None,
) -> None:
    """Best-effort: append the FULL prompt text to ``prompt_bodies.ndjson``.

    Unlike :func:`_log_prompt_metadata`, which records lengths and a truncated
    hash, this records the verbatim prompt plus the FULL sha256. It exists so
    prompt optimization and retry forensics have the actual input the model
    saw — a 16-char hash cannot be replayed, diffed, or optimized against.

    ``prompt_hash`` is the full digest of the same bytes
    ``_log_prompt_metadata`` hashes, so its first 16 chars join the two streams.

    A failure here MUST NOT break the LLM call.
    """
    try:
        if _prompt_bodies_scope() == "off":
            return
        if _prompt_bodies_scope() == "chain" and persona.startswith("manager_"):
            return

        import hashlib

        from factory.manager.signals import write_event

        write_event(
            "prompt_bodies",
            {
                "event": "prompt_body",
                "persona": persona,
                "story_id": story_id,
                "model_id": model_id,
                "prompt_length_total": len(prompt),
                "prompt_hash": hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest(),
                "prompt": prompt,
            },
            software_factory_root=software_factory_root,
            rotate_max_bytes=_PROMPT_BODY_MAX_BYTES,
            rotate_keep=_PROMPT_BODY_KEEP,
        )
    except Exception:  # noqa: BLE001 — logging must never break the call
        pass


def _log_response_body(
    *,
    persona: str,
    response: str,
    prompt: str,
    model_id: str,
    story_id: int | None,
    software_factory_root: Path | None,
    mode: str = "text",
    trajectory_path: str | None = None,
) -> None:
    """Best-effort: append the model's response text to ``response_bodies.ndjson``.

    The other half of :func:`_log_prompt_body`: prompts were captured verbatim,
    responses were not — a reviewer verdict or PM triage rationale could only be
    reconstructed from downstream side effects. This records the response text
    itself, hash-chained like every other stream.

    ``prompt_hash`` is the full sha256 of the SAME bytes ``_log_prompt_body``
    hashes, so a response row joins its prompt row exactly. ``response_hash``
    is the full sha256 of the response text. For sandbox runs (``mode=
    "sandbox"``) the response is the final assistant message and
    ``trajectory_path`` points at the full OpenHands trajectory copy-out.

    Scope and rotation deliberately REUSE the prompt-body mechanics
    (``_prompt_bodies_scope`` + the same 100 MB x 3 window) — one config
    surface for body capture, not two. Responses are typically far smaller
    than prompts (a reviewer verdict is ~100 tokens), so the shared window is
    generous. A failure here MUST NOT break the LLM call.
    """
    try:
        if _prompt_bodies_scope() == "off":
            return
        if _prompt_bodies_scope() == "chain" and persona.startswith("manager_"):
            return

        import hashlib

        from factory.manager.signals import write_event

        if not isinstance(response, str):
            # Some providers return content=None alongside tool calls; a
            # telemetry writer must record that shape, not raise on it.
            response = "" if response is None else str(response)
        payload: dict[str, Any] = {
            "event": "response_body",
            "persona": persona,
            "story_id": story_id,
            "model_id": model_id,
            "mode": mode,
            "response_length_total": len(response),
            "response_hash": hashlib.sha256(
                response.encode("utf-8", errors="replace")
            ).hexdigest(),
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest(),
            "response": response,
        }
        if trajectory_path is not None:
            payload["trajectory_path"] = trajectory_path
        write_event(
            "response_bodies",
            payload,
            software_factory_root=software_factory_root,
            rotate_max_bytes=_PROMPT_BODY_MAX_BYTES,
            rotate_keep=_PROMPT_BODY_KEEP,
        )
    except Exception:  # noqa: BLE001 — logging must never break the call
        pass


# Ceiling for a single copied-out OpenHands trajectory file. Measured on the
# pinned SDK (openhands-sdk 1.22.1): each persisted event is one compact JSON
# file — the system-prompt event is ~26 KB, message/action/observation events
# are hundreds of bytes to tens of KB — so a ~20-turn dev session lands in the
# single-digit-MB range. 100 MB is therefore a defensive cap against a
# pathological session (e.g. an observation echoing a huge file); when hit,
# the copy stops and a ``trajectory_truncated`` marker line records how many
# events were dropped.
_TRAJECTORY_MAX_BYTES = 100_000_000


def _trajectories_dir(software_factory_root: Path | None) -> Path:
    """Resolve ``state/events/trajectories`` with the same root resolution
    every event stream uses (explicit arg → ``FACTORY_STATE_ROOT`` → cwd)."""
    from factory.manager.signals import _events_dir

    return _events_dir(software_factory_root) / "trajectories"


def _capture_trajectory(
    *,
    events_src: Path,
    story_id: int | None,
    attempt: int,
    software_factory_root: Path | None,
    max_bytes: int = _TRAJECTORY_MAX_BYTES,
) -> str | None:
    """Copy an OpenHands persisted event stream out as ONE ndjson trajectory.

    The pinned SDK (1.22.1) persists each conversation event as a separate
    compact-JSON file, ``<persistence_dir>/<conv_id.hex>/events/
    event-NNNNN-<uuid>.json``, written incrementally as the run progresses
    (so a crashed or timed-out run still leaves a partial trail). This
    assembles those files, in sequence order, into
    ``state/events/trajectories/<story>-<attempt>.ndjson`` — the agent's full
    reasoning/tool-call/observation record, captured whole, no filtering.

    Returns the written path, or ``None`` when there was nothing to copy.
    Best-effort by contract: never raises.
    """
    try:
        event_files = sorted(Path(events_src).glob("event-*.json"))
        if not event_files:
            return None
        dest_dir = _trajectories_dir(software_factory_root)
        dest_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{story_id if story_id is not None else 'nostory'}-{attempt}"
        dest = dest_dir / f"{stem}.ndjson"
        if dest.exists():
            # A retry that reuses the same (story, attempt) key — e.g. a
            # review-cycle re-dispatch — must not overwrite an earlier
            # trajectory. One deterministic fallback, no rename loop.
            dest = dest_dir / f"{stem}-{int(time.time() * 1000)}.ndjson"
        written = 0
        events_written = 0
        with dest.open("w", encoding="utf-8") as out:
            for i, f in enumerate(event_files):
                try:
                    raw = f.read_text(encoding="utf-8", errors="replace")
                    line = json.dumps(json.loads(raw), separators=(",", ":"))
                except Exception:  # noqa: BLE001 — one bad event must not lose the rest
                    line = json.dumps(
                        {"event": "trajectory_event_unreadable", "file": f.name}
                    )
                line_bytes = len(line.encode("utf-8", errors="replace")) + 1
                if written + line_bytes > max_bytes:
                    out.write(
                        json.dumps(
                            {
                                "event": "trajectory_truncated",
                                "bytes_written": written,
                                "events_written": events_written,
                                "events_omitted": len(event_files) - i,
                                "max_bytes": max_bytes,
                            }
                        )
                        + "\n"
                    )
                    break
                out.write(line + "\n")
                written += line_bytes
                events_written += 1
        return str(dest)
    except Exception:  # noqa: BLE001 — trajectory capture must never break the run
        return None


def _extract_cached_tokens(usage: Any) -> int:
    """Return cache-read prompt tokens from a litellm ``Usage``-shaped object.

    LiteLLM normalizes both the DeepSeek wire field (``prompt_cache_hit_
    tokens``) and the OpenAI-style field (native ``prompt_tokens_details.
    cached_tokens``, which Azure's gpt-5.4/gpt-5.3-codex deployments also
    use) into the same ``usage.prompt_tokens_details.cached_tokens``
    location — so one accessor covers every model in ``routes.yaml``.
    Defensive against ``usage`` being a plain dict (some call paths) or a
    ``Usage``-like object (the common case); never raises.
    """
    try:
        details: Any = None
        if hasattr(usage, "get"):
            details = usage.get("prompt_tokens_details")
        elif isinstance(usage, dict):
            details = usage.get("prompt_tokens_details")
        if details is None:
            return 0
        cached = getattr(details, "cached_tokens", None)
        if cached is None and isinstance(details, dict):
            cached = details.get("cached_tokens")
        return int(cached or 0)
    except Exception:
        return 0


# --------------------------------------------------------------------------- #
# Public dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LLMConfig:
    """Minimal LLM config the runner needs.

    ``model`` is a LiteLLM-format id (e.g. ``deepseek/deepseek-coder``).
    ``api_key`` may be None — in that case the runner falls back to the
    appropriate provider env var (``DEEPSEEK_API_KEY``, ``ANTHROPIC_API_KEY``,
    ``OPENAI_API_KEY``).
    ``base_url`` overrides the provider default.
    """

    model: str
    api_key: str | None = None
    base_url: str | None = None


@dataclass
class RunResult:
    success: bool
    files_changed: list[str] = field(default_factory=list)
    test_run_passed: bool | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    summary: str = ""
    # Richer signal extracted from the sandbox conversation for cross-retry
    # memory. ``last_assistant_message`` is the verbatim final assistant
    # message (capped); ``recent_tool_calls`` is the trailing window of
    # (tool, args_excerpt, observation_excerpt) so the next retry can see
    # *what dev was doing* when it gave up — not just the test-output tail.
    # ``self_summary`` is dev's own 3-5 sentence reflection (parsed from
    # the ``SELF_SUMMARY:`` marker the dev persona prompt requests). All
    # three fall back to empty / [] when the conversation didn't expose
    # them; callers must tolerate the empty case.
    last_assistant_message: str = ""
    recent_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    self_summary: str = ""
    # Explicit "the sandbox failed BEFORE any model work" signal. True only for
    # genuine pre-model breakage (no API key, SDK import failure, a stalled LLM
    # request killed by the wall-clock timeout before it produced any usage).
    # The dev handler's ``_is_premodel_infra_failure`` prefers this flag over
    # the older zero-cost/None heuristic: a run that DID spend model tokens and
    # then raised (e.g. during metrics extraction or conversation teardown) is
    # a genuine failed dev attempt — it must consume a dev retry, NOT be bounced
    # back for free as "infra". Defaults False so every non-infra return path
    # (including a normal red run) is correctly counted as a real attempt.
    premodel_infra: bool = False
    # Whether the usage/cost numbers on this result are TRUSTWORTHY, as opposed
    # to merely zero. Three-valued on purpose:
    #   None  — not applicable: no model call was attempted (dry-run, pre-model
    #           infra failure). Zero usage is the correct, known answer.
    #   True  — a model call happened and the provider reported usage we read
    #           successfully.
    #   False — a model call happened but the usage/cost read failed or the
    #           provider did not report a cost. The numbers are a floor, not a
    #           measurement.
    # Without this, ``cost_usd == 0.0`` is overloaded three ways and every
    # aggregator silently treats "unknown" as "free" (measured on the live
    # ledger: 1016 text runs with output tokens but zero recorded cost).
    usage_reliable: bool | None = None


# --------------------------------------------------------------------------- #
# DB model
# --------------------------------------------------------------------------- #


class Run(SQLModel, table=True):
    __tablename__ = "runs"

    id: int | None = Field(default=None, primary_key=True)
    ts: str
    persona: str
    model: str
    mode: str  # "sandbox" | "text" | "sandbox-dry-run"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    success: bool = False
    story_path: str | None = None
    repo_path: str | None = None
    error: str | None = None
    # Observability / EBS instrumentation. ``duration_s`` is the wall-clock
    # time the runner spent inside the LLM call (set by sandbox_run /
    # text_run on exit). ``story_id`` lets the TUI tie a run back to its
    # story for per-direction progress / velocity sampling. ``model_tier``
    # is the route's difficulty bucket (standard/hard) when available.
    duration_s: float | None = None
    story_id: int | None = None
    model_tier: str | None = None
    # D003 — complete per-unit attribution. ``story_id`` alone undercounts
    # per-direction / per-app rollups whenever a run predates story creation
    # (PM/analyst) or is a scheduled app-level persona (ralph/bug_hunter/
    # security/ux_auditor) — those legitimately have no story_id but DO have
    # a known app. Chain-persona runs (sm/dev/reviewer/tech_writer/
    # onboarder) are expected to carry all three.
    direction_id: str | None = None
    app: str | None = None
    # D003 follow-up — the cached/fresh token SPLIT, not just the blended
    # cost_usd. cost_usd for models with an estimated cache-read rate (see
    # ``factory.providers.azure_foundry``) mixes an exact-rate fresh-token
    # cost with a guessed-rate cached-token cost; without the split, that
    # guess can never be recomputed once a real rate is known, and
    # historical rows would be permanently unfixable. NULL means "unknown /
    # not applicable" (pre-model failures, dry-runs) — 0 means "a real call
    # happened and had zero cache hits".
    cached_input_tokens: int | None = None
    # The persisted half of ``RunResult.premodel_infra`` / ``usage_reliable``.
    # Both were previously in-memory only, so the ledger could not tell a
    # dry-run from a pre-model infra failure from a real call whose cost we
    # failed to read — all three land as ``cost_usd = 0``. Every downstream
    # aggregator (settings/spend.py, settings/audit.py, observability/queries.py,
    # the cost_spike + fms_yield detectors) inferred from that zero, so an
    # unreadable provider response looked exactly like a free run.
    #
    # NULL on both = a legacy row written before these columns existed; readers
    # must fall back to the old heuristic rather than assuming False.
    premodel_infra: bool | None = None
    usage_reliable: bool | None = None


def _engine(db_path: Path | None = None) -> Any:
    path = db_path or _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    # Run idempotent schema migrations so old DBs gain ``duration_s`` /
    # ``story_id`` / ``model_tier`` on ``runs`` and ``points`` /
    # ``estimated_seconds`` on ``stories`` without dropping data.
    from factory.observability.schema import migrate

    migrate(path)
    engine = create_engine(f"sqlite:///{path}", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


def _record_run(
    *,
    persona: str,
    model: str,
    mode: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    success: bool,
    story_path: str | None,
    repo_path: str | None,
    error: str | None,
    db_path: Path | None = None,
    duration_s: float | None = None,
    story_id: int | None = None,
    model_tier: str | None = None,
    direction_id: str | None = None,
    app: str | None = None,
    cached_input_tokens: int | None = None,
    premodel_infra: bool | None = None,
    usage_reliable: bool | None = None,
    software_factory_root: Path | None = None,
    started_at: str | None = None,
) -> None:
    ended_at = datetime.now(UTC).isoformat()
    redacted_error = redact_secrets(error) if error is not None else None
    bounded_error = truncate_error(redacted_error) if redacted_error is not None else None
    engine = _engine(db_path)
    with Session(engine) as session:
        row = Run(
            ts=ended_at,
            persona=persona,
            model=model,
            mode=mode,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            success=success,
            story_path=story_path,
            repo_path=repo_path,
            error=bounded_error,
            duration_s=duration_s,
            story_id=story_id,
            model_tier=model_tier,
            direction_id=direction_id,
            app=app,
            cached_input_tokens=cached_input_tokens,
            premodel_infra=premodel_infra,
            usage_reliable=usage_reliable,
        )
        session.add(row)
        session.commit()

        # Count prior runs with the same story_id + persona to derive attempt_n.
        # Do this inside the same session so the row we just committed is counted.
        try:
            from sqlmodel import select as _select

            attempt_n = (
                session.exec(
                    _select(Run).where(
                        Run.persona == persona,
                        Run.story_id == story_id,
                    )
                )
                .all()
                .__len__()
            )
        except Exception:
            attempt_n = 1

    # Emit the structured signal — best-effort, never raises.
    try:
        from factory.manager.signals import write_run_event

        _root = software_factory_root or (
            Path(db_path).parent.parent if db_path is not None else None
        )
        write_run_event(
            started_at=started_at or ended_at,
            ended_at=ended_at,
            duration_s=duration_s,
            cost_usd=cost_usd,
            success=success,
            error=error,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
            model_tier=model_tier,
            attempt_n=attempt_n,
            story_id=story_id,
            persona=persona,
            worktree_path=repo_path,
            software_factory_root=_root,
        )
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_REDACTION_TOKEN = "[REDACTED]"

# Pattern for hex-encoded secrets (≥32 hex chars, case-insensitive), e.g.
# ``0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef``.
# Matched with word-boundary anchors to avoid clipping legitimate hex data
# (git SHAs, SHA-256 digests, etc.) unless the run is absurdly long.
_HEX_SECRET_RE = r"\b[A-Fa-f0-9]{64,}\b"

# Pattern for base64-encoded secrets (≥32 base64 characters). The alphabet
# is [A-Za-z0-9+/=]; we require the chunk to be at least 32 chars of the
# non-padding alphabet before allowing optional trailing padding, which
# captures real API key material like ``sk-helper-<b64>`` after the prefix.
_B64_SECRET_RE = r"[A-Za-z0-9+/]{32,}=*"


def redact_secrets(text: str) -> str:
    """Return *text* with common provider-secret substrings replaced by ``[REDACTED]``.

    Covers:
    * OpenAI ``sk-...`` and Anthropic ``sk-ant-...`` tokens
    * ``Bearer <token>`` and ``Authorization: ...`` header values
    * Long hex and base64 runs that match known key shapes
    * Already-redacted text is left unchanged (idempotent).
    """
    import re

    patterns: list[str] = [
        # sk-ant-... (Anthropic) — must precede sk-... so the longer
        # ``sk-ant-api03-...`` form is fully consumed.
        r"sk-ant-[A-Za-z0-9_\-]{20,}",
        # sk-... (OpenAI project keys are sk-proj-... but many are sk-<random>)
        r"sk-[A-Za-z0-9_\-]{20,}",
        # Bearer <token> — captured until whitespace/end-of-string
        r"Bearer\s+[A-Za-z0-9+\-/=]{20,}",
        # Authorization: ... — captures the full header value up to newline
        r"Authorization:\s*[^\n]*",
        # Long hex runs (≥64 hex chars)
        _HEX_SECRET_RE,
        # Long base64 runs (≥32 base64 chars)
        _B64_SECRET_RE,
    ]

    combined = "|".join(patterns)
    return re.sub(combined, _REDACTION_TOKEN, text)


_DEFAULT_ERROR_MAX_LENGTH = 4000


def truncate_error(text: str, max_length: int = _DEFAULT_ERROR_MAX_LENGTH) -> str:
    """Return *text* truncated to fit within *max_length* with a ``...[truncated N chars]`` marker.

    Text at or under *max_length* is returned unchanged. The total output
    (including marker) never exceeds *max_length*, making the helper naturally
    idempotent.
    """
    if max_length <= 0:
        return ""
    if len(text) <= max_length:
        return text

    marker_template = "...[truncated {removed} chars]"
    keep_len = max_length

    while True:
        removed = len(text) - keep_len
        marker = marker_template.format(removed=removed)
        new_keep_len = max_length - len(marker)
        if new_keep_len < 0:
            new_keep_len = 0
        if new_keep_len == keep_len:
            break
        keep_len = new_keep_len

    return (text[:keep_len] + marker)[:max_length]


def _read_persona_prompt(persona: str) -> str:
    """Return ONLY the system-prompt body for ``persona``.

    Delegates to the persona loader, which strips YAML frontmatter. That
    stripping is the point: a persona that grows a ``model:`` key must not start
    describing its own routing to itself inside its system prompt. Files without
    frontmatter (every persona today) are returned unchanged.

    ``PersonaError`` is re-raised as ``FileNotFoundError`` for a missing file so
    the eight existing callers keep the exception type they handle.
    """
    from factory.personas.loader import PersonaError, read_persona_prompt

    try:
        return read_persona_prompt(persona, personas_dir=_PERSONAS_DIR)
    except PersonaError as exc:
        if "missing" in str(exc):
            raise FileNotFoundError(str(exc)) from exc
        raise


def _provider_env_key(model: str) -> str | None:
    """Return the env-var name that holds the API key for ``model``.

    Delegates to ``factory.model_router.provider_env_key`` — the single
    source of truth for the prefix→env mapping (the router also uses it for
    key-aware route degradation). Two Azure prefixes are kept distinct:

    * ``azure_ai/...``  → Azure AI Foundry          → ``AZURE_AI_API_KEY``
    * ``azure/...``     → Azure OpenAI / Cognitive  → ``AZURE_API_KEY``

    The two surfaces share neither URL shape nor key scope.
    """
    from factory.model_router import provider_env_key

    return provider_env_key(model)


def _resolve_api_key(cfg: LLMConfig) -> str | None:
    # Bootstrap Azure env remap on first resolution. Covers BOTH surfaces:
    #   * AZURE_FOUNDRY_* → AZURE_AI_API_* (Foundry / azure_ai)
    #   * AZURE_ENDPOINT  → AZURE_API_BASE (Azure-OpenAI / azure)
    # ...and sets ``litellm.drop_params = True`` so gpt-5.x reasoning models
    # accept ``max_tokens`` (auto-translated to ``max_completion_tokens``).
    from factory.providers.azure_foundry import ensure_bootstrapped

    ensure_bootstrapped()
    if cfg.api_key:
        return cfg.api_key
    env_key = _provider_env_key(cfg.model)
    if env_key:
        value = os.environ.get(env_key)
        if value:
            return value
        # Fallbacks for the two Azure surfaces — accept legacy names too.
        if env_key == "AZURE_AI_API_KEY":
            return os.environ.get("AZURE_FOUNDRY_API_KEY")
        if env_key == "AZURE_API_KEY":
            # Same-shape key — accept the Foundry-named var as a fallback so
            # operators with both surfaces in one .env don't duplicate the key.
            return os.environ.get("AZURE_FOUNDRY_API_KEY")
    return None


def _persona_llm_overrides(persona: str, model_id: str, difficulty: str) -> dict[str, Any]:
    """Per-persona LLM constructor overrides from routes.yaml's ``llm_params``.

    Best-effort by design: a malformed ``llm_params`` block must degrade to
    "no overrides" (SDK defaults), never kill a sandbox run.
    """
    try:
        from factory.model_router import llm_params_for

        return llm_params_for(persona, model_id, difficulty=difficulty)
    except Exception as exc:
        print(f"[runner] llm_params lookup failed for {persona}/{model_id}: {exc}")
        return {}


def _build_agent_for_persona(persona: str, llm: Any, get_default_agent: Any) -> Any:
    """Construct the OpenHands agent, honoring an optional preset override
    from routes.yaml's ``presets`` block (e.g. ``dev: planning``).

    Unknown preset names and preset import failures degrade to the default
    agent — presets are an experiment surface, not a hard dependency.
    """
    try:
        from factory.model_router import preset_for

        preset = preset_for(persona)
    except Exception:
        preset = None
    if preset == "planning":
        try:
            from openhands.tools.preset.planning import get_planning_agent

            return get_planning_agent(llm=llm)
        except Exception as exc:
            print(f"[runner] planning preset unavailable for {persona}: {exc}")
    elif preset:
        print(f"[runner] unknown preset {preset!r} for {persona}; using default agent")
    return get_default_agent(llm=llm, cli_mode=True)


def _scan_repo_for_changed_files(repo_path: Path) -> list[str]:
    """Best-effort: ask git for the working-tree change set."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        # Porcelain v1: "XY path"
        if len(line) < 4:
            continue
        files.append(line[3:].strip())
    return files


# Cap for extracted strings — kept in module scope so tests can assert
# against the limits. ``RECENT_TOOL_CALL_WINDOW`` is the number of trailing
# action/observation pairs we keep; each gets its args + observation
# truncated to ``_TOOL_FIELD_CHAR_CAP`` so the JSON we persist on the
# story stays a few KB, not a few MB.
RECENT_TOOL_CALL_WINDOW = 8
_TOOL_FIELD_CHAR_CAP = 600
_LAST_MSG_CHAR_CAP = 2000

# Marker the dev persona emits for its 3-5-sentence self-summary at the end
# of a run. Falls back to the trailing assistant message if absent.
_SELF_SUMMARY_MARKER = "SELF_SUMMARY:"


def _extract_self_summary(last_assistant_message: str) -> str:
    """Pull the ``SELF_SUMMARY:`` paragraph out of the last assistant message.

    The dev persona prompt asks for ``SELF_SUMMARY: <3-5 sentences>``
    before exit. If the marker is present, we return the text following
    it (up to the next blank line or end-of-message). If not, we fall
    back to the trailing 500 chars of the message — better than nothing
    so the next retry has *some* free-form context to read.
    """
    if not last_assistant_message:
        return ""
    idx = last_assistant_message.find(_SELF_SUMMARY_MARKER)
    if idx == -1:
        return last_assistant_message[-500:].strip()
    tail = last_assistant_message[idx + len(_SELF_SUMMARY_MARKER) :].lstrip()
    # Stop at a blank-line boundary so we don't pull in a wall of trailing
    # tool logs the persona may have appended.
    blank = tail.find("\n\n")
    return (tail[:blank] if blank != -1 else tail).strip()[:_LAST_MSG_CHAR_CAP]


def _extract_conversation_memory(conversation: Any) -> tuple[str, list[dict[str, Any]]]:
    """Pull cross-retry memory signal from an OpenHands ``Conversation``.

    Returns ``(last_assistant_message, recent_tool_calls)``. Each tool
    call dict has the shape::

        {
          "tool": "<name>",          # e.g. "execute_bash", "str_replace_editor"
          "args": "<truncated>",     # JSON-ish excerpt of the call args
          "observation": "<truncated>",  # truncated tool output
        }

    Robust to SDK shape changes — every attribute access is defensive,
    every coercion goes through ``str()`` with a fallback. A failure here
    must not break the run; we return ``("", [])``.
    """
    last_msg = ""
    pairs: list[dict[str, Any]] = []
    try:
        state = getattr(conversation, "state", None)
        if state is None:
            return last_msg, pairs
        events = list(getattr(state, "events", []) or [])
    except Exception:
        return last_msg, pairs

    # Walk events in order. Build (action, observation) pairs by matching
    # tool_call_id when the SDK exposes one; otherwise pair consecutive
    # action+observation events in the stream.
    actions_by_id: dict[str, dict[str, Any]] = {}
    ordered_pairs: list[dict[str, Any]] = []
    for ev in events:
        kind = (getattr(ev, "kind", None) or type(ev).__name__).lower()
        # Capture assistant messages — last one wins.
        if "message" in kind:
            source = getattr(ev, "source", "") or ""
            role = getattr(ev, "role", "") or source
            if str(role).lower() in {"assistant", "agent"}:
                content = _stringify_message_content(ev)
                if content:
                    last_msg = content
        # Tool actions.
        if "action" in kind and "agent" not in kind and "rejection" not in kind:
            tool_name = (
                getattr(ev, "tool_name", None)
                or getattr(ev, "name", None)
                or getattr(getattr(ev, "action", None), "tool", None)
                or "tool"
            )
            args_excerpt = _safe_truncate(_stringify_action_args(ev), _TOOL_FIELD_CHAR_CAP)
            tcid = getattr(ev, "tool_call_id", None)
            record = {"tool": str(tool_name), "args": args_excerpt, "observation": ""}
            if tcid is not None:
                actions_by_id[str(tcid)] = record
            ordered_pairs.append(record)
            continue
        # Observations — attach to the matching action by id, or to the
        # most-recent action in stream order if no id match.
        if "observation" in kind:
            obs_text = _safe_truncate(_stringify_observation(ev), _TOOL_FIELD_CHAR_CAP)
            tcid = getattr(ev, "tool_call_id", None)
            if tcid is not None and str(tcid) in actions_by_id:
                actions_by_id[str(tcid)]["observation"] = obs_text
            elif ordered_pairs:
                ordered_pairs[-1]["observation"] = obs_text

    # Keep just the trailing window so the persisted JSON stays bounded.
    pairs = ordered_pairs[-RECENT_TOOL_CALL_WINDOW:]
    last_msg = (last_msg or "")[-_LAST_MSG_CHAR_CAP:]
    return last_msg, pairs


def _stringify_message_content(ev: Any) -> str:
    """Best-effort extract of a message event's text content."""
    # Common shape: ev.llm_message.content is a list of dicts {type, text}
    # OR ev.message.content is a similar list. The SDK has shifted naming
    # across versions; try a few attribute paths.
    for attr in ("llm_message", "message"):
        msg = getattr(ev, attr, None)
        if msg is None:
            continue
        content = getattr(msg, "content", None)
        if content is None:
            continue
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for c in content:
                if isinstance(c, dict):
                    text = c.get("text") or c.get("content") or ""
                    parts.append(str(text))
                else:
                    text = getattr(c, "text", None) or str(c)
                    parts.append(text)
            joined = "\n".join(p for p in parts if p)
            if joined:
                return joined
    # Fallback: model_dump() and pull a "content" field.
    try:
        data = ev.model_dump()
    except Exception:
        return ""
    for path in (("llm_message", "content"), ("message", "content"), ("content",)):
        node: Any = data
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, str):
            return node
        if isinstance(node, list):
            return "\n".join(str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in node)
    return ""


def _stringify_action_args(ev: Any) -> str:
    """Pull a JSON-ish representation of a tool call's args off the event."""
    for attr in ("arguments", "args", "tool_args", "action"):
        val = getattr(ev, attr, None)
        if val is None:
            continue
        try:
            return json.dumps(val, default=str)
        except Exception:
            return str(val)
    try:
        data = ev.model_dump()
        return json.dumps(data, default=str)
    except Exception:
        return ""


def _stringify_observation(ev: Any) -> str:
    """Pull the text body of a tool observation event."""
    for attr in ("output", "content", "result", "text", "observation"):
        val = getattr(ev, attr, None)
        if isinstance(val, str) and val:
            return val
        if val is None:
            continue
        try:
            return json.dumps(val, default=str)
        except Exception:
            return str(val)
    try:
        data = ev.model_dump()
        return json.dumps(data, default=str)
    except Exception:
        return ""


def _safe_truncate(text: str, cap: int) -> str:
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= cap:
        return text
    return text[: cap - 20] + "...[truncated]"


def _isolated_test_env() -> dict[str, str]:
    """Environment for a test-gate subprocess, isolated per run.

    Two harness-level fixes for last-mile false failures observed in the
    sacrifice queue:

      * ``MEDIA_DIR`` → a fresh writable tmp dir. The app's default
        ``media_dir`` is ``/var/sacrifice/media`` (not writable in the
        sandbox), so any story whose code does ``mkdir(parents=True)`` under
        it fails the gate with ``PermissionError`` — a harness/env defect, not
        a code defect (observed: story 18's upload smoke test). A per-run tmp
        dir also keeps concurrent story gates from colliding on shared media
        state.
      * ``PYTHONDONTWRITEBYTECODE`` → stop leaving ``__pycache__`` behind, so a
        reused worktree can't collect a sibling story's stale ``.pyc`` and run
        a test that isn't on this branch (observed: story 20).
      * ``PATH`` includes ``~/.local/bin`` → the daemon runs under systemd,
        whose PATH is ``/usr/local/bin:/usr/bin:...`` and does NOT include the
        user-local bin dir where ``uv`` (and other pipx/user tools) live. The
        factory process itself starts via an absolute uv path, but when it
        shells out an app's test_command (e.g. ``uv run --extra dev pytest``)
        via /bin/sh with the inherited env, ``uv`` isn't found and EVERY
        code-story test gate dies with ``uv: not found`` before running a test
        (observed 2026-07-07, story 49). Prepend the user-local bin so the
        test command finds the tools it declares, regardless of launch env.
    """
    import shutil
    import tempfile

    env = dict(os.environ)
    env["MEDIA_DIR"] = tempfile.mkdtemp(prefix="factory-test-media-")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    extra_paths: list[str] = []
    local_bin = os.path.expanduser("~/.local/bin")
    if os.path.isdir(local_bin):
        extra_paths.append(local_bin)
    # Also cover the directory of the resolved ``uv`` binary if it lives
    # somewhere non-standard (e.g. a custom install), so the test command's
    # ``uv`` always resolves to the same one the factory itself uses.
    uv_path = shutil.which("uv") or (
        f"{local_bin}/uv" if os.path.exists(f"{local_bin}/uv") else None
    )
    if uv_path:
        uv_dir = os.path.dirname(uv_path)
        if uv_dir and uv_dir not in extra_paths:
            extra_paths.append(uv_dir)
    if extra_paths:
        current = env.get("PATH", "")
        prefix = os.pathsep.join(p for p in extra_paths if p not in current.split(os.pathsep))
        if prefix:
            env["PATH"] = prefix + (os.pathsep + current if current else "")
    return env


def _run_pytest(repo_path: Path, test_command: str | None = None) -> tuple[bool, str]:
    """Return (passed, captured_output) for the chain's post-sandbox test gate.

    Resolution order:
      1. If ``test_command`` is provided (typically from
         ``app_config.gates.test_command``), run it verbatim via shell. This
         lets monorepo apps — where pytest must run from a sub-directory
         like ``backend/`` rather than the repo root — declare the exact
         invocation themselves.
      2. Otherwise look for ``tests/`` or root-level ``test_*.py`` and run
         ``python -m pytest -q`` from the repo root.
      3. If neither path is viable, return ``(False, "no tests directory")``
         so the caller can record a meaningful signal.

    Runs under ``_isolated_test_env`` so a non-writable ``media_dir`` default
    or stale bytecode can't manufacture a false failure.
    """
    import subprocess

    test_env = _isolated_test_env()

    if test_command:
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
                env=test_env,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return (False, f"test_command invocation failed: {exc}")
        return (result.returncode == 0, result.stdout + "\n" + result.stderr)

    if not (repo_path / "tests").exists() and not list(repo_path.glob("test_*.py")):
        return (False, "no tests directory")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
            env=test_env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return (False, f"pytest invocation failed: {exc}")
    return (result.returncode == 0, result.stdout + "\n" + result.stderr)


# --------------------------------------------------------------------------- #
# sandbox_run
# --------------------------------------------------------------------------- #


def _build_initial_message(
    *,
    persona: str,
    story_text: str,
    context_prelude: str,
    persona_prompt: str,
    prior_attempts: list[dict[str, Any]] | None = None,
    reviewer_findings: dict[str, Any] | None = None,
) -> str:
    parts = [
        context_prelude,
        "---",
        f"# Persona prompt: {persona}",
        persona_prompt.rstrip(),
        "---",
        "# Story",
        story_text.rstrip(),
    ]
    # When the chain bounces a story back from the reviewer (state
    # REVIEWER_REQUESTED_CHANGES -> dev), the tests are already green, so the
    # dev LLM has no signal about WHY it was re-dispatched unless we hand it
    # the reviewer's actual change requests. Without this section dev fixes
    # blind, the reviewer re-raises the same findings, and the loop never
    # converges. Render the findings prominently, right after the story.
    if reviewer_findings:
        # Findings are expected to be dicts, but some producers (e.g. the CI-
        # failure feedback path) historically injected a bare string. Coerce
        # any non-dict finding into a minimal dict so the render loop's
        # ``f.get(...)`` can never crash the tick with "'str' object has no
        # attribute 'get'" — and the text still reaches the dev.
        def _coerce(items: Any, text_key: str) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for f in items or []:
                if isinstance(f, dict):
                    out.append(f)
                elif f is not None:
                    out.append({"severity": "high", text_key: str(f)})
            return out

        findings = _coerce(reviewer_findings.get("findings"), "what")
        tq_findings = _coerce(reviewer_findings.get("test_quality_findings"), "issue")
        summary = (reviewer_findings.get("summary") or "").strip()
        # Loop-4: the dev persona owns BOTH code and tests, so its branch frames
        # every finding (code AND test-quality) as dev's to fix. The
        # test_implementer/test_designer branch is retained for any legacy use
        # but those personas are no longer dispatched by the chain.
        is_test_persona = persona in ("test_implementer", "test_designer")
        if findings or tq_findings or summary:
            parts.append("---")
            if is_test_persona:
                parts.append("# Reviewer rejected the TESTS — rewrite them to fix this")
                parts.append(
                    "The reviewer rejected the previous revision on test "
                    "quality. Rewrite the test files so they resolve EVERY "
                    "concern below — correct file location per the test plan, "
                    "tighten weak/sloppy assertions, and add the missing "
                    "behavioral coverage. Editing the test files is exactly "
                    "your job here; do not touch production code."
                )
                if summary:
                    parts.append(f"\n**Reviewer summary:** {summary[:600]}")
                if tq_findings:
                    parts.append("\n## Test-quality findings (fix each)")
                for j, f in enumerate(tq_findings, 1):
                    name = f.get("test_name", "")
                    issue = (f.get("issue") or "").strip()
                    fix = (f.get("fix_suggestion") or "").strip()
                    parts.append(f"\n{j}. `{name}`".rstrip())
                    if issue:
                        parts.append(f"   - Issue: {issue[:400]}")
                    if fix:
                        parts.append(f"   - Suggested fix: {fix[:400]}")
                # Code findings that are really about tests/coverage also help.
                if findings:
                    parts.append("\n## Reviewer code/coverage findings (for context)")
                for i, f in enumerate(findings, 1):
                    loc = f.get("location", "")
                    what = (f.get("what") or "").strip()
                    parts.append(f"\n{i}. {loc}".rstrip())
                    if what:
                        parts.append(f"   - {what[:400]}")
            else:
                parts.append("# Reviewer change requests — you MUST address ALL of these")
                parts.append(
                    "The reviewer rejected the previous revision of this PR. You "
                    "own BOTH the production code AND the tests, so resolve EVERY "
                    "item below: fix the code findings in the source, AND fix the "
                    "test-quality findings by editing the tests themselves. Then "
                    "re-run the full suite — it must stay green. If a request is "
                    "genuinely wrong or impossible, say so explicitly in your "
                    "summary rather than silently ignoring it — leaving any item "
                    "unaddressed will cause the reviewer to reject again."
                )
                if summary:
                    parts.append(f"\n**Reviewer summary:** {summary[:600]}")
                if findings:
                    parts.append("\n## Code change requests (fix these in production code)")
                for i, f in enumerate(findings, 1):
                    sev = f.get("severity", "?")
                    crit = str(f.get("criterion") or "").strip()
                    sev_tag = f"{sev}/{crit}" if crit else sev
                    loc = f.get("location", "")
                    what = (f.get("what") or "").strip()
                    fix = (f.get("fix_suggestion") or "").strip()
                    parts.append(f"\n{i}. **[{sev_tag}]** {loc}".rstrip())
                    if what:
                        parts.append(f"   - Problem: {what[:500]}")
                    if fix:
                        parts.append(f"   - Suggested fix: {fix[:500]}")
                    # Concrete reviewer-proposed edit: render verbatim (much
                    # higher cap than the one-liner — the whole point is that
                    # dev can apply it as an exact search/replace and end the
                    # finding's loop in one cycle).
                    edit = f.get("suggested_edit")
                    if isinstance(edit, dict) and edit.get("file") and edit.get("find"):
                        find_s = str(edit.get("find", ""))[:2000]
                        repl_s = str(edit.get("replace", ""))[:2000]
                        parts.append(f"   - Reviewer-proposed edit in `{edit['file']}`:")
                        parts.append(
                            "     Apply this exact replacement (unless it "
                            "conflicts with the acceptance criteria or breaks "
                            "tests — then explain why in your summary):"
                        )
                        parts.append(f"     FIND:\n```\n{find_s}\n```")
                        parts.append(f"     REPLACE WITH:\n```\n{repl_s}\n```")
                # Test-quality findings: dev OWNS the tests now, so fix them
                # directly — make each test exercise the real behavior and assert
                # the correct contract value the reviewer flagged.
                if tq_findings:
                    parts.append("\n## Test-quality findings (fix these tests directly)")
                    parts.append(
                        "The reviewer flagged the tests below as weak or wrong. "
                        "Edit each test so it drives the REAL behavior end-to-end "
                        "and asserts the correct contract value — do not delete or "
                        "weaken them to dodge the finding."
                    )
                    for j, f in enumerate(tq_findings, 1):
                        name = f.get("test_name", "")
                        issue = (f.get("issue") or "").strip()
                        fix = (f.get("fix_suggestion") or "").strip()
                        parts.append(f"\nTest-quality {j}. `{name}`".rstrip())
                        if issue:
                            parts.append(f"   - Issue: {issue[:400]}")
                        if fix:
                            parts.append(f"   - Suggested fix: {fix[:400]}")
                # Earlier review cycles: what was already fixed must STAY
                # fixed. Without this digest, dev only ever sees the latest
                # cycle and can silently regress cycle-1 fixes while
                # addressing cycle-3 findings — one of the drivers of the
                # 6-cycle non-convergence pattern.
                prior_cycles = reviewer_findings.get("prior_cycles") or []
                if prior_cycles:
                    parts.append("\n## Already addressed in earlier review cycles — do NOT regress")
                    parts.append(
                        "Findings from previous cycles, presumed fixed. Keep "
                        "them fixed while addressing the items above; the "
                        "reviewer re-checks these sites."
                    )
                    for entry in prior_cycles:
                        cyc = entry.get("cycle")
                        for f in entry.get("findings") or []:
                            loc = f.get("location", "")
                            what = (f.get("what") or "")[:200]
                            parts.append(f"- (cycle {cyc}) {loc}: {what}")
    if prior_attempts:
        # The chain feeds prior failed attempts forward so the LLM sees what
        # was already tried and which assertions are still red. Without this,
        # every retry is from scratch (no memory) and re-discovers the same
        # dead ends. Cap each output tail at 1500 chars to keep the prompt
        # bounded — full diagnostic lives in ``state/logs/<story>.log``.
        parts.append("---")
        parts.append("# Previous attempts on THIS story (most recent last)")
        parts.append(
            "These attempts ran in the same git worktree and any file changes "
            "they made persist below. Use them to avoid repeating failed "
            "approaches; if the same test keeps failing because the test itself "
            "is wrong, fix the test (you own it) — make it assert the correct "
            "behavior rather than working around a bad assertion."
        )
        for entry in prior_attempts:
            parts.append("")
            parts.append(f"## Attempt {entry.get('attempt', '?')}")
            files = entry.get("files_touched") or []
            if files:
                parts.append(f"- Files touched: {', '.join(files[:10])}")
            summary = (entry.get("summary") or "").strip()
            if summary:
                parts.append(f"- Summary: {summary[:400]}")
            tail = (entry.get("test_output_tail") or "").strip()
            if tail:
                parts.append("- Test output tail:")
                parts.append("```")
                parts.append(tail[-1500:])
                parts.append("```")

        # Cross-retry memory: dev's own reasoning + the trailing tool-call
        # window. Captured by ``_extract_conversation_memory`` after each
        # sandbox closes. The next retry sees not just *what failed* but
        # *what dev was trying to do* — the difference between giving the
        # LLM a stack trace and giving it the previous LLM's notebook.
        prior_thinking_entries = [
            e
            for e in prior_attempts
            if (
                e.get("self_summary")
                or e.get("last_assistant_message")
                or e.get("recent_tool_calls")
            )
        ]
        if prior_thinking_entries:
            parts.append("")
            parts.append("---")
            parts.append("# Your prior thinking (from previous sandbox sessions)")
            parts.append(
                "Each retry runs a fresh OpenHands conversation, but the "
                "previous run's last assistant message, recent tool calls, "
                "and self-summary are surfaced here so you keep context "
                "across the retry boundary. Do NOT repeat the exact "
                "approach if it failed; use this to inform a new line of "
                "investigation."
            )
            for entry in prior_thinking_entries:
                parts.append("")
                parts.append(f"## Attempt {entry.get('attempt', '?')} — prior thinking")
                self_sum = (entry.get("self_summary") or "").strip()
                if self_sum:
                    parts.append(
                        "### Self-summary (what I tried / what failed / what I'd try next)"
                    )
                    parts.append(self_sum[:1500])
                last_msg = (entry.get("last_assistant_message") or "").strip()
                if last_msg and last_msg != self_sum:
                    parts.append("### Last assistant message (verbatim tail)")
                    parts.append("```")
                    parts.append(last_msg[-1200:])
                    parts.append("```")
                calls = entry.get("recent_tool_calls") or []
                if calls:
                    parts.append("### Recent tool calls (trailing window)")
                    for i, call in enumerate(calls[-RECENT_TOOL_CALL_WINDOW:], 1):
                        tool = call.get("tool", "tool")
                        args = (call.get("args") or "")[:300]
                        obs = (call.get("observation") or "")[:300]
                        parts.append(f"{i}. **{tool}** — args: `{args}`")
                        if obs:
                            parts.append(f"   → `{obs}`")
    return "\n".join(parts) + "\n"


# Per-persona override map for ``sandbox_run.max_iterations``. Personas with
# bounded workflows (Onboarder's 4-phase scan, Test-Implementer's plan
# execution) get tighter caps so the chain doesn't burn budget on an agent
# that lost the plot. ``dev`` keeps the default 200 because it legitimately
# needs many turns for red→green→refactor.
#
# The cap is the *fallback* when the caller passes ``max_iterations=200``
# (the function default). Explicit values from the caller always win — that's
# how tests bound runs and how a power-user can override.
# JSON-mode truncation retry policy. Provider returns finish_reason="length"
# or a partial JSON string when ``max_tokens`` is exceeded. We double the cap
# and retry, up to ``_MAX_OUTPUT_RETRIES`` times, capped at
# ``_MAX_OUTPUT_RETRY_CEILING``. Default seed when callers don't pass
# ``max_tokens`` is conservative — providers bill by actual tokens used so
# the cost cost of generous caps on outputs that fit is zero.
_DEFAULT_MAX_OUTPUT_TOKENS = 8192
_MAX_OUTPUT_RETRIES = 4
_MAX_OUTPUT_RETRY_CEILING = 65536


PERSONA_ITERATION_CAPS: dict[str, int] = {
    # Bumped substantially after D007 showed 60/100 was too tight: onboarder
    # needs to read enough code to write coherent context docs, and
    # test_implementer needs room to write and rewrite tests when its first
    # cut is brittle. Token cost isn't the constraint — sandbox iterations
    # are essentially-free wall-clock until they cap out. Dev keeps the
    # default 600 because it does most of the heavy red→green refactor work.
    "onboarder": 180,
    "test_implementer": 300,
}


async def sandbox_run(
    persona: str,
    story_path: Path,
    repo_path: Path,
    llm_config: LLMConfig,
    difficulty: str = "standard",
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
    task_scope: str | None = None,
    max_iterations: int = 600,
    direction_chain: list[Any] | None = None,
    software_factory_root: Path | None = None,
    test_command: str | None = None,
    prior_attempts: list[dict[str, Any]] | None = None,
    reviewer_findings: dict[str, Any] | None = None,
    story_id: int | None = None,
    app: str | None = None,
    direction_id: str | None = None,
    wall_clock_timeout_s: int | None = None,
) -> RunResult:
    """Run a persona inside an OpenHands SDK sandbox against ``repo_path``.

    ``wall_clock_timeout_s`` overrides the module-level
    ``_SANDBOX_WALL_CLOCK_TIMEOUT_S`` (env ``FACTORY_SANDBOX_TIMEOUT_S``,
    default 1800s) for this run only — used by the dev convergence loop to
    give dev a per-persona budget without touching other personas.

    Reads the persona prompt + story file, composes the context prelude via
    ``factory.context.loader.compose_context_prelude``, hands the combined
    message to a fresh ``Conversation`` with default tools, and waits for
    completion.

    If ``dry_run`` is True, the function does NOT instantiate any SDK objects;
    it assembles the prompt, writes an entry to the DB with ``cost_usd=0`` and
    a synthetic success flag (False — dry-run is a wiring test, not work), and
    returns the assembled prompt as ``RunResult.summary`` so the caller can
    inspect it.
    """
    from factory.context.loader import compose_context_prelude  # local import keeps CLI light

    story_text = Path(story_path).read_text(encoding="utf-8")
    persona_prompt = _read_persona_prompt(persona)
    context_prelude = compose_context_prelude(
        persona=persona,
        app_repo_path=repo_path,
        task_scope=task_scope,
        direction_chain=direction_chain,
        software_factory_root=software_factory_root,
    )
    initial_user_text = _build_initial_message(
        persona=persona,
        story_text=story_text,
        context_prelude=context_prelude,
        persona_prompt=persona_prompt,
        prior_attempts=prior_attempts,
        reviewer_findings=reviewer_findings,
    )

    # Log prompt telemetry HERE — the moment the initial message exists and
    # before any failure path, mirroring the ``text_run`` site. Until this
    # existed, the three sandbox personas (dev, test_implementer, onboarder)
    # had NO prompt telemetry at all: ``prompts.ndjson`` held 45,868 rows
    # across 14 personas and zero rows for the three that write all the code.
    # The metadata is needed precisely when the run later fails, so the
    # placeholder_prompts detector can correlate a leaked-placeholder prompt
    # with the resulting error row in runs.ndjson.
    _log_prompt_metadata(
        persona=persona,
        prompt=initial_user_text,
        model_id=llm_config.model,
        story_id=story_id,
        software_factory_root=software_factory_root,
    )
    _log_prompt_body(
        persona=persona,
        prompt=initial_user_text,
        model_id=llm_config.model,
        story_id=story_id,
        software_factory_root=software_factory_root,
    )

    _t0 = time.monotonic()
    _started_at = datetime.now(UTC).isoformat()

    def _elapsed() -> float:
        return round(time.monotonic() - _t0, 3)

    def _record(**kw: Any) -> None:
        """Thin wrapper that injects started_at + software_factory_root."""
        _record_run(
            **kw,
            started_at=_started_at,
            software_factory_root=software_factory_root,
        )

    if dry_run:
        # Walk: did the prelude actually pull in project.md / navigation.md? Surface that.
        # Match the heading form ONLY — the dev persona prompt mentions
        # ``context/project.md`` as a forbidden write path, so a plain substring
        # check would always be a false positive.
        prelude_signals = []
        if "## context/project.md" in context_prelude:
            prelude_signals.append("project.md included")
        if "## context/navigation.md" in context_prelude:
            prelude_signals.append("navigation.md included")
        if "NO CONTEXT AVAILABLE" in context_prelude:
            prelude_signals.append("NO_CONTEXT_AVAILABLE notice issued")

        _record(
            persona=persona,
            model=llm_config.model,
            mode="sandbox-dry-run",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            success=False,
            story_path=str(story_path),
            repo_path=str(repo_path),
            error=None,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=difficulty,
            direction_id=direction_id,
            app=app,
        )
        summary = (
            f"[DRY-RUN] persona={persona} model={llm_config.model} difficulty={difficulty}\n"
            f"prelude signals: {', '.join(prelude_signals) or 'none'}\n"
            f"initial_user_text bytes: {len(initial_user_text)}\n"
            f"--- INITIAL USER MESSAGE (head 1200 chars) ---\n"
            f"{initial_user_text[:1200]}\n"
            f"--- END ---"
        )
        return RunResult(
            success=False,
            files_changed=[],
            test_run_passed=None,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            error=None,
            summary=summary,
        )

    # ---- Real run: instantiate OpenHands SDK Conversation -----------------
    api_key = _resolve_api_key(llm_config)
    if api_key is None:
        err = (
            f"No API key available for model {llm_config.model!r}. Set the appropriate "
            f"env var (DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY / "
            f"AZURE_AI_API_KEY) or pass --dry-run."
        )
        _record(
            persona=persona,
            model=llm_config.model,
            mode="sandbox",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            success=False,
            story_path=str(story_path),
            repo_path=str(repo_path),
            error=err,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=difficulty,
            direction_id=direction_id,
            app=app,
            premodel_infra=True,
        )
        return RunResult(success=False, error=err, summary=err, premodel_infra=True)

    try:
        # Import OpenHands lazily so test/CLI paths that never hit a real run
        # don't pay the import cost. mypy treats OpenHands as untyped via the
        # ignore_missing_imports override; we cast through Any below.
        from openhands.sdk import LLM, Conversation, LocalWorkspace
        from openhands.tools.preset.default import get_default_agent
        from pydantic import SecretStr
    except Exception as exc:  # pragma: no cover - exercised only with SDK
        err = f"OpenHands SDK import failed: {exc}"
        _record(
            persona=persona,
            model=llm_config.model,
            mode="sandbox",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            success=False,
            story_path=str(story_path),
            repo_path=str(repo_path),
            error=err,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=difficulty,
            direction_id=direction_id,
            app=app,
            premodel_infra=True,
        )
        return RunResult(success=False, error=err, summary=err, premodel_infra=True)

    # For Azure (either surface), populate base_url + api_version from env if
    # the caller didn't pass them. The two surfaces read different env vars:
    #
    #   * ``azure_ai/...``  → AZURE_AI_API_BASE  / AZURE_AI_API_VERSION
    #                         (fallback: AZURE_FOUNDRY_ENDPOINT / _API_VERSION)
    #   * ``azure/...``     → AZURE_API_BASE     / AZURE_API_VERSION
    #                         (fallback: AZURE_ENDPOINT, plus the foundry vars
    #                          for operators sharing a single key/endpoint)
    #
    # The LiteLLM monkey-patch in ``factory.providers.azure_foundry.ensure_
    # bootstrapped`` (already called by ``_resolve_api_key`` above) makes the
    # OpenAI-compatible Foundry path work for every ``azure_ai/...`` id.
    base_url = llm_config.base_url
    api_version: str | None = None
    if llm_config.model.startswith("azure_ai/"):
        base_url = (
            base_url
            or os.environ.get("AZURE_AI_API_BASE")
            or os.environ.get("AZURE_FOUNDRY_ENDPOINT")
        )
        api_version = os.environ.get("AZURE_AI_API_VERSION") or os.environ.get(
            "AZURE_FOUNDRY_API_VERSION"
        )
    elif llm_config.model.startswith("azure/"):
        base_url = (
            base_url
            or os.environ.get("AZURE_API_BASE")
            or os.environ.get("AZURE_ENDPOINT")
            or os.environ.get("AZURE_FOUNDRY_ENDPOINT")
        )
        api_version = os.environ.get("AZURE_API_VERSION") or os.environ.get(
            "AZURE_FOUNDRY_API_VERSION"
        )

    llm_kwargs: dict[str, Any] = {
        "model": llm_config.model,
        "api_key": SecretStr(api_key),
        "base_url": base_url,
        "usage_id": f"factory:{persona}",
    }
    if api_version is not None:
        llm_kwargs["api_version"] = api_version
    llm_kwargs.update(_persona_llm_overrides(persona, llm_config.model, difficulty))
    llm = LLM(**llm_kwargs)
    agent = _build_agent_for_persona(persona, llm, get_default_agent)
    workspace = LocalWorkspace(working_dir=str(Path(repo_path).resolve()))

    # Give the dev/test_impl sandbox a writable MEDIA_DIR so the agent's OWN
    # in-loop test runs don't fail on the unwritable ``/var/sacrifice`` default
    # (which would make dev "see red" on correct code and thrash). The post-
    # sandbox gate (_run_pytest) still uses its own fresh tmp via
    # _isolated_test_env; this only affects what the agent observes mid-run.
    # Process-global is fine: each ``factory tick`` is its own process running
    # handlers serially. PYTHONDONTWRITEBYTECODE avoids stale .pyc accumulation.
    import tempfile as _tf

    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    os.environ["MEDIA_DIR"] = _tf.mkdtemp(prefix="factory-sandbox-media-")

    # Apply per-persona iteration cap when the caller used the default. We
    # detect "default" by comparing to the signature default (200). Callers
    # who explicitly pass a non-default value win; this only narrows the
    # ceiling for personas that historically over-iterate.
    # Apply per-persona iteration cap when the caller used the signature
    # default (we read the live default off the function signature so this
    # detection survives future bumps to the default without code churn).
    import inspect as _inspect

    _signature_default = _inspect.signature(sandbox_run).parameters["max_iterations"].default
    effective_max_iterations = max_iterations
    if max_iterations == _signature_default and persona in PERSONA_ITERATION_CAPS:
        effective_max_iterations = PERSONA_ITERATION_CAPS[persona]

    loop = asyncio.get_running_loop()

    # Trajectory capture: give the SDK a private persistence dir so it writes
    # every conversation event (agent messages, tool calls, observations) to
    # disk AS THE RUN PROGRESSES — after the run (or a timeout/crash, which
    # still leaves a partial trail) the events are copied out whole into
    # ``state/events/trajectories/<story>-<attempt>.ndjson``. The conversation
    # id is fixed up front so the events dir location is known even when the
    # run thread is orphaned by the wall-clock timeout. Gated on the same
    # scope switch as body capture — one config surface.
    import uuid as _uuid

    _traj_attempt = len(prior_attempts or []) + 1
    _traj_conv_id: Any = None
    _traj_persist_dir: str | None = None
    _traj_events_src: Path | None = None
    if _prompt_bodies_scope() != "off":
        _traj_conv_id = _uuid.uuid4()
        _traj_persist_dir = _tf.mkdtemp(prefix="factory-oh-traj-")
        _traj_events_src = Path(_traj_persist_dir) / _traj_conv_id.hex / "events"

    def _capture_traj() -> str | None:
        if _traj_events_src is None:
            return None
        return _capture_trajectory(
            events_src=_traj_events_src,
            story_id=story_id,
            attempt=_traj_attempt,
            software_factory_root=software_factory_root,
        )

    def _cleanup_traj_persist() -> None:
        if _traj_persist_dir is not None:
            import shutil as _shutil

            _shutil.rmtree(_traj_persist_dir, ignore_errors=True)

    # Usage captured AS SOON AS the model run completes, BEFORE memory
    # extraction / conversation teardown. If ``_do_run`` raises after this is
    # populated (e.g. ``_extract_conversation_memory`` or ``close()`` blows up),
    # the ``except`` handler below reads this holder to tell "the model did real
    # work then crashed" (a genuine failed dev attempt — must burn a retry)
    # apart from "the sandbox died before any model work" (infra — free retry).
    _partial_usage: dict[str, float] = {}
    # Whether the SDK actually reported a cost for this conversation. Kept
    # separate from ``_partial_usage`` (which is float-valued) so "the provider
    # reported 0.0" stays distinguishable from "we could not read a cost at
    # all". Populated inside ``_do_run``; read by every exit path below.
    _usage_meta: dict[str, bool] = {}

    def _do_run() -> tuple[int, int, int, float, str, list[dict[str, Any]]]:
        # ``Conversation`` is a factory that returns LocalConversation/RemoteConversation
        # depending on the workspace type. Treat as Any for mypy purposes.
        conv_kwargs: dict[str, Any] = {}
        if _traj_persist_dir is not None:
            # SDK 1.22.1: ``persistence_dir`` makes LocalConversation write
            # each event to ``<persistence_dir>/<conversation_id.hex>/events/``
            # incrementally; ``delete_on_close=False`` (below) keeps them
            # through close() for the post-run copy-out.
            conv_kwargs["persistence_dir"] = _traj_persist_dir
            conv_kwargs["conversation_id"] = _traj_conv_id
        conversation: Any = Conversation(
            agent=agent,
            workspace=workspace,
            max_iteration_per_run=effective_max_iterations,
            delete_on_close=False,
            **conv_kwargs,
        )
        try:
            conversation.send_message(initial_user_text)
            conversation.run()
            stats = conversation.conversation_stats.get_combined_metrics()
            tok = stats.accumulated_token_usage
            t_in = int(getattr(tok, "prompt_tokens", 0) or 0)
            t_out = int(getattr(tok, "completion_tokens", 0) or 0)
            # The OpenHands SDK's ``TokenUsage`` already carries the
            # cache/fresh split (``cache_read_tokens``) — no need to re-parse
            # a raw litellm response here.
            t_cached = int(getattr(tok, "cache_read_tokens", 0) or 0)
            # Read the cost through a None sentinel rather than a 0.0 default:
            # an SDK shape change that drops ``accumulated_cost`` would
            # otherwise be indistinguishable from a genuinely free run, and
            # every run in the ledger would silently read as $0.
            _cost_raw = getattr(stats, "accumulated_cost", None)
            cost = float(_cost_raw or 0.0)
            _usage_meta["reliable"] = _cost_raw is not None
            # Record usage the instant it is known so a later crash in this
            # function is still attributable to real model work.
            _partial_usage.update(tokens_in=t_in, tokens_out=t_out, cached=t_cached, cost=cost)
            # Extract cross-retry memory signal from the conversation's
            # event stream BEFORE closing. ``conversation.state.events`` is
            # the canonical sequence of MessageEvent / ActionEvent /
            # ObservationEvent records. We do the extraction inside the
            # executor (same thread that owns the state) and pass plain
            # dicts back to the async layer.
            last_msg, recent = _extract_conversation_memory(conversation)
            return (t_in, t_out, t_cached, cost, last_msg, recent)
        finally:
            conversation.close()

    # Write a ``live_handlers`` heartbeat row so the TUI can see what's
    # mid-flight. The context manager removes the row on exit regardless
    # of success/failure; reaped on stale-pid scan if the process crashes.
    from factory.observability.heartbeat import live_handler

    effective_wall_clock_timeout_s = wall_clock_timeout_s or _SANDBOX_WALL_CLOCK_TIMEOUT_S
    _hb_db = db_path or _DEFAULT_DB_PATH
    try:
        with live_handler(
            _hb_db,
            persona=persona,
            model=llm_config.model,
            mode="sandbox",
            story_id=story_id,
            app=app,
            direction_id=direction_id,
        ):
            (
                tokens_in,
                tokens_out,
                cached_input_tokens,
                cost_usd,
                last_assistant_message,
                recent_tool_calls,
                # Bound the blocking executor call so a stalled LLM request can't
                # hang the handler forever. asyncio.wait_for cancels the await on
                # timeout; the orphaned worker thread (threads can't be force-
                # killed in-process) is reaped when this one-shot tick process
                # exits. The TimeoutError is handled distinctly below.
            ) = await asyncio.wait_for(
                loop.run_in_executor(None, _do_run),
                timeout=effective_wall_clock_timeout_s,
            )
    except TimeoutError:
        err = (
            f"sandbox run timed out after {effective_wall_clock_timeout_s}s "
            "(likely a stalled LLM call); treating as retryable infrastructure "
            "failure"
        )
        # Copy out whatever trajectory the run persisted before it stalled —
        # the partial trail is exactly the forensic record a timeout needs.
        # Do NOT delete the persistence dir here: the orphaned worker thread
        # may still be writing to it.
        _capture_traj()
        # Same distinction as the generic-except path below: if the model run
        # actually completed and only the post-model teardown (memory
        # extraction / close) hit the wall clock, ``_partial_usage`` is
        # populated — that is a genuine attempt whose spend must be recorded and
        # which must consume a dev retry, NOT a free infra bounce. A truly
        # stalled LLM (no partial usage) stays retryable infra.
        _t_out = int(_partial_usage.get("tokens_out", 0) or 0)
        _cost = float(_partial_usage.get("cost", 0.0) or 0.0)
        model_did_work = _t_out > 0 or _cost > 0.0
        _record(
            persona=persona,
            model=llm_config.model,
            mode="sandbox",
            tokens_in=int(_partial_usage.get("tokens_in", 0) or 0),
            tokens_out=_t_out,
            cost_usd=_cost,
            success=False,
            story_path=str(story_path),
            repo_path=str(repo_path),
            error=err,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=difficulty,
            direction_id=direction_id,
            app=app,
            cached_input_tokens=int(_partial_usage.get("cached", 0) or 0),
            premodel_infra=not model_did_work,
            # Only meaningful when the model actually ran: a run that died
            # before any model work has no usage to be un/reliable about.
            usage_reliable=_usage_meta.get("reliable") if model_did_work else None,
        )
        return RunResult(
            success=False,
            # Model completed then teardown timed out → a real red attempt;
            # otherwise a stalled request that never produced work → infra.
            test_run_passed=False if model_did_work else None,
            tokens_in=int(_partial_usage.get("tokens_in", 0) or 0),
            tokens_out=_t_out,
            cost_usd=_cost,
            error=err,
            summary=err,
            last_assistant_message="",
            recent_tool_calls=[],
            self_summary="",
            premodel_infra=not model_did_work,
            usage_reliable=_usage_meta.get("reliable") if model_did_work else None,
        )
    except Exception as exc:
        err = f"sandbox run raised: {exc!r}"
        # The partial trajectory is most valuable exactly when the run blew up.
        _capture_traj()
        _cleanup_traj_persist()
        # Distinguish "the model already did real work then something raised"
        # (e.g. metrics extraction / conversation teardown blew up) from "the
        # sandbox died before any model work". Only the latter is pre-model
        # infra; the former is a genuine failed dev attempt that MUST consume a
        # dev retry (bypassing the increment was the story-88 bug: dev_retries
        # stuck at 1 while the story was re-dispatched for free 12 times).
        _t_out = int(_partial_usage.get("tokens_out", 0) or 0)
        _cost = float(_partial_usage.get("cost", 0.0) or 0.0)
        model_did_work = _t_out > 0 or _cost > 0.0
        _record(
            persona=persona,
            model=llm_config.model,
            mode="sandbox",
            tokens_in=int(_partial_usage.get("tokens_in", 0) or 0),
            tokens_out=_t_out,
            cost_usd=_cost,
            success=False,
            story_path=str(story_path),
            repo_path=str(repo_path),
            error=err,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=difficulty,
            direction_id=direction_id,
            app=app,
            cached_input_tokens=int(_partial_usage.get("cached", 0) or 0),
            premodel_infra=not model_did_work,
            # Only meaningful when the model actually ran: a run that died
            # before any model work has no usage to be un/reliable about.
            usage_reliable=_usage_meta.get("reliable") if model_did_work else None,
        )
        return RunResult(
            success=False,
            # When the model did work the tests were NOT evaluated by the
            # post-model gate (we never reached it), but the attempt is real:
            # report test_run_passed=False so handle_dev counts it as a red
            # dev run rather than pre-model infra.
            test_run_passed=False if model_did_work else None,
            tokens_in=int(_partial_usage.get("tokens_in", 0) or 0),
            tokens_out=_t_out,
            cost_usd=_cost,
            error=err,
            summary=err,
            last_assistant_message="",
            recent_tool_calls=[],
            self_summary="",
            premodel_infra=not model_did_work,
            usage_reliable=_usage_meta.get("reliable") if model_did_work else None,
        )

    # Response-side observability: copy the full OpenHands trajectory out to
    # per-story state, then record the final assistant message as this call's
    # response body (with the trajectory path attached for the join).
    _traj_path = _capture_traj()
    _cleanup_traj_persist()
    _log_response_body(
        persona=persona,
        response=last_assistant_message,
        prompt=initial_user_text,
        model_id=llm_config.model,
        story_id=story_id,
        software_factory_root=software_factory_root,
        mode="sandbox",
        trajectory_path=_traj_path,
    )

    files_changed = _scan_repo_for_changed_files(Path(repo_path))
    test_passed, test_out = _run_pytest(Path(repo_path), test_command=test_command)
    self_summary = _extract_self_summary(last_assistant_message)

    _record(
        persona=persona,
        model=llm_config.model,
        mode="sandbox",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        success=test_passed,
        story_path=str(story_path),
        repo_path=str(repo_path),
        error=None if test_passed else "tests not green after run",
        db_path=db_path,
        duration_s=_elapsed(),
        story_id=story_id,
        model_tier=difficulty,
        direction_id=direction_id,
        app=app,
        cached_input_tokens=cached_input_tokens,
        premodel_infra=False,
        usage_reliable=_usage_meta.get("reliable", True),
    )

    return RunResult(
        success=test_passed,
        files_changed=files_changed,
        test_run_passed=test_passed,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        error=None if test_passed else "tests not green after run",
        summary=test_out[-2000:],
        last_assistant_message=last_assistant_message,
        recent_tool_calls=recent_tool_calls,
        self_summary=self_summary,
        usage_reliable=_usage_meta.get("reliable", True),
    )


# --------------------------------------------------------------------------- #
# text_run
# --------------------------------------------------------------------------- #


def text_run(
    persona: str,
    prompt: str,
    model_id: str,
    schema: dict[str, Any] | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    db_path: Path | None = None,
    dry_run: bool = False,
    max_tokens: int | None = None,
    story_id: int | None = None,
    app: str | None = None,
    direction_id: str | None = None,
    model_tier: str | None = None,
    software_factory_root: Path | None = None,
) -> str | dict[str, Any]:
    """Single ``litellm.completion()`` call. Returns text, or a dict if ``schema`` set.

    When ``schema`` is provided, the prompt is augmented with an instruction
    to return JSON matching the schema; the response is parsed and validated
    via ``jsonschema`` if installed, falling back to a minimal key-presence
    check otherwise.
    """
    # Log prompt metadata (length, section headers, placeholder markers, hash)
    # to ``state/events/prompts.ndjson`` BEFORE any failure path — including
    # ``_resolve_api_key``, which can return None and raise, and the litellm
    # import below, which can ImportError. The metadata is needed precisely
    # when the call later fails, so the placeholder_prompts detector / L1
    # watcher can correlate a leaked-placeholder prompt with the resulting
    # error row in runs.ndjson. NEVER logs prompt content — only metadata.
    _log_prompt_metadata(
        persona=persona,
        prompt=prompt,
        model_id=model_id,
        story_id=story_id,
        software_factory_root=software_factory_root,
    )
    _log_prompt_body(
        persona=persona,
        prompt=prompt,
        model_id=model_id,
        story_id=story_id,
        software_factory_root=software_factory_root,
    )

    cfg = LLMConfig(model=model_id, api_key=api_key, base_url=base_url)
    resolved_key = _resolve_api_key(cfg)

    _t0 = time.monotonic()
    _started_at = datetime.now(UTC).isoformat()

    def _elapsed() -> float:
        return round(time.monotonic() - _t0, 3)

    def _record(**kw: Any) -> None:
        """Inject started_at + software_factory_root into every _record_run call."""
        _record_run(
            **kw,
            started_at=_started_at,
            software_factory_root=software_factory_root,
        )

    if dry_run:
        _record(
            persona=persona,
            model=model_id,
            mode="text-dry-run",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            success=True,
            story_path=None,
            repo_path=None,
            error=None,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=model_tier,
            direction_id=direction_id,
            app=app,
        )
        if schema is not None:
            return {"_dry_run": True, "persona": persona, "model": model_id}
        return f"[DRY-RUN text_run] persona={persona} model={model_id}"

    if resolved_key is None:
        msg = f"No API key available for {model_id!r}"
        _record(
            persona=persona,
            model=model_id,
            mode="text",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            success=False,
            story_path=None,
            repo_path=None,
            error=msg,
            db_path=db_path,
            duration_s=_elapsed(),
            story_id=story_id,
            model_tier=model_tier,
            direction_id=direction_id,
            app=app,
            premodel_infra=True,
        )
        raise RuntimeError(msg)

    try:
        import litellm
    except Exception as exc:
        raise RuntimeError(f"litellm not installed: {exc}") from exc

    # Azure (either surface): ensure base_url is present so LiteLLM hits the
    # right URL shape. Env-var precedence differs by surface — see
    # ``_provider_env_key`` for the rationale.
    effective_base_url = base_url
    api_version: str | None = None
    if model_id.startswith("azure_ai/"):
        if effective_base_url is None:
            effective_base_url = os.environ.get("AZURE_AI_API_BASE") or os.environ.get(
                "AZURE_FOUNDRY_ENDPOINT"
            )
        api_version = os.environ.get("AZURE_AI_API_VERSION") or os.environ.get(
            "AZURE_FOUNDRY_API_VERSION"
        )
    elif model_id.startswith("azure/"):
        if effective_base_url is None:
            effective_base_url = (
                os.environ.get("AZURE_API_BASE")
                or os.environ.get("AZURE_ENDPOINT")
                or os.environ.get("AZURE_FOUNDRY_ENDPOINT")
            )
        api_version = os.environ.get("AZURE_API_VERSION") or os.environ.get(
            "AZURE_FOUNDRY_API_VERSION"
        )

    messages = [{"role": "user", "content": prompt}]
    if schema is not None:
        messages[0]["content"] = (
            f"{prompt}\n\nReturn ONLY a JSON object matching this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )

    # Retry loop for JSON-mode truncation: when finish_reason == "length"
    # OR the response fails to parse, double max_tokens and retry. Hard
    # ceiling _MAX_OUTPUT_RETRY_CEILING covers every model in our fleet
    # (Claude 4.x supports 32k; Azure GPT 5.4 supports 16k+; DeepSeek
    # caps at 8k and will silently clip past that, which is fine because
    # we'll surface the parse error rather than loop forever).
    #
    # Truncation is *visible* in two places: ``finish_reason="length"``
    # from the provider, and a json.loads exception on the partial text.
    # Either signal triggers the retry; we keep doubling up to the
    # ceiling so a single 4096-cap mistake doesn't wedge the chain.
    current_max = max_tokens if max_tokens is not None else _DEFAULT_MAX_OUTPUT_TOKENS
    tokens_in = 0
    tokens_out = 0
    cached_input_tokens = 0
    cost_usd = 0.0
    # Starts True and is only ever cleared: if ANY attempt in the retry ladder
    # failed to yield a cost, the accumulated total is a floor, not a
    # measurement, and the whole row is flagged unreliable.
    usage_reliable = True
    text = ""
    parsed: dict[str, Any] | None = None
    last_finish_reason: str | None = None

    # Heartbeat for the whole text_run call (potentially multi-attempt). The
    # TUI sees this row while the LLM call is in flight, regardless of retry
    # loops inside this function. Use manual start/end so we don't have to
    # re-indent the multi-page retry block under a ``with`` clause.
    from factory.observability.heartbeat import end_heartbeat, start_heartbeat

    _hb_db = db_path or _DEFAULT_DB_PATH
    _hb_id: int | None = None
    with contextlib.suppress(Exception):
        _hb_id = start_heartbeat(
            _hb_db,
            persona=persona,
            model=model_id,
            mode="text",
            story_id=story_id,
            app=app,
            direction_id=direction_id,
        )

    for attempt in range(1, _MAX_OUTPUT_RETRIES + 1):
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "api_key": resolved_key,
        }
        if effective_base_url:
            kwargs["base_url"] = effective_base_url
        if api_version:
            kwargs["api_version"] = api_version
        kwargs["max_tokens"] = current_max
        if schema is not None:
            kwargs["response_format"] = {"type": "json_object"}

        response = litellm.completion(**kwargs)
        text = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {}) or {}
        tokens_in += int(usage.get("prompt_tokens", 0) or 0)
        attempt_out = int(usage.get("completion_tokens", 0) or 0)
        tokens_out += attempt_out
        cached_input_tokens += _extract_cached_tokens(usage)
        # LiteLLM reports the computed price on a private attribute. Treat a
        # missing attribute, a missing key, or a raise as UNKNOWN rather than
        # zero — silently adding 0.0 is how 1016 live text runs ended up with
        # output tokens and no recorded cost, indistinguishable from free runs.
        try:
            _hidden = getattr(response, "_hidden_params", None)
            _attempt_cost = _hidden.get("response_cost") if isinstance(_hidden, dict) else None
            if _attempt_cost is None:
                usage_reliable = False
            else:
                cost_usd += float(_attempt_cost)
        except Exception:  # noqa: BLE001 - a cost read must never fail the call
            usage_reliable = False
        try:
            last_finish_reason = response["choices"][0].get("finish_reason")
        except Exception:
            last_finish_reason = None

        # A "length" finish_reason is only a REAL truncation if the model
        # actually emitted close to the cap. Some providers (observed:
        # deepseek-chat in JSON mode) intermittently return a tiny malformed
        # body while still flagging finish_reason="length"; doubling the cap
        # then re-calling cannot help — the model isn't using the cap it has.
        # Treat that as futile and stop retrying instead of burning the full
        # doubling ladder (8192 -> 65536) on a model that won't comply.
        fake_truncation = last_finish_reason == "length" and attempt_out < int(current_max * 0.8)

        if schema is None:
            # Plain text mode — only retry on REAL truncation.
            if (
                last_finish_reason != "length"
                or fake_truncation
                or current_max >= _MAX_OUTPUT_RETRY_CEILING
            ):
                break
        else:
            try:
                parsed = json.loads(text)
                break
            except Exception as parse_exc:
                if (
                    current_max >= _MAX_OUTPUT_RETRY_CEILING
                    or attempt == _MAX_OUTPUT_RETRIES
                    or fake_truncation
                ):
                    # No more headroom — record and raise with full diagnostics.
                    if _hb_id is not None:
                        with contextlib.suppress(Exception):
                            end_heartbeat(_hb_db, _hb_id)
                    _record(
                        persona=persona,
                        model=model_id,
                        mode="text",
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        success=False,
                        story_path=None,
                        repo_path=None,
                        error=(
                            f"json parse failed at max_tokens={current_max} "
                            f"finish_reason={last_finish_reason}: {parse_exc}"
                        ),
                        db_path=db_path,
                        duration_s=_elapsed(),
                        story_id=story_id,
                        model_tier=model_tier,
                        direction_id=direction_id,
                        app=app,
                        cached_input_tokens=cached_input_tokens,
                        premodel_infra=False,
                        usage_reliable=usage_reliable,
                    )
                    # Capture the unparseable response too — the raw text is
                    # exactly what a forensic look at this failure needs.
                    _log_response_body(
                        persona=persona,
                        response=text,
                        prompt=prompt,
                        model_id=model_id,
                        story_id=story_id,
                        software_factory_root=software_factory_root,
                    )
                    raise RuntimeError(
                        f"JSON-mode response was not valid JSON after "
                        f"{attempt} attempts (max_tokens up to {current_max}, "
                        f"finish_reason={last_finish_reason}): {parse_exc}"
                    ) from parse_exc

        # Double for next attempt; clamp to ceiling.
        current_max = min(current_max * 2, _MAX_OUTPUT_RETRY_CEILING)

    if _hb_id is not None:
        with contextlib.suppress(Exception):
            end_heartbeat(_hb_db, _hb_id)

    # Response-side observability: the verbatim response text, joinable to its
    # prompt-body row via prompt_hash. ``prompt`` here is the SAME pre-schema-
    # augmentation string ``_log_prompt_body`` hashed above.
    _log_response_body(
        persona=persona,
        response=text,
        prompt=prompt,
        model_id=model_id,
        story_id=story_id,
        software_factory_root=software_factory_root,
    )

    success = True

    _record(
        persona=persona,
        model=model_id,
        mode="text",
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        success=success,
        story_path=None,
        repo_path=None,
        error=None,
        db_path=db_path,
        duration_s=_elapsed(),
        story_id=story_id,
        model_tier=model_tier,
        direction_id=direction_id,
        app=app,
        cached_input_tokens=cached_input_tokens,
        premodel_infra=False,
        usage_reliable=usage_reliable,
    )

    if schema is not None:
        return cast(dict[str, Any], parsed)
    return text
