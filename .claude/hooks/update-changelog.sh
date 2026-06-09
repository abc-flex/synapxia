#!/usr/bin/env bash
# Called by Claude Code PostToolUse hook after a git push to a principal branch.
# Reads new commits since the previous merge/principal-branch tip and prepends
# a changelog entry to memory/CHANGELOG.md.
#
# Usage (from hook): called automatically; can also be run manually:
#   bash .claude/hooks/update-changelog.sh <branch> [<from_ref>] [<to_ref>]

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CHANGELOG="$REPO_ROOT/memory/CHANGELOG.md"
MEMORY="$REPO_ROOT/memory/MEMORY.md"

BRANCH="${1:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)}"
FROM_REF="${2:-}"
TO_REF="${3:-HEAD}"

# Only run for principal branches
PRINCIPAL_BRANCHES="develop main production"
is_principal=false
for b in $PRINCIPAL_BRANCHES; do
  [[ "$BRANCH" == "$b" ]] && is_principal=true && break
done
$is_principal || exit 0

# --- Determine commit range ---
# If FROM_REF not provided, use the parent of the most recent merge commit,
# falling back to the last 10 commits.
if [[ -z "$FROM_REF" ]]; then
  LAST_MERGE=$(git -C "$REPO_ROOT" log "$TO_REF" --merges --format="%H" -1 2>/dev/null || true)
  if [[ -n "$LAST_MERGE" ]]; then
    FROM_REF="${LAST_MERGE}^"
  else
    FROM_REF=$(git -C "$REPO_ROOT" log "$TO_REF" --format="%H" | tail -1)
  fi
fi

# Collect commits in range (skip bare merge commits)
COMMITS=$(git -C "$REPO_ROOT" log "${FROM_REF}..${TO_REF}" \
  --format="%h %s" \
  --no-merges \
  2>/dev/null || true)

[[ -z "$COMMITS" ]] && exit 0   # nothing new to log

# --- Categorise commits by conventional-commit prefix ---
# Use plain variables instead of `declare -A` so the script runs on macOS's
# stock bash 3.2 (associative arrays require bash 4+).
SEC_FEAT=""
SEC_FIX=""
SEC_CHORE=""
SEC_DOCS=""
SEC_REFACTOR=""
SEC_DB=""
SEC_OTHER=""

while IFS= read -r line; do
  hash="${line%% *}"
  msg="${line#* }"
  scope=""
  body="$msg"
  key="other"

  # Extract type(scope): body — bash 3.2-safe: try with-scope, then bare prefix.
  # (Bash 3.2 mishandles optional capturing groups inside [[ =~ ]].)
  type=""
  if [[ "$msg" =~ ^([a-z]+)\(([^\)]+)\):[[:space:]] ]]; then
    type="${BASH_REMATCH[1]}"
    scope="${BASH_REMATCH[2]}"
    body="${msg#*: }"
  elif [[ "$msg" =~ ^([a-z]+):[[:space:]] ]]; then
    type="${BASH_REMATCH[1]}"
    body="${msg#*: }"
  fi

  if [[ -n "$type" ]]; then
    # Map db-scoped chores to db section
    if [[ "$type" == "chore" && "$scope" == "db" ]]; then
      type="db"
    fi
    case "$type" in
      feat|fix|chore|docs|refactor|db) key="$type" ;;
      *) key="other" ;;
    esac
  fi

  entry="- \`${hash}\`"
  [[ -n "$scope" && "$key" != "db" ]] && entry+=" **($scope)**"
  entry+=" ${body}"

  case "$key" in
    feat)     SEC_FEAT+="${entry}"$'\n' ;;
    fix)      SEC_FIX+="${entry}"$'\n' ;;
    chore)    SEC_CHORE+="${entry}"$'\n' ;;
    docs)     SEC_DOCS+="${entry}"$'\n' ;;
    refactor) SEC_REFACTOR+="${entry}"$'\n' ;;
    db)       SEC_DB+="${entry}"$'\n' ;;
    *)        SEC_OTHER+="${entry}"$'\n' ;;
  esac
done <<< "$COMMITS"

# --- Build entry ---
# Use HH:MM alongside the date so multiple same-day entries stay ordered
# (Constitution III: traceability — each PR/merge/direct push gets one entry).
DATE=$(date '+%Y-%m-%d %H:%M')
SHORT_SHA=$(git -C "$REPO_ROOT" rev-parse --short "$TO_REF" 2>/dev/null)

ENTRY="## [${BRANCH}] — ${DATE} · ${SHORT_SHA}"$'\n'$'\n'

append_section() {
  local header="$1" content="$2"
  if [[ -n "$content" ]]; then
    ENTRY+="### ${header}"$'\n'
    ENTRY+="${content}"$'\n'
  fi
}

append_section "Added"     "$SEC_FEAT"
append_section "Fixed"     "$SEC_FIX"
append_section "Database"  "$SEC_DB"
append_section "Changed"   "$SEC_CHORE"
append_section "Refactor"  "$SEC_REFACTOR"
append_section "Docs"      "$SEC_DOCS"
append_section "Other"     "$SEC_OTHER"
ENTRY+="---"$'\n'$'\n'

# --- Prepend entry after the header block (first '---' separator) ---
# Pass the entry via a temp file rather than `awk -v` — BSD awk on macOS chokes
# on newlines inside -v values and silently leaves the file unchanged.
TMP=$(mktemp)
ENTRY_FILE=$(mktemp)
printf '%s' "$ENTRY" > "$ENTRY_FILE"

{
  # Print everything up to AND INCLUDING the first '---' separator.
  awk '{print} /^---$/{exit}' "$CHANGELOG"
  # Blank line, then the new entry.
  printf '\n'
  cat "$ENTRY_FILE"
  # Then everything AFTER the first '---'.
  awk 'seen{print} /^---$/{seen=1}' "$CHANGELOG"
} > "$TMP"

mv "$TMP" "$CHANGELOG"
rm -f "$ENTRY_FILE"

# --- Also stamp last-updated in memory.md ---
sed -i "s|^### [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} — Session.*|### ${DATE} — Session (auto-updated on push to ${BRANCH})|" "$MEMORY" 2>/dev/null || true

echo "[changelog] Entry added for ${BRANCH} at ${DATE} (${SHORT_SHA})"
