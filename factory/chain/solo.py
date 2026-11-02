"""The production ``solo`` pipeline: one agent, one continuous conversation.

Operator decision 2026-11-02, built on the B.1 design (``b1_solo_mode_design``).
A story stamped ``pipeline: solo`` at spawn (``factory/job_routing.py``) runs:

    SM → dev (ONE long conversation, in-conversation gate feedback)
       → TESTS_GREEN → tech_writer → docs_enforcer → PR / delivery level
       → the SAME merge gates (``gates/evaluator.required_gate_labels``) → deploy

What it removes, and nothing else: the reviewer round-trip
(``TESTS_GREEN → review``) and the N fresh dev conversations that each read a
summary of the last one. What it keeps: SM, the worktree, the commit, the
tech-writer, the delivery-level enforcement at the PR-open site
(``handlers.handle_docs_enforcer`` / ``chain/delivery_gate.py``), every merge
gate, CI, deploy, the per-story budget breaker and the dev-retry exhaustion
path.

Why: the 2026-08-11 matched replay put one OpenHands agent at 12/18 (67%,
$1.19/resolved) against the chain's 10/18 (56%, $8.10/resolved), and the
Phase-1a ablation found the reviewer was not expensive in tokens — it caused
REWORK (9 fewer dev calls without it). See ``machinery_fixes_bought_zero_net_rate``
and ``b1_phase1a_reviewer_ablation_result``.

The mode is read from the STORY ROW (``StoryRecord.pipeline``), never from live
config: a story spawned under one mode finishes under it.

**Independence.** With no reviewer, the checks the dev cannot influence are the
app's merge gates and CI. The acceptance oracle is used when the app enables it
(``gates.acceptance_oracle``) — it is then a REQUIRED merge gate, and its leak
check runs as a blocking precondition on every solo dev dispatch — but it is NOT
required for solo: it is vacuous on non-web repos
(``oracle_vacuity_is_webapp_shaped``) and solo must work on any repo. Which
checks gate a given story is logged on its event stream as ``solo_checks``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from factory.runner import GateVerdict

_logger = logging.getLogger(__name__)

SOLO = "solo"

#: One conversation's wall clock (vs the chain's 1800 s per attempt). A TIMEOUT,
#: not a loop cap — it buys continuity, not iterations
#: (``chain_slices_the_dev_horizon``). Matches the single-agent bench arm.
SOLO_DEV_WALL_CLOCK_S = 5400

#: Gate checks inside one conversation (initial grade + up to 2 feedback
#: rounds). Bounded by the repo's "nothing loops more than 3" rule.
SOLO_MAX_GATE_ROUNDS = 3

#: Total solo dev conversations per story (each red one consumes a dev retry).
#: ``≤ 3`` per the operator's spec and CLAUDE.md. Must stay strictly above
#: ``handlers._MAX_DEV_SAME_SIGNATURE`` (2) so the early stall guard stays
#: reachable — asserted in ``tests/chain/test_solo_pipeline.py``.
SOLO_MAX_DEV_ATTEMPTS = 3

#: No-progress abort: a conversation whose working tree is byte-identical to its
#: start this long into the run is paused and graded as-is. Measured: the
#: replay's dead attempts made ZERO writes (``vyper-4801``: 3 x 1800 s, every
#: call a ``view``), while the slowest successful attempt's first write lands
#: far earlier than this.
SOLO_NO_PROGRESS_ABORT_S = 1800

_JOB_TEXT_CAP = 16_000


def is_solo(story: Any) -> bool:
    """True when ``story`` runs the solo pipeline.

    Reads ONLY the spawn stamp. A docs-chain story has no dev/review loop, so
    ``pipeline`` is meaningless for it and it always runs the docs chain.
    """
    if (getattr(story, "chain_kind", "tdd") or "tdd") == "docs":
        return False
    return (getattr(story, "pipeline", "chain") or "chain") == SOLO


def max_dev_attempts(story: Any, configured_cap: int) -> int:
    """The dev-retry cap that applies to ``story``.

    Chain stories keep the configured cap untouched. Solo stories are capped at
    ``SOLO_MAX_DEV_ATTEMPTS`` — each solo attempt is already up to
    ``SOLO_MAX_GATE_ROUNDS`` rounds inside a 5400 s conversation.
    """
    if not is_solo(story):
        return configured_cap
    return max(1, min(int(configured_cap), SOLO_MAX_DEV_ATTEMPTS))


# --------------------------------------------------------------------------- #
# Brief
# --------------------------------------------------------------------------- #


def build_solo_brief(direction: Any | None) -> str:
    """The solo addendum appended to the dev's initial message.

    The dev already receives the persona prompt, the repo context prelude
    (``compose_context_prelude``) and the SM story file. Solo adds the job's own
    text (the direction body — today only ANCESTOR directions reach the dev) and
    the working rules that replace the reviewer: reuse before writing, follow
    the repo's conventions, own the tests.
    """
    parts = [
        "# Solo pipeline — you own this job end to end",
        "",
        "There is NO separate reviewer on this job. You are the only agent that "
        "will read this code before the merge gates (the repo's test suite, its "
        "configured gates and CI) run on it. Work accordingly:",
        "",
        "1. **Find and reuse existing code first.** Before writing anything new, "
        "search the repo (grep/find) for functions, helpers, models, fixtures and "
        "patterns that already do part of the job. Extend or call them. Do NOT "
        "create a parallel reimplementation of something the repo already has.",
        "2. **Follow the repo's conventions** — layout, naming, error handling, "
        "logging, typing and test style — as shown by the neighbouring code and "
        "any contributor docs (README, CONTRIBUTING, CLAUDE.md, AGENTS.md, "
        "lint/format config).",
        "3. **Write or extend tests** for the behaviour you add or change, in the "
        "repo's existing test layout, and run the test command until it is green. "
        "Never weaken, skip or delete an existing test to get green.",
        "4. **Keep the change scoped to the job.** No drive-by refactors.",
        "5. When you stop, the factory runs its gate on your working tree and, if "
        "it is not green, sends you the reason in THIS conversation. Fix the cause "
        "and continue; a round that changes nothing ends the run.",
        "6. If the job cannot be done as written, end with `UNDERSPECIFIED: <why>` "
        "instead of guessing.",
    ]
    body = ""
    if direction is not None:
        body = (getattr(direction, "raw_body", "") or "").strip()
    if body:
        if len(body) > _JOB_TEXT_CAP:
            body = body[:_JOB_TEXT_CAP] + "\n\n[... job text truncated ...]"
        title = getattr(direction, "title", "") or ""
        parts += [
            "",
            "## The job, as submitted" + (f": {title}" if title else ""),
            "",
            "This is the original job text the story above was cut from. The story "
            "file is your scope; this is the intent behind it.",
            "",
            body,
        ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# In-conversation gate
# --------------------------------------------------------------------------- #


def make_gate_check(
    *,
    repo_path: Path,
    test_command: str | None,
    branch_is_empty: Any,
    production_delta: Any | None = None,
) -> Any:
    """Build the ``gate_check`` callable ``sandbox_run`` runs between rounds.

    Checks, in order (each later one only when the earlier ones pass):

    1. ``test_command`` — the app's configured test command, the same one the
       chain grades dev with (``runner._run_pytest``).
    2. ``non_empty_change`` — the branch carries a change vs its base (a green
       suite on an untouched tree proves nothing, and the tech-writer refuses an
       empty diff). ``branch_is_empty()`` returns True/False/None; None
       (unknown) PASSES — fail open, as the chain's own empty-diff check does.
    3. ``production_delta`` (only when the app sets
       ``gates.require_production_delta``) — the branch has a non-test change.
       Same True/False/None contract.
    """
    from factory.runner import _run_pytest

    def _check() -> GateVerdict:
        checks: list[dict[str, Any]] = []
        passed, out = _run_pytest(Path(repo_path), test_command=test_command)
        checks.append(
            {
                "name": "test_command",
                "passed": bool(passed),
                "reason": "green" if passed else "test command exited non-zero",
            }
        )
        if not passed:
            return GateVerdict(
                passed=False,
                reason=(
                    f"the test command ({test_command or 'default pytest'}) is not "
                    "green on your working tree"
                ),
                output=out,
                checks=checks,
            )
        empty = branch_is_empty()
        if empty is True:
            checks.append(
                {
                    "name": "non_empty_change",
                    "passed": False,
                    "reason": "no change vs the base branch",
                }
            )
            return GateVerdict(
                passed=False,
                reason=(
                    "tests are green but the branch has NO change vs its base — "
                    "nothing would ship. Implement the job (uncommitted edits "
                    "count; the factory commits the tree for you)."
                ),
                output=out,
                checks=checks,
            )
        checks.append(
            {
                "name": "non_empty_change",
                "passed": True,
                "reason": "change present" if empty is False else "unknown (fail open)",
            }
        )
        if production_delta is not None:
            delta = production_delta()
            if delta is False:
                checks.append(
                    {
                        "name": "production_delta",
                        "passed": False,
                        "reason": "only test files changed",
                    }
                )
                return GateVerdict(
                    passed=False,
                    reason=(
                        "tests are green but the branch changes ONLY test files — "
                        "the job needs a production-code change"
                    ),
                    output=out,
                    checks=checks,
                )
            checks.append(
                {
                    "name": "production_delta",
                    "passed": True,
                    "reason": "present" if delta is True else "unknown (fail open)",
                }
            )
        return GateVerdict(
            passed=True, reason="all in-conversation checks green", output=out, checks=checks
        )

    return _check


# --------------------------------------------------------------------------- #
# Oracle leak precondition + the logged check plan
# --------------------------------------------------------------------------- #


def oracle_leak_precheck(app_config: Any, worktree: Path) -> list[str] | None:
    """Blocking precondition for a solo dev dispatch.

    ``None`` = not applicable (the app has no acceptance oracle). Otherwise the
    list of oracle-shaped files in ``worktree`` that are REAL leaks (untracked,
    not removable by the sweep). Non-empty ⇒ the caller must NOT dispatch.
    Fail SAFE: if the check itself cannot run, report a synthetic leak so the
    dispatch blocks rather than proceeding blind.
    """
    gates = getattr(app_config, "gates", None)
    if not bool(getattr(gates, "acceptance_oracle", False)):
        return None
    try:
        from factory.chain.acceptance import sweep_leaked_oracles, unremovable_oracle_leaks

        sweep_leaked_oracles(worktree)
        return list(unremovable_oracle_leaks(worktree))
    except Exception as exc:  # noqa: BLE001 - fail safe: block
        _logger.warning("solo oracle leak check failed (blocking): %r", exc)
        return [f"<leak check failed: {exc!r}>"[:300]]


def checks_plan(app_config: Any, story: Any) -> dict[str, Any]:
    """What independently gates this solo story — logged as ``solo_checks``."""
    gates = getattr(app_config, "gates", None)
    oracle_on = bool(getattr(gates, "acceptance_oracle", False))
    try:
        from factory.chain.gates.evaluator import required_gate_labels

        required = required_gate_labels(app_config, story)
    except Exception as exc:  # noqa: BLE001 - telemetry only
        required = [f"<unavailable: {exc!r}>"[:200]]
    in_conv = ["test_command", "non_empty_change"]
    if bool(getattr(gates, "require_production_delta", False)):
        in_conv.append("production_delta")
    return {
        "pipeline": SOLO,
        "reviewer": "skipped (solo pipeline)",
        "in_conversation_checks": in_conv,
        "test_command": getattr(gates, "test_command", None),
        "max_gate_rounds": SOLO_MAX_GATE_ROUNDS,
        "wall_clock_s": SOLO_DEV_WALL_CLOCK_S,
        "no_progress_abort_s": SOLO_NO_PROGRESS_ABORT_S,
        "max_dev_attempts": SOLO_MAX_DEV_ATTEMPTS,
        "acceptance_oracle": (
            "enabled: required merge gate acceptance-verified + blocking leak precheck"
            if oracle_on
            else "disabled for this app: gates are the test suite + configured merge gates + CI"
        ),
        "merge_gates_required": required,
        "ci": "required checks via the auto-merge worker (tests-green reads CI)",
    }


__all__ = [
    "SOLO",
    "SOLO_DEV_WALL_CLOCK_S",
    "SOLO_MAX_DEV_ATTEMPTS",
    "SOLO_MAX_GATE_ROUNDS",
    "SOLO_NO_PROGRESS_ABORT_S",
    "build_solo_brief",
    "checks_plan",
    "is_solo",
    "make_gate_check",
    "max_dev_attempts",
    "oracle_leak_precheck",
]
