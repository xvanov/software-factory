"""Chain-side enforcement of a story's delivery level.

``factory/delivery.py`` owns the vocabulary (``none < branch < draft_pr < pr <
auto_merge < push_to_main``) and the clamp rule. This module owns the three
things the CHAIN needs on top of that:

1. **Resolve once, record forever.** :func:`resolve_for_direction` computes a
   story's level at spawn (app ceiling + the direction's ``delivery:``
   frontmatter) and the spawn handler writes it to ``StoryRecord.delivery_level``
   plus a ``delivery_level_resolved`` story event. Every later decision reads
   the RECORDED value through :func:`story_level`, so an operator raising an
   app's ceiling mid-flight cannot escalate a story already in flight. Lowering
   the ceiling DOES apply (de-escalation is always the safe direction) and is
   recorded once as ``delivery_level_lowered``.

2. **Fail safe.** Anything that cannot be determined resolves to ``none`` — the
   most restrictive level that still preserves the work (it is committed
   locally, never thrown away) — and the reason is logged. The one exception is
   a row that predates per-story recording in an app that never opted into a
   ``delivery`` block: that resolves to today's behaviour (``auto_merge``), so
   shipping this module changes nothing for in-flight legacy work.

3. **The git side of the non-PR levels.** :func:`commit_local_work` (``none``)
   and :func:`fast_forward_default_branch` (``push_to_main``). Branch pushing
   and PR creation reuse ``handlers._push_story_branch`` /
   ``handlers._open_pr_for_story``.

Where each level is enforced (keep in sync with
``apps/factory/context/modules/delivery.md``):

* ``handlers.handle_docs_enforcer`` — the PR-open site. ``none`` commits and
  ends in ``DELIVERED_LOCAL``; ``branch`` pushes and ends in
  ``DELIVERED_BRANCH``; ``draft_pr`` / ``pr`` open a draft / ready PR and end in
  ``DELIVERED_PR``; ``auto_merge`` is unchanged (``PR_OPEN``); ``push_to_main``
  pushes the branch and reaches ``PR_OPEN`` with NO PR.
* ``auto_merge.auto_merge_tick`` — never merges a story whose level does not
  merge (and never a draft PR); runs the full gate set for ``push_to_main`` and
  fast-forwards the default branch, or refuses and falls back to ``pr``.
* ``handlers.handle_dev`` (dev-exhausted WIP preservation) — pushes only when
  the level pushes.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from factory.delivery import (
    LEGACY_DEFAULT,
    DeliveryLevel,
    clamp,
    effective_level,
    parse_level,
)

_logger = logging.getLogger(__name__)

EVENT_RESOLVED = "delivery_level_resolved"
EVENT_LOWERED = "delivery_level_lowered"
EVENT_DELIVERED = "delivered"


def _app_opted_in(app_config: Any) -> bool:
    """True when ``apps/<app>/config.yaml`` carries an explicit ``delivery`` block."""
    fields_set = getattr(app_config, "model_fields_set", None) or set()
    return "delivery" in fields_set


def resolve_for_direction(app_config: Any, direction: Any) -> tuple[DeliveryLevel, dict[str, Any]]:
    """The level a NEW story of ``direction`` runs at, plus an audit payload.

    Never raises: any failure resolves to ``none`` with the reason recorded.
    """
    try:
        cfg = app_config.delivery
        fm = getattr(direction, "raw_frontmatter", None) or {}
        requested = fm.get("delivery") if isinstance(fm, dict) else None
        level = effective_level(cfg, requested)
        info: dict[str, Any] = {
            "level": level.value,
            "requested": None if requested is None else str(requested),
            "ceiling": cfg.max.value,
            "default": (cfg.default or cfg.max).value,
            "app_opted_in": _app_opted_in(app_config),
        }
        if requested not in (None, ""):
            try:
                req = parse_level(requested)
            except ValueError:
                info["reason"] = "unparseable_request_fail_safe_none"
            else:
                if req is not None and req.rank > cfg.max.rank:
                    info["reason"] = "request_clamped_to_ceiling"
                    info["clamped"] = True
        return level, info
    except Exception as exc:  # noqa: BLE001 - fail safe, never fail a spawn
        _logger.warning("delivery level resolution failed (fail-safe none): %r", exc)
        return DeliveryLevel.NONE, {
            "level": DeliveryLevel.NONE.value,
            "reason": f"resolution_failed_fail_safe_none: {exc!r}"[:300],
        }


def _log(story: Any, event: str, payload: dict[str, Any], root: Path) -> None:
    if getattr(story, "id", None) is None:
        return
    try:
        from factory.chain.event_log import log_story_event

        log_story_event(
            story.id, event, payload, software_factory_root=root, slug_hint=story.slug or ""
        )
    except Exception:  # noqa: BLE001 - telemetry must never break delivery
        _logger.warning("story %s: could not log %s", getattr(story, "id", None), event)


def record_spawn_level(
    story: Any, app_config: Any, direction: Any, root: Path
) -> tuple[DeliveryLevel, dict[str, Any]]:
    """Stamp ``story.delivery_level`` at spawn (caller persists). Returns the audit payload
    so the caller can log it once the row has an id."""
    level, info = resolve_for_direction(app_config, direction)
    story.delivery_level = level.value
    info["source"] = "spawn"
    return level, info


def log_spawn_level(story: Any, info: dict[str, Any], root: Path) -> None:
    _log(story, EVENT_RESOLVED, info, root)


def _resolve_unrecorded(
    story: Any, app_config: Any, root: Path
) -> tuple[DeliveryLevel, dict[str, Any]]:
    """A row with no recorded level — it predates per-story recording."""
    try:
        from factory.chain.handlers import find_direction_for_story

        direction = find_direction_for_story(story, root)
    except Exception as exc:  # noqa: BLE001
        return DeliveryLevel.NONE, {
            "level": DeliveryLevel.NONE.value,
            "reason": f"direction_unreadable_fail_safe_none: {exc!r}"[:300],
        }
    if direction is not None:
        return resolve_for_direction(app_config, direction)
    if not _app_opted_in(app_config):
        # Legacy app, legacy row, no direction on disk: nothing could have asked
        # for less than today's behaviour.
        return LEGACY_DEFAULT, {
            "level": LEGACY_DEFAULT.value,
            "reason": "legacy_app_direction_missing_today_behaviour",
        }
    return DeliveryLevel.NONE, {
        "level": DeliveryLevel.NONE.value,
        "reason": "direction_missing_fail_safe_none",
    }


def story_level(
    story: Any,
    app_config: Any,
    root: Path,
    db_path: Path | None = None,
    *,
    persist: bool = True,
) -> DeliveryLevel:
    """The level the chain must enforce for ``story`` RIGHT NOW.

    = the recorded level, lowered (never raised) to the app's CURRENT ceiling,
    with ``push_to_main`` lowered to ``pr`` for factory self-edits (which must
    pass the PR-patch staging gate; a direct push would bypass it). Never
    raises; an unreadable value resolves to ``none``.

    ``persist=False`` (dry-run) mutates only the in-memory record: no DB write
    and no story event, so a preview stays a pure preview.
    """
    pending: list[tuple[str, dict[str, Any]]] = []
    try:
        changed = False
        raw = getattr(story, "delivery_level", None)
        if raw:
            try:
                level = parse_level(raw) or DeliveryLevel.NONE
            except ValueError:
                level = DeliveryLevel.NONE
                story.delivery_level = level.value
                changed = True
                pending.append(
                    (
                        EVENT_LOWERED,
                        {
                            "from": str(raw),
                            "to": level.value,
                            "reason": "unreadable_recorded_level",
                        },
                    )
                )
        else:
            level, info = _resolve_unrecorded(story, app_config, root)
            info["source"] = "first_touch"
            story.delivery_level = level.value
            changed = True
            pending.append((EVENT_RESOLVED, info))

        lowered = clamp(level, app_config.delivery.max)
        reason = "app_ceiling_lowered_mid_flight"
        if lowered is DeliveryLevel.PUSH_TO_MAIN:
            from factory.chain.auto_merge import _story_targets_factory_repo

            if _story_targets_factory_repo(app_config):
                lowered = DeliveryLevel.PR
                reason = "factory_self_edit_requires_staging_gate"
        if lowered is not level:
            story.delivery_level = lowered.value
            changed = True
            pending.append(
                (EVENT_LOWERED, {"from": level.value, "to": lowered.value, "reason": reason})
            )
            level = lowered

        if changed and persist:
            if db_path is not None and getattr(story, "id", None) is not None:
                from factory.chain.handlers import persist_story

                persist_story(story, db_path)
            for event, payload in pending:
                _log(story, event, payload, root)
        return level
    except Exception as exc:  # noqa: BLE001 - fail safe
        _logger.warning(
            "story %s: delivery level undeterminable (%r) — enforcing 'none'",
            getattr(story, "id", None),
            exc,
        )
        return DeliveryLevel.NONE


# --------------------------------------------------------------------------- #
# git helpers
# --------------------------------------------------------------------------- #


def _git(cwd: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False
    )


def commit_local_work(worktree: Path, story: Any) -> tuple[str | None, str | None]:
    """Level ``none``: commit any uncommitted work on the story branch. Never pushes.

    Returns ``(head_sha, error)``.
    """
    try:
        _git(worktree, "add", "-A")
        if _git(worktree, "status", "--porcelain").stdout.strip():
            proc = _git(
                worktree,
                "commit",
                "-m",
                f"factory: story {story.id} ({story.slug}) — delivered locally (delivery: none)",
            )
            if proc.returncode != 0:
                return None, f"git commit failed: {(proc.stderr or proc.stdout).strip()[:300]}"
        if _git(worktree, "status", "--porcelain").stdout.strip():
            return None, "worktree still dirty after commit"
        head = _git(worktree, "rev-parse", "HEAD")
        sha = head.stdout.strip()
        if head.returncode != 0 or not sha:
            return None, "could not resolve HEAD"
        return sha, None
    except (subprocess.SubprocessError, OSError) as exc:
        return None, f"git error: {exc!r}"[:300]


def fast_forward_default_branch(
    *, worktree: Path | None, base: str, expected_sha: str
) -> tuple[bool, str]:
    """Level ``push_to_main``: fast-forward ``origin/<base>`` to the gated commit.

    ``expected_sha`` is the commit the merge gates just evaluated. Refuses
    (``(False, reason)``) unless ALL of:

    * the worktree HEAD is still exactly ``expected_sha``;
    * ``origin/<base>`` (freshly fetched) is an ancestor of it, i.e. the update
      is a genuine fast-forward;
    * a plain, non-force ``git push`` succeeds (the remote re-checks FF);
    * a re-fetch shows ``origin/<base>`` now equals ``expected_sha``.

    Returns ``(True, sha)`` on success. Never force-pushes.
    """
    if worktree is None:
        return False, "no worktree for the gated commit"
    try:
        head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
        if not head or head != expected_sha:
            return (
                False,
                f"worktree HEAD {head[:12] or '?'} is not the gated commit {expected_sha[:12]}",
            )
        fetched = _git(worktree, "fetch", "origin", base)
        if fetched.returncode != 0:
            return False, f"git fetch origin {base} failed: {fetched.stderr.strip()[:200]}"
        anc = _git(worktree, "merge-base", "--is-ancestor", f"origin/{base}", head)
        if anc.returncode != 0:
            return False, f"not a fast-forward: origin/{base} is not an ancestor of {head[:12]}"
        pushed = _git(worktree, "push", "origin", f"{head}:refs/heads/{base}")
        if pushed.returncode != 0:
            return False, f"push rejected: {pushed.stderr.strip()[:200]}"
        _git(worktree, "fetch", "origin", base)
        now = _git(worktree, "rev-parse", f"origin/{base}").stdout.strip()
        if now != head:
            return False, f"origin/{base} is {now[:12] or '?'} after push, expected {head[:12]}"
        return True, head
    except (subprocess.SubprocessError, OSError) as exc:
        return False, f"git error: {exc!r}"[:300]


def worktree_head_and_files(
    worktree: Path | None, base: str
) -> tuple[str | None, list[str] | None]:
    """The worktree's HEAD sha and its changed files vs ``origin/<base>`` — the
    PR-less stand-in for ``gh``'s head sha / file list (``push_to_main``)."""
    if worktree is None:
        return None, None
    try:
        head = _git(worktree, "rev-parse", "HEAD").stdout.strip() or None
        diff = _git(worktree, "diff", "--name-only", f"origin/{base}...HEAD")
        files = (
            [ln for ln in diff.stdout.splitlines() if ln.strip()] if diff.returncode == 0 else None
        )
        return head, files
    except (subprocess.SubprocessError, OSError):
        return None, None
