# CLAUDE.md — Machine Maintenance & Cleaning Tracker

Project context for Kuberpack's internal machine maintenance tracker.
See `todo.md`, `architecture.md`, `schema.md` for scope, plan, and data model.

## Stack
- **Backend:** Python, FastAPI
- **Frontend:** React + TypeScript
- **Database:** PostgreSQL
- **Containerization:** Docker (docker-compose for local/single-server deploy)
- **Alerts:** WhatsApp (Business API or a lightweight provider like Twilio/Gupshup) + email (SMTP)

> Not yet finalized in chat — confirm before Phase 1 if this differs from what you want.

## Coding Rules
- Keep it simple: this is an internal tool for a small team, not a public SaaS product. Avoid over-engineering (no premature microservices, no unnecessary abstraction layers).
- **Backend:** typed Python (type hints everywhere), Pydantic models for request/response schemas, one router file per resource (`machines`, `tasks`, `logs`, `users`).
- **Frontend:** functional React components + hooks only, TypeScript strict mode, no class components.
- **Naming:** snake_case in Python/DB, camelCase in TypeScript/React.
- **No feature code until schema and API contracts are agreed** (per current phase).
- Favor plain, readable code over clever code — this will likely be maintained solo.
- All dates/times stored in UTC, displayed in local (Sonipat) time.
- No hardcoded secrets — use environment variables / `.env` (gitignored).

## Explicitly Out of Scope (for now)
- No integration with TranZact ERP — stays a standalone tool.
- No mobile app — web dashboard only, shared PC access.
