"""Regression guard for the auth route facts in sacrifice's acceptance hint.

``acceptance_harness_hint`` is the ONLY source of app-layout facts the
acceptance author gets: it is deliberately dev-blind (019 AC3 — the oracle runs
out of process and never imports the app tree), so it cannot check a route
against the code the way every other persona can. The hint also instructs it to
use the stated paths "never a guessed variant". A wrong fact here is therefore
not a hint that gets ignored — it is laundered into an authoritative-looking
oracle that 404s at HEAD no matter how correct the implementation is.

That happened: the hint named ``POST /api/auth/register`` and
``POST /api/auth/login``, and neither route has ever existed — the real ones
carry an ``/email`` segment. It stayed invisible because story 172, the only
story the live gate had graded, asserted ``/api/meta`` and never touched auth.

These assertions are about the CONFIG's claims, not about the sacrifice tree
(which is a sibling repo and is not present in CI), so this test is hermetic.
When sacrifice's auth routes genuinely change, update the hint and this test
together — that coupling is the point.

Workstream A1 (docs/BENCHMARK-READINESS-PLAN.md) extends this file with a
MECHANICAL cross-check, additive to the hand-verified assertions above, not a
replacement: every ``METHOD /path`` the hint names, and every required
request-body field it claims for a route, is checked against
``apps/sacrifice/derived/api_surface.json`` — a snapshot AST-parsed from the
real sacrifice tree by ``scripts/generate_sacrifice_api_surface.py`` (method,
path, and pydantic-required-field facts only; no boot, no DB, no import of
the app). That snapshot is checked in because CI never checks out sacrifice
(it lives only at ``/home/k/sacrifice`` on the operator's box) — so the
cross-check test below is hermetic like the rest of this file, and a SEPARATE
test, skipped when that local checkout is absent, re-derives the surface and
asserts the snapshot is not stale against it. Semantic facts the hint states
(plugin-type enums, error vocabulary, response bodies) are NOT covered here
on purpose: sacrifice's routes declare no ``responses=``, so those facts are
not mechanically derivable and stay hand-maintained prose. See A1 in the plan
before adding a semantic assertion here — it is out of scope by design, not
an oversight.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from factory.app_config import load_app_config

_ROOT = Path(__file__).resolve().parents[1]
_SURFACE_PATH = _ROOT / "apps" / "sacrifice" / "derived" / "api_surface.json"
_GENERATOR_PATH = _ROOT / "scripts" / "generate_sacrifice_api_surface.py"
_HTTP_METHODS = "GET|POST|PUT|PATCH|DELETE"

# Verified against sacrifice ``backend/app/routes/auth.py`` (``APIRouter(
# prefix="/api/auth")`` + the ``/email/...`` route decorators) on 2026-08-08.
_REAL_ROUTES = (
    "/api/auth/email/register",
    "/api/auth/email/login",
    "/api/auth/me",
)

# The exact fabrications that shipped. Note ``/api/auth/email/register`` does
# NOT contain ``/api/auth/register`` as a substring, so these stay unambiguous.
_FABRICATED_ROUTES = (
    "/api/auth/register",
    "/api/auth/login",
    "/api/users/me",
)


def _hint() -> str:
    cfg = load_app_config("sacrifice", _ROOT)
    hint = cfg.gates.acceptance_harness_hint
    assert hint, "sacrifice must ship an acceptance_harness_hint"
    return hint


def test_hint_names_the_real_auth_routes() -> None:
    hint = _hint()
    missing = [r for r in _REAL_ROUTES if r not in hint]
    assert not missing, (
        f"acceptance_harness_hint no longer names {missing}. The acceptance "
        "author is dev-blind and cannot recover these from the tree."
    )


def test_hint_does_not_name_routes_that_do_not_exist() -> None:
    hint = _hint()
    present = [r for r in _FABRICATED_ROUTES if r in hint]
    assert not present, (
        f"acceptance_harness_hint names non-existent route(s) {present}. An "
        "oracle built on these 404s at HEAD regardless of the implementation, "
        "blocking every auth-touching story."
    )


# ── A1: mechanical cross-check against the derived route surface ────────────
#
# Everything below parses ``acceptance_harness_hint`` itself (regex over its
# ``METHOD /path`` and JSON-body-literal mentions) rather than hand-listing
# expected facts, so a NEW hand-written fact is checked automatically instead
# of needing its own bespoke assertion the way the auth block above did.


def _load_surface() -> dict:
    """Load the checked-in derived surface. A missing/malformed file FAILS —
    it is never treated as "nothing to check" (that would silently reopen the
    exact drift this test exists to catch)."""
    if not _SURFACE_PATH.exists():
        pytest.fail(
            f"missing derived surface snapshot: {_SURFACE_PATH}. Generate it "
            f"with `uv run python {_GENERATOR_PATH.relative_to(_ROOT)}` and "
            "commit the result."
        )
    try:
        data = json.loads(_SURFACE_PATH.read_text())
    except json.JSONDecodeError as exc:
        pytest.fail(f"{_SURFACE_PATH} is not valid JSON: {exc}")
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes:
        pytest.fail(f"{_SURFACE_PATH} has no parseable 'routes' list")
    return data


def _surface_index(surface: dict) -> dict[tuple[str, str], set[str]]:
    return {
        (r["method"], r["path"]): set(r.get("required_fields") or []) for r in surface["routes"]
    }


def _parse_hint_route_facts(
    hint: str,
) -> tuple[list[tuple[str, str]], dict[tuple[str, str], set[str]]]:
    """Mechanically extract every route the hint mentions, and every required
    request-body field it claims for a route.

    Route mentions: backtick-wrapped ``METHOD /path`` tokens (the hint's own
    convention, e.g. `` `GET /api/health` ``).

    Required-field claims come from two mechanical patterns actually used in
    the hint's prose, associated with the nearest preceding route mention:
      1. A JSON-object literal in backticks appearing BEFORE the bullet's
         ``->`` response arrow (a request body), e.g.
         `` `POST /api/auth/email/register` with `{"email": ..., "password":
         ...}` ``  -- keys of that literal are the claimed required fields.
         A literal AFTER the arrow is a response body and is deliberately
         excluded by scoping the search to the pre-arrow text.
      2. A "REQUIRED fields" bullet with no route mention of its own (the
         goal-creation block): every bare backtick identifier in that bullet
         is a claimed required field for the most-recently-mentioned route.
    Prose that only says "the same JSON body as <other route>" is NOT chased
    (that is a cross-reference, not a mechanically parseable literal) — this
    is a known, accepted limit of the mechanical parse, not a gap to silently
    paper over.
    """
    route_re = re.compile(rf"`({_HTTP_METHODS}) (/[^`\s]+)`")
    json_literal_re = re.compile(r"`\{([^`]*)\}`")
    field_key_re = re.compile(r'"(\w+)"\s*:')
    bare_ident_re = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")

    block_starts = [m.start() for m in re.finditer(r"(?m)^(?:-|  \*) ", hint)]
    assert block_starts, "could not find any bullet in acceptance_harness_hint"
    bounds = block_starts + [len(hint)]
    blocks = [hint[bounds[i] : bounds[i + 1]] for i in range(len(block_starts))]

    mentioned: list[tuple[str, str]] = []
    required: dict[tuple[str, str], set[str]] = defaultdict(set)
    last_route: tuple[str, str] | None = None

    for block in blocks:
        routes_in_block = [(m, p) for m, p in route_re.findall(block)]
        mentioned.extend(routes_in_block)
        if routes_in_block:
            last_route = routes_in_block[-1]
            arrow_idx = block.find("->")
            pre_arrow = block[:arrow_idx] if arrow_idx != -1 else block
            claimed_fields: set[str] = set()
            for lit in json_literal_re.findall(pre_arrow):
                claimed_fields |= set(field_key_re.findall(lit))
            if claimed_fields:
                for route in routes_in_block:
                    required[route] |= claimed_fields
        elif "required fields" in block.lower() and last_route is not None:
            required[last_route] |= set(bare_ident_re.findall(block))

    return mentioned, dict(required)


def test_hint_routes_exist_in_derived_surface() -> None:
    """Every ``METHOD /path`` named in the hint must be a real sacrifice
    route. This is the mechanical, general form of
    ``test_hint_does_not_name_routes_that_do_not_exist`` above — it would have
    caught the fabricated `/api/auth/register` and `/api/auth/login` without
    either of them needing to be hand-listed first."""
    hint = _hint()
    surface = _load_surface()
    index = _surface_index(surface)
    mentioned, _ = _parse_hint_route_facts(hint)
    assert mentioned, "mechanical route-mention parse found nothing to check"
    missing = sorted({r for r in mentioned if r not in index})
    assert not missing, (
        f"acceptance_harness_hint names route(s) {missing} that are not in "
        f"the derived surface ({_SURFACE_PATH.relative_to(_ROOT)}, derived "
        f"from sacrifice@{surface.get('source_commit', '?')[:12]}). Either "
        "the hint has drifted from the real app, or the snapshot is stale — "
        f"regenerate with `uv run python {_GENERATOR_PATH.relative_to(_ROOT)}` "
        "and re-check before assuming the hint is wrong."
    )


def test_hint_required_fields_match_derived_surface() -> None:
    """Every required request-body field the hint claims for a route must
    actually be required on that route's real pydantic body model. This is
    the mechanical form of the goal-creation incident (#277/#278): a hint
    that invents or drops a required field is laundered into an oracle that
    422s (or wrongly accepts) at HEAD no matter how correct the dev's
    implementation is."""
    hint = _hint()
    surface = _load_surface()
    index = _surface_index(surface)
    mentioned, required_claims = _parse_hint_route_facts(hint)
    assert required_claims, "mechanical required-field parse found nothing to check"
    errors = []
    for route, claimed in required_claims.items():
        if route not in index:
            continue  # already reported by test_hint_routes_exist_in_derived_surface
        real_required = index[route]
        drifted = sorted(claimed - real_required)
        if drifted:
            errors.append(
                f"{route[0]} {route[1]}: hint claims required field(s) "
                f"{drifted}, but the derived surface says the required "
                f"fields are {sorted(real_required)}"
            )
    assert not errors, "\n".join(errors)


def test_api_surface_snapshot_is_not_stale() -> None:
    """Local/operator-box-only: re-derive the surface from the real sacrifice
    checkout and confirm the checked-in snapshot names the same routes.

    Skipped (loudly, with a reason) when no local sacrifice checkout exists —
    that is the normal case in CI, which never checks out the sacrifice repo.
    This is the ONLY test in this file that may skip; every other assertion
    here is hermetic against the checked-in config/snapshot and must run
    everywhere, including CI.
    """
    app_root = Path(os.environ.get("SACRIFICE_APP_ROOT", "/home/k/sacrifice"))
    if not app_root.is_dir():
        pytest.skip(
            f"no local sacrifice checkout at {app_root} (expected in CI; set "
            "SACRIFICE_APP_ROOT to point at one to run this check)"
        )

    spec = importlib.util.spec_from_file_location("generate_sacrifice_api_surface", _GENERATOR_PATH)
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    # Register before exec: the module defines `@dataclass` classes, and
    # dataclasses' postponed-annotation resolution looks itself up via
    # `sys.modules[cls.__module__]` — skipping this raises AttributeError
    # deep inside `dataclasses._is_type` on an unrelated-looking line.
    sys.modules[spec.name] = generator
    spec.loader.exec_module(generator)

    fresh = generator.build_surface(app_root)
    snapshot = _load_surface()
    fresh_routes = {(r["method"], r["path"]) for r in fresh["routes"]}
    snap_routes = {(r["method"], r["path"]) for r in snapshot["routes"]}
    added = sorted(fresh_routes - snap_routes)
    removed = sorted(snap_routes - fresh_routes)
    assert not added and not removed, (
        f"{_SURFACE_PATH.relative_to(_ROOT)} is stale against "
        f"{app_root} @ {fresh.get('source_commit', '?')[:12]}: "
        f"added={added} removed={removed}. Regenerate with "
        f"`uv run python {_GENERATOR_PATH.relative_to(_ROOT)} "
        f"--app-root {app_root}` and commit the result."
    )
