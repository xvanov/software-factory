"""Gate: ``acceptance-verified`` (WS1.2 — independent acceptance oracle).

The problem this closes
=======================

Loop-4 makes the dev author AND run its own tests. That is great for
convergence, but a coder that writes the tests judging it can reward-hack —
special-case the exact assertions, weaken them, or delete the hard ones
(ImpossibleBench: hiding the acceptance tests from the coder drops cheating to
~0). Every other merge gate re-derives truth from artifacts the dev produced
(``tests-green`` re-runs the dev's suite; ``tests-meaningful`` scans the dev's
tests). None of them is INDEPENDENT of the dev.

This gate is that independent layer. It runs an acceptance test authored from
the direction's acceptance criteria — the SPEC ONLY, blind to the dev's code
and the dev's tests — that the dev never sees or edits (authored at story spawn,
stored under ``state/acceptance/<app>/<story_id>/`` OUTSIDE the dev worktree;
see ``factory.chain.acceptance``). At merge time this gate copies that test into
the merge-candidate checkout, runs it against the app's python env, and passes
iff it exits 0 — so a story whose OWN tests are green but whose behaviour
violates an acceptance criterion is caught here.

Per-app opt-in (regression-safe), mirroring ``smoke-green``
==========================================================

* Not opted in (``gates.acceptance_oracle`` False): PASS (skip). The gate does
  not apply and ``required_gate_labels`` never adds it — apps without the oracle
  see no new merge blocks.
* Opted in but no oracle authored for this story (``acceptance_test_ref`` None —
  a legacy story or a direction with no ACs): NON-AUTHORITATIVE (passed=False,
  authoritative=False). ``required_gate_labels`` does NOT require it in this
  case (no ref), so the honest "no oracle ran" result surfaces without blocking.
* Opted in + oracle authored (``acceptance_test_ref`` set): the gate is
  REQUIRED. Real-run (checkout present): copy the stored test in, run it, pass
  iff exit 0, remove it. Dry-run / no checkout / missing stored file: cannot
  verify → NON-AUTHORITATIVE (never a false pass).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from factory.app_config import AppConfig
from factory.chain.gates.evaluator import GateResult, PRContext, _run_command

_DEFAULT_ACCEPTANCE_COMMAND = "python -m pytest {test_file} -q"


def evaluate(pr: PRContext, app_config: AppConfig) -> GateResult:
    label = "acceptance-verified"
    gates = app_config.gates

    # Not opted in: skip (pass). Mirrors the optional command gates — a missing
    # capability means "this gate does not apply", not "this gate fails".
    if not gates.acceptance_oracle:
        return GateResult(
            label=label,
            passed=True,
            reason="acceptance oracle not enabled for this app (skipped)",
            details={"acceptance_oracle": False},
        )

    story = pr.story
    ref = getattr(story, "acceptance_test_ref", None) if story is not None else None
    if not ref:
        # Opted in but nothing was authored (legacy story / no ACs). Not
        # required in this case (required_gate_labels keys off the ref), so a
        # non-authoritative result is honest without blocking.
        return GateResult(
            label=label,
            passed=False,
            reason="no acceptance test authored for this story (not applicable)",
            details={"authoritative": False, "acceptance_test_ref": None},
        )

    # Resolve the stored test. It lives under the factory root, deliberately
    # outside repo_root / the dev worktree.
    root = pr.software_factory_root
    stored: Path | None = None
    if root is not None:
        candidate = Path(ref)
        stored = candidate if candidate.is_absolute() else Path(root) / candidate

    if stored is None or not stored.exists():
        return GateResult(
            label=label,
            passed=False,
            reason=(
                "acceptance test ref recorded but the stored file is unreadable "
                f"(ref={ref!r}, root={'set' if root else 'unset'}) — cannot verify"
            ),
            details={"authoritative": False, "acceptance_test_ref": ref},
        )

    # Need a real checkout to run against. Dry-run (no worktree) cannot
    # re-derive truth — never claim a merge-authoritative pass.
    if pr.dry_run or pr.repo_root is None:
        return GateResult(
            label=label,
            passed=False,
            reason="[dry-run] acceptance oracle authored but not run (no checkout)",
            details={"authoritative": False, "acceptance_test_ref": ref},
        )

    # Real-run: copy the independent test into the merge-candidate checkout,
    # run it against the app's env, then remove it (never leave it behind to be
    # committed). Named distinctively so it cannot collide with app tests.
    sid = getattr(story, "id", None)
    dest_name = f"test_acceptance_oracle_{sid if sid is not None else 'story'}.py"
    dest = Path(pr.repo_root) / dest_name
    cmd_template = gates.acceptance_test_command or _DEFAULT_ACCEPTANCE_COMMAND
    cmd = cmd_template.format(test_file=dest_name)
    try:
        shutil.copyfile(stored, dest)
        exit_code, output = _run_command(cmd, cwd=Path(pr.repo_root))
    finally:
        try:
            if dest.exists():
                dest.unlink()
        except OSError:
            pass

    return GateResult(
        label=label,
        passed=exit_code == 0,
        reason=f"ran independent acceptance oracle exit_code={exit_code}",
        details={
            "authoritative": True,
            "acceptance_test_ref": ref,
            "command": cmd,
            "output_tail": output,
        },
    )
