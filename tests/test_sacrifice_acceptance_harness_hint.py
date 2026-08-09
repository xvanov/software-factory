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
"""

from __future__ import annotations

from pathlib import Path

from factory.app_config import load_app_config

_ROOT = Path(__file__).resolve().parents[1]

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
