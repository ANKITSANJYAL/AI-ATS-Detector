# Backup & Disaster Recovery Strategy

This document outlines the backup and disaster recovery (DR) procedures for the
DocGuard & CareerMatch platform.

---

## 1. Database (PostgreSQL)

### Automated Backups

| Method | Frequency | Retention | Tool |
|--------|-----------|-----------|------|
| WAL archiving | Continuous | 7 days | `pg_basebackup` / managed service |
| Full dump | Daily at 02:00 UTC | 30 days | `pg_dump --format=custom` |
| Logical snapshot | Weekly (Sunday) | 90 days | `pg_dump` to S3 |

### Managed Service (Recommended)

When deployed on a managed PostgreSQL service (e.g. AWS RDS, GCP Cloud SQL, Supabase):

- Enable **automated daily backups** with point-in-time recovery (PITR).
- Set backup retention to ≥ 7 days.
- Enable **multi-AZ replication** for production.
- Store manual snapshots before every migration in S3/GCS with lifecycle rules.

### Self-Hosted

```bash
# Daily backup cron (add to crontab)
0 2 * * * pg_dump --format=custom -h localhost -U docguard docguard \
  | gzip > /backups/docguard-$(date +\%Y\%m\%d).dump.gz

# Restore
pg_restore --clean --if-exists -d docguard /backups/docguard-20250101.dump.gz
```

---

## 2. Redis

Redis is used for caching and rate limiting — data is ephemeral.

- **AOF persistence** is enabled in `docker-compose.yml` (`appendonly yes`).
- No long-term backup needed — cache misses are tolerable.
- If Redis is lost, the app automatically repopulates the cache.

---

## 3. Application Code

- All code is version-controlled in **Git** (GitHub: `ANKITSANJYAL/AI-ATS-Detector`).
- Use **tagged releases** for every production deployment.
- Docker images should be pushed to a container registry (e.g. GHCR, ECR).

---

## 4. ML Models

Transformer models (`roberta-base-openai-detector`, `chatgpt-detector-roberta`)
are downloaded from Hugging Face Hub on first run.

- Pin model versions in code to prevent drift.
- Optionally cache models in a Docker layer or artifact store.

---

## 5. Secrets & Configuration

- All secrets are stored in environment variables (never committed to Git).
- Use a secrets manager in production (AWS Secrets Manager, GCP Secret Manager, Vault).
- Keep `.env.example` files updated as the canonical reference.

---

## 6. Disaster Recovery Procedure

### RTO (Recovery Time Objective): < 1 hour
### RPO (Recovery Point Objective): < 24 hours

| Step | Action | Owner |
|------|--------|-------|
| 1 | Detect outage via health check / Sentry alerts | On-call engineer |
| 2 | Identify root cause (DB, app, infra) | On-call engineer |
| 3 | If DB corruption: restore from latest backup | DBA / DevOps |
| 4 | If app failure: roll back to last known-good Docker image | DevOps |
| 5 | Run `alembic upgrade head` to verify migration state | DevOps |
| 6 | Smoke-test `/health` and core endpoints | QA |
| 7 | Post-incident review | Team |

---

## 7. Testing Backups

- **Monthly**: Restore the latest backup to a staging database and verify row counts.
- **Quarterly**: Full DR drill — spin up the entire stack from backups in a clean environment.

---

## 8. Monitoring

| Signal | Tool | Alert Threshold |
|--------|------|-----------------|
| DB connection errors | Sentry | > 5 in 1 min |
| API 5xx rate | Sentry / Prometheus | > 1% of traffic |
| Disk usage (DB host) | Cloud metrics | > 80% |
| Backup job failure | Cron + alerting | Any failure |

---

*Last updated: 2025*
