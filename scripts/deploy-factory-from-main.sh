#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Factory self-deploy — surgically sync the RUNNING factory tree to
# its own origin/main, so merged loop-1 self-improvements actually
# reach the live ticks/manager instead of drifting undeployed.
# ──────────────────────────────────────────────────────────────────
# WHY this is NOT a plain `git pull`/ff (contrast scripts/auto-redeploy.sh
# for the sacrifice APP): the live factory tree runs on a long-lived
# DEPLOY branch that carries local-only commits + uncommitted runtime
# state (state/**, apps/*/state.yaml). A ff/reset would discard that
# state or fail. So this does a SURGICAL, per-file sync of only the
# changed factory/** source files, committing just those paths.
#
# SAFETY INVARIANTS
#   * Only ever touches files under factory/ (source). Never state/**,
#     apps/**, tests/**, docs, or the working tree at large.
#   * NEVER deploys factory/manager/** or bench/** — those are forbidden
#     to self-edit (DGM anti-gaming); operator PR + manual deploy only.
#     A change there is reported and SKIPPED, never applied.
#   * Handles add / modify / DELETE on main correctly, PER FILE, so one
#     bad path can never wedge the rest.
#   * Import-gates the ACTUAL deployed files (py_compile + import their
#     dotted module paths) before committing; on ANY failure every
#     applied change is reverted to HEAD (added files removed, modified
#     files restored, deleted files restored) and nothing is committed —
#     the tree is verified clean afterwards, so a broken module never
#     reaches the running factory.
#   * Restarts factory-manager only AFTER a clean commit, then verifies
#     it stays active across two checks (chain code is picked up by the
#     next tick regardless; the restart is for shared modules the
#     long-lived manager already imported).
#   * Idempotent (in-sync tree = clean no-op), locked, --dry-run preview.
#
# USAGE
#   deploy-factory-from-main.sh            # apply
#   deploy-factory-from-main.sh --dry-run  # report only, mutate nothing
#
# TEST SEAMS (env): IMPORT_GATE_CMD overrides the import gate;
#   SKIP_MANAGER_RESTART=1 skips the systemctl restart. Used only by
#   tests/test_factory_self_deploy.py — never set in production.
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

FACTORY_DIR="${FACTORY_DIR:-/home/k/software-factory}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"
MANAGER_UNIT="${MANAGER_UNIT:-factory-manager.service}"
LOCK_FILE="${LOCK_FILE:-/tmp/factory-self-deploy.lock}"
LOCK_STALE_MINUTES="${LOCK_STALE_MINUTES:-30}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

LOG_PREFIX="[factory-self-deploy]"
log()   { echo "$LOG_PREFIX $(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }
alert() {
  echo "FACTORY_SELF_DEPLOY_ALERT: $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >&2
  logger -t factory-self-deploy -p daemon.err "ALERT: $*" 2>/dev/null || true
}

REMOTE_REF="$GIT_REMOTE/$GIT_BRANCH"

# Does path $1 exist in tree-ish $2?  (git cat-file -e <ref>:<path>)
_in_tree() { git cat-file -e "$2:$1" 2>/dev/null; }

# Revert one applied path back to its HEAD state (added→remove, else restore).
_revert_one() {
  local f="$1"
  if _in_tree "$f" HEAD; then
    git checkout HEAD -- "$f" 2>/dev/null || true
  else
    # Was newly added on main (absent at HEAD) → remove entirely.
    git rm -f --quiet -- "$f" 2>/dev/null || rm -f "$f"
    git reset --quiet -- "$f" 2>/dev/null || true
  fi
}

# ── --dry-run mutates NOTHING (no lock write, no stale-lock rm) ──────
if [ "$DRY_RUN" -eq 0 ]; then
  if [ -f "$LOCK_FILE" ]; then
    if [ -n "$(find "$LOCK_FILE" -mmin +"$LOCK_STALE_MINUTES" 2>/dev/null)" ]; then
      log "breaking stale lock $LOCK_FILE"
      rm -f "$LOCK_FILE"
    else
      log "another run holds $LOCK_FILE — exiting"
      exit 0
    fi
  fi
  echo "$$" > "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT
fi

cd "$FACTORY_DIR"

git fetch --quiet "$GIT_REMOTE" "$GIT_BRANCH" || { alert "git fetch failed"; exit 1; }

# ── Changed factory/** source files (working tree vs main) ──────────
mapfile -t ALL_CHANGED < <(git diff --name-only "$REMOTE_REF" -- factory/ | grep -E '\.py$' || true)

APPLY=()
SKIPPED_FORBIDDEN=()
for f in "${ALL_CHANGED[@]}"; do
  case "$f" in
    factory/manager/*|bench/*) SKIPPED_FORBIDDEN+=("$f") ;;
    *) APPLY+=("$f") ;;
  esac
done

if [ "${#SKIPPED_FORBIDDEN[@]}" -gt 0 ]; then
  alert "forbidden self-edit paths differ from main and were SKIPPED (operator PR + manual deploy required): ${SKIPPED_FORBIDDEN[*]}"
fi

if [ "${#APPLY[@]}" -eq 0 ]; then
  log "factory/ source already in sync with $REMOTE_REF (nothing to deploy)"
  exit 0
fi

log "would deploy ${#APPLY[@]} changed factory file(s) from $REMOTE_REF:"
printf '  %s\n' "${APPLY[@]}"

if [ "$DRY_RUN" -eq 1 ]; then
  log "--dry-run: no changes applied"
  exit 0
fi

# ── Apply per file (add/modify via checkout; delete-on-main via rm) ──
# Per-file so a single bad path never wedges the rest, and so a file
# removed on main propagates as a deletion instead of aborting.
for f in "${APPLY[@]}"; do
  if _in_tree "$f" "$REMOTE_REF"; then
    if ! git checkout "$REMOTE_REF" -- "$f"; then
      alert "checkout of $f from $REMOTE_REF failed — reverting all, nothing committed"
      for g in "${APPLY[@]}"; do _revert_one "$g"; done
      exit 1
    fi
  else
    # Deleted on main → delete locally (stage the removal).
    git rm -f --quiet -- "$f" 2>/dev/null || rm -f "$f"
  fi
done

# ── Import-gate the ACTUAL deployed files, before committing ────────
# py_compile catches SyntaxError in every deployed file; importing each
# deployed module's dotted path catches import-time errors (bad names,
# broken imports) — far broader than a fixed module whitelist.
if [ -n "${IMPORT_GATE_CMD:-}" ]; then
  GATE_OK=0
  eval "$IMPORT_GATE_CMD" >/tmp/factory-self-deploy-import.log 2>&1 && GATE_OK=1 || GATE_OK=0
else
  # Dotted module paths for the deployed files that still EXIST (deletions are
  # skipped). An ``__init__.py`` imports as its PACKAGE dir (so a broken
  # re-export in it is still caught), not skipped.
  GATE_MODS=()
  GATE_FILES=()
  for f in "${APPLY[@]}"; do
    [ -f "$f" ] || continue
    GATE_FILES+=("$f")
    case "$f" in
      */__init__.py) GATE_MODS+=("$(dirname "$f")") ;;  # import the package
      *) GATE_MODS+=("${f%.py}") ;;
    esac
  done
  GATE_OK=1
  if [ "${#GATE_FILES[@]}" -gt 0 ]; then
    if ! uv run python -m py_compile "${GATE_FILES[@]}" >/tmp/factory-self-deploy-import.log 2>&1; then
      GATE_OK=0
    fi
  fi
  # Whenever ANY file was deployed, import the main entrypoint (catches
  # integration breakage) plus each deployed module's dotted path — run
  # UNCONDITIONALLY on GATE_FILES, not gated on GATE_MODS, so an
  # ``__init__.py``-only deploy is still import-checked.
  if [ "$GATE_OK" -eq 1 ] && [ "${#GATE_FILES[@]}" -gt 0 ]; then
    # e.g. factory/chain/foo -> factory.chain.foo
    PYIMPORT="import importlib, factory.cli; [importlib.import_module(m.replace('/', '.')) for m in __import__('sys').argv[1:]]"
    if ! uv run python -c "$PYIMPORT" "${GATE_MODS[@]}" >>/tmp/factory-self-deploy-import.log 2>&1; then
      GATE_OK=0
    fi
  fi
fi

if [ "$GATE_OK" -ne 1 ]; then
  alert "import gate FAILED — reverting all applied paths, nothing committed. See /tmp/factory-self-deploy-import.log"
  for f in "${APPLY[@]}"; do _revert_one "$f"; done
  # Verify the tree is genuinely clean for the touched paths (fail loud if not).
  if [ -n "$(git status --porcelain -- "${APPLY[@]}")" ]; then
    alert "post-revert tree is NOT clean for: $(git status --porcelain -- "${APPLY[@]}" | tr '\n' ' ') — operator attention needed"
  fi
  exit 1
fi

# ── Commit ONLY the deployed paths (never `git add -A`: runtime state).
# The checkout/`git rm` above already staged each path (modify/add via
# `git checkout <ref> -- f` updates the index; deletion via `git rm`), so a
# pathspec-scoped commit needs no extra `git add` (which would error on a
# now-deleted path). ─────────────────────────────────────────────────
git commit --quiet \
  -m "deploy: auto-sync factory/** from $REMOTE_REF (factory self-deploy)" \
  -m "Files: ${APPLY[*]}" \
  -- "${APPLY[@]}"
log "committed $(git rev-parse --short HEAD)"

# ── Restart the long-lived manager (chain code is picked up next tick;
#    restart is for shared modules the manager already imported) ──────
if [ "${SKIP_MANAGER_RESTART:-0}" = "1" ]; then
  log "SKIP_MANAGER_RESTART=1 — skipping restart (test mode)"
  log "self-deploy complete"
  exit 0
fi

if ! systemctl --user restart "$MANAGER_UNIT" 2>/dev/null; then
  alert "failed to restart $MANAGER_UNIT after committing $(git rev-parse --short HEAD). The code IS canonical (== origin/main); recover with: systemctl --user restart $MANAGER_UNIT"
  exit 1
fi
# Confirm it stays active across two checks (catch a delayed crash).
sleep 2
_active1="$(systemctl --user is-active "$MANAGER_UNIT" 2>/dev/null || true)"
sleep 4
_active2="$(systemctl --user is-active "$MANAGER_UNIT" 2>/dev/null || true)"
if [ "$_active1" = "active" ] && [ "$_active2" = "active" ]; then
  log "restarted $MANAGER_UNIT (active)"
else
  alert "$MANAGER_UNIT not stably active after restart (t+2s=$_active1 t+6s=$_active2) on $(git rev-parse --short HEAD) — operator attention needed"
  exit 1
fi

log "self-deploy complete"
