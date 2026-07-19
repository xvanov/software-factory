"""Unit tests for ``_query_ci_state`` — the real-CI conclusion query that
replaced the hardcoded ``ci_state="success"`` in the auto-merge worker.

These pin the parsing of ``gh pr checks --json`` output so a green string
literal can never again masquerade as a real CI pass (the "thinks CI passed
then it crashes" regression class).
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from factory.chain.auto_merge import _query_ci_state

APP = SimpleNamespace(repo="acme/widget")


def _fake_run(stdout: str, *, returncode: int = 0, raise_exc: Exception | None = None):
    def _run(cmd, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if raise_exc is not None:
            raise raise_exc
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    return _run


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        ([{"bucket": "pass", "name": "lint"}, {"bucket": "pass", "name": "pytest"}], "success"),
        ([{"bucket": "pass", "name": "lint"}, {"bucket": "fail", "name": "pytest"}], "failure"),
        ([{"bucket": "pass", "name": "lint"}, {"bucket": "pending", "name": "pytest"}], "pending"),
        ([{"bucket": "cancel", "name": "lint"}], "failure"),
        ([{"state": "SUCCESS", "name": "lint"}], "success"),
    ],
)
def test_bucket_reduction(monkeypatch, checks, expected):
    monkeypatch.setattr(subprocess, "run", _fake_run(json.dumps(checks)))
    assert _query_ci_state(app_config=APP, pr_number=42) == expected


def test_no_checks_returns_none(monkeypatch):
    # gh writes nothing to stdout when no checks are reported (e.g. a repo with
    # no workflows, like sacrifice pre-CI) — must be None so the gate falls
    # back to the recorded dev flag rather than fabricating a pass.
    monkeypatch.setattr(subprocess, "run", _fake_run(""))
    assert _query_ci_state(app_config=APP, pr_number=42) is None


def test_empty_list_returns_none(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("[]"))
    assert _query_ci_state(app_config=APP, pr_number=42) is None


def test_invalid_json_returns_none(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("not json"))
    assert _query_ci_state(app_config=APP, pr_number=42) is None


def test_placeholder_pr_number_skips_query(monkeypatch):
    # Non-positive PR numbers are dry-run docs placeholders — never shell out.
    called = {"n": 0}

    def _boom(*a, **k):  # noqa: ANN002, ANN003
        called["n"] += 1
        raise AssertionError("should not run gh for placeholder PR")

    monkeypatch.setattr(subprocess, "run", _boom)
    assert _query_ci_state(app_config=APP, pr_number=-5) is None
    assert called["n"] == 0


def test_gh_missing_returns_none(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run("", raise_exc=FileNotFoundError()))
    assert _query_ci_state(app_config=APP, pr_number=42) is None


def test_gh_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", _fake_run("", raise_exc=subprocess.TimeoutExpired("gh", 60))
    )
    assert _query_ci_state(app_config=APP, pr_number=42) is None
