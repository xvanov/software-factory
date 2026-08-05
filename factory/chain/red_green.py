"""Harness-owned red→green verification (PLAN A.6) — one implementation.

Why this module exists
======================

A test the harness never ran at the BASE commit cannot tell you whether it is
able to fail. "Red-first" is *instructed* in ``factory/personas/dev.md`` and in
``factory/personas/acceptance_author.md``, and the chain then trusts the claim:
``PRContext.commit_history`` carries the dev's own ``tests_run_red`` report, and
nothing anywhere re-derives it. A gate whose green is produced by a test that
cannot fail is a gate detached from a real check, which
``factory/chain/gates/evaluator.py:18-29`` says is worse than no gate at all.

So the harness runs the test ITSELF at the merge base and observes the result.
Two consumers need exactly this, which is why it lives here and not inside one
of them:

* the ``acceptance-verified`` gate — the oracle must be RED at the merge base
  before its green at HEAD is credited (A.1c);
* a future gate over the DEV's new tests (A.6 proper) — same question, same
  states, same fallback.

⚠ THE CAVEAT — read this before tightening anything below
=========================================================

**Only the fails-at-base half of red→green is oracle-free.** Agentless measured
213/300 generated tests reproducing a bug but only 94/300 of those ALSO flipping
green under the gold patch, so a hard both-halves gate rejects good patches.
Two consequences are encoded in this module and must stay encoded:

1. "Fails at base" means **at least one test FAILED** at base
   (:func:`base_verdict`), never "the whole file was red". A story that
   implements one of its direction's several acceptance criteria produces an
   oracle whose other tests legitimately pass at base.

   An ERROR-only red is not "fails at base" — it is ``unknown``. An oracle that
   cannot be collected at the merge base (``from app.mod import thing`` for a
   module the story adds) is red no matter what it asserts, so a tautology rides
   that route to a credited green. See :func:`base_verdict` for the measurement.
   Errors and failures are different facts here, and only the second one is
   evidence.
2. When the base run cannot be TRUSTED — infra error, timeout, unreadable
   output, nothing collected, no merge base — the verdict is ``unknown``, and an
   ``unknown`` falls back to **regression-only selection: it must never be read
   as "approve"**. Callers get three states, ``red`` / ``green`` / ``unknown``,
   and only ``red`` licenses crediting a green at HEAD. ``unknown`` is a
   *skipped-with-reason*: not a pass, and not evidence against the dev either.

Tampering
=========

:func:`parse_pytest_summary` reads the LAST summary line in the output and flags
CONFLICTING summaries, because a dev-controlled ``conftest.py`` can print
``"7 passed in 0.01s"`` before pytest's own summary and a first-match parse
credits the forgery. Parsing alone cannot close that hole (a conftest can
implement ``pytest_report_teststatus`` and relabel skip→pass); the structural fix
is running in a throwaway :func:`judge_worktree` whose collection channels come
from the merge base, not from the dev's HEAD. Both layers are used together.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_log = logging.getLogger(__name__)

_GIT_TIMEOUT = 60
# pytest's own exit code for "killed by our timeout" never exists; ``_run_command``
# in the gate evaluator synthesises 124, and a timed-out run's output tail is a
# fragment we must never classify as a real red.
TIMEOUT_EXIT_CODE = 124


# --------------------------------------------------------------------------- #
# pytest summary parsing
# --------------------------------------------------------------------------- #

# One ``<n> <outcome>`` token from a pytest summary line. ``warnings`` is
# deliberately NOT a member: it is not a test outcome, and including it would
# make "1 passed, 2 warnings" and "1 passed" read as CONFLICTING summaries.
_TOKEN_RE = re.compile(
    r"(?<![\w.])(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed|deselected)\b"
)
_NO_TESTS_RE = re.compile(r"no tests ran", re.IGNORECASE)


@dataclass(frozen=True)
class PytestSummary:
    """The counts from a pytest summary line, plus whether we can trust them."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0
    deselected: int = 0
    no_tests_ran: bool = False
    # More than one DISTINCT summary appeared in the output. pytest prints one;
    # a second one means something else printed a summary-shaped line, i.e. the
    # count we would read is forgeable. Callers must refuse to grade on it.
    conflicting: bool = False
    line: str = ""

    @property
    def ran_something(self) -> bool:
        """Did any test actually reach a per-test outcome?"""
        return bool(
            self.passed or self.failed or self.errors
            or self.skipped or self.xfailed or self.xpassed
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "xfailed": self.xfailed,
            "xpassed": self.xpassed,
            "deselected": self.deselected,
            "no_tests_ran": self.no_tests_ran,
            "conflicting": self.conflicting,
            "line": self.line[:200],
        }


def _counts_from_line(line: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n, word in _TOKEN_RE.findall(line):
        key = "errors" if word.startswith("error") else word
        counts[key] = counts.get(key, 0) + int(n)
    return counts


def parse_pytest_summary(output: str) -> PytestSummary | None:
    """The counts pytest reported, or ``None`` when the output carries none.

    Takes the **LAST** summary-shaped line, not the first: pytest prints its
    summary last, so a line printed earlier by a dev-controlled ``conftest.py``
    (``print("7 passed in 0.01s")`` from ``pytest_configure``) is a forgery. When
    two DIFFERENT summaries appear, ``conflicting`` is set and the caller must
    refuse to grade on the numbers at all — we cannot tell which one pytest
    wrote, and one of them is a lie.
    """
    if not output:
        return None
    seen: list[tuple[str, dict[str, int]]] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        counts = _counts_from_line(line)
        if counts:
            seen.append((line, counts))
        elif _NO_TESTS_RE.search(line):
            seen.append((line, {}))
    if not seen:
        return None

    line, counts = seen[-1]
    distinct = {json.dumps(c, sort_keys=True) for _l, c in seen}
    return PytestSummary(
        passed=counts.get("passed", 0),
        failed=counts.get("failed", 0),
        errors=counts.get("errors", 0),
        skipped=counts.get("skipped", 0),
        xfailed=counts.get("xfailed", 0),
        xpassed=counts.get("xpassed", 0),
        deselected=counts.get("deselected", 0),
        no_tests_ran=not counts and bool(_NO_TESTS_RE.search(line)),
        conflicting=len(distinct) > 1,
        line=line,
    )


RunStatus = Literal["pass", "fail", "vacuous", "unreadable", "conflicting"]


def classify_pytest_run(exit_code: int, output: str) -> tuple[RunStatus, PytestSummary | None]:
    """Grade one pytest run from its exit code and output.

    * ``pass`` — exit 0 and at least one test passed and nothing failed;
    * ``fail`` — a test failed or errored (or pytest disagreed with the counts);
    * ``vacuous`` — nothing reached an outcome, or only skips/xfails did. Exit 0
      here is NOT evidence of anything (the acceptance author is allowed to
      ``pytest.skip`` a criterion it cannot express);
    * ``unreadable`` — no summary at all: a timeout, a missing runner, a summary
      evicted from the captured tail, or output we simply cannot grade;
    * ``conflicting`` — two different summaries; the numbers are forgeable.
    """
    if exit_code == TIMEOUT_EXIT_CODE:
        # A killed run's tail can contain a partial summary; grading it would let
        # a timeout masquerade as a real red.
        return "unreadable", parse_pytest_summary(output)
    summary = parse_pytest_summary(output)
    if summary is None:
        return "unreadable", None
    if summary.conflicting:
        return "conflicting", summary
    if not summary.ran_something:
        return "vacuous", summary
    if summary.failed or summary.errors:
        return "fail", summary
    if exit_code != 0:
        # pytest exited non-zero while reporting no failure. Trust the exit code.
        return "fail", summary
    if summary.passed >= 1:
        return "pass", summary
    return "vacuous", summary


BaseVerdict = Literal["red", "green", "unknown"]


def base_verdict(exit_code: int, output: str) -> tuple[BaseVerdict, str, PytestSummary | None]:
    """Grade the BASE run: was the test able to fail without the story's diff?

    * ``red`` — at least one test **FAILED** at the merge base: an assertion in
      the oracle ran and disagreed with the base implementation. This is the only
      verdict that licenses crediting a green at HEAD. Deliberately "at least
      one", not "all": see the caveat at the top of this module — requiring every
      test to be red rejects good work.
    * ``green`` — every test already passed at the merge base, so the test does
      not discriminate this story's diff and its green at HEAD carries no
      information about it.
    * ``unknown`` — the base run cannot be trusted (nothing collected, timeout,
      unreadable output, conflicting summaries, or a red made ENTIRELY of
      errors). Regression-only fallback: never "approve".

    ⚠ WHY AN ERRORS-ONLY RED IS ``unknown`` AND NOT ``red`` (2026-08-05)
    -------------------------------------------------------------------
    This function used to count ``errors`` as red alongside ``failed``, and that
    was a MEASURED forced pass. For a story that ADDS a module, an oracle whose
    only relationship to the criterion is ``from app.mod import thing`` raises
    ``ModuleNotFoundError`` at the merge base — a COLLECTION error — whatever it
    goes on to assert. So::

        from app.mod import normalize_email

        def test_ac1():
            assert True

    was red at base, green at HEAD, and credited ``verified=True,
    authoritative=True`` against an implementation that violated the criterion.
    The whole D1 family (``assert True``, a self-referential assertion, an
    assertion inside ``try/except``) rides that route, and it is the COMMON story
    shape rather than an exotic one: any story creating a new module reaches it
    whenever the app's test directory already exists at base, which it does for
    every app past its first commit.

    An error says the oracle could not RUN. Only a failure says its assertions
    ran and discriminated. Those are different facts and no parse of the base run
    alone can turn the first into the second — the file that failed to import is
    exactly the file whose assertions we are trying to evaluate.

    So an errors-only red is ``unknown``, which is not a block: it falls through
    to the ABLATION route, and ablation answers precisely the question the base
    run could not. The good case still merges — the real oracle for a new module
    goes red when its symbol is gutted — and the tautology does not, because
    gutting the code changes nothing ``assert True`` can see. The cost is that
    new-module stories take the (more expensive) ablation route rather than the
    cheap cached one; that is the price of the green meaning something.

    A mixed run (``1 failed, 1 error``) IS red: an assertion did run and did
    discriminate, and the caveat above forbids demanding that all of them do.
    """
    status, summary = classify_pytest_run(exit_code, output)
    if status == "fail":
        if summary is not None and summary.failed >= 1:
            n = summary.failed
            return (
                "red",
                f"{n} test(s) FAILED at the merge base (RED as required)",
                summary,
            )
        # Errors only, or pytest exited non-zero while reporting no outcome at
        # all. Nothing here shows the oracle's assertions ran, so it is not proof
        # of failability. ``unknown`` → the ablation fallback, never a credit.
        n_err = summary.errors if summary is not None else 0
        return (
            "unknown",
            (
                f"the base run is red but ENTIRELY from {n_err} error(s) and no test "
                "failure (exit_code="
                f"{exit_code}) — an oracle that cannot even be COLLECTED at the base "
                "(a story that adds the module it imports) is red whatever it asserts, "
                "so this is not evidence that its assertions discriminate anything"
            ),
            summary,
        )
    if status == "pass":
        n = summary.passed if summary else 0
        return (
            "green",
            f"all {n} test(s) ALREADY PASS at the merge base — the test does not "
            "discriminate this story's diff",
            summary,
        )
    reasons = {
        "vacuous": "the base run reached no test outcome (nothing collected, or all skipped)",
        "unreadable": f"the base run produced no readable pytest summary (exit_code={exit_code})",
        "conflicting": "the base run printed conflicting pytest summaries",
    }
    return "unknown", reasons[status], summary


# --------------------------------------------------------------------------- #
# git plumbing
# --------------------------------------------------------------------------- #


def _git(repo: Path, *args: str, timeout: int = _GIT_TIMEOUT) -> tuple[int, str, str]:
    """Run git in ``repo``; ``(returncode, stdout, stderr)``. Never raises."""
    try:
        proc = subprocess.run(  # noqa: S603,S607 - fixed argv, no shell
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 128, "", f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def head_sha(repo: Path) -> str | None:
    code, out, _err = _git(repo, "rev-parse", "HEAD")
    return out.strip() or None if code == 0 else None


def head_contains_sha(repo: Path, sha: str | None) -> tuple[bool | None, str]:
    """Is ``sha`` an ancestor of (or equal to) ``repo``'s HEAD?

    ``(True, why)`` / ``(False, why)`` / ``(None, why)`` where ``None`` means the
    question could not be answered (not a git checkout, unknown object, git
    unavailable). PROVENANCE, and it is not the same question as SHA equality:
    ``auto_merge._story_worktree`` merges ``origin/main`` into the feature branch
    before gates run, so the checkout's HEAD is normally a merge commit whose
    ancestor is the PR head. Equality would false-block every such PR;
    ancestry is the real property ("the tree I am about to grade contains the
    commit that will be merged").
    """
    if not sha or not _SHA_RE.match(sha.strip()):
        return None, f"head_sha={sha!r} is not a commit id"
    sha = sha.strip()
    code, _out, _err = _git(repo, "rev-parse", "--git-dir")
    if code != 0:
        return None, "the checkout is not a git repository"
    code, _out, _err = _git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
    if code != 0:
        return None, f"commit {sha[:12]} is unknown to the checkout (fetch failed?)"
    code, _out, err = _git(repo, "merge-base", "--is-ancestor", sha, "HEAD")
    if code == 0:
        return True, f"{sha[:12]} is an ancestor of HEAD"
    if code == 1:
        local = head_sha(repo) or "?"
        return False, f"{sha[:12]} is NOT an ancestor of the checkout HEAD {local[:12]}"
    return None, f"git merge-base --is-ancestor failed: {err.strip()[:200]}"


def _base_refs(base_branch: str | None) -> list[str]:
    """The refs that stand for "the base branch", most authoritative first.

    ``origin/<base>`` is what the merge is actually computed against; the local
    branch of the same name can be arbitrarily stale in a worktree, and a bare
    test repo has no remote at all.
    """
    branch = (base_branch or "main").strip() or "main"
    return [f"origin/{branch}", branch, f"refs/remotes/origin/{branch}"]


def extra_commits_beyond(
    repo: Path, head_sha: str, base_branch: str | None
) -> tuple[list[str] | None, str]:
    """Non-merge commits HEAD adds over ``head_sha`` that did NOT come from the base.

    ``([], why)`` is the clean answer, a non-empty list names the offending commits,
    and ``None`` means the question could not be answered — which a caller on the
    merge path must treat as *cannot verify*, never as clean.

    WHY THIS IS NOT REDUNDANT WITH :func:`head_contains_sha`. Ancestry says the
    checkout contains the PR head; it does not say the checkout is ONLY the PR head
    plus the base. ``auto_merge._story_worktree`` legitimately produces
    ``merge(origin/<feature>, origin/<base>)`` — hence ancestry rather than SHA
    equality — but a worktree whose feature branch is AHEAD of ``origin/<feature>``
    (a commit the chain made and failed to push) also passes ancestry, and grading
    it returns an authoritative verdict about code that is not being merged. That is
    D2's own bug class, one level in.

    ``--no-merges`` is the deliberate limit: a merge commit can carry conflict
    resolutions, so a hostile resolving merge would not be listed here. The chain
    never makes one — it aborts a conflicting merge and evaluates as-is
    (``auto_merge._story_worktree``) — so the residual needs an actor who can commit
    into the worktree directly, which is a strictly larger breach than this gate.
    """
    if not head_sha or not _SHA_RE.match(head_sha.strip()):
        return None, f"head_sha={head_sha!r} is not a commit id"
    head_sha = head_sha.strip()
    for ref in _base_refs(base_branch):
        code, out, _err = _git(
            repo, "rev-list", "--no-merges", f"{head_sha}..HEAD", "--not", ref
        )
        if code == 0:
            extra = [line.strip() for line in out.splitlines() if line.strip()]
            return extra, f"rev-list --no-merges {head_sha[:12]}..HEAD --not {ref}"
    return None, f"no base ref resolved among {_base_refs(base_branch)!r}"


def resolve_base_sha(repo: Path, base_branch: str | None) -> tuple[str | None, str]:
    """``merge-base(<base ref>, HEAD)`` — the commit the story's work sits on.

    Tries ``origin/<base>`` first: that is the ref the merge itself is computed
    against, and the local branch of the same name can be arbitrarily stale in a
    worktree. Returns ``(sha, how)`` or ``(None, why-not)``.
    """
    tried: list[str] = []
    for ref in _base_refs(base_branch):
        code, out, _err = _git(repo, "merge-base", ref, "HEAD")
        tried.append(ref)
        if code == 0 and out.strip():
            return out.strip().splitlines()[0], f"merge-base({ref}, HEAD)"
    return None, f"no merge base against any of {tried!r}"


def changed_paths_since(repo: Path, base_sha: str) -> list[str] | None:
    """Repo-relative paths that differ between ``base_sha`` and HEAD (None on error)."""
    code, out, _err = _git(repo, "diff", "--name-only", "-z", f"{base_sha}..HEAD")
    if code != 0:
        return None
    return [p for p in out.split("\0") if p]


@contextmanager
def judge_worktree(repo: Path, committish: str, *, label: str = "judge") -> Iterator[tuple[Path | None, str]]:
    """A THROWAWAY detached checkout of ``committish``, outside the dev worktree.

    The point is that the tree we grade in is not the tree the dev works in:

    * nothing the dev leaves UNTRACKED (a stray ``conftest.py``, a ``.pth``, a
      ``sitecustomize.py``) exists here, because a fresh checkout has only
      tracked content;
    * the hidden acceptance oracle is copied in HERE, so it is never on disk
      inside the dev's worktree at all — no leak window, nothing for the chain's
      ``git add -A`` to stage;
    * uncommitted work is excluded by construction, so we grade the commit that
      will actually be merged rather than whatever the worktree happens to hold.

    Yields ``(path, "")`` on success and ``(None, why)`` on failure — callers
    must treat the failure as *cannot verify*, never as a pass. Cleaned up on
    exit, including the git registration (``worktree remove`` + ``prune``).
    """
    tmp: Path | None = None
    tree: Path | None = None
    try:
        try:
            tmp = Path(tempfile.mkdtemp(prefix=f"factory-{label}-"))
        except OSError as exc:
            yield None, f"could not create a temp dir: {exc}"
            return
        tree = tmp / "tree"
        code, _out, err = _git(
            repo, "worktree", "add", "--detach", str(tree), committish, timeout=300
        )
        if code != 0:
            yield None, f"git worktree add {committish} failed: {err.strip()[:300]}"
            return
        yield tree, ""
    finally:
        if tree is not None:
            _git(repo, "worktree", "remove", "--force", str(tree), timeout=120)
        if tmp is not None and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        _git(repo, "worktree", "prune", timeout=60)


def restore_paths_from(
    tree: Path, sha: str, paths: Sequence[str]
) -> tuple[list[str], list[str], list[str]]:
    """Make ``paths`` inside ``tree`` identical to their state at ``sha``.

    Returns ``(restored, removed, failed)``. A path that does not exist at
    ``sha`` was ADDED by the diff and is deleted from ``tree``. ``failed`` must
    be treated as *cannot verify* by the caller: a channel we failed to restore
    is still under the diff's control.

    Symlinks are tested with :meth:`Path.is_symlink` BEFORE ``is_file`` /
    ``exists``, both of which follow the link. A BROKEN symlink — say the diff
    adds ``backend/tests/conftest.py -> ./generated.py`` and never generates it —
    answers False to both, so the old code reported it in ``removed`` while
    leaving it on disk: a path this function claims to have neutralised, still
    under the diff's control. (It could not forge a green, because pytest cannot
    read it either and the run goes red — but ``removed`` has to be true or the
    caller's "the diff no longer decides this" is not a fact.)
    """
    restored: list[str] = []
    removed: list[str] = []
    failed: list[str] = []
    for rel in paths:
        code, _out, _err = _git(tree, "cat-file", "-e", f"{sha}:{rel}")
        if code == 0:
            c, _o, _e = _git(tree, "checkout", sha, "--", rel)
            (restored if c == 0 else failed).append(rel)
            continue
        target = tree / rel
        try:
            if target.is_symlink() or target.is_file():
                target.unlink()
                removed.append(rel)
            elif not target.exists():
                removed.append(rel)
            else:
                # A directory where the diff put one. Never removed blindly.
                failed.append(rel)
        except OSError:
            failed.append(rel)
    return restored, removed, failed


# --------------------------------------------------------------------------- #
# a tiny keyed cache (a base run is pure in (base sha, test source, command))
# --------------------------------------------------------------------------- #


def run_key(*parts: str) -> str:
    """A stable cache key over everything a run's result depends on."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()


def cache_get(path: Path, key: str) -> dict[str, object] | None:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a missing/corrupt cache is simply a miss
        return None
    entry = raw.get(key) if isinstance(raw, dict) else None
    return entry if isinstance(entry, dict) else None


def cache_put(path: Path, key: str, value: dict[str, object], *, keep: int = 10) -> None:
    """Best-effort write of one cache entry, keeping the ``keep`` newest."""
    try:
        p = Path(path)
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
        except Exception:  # noqa: BLE001
            raw = {}
        raw[key] = {**value, "recorded_at": time.time()}
        if len(raw) > keep:
            ordered = sorted(
                raw.items(),
                key=lambda kv: float(kv[1].get("recorded_at", 0) or 0)
                if isinstance(kv[1], dict)
                else 0.0,
                reverse=True,
            )
            raw = dict(ordered[:keep])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        _log.debug("red_green cache write failed for %s", path)


__all__ = [
    "TIMEOUT_EXIT_CODE",
    "BaseVerdict",
    "PytestSummary",
    "RunStatus",
    "base_verdict",
    "cache_get",
    "cache_put",
    "changed_paths_since",
    "classify_pytest_run",
    "extra_commits_beyond",
    "head_contains_sha",
    "head_sha",
    "judge_worktree",
    "parse_pytest_summary",
    "resolve_base_sha",
    "restore_paths_from",
    "run_key",
]
