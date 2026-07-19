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

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from factory.app_config import AppConfig
from factory.chain.state_machine import StoryRecord

if TYPE_CHECKING:
    from factory.directions.parser import Direction

# Injection seam for tests: an author function takes the assembled spec prompt
# and returns the python source of the acceptance test. Default is the real LLM
# call (``_llm_author``); tests pass a deterministic fake.
AuthorFn = Callable[[str, StoryRecord], str]

_ACCEPTANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["test_file_content"],
    "properties": {"test_file_content": {"type": "string"}},
}


def acceptance_dir(software_factory_root: Path, app: str, story_id: int | None) -> Path:
    """The per-story directory holding the stored acceptance test."""
    sid = int(story_id) if story_id is not None else 0
    return Path(software_factory_root) / "state" / "acceptance" / app / str(sid)


def _read_artifact(direction: Direction, name: str, present: bool) -> str:
    if not present:
        return ""
    try:
        return (direction.dir_path / name).read_text(encoding="utf-8").rstrip()
    except OSError:
        return ""


def build_spec_prompt(story: StoryRecord, direction: Direction) -> str:
    """Assemble the SPEC-ONLY prompt handed to the acceptance author.

    Contains the acceptance criteria verbatim plus any flow.md / api_spec.md the
    direction provides, and the story's title/scope. Deliberately contains NO
    implementation and NO dev tests — the author must write blind to the code.
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
    return "\n".join(parts)


def _llm_author(spec_prompt: str, story: StoryRecord) -> str:
    """Real author: call the ``acceptance_author`` persona with the spec only."""
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
    )
    if not isinstance(result, dict):
        raise RuntimeError("acceptance_author text_run returned a non-dict for schema call")
    content = result.get("test_file_content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("acceptance_author returned empty test_file_content")
    return content


def author_acceptance_test(
    story: StoryRecord,
    direction: Direction,
    app_config: AppConfig,
    software_factory_root: Path,
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
    author_fn: AuthorFn | None = None,
) -> str | None:
    """Author + store the acceptance oracle for ``story``; return its ref.

    Returns the stored path relative to ``software_factory_root`` (also written
    to ``story.acceptance_test_ref`` and persisted), or ``None`` when no oracle
    is authored:

    * app has not opted in (``gates.acceptance_oracle`` False), or
    * the direction has no acceptance criteria (nothing to derive a test from), or
    * ``dry_run`` (no LLM call — the gate stays non-authoritative), or
    * the author call fails (best-effort — spawning must never fail on this).

    Independence is structural: the prompt is SPEC-ONLY (``build_spec_prompt``)
    and the file lands under ``state/acceptance/`` — outside the dev worktree.
    """
    if not app_config.gates.acceptance_oracle:
        return None
    if not direction.acceptance:
        return None
    if dry_run:
        # No LLM in dry-run; leave the ref unset so the gate stays
        # non-authoritative rather than pointing at a stub that could false-pass.
        return None

    author = author_fn or _llm_author
    try:
        spec_prompt = build_spec_prompt(story, direction)
        content = author(spec_prompt, story)
    except Exception:
        # Best-effort: a failed author must not fail story spawn. The story
        # simply gets no oracle (ref stays None → gate not required for it).
        return None

    out_dir = acceptance_dir(software_factory_root, story.app, story.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    test_path = out_dir / "test_acceptance.py"
    test_path.write_text(content, encoding="utf-8")

    rel = test_path.relative_to(Path(software_factory_root))
    story.acceptance_test_ref = str(rel)

    # Persist the ref so the gate can find it on a later tick.
    try:
        from factory.chain.handlers import persist_story

        persist_story(story, db_path or (Path(software_factory_root) / "state" / "factory.db"))
    except Exception:
        # Ref is set on the in-memory record even if persistence hiccups; the
        # caller (handle_stories_spawned) persists the record itself too.
        pass

    return str(rel)


__all__ = [
    "acceptance_dir",
    "author_acceptance_test",
    "build_spec_prompt",
]
