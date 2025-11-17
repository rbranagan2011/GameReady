# Database Backup Implementation Plan

## Goal
Design, document, and automate a reliable backup and restoration workflow for the production PostgreSQL database (Render.com) to mitigate data-loss risk (Critical Issue #10).

## Current State
- Production database hosted on Render PostgreSQL (managed service)
- No documented backup policy or schedule
- Existing `DEPLOYMENT.md` only mentions a manual `pg_dump` command
- No verification / restore drills have been performed

## Requirements
1. **Automatic Backups**
   - Daily snapshot via Render built-in backups (retention ≥ 7 days)
   - Supplemental logical dump (`pg_dump`) stored off-site (e.g., S3) for 30-day retention
2. **Secure Storage**
   - Encrypted at rest (S3 bucket with SSE)
   - Access limited via IAM policy/service user
3. **Restore Testing**
   - Quarterly restore drill into staging DB
   - Documented RTO/RPO targets (RPO ≤ 24h, RTO ≤ 2h)
4. **Monitoring & Alerting**
   - Notifications for failed backup jobs
   - Dashboard/report summarising last successful backup time
5. **Documentation**
   - Step-by-step runbook in repo (`BACKUP_RUNBOOK.md`)
   - Diagram covering data flow and responsibilities

## Implementation Phases
### Phase 1: Baseline Assessment (1 day)
1. Confirm Render plan supports automated snapshots and retention limits
2. Export configuration metadata (DB size, storage growth rate)
3. Record credentials & connectivity requirements for `pg_dump` job
4. Define RTO/RPO targets with stakeholder approval

### Phase 2: Automated Backups (2 days)
1. **Render Snapshots**
   - Enable daily snapshots in Render dashboard
   - Set retention to 7–14 days (based on storage costs)
   - Enable alert webhook/email for snapshot failures
2. **Logical Dumps**
   - Provision S3 bucket `gameready-db-backups`
   - Create IAM user/role limited to write/list bucket
   - Write backup script `scripts/backup_postgres.sh`:
     ```bash
     #!/usr/bin/env bash
     set -euo pipefail
     TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
     pg_dump "$DATABASE_URL" | gzip > /tmp/gameready-${TIMESTAMP}.sql.gz
     aws s3 cp /tmp/gameready-${TIMESTAMP}.sql.gz s3://gameready-db-backups/prod/${TIMESTAMP}.sql.gz --sse
     rm /tmp/gameready-${TIMESTAMP}.sql.gz
     ```
   - Schedule via Render cron job or GitHub Actions nightly at 02:00 UTC
   - Rotate objects older than 30 days using S3 lifecycle policy

### Phase 3: Verification & Testing (1 day)
1. Spin up staging database from latest dump (Render temporary instance)
2. Document restore procedure and validation checklist (schema counts, sanity queries)
3. Automate verification script comparing table row counts vs production snapshot metadata
4. Record test results in `BACKUP_RUNBOOK.md`

### Phase 4: Monitoring & Reporting (0.5 day)
1. Add backup job logging + Slack/email alerts on failure (Render webhook or GitHub Actions notifications)
2. Create simple status badge/page (e.g., `BACKUP_STATUS.md`) updated nightly with timestamp of last successful backup
3. Add checklist item to on-call runbook for daily backup verification

### Phase 5: Documentation & Handoff (0.5 day)
1. Finalise `BACKUP_RUNBOOK.md` with:
   - Backup overview
   - How to trigger manual backup
   - Restore testing steps
   - Contact info/responsible roles
2. Update `PRE_LAUNCH_AUDIT.md` Critical Issue #10 when completed

## Deliverables
- Automated Render snapshot schedule (verified)
- S3-based logical dump pipeline with retention policy
- `scripts/backup_postgres.sh`
- `BACKUP_RUNBOOK.md` (operational instructions)
- Backup status badge/report (optional)
- Documented restore test evidence

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| S3 bucket not secured | Data exposure | Restrict IAM, enable bucket policies, SSE |
| Backup job fails silently | Data loss | Add monitoring + alerts |
| Restore process untested | Long RTO | Quarterly drills, documented procedure |
| Rapid DB growth increases costs | Budget overruns | Monthly review of storage usage |

## Next Actions
1. Confirm Render snapshot capabilities & enable daily backups
2. Provision S3 bucket + IAM permissions
3. Implement `pg_dump` automation + schedule
4. Draft restore runbook and perform initial restore test

