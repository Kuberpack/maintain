# Architecture — Machine Maintenance & Cleaning Tracker

## Tech Stack
- **Frontend:** React + TypeScript, served as a static SPA
- **Backend:** FastAPI (Python), REST API
- **Database:** PostgreSQL
- **Alerts:** Scheduled job (cron or APScheduler) checks due/overdue tasks → sends email (SMTP) + WhatsApp (Business API/Twilio/Gupshup)
- **Containerization:** Docker + docker-compose (frontend, backend, db as separate services)

## Deployment Strategy
- **Public online deployment**: frontend on Vercel (static SPA build), backend + PostgreSQL on Railway (backend built and run from `backend/Dockerfile`, Postgres as Railway's managed database). See `DEPLOYMENT.md` for the exact environment-variable checklist for both platforms.
- Publicly accessible over HTTPS — both platforms terminate TLS at their edge. The earlier "internal tool only, no public exposure" assumption no longer applies: this data isn't financial or otherwise highly sensitive, so public hosting is fine, but standard hygiene still holds — HTTPS everywhere, no secrets committed to the repo, real random secrets set as environment variables on each platform rather than the placeholder values used in local dev.
- Local `docker-compose up` (db + backend + frontend) remains fully supported for development and testing alongside the real deployment — it is not being retired, just no longer the only or production deployment path.
- Backups: `scripts/backup.sh` (pg_dump-based, daily via host cron) still applies as-is to a local docker-compose Postgres. For the Railway-hosted database, backup strategy hasn't been revisited as part of this deployment-config change — check Railway's own backup/snapshot offering for the plan in use, or point `scripts/backup.sh` at the Railway `DATABASE_URL` instead if that's preferred.

## System Flow
1. **Operator** logs in → sees **Today** for every unit they are assigned to (one person may cover several).
2. Operator completes a cleaning/oiling task on the floor → marks it done in the dashboard → system logs date/time/user, resets the next-due date based on the recurring interval.
3. **Scheduler job** runs daily → checks all task instances → flags upcoming/overdue → alerts the **assigned operator** and the machine's **dedicated supervisor** (all supervisors when the unit has none). Unassigned machines alert supervisors only.
4. **Supervisor** can manually reschedule a task instance (e.g. machine was idle, breakdown occurred) — overrides the default recurring interval for that instance only. Supervisors can also cover leave by doing work on any machine.
5. **Management** views a read-only summary dashboard: overall compliance %, overdue counts, per-machine history — no edit access.
6. All actions (mark done, reschedule, repair logged) are timestamped and attributed to a user for the history/audit trail.
7. **Language** is a client-side English/Hindi toggle (remembered in the browser). Operators default to Hindi; other roles default to English.

## Data Flow Diagram (textual)
```
Operator/Supervisor (browser)
        |
        v
   React Frontend  <---->  FastAPI Backend  <---->  PostgreSQL
                                  |
                                  v
                         Scheduler (daily job)
                                  |
                          -----------------
                          |               |
                       Email (SMTP)   WhatsApp API
```
