"""SWE-bench Pro adapter — an externally-graded number for the factory.

PLAN.md Phase 1. The existing ``bench/bench.py`` grades the factory against
sacrifice's own backlog using sacrifice's own gates: the factory writes the
code AND owns the tests that say the code works. That measures convergence,
not correctness. This adapter swaps in a HIDDEN oracle the factory never sees.

Design
------
* ``fetch`` pins a manifest (instance -> repo/base_commit/statement hash) with
  a published RNG seed, BEFORE any run. A benchmark chosen after seeing results
  is not a benchmark.
* ``run`` clones the repo at ``base_commit`` into an isolated bench root
  (own state db, own ``FACTORY_STATE_ROOT``) and drives the chain's dev+review
  handlers over the problem statement — the same restricted surface
  ``bench.py`` uses.
* ``grade`` strips every test-file edit from the produced diff, applies it to
  the instance's official image, and runs the hidden ``fail_to_pass`` /
  ``pass_to_pass`` sets.

Three deliberate constraints, each with a reason
------------------------------------------------
1. **Isolated state root.** A prior session lost a week to bench runs writing
   synthetic failures into production telemetry, which the FMS then escalated
   as real. Nothing here may touch ``state/`` at the factory root.
2. **``--depth 1`` clone, no history.** Cursor found SWE-bench Pro scores
   collapse when agents lose git history, because some were retrieving the
   gold patch from later commits. Denying history is the control.
3. **Test edits are stripped and the strip is ASSERTED.** The factory's dev
   owns its tests (the Loop-4 design), so an unstripped diff would let it edit
   the oracle — the single most common way SWE-bench numbers get inflated.

Known noise floor: OpenAI's 2026-07-08 audit found ~30% of SWE-bench Pro's
public tasks broken and retracted its recommendation. Expect a substantial
unsolvable floor; ``grade`` records ``task_broken_*`` separately from
``wrong_patch`` so the two are never summed into one "failure" number. Run
``selftest`` FIRST and grade only the instances whose gold patch resolves.

The factory arm needs a WORKING test environment
-----------------------------------------------
A bare clone has no dependencies, so ``pytest`` dies with
``ModuleNotFoundError`` and dev — whose whole mechanism is run-until-green —
blocks with an empty diff. The app's ``test_command`` therefore runs inside the
instance's own image with the working tree mounted over ``/app``
(``instance_test_command``). Measured on ``ansible__ansible-9a21e2477...``:
empty diff after 870k tokens before, ``reviewer_done`` with a real patch in
104s / 355k tokens after.

Usage (from the factory root):
  uv run python bench/swebench_adapter.py fetch --language python --limit 10 --seed 20260801
  uv run python bench/swebench_adapter.py selftest            # validate the ORACLE first
  uv run python bench/swebench_adapter.py run   --instance <id> --arm bare|factory
  uv run python bench/swebench_adapter.py grade --instance <id> --arm bare|factory
  uv run python bench/swebench_adapter.py audit --instance <id> --arm bare|factory
  uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 \
      --only-working --dry-run          # ALWAYS preview: a sweep costs real money
  uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 --only-working
  uv run python bench/swebench_adapter.py report

``run-all`` is the same run+grade+audit pipeline fanned out over a pool of
child PROCESSES (never threads — ``run_factory`` mutates process-global state;
see the comment above ``_SWEEP_LOCK``). Four properties matter more than the
speedup:

* It refuses to start when the projected spend would breach
  ``caps.hourly_spend_usd`` / ``caps.daily_spend_usd``. Bench runs write to an
  isolated state root, so the chain's own spend enforcer never sees them and
  will never throttle them — this guard is the only one there is. Because a
  projection can be wrong, ACTUAL accumulated spend is re-checked after every
  completed instance: on breach no new children start (in-flight ones finish,
  so the residual overshoot is bounded by workers x the true per-instance
  cost), the summary records ``stopped_reason: "spend cap: …"``, and the
  sweep exits non-zero. ``--force-over-cap`` bypasses both the projection
  refusal and the mid-sweep stop; the $50/$75/$100 operator notices key off
  actual accumulated spend and are emitted regardless.
* ``--dry-run`` is a PURE preview: it prints the plan and the projected spend,
  spawns nothing and writes nothing.
* ``Ctrl-C`` kills the whole process group of every in-flight child. Without
  that, interrupting a sweep leaves N detached dev runs still calling the
  model.
* Every instance is ``audit``-ed after run+grade. A failed audit marks the
  row invalid (``audit_ok: false``) and the summary separates audited-valid
  results from invalid ones; a sweep where EVERY row fails audit exits
  non-zero. An unauditable run is an invalid run.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FACTORY_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = FACTORY_ROOT / "bench"
SWE_DIR = BENCH_DIR / "swebench"
RUNS_DIR = SWE_DIR / "runs"
MANIFEST_PATH = SWE_DIR / "manifest.json"

DATASET = "ScaleAI/SWE-bench_Pro"
_ROWS_URL = "https://datasets-server.huggingface.co/rows"

# Fake issue numbers far from production so a bench story can never collide
# with a real worktree branch (which is named from the real issue number).
SWE_ISSUE_BASE = 95000


# --------------------------------------------------------------------------- #
# dataset access
# --------------------------------------------------------------------------- #


def _fetch_rows(offset: int, length: int) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": "test",
            "offset": offset,
            "length": length,
        }
    )
    with urllib.request.urlopen(f"{_ROWS_URL}?{qs}", timeout=120) as fh:
        data = json.load(fh)
    return [r["row"] for r in data.get("rows", [])]


def _all_rows(total: int = 731) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for off in range(0, total, 100):
        rows.extend(_fetch_rows(off, 100))
    return rows


def _as_list(value: Any) -> list[str]:
    """Coerce a dataset test-list field into a flat list of test ids.

    These fields are not consistently encoded. Observed in the wild:

    * a JSON array of ids                    -> ``'["a", "b"]'``
    * a JSON array of ONE PYTHON-REPR string -> ``'["[\\'a\\', \\'b\\']"]'``

    The second shape is why this is not a one-liner. Instance
    ``ansible__ansible-9a21e2477...`` ships all six of its ``fail_to_pass`` ids
    inside a single element, so a naive parse hands pytest one giant argument,
    it collects 0 items, and EVERY instance grades as unresolved — a 0% resolve
    rate that looks like factory incompetence and is actually a decoding bug.
    Flatten recursively, and try ``ast.literal_eval`` because a Python repr
    uses single quotes and is not valid JSON.
    """
    import ast

    def _parse(text: str) -> Any:
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(text)
            except (ValueError, SyntaxError):
                continue
        return None

    out: list[str] = []

    def _walk(v: Any, depth: int = 0) -> None:
        if depth > 4:  # pathological nesting: keep whatever we have
            return
        if isinstance(v, (list, tuple)):
            for item in v:
                _walk(item, depth + 1)
            return
        if not isinstance(v, str):
            if v is not None:
                out.append(str(v))
            return
        text = v.strip()
        if not text:
            return
        if text.startswith(("[", "(")):
            parsed = _parse(text)
            if isinstance(parsed, (list, tuple)):
                _walk(parsed, depth + 1)
                return
        out.append(text)

    _walk(value)
    return out


# --------------------------------------------------------------------------- #
# fetch — pin the manifest before running anything
# --------------------------------------------------------------------------- #


def fetch(*, language: str, limit: int, seed: int) -> None:
    """Sample instances and freeze them into a hash-pinned manifest.

    The seed is recorded so the sample is reproducible, and each instance
    carries a hash of its problem statement so a later dataset revision that
    silently rewrites a task is detectable rather than invisible.
    """
    rows = [r for r in _all_rows() if r.get("repo_language") == language]
    if not rows:
        raise SystemExit(f"no instances with repo_language={language!r}")
    rows.sort(key=lambda r: str(r["instance_id"]))  # deterministic pre-shuffle order
    rng = random.Random(seed)
    picked = rng.sample(rows, min(limit, len(rows)))

    instances = []
    for r in picked:
        statement = r.get("problem_statement") or ""
        instances.append(
            {
                "instance_id": r["instance_id"],
                "repo": r["repo"],
                "base_commit": r["base_commit"],
                "language": r.get("repo_language"),
                "dockerhub_tag": r.get("dockerhub_tag"),
                "problem_statement": statement,
                "problem_statement_sha256": hashlib.sha256(
                    statement.encode("utf-8")
                ).hexdigest(),
                "fail_to_pass": _as_list(r.get("fail_to_pass")),
                "pass_to_pass": _as_list(r.get("pass_to_pass")),
                "test_patch": r.get("test_patch") or "",
                "before_repo_set_cmd": r.get("before_repo_set_cmd") or "",
                "selected_test_files_to_run": r.get("selected_test_files_to_run") or "",
            }
        )

    manifest = {
        "dataset": DATASET,
        "language": language,
        "seed": seed,
        "limit": limit,
        "frozen_at": datetime.now(UTC).isoformat(),
        "pool_size": len(rows),
        "instances": instances,
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            [i["instance_id"] for i in instances] + [str(seed)], sort_keys=True
        ).encode("utf-8")
    ).hexdigest()[:16]

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"pinned {len(instances)} instances -> {MANIFEST_PATH}")
    print(f"manifest_sha256={manifest['manifest_sha256']} seed={seed} pool={len(rows)}")
    for i in instances:
        print(f"  {i['instance_id']}  ({i['repo']}@{i['base_commit'][:10]})")


def _manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"no manifest at {MANIFEST_PATH}. Run `fetch` first — instances must "
            "be pinned BEFORE any run, or the sample is chosen after seeing results."
        )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _instance(instance_id: str) -> dict[str, Any]:
    for inst in _manifest()["instances"]:
        if inst["instance_id"] == instance_id:
            return inst
    raise SystemExit(f"{instance_id!r} is not in the pinned manifest")


# --------------------------------------------------------------------------- #
# diff handling — the oracle must stay hidden
# --------------------------------------------------------------------------- #

_DIFF_HEADER = re.compile(r"^diff --git a/(?P<a>\S+) b/(?P<b>\S+)\s*$")

_TEST_PATH = re.compile(
    r"(^|/)tests?(/|$)"           # a tests/ or test/ directory anywhere
    r"|(^|/)test_[^/]+$"          # test_foo.py
    r"|_test\.[a-z]+$"            # foo_test.go
    r"|(^|/)conftest\.py$"        # pytest fixtures shape the oracle too
    r"|\.spec\.[jt]sx?$"
    r"|(^|/)testing(/|$)"
)


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def split_diff(diff_text: str) -> tuple[str, list[str], list[str]]:
    """Return ``(code_only_diff, kept_paths, stripped_test_paths)``.

    Splits a unified diff on ``diff --git`` boundaries and drops any file whose
    path looks like a test. Operating per-file (not per-hunk) is deliberate: a
    file is either part of the oracle or it is not.
    """
    if not diff_text.strip():
        return "", [], []

    blocks: list[tuple[str, list[str]]] = []
    current_path: str | None = None
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        m = _DIFF_HEADER.match(line.rstrip("\n"))
        if m:
            if current_path is not None:
                blocks.append((current_path, current))
            current_path = m.group("b")
            current = [line]
        elif current_path is not None:
            current.append(line)
    if current_path is not None:
        blocks.append((current_path, current))

    kept: list[str] = []
    stripped: list[str] = []
    out: list[str] = []
    for path, lines in blocks:
        if is_test_path(path):
            stripped.append(path)
        else:
            kept.append(path)
            out.extend(lines)
    return "".join(out), kept, stripped


def assert_no_test_edits(diff_text: str) -> None:
    """Hard guarantee, checked in code rather than eyeballed.

    A graded diff containing a test edit would let the factory rewrite the
    oracle that is supposed to be judging it.
    """
    offenders = [
        m.group("b")
        for line in diff_text.splitlines()
        if (m := _DIFF_HEADER.match(line.strip()))
        and is_test_path(m.group("b"))
    ]
    if offenders:
        raise AssertionError(
            f"graded diff still touches test files: {offenders}. "
            "The oracle must never be editable by the arm under test."
        )


# --------------------------------------------------------------------------- #
# run — drive the factory chain over one instance
# --------------------------------------------------------------------------- #


def _story_slug(instance_id: str) -> str:
    """A STABLE slug for an instance.

    Was ``abs(hash(instance_id))``, and Python salts ``hash()`` per process
    (PYTHONHASHSEED), so every run produced a different slug — hence a
    different per-story worktree name. Re-running an instance left the previous
    worktree orphaned in ``state/worktrees/``, and the diff capture below,
    which took ``sorted(glob(...))[0]``, could then grade the WRONG run's tree
    (or one whose git metadata pointed at a deleted ``.git``). Identity must
    never ride on a value that changes between processes.
    """
    return "swe-" + hashlib.sha256(instance_id.encode("utf-8")).hexdigest()[:10]


def _run_dir(instance_id: str, arm: str) -> Path:
    d = RUNS_DIR / instance_id / arm
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_result(
    instance_id: str, arm: str, payload: dict[str, Any], *, merge: bool = False
) -> Path:
    """Persist ``result.json`` for one (instance, arm).

    ``merge=False`` (a fresh ``run``) REPLACES the file wholesale. It used to
    merge unconditionally, so keys from a previous run in the same directory
    (e.g. ``context_*``, or a ``grade`` verdict for a prediction that no
    longer exists) persisted forever and were reported as if this run produced
    them. Wholesale replacement is chosen over deleting known-stale keys
    because a delete-list rots: the next new result key added would silently
    start carrying over again. A new run means a new prediction, so ANY prior
    content — including the old grade — is void.

    ``merge=True`` is for ``grade``, which legitimately adds its verdict onto
    the run's existing result.
    """
    out = _run_dir(instance_id, arm) / "result.json"
    existing: dict[str, Any] = {}
    if merge and out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.update(payload)
    out.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return out


def _reset_run_artifacts(run_dir: Path) -> None:
    """Delete every artifact a PREVIOUS run of this (instance, arm) left behind.

    Called at the TOP of both run functions, before anything can exit. Without
    it, run #2 failing early (precheck, timeout, crash) leaves run #1's
    ``prediction.diff`` sitting next to run #2's result — ``grade`` then
    merges a verdict about a DEAD prediction onto the new run, and ``report``
    counts an oracle pass for a run that produced nothing.

    Also wipes ``state/`` — the bare arm's isolated ledger lives there and
    would otherwise ACCUMULATE Run rows across re-runs, inflating the sum-all
    totals (the factory arm's ``root/`` is already rebuilt by
    ``_build_bench_root``). A crashed run therefore leaves NO result.json,
    which ``audit`` treats as a failure — fail safe, never a stale pass.
    """
    for name in ("prediction.diff", "raw.diff", "grade.log", "result.json", "audit.json"):
        (run_dir / name).unlink(missing_ok=True)
    shutil.rmtree(run_dir / "state", ignore_errors=True)


def _clone_url(inst: dict[str, Any]) -> str:
    """The fetch URL for an instance. Separate so tests can point it at a
    local fixture repo instead of the network."""
    return f"https://github.com/{inst['repo']}.git"


def _clone(inst: dict[str, Any], dest: Path) -> None:
    """Shallow-clone the repo AT the base commit — no history, no future.

    ``--depth 1`` from a fetched commit means the agent cannot walk forward to
    the fix or backward for context it would not have had. This is the
    contamination control, not an optimization.
    """
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    url = _clone_url(inst)
    _git(dest, "init", "-q")
    _git(dest, "remote", "add", "origin", url)
    _git(dest, "fetch", "-q", "--depth", "1", "origin", inst["base_commit"])
    _git(dest, "checkout", "-q", "FETCH_HEAD")
    _git(dest, "checkout", "-q", "-B", "swebench-base")
    _git(dest, "config", "user.email", "bench@example.invalid")
    _git(dest, "config", "user.name", "swebench adapter")
    _init_submodules(inst, dest)
    # A remote-tracking ref for the base branch, set AFTER submodule
    # vendoring so it points at the final base commit. The reviewer's diff
    # helper asks for ``git diff origin/<default_branch>...HEAD``; with only
    # the local branch that fails rc=128 and the reviewer is handed the error
    # string instead of a diff. Belt-and-braces alongside the handlers-side
    # fallback.
    _git(dest, "update-ref", "refs/remotes/origin/swebench-base", "HEAD")


def _init_submodules(inst: dict[str, Any], dest: Path) -> None:
    """Initialise submodules and VENDOR their content into ``swebench-base``.

    openlibrary's ``infogami`` is a symlink into an uninitialised submodule:
    without this step, mounting the tree over the image's ``/app`` produces
    ``ModuleNotFoundError: No module named 'infogami'`` in under a second,
    deterministically, and dev burns its whole budget on an environment that
    can never go green.

    Initialising alone is NOT enough for the factory arm: the chain builds
    per-story worktrees with ``git worktree add``, which never populates
    submodules — the clone would pass the collect precheck while dev's actual
    worktree import-fails (proxy ≠ real). So after init, the gitlinks are
    converted to plain tracked files and committed onto ``swebench-base``:
    every tree derived from that branch then carries the content. Any fetch
    failure is a loud hard error — a silently-partial clone is the exact bug
    this exists to kill.

    The main-repo contamination control is unaffected — submodules are
    DEPENDENCY repos; the gold patch lives in the main repo, whose history
    stays at depth 1.
    """
    if not (dest / ".gitmodules").exists():
        return
    base = ["git", "-C", str(dest), "submodule", "update", "--init", "--recursive"]
    # Two attempts, no more: depth-1 first, then a full fetch — some servers
    # refuse a direct shallow fetch of a submodule's pinned commit.
    proc = subprocess.run([*base, "--depth", "1"], capture_output=True, text=True)
    if proc.returncode != 0:
        proc = subprocess.run(base, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"submodule init failed for {inst['instance_id']}: "
            f"{((proc.stderr or '') + (proc.stdout or ''))[-500:]}"
        )

    paths_proc = subprocess.run(
        ["git", "-C", str(dest), "config", "-f", ".gitmodules",
         "--get-regexp", r"^submodule\..*\.path$"],
        capture_output=True, text=True,
    )
    sub_paths = [line.split(" ", 1)[1] for line in paths_proc.stdout.splitlines() if " " in line]
    for rel in sub_paths:
        sub_dir = dest / rel
        if not sub_dir.is_dir():
            continue
        # Drop every nested ``.git`` (gitfile or dir, including nested
        # submodules') or ``git add`` would re-record a gitlink, not files.
        for gitmeta in sorted(sub_dir.rglob(".git"), reverse=True):
            if gitmeta.is_dir():
                shutil.rmtree(gitmeta, ignore_errors=True)
            else:
                gitmeta.unlink(missing_ok=True)
        # Tolerant: the gitlink may be absent from the index at this commit.
        subprocess.run(
            ["git", "-C", str(dest), "rm", "-q", "--cached", rel],
            capture_output=True, text=True,
        )
        # ``-f``: the SUPERPROJECT's ignore rules can match files inside the
        # submodule (they were tracked in the submodule's own repo, so its
        # ignores never applied there). Without force, those files silently
        # vanish from the vendored tree — recreating the clone-passes /
        # worktree-fails gap for exactly those paths.
        _git(dest, "add", "-f", rel)
    staged = subprocess.run(
        ["git", "-C", str(dest), "diff", "--cached", "--quiet"], capture_output=True
    )
    if staged.returncode != 0:
        _git(
            dest, "commit", "-q", "-m",
            "bench: vendor submodule content so worktree-derived trees carry it",
        )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    )


_STORY_TEMPLATE = """# {instance_id}

## Problem

{statement}

## Definition of done

Change the production code in this repository so the described behaviour is
correct.

Work exactly as you normally do: write tests that express the required
behaviour, then make them pass. A separate held-out test suite, written by the
project's maintainers and which you will never see, is the final judge.

## Where to put tests

Put new tests in the files or directories the test command below already
targets, so your own runs execute them.

Your test edits are removed from the diff before the held-out suite runs, so
they cannot affect the verdict either way — they are your feedback loop, not
the grade. Only your production-code changes are judged. This means a test
that merely asserts whatever your implementation happens to do buys nothing:
make the tests encode what the TASK requires.

## Running the tests

This checkout has NO dependencies installed, so a bare `pytest` fails with
`ModuleNotFoundError`. Run this exact command from the repo root — it executes
inside an image that has the dependencies, with your working tree mounted so it
tests YOUR edits:

```
{test_command}
```
"""


def _test_file_paths(entries: list[str]) -> list[str]:
    """Reduce test entries to distinct FILE paths, dropping any ``::node_id``.

    ``selected_test_files_to_run`` does not contain file paths despite the
    name — it contains the oracle's ``fail_to_pass`` NODE IDS, e.g.
    ``test/.../test_sys_info.py::test_get_distribution_not_linux[SunOS-Solaris]``.

    Handing those to dev is wrong twice over:

    1. It LEAKS the oracle. The hidden suite's test names are exactly what the
       arm under test must not see.
    2. Those tests do not exist in dev's tree — they are added by the test
       patch, which is deliberately withheld. Every run died on
       ``ERROR: not found``, so dev could never get a green signal and blocked
       on an identical failure signature.

    The file itself DOES exist at the base commit, and running it exercises
    the pre-existing tests: a real regression signal, with no oracle leak.
    """
    seen: dict[str, None] = {}
    for entry in entries:
        path = entry.split("::", 1)[0].strip()
        if path:
            seen.setdefault(path, None)
    return list(seen)


def _existing_targets(paths: list[str], repo: Path) -> list[str]:
    """Keep only test targets that EXIST in the arm's tree.

    Some instances add a brand-new test file, so the oracle's target does not
    exist at ``base_commit`` — and the test patch that creates it is
    deliberately withheld from the arm. Pointing dev at it produces
    ``ERROR: file or directory not found``, no green run is ever possible, and
    dev burns its whole retry budget on a target that cannot exist. Observed on
    ``openlibrary-798055d1`` (``scripts/tests/test_import_standard_ebooks.py``).

    A missing file falls back to its nearest existing ancestor DIRECTORY, which
    keeps the run pointed at relevant tests instead of the whole suite. If
    nothing survives, the caller runs the repo default.
    """
    out: dict[str, None] = {}
    for rel in paths:
        candidate = repo / rel
        if candidate.exists():
            out.setdefault(rel, None)
            continue
        parent = candidate.parent
        while parent != repo and parent.is_relative_to(repo):
            if parent.is_dir():
                out.setdefault(str(parent.relative_to(repo)), None)
                break
            parent = parent.parent
    return list(out)


def instance_test_command(
    inst: dict[str, Any],
    test_files: list[str] | None = None,
    repo: Path | None = None,
    *,
    collect_only: bool = False,
) -> str:
    """The app's test command, run INSIDE the instance's official image.

    A bare ``git clone`` has no dependencies installed, so plain
    ``python -m pytest`` dies with ``ModuleNotFoundError`` before dev writes a
    line. Measured: dev burned two attempts on an identical
    ``No module named 'ansible'`` signature, hit the same-signature guard, and
    blocked with an EMPTY diff after 870k tokens. That measured the adapter,
    not the factory — run-until-green is the factory's whole mechanism, and it
    cannot run anything without a working environment.

    The instance's image already has the dependencies, so mount the working
    tree over its ``/app`` and run there. Imports resolve against the image's
    site-packages while the CODE under test is the dev's own edits.

    ``$PWD`` (not a baked path) because the chain runs this from a per-story
    worktree that does not exist when the config is written. OpenHands uses a
    ``LocalWorkspace``, so the dev agent's shell is on the host and can reach
    docker; the post-run ``_run_pytest`` gate shells out the same way.

    The container must not litter the host tree with ROOT-OWNED files, or the
    next run cannot even delete its own workspace ("Permission denied" on
    ``.pytest_cache``, observed). Three guards: run as the invoking uid/gid,
    disable pytest's cache plugin, and suppress ``.pyc`` writes. ``HOME=/tmp``
    because the mapped user has no home inside the image.
    """
    entries = test_files if test_files is not None else _as_list(
        inst.get("selected_test_files_to_run")
    )
    files = _test_file_paths(entries)
    target = " ".join(_shq(t) for t in files) if files else ""
    mode = "--collect-only -q " if collect_only else ""
    inner = f"python -m pytest -p no:cacheprovider {mode}{target}".strip()
    image = f"jefzda/sweap-images:{inst['dockerhub_tag']}"
    return (
        'docker run --rm -v "$PWD":/app -w /app '
        '--user "$(id -u):$(id -g)" -e HOME=/tmp '
        "-e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash "
        f"{image} -lc {_shq(inner)}"
    )


def _ensure_image(inst: dict[str, Any], timeout_s: int = 1800) -> bool:
    """Pull the instance image if absent. Returns False when unavailable."""
    image = f"jefzda/sweap-images:{inst['dockerhub_tag']}"
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0:
        return True
    print(f"pulling {image} …", flush=True)
    return (
        subprocess.run(
            ["docker", "pull", image], capture_output=True, text=True, timeout=timeout_s
        ).returncode
        == 0
    )


_PRECHECK_TIMEOUT_S = 600


def _precheck_collect(inst: dict[str, Any], repo: Path) -> dict[str, Any]:
    """Pre-dispatch gate: does the instance's test command even COLLECT?

    ``proxy ≠ real``: the harness used to check that ``test_command`` was SET,
    never that it WORKED. An environment where collection fails (e.g. an
    uninitialised submodule import) turns a run into 631 seconds of dev
    burning budget against a suite that can never go green. This runs the
    SAME docker command dev will run — same image, same mount, built by
    ``instance_test_command`` — with ``--collect-only -q`` (~1s), so it tests
    the real environment, not a stand-in.

    Two DISTINCT conditions look identical to a naive gate and must not:

    * **infogami class** — the target files exist but collection dies on a
      broken import (uninitialised submodule, wrecked env). Genuinely fatal.
    * **new-test-file class** — the target file does not exist at
      ``base_commit`` because the DEV is supposed to CREATE it (a legitimate
      TDD red; the story template says "put new tests in the files the test
      command already targets"). Observed on ``openlibrary-798055…``: rc 4,
      ``ERROR: file or directory not found``, $0 spend — a working-oracle
      instance hard-failed for doing exactly what the task requires.

    So: targets that EXIST are collected strictly (``mode:
    "existing-targets"``, rc 0 required). When NONE exist, the gate verifies
    the ENVIRONMENT instead (``mode: "ancestor-env-check"``): collect each
    missing target's nearest existing ancestor directory (via
    ``_existing_targets``; repo root as last resort). rc 0 and rc 5 ("no
    tests collected", no errors) both PASS in that mode — an empty ancestor
    is fine, the dev will add the file — while rc 2 (collection/import
    errors: conftest and package imports still execute during ancestor
    collection) and anything else stays a hard fail.

    Returns the ``precheck`` payload: ``collect_ok``, ``duration_s``,
    ``mode``, ``collected_targets``, ``exit_code``, ``tail``.
    """
    files = _test_file_paths(_as_list(inst.get("selected_test_files_to_run")))
    existing = [f for f in files if (repo / f).exists()]
    if existing or not files:
        # No declared targets at all → whole-repo strict collect, as before.
        mode, targets, ok_rcs = "existing-targets", existing, (0,)
    else:
        mode, targets, ok_rcs = "ancestor-env-check", _existing_targets(files, repo), (0, 5)

    cmd = instance_test_command(inst, test_files=targets, repo=repo, collect_only=True)
    t0 = time.monotonic()
    rc: int | None = None
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=_PRECHECK_TIMEOUT_S,
        )
        rc = proc.returncode
        ok = rc in ok_rcs
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
    except (subprocess.TimeoutExpired, OSError) as exc:
        ok, tail = False, f"collect precheck invocation failed: {exc}"
    return {
        "collect_ok": ok,
        "duration_s": round(time.monotonic() - t0, 1),
        "mode": mode,
        "collected_targets": targets,
        "exit_code": rc,
        "tail": tail,
    }


def _ledger_totals(runs: list[Any], story_id: int | None) -> dict[str, Any]:
    """Cost/token totals over EVERY Run row in the run's isolated ledger.

    The bench state root is per-run isolated, so every row in its DB belongs
    to this run. Summing only ``story_id``-attributed rows made any row with a
    different or ``None`` story_id (an onboarder/setup persona) invisible —
    measured 1.62x cost under-reporting. Rows not attributed to ``story_id``
    are ALSO counted separately, so an attribution gap is visible, not silent.
    """
    unattributed = [r for r in runs if getattr(r, "story_id", None) != story_id]
    return {
        "tokens_in": sum(int(r.tokens_in or 0) for r in runs),
        "tokens_out": sum(int(r.tokens_out or 0) for r in runs),
        "cached_input_tokens": sum(
            int(getattr(r, "cached_input_tokens", 0) or 0) for r in runs
        ),
        "cost_usd": round(sum(float(r.cost_usd or 0.0) for r in runs), 4),
        "persona_calls": len(runs),
        "unattributed_persona_calls": len(unattributed),
        "unattributed_cost_usd": round(
            sum(float(r.cost_usd or 0.0) for r in unattributed), 4
        ),
    }


def _build_bench_root(inst: dict[str, Any], repo: Path) -> Path:
    """A minimal factory root: own state db, own settings, app -> the clone."""
    root = _run_dir(inst["instance_id"], "factory") / "root"
    if root.exists():
        shutil.rmtree(root)
    (root / "state").mkdir(parents=True)
    app_dir = root / "apps" / "swebench"
    (app_dir / "stories").mkdir(parents=True)
    (app_dir / "directions").mkdir(parents=True)

    # ``selected_test_files_to_run`` is a JSON-encoded LIST, like fail_to_pass.
    # Interpolating it raw produced `python -m pytest ["tests/x.py"]`, which
    # pytest reads as a nonexistent path — every dev run would have seen a
    # collection error instead of the real suite.
    test_files = _as_list(inst.get("selected_test_files_to_run"))
    test_cmd = instance_test_command(inst, test_files, repo=repo)
    cfg = {
        "name": "swebench",
        "repo": f"swebench/{inst['instance_id']}",
        "default_branch": "swebench-base",
        "app_repo_path": str(repo),
        "context_dir": "context",
        "gates": {
            "test_command": test_cmd,
            "smoke_command": "",
            "smoke_harness_ready": False,
        },
    }
    (app_dir / "config.yaml").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )

    settings = {"dev_convergence": {"enabled": True}}
    (root / "factory_settings.yaml").write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )
    return root


def run_factory(instance_id: str, *, max_steps: int, timeout_s: int) -> None:
    # Wall clock starts at ENTRY. It used to start after clone + bench-root
    # setup, so reported wall_clock_s silently excluded that work.
    entered = time.monotonic()
    inst = _instance(instance_id)
    run_dir = _run_dir(instance_id, "factory")
    # BEFORE any exit path (image pull, clone, precheck): a stale
    # prediction.diff must never outlive the run that produced it.
    _reset_run_artifacts(run_dir)
    if not _ensure_image(inst):
        raise SystemExit(
            f"image for {instance_id} is unavailable; the factory arm needs it for "
            "a working test environment (see instance_test_command)"
        )
    repo = run_dir / "repo"
    _clone(inst, repo)
    root = _build_bench_root(inst, repo)

    # PRE-DISPATCH COLLECT GATE. Fail the run NOW, loudly, if the test command
    # cannot even collect — before a single model token is spent.
    precheck = _precheck_collect(inst, repo)
    # The tail is kept out of the success-path result to stay lean; the mode
    # and collected targets always land in result.json for the audit trail.
    collect_tail = str(precheck.pop("tail", ""))
    if not precheck["collect_ok"]:
        error = f"precheck: test command does not collect: {collect_tail[-400:]}"
        _write_result(
            instance_id,
            "factory",
            {
                "arm": "factory",
                "instance_id": instance_id,
                "repo": inst["repo"],
                "base_commit": inst["base_commit"],
                "problem_statement_sha256": inst["problem_statement_sha256"],
                "manifest_sha256": _manifest()["manifest_sha256"],
                "ts": datetime.now(UTC).isoformat(),
                "wall_clock_s": round(time.monotonic() - entered, 1),
                "final_state": None,  # no story was ever dispatched
                "error": error,
                "factory_says_green": False,
                "precheck": {**precheck, "tail": collect_tail[-1500:]},
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "persona_calls": 0,
            },
        )
        raise SystemExit(error)

    # HARD isolation: every event write, every state read, inside the bench
    # root. Production telemetry must not see a single synthetic row.
    os.environ["FACTORY_STATE_ROOT"] = str(root)

    sys.path.insert(0, str(FACTORY_ROOT))
    from sqlmodel import Session, select

    from factory.app_config import load_app_config
    from factory.chain import orchestrator as O  # noqa: N812
    from factory.chain.state_machine import StoryRecord, StoryState
    from factory.runner import Run, _engine

    story_rel = f"stories/{SWE_ISSUE_BASE}-{instance_id[:40]}.md"
    (root / "apps" / "swebench" / story_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / "apps" / "swebench" / story_rel).write_text(
        _STORY_TEMPLATE.format(
            instance_id=instance_id,
            statement=inst["problem_statement"],
            test_command=instance_test_command(inst, repo=repo),
        ),
        encoding="utf-8",
    )

    db = root / "state" / "factory.db"
    story = StoryRecord(
        id=None,
        direction_id="swebench",
        app="swebench",
        title=instance_id[:80],
        slug=_story_slug(instance_id),
        scope="backend",
        state=StoryState.SM_DONE.value,
        github_issue_number=SWE_ISSUE_BASE,
        story_file_path=story_rel,
    )
    eng = _engine(db)
    with Session(eng) as s:
        s.add(story)
        s.commit()
        s.refresh(story)
        story_id = story.id

    cfg = load_app_config("swebench", root)
    allowed = {"dev", "review"}
    terminal = {
        StoryState.REVIEWER_DONE.value,
        StoryState.BLOCKED_TESTS_NEED_CLARIFICATION.value,
        StoryState.BLOCKED_REVIEW_NONCONVERGENT.value,
    }
    # The dispatch-loop budget deliberately starts HERE (setup already spent
    # is not dev's fault); the reported wall_clock_s uses ``entered``.
    started = time.monotonic()
    transitions: list[str] = []
    error: str | None = None
    for _ in range(max_steps):
        if time.monotonic() - started > timeout_s:
            error = f"wall-clock cap {timeout_s}s hit"
            break
        with Session(eng) as s:
            row = s.get(StoryRecord, story_id)
            assert row is not None
        if row.state in terminal:
            break
        name = O._dispatch_for_story(row)
        if name not in allowed:
            transitions.append(f"stop: state={row.state} dispatches {name}")
            break
        before = row.state
        try:
            O._invoke_handler(name, row, cfg, root, dry_run=False, db_path=db)
        except Exception as exc:  # never crash the driver
            error = f"{name}: {type(exc).__name__}: {exc}"
            break
        transitions.append(f"{name}: {before} -> {row.state}")
        print(transitions[-1], flush=True)

    # EVERY Run row in this isolated DB belongs to this run — see
    # ``_ledger_totals`` for why a story_id filter under-reported cost 1.62x.
    with Session(eng) as s:
        final = s.get(StoryRecord, story_id)
        assert final is not None
        runs = list(s.exec(select(Run)).all())

    # Match this story's OWN worktree. A glob[0] would happily grade a stale
    # directory left by an earlier run of the same instance.
    slug = _story_slug(instance_id)
    matches = [
        p for p in (root / "state" / "worktrees").glob("swebench-*") if p.name.endswith(slug)
    ]
    graded_wt = matches[0] if matches else repo
    raw_diff = _capture_diff(graded_wt)
    code_diff, kept, stripped = split_diff(raw_diff)
    assert_no_test_edits(code_diff)

    (run_dir / "raw.diff").write_text(raw_diff, encoding="utf-8")
    (run_dir / "prediction.diff").write_text(code_diff, encoding="utf-8")

    # Tokens are the primitive; dollars are derived (see bench/README.md).
    result = {
        "arm": "factory",
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "problem_statement_sha256": inst["problem_statement_sha256"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "final_state": final.state,
        "dev_retries": final.dev_retries,
        "reviewer_cycles": final.reviewer_cycles,
        **_ledger_totals(runs, story_id),
        "cost_source": "derived-from-price-table",
        "precheck": precheck,
        "transitions": transitions[-12:],
        "error": error,
        # The factory's OWN verdict — what its gates believe. `grade` supplies
        # the hidden oracle's verdict; the pair is what gate precision means.
        "factory_says_green": final.state == StoryState.REVIEWER_DONE.value,
        "files_changed": kept,
        "test_files_stripped": stripped,
        "diff_bytes": len(code_diff),
    }
    out = _write_result(instance_id, "factory", result)
    print(f"factory arm done: {out}")
    if stripped:
        print(f"  stripped {len(stripped)} test-file edit(s) before grading: {stripped}")


def _capture_diff(wt: Path, base: str = "swebench-base") -> str:
    """Everything the arm changed relative to the BASE COMMIT.

    ``git diff --cached`` alone loses work that was COMMITTED: when dev
    exhausts its retries the chain commits the partial work to preserve it, so
    a staged-only diff comes back empty and the run grades as "produced
    nothing" when it actually produced a patch. Stage the worktree, then diff
    against the base ref so committed and uncommitted changes both appear.
    """
    subprocess.run(["git", "-C", str(wt), "add", "-A"], capture_output=True)
    for ref in (base, "HEAD"):
        proc = subprocess.run(
            ["git", "-C", str(wt), "diff", ref], capture_output=True, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    return subprocess.run(
        ["git", "-C", str(wt), "diff", "--cached"], capture_output=True, text=True
    ).stdout


# --------------------------------------------------------------------------- #
# bare arm — the SAME weights with a minimal scaffold
# --------------------------------------------------------------------------- #

_BARE_SYSTEM = """\
You are fixing a bug in a software repository. You are in a shell at the repo root.

Reply with EXACTLY ONE of these, and nothing else:

  BASH
  <one shell command>

  DONE

Rules:
- One command per reply. No commentary outside the block.
- Edit files with standard tools (cat > file <<'EOF', sed, python - <<'EOF').
- Do NOT create, edit or delete test files. Test edits are stripped before
  grading, so they are wasted effort.
- Reply DONE when the production code change is complete.
- You cannot access the network.
"""

_BARE_TASK = """\
Repository: {repo}
Task:

{statement}

Fix the PRODUCTION code so this is resolved. A hidden test suite will judge it.
"""

_BARE_STEP_CAP = 40
_BARE_OUTPUT_CAP = 4000


def run_bare(instance_id: str, *, max_steps: int, timeout_s: int) -> None:
    """Minimal bash-loop agent on the IDENTICAL Azure deployment the factory uses.

    This is PLAN.md 1.4, and it is not optional. The product thesis is a
    model-agnostic harness that extracts frontier-competitive output from
    non-frontier models — the model is a config value in routes.yaml that gets
    swapped as cheaper models ship. So an absolute factory score measures the
    MODEL. The only number that measures the HARNESS is the delta between the
    factory and the same weights bare, which is what this arm supplies.

    Deliberately unsophisticated: one command per turn, truncated output, no
    planning, no retrieval, no review. That is the point — it is the floor the
    factory has to beat.
    """
    # Wall clock starts at ENTRY so clone/setup time is counted (same fix as
    # run_factory); ``started`` below still scopes the step-loop budget.
    entered = time.monotonic()
    inst = _instance(instance_id)
    run_dir = _run_dir(instance_id, "bare")
    # BEFORE any exit path: clears stale prediction/grade artifacts AND wipes
    # ``state/`` — unlike the factory arm's rebuilt root, the bare arm's
    # ledger lives directly under run_dir and would accumulate Run rows
    # across re-runs, inflating the sum-all totals the audit certifies.
    _reset_run_artifacts(run_dir)
    repo = run_dir / "repo"
    _clone(inst, repo)

    sys.path.insert(0, str(FACTORY_ROOT))
    from factory.model_router import route
    from factory.runner import text_run

    model = route("dev", "standard")
    transcript: list[dict[str, Any]] = []
    tokens_in = tokens_out = 0
    cost = 0.0
    started = time.monotonic()
    error: str | None = None

    history = [
        _BARE_SYSTEM,
        _BARE_TASK.format(repo=inst["repo"], statement=inst["problem_statement"]),
    ]
    steps = min(max_steps, _BARE_STEP_CAP)
    for step in range(steps):
        if time.monotonic() - started > timeout_s:
            error = f"wall-clock cap {timeout_s}s hit"
            break
        prompt = "\n\n".join(history[-24:])  # bounded context, oldest dropped
        try:
            reply = str(
                text_run(
                    persona="dev",
                    prompt=prompt,
                    model_id=model,
                    story_id=None,
                    software_factory_root=run_dir,
                    db_path=run_dir / "state" / "factory.db",
                )
            )
        except Exception as exc:  # noqa: BLE001
            error = f"model call failed at step {step}: {type(exc).__name__}: {exc}"
            break

        if "DONE" in reply and "BASH" not in reply:
            transcript.append({"step": step, "action": "done"})
            break
        command = _parse_bash(reply)
        if not command:
            history.append(reply)
            history.append("Invalid reply. Respond with a BASH block or DONE.")
            transcript.append({"step": step, "action": "invalid", "reply": reply[:200]})
            continue

        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = ((proc.stdout or "") + (proc.stderr or ""))[-_BARE_OUTPUT_CAP:]
        history.append(reply)
        history.append(f"Exit {proc.returncode}. Output:\n{output}")
        transcript.append(
            {
                "step": step,
                "action": "bash",
                "command": command[:300],
                "exit": proc.returncode,
            }
        )

    # Token/cost accounting from this arm's OWN isolated ledger.
    try:
        from sqlmodel import Session, select

        from factory.runner import Run, _engine

        with Session(_engine(run_dir / "state" / "factory.db")) as s:
            runs = list(s.exec(select(Run)).all())
        tokens_in = sum(int(r.tokens_in or 0) for r in runs)
        tokens_out = sum(int(r.tokens_out or 0) for r in runs)
        cost = sum(float(r.cost_usd or 0.0) for r in runs)
        calls = len(runs)
    except Exception:  # noqa: BLE001
        calls = len(transcript)

    raw_diff = _capture_diff(repo)
    code_diff, kept, stripped = split_diff(raw_diff)
    assert_no_test_edits(code_diff)
    (run_dir / "raw.diff").write_text(raw_diff, encoding="utf-8")
    (run_dir / "prediction.diff").write_text(code_diff, encoding="utf-8")

    result = {
        "arm": "bare",
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        "model": model,
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "steps_used": len(transcript),
        "step_cap": steps,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost, 4),
        "cost_source": "derived-from-price-table",
        "persona_calls": calls,
        "error": error,
        # The bare arm has NO gates — it cannot claim green, only produce a
        # diff. Recorded explicitly so `report` never credits it a verdict it
        # never made.
        "factory_says_green": None,
        "files_changed": kept,
        "test_files_stripped": stripped,
        "diff_bytes": len(code_diff),
        "transcript": transcript[-20:],
    }
    out = _write_result(instance_id, "bare", result)
    print(f"bare arm done: {out}")


_BASH_BLOCK = re.compile(r"BASH\s*\n(.+?)(?:\n\s*(?:BASH|DONE)\s*$|\Z)", re.S)


def _parse_bash(reply: str) -> str | None:
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text)
    m = _BASH_BLOCK.search(text)
    if not m:
        return None
    cmd = m.group(1).strip()
    cmd = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", cmd).strip()
    return cmd or None


# --------------------------------------------------------------------------- #
# grade — the hidden oracle
# --------------------------------------------------------------------------- #


def grade(instance_id: str, arm: str, *, timeout_s: int) -> None:
    """Apply the stripped diff in the instance's official image and run the
    hidden test sets.

    Records ``wrong_patch`` and ``task_broken`` as DISTINCT outcomes. ~30% of
    this suite's public tasks were found broken by OpenAI's 2026-07-08 audit;
    summing the two into one "failure" number would read a broken harness as
    factory incompetence.
    """
    inst = _instance(instance_id)
    run_dir = _run_dir(instance_id, arm)
    pred = run_dir / "prediction.diff"
    if not pred.exists():
        raise SystemExit(f"no prediction.diff for {instance_id}/{arm}; run first")
    diff_text = pred.read_text(encoding="utf-8")
    assert_no_test_edits(diff_text)  # belt and braces: re-check at grade time

    image = f"jefzda/sweap-images:{inst['dockerhub_tag']}"
    f2p, p2p = inst["fail_to_pass"], inst["pass_to_pass"]

    started = time.monotonic()
    verdict: dict[str, Any] = {
        "arm": arm,
        "instance_id": instance_id,
        "image": image,
        "graded_at": datetime.now(UTC).isoformat(),
        "fail_to_pass_count": len(f2p),
        "pass_to_pass_count": len(p2p),
        "empty_patch": not diff_text.strip(),
    }

    if not diff_text.strip():
        # An empty patch cannot resolve anything. Recording it as an oracle
        # FAIL (rather than an error) keeps it in the denominator, which is
        # where a no-op belongs.
        verdict.update(
            {"oracle_resolved": False, "outcome": "empty_patch", "log_tail": ""}
        )
        _write_result(instance_id, arm, {"grade": verdict}, merge=True)
        print(json.dumps(verdict, indent=2))
        return

    pulled = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, text=True
    )
    if pulled.returncode != 0:
        proc = subprocess.run(
            ["docker", "pull", image], capture_output=True, text=True, timeout=timeout_s
        )
        if proc.returncode != 0:
            verdict.update(
                {
                    "oracle_resolved": None,
                    "outcome": "image_unavailable",
                    "log_tail": (proc.stderr or "")[-2000:],
                }
            )
            _write_result(instance_id, arm, {"grade": verdict}, merge=True)
            print(json.dumps(verdict, indent=2))
            return

    script = _GRADE_SCRIPT.format(
        test_patch=_heredoc(inst["test_patch"]),
        prediction=_heredoc(diff_text),
        before_cmd=inst.get("before_repo_set_cmd") or "true",
        f2p=" ".join(_shq(t) for t in f2p),
        p2p=" ".join(_shq(t) for t in p2p),
    )
    proc = _docker_bash(image, script, timeout_s)
    log = (proc.stdout or "") + (proc.stderr or "")
    (run_dir / "grade.log").write_text(log, encoding="utf-8")

    resolved = "SWEBENCH_RESULT: RESOLVED" in log
    applied = "SWEBENCH_APPLY: OK" in log
    # Order matters: a broken baseline short-circuits BEFORE the prediction is
    # applied, so "not applied" must not be read as the arm's fault.
    if "SWEBENCH_BASELINE: BROKEN_NO_COLLECT" in log:
        outcome = "task_broken_no_collect"
    elif "SWEBENCH_BASELINE: BROKEN_ALREADY_GREEN" in log:
        outcome = "task_broken_already_green"
    elif not applied:
        outcome = "patch_did_not_apply"
    elif resolved:
        outcome = "resolved"
    else:
        # Did the arm at least edit the files the real fix edited? A patch that
        # found the right function and got a convention wrong is a different
        # failure from one that never located the code.
        #
        # This hits the HuggingFace datasets API, and ``run-all`` can have N
        # graders doing it at once. A rate-limited lookup returns no gold files,
        # which would label a right-place patch ``wrong_place`` — a SILENT
        # misclassification. The verdict is unaffected (this only names the
        # failure, it does not decide it), but record whether the lookup
        # actually worked so the label can be trusted or discounted.
        lookup_ok = True
        try:
            gold_files = set(gold_touched_files(instance_id))
        except Exception:  # noqa: BLE001 - classification must not break grading
            gold_files = set()
            lookup_ok = False
        verdict["gold_files_lookup_ok"] = lookup_ok
        touched = {
            m.group("b")
            for line in diff_text.splitlines()
            if (m := _DIFF_HEADER.match(line.strip()))
        }
        overlap = sorted(gold_files & touched)
        verdict["gold_files"] = sorted(gold_files)
        verdict["touched_files"] = sorted(touched)
        verdict["gold_files_overlap"] = overlap
        outcome = "right_place_wrong_fix" if overlap else "wrong_place"

    verdict.update(
        {
            "oracle_resolved": resolved,
            "outcome": outcome,
            "exit_code": proc.returncode,
            "grade_wall_s": round(time.monotonic() - started, 1),
            "log_tail": log[-3000:],
        }
    )
    _write_result(instance_id, arm, {"grade": verdict}, merge=True)
    print(json.dumps({k: v for k, v in verdict.items() if k != "log_tail"}, indent=2))


def _docker_bash(image: str, script: str, timeout_s: int) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in ``image``.

    ``--entrypoint bash`` is required: these images already set
    ``Entrypoint=[/bin/bash]``, so passing ``bash -lc ...`` as the command made
    bash try to EXECUTE the string "bash" and die with "cannot execute binary
    file". ``--network none`` denies egress during grading so a patch cannot
    reach out for the answer.
    """
    return subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--entrypoint", "bash", image, "-lc", script],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _heredoc(text: str) -> str:
    return text if text.endswith("\n") or not text else text + "\n"


# Runs inside the instance's official image. Order matters: the test patch
# (the ORACLE) is applied first and the prediction second, so a prediction that
# tries to undo the oracle fails loudly instead of silently winning.
_GRADE_SCRIPT = r"""
set -o pipefail
cd /app 2>/dev/null || cd "$(ls -d /*/ | head -1)"
git config --global --add safe.directory '*' 2>/dev/null || true

cat > /tmp/test_patch.diff <<'SWEBENCH_TEST_PATCH_EOF'
{test_patch}
SWEBENCH_TEST_PATCH_EOF

cat > /tmp/prediction.diff <<'SWEBENCH_PRED_EOF'
{prediction}
SWEBENCH_PRED_EOF

# ORACLE SETUP. `before_repo_set_cmd` is the dataset's own setup: it resets to
# the base commit and then `git checkout <fix_commit> -- <test paths>`, i.e. it
# ALREADY installs the oracle test files. Applying `test_patch` on top of that
# conflicts ("patch does not apply"), which is why the test patch is only a
# FALLBACK below, used when the ids still do not collect.
git reset --hard HEAD >/dev/null 2>&1 || true
git clean -fd >/dev/null 2>&1 || true
{before_cmd}
echo "SWEBENCH_SETUP: before_repo_set_cmd rc=$?"

# Does every fail_to_pass id EXIST? pytest exits 4 for a missing file or a
# missing ::id.
#
# Do NOT grep for "no tests ran": `--collect-only -q` prints that line on
# EVERY successful collection, because collect-only runs nothing. Treating it
# as a failure marks healthy instances as broken — it scored 6 of these 10 as
# unusable when they were fine.
collect() {{
  python -m pytest --collect-only -q {f2p} >/tmp/collect.log 2>&1
  rc=$?
  if [ "$rc" = "4" ] || grep -qi "ERROR: not found\|ERROR: file or directory not found" /tmp/collect.log; then
    return 1
  fi
  return 0
}}

if ! collect; then
  echo "SWEBENCH_SETUP: ids missing after before_cmd; applying test_patch as fallback"
  if [ -s /tmp/test_patch.diff ]; then
    git apply -v /tmp/test_patch.diff 2>&1 || git apply -v --3way /tmp/test_patch.diff 2>&1 || true
  fi
fi

# The fail_to_pass ids MUST collect. pytest exits 4 ("file or directory not
# found") for a nonexistent id — non-zero, and therefore indistinguishable
# from a healthy red baseline unless checked separately. Left unchecked the
# instance grades as unresolved no matter what the arm produced.
if ! collect; then
  echo "SWEBENCH_BASELINE: BROKEN_NO_COLLECT (fail_to_pass ids do not exist)"
  tail -20 /tmp/collect.log
  exit 3
fi

# Baseline: the fail_to_pass set MUST fail before the prediction is applied.
# If it already passes, the instance is not measuring what it claims to.
if python -m pytest -q {f2p} >/tmp/baseline.log 2>&1; then
  echo "SWEBENCH_BASELINE: BROKEN_ALREADY_GREEN (fail_to_pass passes unpatched)"
  tail -20 /tmp/baseline.log
  exit 3
fi
echo "SWEBENCH_BASELINE: OK (red as expected)"

if git apply -v /tmp/prediction.diff 2>&1 || git apply -v --3way /tmp/prediction.diff 2>&1; then
  echo "SWEBENCH_APPLY: OK"
else
  echo "SWEBENCH_APPLY: FAILED"
  exit 2
fi

fail=0
if ! python -m pytest -q {f2p} 2>&1 | tail -40; then fail=1; fi
if [ -n "{p2p}" ]; then
  if ! python -m pytest -q {p2p} 2>&1 | tail -40; then fail=1; fi
fi
if [ "$fail" = "0" ]; then echo "SWEBENCH_RESULT: RESOLVED"; else echo "SWEBENCH_RESULT: UNRESOLVED"; fi
"""


# --------------------------------------------------------------------------- #
# selftest — validate the ORACLE before trusting any measurement
# --------------------------------------------------------------------------- #


def selftest(instance_id: str | None, *, timeout_s: int) -> None:
    """Grade the instance's own GOLD patch. It must come back RESOLVED.

    This is the control. If the gold patch does not resolve, the harness is
    wrong — the image, the test-name format, the apply order, something — and
    every factory number produced through it would be measuring my plumbing
    rather than the factory. Run this before believing a single result.

    A gold patch that fails here is also how ``task_broken`` gets identified
    honestly: it separates "this instance is unsolvable as shipped" from "the
    factory could not solve it", which OpenAI's audit says is ~30% of the
    public suite.

    The gold patch is fetched just-in-time and never written next to a run, so
    it cannot leak into an arm's working tree.
    """
    manifest = _manifest()
    targets = (
        [i for i in manifest["instances"] if i["instance_id"] == instance_id]
        if instance_id
        else manifest["instances"]
    )
    if not targets:
        raise SystemExit(f"{instance_id!r} is not in the pinned manifest")

    gold = _gold_patches({i["instance_id"] for i in targets})
    results: list[dict[str, Any]] = []
    for inst in targets:
        iid = inst["instance_id"]
        patch = gold.get(iid, "")
        print(f"\n=== selftest {iid[:60]} ===", flush=True)
        if not patch.strip():
            results.append({"instance_id": iid, "gold_resolves": None, "note": "no gold patch"})
            print("  no gold patch in dataset")
            continue

        image = f"jefzda/sweap-images:{inst['dockerhub_tag']}"
        if subprocess.run(
            ["docker", "image", "inspect", image], capture_output=True
        ).returncode != 0:
            pull = subprocess.run(
                ["docker", "pull", image], capture_output=True, text=True, timeout=timeout_s
            )
            if pull.returncode != 0:
                results.append(
                    {"instance_id": iid, "gold_resolves": None, "note": "image_unavailable"}
                )
                print("  image unavailable")
                continue

        # The gold patch is code-only by construction, but strip anyway: if the
        # dataset's `patch` ever included a test edit, grading it would validate
        # the oracle against a modified oracle.
        code_only, _, stripped = split_diff(patch)
        script = _GRADE_SCRIPT.format(
            test_patch=_heredoc(inst["test_patch"]),
            prediction=_heredoc(code_only),
            before_cmd=inst.get("before_repo_set_cmd") or "true",
            f2p=" ".join(_shq(t) for t in inst["fail_to_pass"]),
            p2p=" ".join(_shq(t) for t in inst["pass_to_pass"]),
        )
        proc = _docker_bash(image, script, timeout_s)
        log = (proc.stdout or "") + (proc.stderr or "")
        d = _run_dir(iid, "selftest")
        (d / "selftest.log").write_text(log, encoding="utf-8")

        resolved = "SWEBENCH_RESULT: RESOLVED" in log
        if "SWEBENCH_BASELINE: BROKEN_NO_COLLECT" in log:
            note = "fail_to_pass_ids_do_not_collect"
        elif "SWEBENCH_BASELINE: BROKEN_ALREADY_GREEN" in log:
            note = "baseline_already_green"
        elif "SWEBENCH_APPLY: FAILED" in log:
            note = "gold_patch_did_not_apply"
        elif resolved:
            note = "ok"
        else:
            note = "gold_patch_does_not_resolve"
        results.append(
            {
                "instance_id": iid,
                "gold_resolves": resolved,
                "note": note,
                "stripped_from_gold": stripped,
            }
        )
        print(f"  gold_resolves={resolved}  ({note})")

    out = SWE_DIR / "selftest.json"
    out.write_text(
        json.dumps(
            {"checked_at": datetime.now(UTC).isoformat(), "results": results}, indent=2
        ),
        encoding="utf-8",
    )
    ok = sum(1 for r in results if r["gold_resolves"])
    print(f"\n{ok}/{len(results)} instances have a WORKING oracle -> {out}")
    if ok < len(results):
        print(
            "Instances whose gold patch does not resolve are NOT factory failures. "
            "Exclude them, or the score measures the harness."
        )


def gold_touched_files(instance_id: str) -> list[str]:
    """Production files the maintainers' real fix changed (tests excluded).

    Lets ``grade`` record whether the arm even edited the right place. Without
    it, every failure collapses into one ``wrong_patch`` label, and a patch
    that found the exact right function but used the wrong string constant is
    indistinguishable from one that never located the code at all. Those are
    completely different failures and should never share a name.
    """
    patch = _gold_patches({instance_id}).get(instance_id, "")
    _, kept, _ = split_diff(patch)
    return kept


def _gold_patches(wanted: set[str]) -> dict[str, str]:
    """Fetch gold patches just-in-time. Never persisted beside a run."""
    found: dict[str, str] = {}
    for off in range(0, 731, 100):
        for row in _fetch_rows(off, 100):
            if row["instance_id"] in wanted:
                found[row["instance_id"]] = row.get("patch") or ""
        if len(found) == len(wanted):
            break
    return found


# --------------------------------------------------------------------------- #
# audit — every run must be fully auditable, and a broken run must not pass
# --------------------------------------------------------------------------- #

# Strings that mean the reviewer was handed an ERROR MESSAGE where the diff
# should have been (see factory/chain/handlers.py `_pr_diff_for_review`'s
# fallback strings). A reviewer verdict formed over one of these is a verdict
# about nothing — the run is invalid.
_REVIEWER_BROKEN_DIFF_MARKERS: tuple[str, ...] = (
    "returned rc=",
    "(diff is empty",
    "(gh pr diff failed",
    "(git diff worktree failed",
    "(could not resolve writing worktree",
)

# A failed dev call this fast never did real work — the pre-model /
# unrunnable-environment signature (cf. the "$0/0.2s retry storm" class).
_FAST_FAIL_S = 5.0

_RUN_COLUMNS = (
    "ts",
    "persona",
    "model",
    "story_id",
    "tokens_in",
    "tokens_out",
    "cached_input_tokens",
    "cost_usd",
    "duration_s",
    "success",
    "error",
)


def _audit_read_runs(db: Path) -> list[dict[str, Any]]:
    """Read every Run row from the run's isolated ledger, READ-ONLY.

    Plain sqlite3 with ``mode=ro`` instead of the factory's ``_engine``: the
    engine runs schema migrations on open, and an audit must never mutate the
    artifact it is auditing.
    """
    import sqlite3

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            f"SELECT {', '.join(_RUN_COLUMNS)} FROM runs ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def _scan_prompt_bodies(state_root: Path) -> tuple[list[str], int]:
    """Return ``(failures, reviewer_prompts_seen)`` from the prompt-body stream.

    Scans the live ``prompt_bodies.ndjson`` plus rotated segments for the
    broken-diff markers in REVIEWER prompts. A missing stream is the CALLER's
    failure to report — this only scans what exists.
    """
    failures: list[str] = []
    reviewer_seen = 0
    for f in sorted((state_root / "state" / "events").glob("prompt_bodies.ndjson*")):
        # Stream line-by-line: a rotated body stream can be ~100MB per segment.
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") != "prompt_body" or rec.get("persona") != "reviewer":
                    continue
                reviewer_seen += 1
                hits = [
                    m for m in _REVIEWER_BROKEN_DIFF_MARKERS if m in str(rec.get("prompt", ""))
                ]
                if hits:
                    failures.append(
                        f"reviewer prompt (hash {str(rec.get('prompt_hash', ''))[:16]}) "
                        f"contains broken-diff markers {hits}: the reviewer saw an error "
                        "string instead of a diff, which invalidates the run"
                    )
    return failures, reviewer_seen


def _scan_response_bodies(state_root: Path) -> list[dict[str, Any]]:
    """Return every response-body record (live stream + rotated segments)."""
    records: list[dict[str, Any]] = []
    for f in sorted((state_root / "state" / "events").glob("response_bodies.ndjson*")):
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "response_body":
                    records.append(rec)
    return records


def _trajectory_files(state_root: Path) -> list[Path]:
    return sorted((state_root / "state" / "events" / "trajectories").glob("*.ndjson"))


_SHOW_TRAJ_LAST_N = 5


def _trajectory_assistant_messages(path: Path) -> list[str]:
    """Extract the agent's message texts from a copied-out trajectory ndjson.

    OpenHands persists ``llm_message.content`` as a list of content parts;
    tolerate string content and missing fields — this is a viewer, not a
    validator.
    """
    messages: list[str] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(ev, dict) or ev.get("source") != "agent":
                    continue
                msg = ev.get("llm_message") or ev.get("message")
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "\n".join(
                        str(c.get("text", "")) for c in content if isinstance(c, dict)
                    )
                else:
                    continue
                if text.strip():
                    messages.append(text.strip())
    except OSError:
        return []
    return messages


def _show_responses(state_root: Path, responses: list[dict[str, Any]]) -> None:
    """Print the reviewer's response text and the tail of the newest dev
    trajectory, so an operator can read what happened without spelunking."""
    reviewer = [r for r in responses if r.get("persona") == "reviewer"]
    print(f"--- reviewer responses ({len(reviewer)}) ---")
    for r in reviewer:
        print(f"[{r.get('ts', '?')}] story={r.get('story_id')}")
        print(str(r.get("response", "")))
        print()
    trajs = _trajectory_files(state_root)
    if not trajs:
        print("--- no dev trajectory captured ---")
        return
    newest = trajs[-1]
    msgs = _trajectory_assistant_messages(newest)
    print(
        f"--- last {min(_SHOW_TRAJ_LAST_N, len(msgs))} of {len(msgs)} dev assistant "
        f"message(s) ({newest.name}) ---"
    )
    for m in msgs[-_SHOW_TRAJ_LAST_N:]:
        print(m)
        print("~" * 40)


def audit(instance_id: str, arm: str, *, show_responses: bool = False) -> None:
    """Audit one run's artifacts end-to-end; exit non-zero on ANY failure.

    Checks, in order:

    1. every persona/LLM call is listed from the isolated ledger's Run rows;
    2. the ledger's cost/token sums MATCH what result.json reported;
    3. no reviewer prompt contained an error string where the diff belonged;
    4. the first dev call did not fast-fail (failed in under ~5s) — the
       unrunnable-environment signature;
    5. a failed collect precheck recorded in result.json fails the audit.

    Response-side coverage (response bodies per call; a trajectory per dev
    call) is reported as WARNINGS, not failures: a size-capped trajectory or
    disabled capture must not invalidate a run. ``show_responses`` also prints
    the reviewer's response text and the tail of the newest dev trajectory.

    FAIL SAFE: a missing artifact (no result.json, no DB, no prompt bodies) is
    an audit FAILURE, never a pass — an unauditable run is an invalid run.
    Writes ``audit.json`` next to ``result.json`` either way.
    """
    run_dir = _run_dir(instance_id, arm)
    state_root = run_dir / "root" if arm == "factory" else run_dir
    failures: list[str] = []

    result: dict[str, Any] = {}
    result_valid = False  # file existed AND parsed to a non-empty JSON object
    result_path = run_dir / "result.json"
    if not result_path.exists():
        failures.append(f"missing artifact: {result_path}")
    else:
        try:
            loaded = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"result.json is not valid JSON: {exc}")
        else:
            if isinstance(loaded, dict) and loaded:
                result = loaded
                result_valid = True
            else:
                # FAIL SAFE: `{}` (or a non-object) would previously skip the
                # entire ledger<->result section via truthiness and audit-pass
                # a run that reported nothing.
                failures.append(
                    "result.json is empty or not a JSON object — nothing to certify"
                )

    calls: list[dict[str, Any]] = []
    db = state_root / "state" / "factory.db"
    if not db.exists():
        failures.append(f"missing artifact: {db} (no Run ledger — calls unauditable)")
    else:
        try:
            calls = _audit_read_runs(db)
        except Exception as exc:  # noqa: BLE001 — an unreadable ledger is a finding
            failures.append(f"Run ledger unreadable: {type(exc).__name__}: {exc}")

    # Response-side coverage: per persona call, was the model's response body
    # (and for dev, an OpenHands trajectory) captured? Missing coverage is a
    # WARNING, never a failure — a size-capped or scope-disabled capture must
    # not invalidate an otherwise-sound run.
    warnings: list[str] = []
    responses = _scan_response_bodies(state_root)
    resp_counts: dict[str, int] = {}
    for r in responses:
        p = str(r.get("persona", ""))
        resp_counts[p] = resp_counts.get(p, 0) + 1
    traj_files = _trajectory_files(state_root)

    print(f"=== audit {instance_id} / {arm} ===")
    resp_seen: dict[str, int] = {}
    traj_seen = 0
    for c in calls:
        persona = str(c["persona"])
        resp_seen[persona] = resp_seen.get(persona, 0) + 1
        has_resp = resp_seen[persona] <= resp_counts.get(persona, 0)
        line = (
            f"  {c['ts']}  {persona:<12} story={c['story_id']} "
            f"in={c['tokens_in']} out={c['tokens_out']} cached={c['cached_input_tokens']} "
            f"cost=${float(c['cost_usd'] or 0):.4f} dur={c['duration_s']}s "
            f"ok={bool(c['success'])} resp={'yes' if has_resp else 'NO'}"
        )
        if persona == "dev":
            traj_seen += 1
            line += f" traj={'yes' if traj_seen <= len(traj_files) else 'NO'}"
        print(line)

    call_counts: dict[str, int] = {}
    for c in calls:
        p = str(c["persona"])
        call_counts[p] = call_counts.get(p, 0) + 1
    for persona, n_calls in sorted(call_counts.items()):
        n_resp = resp_counts.get(persona, 0)
        if n_resp < n_calls:
            warnings.append(
                f"{persona}: {n_calls} call(s) but only {n_resp} response "
                "body(ies) captured — response_bodies.ndjson is incomplete "
                "(rotated away, capture disabled, or a failed call)"
            )
    dev_calls_n = call_counts.get("dev", 0)
    if dev_calls_n and len(traj_files) < dev_calls_n:
        warnings.append(
            f"dev: {dev_calls_n} call(s) but only {len(traj_files)} trajectory "
            "file(s) under state/events/trajectories — the agent's reasoning "
            "trail is incomplete"
        )

    # 2. ledger vs result.json — the number every A/B is measured against.
    ledger_cost = round(sum(float(c["cost_usd"] or 0.0) for c in calls), 4)
    ledger_in = sum(int(c["tokens_in"] or 0) for c in calls)
    ledger_out = sum(int(c["tokens_out"] or 0) for c in calls)
    if result_valid:
        reported = result.get("cost_usd")
        if reported is None:
            failures.append("result.json has no cost_usd")
        elif abs(ledger_cost - float(reported)) > 0.005:
            failures.append(
                f"cost mismatch: ledger sums to ${ledger_cost} but result.json "
                f"reports ${reported} — the reported number is not the real spend"
            )
        for key, ledger_val in (("tokens_in", ledger_in), ("tokens_out", ledger_out)):
            reported_tok = result.get(key)
            if reported_tok is None:
                continue
            try:
                mismatch = int(reported_tok) != ledger_val
            except (TypeError, ValueError):
                mismatch = True  # an unparseable number is not the ledger's number
            if mismatch:
                failures.append(
                    f"{key} mismatch: ledger={ledger_val} result.json={reported_tok}"
                )

    # 3. reviewer prompt integrity. No prompt bodies at all is a failure when
    #    the ledger shows LLM calls were made — the trail is incomplete.
    body_files = list((state_root / "state" / "events").glob("prompt_bodies.ndjson*"))
    if not body_files:
        if calls:
            failures.append(
                "missing artifact: no prompt_bodies.ndjson under "
                f"{state_root / 'state' / 'events'} despite {len(calls)} persona call(s)"
            )
    else:
        marker_failures, reviewer_seen = _scan_prompt_bodies(state_root)
        failures.extend(marker_failures)
        # Coverage cross-check: the ledger is the ground truth for whether a
        # reviewer ran. Zero scanned reviewer prompts despite reviewer Run
        # rows means the bodies were rotated away or never captured — the
        # reviewer's input is unauditable, and silence must not read as clean.
        reviewer_calls = sum(1 for c in calls if c["persona"] == "reviewer")
        if reviewer_calls and reviewer_seen == 0:
            failures.append(
                f"ledger shows {reviewer_calls} reviewer call(s) but zero reviewer "
                "prompt bodies were scanned (rotated away or never captured) — "
                "reviewer input is unauditable"
            )

    # 4. first-dev fast-fail — the unrunnable-environment signature.
    dev_calls = [c for c in calls if c["persona"] == "dev"]
    if dev_calls:
        first = dev_calls[0]
        dur = first.get("duration_s")
        if not first.get("success") and dur is not None and float(dur) < _FAST_FAIL_S:
            failures.append(
                f"first dev execution failed in {dur}s (< {_FAST_FAIL_S}s): "
                "unrunnable-environment signature — the run never tested anything"
            )

    # 5. a recorded failed precheck is a failed run.
    pre = result.get("precheck") if isinstance(result.get("precheck"), dict) else None
    if pre is not None and not pre.get("collect_ok"):
        failures.append("result.json records a failed collect precheck")

    payload = {
        "instance_id": instance_id,
        "arm": arm,
        "audited_at": datetime.now(UTC).isoformat(),
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
        "persona_calls": calls,
        "ledger_cost_usd": ledger_cost,
        "ledger_tokens_in": ledger_in,
        "ledger_tokens_out": ledger_out,
        "result_cost_usd": result.get("cost_usd"),
    }
    out = run_dir / "audit.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if show_responses:
        _show_responses(state_root, responses)
    for w in warnings:
        print(f"AUDIT WARN: {w}")
    if failures:
        for f in failures:
            print(f"AUDIT FAIL: {f}")
        raise SystemExit(f"audit FAILED ({len(failures)} finding(s)) -> {out}")
    print(f"audit OK ({len(calls)} persona call(s), ${ledger_cost}) -> {out}")


# --------------------------------------------------------------------------- #
# report — gate precision and recall
# --------------------------------------------------------------------------- #


def report() -> None:
    rows: list[dict[str, Any]] = []
    for f in sorted(RUNS_DIR.glob("*/*/result.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(r, dict):
            continue
        # The audit gate. Every run must be fully auditable; a row whose
        # audit failed — or that was never audited at all (legacy runs
        # included) — must not be laundered into the headline number.
        # ``None`` = no audit.json (not audited); an unreadable audit.json is
        # a FAIL, never a pass.
        audit_path = f.parent / "audit.json"
        audit_ok: bool | None = None
        if audit_path.exists():
            try:
                audit_ok = json.loads(audit_path.read_text(encoding="utf-8")).get("ok") is True
            except (json.JSONDecodeError, OSError, AttributeError):
                audit_ok = False
        r["_audit_ok"] = audit_ok
        # Both run functions record ``error`` (None on a normal completion);
        # an oracle pass from a run that failed is flagged, not counted.
        r["_run_failed"] = bool(r.get("error"))
        rows.append(r)
    if not rows:
        raise SystemExit(f"no results under {RUNS_DIR}")

    lines = [
        "# SWE-bench Pro — externally graded",
        "",
        f"Generated {datetime.now(UTC).isoformat()}.",
        "",
        "`factory says` is the chain's OWN verdict — it reached `reviewer_done`, "
        "i.e. dev got its tests green and the reviewer approved. `oracle` is the "
        "hidden held-out suite.",
        "",
        "NOTE ON NAMING: the rates below are **chain-verdict** precision/recall, "
        "NOT merge-gate precision. This harness drives dev+review only; no merge "
        "gate runs. Of the six gates, only `tests-green` and `tests-meaningful` "
        "could even apply to a SWE-bench repo — `docs-current`, "
        "`acceptance-verified`, `smoke-green` and `canonical-paths-only` all "
        "require app capabilities these repos do not have. Calling this "
        "\"gate precision\" would overclaim.",
        "",
        "`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's "
        "2026-07-08 audit found ~30% of this suite's public tasks broken, so "
        "summing the two would read a broken harness as factory failure.",
        "",
        "| instance | arm | factory says | oracle | audit | outcome | tokens in | tokens out | wall s |",
        "|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for r in rows:
        g = r.get("grade") or {}
        oracle = g.get("oracle_resolved")
        audit_cell = "ok" if r["_audit_ok"] else ("—" if r["_audit_ok"] is None else "FAIL")
        lines.append(
            f"| {str(r.get('instance_id'))[:46]} | {r.get('arm')} "
            f"| {'green' if r.get('factory_says_green') else 'not green'} "
            f"| {'PASS' if oracle else ('?' if oracle is None else 'FAIL')} "
            f"| {audit_cell} "
            f"| {g.get('outcome', '—')} "
            f"| {r.get('tokens_in', '?'):,} | {r.get('tokens_out', '?'):,} "
            f"| {r.get('wall_clock_s', '—')} |"
        )

    for arm in sorted({str(r.get("arm")) for r in rows}):
        arm_rows = [
            r
            for r in rows
            if r.get("arm") == arm and (r.get("grade") or {}).get("oracle_resolved") is not None
        ]
        gradable = [
            r
            for r in arm_rows
            if not str((r.get("grade") or {}).get("outcome", "")).startswith("task_broken")
        ]
        # The audit gate: the headline counts ONLY rows whose run completed
        # normally AND whose audit passed. Everything else lands in a loud
        # bucket — an oracle pass with a failed (or absent) audit is not a
        # result, and silently laundering it into the resolve rate is exactly
        # the number-inflation this harness exists to prevent.
        valid = [r for r in gradable if r["_audit_ok"] is True and not r["_run_failed"]]
        valid_ids = {id(r) for r in valid}
        audit_failed = [r for r in gradable if r["_audit_ok"] is False]
        not_audited = [r for r in gradable if r["_audit_ok"] is None]
        run_failed = [r for r in gradable if r["_run_failed"]]
        excluded_passes = [
            r
            for r in gradable
            if (r.get("grade") or {}).get("oracle_resolved") and id(r) not in valid_ids
        ]
        said_green = [r for r in valid if r.get("factory_says_green")]
        oracle_pass = [r for r in valid if (r["grade"] or {}).get("oracle_resolved")]
        tp = [r for r in said_green if (r["grade"] or {}).get("oracle_resolved")]
        broken = len(arm_rows) - len(gradable)

        def _rate(num: int, den: int) -> str:
            return f"{num}/{den} = {num / den:.0%}" if den else "n/a (0 in denominator)"

        headline = f"- resolve rate: **{_rate(len(oracle_pass), len(valid))} audited-valid**"
        if excluded_passes:
            reasons = ", ".join(
                f"{str(r.get('instance_id'))[:46]}: "
                + ("run failed" if r["_run_failed"] else "")
                + (" + " if r["_run_failed"] and r["_audit_ok"] is not True else "")
                + (
                    ("audit failed" if r["_audit_ok"] is False else "not audited")
                    if r["_audit_ok"] is not True
                    else ""
                )
                for r in excluded_passes
            )
            headline += (
                f"; **{len(excluded_passes)} oracle-pass EXCLUDED** ({reasons})"
            )
        lines += [
            "",
            f"## {arm}",
            "",
            f"- graded instances: **{len(arm_rows)}** "
            f"({broken} excluded as `task_broken`, leaving {len(gradable)})",
            f"- audit gate: **{len(valid)} audited-valid** of {len(gradable)} gradable "
            f"(audit failed: {len(audit_failed)}, not audited: {len(not_audited)}, "
            f"run failed: {len(run_failed)})",
            headline,
            f"- chain-verdict precision (oracle passes | chain said green): "
            f"**{_rate(len(tp), len(said_green))}**",
            f"- chain-verdict recall (chain said green | oracle passes): "
            f"**{_rate(len(tp), len(oracle_pass))}**",
        ]
    n = len({r.get("instance_id") for r in rows})
    if n < 30:
        lines += [
            "",
            f"> **n={n} — preliminary.** Do not draw conclusions beyond "
            "\"the harness runs\". The MDE at this size is far wider than any "
            "difference worth acting on.",
        ]
    lines += [
        "",
        "> A factory number without the matched **bare-model** number beside it "
        "measures the MODEL, not the harness. See `PLAN.md` 1.4.",
    ]

    SWE_DIR.mkdir(parents=True, exist_ok=True)
    out = SWE_DIR / "results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    print("\n".join(lines))


# --------------------------------------------------------------------------- #
# run-all — the parallel sweep
# --------------------------------------------------------------------------- #
#
# Why SUBPROCESSES and not threads. Verified, not assumed — ``run_factory`` is
# not thread-safe, on three independent counts:
#
#   1. It sets ``os.environ["FACTORY_STATE_ROOT"]`` (line ~594). That is
#      PROCESS-global, and ``factory/manager/signals.py`` +
#      ``factory/observability/state_trace.py`` read it at call time to decide
#      where events land. Two in-process runs would race, and the loser writes
#      its synthetic telemetry into the other's root — or, once both have moved
#      on, into production ``state/``. That exact failure cost a prior session
#      a week (see the module docstring, constraint 1).
#   2. It mutates ``sys.path`` and then imports the chain.
#   3. ``factory/settings/loader.py`` keeps a module-global ``_CACHED`` dict of
#      loaded settings, and ``run_factory`` writes a DIFFERENT
#      ``factory_settings.yaml`` per bench root.
#
# So each unit of work is a fresh ``python bench/swebench_adapter.py run``
# child process. The pool below is a pool of SUPERVISORS: every thread does
# nothing but spawn a child, wait, and read its exit code. The unsafe work
# happens behind a process boundary, which is also what gives us free failure
# isolation (a segfault or an OOM kill is just a return code) and a real
# timeout (``subprocess.run(timeout=…)`` can actually kill a wedged run,
# whereas a thread cannot be interrupted).
#
# Child stdout/stderr is CAPTURED to a per-instance file, never inherited. That
# is what makes requirement 4 hold: no child can emit a partial line into our
# stdout, because no child shares our stdout.

_SWEEP_LOCK = threading.Lock()

# Conservative fallbacks, used only when there is no measured run to learn
# from. Grounded in the six factory-arm runs recorded in
# ``bench/swebench/results.md`` (2026-08-01): 560k–3.3M input tokens, 5k–47k
# output, 98–585 s wall clock. Priced at the verified Azure retail rate for
# ``azure/deepseek-v4-pro`` ($1.93/1M in, $3.83/1M out — see
# ``factory/providers/azure_foundry.py``) the median run is ~$2.70, taken here
# as $3.00 with NO credit for cache hits. Erring high on cost and LOW on
# duration both push the projected burn rate UP, which is the fail-safe
# direction for a guard whose job is to refuse.
_DEFAULT_COST_USD = {"factory": 3.00, "bare": 1.00}
_DEFAULT_HOURS = {"factory": 0.05, "bare": 0.05}  # 3 minutes — the fast end of measured

# Mirrors ``factory.settings.loader.CapsConfig``. Used when
# ``factory_settings.yaml`` is missing or unparseable: a guard that cannot read
# its own limits must assume the TIGHT ones, never none.
_FALLBACK_HOURLY_CAP = 2.0
_FALLBACK_DAILY_CAP = 10.0


def _emit(line: str) -> None:
    """One complete line, one lock, one write.

    Progress from N workers interleaves by definition; what must never happen
    is a half-written line. Building the whole string first and handing it to a
    single ``write`` under a lock is the cheapest way to guarantee that.
    """
    with _SWEEP_LOCK:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def selftest_working_instances(path: Path | None = None) -> set[str]:
    """Instances whose GOLD patch resolves, per ``bench/swebench/selftest.json``.

    A score computed over instances whose own gold patch does not resolve
    measures the harness, not the arm — OpenAI's 2026-07-08 audit puts that at
    ~30% of this suite, and our own selftest measured 6 of 10 usable. Only
    ``gold_resolves is True`` counts: ``None`` means "could not check" (image
    unavailable, no gold patch), which is not evidence of a working oracle.
    """
    p = path or (SWE_DIR / "selftest.json")
    if not p.exists():
        raise SystemExit(
            f"--only-working needs {p}, which does not exist. Run "
            "`selftest` first — it is the control that says which instances "
            "have a working oracle at all."
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{p} is not valid JSON: {exc}") from exc
    return {
        str(r["instance_id"])
        for r in data.get("results", [])
        if r.get("gold_resolves") is True
    }


def select_instances(
    manifest_ids: list[str],
    *,
    requested: list[str] | None = None,
    only_working: bool = False,
    working: set[str] | None = None,
) -> list[str]:
    """Resolve the sweep's work list. Pure, so it is testable without a manifest.

    Order is the manifest's (or the operator's, if ``--instances`` was given)
    and duplicates are dropped — two workers on one instance would write the
    same ``result.json`` and the last writer would silently win.
    """
    known = list(dict.fromkeys(manifest_ids))
    if requested:
        unknown = [i for i in requested if i not in set(known)]
        if unknown:
            raise SystemExit(
                f"not in the pinned manifest: {unknown}. Picking instances that "
                "were never pinned is choosing the sample after seeing results."
            )
        chosen = list(dict.fromkeys(requested))
    else:
        chosen = known

    if only_working:
        allowed = working or set()
        skipped = [i for i in chosen if i not in allowed]
        chosen = [i for i in chosen if i in allowed]
        if skipped:
            _emit(f"--only-working skipped {len(skipped)} instance(s) with no working oracle")
        if not chosen:
            raise SystemExit(
                "no instances left after --only-working. Every candidate's gold "
                "patch fails to resolve, so any score over them would measure "
                "the harness. Re-run `selftest`, or widen the manifest."
            )
    return chosen


def load_spend_caps(settings_path: Path | None = None) -> tuple[float, float]:
    """``(hourly_spend_usd, daily_spend_usd)`` from ``factory_settings.yaml``."""
    path = settings_path or (FACTORY_ROOT / "factory_settings.yaml")
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - unreadable settings must not mean "no cap"
        data = None
    caps = (data or {}).get("caps") or {} if isinstance(data, dict) else {}
    try:
        hourly = float(caps.get("hourly_spend_usd", _FALLBACK_HOURLY_CAP))
        daily = float(caps.get("daily_spend_usd", _FALLBACK_DAILY_CAP))
    except (TypeError, ValueError):
        hourly, daily = _FALLBACK_HOURLY_CAP, _FALLBACK_DAILY_CAP
    return hourly, daily


def estimate_instance_cost(arm: str, runs_dir: Path | None = None) -> tuple[float, float, str]:
    """``(usd_per_instance, hours_per_instance, source)`` for the spend guard.

    Prefers what previous CLEAN runs of this arm actually cost over a baked
    constant — gate on the real artifact, but only the REAL artifact: a run
    that died early leaves a recorded ``error`` and a tiny partial
    ``cost_usd``, and a max() over poisoned samples once projected a
    100-instance sweep at $5.00 against live caps (real cost ~$300). Only
    runs that completed normally (result.json written, no ``error``) are
    samples, and the estimate is FLOORED at the documented default unless
    there are >=2 such runs — one clean-but-cheap run is an anecdote and must
    never LOWER the guard.

    Uses the MAXIMUM cost and MINIMUM duration: both push the projected burn
    rate up, which is the fail-safe direction for a guard whose job is to
    refuse.
    """
    base = RUNS_DIR if runs_dir is None else runs_dir
    costs: list[float] = []
    hours: list[float] = []
    for f in sorted(base.glob(f"*/{arm}/result.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(r, dict) or r.get("error"):
            continue  # a failed run's partial spend is not a cost sample
        cost = float(r.get("cost_usd") or 0.0)
        wall = float(r.get("wall_clock_s") or 0.0)
        if cost > 0:
            costs.append(cost)
        if wall > 0:
            hours.append(wall / 3600.0)
    default_usd = _DEFAULT_COST_USD.get(arm, 3.00)
    if costs:
        usd = max(costs)
        floored = len(costs) < 2 and usd < default_usd
        if floored:
            usd = default_usd
        return (
            usd,
            max(min(hours, default=0.05), 0.01),
            f"measured over {len(costs)} clean prior {arm} run(s)"
            + (f", floored at the ${default_usd:,.2f} default" if floored else ""),
        )
    return (
        default_usd,
        _DEFAULT_HOURS.get(arm, 0.05),
        "default estimate (no clean prior runs to measure)",
    )


def spend_guard(
    *,
    n_instances: int,
    workers: int,
    usd_per_instance: float,
    hours_per_instance: float,
    hourly_cap: float,
    daily_cap: float,
) -> tuple[float, float, str | None]:
    """``(projected_total_usd, projected_peak_usd_per_hour, refusal_or_None)``.

    Pure arithmetic, so the refusal is testable without spending anything.

    The sweep runs ``ceil(n/workers)`` waves, so it lasts
    ``waves * hours_per_instance``. Peak hourly burn is the total divided by
    that duration — floored at one hour, because a sweep that finishes in six
    minutes cannot spend more in an *hour* than it spends in total. That floor
    is what keeps a small sweep from being refused for a burn rate it can never
    sustain, while a 100-instance sweep, which does sustain it, is caught.

    Bench spend is real money that is INVISIBLE to the chain's own enforcer:
    every run writes to an isolated ``FACTORY_STATE_ROOT``, so
    ``factory/settings/enforcer.py`` never sees these rows and will not throttle
    them. This function is the only thing standing between ``--workers 16`` and
    a four-figure afternoon.
    """
    waves = -(-n_instances // max(workers, 1))  # ceil
    duration_h = max(waves * hours_per_instance, 1.0)
    total = n_instances * usd_per_instance
    peak_hourly = total / duration_h

    if total > daily_cap:
        return (
            total,
            peak_hourly,
            f"projected sweep cost ${total:,.2f} exceeds caps.daily_spend_usd "
            f"${daily_cap:,.2f} ({n_instances} instances x ${usd_per_instance:,.2f}). "
            "Shrink the sweep with --instances/--only-working, or raise the cap "
            "deliberately in factory_settings.yaml.",
        )
    if peak_hourly > hourly_cap:
        per_worker = usd_per_instance / max(hours_per_instance, 0.01)
        fits = int(hourly_cap // per_worker) if per_worker > 0 else workers
        advice = (
            f"try --workers {fits}"
            if fits >= 1
            else (
                f"even ONE worker projects ${per_worker:,.2f}/h, so this is the "
                "instance cost, not the parallelism — lowering --workers will not help"
            )
        )
        return (
            total,
            peak_hourly,
            f"projected peak burn ${peak_hourly:,.2f}/h exceeds "
            f"caps.hourly_spend_usd ${hourly_cap:,.2f}/h "
            f"({workers} workers x ${per_worker:,.2f}/h each, {waves} wave(s), "
            f"${total:,.2f} total). {advice}, or shrink the sweep, or pass "
            "--force-over-cap if you are deliberately accepting the spend.",
        )
    return total, peak_hourly, None


_ABORT = threading.Event()
_LIVE_CHILDREN: set[subprocess.Popen[str]] = set()
_LIVE_LOCK = threading.Lock()


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    """SIGTERM the child's whole process GROUP, then SIGKILL what survives.

    The group, not the pid: a ``run`` child spawns git, pytest and an OpenHands
    agent, and killing only the parent orphans those — they keep running, and
    an orphaned dev run keeps calling the model, i.e. keeps spending. Hence
    ``start_new_session=True`` at spawn, which gives each child its own group
    to kill. (Docker containers are the one thing this cannot reach; they are
    owned by dockerd, not by us.)
    """
    if proc.poll() is not None:
        return
    for sig, grace in ((signal.SIGTERM, 10.0), (signal.SIGKILL, 5.0)):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                return
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def abort_all() -> int:
    """Stop the sweep: no new children, and kill every one already running.

    Returns how many were killed. Without this, ``Ctrl-C`` (or a killed parent)
    leaves N detached dev runs burning tokens with nobody watching — measured
    the hard way while building this: killing the parent left four ``run``
    children alive and they had to be hunted down by pid.
    """
    _ABORT.set()
    with _LIVE_LOCK:
        live = list(_LIVE_CHILDREN)
    for proc in live:
        _kill_tree(proc)
    return len(live)


def _bench_subprocess(argv: list[str], *, timeout_s: int, log_path: Path) -> tuple[int, str]:
    """Run one adapter subcommand as a child. Never raises for the child's sake.

    Returns ``(returncode, tail)``. A timeout is reported as returncode ``-9``
    and an abort as ``-2``, rather than as exceptions, so one wedged instance
    is a row in the summary instead of the end of the sweep.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if _ABORT.is_set():
        return -2, "aborted before start"
    try:
        proc = subprocess.Popen(  # noqa: S603
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,  # own process group, so _kill_tree can reach it
        )
    except (OSError, ValueError) as exc:
        log_path.write_text(f"SPAWN FAILED: {exc}\n", encoding="utf-8")
        return -1, f"{type(exc).__name__}: {exc}"

    with _LIVE_LOCK:
        _LIVE_CHILDREN.add(proc)
    # TOCTOU: ``abort_all`` snapshots ``_LIVE_CHILDREN`` once. A child spawned
    # between the pre-spawn ``_ABORT`` check and the registration above is
    # invisible to that snapshot — without this re-check its supervisor would
    # sit in ``communicate()`` for hours while the child keeps spending.
    if _ABORT.is_set():
        _kill_tree(proc)
        with _LIVE_LOCK:
            _LIVE_CHILDREN.discard(proc)
        log_path.write_text("aborted at spawn\n", encoding="utf-8")
        return -2, "aborted at spawn"
    rc: int
    try:
        out, _ = proc.communicate(timeout=timeout_s)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        out, _ = proc.communicate()
        out = (out or "") + f"\nTIMEOUT after {timeout_s}s: {' '.join(argv)}\n"
        rc = -9
    finally:
        with _LIVE_LOCK:
            _LIVE_CHILDREN.discard(proc)

    log_path.write_text(out or "", encoding="utf-8")
    if rc == -9:
        return rc, f"timeout after {timeout_s}s"
    if _ABORT.is_set() and rc != 0:
        return -2, "aborted mid-flight"
    body = (out or "").strip()
    return rc, body.splitlines()[-1][:300] if body else ""


def sweep_one(
    instance_id: str,
    *,
    arm: str,
    max_steps: int,
    run_timeout_s: int,
    grade_timeout_s: int,
) -> dict[str, Any]:
    """Run, GRADE, then AUDIT one instance, in this worker's own child processes.

    Grading happens here rather than in a second pass so an instance is graded
    the moment its run finishes — the pool slot is already held, the image is
    already warm in the local docker cache, and a sweep that dies halfway still
    leaves every completed instance fully graded.

    Auditing happens here for the same reason, plus a stronger one: every
    benchmark run must be fully auditable (the operator's standing
    requirement), and a sweep is exactly where nobody is looking at
    individual runs — so the audit gate has to be automatic, not a manual
    afterthought. A failed audit marks this row invalid (``audit_ok: false``).

    Every failure mode is caught and returned. The contract this function owes
    the pool is that it never raises.
    """
    started = time.monotonic()
    run_dir = _run_dir(instance_id, arm)
    record: dict[str, Any] = {
        "instance_id": instance_id,
        "arm": arm,
        "status": "ok",
        "error": None,
        "audit_ok": None,  # set after run+grade; None = the audit never ran
    }
    try:
        rc, tail = _bench_subprocess(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "run",
                "--instance",
                instance_id,
                "--arm",
                arm,
                "--max-steps",
                str(max_steps),
                "--timeout-s",
                str(run_timeout_s),
            ],
            # Slack over the run's own wall-clock cap for the clone and a
            # cold image pull, which happen before that cap starts counting.
            timeout_s=run_timeout_s + 1800,
            log_path=run_dir / "sweep-run.log",
        )
        record["run_rc"] = rc
        if rc == -2:
            record["status"] = "aborted"
            record["error"] = tail or "aborted"
            return _finish_record(record, run_dir, started)
        if rc != 0:
            record["status"] = "run_failed"
            record["error"] = tail or f"run exited {rc}"

        # Grade whatever the run produced. A run that failed LATE can still
        # have written a prediction; a run that failed early has not, and
        # grading would only add a confusing second error.
        #
        # SAFE ONLY BECAUSE OF ``_reset_run_artifacts``: both run functions
        # delete the previous run's prediction.diff/result.json at their TOP,
        # before any exit path, so a prediction.diff that exists after a
        # failed run is genuinely THIS run's late output — never a stale
        # leftover from an earlier run. If that reset ever moves below an
        # early exit, this branch starts grading dead predictions again.
        if (run_dir / "prediction.diff").exists():
            grc, gtail = _bench_subprocess(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "grade",
                    "--instance",
                    instance_id,
                    "--arm",
                    arm,
                    "--timeout-s",
                    str(grade_timeout_s),
                ],
                timeout_s=grade_timeout_s + 1800,
                log_path=run_dir / "sweep-grade.log",
            )
            record["grade_rc"] = grc
            if grc != 0 and record["status"] == "ok":
                record["status"] = "grade_failed"
                record["error"] = gtail or f"grade exited {grc}"
        elif record["status"] == "ok":
            record["status"] = "no_prediction"
            record["error"] = "run produced no prediction.diff"

        # Audit UNCONDITIONALLY after run+grade — failed runs included.
        # ``audit`` exits non-zero on ANY finding, and a missing artifact is a
        # finding (fail safe), so a run that produced nothing is marked
        # invalid here rather than silently averaged in. The audit reads only
        # local artifacts, hence the short fixed timeout.
        #
        # Drop any stale audit.json FIRST: if the run child failed to spawn,
        # ``_reset_run_artifacts`` never ran, and an audit child that crashes
        # before writing would leave a PREVIOUS run's file for
        # ``_audit_failure_reasons`` to read as this row's findings.
        (run_dir / "audit.json").unlink(missing_ok=True)
        arc, atail = _bench_subprocess(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "audit",
                "--instance",
                instance_id,
                "--arm",
                arm,
            ],
            timeout_s=600,
            log_path=run_dir / "sweep-audit.log",
        )
        record["audit_rc"] = arc
        if arc == 0:
            record["audit_ok"] = True
        elif arc == -2:
            record["audit_ok"] = None  # aborted before the audit could run
        else:
            record["audit_ok"] = False
            record["audit_failures"] = _audit_failure_reasons(run_dir, atail)
    except Exception as exc:  # noqa: BLE001 - one bad instance must not end the sweep
        record["status"] = "crashed"
        record["error"] = f"{type(exc).__name__}: {exc}"

    return _finish_record(record, run_dir, started)


def _audit_failure_reasons(run_dir: Path, tail: str) -> list[str]:
    """The audit child's findings, read from the ``audit.json`` it wrote.

    Falls back to the child's last output line when ``audit.json`` is missing
    or unreadable (the audit itself crashed) — an invalid row must always say
    WHY it is invalid.
    """
    try:
        data = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        failures = data.get("failures")
        if isinstance(failures, list) and failures:
            return [str(f) for f in failures]
    return [tail or "audit exited non-zero without writing audit.json"]


def _finish_record(
    record: dict[str, Any], run_dir: Path, started: float
) -> dict[str, Any]:
    """Fold whatever the child managed to write into the sweep's own record.

    Read on EVERY exit path, including the failures: a run that died after
    writing its result still has real tokens to account for, and dropping them
    would under-report spend.
    """
    result_path = run_dir / "result.json"
    result: dict[str, Any] = {}
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            result = {}
    g = result.get("grade") or {}
    record.update(
        {
            "final_state": result.get("final_state") or "—",
            "tokens_in": int(result.get("tokens_in") or 0),
            "tokens_out": int(result.get("tokens_out") or 0),
            "cost_usd": float(result.get("cost_usd") or 0.0),
            "factory_says_green": result.get("factory_says_green"),
            "oracle_resolved": g.get("oracle_resolved"),
            "outcome": g.get("outcome") or "—",
            "sweep_wall_s": round(time.monotonic() - started, 1),
        }
    )
    return record


def _progress_line(n: int, total: int, r: dict[str, Any]) -> str:
    oracle = r.get("oracle_resolved")
    mark = "PASS" if oracle else ("?" if oracle is None else "FAIL")
    audit_ok = r.get("audit_ok")
    audit_mark = "ok" if audit_ok else ("—" if audit_ok is None else "FAIL")
    status = "" if r["status"] == "ok" else f"  !{r['status']}: {str(r.get('error'))[:80]}"
    return (
        f"[{n:>3}/{total:<3}] {str(r['instance_id'])[:46]:<46} "
        f"{str(r['final_state']):<22} "
        f"in={r['tokens_in']:>9,} out={r['tokens_out']:>7,} "
        f"oracle={mark:<4} {str(r['outcome']):<24} "
        f"audit={audit_mark:<4} "
        f"{r['sweep_wall_s']:>7.1f}s{status}"
    )


def run_all(
    *,
    arm: str,
    workers: int,
    instances: list[str] | None,
    only_working: bool,
    max_steps: int,
    run_timeout_s: int,
    grade_timeout_s: int,
    force_over_cap: bool,
    dry_run: bool = False,
) -> None:
    manifest = _manifest()
    chosen = select_instances(
        [str(i["instance_id"]) for i in manifest["instances"]],
        requested=instances,
        only_working=only_working,
        working=selftest_working_instances() if only_working else None,
    )
    if not chosen:
        raise SystemExit("nothing to sweep: the pinned manifest is empty")
    workers = max(1, min(workers, len(chosen)))

    hourly_cap, daily_cap = load_spend_caps()
    usd, hours, source = estimate_instance_cost(arm)
    total, peak, refusal = spend_guard(
        n_instances=len(chosen),
        workers=workers,
        usd_per_instance=usd,
        hours_per_instance=hours,
        hourly_cap=hourly_cap,
        daily_cap=daily_cap,
    )
    _emit(
        f"sweep: arm={arm} instances={len(chosen)} workers={workers}\n"
        f"spend: ~${usd:,.2f}/instance ({source}); projected ${total:,.2f} total, "
        f"${peak:,.2f}/h peak vs caps ${hourly_cap:,.2f}/h, ${daily_cap:,.2f}/day"
    )
    if dry_run:
        # A PURE preview: no child spawned, no directory created, no file
        # written, no dollar spent. The repo has been bitten before by a
        # "dry-run" that quietly did real work (pm-sync, 2026-07-20), so this
        # path deliberately does nothing but print.
        if refusal and not force_over_cap:
            _emit(f"WOULD REFUSE TO START — {refusal}")
        elif refusal:
            _emit(f"would proceed OVER CAP (--force-over-cap) — {refusal}")
        _emit(
            f"dry-run: would run+grade+audit {len(chosen)} instance(s) "
            f"on {workers} worker(s):"
        )
        for i, iid in enumerate(chosen, 1):
            _emit(f"  [{i:>3}] run --instance {iid} --arm {arm} --max-steps {max_steps}")
            _emit(f"        then grade --instance {iid} --arm {arm}")
            _emit(f"        then audit --instance {iid} --arm {arm}")
        _emit("dry-run: nothing was executed and nothing was written.")
        return

    if refusal:
        if not force_over_cap:
            raise SystemExit(f"REFUSING TO START — {refusal}")
        _emit(f"WARNING: --force-over-cap set; proceeding over cap — {refusal}")

    started = time.monotonic()
    records: list[dict[str, Any]] = []
    stopped_reason: str | None = None
    notified: set[int] = set()
    _ABORT.clear()
    _emit(f"{'-' * 100}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                sweep_one,
                iid,
                arm=arm,
                max_steps=max_steps,
                run_timeout_s=run_timeout_s,
                grade_timeout_s=grade_timeout_s,
            ): iid
            for iid in chosen
        }
        recorded: set[concurrent.futures.Future[dict[str, Any]]] = set()
        try:
            for done in concurrent.futures.as_completed(futures):
                iid = futures[done]
                if done.cancelled():
                    continue  # blank-recorded in the drain below
                try:
                    rec = done.result()
                except Exception as exc:  # noqa: BLE001 - belt and braces; sweep_one swallows
                    rec = _blank_record(iid, arm, f"{type(exc).__name__}: {exc}")
                recorded.add(done)
                records.append(rec)
                _emit(_progress_line(len(records), len(chosen), rec))

                # MID-SWEEP ENFORCEMENT, on ACTUAL spend. The start-of-sweep
                # guard works from a projection, and a projection can be wrong
                # (it once said $5.00 for a sweep that cost ~$300). Actual
                # cost_usd summed over completed rows is the real artifact.
                # Residual window: rows still IN FLIGHT when the cap trips are
                # allowed to finish, so the overshoot is bounded by
                # workers x the true per-instance cost.
                actual = sum(float(r.get("cost_usd") or 0.0) for r in records)
                # Operator notification thresholds ($50/$75/$100 — CLAUDE.md
                # guardrail), each announced once, on real accumulated spend.
                for threshold in (50, 75, 100):
                    if actual >= threshold and threshold not in notified:
                        notified.add(threshold)
                        _emit(
                            f"NOTICE: accumulated sweep spend ${actual:,.2f} has "
                            f"crossed the ${threshold} operator notification threshold."
                        )
                if stopped_reason is None and not force_over_cap:
                    elapsed_h = (time.monotonic() - started) / 3600.0
                    # Same 1-hour floor as the projection guard: within the
                    # first hour the hourly cap bounds the total so far.
                    allowed = min(daily_cap, hourly_cap * max(elapsed_h, 1.0))
                    if actual > allowed:
                        stopped_reason = (
                            f"spend cap: actual ${actual:,.2f} breached the "
                            f"${allowed:,.2f} allowance (caps ${hourly_cap:,.2f}/h, "
                            f"${daily_cap:,.2f}/day)"
                        )
                        for fut in futures:
                            fut.cancel()  # queued rows; in-flight ones finish
                        _emit(
                            f"SPEND CAP — {stopped_reason}; no new instances will "
                            "start, in-flight ones are allowed to finish"
                        )
        except KeyboardInterrupt:
            # Ctrl-C must actually STOP the spend. Letting the executor's
            # shutdown drain normally would keep every in-flight dev run going
            # for up to its full wall-clock cap, unattended.
            killed = abort_all()
            for fut in futures:
                fut.cancel()
            stopped_reason = stopped_reason or "interrupted (Ctrl-C)"
            _emit(
                f"\nINTERRUPTED — killed {killed} in-flight child process(es); "
                "writing a partial summary"
            )

    # The pool has shut down, so every future is now finished or cancelled.
    # Drain the ones the loop never recorded: an interrupt abandons in-flight
    # and just-dequeued rows, and their spend is REAL — dropping them silently
    # under-reports the sweep's cost.
    for fut, iid in futures.items():
        if fut in recorded:
            continue
        if fut.cancelled():
            reason = "cancelled before start"
            if stopped_reason:
                reason += f" ({stopped_reason})"
            records.append(_blank_record(iid, arm, reason, status="aborted"))
            continue
        try:
            records.append(fut.result(timeout=0))
        except BaseException as exc:  # noqa: BLE001 - KeyboardInterrupt included
            records.append(
                _blank_record(iid, arm, f"{type(exc).__name__}: {exc}", status="aborted")
            )

    records.sort(key=lambda r: str(r["instance_id"]))
    summary = _sweep_summary(
        records,
        arm=arm,
        workers=workers,
        wall_s=time.monotonic() - started,
        stopped_reason=stopped_reason,
    )
    out = SWE_DIR / f"sweep-{arm}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _emit(_render_summary(summary) + f"\nwrote {out}\nnext: `report`")
    # Non-zero exits, AFTER the summary is written (it is the evidence):
    # 1. a spend-cap stop is an incomplete sweep, whatever its rows say;
    # 2. a sweep with ZERO audited-valid rows produced nothing reportable —
    #    `not any(True)` rather than `all(False)`, because a single crashed
    #    row (audit_ok null) must not launder an otherwise all-invalid sweep
    #    into rc=0.
    if stopped_reason and stopped_reason.startswith("spend cap"):
        raise SystemExit(f"sweep stopped early — {stopped_reason} (see {out})")
    if records and not any(r.get("audit_ok") is True for r in records):
        raise SystemExit(
            f"sweep produced NO audited-valid rows (see {out}). "
            "An unauditable run is an invalid run."
        )


def _blank_record(
    instance_id: str, arm: str, error: str, *, status: str = "crashed"
) -> dict[str, Any]:
    return {
        "instance_id": instance_id,
        "arm": arm,
        "status": status,
        "error": error,
        "final_state": "—",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "factory_says_green": None,
        "oracle_resolved": None,
        "outcome": "—",
        "audit_ok": None,
        "sweep_wall_s": 0.0,
    }


def _sweep_summary(
    records: list[dict[str, Any]],
    *,
    arm: str,
    workers: int,
    wall_s: float,
    stopped_reason: str | None = None,
) -> dict[str, Any]:
    outcomes: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for r in records:
        outcomes[str(r.get("outcome"))] = outcomes.get(str(r.get("outcome")), 0) + 1
        statuses[str(r.get("status"))] = statuses.get(str(r.get("status")), 0) + 1
    gradable = [
        r
        for r in records
        if r.get("oracle_resolved") is not None
        and not str(r.get("outcome") or "").startswith("task_broken")
    ]
    # DELIBERATE: the headline ``resolved`` counts only rows that are clean
    # end-to-end — run ok AND audit ok. An oracle pass produced by a run that
    # failed late, or by a run whose audit found the trail invalid, is real
    # information but not a trustworthy result: it stays VISIBLE in its own
    # flagged counter instead of being silently conflated into the number a
    # comparison would be built on.
    resolved_clean = sum(
        1
        for r in gradable
        if r.get("oracle_resolved") and r.get("status") == "ok" and r.get("audit_ok") is True
    )
    resolved_run_failed = sum(
        1 for r in gradable if r.get("oracle_resolved") and r.get("status") != "ok"
    )
    resolved_audit_failed = sum(
        1
        for r in gradable
        if r.get("oracle_resolved")
        and r.get("status") == "ok"
        and r.get("audit_ok") is not True
    )
    return {
        "arm": arm,
        "workers": workers,
        "finished_at": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(wall_s, 1),
        "stopped_reason": stopped_reason,
        "instances": len(records),
        "ok": statuses.get("ok", 0),
        "failed": len(records) - statuses.get("ok", 0),
        "statuses": statuses,
        "outcomes": outcomes,
        "audited_valid": sum(1 for r in records if r.get("audit_ok") is True),
        "audit_failed": sum(1 for r in records if r.get("audit_ok") is False),
        "not_audited": sum(1 for r in records if r.get("audit_ok") is None),
        "resolved": resolved_clean,
        "resolved_but_run_failed": resolved_run_failed,
        "resolved_but_audit_failed": resolved_audit_failed,
        "gradable": len(gradable),
        "tokens_in": sum(int(r.get("tokens_in") or 0) for r in records),
        "tokens_out": sum(int(r.get("tokens_out") or 0) for r in records),
        "cost_usd": round(sum(float(r.get("cost_usd") or 0.0) for r in records), 4),
        "results": records,
    }


def _render_summary(s: dict[str, Any]) -> str:
    flagged = []
    if s.get("resolved_but_run_failed"):
        flagged.append(f"+{s['resolved_but_run_failed']} resolved but run FAILED")
    if s.get("resolved_but_audit_failed"):
        flagged.append(f"+{s['resolved_but_audit_failed']} resolved but audit FAILED")
    lines = [
        "-" * 100,
        f"sweep done: {s['instances']} instance(s) in {s['wall_clock_s']}s "
        f"on {s['workers']} worker(s) — {s['ok']} ok, {s['failed']} failed",
        f"  tokens: in={s['tokens_in']:,} out={s['tokens_out']:,}  "
        f"cost=${s['cost_usd']:,.2f} (derived-from-price-table)",
        f"  oracle: {s['resolved']}/{s['gradable']} resolved clean"
        + (" (task_broken excluded)" if s["gradable"] < s["instances"] else "")
        + (" — flagged, NOT counted: " + ", ".join(flagged) if flagged else ""),
        f"  audit: {s['audited_valid']} valid, {s['audit_failed']} failed, "
        f"{s['not_audited']} not audited",
        "  outcomes: "
        + ", ".join(f"{k}={v}" for k, v in sorted(s["outcomes"].items()))
        + "",
    ]
    if s.get("stopped_reason"):
        lines.insert(1, f"  STOPPED EARLY — {s['stopped_reason']}")
    failures = [r for r in s["results"] if r.get("status") != "ok"]
    if failures:
        lines.append("  failures (isolated — the sweep continued):")
        lines += [
            f"    {str(r['instance_id'])[:46]:<46} {r['status']}: {str(r.get('error'))[:100]}"
            for r in failures
        ]
    invalid = [r for r in s["results"] if r.get("audit_ok") is False]
    if invalid:
        lines.append("  audit failures (rows are INVALID — do not report them):")
        lines += [
            f"    {str(r['instance_id'])[:46]:<46} "
            + "; ".join(str(f) for f in (r.get("audit_failures") or ["unknown"]))[:120]
            for r in invalid
        ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #


def _load_env() -> None:
    """Load ``.env`` from this checkout, falling back to the MAIN checkout.

    ``.env`` is gitignored, so it does not exist in a git worktree — and this
    adapter is naturally developed in one. Without the fallback every model
    call dies with "No API key available", which reads as a credential problem
    rather than a path problem.
    """
    from dotenv import load_dotenv

    candidates = [FACTORY_ROOT / ".env"]
    try:
        common = subprocess.run(
            ["git", "-C", str(FACTORY_ROOT), "rev-parse", "--path-format=absolute",
             "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if common:
            candidates.append(Path(common).parent / ".env")
    except (subprocess.CalledProcessError, OSError):
        pass
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)


def main() -> None:
    _load_env()

    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="pin a manifest (do this BEFORE any run)")
    p.add_argument("--language", default="python")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--seed", type=int, required=True, help="published RNG seed")

    p = sub.add_parser("run", help="drive an arm over one instance")
    p.add_argument("--instance", required=True)
    p.add_argument(
        "--arm",
        default="factory",
        choices=["factory", "bare"],
        help="'bare' is the matched minimal scaffold on the SAME Azure models "
             "(PLAN.md 1.4). A factory number without it measures the model.",
    )
    p.add_argument("--max-steps", type=int, default=16)
    p.add_argument("--timeout-s", type=int, default=5400)

    p = sub.add_parser(
        "run-all",
        help="parallel sweep: run + grade many instances across a worker pool",
    )
    p.add_argument("--arm", default="factory", choices=["factory", "bare"])
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--instances",
        default=None,
        help="comma-separated subset; omit for every pinned instance",
    )
    p.add_argument(
        "--only-working",
        action="store_true",
        help="restrict to instances whose GOLD patch resolves (selftest.json). "
             "A score over broken instances measures the harness.",
    )
    p.add_argument("--max-steps", type=int, default=16)
    p.add_argument("--timeout-s", type=int, default=5400, help="per-instance run cap")
    p.add_argument("--grade-timeout-s", type=int, default=3600)
    p.add_argument(
        "--force-over-cap",
        action="store_true",
        help="proceed even though the projected spend exceeds a cap in "
             "factory_settings.yaml. Loud, deliberate, never the default.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan and the projected spend, then stop. A PURE "
             "preview: spawns nothing, writes nothing, costs nothing.",
    )

    p = sub.add_parser("grade", help="run the hidden oracle in the official image")
    p.add_argument("--instance", required=True)
    p.add_argument("--arm", default="factory", choices=["factory", "bare"])
    p.add_argument("--timeout-s", type=int, default=3600)

    p = sub.add_parser(
        "selftest", help="grade the GOLD patch — validates the oracle itself"
    )
    p.add_argument("--instance", default=None, help="omit to check every pinned instance")
    p.add_argument("--timeout-s", type=int, default=3600)

    p = sub.add_parser(
        "audit", help="verify one run's ledger, prompts and reported numbers"
    )
    p.add_argument("--instance", required=True)
    p.add_argument("--arm", default="factory", choices=["factory", "bare"])
    p.add_argument(
        "--show-responses",
        action="store_true",
        help="also print the reviewer's response text and the last few dev "
             "assistant messages from the captured trajectory",
    )

    sub.add_parser("report")

    args = ap.parse_args()
    if args.cmd == "fetch":
        fetch(language=args.language, limit=args.limit, seed=args.seed)
    elif args.cmd == "run":
        runner = run_bare if args.arm == "bare" else run_factory
        runner(args.instance, max_steps=args.max_steps, timeout_s=args.timeout_s)
    elif args.cmd == "run-all":
        run_all(
            arm=args.arm,
            workers=args.workers,
            instances=(
                [s.strip() for s in args.instances.split(",") if s.strip()]
                if args.instances
                else None
            ),
            only_working=args.only_working,
            max_steps=args.max_steps,
            run_timeout_s=args.timeout_s,
            grade_timeout_s=args.grade_timeout_s,
            force_over_cap=args.force_over_cap,
            dry_run=args.dry_run,
        )
    elif args.cmd == "grade":
        grade(args.instance, args.arm, timeout_s=args.timeout_s)
    elif args.cmd == "selftest":
        selftest(args.instance, timeout_s=args.timeout_s)
    elif args.cmd == "audit":
        audit(args.instance, args.arm, show_responses=args.show_responses)
    elif args.cmd == "report":
        report()


if __name__ == "__main__":
    main()
