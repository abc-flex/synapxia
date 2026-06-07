#!/usr/bin/env bash
# Run all SQL migrations against a Neon (or any PostgreSQL) database.
#
# Usage:
#   DATABASE_URL="postgresql://user:pass@host/db?sslmode=require" bash db/neon-migrate.sh
#
# Or export first:
#   export DATABASE_URL="postgresql://..."
#   bash db/neon-migrate.sh
#
# Get DATABASE_URL from: Vercel dashboard → Storage → your Neon DB → .env.local tab
# (copy POSTGRES_URL_NON_POOLING for migrations — avoids PgBouncer transaction limits)

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set. Export it before running this script.}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/sql"

FILES=(
  "11-admin-ddl.sql"
  "12-admin-insert.sql"
  "21-taxo-ddl.sql"
  "22-taxo-insert.sql"
  "31-collab-ddl.sql"
  "32-collab-insert.sql"
  "41-lib-ddl.sql"
  "42-lib-insert.sql"
  "51-inits-ddl.sql"
  "52-inits-insert.sql"
  "61-ana-ddl.sql"
)

echo "🚀 Running SynapxIA migrations against: ${DATABASE_URL%%@*}@..."
echo ""

for f in "${FILES[@]}"; do
  echo "  ▶ $f"
  psql "$DATABASE_URL" -f "$SQL_DIR/$f" -q
done

echo ""
echo "✅ All migrations complete."
