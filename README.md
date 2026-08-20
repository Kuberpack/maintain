# Machine Maintenance & Cleaning Tracker

Internal tool for Kuberpack's Sonipat plant. See `CLAUDE.md`, `architecture.md`,
`schema.md`, `todo.md` for context, design, and data model.

## Stack

- Backend: FastAPI (Python), SQLAlchemy, Alembic, PostgreSQL
- Frontend: React + TypeScript (Vite), Tailwind CSS
- Auth: JWT sessions — phone + PIN for operators/supervisors, email + password for management
- Alerts: WhatsApp + email, stubbed until a BSP is chosen

## Running with Docker Compose

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Backend: http://localhost:8000 (health check at `/health`)
- Frontend: http://localhost:5173
- Postgres: localhost:5432

`/health` passing doesn't mean the app works -- it's just a DB ping. Compose
starts against an **empty database**; run migrations and seed it (once,
after the containers are up) before anything else will work:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

## Running locally without Docker

Backend:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env  # point DATABASE_URL at your local Postgres
.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Seed data

This project has no real machine/task/staff data yet. `backend/app/seed.py`
wipes and reseeds the database with realistic dummy data -- 5 machines,
16 task types across them with varied intervals, 6 users across all three
roles, plus example task instances, repair logs, and part replacements --
so the schema and flows can be tested end-to-end:

```bash
cd backend
.venv/bin/python -m app.seed
```

The `MACHINES` / `USERS` / `TASK_TYPES` constants at the top of that file are
placeholders. Swapping in real data later means editing those constants, not
rewriting the seeding logic.

Dummy login credentials (all `@kuberpack.com` / phone numbers are fake):

| Name | Role | Phone | PIN | Email | Password |
|---|---|---|---|---|---|
| Ramesh Kumar | operator | 9812345001 | 1234 | | |
| Suresh Yadav | operator | 9812345002 | 2345 | | |
| Vikram Singh | operator | 9812345003 | 3456 | | |
| Anita Sharma | supervisor | 9812345004 | 4567 | | |
| Rajesh Verma | supervisor | 9812345005 | 5678 | | |
| Priya Kapoor | management | | | priya.kapoor@kuberpack.com | ChangeMe123! |

## Bootstrapping real data (no dummy accounts)

For a real deployment, don't run `seed.py` -- it wipes and replaces
everything with the dummy data above. Instead, create exactly one real
supervisor account with `backend/app/create_supervisor.py`, then use that
account to add real machines, task types, and staff through the app itself
(machine/task-type/user creation all require being logged in as a
supervisor, so this one account is what unblocks everything else):

```bash
docker compose exec backend python -m app.create_supervisor
```

Prompts for name, phone number, and PIN (the PIN prompt is hidden, like a
password field). Touches nothing else in the database -- safe to run
against a database that already has real data in it, as long as the phone
number you give it isn't already taken.

## Backups

`scripts/backup.sh` dumps the database (compressed) to `backups/` and prunes
dumps older than `BACKUP_RETENTION_DAYS` (default 14). It reads
`POSTGRES_USER`/`PASSWORD`/`DB` from the root `.env` -- the same variables
docker-compose uses -- and connects over TCP to `localhost:5432`, so it
works the same way whether Postgres is running via `docker compose up` (which
publishes that port to the host) or as a bare-metal install. Needs the
`postgresql-client` package on whatever machine runs it (for `pg_dump`).

```bash
./scripts/backup.sh
```

Schedule it with a host crontab entry (not a container -- this is meant to
run on the actual shared PC/server, independent of the app containers'
lifecycle):

```bash
crontab -e
# daily at 2am:
0 2 * * * cd /path/to/maintain && ./scripts/backup.sh >> backups/backup.log 2>&1
```

To restore a dump (into a database that already has the schema, or a fresh
one you'll then run `alembic upgrade head` against):

```bash
gunzip -c backups/maintain_20260101_020000.sql.gz | psql -h localhost -U maintain -d maintain
```
