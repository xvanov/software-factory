#!/usr/bin/env python3
"""The BENCHMARK RECORD store — every benchmark attempt, queryable over time.

WHAT THIS IS NOT
----------------
It is not the engine's tracer database. ``bench/swebench/runs/sssf-bench.db`` is
written by ``/home/k/sssf/adws/adw_modules/tracer.py`` while an ADW executes; its
tables (``sessions, phases, events, agent_sessions, envelopes, gate_results,
processes``) are an EXECUTION TRACE, shared by every sssf run of every arm, and
its ``sessions.total_cost`` is a RUNNING SUM across attempts of the same cell.
This file is the BENCHMARK RECORD: one immutable row per graded attempt, with the
figures snapshotted at ingest and the provenance needed to re-run it.

It is also not a home for ordinary factory work. A benchmark row is graded by a
hidden oracle the agent never sees, runs in an isolated state root against a
pinned immutable manifest, and has its test edits stripped. Ordinary factory
telemetry has none of those properties and must never be written here — see
``BENCHMARK-RECORDS.md``, section "A benchmark run is not the factory building
something".

WHY IT HAS TO EXIST
-------------------
``_sssf_adw_id`` is a pure function of (instance, arm), so a re-run REUSES the
adw_id and the artifacts of the superseded attempt are destroyed:

* ``_reset_run_artifacts`` deletes ``result.json``/``audit.json``/``*.diff``;
* ``_work_dir(fresh=True)`` rmtree's the per-run ``data_dir``, taking
  ``raw_output.jsonl`` — the ONLY per-turn record of what was spent — with it;
* the shared tracer db keeps accumulating into the SAME ``sessions`` row, so its
  totals cannot be split back into per-attempt figures.

Measured today: ``getmoto__moto-9841/chain`` is on attempt 4 and
``keras-team__keras-22316/chain`` on attempt 3. Attempts 1..3 and 1..2 exist
nowhere. Every figure for them is gone, permanently, with nothing recording that
a measurement was destroyed.

So this store keys on **(instance_id, arm, attempt)** and snapshots each
attempt's numbers, roster, caps, prices and artifact digests at ingest time.
Ingest is therefore not a reporting convenience — it is the SNAPSHOT, and it must
run before the next attempt of the same cell overwrites the disk. ``run_all``
calls it automatically at the end of every sweep for exactly that reason.

REUSE, NOT REIMPLEMENTATION
---------------------------
Nothing about validity, cost bases or arm identity is re-decided here. The
adapter is imported and its own predicates are called:

* ``classify_run`` — ok / budget_exhausted / run_failed / no_result;
* ``_ungradable_kind`` — ``task_broken*`` and ``grade_parse_failed``;
* ``_row_provider_starved`` — the throttling detector;
* ``arm_spec`` / ``_ARMS`` — the arm registry (harness, cost source, caps, chain).

A second copy of any of those would be a second answer to "what counts", which
is precisely the defect that forced the 2026-08-03 retraction (two classifiers,
two published denominators).

USAGE
-----
    uv run python bench/swebench/benchmark_store.py ingest
    uv run python bench/swebench/benchmark_store.py rates
    uv run python bench/swebench/benchmark_store.py cost
    uv run python bench/swebench/benchmark_store.py roles --arm chain
    uv run python bench/swebench/benchmark_store.py validity
    uv run python bench/swebench/benchmark_store.py campaigns
    uv run python bench/swebench/benchmark_store.py diff --a <campaign> --b <campaign>
    uv run python bench/swebench/benchmark_store.py show    --instance <id> --arm chain
    uv run python bench/swebench/benchmark_store.py replay  --instance <id> --arm chain
    uv run python bench/swebench/benchmark_store.py verify
    uv run python bench/swebench/benchmark_store.py export --out records.jsonl

Every verb is READ-ONLY except ``ingest``. Nothing here calls a model; nothing
here can spend a cent.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ADAPTER_PATH = _HERE.parent / "swebench_adapter.py"

# The store's default home. Deliberately NOT under ``runs/``:
#
# 1. ``runs/`` is gitignored scratch that the next sweep legitimately wipes, and
#    ``runs/sssf-bench.db`` already lives there. A record store whose whole
#    purpose is to OUTLIVE the run directory cannot sit inside it.
# 2. Two sqlite files in one directory, one of them named ``sssf-bench.db``, is
#    an invitation to point a query at the wrong one. Different directories, and
#    a name that says what it holds.
# 3. It sits beside the other durable evidence — ``manifest.json``,
#    ``selftest.json``, ``sweep-<arm>.json``, ``results-archive/`` — which is
#    where the benchmark's record already lives.
DEFAULT_DB = _HERE / "benchmarks.db"

# Bump when a column is added. Ingest refuses a db written by a NEWER version
# rather than writing rows a newer reader would misread; an older db is migrated
# by ``_migrate`` (additive columns only — this file never drops evidence).
SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


# --------------------------------------------------------------------------- #
# the adapter, imported by path
# --------------------------------------------------------------------------- #
#
# By path because ``bench/`` is not a package and the adapter is designed to run
# as a script; the test suite already loads it this way. Module-level execution
# is pure constant setup (~30 ms, measured) — it opens no database, reads no
# ``.env`` and calls nothing.


def load_adapter(path: Path | None = None) -> Any:
    """The adapter module. THE source of every classification used here."""
    target = path or _ADAPTER_PATH
    spec = importlib.util.spec_from_file_location("_swebench_adapter_store", target)
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable in-repo
        raise SystemExit(f"cannot import the adapter at {target}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
#
# Five tables around one spine, and the shape is driven by four questions the
# operator actually asked.
#
# * "statistics over time" -> ``campaign`` is the time axis. A sweep is the unit
#   an operator runs and the unit a rate is quoted over, so rates are grouped by
#   campaign, never by wall-clock bucket. ``sweep-<arm>.json`` is OVERWRITTEN by
#   the next sweep of the same arm, so its content is snapshotted here verbatim.
# * "every run exactly" -> ``run_attempt``, UNIQUE(instance_id, arm, attempt).
#   Not (instance, arm): that is the identity the DISK uses, and it is why
#   attempt history dies. The whole ``result.json`` is kept verbatim in
#   ``result_json`` beside the extracted columns, so no future question is
#   blocked by a column this schema failed to anticipate, and ``result_sha256``
#   makes the copy checkable against the file it came from.
# * "what the chain was composed of versus the solo agents" -> the composition
#   columns on ``run_attempt`` (``roster_json``, ``roles_run``, ``chain_roles``,
#   ``is_chain``, ``harness_id``) plus per-role rows in ``role_usage``. ``is_chain``
#   is DERIVED from the roster's role count, never from the arm name: an arm
#   called "chain" that ran one role is a solo run and the data must say so.
# * "reproduce it" -> ``provenance``, one row per attempt, holding the roster YAML
#   and prompt VERBATIM, the caps, the price table digest AND its rates, the arm
#   registry entry, and both repositories' git shas with an explicit dirty flag.
# * "audit and replay the full trail" -> ``artifact``, one row per file with
#   path + sha256 + size, so the trail is verifiable later and any tampering or
#   truncation is detectable; and ``price_rate``, the rates in force, normalised
#   so a per-role dollar figure can be re-derived from the store alone.
#
# Cost bases are never merged. ``cost_source`` is NOT NULL on ``run_attempt`` and
# is carried on ``campaign`` too, and every cost query groups by it: Azure
# price-table dollars and Claude-CLI-subscription dollars are different units and
# summing them produces a number with no meaning.

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One sweep. The time axis for every "over time" question.
CREATE TABLE IF NOT EXISTS campaign (
    campaign_id       TEXT PRIMARY KEY,   -- "<run_key>@<finished_at>"
    arm               TEXT NOT NULL,
    model             TEXT,               -- NULL => resolved from routes/roster
    harness           TEXT,
    harness_id        TEXT,
    workers           INTEGER,            -- the parallelism actually used
    finished_at       TEXT NOT NULL,
    wall_clock_s      REAL,
    stopped_reason    TEXT,               -- spend cap / Ctrl-C / NULL
    instances         INTEGER,
    cost_usd          REAL,
    cost_source       TEXT NOT NULL,      -- NEVER summed across values
    resolved          INTEGER,
    gradable          INTEGER,
    summary_path      TEXT,
    summary_sha256    TEXT,
    summary_json      TEXT NOT NULL,      -- verbatim; the file gets overwritten
    first_ingested_at TEXT NOT NULL,
    last_ingested_at  TEXT NOT NULL
);

-- THE row of record. One per graded attempt, forever.
CREATE TABLE IF NOT EXISTS run_attempt (
    attempt_uid              INTEGER PRIMARY KEY,
    instance_id              TEXT NOT NULL,
    arm                      TEXT NOT NULL,   -- the RUN KEY (arm[@model])
    attempt                  INTEGER NOT NULL,
    -- WHERE the attempt number came from. A pre-1.6 row predates the counter
    -- entirely and is attempt 1 BY ASSUMPTION (the adapter's own posture); the
    -- record says so rather than presenting an assumption as a measurement.
    attempt_source           TEXT NOT NULL,
    campaign_id              TEXT REFERENCES campaign(campaign_id),
    ran_at                   TEXT,
    -- the pinned task
    repo                     TEXT,
    base_commit              TEXT,
    problem_statement_sha256 TEXT,
    manifest_sha256          TEXT,
    -- composition: chain vs solo
    runner_base              TEXT,   -- factory | bare | claude | openhands | sssf
    harness                  TEXT,
    harness_id               TEXT,
    has_chain                INTEGER,
    is_chain                 INTEGER NOT NULL,  -- DERIVED from the roster
    roster_role_count        INTEGER,
    roles_run                TEXT,   -- JSON list, measured from the trace
    roles_skipped            TEXT,
    chain_roles              TEXT,
    roster_json              TEXT,   -- {role: model}
    roster_sha256            TEXT,
    models_used              TEXT,   -- JSON list, from the LEDGER not the config
    model_calls              INTEGER,
    -- measurement
    cost_usd                 REAL,
    cost_source              TEXT NOT NULL,
    cost_usd_events          REAL,   -- the cross-checks, kept apart on purpose
    cost_usd_shared_db       REAL,
    cost_usd_rederived       REAL,
    tokens_in                INTEGER,
    cached_input_tokens      INTEGER,
    tokens_out               INTEGER,
    reasoning_tokens         INTEGER,
    total_tokens             INTEGER,
    wall_clock_s             REAL,
    steps_used               INTEGER,
    step_cap                 INTEGER,
    step_unit                TEXT,
    termination              TEXT,
    -- what the harness claimed vs what the oracle found
    factory_says_green       INTEGER,
    green_state              TEXT,
    oracle_resolved          INTEGER,   -- NULL => never graded
    outcome                  TEXT,
    grade_json               TEXT,
    diff_bytes               INTEGER,
    files_changed            TEXT,
    -- validity, all of it derived through the adapter's own predicates
    status                   TEXT NOT NULL,
    status_detail            TEXT,
    audit_ok                 INTEGER,   -- NULL => not audited
    audit_failures           TEXT,
    budget_exhausted         INTEGER,
    budget_exhausted_reason  TEXT,
    provider_starved         INTEGER,
    empty_response_turns     INTEGER,
    reportable               INTEGER NOT NULL,
    invalid_reasons          TEXT NOT NULL,  -- JSON list; "[]" iff reportable
    -- the trail: how many files were digested, and how many of the run dir's
    -- files were NOT (a factory run dir holds an entire isolated state root of
    -- rebuildable scratch). Stated, so the omission is never implied.
    artifacts_recorded       INTEGER,
    artifacts_skipped        INTEGER,
    -- the source, verbatim and checkable
    result_sha256            TEXT NOT NULL,
    result_json              TEXT NOT NULL,
    source_dir               TEXT NOT NULL,
    revision                 INTEGER NOT NULL DEFAULT 1,
    first_ingested_at        TEXT NOT NULL,
    last_ingested_at         TEXT NOT NULL,
    UNIQUE(instance_id, arm, attempt)
);

CREATE INDEX IF NOT EXISTS idx_attempt_arm       ON run_attempt(arm, attempt);
CREATE INDEX IF NOT EXISTS idx_attempt_campaign  ON run_attempt(campaign_id);
CREATE INDEX IF NOT EXISTS idx_attempt_report    ON run_attempt(reportable, arm);
CREATE INDEX IF NOT EXISTS idx_attempt_instance  ON run_attempt(instance_id, arm);

-- Per-role usage: the chain-vs-solo breakdown the operator asked for.
CREATE TABLE IF NOT EXISTS role_usage (
    attempt_uid            INTEGER NOT NULL REFERENCES run_attempt(attempt_uid) ON DELETE CASCADE,
    role                   TEXT NOT NULL,
    roster_model           TEXT,   -- what the roster ASKED for
    models_used            TEXT,   -- what the trace SHOWS (JSON list)
    input_tokens           INTEGER,
    output_tokens          INTEGER,
    cache_read_tokens      INTEGER,
    cache_write_tokens     INTEGER,
    reasoning_tokens       INTEGER,
    total_tokens           INTEGER,
    cost_usd               REAL,
    cost_source            TEXT NOT NULL,
    calls                  INTEGER,
    empty_response_turns   INTEGER,
    peak_turn_input_tokens INTEGER,
    skipped                INTEGER NOT NULL DEFAULT 0,  -- on the roster, never ran
    PRIMARY KEY (attempt_uid, role)
);

-- The audit trail, file by file. path + sha256 + size makes it verifiable and
-- tamper-evident: a diagnostic later truncated, corrupted or swapped fails
-- ``verify`` even after the bytes themselves are long gone from ``runs/``.
CREATE TABLE IF NOT EXISTS artifact (
    attempt_uid  INTEGER NOT NULL REFERENCES run_attempt(attempt_uid) ON DELETE CASCADE,
    path         TEXT NOT NULL,   -- relative to the run dir
    kind         TEXT NOT NULL,   -- scoring | diagnostic | trajectory | config | answer_key | other
    size_bytes   INTEGER,
    sha256       TEXT,
    mtime_utc    TEXT,
    -- 1 for files that carry the hidden test ids (see the adapter's
    -- _NEVER_ARCHIVED). Their DIGEST is recorded, never their content, and
    -- ``export`` refuses to emit them.
    answer_key   INTEGER NOT NULL DEFAULT 0,
    error        TEXT,            -- unreadable at ingest; recorded, not dropped
    PRIMARY KEY (attempt_uid, path)
);

-- Everything needed to re-run the attempt. One row per attempt.
CREATE TABLE IF NOT EXISTS provenance (
    attempt_uid                 INTEGER PRIMARY KEY REFERENCES run_attempt(attempt_uid) ON DELETE CASCADE,
    -- the task, pinned
    manifest_sha256             TEXT,
    manifest_path               TEXT,
    manifest_sha256_at_ingest   TEXT,   -- differs => the manifest MOVED since the run
    instance_id                 TEXT NOT NULL,
    base_commit                 TEXT,
    problem_statement_sha256    TEXT,
    -- the configuration, verbatim
    roster_yaml                 TEXT,
    roster_yaml_sha256          TEXT,
    roster_sha256_recorded      TEXT,   -- what the row claimed; compare the two
    prompt_md                   TEXT,
    prompt_sha256               TEXT,
    arm_spec_json               TEXT,
    arm_spec_source             TEXT NOT NULL,   -- run-time stamp vs registry-at-ingest
    caps_json                   TEXT,
    max_steps                   INTEGER,
    step_unit                   TEXT,
    workers                     INTEGER,
    workers_source              TEXT,   -- campaign | unrecorded
    skip_phases                 TEXT,
    thinking                    TEXT,
    engine_path                 TEXT,
    preflight_json              TEXT,
    diff_integrity_json         TEXT,
    -- the prices, digest AND rates (a digest alone cannot re-derive a dollar)
    price_table_path            TEXT,
    price_table_sha256          TEXT,
    price_table_sha256_pinned   TEXT,
    price_table_matches_pinned  INTEGER,
    price_table_rates_json      TEXT,
    -- the CODE. Without these a "reproduction" is not one.
    harness_repo                TEXT,
    harness_git_sha             TEXT,
    harness_git_dirty           INTEGER,
    engine_repo                 TEXT,
    engine_git_sha              TEXT,
    engine_git_dirty            INTEGER,
    git_sha_source              TEXT NOT NULL,  -- run-time | ingest-time | unavailable
    reproducible                INTEGER NOT NULL,
    reproducibility_caveats     TEXT NOT NULL,  -- JSON list; "[]" iff reproducible
    replay_command              TEXT NOT NULL
);

-- The rates in force for this attempt, normalised. Lets a per-role dollar
-- figure be RE-DERIVED from the store with no external price table.
CREATE TABLE IF NOT EXISTS price_rate (
    attempt_uid       INTEGER NOT NULL REFERENCES run_attempt(attempt_uid) ON DELETE CASCADE,
    model             TEXT NOT NULL,
    units             TEXT NOT NULL,
    input_per_unit    REAL,
    output_per_unit   REAL,
    cache_read_per_unit  REAL,
    cache_write_per_unit REAL,
    PRIMARY KEY (attempt_uid, model)
);

-- Who ingested what, when. An audit trail for the audit trail: a row whose
-- figures changed between ingests is visible as ``revision > 1``, and this
-- table says which ingest did it.
CREATE TABLE IF NOT EXISTS ingest_log (
    ingest_id        INTEGER PRIMARY KEY,
    started_at       TEXT NOT NULL,
    finished_at      TEXT NOT NULL,
    source_root      TEXT NOT NULL,
    rows_seen        INTEGER NOT NULL,
    inserted         INTEGER NOT NULL,
    updated          INTEGER NOT NULL,
    unchanged        INTEGER NOT NULL,
    skipped          INTEGER NOT NULL,
    campaigns_seen   INTEGER NOT NULL,
    notes            TEXT NOT NULL
);
"""


def connect(db_path: Path | None = None, *, read_only: bool = False) -> sqlite3.Connection:
    """Open (and if needed create) the record store.

    WAL, like the engine's tracer db and for the same reason: a query must be
    able to read while a sweep's ingest writes. ``foreign_keys=ON`` so a deleted
    attempt cannot leave orphaned role/artifact rows behind — the trail is only
    verifiable if it stays connected to the row it belongs to.
    """
    path = Path(db_path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA synchronous=NORMAL")
    if not read_only:
        con.executescript(_SCHEMA)
        _migrate(con)
    return con


def _migrate(con: sqlite3.Connection) -> None:
    """Record/verify the schema version. Refuse a db from a NEWER writer.

    A newer writer may have added a column this reader does not know about, and
    quietly ignoring it would publish figures derived from a partial read. The
    other direction is safe: ``CREATE TABLE IF NOT EXISTS`` plus additive
    columns, and this store never drops a column, because a dropped column is
    deleted evidence.
    """
    row = con.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        con.commit()
        return
    found = int(row["value"])
    if found > SCHEMA_VERSION:
        raise SystemExit(
            f"this benchmark store was written by schema version {found}; this "
            f"code speaks {SCHEMA_VERSION}. Refusing to read it partially — "
            "update bench/swebench/benchmark_store.py."
        )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> tuple[str | None, int | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return None, None, f"unreadable: {exc}"
    return _sha256_bytes(raw), len(raw), None


def _js(value: Any) -> str | None:
    """Canonical JSON for a stored blob: sorted keys, so re-ingesting identical
    content produces identical bytes and ``revision`` does not churn."""
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _jl(value: Any) -> str:
    """A JSON list, always a list, never NULL — ``invalid_reasons`` is read by a
    query that must not have to handle three empty representations."""
    if value is None:
        return "[]"
    if isinstance(value, list):
        return json.dumps([str(v) for v in value], ensure_ascii=False)
    return json.dumps([str(value)], ensure_ascii=False)


def _b(value: Any) -> int | None:
    """Tri-state boolean -> sqlite. ``None`` stays ``None``: ``audit_ok`` NULL
    means NOT AUDITED, which is not the same as audit failed."""
    return None if value is None else int(bool(value))


def _f(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# git provenance
# --------------------------------------------------------------------------- #


def repo_state(repo: Path) -> dict[str, Any]:
    """``{path, sha, dirty, error}`` for a git checkout, best effort.

    A DIRTY tree is recorded as dirty rather than silently reported as its HEAD
    sha, because a dirty tree is not reproducible and a record that implies
    otherwise is worse than no record. Uses ``subprocess`` directly rather than
    the adapter's ``_git`` because that helper is scoped to bench worktrees.
    """
    import subprocess

    out: dict[str, Any] = {"path": str(repo), "sha": None, "dirty": None, "error": None}
    if not (repo / ".git").exists():
        out["error"] = "not a git checkout"
        return out
    try:
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if sha.returncode != 0:
            out["error"] = f"rev-parse failed: {sha.stderr.strip()[:200]}"
            return out
        out["sha"] = sha.stdout.strip()
        st = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if st.returncode != 0:
            out["error"] = f"status failed: {st.stderr.strip()[:200]}"
            return out
        changed = [ln for ln in st.stdout.splitlines() if ln.strip()]
        out["dirty"] = bool(changed)
        out["dirty_files"] = len(changed)
    except (OSError, subprocess.SubprocessError) as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------- #
# validity — every predicate delegated to the adapter
# --------------------------------------------------------------------------- #


def classify(adapter: Any, row: dict[str, Any], audit: dict[str, Any] | None) -> dict[str, Any]:
    """``(status, reportable, invalid_reasons)`` for one row.

    "Reportable" means: this row is a measurement OF THE ARM. Six ways it is
    not, and each is named separately because they are different failures and
    lumping them would hide which one is happening:

    1. never graded — no oracle verdict exists, so there is nothing to report;
    2. ``task_broken*`` — the INSTANCE is broken (the ~30% SWE-bench-Pro floor);
    3. ``grade_parse_failed`` — THIS HARNESS could not read pytest's report; a
       harness defect reported as an arm failure becomes a uniform 0% that looks
       like a finding;
    4. the run failed, or produced no result — a crash is not an attempt;
    5. the audit failed or never ran — an unverifiable trail is not evidence.

    Plus one that is not in ``_arm_view``'s ``valid`` filter and belongs here:
    ``provider-empty-response``. The provider refused requests and the engine
    swallowed it, so the row measures somebody else's queue at this sweep's
    concurrency, not the arm. It is flagged loudly in ``_render_summary`` and in
    the report's Table 1 footnote for that reason; the store makes it a first
    class exclusion so "give me only reportable rows" is one predicate.

    And one that is a property of the ARM rather than the run: a SUPERSEDED run
    key (``ArmSpec.superseded_by``) is the same (harness, model) pair re-measured
    under a later arm id, so reporting both would double-count one arm and blend
    pre- and post-fix evidence. ``_report_rows`` segregates those rows; the store
    KEEPS them (they are the "before" evidence) and marks them unreportable.

    What is deliberately NOT here: the row's ``manifest_sha256``. ``_report_rows``
    drops a row from another manifest as "foreign", and it is right to — one
    report is pinned to one manifest. But this store's whole purpose is history
    ACROSS manifests, so a 2026-08-03 row is not invalid for having run under the
    dataset pinned then. Comparability is enforced in the QUERIES instead: every
    rate groups by ``manifest_sha256``, so two manifests can never be blended
    into one rate.

    A budget cap hit is NOT here either. Under pre-registered decision rule 4 a
    cap hit is a COMPLETED, COUNTED, FLAGGED attempt for every arm — excluding one
    is how the retracted run silently improved its own denominator.
    """
    status, detail = adapter.classify_run(row)
    grade = row.get("grade") or {}
    resolved = grade.get("oracle_resolved")
    outcome = str(grade.get("outcome") or "")
    audit_ok = None if audit is None else (audit.get("ok") is True)
    starved = adapter._row_provider_starved(row)

    reasons: list[str] = []
    if resolved is None:
        reasons.append("not graded: no oracle verdict on this attempt")
    kind = adapter._ungradable_kind(outcome)
    if kind == "task_broken":
        reasons.append(f"task_broken: the INSTANCE is broken ({outcome})")
    elif kind is not None:
        reasons.append(
            f"grade_parse_failed: this harness could not read the per-node "
            f"report ({outcome}) — a harness defect, not an arm result"
        )
    if status == adapter._RUN_NO_RESULT:
        reasons.append("no result.json")
    elif status == adapter._RUN_FAILED:
        reasons.append(f"run failed: {adapter._excerpt(detail)}")
    if audit_ok is False:
        fails = "; ".join(str(f) for f in (audit or {}).get("failures") or []) or "unknown"
        reasons.append(f"audit failed: {adapter._excerpt(fails)}")
    elif audit_ok is None:
        reasons.append("not audited: no readable audit.json")
    if starved:
        reasons.append(
            "provider-empty-response: the deployment swallowed "
            f"{int(row.get('empty_response_turns') or 0)} turn(s) — throttling, "
            "not capability; re-run at lower concurrency"
        )
    spec = adapter._ARMS.get(adapter._split_run_key(str(row.get("arm") or ""))[0])
    if spec is not None and spec.superseded_by:
        reasons.append(
            f"superseded run key: {row.get('arm')!r} was replaced by "
            f"{spec.superseded_by!r} — the same (harness, model) pair re-measured "
            "under a later harness. Kept as the 'before' evidence; reporting both "
            "would double-count one arm"
        )
    return {
        "status": status,
        "status_detail": detail,
        "audit_ok": audit_ok,
        "provider_starved": starved,
        "reportable": not reasons,
        "invalid_reasons": reasons,
    }


# --------------------------------------------------------------------------- #
# artifact enumeration
# --------------------------------------------------------------------------- #

_SCORING = ("result.json", "audit.json", "prediction.diff")
_CONFIG = ("sssf-roster.yaml", "sssf-prompt.md", "attempt.json")


def _artifact_kind(adapter: Any, rel: str) -> tuple[str, bool]:
    name = Path(rel).name
    if name in adapter._NEVER_ARCHIVED:
        # The hidden test ids. Digest yes, content never — see ``artifact.answer_key``.
        return "answer_key", True
    if rel in _SCORING:
        return "scoring", False
    if rel in _CONFIG:
        return "config", False
    if name.endswith(".ndjson") or name in (
        adapter._SSSF_EVENTS_NAME,
        adapter._SSSF_TURNS_NAME,
        adapter._SSSF_TRAJECTORY_NAME,
    ):
        return "trajectory", False
    if name.endswith((".log", ".diff")):
        return "diagnostic", False
    return "other", False


def _evidence_files(adapter: Any, run_dir: Path) -> tuple[list[Path], int]:
    """``(files_to_hash, files_skipped)`` for one run dir.

    The set is the run's EVIDENCE, defined by the adapter's own archive lists
    rather than by a second opinion here:

    * every TOP-LEVEL file — ``result.json``, ``audit.json``, both diffs, the
      grade and sweep logs, ``attempt.json``, and the sssf roster / prompt /
      events / turn digest;
    * ``_ARCHIVED_ROW_EXTRAS`` — the reviewer corpus and the acceptance oracle's
      provenance, which live several levels down inside the run's state root;
    * ``_ARCHIVED_TRAJECTORY_GLOBS`` — the action trail, per arm.

    NOT the whole tree. Measured: recursing it produced 102,106 artifact rows and
    a 30 MB store, because a ``factory`` run dir contains an entire isolated
    state root (its own sqlite ledger, worktrees, docker logs) — scratch that the
    next run legitimately rebuilds and that no audit refers to. The count of what
    was skipped is recorded on the attempt, so the omission is stated rather than
    implied.
    """
    seen: set[Path] = set()
    files: list[Path] = []

    def take(p: Path) -> None:
        if p.is_file() and not p.is_symlink() and p not in seen:
            seen.add(p)
            files.append(p)

    for p in sorted(run_dir.iterdir()) if run_dir.is_dir() else []:
        take(p)
    for rel in adapter._ARCHIVED_ROW_EXTRAS:
        take(run_dir / rel)
    for pattern in adapter._ARCHIVED_TRAJECTORY_GLOBS:
        for p in sorted(run_dir.glob(pattern)):
            take(p)
    total = sum(
        1 for p in run_dir.rglob("*") if p.is_file() and not p.is_symlink()
    )
    return files, max(total - len(files), 0)


# --------------------------------------------------------------------------- #
# ingest
# --------------------------------------------------------------------------- #


def _campaign_rows(summary: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    """``{(instance_id, attempt): sweep-record}`` for one sweep summary.

    The join key is (instance, attempt) and that is what makes campaign
    attribution EXACT rather than a timestamp guess: every sweep record already
    carries the attempt number the run wrote, so a row can only ever be claimed
    by the sweep that actually produced it.
    """
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for rec in summary.get("results") or []:
        if not isinstance(rec, dict):
            continue
        iid = str(rec.get("instance_id") or "")
        att = _i(rec.get("attempt"))
        if iid and att is not None:
            out[(iid, att)] = rec
    return out


def campaign_id_for(summary: dict[str, Any]) -> str:
    """``"<run_key>@<finished_at>"``.

    Deterministic and human-readable, so re-ingesting the same
    ``sweep-<arm>.json`` is a no-op while the NEXT sweep of the same arm — which
    overwrites the file — lands as a separate campaign. Keyed on the run key
    (arm plus any model), never the bare arm, for the same reason the run
    directories are: two claude sweeps on two models are two campaigns.
    """
    arm = str(summary.get("arm") or "unknown")
    return f"{arm}@{summary.get('finished_at') or 'unknown'}"


def ingest_campaigns(
    con: sqlite3.Connection, adapter: Any, *, swe_dir: Path, now: str
) -> tuple[dict[str, dict[tuple[str, int], dict[str, Any]]], int]:
    """Snapshot every ``sweep-<key>.json`` beside the manifest.

    Returns ``{campaign_id: {(instance, attempt): record}}`` for the attempt
    join, plus a count. Snapshotting is the point: the file is OVERWRITTEN by the
    next sweep of the same arm, so the ``--workers`` value and the sweep's own
    roll-up survive only here.
    """
    index: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
    seen = 0
    for path in sorted(swe_dir.glob("sweep-*.json")):
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(summary, dict) or not summary.get("arm"):
            continue
        cid = campaign_id_for(summary)
        arm = str(summary["arm"])
        spec = adapter._ARMS.get(adapter._split_run_key(arm)[0])
        digest, _size, _err = _sha256_file(path)
        # The results list is kept — it is the sweep's own per-row roll-up and
        # the only record of rows a later attempt overwrote.
        blob = _js(summary) or "{}"
        con.execute(
            """
            INSERT INTO campaign(
                campaign_id, arm, model, harness, harness_id, workers,
                finished_at, wall_clock_s, stopped_reason, instances, cost_usd,
                cost_source, resolved, gradable, summary_path, summary_sha256,
                summary_json, first_ingested_at, last_ingested_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(campaign_id) DO UPDATE SET
                last_ingested_at=excluded.last_ingested_at,
                summary_json=excluded.summary_json,
                summary_sha256=excluded.summary_sha256
            """,
            (
                cid, arm, summary.get("model"), summary.get("harness"),
                spec.harness_id if spec else None, _i(summary.get("workers")),
                str(summary.get("finished_at") or ""), _f(summary.get("wall_clock_s")),
                summary.get("stopped_reason"), _i(summary.get("instances")),
                _f(summary.get("cost_usd")),
                str(summary.get("cost_source") or (spec.cost_source if spec else "unknown")),
                _i(summary.get("resolved")), _i(summary.get("gradable")),
                str(path), digest, blob, now, now,
            ),
        )
        index[cid] = _campaign_rows(summary)
        seen += 1
    return index, seen


def _find_campaign(
    index: dict[str, dict[tuple[str, int], dict[str, Any]]],
    arm: str,
    instance_id: str,
    attempt: int,
) -> tuple[str | None, dict[str, Any] | None]:
    for cid, rows in index.items():
        if not cid.startswith(f"{arm}@"):
            continue
        rec = rows.get((instance_id, attempt))
        if rec is not None:
            return cid, rec
    return None, None


def _replay_command(instance_id: str, arm: str, *, max_steps: int | None) -> str:
    steps = f" --max-steps {max_steps}" if max_steps else ""
    return (
        "uv run python bench/swebench_adapter.py run "
        f"--instance {instance_id} --arm {arm}{steps}\n"
        "uv run python bench/swebench_adapter.py grade "
        f"--instance {instance_id} --arm {arm}\n"
        "uv run python bench/swebench_adapter.py audit "
        f"--instance {instance_id} --arm {arm}"
    )


def ingest_row(
    con: sqlite3.Connection,
    adapter: Any,
    run_dir: Path,
    *,
    campaign_index: dict[str, dict[tuple[str, int], dict[str, Any]]],
    now: str,
    swe_dir: Path,
    harness_repo: Path,
    engine_repo: Path,
    repo_cache: dict[str, dict[str, Any]],
) -> str:
    """Ingest one ``<instance>/<run-key>/`` directory. Returns the disposition.

    ``inserted`` | ``updated`` | ``unchanged`` | ``skipped:<why>``.

    IDEMPOTENT by construction: the row's identity is (instance, arm, attempt)
    and its content is fingerprinted by ``result_sha256`` over the exact
    ``result.json`` bytes. Same bytes => nothing is written at all. Different
    bytes for the SAME attempt means the file was legitimately amended after the
    run (``grade`` merges its verdict in, then ``audit`` writes beside it), so
    the row is updated in place and ``revision`` counts how many times that
    happened. A NEW attempt number never touches the old row — that is the whole
    point of the store.

    A consequence worth stating: an unchanged ``result.json`` short-circuits
    BEFORE the artifact digests are re-read, so the digests recorded are the ones
    taken at first ingest. That is deliberate — they are the snapshot, and
    silently refreshing them would destroy the very baseline ``verify`` compares
    against.
    """
    result_path = run_dir / "result.json"
    try:
        raw = result_path.read_bytes()
        row = json.loads(raw.decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return f"skipped:unreadable result.json ({exc})"
    if not isinstance(row, dict):
        return "skipped:result.json is not a JSON object"

    key = run_dir.name
    instance_id = str(row.get("instance_id") or run_dir.parent.name)
    recorded_arm = str(row.get("arm") or "")
    if recorded_arm and recorded_arm != key:
        # The adapter's own refusal, kept: a row whose two identities disagree
        # cannot be filed under either.
        return (
            f"skipped:result.json records arm {recorded_arm!r} but sits in the "
            f"{key!r} run directory"
        )
    attempt = _i(row.get("attempt"))
    if attempt is not None:
        attempt_source = "result.json"
    else:
        # A pre-1.6 row: the ``attempt`` stamp did not exist when it was written.
        # Fall back to the adapter's OWN reader, whose documented default is
        # "a row that predates the counter WAS an attempt", i.e. 1. Skipping such
        # rows instead would silently discard 100+ real measurements — including
        # every row of the retracted run, which is the evidence the retraction
        # rests on.
        counted = adapter._attempt_count(run_dir)
        attempt = int(counted)
        attempt_source = (
            "attempt.json" if (run_dir / adapter._ATTEMPT_NAME).is_file()
            else "assumed-1 (pre-1.6 row: no attempt stamp, no counter file)"
        )
    if attempt == 0:
        # ``_write_result`` stamps 0 for a --probe-plumbing row: no model ran, so
        # it is not an attempt AT THE TASK. Keeping it out of the store keeps
        # "attempts of this cell" meaning what it says.
        return "skipped:plumbing probe (attempt 0) — no model ran"

    result_sha = _sha256_bytes(raw)
    existing = con.execute(
        "SELECT attempt_uid, result_sha256, revision FROM run_attempt "
        "WHERE instance_id=? AND arm=? AND attempt=?",
        (instance_id, key, attempt),
    ).fetchone()
    if existing is not None and existing["result_sha256"] == result_sha:
        return "unchanged"

    try:
        audit_raw = (run_dir / "audit.json").read_text(encoding="utf-8")
        audit_obj = json.loads(audit_raw)
        audit: dict[str, Any] | None = audit_obj if isinstance(audit_obj, dict) else None
    except (OSError, json.JSONDecodeError):
        audit = None

    verdict = classify(adapter, row, audit)
    spec = adapter._ARMS.get(adapter._split_run_key(key)[0])
    grade = row.get("grade") or {}
    roster = row.get("sssf_roster")
    roster_map = {k: v for k, v in roster.items()} if isinstance(roster, dict) else {}
    # ``is_chain`` from the ROSTER, not the arm id. An arm called "chain" whose
    # roster has one active role is a solo run, and the record has to say so —
    # the alternative is a "chain vs solo" statistic that trusts a name.
    active_roles = [r for r, m in roster_map.items() if m]
    if roster_map:
        is_chain = len(active_roles) > 1
    else:
        # Non-sssf arms record no roster. Fall back to the registry's own answer
        # to "can this arm produce a chain verdict at all?".
        is_chain = bool(spec and spec.has_chain)

    cid, sweep_rec = _find_campaign(campaign_index, key, instance_id, attempt)
    cost_source = str(row.get("cost_source") or (spec.cost_source if spec else "unknown"))

    fields: dict[str, Any] = {
        "instance_id": instance_id,
        "arm": key,
        "attempt": attempt,
        "attempt_source": attempt_source,
        "campaign_id": cid,
        "ran_at": row.get("ts"),
        "repo": row.get("repo"),
        "base_commit": row.get("base_commit"),
        "problem_statement_sha256": row.get("problem_statement_sha256"),
        "manifest_sha256": row.get("manifest_sha256"),
        "runner_base": spec.base if spec else None,
        "harness": spec.harness if spec else None,
        "harness_id": spec.harness_id if spec else None,
        "has_chain": _b(spec.has_chain) if spec else None,
        "is_chain": int(is_chain),
        "roster_role_count": len(active_roles) if roster_map else None,
        "roles_run": _js(row.get("sssf_roles_run")),
        "roles_skipped": _js(row.get("sssf_roles_skipped")),
        "chain_roles": _js(row.get("sssf_chain_roles")),
        "roster_json": _js(roster_map) if roster_map else None,
        "roster_sha256": row.get("sssf_roster_sha256"),
        "models_used": _js(row.get("models_used")),
        "model_calls": _i(row.get("model_calls")),
        "cost_usd": _f(row.get("cost_usd")),
        "cost_source": cost_source,
        "cost_usd_events": _f(row.get("cost_usd_events")),
        "cost_usd_shared_db": _f(row.get("cost_usd_shared_db")),
        "cost_usd_rederived": _f(row.get("cost_usd_rederived")),
        "tokens_in": _i(row.get("tokens_in")),
        "cached_input_tokens": _i(row.get("cached_input_tokens")),
        "tokens_out": _i(row.get("tokens_out")),
        "reasoning_tokens": _i(row.get("reasoning_tokens")),
        "total_tokens": _i(row.get("total_tokens")),
        "wall_clock_s": _f(row.get("wall_clock_s")),
        "steps_used": _i(row.get("steps_used")),
        "step_cap": _i(row.get("step_cap")),
        "step_unit": spec.step_unit if spec else None,
        "termination": row.get("termination"),
        "factory_says_green": _b(row.get("factory_says_green")),
        "green_state": row.get("green_state"),
        "oracle_resolved": _b(grade.get("oracle_resolved")),
        "outcome": grade.get("outcome"),
        "grade_json": _js(grade) if grade else None,
        "diff_bytes": _i(row.get("diff_bytes")),
        "files_changed": _js(row.get("files_changed")),
        "status": verdict["status"],
        "status_detail": verdict["status_detail"],
        "audit_ok": _b(verdict["audit_ok"]),
        "audit_failures": _js((audit or {}).get("failures")),
        "budget_exhausted": _b(row.get("budget_exhausted")),
        "budget_exhausted_reason": row.get("budget_exhausted_reason"),
        "provider_starved": _b(verdict["provider_starved"]),
        "empty_response_turns": _i(row.get("empty_response_turns")),
        "reportable": int(verdict["reportable"]),
        "invalid_reasons": _jl(verdict["invalid_reasons"]),
        "result_sha256": result_sha,
        "result_json": raw.decode("utf-8"),
        "source_dir": str(run_dir),
        "last_ingested_at": now,
    }

    if existing is None:
        cols = [*fields, "revision", "first_ingested_at"]
        vals = [*fields.values(), 1, now]
        con.execute(
            f"INSERT INTO run_attempt({', '.join(cols)}) "
            f"VALUES({', '.join('?' * len(cols))})",
            vals,
        )
        uid = int(con.execute("SELECT last_insert_rowid() AS i").fetchone()["i"])
        disposition = "inserted"
    else:
        uid = int(existing["attempt_uid"])
        sets = ", ".join(f"{c}=?" for c in fields)
        con.execute(
            f"UPDATE run_attempt SET {sets}, revision=revision+1 WHERE attempt_uid=?",
            [*fields.values(), uid],
        )
        disposition = "updated"

    _write_roles(con, uid, row, roster_map, cost_source)
    recorded, skipped_files = _write_artifacts(con, adapter, uid, run_dir)
    con.execute(
        "UPDATE run_attempt SET artifacts_recorded=?, artifacts_skipped=? "
        "WHERE attempt_uid=?",
        (recorded, skipped_files, uid),
    )
    _write_provenance(
        con, adapter, uid, row, run_dir,
        spec=spec, sweep_rec=sweep_rec, cid=cid, swe_dir=swe_dir,
        harness_repo=harness_repo, engine_repo=engine_repo, repo_cache=repo_cache,
    )
    _write_rates(con, uid, row)
    return disposition


def _write_roles(
    con: sqlite3.Connection,
    uid: int,
    row: dict[str, Any],
    roster_map: dict[str, Any],
    cost_source: str,
) -> None:
    """Per-role usage, plus a row for every roster role that did NOT run.

    The skipped roles matter as much as the run ones: "chain minus documenter"
    is a composition claim, and a store that recorded only what ran could not
    distinguish a role that was skipped by configuration from a role that
    silently never fired.
    """
    con.execute("DELETE FROM role_usage WHERE attempt_uid=?", (uid,))
    usage = row.get("usage_by_role")
    usage = usage if isinstance(usage, dict) else {}
    skipped = {str(r) for r in (row.get("sssf_roles_skipped") or [])}
    for role in sorted(set(usage) | set(roster_map)):
        u = usage.get(role) if isinstance(usage.get(role), dict) else {}
        con.execute(
            """
            INSERT INTO role_usage(
                attempt_uid, role, roster_model, models_used, input_tokens,
                output_tokens, cache_read_tokens, cache_write_tokens,
                reasoning_tokens, total_tokens, cost_usd, cost_source, calls,
                empty_response_turns, peak_turn_input_tokens, skipped)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                uid, role, roster_map.get(role), _js(u.get("models")),
                _i(u.get("input_tokens")), _i(u.get("output_tokens")),
                _i(u.get("cache_read_tokens")), _i(u.get("cache_write_tokens")),
                _i(u.get("reasoning_tokens")), _i(u.get("total_tokens")),
                _f(u.get("total_cost")), cost_source, _i(u.get("calls")),
                _i(u.get("empty_response_turns")), _i(u.get("peak_turn_input_tokens")),
                int(role in skipped or (role in roster_map and not roster_map[role])),
            ),
        )


def _write_artifacts(
    con: sqlite3.Connection, adapter: Any, uid: int, run_dir: Path
) -> tuple[int, int]:
    con.execute("DELETE FROM artifact WHERE attempt_uid=?", (uid,))
    files, skipped = _evidence_files(adapter, run_dir)
    for path in files:
        rel = path.relative_to(run_dir).as_posix()
        kind, answer_key = _artifact_kind(adapter, rel)
        digest, size, err = _sha256_file(path)
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        except OSError:
            mtime = None
        con.execute(
            "INSERT INTO artifact(attempt_uid, path, kind, size_bytes, sha256, "
            "mtime_utc, answer_key, error) VALUES(?,?,?,?,?,?,?,?)",
            (uid, rel, kind, size, digest, mtime, int(answer_key), err),
        )
    return len(files), skipped


def _write_provenance(
    con: sqlite3.Connection,
    adapter: Any,
    uid: int,
    row: dict[str, Any],
    run_dir: Path,
    *,
    spec: Any,
    sweep_rec: dict[str, Any] | None,
    cid: str | None,
    swe_dir: Path,
    harness_repo: Path,
    engine_repo: Path,
    repo_cache: dict[str, dict[str, Any]],
) -> None:
    """Everything needed to re-run, and an explicit verdict on whether it can be.

    ``reproducible`` is a CONCLUSION, not a hope. Each caveat that makes exact
    replay impossible is named in ``reproducibility_caveats``, so the record
    never implies a reproducibility it does not have — a dirty checkout, a moved
    price table, a missing roster, an unrecorded engine sha.
    """
    instance_id = str(row.get("instance_id") or run_dir.parent.name)
    roster_path = run_dir / "sssf-roster.yaml"
    prompt_path = run_dir / "sssf-prompt.md"
    roster_yaml = None
    roster_yaml_sha = None
    if roster_path.is_file():
        try:
            roster_yaml = roster_path.read_text(encoding="utf-8")
            roster_yaml_sha = _sha256_bytes(roster_yaml.encode("utf-8"))
        except OSError:
            roster_yaml = None
    prompt_md = None
    prompt_sha = None
    if prompt_path.is_file():
        try:
            prompt_md = prompt_path.read_text(encoding="utf-8")
            prompt_sha = _sha256_bytes(prompt_md.encode("utf-8"))
        except OSError:
            prompt_md = None

    # The run-time stamp if the row carries one (``_write_result`` adds it), else
    # the registry AS IT IS NOW plus git AS IT IS NOW — labelled, because a
    # retroactively captured sha is evidence about the ingest, not about the run.
    stamp = row.get("provenance_stamp")
    stamp = stamp if isinstance(stamp, dict) else {}
    stamped_repos = stamp.get("repos") if isinstance(stamp.get("repos"), dict) else {}
    if stamped_repos:
        git_source = "run-time"
        harness = stamped_repos.get("harness") or {}
        engine = stamped_repos.get("engine") or {}
    else:
        git_source = "ingest-time"
        for label, repo in (("harness", harness_repo), ("engine", engine_repo)):
            if label not in repo_cache:
                repo_cache[label] = repo_state(repo)
        harness = repo_cache["harness"]
        engine = repo_cache["engine"]
    arm_spec_json = _js(stamp.get("arm_spec")) if stamp.get("arm_spec") else (
        _js(spec._asdict()) if spec is not None else None
    )
    arm_spec_source = "run-time-stamp" if stamp.get("arm_spec") else "registry-at-ingest"

    price = row.get("price_table") if isinstance(row.get("price_table"), dict) else {}
    caps = row.get("sssf_caps") if isinstance(row.get("sssf_caps"), dict) else {}
    preflight = row.get("preflight") if isinstance(row.get("preflight"), dict) else {}

    # Resolved against the SWEEP directory being ingested rather than the
    # adapter's global constant, so ingesting an archive compares against that
    # archive's manifest. In production the two are the same file.
    manifest_path = swe_dir / adapter.MANIFEST_PATH.name
    live_manifest_sha = None
    if manifest_path.is_file():
        # The manifest's OWN recorded digest, which is what a row's
        # ``manifest_sha256`` is a copy of. A sha256 over the file would never
        # equal that 16-char value and would read as a mismatch on every row.
        try:
            live_manifest_sha = json.loads(
                manifest_path.read_text(encoding="utf-8")
            ).get("manifest_sha256")
        except (OSError, ValueError, AttributeError):
            live_manifest_sha = None

    workers = _i((sweep_rec or {}).get("workers"))
    if workers is None and cid is not None:
        got = con.execute(
            "SELECT workers FROM campaign WHERE campaign_id=?", (cid,)
        ).fetchone()
        workers = _i(got["workers"]) if got else None
    workers_source = "campaign" if workers is not None else "unrecorded"

    caveats: list[str] = []
    if harness.get("dirty"):
        caveats.append(
            f"the harness checkout was DIRTY ({harness.get('dirty_files')} changed "
            f"path(s)) — {harness.get('sha')} does not describe the code that ran"
        )
    if harness.get("sha") is None:
        caveats.append(f"no harness git sha: {harness.get('error')}")
    if engine.get("dirty"):
        caveats.append(
            f"the sssf engine checkout was DIRTY ({engine.get('dirty_files')} changed "
            f"path(s)) — {engine.get('sha')} does not describe the engine that ran"
        )
    if engine.get("sha") is None and str(row.get("arm") or "").strip():
        if spec is not None and spec.base == "sssf":
            caveats.append(f"no engine git sha: {engine.get('error')}")
    if git_source == "ingest-time":
        caveats.append(
            "the git shas were captured AT INGEST, not at run time: the row "
            "predates provenance stamping, so they describe the checkout as it "
            "is now and only bound the run from above"
        )
    if price and price.get("matches_pinned") is False:
        caveats.append(
            "the price table did not match its pinned sha256 at run time — the "
            "recorded dollars were derived from rates that had moved"
        )
    if live_manifest_sha and row.get("manifest_sha256") and (
        live_manifest_sha != row.get("manifest_sha256")
    ):
        caveats.append(
            f"the pinned manifest has MOVED since this run "
            f"({row.get('manifest_sha256')} -> {live_manifest_sha}); re-fetch the "
            "recorded manifest before replaying"
        )
    if spec is not None and spec.base == "sssf" and roster_yaml is None:
        caveats.append("the roster yaml is not on disk — the exact role/model wiring "
                       "cannot be replayed byte-for-byte from this record")
    if workers is None:
        caveats.append(
            "the sweep --workers value was not recorded for this attempt (its "
            "sweep-<arm>.json was overwritten by a later sweep); concurrency "
            "affects provider throttling and therefore the result"
        )

    con.execute(
        """
        INSERT INTO provenance(
            attempt_uid, manifest_sha256, manifest_path, manifest_sha256_at_ingest,
            instance_id, base_commit, problem_statement_sha256, roster_yaml,
            roster_yaml_sha256, roster_sha256_recorded, prompt_md, prompt_sha256,
            arm_spec_json, arm_spec_source, caps_json, max_steps, step_unit,
            workers, workers_source, skip_phases, thinking, engine_path,
            preflight_json, diff_integrity_json, price_table_path,
            price_table_sha256, price_table_sha256_pinned,
            price_table_matches_pinned, price_table_rates_json, harness_repo,
            harness_git_sha, harness_git_dirty, engine_repo, engine_git_sha,
            engine_git_dirty, git_sha_source, reproducible,
            reproducibility_caveats, replay_command)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(attempt_uid) DO UPDATE SET
            manifest_sha256=excluded.manifest_sha256,
            manifest_sha256_at_ingest=excluded.manifest_sha256_at_ingest,
            roster_yaml=excluded.roster_yaml,
            roster_yaml_sha256=excluded.roster_yaml_sha256,
            prompt_md=excluded.prompt_md,
            prompt_sha256=excluded.prompt_sha256,
            arm_spec_json=excluded.arm_spec_json,
            arm_spec_source=excluded.arm_spec_source,
            caps_json=excluded.caps_json,
            workers=excluded.workers,
            workers_source=excluded.workers_source,
            price_table_sha256=excluded.price_table_sha256,
            price_table_rates_json=excluded.price_table_rates_json,
            harness_git_sha=excluded.harness_git_sha,
            harness_git_dirty=excluded.harness_git_dirty,
            engine_git_sha=excluded.engine_git_sha,
            engine_git_dirty=excluded.engine_git_dirty,
            git_sha_source=excluded.git_sha_source,
            reproducible=excluded.reproducible,
            reproducibility_caveats=excluded.reproducibility_caveats,
            replay_command=excluded.replay_command
        """,
        (
            uid, row.get("manifest_sha256"), str(manifest_path), live_manifest_sha,
            instance_id, row.get("base_commit"), row.get("problem_statement_sha256"),
            roster_yaml, roster_yaml_sha, row.get("sssf_roster_sha256"),
            prompt_md, prompt_sha, arm_spec_json, arm_spec_source,
            _js(caps) if caps else None, _i(row.get("step_cap")),
            spec.step_unit if spec else None, workers, workers_source,
            _js(row.get("sssf_skip_phases")), row.get("sssf_thinking"),
            preflight.get("engine") or row.get("sssf_engine"),
            _js(preflight) if preflight else None, _js(row.get("diff_integrity")),
            price.get("path"), price.get("sha256"), price.get("sha256_pinned"),
            _b(price.get("matches_pinned")), _js(price.get("rates")),
            str(harness.get("path") or harness_repo), harness.get("sha"),
            _b(harness.get("dirty")),
            str(engine.get("path") or engine_repo), engine.get("sha"),
            _b(engine.get("dirty")), git_source, int(not caveats), _jl(caveats),
            _replay_command(instance_id, str(row.get("arm") or run_dir.name),
                            max_steps=_i(row.get("step_cap"))),
        ),
    )


def _write_rates(con: sqlite3.Connection, uid: int, row: dict[str, Any]) -> None:
    con.execute("DELETE FROM price_rate WHERE attempt_uid=?", (uid,))
    price = row.get("price_table") if isinstance(row.get("price_table"), dict) else {}
    rates = price.get("rates") if isinstance(price.get("rates"), dict) else {}
    units = str(price.get("units") or "unspecified")
    for model, entry in sorted(rates.items()):
        cost = entry.get("cost") if isinstance(entry, dict) else {}
        cost = cost if isinstance(cost, dict) else {}
        con.execute(
            "INSERT INTO price_rate(attempt_uid, model, units, input_per_unit, "
            "output_per_unit, cache_read_per_unit, cache_write_per_unit) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                uid, str(model), units, _f(cost.get("input")), _f(cost.get("output")),
                _f(cost.get("cacheRead")), _f(cost.get("cacheWrite")),
            ),
        )


def ingest(
    *,
    db_path: Path | None = None,
    runs_dir: Path | None = None,
    swe_dir: Path | None = None,
    arms: Iterable[str] | None = None,
    harness_repo: Path | None = None,
    engine_repo: Path | None = None,
    adapter: Any | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """Ingest every on-disk row. Idempotent, retroactive, additive.

    Retroactive: it reads whatever is on disk NOW, so today's rows are captured
    without having re-run anything. Additive: it never deletes an attempt, so a
    row whose disk artifacts were destroyed by a later attempt keeps its record.
    """
    A = adapter or load_adapter()
    swe = Path(swe_dir or A.SWE_DIR)
    runs = Path(runs_dir or A.RUNS_DIR)
    harness = Path(harness_repo or A.FACTORY_ROOT)
    # The ENGINE the sssf arms drive. Read off the adapter's own constant rather
    # than hard-coded, so the record follows the harness if the engine moves.
    engine = Path(engine_repo or A._SSSF_ROOT)
    wanted = {str(a) for a in arms} if arms else None
    started = _now()
    con = connect(db_path)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    skips: list[str] = []
    repo_cache: dict[str, dict[str, Any]] = {}
    try:
        campaign_index, campaigns_seen = ingest_campaigns(
            con, A, swe_dir=swe, now=started
        )
        seen = 0
        for result in sorted(runs.glob("*/*/result.json")):
            run_dir = result.parent
            if wanted is not None and run_dir.name not in wanted:
                continue
            seen += 1
            disposition = ingest_row(
                con, A, run_dir,
                campaign_index=campaign_index, now=started, swe_dir=swe,
                harness_repo=harness, engine_repo=engine, repo_cache=repo_cache,
            )
            head, _, why = disposition.partition(":")
            counts[head] = counts.get(head, 0) + 1
            if head == "skipped":
                skips.append(f"{run_dir.parent.name}/{run_dir.name}: {why}")
        finished = _now()
        con.execute(
            "INSERT INTO ingest_log(started_at, finished_at, source_root, rows_seen, "
            "inserted, updated, unchanged, skipped, campaigns_seen, notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                started, finished, str(runs), seen, counts["inserted"],
                counts["updated"], counts["unchanged"], counts["skipped"],
                campaigns_seen, _jl(skips),
            ),
        )
        con.commit()
    finally:
        con.close()
    out = {
        "db": str(Path(db_path or DEFAULT_DB)),
        "runs_dir": str(runs),
        "rows_seen": seen,
        "campaigns": campaigns_seen,
        "skips": skips,
        **counts,
    }
    if not quiet:
        print(
            f"ingest -> {out['db']}\n"
            f"  rows seen   : {seen}\n"
            f"  inserted    : {counts['inserted']}\n"
            f"  updated     : {counts['updated']}\n"
            f"  unchanged   : {counts['unchanged']}\n"
            f"  skipped     : {counts['skipped']}\n"
            f"  campaigns   : {campaigns_seen}"
        )
        for s in skips:
            print(f"    skip {s}")
    return out


# --------------------------------------------------------------------------- #
# queries
# --------------------------------------------------------------------------- #


def _rows(con: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return list(con.execute(sql, args).fetchall())


def _table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    out.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        out.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)).rstrip())
    return "\n".join(out)


# The ONE predicate every published rate is taken over. Named once so no query
# can quietly use a different denominator than another.
REPORTABLE = "reportable = 1"


def q_rates(con: sqlite3.Connection, *, arm: str | None = None) -> list[dict[str, Any]]:
    """Resolve rate per arm per campaign — the "statistics over time" answer.

    Grouped by campaign, and every arm's row also carries its invalid count, so
    a rate can never be read without seeing how much was excluded to get it.
    Rows with no campaign (a hand-run ``run``, or a sweep whose summary was
    overwritten before ingest) are grouped under ``(no campaign)`` rather than
    dropped.

    Also grouped by ``manifest_sha256``. That is not cosmetic: the first report
    after a dataset switch blended a SWE-bench-Pro row set with a swe-rebench one
    into a single 100% headline. Two manifests are two benchmarks, and this
    grouping makes blending them impossible rather than merely discouraged.
    """
    sql = """
        SELECT
            a.arm                                        AS arm,
            COALESCE(a.manifest_sha256, '(none)')        AS manifest,
            COALESCE(a.campaign_id, '(no campaign)')     AS campaign,
            COALESCE(c.finished_at, MIN(a.ran_at), '')   AS at,
            c.workers                                    AS workers,
            SUM(a.reportable)                            AS reportable,
            SUM(CASE WHEN a.reportable=1 AND a.oracle_resolved=1 THEN 1 ELSE 0 END)
                                                         AS resolved,
            SUM(CASE WHEN a.reportable=0 THEN 1 ELSE 0 END) AS invalid,
            COUNT(*)                                     AS attempts,
            MAX(a.attempt)                               AS max_attempt,
            SUM(CASE WHEN a.reportable=1 THEN a.cost_usd ELSE 0 END) AS cost_usd,
            a.cost_source                                AS cost_source,
            SUM(a.is_chain)                              AS chain_rows
        FROM run_attempt a
        LEFT JOIN campaign c ON c.campaign_id = a.campaign_id
        WHERE (? IS NULL OR a.arm = ?)
        GROUP BY a.arm, manifest, campaign, a.cost_source
        ORDER BY at, a.arm
    """
    out = []
    for r in _rows(con, sql, (arm, arm)):
        d = dict(r)
        n, k = int(d["reportable"] or 0), int(d["resolved"] or 0)
        d["rate"] = (k / n) if n else None
        out.append(d)
    return out


def q_cost(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """$/instance and $/resolved per arm, per cost base.

    ``GROUP BY cost_source`` is not decoration. Azure price-table dollars and
    Claude-CLI-subscription dollars are different units; a single "$/resolved"
    across both would be arithmetic on incommensurable numbers. If an arm ever
    appears twice here, that is the store telling you its rows have two bases.
    """
    sql = f"""
        SELECT arm, cost_source,
               COALESCE(manifest_sha256, '(none)')              AS manifest,
               COUNT(*)                                        AS rows_counted,
               COUNT(DISTINCT instance_id)                      AS instances,
               SUM(oracle_resolved)                             AS resolved,
               SUM(cost_usd)                                    AS cost_usd,
               SUM(tokens_in)                                   AS tokens_in,
               SUM(cached_input_tokens)                         AS cache_read,
               SUM(tokens_out)                                  AS tokens_out,
               AVG(wall_clock_s)                                AS avg_wall_s
        FROM run_attempt
        WHERE {REPORTABLE}
        GROUP BY arm, cost_source, manifest
        ORDER BY arm
    """
    out = []
    for r in _rows(con, sql):
        d = dict(r)
        cost = float(d["cost_usd"] or 0.0)
        res = int(d["resolved"] or 0)
        n = int(d["rows_counted"] or 0)
        d["usd_per_attempt"] = (cost / n) if n else None
        d["usd_per_resolved"] = (cost / res) if res else None
        out.append(d)
    return out


def q_roles(con: sqlite3.Connection, *, arm: str | None = None) -> list[dict[str, Any]]:
    """Per-role cost breakdown — where a chain's dollars actually went."""
    sql = f"""
        SELECT a.arm, u.role, u.roster_model,
               COUNT(*)                 AS attempts,
               SUM(u.skipped)           AS skipped_rows,
               SUM(u.calls)             AS calls,
               SUM(u.input_tokens)      AS input_tokens,
               SUM(u.cache_read_tokens) AS cache_read,
               SUM(u.output_tokens)     AS output_tokens,
               SUM(u.cost_usd)          AS cost_usd,
               u.cost_source            AS cost_source
        FROM role_usage u JOIN run_attempt a ON a.attempt_uid = u.attempt_uid
        WHERE a.{REPORTABLE} AND (? IS NULL OR a.arm = ?)
        GROUP BY a.arm, u.role, u.roster_model, u.cost_source
        ORDER BY a.arm, cost_usd DESC
    """
    return [dict(r) for r in _rows(con, sql, (arm, arm))]


def q_validity(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Which rows are reportable and, for the rest, exactly why not."""
    sql = """
        SELECT instance_id, arm, attempt, reportable, invalid_reasons, status,
               audit_ok, oracle_resolved, outcome, provider_starved,
               budget_exhausted, termination, cost_usd, cost_source
        FROM run_attempt
        ORDER BY arm, instance_id, attempt
    """
    return [dict(r) for r in _rows(con, sql)]


def q_campaigns(con: sqlite3.Connection) -> list[dict[str, Any]]:
    sql = """
        SELECT c.campaign_id, c.arm, c.workers, c.finished_at, c.wall_clock_s,
               c.instances, c.cost_usd, c.cost_source, c.stopped_reason,
               COUNT(a.attempt_uid)     AS attempts_recorded,
               SUM(a.reportable)        AS reportable,
               SUM(CASE WHEN a.reportable=1 AND a.oracle_resolved=1 THEN 1 ELSE 0 END)
                                        AS resolved
        FROM campaign c LEFT JOIN run_attempt a ON a.campaign_id = c.campaign_id
        GROUP BY c.campaign_id
        ORDER BY c.finished_at
    """
    return [dict(r) for r in _rows(con, sql)]


def q_diff(con: sqlite3.Connection, a: str, b: str) -> dict[str, Any]:
    """Two campaigns, instance by instance. What moved, and what it cost.

    Only instances present in BOTH are compared for the delta — a rate move
    computed over different instance sets measures the instance set, which is
    the exact error ``test_cross_sweep_attribution.py`` exists to pin shut.
    """
    def load(cid: str) -> dict[str, sqlite3.Row]:
        rows = _rows(
            con,
            "SELECT * FROM run_attempt WHERE campaign_id=? ORDER BY instance_id",
            (cid,),
        )
        if not rows:
            raise SystemExit(
                f"no rows recorded for campaign {cid!r}. `campaigns` lists them."
            )
        return {str(r["instance_id"]): r for r in rows}

    ra, rb = load(a), load(b)
    common = sorted(set(ra) & set(rb))
    moves: list[dict[str, Any]] = []
    for iid in common:
        x, y = ra[iid], rb[iid]
        rx = None if x["reportable"] != 1 else bool(x["oracle_resolved"])
        ry = None if y["reportable"] != 1 else bool(y["oracle_resolved"])
        moves.append({
            "instance_id": iid,
            "a": "n/a" if rx is None else ("RESOLVED" if rx else "failed"),
            "b": "n/a" if ry is None else ("RESOLVED" if ry else "failed"),
            "move": ("gained" if (ry and not rx) else "lost" if (rx and not ry)
                     else "same" if rx == ry else "incomparable"),
            "a_outcome": x["outcome"], "b_outcome": y["outcome"],
            "a_cost": x["cost_usd"], "b_cost": y["cost_usd"],
            "a_attempt": x["attempt"], "b_attempt": y["attempt"],
        })
    return {
        "a": a, "b": b,
        "only_in_a": sorted(set(ra) - set(rb)),
        "only_in_b": sorted(set(rb) - set(ra)),
        "common": len(common),
        "gained": [m["instance_id"] for m in moves if m["move"] == "gained"],
        "lost": [m["instance_id"] for m in moves if m["move"] == "lost"],
        "incomparable": [m["instance_id"] for m in moves if m["move"] == "incomparable"],
        "rows": moves,
    }


def _one_attempt(
    con: sqlite3.Connection, instance_id: str, arm: str, attempt: int | None
) -> sqlite3.Row:
    if attempt is None:
        row = con.execute(
            "SELECT * FROM run_attempt WHERE instance_id=? AND arm=? "
            "ORDER BY attempt DESC LIMIT 1",
            (instance_id, arm),
        ).fetchone()
    else:
        row = con.execute(
            "SELECT * FROM run_attempt WHERE instance_id=? AND arm=? AND attempt=?",
            (instance_id, arm, attempt),
        ).fetchone()
    if row is None:
        raise SystemExit(
            f"no recorded attempt for instance={instance_id!r} arm={arm!r}"
            + (f" attempt={attempt}" if attempt is not None else "")
        )
    return row


def q_show(
    con: sqlite3.Connection, instance_id: str, arm: str, attempt: int | None = None
) -> dict[str, Any]:
    """Everything needed to reconstruct one attempt's configuration."""
    row = _one_attempt(con, instance_id, arm, attempt)
    uid = int(row["attempt_uid"])
    prov = con.execute(
        "SELECT * FROM provenance WHERE attempt_uid=?", (uid,)
    ).fetchone()
    return {
        "attempt": dict(row),
        "provenance": dict(prov) if prov else {},
        "roles": [dict(r) for r in _rows(
            con, "SELECT * FROM role_usage WHERE attempt_uid=? ORDER BY role", (uid,)
        )],
        "artifacts": [dict(r) for r in _rows(
            con, "SELECT * FROM artifact WHERE attempt_uid=? ORDER BY path", (uid,)
        )],
        "rates": [dict(r) for r in _rows(
            con, "SELECT * FROM price_rate WHERE attempt_uid=? ORDER BY model", (uid,)
        )],
        "history": [dict(r) for r in _rows(
            con,
            "SELECT attempt, ran_at, status, outcome, oracle_resolved, cost_usd, "
            "reportable FROM run_attempt WHERE instance_id=? AND arm=? "
            "ORDER BY attempt",
            (instance_id, arm),
        )],
    }


def q_replay(
    con: sqlite3.Connection, instance_id: str, arm: str, attempt: int | None = None
) -> dict[str, Any]:
    """The exact command + config needed to re-run one attempt.

    Unambiguous rather than executable, deliberately. Executing a replay would
    SPEND, and it would also have to reconstitute a specific engine checkout; a
    record that hands the operator the sha, the roster bytes and the command
    leaves the spend decision where it belongs. ``caveats`` is not a disclaimer:
    it is the list of reasons this replay would NOT be bit-exact, and an empty
    list is the only claim of exactness this store ever makes.
    """
    row = _one_attempt(con, instance_id, arm, attempt)
    uid = int(row["attempt_uid"])
    prov = con.execute("SELECT * FROM provenance WHERE attempt_uid=?", (uid,)).fetchone()
    p = dict(prov) if prov else {}
    return {
        "instance_id": instance_id,
        "arm": arm,
        "attempt": int(row["attempt"]),
        "command": p.get("replay_command"),
        "workers": p.get("workers"),
        "workers_source": p.get("workers_source"),
        "max_steps": p.get("max_steps"),
        "step_unit": p.get("step_unit"),
        "caps": json.loads(p["caps_json"]) if p.get("caps_json") else None,
        "manifest_sha256": p.get("manifest_sha256"),
        "manifest_sha256_at_ingest": p.get("manifest_sha256_at_ingest"),
        "base_commit": p.get("base_commit"),
        "problem_statement_sha256": p.get("problem_statement_sha256"),
        "roster_yaml": p.get("roster_yaml"),
        "roster_yaml_sha256": p.get("roster_yaml_sha256"),
        "roster_sha256_recorded": p.get("roster_sha256_recorded"),
        "skip_phases": json.loads(p["skip_phases"]) if p.get("skip_phases") else None,
        "thinking": p.get("thinking"),
        "engine_path": p.get("engine_path"),
        "harness_repo": p.get("harness_repo"),
        "harness_git_sha": p.get("harness_git_sha"),
        "harness_git_dirty": p.get("harness_git_dirty"),
        "engine_repo": p.get("engine_repo"),
        "engine_git_sha": p.get("engine_git_sha"),
        "engine_git_dirty": p.get("engine_git_dirty"),
        "git_sha_source": p.get("git_sha_source"),
        "price_table_sha256": p.get("price_table_sha256"),
        "price_table_matches_pinned": p.get("price_table_matches_pinned"),
        "arm_spec": json.loads(p["arm_spec_json"]) if p.get("arm_spec_json") else None,
        "arm_spec_source": p.get("arm_spec_source"),
        "reproducible": bool(p.get("reproducible")),
        "caveats": json.loads(p.get("reproducibility_caveats") or "[]"),
    }


def q_verify(con: sqlite3.Connection) -> dict[str, Any]:
    """Re-hash every artifact still on disk against what was recorded.

    Three outcomes, and the middle one is the important one. ``ok`` — the bytes
    are unchanged. ``gone`` — the file is no longer on disk, which is EXPECTED
    for a superseded attempt and is why the store exists. ``MISMATCH`` — the
    file is there and its digest changed, i.e. evidence was altered after the
    fact. Only the third is a problem, and without a recorded digest it would be
    invisible.
    """
    ok = gone = mismatch = 0
    problems: list[str] = []
    sql = """
        SELECT a.attempt_uid, a.path, a.sha256, r.source_dir, r.instance_id,
               r.arm, r.attempt
        FROM artifact a JOIN run_attempt r ON r.attempt_uid = a.attempt_uid
        WHERE a.sha256 IS NOT NULL
        ORDER BY r.instance_id, r.arm, r.attempt, a.path
    """
    for r in _rows(con, sql):
        path = Path(r["source_dir"]) / r["path"]
        if not path.is_file():
            gone += 1
            continue
        digest, _size, err = _sha256_file(path)
        if err is not None or digest != r["sha256"]:
            mismatch += 1
            problems.append(
                f"{r['instance_id']}/{r['arm']}#{r['attempt']} {r['path']}: "
                f"recorded {r['sha256'][:12]} found {(digest or 'unreadable')[:12]}"
            )
        else:
            ok += 1
    return {"ok": ok, "gone": gone, "mismatch": mismatch, "problems": problems}


def q_export(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """A deterministic, text-diffable mirror of the store: one object per attempt.

    Why it exists: the db is a binary, and a binary is a poor durable record in
    git. This is the committable projection. ``answer_key`` artifacts appear as
    path+digest only — their CONTENT is never emitted, because committing the
    hidden test ids would put the answer key in the repo for every later arm to
    read (the adapter refuses the same thing in ``_row_diagnostic_files``).
    """
    out: list[dict[str, Any]] = []
    for row in _rows(con, "SELECT * FROM run_attempt ORDER BY instance_id, arm, attempt"):
        uid = int(row["attempt_uid"])
        d = {k: row[k] for k in row.keys() if k != "attempt_uid"}
        prov = con.execute(
            "SELECT * FROM provenance WHERE attempt_uid=?", (uid,)
        ).fetchone()
        d["provenance"] = (
            {k: prov[k] for k in prov.keys() if k != "attempt_uid"} if prov else {}
        )
        d["roles"] = [
            {k: r[k] for k in r.keys() if k != "attempt_uid"}
            for r in _rows(con, "SELECT * FROM role_usage WHERE attempt_uid=? "
                                "ORDER BY role", (uid,))
        ]
        d["artifacts"] = [
            {"path": r["path"], "kind": r["kind"], "size_bytes": r["size_bytes"],
             "sha256": r["sha256"], "answer_key": r["answer_key"]}
            for r in _rows(con, "SELECT * FROM artifact WHERE attempt_uid=? "
                                "ORDER BY path", (uid,))
        ]
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


def _pct(rate: float | None) -> str:
    return "n/a" if rate is None else f"{100 * rate:.0f}%"


def _usd(v: Any) -> str:
    return "—" if v is None else f"${float(v):,.2f}"


def render_rates(rows: list[dict[str, Any]]) -> str:
    body = [
        [
            str(r["arm"]), str(r["manifest"]), str(r["campaign"]), str(r["at"])[:19],
            "—" if r["workers"] is None else str(r["workers"]),
            f"{int(r['resolved'] or 0)}/{int(r['reportable'] or 0)}",
            _pct(r["rate"]), str(int(r["invalid"] or 0)), str(int(r["attempts"] or 0)),
            str(int(r["max_attempt"] or 0)), _usd(r["cost_usd"]), str(r["cost_source"]),
        ]
        for r in rows
    ]
    return (
        _table(
            ["arm", "manifest", "campaign", "finished", "wkrs", "resolved", "rate",
             "invalid", "attempts", "max_att", "cost", "cost_source"],
            body,
        )
        + "\n\nNOTE: rows are grouped by manifest — two manifests are two "
          "benchmarks and their rates are NOT comparable. `resolved`/`rate` are "
          "over REPORTABLE rows only; `invalid` is what was excluded to get them "
          "(`validity` says why, row by row)."
    )


def render_cost(rows: list[dict[str, Any]]) -> str:
    body = [
        [
            str(r["arm"]), str(r["manifest"]), str(r["cost_source"]),
            str(int(r["instances"] or 0)),
            str(int(r["rows_counted"] or 0)), str(int(r["resolved"] or 0)),
            _usd(r["cost_usd"]), _usd(r["usd_per_attempt"]),
            _usd(r["usd_per_resolved"]),
            "—" if r["avg_wall_s"] is None else f"{float(r['avg_wall_s']):.0f}s",
        ]
        for r in rows
    ]
    return (
        _table(
            ["arm", "manifest", "cost_source", "instances", "rows", "resolved",
             "total", "$/attempt", "$/resolved", "avg_wall"],
            body,
        )
        + "\n\nNOTE: rows are grouped by cost_source and MUST NOT be summed across "
          "it — price-table dollars and CLI-subscription dollars are different "
          "units. Grouped by manifest for the same reason: two manifests are two "
          "benchmarks."
    )


def render_roles(rows: list[dict[str, Any]]) -> str:
    body = [
        [
            str(r["arm"]), str(r["role"]), str(r["roster_model"] or "—"),
            str(int(r["attempts"] or 0)), str(int(r["skipped_rows"] or 0)),
            str(int(r["calls"] or 0)), f"{int(r['input_tokens'] or 0):,}",
            f"{int(r['cache_read'] or 0):,}", f"{int(r['output_tokens'] or 0):,}",
            _usd(r["cost_usd"]), str(r["cost_source"]),
        ]
        for r in rows
    ]
    return _table(
        ["arm", "role", "roster_model", "attempts", "skipped", "calls", "in",
         "cache_read", "out", "cost", "cost_source"],
        body,
    )


def render_validity(rows: list[dict[str, Any]]) -> str:
    good = [r for r in rows if r["reportable"]]
    bad = [r for r in rows if not r["reportable"]]
    lines = [f"REPORTABLE: {len(good)}    INVALID: {len(bad)}", ""]
    lines.append(_table(
        ["instance", "arm", "att", "resolved", "outcome", "cost"],
        [
            [str(r["instance_id"])[:46], str(r["arm"]), str(r["attempt"]),
             "RESOLVED" if r["oracle_resolved"] else "failed",
             str(r["outcome"] or "—"), _usd(r["cost_usd"])]
            for r in good
        ],
    ))
    if bad:
        lines += ["", "INVALID rows — NOT capability data, and why:"]
        for r in bad:
            why = "; ".join(json.loads(r["invalid_reasons"] or "[]")) or "unknown"
            lines.append(
                f"  {str(r['instance_id'])[:46]:<46} {r['arm']:<12} "
                f"#{r['attempt']}  {why}"
            )
    return "\n".join(lines)


def render_campaigns(rows: list[dict[str, Any]]) -> str:
    return _table(
        ["campaign_id", "arm", "wkrs", "instances", "recorded", "reportable",
         "resolved", "cost", "wall", "stopped"],
        [
            [
                str(r["campaign_id"]), str(r["arm"]),
                "—" if r["workers"] is None else str(r["workers"]),
                str(r["instances"] or 0), str(r["attempts_recorded"] or 0),
                str(int(r["reportable"] or 0)), str(int(r["resolved"] or 0)),
                _usd(r["cost_usd"]),
                "—" if r["wall_clock_s"] is None else f"{float(r['wall_clock_s']):.0f}s",
                str(r["stopped_reason"] or "—"),
            ]
            for r in rows
        ],
    )


def render_diff(d: dict[str, Any]) -> str:
    lines = [
        f"A: {d['a']}",
        f"B: {d['b']}",
        f"instances in both: {d['common']}   only in A: {len(d['only_in_a'])}   "
        f"only in B: {len(d['only_in_b'])}",
        f"gained: {len(d['gained'])} {d['gained']}",
        f"lost  : {len(d['lost'])} {d['lost']}",
        f"incomparable (one side invalid): {len(d['incomparable'])} {d['incomparable']}",
        "",
    ]
    lines.append(_table(
        ["instance", "A", "B", "move", "A outcome", "B outcome", "A $", "B $"],
        [
            [str(m["instance_id"])[:46], m["a"], m["b"], m["move"],
             str(m["a_outcome"] or "—"), str(m["b_outcome"] or "—"),
             _usd(m["a_cost"]), _usd(m["b_cost"])]
            for m in d["rows"]
        ],
    ))
    if d["only_in_a"] or d["only_in_b"]:
        lines += [
            "",
            "NOTE: the gained/lost counts are over the INSTANCES PRESENT IN BOTH "
            "only. A rate difference computed over different instance sets "
            "measures the instance set.",
        ]
    return "\n".join(lines)


def render_show(d: dict[str, Any]) -> str:
    a, p = d["attempt"], d["provenance"]
    lines = [
        f"{a['instance_id']}  arm={a['arm']}  attempt={a['attempt']}  "
        f"ran_at={a['ran_at']}",
        f"  campaign      : {a['campaign_id'] or '(none recorded)'}",
        f"  composition   : {'CHAIN' if a['is_chain'] else 'SOLO'} "
        f"({a['roster_role_count'] or '?'} active role(s)), harness_id="
        f"{a['harness_id']}, roster={a['roster_json'] or '(not an sssf arm)'}",
        f"  roles run     : {a['roles_run'] or '—'}   skipped: {a['roles_skipped'] or '—'}",
        f"  models used   : {a['models_used'] or '—'}  ({a['model_calls'] or 0} call(s))",
        f"  measurement   : {_usd(a['cost_usd'])} [{a['cost_source']}], "
        f"in={a['tokens_in'] or 0:,} cache_read={a['cached_input_tokens'] or 0:,} "
        f"out={a['tokens_out'] or 0:,}, {a['wall_clock_s'] or 0:.0f}s, "
        f"{a['steps_used'] or 0}/{a['step_cap'] or 0} {a['step_unit'] or 'steps'}",
        f"  cross-checks  : events={_usd(a['cost_usd_events'])} "
        f"shared_db={_usd(a['cost_usd_shared_db'])} "
        f"rederived={_usd(a['cost_usd_rederived'])}",
        f"  verdict       : oracle_resolved={a['oracle_resolved']} "
        f"outcome={a['outcome']}  harness claimed green={a['factory_says_green']} "
        f"({a['green_state']})",
        f"  validity      : reportable={bool(a['reportable'])} status={a['status']} "
        f"audit_ok={a['audit_ok']} termination={a['termination']}",
    ]
    reasons = json.loads(a["invalid_reasons"] or "[]")
    for r in reasons:
        lines.append(f"                  - {r}")
    lines += [
        "",
        "PROVENANCE",
        f"  manifest      : {p.get('manifest_sha256')} "
        f"(now on disk: {p.get('manifest_sha256_at_ingest')})",
        f"  task          : base_commit={p.get('base_commit')} "
        f"statement={str(p.get('problem_statement_sha256'))[:16]}…",
        f"  harness repo  : {p.get('harness_repo')} @ {p.get('harness_git_sha')} "
        f"dirty={bool(p.get('harness_git_dirty'))}",
        f"  engine repo   : {p.get('engine_repo')} @ {p.get('engine_git_sha')} "
        f"dirty={bool(p.get('engine_git_dirty'))}  [{p.get('git_sha_source')}]",
        f"  price table   : {p.get('price_table_path')} @ "
        f"{str(p.get('price_table_sha256'))[:16]}… "
        f"matches_pinned={p.get('price_table_matches_pinned')}",
        f"  caps          : {p.get('caps_json')}",
        f"  workers       : {p.get('workers')} ({p.get('workers_source')})",
        f"  reproducible  : {bool(p.get('reproducible'))}",
    ]
    for c in json.loads(p.get("reproducibility_caveats") or "[]"):
        lines.append(f"                  - {c}")
    lines += ["", "RATES IN FORCE"]
    for r in d["rates"]:
        lines.append(
            f"  {r['model']:<28} in={r['input_per_unit']} out={r['output_per_unit']} "
            f"cache_read={r['cache_read_per_unit']} ({r['units']})"
        )
    lines += ["", "PER-ROLE"]
    for r in d["roles"]:
        lines.append(
            f"  {r['role']:<12} model={r['roster_model'] or '—':<26} "
            f"{_usd(r['cost_usd'])} calls={r['calls'] or 0} "
            f"in={r['input_tokens'] or 0:,} out={r['output_tokens'] or 0:,}"
            + ("  [SKIPPED]" if r["skipped"] else "")
        )
    lines += ["", f"ARTIFACTS ({len(d['artifacts'])})"]
    for r in d["artifacts"]:
        lines.append(
            f"  {r['kind']:<11} {str(r['sha256'])[:16]}… "
            f"{(r['size_bytes'] or 0):>10,}  {r['path']}"
            + ("   [ANSWER KEY — digest only]" if r["answer_key"] else "")
        )
    lines += ["", "ATTEMPT HISTORY for this cell"]
    for r in d["history"]:
        lines.append(
            f"  #{r['attempt']}  {str(r['ran_at'])[:19]}  {r['status']:<17} "
            f"{str(r['outcome'] or '—'):<24} resolved={r['oracle_resolved']} "
            f"{_usd(r['cost_usd'])} reportable={bool(r['reportable'])}"
        )
    return "\n".join(lines)


def render_replay(d: dict[str, Any]) -> str:
    lines = [
        "# REPLAY RECORD — "
        f"{d['instance_id']} / arm={d['arm']} / attempt={d['attempt']}",
        "#",
        "# Run this from /home/k/software-factory. It COSTS MONEY: check the caps",
        "# below first, and note that a re-run overwrites this cell's artifacts on",
        "# disk (the record in benchmarks.db survives — that is its job).",
        "",
        "## 1. the code",
        f"harness  : {d['harness_repo']} @ {d['harness_git_sha']}"
        + ("   *** DIRTY at capture — not reproducible ***" if d["harness_git_dirty"] else ""),
        f"engine   : {d['engine_repo']} @ {d['engine_git_sha']}"
        + ("   *** DIRTY at capture — not reproducible ***" if d["engine_git_dirty"] else ""),
        f"sha source: {d['git_sha_source']}",
        f"  git -C {d['harness_repo']} checkout {d['harness_git_sha']}",
        f"  git -C {d['engine_repo']} checkout {d['engine_git_sha']}",
        "",
        "## 2. the task, pinned",
        f"manifest_sha256          : {d['manifest_sha256']}",
        f"manifest now on disk     : {d['manifest_sha256_at_ingest']}",
        f"base_commit              : {d['base_commit']}",
        f"problem_statement_sha256 : {d['problem_statement_sha256']}",
        "",
        "## 3. the configuration",
        f"arm            : {d['arm']}  ({d['arm_spec_source']})",
        f"max_steps      : {d['max_steps']} {d['step_unit'] or ''}",
        f"workers        : {d['workers']}  ({d['workers_source']})",
        f"thinking       : {d['thinking']}",
        f"skip_phases    : {d['skip_phases']}",
        f"engine entry   : {d['engine_path']}",
        f"caps           : {json.dumps(d['caps'])}",
        f"price table    : {d['price_table_sha256']} "
        f"(matches_pinned={d['price_table_matches_pinned']})",
        f"arm registry   : {json.dumps(d['arm_spec'])}",
        "",
        "## 4. the command",
        str(d["command"]),
        "",
        "## 5. the roster, VERBATIM",
        f"# sha256 of the bytes below : {d['roster_yaml_sha256']}",
        f"# sha256 the row recorded    : {d['roster_sha256_recorded']}",
        "# AGREE: " + (
            "yes — the bytes below are the exact roster the row claims it ran"
            if (d["roster_yaml_sha256"]
                and d["roster_yaml_sha256"] == d["roster_sha256_recorded"])
            else "NO — the roster on disk is not the one the row recorded. Replaying "
                 "the bytes below would run a DIFFERENT configuration; treat this "
                 "attempt's model attribution as unverified."
            if (d["roster_yaml_sha256"] and d["roster_sha256_recorded"])
            else "n/a — one side is absent (not an sssf arm, or no roster on disk)"
        ),
        "",
        str(d["roster_yaml"] or "# (no roster on disk for this arm)"),
        "",
        "## 6. is this replay exact?",
        f"reproducible: {d['reproducible']}",
    ]
    if d["caveats"]:
        lines.append("caveats — each one is a reason the replay is NOT bit-exact:")
        lines += [f"  - {c}" for c in d["caveats"]]
    else:
        lines.append("no caveats recorded: every input above was pinned at capture.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="benchmark_store.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", default=None, help=f"store path (default {DEFAULT_DB})")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest", help="snapshot on-disk rows into the store (idempotent)")
    p.add_argument(
        "--runs-dir",
        default=None,
        help="where the <instance>/<arm>/result.json rows are; defaults to "
             "bench/swebench/runs. A results-archive/<ts>/ dir has the same "
             "layout and can be ingested the same way.",
    )
    p.add_argument("--arm", action="append", default=None, help="restrict to arm(s)")

    sub.add_parser("rates", help="resolve rate per arm per campaign, over time") \
       .add_argument("--arm", default=None)
    sub.add_parser("cost", help="$/instance and $/resolved per arm, per cost base")
    sub.add_parser("roles", help="per-role cost breakdown") \
       .add_argument("--arm", default=None)
    sub.add_parser("validity", help="which rows are reportable, and why the rest are not")
    sub.add_parser("campaigns", help="every recorded sweep")

    p = sub.add_parser("diff", help="compare two campaigns instance by instance")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)

    for name, helptext in (
        ("show", "everything needed to reconstruct one attempt's config"),
        ("replay", "the exact command + config needed to re-run one attempt"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--instance", required=True)
        p.add_argument("--arm", required=True)
        p.add_argument("--attempt", type=int, default=None,
                       help="default: the latest recorded attempt")

    sub.add_parser("verify", help="re-hash on-disk artifacts against the record")
    sub.add_parser("export", help="deterministic JSONL mirror of the store") \
       .add_argument("--out", default=None, help="file to write; default stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = Path(args.db) if args.db else None

    if args.cmd == "ingest":
        out = ingest(
            db_path=db,
            runs_dir=Path(args.runs_dir) if args.runs_dir else None,
            arms=args.arm,
            quiet=args.json,
        )
        if args.json:
            print(json.dumps(out, indent=2))
        return 0

    con = connect(db)
    try:
        if args.cmd == "rates":
            data: Any = q_rates(con, arm=args.arm)
            text = render_rates(data)
        elif args.cmd == "cost":
            data = q_cost(con)
            text = render_cost(data)
        elif args.cmd == "roles":
            data = q_roles(con, arm=args.arm)
            text = render_roles(data)
        elif args.cmd == "validity":
            data = q_validity(con)
            text = render_validity(data)
        elif args.cmd == "campaigns":
            data = q_campaigns(con)
            text = render_campaigns(data)
        elif args.cmd == "diff":
            data = q_diff(con, args.a, args.b)
            text = render_diff(data)
        elif args.cmd == "show":
            data = q_show(con, args.instance, args.arm, args.attempt)
            text = render_show(data)
        elif args.cmd == "replay":
            data = q_replay(con, args.instance, args.arm, args.attempt)
            text = render_replay(data)
        elif args.cmd == "verify":
            data = q_verify(con)
            text = (
                f"artifacts verified: {data['ok']} ok, {data['gone']} gone "
                f"(expected for superseded attempts), {data['mismatch']} MISMATCH"
            )
            for p in data["problems"]:
                text += f"\n  MISMATCH {p}"
        elif args.cmd == "export":
            data = q_export(con)
            body = "\n".join(
                json.dumps(r, sort_keys=True, ensure_ascii=False) for r in data
            )
            if args.out:
                Path(args.out).write_text(body + "\n", encoding="utf-8")
                print(f"wrote {len(data)} record(s) to {args.out}")
                return 0
            text = body
        else:  # pragma: no cover - argparse enforces the choices
            raise SystemExit(f"unknown command {args.cmd!r}")
        print(json.dumps(data, indent=2, default=str) if args.json else text)
        if args.cmd == "verify" and data["mismatch"]:
            return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
