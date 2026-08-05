"""The feedback-loop caps are a SAFETY property, not just a budget guard.

Nobody should raise them as an "improvement", so the reasoning is pinned here
rather than living only in a comment:

* ImpossibleBench (ICLR 2026, arXiv 2510.20270) measured cheating rising
  33% -> 38% when agents get MULTIPLE submissions with feedback. More cycles is
  the condition that produced MORE gaming.
* Self-refine / self-repair at MATCHED budget buys only 3-10% (arXiv
  2306.09896) — the same tokens spent on more independent attempts do about as
  well, so extra cycles are not where the win is.
* Under Loop-4 the dev writes the code AND the tests, and the reviewer's approve
  rule reads a ``test_quality_score`` derived from those same tests. Each extra
  cycle is therefore another chance to make the CHECK agree with the code
  instead of the code agree with the story. The 2026-08-04 hidden-oracle
  grading measured the outcome: the chain's own green verdict was 40% precise
  (6 of 15 "green" rows actually passed).

This PR deliberately changed NO cap. If a future change needs to raise one, the
burden is a measurement, not an intuition — and the cheaper moves are the
checks the dev cannot author: a hidden oracle, a mutation score instead of
``test_quality_score``, or execution output fed to the reviewer.
"""

from __future__ import annotations

# The operator rule ("nothing loops more than ~3 times") and the literature
# above agree on the ceiling.
_CEILING = 3


def test_dev_and_review_caps_stay_at_or_below_three() -> None:
    from factory.chain.handlers import (
        _MAX_DEV_RETRIES,
        _MAX_DEV_SAME_SIGNATURE,
        _MAX_REVIEW_CYCLES,
        _MAX_REVIEW_STUCK,
    )

    assert _MAX_DEV_RETRIES <= _CEILING
    assert _MAX_REVIEW_CYCLES <= _CEILING
    # The early-escalation guards must stay STRICTLY below their hard caps or
    # they become unreachable and two layered guards collapse into one.
    assert _MAX_DEV_SAME_SIGNATURE < _MAX_DEV_RETRIES
    assert _MAX_REVIEW_STUCK < _MAX_REVIEW_CYCLES


def test_ci_fix_and_auto_recovery_caps_stay_at_or_below_three() -> None:
    from factory.chain.auto_merge import _MAX_CI_FIX_CYCLES
    from factory.chain.orchestrator import (
        _MAX_AUTO_RECOVERIES,
        _MAX_DEPENDENCY_DEFERRALS,
    )

    assert _MAX_CI_FIX_CYCLES <= _CEILING
    assert _MAX_AUTO_RECOVERIES <= _CEILING
    assert _MAX_DEPENDENCY_DEFERRALS <= _CEILING


def test_the_evidence_stays_next_to_the_constants() -> None:
    """A cap whose rationale is only in a test file gets raised by someone
    reading the module. The citation has to be where the number is."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "factory" / "chain"
    handlers_src = (root / "handlers.py").read_text(encoding="utf-8")
    merge_src = (root / "auto_merge.py").read_text(encoding="utf-8")
    for src in (handlers_src, merge_src):
        assert "2510.20270" in src, "the ImpossibleBench citation was dropped"
    assert "2306.09896" in handlers_src, "the self-repair citation was dropped"
