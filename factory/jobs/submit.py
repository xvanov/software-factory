"""``factory job submit`` — turn a PA job into an operator-approved direction.

What a submit writes, all inside ONE directory that appears atomically
(staged under a dot-name, then ``rename``-d into place so a concurrent tick's
pm-sync can never triage a half-written job):

* ``direction.md`` — built by the same ``creator._build_direction_md`` every
  direction uses, plus the job keys in frontmatter: ``source``,
  ``external_id``, ``pipeline`` (as requested: chain|solo|auto),
  ``delivery`` (as requested, raw, or null) and ``models``.
* ``state.yaml`` — ``status: created``, ``source: <source>`` and a signed
  ``operator_approval`` record (see :func:`_approval_record`).
* ``artifacts/ask.md`` — the ask, verbatim, as evidence.
* optional ``flow.md`` / ``api_spec.md`` from ``--flow-file`` /
  ``--api-spec-file`` (the backpressure gate's inputs; see JOBS-API.md).

Then a ``directions`` row carrying ``source`` (the row is what the approval
gate trusts first; ``state.yaml`` is gitignored and can be lost).
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from factory.app_config import AppConfig, load_app_config
from factory.delivery import effective_level, parse_level
from factory.directions.approval import APPROVAL_KEY
from factory.directions.creator import _build_direction_md, _write_initial_state_yaml
from factory.directions.parser import next_direction_id, parse_direction_dir, slugify
from factory.jobs.common import (
    JobError,
    format_job_id,
    iter_jobs,
    registered_apps,
    state_db_path,
)

PIPELINES: tuple[str, ...] = ("chain", "solo", "auto")
CONCRETE_PIPELINES: tuple[str, ...] = ("chain", "solo")
SUBMITTED_BY = "factory job submit"


@dataclass
class SubmitRequest:
    title: str
    ask: str
    app: str | None = None
    repo: str | None = None
    done: list[str] = field(default_factory=list)
    pipeline: str = "auto"
    delivery: str | None = None
    models: list[str] = field(default_factory=list)
    source: str = "pa"
    external_id: str | None = None
    flow_md: str | None = None
    api_spec_md: str | None = None


# --------------------------------------------------------------------------- #
# Resolution / validation
# --------------------------------------------------------------------------- #


def resolve_repo(root: Path, repo: str) -> str:
    """``owner/name`` → the registered app whose ``config.yaml`` names it."""
    want = repo.strip().lower().removesuffix(".git")
    if want.startswith("https://github.com/"):
        want = want[len("https://github.com/") :]
    matches: list[str] = []
    for app in registered_apps(root):
        try:
            cfg = load_app_config(app, root)
        except Exception:  # noqa: BLE001 - one broken config must not hide the rest
            continue
        if cfg.repo.strip().lower() == want:
            matches.append(app)
    if not matches:
        raise JobError("unknown_repo", f"no registered app for repo {repo!r}")
    if len(matches) > 1:
        raise JobError(
            "ambiguous_repo",
            f"repo {repo!r} is registered by several apps ({', '.join(matches)}); pass --app",
        )
    return matches[0]


def resolve_app(root: Path, app: str | None, repo: str | None) -> tuple[str, AppConfig]:
    if not app and not repo:
        raise JobError("missing_argument", "one of --app or --repo is required")
    if repo:
        from_repo = resolve_repo(root, repo)
        if app and app != from_repo:
            raise JobError(
                "app_repo_mismatch",
                f"--app {app!r} does not match --repo {repo!r} (registered as {from_repo!r})",
            )
        app = from_repo
    assert app is not None
    if app not in registered_apps(root):
        raise JobError("unknown_app", f"no registered app {app!r} (apps/{app}/config.yaml)")
    try:
        cfg = load_app_config(app, root)
    except Exception as exc:  # noqa: BLE001
        raise JobError("invalid_app_config", f"apps/{app}/config.yaml: {exc}") from exc
    return app, cfg


def app_pipeline_default(root: Path, app: str) -> str | None:
    """The app's pipeline default, read from raw config (``pipeline_default``
    or ``pipeline: {default: …}``) so this works before/without an
    ``AppConfig`` field for it. ``None`` when unset or invalid."""
    path = Path(root) / "apps" / app / "config.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(raw, dict):
        return None
    value = raw.get("pipeline_default")
    block = raw.get("pipeline")
    if value is None and isinstance(block, dict):
        value = block.get("default")
    value = str(value).strip().lower() if value else None
    return value if value in CONCRETE_PIPELINES else None


def effective_pipeline(root: Path, app: str, requested: Any) -> str:
    """docs/JOBS-API.md v1: ``auto`` = app default, else ``chain``."""
    req = str(requested or "auto").strip().lower()
    if req in CONCRETE_PIPELINES:
        return req
    return app_pipeline_default(root, app) or "chain"


def _parse_models(items: list[str]) -> dict[str, str]:
    """``["reviewer=azure/x", "dev.hard=azure/y"]`` → mapping, validated."""
    from factory.model_router import all_known_personas

    known = set(all_known_personas())
    out: dict[str, str] = {}
    for item in items:
        persona, sep, model = (item or "").partition("=")
        persona, model = persona.strip(), model.strip()
        if not sep or not persona or not model:
            raise JobError("invalid_model", f"--model must be <persona>=<model_id>, got {item!r}")
        base, _, tier = persona.partition(".")
        if base not in known or (tier and (base != "dev" or tier not in ("standard", "hard"))):
            raise JobError(
                "invalid_model",
                f"unknown persona {persona!r}; one of: {', '.join(sorted(known))} "
                "(dev may be dev.standard / dev.hard)",
            )
        out[persona] = model
    _check_reviewer_independence(out)
    return out


def _check_reviewer_independence(models: dict[str, str]) -> None:
    """Refuse a job whose overrides make the reviewer share a model with dev.

    CLAUDE.md hard guardrail ("Reviewer independence"): the router enforces it
    for routes.yaml; a per-job override must not be a way around it. Checked
    against the ACTIVE provider's routes overlaid with the job's overrides.
    """
    if not any(k == "reviewer" or k.startswith("dev") for k in models):
        return
    from factory.model_router import _dev_tier_models, _load_routes, active_provider

    data = _load_routes()
    provider = active_provider()
    block = "azure_routes" if provider == "azure" else "routes"
    section = dict(data.get(block) or {})
    dev = dict(_dev_tier_models(section))
    if "dev" in models:
        dev = {"standard": models["dev"], "hard": models["dev"]}
    for tier in ("standard", "hard"):
        if f"dev.{tier}" in models:
            dev[tier] = models[f"dev.{tier}"]
    reviewer = models.get("reviewer", section.get("reviewer"))
    clash = sorted(t for t, m in dev.items() if reviewer and m == reviewer)
    if clash:
        raise JobError(
            "invalid_model",
            f"reviewer would share model {reviewer!r} with "
            f"{', '.join('dev.' + t for t in clash)}; reviewer independence is a hard "
            "guardrail — pick a different reviewer or dev model",
        )


def _demote_headings(text: str) -> str:
    """Turn markdown headings in the ask into bold lines.

    The ask is embedded under ``## Why``; a heading inside it would end that
    section early (``parser._parse_why``) or open a fake ``Acceptance
    Criteria`` section. The verbatim ask is kept in ``artifacts/ask.md``.
    """
    return re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", r"**\1**", text)


def _approval_record(source: str, external_id: str | None) -> dict[str, Any]:
    """Every job is pre-approved, deliberately.

    The approval gate (``factory.directions.approval``) exists to stop the
    factory filing work for ITSELF. A job is filed through an operator CLI by a
    human or by the PA acting on a plan its human approved — operator intent,
    so it is recorded as an explicit, signed approval rather than left to
    wait in ``factory inbox`` for a redundant second yes.
    """
    note = f"submitted via '{SUBMITTED_BY}' (source={source}"
    note += f", external_id={external_id})" if external_id else ")"
    return {
        "approved": True,
        "approved_by": f"{SUBMITTED_BY}:{source}",
        "approved_at": datetime.now(UTC).isoformat(),
        "note": note,
    }


@contextlib.contextmanager
def _submit_lock(root: Path) -> Iterator[None]:
    """Serialise submits: id allocation and the idempotency scan must be atomic
    with the write, or two concurrent resubmits create two jobs."""
    lock_path = state_db_path(root).parent / "jobs-submit.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except ImportError:  # pragma: no cover - non-POSIX
        yield
        return
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def find_existing(root: Path, source: str, external_id: str) -> Any:
    for ref in iter_jobs(root):
        if (
            str(ref.meta.get("source") or "") == source
            and str(ref.meta.get("external_id") or "") == external_id
        ):
            return ref
    return None


# --------------------------------------------------------------------------- #
# Submit
# --------------------------------------------------------------------------- #


def submit_job(root: Path, req: SubmitRequest) -> dict[str, Any]:
    """Create (or return the existing) job. Returns the contract's success shape."""
    root = Path(root)
    title = (req.title or "").strip()
    if not title:
        raise JobError("missing_argument", "--title is required")
    ask = (req.ask or "").strip()
    if not ask:
        raise JobError("missing_argument", "one of --ask or --ask-file is required (non-empty)")
    source = (req.source or "").strip()
    if not source:
        raise JobError("missing_argument", "--source must be non-empty")
    external_id = (req.external_id or "").strip() or None

    pipeline = (req.pipeline or "auto").strip().lower()
    if pipeline not in PIPELINES:
        raise JobError("invalid_pipeline", f"--pipeline must be one of {', '.join(PIPELINES)}")
    try:
        requested = parse_level(req.delivery)
    except ValueError as exc:
        raise JobError("invalid_delivery", str(exc)) from exc
    models = _parse_models(req.models)
    app, cfg = resolve_app(root, req.app, req.repo)

    with _submit_lock(root):
        if external_id:
            existing = find_existing(root, source, external_id)
            if existing is not None:
                return _result(root, existing.app, existing.dir_path, existing.meta, created=False)

        direction_id = next_direction_id(app, root)
        slug = slugify(title)
        directions_dir = root / "apps" / app / "directions"
        directions_dir.mkdir(parents=True, exist_ok=True)
        final = directions_dir / f"{direction_id}-{slug}"
        if final.exists():
            raise JobError("conflict", f"direction directory already exists: {final}")
        staging = directions_dir / f".job-staging-{uuid.uuid4().hex[:12]}"
        staging.mkdir()
        try:
            meta = {
                "source": source,
                "external_id": external_id,
                "pipeline": pipeline,
                "delivery": requested.value if requested else None,
                "models": models,
            }
            why = _demote_headings(ask) + (
                f"\n\n_Submitted by `{source}`"
                + (f" (external id `{external_id}`)" if external_id else "")
                + " via `factory job submit`. The requester's verbatim ask is "
                "`artifacts/ask.md`._"
            )
            (staging / "direction.md").write_text(
                _build_direction_md(
                    title=title,
                    type_tag=None,
                    why=why,
                    acceptance=[d for d in req.done if d.strip()],
                    explore=False,
                    extra_frontmatter=meta,
                ),
                encoding="utf-8",
            )
            (staging / "artifacts").mkdir()
            (staging / "artifacts" / "ask.md").write_text(req.ask, encoding="utf-8")
            if req.flow_md and req.flow_md.strip():
                (staging / "flow.md").write_text(req.flow_md, encoding="utf-8")
            if req.api_spec_md and req.api_spec_md.strip():
                (staging / "api_spec.md").write_text(req.api_spec_md, encoding="utf-8")
            _write_initial_state_yaml(staging, source=source)
            state_path = staging / "state.yaml"
            state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
            state[APPROVAL_KEY] = _approval_record(source, external_id)
            state.setdefault("audit", []).append(
                {
                    "ts": state[APPROVAL_KEY]["approved_at"],
                    "by": SUBMITTED_BY,
                    "event": "operator_approved",
                    "details": {"source": source, "external_id": external_id},
                }
            )
            state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
            os.rename(staging, final)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    _record_direction_row(root, app, direction_id, slug, source)
    result = _result(root, app, final, meta, created=True, cfg=cfg)
    return result


def _record_direction_row(root: Path, app: str, direction_id: str, slug: str, source: str) -> None:
    """Write the authoritative ``directions`` row (status ``created`` + source).

    Best-effort: ``state.yaml`` already carries the same facts, so a DB hiccup
    leaves a buildable job, and the gate's fail-safe covers the rest.
    """
    try:
        from sqlmodel import Session

        from factory.directions.schema import upsert_direction
        from factory.directions.watcher import _engine

        with Session(_engine(state_db_path(root))) as session:
            upsert_direction(
                session,
                app,
                direction_id,
                slug,
                "created",
                updated_by=SUBMITTED_BY,
                source=source,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"warning: could not write directions row: {exc!r}", file=sys.stderr)


def _result(
    root: Path,
    app: str,
    dir_path: Path,
    meta: dict[str, Any],
    *,
    created: bool,
    cfg: AppConfig | None = None,
) -> dict[str, Any]:
    from factory.backpressure.validator import validate_direction

    cfg = cfg or load_app_config(app, root)
    direction = parse_direction_dir(app, dir_path)
    requested = meta.get("delivery")
    out: dict[str, Any] = {
        "job_id": format_job_id(app, direction.id),
        "app": app,
        "direction_id": direction.id,
        "direction_path": str(dir_path),
        "pipeline": effective_pipeline(root, app, meta.get("pipeline")),
        "delivery": effective_level(cfg.delivery, requested).value,
        "delivery_requested": requested if requested else None,
        "created": created,
    }
    # Additive (not in the v1 success shape): a job with no flow.md, no
    # api_spec.md and no explore tag fails the backpressure gate
    # deterministically at pm-sync and lands in needs_human. Say so now.
    warnings: list[str] = []
    try:
        validation = validate_direction(direction)
    except Exception:  # noqa: BLE001 - a classifier crash must not fail a submit
        validation = None
    if validation is not None and not validation.is_valid:
        warnings.append(
            "backpressure: pm-sync will mark this job needs-direction (missing: "
            + ", ".join(validation.missing)
            + "); add --flow-file or --api-spec-file, or criteria that name an observable"
        )
    if validation is not None:
        warnings += [f"backpressure: {issue}" for issue in validation.issues]
    out["warnings"] = warnings
    return out
