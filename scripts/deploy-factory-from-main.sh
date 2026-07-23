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
# state or fail. So this does a SURGICAL, per-file
# `git checkout origin/main -- <file>` of only the changed factory/**
# source files, committing just those paths.
#
# SAFETY INVARIANTS
#   * Only ever touches files under factory/ (source). Never state/**,
#     apps/**, tests/**, docs, or the working tree at large.
#   * NEVER deploys factory/manager/** or bench/** — those are
#     forbidden to self-edit (DGM anti-gaming); an operator PR + manual
#     deploy is the only path for them. A change there is reported and
#     SKIPPED, never applied.
#   * Import-gates before committing: the candidate tree is imported in
#     a subprocess; on any ImportError/SyntaxError the checkout is
#     reverted and nothing is committed (a broken module must never
#     reach the running factory).
#   * Restarts factory-manager only AFTER a successful, import-clean
#     commit, then verifies it comes back active (chain code is picked
#     up by the next tick process regardless; the restart is for shared
#     modules the long-lived manager already imported).
#   * Idempotent: a tree already equal to origin/main is a clean no-op.
#   * A single lock prevents concurrent runs.
#
# USAGE
#   deploy-factory-from-main.sh            # apply
#   deploy-factory-from-main.sh --dry-run  # report only, mutate nothing
#
# Intended trigger: factory-self-deploy.timer (see the unit shipped
# alongside this script under scripts/systemd/).
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

# ── Locking ────────────────────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
  if [ -n "$(find "$LOCK_FILE" -mmin +"$LOCK_STALE_MINUTES" 2>/dev/null)" ]; then
    log "breaking stale lock $LOCK_FILE"
    rm -f "$LOCK_FILE"
  else
    log "another run holds $LOCK_FILE — exiting"
    exit 0
  fi
fi
[ "$DRY_RUN" -eq 0 ] && { echo "$$" > "$LOCK_FILE"; trap 'rm -f "$LOCK_FILE"' EXIT; }

cd "$FACTORY_DIR"

# ── Fetch authoritative main ───────────────────────────────────────
git fetch --quiet "$GIT_REMOTE" "$GIT_BRANCH" || { alert "git fetch failed"; exit 1; }
REMOTE_REF="$GIT_REMOTE/$GIT_BRANCH"

# ── Compute changed factory/** source files (working tree vs main) ──
# `git diff --name-only <ref> -- factory/` lists every factory source
# file whose live content differs from main (added/modified/deleted).
mapfile -t ALL_CHANGED < <(git diff --name-only "$REMOTE_REF" -- factory/ | grep -E '\.py$' || true)

APPLY=()
SKIPPED_FORBIDDEN=()
for f in "${ALL_CHANGED[@]}"; do
  case "$f" in
    factory/manager/*|bench/*)
      SKIPPED_FORBIDDEN+=("$f") ;;
    *)
      APPLY+=("$f") ;;
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

# ── Surgical checkout of just those files ──────────────────────────
git checkout "$REMOTE_REF" -- "${APPLY[@]}"

# ── Import-gate BEFORE committing: a broken module must never ship ──
if ! uv run python -c "import importlib, factory; import factory.chain.orchestrator, factory.chain.handlers, factory.chain.auto_merge, factory.chain.dual_draft, factory.cli" >/tmp/factory-self-deploy-import.log 2>&1; then
  alert "import check FAILED after checkout — reverting, nothing committed. See /tmp/factory-self-deploy-import.log"
  git checkout HEAD -- "${APPLY[@]}"
  exit 1
fi

# ── Commit ONLY the deployed paths (never `git add -A`: runtime state) ─
git commit --quiet -- "${APPLY[@]}" \
  -m "deploy: auto-sync factory/** from $REMOTE_REF (factory self-deploy)" \
  -m "Files: ${APPLY[*]}"
log "committed $(git rev-parse --short HEAD)"

# ── Restart the long-lived manager (chain code is picked up next tick;
#    restart is for shared modules the manager already imported) ──────
if systemctl --user restart "$MANAGER_UNIT" 2>/dev/null; then
  sleep 2
  if [ "$(systemctl --user is-active "$MANAGER_UNIT" 2>/dev/null)" = "active" ]; then
    log "restarted $MANAGER_UNIT (active)"
  else
    alert "$MANAGER_UNIT is NOT active after restart — operator attention needed"
    exit 1
  fi
else
  alert "failed to restart $MANAGER_UNIT — operator attention needed"
  exit 1
fi

log "self-deploy complete"
