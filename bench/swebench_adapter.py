"""SWE-bench adapter — an externally-graded number for the factory.

PLAN.md Phase 1. The existing ``bench/bench.py`` grades the factory against
sacrifice's own backlog using sacrifice's own gates: the factory writes the
code AND owns the tests that say the code works. That measures convergence,
not correctness. This adapter swaps in a HIDDEN oracle the factory never sees.

Datasets are PROFILES (see ``PROFILES``): ``swe-rebench``
(nebius/SWE-rebench-leaderboard — execution-validated upstream, monthly
post-cutoff splits, gold patch and docker image in-row) is primary;
``swebench-pro`` is frozen after OpenAI's 2026-07-08 audit found ~30% of its
tasks broken. ``fetch --dataset`` selects the profile ONCE and pins it in the
manifest; every later command reads it back from there. Only harness plumbing
varies by profile — the factory chain (handlers, state machine, personas,
worktrees) runs identically, exactly as it does in the wild.

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

``grade_parse_failed`` is the same idea one level down: when THIS harness cannot
read pytest's per-node report, the row says nothing about the arm, so it is
excluded from every rate instead of being counted as an unresolved attempt. A
parse failure reported as an arm failure is how one harness defect becomes a
uniform 0% across every arm — a number that looks like a finding and is a bug.

The factory arm needs a WORKING test environment
-----------------------------------------------
A bare clone has no dependencies, so ``pytest`` dies with
``ModuleNotFoundError`` and dev — whose whole mechanism is run-until-green —
blocks with an empty diff. The app's ``test_command`` therefore runs inside the
instance's own image with the working tree mounted over the profile's workdir
(``instance_test_command``). Measured on ``ansible__ansible-9a21e2477...``:
empty diff after 870k tokens before, ``reviewer_done`` with a real patch in
104s / 355k tokens after.

Three arms
----------
* ``factory`` — the chain's dev+review handlers (azure/deepseek-v4-pro dev,
  azure/gpt-5.4 reviewer, per ``routes.yaml``).
* ``bare`` — the SAME weights with a minimal bash-loop scaffold; the harness
  delta is factory minus bare.
* ``claude`` — the local Claude Code CLI, headless, hermetically configured
  (see ``run_claude``); the frontier-tool comparator. Its spend bills the
  operator's ANTHROPIC subscription/API, not the Azure ledger, and its cost
  numbers are the CLI's own report (``cost_source: "claude-cli-reported"``).

Usage (from the factory root):
  uv run python bench/swebench_adapter.py fetch --dataset swe-rebench \
      --language python --limit 20 --seed 20260802
  uv run python bench/swebench_adapter.py selftest            # validate the ORACLE first
  uv run python bench/swebench_adapter.py run   --instance <id> --arm bare|factory|claude
  uv run python bench/swebench_adapter.py grade --instance <id> --arm bare|factory|claude
  uv run python bench/swebench_adapter.py audit --instance <id> --arm bare|factory|claude
  uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 \
      --only-working --dry-run          # ALWAYS preview: a sweep costs real money
  uv run python bench/swebench_adapter.py run-all --arm factory --workers 4 --only-working
  uv run python bench/swebench_adapter.py report
  uv run python bench/swebench_adapter.py report \
      --from-archive bench/swebench/results-archive/<ts>   # re-derive, no live runs

``report`` is artifact-backed (PLAN 1.5): it snapshots every consumed
``result.json`` / ``audit.json`` / ``prediction.diff`` into a dated
``bench/swebench/results-archive/<generated-at>/`` dir (committed — unlike
``runs/``, which the next sweep wipes) and REFUSES any row whose artifacts
are missing, naming it in the output instead of silently dropping it.
``--from-archive`` re-derives the committed table byte-for-byte from a
snapshot alone.

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
import contextlib
import difflib
import hashlib
import json
import math
import os
import random
import re
import secrets
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

FACTORY_ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = FACTORY_ROOT / "bench"
SWE_DIR = BENCH_DIR / "swebench"
RUNS_DIR = SWE_DIR / "runs"
MANIFEST_PATH = SWE_DIR / "manifest.json"
# Committed evidence snapshots — one dated dir per ``report`` run, holding the
# exact artifacts every published row was derived from (PLAN 1.5). Unlike
# ``runs/`` (gitignored scratch that ``_reset_run_artifacts`` legitimately
# wipes on the next sweep), an archive is immutable once committed: re-running
# ``report --from-archive <dir>`` must re-derive the published table from it
# with no live runs dir at all.
RESULTS_ARCHIVE_DIR = SWE_DIR / "results-archive"
# The gold-patch control's own logs. ``runs/`` is gitignored and
# ``_reset_run_artifacts`` legitimately wipes it, so 0 of the 19 published
# swe-rebench instances kept the log that certified their oracle. The control
# is the whole argument for trusting a number; its evidence has to survive.
SELFTEST_LOG_DIR = SWE_DIR / "selftest-logs"

_ROWS_URL = "https://datasets-server.huggingface.co/rows"

# Fake issue numbers far from production so a bench story can never collide
# with a real worktree branch (which is named from the real issue number).
SWE_ISSUE_BASE = 95000


# --------------------------------------------------------------------------- #
# arm isolation — nothing the arm can WALK TO may carry the answer
# --------------------------------------------------------------------------- #
#
# Every arm executes on this host filesystem, so the working tree's ANCESTRY is
# part of the threat model. It was not: the factory arm's dev agent ran with
# cwd ``bench/swebench/runs/<id>/factory/root/state/worktrees/<name>/`` — six
# ``..`` from ``oracle.json.z`` and ``manifest.json``, three from the OTHER
# arms' ``grade.log`` (which lists every hidden test id) and their
# ``result.json`` (which lists the gold patch's files). This FIRED: four
# factory rows in ``results-archive/2026-08-03T02-21-23.249790Z`` are
# ``ok: false`` on "own run's oracle-bearing subdir runs/…/bare".
#
# Two prepared trees were worse than reachable, they were pre-decoded: ``grade``
# applied the ORACLE TEST PATCH into ``runs/<id>/<arm>/grade-repo/`` and
# ``selftest`` applied the GOLD PATCH into ``runs/<id>/selftest/repo/``, both
# on the host, both left behind for the next arm to read in plaintext.
#
# So every live working tree now lives under a scratch root OUTSIDE the repo,
# and only finished artifacts (result.json, prediction.diff, grade.log, the
# audit trail) are copied back into ``bench/swebench/runs/<id>/<arm>/`` after
# the arm has stopped running. ``assert_workspace_isolated`` is the invariant,
# checked at run time: no ancestor of the workspace may contain oracle
# material. It fails CLOSED — a workspace it cannot clear refuses the run.

# Basenames that carry answer material. An ancestor directory holding any of
# these is disqualifying. ``manifest.json`` is deliberately absent: target
# repos legitimately ship one (web-app manifests) and the pinned manifest is
# already covered by the ``SWE_DIR`` ancestry check below.
_ORACLE_BEARING_NAMES = frozenset(
    {
        "oracle.json.z",
        "selftest.json",
        "grade.log",
        "grade-nodes.log",
        "selftest.log",
        "sweep-grade.log",
    }
)


def _work_root() -> Path:
    """Scratch root for every live working tree, outside the repo.

    ``SWEBENCH_WORK_ROOT`` overrides it (tests, and an operator who wants the
    trees on a different disk). Default: ``$XDG_CACHE_HOME/swebench-work``.
    """
    override = os.environ.get("SWEBENCH_WORK_ROOT")
    if override:
        return Path(override).expanduser()
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    return base / "swebench-work"


def _work_dir(instance_id: str, arm: str, *, fresh: bool = False) -> Path:
    """The scratch working directory for one (instance, arm).

    Flat ``<instance>__<arm>`` rather than nested ``<instance>/<arm>`` on
    purpose: a nested layout makes every OTHER arm of the same instance a
    sibling one ``..`` away, which is the shape that leaked in the first place.
    """
    d = _work_root() / f"{instance_id}__{arm}"
    if fresh:
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _prepared_tree_dir(prefix: str) -> Path:
    """A fresh, UNGUESSABLE directory for a tree that will hold oracle material.

    ``grade`` applies the oracle test patch into the tree it mounts and
    ``selftest`` applies the gold patch into its own, so both are the answer in
    plaintext on the host filesystem. They used to sit at
    ``runs/<id>/<arm>/grade-repo`` and ``runs/<id>/selftest/repo`` — stable,
    guessable paths inside the tree every other arm walks past. Now: a
    ``mkdtemp`` suffix under the scratch root (so an arm cannot guess a sibling
    even if it goes looking), deleted by the caller the moment grading ends.
    """
    base = _work_root() / "_prepared"
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(base)))


def _grade_mount_dir(instance_id: str, arm: str) -> Path:
    """Where ``grade`` prepares the clone it mounts into the image."""
    return _prepared_tree_dir(f"grade-{instance_id[:40]}-{arm}-") / "repo"


def _selftest_mount_dir(instance_id: str) -> Path:
    """Where ``selftest`` prepares the clone it mounts. Holds the GOLD patch."""
    return _prepared_tree_dir(f"selftest-{instance_id[:40]}-") / "repo"


def assert_workspace_isolated(path: Path) -> None:
    """Refuse unless the workspace's ANCESTOR CHAIN is clear of oracle material.

    Fail CLOSED, and deliberately structural rather than a denylist of known
    leaks: the check is "walk up from the agent's cwd and see what is there",
    which is exactly what an arm looking for the answer would do.

    Scope, stated honestly: this bounds the walk at the scratch root. Nothing
    can make the oracle store unreachable from an arbitrary absolute path on a
    shared host — every arm's shell runs on this filesystem, so ``ls ~`` finds
    the repo no matter where the workspace is. What IS achievable, and what was
    missing, is that the answer must not be somewhere a plain ``cd ..; ls``
    lands on. Above the scratch root is the operator's own filesystem, not
    harness data, so a stray ``grade.log`` in ``~/.cache`` is not a finding —
    flagging it would make a detector that blocks every run, which is not the
    same thing as failing safe. Exploration BEYOND the chain is the
    oracle-probe scan's job (``_scan_oracle_probes``).
    """
    resolved = Path(path).resolve()
    swe = SWE_DIR.resolve()
    stop = _work_root().resolve()
    if resolved == swe or swe in resolved.parents:
        raise SystemExit(
            f"workspace {path} is inside the harness directory {SWE_DIR} — the "
            "oracle store, the pinned manifest and every other arm's grade log "
            "are reachable from the agent's shell. Refusing to run; set "
            "SWEBENCH_WORK_ROOT to a path outside the repo."
        )
    for anc in (resolved, *resolved.parents):
        if anc.is_dir():
            try:
                names = {p.name for p in anc.iterdir()}
            except OSError:
                names = set()
            leaks = sorted(names & _ORACLE_BEARING_NAMES)
            if leaks:
                raise SystemExit(
                    f"workspace {path} has an ancestor {anc} holding oracle "
                    f"material {leaks} — it is reachable from the agent's "
                    "shell. Refusing to run."
                )
        if anc == stop:
            return


def _copy_audit_trail(src_state: Path, dest_state: Path) -> None:
    """Copy a finished run's audit trail back into its committed run dir.

    ``worktrees/`` is excluded: it is a full clone per story (hundreds of MB)
    and nothing in ``audit`` reads it. Everything ``audit`` DOES read —
    ``state/factory.db``, ``state/events/**`` (prompt bodies, response bodies,
    trajectories), ``state/logs/**`` — comes across, so the on-disk layout
    ``audit`` sees is byte-for-byte what it saw before the working tree moved.
    """
    if not src_state.is_dir():
        return
    dest_state.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(dest_state, ignore_errors=True)
    shutil.copytree(
        src_state,
        dest_state,
        ignore=shutil.ignore_patterns("worktrees", "*.sock"),
        symlinks=True,
        dirs_exist_ok=True,
    )


# --------------------------------------------------------------------------- #
# dataset profiles — everything dataset-specific lives HERE, nowhere else
# --------------------------------------------------------------------------- #
#
# The harness supports more than one upstream dataset, but a RUN never mixes
# them: ``fetch --dataset <name>`` selects a profile and persists its name in
# the manifest (and in every pinned instance), and every later command —
# run, grade, selftest, audit, report — reads the profile back FROM the
# manifest. There is deliberately no ``--dataset`` flag anywhere but fetch.
#
# ``swebench-pro`` is FROZEN: OpenAI's 2026-07-08 audit found ~30% of its
# public tasks broken (our own selftest measured 6/10 usable), no fixed
# release or broken-ID list exists, and the selftest is structurally blind to
# the dominant failure class (overly-strict hidden tests pass a gold-patch
# control by construction). Existing Pro manifests, run dirs and archives must
# keep loading and rendering — but do not extend the profile.
#
# ``swe-rebench`` (nebius/SWE-rebench-leaderboard) is the primary dataset:
# every instance is execution-validated upstream, contamination is controlled
# via monthly post-cutoff splits (``created_at``), the gold patch ships in-row
# (no rate-limited HF lookup at selftest/grade time), and per-instance docker
# images come verbatim in the row. Schema verified against the live rows API
# on 2026-08-02: ``instance_id, repo, base_commit, patch, test_patch,
# problem_statement, created_at, install_config, FAIL_TO_PASS, PASS_TO_PASS
# (uppercase, real JSON lists), docker_image, image_name`` — 860 rows in the
# ``test`` split (the union of the monthly splits), zero truncated cells.


class DatasetProfile(NamedTuple):
    """Environment plumbing for one upstream dataset.

    Only the HARNESS varies by profile — fetch, docker image selection,
    container layout, test-command derivation, gold-patch sourcing, grading
    setup. The factory chain itself (handlers, state machine, personas,
    worktrees) is identical across profiles by design: the benchmark must
    exercise the factory exactly as it runs in the wild.

    (A NamedTuple, not a dataclass: this module is exec'd from a file path
    without a ``sys.modules`` entry in child processes, where the dataclass
    machinery cannot resolve ``from __future__ import annotations`` strings.)
    """

    name: str
    title: str                 # report heading
    dataset: str               # HuggingFace dataset id
    split: str                 # rows-API split the pool is read from
    pool_cap: int              # pagination hard stop (pages of 100)
    container_workdir: str     # where the image keeps the repo; also the mount target
    env_setup: str             # shell prefix that puts the test env on PATH ("" = none)
    image_template: str | None # image ref from a tag ({tag}); None = in-row docker_image
    gold_in_row: bool          # gold patch pinned into the manifest at fetch time


PROFILES: dict[str, DatasetProfile] = {
    "swebench-pro": DatasetProfile(
        name="swebench-pro",
        title="SWE-bench Pro",
        dataset="ScaleAI/SWE-bench_Pro",
        split="test",
        pool_cap=800,
        container_workdir="/app",
        env_setup="",
        image_template="jefzda/sweap-images:{tag}",
        gold_in_row=False,
    ),
    "swe-rebench": DatasetProfile(
        name="swe-rebench",
        title="SWE-rebench",
        dataset="nebius/SWE-rebench-leaderboard",
        split="test",
        pool_cap=5000,
        container_workdir="/testbed",
        # The images ship a conda env; a non-root login shell (the factory arm
        # runs containers as the invoking uid with HOME=/tmp) does NOT inherit
        # it, so activate explicitly. Verified against a live image 2026-08-02.
        env_setup="source /opt/conda/bin/activate testbed && ",
        image_template=None,
        gold_in_row=True,
    ),
}

_DEFAULT_PROFILE = "swebench-pro"  # what a pre-profile manifest means

# DeepSeek-V4 Pro's training cutoff is UNDOCUMENTED (preview released
# 2026-04-24; neither the release notes nor the model card state a data
# cutoff), so the pilot uses 2026-01-01 as a conservative stand-in and says
# so. Instances created after this date land in the manifest; ones at or
# before it are filtered out at fetch time.
_REBENCH_DEFAULT_CUTOFF = "2026-01-01"


def _profile_of(inst_or_manifest: dict[str, Any]) -> DatasetProfile:
    """The profile a pinned instance (or manifest) was fetched under.

    A missing key means the artifact predates profiles, i.e. SWE-bench Pro —
    old manifests and old run dirs must keep loading (frozen, not dropped).
    An unknown name is a hard error, never a silent fallback: grading a
    rebench instance with Pro plumbing would produce a confident wrong number.
    """
    name = str(inst_or_manifest.get("profile") or _DEFAULT_PROFILE)
    if name not in PROFILES:
        raise SystemExit(
            f"unknown dataset profile {name!r} (known: {sorted(PROFILES)}). "
            "The manifest names a profile this adapter version does not have."
        )
    return PROFILES[name]


def _image_for(inst: dict[str, Any]) -> str:
    """The instance's official docker image, profile-aware.

    swe-rebench rows carry the full image ref verbatim (``docker_image``),
    which fetch resolves to an immutable ``repo@sha256:…`` digest
    (``docker_image_digest`` — preferred, because upstream tags are mutable
    and a drifted image invalidates what the selftest certified). Pro
    manifests carry only ``dockerhub_tag`` and the ref is templated. A
    manifest entry that supports none of these is a hard error — grading in
    the wrong image measures nothing.
    """
    digest = inst.get("docker_image_digest")
    if digest:
        return str(digest)
    image = inst.get("docker_image")
    if image:
        return str(image)
    profile = _profile_of(inst)
    if profile.image_template and inst.get("dockerhub_tag"):
        return profile.image_template.format(tag=inst["dockerhub_tag"])
    raise SystemExit(
        f"instance {inst.get('instance_id')!r} has neither docker_image nor a "
        f"dockerhub_tag usable with profile {profile.name!r}"
    )


# --------------------------------------------------------------------------- #
# the oracle store — answer material must not be greppable from the manifest
# --------------------------------------------------------------------------- #
#
# Every arm executes on THIS host filesystem (OpenHands LocalWorkspace; the
# bare arm's bash loop; the claude arm's CLI tools), so anything the harness
# stores in plaintext is one
# ``grep -r <instance_id>`` away from the arm under test. The gold patch, the
# test patch and the hidden test ids therefore live OUTSIDE the manifest, in
# ``oracle.json.z`` — zlib-compressed, base64-wrapped JSON. That defeats
# text-scavenging (grep, ripgrep, ctags, naive cat), which is the actual
# threat model; it is NOT cryptography, and a determined host process that
# knows the format can still decode it. The manifest keeps only a sha256
# digest per instance, which every consumer verifies before trusting the
# store — a tampered or stale store is a hard error, never a silent
# substitution. ``audit`` additionally scans the arms' action trails for any
# reference to these paths (see ``_scan_oracle_probes``).

ORACLE_PATH = SWE_DIR / "oracle.json.z"

# Every per-instance field that names or contains the answer. Pro's
# ``before_repo_set_cmd`` embeds the FIX COMMIT sha and the oracle file list;
# ``selected_test_files_to_run`` is the f2p node ids under another name.
_ORACLE_FIELDS = (
    "gold_patch",
    "test_patch",
    "fail_to_pass",
    "pass_to_pass",
    "before_repo_set_cmd",
    "selected_test_files_to_run",
)


def _oracle_record_digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _write_oracle_store(records: dict[str, dict[str, Any]], path: Path | None = None) -> Path:
    import base64
    import zlib

    p = path or ORACLE_PATH
    blob = base64.b64encode(
        zlib.compress(json.dumps(records, sort_keys=True).encode("utf-8"), 9)
    ).decode("ascii")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(blob, encoding="utf-8")
    return p


def _load_oracle_store(path: Path | None = None) -> dict[str, dict[str, Any]]:
    import base64
    import zlib

    p = path or ORACLE_PATH
    if not p.exists():
        raise SystemExit(
            f"oracle store missing at {p}. The manifest pins oracle digests, so "
            "grading is impossible without the store — re-run `fetch`."
        )
    data = json.loads(zlib.decompress(base64.b64decode(p.read_text(encoding="utf-8"))))
    if not isinstance(data, dict):
        raise SystemExit(f"oracle store at {p} is not a JSON object")
    return data


def _normalize_oracle(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "gold_patch": str(rec.get("gold_patch") or ""),
        "test_patch": str(rec.get("test_patch") or ""),
        "fail_to_pass": _as_list(rec.get("fail_to_pass")),
        "pass_to_pass": _as_list(rec.get("pass_to_pass")),
        "before_repo_set_cmd": str(rec.get("before_repo_set_cmd") or ""),
        "selected_test_files_to_run": rec.get("selected_test_files_to_run") or "",
    }


def _oracle_for(inst: dict[str, Any]) -> dict[str, Any]:
    """The instance's oracle material, digest-verified.

    New manifests carry ``oracle_sha256`` and no material; the record comes
    from the store and MUST hash to the pinned digest (fail safe: a missing
    or tampered record refuses, it never grades against a guess).
    Pre-oracle-store manifests (old Pro pins, test fixtures) carry the
    material inline — read it from the instance itself so frozen artifacts
    keep loading.
    """
    pinned = inst.get("oracle_sha256")
    if not pinned:
        return _normalize_oracle(inst)
    store = _load_oracle_store()
    rec = store.get(str(inst["instance_id"]))
    if rec is None:
        raise SystemExit(
            f"oracle store has no record for {inst['instance_id']!r} — the "
            "manifest and oracle.json.z are out of sync; re-run `fetch`."
        )
    if _oracle_record_digest(rec) != pinned:
        raise SystemExit(
            f"oracle record for {inst['instance_id']!r} does not match the "
            "manifest's pinned digest — the store was modified after the pin. "
            "Refusing to grade against unverified oracle material."
        )
    return _normalize_oracle(rec)


def _assert_oracle_store_complete(instances: list[dict[str, Any]]) -> None:
    """Hard-fail BEFORE any spend when the oracle store cannot serve every
    pinned instance.

    The store is only consulted by ``grade`` — the LAST step — so a missing
    or stale store used to surface after the money was spent: the first live
    sweep burned $24.78 producing runs whose every grade then refused with
    "oracle store has no record". Every entry point that leads to spend
    (``run``, ``run-all``, ``selftest``) calls this first; instances from
    pre-store manifests (material inline, no ``oracle_sha256``) are exempt.
    """
    problems: list[str] = []
    for inst in instances:
        if not inst.get("oracle_sha256"):
            continue
        try:
            _oracle_for(inst)
        except SystemExit as exc:
            problems.append(f"  {inst.get('instance_id')}: {exc}")
    if problems:
        raise SystemExit(
            "oracle store cannot serve the pinned manifest — refusing BEFORE "
            f"any spend ({len(problems)} instance(s)):\n" + "\n".join(problems)
            + "\nRe-run `fetch` to rebuild manifest.json and oracle.json.z together."
        )


def _declared_test_entries(inst: dict[str, Any]) -> list[str]:
    """The instance's declared test targets, as raw entries (may hold ::ids).

    Pro pins them under ``selected_test_files_to_run`` (a JSON-encoded list of
    the oracle's fail_to_pass NODE IDS — see ``_test_file_paths`` for why they
    are reduced to files before dev ever sees them). swe-rebench manifests pin
    ``test_targets``, already reduced to file paths at fetch time from
    FAIL_TO_PASS. Either way the caller must still run the result through
    ``_test_file_paths`` — it is idempotent on plain paths.
    """
    targets = inst.get("test_targets")
    if isinstance(targets, list):
        return [str(t) for t in targets]
    return _as_list(inst.get("selected_test_files_to_run"))


# --------------------------------------------------------------------------- #
# dataset access
# --------------------------------------------------------------------------- #


def _fetch_rows(
    offset: int, length: int, *, dataset: str, split: str
) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode(
        {
            "dataset": dataset,
            "config": "default",
            "split": split,
            "offset": offset,
            "length": length,
        }
    )
    with urllib.request.urlopen(f"{_ROWS_URL}?{qs}", timeout=120) as fh:
        data = json.load(fh)
    return [r["row"] for r in data.get("rows", [])]


def _all_rows(profile: DatasetProfile) -> list[dict[str, Any]]:
    """Every row in the profile's pool split.

    Paginates until a short page rather than to a baked total, so a dataset
    that grows (SWE-rebench adds a monthly split) is picked up whole;
    ``pool_cap`` bounds the loop so a runaway API can never loop forever.
    """
    rows: list[dict[str, Any]] = []
    for off in range(0, profile.pool_cap, 100):
        page = _fetch_rows(off, 100, dataset=profile.dataset, split=profile.split)
        rows.extend(page)
        if len(page) < 100:
            break
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


def _repair_truncated_param_ids(ids: list[str]) -> list[str]:
    """Repair SWE-rebench's whitespace-truncated parametrized test ids.

    The upstream log parser splits ids on whitespace, so a parametrized id
    whose parameter contains a space arrives truncated with an UNCLOSED
    bracket — e.g. ``test_kms.py::test_sign_happy[some`` for the real
    ``test_sign_happy[some message]`` (measured on getmoto__moto-9841 and
    conan-io__conan-19735). Such an id can never match anything, so a healthy
    instance grades broken.

    The repair strips the parametrization, selecting EVERY parametrization of
    that test function. That is a strict superset of the intended set: more
    tests must pass, so grading can only get stricter, never laxer — and an
    instance whose gold patch cannot carry the superset drops out at selftest,
    honestly. Well-formed ids (closed bracket or no bracket) pass through
    untouched. Duplicates from collapsed params are dropped, order preserved.
    """
    out: dict[str, None] = {}
    for tid in ids:
        if "[" in tid and not tid.endswith("]"):
            tid = tid.split("[", 1)[0]
        out.setdefault(tid, None)
    return list(out)


def _row_to_instance(profile: DatasetProfile, r: dict[str, Any]) -> dict[str, Any]:
    """Map ONE raw dataset row into the manifest's normalized instance shape.

    Common keys are consumed by every downstream command; profile-specific
    keys carry what only that profile's plumbing needs. Every instance is
    tagged with its profile so old (untagged = Pro) and new manifests resolve
    identically at consumption time.
    """
    statement = r.get("problem_statement") or ""
    inst: dict[str, Any] = {
        "profile": profile.name,
        "instance_id": r["instance_id"],
        "repo": r["repo"],
        "base_commit": r["base_commit"],
        "problem_statement": statement,
        "problem_statement_sha256": hashlib.sha256(
            statement.encode("utf-8")
        ).hexdigest(),
        "test_patch": r.get("test_patch") or "",
    }
    if profile.name == "swe-rebench":
        fail_to_pass = _repair_truncated_param_ids(_as_list(r.get("FAIL_TO_PASS")))
        inst.update(
            {
                "language": "python",  # the leaderboard split is Python-only
                "docker_image": r.get("docker_image") or "",
                "created_at": r.get("created_at") or "",
                # The dataset's own install/build step — what the image was
                # baked with. Public (environment plumbing, not answer
                # material): `_prepare_cloned_tree` replays it against the
                # mounted fresh clone so control and measurement share one
                # topology.
                "install_cmd": _install_cmd_from(r),
                "fail_to_pass": fail_to_pass,
                "pass_to_pass": _repair_truncated_param_ids(
                    _as_list(r.get("PASS_TO_PASS"))
                ),
                # The gold patch ships IN the row. Pinning it here kills the
                # rate-limited HF lookup that Pro's selftest/grade needed. It
                # lives beside test_patch/fail_to_pass, which are equally
                # oracle — the manifest is harness-side and never enters an
                # arm's working tree.
                "gold_patch": r.get("patch") or "",
                # Dev-facing test targets: fail_to_pass node ids reduced to
                # FILE paths at fetch time (same reduction Pro applies at run
                # time) — files exist in the tree, node ids would leak the
                # oracle AND not exist until the withheld test patch lands.
                "test_targets": _test_file_paths(fail_to_pass),
            }
        )
    else:
        inst.update(
            {
                "language": r.get("repo_language"),
                "dockerhub_tag": r.get("dockerhub_tag"),
                "fail_to_pass": _as_list(r.get("fail_to_pass")),
                "pass_to_pass": _as_list(r.get("pass_to_pass")),
                "before_repo_set_cmd": r.get("before_repo_set_cmd") or "",
                "selected_test_files_to_run": r.get("selected_test_files_to_run") or "",
                # Dev-facing FILE paths, so new-format Pro manifests need not
                # carry the raw node ids (which move to the oracle store).
                "test_targets": _test_file_paths(
                    _as_list(r.get("selected_test_files_to_run"))
                ),
            }
        )
    return inst


def _install_cmd_from(row: dict[str, Any]) -> str:
    """The dataset's install/build command from ``install_config``.

    ``pre_install`` (a list) runs before ``install``; both are optional. The
    rows API serves the config as a dict, but tolerate a JSON string too.
    """
    ic = row.get("install_config") or {}
    if isinstance(ic, str):
        try:
            ic = json.loads(ic)
        except json.JSONDecodeError:
            return ""
    if not isinstance(ic, dict):
        return ""
    parts = [str(p).strip() for p in (ic.get("pre_install") or [])]
    parts.append(str(ic.get("install") or "").strip())
    return " && ".join(p for p in parts if p)


def _split_oracle(inst: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split a full instance into ``(public_instance, oracle_record)``.

    The public instance keeps everything an arm may see plus a sha256 digest
    of the oracle record; the record itself goes to the compressed store.
    """
    public = dict(inst)
    record = {k: public.pop(k) for k in _ORACLE_FIELDS if k in public}
    public["oracle_sha256"] = _oracle_record_digest(record)
    return public, record


def _row_language(profile: DatasetProfile, r: dict[str, Any]) -> str:
    if profile.name == "swe-rebench":
        return "python"  # single-language dataset; rows carry no language field
    return str(r.get("repo_language") or "")


def _created_after(row: dict[str, Any], after: str) -> bool:
    """True when the row's ``created_at`` DATE is strictly after ``after``.

    Parsed as datetimes, not compared as strings: string comparison let
    cutoff-DAY instances slip in (``"2026-01-01 00:00:01" > "2026-01-01"`` is
    string-true), while the documented semantics are "strictly after the
    cutoff date" — the whole cutoff day is excluded. An unparseable
    ``created_at`` is excluded too (fail safe: unknown provenance is not
    post-cutoff evidence).
    """
    from datetime import date

    raw = str(row.get("created_at") or "").strip()
    try:
        cutoff = date.fromisoformat(after)
    except ValueError as exc:
        raise SystemExit(f"--after must be YYYY-MM-DD, got {after!r}") from exc
    try:
        created = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return created.date() > cutoff


def _resolve_image_digest(image: str) -> str | None:
    """Resolve an image ref to its immutable ``repo@sha256:…`` form.

    ``:latest`` tags are MUTABLE upstream — a selftest certifies the
    environment only as of the day it ran (the flax exclusion was exactly
    such drift). Pinning the digest at fetch time makes every later pull
    byte-identical to what the selftest validated. Local ``RepoDigests``
    first (no network); ``docker manifest inspect`` as the registry fallback
    (no pull). Returns None when neither works — the caller keeps the tag
    and warns loudly rather than failing the fetch.
    """
    repo = image.split("@", 1)[0].rsplit(":", 1)[0]
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", '{{join .RepoDigests "\n"}}', image],
        capture_output=True, text=True,
    )
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith(f"{repo}@sha256:"):
                return line
    proc = subprocess.run(
        ["docker", "manifest", "inspect", "-v", image],
        capture_output=True, text=True,
    )
    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            digest = (entry.get("Descriptor") or {}).get("digest", "")
            if str(digest).startswith("sha256:"):
                return f"{repo}@{digest}"
    return None


def fetch(*, dataset: str, language: str, limit: int, seed: int, after: str | None) -> None:
    """Sample instances and freeze them into a hash-pinned manifest.

    The seed is recorded so the sample is reproducible, and each instance
    carries a hash of its problem statement so a later dataset revision that
    silently rewrites a task is detectable rather than invisible. The chosen
    profile is persisted in the manifest AND in every instance: all later
    commands read it back from there, so a run can never mix profiles.

    Oracle material (gold patch, test patch, hidden test ids, Pro's setup
    command) is NOT written to the manifest — it goes to the compressed
    oracle store, digest-pinned per instance (see the oracle-store section).

    ``after`` keeps only instances whose ``created_at`` DATE is strictly
    after the given date — the cutoff day itself is excluded (contamination
    control for profiles with ``created_at``). For swe-rebench it defaults
    to 2026-01-01 — DeepSeek-V4 Pro's training cutoff is undocumented, so
    that stand-in is deliberately conservative and recorded in the manifest.
    """
    if dataset not in PROFILES:
        raise SystemExit(f"unknown --dataset {dataset!r} (known: {sorted(PROFILES)})")
    profile = PROFILES[dataset]
    if after is None and profile.name == "swe-rebench":
        after = _REBENCH_DEFAULT_CUTOFF

    rows = [r for r in _all_rows(profile) if _row_language(profile, r) == language]
    if not rows:
        raise SystemExit(f"no instances with language={language!r}")
    if after:
        rows = [r for r in rows if _created_after(r, after)]
        if not rows:
            raise SystemExit(f"no instances created after {after!r}")
    rows.sort(key=lambda r: str(r["instance_id"]))  # deterministic pre-shuffle order
    rng = random.Random(seed)
    picked = rng.sample(rows, min(limit, len(rows)))

    instances: list[dict[str, Any]] = []
    oracle_records: dict[str, dict[str, Any]] = {}
    for r in picked:
        full = _row_to_instance(profile, r)
        # Pin the docker image to its immutable digest: a `:latest` tag is
        # mutable upstream, so a tag-pinned manifest silently drifts away
        # from the environment the selftest certified.
        image = full.get("docker_image")
        if image:
            digest_ref = _resolve_image_digest(str(image))
            full["docker_image_digest"] = digest_ref
            if not digest_ref:
                print(
                    f"WARNING: could not resolve a digest for {image} — "
                    f"{full['instance_id']} stays tag-pinned and may drift upstream"
                )
        public, record = _split_oracle(full)
        instances.append(public)
        oracle_records[public["instance_id"]] = record

    manifest = {
        "profile": profile.name,
        "dataset": profile.dataset,
        "language": language,
        "seed": seed,
        "limit": limit,
        "created_at_after": after,
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
    store = _write_oracle_store(oracle_records)
    print(f"pinned {len(instances)} instances -> {MANIFEST_PATH}")
    print(f"oracle store ({len(oracle_records)} records) -> {store}")
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

_DIFF_GIT = "diff --git "

_TEST_PATH = re.compile(
    r"(^|/)tests?(/|$)"           # a tests/ or test/ directory anywhere
    r"|(^|/)test_[^/]+$"          # test_foo.py
    r"|_test\.[a-z]+$"            # foo_test.go
    r"|(^|/)conftest\.py$"        # pytest fixtures shape the oracle too
    r"|\.spec\.[jt]sx?$"
    r"|(^|/)testing(/|$)"
)

# Files that decide WHICH tests run and WHETHER they run, without being test
# files themselves. ``_TEST_PATH`` strips test code; these are the collection
# and auto-import channels that reach the same outcome sideways:
#
#   * ``pyproject.toml`` / ``setup.cfg`` / ``tox.ini`` / ``pytest.ini`` —
#     ``[tool.pytest.ini_options] addopts``, ``-p <plugin>``, markers,
#     ``collect_ignore``;
#   * ``setup.py`` / ``noxfile.py`` — run at build/test time;
#   * ``sitecustomize.py`` / ``usercustomize.py`` / ``*.pth`` — imported by
#     the interpreter itself, before pytest starts;
#   * ``*pytest*plugin*.py`` — an entry-point plugin.
#
# Measured against real pytest: a root ``_fixup.py`` with
# ``pytest_collection_modifyitems`` marking every item skipped plus
# ``addopts = "-p _fixup"`` makes ``python -m pytest <ids>`` exit 0 with
# "2 skipped". Under exit-code grading (see ``_GRADE_SCRIPT``) that was
# RESOLVED. The plugin file itself is ordinary production-looking code, so the
# CONFIG edit is the chokepoint worth refusing on.
_COLLECTION_CHANNEL = re.compile(
    r"(^|/)(pyproject\.toml|setup\.cfg|tox\.ini|pytest\.ini|setup\.py"
    r"|noxfile\.py|sitecustomize\.py|usercustomize\.py|conftest\.py)$"
    r"|\.pth$"
    r"|(^|/)[^/]*pytest[^/]*plugin[^/]*\.py$"
    r"|(^|/)[^/]*plugin[^/]*pytest[^/]*\.py$"
)


class DiffRefused(RuntimeError):
    """A prediction the harness refuses to grade at all.

    Refusing beats stripping and beats guessing:

    * an unparseable ``diff --git`` line means the parser does not know which
      file the following hunks belong to. The old code appended the line to the
      PREVIOUS block, so a test edit git had to quote merged into a kept code
      block and survived both the strip and ``assert_no_test_edits``;
    * a collection-config edit cannot be stripped honestly — stripping it could
      break an otherwise valid patch, and grading the remainder as if it were
      the arm's answer is the ``proxy != real`` class.
    """

    def __init__(self, reason: str, paths: list[str]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.paths = paths


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


def is_collection_channel_path(path: str) -> bool:
    """True for a file that can change which tests run, or whether they run."""
    return bool(_COLLECTION_CHANNEL.search(path))


def _c_unquote(token: str) -> str | None:
    """Decode git's ``quote_c_style`` form, e.g. ``"a/test_\\303\\247.py"``.

    git quotes a path (independently per side of the header) when it contains a
    control character, a quote, a backslash, or — with ``core.quotePath``, the
    default — any non-ASCII byte. Octal escapes are BYTES, so they are
    assembled and decoded as UTF-8 at the end.
    """
    if len(token) < 2 or not token.startswith('"') or not token.endswith('"'):
        return None
    body = token[1:-1]
    simple = {
        "a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13,
        '"': 34, "\\": 92,
    }
    out = bytearray()
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\":
            out.extend(ch.encode("utf-8"))
            i += 1
            continue
        i += 1
        if i >= len(body):
            return None
        esc = body[i]
        if esc in simple:
            out.append(simple[esc])
            i += 1
        elif esc.isdigit():
            octal = body[i : i + 3]
            if len(octal) != 3 or any(c not in "01234567" for c in octal):
                return None
            out.append(int(octal, 8))
            i += 3
        else:
            return None
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _take_quoted(s: str) -> tuple[str, str] | None:
    """Split a leading C-quoted token off ``s``; None if there is not one."""
    if not s.startswith('"'):
        return None
    i = 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            decoded = _c_unquote(s[: i + 1])
            return None if decoded is None else (decoded, s[i + 1 :])
        i += 1
    return None  # unterminated quote


def _strip_ab(a_raw: str, b_raw: str) -> tuple[str, str] | None:
    if not a_raw.startswith("a/") or not b_raw.startswith("b/"):
        return None
    return a_raw[2:], b_raw[2:]


def _split_unquoted_pair(rest: str) -> tuple[str, str] | None:
    """Split ``a/<path> b/<path>`` where either path may contain spaces.

    ``\\S+`` could not do this at all, which is the whole of defect 4. There is
    no unambiguous split in general, so: prefer the (unique) split where both
    sides name the SAME path — every non-rename header, which is nearly all of
    them — then fall back to a unique split for a rename. Anything still
    ambiguous returns None and the caller refuses the row.
    """
    candidates: list[tuple[str, str]] = []
    for m in re.finditer(r" b/", rest):
        pair = _strip_ab(rest[: m.start()], rest[m.start() + 1 :])
        if pair is not None:
            candidates.append(pair)
    same = [c for c in candidates if c[0] == c[1]]
    if len(same) == 1:
        return same[0]
    if same:
        return None
    return candidates[0] if len(candidates) == 1 else None


def parse_diff_header(line: str) -> tuple[str, str] | None:
    """``(a_path, b_path)`` for a ``diff --git`` line, or None if unparseable.

    Handles all three shapes git emits: both sides plain, either side C-quoted,
    and plain paths containing spaces. None is a REFUSAL signal, never a
    "treat it as content" signal.
    """
    if not line.startswith(_DIFF_GIT):
        return None
    rest = line[len(_DIFF_GIT) :].rstrip()
    if not rest:
        return None
    left = _take_quoted(rest)
    if left is not None:
        a_raw, remainder = left
        remainder = remainder.lstrip()
        right = _take_quoted(remainder)
        if right is not None:
            b_raw, tail = right
            if tail.strip():
                return None
        else:
            b_raw = remainder
        return _strip_ab(a_raw, b_raw) if b_raw else None
    quoted_right = rest.find(' "')
    if quoted_right != -1:
        right = _take_quoted(rest[quoted_right + 1 :])
        if right is None or right[1].strip():
            return None
        return _strip_ab(rest[:quoted_right], right[0])
    return _split_unquoted_pair(rest)


def split_diff(
    diff_text: str, *, refuse_collection_channels: bool = True
) -> tuple[str, list[str], list[str]]:
    """Return ``(code_only_diff, kept_paths, stripped_test_paths)``.

    Splits a unified diff on ``diff --git`` boundaries and drops any file whose
    path looks like a test. Operating per-file (not per-hunk) is deliberate: a
    file is either part of the oracle or it is not.

    Raises ``DiffRefused`` on a header it cannot parse, or on an edit to a
    pytest-collection channel. ``refuse_collection_channels=False`` is for the
    GOLD patch only: the maintainers' own fix legitimately edits ``setup.py``,
    and it is not an arm under test. (Measured: 0 of the 20 pinned oracle
    records touch a collection channel, and 0 of the 188 retained
    ``prediction.diff`` files do either — this refuses nothing that exists
    today.)
    """
    if not diff_text.strip():
        return "", [], []

    blocks: list[tuple[str, list[str]]] = []
    unparseable: list[str] = []
    current_path: str | None = None
    current: list[str] = []
    for line in diff_text.splitlines(keepends=True):
        bare = line.rstrip("\n")
        if bare.startswith(_DIFF_GIT) or bare.rstrip() == _DIFF_GIT.rstrip():
            parsed = parse_diff_header(bare)
            if parsed is None:
                # FAIL CLOSED. Never append it to the previous block.
                unparseable.append(bare[:200])
                current_path = None
                current = []
                continue
            if current_path is not None:
                blocks.append((current_path, current))
            current_path = parsed[1]
            current = [line]
        elif current_path is not None:
            current.append(line)
    if current_path is not None:
        blocks.append((current_path, current))

    if unparseable:
        raise DiffRefused(
            f"{len(unparseable)} 'diff --git' header(s) cannot be parsed, so the "
            "files their hunks belong to are unknown: "
            f"{unparseable}. Refusing to grade — an unclassified block used to "
            "be merged into the previous file's diff, which is how a test edit "
            "survives the strip.",
            unparseable,
        )

    kept: list[str] = []
    stripped: list[str] = []
    refused: list[str] = []
    out: list[str] = []
    for path, lines in blocks:
        # Order matters: conftest.py is BOTH a test path and a collection
        # channel, and the long-standing behaviour (strip it) must win, or
        # every conftest edit would start refusing rows that graded fine.
        if is_test_path(path):
            stripped.append(path)
        elif refuse_collection_channels and is_collection_channel_path(path):
            refused.append(path)
        else:
            kept.append(path)
            out.extend(lines)
    if refused:
        raise DiffRefused(
            f"prediction edits pytest collection/auto-import channel(s) "
            f"{refused}. Those files decide which tests run and whether they "
            "run at all (addopts, -p plugins, collect_ignore, sitecustomize), "
            "so an edit there can neuter the hidden suite without touching a "
            "test file. Refusing the row: stripping the edit could break an "
            "otherwise valid patch.",
            refused,
        )
    return "".join(out), kept, stripped


def assert_no_test_edits(diff_text: str) -> None:
    """Hard guarantee, checked in code rather than eyeballed.

    A graded diff containing a test edit would let the factory rewrite the
    oracle that is supposed to be judging it. Re-run at grade time as a second
    line of defence, so it must use the same parser as ``split_diff`` — the old
    shared regex was fail-open in both places at once.
    """
    offenders: list[str] = []
    unparseable: list[str] = []
    for line in diff_text.splitlines():
        bare = line.rstrip("\n")
        if not bare.startswith(_DIFF_GIT):
            continue
        parsed = parse_diff_header(bare)
        if parsed is None:
            unparseable.append(bare[:200])
        elif is_test_path(parsed[1]):
            offenders.append(parsed[1])
    if unparseable:
        raise DiffRefused(
            f"graded diff has {len(unparseable)} 'diff --git' header(s) that "
            f"cannot be parsed: {unparseable}. An unclassifiable header could "
            "be hiding a test edit; refusing.",
            unparseable,
        )
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
    """The one directory holding everything about one (instance, arm, MODEL).

    ``arm`` here is a RUN KEY, not necessarily a bare arm id — see ``run_key``.
    The key had no model component until the five-arm re-run, so two runs of
    the Claude CLI on different models shared this directory and the second
    silently destroyed the first's artifacts.
    """
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

    A fresh write also stamps the row with the two facts a reader must not have
    to reconstruct: which ATTEMPT this is (the retracted run published 4 second
    attempts, disclosed nowhere) and whether the run ran out of BUDGET (one
    rule, all arms — a cap hit is a counted, flagged attempt). Both are derived
    from the artifact right here so no arm can forget to record them.
    """
    run_dir = _run_dir(instance_id, arm)
    out = run_dir / "result.json"
    existing: dict[str, Any] = {}
    if merge and out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.update(payload)
    if not merge:
        if existing.get("probe_plumbing"):
            # A plumbing probe is not an attempt AT THE TASK — no model ran. Roll
            # the counter back so a real run of this cell is still attempt 1;
            # otherwise using the FREE plumbing check would make every
            # subsequent row look like a re-roll, and the report flags any
            # attempt > 1 as a protocol violation.
            _rewind_attempt(run_dir)
            existing["attempt"] = 0
        else:
            existing["attempt"] = _attempt_count(run_dir)
        # Through the SHARED classifier, not the raw reason, so the artifact
        # agrees with every consumer: a plumbing probe that happens to end on
        # its last step is a failed run, not a budget-exhausted attempt.
        status, detail = classify_run(existing)
        existing["budget_exhausted"] = status == _RUN_BUDGET_EXHAUSTED
        existing["budget_exhausted_reason"] = (
            detail if status == _RUN_BUDGET_EXHAUSTED else None
        )
    out.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return out


_ATTEMPT_NAME = "attempt.json"


def _bump_attempt(run_dir: Path) -> int:
    """Increment and return this (instance, arm, model)'s attempt counter.

    Survives ``_reset_run_artifacts`` deliberately — it is the ONE fact about a
    run directory that must outlive the run, because "this is the third time we
    ran this cell" is not visible in any other artifact. The retracted
    2026-08-03 run published four second attempts after the integrity gate
    invalidated the first, and nothing in the evidence said so.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    # ``missing=0``: no counter file means no attempt has happened YET, so this
    # one is the first. (Reading it back defaults to 1 instead — a row that
    # predates the counter WAS an attempt.)
    n = _attempt_count(run_dir, missing=0) + 1
    (run_dir / _ATTEMPT_NAME).write_text(
        json.dumps({"attempts": n}) + "\n", encoding="utf-8"
    )
    return n


def _rewind_attempt(run_dir: Path) -> None:
    """Un-count the attempt ``_reset_run_artifacts`` just recorded."""
    n = max(_attempt_count(run_dir, missing=0) - 1, 0)
    (run_dir / _ATTEMPT_NAME).write_text(
        json.dumps({"attempts": n}) + "\n", encoding="utf-8"
    )


def _attempt_count(run_dir: Path, *, missing: int = 1) -> int:
    try:
        data = json.loads((run_dir / _ATTEMPT_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return missing  # pre-1.6 rows and hand-made fixtures are attempt 1
    try:
        return max(missing, int(data["attempts"]))
    except (KeyError, TypeError, ValueError):
        return missing


# --------------------------------------------------------------------------- #
# ONE run classifier, shared by the sweep roll-up and the report
# --------------------------------------------------------------------------- #
#
# There used to be two. ``sweep_one`` set its row status from the run child's
# EXIT CODE; ``report`` set ``_run_failed`` from ``result.json["error"]``. On
# the retracted 2026-08-03 run they disagreed — ``sweep-claude.json`` reported
# 17 resolved while ``results.md`` reported 16 of 18 — and neither number could
# be checked against the other because they were computed from different facts.
# One function now owns the question, and both callers ask it.

_RUN_OK = "ok"
_RUN_BUDGET_EXHAUSTED = "budget_exhausted"
_RUN_FAILED = "run_failed"
_RUN_NO_RESULT = "no_result"

# Every arm's cap-hit termination value. ONE rule for all arms (pre-registered
# decision rule 4): a turn-cap / wall-cap hit is a COMPLETED, COUNTED, FLAGGED
# attempt, never an excluded run. The retracted run excluded a Claude row that
# hit its turn cap AND PASSED the oracle, which silently improved its own
# denominator; that is the failure this constant exists to prevent.
_BUDGET_TERMINATIONS = frozenset(
    {
        "wall-clock-cap",  # every arm
        "tick-cap",  # factory: ran out of orchestrator ticks
        "step-cap",  # bare: ran out of shell turns
        "iteration-cap",  # openhands
        "turn-cap",  # claude
    }
)

# Pre-1.6 rows recorded the cap hit ONLY as this substring inside ``error``.
# Recognising it keeps the one rule applicable to the already-archived
# evidence, which is the only way the retracted run can be re-read honestly.
_BUDGET_ERROR_MARK = "wall-clock cap"

# Terminations that mean something BROKE. A run that stopped here is a failure
# even if it happens to have used its last step, so the step-count heuristic
# below must not fire for it.
_ERROR_TERMINATIONS = frozenset({"error", "model-call-error", "agent-error"})


def budget_exhausted_reason(result: dict[str, Any]) -> str | None:
    """Why this run ran out of budget, or ``None`` if it did not.

    Derived, not trusted. ``termination`` is authoritative; the ``error``
    substring and the step count are fallbacks for rows written before
    ``termination`` carried a cap value — which is what lets the retracted run's
    archive be re-read under the new rule instead of being taken on faith.

    The step count matters for a real, measured case: the Claude row for
    ``harumiweb__exstruct-113`` recorded ``num_turns 61`` against
    ``turn_cap 60`` and ``error: "claude CLI exited 1: "`` (empty stderr). That
    is the CLI stopping AT its cap, and the retracted report read it as a
    crashed run — dropping a row that had PASSED the oracle out of both
    numerator and denominator.
    """
    term = str(result.get("termination") or "")
    if term in _BUDGET_TERMINATIONS:
        return f"{term} ({result.get('wall_clock_s')}s wall)"
    err = str(result.get("error") or "")
    if _BUDGET_ERROR_MARK in err:
        return err
    if term in _ERROR_TERMINATIONS:
        return None
    used = result.get("steps_used", result.get("num_turns"))
    cap = result.get("step_cap", result.get("turn_cap"))
    if isinstance(used, int) and isinstance(cap, int) and cap > 0 and used >= cap:
        return f"used all {cap} of its steps/turns ({used})"
    return None


def classify_run(
    result: dict[str, Any] | None, *, rc: int | None = None
) -> tuple[str, str | None]:
    """``(status, detail)`` for one run. THE single source of that verdict.

    Order matters and is fail-closed in the direction that keeps evidence
    VISIBLE — a flagged, counted row is safer than a silently dropped one,
    because a dropped row moves a published denominator:

    1. no readable ``result.json`` -> ``no_result`` (nothing to report at all);
    2. a plumbing PROBE -> ``run_failed``, always: it called no model and must
       never reach a rate, whatever else its fields say;
    3. any budget cap hit -> ``budget_exhausted``: a COUNTED attempt, flagged,
       with any recorded error text carried along rather than discarded;
    4. a recorded ``error`` -> ``run_failed``;
    5. a non-zero child exit code -> ``run_failed`` (the child died after
       writing an otherwise clean result);
    6. otherwise ``ok``.

    ``rc`` is optional because ``report`` reads archived rows with no child
    process to ask.
    """
    if not isinstance(result, dict) or not result:
        # A child that also exited non-zero gets the more informative verdict:
        # the caller has the exit code and the log tail, which "no result" does
        # not convey. Both are failures either way.
        if rc is not None and rc != 0:
            return _RUN_FAILED, f"run exited {rc} and wrote no readable result.json"
        return _RUN_NO_RESULT, "run wrote no readable result.json"
    err = str(result.get("error") or "")
    if result.get("probe_plumbing") or err.startswith("PLUMBING PROBE"):
        return _RUN_FAILED, err or "plumbing probe — not a measurement"
    budget = budget_exhausted_reason(result)
    if budget is not None:
        return _RUN_BUDGET_EXHAUSTED, (
            f"{budget}; recorded error: {err}" if err else budget
        )
    if err:
        return _RUN_FAILED, err
    if rc is not None and rc != 0:
        return _RUN_FAILED, f"run exited {rc}"
    return _RUN_OK, None


def _read_result(run_dir: Path) -> dict[str, Any] | None:
    """This run's ``result.json``, or ``None`` when it is absent or unreadable."""
    try:
        data = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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

    ONE file is deliberately exempt and is BUMPED here instead: ``attempt.json``
    (see ``_bump_attempt``). Every run function calls this at its top before any
    exit path — a contract an existing AST test enforces — which makes this the
    only hook guaranteed to fire exactly once per attempt, including the
    attempts that die early.
    """
    _bump_attempt(run_dir)
    for name in (
        "prediction.diff",
        "raw.diff",
        "grade.log",
        "grade-nodes.log",
        "result.json",
        "audit.json",
        "bare-commands.ndjson",  # APPENDED per step; must not span runs
        "claude-transcript.ndjson",  # the claude arm's action trail
        "claude-stderr.log",
    ):
        (run_dir / name).unlink(missing_ok=True)
    # `run-all` captures each child's stdout here, so `sweep-grade.log` held the
    # previous grade's verdict — including, before this change, the oracle's
    # gold_files. A stale one is both wrong and a leak.
    for stale in run_dir.glob("sweep-*.log"):
        stale.unlink(missing_ok=True)
    shutil.rmtree(run_dir / "state", ignore_errors=True)
    shutil.rmtree(run_dir / "root", ignore_errors=True)
    # Pre-isolation layouts kept the prepared clone and the factory root here;
    # a leftover one is stale AND reachable from the next arm's shell.
    shutil.rmtree(run_dir / "grade-repo", ignore_errors=True)
    shutil.rmtree(run_dir / "repo", ignore_errors=True)


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


_PREPARE_TIMEOUT_S = 3600


def _prepare_cloned_tree(
    inst: dict[str, Any], repo: Path, *, timeout_s: int = _PREPARE_TIMEOUT_S
) -> str | None:
    """Make a fresh clone equivalent to the image's baked tree. rebench-only.

    proxy ≠ real, measured on the first live sweep: ``selftest`` graded gold
    patches inside the image's BAKED ``/testbed`` — which contains
    build-generated artifacts (setuptools-scm ``_version.py``, compiled
    extensions) — while ``run`` mounts a FRESH clone over ``/testbed`` and
    loses them. Three instances (tox, vyper, pandas) passed the control and
    then died at the run's collect gate. The control must exercise the
    MEASUREMENT's topology, so both now operate on a mounted fresh clone
    prepared by this function:

    1. run the dataset's own install/build step (``install_cmd``, from the
       row's ``install_config`` — the exact command the image was baked
       with) inside the instance image against the mounted clone. As ROOT,
       because editable installs write into the image's conda env; with
       network, because this is the dataset's bake step at the pristine base
       commit — no arm code exists yet. Ownership is chowned back to the
       invoking uid so later host git operations and cleanup work.
    2. COMMIT whatever the step generated onto ``swebench-base``: untracked
       files survive neither ``git worktree add`` (dev's per-story tree) nor
       the grade script's ``git clean -fd`` — the same clone-passes/
       worktree-fails class the submodule vendoring closed.

    Returns an error string when the install step fails — the caller treats
    that as environment-not-preparable BEFORE any model spend (for selftest
    that honestly excludes the instance; for run it fails the run at $0).
    Pro stays on its frozen baked topology and returns None untouched.
    """
    profile = _profile_of(inst)
    if profile.name != "swe-rebench":
        return None
    install = str(inst.get("install_cmd") or "").strip()
    if install:
        wd = profile.container_workdir
        uid, gid = os.getuid(), os.getgid()
        script = (
            "set -o pipefail\n"
            f"cd {wd} || exit 97\n"
            # The mounted tree is HOST-uid-owned while this container runs as
            # root: git (invoked by setuptools-scm / uv-dynamic-versioning
            # during the install) refuses with "dubious ownership" without
            # this — measured on 3 of the pinned 20.
            "git config --global --add safe.directory '*' 2>/dev/null || true\n"
            # A --depth 1 clone (the contamination control) has no tags, so
            # scm-version backends cannot derive a version. These are the
            # backends' own documented fallbacks; a test that asserts a real
            # version string will fail the gold run and exclude the instance
            # VISIBLY at selftest rather than silently passing a wrong env.
            "export SETUPTOOLS_SCM_PRETEND_VERSION=0.0.1.dev0\n"
            "export PDM_BUILD_SCM_VERSION=0.0.1.dev0\n"
            f"{profile.env_setup.rstrip() or 'true &&'} true\n"
            f"({install})\n"
            "rc=$?\n"
            f"chown -R {uid}:{gid} {wd}\n"
            'exit "$rc"\n'
        )
        try:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-i",
                 "-v", f"{repo}:{wd}", "-w", wd,
                 "--entrypoint", "bash", _image_for(inst), "-lc",
                 "cat > /tmp/.swebench_prepare.sh && "
                 "exec bash -l /tmp/.swebench_prepare.sh < /dev/null"],
                input=script,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            return f"install step could not run: {exc}"
        if proc.returncode != 0:
            tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
            return f"install step failed rc={proc.returncode}: {tail}"
    # Commit generated artifacts even when install_cmd is empty (a no-op
    # commit path): derived worktrees and in-container resets must see the
    # exact prepared state.
    subprocess.run(["git", "-C", str(repo), "add", "-A"], capture_output=True)
    staged = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet"], capture_output=True
    )
    if staged.returncode != 0:
        _git(
            repo, "commit", "-q", "-m",
            "bench: commit build-generated artifacts so derived trees keep them",
        )
    _git(repo, "update-ref", "refs/remotes/origin/swebench-base", "HEAD")
    return None


# The test policy EVERY arm must receive BYTE-IDENTICALLY. Extracted from
# ``_STORY_TEMPLATE`` (whose rendered text is unchanged — pinned by
# ``test_story_template_rendering_is_unchanged``) because the bare arm's system
# prompt used to say the OPPOSITE: "Do NOT create, edit or delete test files.
# Test edits are stripped before grading, so they are wasted effort." Same
# stripping mechanic, opposite instruction — so the arm that anchors the
# scaffold-lift headline was prompt-FORBIDDEN from building the very
# red-green feedback loop the factory's thesis rests on, while factory and
# claude were told to build it. A prompt asymmetry on the control arm
# invalidates the comparison, not just the arm.
# The base-suite warning — EVERY arm receives this, byte-identical.
#
# It exists because the test command every arm gates DONE on CANNOT FAIL for
# this task: it targets the fail_to_pass FILES at base_commit, i.e. before the
# withheld gold test patch adds the tests that encode the required behaviour.
# Measured over the 19 pinned rebench instances: 3 target a file that does not
# exist at base, 11 more contain ZERO of the fail_to_pass test functions, and
# the remaining 5 contain them asserting the OLD behaviour. So "N passed" is
# the default state of the tree and says nothing. Three confirmed consequences:
# conan-19735 ran a `sed` that matched nothing, saw "28 passed", and replied
# DONE at step 6 with a 0-byte diff; nicegui-5858 the same;
# ucfopen__canvasapi-716 wrote a CORRECT fix, saw the pre-existing test assert
# the old behaviour and fail, restored the original file out of the docker
# image ("the tests are designed for the original implementation") and declared
# DONE with a 0-byte diff.
#
# #223 fixed this for the BARE arm only, deliberately, to keep the other arms'
# prompt bytes stable and avoid confounding two axes at once, and left an
# operator to-do saying it had to reach every arm before any run could be
# published as "matched prompt". That is now discharged: the operator's decision
# (2026-08-03) is to apply it identically everywhere, so the parity claim is
# actually true. The five-arm re-run is therefore a FRESH BASELINE, not a
# before/after against the retracted run: every arm's prompt changed.
#
# Appended to `_STORY_TEMPLATE` (factory, openhands, claude) and to `_BARE_TASK`
# (bare) — one string, four arms, no privileged wording.
_BASE_TESTS_NOTE = """\
Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
"""

_TEST_POLICY = """\
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
make the tests encode what the TASK requires."""

_STORY_TEMPLATE = (
    """# {instance_id}

## Problem

{statement}

## Definition of done

Change the production code in this repository so the described behaviour is
correct.

"""
    + _TEST_POLICY
    + """

## Running the tests

This checkout has NO dependencies installed, so a bare `pytest` fails with
`ModuleNotFoundError`. Run this exact command from the repo root — it executes
inside an image that has the dependencies, with your working tree mounted so it
tests YOUR edits:

```
{test_command}
```

"""
    + _BASE_TESTS_NOTE
)


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

    Profile plumbing: the image ref, the mount target (Pro images keep the
    repo at ``/app``, swe-rebench at ``/testbed``) and the env-activation
    prefix (swe-rebench images ship a conda env that a non-root login shell
    does not inherit) all come from the instance's pinned profile.

    ``repo``, when given, makes the command RUNNABLE in that tree: a declared
    target that does not exist at ``base_commit`` falls back to its nearest
    existing ancestor directory (``_existing_targets``). This argument was
    accepted and then ignored, so the command handed to every arm embedded a
    path that cannot be collected on 3 of the 19 pinned rebench instances
    (``hkuds__openharness-217``, ``vyperlang__vyper-4801``,
    ``line__line-bot-sdk-python-981_interface``) — pytest exits 4 with "file or
    directory not found" and the arm's only verification channel is dead
    before it starts. ``_precheck_collect`` already salvaged exactly this way
    for its own collect probe; the salvage now reaches the command the arms
    actually run, for every arm identically.
    """
    entries = test_files if test_files is not None else _declared_test_entries(inst)
    files = _test_file_paths(entries)
    if repo is not None and any(not (repo / f).exists() for f in files):
        files = _existing_targets(files, repo)
    target = " ".join(_shq(t) for t in files) if files else ""
    mode = "--collect-only -q " if collect_only else ""
    profile = _profile_of(inst)
    inner = (
        f"{profile.env_setup}python -m pytest -p no:cacheprovider {mode}{target}"
    ).strip()
    image = _image_for(inst)
    wd = profile.container_workdir
    return (
        f'docker run --rm -v "$PWD":{wd} -w {wd} '
        '--user "$(id -u):$(id -g)" -e HOME=/tmp '
        "-e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash "
        f"{image} -lc {_shq(inner)}"
    )


def _ensure_image(inst: dict[str, Any], timeout_s: int = 1800) -> bool:
    """Pull the instance image if absent. Returns False when unavailable."""
    image = _image_for(inst)
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
    files = _test_file_paths(_declared_test_entries(inst))
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


# The three result.json keys that answer "which weights produced this row".
_MODEL_MIX_KEYS = ("models_used", "model_calls", "model_escalated_calls")


def _no_model_mix() -> dict[str, Any]:
    """The mix payload for a run that never reached the model (precheck/prepare
    failure). Explicit empties, so "nothing ran" never reads like "not
    recorded"."""
    return {"models_used": [], "model_calls": [], "model_escalated_calls": 0}


def _model_mix(events_dir: Path, *, nominal: str | None) -> dict[str, Any]:
    """Which models ACTUALLY ran, per persona and per tier, from the ledger.

    ``result.json["model"]`` was absent on every factory row, and that hid a
    finding that goes to the heart of the published claim: across the 19 pinned
    rebench instances the factory arm escalated 7 dev calls to
    ``azure/gpt-5.3-codex`` (the HARD tier) on 5 instances, and 4 of its 11
    resolves used that tier. "Matched weights vs the bare arm" was therefore
    false, and nothing in the artifact said so. Verified in this repo's own run
    dirs: ``idaholab__montepy-933_interface`` (2 hard dev calls),
    ``pandas-dev__pandas-63945`` (2), ``jsonpickle__jsonpickle-588`` (1),
    ``raullenchai__rapid-mlx-289`` (1), ``vyperlang__vyper-4801`` (1).

    Read from ``state/events/runs.ndjson`` — the per-run event ledger, which
    already records ``persona``, ``model`` and ``model_tier`` per call — so
    this is a MEASUREMENT of the calls that happened, not a restatement of the
    route that was resolved. ``nominal`` is the arm's claimed model; calls on
    any other model are counted separately so an escalation is visible at a
    glance rather than requiring an ndjson dig.

    Best-effort by contract: a missing or partly-corrupt ledger yields the
    empty mix rather than raising — the arms' cost/token accounting already
    fails the audit when the ledger is unreadable.
    """
    counts: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    path = events_dir / "runs.ndjson"
    if path.exists():
        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(ev, dict) or ev.get("event") != "run":
                        continue
                    key = (
                        str(ev.get("persona") or "?"),
                        str(ev.get("model") or "?"),
                        ev.get("model_tier"),
                    )
                    row = counts.setdefault(
                        key,
                        {
                            "persona": key[0],
                            "model": key[1],
                            "model_tier": key[2],
                            "calls": 0,
                            "cost_usd": 0.0,
                        },
                    )
                    row["calls"] = int(row["calls"]) + 1
                    row["cost_usd"] = round(
                        float(row["cost_usd"]) + float(ev.get("cost_usd") or 0.0), 4
                    )
        except OSError:
            pass
    calls = sorted(counts.values(), key=lambda r: (r["persona"], r["model"]))
    return {
        "models_used": sorted({str(r["model"]) for r in calls}),
        "model_calls": calls,
        "model_escalated_calls": sum(
            int(r["calls"]) for r in calls if nominal and r["model"] != nominal
        ),
    }


def _build_bench_root(inst: dict[str, Any], repo: Path, root: Path) -> Path:
    """A minimal factory root: own state db, own settings, app -> the clone.

    ``root`` is passed in because it lives in the scratch work tree now, not
    under ``runs/``: the dev agent's cwd is ``root/state/worktrees/<name>``, and
    under ``runs/`` that was six ``..`` from the oracle store.
    """
    if root.exists():
        shutil.rmtree(root)
    (root / "state").mkdir(parents=True)
    app_dir = root / "apps" / "swebench"
    (app_dir / "stories").mkdir(parents=True)
    (app_dir / "directions").mkdir(parents=True)

    # The declared targets are a JSON-encoded LIST, like fail_to_pass.
    # Interpolating it raw produced `python -m pytest ["tests/x.py"]`, which
    # pytest reads as a nonexistent path — every dev run would have seen a
    # collection error instead of the real suite.
    test_files = _declared_test_entries(inst)
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
    # BEFORE anything costs money or time: the oracle store must be able to
    # grade this run, or the whole run is a write-off (the $24.78 class).
    _assert_oracle_store_complete([inst])
    run_dir = _run_dir(instance_id, "factory")
    # BEFORE any exit path (image pull, clone, precheck): a stale
    # prediction.diff must never outlive the run that produced it.
    _reset_run_artifacts(run_dir)
    # The LIVE tree lives outside the repo (see `assert_workspace_isolated`);
    # only finished artifacts come back to `run_dir` afterwards.
    work = _work_dir(instance_id, "factory", fresh=True)
    if not _ensure_image(inst):
        raise SystemExit(
            f"image for {instance_id} is unavailable; the factory arm needs it for "
            "a working test environment (see instance_test_command)"
        )
    repo = work / "repo"
    assert_workspace_isolated(repo)
    _clone(inst, repo)
    # Same topology as the control: replay the dataset's install/build step
    # against the fresh clone and commit what it generates, so dev's derived
    # worktrees carry the build artifacts the baked image had.
    prep_error = _prepare_cloned_tree(inst, repo)
    if prep_error:
        error = f"prepare: {prep_error}"
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
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "persona_calls": 0,
                **_no_model_mix(),
            },
        )
        raise SystemExit(error)
    root = _build_bench_root(inst, repo, work / "root")
    # The dev agent's cwd will be `root/state/worktrees/<name>`. Prove NOW that
    # nothing above it carries the answer, before a token is spent.
    assert_workspace_isolated(root / "state" / "worktrees")

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
                **_no_model_mix(),
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
    from factory.model_router import route
    from factory.runner import Run, _engine

    # The weights this arm CLAIMS — resolved, not assumed, and recorded in
    # result.json so "matched weights" is checkable against ``models_used``.
    nominal_model = route("dev", "standard")

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

    # The arm has stopped; its audit trail can come home. This happens BEFORE
    # the diff is refused below, because `audit` treats a missing trail as a
    # finding and a refused prediction still needs to be auditable.
    _copy_audit_trail(root / "state", run_dir / "root" / "state")

    (run_dir / "raw.diff").write_text(raw_diff, encoding="utf-8")
    refused: list[str] = []
    try:
        code_diff, kept, stripped = split_diff(raw_diff)
    except DiffRefused as exc:
        # No prediction.diff is written, so `grade` refuses and `audit` fails:
        # a refused row can never be counted as a resolve. The reason is
        # recorded where the report can see it.
        refused = exc.paths
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
                "final_state": final.state,
                **_ledger_totals(runs, story_id),
                "cost_source": "derived-from-price-table",
                "error": f"diff refused: {exc.reason}",
                "refused_paths": refused,
                "factory_says_green": False,
            },
        )
        raise SystemExit(f"diff refused: {exc.reason}") from exc
    assert_no_test_edits(code_diff)

    (run_dir / "prediction.diff").write_text(code_diff, encoding="utf-8")

    # Tokens are the primitive; dollars are derived (see bench/README.md).
    result = {
        "arm": "factory",
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "problem_statement_sha256": inst["problem_statement_sha256"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        # The NOMINAL weights this arm claims — the dev/standard route, i.e.
        # what "matched weights vs bare" means. ``models_used`` below is what
        # actually ran, and the two DIVERGE: the chain's convergence loop
        # escalates a stuck dev to the hard tier, which no factory row recorded
        # (``model`` was absent from every one of them). See ``_model_mix``.
        "model": nominal_model,
        **_model_mix(root / "state" / "events", nominal=nominal_model),
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "final_state": final.state,
        "dev_retries": final.dev_retries,
        "reviewer_cycles": final.reviewer_cycles,
        "steps_used": len(transitions),
        "step_cap": max_steps,
        "termination": (
            "wall-clock-cap"
            if error and "wall-clock cap" in error
            else (
                "error"
                if error
                else ("terminal-state" if final.state in terminal else "tick-cap")
            )
        ),
        # The chain writes one trajectory per dev call under the run's own
        # state root; named here so a single run says where to look.
        "trajectory": "root/state/events/trajectories/",
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
        "refused_paths": refused,
        "diff_bytes": len(code_diff),
    }
    out = _write_result(instance_id, "factory", result)
    _print_run_summary(result, out)
    print(f"  factory says green : {result['factory_says_green']}")


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

_BARE_SYSTEM = (
    """\
You are fixing a bug in a software repository. You are in a shell at the repo root.

Reply with EXACTLY ONE of these, and nothing else:

  BASH
  <one shell command>

  DONE

Rules:
- One command per reply. No commentary outside the block.
- Edit files with standard tools (cat > file <<'EOF', sed, python - <<'EOF').
- Never write an "Exit N", "Exit code:", "Output:" or "Result:" line yourself.
  Only the environment reports what a command did; anything you write on those
  lines is fiction and will be discarded.
- Reply DONE when the production code change is complete AND you have seen a
  test you wrote for this task go from failing to passing.
- You cannot access the network.

## Definition of done

"""
    + _TEST_POLICY
    + "\n"
)

_BARE_STEP_CAP = 40
_BARE_OUTPUT_CAP = 4000
_FACTORY_STEP_DEFAULT = 16

# One command's own wall clock. A ``docker run … pytest`` on a big suite is the
# expensive case; past it the observation is a timeout notice, not a crash.
_BARE_CMD_TIMEOUT_S = 300

# How many turns of history the model sees, EXCLUDING the pinned system+task
# prefix. The old window (``history[-24:]`` over a flat list that started with
# system+task and grew by 2 per step) EVICTED the system prompt and the task
# once a run passed step 11 — and invalid-format replies clustered at exactly
# steps 12-24, in the four longest runs, all four of which ended wrong or
# empty. The prefix is now pinned and only the tail slides.
_BARE_HISTORY_TURNS = 22

# Extra continuations granted when the model says DONE with nothing to grade.
# Below the repo's hard cap of 3 (CLAUDE.md: nothing loops more than 3 times);
# on the (N+1)-th DONE the loop accepts it and records the empty diff.
_BARE_DONE_NUDGES = 2

_BARE_TASK = (
    """\
Repository: {repo}
Task:

{statement}

Fix the PRODUCTION code so this is resolved. A hidden test suite will judge it.

This checkout has no dependencies installed; the command below runs the repo's
tests inside a docker image that has them, with your working tree mounted. Run
it to check your fix before replying DONE:

{test_command}

"""
    + _BASE_TESTS_NOTE
)


def _resolve_max_steps(arm: str, requested: int | None) -> int:
    """Per-arm default step budget; an explicit ``--max-steps`` always wins.

    The ONE place per-arm budgets resolve — the units differ per arm: a
    factory "step" is one orchestrator tick (a whole dev/review/gate pass),
    a bare "step" is ONE shell command, a claude "step" is one CLI turn
    (``--max-turns``), an openhands "step" is one agent iteration. All 19 bare
    runs of the first rebench sweep inherited the factory's default of 16 while
    ``_BARE_STEP_CAP`` sat unused, so the bare arm ran at less than half its
    intended budget.

    Reads ``_ARMS`` and FAILS LOUD on an unknown arm. The old if-chain ended in
    ``return _FACTORY_STEP_DEFAULT``, so any name it did not enumerate silently
    got 16 — which for the Claude CLI is 16 turns instead of 60, i.e. a
    quarter of the pre-registered budget, reported as if it were the budget.
    """
    if requested is not None:
        return requested
    return arm_spec(arm).max_steps


# The file a plumbing probe writes so the run has a real, non-test production
# change to capture, split and grade-shape. Named so nobody mistakes it for
# task output.
_PROBE_FILE = "swebench_plumbing_probe.py"

# Recorded as the run's ``error`` so a probe row is fail-closed everywhere: the
# report buckets it as a failed run, ``estimate_instance_cost`` refuses it as a
# cost sample, and no headline can absorb it.
_PROBE_ERROR = (
    "PLUMBING PROBE — not a measurement: no model was called. Re-run without "
    "--probe-plumbing for a real row."
)

# A fixed reply script for ``--probe-plumbing``: no model, no spend, and every
# parser branch this PR touches exercised in order —
#   1. the BASH-marker form;
#   2. DONE with an EMPTY tree, which must be REJECTED and nudged;
#   3. the plain ```bash fence form deepseek actually emits (34 of 231 measured
#      replies carried no marker; 12 were exactly this shape and were thrown
#      away), writing a real production-code file;
#   4. DONE with fabricated ``Exit code:``/``Result:`` lines, which must be
#      accepted as DONE (the tree now has changes) with those lines never
#      becoming an observation.
_BARE_PROBE_REPLIES = (
    "BASH\ngit status --porcelain",
    "I have finished the change.\nDONE",
    "Now the fix:\n\n```bash\nprintf '%s\\n' "
    f"'# swebench plumbing probe' > {_PROBE_FILE}\n```",
    "The tests now pass.\nExit code: 0\nResult: 4 passed, 0 failed\nDONE",
)


def _probe_text_run() -> Any:
    """A ``text_run`` stand-in that returns the fixed probe script.

    Deliberately shaped like the real call site (same keyword arguments,
    returns a string) so the probe exercises the loop, the parser, the
    executor, the diff capture and the artifact write — everything except the
    provider. It writes no ledger rows, which is why a probe run reports
    ``persona_calls: 0`` and an explicit ``error``.
    """
    replies = list(_BARE_PROBE_REPLIES)

    def _stub(**kwargs: Any) -> str:
        return replies.pop(0) if replies else "DONE"

    return _stub


def run_bare(
    instance_id: str, *, max_steps: int, timeout_s: int, probe: bool = False
) -> None:
    """Minimal bash-loop agent on the IDENTICAL Azure deployment the factory uses.

    This is PLAN.md 1.4, and it is not optional. The product thesis is a
    model-agnostic harness that extracts frontier-competitive output from
    non-frontier models — the model is a config value in routes.yaml that gets
    swapped as cheaper models ship. So an absolute factory score measures the
    MODEL. The only number that measures the HARNESS is the delta between the
    factory and the same weights bare, which is what this arm supplies.

    Deliberately unsophisticated: one command per turn, truncated output, no
    planning, no retrieval, no review. That is the point — it is the floor the
    factory has to beat. It DOES get the same docker test one-liner the
    factory dev gets: an arm with no way to run anything measures
    verification-blindness, not scaffold lift (0 of 19 first-sweep bare runs
    ever invoked pytest).

    "Minimal" means FEW AFFORDANCES, not a broken substrate. Everything below
    is the difference between measuring a model and measuring this function's
    bugs — the 2026-08-03 audit invalidated a published 0/19 for exactly that
    reason (external anchor: the same deployment scores 40.2% under Nebius's
    own minimal scaffold, so P(0 of 19) ≈ 5.7e-5):

    * a real role-tagged message list, so the model can tell its own text from
      the environment's — and only the PARSED COMMAND is ever echoed back, so
      a fabricated ``Exit 0 / Output: / Result:`` line can never become an
      observation. Two runs declared DONE on invented test results;
      ``conan-19750`` wrote 11,890 characters with 8 fenced blocks, executed
      ZERO commands, and said "The tests now pass. DONE";
    * a PINNED system+task prefix, because a flat ``history[-24:]`` window
      evicted both after step 11;
    * the same collect precheck the factory arm runs, and the same salvaged
      test target, so the command in the prompt is runnable;
    * an empty-diff guard on DONE — 6 of 19 rows (32%) shipped 0 bytes;
    * a caught command timeout, which used to propagate out of this function
      and kill the run with no ``result.json`` at all;
    * a full observation trail in ``bare-commands.ndjson``.

    ``probe=True`` (``--probe-plumbing``) replaces the model with a fixed reply
    script and spends NOTHING. See ``_probe_replies``.
    """
    # Wall clock starts at ENTRY so clone/setup time is counted (same fix as
    # run_factory); ``started`` below still scopes the step-loop budget.
    entered = time.monotonic()
    inst = _instance(instance_id)
    # A run the store cannot grade is a write-off — refuse before any spend.
    _assert_oracle_store_complete([inst])
    run_dir = _run_dir(instance_id, "bare")
    # BEFORE any exit path: clears stale prediction/grade artifacts AND wipes
    # ``state/`` — unlike the factory arm's rebuilt root, the bare arm's
    # ledger lives directly under run_dir and would accumulate Run rows
    # across re-runs, inflating the sum-all totals the audit certifies.
    _reset_run_artifacts(run_dir)
    if not _ensure_image(inst):
        raise SystemExit(
            f"image for {instance_id} is unavailable; the bare arm's test "
            "command runs inside it (see instance_test_command)"
        )
    # OUTSIDE the repo. The arm's shell runs with cwd inside this clone, and at
    # `runs/<id>/bare/repo` that was three `..` from `bench/swebench/
    # oracle.json.z` and one from every other arm's `grade.log`. `state/` stays
    # under `run_dir` — it is where `audit` reads the ledger from and is no
    # longer an ancestor of the agent's cwd.
    repo = _work_dir(instance_id, "bare", fresh=True) / "repo"
    _clone(inst, repo)
    assert_workspace_isolated(repo)
    # Same topology as the factory arm and the selftest control: replay the
    # dataset's install/build step so the test command handed to the model
    # below actually collects from this clone (rebench-only; Pro is a no-op).
    # Fresh unprepared clones lose build-generated artifacts and die at
    # collect — handing the model a command that cannot run would be the same
    # broken-tool class this fix removes. Failing here costs $0.
    prep_error = _prepare_cloned_tree(inst, repo)
    if prep_error:
        raise SystemExit(f"prepare: {prep_error}")

    # THE SAME PRE-DISPATCH COLLECT GATE the factory and claude arms pass. The
    # bare arm had none, so it was the one arm that could be handed a test
    # command that cannot run and still burn its whole budget against it.
    # Failing here costs $0.
    precheck = _precheck_collect(inst, repo)
    collect_tail = str(precheck.pop("tail", ""))
    if not precheck["collect_ok"]:
        error = f"precheck: test command does not collect: {collect_tail[-400:]}"
        _write_result(
            instance_id,
            "bare",
            {
                "arm": "bare",
                "instance_id": instance_id,
                "repo": inst["repo"],
                "base_commit": inst["base_commit"],
                "problem_statement_sha256": inst["problem_statement_sha256"],
                "manifest_sha256": _manifest()["manifest_sha256"],
                "ts": datetime.now(UTC).isoformat(),
                "wall_clock_s": round(time.monotonic() - entered, 1),
                "error": error,
                "factory_says_green": None,
                "precheck": {**precheck, "tail": collect_tail[-1500:]},
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "persona_calls": 0,
                **_no_model_mix(),
            },
        )
        raise SystemExit(error)

    sys.path.insert(0, str(FACTORY_ROOT))
    from factory.model_router import route
    from factory.runner import text_run as _text_run

    model = route("dev", "standard")
    text_run = _probe_text_run() if probe else _text_run
    transcript: list[dict[str, Any]] = []
    tokens_in = tokens_out = 0
    cost = 0.0
    started = time.monotonic()
    error: str | None = None
    cmd_log = run_dir / "bare-commands.ndjson"

    def _log_step(row: dict[str, Any]) -> None:
        """One line per turn in ``bare-commands.ndjson``, UNTRUNCATED.

        The command log used to hold commands only, so reconstructing what the
        arm actually SAW meant cross-referencing ``prompt_bodies.ndjson`` by
        hand; ``result.json["transcript"]`` keeps 20 steps of 300-char commands
        and no output at all. The observation now lands here too, which also
        means the audit's oracle-probe scan sees command OUTPUT — previously a
        probe's result was invisible to it.
        """
        with cmd_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")

    # A REAL role-tagged conversation. ``prefix`` is pinned for the whole run;
    # only ``turns`` slides. Assistant turns carry the PARSED COMMAND, never
    # the model's raw reply — that is what makes a fabricated observation
    # unrepresentable in the context rather than merely discouraged.
    prefix: list[dict[str, str]] = [
        {"role": "system", "content": _BARE_SYSTEM},
        {
            "role": "user",
            "content": _BARE_TASK.format(
                repo=inst["repo"],
                statement=inst["problem_statement"],
                # SAME derivation, SAME call shape as the factory story
                # template (_STORY_TEMPLATE): no privileged targets. A bare arm
                # with no way to run tests measures verification, not scaffold
                # lift — 0 of 19 first-sweep bare runs ever invoked pytest.
                test_command=instance_test_command(inst, repo=repo),
            ),
        },
    ]
    turns: list[dict[str, str]] = []
    steps = min(max_steps, _BARE_STEP_CAP)
    done_nudges = 0
    done_empty_diff = False
    # Why the loop stopped. Recorded because "steps_used < step_cap" is
    # ambiguous on its own — a run that said DONE at step 6 and a run whose
    # model call blew up at step 6 look identical in the old artifact.
    termination = "step-cap"
    for step in range(steps):
        if time.monotonic() - started > timeout_s:
            error = f"wall-clock cap {timeout_s}s hit"
            termination = "wall-clock-cap"
            break
        messages = prefix + turns[-_BARE_HISTORY_TURNS:]
        try:
            reply = str(
                text_run(
                    persona="dev",
                    # ``prompt`` remains the telemetry view of the call (prompt
                    # bodies, hashes); ``messages`` is what goes on the wire.
                    prompt="\n\n".join(m["content"] for m in messages),
                    messages=messages,
                    model_id=model,
                    story_id=None,
                    software_factory_root=run_dir,
                    db_path=run_dir / "state" / "factory.db",
                )
            )
        except Exception as exc:  # noqa: BLE001
            error = f"model call failed at step {step}: {type(exc).__name__}: {exc}"
            termination = "model-call-error"
            break

        command = _parse_bash(reply)
        if command is None:
            # DONE is only considered once no command was found, so a reply
            # that both patches a file and says "then reply DONE" runs the
            # command instead of terminating (the old ``"BASH" not in reply``
            # test made that ordering accidental).
            if re.search(r"\bDONE\b", reply):
                empty_reason = _bare_empty_diff_reason(repo)
                if empty_reason is None or done_nudges >= _BARE_DONE_NUDGES:
                    done_empty_diff = empty_reason is not None
                    termination = (
                        "done-empty-diff" if done_empty_diff else "done"
                    )
                    transcript.append(
                        {"step": step, "action": "done", "empty_diff": done_empty_diff}
                    )
                    _log_step(
                        {"step": step, "action": "done", "empty_diff": done_empty_diff}
                    )
                    break
                # DONE with nothing to grade is not done. 6 of 19 measured rows
                # (32%) shipped a 0-byte diff, one of them after REVERTING its
                # own correct fix. Bounded by _BARE_DONE_NUDGES (< the repo's
                # hard cap of 3) so this can never become a loop.
                done_nudges += 1
                turns.append({"role": "assistant", "content": "DONE"})
                turns.append({"role": "user", "content": empty_reason})
                transcript.append(
                    {"step": step, "action": "done_rejected_empty_diff"}
                )
                _log_step({"step": step, "action": "done_rejected_empty_diff"})
                continue
            turns.append(
                {
                    "role": "assistant",
                    # NOT ``reply``: the raw text is the fabrication vector.
                    "content": "(no runnable command in my last reply)",
                }
            )
            turns.append(
                {
                    "role": "user",
                    "content": (
                        "That reply contained no command. Reply with a BASH "
                        "block (or a ```bash fenced block) containing exactly "
                        "one shell command, or DONE."
                    ),
                }
            )
            transcript.append({"step": step, "action": "invalid", "reply": reply[:200]})
            _log_step({"step": step, "action": "invalid"})
            continue

        exit_code, output = _bare_exec(command, repo)
        # ``None`` means the command never produced a status (timeout / could not
        # start), so there is no exit code to report and claiming "Exit None"
        # would be one more thing for the model to misread.
        observation = (
            f"Exit {exit_code}. Output:\n{output}"
            if exit_code is not None
            else f"No exit status: {output}"
        )
        turns.append({"role": "assistant", "content": f"BASH\n{command}"})
        turns.append({"role": "user", "content": observation})
        _log_step(
            {"step": step, "command": command, "exit": exit_code, "output": output}
        )
        transcript.append(
            {
                "step": step,
                "action": "bash",
                "command": command[:300],
                "exit": exit_code,
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

    if probe:
        # FAIL-CLOSED: a probe row carries a recorded ``error``, so `report`
        # buckets it as a failed run and it can never reach a headline. The
        # operator re-runs the instance for real; ``_reset_run_artifacts``
        # wipes this row at the top of that run.
        error = _PROBE_ERROR

    result = {
        "arm": "bare",
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "problem_statement_sha256": inst["problem_statement_sha256"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        "model": model,
        # WHICH WEIGHTS ACTUALLY RAN, measured from this run's own ledger —
        # never assumed from the route above. See ``_model_mix``.
        **_model_mix(run_dir / "state" / "events", nominal=model),
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "steps_used": len(transcript),
        "step_cap": steps,
        "termination": termination,
        "done_with_empty_diff": done_empty_diff,
        "done_nudges": done_nudges,
        "trajectory": cmd_log.name,
        "probe_plumbing": probe,
        "precheck": precheck,
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
    _print_run_summary(result, out)


# The one-screen answer to "did that run do anything?". A single run used to
# print one line naming result.json, so an EMPTY diff — 6 of 19 measured rows —
# was silent unless somebody opened the JSON. Every arm prints this.
def _print_run_summary(result: dict[str, Any], out: Path) -> None:
    arm = result.get("arm")
    steps = result.get("steps_used", result.get("num_turns"))
    cap = result.get("step_cap", result.get("turn_cap"))
    files = result.get("files_changed") or []
    diff_bytes = int(result.get("diff_bytes") or 0)
    models = result.get("models_used") or []
    escalated = int(result.get("model_escalated_calls") or 0)
    print("")
    print(f"=== {arm} arm: {result.get('instance_id')} ===")
    print(f"  model (nominal)  : {result.get('model')}")
    print(
        f"  models used      : {', '.join(str(m) for m in models) or '(ledger empty)'}"
        + (f"   [{escalated} call(s) OFF the nominal model]" if escalated else "")
    )
    print(f"  steps used / cap : {steps} / {cap}")
    print(f"  terminated by    : {result.get('termination')}")
    print(f"  wall clock       : {result.get('wall_clock_s')}s")
    print(
        f"  spend            : ${result.get('cost_usd')} "
        f"({result.get('persona_calls')} model call(s))"
    )
    print(f"  graded diff      : {diff_bytes} bytes across {len(files)} file(s)")
    for f in files[:10]:
        print(f"      {f}")
    if result.get("test_files_stripped"):
        print(f"  test edits stripped: {result['test_files_stripped']}")
    if diff_bytes == 0:
        print(
            "  *** EMPTY DIFF — this run produced NOTHING to grade. It will be "
            "graded as unresolved no matter what the model said. ***"
        )
    if result.get("error"):
        print(f"  error            : {result['error']}")
    print(f"  trajectory       : {result.get('trajectory')}")
    print(f"  result           : {out}")


def _bare_exec(command: str, repo: Path) -> tuple[int | None, str]:
    """Run ONE command in the arm's tree; never raise.

    ``subprocess.run(..., timeout=300)`` had no handler, so a single slow
    ``docker run … pytest`` raised ``TimeoutExpired`` straight out of
    ``run_bare`` and killed the whole run — no ``result.json``, no
    ``prediction.diff``, and a sweep row reading "run_failed" for work the
    model may well have completed. A timeout is an observation, not a crash:
    the model is told, and gets its next turn.

    The command runs in its own session so the kill on timeout reaches the
    whole tree (``bash -lc 'docker run …'`` spawns children; killing only the
    shell leaves them holding the mount).
    """
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(  # noqa: S603
            ["bash", "-lc", command],
            cwd=str(repo),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        out, err = proc.communicate(timeout=_BARE_CMD_TIMEOUT_S)
        return proc.returncode, ((out or "") + (err or ""))[-_BARE_OUTPUT_CAP:]
    except subprocess.TimeoutExpired:
        if proc is not None:
            _kill_tree(proc)
            with contextlib.suppress(Exception):
                proc.communicate(timeout=30)
        return None, (
            f"command timed out after {_BARE_CMD_TIMEOUT_S}s and was killed. "
            "Nothing it printed was captured. Try a narrower command."
        )
    except OSError as exc:
        return None, f"command could not be started: {type(exc).__name__}: {exc}"


def _changed_paths(repo: Path) -> list[str]:
    """Every path ``git status --porcelain`` reports as changed or untracked.

    Deliberately NOT ``_capture_diff``: that stages the whole tree (``git add
    -A``) as a side effect, and this runs MID-RUN, so it would silently empty
    the model's next ``git diff``. Porcelain status compares content, so a file
    that was edited and then restored byte-for-byte — the measured
    ``ucfopen__canvasapi-716`` failure, where the arm reverted its own correct
    fix out of the docker image — reads as unchanged here, which is exactly the
    verdict the grader would reach.
    """
    # ``-uall`` expands untracked DIRECTORIES into their files. Without it git
    # reports a whole new directory as one entry (``?? newpkg/``), and a
    # directory name is not a test path — so a tree holding nothing but a new
    # directory of tests would have read as a production change.
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "-uall"],
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if len(line) < 4:
            continue
        entry = line[3:].strip()
        # Renames/copies are reported as ``old -> new``; the new path is the
        # one that carries content.
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            paths.append(entry)
    return paths


def _bare_empty_diff_reason(repo: Path) -> str | None:
    """``None`` when the tree has something to grade; the nudge text otherwise.

    ``DONE`` used to be accepted unconditionally, and 6 of 19 measured rows
    (32%) shipped a 0-byte diff — including one that wrote a correct fix, saw a
    pre-existing test assert the OLD behaviour, restored the original file out
    of the docker image and declared DONE. An arm that says "done" with nothing
    in the tree has not produced a measurement of the model; it has produced a
    measurement of this loop.

    Test-only changes count as empty, because ``split_diff`` strips them before
    grading — the same ``is_test_path`` predicate decides both, so this can
    never disagree with the graded prediction about what survives.
    """
    changed = _changed_paths(repo)
    code = [p for p in changed if not is_test_path(p)]
    if code:
        return None
    detail = (
        " Your only changes are to test files, and test edits are stripped from "
        "the diff before grading."
        if changed
        else ""
    )
    return (
        "Not done: this working tree contains no production-code changes, so "
        f"the diff that gets graded would be EMPTY.{detail} Either nothing you "
        "described was ever written to a file, or it was reverted. Make the "
        "production-code edit, verify it, then reply DONE."
    )


# The command starts after the first line that is exactly "BASH" …
_BASH_MARKER = re.compile(r"^\s*BASH\s*$")
# … and ends at the first line that opens ANOTHER block (BASH/DONE), closes a
# code fence, or looks like a fabricated observation. The old greedy regex
# captured to end-of-reply, so when the model hallucinated a whole transcript
# ("Exit 0. Output:\nimport collections…\nBASH\npytest …") the fabricated
# tail was executed as real shell — one measured run executed 4 fabricated
# commands while its actual patch script was written but never run.
#
# ``Exit code: N`` and ``Result:`` are here because the two forms the old
# pattern caught were not the only two the model produces: 76 of 231 measured
# replies contained a fabricated observation line, and two of those shapes slid
# straight through into the executed command.
_BARE_STOP = re.compile(
    r"^\s*(?:BASH|DONE)\s*$"     # a second block: only the FIRST is executed
    r"|^\s*```"                  # closing/next code fence
    r"|^\s*Exit\s+-?\d+\b"       # hallucinated exit status
    r"|^\s*Exit\s+code\s*:"      # … the other spelling of it
    r"|^\s*Output\s*:"           # hallucinated command output
    r"|^\s*Result\s*:"           # … and the other spelling of that
)

# deepseek's native shape is fenced markdown, not a bespoke marker. 12 of 231
# measured replies were a plain ```bash fence with no BASH line and were thrown
# away as "Invalid reply" (34 replies had no marker at all), burning turns on
# protocol tax rather than on the task. A fenced shell block is accepted as
# equivalent to the marker form. The language tag is required: an untagged
# fence is as likely to be Python, a diff, or pasted output.
_BARE_FENCE = re.compile(
    r"^[ \t]*```[ \t]*(?:bash|sh|shell|console|zsh)[ \t]*\n(?P<body>.*?)(?:^[ \t]*```|\Z)",
    re.S | re.M,
)


def _parse_bash(reply: str) -> str | None:
    """Extract exactly ONE command: the first BASH block (or, failing that, the
    first fenced shell block), minus any model-fabricated 'observations'.
    Truncating mid-heredoc on a fabricated line is fail-safe — bash errors, the
    model sees it, and retries."""
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text)
    lines = text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if _BASH_MARKER.match(line):
            start = i + 1
            break
    if start is None:
        return _fenced_command(reply)
    # An inner fence directly under the marker wraps the command; skip it and
    # let the fence rule in _BARE_STOP terminate the block.
    if start < len(lines) and lines[start].lstrip().startswith("```"):
        start += 1
    return _until_fabrication(lines[start:])


def _fenced_command(reply: str) -> str | None:
    """The first fenced shell block's body, same fabrication rules applied."""
    m = _BARE_FENCE.search(reply)
    if m is None:
        return None
    return _until_fabrication(m.group("body").splitlines())


def _until_fabrication(lines: list[str]) -> str | None:
    """Join ``lines`` up to the first line that opens another block, closes a
    fence, or fabricates an observation."""
    cmd_lines: list[str] = []
    for line in lines:
        if _BARE_STOP.match(line):
            break
        cmd_lines.append(line)
    cmd = "\n".join(cmd_lines).strip()
    return cmd or None


# --------------------------------------------------------------------------- #
# the arm registry — ONE table, every arm, every per-arm budget and guard
# --------------------------------------------------------------------------- #
#
# Why a registry and not four `if arm == ...` chains. Adding the fifth arm
# (the Claude CLI a second time, on an older-cutoff model) touched, in the old
# shape: `_ARM_NAMES`, three separate argparse `choices=`, `_resolve_max_steps`,
# `_DEFAULT_COST_USD`, `_DEFAULT_HOURS` and `_ARM_TRAJECTORY_EXPECTATION` — six
# places, three of which FELL BACK SILENTLY on an unknown key. A new arm
# silently inheriting the factory's 16-tick cap and a wrong cost guard is
# exactly how a sweep produces a table nobody can interpret. Every lookup below
# is fail-loud, and the argparse choices are derived, so registering an arm is
# a one-entry change.

# The factory dev's own per-attempt iteration budget (``sandbox_run``'s
# signature default; ``dev`` is deliberately NOT in
# ``factory.runner.PERSONA_ITERATION_CAPS``). Matching it exactly is the point:
# the openhands arm must be the factory's dev agent MINUS the chain, so its
# inner budget cannot be the thing that explains a difference. The factory arm
# may open up to three such conversations across its 16 ticks; in practice the
# shared 5400 s wall clock binds first for both (measured factory wall clocks:
# 98-3400 s).
_OPENHANDS_ITERATION_CAP = 600

# Pinned EXPLICITLY (the operator wants the models named). Discovered
# 2026-08-02 by running the CLI (v2.1.220) with no --model: the default
# resolved to ``claude-opus-5[1m]`` (canonical ``claude-opus-5``; the ``[1m]``
# suffix is only the 1M-context variant of the same weights). The canonical id
# is pinned; the ids the CLI actually reports land in result.json
# (``model_reported``, ``models_observed``) so the record is the CLI's own,
# not this constant's claim.
_CLAUDE_MODEL = "claude-opus-5"

# The contamination probe's twin: the SAME CLI, the same flags, an older
# published cutoff (2026-01-31 vs 2026-05-31). Every pinned instance predates
# opus-5's cutoff, so a gap favouring opus-5 on the low-margin rows is the
# memorization signal.
_CLAUDE_MODEL_OLD = "claude-opus-4-8"

# Generous but bounded (CLAUDE.md: nothing loops without a cap). ``--max-turns``
# is accepted by CLI 2.1.220 (hidden from --help but validated: an unknown
# option fails argv parsing immediately, this one does not). The wall clock is
# the second bound, via the run's existing ``timeout_s``.
_CLAUDE_TURN_CAP = 60

_CLAUDE_TRANSCRIPT_NAME = "claude-transcript.ndjson"

# Cost-column provenance, printed per arm in the report. The two are NOT
# comparable and must never be summed: the Azure arms' dollars are derived from
# a price table over measured tokens, the Claude arms' are the CLI's own report
# against a subscription.
_COST_PRICE_TABLE = "price-table estimate"
_COST_CLI_SUBSCRIPTION = "CLI-reported, subscription"

_TRAJECTORIES_PER_DEV_CALL = "per-call"
_TRAJECTORIES_AT_LEAST_ONE = "at-least-one"
_TRAJECTORIES_NONE_EXPECTED = "none"
_TRAJECTORIES_TRANSCRIPT = "transcript"


class ArmSpec(NamedTuple):
    """Everything the harness needs to know about one arm.

    ``harness`` and ``model`` are BOTH load-bearing: an arm is a (harness,
    model set) pair, and no number from this bench may be quoted with either
    half omitted (see ``bench/swebench/PRE-REGISTRATION-1.6.md``). The report
    prints both inline on every headline row for exactly that reason.
    """

    name: str  # the id passed to --arm, and the run-dir name
    base: str  # which runner family: factory | bare | claude | openhands
    harness: str  # human label, printed in the report's headline table
    harness_id: str  # comparisons key: same id => the harness is held constant
    model: str | None  # the arm's nominal model; None => resolved from routes
    model_selectable: bool  # may --model override it?
    max_steps: int  # the arm's own step/tick/turn/iteration budget
    step_unit: str  # what one "step" IS for this arm (units differ per arm)
    default_cost_usd: float  # spend-guard fallback with no measured runs
    default_hours: float
    trajectories: str  # _TRAJECTORIES_*
    cost_source: str  # _COST_*
    has_chain: bool  # can this arm produce a chain verdict at all?


def _arm(**kw: Any) -> ArmSpec:
    return ArmSpec(**kw)


_ARMS: dict[str, ArmSpec] = {
    "factory": _arm(
        name="factory",
        base="factory",
        harness="software-factory chain on OpenHands",
        harness_id="software-factory",
        model=None,  # routes.yaml resolves dev/standard; the LEDGER is the record
        model_selectable=False,
        max_steps=_FACTORY_STEP_DEFAULT,
        step_unit="orchestrator ticks",
        default_cost_usd=3.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_PER_DEV_CALL,
        cost_source=_COST_PRICE_TABLE,
        has_chain=True,
    ),
    "openhands": _arm(
        name="openhands",
        base="openhands",
        harness="OpenHands single agent, no chain",
        harness_id="openhands",
        model=None,  # the factory dev's own deployment, from routes.yaml
        model_selectable=False,
        max_steps=_OPENHANDS_ITERATION_CAP,
        step_unit="agent iterations",
        # NOT the bare arm's $1.00: it runs the same deployment with the same
        # real tool loop the factory's dev uses, so its token profile is a dev
        # attempt's, not a 40-turn shell loop's.
        default_cost_usd=3.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_AT_LEAST_ONE,
        cost_source=_COST_PRICE_TABLE,
        has_chain=False,
    ),
    "bare": _arm(
        name="bare",
        base="bare",
        harness="hand-rolled text loop, no tool calls",
        harness_id="bare-loop",
        model=None,
        model_selectable=False,
        max_steps=_BARE_STEP_CAP,
        step_unit="shell turns",
        default_cost_usd=1.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_NONE_EXPECTED,
        cost_source=_COST_PRICE_TABLE,
        has_chain=False,
    ),
    # THREE claude entries, one runner. `claude` is the back-compatible name
    # (default model unchanged); `claude-5` and `claude-4.8` are the
    # pre-registered five-arm ids, so the sweep needs no --model at all and the
    # two runs land in DIFFERENT run dirs by construction.
    "claude": _arm(
        name="claude",
        base="claude",
        harness="Claude Code CLI",
        harness_id="claude-code",
        model=_CLAUDE_MODEL,
        model_selectable=True,
        max_steps=_CLAUDE_TURN_CAP,
        step_unit="CLI turns",
        default_cost_usd=3.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_TRANSCRIPT,
        cost_source=_COST_CLI_SUBSCRIPTION,
        has_chain=False,
    ),
    "claude-5": _arm(
        name="claude-5",
        base="claude",
        harness="Claude Code CLI",
        harness_id="claude-code",
        model=_CLAUDE_MODEL,
        model_selectable=True,
        max_steps=_CLAUDE_TURN_CAP,
        step_unit="CLI turns",
        default_cost_usd=3.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_TRANSCRIPT,
        cost_source=_COST_CLI_SUBSCRIPTION,
        has_chain=False,
    ),
    "claude-4.8": _arm(
        name="claude-4.8",
        base="claude",
        harness="Claude Code CLI",
        harness_id="claude-code",
        model=_CLAUDE_MODEL_OLD,
        model_selectable=True,
        max_steps=_CLAUDE_TURN_CAP,
        step_unit="CLI turns",
        default_cost_usd=3.00,
        default_hours=0.05,
        trajectories=_TRAJECTORIES_TRANSCRIPT,
        cost_source=_COST_CLI_SUBSCRIPTION,
        has_chain=False,
    ),
}

# Every arm this harness knows, derived — the oracle-probe scanner and all
# three argparse `choices=` read this, so a registry entry is the only edit
# needed to add an arm.
_ARM_NAMES = tuple(_ARMS)

# Separates an arm id from a NON-default model in a run key. Chosen over ``-``
# so the claude-prefix recognition in ``_is_claude_arm`` keeps working, and
# over ``/`` because a run key is a single directory name.
_ARM_MODEL_SEP = "@"


def _split_run_key(key: str) -> tuple[str, str | None]:
    """``"claude@claude-opus-4-8"`` -> ``("claude", "claude-opus-4-8")``.

    A key with no separator is a bare arm id and carries no model override.
    """
    arm, sep, model = key.partition(_ARM_MODEL_SEP)
    return arm, (model or None) if sep else None


def arm_spec(arm: str) -> ArmSpec:
    """The registry entry for an arm id or a run key. FAIL LOUD on unknown.

    The three lookups this replaces (`_resolve_max_steps`, `_DEFAULT_COST_USD`,
    `_DEFAULT_HOURS`) all fell back silently, so a typo'd or newly added arm
    inherited the factory's tick cap and a wrong cost guard and produced a row
    nobody could interpret. An unknown arm is a configuration error, not a
    default.
    """
    base, _model = _split_run_key(arm)
    try:
        return _ARMS[base]
    except KeyError:
        raise SystemExit(
            f"unknown arm {arm!r}. Registered arms: {', '.join(sorted(_ARMS))}. "
            "Add an entry to _ARMS (one place) rather than special-casing a "
            "name — every per-arm budget, cost guard and gate reads that table."
        ) from None


def resolve_arm_model(arm: str, model: str | None = None) -> str | None:
    """The model id this (arm, --model) pair will actually run.

    ``None`` means "this arm resolves its own weights from ``routes.yaml``" —
    the factory/openhands/bare arms, whose real mix is measured from the
    per-run ledger (``_model_mix``), never claimed by a constant here.
    """
    spec = arm_spec(arm)
    _base, keyed = _split_run_key(arm)
    requested = model or keyed
    if requested is None:
        return spec.model
    if not spec.model_selectable:
        raise SystemExit(
            f"--model is not accepted for --arm {arm}: this arm resolves its "
            "weights from routes.yaml, and pinning one here would report a "
            "model the run did not necessarily use. Change routes.yaml instead."
        )
    return requested


def run_key(arm: str, model: str | None = None) -> str:
    """The per-(instance, arm, MODEL) key: run dir, report row and sweep row.

    SILENT DATA LOSS this closes: the key used to be ``(instance, arm)``, so the
    two pre-registered Claude runs — same CLI, ``claude-opus-5`` and
    ``claude-opus-4-8`` — resolved to the SAME ``runs/<instance>/claude``
    directory. The second run's ``_reset_run_artifacts`` would delete the
    first's ``result.json``, ``prediction.diff`` and transcript, and the report
    would show one row where two runs happened. Nothing anywhere would have
    said a measurement had been destroyed.

    The default model keeps the plain arm id, so ``claude-5``/``claude-4.8``
    (and every existing archive) are unchanged; only an explicit off-default
    ``--model`` appends ``@<model>``.
    """
    spec = arm_spec(arm)
    base, _keyed = _split_run_key(arm)
    resolved = resolve_arm_model(arm, model)
    if resolved is None or resolved == spec.model:
        return base
    return f"{base}{_ARM_MODEL_SEP}{resolved}"


# --------------------------------------------------------------------------- #
# claude arm — the local Claude Code CLI, headless and hermetic
# --------------------------------------------------------------------------- #

# Appended AFTER the shared story template. Mirrors the bare arm's "You cannot
# access the network" rule — for this arm it is the contamination control in
# prose form (the flag form is ``--disallowedTools WebFetch WebSearch``):
# swe-rebench instances are post-cutoff PRs on public GitHub, so any web or
# git-remote access is one search away from the gold patch.
_CLAUDE_RULES = """
## Constraints

- Work only inside this repository checkout.
- Do not access the network: no web browsing, no fetching from remotes. The
  fix and its judge live entirely in this checkout and the test command above.
"""


def _claude_task_prompt(inst: dict[str, Any], repo: Path) -> str:
    """The claude arm's task, built from the SAME template the factory dev gets.

    ``_STORY_TEMPLATE`` (statement + definition of done + the test-edits-are-
    stripped note + the exact in-image test command) is the single source, so
    no arm gets privileged wording. The only addition is ``_CLAUDE_RULES`` —
    the no-network rule the bare arm's system prompt already carries.
    """
    return (
        _STORY_TEMPLATE.format(
            instance_id=inst["instance_id"],
            statement=inst["problem_statement"],
            test_command=instance_test_command(inst, repo=repo),
        )
        + _CLAUDE_RULES
    )


def _claude_cli_argv(prompt: str, *, model: str, max_turns: int) -> list[str]:
    """The headless CLI invocation. Every flag is load-bearing; validated live
    on CLI 2.1.220 (1-turn smoke tests, 2026-08-02) before being wired here.

    Hermeticity — the dogfooding hazard: this harness runs on the machine
    where Claude Code is the operator's daily driver, so the child must not
    inherit this user's MCP servers, skills, hooks, memory or project state:

    * ``--safe-mode``    — all customizations (CLAUDE.md, skills, plugins,
      hooks, MCP, custom agents) disabled; auth and built-in tools normal.
    * ``--strict-mcp-config`` with no ``--mcp-config`` — zero MCP servers,
      even policy-injected ones (verified: init event reports
      ``mcp_servers: []``).
    * ``--setting-sources ""`` — no user/project/local settings files load at
      all (belt and braces under --safe-mode).
    * ``--disallowedTools WebFetch WebSearch`` — the contamination control:
      the instances are post-cutoff public-GitHub PRs, so web access is
      answer leakage (verified: neither tool appears in the init tool list).
    * ``--no-session-persistence`` — nothing written to the operator's
      session store; project state is keyed by cwd anyway and the cwd is a
      fresh clone.
    * ``--dangerously-skip-permissions`` — headless runs cannot answer
      permission prompts; the blast radius is the isolated clone.
    * ``--output-format stream-json --verbose`` — the full session transcript
      (assistant turns, tool calls, tool results, usage, cost) on stdout;
      persisted as the arm's trajectory equivalent and scanned by the audit's
      oracle probe. ``--verbose`` is REQUIRED by the CLI for stream-json in
      -p mode.
    """
    return [
        "claude",
        "-p", prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--output-format", "stream-json",
        "--verbose",
        "--safe-mode",
        "--strict-mcp-config",
        "--setting-sources", "",
        "--disallowedTools", "WebFetch", "WebSearch",
        "--no-session-persistence",
        "--dangerously-skip-permissions",
    ]


def _claude_child_env() -> dict[str, str]:
    """The child CLI's environment: HOME kept (its stored login IS the auth),
    everything Claude/Anthropic-shaped dropped.

    * ``CLAUDE*`` (CLAUDECODE, CLAUDE_CODE_*): this harness is routinely run
      FROM a Claude Code session, and a child that inherits those thinks it is
      nested inside it — the dogfooding hazard again.
    * ``ANTHROPIC_*`` (the factory ``.env`` exports ANTHROPIC_API_KEY, and
      ``_load_env`` puts it in os.environ): an env key would silently switch
      the child's auth/billing away from the operator's logged-in
      subscription, and ANTHROPIC_BASE_URL/_MODEL would redirect it entirely.
      The smoke-tested, working path is the CLI's own stored claude.ai login.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if not (k.startswith("CLAUDE") or k.startswith("ANTHROPIC"))
        and k != "FACTORY_STATE_ROOT"
    }


def _claude_cli_version() -> str | None:
    try:
        proc = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=60
        )
        return (proc.stdout or "").strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _parse_claude_transcript(
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """``(init_event, result_event, fallback_token_sums)`` from a stream-json
    transcript. Tolerant of a truncated stream (a timeout kill ends the file
    mid-run, before the final ``result`` event).

    The fallback sums come from the per-message ``usage`` on assistant events,
    deduplicated by message id (one message can span several stream events);
    they exist so a killed run still reports real token counts. They carry no
    cost — the CLI prices its own usage in the ``result`` event and nowhere
    else, and this harness does not maintain an Anthropic price table.
    """
    init: dict[str, Any] = {}
    result: dict[str, Any] = {}
    per_msg: dict[str, dict[str, int]] = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(ev, dict):
                    continue
                if ev.get("type") == "system" and ev.get("subtype") == "init" and not init:
                    init = ev
                elif ev.get("type") == "assistant":
                    msg = ev.get("message") or {}
                    usage = msg.get("usage") or {}
                    if isinstance(msg, dict) and isinstance(usage, dict):
                        per_msg[str(msg.get("id"))] = {
                            "tokens_in": int(usage.get("input_tokens") or 0)
                            + int(usage.get("cache_creation_input_tokens") or 0)
                            + int(usage.get("cache_read_input_tokens") or 0),
                            "tokens_out": int(usage.get("output_tokens") or 0),
                            "cache_read": int(usage.get("cache_read_input_tokens") or 0),
                        }
                elif ev.get("type") == "result":
                    result = ev
    except OSError:
        pass
    sums = {
        "tokens_in": sum(u["tokens_in"] for u in per_msg.values()),
        "tokens_out": sum(u["tokens_out"] for u in per_msg.values()),
        "cache_read": sum(u["cache_read"] for u in per_msg.values()),
    }
    return init, result, sums


def _claude_usage_totals(result_ev: dict[str, Any]) -> dict[str, int] | None:
    """Token totals over EVERY model the CLI used, from the result event's
    ``modelUsage`` — which includes side calls (e.g. the haiku auto-mode
    classifier) that the top-level ``usage`` block omits. ``tokens_in`` is
    TOTAL input processed (raw + cache-read + cache-creation), matching what
    the other arms' ledgers mean by it; the cached subset is kept separately.
    """
    mu = result_ev.get("modelUsage")
    if not isinstance(mu, dict) or not mu:
        return None
    vals = [v for v in mu.values() if isinstance(v, dict)]
    return {
        "tokens_in": sum(
            int(v.get("inputTokens") or 0)
            + int(v.get("cacheReadInputTokens") or 0)
            + int(v.get("cacheCreationInputTokens") or 0)
            for v in vals
        ),
        "tokens_out": sum(int(v.get("outputTokens") or 0) for v in vals),
        "cache_read": sum(int(v.get("cacheReadInputTokens") or 0) for v in vals),
    }


def run_claude(
    instance_id: str,
    *,
    max_steps: int,
    timeout_s: int,
    arm: str = "claude",
    model: str | None = None,
    probe: bool = False,
) -> None:
    """Drive the LOCAL Claude Code CLI, headless, over one instance.

    The third arm: factory (harnessed cheap models) vs bare (same weights, no
    harness) vs claude (the frontier tool the factory's thesis is measured
    against). Preparation is IDENTICAL to the other arms — pinned-manifest
    clone at base_commit with ``--depth 1``, the profile's install/topology
    replay, the pre-dispatch collect gate — so the only variable is the agent.

    Hidden-oracle discipline: the CLI runs with cwd = the clone and sees only
    the shared story template. It never sees test_patch/fail_to_pass or the
    oracle store, has no MCP servers, no web tools, and none of the operator's
    config (see ``_claude_cli_argv``). Its full stream-json transcript is
    persisted as ``claude-transcript.ndjson`` and the audit scans it for
    oracle/manifest path references exactly like the bare arm's command log.

    Spend: bills the operator's Anthropic subscription/API — NOT the Azure
    ledger, and invisible to the factory's own spend enforcer. cost/tokens are
    the CLI's own report (``cost_source: "claude-cli-reported"``).

    ``probe=True`` (``--probe-plumbing``) does everything except SPAWN the CLI:
    the clone, the install replay, the collect precheck, the prompt assembly,
    the hermetic argv, the CLI version probe, the run-dir key, then a real
    non-test file change so the diff/split/assert/write path runs end to end.
    It costs nothing, and the row it writes carries a recorded ``error`` so no
    rate can absorb it. Without it the only free-ish check on these arms was a
    one-turn CLI call, which is still a subscription call.
    """
    entered = time.monotonic()
    inst = _instance(instance_id)
    # A run the store cannot grade is a write-off — refuse before any spend.
    _assert_oracle_store_complete([inst])
    # (instance, arm, MODEL) — never (instance, arm). The two pre-registered
    # Claude runs are the SAME arm on two models; a model-blind key made the
    # second overwrite the first (see `run_key`).
    resolved_model = resolve_arm_model(arm, model)
    assert resolved_model is not None  # the claude arms always name a model
    key = run_key(arm, model)
    run_dir = _run_dir(instance_id, key)
    # BEFORE any exit path: a stale prediction/transcript must never outlive
    # the run that produced it.
    _reset_run_artifacts(run_dir)
    base: dict[str, Any] = {
        "arm": key,
        "arm_base": arm_spec(arm).base,
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "problem_statement_sha256": inst["problem_statement_sha256"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        # The model this run was POINTED at. What the CLI actually reports lands
        # in ``model_reported`` / ``models_observed`` below; the report reads
        # those, never this.
        "model": resolved_model,
        "claude_cli_version": _claude_cli_version(),
    }

    def _fail(error: str, **extra: Any) -> None:
        _write_result(
            instance_id,
            key,
            {
                **base,
                "ts": datetime.now(UTC).isoformat(),
                "wall_clock_s": round(time.monotonic() - entered, 1),
                "error": error,
                "factory_says_green": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "cost_source": "claude-cli-reported",
                **extra,
            },
        )
        raise SystemExit(error)

    if not _ensure_image(inst):
        _fail(
            f"image for {instance_id} is unavailable; the claude arm's test "
            "command runs inside it (see instance_test_command)"
        )
    # OUTSIDE the repo: the CLI's cwd is this tree, and as
    # `runs/<id>/claude/repo` it was three `..` from the oracle store and from
    # every other arm's grade log.
    repo = _work_dir(instance_id, key, fresh=True) / "repo"
    assert_workspace_isolated(repo)
    _clone(inst, repo)
    # Same topology as the other arms: replay the dataset's install/build step
    # so the tree the CLI edits matches the tree the grade mounts.
    prep_error = _prepare_cloned_tree(inst, repo)
    if prep_error:
        _fail(f"prepare: {prep_error}")

    # PRE-DISPATCH COLLECT GATE — the same gate the other arms pass before a
    # single model token is spent.
    precheck = _precheck_collect(inst, repo)
    collect_tail = str(precheck.pop("tail", ""))
    if not precheck["collect_ok"]:
        _fail(
            f"precheck: test command does not collect: {collect_tail[-400:]}",
            precheck={**precheck, "tail": collect_tail[-1500:]},
        )

    prompt = _claude_task_prompt(inst, repo)
    turns = min(max_steps, _CLAUDE_TURN_CAP)
    argv = _claude_cli_argv(prompt, model=resolved_model, max_turns=turns)
    transcript_path = run_dir / _CLAUDE_TRANSCRIPT_NAME
    error: str | None = None
    termination: str | None = None
    stderr_text = ""
    rc: int | None = None
    started = time.monotonic()
    if probe:
        # Everything up to here was REAL — clone, install replay, collect
        # precheck, prompt, hermetic argv, CLI version. Only the spawn is
        # skipped, and a real non-test file change follows so diff capture,
        # split_diff, assert_no_test_edits and result.json all run.
        assert argv and argv[0], "the hermetic argv must still be constructed"
        (repo / _PROBE_FILE).write_text(
            "# swebench plumbing probe\n", encoding="utf-8"
        )
        transcript_path.write_text("", encoding="utf-8")
        termination = "plumbing-probe"
        rc = 0
    else:
        try:
            with transcript_path.open("w", encoding="utf-8") as out_fh:
                proc = subprocess.Popen(  # noqa: S603
                    argv,
                    cwd=str(repo),
                    env=_claude_child_env(),
                    stdin=subprocess.DEVNULL,
                    stdout=out_fh,  # streamed to disk AS produced — a kill loses nothing
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,  # own process group, so the kill reaches tool children
                )
                try:
                    _, stderr_text = proc.communicate(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    _kill_tree(proc)
                    _, stderr_text = proc.communicate()
                    error = (
                        f"wall-clock cap {timeout_s}s hit; partial work is still graded"
                    )
                    termination = "wall-clock-cap"
                rc = proc.returncode
        except OSError as exc:  # CLI not installed / not spawnable
            error = f"claude CLI could not run: {type(exc).__name__}: {exc}"
    if stderr_text.strip():
        (run_dir / "claude-stderr.log").write_text(stderr_text, encoding="utf-8")

    init_ev, result_ev, fallback = _parse_claude_transcript(transcript_path)
    # THE TURN CAP IS NOT A CRASH. The CLI exits 1 with empty stderr when it
    # stops at ``--max-turns``, and recording that as a generic error made the
    # retracted run DROP a row that had passed the oracle — improving its own
    # denominator. Recorded as a budget termination instead: a completed,
    # counted, flagged attempt, the same rule every other arm gets.
    used_turns = int(result_ev.get("num_turns") or 0)
    if termination is None and used_turns >= turns > 0:
        termination = "turn-cap"
    elif error is None and rc != 0:
        error = f"claude CLI exited {rc}: {stderr_text.strip()[-400:]}"
    totals = _claude_usage_totals(result_ev)
    if probe:
        totals, cost = {"tokens_in": 0, "tokens_out": 0, "cache_read": 0}, 0.0
        cost_source = "none — plumbing probe, no CLI call"
    elif totals is not None:
        cost = float(result_ev.get("total_cost_usd") or 0.0)
        cost_source = "claude-cli-reported"
    else:
        # Killed/crashed before the final result event: tokens are recovered
        # from the assistant events; the cost is UNKNOWN (only the CLI prices
        # its usage) and recorded as such rather than invented from a price
        # table this harness does not maintain. ``error`` is already set on
        # every path that gets here, so this run can never read as clean.
        totals = fallback
        cost = 0.0
        cost_source = "claude-cli-reported (no result event — cost unknown)"
        if error is None:
            error = "claude CLI stream ended without a result event"
    if error is None and result_ev.get("is_error"):
        error = f"claude CLI reported is_error ({result_ev.get('subtype')})"

    raw_diff = _capture_diff(repo)
    (run_dir / "raw.diff").write_text(raw_diff, encoding="utf-8")
    refused: list[str] = []
    try:
        code_diff, kept, stripped = split_diff(raw_diff)
    except DiffRefused as exc:
        # No prediction.diff: `grade` refuses, `audit` fails, so a refused row
        # can never be counted as a resolve. The transcript is already on disk.
        _fail(f"diff refused: {exc.reason}", refused_paths=exc.paths)
        raise  # unreachable: _fail always raises SystemExit
    assert_no_test_edits(code_diff)
    (run_dir / "prediction.diff").write_text(code_diff, encoding="utf-8")

    if probe:
        # FAIL-CLOSED, exactly like the bare/openhands probe rows: `report`
        # buckets this as a failed run (`classify_run` refuses a probe row
        # before it looks at anything else) and `estimate_instance_cost` will
        # not sample it.
        error = _PROBE_ERROR

    result = {
        **base,
        "probe_plumbing": probe,
        # The CLI's OWN account of what ran — recorded from the transcript,
        # never assumed from this file's constants.
        "model_reported": init_ev.get("model"),
        "models_observed": sorted((result_ev.get("modelUsage") or {}).keys()),
        "mcp_servers": init_ev.get("mcp_servers", []),
        "permission_mode": init_ev.get("permissionMode"),
        "session_id": result_ev.get("session_id") or init_ev.get("session_id"),
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "agent_wall_s": round(time.monotonic() - started, 1),
        "num_turns": used_turns,
        "turn_cap": turns,
        "termination": termination or ("error" if error else "cli-finished"),
        "trajectory": _CLAUDE_TRANSCRIPT_NAME,
        "tokens_in": totals["tokens_in"],
        "tokens_out": totals["tokens_out"],
        "cached_input_tokens": totals["cache_read"],
        "cost_usd": round(cost, 4),
        "cost_source": cost_source,
        # The CLI is its own ledger, so the mix comes from ``modelUsage`` rather
        # than from ``state/events/runs.ndjson`` — same three keys, so `report`
        # and the audit need no per-arm special case.
        "models_used": sorted((result_ev.get("modelUsage") or {}).keys()),
        "model_calls": [
            {
                "persona": "claude-cli",
                "model": name,
                "model_tier": None,
                "calls": None,  # the CLI reports usage per model, not call counts
                "cost_usd": round(float((usage or {}).get("costUSD") or 0.0), 4),
            }
            for name, usage in sorted((result_ev.get("modelUsage") or {}).items())
        ],
        "model_escalated_calls": 0,  # one pinned model; side models are the CLI's own
        "precheck": precheck,
        "error": error,
        # No gates ran — like the bare arm, this arm cannot claim green.
        "factory_says_green": None,
        "files_changed": kept,
        "test_files_stripped": stripped,
        "refused_paths": refused,
        "diff_bytes": len(code_diff),
    }
    out = _write_result(instance_id, key, result)
    _print_run_summary(result, out)


# --------------------------------------------------------------------------- #
# openhands arm — a single competent agent loop, no chain
# --------------------------------------------------------------------------- #


def _azure_llm_env(model_id: str) -> tuple[str | None, str | None]:
    """``(base_url, api_version)`` for an Azure model id, from the environment.

    Mirrors ``factory.runner.sandbox_run``'s own resolution (the two surfaces
    read different vars: ``azure_ai/`` → ``AZURE_AI_API_BASE`` /
    ``AZURE_AI_API_VERSION`` with the Foundry names as fallback; ``azure/`` →
    ``AZURE_API_BASE`` / ``AZURE_API_VERSION``, plus ``AZURE_ENDPOINT`` and the
    Foundry vars for operators sharing one key). Kept here rather than reaching
    into the runner so this harness cannot change chain behaviour;
    ``test_openhands_arm_reads_the_same_azure_env_vars_as_the_chain`` pins the
    variable names against ``factory/runner.py`` so the two cannot drift
    silently.
    """
    if model_id.startswith("azure_ai/"):
        return (
            os.environ.get("AZURE_AI_API_BASE") or os.environ.get("AZURE_FOUNDRY_ENDPOINT"),
            os.environ.get("AZURE_AI_API_VERSION")
            or os.environ.get("AZURE_FOUNDRY_API_VERSION"),
        )
    if model_id.startswith("azure/"):
        return (
            os.environ.get("AZURE_API_BASE")
            or os.environ.get("AZURE_ENDPOINT")
            or os.environ.get("AZURE_FOUNDRY_ENDPOINT"),
            os.environ.get("AZURE_API_VERSION")
            or os.environ.get("AZURE_FOUNDRY_API_VERSION"),
        )
    return None, None


def _build_openhands_agent(model: str, repo: Path) -> tuple[Any, Any]:
    """``(agent, workspace)`` on the SAME SDK call path the factory's dev uses.

    ``factory.runner.sandbox_run`` builds exactly this — ``LLM`` +
    ``get_default_agent(cli_mode=True)`` + ``LocalWorkspace`` — and its
    per-persona ``llm_params`` (from ``routes.yaml``: deepseek-v4-pro runs with
    ``reasoning_effort: none``) and preset selection are reused verbatim via the
    runner's own helpers, so the agent this arm drives is not a lookalike.
    Raises on a missing key or a failed SDK import: an arm that cannot build its
    agent must fail loudly before it is reported as a zero.
    """
    from openhands.sdk import LLM, LocalWorkspace
    from openhands.tools.preset.default import get_default_agent
    from pydantic import SecretStr

    from factory.runner import (
        LLMConfig,
        _build_agent_for_persona,
        _persona_llm_overrides,
        _resolve_api_key,
    )

    api_key = _resolve_api_key(LLMConfig(model=model))
    if api_key is None:
        raise SystemExit(
            f"no API key available for {model!r} — the openhands arm cannot run. "
            "Set AZURE_API_KEY / AZURE_FOUNDRY_API_KEY in .env (see .env.example)."
        )
    base_url, api_version = _azure_llm_env(model)
    llm_kwargs: dict[str, Any] = {
        "model": model,
        "api_key": SecretStr(api_key),
        "base_url": base_url,
        "usage_id": "bench:openhands",
    }
    if api_version is not None:
        llm_kwargs["api_version"] = api_version
    llm_kwargs.update(_persona_llm_overrides("dev", model, "standard"))
    llm = LLM(**llm_kwargs)
    agent = _build_agent_for_persona("dev", llm, get_default_agent)
    return agent, LocalWorkspace(working_dir=str(repo.resolve()))


def run_openhands(
    instance_id: str, *, max_steps: int, timeout_s: int, probe: bool = False
) -> None:
    """ONE OpenHands agent, the factory's dev model, no chain around it.

    This is the arm the product claim actually needs. ``bare`` isolates "cheap
    weights with almost no scaffold"; ``claude`` isolates "frontier weights in
    a frontier harness". Neither isolates the thing being sold, which is THE
    CHAIN — PM/SM decomposition, a reviewer on different weights, retries, and
    merge gates. So this arm holds everything else constant and removes exactly
    that: the same ``azure/deepseek-v4-pro`` dev deployment, the same OpenHands
    SDK and default toolset (real file editor, real bash, real search) the
    factory's dev runs inside, the same ``_STORY_TEMPLATE`` task text, the same
    prepared clone, the same wall clock, the same prediction path. The only
    difference from the factory arm is the chain.

    Deliberately NOT included: the dev persona prompt and the context prelude
    (``factory/personas/dev.md`` + ``compose_context_prelude``). They are part
    of the harness under test, so this arm carries the story file alone — the
    factory arm's advantage therefore includes its persona engineering, which is
    the honest attribution.

    Accounting: one ``Run`` row is written into the run's own isolated ledger
    from the conversation's OWN usage totals, so ``audit`` certifies this arm
    exactly like the factory and bare arms with no special case. OpenHands'
    persisted event stream is copied out whole as this arm's trajectory.

    ``probe=True`` builds the agent and exercises every artifact path WITHOUT
    calling the model.
    """
    entered = time.monotonic()
    inst = _instance(instance_id)
    # A run the store cannot grade is a write-off — refuse before any spend.
    _assert_oracle_store_complete([inst])
    run_dir = _run_dir(instance_id, "openhands")
    # BEFORE any exit path: a stale prediction/ledger must never outlive the
    # run that produced it.
    _reset_run_artifacts(run_dir)

    sys.path.insert(0, str(FACTORY_ROOT))
    from factory.model_router import route

    model = route("dev", "standard")
    state_root = run_dir
    db_path = run_dir / "state" / "factory.db"
    base: dict[str, Any] = {
        "arm": "openhands",
        "instance_id": instance_id,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "problem_statement_sha256": inst["problem_statement_sha256"],
        "manifest_sha256": _manifest()["manifest_sha256"],
        "model": model,
        "agent": "openhands-sdk default agent (cli_mode), single conversation",
    }

    def _fail(error: str, **extra: Any) -> None:
        _write_result(
            instance_id,
            "openhands",
            {
                **base,
                **_no_model_mix(),
                "ts": datetime.now(UTC).isoformat(),
                "wall_clock_s": round(time.monotonic() - entered, 1),
                "error": error,
                "factory_says_green": None,
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "cost_source": "derived-from-price-table",
                "persona_calls": 0,
                **extra,
            },
        )
        raise SystemExit(error)

    if not _ensure_image(inst):
        _fail(
            f"image for {instance_id} is unavailable; the openhands arm's test "
            "command runs inside it (see instance_test_command)"
        )
    # OUTSIDE the repo, same reason as every other arm: the OpenHands agent's
    # working directory IS this clone, and at `runs/<id>/openhands/repo` the
    # oracle store was three `..` up. `state/` stays under `run_dir` (the
    # trajectory the audit scans lives there) and is not an ancestor of the
    # agent's cwd.
    repo = _work_dir(instance_id, "openhands", fresh=True) / "repo"
    _clone(inst, repo)
    assert_workspace_isolated(repo)
    prep_error = _prepare_cloned_tree(inst, repo)
    if prep_error:
        _fail(f"prepare: {prep_error}")

    # THE SAME pre-dispatch collect gate every other arm passes. $0 to fail.
    precheck = _precheck_collect(inst, repo)
    collect_tail = str(precheck.pop("tail", ""))
    if not precheck["collect_ok"]:
        _fail(
            f"precheck: test command does not collect: {collect_tail[-400:]}",
            precheck={**precheck, "tail": collect_tail[-1500:]},
        )

    # The IDENTICAL task text the factory dev's story file is written from —
    # same helper, same arguments, no arm-specific wording.
    task = _STORY_TEMPLATE.format(
        instance_id=instance_id,
        statement=inst["problem_statement"],
        test_command=instance_test_command(inst, repo=repo),
    )

    from factory.runner import _capture_trajectory, _log_prompt_body, _log_prompt_metadata

    # Prompt telemetry BEFORE the first failure path, exactly as ``sandbox_run``
    # does it — the audit treats missing prompt bodies beside recorded calls as
    # an unauditable run.
    for _log in (_log_prompt_metadata, _log_prompt_body):
        _log(
            persona="dev",
            prompt=task,
            model_id=model,
            story_id=None,
            software_factory_root=state_root,
        )

    agent, workspace = _build_openhands_agent(model, repo)
    iterations = min(max_steps, _OPENHANDS_ITERATION_CAP)
    persist_dir = Path(tempfile.mkdtemp(prefix="bench-oh-traj-"))
    import uuid as _uuid

    conv_id = _uuid.uuid4()
    events_src = persist_dir / conv_id.hex / "events"

    usage: dict[str, Any] = {}
    started = time.monotonic()
    error: str | None = None
    termination = "agent-finished"
    worker: threading.Thread | None = None

    def _worker() -> None:
        from openhands.sdk import Conversation

        conversation: Any = None
        try:
            conversation = Conversation(
                agent=agent,
                workspace=workspace,
                max_iteration_per_run=iterations,
                delete_on_close=False,
                persistence_dir=str(persist_dir),
                conversation_id=conv_id,
            )
            conversation.send_message(task)
            conversation.run()
            stats = conversation.conversation_stats.get_combined_metrics()
            tok = stats.accumulated_token_usage
            # Read cost through a None sentinel, like the runner: an SDK shape
            # change that drops ``accumulated_cost`` must not be
            # indistinguishable from a genuinely free run.
            cost_raw = getattr(stats, "accumulated_cost", None)
            usage.update(
                tokens_in=int(getattr(tok, "prompt_tokens", 0) or 0),
                tokens_out=int(getattr(tok, "completion_tokens", 0) or 0),
                cached=int(getattr(tok, "cache_read_tokens", 0) or 0),
                cost=float(cost_raw or 0.0),
                cost_reliable=cost_raw is not None,
            )
        except Exception as exc:  # noqa: BLE001 — the driver must never crash
            usage["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            if conversation is not None:
                with contextlib.suppress(Exception):
                    conversation.close()

    if probe:
        # Everything except the provider call: the agent above was really
        # built (SDK import, key resolution, azure env, routes.yaml llm_params),
        # and a real non-test file change follows so the diff/split/assert/write
        # path is exercised end to end.
        (repo / _PROBE_FILE).write_text(
            "# swebench plumbing probe\n", encoding="utf-8"
        )
        termination = "plumbing-probe"
    else:
        # Daemon thread, not an executor: the OpenHands conversation runs
        # in-process and cannot be killed, and a non-daemon worker would hold
        # the interpreter open past the wall-clock cap. The cap therefore
        # ABANDONS the thread and grades the tree as it stands — the same
        # trade-off ``sandbox_run`` makes, and the reason the trajectory is
        # persisted incrementally rather than at the end.
        worker = threading.Thread(target=_worker, name="openhands-arm", daemon=True)
        worker.start()
        worker.join(timeout=float(timeout_s))
        if worker.is_alive():
            error = f"wall-clock cap {timeout_s}s hit; partial work is still graded"
            termination = "wall-clock-cap"
        elif usage.get("error"):
            error = f"openhands conversation failed: {usage['error']}"
            termination = "agent-error"

    traj = _capture_trajectory(
        events_src=events_src,
        story_id=None,
        attempt=1,
        software_factory_root=state_root,
    )
    # An ABANDONED conversation may still be writing into its persistence dir,
    # so only reap it when the worker really finished. (The runner makes the
    # same call for the same reason; stale dirs there are reaped on the next
    # run.)
    if worker is None or not worker.is_alive():
        shutil.rmtree(persist_dir, ignore_errors=True)
    traj_path = Path(traj) if traj else None
    actions, sdk_events = _count_trajectory_actions(traj_path)

    # ONE Run row, from the conversation's OWN usage, into this run's isolated
    # ledger — so ``audit`` reads this arm through the same code path as the
    # factory and bare arms.
    if not probe:
        from factory.runner import _record_run

        _record_run(
            persona="dev",
            model=model,
            mode="sandbox",
            tokens_in=int(usage.get("tokens_in", 0) or 0),
            tokens_out=int(usage.get("tokens_out", 0) or 0),
            cost_usd=float(usage.get("cost", 0.0) or 0.0),
            success=error is None,
            story_path=None,
            repo_path=str(repo),
            error=error,
            db_path=db_path,
            duration_s=round(time.monotonic() - started, 3),
            story_id=None,
            model_tier="standard",
            software_factory_root=state_root,
            cached_input_tokens=int(usage.get("cached", 0) or 0),
            usage_reliable=bool(usage.get("cost_reliable", False)),
        )

    # Read the numbers BACK from the ledger, so result.json reports what the
    # audit will independently sum rather than a parallel in-memory tally.
    ledger = _read_ledger_totals(db_path)

    raw_diff = _capture_diff(repo)
    code_diff, kept, stripped = split_diff(raw_diff)
    assert_no_test_edits(code_diff)
    (run_dir / "raw.diff").write_text(raw_diff, encoding="utf-8")
    (run_dir / "prediction.diff").write_text(code_diff, encoding="utf-8")

    if probe:
        error = _PROBE_ERROR

    result = {
        **base,
        **_model_mix(state_root / "state" / "events", nominal=model),
        "ts": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(time.monotonic() - entered, 1),
        "agent_wall_s": round(time.monotonic() - started, 1),
        # Tool calls the agent actually made, counted from its OWN persisted
        # event stream — not an SDK event total (which counts observations and
        # messages too and would print as "812 / 600").
        "steps_used": actions,
        "step_cap": iterations,
        "sdk_events": sdk_events,
        "termination": termination,
        "trajectory": (
            str(traj_path.relative_to(run_dir)) if traj_path else None
        ),
        "probe_plumbing": probe,
        "tokens_in": ledger["tokens_in"],
        "tokens_out": ledger["tokens_out"],
        "cached_input_tokens": ledger["cached_input_tokens"],
        "cost_usd": ledger["cost_usd"],
        "cost_source": "derived-from-price-table",
        "persona_calls": ledger["persona_calls"],
        "usage_reliable": usage.get("cost_reliable"),
        "precheck": precheck,
        "error": error,
        # No reviewer, no gates: like bare and claude, this arm cannot claim
        # green — only produce a diff.
        "factory_says_green": None,
        "files_changed": kept,
        "test_files_stripped": stripped,
        "diff_bytes": len(code_diff),
    }
    out = _write_result(instance_id, "openhands", result)
    _print_run_summary(result, out)


def _count_trajectory_actions(path: Path | None) -> tuple[int, int]:
    """``(tool_calls, total_events)`` in a copied-out OpenHands trajectory.

    The tool-call count is the honest analogue of the bare arm's step count and
    the claude arm's turn count: what the agent DID. Total events (which also
    include observations, agent messages and the harness's own system prompt) is
    kept beside it so a reader can see the trail's size without opening it.
    """
    if path is None or not path.exists():
        return 0, 0
    actions = total = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                total += 1
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(ev, dict) and str(ev.get("kind")) == "ActionEvent":
                    actions += 1
    except OSError:
        return actions, total
    return actions, total


def _read_ledger_totals(db_path: Path) -> dict[str, Any]:
    """Sum every Run row in an isolated bench ledger; zeros when unreadable."""
    empty = {
        "tokens_in": 0,
        "tokens_out": 0,
        "cached_input_tokens": 0,
        "cost_usd": 0.0,
        "persona_calls": 0,
    }
    if not db_path.exists():
        return empty
    try:
        from sqlmodel import Session, select

        from factory.runner import Run, _engine

        with Session(_engine(db_path)) as s:
            runs = list(s.exec(select(Run)).all())
    except Exception:  # noqa: BLE001 — an unreadable ledger is the audit's problem
        return empty
    return {
        "tokens_in": sum(int(r.tokens_in or 0) for r in runs),
        "tokens_out": sum(int(r.tokens_out or 0) for r in runs),
        "cached_input_tokens": sum(
            int(getattr(r, "cached_input_tokens", 0) or 0) for r in runs
        ),
        "cost_usd": round(sum(float(r.cost_usd or 0.0) for r in runs), 4),
        "persona_calls": len(runs),
    }


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

    image = _image_for(inst)
    oracle = _oracle_for(inst)
    f2p = oracle["fail_to_pass"]
    p2p, p2p_source = _pass_to_pass_for(inst, oracle)

    started = time.monotonic()
    verdict: dict[str, Any] = {
        "arm": arm,
        "instance_id": instance_id,
        "image": image,
        "graded_at": datetime.now(UTC).isoformat(),
        "fail_to_pass_count": len(f2p),
        # Recorded so the report can flag a row graded with no regression suite
        # at all, and so an implicit set never passes for a dataset-declared one.
        "pass_to_pass_count": len(p2p),
        "pass_to_pass_declared_count": len(oracle["pass_to_pass"]),
        "pass_to_pass_source": p2p_source,
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

    # Same topology as the run and the control (swe-rebench): grade against
    # a PREPARED fresh clone mounted over the workdir, not the image's baked
    # tree — the baked tree carries build artifacts a fresh clone lacks, and
    # grading a different environment from the one measured is proxy ≠ real.
    # Pro (frozen) keeps its baked-tree grading unchanged.
    profile = _profile_of(inst)
    mount: Path | None = None
    if profile.name == "swe-rebench":
        # OUTSIDE the repo: the ORACLE TEST PATCH is applied inside this tree
        # by the grade script, so as `runs/<id>/<arm>/grade-repo/` it sat three
        # `..` from the next arm's cwd with the hidden tests in plaintext.
        grade_repo = _grade_mount_dir(instance_id, arm)
        _clone(inst, grade_repo)
        prep_error = _prepare_cloned_tree(inst, grade_repo, timeout_s=timeout_s)
        if prep_error:
            verdict.update(
                {
                    "oracle_resolved": None,
                    "outcome": "environment_prepare_failed",
                    "log_tail": prep_error[-2000:],
                }
            )
            _write_result(instance_id, arm, {"grade": verdict}, merge=True)
            print(json.dumps(verdict, indent=2))
            return
        mount = grade_repo

    # Nonce-suffixed markers (env-injected, never in the script text): a
    # marker echoed by arm-authored test code, or replayed from any static
    # text, can never match the strings checked below.
    nonce = secrets.token_hex(8)
    script = _grade_script_for(inst, diff_text)
    proc = _docker_bash(
        image, script, timeout_s, nonce=nonce, mount=mount,
        workdir=profile.container_workdir,
    )
    log = (proc.stdout or "") + (proc.stderr or "")
    human_log, node_regions = _split_node_regions(log, nonce)
    (run_dir / "grade.log").write_text(human_log, encoding="utf-8")
    if node_regions:
        (run_dir / "grade-nodes.log").write_text(
            "".join(f"=== {k} ===\n{v}" for k, v in node_regions.items()),
            encoding="utf-8",
        )

    # PER-NODE, not exit-code. `pytest -q <ids>` exits 0 when every selected
    # test skips, so the marker alone is not proof that the named tests passed.
    # Both sets must be demonstrably PASSED, and a missing report refuses.
    f2p_outcomes = _parse_node_outcomes(node_regions.get("fail_to_pass", ""))
    p2p_outcomes = _parse_node_outcomes(node_regions.get("pass_to_pass", ""))
    f2p_ok, f2p_reasons = evaluate_node_coverage(f2p, f2p_outcomes)
    p2p_ok, p2p_reasons = evaluate_node_coverage(p2p, p2p_outcomes)
    nodes_ok = f2p_ok and p2p_ok
    verdict["node_coverage_ok"] = nodes_ok
    verdict["node_coverage_reasons"] = f2p_reasons + p2p_reasons

    # Did the PARSER fail, or did the ARM fail? Compare what pytest says it
    # reported against what was extracted. Without this the two are the same
    # row label, and one broken parse reads as a uniform 0% for every arm.
    tallies = _tally_lines(log, nonce)
    parse_failures = [
        f"{label}: {why}"
        for label, outcomes in (
            ("fail_to_pass", f2p_outcomes),
            ("pass_to_pass", p2p_outcomes),
        )
        if label in tallies
        and (why := node_parse_failure(tallies[label], outcomes)) is not None
    ]
    verdict["node_parse_failures"] = parse_failures

    marker_resolved = f"{_marker('SWEBENCH_RESULT', nonce)}: RESOLVED" in log
    # An unparsable per-node report certifies nothing in EITHER direction: not a
    # pass, and — the half that matters — not the arm's failure either. The
    # `grade_parse_failed` outcome below carries that distinction and keeps the
    # row out of every rate.
    resolved = marker_resolved and nodes_ok and not parse_failures
    applied = f"{_marker('SWEBENCH_APPLY', nonce)}: OK" in log
    # Visible, not decisive: on a selftest-cleared instance, ids that do not
    # collect under the ARM's patch mean the arm did not deliver the API the
    # tests need — an ordinary UNRESOLVED, recorded so the log tail is
    # interpretable without spelunking.
    verdict["post_patch_ids_collect"] = (
        f"{_marker('SWEBENCH_POST_PATCH', nonce)}: FAIL_TO_PASS_IDS_DO_NOT_COLLECT"
        not in log
    )
    # Order matters: a broken baseline short-circuits BEFORE the prediction is
    # applied, so "not applied" must not be read as the arm's fault.
    # (BROKEN_NO_COLLECT is the Pro profile's frozen semantics.)
    if f"{_marker('SWEBENCH_BASELINE', nonce)}: BROKEN_NO_COLLECT" in log:
        outcome = "task_broken_no_collect"
    elif f"{_marker('SWEBENCH_BASELINE', nonce)}: BROKEN_ALREADY_GREEN" in log:
        outcome = "task_broken_already_green"
    elif not applied:
        outcome = "patch_did_not_apply"
    elif parse_failures:
        # THE HARNESS BROKE, NOT THE ARM. Kept distinct from
        # `unresolved_no_per_node_pass` (a real all-skipped/uncollected result)
        # because they are indistinguishable at the verdict level and only one
        # of them is the arm's fault. Excluded from every rate, exactly like
        # `task_broken`, and named in the report's exclusion accounting.
        outcome = "grade_parse_failed"
    elif resolved:
        outcome = "resolved"
    elif marker_resolved:
        # Every selected test "did not fail" and yet some declared id has no
        # PASSED node: skipped, deselected, uncollected, or the per-node report
        # never arrived. Its own outcome, so it can never be read as a pass and
        # never be confused with a wrong patch.
        outcome = "unresolved_no_per_node_pass"
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
            parsed[1]
            for line in diff_text.splitlines()
            if line.startswith(_DIFF_GIT)
            and (parsed := parse_diff_header(line.rstrip("\n"))) is not None
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
            "log_tail": human_log[-3000:],
        }
    )
    _write_result(instance_id, arm, {"grade": verdict}, merge=True)
    # The prepared mount has the oracle test patch applied INSIDE it. Grading
    # is over, so it is pure liability now.
    if mount is not None:
        shutil.rmtree(mount.parent, ignore_errors=True)
    # NEVER print the oracle's gold_files. `run-all` captures each grade's
    # stdout into `runs/<id>/<arm>/sweep-grade.log`, which is a file inside the
    # run tree the NEXT arm walks past — the answer key, published next to the
    # answer sheet. They stay in result.json, which the report needs.
    print(
        json.dumps(
            {
                k: v
                for k, v in verdict.items()
                if k not in _GRADE_STDOUT_SUPPRESSED
            },
            indent=2,
        )
    )


# Verdict keys that must never reach a captured stdout stream: they name the
# maintainers' real fix (or the hidden ids that decide it).
_GRADE_STDOUT_SUPPRESSED = frozenset(
    {"log_tail", "gold_files", "gold_files_overlap", "node_coverage_reasons"}
)


def _docker_bash(
    image: str,
    script: str,
    timeout_s: int,
    *,
    nonce: str = "",
    mount: Path | None = None,
    workdir: str = "/testbed",
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` in ``image``.

    ``--entrypoint bash`` is required: these images already set
    ``Entrypoint=[/bin/bash]``, so passing ``bash -lc ...`` as the command made
    bash try to EXECUTE the string "bash" and die with "cannot execute binary
    file". ``--network none`` denies egress during grading so a patch cannot
    reach out for the answer.

    The script goes in on STDIN, not as an argv element: it embeds the test
    patch, the prediction AND every hidden test id, and Linux caps a single
    argv string at ~128KB (MAX_ARG_STRLEN) — a pinned swe-rebench instance
    with 16k fail_to_pass ids dies with E2BIG as argv.

    Stdin is NOT the execution stream, though. ``bash -l -s`` left the
    unread script on fd 0 while arm-authored test code ran: a stdin-reading
    test ate the trailing verdict echo (wrong UNRESOLVED), and a
    stdin-echoing test printed the literal ``echo "SWEBENCH_RESULT: …"``
    line into the tail the verdict grep matched (false RESOLVED — executed
    demo). So the script is first drained to a container-local file with
    ``cat``, then exec'd with stdin re-pointed at ``/dev/null``: nothing the
    graded code runs can see, eat, or replay the script. The verdict markers
    are additionally nonce-suffixed (``SWEBENCH_NONCE``, env-injected) so a
    marker echoed from any static text can never match the checked string.

    ``mount`` switches the topology: the given host tree is mounted over
    ``workdir`` and the container runs as the invoking uid (the tree is
    host-owned; the swe-rebench control and measurement both grade a
    prepared fresh clone, not the image's baked tree). Without it (Pro,
    frozen) the image's own baked tree is graded as before.
    """
    args = [
        "docker", "run", "--rm", "-i", "--network", "none",
        "-e", f"SWEBENCH_NONCE={nonce}",
    ]
    if mount is not None:
        args += [
            "-v", f"{mount}:{workdir}", "-w", workdir,
            "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
        ]
    args += [
        "--entrypoint", "bash", image, "-lc",
        "cat > /tmp/.swebench_grade.sh && exec bash -l /tmp/.swebench_grade.sh < /dev/null",
    ]
    return subprocess.run(
        args,
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _heredoc(text: str) -> str:
    return text if text.endswith("\n") or not text else text + "\n"


# The shell-side spelling of a nonce-suffixed marker. The value is injected
# via ``docker run -e SWEBENCH_NONCE=…`` — deliberately NOT embedded in the
# script text, so even a verbatim replay of the script cannot reproduce a
# checked marker string.
#
# ``_N`` is a SHELL variable, not an exported one: the script's first act is to
# copy ``SWEBENCH_NONCE`` into it and ``unset`` the environment entry, so
# ``python -m pytest`` and everything the graded code runs inherit no nonce at
# all. Before that, arm-authored test code could read ``os.environ`` and print
# a perfectly-formed verdict marker.
_NONCE_VAR = "${_N}"


def _marker(name: str, nonce: str) -> str:
    """The exact log string a genuine script emission expands to."""
    return f"{name}_{nonce}"


# --------------------------------------------------------------------------- #
# per-node grading — an exit code cannot tell PASSED from SKIPPED
# --------------------------------------------------------------------------- #
#
# ``if ! python -m pytest -q "${SWEBENCH_F2P[@]}"; then fail=1; fi`` graded on
# the exit code, and pytest exits 0 when every selected test SKIPS. So a
# prediction that made the hidden suite skip — via a collection-config channel
# (defect 3), a plugin hook, or a conditional skip in production code the tests
# import — graded RESOLVED with no work done. Verified against real pytest:
# ``2 skipped`` exits 0.
#
# The official SWE-bench harness parses per-test outcomes and requires an
# explicit PASSED for every fail_to_pass and pass_to_pass id. So does this now.

# pytest's short-summary lines. ``-r`` reports skips by LOCATION
# (``SKIPPED [1] tests/x.py:23: reason``), not by node id, which is fine: the
# rule below needs PASSED node ids and FAILED/ERROR node ids, and "no PASSED
# for this id" is exactly what an all-skipped run looks like.
_SHORT_SUMMARY = re.compile(r"^=+ short test summary info =+\s*$")
_NODE_LINE = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS) (\S.*)$")
_TALLY = re.compile(r"^=*\s*(no tests ran|\d+ (passed|failed|error|skipped))")

# ANSI escapes, stripped before ANY of the patterns above are matched.
#
# MEASURED FAILURE (getmoto__moto-9841/openhands, 2026-08-03): moto's own
# ``pyproject.toml`` carries ``addopts = "--color=yes"``, so pytest coloured its
# output even into a pipe — ``\x1b[32mPASSED\x1b[0m tests/…::\x1b[1mtest_x\x1b[0m``
# and a wrapped ``short test summary info`` header. Every pattern here is
# anchored, so all of them missed: 153 tests passed and the parser found ZERO
# node outcomes. The grade script now forces colour off three ways, and this
# strips escapes anyway — the per-node report is the load-bearing verdict, and
# any repository can re-enable colour in config the arm never touches.
_ANSI_ESCAPE = re.compile(
    r"\x1b(?:\[[0-9;:?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])"
)


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def _parse_node_outcomes(text: str) -> dict[str, set[str]]:
    """``{node_id: {outcomes}}`` from pytest's SHORT SUMMARY section only.

    Deliberately not the whole log. ``-rA`` echoes a passing test's captured
    stdout in a ``PASSES`` section, so arm-authored code could print
    ``PASSED <some other id>`` and have it appear verbatim; the script asks for
    ``-rpfEsxX`` (same reports, no captured output) and this reads only the
    section pytest itself writes, after the LAST section header.
    """
    lines = _strip_ansi(text).splitlines()
    starts = [i for i, ln in enumerate(lines) if _SHORT_SUMMARY.match(ln)]
    if not starts:
        return {}
    outcomes: dict[str, set[str]] = {}
    for ln in lines[starts[-1] + 1 :]:
        if ln.startswith("=") or _TALLY.match(ln):
            break
        m = _NODE_LINE.match(ln)
        if not m:
            continue
        verdict, rest = m.group(1), m.group(2).strip()
        if verdict != "PASSED":
            # pytest appends " - <reason>" for failures/errors. A node id that
            # itself contains " - " truncates here, which is harmless: the
            # truncated id is still a prefix of the real one, so it still
            # attaches to the same declared id.
            rest = rest.split(" - ", 1)[0].strip()
        if rest:
            outcomes.setdefault(rest, set()).add(verdict)
    return outcomes


def _node_matches(node_id: str, declared: str) -> bool:
    """Does a collected node satisfy a DECLARED id?

    One declared id legitimately selects several nodes: ``_repair_truncated_
    param_ids`` widens a truncated parametrised id to the whole test function
    (measured: conan-19735 declares 1 fail_to_pass id and 4 nodes pass), and
    the implicit pass_to_pass set (defect 6) is FILE paths. So a literal
    ``count(PASSED) == len(ids)`` rule would flip valid rows; the rule is
    "every declared id has at least one PASSED node and no FAILED/ERROR node".
    """
    return (
        node_id == declared
        or node_id.startswith(declared + "[")
        or node_id.startswith(declared + "::")
    )


def evaluate_node_coverage(
    declared_ids: list[str], outcomes: dict[str, set[str]]
) -> tuple[bool, list[str]]:
    """``(ok, reasons)`` — is every declared id demonstrably PASSED?

    FAIL CLOSED: no per-node evidence at all means not resolved, because the
    thing being certified is "these named tests passed", and an absent report
    certifies nothing. XFAIL/XPASS count as neither a pass nor a failure
    (pytest exits 0 for both, and a file-level id legitimately contains
    xfails — pandas-63945's run reports 2).
    """
    if not declared_ids:
        return True, []
    reasons: list[str] = []
    for declared in declared_ids:
        norm = declared.strip().removeprefix("./")
        matched = {n: o for n, o in outcomes.items() if _node_matches(n, norm)}
        broken = sorted(n for n, o in matched.items() if o & {"FAILED", "ERROR"})
        if broken:
            reasons.append(f"{declared}: node(s) FAILED/ERROR: {broken[:5]}")
        elif not any("PASSED" in o for o in matched.values()):
            reasons.append(
                f"{declared}: no PASSED node in pytest's report — a skipped, "
                "deselected, uncollected or missing test is not a pass"
            )
    return not reasons, reasons[:20]


# pytest's own count of the outcomes it reports BY NODE ID. ``skipped`` and
# ``deselected`` are deliberately absent: ``-r`` reports skips by location, not
# by node id, so an all-skipped run legitimately yields zero node outcomes (and
# is a genuine UNRESOLVED, never a parse failure).
_TALLY_COUNT = re.compile(r"(\d+) (passed|failed|errors?|xfailed|xpassed)\b")


def reported_node_outcomes(tally: str) -> dict[str, int] | None:
    """What pytest's tally line says it reported, or ``None`` if there is none.

    ``None`` means "no evidence either way" — a crashed or timed-out run — and
    must not be read as "it reported nothing".
    """
    clean = _strip_ansi(tally)
    counts: dict[str, int] = {}
    for m in _TALLY_COUNT.finditer(clean):
        key = "error" if m.group(2).startswith("error") else m.group(2)
        counts[key] = counts.get(key, 0) + int(m.group(1))
    if not counts:
        return {"passed": 0} if "no tests ran" in clean else None
    return counts


def node_parse_failure(tally: str, outcomes: dict[str, set[str]]) -> str | None:
    """Did the PER-NODE PARSER fail, as opposed to the arm's patch failing?

    THE DISTINCTION IS THE POINT. "the parser found no node outcomes" and "the
    named tests did not pass" are indistinguishable at the verdict level, and
    conflating them turns a harness defect into a uniform 0% across every arm —
    a result that looks like a finding and is a bug. This returns a reason
    string when pytest's own tally contradicts what the parser extracted, and
    the caller records a distinct ``grade_parse_failed`` outcome that is
    EXCLUDED from every rate (same posture as ``task_broken``).

    Two contradictions, both conservative:

    * the tally reports node-reportable outcomes and the parser found NONE;
    * the tally reports more PASSED tests than the parser could attribute to a
      node id. Every ``PASSED <nodeid>`` line is one distinct id, so these
      counts match exactly on a healthy log. FAILED/ERROR counts are NOT
      compared: pytest truncates those lines at `` - `` and one node can be
      both FAILED and ERROR, so shrinkage there is expected — and a row with
      failures is unresolved on the merits anyway.

    An arm cannot use this to launder its own failures into an exclusion: it
    would have to suppress pytest's short-summary section, which needs an edit
    to a collection channel (``pytest.ini``, ``pyproject.toml``, ``conftest.py``,
    ``setup.cfg``), and ``split_diff`` REFUSES a prediction that touches one.
    """
    reported = reported_node_outcomes(tally)
    if reported is None:
        return None
    total = sum(reported.values())
    if total > 0 and not outcomes:
        return (
            f"pytest reported {total} node outcome(s) ({_fmt_counts(reported)}) "
            "and the per-node parser extracted ZERO — the short-summary section "
            "was not readable. This is a HARNESS defect, not a failed patch."
        )
    passed = reported.get("passed", 0)
    parsed_passed = sum(1 for o in outcomes.values() if "PASSED" in o)
    if passed > parsed_passed:
        return (
            f"pytest reported {passed} passed test(s) and the per-node parser "
            f"attributed only {parsed_passed} PASSED node id(s) — the per-node "
            "report is incomplete, so it cannot certify anything either way."
        )
    return None


def _fmt_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))


def _tally_lines(log: str, nonce: str) -> dict[str, str]:
    """``{label: pytest's own tally line}`` from the grade log's TALLY markers.

    Emitted OUTSIDE the node region on purpose: when the region extraction is
    what broke, the region is empty and the tally is the only evidence that the
    tests ran at all.
    """
    prefix = f"{_marker('SWEBENCH_TALLY', nonce)}: "
    out: dict[str, str] = {}
    for line in log.splitlines():
        bare = line.strip()
        if not bare.startswith(prefix):
            continue
        # ``<label> <pytest's tally line>``. The label is the script's own
        # literal; only the tally half can carry colour escapes.
        parts = bare[len(prefix) :].split(None, 1)
        if parts:
            out[parts[0]] = parts[1] if len(parts) > 1 else ""
    return out


def _split_node_regions(log: str, nonce: str) -> tuple[str, dict[str, str]]:
    """Peel the machine-readable node-outcome regions out of a grade log.

    Returns ``(human_log, {label: region_text})``. The regions can run to
    thousands of lines (pandas-63945 declares 16215 fail_to_pass ids), which
    would bury the verdict and make ``log_tail`` useless; they go to
    ``grade-nodes.log`` instead and the human log keeps a one-line placeholder.

    An UNTERMINATED region is discarded: a killed or timed-out run must never
    have a partial report read as a complete one.
    """
    begin = f"{_marker('SWEBENCH_NODES', nonce)}: BEGIN "
    end = f"{_marker('SWEBENCH_NODES', nonce)}: END "
    human: list[str] = []
    regions: dict[str, str] = {}
    label: str | None = None
    buf: list[str] = []
    for line in log.splitlines(keepends=True):
        bare = line.strip()
        if label is None and bare.startswith(begin):
            label = bare[len(begin) :].split()[0] if bare[len(begin) :].split() else ""
            buf = []
            continue
        if label is not None and bare.startswith(end):
            regions[label] = "".join(buf)
            human.append(
                f"[{len(buf)} node outcomes for {label} -> grade-nodes.log]\n"
            )
            label = None
            buf = []
            continue
        (buf if label is not None else human).append(line)
    if label is not None:
        human.append(f"[node-outcome region for {label} was TRUNCATED]\n")
    return "".join(human), regions


def _pass_to_pass_for(
    inst: dict[str, Any], oracle: dict[str, Any]
) -> tuple[list[str], str]:
    """The regression set to grade against, and where it came from.

    Two pinned swe-rebench instances ship an EMPTY ``pass_to_pass``
    (``line__line-bot-sdk-python-981_interface`` and
    ``pandas-dev__pandas-63945``), and the grade script skipped the p2p
    invocation entirely — so those two rows were graded with no regression
    suite at all: a prediction that fixed the target test by breaking
    everything around it scored the same as a correct one.

    Fallback: the instance's own declared ``test_targets`` FILES, reduced to
    paths. They are already in the manifest and already the arm's test command,
    so this leaks nothing new, and requiring those files to pass in full is a
    real regression signal.

    Pro is FROZEN — no implicit set there, or old archives' outcome labels stop
    being reproducible (and Pro's ``selected_test_files_to_run`` IS the
    fail_to_pass id list, so it would be a tautology anyway).
    """
    declared = oracle["pass_to_pass"]
    if declared:
        return declared, "dataset"
    if _profile_of(inst).name != "swe-rebench":
        return [], "dataset"
    implicit = _test_file_paths(_declared_test_entries(inst))
    if not implicit:
        return [], "dataset"
    return implicit, "declared_test_targets"


def _grade_script_for(inst: dict[str, Any], prediction: str) -> str:
    """The grade script for one instance, with its profile's plumbing filled in.

    Shared by ``grade`` (the arm's prediction) and ``selftest`` (the gold
    patch) so the control validates EXACTLY the script the measurement uses.
    Profile differences: where the repo lives in the image, how the test env
    gets on PATH, the dataset's own setup command, and the BASELINE
    semantics — Pro is FROZEN on its origin/main behavior (persistent
    no-collect is a hard ``BROKEN_NO_COLLECT`` exit → ``task_broken``,
    excluded from the denominator, so old archives' outcome labels stay
    reproducible), while swe-rebench treats pre-patch no-collect as a red
    baseline (TDD instances) and moves the broken-instance signal post-patch.
    """
    profile = _profile_of(inst)
    oracle = _oracle_for(inst)
    if profile.name == "swe-rebench":
        # No dataset setup command exists; the test patch IS the oracle
        # install and must be applied UNCONDITIONALLY. Applying it only as a
        # collect-fallback (the Pro flow) silently skips it whenever the f2p
        # test NAMES already exist at base_commit with old assertions — the
        # baseline then runs the OLD tests, passes, and a healthy instance is
        # excluded as BROKEN_ALREADY_GREEN (measured on nicegui-5858).
        oracle_setup = (
            "if [ -s /tmp/test_patch.diff ]; then\n"
            "  git apply -v /tmp/test_patch.diff 2>&1 "
            "|| git apply -v --3way /tmp/test_patch.diff 2>&1 || true\n"
            '  echo "SWEBENCH_SETUP: test_patch applied"\n'
            "fi"
        )
        # Pre-patch collection MAY legitimately fail: a TDD-style instance's
        # oracle test imports API the fix itself introduces (measured on
        # pandas-dev__pandas-63945). Official SWE-bench semantics treat an
        # import error as a red baseline; the honest broken-instance signal
        # moves POST-patch, where only the gold patch (selftest) decides it.
        baseline_gate = (
            "baseline_no_collect=0\n"
            "if ! collect; then\n"
            f'  echo "SWEBENCH_BASELINE_{_NONCE_VAR}: NO_COLLECT_PRE_PATCH '
            '(collection fails before the patch; treated as a red baseline)"\n'
            "  tail -20 /tmp/collect.log\n"
            "  baseline_no_collect=1\n"
            "else\n"
            '  if python -m pytest -q "${SWEBENCH_F2P[@]}" >/tmp/baseline.log 2>&1 </dev/null; then\n'
            f'    echo "SWEBENCH_BASELINE_{_NONCE_VAR}: BROKEN_ALREADY_GREEN '
            '(fail_to_pass passes unpatched)"\n'
            "    tail -20 /tmp/baseline.log\n"
            "    exit 3\n"
            "  fi\n"
            f'  echo "SWEBENCH_BASELINE_{_NONCE_VAR}: OK (red as expected)"\n'
            "fi"
        )
        post_patch_check = (
            "# Ids that STILL do not collect with the patch applied can never\n"
            "# pass: under the gold patch (selftest) the instance is broken as\n"
            "# shipped; under an arm's prediction it simply stays UNRESOLVED.\n"
            'if [ "$baseline_no_collect" = "1" ] && ! collect; then\n'
            f'  echo "SWEBENCH_POST_PATCH_{_NONCE_VAR}: FAIL_TO_PASS_IDS_DO_NOT_COLLECT '
            '(even with the patch applied)"\n'
            "  tail -20 /tmp/collect.log\n"
            "fi"
        )
    else:
        # Pro: ``before_repo_set_cmd`` already checks out the oracle test
        # files from the fix commit, so applying test_patch on top CONFLICTS
        # ("patch does not apply") — it stays a fallback used only when the
        # ids do not collect.
        before_cmd = oracle["before_repo_set_cmd"] or "true"
        oracle_setup = (
            f"{before_cmd}\n"
            'echo "SWEBENCH_SETUP: before_repo_set_cmd rc=$?"\n'
            "if ! collect; then\n"
            '  echo "SWEBENCH_SETUP: ids missing after before_cmd;'
            ' applying test_patch as fallback"\n'
            "  if [ -s /tmp/test_patch.diff ]; then\n"
            "    git apply -v /tmp/test_patch.diff 2>&1 "
            "|| git apply -v --3way /tmp/test_patch.diff 2>&1 || true\n"
            "  fi\n"
            "fi"
        )
        # FROZEN origin/main semantics: the fail_to_pass ids MUST collect
        # pre-patch, or the instance is task_broken (excluded from the
        # denominator, exactly as every published Pro archive was labeled).
        baseline_gate = (
            "if ! collect; then\n"
            f'  echo "SWEBENCH_BASELINE_{_NONCE_VAR}: BROKEN_NO_COLLECT '
            '(fail_to_pass ids do not exist)"\n'
            "  tail -20 /tmp/collect.log\n"
            "  exit 3\n"
            "fi\n"
            'if python -m pytest -q "${SWEBENCH_F2P[@]}" >/tmp/baseline.log 2>&1 </dev/null; then\n'
            f'  echo "SWEBENCH_BASELINE_{_NONCE_VAR}: BROKEN_ALREADY_GREEN '
            '(fail_to_pass passes unpatched)"\n'
            "  tail -20 /tmp/baseline.log\n"
            "  exit 3\n"
            "fi\n"
            f'echo "SWEBENCH_BASELINE_{_NONCE_VAR}: OK (red as expected)"'
        )
        post_patch_check = ""
    return _GRADE_SCRIPT.format(
        workdir=profile.container_workdir,
        env_setup=profile.env_setup.rstrip() or "true &&",
        test_patch=_heredoc(oracle["test_patch"]),
        prediction=_heredoc(prediction),
        oracle_setup=oracle_setup,
        baseline_gate=baseline_gate,
        post_patch_check=post_patch_check,
        f2p=" ".join(_shq(t) for t in oracle["fail_to_pass"]),
        p2p=" ".join(_shq(t) for t in _pass_to_pass_for(inst, oracle)[0]),
    )


# Runs inside the instance's official image. Order matters: the test patch
# (the ORACLE) is applied first and the prediction second, so a prediction that
# tries to undo the oracle fails loudly instead of silently winning.
#
# Verdict markers carry a ``_${_N}`` suffix and every pytest invocation gets
# ``</dev/null``, so arm-authored test code can neither forge a marker into the
# log nor consume anything from stdin (which is already ``/dev/null`` — see
# ``_docker_bash``). The nonce arrives as the ENVIRONMENT variable
# ``SWEBENCH_NONCE``, is copied into the shell variable ``_N`` and then
# unset: pytest and everything the graded code runs therefore inherit no nonce
# at all, where before they could have read it and printed a valid marker.
# The hidden test ids live in bash ARRAYS: element quoting survives ids with
# spaces (``test_sign_happy[some message]``) that unquoted expansion would
# word-split and glob-expand.
_GRADE_SCRIPT = r"""
set -o pipefail
_N="${{SWEBENCH_NONCE}}"
unset SWEBENCH_NONCE
# COLOUR OFF, three ways. moto's own `pyproject.toml` sets
# `addopts = "--color=yes"`, so pytest coloured its output even into a pipe and
# every ANSI-wrapped `PASSED`/section header slipped past the anchored per-node
# parser: 153 tests passed and 0 node outcomes were extracted. `NO_COLOR`/
# `PY_COLORS` cover every pytest invocation in this script (including the
# profile-specific baseline gates); `--color=no` is repeated on the parsed
# invocations because addopts are PREPENDED, so a command-line flag wins over
# whatever the repository configured.
export NO_COLOR=1
export PY_COLORS=0
cd {workdir} 2>/dev/null || cd "$(ls -d /*/ | head -1)"
{env_setup} true
git config --global --add safe.directory '*' 2>/dev/null || true

SWEBENCH_F2P=({f2p})
SWEBENCH_P2P=({p2p})

cat > /tmp/test_patch.diff <<'SWEBENCH_TEST_PATCH_EOF'
{test_patch}
SWEBENCH_TEST_PATCH_EOF

cat > /tmp/prediction.diff <<'SWEBENCH_PRED_EOF'
{prediction}
SWEBENCH_PRED_EOF

# Does every fail_to_pass id EXIST? pytest exits 4 for a missing file or a
# missing ::id.
#
# Do NOT grep for "no tests ran": `--collect-only -q` prints that line on
# EVERY successful collection, because collect-only runs nothing. Treating it
# as a failure marks healthy instances as broken — it scored 6 of these 10 as
# unusable when they were fine.
collect() {{
  python -m pytest --collect-only -q --color=no "${{SWEBENCH_F2P[@]}}" >/tmp/collect.log 2>&1 </dev/null
  rc=$?
  if [ "$rc" = "4" ] || grep -qi "ERROR: not found\|ERROR: file or directory not found" /tmp/collect.log; then
    return 1
  fi
  return 0
}}

# ORACLE SETUP — profile-specific, built by `_grade_script_for`. Pro runs its
# `before_repo_set_cmd` (which already installs the oracle test files) with
# the test patch as a collect-fallback; swe-rebench applies the test patch
# unconditionally (there is no setup command, and skipping the patch when the
# f2p test NAMES already exist at base leaves the OLD assertions in place —
# a false BROKEN_ALREADY_GREEN).
git reset --hard HEAD >/dev/null 2>&1 || true
git clean -fd >/dev/null 2>&1 || true
{oracle_setup}

# BASELINE GATE — profile-specific, built by `_grade_script_for`. Pro keeps
# its frozen origin/main semantics (persistent no-collect = hard
# BROKEN_NO_COLLECT exit -> task_broken); swe-rebench treats pre-patch
# no-collect as a red baseline (TDD instances) and checks post-patch instead.
{baseline_gate}

if git apply -v /tmp/prediction.diff 2>&1 || git apply -v --3way /tmp/prediction.diff 2>&1; then
  echo "SWEBENCH_APPLY_${{_N}}: OK"
else
  echo "SWEBENCH_APPLY_${{_N}}: FAILED"
  exit 2
fi

{post_patch_check}

# PER-NODE OUTCOMES, not an exit code. pytest exits 0 when every selected test
# SKIPS, so `if ! pytest -q <ids>` graded an all-skipped run as RESOLVED.
# `-rpfEsxX` is `-rA` minus `P`: the same per-node report WITHOUT echoing a
# passing test's captured stdout, which would let arm-authored code print a
# forged `PASSED <id>` line into the very section the parser reads.
# The report goes between nonce-suffixed BEGIN/END markers; the Python side
# (`_parse_node_outcomes` + `evaluate_node_coverage`) requires an explicit
# PASSED for every declared id and refuses if the region is missing.
run_ids() {{
  label="$1"; shift
  python -m pytest -q -rpfEsxX --color=no "$@" </dev/null >"/tmp/nodes-$label.log" 2>&1
  rc=$?
  tail -40 "/tmp/nodes-$label.log"
  # pytest's OWN tally, echoed outside the region: when the region extraction is
  # what broke, this is the only evidence that the tests ran at all, and the
  # Python side compares the two (`node_parse_failure`). Unanchored on purpose —
  # a coloured tally line does not start with a digit — and the LAST match wins,
  # because pytest's tally is the final line it writes and nothing a test prints
  # can appear after it.
  echo "SWEBENCH_TALLY_${{_N}}: $label $(grep -aE '[0-9]+ (passed|failed|errors?|skipped|deselected|xfailed|xpassed)|no tests ran' "/tmp/nodes-$label.log" | tail -1)"
  echo "SWEBENCH_NODES_${{_N}}: BEGIN $label rc=$rc"
  # NOT anchored on `^=*`: a coloured header is `\033[1m===== short test summary
  # info =====\033[0m`, which the anchored pattern missed entirely — the region
  # came out EMPTY on a run where 153 tests passed. The Python parser still
  # narrows to the LAST properly-formed header, so a forged phrase in a failing
  # test's captured output only widens the region, it cannot become the section
  # that is read.
  sed -n '/short test summary info/,$p' "/tmp/nodes-$label.log"
  echo "SWEBENCH_NODES_${{_N}}: END $label"
  return $rc
}}

fail=0
if ! run_ids fail_to_pass "${{SWEBENCH_F2P[@]}}"; then fail=1; fi
if [ "${{#SWEBENCH_P2P[@]}}" -gt 0 ]; then
  if ! run_ids pass_to_pass "${{SWEBENCH_P2P[@]}}"; then fail=1; fi
fi
if [ "$fail" = "0" ]; then
  echo "SWEBENCH_RESULT_${{_N}}: RESOLVED"
else
  echo "SWEBENCH_RESULT_${{_N}}: UNRESOLVED"
fi
"""


# --------------------------------------------------------------------------- #
# selftest — validate the ORACLE before trusting any measurement
# --------------------------------------------------------------------------- #


def _relpath_str(p: Path) -> str:
    """Repo-relative when it can be, absolute otherwise (tests repoint dirs)."""
    try:
        return str(p.relative_to(FACTORY_ROOT))
    except ValueError:
        return str(p)


def _selftest_log_path(instance_id: str) -> Path:
    """Where a gold-patch control log lives. COMMITTED, outside ``runs/``.

    The control is the entire argument for believing a published number ("the
    gold patch resolves through this exact plumbing"), and its evidence was
    being written into gitignored scratch that the next sweep wipes: 0 of the
    19 published swe-rebench instances retained one. The instance id is used
    verbatim as the filename — every pinned id is already a safe basename
    (``owner__repo-1234``), and anything with a separator in it would be a
    manifest defect worth failing on.
    """
    if "/" in instance_id or instance_id in {"", ".", ".."}:
        raise SystemExit(f"instance id {instance_id!r} is not a usable filename")
    return SELFTEST_LOG_DIR / f"{instance_id}.log"


def _write_selftest_log(instance_id: str, log: str) -> Path:
    p = _selftest_log_path(instance_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(log, encoding="utf-8")
    return p


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

    The gold patch is read from the digest-verified oracle store where the
    profile ships it in-row (swe-rebench), and fetched just-in-time from the
    dataset API otherwise (old Pro pins — a rate-limited path, one reason Pro
    is frozen). Either way it is never written next to a run, so it cannot
    leak into an arm's working tree.
    """
    manifest = _manifest()
    targets = (
        [i for i in manifest["instances"] if i["instance_id"] == instance_id]
        if instance_id
        else manifest["instances"]
    )
    if not targets:
        raise SystemExit(f"{instance_id!r} is not in the pinned manifest")
    # Refuse up front (with the actionable fix) rather than crashing on the
    # first instance mid-way through docker pulls.
    _assert_oracle_store_complete(targets)

    oracles = {i["instance_id"]: _oracle_for(i) for i in targets}
    # The HF lookup is only for instances whose oracle record carries no gold
    # patch (old Pro pins). For swe-rebench this set is empty and no network
    # call happens at all.
    needs_lookup = {
        iid for iid, rec in oracles.items() if not rec["gold_patch"].strip()
    }
    gold = _gold_patches(needs_lookup, _profile_of(manifest)) if needs_lookup else {}
    results: list[dict[str, Any]] = []
    for inst in targets:
        iid = inst["instance_id"]
        patch = oracles[iid]["gold_patch"] or gold.get(iid, "")
        print(f"\n=== selftest {iid[:60]} ===", flush=True)
        if not patch.strip():
            results.append({"instance_id": iid, "gold_resolves": None, "note": "no gold patch"})
            print("  no gold patch in dataset")
            continue

        image = _image_for(inst)
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

        # CONTROL = MEASUREMENT (swe-rebench): the gold patch is graded in
        # the same topology the arms run and are graded in — a PREPARED
        # fresh clone mounted over the workdir. Grading the image's baked
        # tree instead let three instances pass the control and then die at
        # the run's collect gate on missing build artifacts (proxy ≠ real).
        # An instance whose install step cannot succeed in this topology is
        # excluded HERE, before any model spend. Pro (frozen) stays baked.
        profile = _profile_of(inst)
        mount: Path | None = None
        if profile.name == "swe-rebench":
            # OUTSIDE the repo. The grade script applies the test patch AND the
            # GOLD patch into this tree, so `runs/<id>/selftest/repo/` was the
            # answer, decoded, on the host, next to every arm's run dir.
            repo = _selftest_mount_dir(iid)
            _clone(inst, repo)
            prep_error = _prepare_cloned_tree(inst, repo, timeout_s=timeout_s)
            if prep_error:
                results.append(
                    {
                        "instance_id": iid,
                        "gold_resolves": None,
                        "note": "install_failed_in_mounted_topology",
                        "detail": prep_error[-500:],
                    }
                )
                print("  install step failed in the mounted-clone topology")
                continue
            mount = repo

        # The gold patch is code-only by construction, but strip anyway: if the
        # dataset's `patch` ever included a test edit, grading it would validate
        # the oracle against a modified oracle. The collection-channel REFUSAL
        # is off here: the maintainers' own fix legitimately edits setup.py, and
        # the gold patch is not an arm gaming its grader.
        code_only, _, stripped = split_diff(patch, refuse_collection_channels=False)
        nonce = secrets.token_hex(8)
        script = _grade_script_for(inst, code_only)
        proc = _docker_bash(
            image, script, timeout_s, nonce=nonce, mount=mount,
            workdir=profile.container_workdir,
        )
        log = (proc.stdout or "") + (proc.stderr or "")
        human_log, node_regions = _split_node_regions(log, nonce)
        # COMMITTED, and outside `runs/` — `runs/` is gitignored scratch that
        # `_reset_run_artifacts` wipes, which is why 0 of the 19 published
        # swe-rebench instances retained the control log that cleared them.
        _write_selftest_log(iid, human_log)
        if mount is not None:
            # It holds the gold patch. Nothing needs it once graded.
            shutil.rmtree(mount.parent, ignore_errors=True)

        # Per-node, same rule as `grade`: an all-skipped gold patch is not a
        # working oracle, and the CONTROL is where that has to be caught.
        f2p_outcomes = _parse_node_outcomes(node_regions.get("fail_to_pass", ""))
        p2p_outcomes = _parse_node_outcomes(node_regions.get("pass_to_pass", ""))
        f2p_ok, f2p_reasons = evaluate_node_coverage(
            oracles[iid]["fail_to_pass"], f2p_outcomes
        )
        p2p_ids, p2p_source = _pass_to_pass_for(inst, oracles[iid])
        p2p_ok, p2p_reasons = evaluate_node_coverage(p2p_ids, p2p_outcomes)
        nodes_ok = f2p_ok and p2p_ok
        # Same distinction as `grade`, and the CONTROL is where it matters most:
        # "the gold patch does not resolve" would otherwise be the label on a
        # harness that simply could not read pytest's report.
        tallies = _tally_lines(log, nonce)
        parse_failures = [
            f"{label}: {why}"
            for label, outcomes in (
                ("fail_to_pass", f2p_outcomes),
                ("pass_to_pass", p2p_outcomes),
            )
            if label in tallies
            and (why := node_parse_failure(tallies[label], outcomes)) is not None
        ]
        resolved = (
            f"{_marker('SWEBENCH_RESULT', nonce)}: RESOLVED" in log
            and nodes_ok
            and not parse_failures
        )
        # POST_PATCH is swe-rebench's broken-instance signal (ids that do not
        # collect even WITH the gold patch can never pass); BROKEN_NO_COLLECT
        # is Pro's frozen pre-patch equivalent.
        if (
            f"{_marker('SWEBENCH_POST_PATCH', nonce)}: FAIL_TO_PASS_IDS_DO_NOT_COLLECT"
            in log
            or f"{_marker('SWEBENCH_BASELINE', nonce)}: BROKEN_NO_COLLECT" in log
        ):
            note = "fail_to_pass_ids_do_not_collect"
        elif f"{_marker('SWEBENCH_BASELINE', nonce)}: BROKEN_ALREADY_GREEN" in log:
            note = "baseline_already_green"
        elif f"{_marker('SWEBENCH_APPLY', nonce)}: FAILED" in log:
            note = "gold_patch_did_not_apply"
        elif resolved:
            note = "ok"
        elif parse_failures:
            note = "grade_parse_failed"
        else:
            note = "gold_patch_does_not_resolve"
        # `None`, not `False`: a report that did not parse is "could not check",
        # which `selftest_working_instances` already refuses to count as a
        # working oracle. Calling it False would blame the dataset for a defect
        # in this harness.
        gold_resolves = None if note == "grade_parse_failed" else resolved
        results.append(
            {
                "instance_id": iid,
                "gold_resolves": gold_resolves,
                "note": note,
                "node_parse_failures": parse_failures,
                "stripped_from_gold": stripped,
                "node_coverage_ok": nodes_ok,
                "node_coverage_reasons": f2p_reasons + p2p_reasons,
                "pass_to_pass_count": len(p2p_ids),
                "pass_to_pass_source": p2p_source,
                "control_log": _relpath_str(_selftest_log_path(iid)),
            }
        )
        print(f"  gold_resolves={gold_resolves}  ({note})")

    out = SWE_DIR / "selftest.json"
    out.write_text(
        json.dumps(
            {"checked_at": datetime.now(UTC).isoformat(), "results": results}, indent=2
        ),
        encoding="utf-8",
    )
    for line in selftest_summary_lines(results, out):
        print(line)


def selftest_summary_lines(results: list[dict[str, Any]], out: Path) -> list[str]:
    """The control's closing summary. Pure, so its arithmetic is testable.

    ``grade_parse_failed`` is named SEPARATELY from a gold patch that does not
    resolve, for the same reason ``grade`` gives it its own outcome: one is a
    statement about the DATASET, the other about THIS HARNESS. ``gold_resolves``
    is three-state, so the old ``ok < len(results)`` test counted an unreadable
    row as a non-resolving oracle — blaming the dataset for our own defect, in
    the one output whose entire job is to say whether the oracle works.
    """
    ok = sum(1 for r in results if r.get("gold_resolves"))
    parse_failed = [r for r in results if r.get("note") == "grade_parse_failed"]
    lines = [f"\n{ok}/{len(results)} instances have a WORKING oracle -> {out}"]
    if parse_failed:
        lines.append(
            f"  of which {len(parse_failed)} could not be CHECKED at all — THIS "
            "HARNESS could not read pytest's per-node report: "
            + ", ".join(str(r.get("instance_id")) for r in parse_failed)
            + ". Fix the harness; these say nothing about the dataset."
        )
    if ok < len(results) - len(parse_failed):
        lines.append(
            "Instances whose gold patch does not resolve are NOT factory failures. "
            "Exclude them, or the score measures the harness."
        )
    return lines


def gold_touched_files(instance_id: str) -> list[str]:
    """Production files the maintainers' real fix changed (tests excluded).

    Lets ``grade`` record whether the arm even edited the right place. Without
    it, every failure collapses into one ``wrong_patch`` label, and a patch
    that found the exact right function but used the wrong string constant is
    indistinguishable from one that never located the code at all. Those are
    completely different failures and should never share a name.

    The gold patch comes from the digest-verified oracle store when the
    profile ships it in-row; the network lookup is the old-Pro fallback (and
    was a measured rate-limit failure mode under a parallel sweep —
    ``gold_files_lookup_ok`` exists because of it).
    """
    inst = _instance(instance_id)
    patch = _oracle_for(inst)["gold_patch"]
    if not patch.strip():
        patch = _gold_patches({instance_id}, _profile_of(inst)).get(instance_id, "")
    _, kept, _ = split_diff(patch)
    return kept


def _gold_patches(wanted: set[str], profile: DatasetProfile) -> dict[str, str]:
    """Fetch gold patches just-in-time from the dataset API (Pro fallback).

    Never persisted beside a run. Profiles with ``gold_in_row`` never reach
    this — their gold patch is pinned in the manifest at fetch time.
    """
    found: dict[str, str] = {}
    for off in range(0, profile.pool_cap, 100):
        page = _fetch_rows(off, 100, dataset=profile.dataset, split=profile.split)
        for row in page:
            if row["instance_id"] in wanted:
                found[row["instance_id"]] = row.get("patch") or ""
        if len(found) == len(wanted) or len(page) < 100:
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


def _scan_response_bodies(state_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Return ``(records, scan_warnings)`` from the response-body stream.

    Response coverage is a WARNINGS-class artifact by contract — so an
    UNREADABLE stream must degrade to a warning too, never crash ``audit()``
    before it writes ``audit.json`` (which would invalidate the run and
    promote a warnings-class artifact to failure-class through the back
    door). Contrast ``_scan_prompt_bodies``, which stays strict: prompt
    bodies are legitimately failure-class.
    """
    records: list[dict[str, Any]] = []
    scan_warnings: list[str] = []
    for f in sorted((state_root / "state" / "events").glob("response_bodies.ndjson*")):
        try:
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("event") == "response_body":
                        records.append(rec)
        except OSError as exc:
            scan_warnings.append(
                f"response-body stream {f.name} is unreadable ({exc}) — "
                "response coverage for this segment is unknown"
            )
    return records, scan_warnings


def _trajectory_files(state_root: Path) -> list[Path]:
    return sorted((state_root / "state" / "events" / "trajectories").glob("*.ndjson"))


# Characters that legitimately terminate a path mention. Used to decide
# whether a ``bench/swebench/runs/<id>/<arm>`` reference stayed inside the
# run's own subtree ("/" continues INTO the subtree) or merely named the dir.
_PATH_BOUNDARY = set("/'\"`)]}>,;: \t\n\\")

# Trajectory events that are HARNESS-authored, not arm actions. The
# SystemPromptEvent legitimately contains the run's own cwd (measured: it
# false-flagged 13/19 factory rows in the first live sweep), and user-source
# MessageEvents are the harness's task prompt. Only the arm's actions and
# the environment's responses to them can constitute a probe.
_HARNESS_AUTHORED_KINDS = ("SystemPromptEvent",)


# OpenHands truncates oversized observations with this sentinel — sometimes
# MID-PATH, leaving a fragment like ``bench/swebench/ru<response clipped``
# that no prefix rule can resolve. A fragment is allowed ONLY when it is a
# strict prefix of the run's own subtree AND the divergence point is exactly
# this sentinel; any other truncated form stays flagged.
_CLIP_SENTINEL = "<response clipped"

# The OTHER way to the answer: don't decode the local store, fetch the public
# fix. Every instance is a real merged PR, so the gold patch is one HTTP
# request away — and shell-level network is not technically blocked in any arm
# (only forbidden by the prompt), which the README already lists as the
# residual risk. Detection is therefore the control, so it belongs here.
#
# Each pattern requires an actual RETRIEVAL shape, not a mention: `curl` and
# `wget` need a URL, `urlopen` needs one too. A bare "curl" in prose or in an
# echoed README is not a probe, and a detector that flags those flags
# everything (13/19 rows were false-flagged once already by an over-strict
# own-cwd rule).
_NETWORK_PROBE_PATTERNS = (
    ("curl", re.compile(r"\bcurl\b[^\n]{0,200}?(?:https?://|ftp://)")),
    ("wget", re.compile(r"\bwget\b[^\n]{0,200}?(?:https?://|ftp://)")),
    ("git fetch/pull/ls-remote", re.compile(r"\bgit\s+(?:fetch|pull|ls-remote)\b")),
    ("git remote add", re.compile(r"\bgit\s+remote\s+add\b")),
    ("gh cli", re.compile(r"\bgh\s+(?:pr|api|issue|repo|release|search|browse)\b")),
    ("urlopen", re.compile(r"\burlopen\b[^\n]{0,200}?https?://")),
    ("github api/raw", re.compile(r"https?://(?:api|raw)\.githubusercontent\.com|https?://api\.github\.com")),
)

# A github.com URL, so the own-origin exemption below can look at its path.
_GITHUB_URL = re.compile(r"https?://(?:www\.)?github\.com/([^\s'\"`,;)\]}>]*)")

# Basenames under the run's OWN subtree that still carry answer material. The
# blanket "anything under runs/<own-id>/ is just the cwd echoing" rule was too
# generous: `grade.log` lists every hidden test id and `result.json` lists the
# gold patch's files, so reading either one of the arm's OWN previous attempt is
# reading the answer key.
_OWN_SUBTREE_ORACLE_FILES = frozenset(
    {
        "grade.log",
        "grade-nodes.log",
        "selftest.log",
        "sweep-grade.log",
        "result.json",
        "oracle.json.z",
    }
)


def _is_claude_arm(arm: str) -> bool:
    """Is this arm the Claude Code CLI, whatever model it was pointed at?

    The next sweep runs the CLI TWICE (``--model claude-opus-5`` and
    ``--model claude-opus-4-8``), so a single ``claude`` arm name stops being
    enough: two runs of one arm name would overwrite each other's run dir. If
    the arm names grow a model suffix (``claude-opus-5``), an ``arm ==
    "claude"`` equality test silently stops recognising them — and every
    claude-specific certification (the transcript scan, the missing-transcript
    failure, the ledger path) would be SKIPPED rather than applied. Prefix
    matching keeps those checks attached, which is the fail-closed direction.

    Now ALSO registry-backed, because a run key may carry an off-default model
    (``claude@claude-opus-4-8``), which no ``claude-`` prefix test matches. The
    registry answers first; the prefix rule stays as the fallback so an arm
    name nobody registered still fails closed rather than skipping the checks.
    """
    base, _model = _split_run_key(arm)
    spec = _ARMS.get(base)
    if spec is not None:
        return spec.base == "claude"
    return base == "claude" or base.startswith("claude-")


def _network_probe_hits(line: str, own_repo: str | None) -> list[str]:
    """Retrieval-shaped network activity in one trail line.

    ``own_repo`` exempts the instance's OWN origin URL: ``git remote -v``,
    ``.git/config`` and clone echoes legitimately print
    ``https://github.com/<repo>.git``, and flagging those would invalidate
    every run. ``https://github.com/<repo>/pull/981`` is NOT exempt — that is
    the fix.
    """
    hits = [name for name, pat in _NETWORK_PROBE_PATTERNS if pat.search(line)]
    for m in _GITHUB_URL.finditer(line):
        path = m.group(1).rstrip("/").removesuffix(".git")
        if own_repo and path.lower() == own_repo.strip("/").lower():
            continue  # the run's own origin
        hits.append("github.com retrieval")
        break
    return hits


def _probe_line_hits(
    line: str, instance_id: str, arm: str, own_repo: str | None = None
) -> list[str]:
    """Oracle-probe markers in one trail line, own-run references excluded.

    Flags, fail-closed:
    * ``oracle.json`` anywhere — the store's basename never legitimately
      appears in a run subtree;
    * ``swebench/manifest.json`` — the pinned manifest, in any path form (a
      target repo's OWN manifest.json — web-app manifests are common — does
      not match);
    * retrieval-shaped network activity (``_NETWORK_PROBE_PATTERNS``): every
      instance is a merged public PR, so fetching the answer is easier than
      decoding it locally;
    * any other ``bench/swebench`` path that does NOT stay inside the run's
      own ``runs/<instance>/`` subtree. The arm's cwd IS under that subtree,
      so its own paths echo constantly in commands, tracebacks, directory
      listings and condensed summaries (measured: every flagged row of the
      first live sweep was such an echo). Inside the own subtree, two subdirs
      (``selftest/`` and every OTHER arm's) and the oracle-bearing FILENAMES
      in ``_OWN_SUBTREE_ORACLE_FILES`` are still flagged — the arm's own
      ``grade.log`` is the hidden test ids and its own ``result.json`` is the
      gold patch's file list.
    """
    hits: list[str] = []
    if "oracle.json" in line:
        hits.append("oracle.json")
    if "swebench/manifest.json" in line:
        hits.append("swebench/manifest.json")
    hits.extend(_network_probe_hits(line, own_repo))
    own_dir = f"bench/swebench/runs/{instance_id}"
    for m in re.finditer(r"bench/swebench", line):
        reason = _classify_bench_ref(line[m.start():], own_dir, arm)
        if reason:
            hits.append(reason)
            break
    return hits


def _is_clipped_prefix(text: str, want: str) -> bool:
    """Is ``text`` ``want`` cut short by the observation clipper, and nothing else?

    ``bench/swebench/runs/<id>/fact<response clipped`` is the own arm's own
    path, truncated mid-segment by OpenHands. Any OTHER divergence stays
    flagged — a fragment is exempt only when it is a strict prefix of the
    expected text and the divergence point is exactly the sentinel.
    """
    n = 0
    while n < len(text) and n < len(want) and text[n] == want[n]:
        n += 1
    return n < len(want) and text[n:].startswith(_CLIP_SENTINEL)


def _classify_bench_ref(rest: str, own_dir: str, own_arm: str) -> str | None:
    """None when ``rest`` is an own-run reference; the flag reason otherwise.

    The first path segment under ``runs/<instance>/`` must be the arm's OWN
    name. It used to be checked against an allowlist of the OTHER known arm
    names (``_ARM_NAMES`` minus self, plus ``selftest``), which quietly
    stopped covering anything the tuple did not list — and the next sweep adds
    ``openhands`` and runs the Claude CLI under two model names. Inverting it
    to "own arm only" is fail-closed by construction and needs no roster.
    """
    if rest.startswith(own_dir):
        after = rest[len(own_dir):]
        if not after or (after[0] in _PATH_BOUNDARY and after[0] != "/"):
            return None  # dir-level mention of the own run dir (find/ls target)
        if after[0] == "/":
            seg = re.match(r"[^/'\"`)\]}>,;: \t\n\\]*", after[1:])
            first = seg.group(0) if seg else ""
            # `...` / `…` is the OpenHands condenser abbreviating the middle of
            # a path (measured), not a sibling directory. Safe to allow: the
            # oracle-bearing BASENAME check below still runs on the tail, so
            # `runs/<id>/.../grade.log` is flagged on the filename.
            if (
                first
                and first not in {own_arm, "...", "…"}
                and not _is_clipped_prefix(after[1:], own_arm)
            ):
                return f"another run subdir runs/…/{first} (own arm is {own_arm})"
            # NOT a blanket exemption any more: the own subtree also holds the
            # arm's own grade log (every hidden test id) and its own
            # result.json (the gold patch's file list).
            tail = re.match(r"[^'\"`)\]}>,;: \t\n\\]*", after[1:])
            for part in (tail.group(0) if tail else "").split("/"):
                if part in _OWN_SUBTREE_ORACLE_FILES:
                    return f"own run's oracle-bearing file runs/…/{part}"
            return None  # anywhere else under the own run dir — cwd echo
        # e.g. runs/<id>SUFFIX — an id-prefix collision is NOT the own dir.
        return "bench/swebench path outside the run's own subtree"
    # A truncated own path is tolerated ONLY when it diverges exactly at the
    # observation clipper's sentinel; every other divergence is foreign.
    if _is_clipped_prefix(rest, f"{own_dir}/"):
        return None
    return "bench/swebench path outside the run's own subtree"


def _scan_oracle_probes(
    state_root: Path,
    run_dir: Path,
    result: dict[str, Any],
    *,
    instance_id: str,
    arm: str,
) -> tuple[list[str], int, int]:
    """``(failures, trajectories_scanned, trails_scanned)``.

    Detection layer for the answer-leak threat: the compressed store defeats
    grep, but a process that knows the format can still decode it — and the
    fix is a public PR one HTTP request away — so the arms' OWN action trails
    are scanned. Sources: OpenHands trajectory events (the arm's actions and
    the environment's observations — NOT the harness-authored system prompt or
    task message, which legitimately carry the run's own cwd), the bare arm's
    UNTRUNCATED ``bare-commands.ndjson``, the claude arm's stream-json
    ``claude-transcript.ndjson`` (its tool calls ARE its command log), and the
    result.json transcript as a fallback. References inside the run's own
    ``runs/<instance>/<arm>/`` subtree are the arm's cwd, never a probe;
    everything else stays fail-closed. A bare run that executed commands but
    left no full command log cannot be cleared, and an unreadable trail is a
    finding, not a pass.

    The COUNTS are returned because the absence of a trail used to be silent:
    with zero trajectory files this function returned no findings at all, so a
    run whose state root had been wiped audited clean — which is exactly the
    state the four re-rolled 2026-08-03 factory rows are in. ``audit`` turns a
    zero count on an arm that made model calls into a failure.
    """
    failures: list[str] = []
    trajectories = 0
    trails = 0
    own_repo = result.get("repo") if isinstance(result.get("repo"), str) else None
    for traj in _trajectory_files(state_root):
        trajectories += 1
        trails += 1
        try:
            with traj.open(encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    hits = _probe_line_hits(line, instance_id, arm, own_repo)
                    if not hits:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        ev = {}
                    kind = str(ev.get("kind") or "")
                    if kind in _HARNESS_AUTHORED_KINDS:
                        continue  # the harness's own system prompt
                    if kind == "MessageEvent" and ev.get("source") == "user":
                        continue  # the harness's task message
                    failures.append(
                        f"oracle-probe: trajectory {traj.name}:{n} "
                        f"({kind or 'unparsed'}) references the harness's "
                        f"oracle/manifest paths {hits} — the arm went looking "
                        "for the answer; the run is invalid"
                    )
        except OSError as exc:
            failures.append(
                f"oracle-probe: trajectory {traj.name} unreadable ({exc}) — "
                "the arm's actions cannot be cleared of oracle access"
            )

    # The claude arm's trail is its stream-json transcript: assistant turns,
    # tool calls (the command-log equivalent) and tool results. Scan every
    # line fail-closed — the task prompt is passed via argv, never echoed
    # into the stream, so nothing here is harness-authored except the init
    # event's own-cwd mention, which the own-run rule already excludes.
    claude_log = run_dir / _CLAUDE_TRANSCRIPT_NAME
    if claude_log.exists():
        trails += 1
        try:
            with claude_log.open(encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    hits = _probe_line_hits(line, instance_id, arm, own_repo)
                    if hits:
                        failures.append(
                            f"oracle-probe: {_CLAUDE_TRANSCRIPT_NAME}:{n} references "
                            f"the harness's oracle/manifest paths {hits} — the "
                            "arm went looking for the answer; the run is invalid"
                        )
        except OSError as exc:
            failures.append(
                f"oracle-probe: {_CLAUDE_TRANSCRIPT_NAME} unreadable ({exc}) — "
                "the arm's actions cannot be cleared of oracle access"
            )
    elif _is_claude_arm(arm) and (
        int(result.get("num_turns") or 0) > 0
        or float(result.get("cost_usd") or 0.0) > 0
    ):
        failures.append(
            "oracle-probe: claude arm made model calls but left no "
            f"{_CLAUDE_TRANSCRIPT_NAME} — the full action trail is missing, so "
            "the run cannot be cleared of oracle access"
        )

    transcript = [s for s in (result.get("transcript") or []) if isinstance(s, dict)]
    cmd_log = run_dir / "bare-commands.ndjson"
    if cmd_log.exists():
        trails += 1
        try:
            with cmd_log.open(encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    hits = _probe_line_hits(line, instance_id, arm, own_repo)
                    if hits:
                        failures.append(
                            f"oracle-probe: bare-commands.ndjson:{n} references "
                            f"the harness's oracle/manifest paths {hits} — the "
                            "arm went looking for the answer; the run is invalid"
                        )
        except OSError as exc:
            failures.append(
                f"oracle-probe: bare-commands.ndjson unreadable ({exc}) — "
                "the arm's commands cannot be cleared of oracle access"
            )
    elif any(s.get("action") == "bash" for s in transcript):
        failures.append(
            "oracle-probe: bare arm executed commands but left no "
            "bare-commands.ndjson — the full command trail is missing, so the "
            "run cannot be cleared of oracle access"
        )
    if transcript:
        trails += 1
    for step in transcript:
        hits = _probe_line_hits(json.dumps(step), instance_id, arm, own_repo)
        if hits:
            failures.append(
                f"oracle-probe: bare-arm transcript step {step.get('step')} "
                f"references the harness's oracle/manifest paths {hits} — the "
                "arm went looking for the answer; the run is invalid"
            )
    return failures, trajectories, trails


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

    def _mtime(p: Path) -> float:
        # Lexicographic order lies here: retry-suffixed names sort before
        # their base file and "10-1" sorts before "9-1". mtime is the truth
        # for "newest"; a vanished file counts as oldest rather than crashing.
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    newest = max(trajs, key=_mtime)
    msgs = _trajectory_assistant_messages(newest)
    print(
        f"--- last {min(_SHOW_TRAJ_LAST_N, len(msgs))} of {len(msgs)} dev assistant "
        f"message(s) ({newest.name}) ---"
    )
    for m in msgs[-_SHOW_TRAJ_LAST_N:]:
        print(m)
        print("~" * 40)


def _audit_claude_run(
    run_dir: Path, result: dict[str, Any], result_valid: bool
) -> tuple[list[str], list[str], tuple[float, int, int]]:
    """The claude arm's audit: certify result.json against the CLI transcript.

    The transcript is this arm's ledger — the CLI's stream-json ``result``
    event is the only priced record of what the run cost, so the checks mirror
    the factory path's ledger<->result comparison, plus two hermeticity checks
    the other arms don't need (the init event proves what config actually
    loaded, and a leaked MCP server or web tool would void the contamination
    control). A transcript that exists but disagrees with result.json is a
    FAILURE; a MISSING transcript is a warning here and a hard oracle-probe
    failure in ``_scan_oracle_probes`` whenever the run actually made calls —
    fail-closed, same as the bare arm's missing command log.

    Returns ``(failures, warnings, (cost, tokens_in, tokens_out))`` where the
    totals are the TRANSCRIPT's, for audit.json's ledger_* fields.
    """
    failures: list[str] = []
    warnings: list[str] = []
    transcript_path = run_dir / _CLAUDE_TRANSCRIPT_NAME
    if not transcript_path.exists():
        warnings.append(
            f"no {_CLAUDE_TRANSCRIPT_NAME} — the CLI never started or was "
            "killed before emitting a line (the oracle-probe scan fails the "
            "run if it made any calls)"
        )
        return failures, warnings, (0.0, 0, 0)

    init_ev, result_ev, fallback = _parse_claude_transcript(transcript_path)

    # Hermeticity — the init event records what config the CLI REALLY loaded.
    if not init_ev:
        warnings.append("transcript has no init event — the CLI died at startup")
    else:
        mcp = init_ev.get("mcp_servers") or []
        if mcp:
            failures.append(
                f"hermetic-config: the CLI loaded MCP server(s) {mcp} — the "
                "arm did not run in the isolated configuration"
            )
        tools = {str(t) for t in (init_ev.get("tools") or [])}
        leaked = sorted(tools & {"WebFetch", "WebSearch"})
        if leaked:
            failures.append(
                f"hermetic-config: web tool(s) {leaked} were available — the "
                "contamination control (no web access) was not applied"
            )

    # The operator wants the models NAMED: a run that cannot say what model
    # produced it is not comparable to anything.
    if result_valid and not result.get("model"):
        failures.append("result.json records no model id")

    totals = _claude_usage_totals(result_ev)
    if totals is None:
        # Truncated stream: tokens are recoverable, the cost is not.
        cost, tin, tout = 0.0, fallback["tokens_in"], fallback["tokens_out"]
        if result_valid and float(result.get("cost_usd") or 0.0) > 0:
            failures.append(
                "result.json reports cost_usd but the transcript has no "
                "result event to certify it against"
            )
        elif result_valid and not result.get("error"):
            failures.append(
                "transcript has no result event yet result.json records no "
                "error — a truncated run must not read as clean"
            )
        else:
            warnings.append(
                "transcript is truncated (no result event) — cost is unknown; "
                "token counts recovered from assistant events"
            )
    else:
        cost = round(float(result_ev.get("total_cost_usd") or 0.0), 4)
        tin, tout = totals["tokens_in"], totals["tokens_out"]
        for model, mu in sorted((result_ev.get("modelUsage") or {}).items()):
            if isinstance(mu, dict):
                print(
                    f"  {model:<28} in={int(mu.get('inputTokens') or 0):,} "
                    f"out={int(mu.get('outputTokens') or 0):,} "
                    f"cacheRead={int(mu.get('cacheReadInputTokens') or 0):,} "
                    f"cost=${float(mu.get('costUSD') or 0.0):.4f}"
                )
        if result_valid:
            reported = result.get("cost_usd")
            if reported is None:
                failures.append("result.json has no cost_usd")
            elif abs(cost - float(reported)) > 0.005:
                failures.append(
                    f"cost mismatch: transcript result event sums to ${cost} but "
                    f"result.json reports ${reported} — the reported number is "
                    "not what the CLI said it spent"
                )
            for key, ledger_val in (("tokens_in", tin), ("tokens_out", tout)):
                reported_tok = result.get(key)
                if reported_tok is None:
                    continue
                try:
                    mismatch = int(reported_tok) != ledger_val
                except (TypeError, ValueError):
                    mismatch = True
                if mismatch:
                    failures.append(
                        f"{key} mismatch: transcript={ledger_val} "
                        f"result.json={reported_tok}"
                    )
    return failures, warnings, (cost, tin, tout)


# Directory names that only exist under a run dir if the run put a LIVE
# working tree there. Both are pre-isolation layouts: `runs/<id>/<arm>/repo`
# was every arm's clone, and `runs/<id>/<arm>/grade-repo` was the tree `grade`
# applied the ORACLE TEST PATCH into. `_reset_run_artifacts` deletes both at
# run start, so either one present at audit time is this run's own doing.
_IN_REPO_WORKTREE_NAMES = ("repo", "grade-repo")


def _audit_workspace_layout(run_dir: Path, arm: str) -> list[str]:
    """Fail-closed backstop for arm isolation, independent of the run functions.

    ``assert_workspace_isolated`` runs before spend, but only in the arms that
    call it. An arm that simply never calls it — or a new arm added later — puts
    its shell's cwd back inside ``bench/swebench/``, three ``..`` from
    ``oracle.json.z`` and one from every other arm's ``grade.log``. The audit
    is the one step every arm goes through, so the invariant is re-checked from
    the artifacts here rather than trusted from the code path.
    """
    failures: list[str] = []
    for name in _IN_REPO_WORKTREE_NAMES:
        tree = run_dir / name
        if tree.is_dir():
            failures.append(
                f"{arm} arm left a live working tree at {tree} — inside the "
                "harness directory, so oracle.json.z, the pinned manifest and "
                "every other arm's grade.log were reachable from the agent's "
                "shell by `cd ..`. The run function must clone into "
                "`_work_dir(instance_id, arm)` (outside the repo), call "
                "`assert_workspace_isolated` on it before spend, and copy only "
                "finished artifacts back into the run dir."
            )
    return failures


def audit(instance_id: str, arm: str, *, show_responses: bool = False) -> None:
    """Audit one run's artifacts end-to-end; exit non-zero on ANY failure.

    Checks, in order:

    1. every persona/LLM call is listed from the isolated ledger's Run rows;
    2. the ledger's cost/token sums MATCH what result.json reported;
    3. no reviewer prompt contained an error string where the diff belonged;
    4. the first dev call did not fast-fail (failed in under ~5s) — the
       unrunnable-environment signature;
    5. a failed collect precheck recorded in result.json fails the audit;
    6. the arm's action trail (OpenHands trajectories; the bare arm's full
       command log; the claude arm's CLI transcript) never references the
       harness's manifest/oracle paths — an arm that went looking for the
       answer invalidates the run.

    The claude arm has no factory Run ledger, so checks 1-4 are replaced by
    ``_audit_claude_run``: the CLI's stream-json result event is certified
    against result.json, and the init event must prove the hermetic config
    (zero MCP servers, no web tools) actually loaded.

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
    responses: list[dict[str, Any]] = []
    warnings: list[str] = []
    ledger_cost = 0.0
    ledger_in = ledger_out = 0
    print(f"=== audit {instance_id} / {arm} ===")

    if _is_claude_arm(arm):
        # The claude arm has no factory Run ledger — the CLI's own stream-json
        # transcript is the ledger. Checks 1-4 are replaced by
        # ``_audit_claude_run`` (usage/cost certification + hermeticity);
        # checks 5 (precheck) and 6 (oracle probe) below are shared.
        c_failures, c_warnings, (ledger_cost, ledger_in, ledger_out) = (
            _audit_claude_run(run_dir, result, result_valid)
        )
        failures.extend(c_failures)
        warnings.extend(c_warnings)
    else:
        failures, warnings, calls, responses, ledger = _audit_factory_ledger(
            state_root, result, result_valid, failures, arm
        )
        ledger_cost, ledger_in, ledger_out = ledger

    # 5. a recorded failed precheck is a failed run.
    pre = result.get("precheck") if isinstance(result.get("precheck"), dict) else None
    if pre is not None and not pre.get("collect_ok"):
        failures.append("result.json records a failed collect precheck")

    # 5b. the arm's LIVE working tree must not have been inside the harness
    #     directory. `assert_workspace_isolated` enforces this before spend,
    #     but only for the arms that call it — so this is the fail-closed
    #     backstop that does not depend on any run function remembering to.
    #     `_reset_run_artifacts` deletes these at run start, so a tree sitting
    #     here at audit time means THIS run put it here, three `..` from
    #     `bench/swebench/oracle.json.z`.
    failures.extend(_audit_workspace_layout(run_dir, arm))

    # 6. oracle-probe scan: any reference to the harness's manifest/oracle
    #    paths, or any retrieval-shaped network activity, in the arm's own
    #    action trail means it went looking for the answer — the run is invalid.
    probe_failures, trajectories_scanned, trails_scanned = _scan_oracle_probes(
        state_root, run_dir, result, instance_id=instance_id, arm=arm
    )
    failures.extend(probe_failures)

    # 7. an arm that made model calls MUST have left a scannable trail.
    #    Without this the scan was fail-OPEN on an empty trajectory dir: zero
    #    trails produced zero findings, so a wiped state root audited clean.
    made_calls = (
        len(calls) > 0
        or int(result.get("persona_calls") or 0) > 0
        or int(result.get("num_turns") or 0) > 0
        or float(result.get("cost_usd") or 0.0) > 0
    )
    if made_calls and trails_scanned == 0:
        failures.append(
            f"{arm} arm reports model calls but left no action trail to scan "
            "(no trajectories, no command log, no transcript) — an unscannable "
            "run cannot be cleared of oracle access"
        )

    # 8. the graded patch itself. The audit certified the LEDGER and the TRAIL
    #    and never once looked at prediction.diff, so nothing tied a published
    #    verdict to the bytes that produced it.
    pred_path = run_dir / "prediction.diff"
    prediction_sha256: str | None = None
    if pred_path.exists():
        prediction_sha256 = hashlib.sha256(pred_path.read_bytes()).hexdigest()

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
        # What was actually graded, and what the harness removed or refused
        # before grading it.
        "prediction_sha256": prediction_sha256,
        "base_commit": result.get("base_commit"),
        "stripped_test_paths": result.get("test_files_stripped") or [],
        "refused_paths": result.get("refused_paths") or [],
        "trajectories_scanned": trajectories_scanned,
        "trails_scanned": trails_scanned,
        # Recorded SEPARATELY from ``failures`` so the report can print an
        # oracle-probe count per arm without pattern-matching prose. A blank
        # column in the provenance table is a bug, not a result.
        "oracle_probe_failures": probe_failures,
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
    print(
        f"audit OK ({len(calls)} persona call(s), ${ledger_cost}) -> {out}"
        if not _is_claude_arm(arm)
        else f"audit OK (claude transcript certified, ${ledger_cost}) -> {out}"
    )


# How many OpenHands trajectory files a HEALTHY run of each arm leaves behind.
# Keyed by ARM, not by "is some other artifact present" — an arm's identity is
# what decides whether a trajectory should exist, and inferring it from a file
# on disk is the `proxy != real` class: a FACTORY run that lost its trajectories
# would have been waved through by a stray `bare-commands.ndjson` in its state
# root.
#
#   factory   — every dev call is a whole OpenHands conversation, so ONE
#               trajectory PER dev call. Fewer means the reasoning trail is
#               incomplete.
#   openhands — ONE conversation for the entire run, copied out whole as
#               `nostory-1.ndjson`, against exactly one dev Run row. The rule is
#               "at least one", never one-per-call.
#   bare      — single litellm completions, no OpenHands conversation at any
#               point, so there is no trajectory to capture and never was. Its
#               full action+observation trail is `bare-commands.ndjson`, which
#               the oracle-probe scan reads and whose absence beside executed
#               commands is already a hard FAILURE there. Warning "0 trajectory
#               files" on every bare row trained the reader to ignore the one
#               warning that matters.
#   claude    — never reaches this function (transcript-backed, see
#               `_audit_claude_run`).
# Derived from the one arm registry (``_ARMS``); kept as a name because the
# expectation is a property of the arm, and a second hand-maintained table
# would drift from it.
_ARM_TRAJECTORY_EXPECTATION = {
    name: spec.trajectories for name, spec in _ARMS.items()
}


def _trajectory_coverage_warnings(
    state_root: Path, arm: str, call_counts: dict[str, int]
) -> list[str]:
    """Trajectory-coverage warnings for one arm, scoped by what it can produce.

    An UNKNOWN arm gets the strictest rule (one trajectory per dev call), so a
    newly added arm is noisy rather than silently unchecked.

    Warnings only, never failures, in both directions: a size-capped or
    scope-disabled capture must not invalidate an otherwise-sound run. The
    fail-CLOSED rule lives in ``audit`` — an arm reporting model calls with
    ``trails_scanned == 0`` FAILS — and it is untouched by this: for bare, the
    command log is the trail that satisfies it, and for factory and openhands
    it is the trajectory itself.
    """
    dev_calls = call_counts.get("dev", 0)
    if not dev_calls:
        return []
    base, _model = _split_run_key(arm)
    rule = _ARM_TRAJECTORY_EXPECTATION.get(base, _TRAJECTORIES_PER_DEV_CALL)
    if rule == _TRAJECTORIES_TRANSCRIPT:
        return []  # certified by `_audit_claude_run` against the CLI transcript
    n = len(_trajectory_files(state_root))
    if rule == _TRAJECTORIES_NONE_EXPECTED:
        # Not "and never was" in the abstract: its trail must actually be there.
        if not (state_root / "bare-commands.ndjson").exists():
            return [
                f"{arm}: {dev_calls} dev call(s) and no bare-commands.ndjson — "
                "this arm's only action trail is missing (a hard FAILURE in the "
                "oracle-probe scan if it executed anything)"
            ]
        return []
    expected = dev_calls if rule == _TRAJECTORIES_PER_DEV_CALL else 1
    if n < expected:
        return [
            f"dev: {dev_calls} call(s) but only {n} trajectory file(s) under "
            f"state/events/trajectories (expected at least {expected} for the "
            f"{arm} arm) — the agent's reasoning trail is incomplete"
        ]
    return []


def _audit_factory_ledger(
    state_root: Path,
    result: dict[str, Any],
    result_valid: bool,
    failures: list[str],
    arm: str,
) -> tuple[
    list[str], list[str], list[dict[str, Any]], list[dict[str, Any]],
    tuple[float, int, int],
]:
    """Checks 1-4 for the ledger-backed arms (factory, bare) — verbatim the
    logic that lived inline in ``audit`` before the claude arm needed a
    transcript-backed replacement. Returns
    ``(failures, warnings, calls, responses, (cost, tokens_in, tokens_out))``.
    """
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
    responses, warnings = _scan_response_bodies(state_root)
    resp_counts: dict[str, int] = {}
    for r in responses:
        p = str(r.get("persona", ""))
        resp_counts[p] = resp_counts.get(p, 0) + 1
    traj_files = _trajectory_files(state_root)

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
    warnings.extend(_trajectory_coverage_warnings(state_root, arm, call_counts))

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

    return failures, warnings, calls, responses, (ledger_cost, ledger_in, ledger_out)


# --------------------------------------------------------------------------- #
# report — gate precision and recall
# --------------------------------------------------------------------------- #


# Every artifact a published row is derived from. ``result.json`` carries the
# run record AND the oracle verdict (``grade`` is merged into it by
# ``_write_result(..., merge=True)`` — there is no standalone grade.json);
# ``audit.json`` is the gate verdict; ``prediction.diff`` is the graded patch.
_ROW_ARTIFACTS = ("result.json", "audit.json", "prediction.diff")
_REPORT_META_NAME = "report-meta.json"

# Bumped when the archive gains a field the report reads. An older archive is
# still re-derivable; the fields it never recorded print as an explicit
# ``n/a (archive predates …)`` rather than as an empty cell that reads like a
# measured zero.
_REPORT_META_VERSION = "1.6"

# Sweep roll-ups and the gold-patch control travel INTO the archive alongside
# the per-row evidence. The retracted run's control rested on a summary that
# could not be re-derived at all: `selftest.json` sat in the working tree and
# was overwritten by the next selftest.
_ARCHIVED_EXTRAS = ("selftest.json",)
_ARCHIVED_LOG_DIRS = ("selftest-logs",)

# An OPTIONAL operator-written file inside an archive. Its contents are emitted
# verbatim at the top of any table re-derived from that archive.
#
# It exists so a run can be marked retracted WITHOUT editing the evidence: the
# rows, the audits and the original ``report-meta.json`` stay byte-for-byte as
# they were written, and the annotation is a new file beside them. Rewriting an
# archive to change what a published number says about itself is the failure
# this whole PR is about.
_DISCLAIMER_NAME = "DISCLAIMER.md"


# --------------------------------------------------------------------------- #
# contamination margins — one bound per model, with its TYPE
# --------------------------------------------------------------------------- #


class ModelBound(NamedTuple):
    """The date after which an instance is outside a model's knowledge.

    ``kind`` is load-bearing and printed: a published training cutoff and a
    release date are not the same claim. ``deepseek-v4-pro`` publishes no
    cutoff, so its bound is its RELEASE date — an upper bound on what it could
    have memorised, and a weaker guarantee than a published cutoff.
    """

    date: str
    kind: str


_BOUND_PUBLISHED = "published-cutoff"
_BOUND_RELEASE_PROXY = "release-date-proxy"

_MODEL_BOUNDS: dict[str, ModelBound] = {
    "deepseek-v4-pro": ModelBound("2026-04-24", _BOUND_RELEASE_PROXY),
    "gpt-5.4": ModelBound("2025-08-31", _BOUND_PUBLISHED),
    "gpt-5.3-codex": ModelBound("2025-08-31", _BOUND_PUBLISHED),
    "claude-opus-5": ModelBound("2026-05-31", _BOUND_PUBLISHED),
    "claude-opus-4-8": ModelBound("2026-01-31", _BOUND_PUBLISHED),
}


def _norm_model(model: str) -> str:
    """``azure/claude-opus-5[1m]`` -> ``claude-opus-5``.

    Provider prefixes and the CLI's context-variant suffix are packaging, not
    weights, and the bound table is keyed by weights.
    """
    name = str(model).strip().rsplit("/", 1)[-1]
    return re.sub(r"\[[^\]]*\]$", "", name).strip()


def _model_bound(model: str) -> ModelBound | None:
    return _MODEL_BOUNDS.get(_norm_model(model))


def _margin_days(created_at: str | None, bound: ModelBound | None) -> int | None:
    """Days from a model's bound to the instance's creation. Positive = AFTER.

    A positive margin is the only kind of instance that can carry a clean
    "this could not have been memorised" claim.
    """
    if not created_at or bound is None:
        return None
    try:
        made = datetime.fromisoformat(str(created_at).replace(" ", "T"))
        edge = datetime.fromisoformat(bound.date)
    except ValueError:
        return None
    return (made.date() - edge.date()).days


# --------------------------------------------------------------------------- #
# exact statistics, in-repo — no new dependency
# --------------------------------------------------------------------------- #
#
# n <= 19 here, so the exact forms are a few lines of `math.comb` and cost
# nothing. Wilson/normal approximations at n=19 are wrong in exactly the
# direction that flatters a small sample, and adding scipy to the bench for two
# functions is not a trade this repo should make.


def _binom_cdf(k: int, n: int, p: float) -> float:
    """``P(X <= k)`` for ``X ~ Binomial(n, p)``."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect_p(target: float, lo: float, hi: float, f: Any) -> float:
    """Solve ``f(p) == target`` on ``[lo, hi]`` for a NON-INCREASING ``f``.

    Both Clopper-Pearson bounds are expressed as binomial CDFs, which decrease
    in ``p``, so one monotonicity direction covers both. (Written the other way
    round it silently returned 1.0 for every lower bound — a confidence
    interval that always contains the estimate is not a confidence interval.)
    """
    for _ in range(80):  # 2^-80 — far finer than anything printed
        mid = (lo + hi) / 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact ``(lower, upper)`` binomial confidence bounds for ``k`` of ``n``.

    Solved by bisection on the exact binomial CDF rather than a Beta quantile,
    so it needs nothing outside the stdlib. Degenerate ends are exact: 0 of n
    has a lower bound of 0, n of n an upper bound of 1.
    """
    if n <= 0:
        return (0.0, 1.0)
    k = max(0, min(k, n))
    # Both bounds as decreasing CDFs of p:
    #   lower solves P(X <= k-1 | p) = 1 - alpha/2
    #   upper solves P(X <= k   | p) =     alpha/2
    lower = (
        0.0
        if k == 0
        else _bisect_p(1 - alpha / 2, 0.0, 1.0, lambda p: _binom_cdf(k - 1, n, p))
    )
    upper = 1.0 if k == n else _bisect_p(alpha / 2, 0.0, 1.0, lambda p: _binom_cdf(k, n, p))
    return (lower, upper)


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact McNemar p for a discordant pair count ``(b, c)``.

    The binomial sign test on the discordant pairs only — the concordant cells
    carry no information about a difference. With no discordant pairs at all
    there is nothing to test and the p-value is 1.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = float(sum(math.comb(n, i) for i in range(k + 1))) / float(2**n)
    return min(1.0, 2.0 * tail)


def _fmt_ci(k: int, n: int) -> str:
    if n <= 0:
        return "n/a (0 in denominator)"
    lo, hi = clopper_pearson(k, n)
    return f"[{lo:.0%}, {hi:.0%}]"


def _fmt_p(p: float) -> str:
    """A p-value that never rounds to a misleading ``0.000``."""
    return f"{p:.3f}" if p >= 0.001 else "<0.001"


def _fmt_rate(num: int, den: int) -> str:
    return f"{num}/{den} = {num / den:.0%}" if den else "n/a (0 in denominator)"


def _fmt_int(value: Any) -> str:
    return f"{int(value):,}" if isinstance(value, (int, float)) else "?"


# --------------------------------------------------------------------------- #
# reading rows
# --------------------------------------------------------------------------- #


def _report_rows(
    base_dir: Path,
    expected_sha: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    """Read every ``<instance>/<run-key>/result.json`` under ``base_dir``.

    Returns ``(rows, refused, foreign)``. FAIL-CLOSED: a row whose backing
    artifacts are missing or unreadable is never silently dropped and never
    emitted as a table row — it lands in ``refused`` with the exact reason,
    which the report prints. This is the same posture as the audit gate:
    evidence that cannot be produced is a refusal, not a shrug (PLAN 1.5 —
    the July retraction class was "reported rows with no raw artifacts").

    ``expected_sha`` pins the report to ONE pinned manifest: every
    result.json records the ``manifest_sha256`` it ran under, and a row from
    any other manifest (a previous dataset's runs still sitting in ``runs/``)
    goes to ``foreign`` — named in the output, merged into NO table and NO
    rate. Without this, the very next report after a dataset switch merged
    the old profile's rows into the new headline (executed probe: a Pro +
    rebench blended 100%). A row that records no sha at all is foreign too —
    unverifiable provenance is not this manifest's evidence.

    The directory NAME under the instance is the row's run key — arm plus, for
    a model-selectable arm on an off-default model, the model. The recorded
    ``arm`` field must agree with it; a row whose two identities disagree is
    refused rather than filed under either.
    """
    rows: list[dict[str, Any]] = []
    refused: list[dict[str, str]] = []
    foreign: list[dict[str, str]] = []
    for f in sorted(base_dir.glob("*/*/result.json")):
        run_dir = f.parent
        key = run_dir.name
        row_id = f"{run_dir.parent.name}/{key}"
        missing = [name for name in _ROW_ARTIFACTS if not (run_dir / name).is_file()]
        if missing:
            refused.append(
                {"row": row_id, "why": f"missing artifact(s): {', '.join(missing)}"}
            )
            continue
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            refused.append({"row": row_id, "why": f"result.json unreadable: {exc}"})
            continue
        if not isinstance(r, dict):
            refused.append({"row": row_id, "why": "result.json is not a JSON object"})
            continue
        if str(r.get("arm") or "") != key:
            refused.append(
                {
                    "row": row_id,
                    "why": f"result.json records arm {r.get('arm')!r} but sits in "
                    f"the {key!r} run directory — one run cannot be two arms",
                }
            )
            continue
        if expected_sha is not None:
            row_sha = str(r.get("manifest_sha256") or "")
            if row_sha != expected_sha:
                foreign.append(
                    {
                        "row": row_id,
                        "sha": row_sha or "(none recorded)",
                        "why": f"ran under manifest {row_sha or '(none recorded)'}, "
                        f"report is pinned to {expected_sha}",
                    }
                )
                continue
        # The audit gate. Every run must be fully auditable; a row whose
        # audit failed must not be laundered into the headline number. An
        # unreadable audit.json is a FAIL, never a pass. (A MISSING audit.json
        # no longer reaches this point — the artifact check above refuses the
        # whole row, fail-closed, where the old code showed it as "not
        # audited".)
        audit: dict[str, Any] = {}
        audit_ok: bool | None = None
        try:
            loaded = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                audit = loaded
                audit_ok = loaded.get("ok") is True
            else:
                audit_ok = False
        except (json.JSONDecodeError, OSError):
            audit_ok = False
        r["_audit"] = audit
        r["_audit_ok"] = audit_ok
        # ONE classifier, shared with the sweep roll-up — see ``classify_run``.
        # ``_run_failed`` used to be ``bool(result["error"])`` here while the
        # sweep used the child's exit code, and the two published different
        # denominators for the same run.
        status, detail = classify_run(r)
        r["_status"] = status
        r["_status_detail"] = detail
        r["_run_failed"] = status in (_RUN_FAILED, _RUN_NO_RESULT)
        r["_budget_exhausted"] = status == _RUN_BUDGET_EXHAUSTED
        r["_arm"] = key
        r["_attempt"] = int(r.get("attempt") or 1)
        cache_read = int(r.get("cached_input_tokens") or 0)
        r["_cache_read"] = cache_read
        r["_fresh_in"] = max(int(r.get("tokens_in") or 0) - cache_read, 0)
        r["_run_dir"] = str(run_dir)
        rows.append(r)
    return rows, refused, foreign


def _row_models(r: dict[str, Any]) -> list[str]:
    """Which models this row's LEDGER says ran — never the config's intent.

    The retracted run's config named one model while the ledger showed 7
    escalations to a hard tier, 4 of them behind resolved rows. Config is
    intent; the ledger is what happened.
    """
    used = r.get("models_used")
    if isinstance(used, list) and used:
        return sorted({str(m) for m in used})
    nominal = r.get("model")
    return [str(nominal)] if nominal else []


def _nominal_model(rows: list[dict[str, Any]], arm: str) -> str | None:
    """The model an arm CLAIMS, for the "does the model vary?" column.

    Registry first (the claude arms pin theirs); otherwise the ``model`` field
    the rows recorded, which for the factory/openhands arms is the dev/standard
    route. ``None`` means no row recorded one — printed as such, never guessed.
    """
    spec = _ARMS.get(_split_run_key(arm)[0])
    if spec is not None and spec.model:
        return spec.model
    seen = {str(r["model"]) for r in rows if r.get("model")}
    return sorted(seen)[0] if len(seen) == 1 else None


def _arm_label(arm: str) -> str:
    spec = _ARMS.get(_split_run_key(arm)[0])
    return spec.harness if spec is not None else f"(unregistered arm {arm})"


def _arm_cost_source(arm: str) -> str:
    spec = _ARMS.get(_split_run_key(arm)[0])
    return spec.cost_source if spec is not None else "unknown"


def _arm_has_chain(arm: str) -> bool:
    spec = _ARMS.get(_split_run_key(arm)[0])
    return bool(spec is not None and spec.has_chain)


class ArmView(NamedTuple):
    """One arm's rows, already bucketed by the audit + run gate.

    ``valid`` is the denominator of every published rate: graded, not
    task-broken, not a harness parse failure, audit-ok, and either completed or
    BUDGET-EXHAUSTED. A cap hit is a counted attempt for every arm
    (pre-registered decision rule 4) — excluding one silently improved the
    retracted run's Claude denominator.

    ``ungradable`` is the not-the-arm's-fault bucket, split by outcome so the
    gate accounting can name each kind: a broken TASK and a broken HARNESS are
    both excluded, and neither may be presented as the arm failing.
    """

    arm: str
    rows: list[dict[str, Any]]
    graded: list[dict[str, Any]]
    gradable: list[dict[str, Any]]
    valid: list[dict[str, Any]]
    excluded: list[dict[str, Any]]
    resolved: list[dict[str, Any]]
    ungradable: dict[str, list[dict[str, Any]]]


# Outcomes that are NOT a verdict on the arm, and are therefore excluded from
# every published rate. ``grade_parse_failed`` joins ``task_broken`` here: a
# per-node report this harness could not read says nothing about the patch, and
# counting it as an unresolved attempt turns one harness defect into a uniform
# 0% across every arm — a benchmark result that looks like a finding.
_UNGRADABLE_PREFIXES = ("task_broken", "grade_parse_failed")


def _ungradable_kind(outcome: str) -> str | None:
    for prefix in _UNGRADABLE_PREFIXES:
        if outcome.startswith(prefix):
            return prefix
    return None


def _arm_view(rows: list[dict[str, Any]], arm: str) -> ArmView:
    arm_rows = [r for r in rows if r["_arm"] == arm]
    graded = [
        r for r in arm_rows if (r.get("grade") or {}).get("oracle_resolved") is not None
    ]
    ungradable: dict[str, list[dict[str, Any]]] = {p: [] for p in _UNGRADABLE_PREFIXES}
    gradable = []
    for r in graded:
        kind = _ungradable_kind(str((r.get("grade") or {}).get("outcome", "")))
        if kind is None:
            gradable.append(r)
        else:
            ungradable[kind].append(r)
    valid = [
        r for r in gradable if r["_audit_ok"] is True and not r["_run_failed"]
    ]
    valid_ids = {id(r) for r in valid}
    excluded = [r for r in gradable if id(r) not in valid_ids]
    resolved = [r for r in valid if (r.get("grade") or {}).get("oracle_resolved")]
    return ArmView(
        arm, arm_rows, graded, gradable, valid, excluded, resolved, ungradable
    )


def _exclusion_reason(r: dict[str, Any]) -> str:
    """Why one row is not in its arm's denominator, and WHAT IT SCORED.

    Both halves matter. The old line named only excluded PASSES, so an excluded
    FAILURE vanished with no verdict shown — and a reader could not tell
    whether the exclusions were helping or hurting the published rate.
    """
    oracle = (r.get("grade") or {}).get("oracle_resolved")
    verdict = "PASS" if oracle else ("?" if oracle is None else "FAIL")
    why: list[str] = []
    if r["_status"] == _RUN_NO_RESULT:
        why.append("no result.json")
    elif r["_run_failed"]:
        why.append(f"run failed ({str(r['_status_detail'] or '')[:80]})")
    if r["_audit_ok"] is False:
        why.append("audit failed")
    elif r["_audit_ok"] is None:
        why.append("not audited")
    return f"{str(r.get('instance_id'))[:46]} [{verdict}]: {', '.join(why) or 'unknown'}"


# --------------------------------------------------------------------------- #
# the five pre-registered tables
# --------------------------------------------------------------------------- #


def _table1_headline(views: list[ArmView]) -> list[str]:
    """Harness AND models AND cost source, inline on every row.

    A headline row torn out of this file must still say what produced it: an
    arm's score is a property of the (harness, model set) pair, never of the
    model alone and never of the harness alone.
    """
    lines = [
        "## Table 1 — headline, one row per arm",
        "",
        "Harness and models are repeated per row, not cross-referenced. The model",
        "column is filled **from the per-row ledger, not from `routes.yaml`** —",
        "config is intent, the ledger is what happened.",
        "",
        "`fresh in` and `cache read` are separate columns on purpose: one blended",
        '"tokens in" column mixed them last time and cache share differed 0%-97%',
        'across arms, which made the published "34x tokens" claim wrong by 4.5x.',
        "",
        "| arm | harness | model(s) actually used | resolved / audited-valid | rate "
        "| 95% CI (Clopper-Pearson) | invalid rows | budget-exhausted | fresh in "
        "| cache read | out | wall s (median) | $ | cost source |",
        "|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for v in views:
        # CALL counts where the ledger recorded them (the spec's "(n calls)"),
        # row counts otherwise, and the unit is stated either way — "7" with no
        # unit is how a hard-tier escalation count gets mistaken for a row count.
        calls: dict[str, int] = {}
        rows_per_model: dict[str, int] = {}
        for r in v.rows:
            for m in _row_models(r):
                rows_per_model[m] = rows_per_model.get(m, 0) + 1
            for c in r.get("model_calls") or []:
                if isinstance(c, dict) and isinstance(c.get("calls"), int):
                    name = str(c.get("model"))
                    calls[name] = calls.get(name, 0) + int(c["calls"])
        if calls:
            models = ", ".join(
                f"`{m}` ({calls[m]} calls)"
                if m in calls
                else f"`{m}` ({n} rows, calls not recorded)"
                for m, n in sorted(rows_per_model.items())
            )
        else:
            models = (
                ", ".join(
                    f"`{m}` ({n} rows, calls not recorded)"
                    for m, n in sorted(rows_per_model.items())
                )
                or "n/a (no model recorded in any row)"
            )
        walls = sorted(
            float(r["wall_clock_s"]) for r in v.valid if r.get("wall_clock_s") is not None
        )
        median = f"{statistics.median(walls):.1f}" if walls else "n/a"
        lines.append(
            f"| {v.arm} | {_arm_label(v.arm)} | {models} "
            f"| {len(v.resolved)}/{len(v.valid)} "
            f"| {_fmt_rate(len(v.resolved), len(v.valid))} "
            f"| {_fmt_ci(len(v.resolved), len(v.valid))} "
            f"| {len(v.excluded)} "
            f"| {sum(1 for r in v.valid if r['_budget_exhausted'])} "
            f"| {sum(r['_fresh_in'] for r in v.rows):,} "
            f"| {sum(r['_cache_read'] for r in v.rows):,} "
            f"| {sum(int(r.get('tokens_out') or 0) for r in v.rows):,} "
            f"| {median} "
            f"| {sum(float(r.get('cost_usd') or 0.0) for r in v.rows):.2f} "
            f"| {_arm_cost_source(v.arm)} |"
        )
    return lines


_OUTCOME_CODES = (
    "`R` resolved · `F` wrong patch · `E` empty patch · `B` task broken · "
    "`X` audit-invalid or run-failed · `!` budget-exhausted (counted as an "
    "attempt, not excluded) · `*` attempt > 1 · `·` no row"
)
# Appended ONLY when such a row exists, so an archive without one still
# re-derives byte-for-byte under `report --check`.
_PARSE_FAILED_CODE = (
    " · `P` grade-parse failed — THIS HARNESS could not read pytest's per-node "
    "report; excluded from every rate, never counted as an arm failure"
)


def _outcome_codes(rows: list[dict[str, Any]]) -> str:
    if any(
        str((r.get("grade") or {}).get("outcome") or "") == "grade_parse_failed"
        for r in rows
    ):
        return _OUTCOME_CODES + _PARSE_FAILED_CODE
    return _OUTCOME_CODES


def _outcome_cell(r: dict[str, Any] | None) -> str:
    if r is None:
        return "·"
    g = r.get("grade") or {}
    outcome = str(g.get("outcome") or "")
    if outcome == "grade_parse_failed":
        # BEFORE the audit/run gate: "the grader could not read the report" is
        # the fact about this cell, and `X` would file it under the arm's own
        # invalid rows.
        code = "P"
    elif r["_audit_ok"] is not True or r["_run_failed"]:
        code = "X"
    elif outcome.startswith("task_broken"):
        code = "B"
    elif g.get("oracle_resolved"):
        code = "R"
    elif outcome == "empty_patch":
        code = "E"
    elif g.get("oracle_resolved") is False:
        code = "F"
    else:
        code = "?"
    return code + ("!" if r["_budget_exhausted"] else "") + ("*" if r["_attempt"] > 1 else "")


def _table2_matrix(
    rows: list[dict[str, Any]],
    arms: list[str],
    created: dict[str, str],
    bound_models: list[str],
) -> list[str]:
    """Per-instance outcomes, with a contamination margin per bound model.

    No absolute rate is published without its margin column (pre-registered
    decision rule 3): a resolve on an instance INSIDE a model's bound is not
    the same evidence as a resolve outside it.
    """
    by_cell: dict[tuple[str, str], dict[str, Any]] = {
        (str(r.get("instance_id")), r["_arm"]): r for r in rows
    }
    instances = sorted(
        {str(r.get("instance_id")) for r in rows},
        key=lambda i: (created.get(i, "9999"), i),
    )
    margin_heads = "".join(
        f" margin vs `{m}` ({_MODEL_BOUNDS[_norm_model(m)].date}) |" for m in bound_models
    )
    lines = [
        "## Table 2 — per-instance outcome matrix",
        "",
        _outcome_codes(rows),
        "",
        "A POSITIVE margin means the instance was created after that model's",
        "bound, i.e. it cannot have been memorised. Bound TYPE is in Table 4's",
        "footnote: a published cutoff and a release-date proxy are different",
        "claims.",
        "",
        "| instance | created_at |" + margin_heads + "".join(f" {a} |" for a in arms),
        "|---|---|" + "---:|" * len(bound_models) + ":-:|" * len(arms),
    ]
    for iid in instances:
        cells = []
        for m in bound_models:
            days = _margin_days(created.get(iid), _model_bound(m))
            if days is None:
                cells.append(" n/a |")
            else:
                cells.append(f" **+{days}** |" if days > 0 else f" {days} |")
        lines.append(
            f"| {iid[:46]} | {created.get(iid, 'n/a (not in the pinned manifest)')} |"
            + "".join(cells)
            + "".join(f" {_outcome_cell(by_cell.get((iid, a)))} |" for a in arms)
        )
    return lines


def _table3_comparisons(
    views: list[ArmView], rows: list[dict[str, Any]], created: dict[str, str]
) -> list[str]:
    """Every pair, with what is held constant and what varies.

    A comparison that varies BOTH halves of the (harness, model) pair is a
    reference point, not a measurement — printed as such, so the retracted
    run's unattributable "+58 pp scaffold lift" cannot be restated.
    """
    lines = [
        "## Table 3 — the comparisons, and which ones may mean anything",
        "",
        "Paired over instances where BOTH arms have an audited-valid row.",
        "`only-A / only-B` are the discordant cells McNemar's exact test uses;",
        "the concordant cells carry no information about a difference.",
        "",
        "| comparison | harness varies? | model varies? | paired n | only-A / only-B "
        "| McNemar exact p | what it isolates |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for i, a in enumerate(views):
        for b in views[i + 1 :]:
            pa = {
                str(r.get("instance_id")): bool((r.get("grade") or {}).get("oracle_resolved"))
                for r in a.valid
            }
            pb = {
                str(r.get("instance_id")): bool((r.get("grade") or {}).get("oracle_resolved"))
                for r in b.valid
            }
            shared = sorted(set(pa) & set(pb))
            only_a = sum(1 for i2 in shared if pa[i2] and not pb[i2])
            only_b = sum(1 for i2 in shared if pb[i2] and not pa[i2])
            spec_a = _ARMS.get(_split_run_key(a.arm)[0])
            spec_b = _ARMS.get(_split_run_key(b.arm)[0])
            harness_varies = (
                "n/a (unregistered arm)"
                if spec_a is None or spec_b is None
                else ("no" if spec_a.harness_id == spec_b.harness_id else "yes")
            )
            na = _nominal_model(a.rows, a.arm)
            nb = _nominal_model(b.rows, b.arm)
            if na is None or nb is None:
                model_varies = "n/a (nominal model not recorded)"
            else:
                model_varies = "no" if na == nb else "yes"
                observed_a = {m for r in a.rows for m in _row_models(r)}
                observed_b = {m for r in b.rows for m in _row_models(r)}
                if model_varies == "no" and observed_a != observed_b:
                    model_varies = "no (nominal) †"
            if harness_varies.startswith("n/a") or model_varies.startswith("n/a"):
                isolates = "**n/a — one half of the pair is unrecorded**"
            elif harness_varies == "yes" and model_varies.startswith("yes"):
                isolates = "**nothing attributable** — reference point only"
            elif harness_varies == "yes":
                isolates = "the harness"
            elif model_varies.startswith("yes"):
                isolates = "the model (same harness)"
            else:
                isolates = "nothing — the arms are the same pair"
            lines.append(
                f"| {a.arm} vs {b.arm} | {harness_varies} | {model_varies} "
                f"| {len(shared)} | {only_a} / {only_b} "
                f"| {_fmt_p(mcnemar_exact_p(only_a, only_b))} | {isolates} |"
            )
    lines += [
        "",
        "† nominal models match but the observed ledgers differ — the chain",
        "escalates a stuck dev to a harder tier, so a matched-weights claim must",
        "be checked against Table 4's per-tier call counts, not against config.",
        "",
        "### High-margin stratum, within each arm",
        "",
        "Descriptive only: the stratum is whatever instances post-date the arm's",
        "OWN nominal model's bound, and at this n it is a handful of rows.",
        "",
        "| arm | bound | high-margin | rest |",
        "|---|---|---:|---:|",
    ]
    for v in views:
        nominal = _nominal_model(v.rows, v.arm)
        bound = _model_bound(nominal) if nominal else None
        if bound is None:
            lines.append(
                f"| {v.arm} | n/a (no bound for "
                f"{('`' + str(nominal) + '`') if nominal else 'an unrecorded model'}) "
                "| n/a | n/a |"
            )
            continue
        hi = [
            r
            for r in v.valid
            if (_margin_days(created.get(str(r.get("instance_id"))), bound) or -1) > 0
        ]
        rest = [r for r in v.valid if r not in hi]
        lines.append(
            f"| {v.arm} | `{nominal}` after {bound.date} ({bound.kind}) "
            f"| {_fmt_rate(sum(1 for r in hi if (r.get('grade') or {}).get('oracle_resolved')), len(hi))} "
            f"| {_fmt_rate(sum(1 for r in rest if (r.get('grade') or {}).get('oracle_resolved')), len(rest))} |"
        )
    return lines


def _table4_provenance(views: list[ArmView]) -> list[str]:
    """Filled from result.json / audit.json. Any blank here is a bug."""
    lines = [
        "## Table 4 — provenance and integrity, per arm",
        "",
        "`attempts` exists because the retracted run published 4 second attempts",
        "after the integrity gate invalidated the first, disclosed nowhere. Any",
        "value > 1 is a protocol violation, not a data point.",
        "",
        "| arm | resolved model id(s) | per-tier call counts | max attempt "
        "| audit ok / invalid | action trails present | test files stripped "
        "| oracle-probe hits | p2p empty rows | p2p source(s) |",
        "|---|---|---|---:|---|---|---:|---:|---:|---|",
    ]
    for v in views:
        models = sorted({m for r in v.rows for m in _row_models(r)})
        tiers: dict[str, int] = {}
        recorded_calls = False
        for r in v.rows:
            calls = r.get("model_calls")
            if isinstance(calls, list) and calls:
                recorded_calls = True
                for c in calls:
                    if not isinstance(c, dict):
                        continue
                    tier = str(c.get("model_tier") or "—")
                    n = c.get("calls")
                    tiers[tier] = tiers.get(tier, 0) + (int(n) if isinstance(n, int) else 0)
        tier_cell = (
            ", ".join(f"{k}={v2}" for k, v2 in sorted(tiers.items()))
            if recorded_calls
            else "n/a (not recorded by these rows)"
        )
        if any("trails_scanned" in r["_audit"] for r in v.rows):
            n_trails = sum(
                1 for r in v.rows if int(r["_audit"].get("trails_scanned") or 0) > 0
            )
            trail_cell = f"{n_trails}/{len(v.rows)}"
        else:
            trail_cell = "n/a (not recorded)"
        probes = sum(len(r["_audit"].get("oracle_probe_failures") or []) for r in v.rows)
        probe_cell = (
            str(probes)
            if any("oracle_probe_failures" in r["_audit"] for r in v.rows)
            else "n/a (not recorded)"
        )
        p2p_counts = [
            (r.get("grade") or {}).get("pass_to_pass_count")
            for r in v.rows
            if isinstance((r.get("grade") or {}).get("pass_to_pass_count"), int)
        ]
        p2p_cell = str(sum(1 for c in p2p_counts if c == 0)) if p2p_counts else "n/a"
        p2p_sources = sorted(
            {
                str((r.get("grade") or {}).get("pass_to_pass_source"))
                for r in v.rows
                if (r.get("grade") or {}).get("pass_to_pass_source")
            }
        )
        lines.append(
            f"| {v.arm} "
            f"| {', '.join('`' + m + '`' for m in models) or 'n/a (none recorded)'} "
            f"| {tier_cell} "
            f"| {max((r['_attempt'] for r in v.rows), default=0)} "
            f"| {sum(1 for r in v.rows if r['_audit_ok'] is True)} ok / "
            f"{sum(1 for r in v.rows if r['_audit_ok'] is not True)} invalid "
            f"| {trail_cell} "
            f"| {sum(len(r.get('test_files_stripped') or []) for r in v.rows)} "
            f"| {probe_cell} "
            f"| {p2p_cell} "
            f"| {', '.join(p2p_sources) or 'n/a'} |"
        )
    lines += [
        "",
        "An `p2p empty rows` count above 0 is a real property of the suite, not a",
        "harness fault: those instances declare NO PASS_TO_PASS, so their grade",
        "has no regression half and a patch cannot be caught breaking anything.",
        "",
        "Model bounds used for the margin columns:",
        "",
        "| model | bound | type |",
        "|---|---|---|",
    ]
    lines += [
        f"| `{m}` | {b.date} | {b.kind} |" for m, b in sorted(_MODEL_BOUNDS.items())
    ]
    return lines


def _table5_chain(views: list[ArmView]) -> list[str]:
    """Chain-verdict quality — for the arms that HAVE a chain verdict.

    An arm with no chain (`factory_says_green is None` on every row) gets
    `n/a (arm has no chain verdict)` for BOTH rates. The retracted run
    published "claude recall 0/16 = 0%", which was a division artifact on a
    column that does not exist for that arm — and it read as a finding.
    """
    lines = [
        "## Table 5 — chain-verdict quality",
        "",
        "`factory says green` is the chain's OWN verdict (it reached",
        "`reviewer_done`: dev got its tests green and the reviewer approved).",
        "These are **chain-verdict** precision/recall, NOT merge-gate precision —",
        "this harness drives dev+review only; no merge gate runs.",
        "",
        "| arm | quantity | value | 95% CI |",
        "|---|---|---|---|",
    ]
    for v in views:
        has_verdict = any(r.get("factory_says_green") is not None for r in v.valid)
        if not has_verdict:
            reason = "n/a (arm has no chain verdict)"
            lines += [
                f"| {v.arm} | chain-verdict precision | {reason} | {reason} |",
                f"| {v.arm} | chain-verdict recall | {reason} | {reason} |",
            ]
            if _arm_has_chain(v.arm):
                lines.append(
                    f"| {v.arm} | **WARNING** | this arm HAS a chain but recorded no "
                    "verdict on any valid row | — |"
                )
            continue
        said_green = [r for r in v.valid if r.get("factory_says_green")]
        tp = [r for r in said_green if (r.get("grade") or {}).get("oracle_resolved")]
        lines += [
            f"| {v.arm} | chain-verdict precision (oracle passes \\| chain said green) "
            f"| {_fmt_rate(len(tp), len(said_green))} | {_fmt_ci(len(tp), len(said_green))} |",
            f"| {v.arm} | chain-verdict recall (chain said green \\| oracle passes) "
            f"| {_fmt_rate(len(tp), len(v.resolved))} | {_fmt_ci(len(tp), len(v.resolved))} |",
            f"| {v.arm} | reviewer cycles, distribution "
            f"| {_distribution(v.valid, 'reviewer_cycles')} | — |",
            f"| {v.arm} | dev retries, distribution "
            f"| {_distribution(v.valid, 'dev_retries')} | — |",
        ]
    return lines


def _distribution(rows: list[dict[str, Any]], field: str) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        counts[str(r.get(field))] = counts.get(str(r.get(field)), 0) + 1
    if set(counts) <= {"None"}:
        return "n/a (not recorded)"
    return ", ".join(f"{k}x{v}" for k, v in sorted(counts.items()))


# --------------------------------------------------------------------------- #
# archiving
# --------------------------------------------------------------------------- #


def _archive_disclaimer(from_archive: Path | None) -> list[str]:
    """The archive's ``DISCLAIMER.md``, verbatim, or nothing.

    Read at RENDER time, so a run can be marked retracted after the fact
    without any archived row, audit or meta file being touched. A live report
    has no archive yet, hence no disclaimer — and adding one later makes
    ``--check`` fail until the table is re-published, which is the correct
    prompt rather than a silent divergence.
    """
    if from_archive is None:
        return []
    path = from_archive / _DISCLAIMER_NAME
    if not path.is_file():
        return []
    return [*path.read_text(encoding="utf-8").strip().splitlines(), ""]


def _archive_stamp(generated_at: str) -> str:
    """The archive directory name for a ``generated_at``.

    ONE derivation, used both to write the archive and to NAME it in the
    published table — so the table always says which snapshot backs it, in live
    mode and in a re-derivation alike, without either mode having to know the
    other's paths.
    """
    return generated_at.replace(":", "-").replace("+00-00", "Z")


def _archive_report_artifacts(
    rows: list[dict[str, Any]],
    *,
    generated_at: str,
    table_text: str,
    refused: list[dict[str, str]],
    foreign: list[dict[str, str]],
    created: dict[str, str],
) -> Path:
    """Snapshot every consumed artifact into a dated results-archive dir.

    Copies the three per-row evidence files (no state roots, no trajectories —
    archives must stay small enough to commit), the sweep roll-up for every arm
    present, the gold-patch control (``selftest.json`` and its per-instance
    logs), the rendered table, and a meta file — so ``report --from-archive``
    can re-derive the table byte-for-byte with no live runs dir.

    The refused/foreign DISCLOSURES are persisted into the meta. They used to be
    recomputed from ``runs/`` at report time, so from an archive they were
    always EMPTY: a re-derivation silently dropped a 20-line "these rows ran
    under another manifest" section from the committed evidence. A disclosure
    that does not survive re-derivation is not a disclosure.
    """
    archive_dir = RESULTS_ARCHIVE_DIR / _archive_stamp(generated_at)
    arms = sorted({r["_arm"] for r in rows})
    for r in rows:
        run_dir = Path(r["_run_dir"])
        dest = archive_dir / run_dir.parent.name / run_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        for name in _ROW_ARTIFACTS:
            shutil.copy2(run_dir / name, dest / name)
    sweeps: list[str] = []
    for arm in arms:
        src = SWE_DIR / f"sweep-{arm}.json"
        if src.is_file():
            shutil.copy2(src, archive_dir / src.name)
            sweeps.append(src.name)
    extras: list[str] = []
    for name in _ARCHIVED_EXTRAS:
        src = SWE_DIR / name
        if src.is_file():
            shutil.copy2(src, archive_dir / name)
            extras.append(name)
    log_files = 0
    for dirname in _ARCHIVED_LOG_DIRS:
        src_dir = SWE_DIR / dirname
        if src_dir.is_dir():
            shutil.copytree(src_dir, archive_dir / dirname, dirs_exist_ok=True)
            log_files += sum(1 for p in src_dir.rglob("*") if p.is_file())
    # The profile AND the manifest sha are pinned into the meta so
    # ``--from-archive`` re-derives the SAME heading and the SAME row set
    # even after the live manifest moves to another dataset. Because the
    # rows were sha-filtered before archiving, the live manifest's identity
    # IS the included rows' identity.
    try:
        manifest = _manifest()
        profile_name = _profile_of(manifest).name
        manifest_sha = str(manifest.get("manifest_sha256") or "")
    except SystemExit:
        profile_name, manifest_sha = _DEFAULT_PROFILE, ""
    (archive_dir / _REPORT_META_NAME).write_text(
        json.dumps(
            {
                "meta_version": _REPORT_META_VERSION,
                "generated_at": generated_at,
                "source": str(RUNS_DIR),
                "rows": len(rows),
                "arms": arms,
                "profile": profile_name,
                "manifest_sha256": manifest_sha,
                # The disclosures, PERSISTED — see the docstring.
                "refused": refused,
                "foreign": foreign,
                # created_at per instance, so the margin columns survive a
                # manifest move as well.
                "instances": {iid: {"created_at": ts} for iid, ts in sorted(created.items())},
                "sweeps": sweeps,
                "extras": extras,
                "log_files": log_files,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (archive_dir / "results.md").write_text(table_text, encoding="utf-8")
    return archive_dir


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #


def report(
    *, from_archive: Path | None = None, check: bool = False, publish: bool = False
) -> str:
    """Render the pre-registered tables from artifacts; archive the evidence.

    Live mode (default): rows come from ``runs/``, every artifact a row consumed
    is copied into ``results-archive/<generated-at>/``, and ``results.md`` is
    written.

    ``from_archive``: re-derive the table purely from a previous archive dir and
    print it to STDOUT. It writes NOTHING. It used to overwrite the very file it
    was verifying — which is how a hand-written 20-line disclosure section was
    silently deleted from committed evidence by a command whose whole purpose
    was to confirm that evidence.

    ``check``: re-derive from the archive and DIFF against the committed
    ``results.md``, exiting non-zero on any difference. This is the executable
    form of PLAN 1.5's acceptance criterion — "a second report run re-derives
    the committed table byte-for-byte" — which was previously unfalsifiable
    because the re-derivation overwrote its own reference.

    ``publish``: the ONE way to write ``results.md`` from an archive. Explicit,
    opt-in and never implied, so re-deriving stays a read-only act; a shell
    redirect is not an acceptable substitute because ``print`` adds a trailing
    newline and the result then fails its own ``--check``.
    """
    if check and publish:
        raise SystemExit(
            "--check and --publish are opposites: one asserts the committed "
            "table is unchanged, the other replaces it. Pick one."
        )
    if (check or publish) and from_archive is None:
        from_archive = _latest_archive()
    base_dir = from_archive if from_archive is not None else RUNS_DIR
    generated_at = datetime.now(UTC).isoformat()
    archive_profile: str | None = None
    meta: dict[str, Any] = {}
    if from_archive is not None:
        meta_path = from_archive / _REPORT_META_NAME
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            generated_at = str(meta["generated_at"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise SystemExit(
                f"archive at {from_archive} has no readable {_REPORT_META_NAME} "
                f"({exc}) — not a report archive"
            ) from exc
        # Pre-port archives carry no profile; they are all Pro by definition.
        archive_profile = str(meta.get("profile") or _DEFAULT_PROFILE)

    # The report is pinned to ONE manifest: live mode uses the live pinned
    # manifest's sha; --from-archive uses the sha the archive recorded when
    # it was made (a pre-port archive recorded none — its rows were curated
    # by the snapshot itself, so no filter applies).
    if from_archive is not None:
        expected_sha = str(meta.get("manifest_sha256") or "") or None
    else:
        expected_sha = str(_manifest().get("manifest_sha256") or "") or None

    rows, refused, foreign = _report_rows(base_dir, expected_sha)
    if from_archive is not None:
        # The archive's OWN record of what it excluded, re-emitted. Rows
        # refused at archive time were never copied in, so recomputing here
        # yields nothing — the disclosure has to be read back, not recomputed.
        recorded_refused = meta.get("refused")
        recorded_foreign = meta.get("foreign")
        disclosure_recorded = isinstance(recorded_refused, list) and isinstance(
            recorded_foreign, list
        )
        if isinstance(recorded_refused, list):
            refused = [dict(x) for x in recorded_refused] + refused
        if isinstance(recorded_foreign, list):
            foreign = [dict(x) for x in recorded_foreign] + foreign
    else:
        disclosure_recorded = True

    if not rows:
        detail = "; ".join(f"{x['row']}: {x['why']}" for x in refused + foreign)
        raise SystemExit(
            f"no reportable results under {base_dir} for manifest "
            f"{expected_sha or '(unpinned)'}"
            + (
                f" — every row refused (fail-closed) or foreign: {detail}"
                if detail
                else ""
            )
        )

    # The heading names the profile the rows were produced under: the
    # archive's pinned profile when re-deriving, else the live manifest's.
    # This keeps ``--from-archive`` byte-for-byte even after the live
    # manifest moves to another dataset.
    if archive_profile is not None:
        profile = PROFILES.get(archive_profile, PROFILES[_DEFAULT_PROFILE])
    else:
        try:
            profile = _profile_of(_manifest())
        except SystemExit:
            profile = PROFILES[_DEFAULT_PROFILE]
    if profile.name == "swebench-pro":
        broken_note = (
            "`task_broken` is reported SEPARATELY from `wrong_patch`. OpenAI's "
            "2026-07-08 audit found ~30% of this suite's public tasks broken, so "
            "summing the two would read a broken harness as factory failure."
        )
    else:
        broken_note = (
            "`task_broken` is reported SEPARATELY from `wrong_patch`. This "
            "dataset execution-validates every instance upstream, so a "
            "non-trivial `task_broken` rate means THIS harness's plumbing "
            "broke, not the tasks."
        )

    arms = sorted({r["_arm"] for r in rows})
    views = [_arm_view(rows, a) for a in arms]
    created = _instance_created_at(rows, meta)
    bound_models = sorted(
        {
            _norm_model(m)
            for r in rows
            for m in ([str(r["model"])] if r.get("model") else [])
            if _model_bound(m) is not None
        }
        | {
            _norm_model(str(spec.model))
            for a in arms
            if (spec := _ARMS.get(_split_run_key(a)[0])) is not None and spec.model
            if _model_bound(str(spec.model)) is not None
        }
    )

    lines = [
        f"# {profile.title} — externally graded",
        "",
        f"Generated {generated_at}.",
        "",
        "Every row here is backed by the evidence snapshot in",
        f"`bench/swebench/results-archive/{_archive_stamp(generated_at)}/`, and",
        "`report --check` asserts that this table is still byte-for-byte",
        "re-derivable from it.",
        "",
        *_archive_disclaimer(from_archive),
        "Tables 1-5 are the shape fixed in `bench/swebench/PRE-REGISTRATION-1.6.md`",
        "before the run. Every cell is filled from an archived artifact or printed",
        "as `n/a` with a reason; no cell is filled by hand.",
        "",
        "**An arm is a (harness, model set) pair.** Neither half may be omitted",
        "when a number from this run is quoted: a score is never a property of the",
        "model alone and never of the harness alone.",
        "",
        broken_note,
        "",
    ]
    lines += _table1_headline(views)
    lines += ["", *_table2_matrix(rows, arms, created, bound_models)]
    lines += ["", *_table3_comparisons(views, rows, created)]
    lines += ["", *_table4_provenance(views)]
    lines += ["", *_table5_chain(views)]

    # Per-arm gate accounting, and the loud exclusion line.
    for v in views:
        broken = len(v.ungradable["task_broken"])
        parse_failed = v.ungradable["grade_parse_failed"]
        headline = (
            f"- resolve rate: **{_fmt_rate(len(v.resolved), len(v.valid))} "
            f"audited-valid**, 95% CI {_fmt_ci(len(v.resolved), len(v.valid))}"
        )
        lines += [
            "",
            f"## {v.arm} — gate accounting",
            "",
            f"- harness: {_arm_label(v.arm)}",
            # The `grade_parse_failed` clause appears only when such a row
            # exists, so an archive without one still re-derives byte-for-byte.
            f"- graded instances: **{len(v.graded)}** "
            f"({broken} excluded as `task_broken`"
            + (
                f", {len(parse_failed)} as `grade_parse_failed`"
                if parse_failed
                else ""
            )
            + f", leaving {len(v.gradable)})",
            f"- audit gate: **{len(v.valid)} audited-valid** of {len(v.gradable)} "
            f"gradable (audit failed: "
            f"{sum(1 for r in v.gradable if r['_audit_ok'] is False)}, "
            f"not audited: {sum(1 for r in v.gradable if r['_audit_ok'] is None)}, "
            f"run failed: {sum(1 for r in v.gradable if r['_run_failed'])})",
            f"- budget-exhausted, COUNTED as attempts: "
            f"{sum(1 for r in v.valid if r['_budget_exhausted'])} "
            "(one rule, every arm: a turn-cap or wall-cap hit is a completed, "
            "counted, flagged attempt)",
            headline,
        ]
        if parse_failed:
            # LOUD, and above the ordinary exclusions: this one says THIS
            # HARNESS could not read pytest's per-node report, so the row is a
            # verdict on the plumbing and not on the arm.
            lines.append(
                f"- **{len(parse_failed)} row(s) EXCLUDED as `grade_parse_failed` "
                "— a HARNESS defect, not an arm failure**: "
                + "; ".join(
                    f"{str(r.get('instance_id'))[:46]}: "
                    + "; ".join(
                        str(x)
                        for x in ((r.get("grade") or {}).get("node_parse_failures") or [])
                    )[:200]
                    for r in parse_failed
                )
            )
        if v.excluded:
            lines.append(
                f"- **{len(v.excluded)} row(s) EXCLUDED from the denominator, "
                "passes AND failures named**: "
                + "; ".join(_exclusion_reason(r) for r in v.excluded)
            )

    discarded = [r for r in rows if r["_attempt"] > 1]
    lines += [
        "",
        "## Discarded runs (attempt > 1)",
        "",
    ]
    if discarded:
        lines += [
            "Each row below is a RE-RUN of a cell that had already been attempted.",
            "The retracted run published 4 second attempts after the integrity gate",
            "invalidated the first, disclosed nowhere; under the no-re-rolls rule any",
            "row here is a protocol violation, not a data point.",
            "",
        ]
        lines += [
            f"- `{str(r.get('instance_id'))}/{r['_arm']}` — attempt {r['_attempt']}"
            for r in sorted(discarded, key=lambda r: (str(r.get("instance_id")), r["_arm"]))
        ]
    else:
        lines.append("None — every published row is its cell's first attempt.")

    lines += [
        "",
        "## Per-row ledger",
        "",
        "The row-level evidence every table above is derived from. `p2p` is the",
        "instance's PASS_TO_PASS count: a **0** means the grade has no regression",
        "half at all, so nothing there can catch a patch breaking the suite.",
        "",
    ]
    lines += [
        "| instance | arm | model(s) | attempt | budget | factory says | oracle "
        "| audit | outcome | p2p | fresh in | cache read | tokens out | wall s | $ |",
        "|---|---|---|---:|:-:|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(rows, key=lambda r: (str(r.get("instance_id")), r["_arm"])):
        g = r.get("grade") or {}
        oracle = g.get("oracle_resolved")
        audit_cell = "ok" if r["_audit_ok"] else ("—" if r["_audit_ok"] is None else "FAIL")
        p2p = g.get("pass_to_pass_count")
        p2p_cell = (
            "**0 (no regression half)**" if p2p == 0 else (str(p2p) if p2p is not None else "?")
        )
        lines.append(
            f"| {str(r.get('instance_id'))[:46]} | {r['_arm']} "
            f"| {', '.join(_row_models(r)) or '?'} "
            f"| {r['_attempt']} "
            f"| {'!' if r['_budget_exhausted'] else '—'} "
            f"| {'green' if r.get('factory_says_green') else ('not green' if r.get('factory_says_green') is not None else 'n/a')} "
            f"| {'PASS' if oracle else ('?' if oracle is None else 'FAIL')} "
            f"| {audit_cell} "
            f"| {g.get('outcome', '—')} "
            f"| {p2p_cell} "
            f"| {r['_fresh_in']:,} | {r['_cache_read']:,} "
            f"| {_fmt_int(r.get('tokens_out'))} "
            f"| {r.get('wall_clock_s', '—')} "
            f"| {float(r.get('cost_usd') or 0.0):.2f} |"
        )

    if not disclosure_recorded:
        lines += [
            "",
            "## Excluded-row disclosure",
            "",
            f"n/a (archive predates `{_REPORT_META_NAME}` version "
            f"{_REPORT_META_VERSION}, which is the first to PERSIST the refused",
            "and foreign row lists). Rows refused or excluded when this archive was",
            "made cannot be recovered from it — that gap is exactly why the lists",
            "are persisted now.",
        ]
    if refused:
        lines += [
            "",
            "## Refused rows (fail-closed: backing artifacts missing)",
            "",
            "These result dirs exist but their evidence is incomplete, so they are",
            "NOT table rows and count in NO rate above. A number without its",
            "artifacts is the retraction class this report exists to prevent.",
            "",
        ]
        lines += [f"- `{x['row']}` — {x['why']}" for x in refused]

    if foreign:
        lines += [
            "",
            "## Excluded rows (other manifest/profile)",
            "",
            f"These runs did not run under the pinned manifest `{expected_sha}`,",
            "so they are NOT table rows and count in NO rate above — merging",
            "runs from two manifests (e.g. a previous dataset's leftovers in",
            "`runs/`) would blend incomparable numbers into one headline.",
            "",
        ]
        lines += [f"- `{x['row']}` — {x['why']}" for x in foreign]

    n = len({r.get("instance_id") for r in rows})
    if n < 30:
        lines += [
            "",
            f"> **n={n} — preliminary.** Do not draw conclusions beyond "
            "\"the harness runs\". The MDE at this size is far wider than any "
            "difference worth acting on; k>=3 is required before any delta from "
            "this suite is quoted as a result.",
        ]
    lines += [
        "",
        "> Cost columns are NOT comparable across arms and must never be summed: "
        "the Azure arms' dollars are a price-table estimate over measured tokens, "
        "the Claude arms' are the CLI's own report against a subscription.",
    ]

    text = "\n".join(lines) + "\n"

    if check:
        return _check_against_committed(text, base_dir)

    # Archive BEFORE publishing results.md: a table whose evidence snapshot
    # failed must not exist. The reverse order would recreate the exact gap
    # this exists to close (published number, no backing artifacts).
    if from_archive is None:
        archive_dir = _archive_report_artifacts(
            rows,
            generated_at=generated_at,
            table_text=text,
            refused=refused,
            foreign=foreign,
            created=created,
        )
        print(f"archived evidence -> {archive_dir}")
        SWE_DIR.mkdir(parents=True, exist_ok=True)
        out = SWE_DIR / "results.md"
        out.write_text(text, encoding="utf-8")
        print(out)
    elif publish:
        SWE_DIR.mkdir(parents=True, exist_ok=True)
        out = SWE_DIR / "results.md"
        out.write_text(text, encoding="utf-8")
        print(f"published {out} from {base_dir} (now `report --check`-clean)")
    else:
        # STDOUT ONLY. A verification pass must not mutate the thing it
        # verifies; `--publish` is the explicit way to write it.
        print(
            f"re-derived from {base_dir} — printing to stdout, results.md untouched "
            "(`report --check` asserts byte-for-byte equality; `--publish` writes it)"
        )
    print(text)
    return text


def _instance_created_at(
    rows: list[dict[str, Any]], meta: dict[str, Any]
) -> dict[str, str]:
    """``created_at`` per instance, for the contamination margins.

    Prefers the ARCHIVE's own persisted copy, so the margins survive the live
    manifest moving to another dataset; falls back to the live manifest, which
    is what makes pre-1.6 archives still render margins today.
    """
    out: dict[str, str] = {}
    recorded = meta.get("instances")
    if isinstance(recorded, dict):
        for iid, info in recorded.items():
            if isinstance(info, dict) and info.get("created_at"):
                out[str(iid)] = str(info["created_at"])
    wanted = {str(r.get("instance_id")) for r in rows}
    if not wanted - set(out):
        return {k: v for k, v in out.items() if k in wanted}
    try:
        manifest = _manifest()
    except SystemExit:
        return {k: v for k, v in out.items() if k in wanted}
    for inst in manifest.get("instances") or []:
        iid = str(inst.get("instance_id"))
        if iid in wanted and iid not in out and inst.get("created_at"):
            out[iid] = str(inst["created_at"])
    return {k: v for k, v in out.items() if k in wanted}


def _latest_archive() -> Path:
    """The newest results-archive dir, by name (the names are timestamps)."""
    if not RESULTS_ARCHIVE_DIR.is_dir():
        raise SystemExit(
            f"no {RESULTS_ARCHIVE_DIR} to check against — run `report` first"
        )
    dirs = sorted(p for p in RESULTS_ARCHIVE_DIR.iterdir() if p.is_dir())
    if not dirs:
        raise SystemExit(f"{RESULTS_ARCHIVE_DIR} holds no archive dirs")
    return dirs[-1]


def _check_against_committed(text: str, base_dir: Path) -> str:
    """Diff a re-derivation against the committed ``results.md``. Exit 1 on any
    difference.

    Fail-closed in both directions: a missing ``results.md`` is a failure (there
    is nothing to have reproduced), and so is any byte of drift. The diff itself
    is printed, because "they differ" is not actionable.
    """
    out = SWE_DIR / "results.md"
    if not out.is_file():
        raise SystemExit(
            f"--check has nothing to compare against: {out} does not exist. "
            "The committed table IS the reference."
        )
    committed = out.read_text(encoding="utf-8")
    if committed == text:
        print(
            f"CHECK OK — {out} is byte-for-byte re-derivable from {base_dir} "
            f"({len(text)} bytes, {len(text.splitlines())} lines)."
        )
        return text
    diff = "".join(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile=f"committed {out}",
            tofile=f"re-derived from {base_dir}",
        )
    )
    print(diff)
    raise SystemExit(
        f"CHECK FAILED — {out} is NOT byte-for-byte re-derivable from {base_dir}. "
        "Either the archive is not the one that produced it, or the report code "
        "changed without the published table being regenerated. A published "
        "number whose own evidence no longer reproduces it is retracted, not "
        "explained."
    )

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
# The claude default is the documented $3 first-run stand-in; NOTE its spend is
# ANTHROPIC-side (the CLI's own report), so the guard conservatively counts it
# against the same factory_settings.yaml caps even though it never touches the
# Azure ledger.
# Measured bare rows average $0.16 and measured factory rows $1.44 per
# instance, so $3.00 is conservative in the direction the guard needs.
#
# Both tables are DERIVED VIEWS of the one arm registry, and both are
# fail-loud: the old plain dicts were read with ``.get(arm, 3.00)`` /
# ``.get(arm, 0.05)``, so a new or misspelled arm silently inherited a cost
# guard tuned for a different arm — a projection that refuses (or fails to
# refuse) for reasons the operator cannot see.


class _FailLoudArmMap(dict[str, float]):
    """A per-arm table with no silent default. ``in`` still works."""

    def __init__(self, values: dict[str, float], what: str) -> None:
        super().__init__(values)
        self._what = what

    def __missing__(self, key: str) -> float:
        raise SystemExit(
            f"no {self._what} registered for arm {key!r}. Registered arms: "
            f"{', '.join(sorted(self))}. Add the arm to _ARMS — a guard that "
            "guesses its own limits is not a guard."
        )


_DEFAULT_COST_USD = _FailLoudArmMap(
    {name: spec.default_cost_usd for name, spec in _ARMS.items()},
    "default per-instance cost",
)
_DEFAULT_HOURS = _FailLoudArmMap(  # 3 min — fast end of measured
    {name: spec.default_hours for name, spec in _ARMS.items()},
    "default per-instance duration",
)

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


def estimate_instance_cost(
    arm: str,
    runs_dir: Path | None = None,
    *,
    manifest_sha: str | None = None,
) -> tuple[float, float, str]:
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

    Samples are restricted to ONE manifest (``manifest_sha``, defaulting to the
    live pinned one). Without that filter the guard pooled every leftover run
    in ``runs/`` regardless of dataset: SWE-bench-Pro instances are far bigger
    than SWE-rebench ones, and their MINIMUM wall clock became the rebench
    sweep's projected per-instance duration — which is the denominator of the
    hourly burn rate. Mixing datasets in a projection is the same error class
    as mixing them in a headline; ``report`` already refuses it, and so does
    this. A row that records no sha is unverifiable provenance and is never a
    sample.

    Uses the MAXIMUM cost and MINIMUM duration: both push the projected burn
    rate up, which is the fail-safe direction for a guard whose job is to
    refuse.
    """
    base = RUNS_DIR if runs_dir is None else runs_dir
    if manifest_sha is None:
        try:
            manifest_sha = str(_manifest().get("manifest_sha256") or "")
        except SystemExit:
            manifest_sha = ""
    key = run_key(arm)
    costs: list[float] = []
    hours: list[float] = []
    foreign = 0
    for f in sorted(base.glob(f"*/{key}/result.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(r, dict) or r.get("error"):
            continue  # a failed run's partial spend is not a cost sample
        if manifest_sha and str(r.get("manifest_sha256") or "") != manifest_sha:
            foreign += 1
            continue
        cost = float(r.get("cost_usd") or 0.0)
        wall = float(r.get("wall_clock_s") or 0.0)
        if cost > 0:
            costs.append(cost)
        if wall > 0:
            hours.append(wall / 3600.0)
    default_usd = _DEFAULT_COST_USD[key]
    skipped = f", {foreign} other-manifest row(s) ignored" if foreign else ""
    if costs:
        usd = max(costs)
        floored = len(costs) < 2 and usd < default_usd
        if floored:
            usd = default_usd
        return (
            usd,
            max(min(hours, default=0.05), 0.01),
            f"measured over {len(costs)} clean prior {key} run(s) on manifest "
            f"{manifest_sha or '(unpinned)'}"
            + (f", floored at the ${default_usd:,.2f} default" if floored else "")
            + skipped,
        )
    return (
        default_usd,
        _DEFAULT_HOURS[key],
        "default estimate (no clean prior runs on this manifest to measure)"
        + skipped,
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
    model: str | None = None,
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
    # (instance, arm, MODEL): two runs of one arm on two models are two rows in
    # two directories, never one row that silently replaced the other.
    key = run_key(arm, model)
    model_argv = ["--model", model] if model else []
    run_dir = _run_dir(instance_id, key)
    record: dict[str, Any] = {
        "instance_id": instance_id,
        "arm": key,
        "model": resolve_arm_model(arm, model),
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
                *model_argv,
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
        # ONE classifier, shared with `report` — see ``classify_run``. The sweep
        # used to set this status from the child's exit code alone while the
        # report set its own from ``result.json["error"]``, and the two
        # DISAGREED on the retracted run: sweep-claude.json said 17 resolved,
        # results.md said 16/18. The exit code is still consulted (it catches a
        # child that died without writing anything) but it no longer overrides
        # the artifact.
        child_result = _read_result(run_dir)
        status, detail = classify_run(child_result, rc=rc)
        if status != _RUN_OK:
            record["status"] = status
            # With an artifact, the artifact's own reason wins. WITHOUT one, the
            # child's last log line is the only evidence there is (a timeout, a
            # traceback) and must not be replaced by a generic message.
            record["error"] = (
                detail if child_result else (tail or detail)
            ) or f"run exited {rc}"

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
                    *model_argv,
                    "--timeout-s",
                    str(grade_timeout_s),
                ],
                timeout_s=grade_timeout_s + 1800,
                log_path=run_dir / "sweep-grade.log",
            )
            record["grade_rc"] = grc
            # ``budget_exhausted`` counts as "nothing has gone wrong YET": a
            # cap hit is a completed attempt, so a grade failure on top of it
            # must still be reported rather than hidden behind the flag. The
            # flag itself survives in ``_finish_record``.
            if grc != 0 and record["status"] in (_RUN_OK, _RUN_BUDGET_EXHAUSTED):
                record["status"] = "grade_failed"
                record["error"] = gtail or f"grade exited {grc}"
        elif record["status"] in (_RUN_OK, _RUN_BUDGET_EXHAUSTED):
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
                *model_argv,
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
    result = _read_result(run_dir) or {}
    g = result.get("grade") or {}
    record.update(
        {
            "final_state": result.get("final_state") or "—",
            "tokens_in": int(result.get("tokens_in") or 0),
            "cache_read": int(result.get("cached_input_tokens") or 0),
            "tokens_out": int(result.get("tokens_out") or 0),
            "cost_usd": float(result.get("cost_usd") or 0.0),
            "factory_says_green": result.get("factory_says_green"),
            "oracle_resolved": g.get("oracle_resolved"),
            "outcome": g.get("outcome") or "—",
            # Same derivation the report uses, from the same artifact.
            "attempt": int(result.get("attempt") or 1),
            # Same shared classifier the report uses, so the sweep roll-up and
            # the published table can never disagree about this row again.
            "budget_exhausted": classify_run(result)[0] == _RUN_BUDGET_EXHAUSTED,
            "models_used": result.get("models_used") or [],
            "sweep_wall_s": round(time.monotonic() - started, 1),
        }
    )
    return record


def _progress_line(n: int, total: int, r: dict[str, Any]) -> str:
    oracle = r.get("oracle_resolved")
    mark = "PASS" if oracle else ("?" if oracle is None else "FAIL")
    audit_ok = r.get("audit_ok")
    audit_mark = "ok" if audit_ok else ("—" if audit_ok is None else "FAIL")
    status = "" if r["status"] == _RUN_OK else f"  !{r['status']}: {str(r.get('error'))[:80]}"
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
    model: str | None = None,
) -> None:
    manifest = _manifest()
    # Resolve (and refuse) the arm/model pair BEFORE any spend, and key every
    # artifact this sweep writes — run dirs, records, sweep-<key>.json — by it.
    key = run_key(arm, model)
    resolved_model = resolve_arm_model(arm, model)
    chosen = select_instances(
        [str(i["instance_id"]) for i in manifest["instances"]],
        requested=instances,
        only_working=only_working,
        working=selftest_working_instances() if only_working else None,
    )
    if not chosen:
        raise SystemExit("nothing to sweep: the pinned manifest is empty")
    # The oracle store must be able to grade EVERY chosen instance before a
    # single child spawns: the first live sweep burned $24.78 and produced
    # zero audited-valid rows because grade — the last step — was the first
    # place the clobbered store was consulted. Applies to --dry-run too: a
    # preview of a sweep that would refuse should say so.
    chosen_set = set(chosen)
    _assert_oracle_store_complete(
        [i for i in manifest["instances"] if i["instance_id"] in chosen_set]
    )
    workers = max(1, min(workers, len(chosen)))

    hourly_cap, daily_cap = load_spend_caps()
    usd, hours, source = estimate_instance_cost(
        key, manifest_sha=str(manifest.get("manifest_sha256") or "")
    )
    total, peak, refusal = spend_guard(
        n_instances=len(chosen),
        workers=workers,
        usd_per_instance=usd,
        hours_per_instance=hours,
        hourly_cap=hourly_cap,
        daily_cap=daily_cap,
    )
    _emit(
        f"sweep: arm={key} model={resolved_model or '(from routes.yaml)'} "
        f"instances={len(chosen)} workers={workers}\n"
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
        model_flag = f" --model {model}" if model else ""
        for i, iid in enumerate(chosen, 1):
            _emit(
                f"  [{i:>3}] run --instance {iid} --arm {arm}{model_flag} "
                f"--max-steps {max_steps}"
            )
            _emit(f"        then grade --instance {iid} --arm {arm}{model_flag}")
            _emit(f"        then audit --instance {iid} --arm {arm}{model_flag}")
            _emit(f"        -> bench/swebench/runs/{iid}/{key}/")
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
                model=model,
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
                    rec = _blank_record(iid, key, f"{type(exc).__name__}: {exc}")
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
            records.append(_blank_record(iid, key, reason, status="aborted"))
            continue
        try:
            records.append(fut.result(timeout=0))
        except BaseException as exc:  # noqa: BLE001 - KeyboardInterrupt included
            records.append(
                _blank_record(iid, key, f"{type(exc).__name__}: {exc}", status="aborted")
            )

    records.sort(key=lambda r: str(r["instance_id"]))
    summary = _sweep_summary(
        records,
        arm=key,
        model=resolved_model,
        workers=workers,
        wall_s=time.monotonic() - started,
        stopped_reason=stopped_reason,
    )
    # Keyed by the RUN KEY, not the bare arm: two claude sweeps on two models
    # would otherwise write one file and the second would erase the first.
    out = SWE_DIR / f"sweep-{key}.json"
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
        "cache_read": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "factory_says_green": None,
        "oracle_resolved": None,
        "outcome": "—",
        "attempt": 0,  # never started, so it is not an attempt at anything
        "budget_exhausted": False,
        "models_used": [],
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
    model: str | None = None,
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
        and _ungradable_kind(str(r.get("outcome") or "")) is None
    ]
    # DELIBERATE: the headline ``resolved`` counts only rows that are clean
    # end-to-end — run completed (or ran out of budget, which is a COMPLETED
    # attempt under the one shared rule) AND audit ok. An oracle pass produced
    # by a run that genuinely failed, or by a run whose audit found the trail
    # invalid, is real information but not a trustworthy result: it stays
    # VISIBLE in its own flagged counter instead of being silently conflated
    # into the number a comparison would be built on.
    #
    # ``budget_exhausted`` joining ``ok`` here is the fix for the retracted
    # run's silently-improved denominator: a Claude row that hit its turn cap
    # AND passed the oracle was dropped from both numerator and denominator.
    def _counted(r: dict[str, Any]) -> bool:
        return r.get("status") in (_RUN_OK, _RUN_BUDGET_EXHAUSTED)

    resolved_clean = sum(
        1 for r in gradable if r.get("oracle_resolved") and _counted(r) and r.get("audit_ok") is True
    )
    resolved_run_failed = sum(
        1 for r in gradable if r.get("oracle_resolved") and not _counted(r)
    )
    resolved_audit_failed = sum(
        1
        for r in gradable
        if r.get("oracle_resolved") and _counted(r) and r.get("audit_ok") is not True
    )
    return {
        "arm": arm,
        # Both halves of the (harness, model) pair, in the artifact, so a
        # sweep-<arm>.json torn out of context still says what produced it.
        "model": model,
        "harness": arm_spec(arm).harness,
        "workers": workers,
        "finished_at": datetime.now(UTC).isoformat(),
        "wall_clock_s": round(wall_s, 1),
        "stopped_reason": stopped_reason,
        "instances": len(records),
        "ok": sum(1 for r in records if _counted(r)),
        "failed": sum(1 for r in records if not _counted(r)),
        "statuses": statuses,
        "outcomes": outcomes,
        "audited_valid": sum(1 for r in records if r.get("audit_ok") is True),
        "audit_failed": sum(1 for r in records if r.get("audit_ok") is False),
        "not_audited": sum(1 for r in records if r.get("audit_ok") is None),
        "resolved": resolved_clean,
        "resolved_but_run_failed": resolved_run_failed,
        "resolved_but_audit_failed": resolved_audit_failed,
        # Loud in the artifact, not only in the terminal: a non-zero count here
        # means THIS HARNESS could not read pytest's report on that many rows,
        # and any rate computed from the sweep is over a smaller denominator.
        "grade_parse_failed": sum(
            1 for r in records if str(r.get("outcome") or "") == "grade_parse_failed"
        ),
        "budget_exhausted": sum(1 for r in records if r.get("budget_exhausted")),
        "retried_rows": sum(1 for r in records if int(r.get("attempt") or 1) > 1),
        "gradable": len(gradable),
        "tokens_in": sum(int(r.get("tokens_in") or 0) for r in records),
        "cache_read": sum(int(r.get("cache_read") or 0) for r in records),
        "fresh_in": sum(
            max(int(r.get("tokens_in") or 0) - int(r.get("cache_read") or 0), 0)
            for r in records
        ),
        "tokens_out": sum(int(r.get("tokens_out") or 0) for r in records),
        "cost_usd": round(sum(float(r.get("cost_usd") or 0.0) for r in records), 4),
        "cost_source": arm_spec(arm).cost_source,
        "results": records,
    }


def _render_summary(s: dict[str, Any]) -> str:
    flagged = []
    if s.get("resolved_but_run_failed"):
        flagged.append(f"+{s['resolved_but_run_failed']} resolved but run FAILED")
    if s.get("resolved_but_audit_failed"):
        flagged.append(f"+{s['resolved_but_audit_failed']} resolved but audit FAILED")
    if s.get("grade_parse_failed"):
        flagged.append(
            f"{s['grade_parse_failed']} GRADE-PARSE FAILED (harness defect, "
            "excluded from the denominator — investigate before publishing)"
        )
    lines = [
        "-" * 100,
        f"sweep done: arm={s['arm']} model={s.get('model') or '(from routes.yaml)'} "
        f"{s['instances']} instance(s) in {s['wall_clock_s']}s "
        f"on {s['workers']} worker(s) — {s['ok']} ok, {s['failed']} failed",
        # fresh vs cache-read, never one blended "tokens in": cache share ranged
        # 0%-97% across the arms of the retracted run, which made its published
        # token ratio wrong by 4.5x.
        f"  tokens: fresh_in={s.get('fresh_in', s['tokens_in']):,} "
        f"cache_read={s.get('cache_read', 0):,} out={s['tokens_out']:,}  "
        f"cost=${s['cost_usd']:,.2f} ({s.get('cost_source', _COST_PRICE_TABLE)})",
        f"  oracle: {s['resolved']}/{s['gradable']} resolved clean"
        + (
            " (task_broken / grade_parse_failed excluded)"
            if s["gradable"] < s["instances"]
            else ""
        )
        + (" — flagged, NOT counted: " + ", ".join(flagged) if flagged else ""),
        f"  audit: {s['audited_valid']} valid, {s['audit_failed']} failed, "
        f"{s['not_audited']} not audited",
        f"  budget-exhausted (counted as attempts): {s.get('budget_exhausted', 0)}; "
        f"rows on attempt>1: {s.get('retried_rows', 0)}",
        "  outcomes: "
        + ", ".join(f"{k}={v}" for k, v in sorted(s["outcomes"].items()))
        + "",
    ]
    if s.get("stopped_reason"):
        lines.insert(1, f"  STOPPED EARLY — {s['stopped_reason']}")
    failures = [
        r
        for r in s["results"]
        if r.get("status") not in (_RUN_OK, _RUN_BUDGET_EXHAUSTED)
    ]
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


def _add_model_arg(p: argparse.ArgumentParser) -> None:
    """``--model`` for every command that addresses a run directory.

    ``grade`` and ``audit`` take it too, not just ``run``: the run directory is
    keyed by (instance, arm, MODEL), so a grade that could not name the model
    could not find the right prediction — it would silently grade whichever run
    happened to own the plain arm directory.
    """
    p.add_argument(
        "--model",
        default=None,
        help="model id for a model-selectable arm (the claude arms). Defaults "
             f"to {_CLAUDE_MODEL}. An off-default id keys its own run "
             f"directory (`<arm>{_ARM_MODEL_SEP}<model>`) so two runs of one "
             "arm on two models cannot overwrite each other. Rejected for the "
             "arms whose weights come from routes.yaml.",
    )


def main() -> None:
    _load_env()

    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="pin a manifest (do this BEFORE any run)")
    p.add_argument(
        "--dataset",
        required=True,
        choices=sorted(PROFILES),
        help="dataset profile; persisted in the manifest, which every later "
             "command reads it back from — a run never mixes profiles. "
             "REQUIRED, no default: defaulting silently to the FROZEN "
             "swebench-pro profile pinned the wrong dataset. swe-rebench is "
             "primary.",
    )
    p.add_argument("--language", default="python")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--seed", type=int, required=True, help="published RNG seed")
    p.add_argument(
        "--after",
        default=None,
        help="keep only instances created strictly after this date "
             "(YYYY-MM-DD). Defaults to 2026-01-01 for swe-rebench — a "
             "conservative stand-in for DeepSeek-V4 Pro's UNDOCUMENTED "
             "training cutoff.",
    )

    p = sub.add_parser("run", help="drive an arm over one instance")
    p.add_argument("--instance", required=True)
    p.add_argument(
        "--arm",
        default="factory",
        choices=list(_ARM_NAMES),
        help="'bare' is the matched minimal scaffold on the SAME Azure models "
             "(PLAN.md 1.4). A factory number without it measures the model. "
             "'claude' is the local Claude Code CLI, headless and hermetic — "
             "its spend bills the operator's Anthropic subscription, not the "
             "Azure ledger; 'claude-5'/'claude-4.8' are that same CLI pinned to "
             "the two pre-registered models (the older cutoff is the "
             "contamination probe). 'openhands' is ONE OpenHands agent on the "
             "factory's own dev deployment with no chain around it — it isolates "
             "the chain, which is what the product claim asserts.",
    )
    _add_model_arg(p)
    p.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help=f"explicit step/turn budget; default is per-arm — "
             f"{_FACTORY_STEP_DEFAULT} orchestrator ticks for factory, "
             f"{_BARE_STEP_CAP} shell turns for bare, "
             f"{_CLAUDE_TURN_CAP} claude CLI turns, "
             f"{_OPENHANDS_ITERATION_CAP} openhands agent iterations",
    )
    p.add_argument("--timeout-s", type=int, default=5400)
    p.add_argument(
        "--probe-plumbing",
        action="store_true",
        help="bare/openhands/claude-* (not factory): run the WHOLE pipeline (clone, install "
             "replay, collect precheck, prompt assembly, command parse, tool "
             "loop, diff capture, split_diff, assert_no_test_edits, ledger "
             "read-back, result.json, summary) with the model REPLACED by a "
             "fixed script. Costs $0. The row it writes carries a recorded "
             "error so it can never be reported as a measurement.",
    )

    p = sub.add_parser(
        "run-all",
        help="parallel sweep: run + grade many instances across a worker pool",
    )
    p.add_argument("--arm", default="factory", choices=list(_ARM_NAMES))
    _add_model_arg(p)
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
    p.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help=f"explicit step/turn budget; default is per-arm — "
             f"{_FACTORY_STEP_DEFAULT} orchestrator ticks for factory, "
             f"{_BARE_STEP_CAP} shell turns for bare, "
             f"{_CLAUDE_TURN_CAP} claude CLI turns, "
             f"{_OPENHANDS_ITERATION_CAP} openhands agent iterations",
    )
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
    p.add_argument("--arm", default="factory", choices=list(_ARM_NAMES))
    _add_model_arg(p)
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
    p.add_argument("--arm", default="factory", choices=list(_ARM_NAMES))
    _add_model_arg(p)
    p.add_argument(
        "--show-responses",
        action="store_true",
        help="also print the reviewer's response text and the last few dev "
             "assistant messages from the captured trajectory",
    )

    p = sub.add_parser("report")
    p.add_argument(
        "--from-archive",
        default=None,
        help="re-derive the table purely from a results-archive dir and print it "
             "to STDOUT. Writes NOTHING — this mode used to overwrite the very "
             "results.md it was verifying, and silently deleted a disclosure "
             "section from committed evidence.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="re-derive from an archive (newest by default) and DIFF against the "
             "committed results.md; exit non-zero on any difference. The "
             "executable form of 'a second report run re-derives the committed "
             "table byte-for-byte'.",
    )
    p.add_argument(
        "--publish",
        action="store_true",
        help="write results.md FROM an archive. The only way to do that; plain "
             "--from-archive is read-only so verifying never mutates what it "
             "verifies.",
    )

    args = ap.parse_args()
    if args.cmd == "fetch":
        fetch(
            dataset=args.dataset,
            language=args.language,
            limit=args.limit,
            seed=args.seed,
            after=args.after,
        )
    elif args.cmd == "run":
        steps = _resolve_max_steps(args.arm, args.max_steps)
        # Validated (and refused for a non-selectable arm) BEFORE anything is
        # cloned or spent.
        key = run_key(args.arm, args.model)
        base = arm_spec(args.arm).base
        if args.probe_plumbing:
            if base not in ("bare", "openhands", "claude"):
                raise SystemExit(
                    "--probe-plumbing is implemented for --arm bare, openhands "
                    "and the claude arms (the factory arm's dry-run surface is "
                    "`factory pm-sync --dry-run`)."
                )
            if base == "claude":
                run_claude(
                    args.instance,
                    max_steps=steps,
                    timeout_s=args.timeout_s,
                    arm=args.arm,
                    model=args.model,
                    probe=True,
                )
            else:
                probe_runner = {"bare": run_bare, "openhands": run_openhands}[base]
                probe_runner(
                    args.instance, max_steps=steps, timeout_s=args.timeout_s, probe=True
                )
        elif base == "claude":
            run_claude(
                args.instance,
                max_steps=steps,
                timeout_s=args.timeout_s,
                arm=args.arm,
                model=args.model,
            )
        else:
            runner = {
                "bare": run_bare,
                "openhands": run_openhands,
            }.get(base, run_factory)
            assert key == base  # non-selectable arms are 1:1 with their run dir
            runner(args.instance, max_steps=steps, timeout_s=args.timeout_s)
    elif args.cmd == "run-all":
        run_all(
            arm=args.arm,
            model=args.model,
            workers=args.workers,
            instances=(
                [s.strip() for s in args.instances.split(",") if s.strip()]
                if args.instances
                else None
            ),
            only_working=args.only_working,
            max_steps=_resolve_max_steps(args.arm, args.max_steps),
            run_timeout_s=args.timeout_s,
            grade_timeout_s=args.grade_timeout_s,
            force_over_cap=args.force_over_cap,
            dry_run=args.dry_run,
        )
    elif args.cmd == "grade":
        grade(args.instance, run_key(args.arm, args.model), timeout_s=args.timeout_s)
    elif args.cmd == "selftest":
        selftest(args.instance, timeout_s=args.timeout_s)
    elif args.cmd == "audit":
        audit(
            args.instance,
            run_key(args.arm, args.model),
            show_responses=args.show_responses,
        )
    elif args.cmd == "report":
        report(
            from_archive=Path(args.from_archive) if args.from_archive else None,
            check=args.check,
            publish=args.publish,
        )


if __name__ == "__main__":
    main()
