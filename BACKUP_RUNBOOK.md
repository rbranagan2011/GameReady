# GameReady Backup Runbook

_Last reviewed: November 2025_

## Objectives
- **Recovery Point Objective (RPO)**: ≤ 24 hours (max one day of data loss)
- **Recovery Time Objective (RTO)**: ≤ 2 hours (time to restore service)
- Address Critical Issue #10 from `PRE_LAUNCH_AUDIT.md`

## Backup Architecture Overview
1. **Render Managed Snapshots** – daily automatic snapshots retained for 7 days via Render dashboard.
2. **Nightly Logical Dumps** – `scripts/backup_postgres.sh` runs at 02:00 UTC, uploads `.sql.gz` to S3 bucket `s3://gameready-db-backups/prod/` with 30-day retention.
3. **Restore Testing** – quarterly drill restoring the latest dump into staging; validation checklist below.
4. **Monitoring & Alerts** – Render backup notifications + GitHub Actions/Render cron alerts for dump job failures.

## Responsibilities
| Role | Responsibility |
|------|----------------|
| DevOps Lead (primary) | Owns automation, reviews daily backup status |
| Engineering Manager (backup) | Runs quarterly restore drill & signs off |
| On-call Engineer | Responds to failed backup alerts |

## 1. Render Managed Snapshots
1. Sign in to Render → PostgreSQL service → **Backups** tab.
2. Enable **Automatic Backups** (Daily) and set retention to **7 days** (adjust as data grows).
3. Configure notification email/webhook (`devops@gamereadyapp.com` or Slack webhook).
4. Verify “Last backup” timestamp daily (visible on same tab).

## 2. Nightly Logical Dump Job
### Required environment variables (Render cron or GitHub Actions)
```
DB_NAME=<render_db_name>
DB_USER=<render_db_user>
DB_PASSWORD=<render_db_password>
DB_HOST=<render_db_host>
DB_PORT=5432
AWS_ACCESS_KEY_ID=<iam_key>
AWS_SECRET_ACCESS_KEY=<iam_secret>
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=gameready-db-backups
BACKUP_DIR=/tmp/backups
```

### Command executed nightly (02:00 UTC)
```
chmod +x scripts/backup_postgres.sh
./scripts/backup_postgres.sh --s3
```
- Logs stored in Render cron history or GitHub Actions workflow logs.
- S3 lifecycle policy removes objects older than 30 days.

### Manual run
```
DB_NAME=prod DB_USER=render DB_PASSWORD=*** DB_HOST=*** ./scripts/backup_postgres.sh --s3
```
Use `--local-only` to skip S3 upload during testing; dumps written to `./backups/`.

## 3. Restoration Procedure
### Preparation
1. Provision temporary Postgres instance (Render staging DB or local Docker).
2. Export `TARGET_DB`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`.
3. Download desired backup:
   ```
   aws s3 cp s3://gameready-db-backups/prod/20251117-020000.sql.gz ./restore.sql.gz
   ```

### Restore using helper script
```
chmod +x scripts/restore_postgres.sh
BACKUP_FILE=./restore.sql.gz TARGET_DB=gameready_staging DB_HOST=... DB_USER=... DB_PASSWORD=... ./scripts/restore_postgres.sh
```
- Script prompts before dropping target DB.
- Handles compressed (`.gz`) and plain SQL dumps.

### Validation checklist (record results below)
1. `python manage.py check`
2. Compare row counts:
   ```
   SELECT COUNT(*) FROM core_readinessreport;
   SELECT COUNT(*) FROM core_profile;
   ```
3. Confirm latest `ReadinessReport` date matches production snapshot (≤24h delta).
4. Spot-check Django admin for sample data.
5. Update Restore Drill Log.

## 4. Monitoring & Alerts
- **Render snapshots**: ensure backup failure notifications reach DevOps.
- **Nightly dump job**:
  - GitHub Actions: on failure, send Slack message using `if: failure()` notification step.
  - Render cron: enable “notify on failure”.
- Optional nightly `BACKUP_STATUS.md` badge updated by workflow (timestamp, file size).

## 5. Backup Verification Commands
| Purpose | Command |
|---------|---------|
| List latest snapshots | Render dashboard → Backups tab |
| List latest S3 dumps | `aws s3 ls s3://gameready-db-backups/prod/ | tail -5` |
| Check dump size | `aws s3 ls s3://gameready-db-backups/prod/ | sort | tail -1` |
| Verify gzip integrity | `gunzip -t backup.sql.gz` |

## 6. Restore Drill Log
| Date | Backup Used | Target Env | Result | Notes |
|------|-------------|------------|--------|-------|
| _TBD_ | | | | |

## 7. Troubleshooting
- **Snapshot missing**: confirm Render plan still includes backups; open ticket if not.
- **Dump job failing**: verify `pg_dump` availability, DB credentials, IAM permissions.
- **Restore errors**: ensure disk space > DB size; terminate existing connections (handled in script).
- **Slow S3 upload**: run job in same AWS region as bucket.

## 8. Security Considerations
- S3 bucket enforces server-side encryption (SSE) and IAM least-privilege.
- Never commit `.sql` dumps to repo; `.gitignore` already excludes `/backups`.
- Rotate AWS IAM keys every 90 days; store rotation date in password manager.

## 9. References
- `scripts/backup_postgres.sh`
- `scripts/restore_postgres.sh`
- `DEPLOYMENT.md` → Maintenance → Backup Database
- Render docs: https://render.com/docs/databases#backups
- AWS lifecycle docs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html

---
Questions? Ping `#devops` in Slack or email `devops@gamereadyapp.com`.

