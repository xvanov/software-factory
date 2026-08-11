"""The published archive could not reproduce its own root-cause analysis.

``results-archive/`` snapshotted the SCORING evidence — ``result.json``,
``audit.json``, ``prediction.diff`` — and none of the DIAGNOSTIC evidence. Every
bucket-A finding in the sweep-2 post-mortem came from the latter: the unstripped
``raw.diff``, the agent's action trail, and the sweep's own per-row log. Those
lived only in ``bench/swebench/runs/``, which ``.gitignore`` excludes and
``_reset_run_artifacts`` deletes at the top of the next run of the same cell.

Measured consequence: the flagship ``tox-3931`` finding — a CORRECT patch
destroyed by diff capture — survived only because an operator hand-copied git
objects out of an ephemeral cache before it was overwritten. A number whose
explanation cannot be re-derived is a number that has to be taken on trust.

Every test here holds one property of the fix:

1. the diagnostics are actually copied, at the same relative path;
2. the copy is byte-stable, so the archive's own integrity record is a digest
   and not a clock reading;
3. ``report --check`` FAILS when a diagnostic is missing or corrupt;
4. an archive written before this change still verifies clean — demanding the
   files retroactively would refuse every committed archive, which is the trap
   ``_ROW_ARTIFACTS`` documents;
5. an oversized file is truncated LOUDLY, never silently halved;
6. every arm's trail shape is covered, so a new arm cannot opt out by accident.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ADAPTER = Path(__file__).resolve().parents[1] / "bench" / "swebench_adapter.py"


@pytest.fixture
def A() -> Any:  # noqa: N802
    spec = importlib.util.spec_from_file_location("_swe_archive_diagnostics", _ADAPTER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_SHA = "test-manifest-sha"


def _patch_dirs(A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:  # noqa: N803
    runs = tmp_path / "runs"
    monkeypatch.setattr(A, "RUNS_DIR", runs)
    monkeypatch.setattr(A, "SWE_DIR", tmp_path)
    monkeypatch.setattr(A, "RESULTS_ARCHIVE_DIR", tmp_path / "results-archive")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "profile": "swe-rebench",
                "manifest_sha256": _SHA,
                "instances": [{"instance_id": "inst_a", "created_at": "2026-03-01 00:00:00"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(A, "MANIFEST_PATH", manifest)
    return runs


_RAW_DIFF = (
    "diff --git a/src/thing.py b/src/thing.py\n+ real fix\n"
    "diff --git a/tests/test_thing.py b/tests/test_thing.py\n- assert old\n"
)
_TRAJECTORY = '{"kind":"ActionEvent","action":"str_replace"}\n'
_SWEEP_LOG = "run --instance inst_a --arm factory\nOK\n"


def _row(runs: Path, iid: str, arm: str, *, diagnostics: bool = True) -> Path:
    """One row dir carrying the three required artifacts, plus diagnostics."""
    d = runs / iid / arm
    d.mkdir(parents=True, exist_ok=True)
    (d / "prediction.diff").write_text("diff --git a/x b/x\n+1\n", encoding="utf-8")
    (d / "result.json").write_text(
        json.dumps(
            {
                "arm": arm,
                "instance_id": iid,
                "manifest_sha256": _SHA,
                "error": None,
                "attempt": 1,
                "tokens_in": 10,
                "cached_input_tokens": 4,
                "tokens_out": 5,
                "cost_usd": 0.5,
                "wall_clock_s": 60.0,
                "factory_says_green": None,
                "grade": {
                    "oracle_resolved": True,
                    "outcome": "resolved",
                    "pass_to_pass_count": 7,
                    "pass_to_pass_source": "manifest",
                },
            }
        ),
        encoding="utf-8",
    )
    (d / "audit.json").write_text(json.dumps({"ok": True, "findings": []}), encoding="utf-8")
    if diagnostics:
        (d / "raw.diff").write_text(_RAW_DIFF, encoding="utf-8")
        (d / "sweep-run.log").write_text(_SWEEP_LOG, encoding="utf-8")
        traj = d / "root" / "state" / "events" / "trajectories"
        traj.mkdir(parents=True)
        (traj / "1-1.ndjson").write_text(_TRAJECTORY, encoding="utf-8")
    return d


def _archive(A: Any, runs: Path, *, stamp: str = "2026-08-11T00:00:00+00:00") -> Path:  # noqa: N803
    rows = [
        {"_arm": p.name, "_run_dir": str(p)}
        for p in sorted(runs.glob("*/*"))
        if (p / "result.json").is_file()
    ]
    return A._archive_report_artifacts(
        rows,
        generated_at=stamp,
        table_text="t\n",
        refused=[],
        foreign=[],
        superseded=[],
        created={},
    )


# --------------------------------------------------------------------------- #
# 1 — the diagnostics are actually copied
# --------------------------------------------------------------------------- #


def test_the_archive_snapshots_the_diagnostic_evidence(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The three file kinds every sweep-2 root cause was read from land in the
    archive, at the SAME relative path, and decompress to the original bytes."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    out = _archive(A, runs)

    dest = out / "inst_a" / "factory"
    for rel, expected in (
        ("raw.diff", _RAW_DIFF),
        ("sweep-run.log", _SWEEP_LOG),
        ("root/state/events/trajectories/1-1.ndjson", _TRAJECTORY),
    ):
        stored = dest / f"{rel}.gz"
        assert stored.is_file(), f"{rel} was not archived"
        assert gzip.decompress(stored.read_bytes()).decode("utf-8") == expected

    # The unstripped diff is the point: the STRIPPED one is already archived as
    # prediction.diff, and the containment findings live in the difference.
    assert "tests/test_thing.py" in gzip.decompress(
        (dest / "raw.diff.gz").read_bytes()
    ).decode("utf-8")

    manifest = json.loads((out / A._DIAGNOSTICS_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["count"] == 3
    assert {e["path"] for e in manifest["files"]} == {
        "raw.diff",
        "sweep-run.log",
        "root/state/events/trajectories/1-1.ndjson",
    }
    assert all(e["row"] == "inst_a/factory" for e in manifest["files"])


def test_a_row_without_diagnostics_still_archives(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """A run that died before its first model call has no trail. It is not
    refused for that — ``_ROW_ARTIFACTS`` is the fail-closed set, and widening
    it retroactively invalidates every committed archive."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "bare", diagnostics=False)
    out = _archive(A, runs)
    assert (out / "inst_a" / "bare" / "result.json").is_file()
    manifest = json.loads((out / A._DIAGNOSTICS_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["count"] == 0
    summary, problems = A.verify_archive_diagnostics(out)
    assert problems == []
    assert "0/0" in summary


def test_the_diagnostics_never_become_report_rows(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """``_report_rows`` globs ``*/*/result.json``; a diagnostic must not create a
    path that looks like a row."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    out = _archive(A, runs)
    assert sorted(p.relative_to(out).parts[:2] for p in out.glob("*/*/result.json")) == [
        ("inst_a", "factory")
    ]


# --------------------------------------------------------------------------- #
# 2 — byte-stable, so the integrity record is a digest and not a clock
# --------------------------------------------------------------------------- #


def test_an_identical_diagnostic_compresses_to_identical_bytes(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """gzip stamps the current time into its header by default, which would make
    two archives of the same evidence differ in every byte-comparison and turn
    the integrity record into a clock reading."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    first = _archive(A, runs, stamp="2026-08-11T00:00:00+00:00")
    second = _archive(A, runs, stamp="2026-08-12T00:00:00+00:00")
    assert first != second
    a = (first / "inst_a" / "factory" / "raw.diff.gz").read_bytes()
    b = (second / "inst_a" / "factory" / "raw.diff.gz").read_bytes()
    assert a == b, "gzip output is not reproducible — mtime leaked into the header"
    assert A._deterministic_gzip(b"x") == A._deterministic_gzip(b"x")


# --------------------------------------------------------------------------- #
# 3 — a broken diagnostic FAILS the check
# --------------------------------------------------------------------------- #


def test_verification_catches_a_deleted_diagnostic(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    out = _archive(A, runs)
    summary, problems = A.verify_archive_diagnostics(out)
    assert problems == [], summary
    assert "3/3" in summary

    (out / "inst_a" / "factory" / "sweep-run.log.gz").unlink()
    _, problems = A.verify_archive_diagnostics(out)
    assert len(problems) == 1
    assert "missing" in problems[0] and "sweep-run.log.gz" in problems[0]


def test_verification_catches_a_corrupted_diagnostic(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """Both shapes of corruption: bytes that no longer decompress, and bytes
    that decompress to content the manifest never recorded."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    out = _archive(A, runs)

    (out / "inst_a" / "factory" / "raw.diff.gz").write_bytes(b"not gzip at all")
    _, problems = A.verify_archive_diagnostics(out)
    assert len(problems) == 1 and "undecompressable" in problems[0]

    (out / "inst_a" / "factory" / "raw.diff.gz").write_bytes(
        A._deterministic_gzip(b"a quietly rewritten diff\n")
    )
    _, problems = A.verify_archive_diagnostics(out)
    assert len(problems) == 1 and "digest drift" in problems[0]


def test_report_check_fails_on_a_corrupted_diagnostic(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]  # noqa: N803
) -> None:
    """``--check`` is the only gate that runs over COMMITTED evidence, so it is
    where reproducibility has to be enforced. Today it reads the table and
    nothing else, so the trajectories could rot under a green check."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    A.report()  # live: archives the evidence and writes results.md
    capsys.readouterr()
    archive = next((tmp_path / "results-archive").iterdir())

    # Unmolested, --check passes and SAYS what it verified.
    A.report(check=True)
    assert "diagnostics: 3/3" in capsys.readouterr().out

    (archive / "inst_a" / "factory" / "root" / "state" / "events" / "trajectories"
     / "1-1.ndjson.gz").unlink()
    with pytest.raises(SystemExit) as exc:
        A.report(check=True)
    out = capsys.readouterr().out
    assert "1-1.ndjson.gz" in out
    assert "CHECK FAILED" in str(exc.value)
    assert "not\nreproducible" in str(exc.value) or "not " in str(exc.value)


# --------------------------------------------------------------------------- #
# 4 — an older archive is not retroactively invalidated
# --------------------------------------------------------------------------- #


def test_an_archive_predating_diagnostics_verifies_clean(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The two committed archives hold no diagnostics. Refusing them would break
    ``report --check`` on published evidence — so the absence is reported as
    ``n/a``, with zero problems, and the distinction between "predates" and
    "found none" is carried by the manifest's PRESENCE."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    _row(runs, "inst_a", "factory")
    out = _archive(A, runs)
    (out / A._DIAGNOSTICS_MANIFEST_NAME).unlink()

    summary, problems = A.verify_archive_diagnostics(out)
    assert problems == []
    assert "predates" in summary
    assert "not" in summary and "reproducible" in summary


def test_check_still_passes_on_the_committed_sweep_2_archive(A: Any) -> None:  # noqa: N803
    """The real thing, not a fixture: the newest committed archive must keep
    verifying, because ``report --check`` is a required part of publishing."""
    archive = A._latest_archive()
    summary, problems = A.verify_archive_diagnostics(archive)
    assert problems == [], f"{archive}: {problems}"
    assert summary


# --------------------------------------------------------------------------- #
# 5 — an oversized file is truncated LOUDLY
# --------------------------------------------------------------------------- #


def test_an_oversized_diagnostic_is_truncated_and_says_so(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """A pathological run must not commit a 500 MB trajectory, and must not
    silently commit half of one either: the entry records what was lost."""
    # 200 is above every other fixture file, so exactly one entry truncates and
    # the count below is a real discriminator.
    monkeypatch.setattr(A, "_DIAGNOSTIC_MAX_BYTES", 200)
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    d = _row(runs, "inst_a", "factory")
    big = b"x" * 500
    (d / "raw.diff").write_bytes(big)
    out = _archive(A, runs)

    manifest = json.loads((out / A._DIAGNOSTICS_MANIFEST_NAME).read_text(encoding="utf-8"))
    entry = next(e for e in manifest["files"] if e["path"] == "raw.diff")
    assert entry["truncated"] is True
    assert entry["original_bytes"] == 500
    assert entry["stored_bytes"] == 200
    assert entry["original_sha256"] != entry["stored_sha256"]
    assert manifest["truncated"] == 1
    assert [e["truncated"] for e in manifest["files"] if e["path"] != "raw.diff"] == [
        False,
        False,
    ]

    # And a truncated entry still VERIFIES — against the stored digest, which is
    # the only one the bytes on disk can satisfy.
    summary, problems = A.verify_archive_diagnostics(out)
    assert problems == []
    assert "truncated" in summary


# --------------------------------------------------------------------------- #
# 5b — the answer key never travels with the answer sheet
# --------------------------------------------------------------------------- #


def test_the_grading_logs_are_never_archived(A: Any) -> None:  # noqa: N803
    """``sweep-grade.log`` / ``grade.log`` / ``grade-nodes.log`` carry the HIDDEN
    test node ids — measured on ``tox-dev__tox-3931``, ``sweep-grade.log`` hits
    ``fail_to_pass``/``pass_to_pass`` where ``sweep-run.log`` hits neither.
    Committing them would put the answer key in the repo, greppable by every
    later arm, since every arm runs on this filesystem."""
    for name in ("grade.log", "grade-nodes.log", "sweep-grade.log", "oracle.json.z"):
        assert name in A._NEVER_ARCHIVED
    assert not set(A._ARCHIVED_ROW_DIAGNOSTICS) & set(A._NEVER_ARCHIVED)
    assert not set(A._ARCHIVED_TRAJECTORY_GLOBS) & set(A._NEVER_ARCHIVED)


def test_selecting_a_grading_log_for_archiving_is_refused_loudly(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """The deny-list is enforced where the files are CHOSEN, not trusted to the
    tuples — the tuples are what a later edit would get wrong. And it refuses
    rather than skips, so that edit cannot look like it worked."""
    monkeypatch.setattr(A, "_ARCHIVED_ROW_DIAGNOSTICS", ("raw.diff", "sweep-grade.log"))
    d = tmp_path / "inst" / "factory"
    d.mkdir(parents=True)
    (d / "raw.diff").write_text(_RAW_DIFF, encoding="utf-8")
    (d / "sweep-grade.log").write_text("FAIL_TO_PASS ids here\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="answer key"):
        A._row_diagnostic_files(d)


# --------------------------------------------------------------------------- #
# 6 — every arm's trail shape is covered
# --------------------------------------------------------------------------- #


def test_every_arms_trail_shape_is_covered_by_a_glob(A: Any) -> None:  # noqa: N803
    """The trail location differs per arm and the arm id is NOT a parameter of
    the archiver. Pin the four shapes, so adding an arm without adding its shape
    is a failing test rather than a silently unarchived trail."""
    assert A._ARCHIVED_ROW_DIAGNOSTICS == ("raw.diff", "sweep-run.log")
    assert A._ARCHIVED_TRAJECTORY_GLOBS == (
        "root/state/events/trajectories/*.ndjson",
        "state/events/trajectories/*.ndjson",
        "bare-commands.ndjson",
        "claude-transcript.ndjson",
    )


def test_each_arms_documented_trajectory_path_matches_a_glob(
    A: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: N803
) -> None:
    """Behaviour: lay down the trail each arm really writes and assert the
    archiver finds it. The paths come from ``result.json``'s ``trajectory``
    field as the four run drivers write it."""
    runs = _patch_dirs(A, tmp_path, monkeypatch)
    cases = {
        "factory": "root/state/events/trajectories/1-1.ndjson",
        "solo-noreview": "root/state/events/trajectories/1-1.ndjson",
        "openhands": "state/events/trajectories/nostory-1.ndjson",
        "bare": "bare-commands.ndjson",
        "claude-5": A._CLAUDE_TRANSCRIPT_NAME,
    }
    for arm, rel in cases.items():
        d = _row(runs, "inst_a", arm, diagnostics=False)
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_TRAJECTORY, encoding="utf-8")
        found = [f.relative_to(d).as_posix() for f in A._row_diagnostic_files(d)]
        assert rel in found, f"{arm}: {rel} is not archived (found {found})"
