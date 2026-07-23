"""``scripts/deploy-factory-from-main.sh`` — factory self-deploy (G4).

Merged loop-1 self-improvements must reach the RUNNING factory tree, but the
live tree is a long-lived deploy branch with local-only commits + uncommitted
runtime state, so a ff/reset is unsafe. The script instead does a surgical
per-file ``git checkout origin/main -- <factory file>`` of only the changed
factory source, NEVER touching ``factory/manager/**`` or ``bench/**`` (forbidden
self-edit).

These tests exercise the ``--dry-run`` path (file selection + forbidden-path
exclusion) against a real synthetic git repo — no ``uv``/``systemctl`` needed,
since dry-run stops before the import-gate/commit/restart.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deploy-factory-from-main.sh"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=str(cwd), capture_output=True, text=True, check=True, timeout=60
    )


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _make_live_tree(tmp_path: Path) -> Path:
    """A bare 'origin' whose main carries v2 of three files, and a working
    clone on a deploy branch carrying v1 — mirroring the live factory tree
    drifting behind its own origin/main."""
    origin = tmp_path / "origin.git"
    live = tmp_path / "live"
    _run(["git", "init", "-q", "--bare", "--initial-branch=main", str(origin)], cwd=tmp_path)

    # Seed main (v1 everywhere) via a scratch clone, then push v2 on main.
    seed = tmp_path / "seed"
    _run(["git", "init", "-q", "--initial-branch=main", str(seed)], cwd=tmp_path)
    _run(["git", "-C", str(seed), "config", "user.email", "t@e.x"], cwd=tmp_path)
    _run(["git", "-C", str(seed), "config", "user.name", "T E"], cwd=tmp_path)
    for rel in ("factory/chain/foo.py", "factory/manager/bar.py", "bench/baz.py"):
        _write(seed / rel, "V = 1\n")
    _run(["git", "-C", str(seed), "add", "."], cwd=tmp_path)
    _run(["git", "-C", str(seed), "commit", "-q", "-m", "v1"], cwd=tmp_path)
    _run(["git", "-C", str(seed), "remote", "add", "origin", str(origin)], cwd=tmp_path)
    _run(["git", "-C", str(seed), "push", "-q", "-u", "origin", "main"], cwd=tmp_path)

    # Clone as the "live" tree, branch off to a deploy branch (stays on v1).
    _run(["git", "clone", "-q", str(origin), str(live)], cwd=tmp_path)
    _run(["git", "-C", str(live), "config", "user.email", "t@e.x"], cwd=tmp_path)
    _run(["git", "-C", str(live), "config", "user.name", "T E"], cwd=tmp_path)
    _run(["git", "-C", str(live), "checkout", "-q", "-b", "deploy-branch"], cwd=tmp_path)

    # Advance origin/main to v2 for all three files (from the seed clone).
    for rel in ("factory/chain/foo.py", "factory/manager/bar.py", "bench/baz.py"):
        _write(seed / rel, "V = 2\n")
    _run(["git", "-C", str(seed), "commit", "-q", "-am", "v2"], cwd=tmp_path)
    _run(["git", "-C", str(seed), "push", "-q", "origin", "main"], cwd=tmp_path)
    return live


def _dry_run(live: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SCRIPT), "--dry-run"],
        cwd=str(live),
        env={"FACTORY_DIR": str(live), "PATH": __import__("os").environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_dry_run_selects_only_non_forbidden_factory_files(tmp_path: Path) -> None:
    live = _make_live_tree(tmp_path)
    head_before = _run(["git", "rev-parse", "HEAD"], cwd=live).stdout.strip()

    res = _dry_run(live)

    assert res.returncode == 0, res.stdout + res.stderr
    # The ordinary factory source file is selected for deploy...
    assert "factory/chain/foo.py" in res.stdout
    # ...and it is the ONLY one (factory/manager is excluded; bench/ isn't even
    # under the factory/ diff scope, so it's inherently never deployed).
    assert "would deploy 1 changed factory file" in res.stdout
    # The forbidden factory/manager path is surfaced as an alert and skipped.
    assert "FACTORY_SELF_DEPLOY_ALERT" in res.stderr
    assert "factory/manager/bar.py" in res.stderr
    # Neither forbidden path is ever in the apply/deploy list on stdout.
    assert "factory/manager/bar.py" not in res.stdout
    assert "bench/baz.py" not in res.stdout

    # Dry-run mutates nothing: HEAD unchanged, files still v1.
    assert _run(["git", "rev-parse", "HEAD"], cwd=live).stdout.strip() == head_before
    assert (live / "factory/chain/foo.py").read_text() == "V = 1\n"


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
def test_dry_run_noop_when_in_sync(tmp_path: Path) -> None:
    """When the live tree already matches origin/main, it's a clean no-op."""
    live = _make_live_tree(tmp_path)
    # Bring the one deployable file to v2 so nothing differs except forbidden.
    _run(["git", "fetch", "-q", "origin", "main"], cwd=live)
    _run(["git", "checkout", "origin/main", "--", "factory/chain/foo.py"], cwd=live)
    _run(["git", "commit", "-q", "-m", "sync foo", "--", "factory/chain/foo.py"], cwd=live)

    res = _dry_run(live)
    assert res.returncode == 0, res.stdout + res.stderr
    # Only forbidden paths differ now → no deployable files.
    assert "would deploy" not in res.stdout or "would deploy 0" in res.stdout
