"""Tests for factory.manager.escalation — the L4 escalation channel (WS3.1).

Closes the silent-sink: an escalate_to_human / forbidden proposal must open an
(idempotent) GitHub issue + emit a loud alert instead of dying in the history
file. gh is mocked; no network is touched.

Coverage:
  * an escalate_to_human proposal opens a gh issue + writes an alert event
  * a re-fired SAME-id escalation does NOT open a duplicate (local dedup)
  * an already-open matching issue (gh-side dedup) is reused, not re-created
  * a gh failure does NOT crash L4 and is still visible on the alert stream
  * end-to-end through apply_manager_proposals: escalation issue is opened
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factory.manager.apply import apply_manager_proposals
from factory.manager.escalation import ESCALATION_LABEL, notify_escalation


@dataclass
class _Completed:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _make_gh_runner(
    *,
    list_stdout: str = "[]",
    list_rc: int = 0,
    create_rc: int = 0,
    create_url: str = "https://github.com/owner/repo/issues/777\n",
) -> tuple[Callable[..., Any], list[list[str]]]:
    """A runner that mocks the gh commands the escalation channel uses."""
    calls: list[list[str]] = []

    def _runner(args: list[str], **kwargs: Any) -> Any:
        calls.append(list(args))
        if args[:3] == ["gh", "issue", "list"]:
            return _Completed(returncode=list_rc, stdout=list_stdout)
        if args[:3] == ["gh", "label", "create"]:
            return _Completed(returncode=0)
        if args[:3] == ["gh", "issue", "create"]:
            return _Completed(returncode=create_rc, stdout=create_url)
        return _Completed(returncode=0)

    return _runner, calls


def _proposal(
    *,
    concern_id: str = "concern-abc",
    proposal_id: str = "prop-1",
    classification_hint: str = "escalate_to_human",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "concern_id": concern_id,
        "proposal_id": proposal_id,
        "concern_title": "sm-token-overflow",
        "diagnosis": "SM persona overflowed its token budget repeatedly.",
        "escalation_reason": "no safe automated fix available",
        "proposal": {
            "kind": "improvement",
            "target": "factory/personas/sm.md",
            "rationale": "Operator should trim the SM persona.",
            "suggested_patch": "",
        },
        "target_class": classification_hint,
        "escalate_to_human": classification_hint == "escalate_to_human",
    }


def _alerts(root: Path) -> list[dict[str, Any]]:
    p = root / "state" / "events" / "alerts.ndjson"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# A. Escalation opens an issue + alert
# ---------------------------------------------------------------------------


def test_escalation_opens_issue_and_alert(tmp_path: Path) -> None:
    runner, calls = _make_gh_runner()
    outcome = notify_escalation(
        _proposal(),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=runner,
    )
    assert outcome["notified"] is True
    assert outcome["gh_ok"] is True
    assert outcome["issue_number"] == 777

    # A gh issue create call was made with the escalation label.
    create = [c for c in calls if c[:3] == ["gh", "issue", "create"]]
    assert create, "expected a gh issue create call"
    assert ESCALATION_LABEL in create[0]

    # A loud alert was written.
    alerts = _alerts(tmp_path)
    assert any(a.get("kind") == "fms_escalation" for a in alerts)


def test_forbidden_also_escalates(tmp_path: Path) -> None:
    runner, calls = _make_gh_runner()
    outcome = notify_escalation(
        _proposal(classification_hint="forbidden"),
        root=tmp_path,
        repo="owner/repo",
        classification="forbidden",
        runner=runner,
    )
    assert outcome["notified"] is True
    assert [c for c in calls if c[:3] == ["gh", "issue", "create"]]
    assert any(a.get("kind") == "fms_escalation" for a in _alerts(tmp_path))


# ---------------------------------------------------------------------------
# A. Idempotency — re-firing the same id does not open a duplicate
# ---------------------------------------------------------------------------


def test_same_id_refire_does_not_duplicate_local(tmp_path: Path) -> None:
    """A second escalation with the same concern_id is deduped locally: no new
    issue, no repeat alert."""
    runner, calls = _make_gh_runner()
    notify_escalation(
        _proposal(),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=runner,
    )
    creates_after_first = len([c for c in calls if c[:3] == ["gh", "issue", "create"]])
    alerts_after_first = len(_alerts(tmp_path))

    # Re-fire the SAME concern under a FRESH proposal_id (L3 re-emitted it).
    outcome2 = notify_escalation(
        _proposal(proposal_id="prop-2"),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=runner,
    )
    assert outcome2["deduped"] is True
    assert outcome2["reason"] == "already_notified_local"
    # No second issue created, no second alert emitted.
    assert len([c for c in calls if c[:3] == ["gh", "issue", "create"]]) == creates_after_first
    assert len(_alerts(tmp_path)) == alerts_after_first


def test_existing_open_issue_reused_not_recreated(tmp_path: Path) -> None:
    """gh-side dedup: if an open fms-escalation issue already carries the id
    marker (e.g. local history was wiped), reuse it instead of creating a new
    one."""
    marker = "<!-- fms-escalation:concern-abc -->"
    list_stdout = json.dumps([{"number": 123, "body": f"prior body\n{marker}"}])
    runner, calls = _make_gh_runner(list_stdout=list_stdout)
    outcome = notify_escalation(
        _proposal(),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=runner,
    )
    assert outcome["issue_number"] == 123
    assert outcome["deduped"] is True
    # No new issue created.
    assert not [c for c in calls if c[:3] == ["gh", "issue", "create"]]


# ---------------------------------------------------------------------------
# A. gh failure does not crash, still visible
# ---------------------------------------------------------------------------


def test_gh_create_failure_does_not_crash_but_is_visible(tmp_path: Path) -> None:
    runner, _ = _make_gh_runner(create_rc=1, create_url="")
    outcome = notify_escalation(
        _proposal(),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=runner,
    )
    # Did not crash; recorded the failure.
    assert outcome["notified"] is True
    assert outcome["gh_ok"] is False
    assert outcome["reason"] == "gh_create_failed"
    # Both the escalation alert AND a gh-failure alert are visible.
    kinds = {a.get("kind") for a in _alerts(tmp_path)}
    assert "fms_escalation" in kinds
    assert "fms_escalation_gh_failed" in kinds


def test_gh_runner_raising_does_not_crash(tmp_path: Path) -> None:
    """Even a runner that raises (e.g. gh binary missing) must not crash L4."""

    def _raising_runner(args: list[str], **kwargs: Any) -> Any:
        raise FileNotFoundError("gh not found")

    outcome = notify_escalation(
        _proposal(),
        root=tmp_path,
        repo="owner/repo",
        classification="escalate_to_human",
        runner=_raising_runner,
    )
    assert outcome["notified"] is True
    assert outcome["gh_ok"] is False
    # The escalation is still visible on the alert stream.
    assert any(a.get("kind") == "fms_escalation" for a in _alerts(tmp_path))


def test_no_repo_still_alerts(tmp_path: Path) -> None:
    """With no repo we cannot open an issue, but the alert must still fire."""
    runner, calls = _make_gh_runner()
    outcome = notify_escalation(
        _proposal(),
        root=tmp_path,
        repo=None,
        classification="escalate_to_human",
        runner=runner,
    )
    assert outcome["notified"] is True
    assert outcome["reason"] == "no_repo"
    assert not [c for c in calls if c[:3] == ["gh", "issue", "create"]]
    assert any(a.get("kind") == "fms_escalation" for a in _alerts(tmp_path))


# ---------------------------------------------------------------------------
# A. End-to-end through apply_manager_proposals
# ---------------------------------------------------------------------------


def test_apply_escalation_opens_issue_end_to_end(tmp_path: Path) -> None:
    """An escalate_to_human proposal processed by the L4 apply loop opens a gh
    issue via the escalation channel (not a silent history append)."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Factory\n")
    for args in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "config", "user.email", "t@e.com"],
        ["git", "config", "user.name", "T"],
        ["git", "add", "."],
        ["git", "commit", "-q", "-m", "init"],
    ):
        subprocess.run(args, cwd=str(repo), check=True, capture_output=True)

    proposals_dir = repo / "state" / "manager_proposals"
    proposals_dir.mkdir(parents=True)
    proposal = _proposal()
    (proposals_dir / "esc.json").write_text(json.dumps(proposal))

    gh_calls: list[list[str]] = []

    def _runner(args: list[str], **kwargs: Any) -> Any:
        gh_calls.append(list(args))
        if args[:3] == ["gh", "issue", "list"]:
            return _Completed(returncode=0, stdout="[]")
        if args[:3] == ["gh", "issue", "create"]:
            return _Completed(
                returncode=0, stdout="https://github.com/owner/repo/issues/900\n"
            )
        if args[:3] == ["gh", "label", "create"]:
            return _Completed(returncode=0)
        kwargs.pop("check", None)
        return subprocess.run(args, **kwargs)

    result = apply_manager_proposals(
        root=repo,
        dry_run=False,
        runner=_runner,
        repo="owner/repo",
    )
    assert result["escalated_human"] == 1
    assert [c for c in gh_calls if c[:3] == ["gh", "issue", "create"]]
