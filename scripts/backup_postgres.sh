#!/usr/bin/env bash
#
# GameReady PostgreSQL Backup Script
# 
# This script creates a logical dump of the production database and optionally
# uploads it to S3 for off-site storage.
#
# Usage:
#   ./scripts/backup_postgres.sh [--s3] [--local-only]
#
# Environment Variables Required:
#   - DB_NAME: Database name
#   - DB_USER: Database user
#   - DB_PASSWORD: Database password
#   - DB_HOST: Database host
#   - DB_PORT: Database port (default: 5432)
#
# For S3 upload (optional):
#   - AWS_ACCESS_KEY_ID: AWS access key
#   - AWS_SECRET_ACCESS_KEY: AWS secret key
#   - AWS_S3_BUCKET: S3 bucket name (default: gameready-db-backups)
#   - AWS_DEFAULT_REGION: AWS region (default: us-east-1)
#
# Exit codes:
#   0: Success
#   1: Database connection error
#   2: Backup creation error
#   3: S3 upload error (if --s3 specified)
#   4: Missing required environment variables

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
UPLOAD_TO_S3=false
LOCAL_ONLY=false
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
DB_PORT="${DB_PORT:-5432}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3)
            UPLOAD_TO_S3=true
            shift
            ;;
        --local-only)
            LOCAL_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--s3] [--local-only]"
            exit 1
            ;;
    esac
done

# Check required environment variables
if [[ -z "${DB_NAME:-}" ]] || [[ -z "${DB_USER:-}" ]] || [[ -z "${DB_PASSWORD:-}" ]] || [[ -z "${DB_HOST:-}" ]]; then
    echo -e "${RED}Error: Missing required database environment variables${NC}"
    echo "Required: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST"
    echo "Optional: DB_PORT (default: 5432)"
    exit 4
fi

# Check for pg_dump
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}Error: pg_dump not found. Please install PostgreSQL client tools.${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Construct database URL for pg_dump
# Format: postgresql://user:password@host:port/database
DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Backup filename
BACKUP_FILE="${BACKUP_DIR}/gameready-${TIMESTAMP}.sql.gz"

echo -e "${GREEN}Starting database backup...${NC}"
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}"
echo "Backup file: ${BACKUP_FILE}"

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    exit 1
fi

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
if pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  Size: ${BACKUP_SIZE}"
    echo "  File: ${BACKUP_FILE}"
else
    echo -e "${RED}Error: Failed to create backup${NC}"
    rm -f "$BACKUP_FILE"
    exit 2
fi

# Upload to S3 if requested
if [[ "$UPLOAD_TO_S3" == true ]] && [[ "$LOCAL_ONLY" != true ]]; then
    # Check for AWS credentials
    if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]] || [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
        echo -e "${YELLOW}Warning: AWS credentials not found. Skipping S3 upload.${NC}"
        echo "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to enable S3 upload."
    else
        # Check for aws CLI
        if ! command -v aws &> /dev/null; then
            echo -e "${YELLOW}Warning: AWS CLI not found. Skipping S3 upload.${NC}"
            echo "Install AWS CLI to enable S3 upload: https://aws.amazon.com/cli/"
        else
            AWS_S3_BUCKET="${AWS_S3_BUCKET:-gameready-db-backups}"
            AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
            S3_PATH="s3://${AWS_S3_BUCKET}/prod/${TIMESTAMP}.sql.gz"
            
            echo -e "${YELLOW}Uploading to S3...${NC}"
            if aws s3 cp "$BACKUP_FILE" "$S3_PATH" \
                --region "$AWS_REGION" \
                --server-side-encryption AES256 \
                --storage-class STANDARD_IA; then
                echo -e "${GREEN}✓ Backup uploaded to S3${NC}"
                echo "  S3 Path: ${S3_PATH}"
                
                # Optionally remove local file after successful upload
                # Uncomment the next line if you want to save local disk space
                # rm -f "$BACKUP_FILE"
            else
                echo -e "${RED}Error: Failed to upload to S3${NC}"
                echo "Local backup preserved at: ${BACKUP_FILE}"
                exit 3
            fi
        fi
    fi
fi

# Create a symlink to the latest backup for easy access
LATEST_LINK="${BACKUP_DIR}/latest.sql.gz"
ln -sf "$(basename "$BACKUP_FILE")" "$LATEST_LINK"

echo -e "${GREEN}✓ Backup completed successfully${NC}"
echo "Backup file: ${BACKUP_FILE}"
if [[ -L "$LATEST_LINK" ]]; then
    echo "Latest link: ${LATEST_LINK}"
fi

exit 0

