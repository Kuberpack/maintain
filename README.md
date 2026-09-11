# Maintain — plant maintenance & cleaning tracker

Internal operations app for Kuberpack’s Sonipat plant: schedule and complete machine cleaning/PM checklists, capture photo proof, escalate exceptions for supervisor review, and report overdue work.

For the live online deployment (Vercel frontend + Railway backend), see `DEPLOYMENT.md`.

## Problem

Corrugation and converting lines need recurring cleaning, oiling, and preventive checks. Paper checklists go missing, exceptions are verbal, and management lacks a live view of overdue or critical items. Maintain replaces that with role-led workflows (operator / supervisor / management), photo evidence, and review gates before a run counts as done.

## Features

- Role-based auth: phone + PIN for operators/supervisors; email + password for management
- Machine registry with task types (cleaning, oiling, part replacement, repair, preventive)
- Checklist items with optional numeric readings and min/max bands
- Task instances with due dates, overdue tracking, photo + exception photo requirements
- Supervisor review workflow (`awaiting_review` → approved/rejected) before recurrence advances
- Supervisor machine scope and plant rotation assignment flows
- Handover notes / shift logs per machine
- Repair logs and part replacement records
- Weekly/summary reporting views
- Seed + plant roster scripts; separate bootstrap for first real admin/supervisor
- Docker Compose (API, frontend, Postgres); Alembic migrations
- Vercel API proxy so company Wi‑Fi does not need direct Railway access
- Backup script (`scripts/backup.sh`) with retention pruning

## Architecture

```mermaid
flowchart LR
  Op[Operator / Supervisor UI] --> FE[React + Vite + TS]
  FE -->|JWT| API[FastAPI]
  API --> PG[(PostgreSQL)]
  API --> Sched[APScheduler-style jobs]
  FE --> Photos[Photo upload endpoints]
  Mgmt[Management UI] --> FE
```

Data model centrepiece is `task_instances` joined to `task_types` / `checklist_items` / `checklist_item_results`. Work is not `done` until `review_status=approved`; only then is the next recurring instance created. See `schema.md` and `architecture.md` for column-level detail.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Frontend | React + TypeScript (Vite), Tailwind CSS |
| Auth | JWT sessions (dual credential styles by role) |
| Alerts | WhatsApp + email hooks stubbed pending BSP choice |
| Ops | Docker Compose, `pg_dump` backup script, Vercel + Railway |

## Key engineering decisions

1. **Review gate before recurrence.** Prevents rubber-stamp completions from advancing the schedule; supervisors must approve.
2. **Photo proof + exception photos.** Critical/attention items require extra evidence.
3. **Fast-submit heuristic.** Large checklists completed unrealistically quickly are flagged (`is_fast_submit`) for scrutiny.
4. **Seed vs bootstrap vs keep-users.** `app.seed` wipes and loads demo/plant data — never against live floor history without a backup. `scripts.seed_plant_keep_users` refreshes the machine roster without deleting accounts. `bootstrap_account.py` creates a single real admin/supervisor without touching machines.
5. **Host-side backups.** `backup.sh` runs on the host against published Postgres `5432`, independent of container lifecycle.

## Getting started

### Prerequisites

- Docker + Compose, or local Python 3.11+ / Node 20+ and Postgres

### Docker Compose

```bash
git clone https://github.com/Kuberpack/maintain.git
cd maintain
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

Then migrate and seed (empty DB on first boot):

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

- Backend: http://localhost:8000 (`/health` is a DB ping only)
- Frontend: http://localhost:5173

### Local backend (without Compose)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # point DATABASE_URL at your local Postgres
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

### Environment variables (names)

Root / backend / frontend `.env.example` files list names such as:

- `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- JWT / secret settings used by the API
- `VITE_API_URL` (or equivalent) for the frontend
- `BACKUP_RETENTION_DAYS` for the backup script

Never commit filled `.env` files.

### Demo / plant seed (destructive)

`backend/app/seed.py` wipes and reseeds the database with the plant roster (32 units, operator/supervisor phones, split FAC checklists, utility PM for compressors/DGs/etc.):

```bash
cd backend
.venv/bin/python -m app.seed
```

**Do not run seed against a database that already has real floor history unless you have a backup** — it deletes existing machines, tasks, and users.

Operator and supervisor PINs are random. After seed, read `backend/.plant_pins.txt` (gitignored) and hand those out. Management login for local seed is still `priya.kapoor@kuberpack.com` / `ChangeMe123!` — change before any shared deployment.

### Refresh machines on a live DB (keep accounts)

```bash
cd backend
.venv/bin/python -m scripts.seed_plant_keep_users
```

Keeps admin/management accounts and upserts the roster by phone.

### First real account (no wipe)

For a real deployment, do **not** run `seed.py`. Create exactly one real admin or supervisor, then add the rest through the app:

```bash
docker compose exec backend python -m app.bootstrap_account
# or locally:
# cd backend && .venv/bin/python -m app.bootstrap_account
```

Prompts for role (`admin` or `supervisor`), name, phone number, and PIN. `admin` can manage all account types; `supervisor` can only manage operator accounts.

### Backups

```bash
./scripts/backup.sh
# restore example:
# gunzip -c backups/maintain_YYYYMMDD_HHMMSS.sql.gz | psql -h localhost -U maintain -d maintain
```

Uses `POSTGRES_USER` / `PASSWORD` / `DB` from the root `.env`. Needs `postgresql-client` (`pg_dump`) on the host that runs the script.

## Project structure

```
maintain/
├── backend/app/
│   ├── routers/       # auth, machines, tasks, reviews, reports, …
│   ├── models.py
│   ├── scheduler.py
│   ├── seed.py
│   └── bootstrap_account.py
├── backend/alembic/
├── backend/scripts/   # e.g. seed_plant_keep_users
├── frontend/src/
│   ├── pages/         # Today, Overdue, Review, Reports, Users, …
│   ├── auth/
│   └── api/
├── scripts/backup.sh
├── docker-compose.yml
├── DEPLOYMENT.md
├── architecture.md
└── schema.md
```

## Testing / quality

Validate via `/health`, login, and completing a checklist through review. Prefer adding API tests around review transitions, supervisor machine scope, and recurrence creation before expanding plant rollout.

## Deployment

See `DEPLOYMENT.md` for the Vercel + Railway split, the Vercel API proxy, env wiring, and migration order.
