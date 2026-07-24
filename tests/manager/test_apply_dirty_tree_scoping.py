"""Regression cover for the two L4 apply bugs found in the 2026-07-24 audit.

Bug B: the dirty-working-tree refusal was repo-wide, so on a live factory tree
(dirty as a matter of normal operating practice) EVERY autonomous apply aborted
with ``dirty_working_tree``. 53 of 163 lifetime attempts died here.

Bug (audit trail): ``_append_history`` discarded ``result["error"]``, so all 53
recorded a bare ``status: "abandoned"`` with no reason — which is why a total
yield failure went unnoticed for 59 days.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from factory.manager.apply import _load_history, apply_manager_proposals
from tests.manager.test_apply import (
    _make_repo,
    _make_runner,
    _minimal_proposal,
    _persona_patch,
    _plant_proposal,
)


def _dirty(repo: Path, rel: str, content: str) -> None:
    """Leave an uncommitted modification at ``rel``."""
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    if not (repo / rel).exists():  # pragma: no cover - defensive
        raise AssertionError(rel)


def _tracked_dirty(repo: Path, rel: str, content: str) -> None:
    """Commit ``rel`` first, then modify it, so it is a TRACKED dirty file."""
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "add", rel], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", f"add {rel}"], cwd=str(repo), check=True, capture_output=True
    )
    p.write_text(content, encoding="utf-8")


def _run_apply(repo: Path, **kw: Any) -> dict[str, Any]:
    runner, _calls = _make_runner(pr_number=101)
    return apply_manager_proposals(
        root=repo,
        dry_run=False,
        runner=runner,
        repo="owner/repo",
        push=True,
        stage_self_edits=False,
        **kw,
    )


def test_apply_proceeds_when_dirt_is_outside_the_patch(tmp_path: Path) -> None:
    """The production condition: tree dirty in unrelated files, patch targets a
    clean path. This used to abort; it must now apply."""
    repo = _make_repo(
        tmp_path,
        {
            "factory/personas/sm.md": "# SM Persona\nbody line\n",
            "apps/sacrifice/config.yaml": "repo: x/y\n",
        },
    )
    _tracked_dirty(repo, "apps/sacrifice/config.yaml", "repo: x/y\nchanged: true\n")

    _plant_proposal(
        repo / "state" / "manager_proposals",
        _minimal_proposal(target_class="prompt_edit", patch=_persona_patch()),
        "p.json",
    )
    result = _run_apply(repo)

    assert result["processed"] == 1
    assert result["safe_applied"] == 1, f"expected apply to proceed, got {result['results']}"
    statuses = [r.get("status") for r in result["results"]]
    assert "abandoned" not in statuses


def test_apply_still_refuses_when_dirt_is_inside_the_patch(tmp_path: Path) -> None:
    """The case the guard actually exists for: uncommitted edits to the very file
    the patch rewrites. Must still refuse."""
    repo = _make_repo(tmp_path, {"factory/personas/sm.md": "# SM Persona\nbody line\n"})
    _tracked_dirty(repo, "factory/personas/sm.md", "# SM Persona\nlocally edited\n")

    _plant_proposal(
        repo / "state" / "manager_proposals",
        _minimal_proposal(target_class="prompt_edit", patch=_persona_patch()),
        "p.json",
    )
    result = _run_apply(repo)

    assert result["processed"] == 1
    assert result["safe_applied"] == 0
    r0 = result["results"][0]
    assert r0["status"] == "abandoned"
    assert "dirty_working_tree" in (r0.get("error") or "")


def test_unrelated_dirty_file_survives_a_failed_apply(tmp_path: Path) -> None:
    """``_cleanup()`` must not destroy operator work outside the patch.

    It used to run a repo-wide ``git reset --hard`` + ``git clean -fd``, which
    would silently discard uncommitted changes anywhere in the tree the moment an
    apply failed. Now that an apply can legitimately run in a dirty tree, that
    would have turned a recoverable patch failure into data loss.
    """
    repo = _make_repo(
        tmp_path,
        {
            "factory/personas/sm.md": "# SM Persona\nbody line\n",
            "apps/sacrifice/config.yaml": "repo: x/y\n",
        },
    )
    _tracked_dirty(repo, "apps/sacrifice/config.yaml", "repo: x/y\nPRECIOUS\n")

    # A patch that will fail to apply (context does not match).
    bad_patch = (
        "--- a/factory/personas/sm.md\n"
        "+++ b/factory/personas/sm.md\n"
        "@@ -1,2 +1,3 @@\n"
        " # NOT THE REAL FIRST LINE\n"
        " nor this\n"
        "+added\n"
    )
    _plant_proposal(
        repo / "state" / "manager_proposals",
        _minimal_proposal(target_class="prompt_edit", patch=bad_patch),
        "p.json",
    )
    result = _run_apply(repo)

    assert result["results"][0]["status"] in {"abandoned", "test_failed"}
    assert (
        "PRECIOUS" in (repo / "apps/sacrifice/config.yaml").read_text()
    ), "cleanup destroyed uncommitted operator work outside the patch"


def test_history_persists_the_error_reason(tmp_path: Path) -> None:
    """A status without a reason is not an audit trail."""
    repo = _make_repo(tmp_path, {"factory/personas/sm.md": "# SM Persona\nbody line\n"})
    _tracked_dirty(repo, "factory/personas/sm.md", "# SM Persona\nlocally edited\n")
    _plant_proposal(
        repo / "state" / "manager_proposals",
        _minimal_proposal(target_class="prompt_edit", patch=_persona_patch()),
        "p.json",
    )
    _run_apply(repo)

    history = _load_history(repo)
    assert len(history) == 1
    assert "error" in history[0], "history entry must carry the failure reason"
    assert "dirty_working_tree" in history[0]["error"]
    # And it must survive a JSON round-trip on disk.
    raw = json.loads(
        (repo / "state" / ".manager_apply_history.json").read_text(encoding="utf-8")
    )
    assert "dirty_working_tree" in raw[0]["error"]
