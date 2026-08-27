#!/usr/bin/env python3
"""Phase 0 tooling for ``frozen/PRE-REGISTRATION-SAIL-AB.md``. ALL $0. NO MODEL CALLS.

Every subcommand here implements one SCRIPTABLE item of the pre-registration's
"Harness-correctness protocol — Phase 0" section and prints PASS/FAIL plus
what it checked, so a campaign operator (or CI) gets a machine-checkable
answer instead of having to re-read the prose checklist by hand before every
paid call. Nothing here spends a cent: every subcommand either reads files
already on disk, reads environment variables already in this process, or
drives the adapter's OWN ``_sandbox_argv``/``_sandbox_probe`` primitives with
``/bin/true``-shaped payloads.

Subcommands, one per Phase 0 item:

  p0_6-isolation          P0.6  provider-isolation preflight, checkable half
  p0_7-keyscan PATHS...   P0.7  key-hygiene scan (counts only, never content)
  p0_4-stage / -unstage   P0.4  detector regression: reconstruct/remove the
                                 real historical contamination under live runs/
  p0_5b-stage / -unstage  P0.5b detector proof: synthesize a foreign-workdir
                                 leak into a copied real trace
  p0_5a-plant/-check/-clean
                          P0.5a sandbox proof: a literal /tmp marker must be
                                 invisible from inside SWEBENCH_SANDBOX=1

Run from the ``software-factory`` repo root, e.g.::

    uv run python bench/swebench/phase0_sail_ab.py p0_6-isolation

Every subcommand's own ``--help`` documents its specific mechanics and, where
the pre-registration's prose describes something this harness does not
actually implement the way the prose assumes, the docstring says so — see
``p0_5a-check`` and ``p0_4-stage`` in particular.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SWE_DIR = _REPO_ROOT / "bench" / "swebench"
_ADAPTER_PATH = _REPO_ROOT / "bench" / "swebench_adapter.py"
_MODELS_JSON = Path.home() / ".pi" / "agent" / "models.json"
_RUNS_DIR = _SWE_DIR / "runs"
# Staging backups NEVER live under runs/ — record()/ingest glob `runs/*/*/
# result.json` recursively and a backup dir sitting beside a staged one would
# be one accidental deletion away from being mistaken for a live row.
_PHASE0_BACKUPS_DIR = _SWE_DIR / ".phase0-backups"

_AZURE_KEY_VAR = "AZURE_API_KEY"
_SAIL_KEY_VAR = "SAIL_RESEARCH_KEY"
_PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
               "http_proxy", "https_proxy", "all_proxy", "no_proxy")

_TMP_MARKER_PATH = Path("/tmp/report.json")
_TMP_MARKER_SENTINEL = "PHASE0-P0-5A-SANDBOX-PROBE"

_P0_4_INSTANCE = "harumiweb__exstruct-113"
_P0_4_ARM = "flash-chain"
_P0_4_STAGE_MARKER = ".phase0-p0_4-staged.json"
_P0_5B_STAGE_MARKER = ".phase0-p0_5b-staged.json"

# THE REAL CELLS, not a placeholder. `benchmarks.db` holds the historical row
# verbatim — (harumiweb__exstruct-113, flash-chain, attempt 2) — with its
# recorded audit finding: `audit failed: foreign-workdir:
# sssf-events.jsonl:152 named another arm's working tree
# ['harumiweb__exstruct-113__v32-solo', 'harumiweb__exstruct-113__bare']`,
# plus artifact digests (sssf-events.jsonl 786,524 B,
# sha256 a2dccb282fd9…; audit.json 2,421 B). The BYTES are gone — attempt 3
# overwrote them on disk before this task started (`runs/` is gitignored, so
# there is no history to recover them from either) — but the INCIDENT was
# real, and it IS the foreign-workdir detector: the exstruct `.pth` leak
# (adapter comment ~13084-13102) is why an agent's own tooling landed reads
# in exactly these two other arms' trees for this instance. See
# SAIL-DISCOVERY.md for the full reconstruction rationale.
_P0_4_FOREIGN_CELLS = (
    "harumiweb__exstruct-113__v32-solo",
    "harumiweb__exstruct-113__bare",
)


def _adapter() -> Any:
    """Import ``bench/swebench_adapter.py`` as a module, once per process.

    Same technique ``tests/test_swebench_sandbox_isolation.py`` uses: the
    adapter is a script, not a package, so it has to be loaded by path.
    """
    name = "_phase0_sail_ab_adapter"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _ADAPTER_PATH)
    assert spec and spec.loader, f"cannot load {_ADAPTER_PATH}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _pass(check: str, detail: str = "") -> bool:
    print(f"PASS: {check}" + (f" — {detail}" if detail else ""))
    return True


def _fail(check: str, detail: str = "") -> bool:
    print(f"FAIL: {check}" + (f" — {detail}" if detail else ""))
    return False


# --------------------------------------------------------------------------- #
# P0.6 — provider-isolation preflight, the checkable half
# --------------------------------------------------------------------------- #


def cmd_p0_6_isolation(_args: argparse.Namespace) -> int:
    """Everything P0.6 says a $0 script CAN check. See the pre-registration's

    P0.6 item for the full text and for what is explicitly NOT checkable here
    (``_sssf_child_env`` copies the FULL parent env, so both provider keys
    reach both arms' children regardless of what this script finds — that
    residual risk is disclosed in the pre-registration's Threats section and
    backstopped by P0.7's scan, not fixed by this check).
    """
    ok = True

    azure_val = os.environ.get(_AZURE_KEY_VAR, "")
    sail_val = os.environ.get(_SAIL_KEY_VAR, "")
    if not azure_val:
        ok = _fail(f"{_AZURE_KEY_VAR} present", "not set in this process's environment") and ok
    else:
        ok = _pass(f"{_AZURE_KEY_VAR} present", f"{len(azure_val)} chars") and ok
    if not sail_val:
        ok = _fail(f"{_SAIL_KEY_VAR} present", "not set in this process's environment") and ok
    else:
        ok = _pass(f"{_SAIL_KEY_VAR} present", f"{len(sail_val)} chars") and ok
    if azure_val and sail_val:
        if azure_val == sail_val:
            ok = _fail(
                "the two key values differ",
                "AZURE_API_KEY and SAIL_RESEARCH_KEY hold the IDENTICAL value — "
                "either one var is aliased to the other, or a key was pasted "
                "into the wrong .env entry",
            ) and ok
        else:
            ok = _pass("the two key values differ") and ok

    # models.json routing: each provider's declared `apiKey` must name the
    # right env var. Read the LIVE file, not an assumption — this is exactly
    # the class of drift P-2b's own comment warns about.
    try:
        table = json.loads(_MODELS_JSON.read_bytes())
    except OSError as exc:
        return int(not _fail(f"{_MODELS_JSON} readable", str(exc)))
    except json.JSONDecodeError as exc:
        return int(not _fail(f"{_MODELS_JSON} is valid JSON", str(exc)))
    providers = table.get("providers") or {}
    base_urls: dict[str, str] = {}
    for name, cfg in providers.items():
        if not isinstance(cfg, dict):
            continue
        base_urls[name] = str(cfg.get("baseUrl") or "")
        wanted = _AZURE_KEY_VAR if name.startswith("azure") else (
            _SAIL_KEY_VAR if name == "sail" else None
        )
        if wanted is None:
            print(f"  (skip) provider {name!r}: no routing rule declared for it here")
            continue
        got = str(cfg.get("apiKey") or "")
        if got == wanted:
            ok = _pass(f"models.json routes {name!r} -> {wanted}") and ok
        else:
            ok = _fail(
                f"models.json routes {name!r} -> {wanted}",
                f"declares apiKey={got!r} instead",
            ) and ok

    azure_url = base_urls.get("azure", "")
    sail_url = base_urls.get("sail", "")
    if azure_url and sail_url and azure_url != sail_url:
        ok = _pass("azure and sail baseUrls differ", f"{azure_url!r} != {sail_url!r}") and ok
    else:
        ok = _fail(
            "azure and sail baseUrls differ",
            f"azure={azure_url!r} sail={sail_url!r}",
        ) and ok

    # NAMES ONLY, never values: `HTTP_PROXY=http://user:pass@host` is a live
    # credential, and a check that leaks one secret while hunting for another
    # is not a check this campaign can run.
    found_proxy_vars = [var for var in _PROXY_VARS if os.environ.get(var)]
    if found_proxy_vars:
        ok = _fail(
            "no HTTP(S)_PROXY / ALL_PROXY / NO_PROXY set (any case)",
            f"set: {found_proxy_vars} (names only, values withheld)",
        ) and ok
    else:
        ok = _pass("no HTTP(S)_PROXY / ALL_PROXY / NO_PROXY set (any case)") and ok

    # The runtime closures carried over from E5: re-asserted against the REAL
    # function rather than re-implemented here, so a future edit to
    # `_sssf_child_env` cannot drift silently out of sync with this check.
    A = _adapter()
    child_env, problem = A._sssf_child_env()
    if problem:
        ok = _fail("_sssf_child_env reports no credential problem", problem) and ok
    else:
        ok = _pass("_sssf_child_env reports no credential problem") and ok
    if child_env.get("PYTHONNOUSERSITE") == "1":
        ok = _pass("_sssf_child_env sets PYTHONNOUSERSITE=1") and ok
    else:
        ok = _fail("_sssf_child_env sets PYTHONNOUSERSITE=1", repr(child_env.get("PYTHONNOUSERSITE"))) and ok
    venv_entries = [
        e for e in child_env.get("PATH", "").split(os.pathsep)
        if e.rstrip("/").endswith("/.venv/bin")
    ]
    if venv_entries:
        ok = _fail("_sssf_child_env strips */.venv/bin from PATH", f"still present: {venv_entries}") and ok
    else:
        ok = _pass("_sssf_child_env strips */.venv/bin from PATH") and ok

    # Per-run TMPDIR and fresh-workdir-per-attempt are RUNTIME behaviours of
    # `run_sssf`, not static config — nothing to read from an env var or a
    # json file. Asserted structurally against the adapter's OWN SOURCE
    # instead (the same technique `tests/test_swebench_sandbox_isolation.py`
    # uses for `run_sssf`'s sandbox wiring), so this stays a $0 check.
    source = _ADAPTER_PATH.read_text(encoding="utf-8")
    try:
        run_sssf_body = source.split("def run_sssf(")[1].split("\ndef ")[0]
    except IndexError:
        run_sssf_body = ""
    if "_work_dir(instance_id, arm, fresh=True)" in run_sssf_body:
        ok = _pass("run_sssf requests a FRESH work dir per attempt (fresh=True)") and ok
    else:
        ok = _fail("run_sssf requests a FRESH work dir per attempt (fresh=True)") and ok
    if '("TMPDIR", "TEMP", "TMP")' in run_sssf_body and "child_env[var] = str(tmp)" in run_sssf_body:
        ok = _pass("run_sssf sets a per-run TMPDIR/TEMP/TMP") and ok
    else:
        ok = _fail("run_sssf sets a per-run TMPDIR/TEMP/TMP") and ok

    print()
    print("PASS: p0_6-isolation" if ok else "FAIL: p0_6-isolation (see failing check(s) above)")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# P0.7 — key-hygiene scan
# --------------------------------------------------------------------------- #


def cmd_p0_7_keyscan(args: argparse.Namespace) -> int:
    """Grep PATHS for the literal Sail/Azure key VALUES. Reports counts only.

    The values are read from the environment at call time and never written
    anywhere — not to argv (this process's own argv never contains them), not
    to a log line, not into the hit report. A hit prints ``path:line`` and
    nothing else; the matched text itself is never echoed.

    FAIL CLOSED on a partial scan. A campaign's R7 (key hygiene) is "zero
    hits for BOTH keys" — a scan that silently ran over only one of them
    because the other var happened to be unset in this shell would report a
    green R7 that never looked for half the leak.

    Streamed line-by-line, never slurped whole: an archived pi raw-output
    stream can be multiple GB (one measured at 7.0 GB), and
    ``Path.read_text()`` over that is an OOM waiting to happen, not a scan.
    A file this process cannot even OPEN is reported as a FAIL, not silently
    skipped — ``except OSError: continue`` previously reported an unreadable
    file as clean, which is the wrong direction for a hygiene gate to fail in.
    """
    needles: dict[str, str] = {}
    for label, var in ((_SAIL_KEY_VAR, _SAIL_KEY_VAR), (_AZURE_KEY_VAR, _AZURE_KEY_VAR)):
        val = os.environ.get(var, "")
        if val:
            needles[label] = val
        else:
            print(f"  (skip) {var} not set in this process — cannot scan for it")
    if len(needles) < 2:
        return int(not _fail(
            "both key values available to scan for",
            "P0.7 requires the Sail AND Azure values; a partial scan cannot "
            "return a green R7",
        ))

    targets: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            targets.extend(f for f in p.rglob("*") if f.is_file())
        elif p.is_file():
            targets.append(p)
        else:
            print(f"  (skip) {raw}: not a file or directory")

    hits: list[str] = []
    unreadable: list[str] = []
    for f in targets:
        try:
            with f.open("r", encoding="utf-8", errors="ignore") as fh:
                for lineno, line in enumerate(fh, 1):
                    for label, needle in needles.items():
                        if needle in line:
                            hits.append(f"{f}:{lineno} (matches {label})")
        except (OSError, ValueError) as exc:
            unreadable.append(f"{f}: {type(exc).__name__}")
    if unreadable:
        print(f"FAIL: {len(unreadable)} file(s) could not be scanned:")
        for u in unreadable:
            print(f"  {u}")
        return 1

    print(f"scanned {len(targets)} file(s) under {len(args.paths)} path(s)")
    if hits:
        print(f"FAIL: {len(hits)} hit(s):")
        for h in hits:
            print(f"  {h}")
        return 1
    return int(not _pass("p0_7-keyscan", "0 hits"))


# --------------------------------------------------------------------------- #
# P0.4 — detector regression: reconstruct the real contaminated attempt
# --------------------------------------------------------------------------- #


def _p0_4_target() -> Path:
    return _RUNS_DIR / _P0_4_INSTANCE / _P0_4_ARM


def _neutralize_result_json(run_dir: Path, own_instance: str) -> None:
    """Make a staged/synthetic ``result.json`` un-ingestable as a real row.

    ``record`` (``ingest_row``) globs ``runs/*/*/result.json`` and reads
    ``instance_id`` straight off it. A staged copy that still carried the
    SOURCE run's real ``instance_id`` would resolve to a REAL cell — the
    source's own — if ``record`` ever ran over the staged tree by accident
    (it currently does not check for a staging marker). Rewritten here to
    the identity this staged dir actually claims, and ``attempt`` forced to
    ``0`` as a second, independent backstop: ``ingest_row`` skips attempt 0
    outright regardless of what ``instance_id`` says.

    ONLY ``instance_id`` and ``attempt`` are rewritten — NOT ``arm``. Read
    from ``benchmark_store.py::ingest_row``: the arm KEY is the run
    directory's own name (``key = run_dir.name``), and if
    ``result.json``'s ``arm`` field is non-empty and disagrees with it, the
    WHOLE ROW IS SKIPPED (``"skipped:result.json records arm ... but sits
    in the ... run directory"``) rather than filed under either identity. So
    a mismatched ``arm`` left over from the source row (e.g. p0_4-stage's
    copy keeps ``arm: "v32-solo"`` under a live ``.../flash-chain/``
    directory) is not merely harmless — it is an ACTIVE third guard that
    makes ``record`` refuse the row outright, independent of anything this
    function does. This function does not claim to make the row's claimed
    identity consistent on every field, only ``instance_id``/``attempt``.
    """
    res = run_dir / "result.json"
    if not res.is_file():
        return
    try:
        row = json.loads(res.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(row, dict):
        return
    row["instance_id"] = own_instance
    row["attempt"] = 0
    res.write_text(json.dumps(row, indent=2), encoding="utf-8")


def cmd_p0_4_stage(args: argparse.Namespace) -> int:
    """Reconstruct the real ``harumiweb__exstruct-113 / flash-chain`` attempt-2 positive.

    THE ORIGINAL BYTES ARE GONE — attempt 3 overwrote them on disk before
    this task started, and ``runs/``/``results-archive/`` are gitignored, so
    there is no history to recover them from — but the INCIDENT WAS REAL.
    ``benchmarks.db`` holds the row verbatim: (harumiweb__exstruct-113,
    flash-chain, attempt 2), audit finding ``audit failed: foreign-workdir:
    sssf-events.jsonl:152 named another arm's working tree
    ['harumiweb__exstruct-113__v32-solo', 'harumiweb__exstruct-113__bare']``.
    See ``_P0_4_FOREIGN_CELLS`` and ``SAIL-DISCOVERY.md`` for the full
    reconstruction rationale, including why this is the SAME detector as the
    `.pth`-leak incident documented beside ``_foreign_workdir_hits`` in the
    adapter (that leak is WHY the agent's own tooling read into those two
    other arms' trees for this instance — not a different detector).

    Default source: the real, archived ``runs/harumiweb__exstruct-113/
    v32-solo/`` row (same instance, a real sssf trace) — ``--from PATH``
    overrides it. The copy's own self-references are rewritten to the
    ``flash-chain`` identity (so its OWN legitimate paths are not
    accidentally flagged), then ONE planted ``tool_call`` event is
    appended — a single bash command naming BOTH ``_P0_4_FOREIGN_CELLS``
    entries, not two separate events naming one each. The real historical
    positive was ONE command (line 152) that touched both other arms' trees
    at once; ``_foreign_workdir_hits`` returns every distinct cell it finds
    in one command's text, and that multi-match dedup path is exactly what
    the historical row exercised — a one-cell-per-event reconstruction would
    never reach it. Deterministic, regardless of which source is used,
    rather than relying on an incidental match.

    The LIVE target directory currently holds a real, clean attempt
    (attempt 3) for one of the 8 E5 campaign instances, so this command
    backs it up (to ``bench/swebench/.phase0-backups/``, NEVER under
    ``runs/`` — see ``_PHASE0_BACKUPS_DIR``) before overwriting, and
    ``p0_4-unstage`` restores it — never deletes it outright.
    """
    default_source = _RUNS_DIR / _P0_4_INSTANCE / "v32-solo"
    source = Path(args.from_path) if args.from_path else default_source
    if not (source / "sssf-events.jsonl").is_file():
        return int(not _fail(
            "source has a real sssf-events.jsonl",
            f"{source} — pass --from PATH to point at a different real "
            "runs/<instance>/<arm>/ row",
        ))

    target = _p0_4_target()
    target.mkdir(parents=True, exist_ok=True)
    marker = target / _P0_4_STAGE_MARKER
    if marker.exists():
        return int(not _fail(
            "not already staged",
            f"{marker} exists — run p0_4-unstage first",
        ))

    _PHASE0_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backup_dir = _PHASE0_BACKUPS_DIR / f"{_P0_4_INSTANCE}__{_P0_4_ARM}"
    live_files = [p for p in target.iterdir()]
    if live_files:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(target, backup_dir)
        print(f"  backed up {len(live_files)} existing item(s) to {backup_dir}")
        for p in live_files:
            shutil.rmtree(p) if p.is_dir() else p.unlink()

    copied = 0
    for src in source.iterdir():
        dst = target / src.name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        copied += 1

    # Rewrite the copy's OWN self-references to the target identity — same
    # technique as p0_5b-stage — so only the two PLANTED events below are
    # foreign, not every legitimate path the source trace already contained.
    events_path = target / "sssf-events.jsonl"
    source_cell = f"{source.parent.name}__{source.name}"
    target_cell = f"{_P0_4_INSTANCE}__{_P0_4_ARM}"
    text = events_path.read_text(encoding="utf-8")
    if source_cell != target_cell:
        text = text.replace(source_cell, target_cell)
        events_path.write_text(text, encoding="utf-8")
    lines = text.splitlines()
    real_events = [json.loads(ln) for ln in lines if ln.strip()]
    last = next((e for e in reversed(real_events) if isinstance(e, dict)), {})
    last_ts = last.get("ts") or datetime.now(UTC).isoformat()

    # ONE event naming BOTH cells, not two events naming one each. The real
    # historical positive was a SINGLE command (line 152) that happened to
    # touch both other arms' trees in one shot, and `_foreign_workdir_hits`
    # returns every distinct cell it finds in ONE command's text — its
    # multi-match dedup path is exactly what the historical row exercised
    # and what a one-cell-per-event reconstruction would never reach.
    try:
        ts = (datetime.fromisoformat(last_ts) + timedelta(milliseconds=1)).isoformat()
    except ValueError:
        ts = datetime.now(UTC).isoformat()
    planted_command = " ".join(
        f"grep -r x /home/k/.cache/swebench-work/{cell}/repo"
        for cell in _P0_4_FOREIGN_CELLS
    )
    last_payload = last.get("payload") if isinstance(last.get("payload"), dict) else {}
    event = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "ts": ts,
        "adw_id": last.get("adw_id", "phase0p04"),
        "phase_id": last.get("phase_id", ""),
        "type": "tool_call",
        "name": f"bash: {planted_command[:80]}…",
        "payload": {
            "agent": last_payload.get("agent", "builder"),
            "tool": "bash",
            "tool_call_id": f"call_{uuid.uuid4().hex[:24]}",
            "args": {"command": planted_command},
            "duration_ms": 1,
            "ok": True,
            "result_snippet": "PLANTED-P0-4-RECONSTRUCTION (one command naming both real cells)",
        },
        "parent_id": "",
        "tokens": None,
        "started_at": ts,
        "ended_at": ts,
    }
    lines.append(json.dumps(event))
    planted_line = len(lines)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _neutralize_result_json(target, _P0_4_INSTANCE)

    marker.write_text(
        json.dumps(
            {
                "staged_at": datetime.now(UTC).isoformat(),
                "from": str(source),
                "backup_dir": str(backup_dir) if live_files else None,
                "planted_cells": list(_P0_4_FOREIGN_CELLS),
                "planted_line": planted_line,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"PASS: staged {copied} item(s) from {source} into {target}")
    print(f"  planted ONE command at sssf-events.jsonl:{planted_line} naming "
          f"both cells: {list(_P0_4_FOREIGN_CELLS)}")
    print(f"  next: uv run python bench/swebench_adapter.py audit "
          f"--instance {_P0_4_INSTANCE} --arm {_P0_4_ARM}")
    print(f"  expect ONE finding listing BOTH: {list(_P0_4_FOREIGN_CELLS)}")
    print("  then: p0_4-unstage (BEFORE any `record`)")
    return 0


def cmd_p0_4_unstage(_args: argparse.Namespace) -> int:
    """Remove the staged copy, restoring whatever real row was backed up."""
    target = _p0_4_target()
    marker = target / _P0_4_STAGE_MARKER
    if not marker.exists():
        return int(not _fail("staged marker present", f"{marker} not found — nothing to unstage"))
    info = json.loads(marker.read_text(encoding="utf-8"))
    backup_dir = Path(info["backup_dir"]) if info.get("backup_dir") else None
    for p in target.iterdir():
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    target.rmdir()
    if backup_dir and backup_dir.is_dir():
        shutil.move(str(backup_dir), str(target))
        print(f"PASS: unstaged; restored the real row from {backup_dir}")
    else:
        print("PASS: unstaged; no prior real row existed to restore")
    # `_PHASE0_BACKUPS_DIR` itself (created unconditionally by p0_4-stage,
    # even on a first-ever stage with no backup to make) has no other
    # purpose once its one entry is gone — left behind otherwise.
    with contextlib.suppress(OSError):
        _PHASE0_BACKUPS_DIR.rmdir()
    return 0


# --------------------------------------------------------------------------- #
# P0.5b — detector proof: synthesize a foreign-workdir leak
# --------------------------------------------------------------------------- #


def _p0_5b_default_source() -> Path:
    return _RUNS_DIR / "getmoto__moto-9841" / "flash-solo"


def cmd_p0_5b_stage(args: argparse.Namespace) -> int:
    """Build a staged run dir whose trace contains ONE planted foreign-workdir read.

    DEVIATION FROM THE PRE-REGISTRATION'S LITERAL TEXT, disclosed here and in
    ``frozen/PRE-REGISTRATION-SAIL-AB.md``'s Resolved review notes: the draft's
    example planted path (``runs/<other-instance>/<other-arm>/planted.txt``)
    does NOT match what the real detector (``_foreign_workdir_hits`` /
    ``_WORKDIR_CELL`` in ``bench/swebench_adapter.py``) actually matches on.
    The live regex is ``swebench-work/([A-Za-z0-9_.\\-]+?__[A-Za-z0-9_.\\-]+)``
    — it fires on the scratch-root cell naming convention
    (``/home/k/.cache/swebench-work/<instance>__<arm>/...``, confirmed against
    a real archived trace), not on a ``runs/`` path. A planted ``runs/...``
    path would NOT trip the detector at all, which would make this proof
    worthless. The planted event below therefore uses the real pattern.

    Copies every file from ``--source-run`` (default: a real archived
    ``getmoto__moto-9841/flash-solo`` row, builder-only, same shape as every
    arm this campaign runs) into ``--run-dir DIR``, then appends one
    well-formed ``tool_call`` event to the copy's ``sssf-events.jsonl`` naming
    a foreign cell. ``DIR``'s last two path segments become the
    ``--instance``/``--arm`` you audit against — pick a DIR under
    ``bench/swebench/runs/`` so ``_run_dir`` resolves it the same way the real
    ``audit`` command does, e.g.::

        bench/swebench/runs/phase0-p0-5b-synthetic-leak/flash-solo
    """
    run_dir = Path(args.run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        return int(not _fail(
            "--run-dir is empty or absent",
            f"{run_dir} already has content — pick a fresh synthetic path",
        ))
    source = Path(args.source_run) if args.source_run else _p0_5b_default_source()
    if not (source / "sssf-events.jsonl").is_file():
        return int(not _fail(
            "--source-run has a real sssf-events.jsonl",
            str(source),
        ))

    run_dir.mkdir(parents=True, exist_ok=True)
    for src in source.iterdir():
        dst = run_dir / src.name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # The instance/arm THIS staged dir claims to be (derived from DIR) — see
    # below.
    own_instance, own_arm = run_dir.parent.name, run_dir.name
    # The SOURCE trace's own paths name ITS OWN identity throughout (every
    # legitimate `swebench-work/<source_instance>__<source_arm>/...` read),
    # which the detector would otherwise flag as foreign for every single one
    # of them once copied under a DIFFERENT (instance, arm) — that is real
    # detector behaviour, not a bug, but it would bury the ONE finding this
    # command exists to prove under dozens of accidental ones. So the copy's
    # self-references are rewritten to the STAGED identity first, exactly as
    # if this run's own working tree had always been named that — a real,
    # structurally valid trace shape, just relabelled — leaving the PLANTED
    # line as the only foreign reference once it is appended below.
    events_path = run_dir / "sssf-events.jsonl"
    source_cell = f"{source.parent.name}__{source.name}"
    target_cell = f"{own_instance}__{own_arm}"
    if source_cell != target_cell:
        rewritten = events_path.read_text(encoding="utf-8").replace(source_cell, target_cell)
        events_path.write_text(rewritten, encoding="utf-8")

    lines = events_path.read_text(encoding="utf-8").splitlines()
    real_events = [json.loads(ln) for ln in lines if ln.strip()]
    last = next((e for e in reversed(real_events) if isinstance(e, dict)), {})
    last_ts = last.get("ts") or datetime.now(UTC).isoformat()
    try:
        planted_ts = (
            datetime.fromisoformat(last_ts) + timedelta(milliseconds=1)
        ).isoformat()
    except ValueError:
        planted_ts = datetime.now(UTC).isoformat()

    # The planted path names something ELSE — any other cell is foreign to it.
    foreign_cell = "planted__other-instance__planted-other-arm"
    if foreign_cell == f"{own_instance}__{own_arm}":  # pathological DIR choice
        foreign_cell = "planted__yet-another-instance__planted-yet-another-arm"
    planted_path = f"/home/k/.cache/swebench-work/{foreign_cell}/repo/planted.txt"

    last_payload = last.get("payload") if isinstance(last.get("payload"), dict) else {}
    planted_event = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "ts": planted_ts,
        "adw_id": last.get("adw_id", "phase0p05b"),
        "phase_id": last.get("phase_id", ""),
        "type": "tool_call",
        "name": f"read: {planted_path}",
        # The full real key set a `read` tool_call carries (confirmed against
        # an archived trace), not the minimal subset — so this event is
        # structurally indistinguishable from a genuine one to anything that
        # reads `payload` generically.
        "payload": {
            "agent": last_payload.get("agent", "builder"),
            "tool": "read",
            "tool_call_id": f"call_{uuid.uuid4().hex[:24]}",
            "args": {"path": planted_path},
            "duration_ms": 1,
            "ok": True,
            "result_snippet": "PLANTED-FOREIGN-WORKDIR-LEAK-PROBE (p0_5b-stage)",
        },
        "parent_id": "",
        "tokens": None,
        "started_at": planted_ts,
        "ended_at": planted_ts,
    }
    lines.append(json.dumps(planted_event))
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    planted_line = len(lines)

    _neutralize_result_json(run_dir, own_instance)

    (run_dir / _P0_5B_STAGE_MARKER).write_text(
        json.dumps(
            {
                "staged_at": datetime.now(UTC).isoformat(),
                "source_run": str(source),
                "planted_path": planted_path,
                "planted_line": planted_line,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"PASS: staged {run_dir}")
    print(f"  planted foreign path: {planted_path}")
    print(f"  planted at sssf-events.jsonl:{planted_line}")
    print(f"  expected finding substring: foreign-workdir: sssf-events.jsonl:{planted_line}")
    print(f"  next: uv run python bench/swebench_adapter.py audit "
          f"--instance {own_instance} --arm {own_arm}")
    print("  then: p0_5b-unstage (BEFORE any `record`)")
    return 0


def cmd_p0_5b_unstage(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    marker = run_dir / _P0_5B_STAGE_MARKER
    if not marker.exists():
        return int(not _fail("staged marker present", f"{marker} not found — nothing to unstage"))
    shutil.rmtree(run_dir)
    # The empty <instance>/ parent this DIR's own instance segment created
    # (e.g. runs/phase0-p0-5b-synthetic-leak/) has no other purpose once its
    # only arm dir is gone — left behind otherwise, found and removed by hand
    # during review.
    with contextlib.suppress(OSError):
        run_dir.parent.rmdir()
    print(f"PASS: removed staged dir {run_dir}")
    return 0


# --------------------------------------------------------------------------- #
# P0.5a — sandbox proof: a planted literal /tmp marker must be invisible
# --------------------------------------------------------------------------- #


def cmd_p0_5a_plant(_args: argparse.Namespace) -> int:
    """Write the literal ``/tmp/report.json`` marker. Refuses to clobber a stranger.

    ``/tmp/report.json`` is the name 13 different adw_ids collided on in E5
    — i.e. it is exactly the kind of path a REAL concurrent run could be
    holding right now. If the file already exists and does NOT carry this
    script's own sentinel, planting over it would silently destroy whatever
    real run wrote it and would make ``p0_5a-clean`` delete someone else's
    file later. Refuses instead.
    """
    if _TMP_MARKER_PATH.exists():
        status = _marker_status()
        if status != "FOUND":
            return int(not _fail(
                f"{_TMP_MARKER_PATH} is empty or already ours to plant into",
                f"exists with status {status} — NOT this script's own marker; "
                "refusing to overwrite what may be a real concurrent run's "
                "file. Investigate before removing it by hand.",
            ))
    _TMP_MARKER_PATH.write_text(
        json.dumps({"marker": _TMP_MARKER_SENTINEL, "planted_by": "phase0_sail_ab.py",
                     "planted_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    return int(not _pass("p0_5a-plant", f"wrote {_TMP_MARKER_PATH}"))


def _marker_status() -> str:
    if not _TMP_MARKER_PATH.exists():
        return "NOT-FOUND"
    try:
        data = json.loads(_TMP_MARKER_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "FOUND-UNREADABLE"
    return "FOUND" if data.get("marker") == _TMP_MARKER_SENTINEL else "FOUND-WRONG-CONTENT"


def cmd_p0_5a_check(args: argparse.Namespace) -> int:
    """Report whether the planted /tmp marker is visible from THIS process.

    DEVIATION FROM THE PRE-REGISTRATION'S LITERAL TEXT, disclosed here and in
    the draft's Resolved review notes: the draft describes this running
    "inside a probe" via ``--probe-plumbing``'s "scripted reply". For the sssf
    arms that mechanism does not exist — ``run_sssf``'s own docstring is
    explicit that ``probe_plumbing=True`` means "the ADW is never invoked at
    all" and no reply script of any kind runs (the fixed-reply mechanism
    ``_BARE_PROBE_REPLIES`` belongs to the UNRELATED ``bare`` arm and answers
    a fixed, hardcoded script — there is nothing to inject an arbitrary
    ``cat /tmp/...`` command into). So this command drives the adapter's own
    sandbox primitives directly — the same ones ``run_sssf`` wraps a real
    spawn in, and the same ones
    ``tests/test_swebench_sandbox_isolation.py::test_slash_tmp_is_private_and_must_exist``
    already exercises for exactly this property — rather than pretending a
    probe-reply hook exists for sssf arms.

    Without ``--inside-sandbox``: plain host-side status report (the CONTROL
    — expected FOUND after ``p0_5a-plant``).

    With ``--inside-sandbox``: re-invokes THIS SAME subcommand (no flag, so no
    recursion) inside a real ``bwrap`` namespace built by
    ``_sandbox_argv``/``_sandbox_probe`` (skips with a clear reason if bwrap
    cannot build a namespace here) and reports the CHILD's status — expected
    NOT-FOUND. This is the sandbox-side half.
    """
    if not args.inside_sandbox:
        status = _marker_status()
        print(f"STATUS: {status}")
        return 0

    A = _adapter()
    ok, problem = A._sandbox_probe()
    if not ok:
        print(f"SKIP: bwrap cannot build a namespace here: {problem}")
        return 3
    # THE MODE A REAL RUN WOULD ACTUALLY USE, not a fixed "none" — a real run
    # defaults to the docker BROKER, and `SWEBENCH_SANDBOX_DOCKER=raw` binds
    # the real `/var/run/docker.sock` into the namespace, which lets
    # `docker run -v /tmp:/x ...` reach the HOST's /tmp from inside — the
    # exact channel this proof exists to close. A proof that always wrapped
    # "none" would never see the mode that defeats it.
    mode = A._sandbox_docker_mode()
    if mode == "raw":
        return int(not _fail(
            "p0_5a sandbox proof",
            "SWEBENCH_SANDBOX_DOCKER=raw binds /var/run/docker.sock, so a run "
            "can reach the host /tmp via `docker run -v`. This proof cannot "
            "hold under raw; unset it for the campaign.",
        ))
    with tempfile.TemporaryDirectory(prefix="phase0-p0-5a-") as td:
        root = Path(td)
        tree = root / "acme__widget-1__phase0"
        (tree / "repo").mkdir(parents=True)
        (tree / "tmp").mkdir()
        ledger_dir = root / "ledger"
        ledger_dir.mkdir()
        # NOT ``sys.executable``: this process typically runs from a project
        # venv under a path (e.g. ``.../backend/.venv/bin/python3``) that
        # ``_sandbox_argv`` never mounts — only ``/usr``, ``/bin``, ``/sbin``
        # and specific HOME subpaths are. ``/usr/bin/python3`` is the system
        # interpreter, always reachable inside the namespace.
        #
        # NOT a re-invocation of THIS FILE either: ``bench/swebench/`` itself
        # is never mounted into the namespace (the run's own tree and the
        # engine's ``adws/`` are the only non-HOME binds), so the child could
        # not open its own source. The check is small enough to inline as a
        # ``python3 -c`` one-liner instead — the exact same
        # ``os.path.exists``/content check ``_marker_status`` runs, just
        # without needing a mounted file to run it from.
        interpreter = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else "python3"
        inline_check = (
            "import json,sys\n"
            "p='/tmp/report.json'\n"
            "try:\n"
            "    d=json.load(open(p))\n"
            f"    ok = d.get('marker') == {_TMP_MARKER_SENTINEL!r}\n"
            "    print('STATUS:', 'FOUND' if ok else 'FOUND-WRONG-CONTENT')\n"
            "except FileNotFoundError:\n"
            "    print('STATUS: NOT-FOUND')\n"
            "except Exception:\n"
            "    print('STATUS: FOUND-UNREADABLE')\n"
        )
        argv = A._sandbox_argv(
            [interpreter, "-c", inline_check],
            tree=tree,
            cwd=tree / "repo",
            ledger_dir=ledger_dir,
            docker_mode=mode,
        )
        proc = subprocess.run(  # noqa: S603
            argv, capture_output=True, text=True, cwd=str(tree / "repo"), timeout=60
        )
    child_out = proc.stdout.strip()
    print(f"  child (inside sandbox) stdout: {child_out!r}")
    if proc.stderr.strip():
        print(f"  child stderr: {proc.stderr.strip()[:500]!r}")
    m = re.search(r"STATUS:\s*(\S+)", child_out)
    child_status = m.group(1) if m else "UNKNOWN"
    if child_status == "NOT-FOUND":
        return int(not _pass(
            "p0_5a sandbox proof",
            "the planted /tmp marker is INVISIBLE inside the sandbox",
        ))
    return int(not _fail(
        "p0_5a sandbox proof",
        f"child reported {child_status} — the known-open /tmp channel is "
        "STILL OPEN; ABORT per the pre-registration",
    ))


def cmd_p0_5a_clean(_args: argparse.Namespace) -> int:
    """Remove the marker — ONLY when it is still this script's own sentinel.

    Same reasoning as ``p0_5a-plant``'s refusal: ``/tmp/report.json`` is a
    path real concurrent runs collide on, so deleting it unconditionally
    could destroy someone else's file. If it exists but is not our sentinel,
    this is a FAIL naming the status, not a silent no-op and not a delete.
    """
    status = _marker_status()
    if status == "NOT-FOUND":
        return int(not _pass("p0_5a-clean", f"{_TMP_MARKER_PATH} was already absent"))
    if status != "FOUND":
        return int(not _fail(
            f"{_TMP_MARKER_PATH} is our own sentinel before removing it",
            f"status {status} — NOT this script's marker; left in place",
        ))
    _TMP_MARKER_PATH.unlink()
    return int(not _pass("p0_5a-clean", f"removed {_TMP_MARKER_PATH}"))


# --------------------------------------------------------------------------- #
# argparse wiring
# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("p0_6-isolation", help="P0.6 provider-isolation preflight (checkable half)")

    p = sub.add_parser("p0_7-keyscan", help="P0.7 key-hygiene scan (counts only, never content)")
    p.add_argument("paths", nargs="+", help="files or directories to scan")

    p = sub.add_parser("p0_4-stage", help="P0.4 reconstruct the real contaminated attempt into live runs/")
    p.add_argument(
        "--from", dest="from_path", default=None,
        help="override the default source (runs/harumiweb__exstruct-113/"
             "v32-solo, a real archived row for the same instance) with a "
             "different directory shaped like one runs/<instance>/<arm>/ "
             "row. The two REAL foreign cells from benchmarks.db's recorded "
             "finding are planted regardless of source — see the command's "
             "own --help / docstring and SAIL-DISCOVERY.md.",
    )
    sub.add_parser("p0_4-unstage", help="P0.4b remove the staged copy, restore the real row")

    p = sub.add_parser("p0_5b-stage", help="P0.5b synthesize a foreign-workdir leak into a staged run dir")
    p.add_argument("--run-dir", required=True, help="fresh, empty directory to stage into")
    p.add_argument(
        "--source-run", default=None,
        help="an existing runs/<instance>/<arm> dir to copy from "
             "(default: runs/getmoto__moto-9841/flash-solo, a real archived "
             "builder-only row)",
    )
    p = sub.add_parser("p0_5b-unstage", help="remove a p0_5b-stage'd directory")
    p.add_argument("--run-dir", required=True)

    sub.add_parser("p0_5a-plant", help="P0.5a write a literal /tmp/report.json marker")
    p = sub.add_parser("p0_5a-check", help="P0.5a report whether the marker is visible")
    p.add_argument(
        "--inside-sandbox", action="store_true",
        help="build a real bwrap namespace and report the CHILD's visibility "
             "instead of this process's own (see this command's docstring "
             "for why there is no --probe-plumbing hook to use instead)",
    )
    sub.add_parser("p0_5a-clean", help="P0.5a remove the planted marker")

    args = ap.parse_args()
    handlers = {
        "p0_6-isolation": cmd_p0_6_isolation,
        "p0_7-keyscan": cmd_p0_7_keyscan,
        "p0_4-stage": cmd_p0_4_stage,
        "p0_4-unstage": cmd_p0_4_unstage,
        "p0_5b-stage": cmd_p0_5b_stage,
        "p0_5b-unstage": cmd_p0_5b_unstage,
        "p0_5a-plant": cmd_p0_5a_plant,
        "p0_5a-check": cmd_p0_5a_check,
        "p0_5a-clean": cmd_p0_5a_clean,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
