"""Independent acceptance-oracle authoring (WS1.2).

This module authors the acceptance test that the ``acceptance-verified`` gate
later runs. The whole point is INDEPENDENCE from the dev:

* Authored from the SPEC ONLY — the direction's acceptance criteria (+ its
  ``flow.md`` / ``api_spec.md`` if present) and the story title/scope. It is
  NEVER given the dev's implementation or the dev's tests.
* Authored EARLY — at story spawn (``handle_stories_spawned``), which runs at
  pm-sync time, long before the dev handler runs on a later tick. Freezing the
  test before the dev starts is the strongest anti-reward-hack posture: the dev
  cannot shape a test that already exists and that it never sees.
* Stored in FACTORY STATE — under ``state/acceptance/<app>/<story_id>/`` — which
  is outside the app repo and outside the per-story dev worktree (the worktree
  is a checkout of the app repo under ``state/worktrees/``; nothing copies
  factory ``state/acceptance/`` into it — see ``factory.chain.worktree``). The
  dev sandbox is handed only ``repo_path`` (the worktree) and never a pointer to
  this path, so it does not receive the acceptance test.

The authored path (relative to the factory root) is recorded on
``StoryRecord.acceptance_test_ref``.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from factory.app_config import AppConfig
from factory.chain.state_machine import StoryRecord, StoryState, is_terminal

if TYPE_CHECKING:
    from factory.directions.parser import Direction

_log = logging.getLogger(__name__)

# Injection seam for tests: an author function takes the assembled spec prompt
# and returns the python source of the acceptance test. Default is the real LLM
# call (``_llm_author``); tests pass a deterministic fake.
AuthorFn = Callable[[str, StoryRecord], str]

_ACCEPTANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["test_file_content"],
    "properties": {"test_file_content": {"type": "string"}},
}

# How many times to retry a flaky author call before giving up for this pass.
# Expected-but-unauthored stories are re-attempted again on later ticks by
# ``reauthor_missing_oracles`` — this just absorbs transient errors in one pass.
_AUTHOR_ATTEMPTS = 3

# How many PASSES (spawn + later tick self-heals) may attempt authoring before the
# story is declared unauthorable. Without this ceiling the tick self-heal retries
# an unauthorable story on EVERY tick forever — ``_AUTHOR_ATTEMPTS`` LLM calls
# every five minutes, unbounded (the repo's rule is that nothing loops more than
# 3 times). Exhausting the ceiling does NOT unblock the story: the gate still
# blocks (fail-safe) and names the exhaustion, so the operator fixes the spec or
# the harness instead of the factory quietly burning money.
_MAX_AUTHOR_PASSES = 3

# Basename of the copy the gate drops into the merge-candidate checkout. Shared
# with the gate and with ``factory.chain.worktree`` so the sweep that removes a
# leaked copy and the code that creates it can never disagree on the pattern.
ORACLE_COPY_PREFIX = "test_acceptance_oracle_"
# Matches the copy AND its compiled ``__pycache__`` sibling; used both for the
# sweep and for the checkout-local git exclude.
ORACLE_COPY_GLOB = f"{ORACLE_COPY_PREFIX}*"

# Directories never worth walking when sweeping a checkout for a leaked oracle.
# ``__pycache__`` is deliberately NOT skipped: running the oracle leaves a
# ``__pycache__/test_acceptance_oracle_<id>.cpython-*.pyc`` next to it, which is a
# compiled copy of the hidden test and is staged by ``git add -A`` exactly like the
# source would be (caught by this module's own leak test, 2026-08-05).
_SWEEP_SKIP_DIRS = frozenset(
    {".git", "node_modules", ".venv", "venv", ".next", "dist", "build",
     ".mypy_cache", ".ruff_cache", "target"}
)

# Stories that will never be dispatched or merged again — no point authoring an
# oracle for them, and doing so would fire hundreds of LLM calls the moment an app
# opts in (165 historical stories in the live DB). Everything terminal EXCEPT
# ``ci_pending``, which is terminal only by omission from the transition table yet
# is still a MERGEABLE state the acceptance gate evaluates (the trap that made an
# earlier fix use an allowlist instead of ``is_terminal``).
_NO_ORACLE_STATES = frozenset(
    {s.value for s in StoryState if is_terminal(s)} - {StoryState.CI_PENDING.value}
)


def acceptance_dir(software_factory_root: Path, app: str, story_id: int | None) -> Path:
    """The per-story directory holding the stored acceptance test."""
    sid = int(story_id) if story_id is not None else 0
    return Path(software_factory_root) / "state" / "acceptance" / app / str(sid)


def sweep_leaked_oracles(tree: Path) -> list[str]:
    """Delete every copied-in acceptance oracle found inside ``tree``.

    The gate copies the oracle INTO the merge-candidate checkout — which is the
    story's own dev worktree (``auto_merge._story_worktree`` returns the same
    tree ``handlers._writing_worktree`` hands the dev). If the process dies
    between the copy and the unlink, the oracle sits in the dev's tree, where the
    dev can read it (independence gone) and where the chain's deterministic
    ``git add -A`` commit (``handlers._commit_green_dev_work``) would bake it into
    the PR. Called both before every gate run and on every worktree ensure, so
    neither the dev nor a later gate run ever sees a stale copy.

    Sweeps the compiled ``__pycache__/…​.pyc`` too — pytest leaves one next to the
    copy, it contains the same assertions, and ``git add -A`` stages it.

    NEVER deletes a file git TRACKS. Otherwise this sweep would itself be a
    destructive mechanism: a legitimately committed app test that happens to match
    the pattern would be removed from the checkout, and the chain's later
    ``git add -A`` would commit the deletion. A tracked match is logged instead —
    it cannot be a leak (a leak is untracked by construction, and the git exclude
    the gate installs keeps it that way).

    Returns the relative paths removed (usually empty). Never raises.
    """
    root = Path(tree)
    candidates: list[Path] = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SWEEP_SKIP_DIRS]
            candidates.extend(
                Path(dirpath) / name
                for name in filenames
                if name.startswith(ORACLE_COPY_PREFIX)
            )
    except OSError:
        return []
    if not candidates:
        return []

    rels = [p.relative_to(root).as_posix() for p in candidates]
    tracked = _git_tracked(root, rels)
    removed: list[str] = []
    for p, rel in zip(candidates, rels, strict=True):
        if rel in tracked:
            _log.warning(
                "acceptance-oracle sweep: %s in %s is TRACKED by git — leaving it "
                "alone (a leaked oracle copy is never tracked)", rel, root,
            )
            continue
        try:
            p.unlink()
            removed.append(rel)
        except OSError:  # noqa: PERF203 - per-file, keep sweeping
            continue
    return removed


def _git_tracked(tree: Path, rel_paths: list[str]) -> set[str]:
    """Which of ``rel_paths`` git tracks in ``tree`` (empty set when unknowable)."""
    try:
        proc = subprocess.run(  # noqa: S603,S607 - fixed argv, no shell
            ["git", "ls-files", "-z", "--", *rel_paths],
            cwd=str(tree),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    return {p for p in proc.stdout.split("\0") if p}


def acceptance_expected_for(app_config: AppConfig, direction: Direction) -> bool:
    """Whether a story under ``direction`` MUST have an acceptance oracle.

    The single source of truth for the required/blocking decision — set at spawn
    INDEPENDENT of whether authoring later succeeds, so a flaky author cannot
    silently downgrade a story to "not required".
    """
    return bool(app_config.gates.acceptance_oracle and direction.acceptance)


def acceptance_expected_for_story(
    story: StoryRecord | None,
    app_config: AppConfig,
    software_factory_root: Path | None,
) -> tuple[bool, str]:
    """Whether ``story`` MUST be gated by an oracle — re-derived, not trusted.

    Returns ``(expected, source)`` where ``source`` explains the decision.

    ``StoryRecord.acceptance_expected`` is a CACHE of a decision that is really a
    property of the SPEC ("the app opted in AND this story's direction carries
    acceptance criteria"). Trusting the cache alone is a silent fail-open: the
    flag is written by a best-effort DB write that swallows its own errors, so a
    failed write left ``acceptance_expected=0`` on a story that should be gated —
    and both the gate and ``required_gate_labels`` would then treat it as "no
    acceptance criteria, not applicable" and ship it un-gated. So the flag is only
    ever used to say YES; a NO is re-derived from the direction on disk.

    Fail-safe when the direction cannot be resolved under an opted-in app: we
    cannot establish that the story is EXEMPT, so it counts as expected (source
    ``direction_unresolvable``) and the gate blocks with that reason rather than
    waving the story through.
    """
    if not app_config.gates.acceptance_oracle:
        return False, "not_opted_in"
    if story is None:
        # Opted in but no StoryRecord: nothing to resolve a spec from, and no
        # oracle can exist. Cannot verify → treat as expected so the gate blocks.
        return True, "no_story_record"
    if story.acceptance_expected:
        return True, "flag"
    if story.acceptance_test_ref:
        return True, "ref"
    if software_factory_root is None:
        return True, "no_factory_root"
    try:
        from factory.chain.handlers import find_direction_for_story

        direction = find_direction_for_story(story, Path(software_factory_root))
    except Exception:  # noqa: BLE001 - a lookup error must not wave the story through
        return True, "direction_lookup_error"
    if direction is None:
        return True, "direction_unresolvable"
    if direction.acceptance:
        return True, "spec"
    return False, "no_acceptance_criteria"


def _emit(
    software_factory_root: Path,
    event: str,
    story: StoryRecord,
    **extra: Any,
) -> None:
    """Best-effort visibility event on the ``acceptance`` stream (never raises)."""
    try:
        from factory.manager.signals import write_event

        write_event(
            "acceptance",
            {"event": event, "app": story.app, "story_id": story.id,
             "direction_id": story.direction_id, **extra},
            software_factory_root=software_factory_root,
        )
    except Exception:  # noqa: BLE001 - telemetry path, never fail the caller
        pass


def _read_artifact(direction: Direction, name: str, present: bool) -> str:
    if not present:
        return ""
    try:
        return (direction.dir_path / name).read_text(encoding="utf-8").rstrip()
    except OSError:
        return ""


def _property_mode_block(acceptance_lines: list[str]) -> list[str]:
    """Structured EARS decomposition for the property-mode section, or [].

    When one or more acceptance criteria are EARS-shaped (``WHEN ... THE SYSTEM
    SHALL ...``), each ``SHALL`` names an INVARIANT rather than a single example,
    so the author should encode it as a Hypothesis property asserted over many
    generated inputs. This block hands the author the already-split
    trigger / precondition / system / response for each such criterion; non-EARS
    criteria are omitted here and remain in example-mode (the criteria block
    above still lists them verbatim). Returns [] when no AC is EARS-shaped, in
    which case the author sees no property-mode instructions and writes example
    tests exactly as before — the conservative, opt-in fallback.
    """
    from factory.chain.ears import split_acs

    pairs = split_acs(acceptance_lines)
    if not any(clause is not None for _, clause in pairs):
        return []

    lines = [
        "## Property-based testing mode (EARS criteria)",
        "",
        "One or more acceptance criteria are written in EARS form",
        "(`WHEN <trigger>, [GIVEN <precondition>,] THE <system> SHALL <response>`).",
        "In EARS the `SHALL` response is an INVARIANT, not one example — so for",
        "EACH criterion below, write a **Hypothesis property test**: decorate a",
        "property with `@given(...)` over `hypothesis.strategies` inputs that",
        "cover the trigger space, and assert the `SHALL` response holds for every",
        "generated input. Import `hypothesis` and `hypothesis.strategies as st`.",
        "Let Hypothesis shrink to a minimal counterexample on failure — do not",
        "wrap the assertion in try/except. Name each property `test_<ac_id>_...`",
        "so a failure names the criterion. For any criterion NOT listed here",
        "(not EARS-shaped), fall back to a normal example-based assertion.",
        "",
        "Structured decomposition of the EARS criteria:",
        "",
    ]
    n = 0
    for raw, clause in pairs:
        if clause is None:
            continue
        n += 1
        label = clause.ac_id or f"AC{n}"
        lines.append(f"{n}. [{label}] (EARS/{clause.kind}) — {raw}")
        if clause.trigger:
            lines.append(f"   - trigger (generate inputs across this): {clause.trigger}")
        if clause.precondition:
            lines.append(f"   - precondition (assume/filter to this): {clause.precondition}")
        if clause.system:
            lines.append(f"   - system under test: {clause.system}")
        lines.append(f"   - invariant to assert (the SHALL response): {clause.response}")
    return lines


def build_spec_prompt(
    story: StoryRecord, direction: Direction, *, harness_hint: str | None = None
) -> str:
    """Assemble the SPEC-ONLY prompt handed to the acceptance author.

    Contains the acceptance criteria verbatim plus any flow.md / api_spec.md the
    direction provides, and the story's title/scope. Deliberately contains NO
    implementation and NO dev tests — the author must write blind to the code.

    When any acceptance criterion is EARS-shaped, a property-mode block is
    appended (see :func:`_property_mode_block`) that decomposes each such
    criterion and instructs the author to encode its ``SHALL`` invariant as a
    Hypothesis property test. This is additive and spec-derived only — the block
    is built entirely from the acceptance criteria, so independence from the dev
    is preserved, and it is absent (example-mode) whenever no AC is EARS-shaped.

    ``harness_hint`` (``gates.acceptance_harness_hint``) is the app's OPERATOR-
    WRITTEN repo-layout facts: which module exposes the app, which client to drive
    it with, where the tests run from. It is required for the output to be
    runnable at all — the first real authoring run (2026-08-05) produced a test
    that guessed ``sacrifice.main`` / ``main`` / ``app.main`` and died with
    ``No module named 'app'``, because nothing told the author where the app
    lives. It is NOT an independence leak: it is the same static layout any
    reader of the repo's README can see, is identical for every story in the app,
    and contains none of the dev's implementation or tests for THIS story.
    """
    acceptance_lines = list(direction.acceptance)
    ac_block = (
        "\n".join(f"{i + 1}. {ac}" for i, ac in enumerate(acceptance_lines))
        if acceptance_lines
        else "(no explicit acceptance criteria)"
    )
    flow_text = _read_artifact(direction, "flow.md", direction.has_flow)
    api_text = _read_artifact(direction, "api_spec.md", direction.has_api_spec)

    parts = [
        "## Story under acceptance",
        f"- Title: {story.title}",
        f"- Scope: {story.scope}",
        f"- App: {story.app}",
        "",
        "## Acceptance criteria (verbatim from the direction — the SPEC)",
        "",
        ac_block,
    ]
    if flow_text:
        parts += ["", "## Flow (verbatim from the direction)", "", flow_text]
    if api_text:
        parts += ["", "## API spec (verbatim from the direction)", "", api_text]
    if harness_hint and harness_hint.strip():
        parts += [
            "",
            "## Harness (how to import and drive this app — repo layout, NOT an implementation)",
            "",
            "These are stable facts about where the app lives and how its test suite",
            "runs. They are the same for every story in this app and tell you nothing",
            "about how THIS story was implemented. Your file is executed inside this",
            "harness, so import exactly as described rather than guessing module paths.",
            "",
            harness_hint.strip(),
        ]
    property_block = _property_mode_block(acceptance_lines)
    if property_block:
        parts += ["", *property_block]
    return "\n".join(parts)


def _llm_author(
    spec_prompt: str,
    story: StoryRecord,
    *,
    software_factory_root: Path | None = None,
    db_path: Path | None = None,
) -> str:
    """Real author: call the ``acceptance_author`` persona with the spec only.

    ``software_factory_root`` / ``db_path`` are threaded through so the call lands
    in the factory's OWN run ledger and prompt/telemetry streams. Without them the
    spend of every acceptance-authoring call was attributed to whatever cwd the
    process happened to have, i.e. invisible to ``factory audit``.
    """
    from factory.model_router import route
    from factory.runner import _read_persona_prompt, text_run

    persona = "acceptance_author"
    persona_prompt = _read_persona_prompt(persona)
    full_prompt = (
        f"{persona_prompt.rstrip()}\n\n"
        "---\n\n"
        "## Input (SPEC ONLY — you are blind to any implementation)\n\n"
        f"{spec_prompt}\n\n"
        "---\n\n"
        "Return the JSON object with the acceptance test file content."
    )
    result = text_run(
        persona=persona,
        prompt=full_prompt,
        model_id=route(persona),
        schema=_ACCEPTANCE_SCHEMA,
        max_tokens=4096,
        story_id=story.id,
        app=story.app,
        direction_id=story.direction_id,
        software_factory_root=software_factory_root,
        db_path=db_path,
    )
    if not isinstance(result, dict):
        raise RuntimeError("acceptance_author text_run returned a non-dict for schema call")
    content = result.get("test_file_content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("acceptance_author returned empty test_file_content")
    return content


_FENCE_RE = re.compile(r"^\s*```(?:python|py)?\s*\n(?P<body>.*?)\n?```\s*$", re.DOTALL)


class OracleSourceError(ValueError):
    """The author returned something that is not a runnable acceptance test."""


def normalize_oracle_source(content: str) -> str:
    """Return ``content`` as storable python, or raise :class:`OracleSourceError`.

    Nothing validated the author's output before it was written to disk, so
    markdown-fenced code, an apology paragraph, or a truncated file was stored as
    the story's oracle and only discovered at merge time as a pytest collection
    error — an expensive FALSE BLOCK (the gate is required, so the story is
    re-dispatched to dev with an identical failure signature until it exhausts its
    retries; observed on stories 148/157 for the analogous env bug). Validating
    here makes a bad response a FAILED AUTHOR ATTEMPT that gets retried, which is
    the cheap and correct place to catch it.

    Checks: non-empty, parses as python, and declares at least one ``test_*``
    function (module-level or in a class). Deliberately does NOT require an
    ``assert``: the persona is allowed to ``pytest.skip`` a criterion that is
    untestable as written, and a wholly-vacuous oracle is caught authoritatively at
    gate time (a run in which nothing passed cannot satisfy the gate).
    """
    if not isinstance(content, str) or not content.strip():
        raise OracleSourceError("empty acceptance test content")
    src = content.strip()
    m = _FENCE_RE.match(src)
    if m:  # the model wrapped the file in a markdown fence
        src = m.group("body").strip()
    if not src:
        raise OracleSourceError("acceptance test content was an empty code fence")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        raise OracleSourceError(f"acceptance test is not valid python: {exc}") from exc
    has_test = any(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )
    if not has_test:
        raise OracleSourceError("acceptance test declares no test_* function")
    return src if src.endswith("\n") else src + "\n"


def _attempts_path(software_factory_root: Path, app: str, story_id: int | None) -> Path:
    return acceptance_dir(software_factory_root, app, story_id) / "attempts.json"


def author_passes(software_factory_root: Path, app: str, story_id: int | None) -> int:
    """How many authoring PASSES this story has already burned (0 when unknown)."""
    try:
        raw = json.loads(
            _attempts_path(software_factory_root, app, story_id).read_text(encoding="utf-8")
        )
        return int(raw.get("passes") or 0)
    except Exception:  # noqa: BLE001 - missing/corrupt sidecar counts as no passes
        return 0


def _record_failed_pass(
    software_factory_root: Path, story: StoryRecord, error: str | None
) -> int:
    """Increment and persist the failed-pass counter; return the new count."""
    n = author_passes(software_factory_root, story.app, story.id) + 1
    try:
        p = _attempts_path(software_factory_root, story.app, story.id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"passes": n, "last_error": error}, indent=2), encoding="utf-8"
        )
    except OSError:  # noqa: BLE001 - the counter is an optimisation, never a gate
        pass
    return n


def author_exhausted(story: StoryRecord | None, software_factory_root: Path | None) -> bool:
    """True when authoring has burned its pass ceiling and must stop retrying."""
    if story is None or software_factory_root is None:
        return False
    return author_passes(Path(software_factory_root), story.app, story.id) >= _MAX_AUTHOR_PASSES


def _persist(story: StoryRecord, software_factory_root: Path, db_path: Path | None) -> bool:
    """Persist the story's acceptance flags. Returns False when the write failed.

    A swallowed failure here is a fail-open (the flag that makes the gate block
    never reaches the DB), so it is now LOUD: logged and emitted on the acceptance
    event stream. It is no longer load-bearing either — the gate and
    ``required_gate_labels`` re-derive expectation from the spec via
    ``acceptance_expected_for_story``, so a lost flag cannot exempt a story.
    """
    try:
        from factory.chain.handlers import persist_story

        persist_story(story, db_path or (Path(software_factory_root) / "state" / "factory.db"))
        return True
    except Exception as exc:  # noqa: BLE001 - flags are set in-memory regardless
        _log.error(
            "acceptance flag PERSIST FAILED for story %s (%s): %r — expectation is "
            "re-derived from the spec at gate time, so this cannot ship un-gated",
            getattr(story, "id", None), story.slug, exc,
        )
        _emit(software_factory_root, "persist_failed", story, error=repr(exc)[:300])
        return False


def author_acceptance_test(
    story: StoryRecord,
    direction: Direction,
    app_config: AppConfig,
    software_factory_root: Path,
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
    author_fn: AuthorFn | None = None,
    force: bool = False,
) -> str | None:
    """Author + store the acceptance oracle for ``story``; return its ref.

    ALWAYS sets ``story.acceptance_expected`` (= app opted in AND the direction
    has ACs) and persists it — INDEPENDENT of whether authoring succeeds. This
    is what makes an authoring failure BLOCK rather than silently ship: the gate
    and ``required_gate_labels`` treat an app that opted in as gated, and
    re-derive per-story applicability from the SPEC, never from a flag that a
    failed DB write could have dropped.

    Returns the stored path (relative to ``software_factory_root``, also written
    to ``story.acceptance_test_ref``) on success, else ``None``:

    * app not opted in / direction has no ACs → expected=False, ref None; and
    * ``dry_run`` (no LLM) → expected set from spec, ref left None (a later
      real tick authors it); and
    * ``story.id`` is None → ref None (an unidentified story would write into the
      shared ``…/0/`` directory and one story would then be gated by another
      story's oracle); and
    * the pass ceiling is exhausted → ref None, no LLM call; and
    * author fails after ``_AUTHOR_ATTEMPTS`` retries → expected stays True, ref
      None → gate BLOCKS and the tick self-heal re-authors later.

    IDEMPOTENT: an oracle that is already stored and readable is NOT re-authored
    (pass ``force=True`` to override). Re-authoring would silently replace a test
    that was frozen before the dev started with one written after — the freeze is
    the anti-reward-hack property, so overwriting it by accident is exactly what
    must not happen (and it would pay for the same test twice).

    Independence is structural: the prompt is SPEC-ONLY (``build_spec_prompt``)
    and the file lands under ``state/acceptance/`` — outside the dev worktree.
    """
    expected = acceptance_expected_for(app_config, direction)
    story.acceptance_expected = expected
    if not expected:
        _persist(story, software_factory_root, db_path)
        return None
    if dry_run:
        # No LLM in dry-run; record the expectation so the gate correctly
        # blocks (expected but no oracle) until a real tick authors it.
        _persist(story, software_factory_root, db_path)
        return None

    root = Path(software_factory_root)
    if story.id is None:
        # Unidentified story: acceptance_dir would collapse to ``…/0/`` and two
        # such stories would share (and overwrite) one oracle. Block instead.
        _persist(story, root, db_path)
        _emit(root, "author_skipped_no_story_id", story)
        _log.warning(
            "acceptance oracle NOT authored for %s: story has no id yet "
            "(would collide in the shared 0/ directory); gate blocks until it does",
            story.slug,
        )
        return None

    if not force and ref_is_readable(story, root):
        # Already frozen. Never re-author over a stored oracle.
        return story.acceptance_test_ref

    if author_exhausted(story, root):
        _persist(story, root, db_path)
        _emit(root, "author_exhausted", story, passes=author_passes(root, story.app, story.id))
        _log.error(
            "acceptance oracle authoring EXHAUSTED for story %s (%s) after %d passes — "
            "the acceptance-verified gate stays blocked; operator must fix the spec "
            "or the app's acceptance harness config",
            story.id, story.slug, _MAX_AUTHOR_PASSES,
        )
        return None

    author = author_fn or _default_author(root, db_path)
    spec_prompt = build_spec_prompt(
        story, direction, harness_hint=app_config.gates.acceptance_harness_hint
    )
    content: str | None = None
    last_err: str | None = None
    for attempt in range(1, _AUTHOR_ATTEMPTS + 1):
        try:
            content = normalize_oracle_source(author(spec_prompt, story))
            break
        except Exception as exc:  # noqa: BLE001 - retry transient author failures
            content = None
            last_err = repr(exc)[:300]
            _log.warning(
                "acceptance author failed (story=%s attempt=%d/%d): %s",
                story.id, attempt, _AUTHOR_ATTEMPTS, last_err,
            )

    if content is None:
        # Expected but authoring flaked. Leave ref None; expected stays True so
        # the gate blocks and reauthor_missing_oracles retries on a later tick —
        # up to _MAX_AUTHOR_PASSES passes, then it stops retrying and stays blocked.
        _persist(story, root, db_path)
        passes = _record_failed_pass(root, story, last_err)
        _emit(
            software_factory_root, "author_failed", story,
            attempts=_AUTHOR_ATTEMPTS, error=last_err, passes=passes,
            exhausted=passes >= _MAX_AUTHOR_PASSES,
        )
        return None

    out_dir = acceptance_dir(software_factory_root, story.app, story.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    test_path = out_dir / "test_acceptance.py"
    test_path.write_text(content, encoding="utf-8")

    rel = test_path.relative_to(Path(software_factory_root))
    story.acceptance_test_ref = str(rel)
    _persist(story, software_factory_root, db_path)
    _emit(software_factory_root, "authored", story, ref=str(rel))
    return str(rel)


def _default_author(software_factory_root: Path, db_path: Path | None) -> AuthorFn:
    """The real LLM author, bound to this factory root's ledger/telemetry."""

    def _author(spec_prompt: str, story: StoryRecord) -> str:
        return _llm_author(
            spec_prompt,
            story,
            software_factory_root=software_factory_root,
            db_path=db_path,
        )

    return _author


def ref_is_readable(story: StoryRecord | None, software_factory_root: Path | None) -> bool:
    """True when the story's stored acceptance test exists on disk AND has content.

    Emptiness counts as unreadable: a zero-byte file (an interrupted write) would
    otherwise pass this check, be copied into the checkout, and make pytest exit 5
    — a block whose reason blamed the app instead of the truncated oracle.
    """
    if story is None or software_factory_root is None:
        return False
    ref = story.acceptance_test_ref
    if not ref:
        return False
    p = Path(ref)
    stored = p if p.is_absolute() else Path(software_factory_root) / p
    try:
        return stored.is_file() and stored.stat().st_size > 0
    except OSError:
        return False


def reauthor_missing_oracles(
    app: str,
    software_factory_root: Path,
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
    author_fn: AuthorFn | None = None,
    max_per_pass: int = 10,
) -> int:
    """Self-heal pass: (re-)author acceptance oracles for stories that are
    EXPECTED to have one but whose stored test is missing (authoring flaked on
    a previous tick). Returns the number newly authored.

    Runs early in the tick, before the story chain advances and before merge
    evaluation — so a story that blocked on ``acceptance-verified`` last tick
    gets its oracle back this tick. Re-authoring is always SPEC-ONLY
    (``build_spec_prompt`` via a freshly-resolved Direction), so it stays blind
    to the dev's code no matter how late it happens — independence is preserved.

    Scope and spend are BOUNDED three ways, because this runs on every tick:

    * only stories that are still live — anything in a resolved/abandoned state
      (``_NO_ORACLE_STATES``) is skipped, so opting an app in does not fire an LLM
      call for each of its already-shipped stories (165 of them in the live DB);
    * only ``max_per_pass`` stories per call; and
    * only stories that have not exhausted ``_MAX_AUTHOR_PASSES``.

    Candidates are NOT limited to ``acceptance_expected=True`` rows. Expectation is
    re-derived from the spec (``acceptance_expected_for_story``) so this also heals
    (a) a story whose flag write failed and (b) every in-flight story that was
    spawned before the operator flipped ``gates.acceptance_oracle`` on — which
    would otherwise sit blocked forever with no oracle and no way to get one.

    Best-effort: never raises. No-op in dry-run (no LLM).
    """
    if dry_run:
        return 0
    root = Path(software_factory_root)
    db = db_path or (root / "state" / "factory.db")
    try:
        from sqlmodel import Session, select

        from factory.chain.handlers import _engine, find_direction_for_story
    except Exception:  # noqa: BLE001
        return 0

    try:
        app_config = _load_app_config(app, root)
    except Exception:  # noqa: BLE001
        return 0
    if not app_config.gates.acceptance_oracle:
        return 0

    try:
        eng = _engine(db)
        with Session(eng) as session:
            candidates = list(
                session.exec(
                    select(StoryRecord).where(StoryRecord.app == app)
                ).all()
            )
    except Exception:  # noqa: BLE001
        return 0

    healed = 0
    for story in candidates:
        if healed >= max_per_pass:
            break
        if story.state in _NO_ORACLE_STATES:
            continue
        if ref_is_readable(story, root):
            continue
        expected, _source = acceptance_expected_for_story(story, app_config, root)
        if not expected:
            continue
        if author_exhausted(story, root):
            continue
        direction = None
        try:
            direction = find_direction_for_story(story, root)
        except Exception:  # noqa: BLE001
            direction = None
        if direction is None:
            _emit(root, "reauthor_no_direction", story)
            continue
        ref = author_acceptance_test(
            story, direction, app_config, root,
            dry_run=False, db_path=db, author_fn=author_fn,
        )
        if ref is not None:
            healed += 1
            _emit(root, "reauthored", story, ref=ref)
    return healed


def _load_app_config(app: str, software_factory_root: Path) -> AppConfig:
    from factory.app_config import load_app_config

    return load_app_config(app, software_factory_root)


__all__ = [
    "ORACLE_COPY_GLOB",
    "ORACLE_COPY_PREFIX",
    "OracleSourceError",
    "acceptance_dir",
    "acceptance_expected_for",
    "acceptance_expected_for_story",
    "author_acceptance_test",
    "author_exhausted",
    "author_passes",
    "build_spec_prompt",
    "normalize_oracle_source",
    "reauthor_missing_oracles",
    "ref_is_readable",
    "sweep_leaked_oracles",
]
