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
