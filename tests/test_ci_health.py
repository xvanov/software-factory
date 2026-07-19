"""Tests for the post-merge main-branch CI-health monitor (D004).

All ``gh`` calls are mocked via ``monkeypatch.setattr(subprocess, "run", ...)``
— no network escapes the process. Directions are written to a real
``tmp_path``-rooted ``apps/<app>/directions/`` tree (never the production
one) so the dedup guard's filesystem scan is exercised for real.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from factory.chain.ci_health import main_ci_health_tick

_PROTECTION_URL = "repos/o/r/branches/main/protection"
_CHECK_RUNS_URL = "repos/o/r/commits/main/check-runs"


@pytest.fixture
def factory_root(tmp_path: Path) -> Path:
    apps = tmp_path / "apps" / "sacrifice" / "directions"
    apps.mkdir(parents=True)
    (tmp_path / "apps" / "sacrifice" / "config.yaml").write_text(
        "name: sacrifice\nrepo: o/r\n",
        encoding="utf-8",
    )
    (tmp_path / "state").mkdir()
    return tmp_path


def _completed(cmd: list[str], returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)


def _make_gh_fake(
    *,
    protection: dict | None,
    check_runs: list[dict] | None,
    log_text: str = "AssertionError: boom\n  at test_foo.py:12",
    protection_returncode: int = 0,
):
    """Builds a ``subprocess.run`` fake dispatching on the ``gh`` subcommand."""

    def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        joined = " ".join(cmd)
        if _PROTECTION_URL in joined:
            if protection is None:
                return _completed(cmd, 1, "", "404 Not Found")
            return _completed(cmd, protection_returncode, json.dumps(protection), "")
        if _CHECK_RUNS_URL in joined:
            if check_runs is None:
                return _completed(cmd, 1, "", "error")
            return _completed(cmd, 0, json.dumps({"check_runs": check_runs}), "")
        if cmd[:3] == ["gh", "run", "view"]:
            return _completed(cmd, 0, log_text, "")
        raise AssertionError(f"unexpected gh invocation: {cmd!r}")

    return _fake_run


def _direction_dirs(root: Path, app: str = "sacrifice") -> list[Path]:
    d = root / "apps" / app / "directions"
    return sorted(p for p in d.iterdir() if p.is_dir())


def _required_check_run(
    *, name: str = "ci/tests", conclusion: str = "failure", run_id: str = "123"
) -> dict:
    return {
        "name": name,
        "status": "completed",
        "conclusion": conclusion,
        "head_sha": "deadbeef",
        "details_url": f"https://github.com/o/r/actions/runs/{run_id}/jobs/999",
    }


# --------------------------------------------------------------------------- #
# (a) required-check red -> exactly one ci-health direction filed
# --------------------------------------------------------------------------- #


def test_required_check_red_files_one_direction(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[_required_check_run()],
        log_text="AssertionError: expected 200 got 500\n  at test_healthz.py:9",
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "red_required"
    assert result.filed is True
    assert result.filed_direction_id is not None
    assert result.required_failing == ["ci/tests"]

    dirs = _direction_dirs(factory_root)
    assert len(dirs) == 1
    md_text = (dirs[0] / "direction.md").read_text(encoding="utf-8")
    assert "ci/tests" in md_text
    assert "AssertionError: expected 200 got 500" in md_text

    state_text = (dirs[0] / "state.yaml").read_text(encoding="utf-8")
    assert "ci-health" in state_text


# --------------------------------------------------------------------------- #
# (b) advisory-only red -> no direction filed
# --------------------------------------------------------------------------- #


def test_advisory_red_files_no_direction(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[
            {
                "name": "ci/tests",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "deadbeef",
            },
            {
                "name": "coderabbit-advisory",
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "deadbeef",
                "details_url": "https://github.com/o/r/actions/runs/999/jobs/1",
            },
        ],
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "red_advisory"
    assert result.filed is False
    assert result.filed_direction_id is None
    assert result.advisory_failing == ["coderabbit-advisory"]
    assert _direction_dirs(factory_root) == []


# --------------------------------------------------------------------------- #
# (c) all-green -> nothing filed
# --------------------------------------------------------------------------- #


def test_all_green_files_nothing(factory_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[
            {
                "name": "ci/tests",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "deadbeef",
            }
        ],
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "green"
    assert result.filed is False
    assert _direction_dirs(factory_root) == []


# --------------------------------------------------------------------------- #
# (d) dedup: second cycle, same failure -> no duplicate direction
# --------------------------------------------------------------------------- #


def test_same_failure_is_not_refiled_while_open(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[_required_check_run()],
        log_text="AssertionError: expected 200 got 500\n  at test_healthz.py:9",
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    first = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)
    assert first.filed is True
    assert len(_direction_dirs(factory_root)) == 1

    second = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)
    assert second.filed is False
    assert "duplicate" in second.reason
    assert len(_direction_dirs(factory_root)) == 1


def test_different_failure_after_prior_closed_is_refiled(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A DIFFERENT failure signature (not the same one) should file a
    second, independent direction — dedup keys on the failure, not on
    "any open ci-health direction exists"."""
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[_required_check_run()],
        log_text="AssertionError: expected 200 got 500\n  at test_healthz.py:9",
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)
    first = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)
    assert first.filed is True

    fake2 = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[_required_check_run(run_id="456")],
        log_text="KeyError: 'total'\n  at test_pledge.py:44",
    )
    monkeypatch.setattr(subprocess, "run", fake2, raising=True)
    second = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)
    assert second.filed is True
    assert len(_direction_dirs(factory_root)) == 2


# --------------------------------------------------------------------------- #
# (e) gh error/timeout -> nothing filed, no crash
# --------------------------------------------------------------------------- #


def test_gh_timeout_files_nothing_and_does_not_raise(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=30)

    monkeypatch.setattr(subprocess, "run", _fake_run, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "unknown"
    assert result.filed is False
    assert _direction_dirs(factory_root) == []


def test_gh_error_exit_files_nothing(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(protection=None, check_runs=None)
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "unknown"
    assert result.filed is False
    assert _direction_dirs(factory_root) == []


# --------------------------------------------------------------------------- #
# (f) repo with no required checks -> nothing filed
# --------------------------------------------------------------------------- #


def test_no_required_checks_configured_files_nothing(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": []}},
        check_runs=[_required_check_run()],
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "unknown"
    assert result.filed is False
    assert _direction_dirs(factory_root) == []


def test_no_branch_protection_files_nothing(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(protection=None, check_runs=[_required_check_run()])
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=False)

    assert result.state == "unknown"
    assert result.filed is False
    assert _direction_dirs(factory_root) == []


# --------------------------------------------------------------------------- #
# dry_run gating
# --------------------------------------------------------------------------- #


def test_dry_run_does_not_write_a_direction(
    factory_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _make_gh_fake(
        protection={"required_status_checks": {"contexts": ["ci/tests"]}},
        check_runs=[_required_check_run()],
    )
    monkeypatch.setattr(subprocess, "run", fake, raising=True)

    result = main_ci_health_tick(factory_root, "sacrifice", dry_run=True)

    assert result.state == "red_required"
    assert result.filed is False
    assert "dry-run" in result.reason
    assert _direction_dirs(factory_root) == []
