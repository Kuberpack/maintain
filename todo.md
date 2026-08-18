# TODO — Machine Maintenance & Cleaning Tracker

## Phase 0: Setup
- [ ] Finalize tech stack (see `CLAUDE.md`)
- [ ] Init repo structure (backend/, frontend/, docker-compose.yml)
- [ ] Set up PostgreSQL locally via Docker
- [ ] Decide on number of machines / initial machine list to seed

## Phase 1: MVP Core (backend + data)
- [ ] Implement DB schema (see `schema.md`)
- [ ] CRUD API: machines
- [ ] CRUD API: task types (clean / oil / part replacement / repair)
- [ ] CRUD API: task instances (schedule + log entries)
- [ ] Basic recurring schedule logic (fixed interval per task type)
- [ ] Manual reschedule/override endpoint
- [ ] Seed sample data for testing

## Phase 2: Dashboard UI
- [ ] Machine list view with status (green/yellow/red)
- [ ] Machine detail view: timeline of cleaning/oiling/parts/repairs
- [ ] "Mark as done" action (auto-logs date + user)
- [ ] Supervisor view: overdue items across all machines
- [ ] Management view: read-only summary/compliance %

## Phase 3: Access & Roles
- [ ] Decide login approach (per-user vs role-based vs open access)
- [ ] Implement auth (if per-user/role-based chosen)
- [ ] Role-based permissions: operator / supervisor / management

## Phase 4: Alerts
- [ ] Email alert on task due
- [ ] Email alert on task overdue (escalation to supervisor/management)
- [ ] WhatsApp alert integration
- [ ] Configurable alert timing (e.g. X days before due)

## Phase 5: Polish
- [ ] Photo upload as proof of completed task (open question)
- [ ] Exportable/printable maintenance report (PDF)
- [ ] Search/filter machines and history
- [ ] Deploy to shared PC / internal server
