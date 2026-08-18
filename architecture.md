# Architecture — Machine Maintenance & Cleaning Tracker

## Tech Stack
- **Frontend:** React + TypeScript, served as a static SPA
- **Backend:** FastAPI (Python), REST API
- **Database:** PostgreSQL
- **Alerts:** Scheduled job (cron or APScheduler) checks due/overdue tasks → sends email (SMTP) + WhatsApp (Business API/Twilio/Gupshup)
- **Containerization:** Docker + docker-compose (frontend, backend, db as separate services)

## Deployment Strategy
- Single internal deployment — runs on a shared PC or small internal server at the Sonipat plant, accessible over the local network.
- No public internet exposure needed (internal tool only).
- `docker-compose up` to run all services together.
- Backups: scheduled PostgreSQL dumps (daily) to a local backup folder or external drive.

## System Flow
1. **Operator** logs into shared dashboard PC → sees machine list with status.
2. Operator completes a cleaning/oiling task on the floor → marks it done in the dashboard → system logs date/time/user, resets the next-due date based on the recurring interval.
3. **Scheduler job** runs daily → checks all task instances → flags upcoming/overdue → triggers email/WhatsApp alerts to relevant roles.
4. **Supervisor** can manually reschedule a task instance (e.g. machine was idle, breakdown occurred) — overrides the default recurring interval for that instance only.
5. **Management** views a read-only summary dashboard: overall compliance %, overdue counts, per-machine history — no edit access.
6. All actions (mark done, reschedule, repair logged) are timestamped and attributed to a user for the history/audit trail.

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
