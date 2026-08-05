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
see ``factory.chain.acceptance``).

WHAT MAKES ITS GREEN MEAN SOMETHING (2026-08-05)
================================================

Running the oracle is not enough. Three properties have to hold or the green
carries no information, and none of them was checked when the gate first became
executable:

1. **The oracle must be able to FAIL.** ``normalize_oracle_source`` deliberately
   requires no ``assert``, and the vacuity check only catches skips — so
   ``def test_ac1(): assert True`` ran, reported "1 passed", and produced a
   merge-authoritative green against an implementation that violated the
   criterion. Closed by running the SAME oracle at the PR's MERGE BASE and
   requiring it to be RED there (PLAN A.6, ``factory.chain.red_green``), with
   ABLATION (``factory.chain.mutation.check_can_fail``) as the fallback when that
   base run yields no usable answer.

   ⚠ THE CAVEAT — it lives in ``red_green``'s docstring and is repeated here
   because this is where it bites: only the *fails-at-base* half is oracle-free.
   Agentless measured 213/300 generated tests reproducing a bug but only 94/300
   also flipping green under the gold patch, so a hard both-halves gate rejects
   good work. Therefore "red at base" means AT LEAST ONE test failed there, and a
   base run that cannot be TRUSTED is ``unknown`` — a *skipped-with-reason*,
   which blocks and is never read as a pass (regression-only, never "approve").

   TWO MECHANISMS, ONE ORDER — and the order is the whole argument
   --------------------------------------------------------------
   ``red_green.base_verdict`` asks *"is this oracle RED without the story's
   diff?"*. ``mutation.check_can_fail`` asks *"if we gut a symbol the diff
   touched, does the oracle go red?"*. They are not redundant and they are not
   interchangeable: **the base run is the STRONGER instrument**, so it always
   speaks first and its definitive answers are never overturned.

   Why stronger: ablation is satisfied by an oracle that merely *calls* the code.
   ``def test(): client.post("/healthz"); assert True`` goes red under ablation
   (the gutted handler raises) while asserting nothing at all — whereas at the
   merge base that same oracle passes, which is the correct verdict "this carries
   no information about the diff". So ablation is used **only** where the base run
   returned ``unknown`` (no readable summary, timeout, nothing collected at base,
   the acceptance harness does not resolve at base — common for a story that
   CREATES the test directory). It is never allowed to rescue a base run that came
   back ``green``: ``green`` is a definitive "this oracle does not discriminate
   this diff", and the ablation of a diff symbol would answer a weaker question
   more permissively. That state stays a block with an operator waiver as its only
   path back.

   The ``unknown`` state is also, by construction, not something the dev can
   steer into: the base run happens at the merge base, in a tree that predates the
   diff, under operator-owned app config. And the ablation fallback reproduces the
   primary path's structural defences in its own scratch clone — same channel
   rollback, plus a check that the clone really is the graded commit — so even a
   dev who could force ``unknown`` would gain nothing.

2. **The dev must not control the environment that judges it.** The old run
   happened in ``PRContext.repo_root`` — the story's own dev worktree — with
   pytest loading whatever ``conftest.py`` / ``pyproject.toml`` the diff put
   there. Two 7-line attacks forced a pass against a violating implementation (a
   ``pytest_runtest_call`` hookwrapper calling ``outcome.force_result(None)``, and
   ``addopts = "-p _fixup"`` plus a root plugin). Closed by running in a
   THROWAWAY git worktree (``red_green.judge_worktree``) — so nothing the dev left
   UNTRACKED exists there at all — in which the diff's own contribution to the
   oracle's import path is rolled back to the merge base. The oracle is never
   copied into the dev's tree, which also closes the leak window and the
   ``.pytest_cache`` disclosure.

   PRODUCTION CODE FROM HEAD, THE WHOLE TEST SURFACE FROM BASE. That is the
   invariant, and it is wider than "collection channels" because restricting it to
   collection channels left a working forced-pass attack: the oracle is copied into
   the app's test directory, so pytest imports it as part of that package and runs
   ``backend/tests/__init__.py`` first — seven lines there rebind the function under
   test and a violating implementation goes green, with a RED merge-base run
   corroborating it (the file does not exist at base). ``__init__.py`` under
   ``tests/`` is test CODE, not a collection channel. The rollback set is therefore
   defined as the exact complement of ``factory.diff_paths.is_production_path``, so
   widening either underlying classifier widens it for free.

   Still CONVENTIONAL, not structural: what gets restored is the app's own
   PREVIOUSLY MERGED test surface, which is dev-authored history — sacrifice's
   ``backend/tests/conftest.py:147`` overrides ``get_db`` with an autouse fixture
   and the shipped ``acceptance_harness_hint`` advertises that as a feature, so the
   oracle is judged against a dev-configured DB substitute. What IS structural:
   THIS story's diff cannot change it.

   ⚠⚠ AND HERE IS WHAT THIS GATE DOES **NOT** GIVE YOU — READ BEFORE FLIPPING THE
   FLAG. This gate's green is bounded by "the diff's production code did not attack
   the harness", and **nothing checks that**. Measured 2026-08-05, three lines in
   the module under test:

       import sys
       if 'pytest' in sys.modules:
           import _pytest.python
           _pytest.python.Function.runtest = lambda self: None

   ...produces ``passed=True, verified=True, authoritative=True`` against an
   implementation that violates the criterion, with a genuinely RED merge-base run
   corroborating it. An ablation-AWARE variant of the same trick forges the fallback
   route too (detect the sentinel raise, forge red; otherwise forge green).

   No rollback set closes this. The oracle must import the diff's production code to
   test it, so that code runs in the interpreter that computes the verdict, and
   in-process anything is defeatable in-process. The two candidate closures are
   (a) an out-of-process behavioural oracle — the verdict computed in the factory
   from HTTP responses, the way ``smoke-green`` already works — or (b) a
   tampering detector over the diff's production paths, which would false-block the
   ``factory`` app wholesale because its production code IS test infrastructure.
   Neither is built. See
   ``tests/…::test_KNOWN_OPEN_production_code_can_patch_pytest_in_process``, an
   ``xfail(strict=True)`` that turns red the day this is fixed.

3. **The tree must be the merge candidate.** ``auto_merge._story_worktree``
   resets to ``origin/<feature>`` only when ``git fetch`` returned 0, so on a
   fetch failure the gate graded whatever the worktree held — and could return an
   authoritative pass for an unrelated commit. The gate now requires
   ``pr.head_sha`` to be an ANCESTOR of the checkout's HEAD (not equal to it: the
   worktree merges ``origin/main`` in first, so equality would false-block) — AND
   that HEAD adds nothing over the PR head except the base branch
   (``red_green.extra_commits_beyond``). Ancestry alone still lets a worktree that
   is AHEAD of ``origin/<feature>`` — a commit the chain made and failed to push —
   pass as the merge candidate, which is the same fault one level in. Found by the
   adversarial pass on the fix for that fault.

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
* Expected + stored test MISSING/unreadable (authoring flaked): AUTHORITATIVE
  BLOCK — the self-heal re-authors it, up to ``acceptance._MAX_AUTHOR_PASSES``
  passes, after which it stays blocked and names the exhaustion.
* Dry-run / no checkout: NON-AUTHORITATIVE block (cannot verify), never a pass.
* Real run — three families, and only the first is a green:
    - **pass**: HEAD run green (≥1 passed, nothing failed, one readable summary)
      AND failability established — the base run RED
      (``failability_route="merge_base_red"``), or, when the base run was
      ``unknown``, an ablation of the diff's own production symbols that turned the
      oracle red (``failability_route="ablation"``). ``authoritative=True``,
      ``verified=True``.
    - **block**: the HEAD run failed or was vacuous. ``authoritative=True``.
    - **skipped-with-reason**: provenance unverified, no judge tree, no merge
      base, a collection channel we could not restore, conflicting summaries, an
      unreadable runner, an oracle that already passes at base, or a base run we
      cannot trust. ``passed=False``, ``authoritative=False``, ``verified=False``
      — it blocks (fail-safe), does not blame the dev, is recorded for
      ``factory inbox``, and is the only family an operator waiver can clear
      (``acceptance.read_waiver`` — never a red HEAD run, never tampering,
      never the wrong commit).
* Any infrastructure error inside this gate: AUTHORITATIVE BLOCK. A raised
  exception here used to escape ``evaluate_all_gates`` and abort the entire merge
  evaluation.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from factory.app_config import AppConfig, AppGatesConfig
from factory.chain.acceptance import (
    ORACLE_COPY_GLOB,
    ORACLE_COPY_PREFIX,
    acceptance_dir,
    acceptance_expected_for_story,
    author_exhausted,
    author_passes,
    clear_gate_block,
    oracle_sha256,
    read_waiver,
    record_gate_block,
    ref_is_readable,
    sweep_leaked_oracles,
    unremovable_oracle_leaks,
)
from factory.chain.gates.evaluator import GateResult, PRContext, _run_command
from factory.chain.red_green import (
    base_verdict,
    cache_get,
    cache_put,
    changed_paths_since,
    classify_pytest_run,
    extra_commits_beyond,
    head_contains_sha,
    head_sha,
    judge_worktree,
    resolve_base_sha,
    restore_paths_from,
    run_key,
)
from factory.diff_paths import is_collection_channel_path, is_production_path

_LABEL = "acceptance-verified"

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
#
# ``-B`` (no bytecode) plus ``-p no:cacheprovider`` keep the run from leaving a
# compiled copy of the hidden oracle or a ``.pytest_cache`` entry naming its
# tests. Both now land in a throwaway judge tree, but an app that overrides the
# command should keep the flags: ``.pytest_cache/v/cache/nodeids`` records the
# oracle's TEST NAMES and ``lastfailed`` records which of its assertions failed.
_DEFAULT_ACCEPTANCE_COMMAND = (
    f"{sys.executable} -B -m pytest {{test_file}} -q -p no:cacheprovider"
)


# The ablation fallback runs one oracle invocation per target, plus one baseline.
# Capped at 3 by the repo rule that nothing loops more than 3 times, and because
# the first target is the symbol the diff changed MOST — the marginal value of a
# fourth is small and the cost is another oracle run per tick.
_MAX_ABLATION_TARGETS = 3
# Matches ``evaluator._run_command``'s budget, deliberately: the ablation runs the
# SAME oracle command the HEAD run already completed inside, so anything much
# longer would only be waiting on a hang.
_ABLATION_TIMEOUT_S = 600
# HARD wall clock for the whole fallback, and it is not decoration. Each target
# costs a green baseline plus a mutant run, so three targets at the per-run budget
# is a 60-minute gate — inside ``evaluate_all_gates``, which has no timeout of its
# own, on a tick that other stories are queued behind. The per-run timeout is
# clamped to whatever is left, so this is the real bound, not a hint. Running out
# of budget is "not proven", i.e. the block stands.
_ABLATION_BUDGET_S = 900
# Below this there is no point starting another target: a run that cannot finish
# reports a timeout, which is an unattributable red, which is not a proof anyway.
_ABLATION_MIN_RUN_S = 30


class _ConfigError(ValueError):
    """The app's acceptance config does not resolve against a given tree."""


@dataclass
class _OracleRun:
    exit_code: int
    output: str
    command: str
    cwd: str
    test_file: str


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
        raise _ConfigError(f"{what}={rel!r} resolves outside the checkout ({target})")
    if not target.is_dir():
        raise _ConfigError(f"{what}={rel!r} does not exist in the checkout ({target})")
    return target


def _command_template(gates: AppGatesConfig) -> str:
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
    return cmd_template


def _oracle_test_file(gates: AppGatesConfig, dest_name: str) -> str:
    """Where the copied oracle sits, RELATIVE TO the configured run cwd.

    Computed from the config strings only — never from a concrete tree — so the
    identical invocation replays in the judge worktree, at the merge base, and
    inside ``mutation.check_can_fail``'s scratch clone. ``os.path.relpath`` covers
    the case where the test dir is not under the cwd (dir=``backend/tests``,
    cwd=``backend/app`` ⇒ ``../tests/…``); the old code emitted an absolute path
    there, which is correct for exactly one tree and wrong for every other.
    """
    d = (gates.acceptance_test_dir or "").strip() or "."
    c = (gates.acceptance_test_cwd or "").strip() or "."
    rel = os.path.relpath(os.path.join(d, dest_name), c)
    return PurePosixPath(Path(rel).as_posix()).as_posix()


def _place_oracle(
    tree: Path, gates: AppGatesConfig, stored: Path, dest_name: str
) -> tuple[Path, Path]:
    """Copy the stored oracle into ``tree``; return ``(dest, run_cwd)``.

    ``tree`` is always a THROWAWAY tree, never the dev's. Raises
    :class:`_ConfigError` when the configured dir/cwd does not resolve there — at
    the merge base that is an ordinary "cannot verify" rather than an infra fault,
    so the callers handle it differently.
    """
    dest_dir = _resolve_subdir(tree, gates.acceptance_test_dir, what="acceptance_test_dir")
    run_cwd = _resolve_subdir(tree, gates.acceptance_test_cwd, what="acceptance_test_cwd")
    dest = dest_dir / dest_name
    shutil.copyfile(stored, dest)
    return dest, run_cwd


def _run_oracle_in(
    tree: Path, gates: AppGatesConfig, stored: Path, dest_name: str
) -> _OracleRun:
    """Copy the stored oracle into ``tree`` and run the app's acceptance command."""
    _dest, run_cwd = _place_oracle(tree, gates, stored, dest_name)
    rel_for_cmd = _oracle_test_file(gates, dest_name)
    cmd = _fmt_command(_command_template(gates), test_file=rel_for_cmd)
    exit_code, output = _run_command(cmd, cwd=run_cwd)
    return _OracleRun(
        exit_code=exit_code, output=output, command=cmd,
        cwd=str(run_cwd), test_file=rel_for_cmd,
    )


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

    Defense in depth for the independence guarantee. The oracle now runs in a
    throwaway judge tree, so the gate no longer writes into the dev's worktree at
    all — but a copy left by an OLDER factory build, or by any future path that
    runs in-tree, sits where the chain does a deterministic ``git add -A`` +
    commit on the dev's green pass (``handlers._commit_green_dev_work``), which
    would publish the hidden oracle into the PR. A local ``.git/info/exclude``
    entry keeps ``add -A`` from staging it even then. Best-effort and local-only —
    never written to the repo tree.
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
            label=_LABEL,
            passed=False,
            reason=(
                "acceptance oracle gate FAILED to run "
                f"({type(exc).__name__}: {exc}) — blocking (fail-closed)"
            ),
            details={
                "authoritative": True,
                "verified": False,
                "infra_error": repr(exc)[:500],
            },
        )


def _unverifiable(
    pr: PRContext,
    details: dict[str, object],
    *,
    kind: str,
    why: str,
    waiver_sha: str | None = None,
) -> GateResult:
    """SKIPPED-WITH-REASON: the oracle could not be graded, so we do not approve.

    Blocks, but non-authoritatively: this is not evidence against the dev, it names
    the operator action, and it is recorded for ``factory inbox`` (a story stuck
    here sits at ``pr_open`` with no rejection reason and would otherwise appear in
    no operator surface at all). The one thing it must never be is a green —
    ``passed`` and ``verified`` are both False.

    ``waiver_sha`` opts this state into the operator waiver
    (``acceptance.read_waiver``); pass ``None`` for states where a human must not
    be able to wave the story through (tampered evidence, the wrong commit).
    """
    story = pr.story
    app = story.app if story is not None else ""
    sid = story.id if story is not None else None
    details = {
        **details,
        "authoritative": False,
        "verified": False,
        "unverifiable_kind": kind,
    }
    reason = f"acceptance oracle NOT VERIFIED ({kind}): {why}"

    waiver = (
        read_waiver(pr.software_factory_root, app, sid, for_oracle_sha=waiver_sha)
        if waiver_sha
        else None
    )
    if waiver is not None:
        details["waived"] = True
        details["waiver"] = {
            "reason": str(waiver.get("reason"))[:300],
            "operator": str(waiver.get("operator")),
            "recorded_at": waiver.get("recorded_at"),
        }
        clear_gate_block(pr.software_factory_root, app, sid)
        return GateResult(
            label=_LABEL,
            passed=True,
            reason=(
                f"{reason} — cleared by an OPERATOR WAIVER "
                f"({str(waiver.get('reason'))[:120]}); the oracle did NOT verify this story"
            ),
            details=details,
        )

    record_gate_block(pr.software_factory_root, app, sid, kind=kind, reason=reason)
    return GateResult(label=_LABEL, passed=False, reason=reason, details=details)


def _evaluate(pr: PRContext, app_config: AppConfig) -> GateResult:  # noqa: PLR0911,PLR0912,PLR0915
    gates = app_config.gates

    # Not opted in: skip (pass). Mirrors the optional command gates — a missing
    # capability means "this gate does not apply", not "this gate fails".
    if not gates.acceptance_oracle:
        return GateResult(
            label=_LABEL,
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
            label=_LABEL,
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
            label=_LABEL,
            passed=False,
            reason=(
                "acceptance oracle EXPECTED but not available "
                f"(ref={ref!r}, root={'set' if root else 'unset'}, "
                f"expected_source={source}){tail}"
            ),
            details={
                "authoritative": True,
                "verified": False,
                "acceptance_expected": True,
                "acceptance_test_ref": ref,
                "expected_source": source,
                "author_passes": passes,
                "author_exhausted": exhausted,
            },
        )

    # ref_is_readable(story, root) returned True above → story, ref, root all set.
    assert story is not None and ref is not None and root is not None

    details: dict[str, object] = {
        "acceptance_test_ref": ref,
        "expected_source": source,
    }

    # Need a real checkout to run against. Dry-run (no worktree) cannot
    # re-derive truth — never claim a merge-authoritative pass.
    if pr.dry_run or pr.repo_root is None:
        return GateResult(
            label=_LABEL,
            passed=False,
            reason="[dry-run] acceptance oracle present but not run (no checkout)",
            details={**details, "authoritative": False, "verified": False},
        )

    repo_root = Path(pr.repo_root)
    p = Path(ref)
    stored = p if p.is_absolute() else Path(root) / p
    oracle_sha = oracle_sha256(stored.read_text(encoding="utf-8", errors="replace"))
    details["oracle_sha256"] = oracle_sha[:16]
    sid = story.id if story.id is not None else pr.head_sha
    dest_name = f"{ORACLE_COPY_PREFIX}{sid}.py"

    # Validate the command template first: a broken template is an operator config
    # fault and must block AUTHORITATIVELY (it raises out to ``evaluate``), never
    # be mistaken for a run we merely could not read.
    cmd_template = _command_template(gates)

    # Independence hygiene in the DEV worktree. The oracle no longer runs there, so
    # this only cleans up after older builds and interrupted runs — but a copy left
    # in the dev's tree is still a breach, so anything the sweep cannot remove
    # BLOCKS (the sweep now REFUSES to delete when git cannot say what is tracked).
    details["swept_before_run"] = sweep_leaked_oracles(repo_root)
    _exclude_oracle_from_git(repo_root)
    # Only a REAL leak blocks: an untracked copy (or a tree where git cannot say).
    # A git-TRACKED file matching the prefix is the app's own committed test, and
    # blocking on it was a permanent unwaivable wedge — see
    # ``acceptance.unremovable_oracle_leaks``.
    leaked = unremovable_oracle_leaks(repo_root)
    if leaked:
        return GateResult(
            label=_LABEL,
            passed=False,
            reason=(
                "acceptance oracle copies are present in the DEV worktree and could not be "
                f"removed ({leaked[:5]}) — blocking to protect dev-blindness"
            ),
            details={
                **details, "authoritative": True, "verified": False, "leaked_copies": leaked,
            },
        )

    # (3) PROVENANCE — grade the merge candidate or grade nothing.
    contains, why = head_contains_sha(repo_root, pr.head_sha)
    details["head_sha"] = pr.head_sha
    details["provenance"] = why
    if contains is not True:
        return _unverifiable(
            pr, details,
            kind="provenance_unverified" if contains is None else "wrong_commit",
            why=(
                f"the checkout does not demonstrably contain the PR head commit ({why}) — "
                "``_story_worktree`` only resets to origin/<feature> when git fetch "
                "returned 0, so an authoritative pass here could describe code that is "
                "not the one being merged"
            ),
            waiver_sha=None,  # never waivable: this is not the merge candidate
        )

    # ...and nothing BEYOND the merge candidate. Ancestry alone allows a checkout
    # that is the PR head PLUS unpushed local commits, which is the same "grading
    # something other than what will merge" fault one level in.
    extra, how_extra = extra_commits_beyond(repo_root, pr.head_sha, pr.base_branch)
    details["provenance_extra"] = how_extra
    if extra is None or extra:
        details["extra_commits"] = extra[:5] if extra else None
        return _unverifiable(
            pr, details,
            kind="provenance_unverified" if extra is None else "checkout_ahead_of_pr_head",
            why=(
                f"the checkout carries work that is neither the PR head nor the base "
                f"branch ({how_extra}: {(extra or [])[:5]}) — an authoritative verdict "
                "here would describe code that is not being merged"
                if extra
                else f"could not establish that the checkout adds nothing to the PR head "
                     f"({how_extra})"
            ),
            waiver_sha=None,  # never waivable: this is not the merge candidate
        )

    base_sha, how = resolve_base_sha(repo_root, pr.base_branch)
    details["base_ref"] = how
    if base_sha is None:
        return _unverifiable(
            pr, details, kind="no_merge_base",
            why=f"cannot resolve the merge base ({how}), so the oracle's failability is unknown",
            waiver_sha=oracle_sha,
        )
    details["base_sha"] = base_sha[:12]
    local_head = head_sha(repo_root) or ""
    details["checkout_head"] = local_head[:12]
    if base_sha == local_head:
        return _unverifiable(
            pr, details, kind="base_equals_head",
            why=(
                f"the merge base IS the checkout HEAD ({base_sha[:12]}) — there is no story "
                "diff here for the oracle to discriminate"
            ),
            waiver_sha=oracle_sha,
        )

    changed = changed_paths_since(repo_root, base_sha)
    if changed is None:
        return _unverifiable(
            pr, details, kind="diff_unreadable",
            why=f"git could not diff {base_sha[:12]}..HEAD in the checkout",
            waiver_sha=oracle_sha,
        )
    # PRODUCTION CODE FROM HEAD, THE WHOLE TEST SURFACE FROM BASE.
    #
    # Restoring only ``is_collection_channel_path`` was not enough, and the gap was
    # a WORKING forced-pass attack (found 2026-08-05 by the adversarial pass on this
    # very fix, and the reason the set below is a union). The oracle is copied INTO
    # the app's test directory, so pytest's prepend import mode imports it as part of
    # that package — which executes ``backend/tests/__init__.py`` first. Seven lines
    # there (``import app.mod; app.mod.normalize_email = lambda e: e.lower()``) repair
    # a violating implementation before a single assertion runs. ``__init__.py`` under
    # ``tests/`` is test CODE, not a collection channel, so it was passed straight
    # through from HEAD — and the merge-base run went RED (the file does not exist at
    # base), so the forgery arrived wearing a perfect red→green.
    #
    # The general fact: every file in the test surface is in the oracle's import
    # path. Only production code may come from the diff.
    #
    # Expressed as the exact COMPLEMENT of ``is_production_path`` rather than as a
    # union of the two classifiers it is defined against
    # (``factory.diff_paths.is_production_path`` *is*
    # ``not is_test_code_path and not is_collection_channel_path``). Same set today,
    # but it stays correct for free: anything a future edit adds to either classifier
    # joins the rollback set automatically, instead of leaving a third place that
    # someone has to remember to widen. The ``__init__.py`` hole below is exactly
    # what forgetting costs.
    rollbacks = sorted({c for c in changed if not is_production_path(c)})
    details["rolled_back_to_base"] = rollbacks
    details["collection_channels_in_diff"] = [
        c for c in rollbacks if is_collection_channel_path(c)
    ]

    # (2) Run at HEAD in a THROWAWAY tree whose collection channels are rolled
    # back to the merge base, so the diff cannot decide its own verdict.
    with judge_worktree(repo_root, "HEAD", label="oracle-head") as (judge, err):
        if judge is None:
            return _unverifiable(
                pr, details, kind="no_judge_tree",
                why=(
                    f"could not build the independent judge tree ({err}); running in the dev's "
                    "own worktree would let the diff's conftest/pyproject force the verdict, "
                    "which is the hole this gate exists to close"
                ),
                waiver_sha=oracle_sha,
            )
        restored, removed, failed = restore_paths_from(judge, base_sha, rollbacks)
        details["channels_restored"] = restored
        details["channels_removed"] = removed
        if failed:
            return _unverifiable(
                pr, details, kind="channel_restore_failed",
                why=(
                    f"could not restore collection channel(s) {failed!r} from the merge base; "
                    "the diff would still control how the oracle is collected"
                ),
                waiver_sha=oracle_sha,
            )
        head_run = _run_oracle_in(judge, gates, stored, dest_name)

    details.update(
        {
            "command": head_run.command,
            "cwd": head_run.cwd,
            "test_file": head_run.test_file,
            "exit_code": head_run.exit_code,
            "output_tail": head_run.output,
        }
    )
    status, summary = classify_pytest_run(head_run.exit_code, head_run.output)
    details["head_status"] = status
    # A count read from CONFLICTING summaries is not a count — one of the lines is
    # not pytest's. Recording it would republish the forgery as the gate's own
    # finding (``tests_passed: 7`` with zero real passes).
    details["tests_passed"] = (
        summary.passed if summary is not None and status != "conflicting" else None
    )
    if summary is not None:
        details["head_summary"] = summary.as_dict()

    if status == "fail":
        return GateResult(
            label=_LABEL,
            passed=False,
            reason=f"ran independent acceptance oracle exit_code={head_run.exit_code}",
            details={**details, "authoritative": True, "verified": False},
        )
    if status == "vacuous":
        # A pytest run in which every test SKIPPED also exits 0 while verifying
        # nothing, and the persona is explicitly allowed to ``pytest.skip`` a
        # criterion that is untestable as written.
        return GateResult(
            label=_LABEL,
            passed=False,
            reason=(
                "acceptance oracle exited 0 but reported NO passing test "
                "(vacuous run — every criterion skipped, or nothing collected); "
                "blocking rather than crediting a verification that did not happen"
            ),
            details={**details, "authoritative": True, "verified": False},
        )
    if status == "conflicting":
        # Two DIFFERENT pytest summaries in one output; one of them is not
        # pytest's. A parser cannot decide which, so nothing here is gradeable.
        return _unverifiable(
            pr, details, kind="conflicting_summaries",
            why=(
                "the run printed more than one pytest summary — the pass count is forged or "
                "forgeable, so it cannot be evidence of anything"
            ),
            waiver_sha=None,  # never waivable: the evidence itself is suspect
        )
    if status == "unreadable":
        if "pytest" in head_run.command:
            return GateResult(
                label=_LABEL,
                passed=False,
                reason=(
                    "acceptance oracle exited 0 but produced no pytest result summary "
                    "(nothing ran, or the output was suppressed) — blocking rather than "
                    "crediting a verification that cannot be evidenced"
                ),
                details={**details, "authoritative": True, "verified": False},
            )
        return _unverifiable(
            pr, details, kind="unreadable_runner",
            why=(
                f"the configured runner produced no readable test summary "
                f"(exit_code={head_run.exit_code}); an exit code alone cannot show that the "
                "oracle ran, let alone that it was able to fail"
            ),
            waiver_sha=oracle_sha,
        )

    # (1) The oracle passed at HEAD. Can it fail AT ALL? Run the same oracle at
    # the merge base; only a RED base licenses crediting this green.
    verdict, base_reason, base_details = _base_run(
        pr, gates, stored, dest_name,
        repo_root=repo_root, base_sha=base_sha,
        cmd_template=cmd_template, oracle_sha=oracle_sha,
    )
    details["base_run"] = base_details
    if verdict == "green":
        return _unverifiable(
            pr, details, kind="oracle_not_discriminating",
            why=(
                f"{base_reason}. Its green at HEAD therefore says nothing about this story: "
                "a tautological oracle (``assert True``) and a criterion a sibling story "
                "already satisfied look identical from here. Re-author the oracle, tighten "
                "the direction's acceptance criteria, or record a decision with "
                "`factory acceptance-waive`"
            ),
            waiver_sha=oracle_sha,
        )
    route = f"red at merge base {base_sha[:12]}, green at HEAD"
    if verdict == "unknown":
        # The base run could not be trusted. Fall back to ABLATION, which needs no
        # usable base: gut the production symbols this story's diff touched and
        # require the oracle to go red. See ``_ablation_can_fail``.
        proven, abl_reason, abl_details = _ablation_can_fail(
            gates, stored, dest_name,
            repo_root=repo_root, head_ref=local_head,
            base_sha=base_sha, rollbacks=rollbacks,
        )
        details["failability_ablation"] = abl_details
        if not proven:
            return _unverifiable(
                pr, details, kind="failability_unverified",
                why=(
                    f"{base_reason}, and {abl_reason} — so a green at HEAD cannot be "
                    "distinguished from an oracle that cannot fail. Regression-only "
                    "fallback: NOT approving"
                ),
                waiver_sha=oracle_sha,
            )
        route = f"failability proven by ablation ({abl_reason}); the merge-base run was unusable"

    clear_gate_block(pr.software_factory_root, story.app, story.id)
    return GateResult(
        label=_LABEL,
        passed=True,
        reason=f"ran independent acceptance oracle exit_code={head_run.exit_code} ({route})",
        details={
            **details,
            "authoritative": True,
            "verified": True,
            "failability_route": "merge_base_red" if verdict == "red" else "ablation",
        },
    )


def _ablation_can_fail(
    gates: AppGatesConfig,
    stored: Path,
    dest_name: str,
    *,
    repo_root: Path,
    head_ref: str,
    base_sha: str,
    rollbacks: list[str],
) -> tuple[bool, str, dict[str, object]]:
    """SECOND route to failability: gut the story's own code, require the oracle to notice.

    Reached only when the merge-base run came back ``unknown`` — see the module
    docstring for why that is the only place it is allowed to speak.

    Delegates to ``factory.chain.mutation.check_can_fail`` (PR #239), which
    materializes its own scratch clone at ``head_ref``, demands a GREEN baseline,
    splices a raise into ``path::qualname``, and returns ``True`` only for a red it
    can attribute to that splice. Targets come from
    ``mutation.select_symbols`` — the PRODUCTION functions this story's diff
    actually touched, so a proof here says something about *this* story and not
    just about the oracle in the abstract.

    The ``prepare`` hook reproduces the primary path's structural defences inside
    that clone: the hidden oracle is copied in (it exists in no repo), the diff's
    whole test surface is rolled back to the merge base so a hostile ``conftest.py``
    or ``tests/__init__.py`` at HEAD cannot decide its own ablation verdict, and the
    clone is confirmed to BE the graded commit. Without those, the fallback would be
    weaker than the path it stands in for, and a dev who could steer the gate into
    ``unknown`` would have found a way in.

    Returns ``(proven, reason, details)``. Every non-proof is ``False``.
    """
    from factory.chain import mutation

    attempts: list[dict[str, object]] = []
    out: dict[str, object] = {"route": "ablation", "attempts": attempts}

    selection = mutation.select_symbols(
        repo_root, base_sha, head_ref, max_symbols=_MAX_ABLATION_TARGETS
    )
    if selection is None:
        why = f"the diff {base_sha[:12]}..{head_ref} could not be read, so there is nothing to ablate"
        out["reason"] = why
        return False, why, out
    symbols, candidates, notes = selection
    out["candidates"] = candidates
    if notes:
        out["notes"] = notes[:5]
    if not symbols:
        why = (
            "the story's diff touches no production function that could be ablated, so the "
            "oracle's failability cannot be established this way either"
        )
        out["reason"] = why
        return False, why, out

    command = _fmt_command(
        _command_template(gates), test_file=_oracle_test_file(gates, dest_name)
    )
    out["command"] = command

    def _prepare(tree: Path) -> str | None:
        # ``mutation._materialize_tree`` falls back to copying the WORKING TREE when
        # it cannot clone, and a copy carries the dev's UNTRACKED files (a stray
        # ``conftest.py``, a ``sitecustomize.py``) while carrying no ``.git`` — so
        # the channel rollback below silently has nothing to roll back. Refuse
        # anything that is not a real checkout at the commit we asked for. This is
        # D2's property (grade the merge candidate or grade nothing) applied to the
        # second tree; without it the fallback grades a tree nobody committed.
        actual = head_sha(tree)
        if actual != head_ref:
            return (
                f"the scratch tree is at {actual!r}, not the graded commit "
                f"{head_ref[:12]} — it is a working-tree copy or a wrong checkout, "
                "and its collection config is not the merge candidate's"
            )
        _restored, _removed, failed = restore_paths_from(tree, base_sha, rollbacks)
        if failed:
            return (
                f"could not restore collection channel(s) {failed!r} from the merge base — "
                "the diff would still control how the oracle is collected"
            )
        try:
            _place_oracle(tree, gates, stored, dest_name)
        except (_ConfigError, OSError) as exc:
            return f"the acceptance harness does not resolve in the scratch tree ({exc})"
        return None

    deadline = time.monotonic() + _ABLATION_BUDGET_S
    for sym in symbols:
        remaining = int(deadline - time.monotonic())
        if remaining < _ABLATION_MIN_RUN_S:
            out["budget_exhausted_after"] = len(attempts)
            break
        proven, detail = mutation.check_can_fail(
            repo_root=repo_root,
            head_ref=head_ref,
            target_path=sym.path,
            qualname=sym.qualname,
            check_command=command,
            timeout_s=min(_ABLATION_TIMEOUT_S, remaining),
            prepare=_prepare,
            run_cwd=gates.acceptance_test_cwd,
        )
        attempts.append({"symbol": sym.key, "proven": proven, "detail": detail[:300]})
        if proven:
            out["proven_by"] = sym.key
            out["reason"] = detail
            return True, detail, out

    why = (
        f"ablating {len(attempts)} of this story's own production symbol(s) "
        f"({', '.join(str(a['symbol']) for a in attempts)}) never made the oracle go red"
        if attempts
        else f"the ablation fallback ran out of its {_ABLATION_BUDGET_S}s budget "
             "before it could measure anything"
    )
    out["reason"] = why
    return False, why, out


def _base_run(
    pr: PRContext,
    gates: AppGatesConfig,
    stored: Path,
    dest_name: str,
    *,
    repo_root: Path,
    base_sha: str,
    cmd_template: str,
    oracle_sha: str,
) -> tuple[str, str, dict[str, object]]:
    """Run the oracle at the merge base; ``(verdict, reason, details)``.

    CACHED on ``(base sha, oracle content, command, dir, cwd)`` — everything the
    result depends on. The base tree for a given sha is immutable and the oracle is
    frozen, so re-running it on every tick of every open PR buys nothing. Only
    DEFINITIVE verdicts (``red``/``green``) are cached: caching an ``unknown``
    would freeze a transient infra fault into a block that fixing the environment
    could never clear.
    """
    root = pr.software_factory_root
    story = pr.story
    cache_path = (
        acceptance_dir(Path(root), story.app, story.id) / "base_runs.json"
        if root is not None and story is not None
        else None
    )
    key = run_key(
        base_sha, oracle_sha, cmd_template,
        gates.acceptance_test_dir or "", gates.acceptance_test_cwd or "",
    )
    if cache_path is not None:
        hit = cache_get(cache_path, key)
        if hit is not None and hit.get("verdict") in {"red", "green"}:
            return (
                str(hit["verdict"]),
                f"{hit.get('reason', '')} [cached]",
                {**hit, "cached": True},
            )

    with judge_worktree(repo_root, base_sha, label="oracle-base") as (base_tree, err):
        if base_tree is None:
            return "unknown", f"could not check out the merge base ({err})", {
                "verdict": "unknown", "reason": err[:300], "base_sha": base_sha[:12],
            }
        try:
            run = _run_oracle_in(base_tree, gates, stored, dest_name)
        except _ConfigError as exc:
            # e.g. ``acceptance_test_dir`` is a directory this story CREATES, so it
            # does not exist at the base. Unknown, not red: "the harness could not
            # run" is not "the test failed".
            return "unknown", f"the acceptance config does not resolve at the base ({exc})", {
                "verdict": "unknown", "reason": str(exc)[:300], "base_sha": base_sha[:12],
            }
        except OSError as exc:
            return "unknown", f"the base run could not start ({exc})", {
                "verdict": "unknown", "reason": repr(exc)[:300], "base_sha": base_sha[:12],
            }

    verdict, reason, summary = base_verdict(run.exit_code, run.output)
    out: dict[str, object] = {
        "verdict": verdict,
        "reason": reason,
        "base_sha": base_sha[:12],
        "exit_code": run.exit_code,
        "summary": summary.as_dict() if summary is not None else None,
        "output_tail": run.output[-1500:],
    }
    if cache_path is not None and verdict in {"red", "green"}:
        cache_put(cache_path, key, {k: v for k, v in out.items() if k != "output_tail"})
    return verdict, reason, out
