#!/usr/bin/env bash
#
# GameReady PostgreSQL Restore Script
# 
# This script restores a database from a backup file.
# 
# WARNING: This will DROP and RECREATE the target database!
# Only use this for testing/restore scenarios, not on production!
#
# Usage:
#   ./scripts/restore_postgres.sh <backup_file> [target_db_name]
#
# Environment Variables Required:
#   - DB_HOST: Database host
#   - DB_USER: Database user (must have CREATEDB privileges)
#   - DB_PASSWORD: Database password
#   - DB_PORT: Database port (default: 5432)
#
# Arguments:
#   backup_file: Path to backup file (.sql or .sql.gz)
#   target_db_name: Target database name (default: from backup or DB_NAME env var)
#
# Exit codes:
#   0: Success
#   1: Missing arguments
#   2: Backup file not found
#   3: Database connection error
#   4: Restore error

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [[ $# -lt 1 ]]; then
    echo -e "${RED}Error: Missing backup file argument${NC}"
    echo "Usage: $0 <backup_file> [target_db_name]"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-${DB_NAME:-gameready_db}}"
DB_PORT="${DB_PORT:-5432}"

# Check if backup file exists
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 2
fi

# Check required environment variables
if [[ -z "${DB_USER:-}" ]] || [[ -z "${DB_PASSWORD:-}" ]] || [[ -z "${DB_HOST:-}" ]]; then
    echo -e "${RED}Error: Missing required database environment variables${NC}"
    echo "Required: DB_USER, DB_PASSWORD, DB_HOST"
    echo "Optional: DB_PORT (default: 5432), DB_NAME (default: gameready_db)"
    exit 3
fi

# Check for psql
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql not found. Please install PostgreSQL client tools.${NC}"
    exit 1
fi

echo -e "${YELLOW}WARNING: This will DROP and RECREATE the database '${TARGET_DB}'!${NC}"
echo "Are you sure you want to continue? (yes/no)"
read -r CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    exit 3
fi

# Drop and recreate database
echo -e "${YELLOW}Dropping existing database (if exists)...${NC}"
PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres <<EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '${TARGET_DB}'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS ${TARGET_DB};
CREATE DATABASE ${TARGET_DB};
EOF

# Determine if backup is compressed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Restoring from compressed backup...${NC}"
    if gunzip -c "$BACKUP_FILE" | PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TARGET_DB}"; then
        echo -e "${GREEN}✓ Database restored successfully${NC}"
    else
        echo -e "${RED}Error: Failed to restore database${NC}"
        exit 4
    fi
else
    echo -e "${YELLOW}Restoring from uncompressed backup...${NC}"
    if PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TARGET_DB}" < "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Database restored successfully${NC}"
    else
        echo -e "${RED}Error: Failed to restore database${NC}"
        exit 4
    fi
fi

echo -e "${GREEN}Restore completed successfully${NC}"
echo "Database: ${TARGET_DB}"
echo "Backup file: ${BACKUP_FILE}"

exit 0

