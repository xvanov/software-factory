"""Gate: ``production-tree-changed``.

The story's diff must change at least one PRODUCTION file. FAIL-CLOSED: a diff
this gate cannot see is a diff it refuses to bless.

Why this gate exists (measured, 2026-08-04)
-------------------------------------------
The chain was graded against a hidden oracle for the first time: 7/19 resolved,
and its own green verdict was 40% precise (6 of 15 "green" rows actually
passed). Every check the chain runs measures agreement with artifacts the chain
itself produced — the dev writes the code AND the tests, the reviewer's approve
rule reads a ``test_quality_score``, the merge gate re-runs the dev's own
tests. One row, ``harumiweb__exstruct-113``, spent $2.45, edited ONLY
``tests/cli/test_cli_lazy_imports.py``, was approved by the reviewer at
``test_quality_score=0.90``, reached ``reviewer_done``, and recorded
``files_changed: []`` / ``diff_bytes: 0``. Nothing in the chain noticed that
the production tree was untouched, because nothing was looking.

That is the cheapest possible false-green to close: "did the arm change
anything other than the thing that judges it" needs no model call, no
execution, and no judgement.

What counts as production code
------------------------------
``factory.diff_paths`` — the SAME classifier ``bench/swebench_adapter.py`` uses
to strip test edits out of a graded prediction and to refuse a prediction that
edits a pytest collection channel. Production = not test code, and not a
collection/auto-import channel (``pyproject.toml``, ``pytest.ini``, ``tox.ini``,
``setup.cfg``, ``noxfile.py``, ``sitecustomize.py``, ``*.pth``,
``*pytest*plugin*.py``, ``conftest.py``). A story whose only non-test change is
pytest configuration is not a fix: measured against real pytest, ``addopts =
"-p _fixup"`` plus a collection hook makes the whole suite exit 0 with
"skipped".

Docs, non-collection config and source all count as production. This gate asks
"was anything but the oracle touched", not "is this change interesting" — so a
docs-only TDD story still passes, and only a genuinely vacuous or
test-only/config-only diff blocks.

Resolution order (every branch derives from a REAL artifact)
------------------------------------------------------------
1. ``pr.files_changed`` — GitHub's own file list for the PR, when the worker
   built the fixture from GH.
2. ``pr.repo_root`` — ``git diff --name-only <base_ref>...HEAD`` in the story
   worktree, with the same ``origin/<base>`` → local ``<base>`` fallback
   (``handlers._resolve_diff_base``) the reviewer's diff and the docs-enforcer
   use, so all three agree about what the branch changed. COMMITTED work only:
   uncommitted edits are not what merges.
3. Neither available → BLOCK. There is deliberately no "assume it is fine"
   branch and no recorded-flag branch: ``evaluator.py`` (see the ALL_GATE_LABELS
   comment) records the precedent that a gate detached from a real check is
   worse than no gate, because it manufactures a verdict.

This gate is in ``LOOP4_REQUIRED_GATE_LABELS``, i.e. merge-REQUIRED. That is
load-bearing: ``auto_merge`` computes ``missing_labels`` only over
``required_gate_labels(...)``, so a non-required gate's failure is filtered out
of the merge decision and the PR merges anyway.
"""

from __future__ import annotations

from pathlib import Path

from factory.app_config import AppConfig
from factory.chain.gates.evaluator import GateResult, PRContext
from factory.diff_paths import (
    is_collection_channel_path,
    is_test_path,
    production_paths,
)

_LABEL = "production-tree-changed"


def _git_changed_paths(repo_root: Path, base_branch: str) -> tuple[list[str] | None, str]:
    """``(paths, note)`` from ``git diff --name-only <base_ref>...HEAD``.

    ``None`` means "could not derive" — a missing base ref, a git failure, a
    timeout. The caller fails closed on it; it never degrades to ``[]``, which
    would read as "the branch genuinely changed nothing".
    """
    import subprocess

    # Reuse the chain's own base-ref resolver rather than re-deriving the
    # fallback chain here: a gate that disagrees with the reviewer about the
    # diff base would block PRs the reviewer approved on a different diff.
    # Imported lazily — handlers is a heavy module and gates are imported by
    # the CLI.
    try:
        from factory.chain.handlers import _resolve_diff_base
    except Exception as exc:  # noqa: BLE001 — fail closed, never wave through
        return None, f"could not import the diff-base resolver: {exc!r}"

    base_ref = _resolve_diff_base(repo_root, base_branch)
    if base_ref is None:
        return None, (
            f"no diff base ref: neither 'origin/{base_branch}' nor "
            f"'{base_branch}' resolves in {repo_root}"
        )
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            errors="replace",  # paths are arbitrary bytes; never strict-decode-crash
            check=False,
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001 — any git/OS failure fails CLOSED
        return None, f"git diff --name-only failed: {exc!r}"
    if proc.returncode != 0:
        return None, (
            f"git diff --name-only {base_ref}...HEAD exited "
            f"rc={proc.returncode}; stderr_tail={proc.stderr.strip()[-200:]!r}"
        )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()], (
        f"git diff --name-only {base_ref}...HEAD"
    )


def evaluate(pr: PRContext, app_config: AppConfig) -> GateResult:
    label = _LABEL

    if pr.files_changed:
        paths: list[str] | None = list(pr.files_changed)
        source = "pr.files_changed (GitHub)"
    elif pr.repo_root is not None:
        paths, source = _git_changed_paths(pr.repo_root, pr.base_branch or "main")
    else:
        paths, source = None, "no files_changed and no repo_root"

    if paths is None:
        return GateResult(
            label=label,
            passed=False,
            reason=f"cannot determine the changed files, so cannot prove production code changed: {source}",
            details={"source": source, "authoritative": False},
        )

    production = production_paths(paths)
    if production:
        return GateResult(
            label=label,
            passed=True,
            reason=f"{len(production)} production file(s) changed",
            details={
                "source": source,
                "production_paths": production[:20],
                "changed_count": len(paths),
                "authoritative": True,
            },
        )

    # Zero production files. Say WHICH kind of vacuous this is — a 0-file diff
    # and a test-only diff need different operator responses.
    test_only = [p for p in paths if is_test_path(p)]
    config_only = [
        p for p in paths if not is_test_path(p) and is_collection_channel_path(p)
    ]
    if not paths:
        detail = "the diff is EMPTY — nothing was committed on this branch"
    else:
        detail = (
            f"the diff touches only test files ({len(test_only)}) and pytest "
            f"collection config ({len(config_only)})"
        )
    return GateResult(
        label=label,
        passed=False,
        reason=f"no production-code change: {detail}",
        details={
            "source": source,
            "changed_paths": paths[:20],
            "test_paths": test_only[:20],
            "collection_config_paths": config_only[:20],
            "authoritative": True,
        },
    )
