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

This project has no real machine/task/staff data yet. Everything is seeded with
realistic dummy data (`backend/app/seed.py`, added in a later step) so the
schema and flows can be tested end-to-end. Swapping in real data is meant to
be a seed-script edit, not a rebuild.
