"""Tests for D018 — machine-written state.yaml and stories/*.md are gitignored.

Verifies:
- apps/*/directions/*/state.yaml is gitignored (AC1.1, AC1.2)
- apps/*/stories/*.md is gitignored (AC2.1, AC2.2)
- Files still written to disk (AC3.1, AC3.2, AC3.3)
- Already-tracked copies removed from index (AC4.1, AC4.2)
- direction.md, flow.md, api_spec.md, artifacts/, context/*.md stay tracked
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    """Run a git command in *repo* and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=10,
    )
    result.check_returncode()
    return result.stdout


def _init_temp_repo(tmp_path: Path) -> Path:
    """Create a temp git repo with initial commit, return repo root."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@factory.local")
    _git(repo, "config", "user.name", "Test Factory")
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial commit")
    return repo


def _write_gitignore(repo: Path, rules: str) -> None:
    """Write (overwrite) the .gitignore at the repo root with *rules*."""
    (repo / ".gitignore").write_text(rules, encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "update gitignore")


def _porcelain(repo: Path) -> str:
    """Return ``git status --porcelain`` output."""
    return _git(repo, "status", "--porcelain")


# ---------------------------------------------------------------------------
# AC1.1, AC1.2: state.yaml gitignored after tick
# ---------------------------------------------------------------------------


class TestStateYamlGitignored:
    """AC1.1, AC1.2: WHEN a tick changes a direction's status, state.yaml is
    gitignored and git status is clean."""

    def test_state_yaml_dirty_without_ignore_rule(self, tmp_path: Path) -> None:
        """state.yaml dirties git status BEFORE the ignore rule exists."""
        repo = _init_temp_repo(tmp_path)

        # Set up canonical direction directory layout.
        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add direction.md")

        # Simulate a tick writing state.yaml.
        state = {"status": "pm-validated", "created_at": "2026-01-01T00:00:00Z"}
        (direction_dir / "state.yaml").write_text(
            yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
        )

        # Without the ignore rule, git status should show the file.
        porcelain = _porcelain(repo)
        assert porcelain != "", (
            "state.yaml should dirty git status without ignore rule"
        )
        assert "state.yaml" in porcelain

    def test_state_yaml_clean_with_ignore_rule(self, tmp_path: Path) -> None:
        """state.yaml does NOT dirty git status AFTER the ignore rule exists."""
        repo = _init_temp_repo(tmp_path)

        # Set up canonical direction directory layout.
        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add direction.md")

        # Add the ignore rule.
        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n", encoding="utf-8"
        )
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-m", "add gitignore")

        # Simulate a tick writing state.yaml.
        state = {"status": "pm-validated", "created_at": "2026-01-01T00:00:00Z"}
        (direction_dir / "state.yaml").write_text(
            yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
        )

        # With the ignore rule, git status should be clean.
        porcelain = _porcelain(repo)
        assert porcelain == "", (
            f"state.yaml should be gitignored, but git status shows:\n{porcelain}"
        )

    def test_state_yaml_still_on_disk_after_ignore(self, tmp_path: Path) -> None:
        """AC3.1: state.yaml is still WRITTEN to disk even though gitignored."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add direction.md")

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n", encoding="utf-8"
        )
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-m", "add gitignore")

        # Simulate a tick writing state.yaml.
        state = {"status": "pm-validated", "created_at": "2026-01-01T00:00:00Z"}
        state_path = direction_dir / "state.yaml"
        state_path.write_text(
            yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
        )

        # File exists on disk even though git status is clean.
        assert state_path.exists(), "state.yaml must exist on disk"
        assert state_path.is_file(), "state.yaml must be a regular file"
        loaded = yaml.safe_load(state_path.read_text(encoding="utf-8"))
        assert loaded["status"] == "pm-validated"


# ---------------------------------------------------------------------------
# AC2.1, AC2.2: stories/*.md gitignored after tick
# ---------------------------------------------------------------------------


class TestStoriesMarkdownGitignored:
    """AC2.1, AC2.2: WHEN a tick spawns or advances a story, stories/*.md is
    gitignored and git status is clean."""

    def test_story_md_dirty_without_ignore_rule(self, tmp_path: Path) -> None:
        """stories/*.md dirties git status BEFORE the ignore rule exists."""
        repo = _init_temp_repo(tmp_path)

        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)
        # Pre-populate with a committed .gitkeep so the dir itself is tracked.
        (stories_dir / ".gitkeep").write_text("", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add stories dir")

        # Simulate a tick spawning a story.
        story_path = stories_dir / "42-test-story.md"
        story_path.write_text("# Story: Test\n\nAC: test\n", encoding="utf-8")

        # Without the ignore rule, git status should show the file.
        porcelain = _porcelain(repo)
        assert porcelain != "", (
            "stories/*.md should dirty git status without ignore rule"
        )
        assert "test-story.md" in porcelain

    def test_story_md_clean_with_ignore_rule(self, tmp_path: Path) -> None:
        """stories/*.md does NOT dirty git status AFTER the ignore rule exists."""
        repo = _init_temp_repo(tmp_path)

        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)
        (stories_dir / ".gitkeep").write_text("", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add stories dir")

        # Add the ignore rule.
        (repo / ".gitignore").write_text(
            "apps/*/stories/*.md\n", encoding="utf-8"
        )
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-m", "add gitignore")

        # Simulate a tick spawning a story.
        story_path = stories_dir / "42-test-story.md"
        story_path.write_text("# Story: Test\n\nAC: test\n", encoding="utf-8")

        # With the ignore rule, git status should be clean.
        porcelain = _porcelain(repo)
        assert porcelain == "", (
            f"stories/*.md should be gitignored, but git status shows:\n{porcelain}"
        )

    def test_story_md_still_on_disk_after_ignore(self, tmp_path: Path) -> None:
        """AC3.2: stories/*.md is still WRITTEN to disk even though gitignored."""
        repo = _init_temp_repo(tmp_path)

        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)
        (stories_dir / ".gitkeep").write_text("", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add stories dir")

        (repo / ".gitignore").write_text(
            "apps/*/stories/*.md\n", encoding="utf-8"
        )
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-m", "add gitignore")

        story_path = stories_dir / "42-test-story.md"
        story_path.write_text("# Story: Test\n\nAC: test\n", encoding="utf-8")

        # File exists on disk even though git status doesn't show it.
        assert story_path.exists(), "stories/*.md must exist on disk"
        assert story_path.is_file(), "stories/*.md must be a regular file"
        content = story_path.read_text(encoding="utf-8")
        assert "Story: Test" in content


# ---------------------------------------------------------------------------
# AC4.1, AC4.2: Already-tracked copies removed from index
# ---------------------------------------------------------------------------


class TestUntrackPreviouslyCommitted:
    """AC4.1, AC4.2: Already-committed copies removed from tracking, working
    tree stops showing them as modified."""

    def test_git_rm_cached_removes_tracking_preserves_disk(self, tmp_path: Path) -> None:
        """git rm --cached removes from index but keeps file on disk."""
        repo = _init_temp_repo(tmp_path)

        # Create and commit a direction with state.yaml (simulating the
        # pre-D018 state where these files were tracked).
        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")
        state_path = direction_dir / "state.yaml"
        state_path.write_text("status: created\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add direction with tracked state.yaml")

        # Verify it IS tracked.
        tracked = _git(repo, "ls-files", "--", "apps/*/directions/*/state.yaml")
        assert "state.yaml" in tracked

        # Now do git rm --cached (the fix this story applies).
        _git(repo, "rm", "--cached", "--", "apps/*/directions/*/state.yaml")
        _git(repo, "commit", "-m", "untrack machine-written state.yaml")

        # After rm --cached, file still exists on disk.
        assert state_path.exists(), "state.yaml must still exist on disk"

        # But git no longer tracks it.
        tracked_after = _git(
            repo, "ls-files", "--", "apps/*/directions/*/state.yaml"
        )
        assert tracked_after.strip() == "", (
            f"state.yaml should no longer be tracked: {tracked_after}"
        )

    def test_untracked_copy_not_shown_as_modified(self, tmp_path: Path) -> None:
        """AC4.2: After untracking, working tree stops showing the file as modified."""
        repo = _init_temp_repo(tmp_path)

        # Create and commit a story file (pre-D018 state).
        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)
        story_path = stories_dir / "42-old-story.md"
        story_path.write_text("# Old Story\n\nAC: test\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add tracked story file")

        # Modify the tracked story — this dirties git status.
        story_path.write_text("# Old Story (modified)\n\nAC: test\n", encoding="utf-8")
        porcelain_before = _porcelain(repo)
        assert "old-story.md" in porcelain_before, (
            "modified tracked story should appear in porcelain"
        )

        # Undo the modification, then untrack + ignore.
        story_path.write_text("# Old Story\n\nAC: test\n", encoding="utf-8")
        _git(repo, "checkout", "--", "apps/factory/stories/42-old-story.md")

        (repo / ".gitignore").write_text(
            "apps/*/stories/*.md\n", encoding="utf-8"
        )
        _git(repo, "rm", "--cached", "--", "apps/*/stories/*.md")
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-m", "untrack stories/*.md and add gitignore")

        # Now modify the file again — git status should be clean because
        # it's both untracked AND gitignored.
        story_path.write_text("# Old Story (modified again)\n\nAC: test\n", encoding="utf-8")
        porcelain_after = _porcelain(repo)
        assert porcelain_after == "", (
            f"untracked+gitignored file should not dirty status:\n{porcelain_after}"
        )
        # File still on disk.
        assert story_path.exists()


# ---------------------------------------------------------------------------
# Guard: direction.md, flow.md, api_spec.md, artifacts/, context/*.md stay tracked
# ---------------------------------------------------------------------------


class TestHumanAuthoredArtifactsStayTracked:
    """Guard scope boundaries: human-authored direction artifacts are NOT
    gitignored."""

    def test_direction_md_still_tracked(self, tmp_path: Path) -> None:
        """direction.md is NOT gitignored by the new rules."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")

        # Apply the story's gitignore rules.
        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add direction.md and gitignore")

        # direction.md must be tracked.
        tracked = _git(repo, "ls-files", "--", "apps/*/directions/*/direction.md")
        assert "direction.md" in tracked, (
            "direction.md must remain tracked (human-authored)"
        )

    def test_flow_md_still_tracked(self, tmp_path: Path) -> None:
        """flow.md is NOT gitignored by the new rules."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "flow.md").write_text("# Flow\n", encoding="utf-8")

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add flow.md and gitignore")

        tracked = _git(repo, "ls-files", "--", "apps/*/directions/*/flow.md")
        assert "flow.md" in tracked, (
            "flow.md must remain tracked (human-authored)"
        )

    def test_api_spec_md_still_tracked(self, tmp_path: Path) -> None:
        """api_spec.md is NOT gitignored by the new rules."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "api_spec.md").write_text("# API Spec\n", encoding="utf-8")

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add api_spec.md and gitignore")

        tracked = _git(repo, "ls-files", "--", "apps/*/directions/*/api_spec.md")
        assert "api_spec.md" in tracked, (
            "api_spec.md must remain tracked (human-authored)"
        )

    def test_context_md_still_tracked(self, tmp_path: Path) -> None:
        """apps/<app>/context/*.md is NOT gitignored by the new rules."""
        repo = _init_temp_repo(tmp_path)

        context_dir = repo / "apps" / "factory" / "context" / "modules"
        context_dir.mkdir(parents=True)
        (context_dir / "dispatch.md").write_text("# Dispatch\n", encoding="utf-8")

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add context doc and gitignore")

        tracked = _git(repo, "ls-files", "--", "apps/*/context/modules/dispatch.md")
        assert "dispatch.md" in tracked, (
            "apps/<app>/context/*.md must remain tracked"
        )

    def test_artifacts_dir_not_tracked_but_gitkeep_is(self, tmp_path: Path) -> None:
        """artifacts/ contents are gitignored (existing rule), .gitkeep stays tracked."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        artifacts_dir = direction_dir / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / ".gitkeep").write_text("", encoding="utf-8")

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n"
            "apps/*/directions/*/artifacts/**\n"
            "!apps/*/directions/*/artifacts/.gitkeep\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add artifacts and gitignore")

        tracked = _git(repo, "ls-files", "--", "apps/*/directions/*/artifacts/.gitkeep")
        assert ".gitkeep" in tracked, (
            "artifacts/.gitkeep must remain tracked"
        )


# ---------------------------------------------------------------------------
# Combined scenario: both state.yaml and stories/*.md gitignored simultaneously
# ---------------------------------------------------------------------------


class TestCombinedTickSimulation:
    """Simulate a full tick: direction status change AND story advance/spawn.
    Both artifact types must be gitignored and git status clean."""

    def test_tick_both_artifacts_gitignored_clean_status(self, tmp_path: Path) -> None:
        """After a tick writes both state.yaml and stories/*.md, git status is clean."""
        repo = _init_temp_repo(tmp_path)

        # Set up direction directory.
        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")

        # Set up stories directory.
        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)

        # Apply the gitignore rules (the production change).
        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "initial setup with gitignore")

        # Simulate a tick: write state.yaml and story markdown.
        state = {"status": "pm-validated", "created_at": "2026-01-01T00:00:00Z"}
        (direction_dir / "state.yaml").write_text(
            yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
        )
        (stories_dir / "42-test-story.md").write_text(
            "# Story: Test\n\nAC: test\n", encoding="utf-8"
        )

        # git status must be clean — both artifacts gitignored.
        porcelain = _porcelain(repo)
        assert porcelain == "", (
            f"git status must be clean after tick writes both artifacts:\n{porcelain}"
        )

    def test_tick_both_artifacts_exist_on_disk(self, tmp_path: Path) -> None:
        """AC3.3: After a tick, an operator can read both artifact types on disk."""
        repo = _init_temp_repo(tmp_path)

        direction_dir = repo / "apps" / "factory" / "directions" / "001-test-dir"
        direction_dir.mkdir(parents=True)
        (direction_dir / "direction.md").write_text("# Test\n", encoding="utf-8")

        stories_dir = repo / "apps" / "factory" / "stories"
        stories_dir.mkdir(parents=True)

        (repo / ".gitignore").write_text(
            "apps/*/directions/*/state.yaml\n"
            "apps/*/stories/*.md\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "initial setup with gitignore")

        # Simulate tick output.
        state_yaml_path = direction_dir / "state.yaml"
        state = {"status": "pm-validated"}
        state_yaml_path.write_text(
            yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
        )

        story_path = stories_dir / "42-test-story.md"
        story_path.write_text("# Story: Test\n\nAC: test\n", encoding="utf-8")

        # Operator can read both without querying the database.
        assert state_yaml_path.exists(), "operator must see state.yaml on disk"
        assert story_path.exists(), "operator must see stories/*.md on disk"

        state_content = yaml.safe_load(state_yaml_path.read_text(encoding="utf-8"))
        assert state_content["status"] == "pm-validated"

        story_content = story_path.read_text(encoding="utf-8")
        assert "Story: Test" in story_content