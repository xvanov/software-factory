"""E6 — the PR-blocking fast lane's exclude manifest cannot rot.

CI's PR lane runs the suite MINUS the files in ``tests/fast_lane_excludes.txt``
(they run post-merge in the full lane). The tiering rule is CAPABILITY, not
speed: a file that boots a server, runs a sandbox, or touches docker belongs
in the full lane — that is where the suite's wall-clock lives (the plan's
measured 380 ms/test average), and it is the plan-sanctioned exclusion set.

Two directions, both pinned:

* every ``test_*.py`` whose text matches a heavy-capability signature must be
  in the manifest — a NEW heavy test file left out of the manifest still runs
  in the PR lane (slow but SAFE); this test flags it so it gets classified
  instead of silently dragging the lane over budget;
* every manifest entry must exist and still match a signature — a stale entry
  is an ``--ignore`` for a file that either vanished or became light, i.e. a
  test silently dropped from the PR lane for no reason.

Deliberate trade, stated: the signature match is textual, so a file that
merely MENTIONS docker in a config string is over-excluded from the PR lane.
It still runs in the full lane; the rule stays mechanically auditable.
"""

from __future__ import annotations

import re
from pathlib import Path

_TESTS_DIR = Path(__file__).parent
_MANIFEST = _TESTS_DIR / "fast_lane_excludes.txt"

# The heavy-capability signatures. Keep in sync with the rationale above and
# with .github/workflows/test.yml's fast-lane step.
_HEAVY_RE = re.compile(
    r"boot_app|stub_app|sandbox_run|docker|uvicorn|http\.server"
    r"|ThreadingHTTPServer|serve_forever|start_server|oracle_boot_fixture"
)


def _manifest_entries() -> list[str]:
    return [
        line.strip()
        for line in _MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _heavy_test_files() -> set[str]:
    out: set[str] = set()
    for p in sorted(_TESTS_DIR.rglob("test_*.py")):
        if p.name == Path(__file__).name:
            continue  # this guard quotes the signatures; it is not heavy
        if _HEAVY_RE.search(p.read_text(encoding="utf-8", errors="replace")):
            out.add(str(p.relative_to(_TESTS_DIR.parent)))
    return out


def test_every_heavy_capability_file_is_in_the_manifest() -> None:
    missing = _heavy_test_files() - set(_manifest_entries())
    assert not missing, (
        "test files with heavy-capability signatures (server boot / sandbox / "
        f"docker) are not in tests/fast_lane_excludes.txt: {sorted(missing)}. "
        "Add them so the PR lane stays under its 60s budget — they still run "
        "in the post-merge full lane."
    )


def test_every_manifest_entry_exists_and_is_still_heavy() -> None:
    entries = _manifest_entries()
    assert entries == sorted(set(entries)), "manifest must be sorted and duplicate-free"
    heavy = _heavy_test_files()
    stale = [e for e in entries if e not in heavy]
    assert not stale, (
        f"stale fast-lane excludes (file gone or no longer heavy): {stale}. "
        "Remove them — each is a test silently dropped from the PR lane."
    )
