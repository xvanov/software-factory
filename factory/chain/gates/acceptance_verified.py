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
iff it exits 0 AND at least one test actually passed — so a story whose OWN
tests are green but whose behaviour violates an acceptance criterion is caught
here.

What "blocking" keys off
========================

Required-ness is a property of the APP, not of a database flag: once
``gates.acceptance_oracle`` is on, ``required_gate_labels`` requires this label
for every non-docs story, and THIS gate decides applicability. Per-story
expectation is re-derived from the spec by
``acceptance.acceptance_expected_for_story`` (flag → ref → the direction on
disk), because the flag is written by a best-effort DB write: a lost write used
to leave ``acceptance_expected=0`` on a story that must be gated, and both the
gate and the required set then read that as "no acceptance criteria, skip" and
shipped it un-gated.

Resolution
==========

* Not opted in (``gates.acceptance_oracle`` False): PASS (skip). Never required.
* Opted in, story genuinely has no acceptance criteria: PASS (not applicable).
* Opted in, expectation cannot be established (no story row, unresolvable
  direction): AUTHORITATIVE BLOCK — never a silent pass.
* Expected + stored test readable:
    - real-run (checkout present): copy in, run, pass iff exit 0 AND the run
      reports at least one passing test, remove.
    - dry-run / no checkout: NON-AUTHORITATIVE (cannot verify), never a pass.
* Expected + stored test MISSING/unreadable (authoring flaked): AUTHORITATIVE
  BLOCK (passed=False, authoritative=True) — self-heal re-authors next tick,
  up to ``acceptance._MAX_AUTHOR_PASSES`` passes, after which it stays blocked
  and names the exhaustion for the operator.
* Any infrastructure error inside this gate (copy failed, command template
  broken, unexpected exception): AUTHORITATIVE BLOCK. A raised exception here
  used to escape ``evaluate_all_gates`` and abort the entire merge evaluation.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from factory.app_config import AppConfig
from factory.chain.acceptance import (
    ORACLE_COPY_GLOB,
    ORACLE_COPY_PREFIX,
    acceptance_expected_for_story,
    author_exhausted,
    author_passes,
    ref_is_readable,
    sweep_leaked_oracles,
)
from factory.chain.gates.evaluator import GateResult, PRContext, _run_command

# THIS interpreter, not a bare ``python`` resolved through PATH.
#
# The oracle authors Hypothesis PROPERTY tests from EARS-form acceptance criteria
# (WS4.3), so a generated test opens with ``from hypothesis import given`` — and
# ``hypothesis`` is a DEV EXTRA of this project. Bare ``python`` resolves through
# PATH to whatever the caller inherited; inside the dev sandbox that is a sibling
# app's venv (an interactive shell's rc file prepends it), which has no
# hypothesis. Collection then died with ModuleNotFoundError and the gate returned
# exit_code=2.
#
# That is a FALSE BLOCK, and an expensive one: the gate is required, so the story
# was re-dispatched to dev with an IDENTICAL failure signature until it exhausted
# its retries and sank to blocked_tests_need_clarification. Observed on stories
# 148 and 157 (2026-07-30); in both cases the dev's code was fine and the harness
# was broken.
#
# ``sys.executable`` is the fix rather than ``uv run``: the oracle runs the test in
# a bare temp directory with no ``pyproject.toml``, so ``uv run`` would find no
# project, build an ephemeral env, and still lack hypothesis. The interpreter
# already running the factory is by construction the one whose env satisfies the
# factory's own dev extras.
#
# It is only a DEFAULT, and for a real app it is usually the wrong one: an app
# whose deps are not in the factory's env MUST set ``acceptance_test_command``
# (plus ``acceptance_test_dir`` / ``acceptance_test_cwd``) so the oracle runs in
# the app's own harness — and must then guarantee hypothesis in that env if any
# of its acceptance criteria are EARS-shaped.
# ``-B`` (no bytecode) plus ``-p no:cacheprovider`` keep the run from leaving a
# compiled ``__pycache__`` copy of the hidden oracle, or a ``.pytest_cache`` entry
# naming its tests, inside the checkout. The sweep removes both anyway; not
# creating them is cheaper and still right if the sweep never gets to run.
_DEFAULT_ACCEPTANCE_COMMAND = (
    f"{sys.executable} -B -m pytest {{test_file}} -q -p no:cacheprovider"
)

# "N passed" in pytest's summary line. Used to refuse a VACUOUS pass: a file whose
# every test is skipped (the persona is told to ``pytest.skip`` criteria that are
# untestable as written) exits 0 while verifying nothing, and exit-0-means-pass
# would have turned that into a merge-authoritative green.
_PASSED_RE = re.compile(r"(\d+) passed")
# Enough of a pytest summary to know the run was READABLE even when nothing
# passed ("1 skipped in 0.01s" carries no "passed" token at all).
_SUMMARY_RE = re.compile(
    r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed|deselected)|no tests ran"
)


def _fmt_command(template: str, *, test_file: str) -> str:
    """Substitute ``{test_file}`` by literal replacement.

    NOT ``str.format``: a template containing any other brace (a shell brace
    expansion, a jq filter) raised ``KeyError`` from inside the gate, and that
    exception escaped into ``evaluate_all_gates`` and killed the whole merge
    evaluation for the app rather than failing this one gate.
    """
    return template.replace("{test_file}", test_file)


def _resolve_subdir(repo_root: Path, rel: str | None, *, what: str) -> Path:
    """Resolve a repo-relative config path, refusing to escape the checkout."""
    base = Path(repo_root).resolve()
    if not rel or not rel.strip():
        return base
    target = (base / rel.strip()).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"{what}={rel!r} resolves outside the checkout ({target})")
    if not target.is_dir():
        raise ValueError(f"{what}={rel!r} does not exist in the checkout ({target})")
    return target


def _git_common_dir(repo_root: Path) -> Path | None:
    """The checkout's shared git dir (``.git``, or the worktree's parent gitdir)."""
    try:
        proc = subprocess.run(  # noqa: S603,S607 - fixed argv, no shell
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    p = Path(out)
    return p if p.is_absolute() else (Path(repo_root) / p)


def _exclude_oracle_from_git(repo_root: Path) -> None:
    """Make a leaked oracle copy un-committable in this checkout.

    Defense in depth for the independence guarantee. The checkout the gate runs in
    IS the story's dev worktree, and the chain does a deterministic ``git add -A``
    + commit on the dev's green pass (``handlers._commit_green_dev_work``). If a
    crash ever leaves a copy behind, that commit would publish the hidden oracle
    into the PR. A local ``.git/info/exclude`` entry keeps ``add -A`` from staging
    it even then. Best-effort and local-only — never written to the repo tree.
    """
    common = _git_common_dir(repo_root)
    if common is None:
        return
    try:
        info = common / "info"
        info.mkdir(parents=True, exist_ok=True)
        excl = info / "exclude"
        pattern = ORACLE_COPY_GLOB
        existing = excl.read_text(encoding="utf-8") if excl.exists() else ""
        if pattern in existing:
            return
        sep = "" if existing.endswith("\n") or not existing else "\n"
        excl.write_text(
            f"{existing}{sep}# factory acceptance oracle (never committed)\n{pattern}\n",
            encoding="utf-8",
        )
    except OSError:
        return


def evaluate(pr: PRContext, app_config: AppConfig) -> GateResult:
    """Run the gate, converting ANY unexpected error into an authoritative block."""
    try:
        return _evaluate(pr, app_config)
    except Exception as exc:  # noqa: BLE001 - a broken detector must block, not raise
        return GateResult(
            label="acceptance-verified",
            passed=False,
            reason=(
                "acceptance oracle gate FAILED to run "
                f"({type(exc).__name__}: {exc}) — blocking (fail-closed)"
            ),
            details={"authoritative": True, "infra_error": repr(exc)[:500]},
        )


def _evaluate(pr: PRContext, app_config: AppConfig) -> GateResult:
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
    root = pr.software_factory_root

    # Re-derived from the SPEC, never trusted from the DB flag alone.
    expected, source = acceptance_expected_for_story(story, app_config, root)
    if not expected:
        # Opted in, but this story has no acceptance criteria to verify — not
        # applicable. (Only ever reached when the direction was resolvable and
        # genuinely carries no criteria.)
        return GateResult(
            label=label,
            passed=True,
            reason="story has no acceptance criteria (not applicable, skipped)",
            details={
                "acceptance_oracle": True,
                "acceptance_expected": False,
                "expected_source": source,
            },
        )

    # Expected but the stored oracle is missing/unreadable → authoring flaked, or
    # there is no story row to author for at all. BLOCK AUTHORITATIVELY (never a
    # silent pass). The tick self-heal (reauthor_missing_oracles) re-authors it
    # before a later merge attempt, so this is not normally a dead-end; once the
    # authoring pass ceiling is exhausted it IS a dead-end that names itself.
    if not ref_is_readable(story, root):
        exhausted = author_exhausted(story, root)
        passes = (
            author_passes(Path(root), story.app, story.id)
            if story is not None and root is not None
            else 0
        )
        tail = (
            " — authoring EXHAUSTED its pass ceiling; the operator must fix the "
            "direction's acceptance criteria or the app's acceptance harness config"
            if exhausted
            else " — authoring failed; blocking until it is re-authored (self-heals next tick)"
        )
        return GateResult(
            label=label,
            passed=False,
            reason=(
                "acceptance oracle EXPECTED but not available "
                f"(ref={ref!r}, root={'set' if root else 'unset'}, "
                f"expected_source={source}){tail}"
            ),
            details={
                "authoritative": True,
                "acceptance_expected": True,
                "acceptance_test_ref": ref,
                "expected_source": source,
                "author_passes": passes,
                "author_exhausted": exhausted,
            },
        )

    # Need a real checkout to run against. Dry-run (no worktree) cannot
    # re-derive truth — never claim a merge-authoritative pass.
    if pr.dry_run or pr.repo_root is None:
        return GateResult(
            label=label,
            passed=False,
            reason="[dry-run] acceptance oracle present but not run (no checkout)",
            details={"authoritative": False, "acceptance_test_ref": ref},
        )

    # Real-run: copy the independent test into the merge-candidate checkout,
    # run it against the app's env, then remove it (never leave it behind to be
    # committed). Named distinctively (story id, else head_sha) so it cannot
    # collide with app tests.
    # ref_is_readable(story, root) returned True above → story, ref, root all set.
    assert story is not None and ref is not None and root is not None
    repo_root = Path(pr.repo_root)
    sid = story.id if story.id is not None else pr.head_sha
    dest_name = f"{ORACLE_COPY_PREFIX}{sid}.py"

    # WHERE the file goes and WHERE the command runs. Defaults are the checkout
    # root; a real app almost always needs both (sacrifice: ``backend/tests`` and
    # ``backend``), because a python file dropped at the repo root can neither
    # import the app package nor pick up the conftest that provides its test env.
    dest_dir = _resolve_subdir(repo_root, gates.acceptance_test_dir, what="acceptance_test_dir")
    run_cwd = _resolve_subdir(repo_root, gates.acceptance_test_cwd, what="acceptance_test_cwd")
    dest = dest_dir / dest_name

    # Any copy left behind by an earlier interrupted run is removed BEFORE this
    # one, and the pattern is excluded from git, so a leaked oracle can neither be
    # read by the dev on a later cycle nor committed into the PR.
    swept_before = sweep_leaked_oracles(repo_root)
    _exclude_oracle_from_git(repo_root)

    p = Path(ref)
    stored = p if p.is_absolute() else Path(root) / p

    try:
        rel_for_cmd = dest.relative_to(run_cwd).as_posix()
    except ValueError:
        # dest is not under the cwd (e.g. dir=backend/tests, cwd=backend/app):
        # an absolute path is always valid for pytest.
        rel_for_cmd = dest.as_posix()

    cmd_template = gates.acceptance_test_command or _DEFAULT_ACCEPTANCE_COMMAND
    if "{test_file}" not in cmd_template:
        # A command that never names the oracle does not run it. Exit 0 would then
        # be a green gate that verified nothing at all — the worst kind of
        # fail-open, produced by a single config typo.
        raise ValueError(
            "gates.acceptance_test_command must contain '{test_file}' "
            f"(got {cmd_template!r}) — a command that does not name the oracle "
            "cannot be evidence that it ran"
        )
    cmd = _fmt_command(cmd_template, test_file=rel_for_cmd)
    swept_after: list[str] = []
    try:
        shutil.copyfile(stored, dest)
        exit_code, output = _run_command(cmd, cwd=run_cwd)
    finally:
        # The sweep IS the cleanup: it removes this run's copy and anything an
        # earlier crash left elsewhere in the tree.
        swept_after = sweep_leaked_oracles(repo_root)

    details: dict[str, object] = {
        "authoritative": True,
        "acceptance_test_ref": ref,
        "expected_source": source,
        "command": cmd,
        "cwd": str(run_cwd),
        "test_file": rel_for_cmd,
        "exit_code": exit_code,
        "swept_before_run": swept_before,
        "swept_after_run": swept_after,
        "output_tail": output,
    }

    # The copy MUST be gone. If it is not, the oracle is sitting in the dev's
    # worktree — block rather than pass, because passing here would leave the next
    # dev cycle able to read the hidden test (and the chain's ``git add -A`` able
    # to commit it).
    if dest.exists():
        details["leaked_copy"] = str(dest)
        return GateResult(
            label=label,
            passed=False,
            reason=(
                f"acceptance oracle copy could not be removed from the checkout ({dest}) — "
                "blocking to protect dev-blindness"
            ),
            details=details,
        )

    if exit_code != 0:
        return GateResult(
            label=label,
            passed=False,
            reason=f"ran independent acceptance oracle exit_code={exit_code}",
            details=details,
        )

    # Exit 0 is not enough. A pytest run in which every test SKIPPED also exits 0
    # while verifying nothing, and the persona is explicitly allowed to emit
    # ``pytest.skip`` for a criterion that is untestable as written — so
    # "exit 0 → merge-authoritative green" would ship an un-verified story with a
    # gate that claims to have checked it. Require positive evidence instead.
    #
    # The count is read from the OUTPUT, not gated on the command string: an app
    # whose command is a wrapper (``make acceptance``) still prints pytest's
    # summary, and keying off ``"pytest" in cmd`` would have skipped the check for
    # exactly those apps. Only a run whose output carries no summary at all is
    # unjudgeable — and then the command decides: if it named pytest we expected a
    # summary and its absence is itself suspicious (block); otherwise the app owns
    # a runner we cannot read and exit 0 is all we have.
    m = _PASSED_RE.search(output)
    if m is not None or _SUMMARY_RE.search(output) is not None:
        n_passed = int(m.group(1)) if m is not None else 0
        details["tests_passed"] = n_passed
        if n_passed < 1:
            return GateResult(
                label=label,
                passed=False,
                reason=(
                    "acceptance oracle exited 0 but reported NO passing test "
                    "(vacuous run — every criterion skipped, or nothing collected); "
                    "blocking rather than crediting a verification that did not happen"
                ),
                details=details,
            )
    elif "pytest" in cmd:
        details["tests_passed"] = None
        return GateResult(
            label=label,
            passed=False,
            reason=(
                "acceptance oracle exited 0 but produced no pytest result summary "
                "(nothing ran, or the output was suppressed) — blocking rather than "
                "crediting a verification that cannot be evidenced"
            ),
            details=details,
        )
    else:
        # A non-pytest runner we cannot read: exit 0 is all we have. Recorded so an
        # operator can see the gate's evidence was weaker here.
        details["tests_passed"] = None
        details["vacuity_check"] = "skipped (unreadable non-pytest runner output)"

    return GateResult(
        label=label,
        passed=True,
        reason=f"ran independent acceptance oracle exit_code={exit_code}",
        details=details,
    )
