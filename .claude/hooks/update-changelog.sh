#!/usr/bin/env bash
# Called by Claude Code PostToolUse hook after a git push to a principal branch.
# Reads new commits since the previous merge/principal-branch tip and prepends
# a changelog entry to memory/changelog.md.
#
# Usage (from hook): called automatically; can also be run manually:
#   bash .claude/hooks/update-changelog.sh <branch> [<from_ref>] [<to_ref>]

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CHANGELOG="$REPO_ROOT/memory/changelog.md"
MEMORY="$REPO_ROOT/memory/memory.md"

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
declare -A sections
sections[feat]=""
sections[fix]=""
sections[chore]=""
sections[docs]=""
sections[refactor]=""
sections[db]=""
sections[other]=""

while IFS= read -r line; do
  hash="${line%% *}"
  msg="${line#* }"
  scope=""
  body="$msg"

  # Extract type(scope): body
  if [[ "$msg" =~ ^([a-z]+)(\(([^)]+)\))?: ]]; then
    type="${BASH_REMATCH[1]}"
    scope="${BASH_REMATCH[3]:-}"
    body="${msg#*: }"
    # Map db-scoped chores to db section
    if [[ "$type" == "chore" && "$scope" == "db" ]]; then
      type="db"
    fi
    key="${type}"
    [[ -v sections[$key] ]] || key="other"
  else
    key="other"
  fi

  entry="- \`${hash}\`"
  [[ -n "$scope" && "$type" != "db" ]] && entry+=" **($scope)**"
  entry+=" ${body}"
  sections[$key]+="${entry}"$'\n'
done <<< "$COMMITS"

# --- Build entry ---
# Use HH:MM alongside the date so multiple same-day entries stay ordered
# (Constitution III: traceability — each PR/merge/direct push gets one entry).
DATE=$(date '+%Y-%m-%d %H:%M')
SHORT_SHA=$(git -C "$REPO_ROOT" rev-parse --short "$TO_REF" 2>/dev/null)

ENTRY="## [${BRANCH}] — ${DATE} · ${SHORT_SHA}"$'\n'$'\n'

add_section() {
  local header="$1" key="$2"
  if [[ -n "${sections[$key]:-}" ]]; then
    ENTRY+="### ${header}"$'\n'
    ENTRY+="${sections[$key]}"$'\n'
  fi
}

add_section "Added"     feat
add_section "Fixed"     fix
add_section "Database"  db
add_section "Changed"   chore
add_section "Refactor"  refactor
add_section "Docs"      docs
add_section "Other"     other
ENTRY+="---"$'\n'$'\n'

# --- Prepend entry after the header block (first blank line after the first '---') ---
TMP=$(mktemp)
awk -v entry="$ENTRY" '
  /^---$/ && !done {
    print
    printf "\n%s", entry
    done=1
    next
  }
  { print }
' "$CHANGELOG" > "$TMP" && mv "$TMP" "$CHANGELOG"

# --- Also stamp last-updated in memory.md ---
sed -i "s|^### [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} — Session.*|### ${DATE} — Session (auto-updated on push to ${BRANCH})|" "$MEMORY" 2>/dev/null || true

echo "[changelog] Entry added for ${BRANCH} at ${DATE} (${SHORT_SHA})"
