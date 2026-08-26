# Machine Maintenance & Cleaning Tracker

Internal tool for Kuberpack's Sonipat plant. See `CLAUDE.md`, `architecture.md`,
`schema.md`, `todo.md` for context, design, and data model. For the real
online deployment (Vercel + Railway) rather than local dev, see `DEPLOYMENT.md`.

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

`backend/app/seed.py` wipes and reseeds the database with the plant roster
(32 units, real operator/supervisor phones, split FAC checklists, utility
PM for compressors/DGs/etc.):

```bash
cd backend
.venv/bin/python -m app.seed
```

Do not run seed against a database that already has real floor history
unless you have a backup — it deletes existing machines, tasks, and users.

Operator and supervisor PINs are random. After seed, read
`backend/.plant_pins.txt` (gitignored) and hand those out. Management login
for local seed is still `priya.kapoor@kuberpack.com` / `ChangeMe123!`.

To refresh machines on a live DB without deleting existing accounts:

```bash
cd backend
.venv/bin/python -m scripts.seed_plant_keep_users
```

## Bootstrapping real data (no dummy accounts)

For a real deployment, don't run `seed.py` -- it wipes everything. Either
run `scripts.seed_plant_keep_users` after migrate (keeps admin/management,
upserts the roster by phone) or create exactly one real admin or
supervisor account with `backend/app/bootstrap_account.py`, then add the
rest through the app:

```bash
docker compose exec backend python -m app.bootstrap_account
```

Prompts for role (`admin` or `supervisor`), name, phone number, and PIN
(the PIN prompt is hidden, like a password field). Touches nothing else in
the database -- safe to run against a database that already has real data
in it, as long as the phone number you give it isn't already taken. See
`schema.md`/`architecture.md` for the difference between the two roles --
briefly, `admin` can manage any user account (including other
supervisors), while `supervisor` can only manage operator accounts.

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
