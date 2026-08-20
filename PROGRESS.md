# PROGRESS.md — Handoff Summary

**Purpose:** this file exists so a new Claude Code session (or a human) can pick up this
project with full context, without needing the chat history that produced it. It
describes what was **actually built and verified**, not what was planned. Where
something was not fully verified, that is stated explicitly rather than implied.

Written 2026-08-19, at the end of the session that took this project from four
planning docs (`CLAUDE.md`, `architecture.md`, `schema.md`, `todo.md`) through a
working MVP with dummy seed data. Read those four docs first for the *intent*;
this file describes the *actual state*.

---

## 1. Git / repo state right now

- **Everything is merged into `main`.** PR #1
  (https://github.com/Kuberpack/maintain/pull/1) contained all 13 build commits,
  was reviewed and merged (merge commit `db8eb74`) on 2026-08-19. It is closed.
- The branch all this work happened on was `claude/initial-commit-gitignore-aqwpbw`
  (that name is an artifact of the very first task in this repo's history — "create a
  gitignore file" — nothing more significant than that). It still exists on the
  remote, fully merged into `main`, safe to delete or leave.
- **⚠️ GitHub's default branch is still set to `claude/initial-commit-gitignore-aqwpbw`,
  not `main`.** This was asked about twice during the session and never confirmed
  fixed. Check **Settings → General → Default branch** on the repo. Until that's
  changed, anyone browsing the repo's front page, and any new PR opened without
  explicitly picking a base, will target the feature branch instead of `main`.
  All the actual code is on `main` too (via the merge) so nothing is lost, but new
  work should explicitly target `main` as a base until this is fixed.
- Working tree was clean (nothing uncommitted or unpushed) as of the last commit,
  `22ab335` ("Add Postgres backup script with retention pruning") plus one
  doc-only follow-up (`f1564b3`, folded in before the PR was opened).
- A local `main` branch ref exists in whatever sandbox produced this but is stale
  (still points at the original docs-only commit). Irrelevant for a fresh clone —
  `origin/main` has everything. Just don't trust a local `main` checkout in that
  old sandbox without pulling first.

### Commit history, in order (oldest first)

1. `f3157b4` — Initial commit: project docs and .gitignore (pre-existing, not part of this build)
2. `d37de85` — Repo skeleton: FastAPI backend, React+TS frontend, docker-compose
3. `b146578` — SQLAlchemy models + initial Alembic migration
4. `857a42c` — Auth: PIN login, password login, JWT sessions, role guards
5. `0f45114` — CRUD APIs for all six resources with role-appropriate permissions
6. `22517d7` — Recurring schedule logic, centralized in one place
7. `a5409a7` — Seed script with realistic dummy data; fixed a local-timezone bug
8. `4122eee` — Made the API wire format camelCase (Pydantic alias generator)
9. `f2aa840` — Read-only `GET /config` for alert thresholds
10. `925eca0` — Frontend: machine list, detail/timeline, mark-done, overdue, summary
11. `0434892` — Camera-capture component, wired into mark-as-done
12. `f1564b3` — Documented the missing migrate+seed step for docker compose
13. `e215394` — Alert logic: status computation, stubbed sends, daily scheduler
14. `22ab335` — Postgres backup script with retention pruning

Every commit message is long-form and explains *why*, not just *what* — including
the specific verification performed for that step. Read individual commit messages
via `git log <sha> -1` for the full reasoning if this summary isn't enough.

---

## 2. What was actually built, step by step

### Step 1 — Repo skeleton
FastAPI backend (`backend/`), React + TypeScript frontend via Vite (`frontend/`),
`docker-compose.yml` wiring `db` (Postgres 16) + `backend` + `frontend`.

- TypeScript **strict mode** was explicitly turned on — the Vite template does not
  enable it by default, and CLAUDE.md requires it.
- Tailwind CSS wired in for styling.
- `backend/app/main.py` has a `/health` endpoint that does a real DB round-trip
  (`SELECT 1`), not just a liveness ping.
- **Verified:** boot confirmed via local Postgres + uvicorn + Vite dev server in
  the sandbox (no Docker daemon available there). **The user separately verified
  a real `docker compose up --build` themselves at this point** — db, backend,
  frontend all up, `/health` reachable through both direct port and the frontend's
  proxy. This is the *only* point in the whole build where `docker compose` was
  confirmed working end-to-end; see the caveat in §7.

### Step 2 — SQLAlchemy models + Alembic migration
All six tables from `schema.md` (`users`, `machines`, `task_types`,
`task_instances`, `part_replacements`, `repair_logs`) as typed SQLAlchemy 2.0
models in `backend/app/models.py`, single file (not split per-resource — a
deliberate choice given only six small tables).

- Added `pin_hash` and `password_hash` columns to `users` (not in the original
  `schema.md` draft — needed for the two login paths, see §3).
- Added `phone_number` as a column distinct from `whatsapp_number` (see §3).
- UUID primary keys, native Postgres enums for `role`/`category`/`status`.
- FK cascade design: `machines → task_types → task_instances` cascade-delete
  (orphaned children are meaningless without their parent). Every FK to
  `users.id` is plain `RESTRICT` (the default) — deleting a user with history
  is supposed to be blocked, not silently orphan/null the audit trail. **This
  didn't actually work correctly until a bug was found and fixed — see §4.**
- **Verified:** migration applied and rolled back twice against real Postgres
  16, `alembic check` confirmed zero drift between models and DB.

### Step 3 — Auth
`POST /auth/login/pin` (phone + 4-6 digit PIN, operator/supervisor),
`POST /auth/login/password` (email + password, management), `GET /auth/me`,
JWT sessions (PyJWT + bcrypt, not passlib/python-jose — fewer version-compat
issues). `require_roles(*roles)` dependency factory in `app/core/deps.py` for
role-gating future endpoints.

- Which login path works for a given user falls out of which hash column is
  populated — not re-checked per-role in the login handlers themselves.
- **Verified:** both login paths (success / wrong secret / unknown identifier /
  malformed PIN), `/auth/me` with valid/missing/garbage tokens, and
  `require_roles` composed into a real temporary test route (403 wrong role,
  200 right role, 401 no token) — the test route and test users were removed
  before committing.

### Step 4 — CRUD APIs for all six resources
One router file per resource under `backend/app/routers/`, one schema file per
resource under `backend/app/schemas/`. Shared `get_or_404` / `commit_or_409`
helpers in `app/core/utils.py`.

**Permission model** (derived from `architecture.md`, not explicitly specified
by the user — flag this to whoever reviews it, see §6):
- All three roles can read (list/get) everything.
- Only **supervisor** can write `machines`, `task_types`, and `users`.
- **Operator + supervisor** can mark `task_instances` done, report
  `repair_logs`, and log `part_replacements` — the actual floor work.
- Only **supervisor** can reschedule `task_instances`, resolve `repair_logs`,
  or manually create `task_instances`.
- **Management has no write access anywhere** — matches architecture.md's
  "read-only summary dashboard ... no edit access."

Attribution fields (`completed_by`, `reported_by`, `replaced_by`, etc.) are
always taken from the authenticated user's JWT, never from the request body.

`task_type`'s documented invariant (`default_interval_days` null **iff**
`category=repair`) is enforced via a Pydantic validator on create, and
re-checked in the router on update (a PATCH might touch only one of the two
fields — this exact edge case was tested).

- **Verified:** full permission matrix exercised for all three roles across
  all six resources against real Postgres. **Two real bugs found and fixed
  here — see §4.**

### Step 5 — Recurring schedule logic
`backend/app/services/scheduling.py::complete_task_instance()` is the single
place that marks a `task_instance` done and, for recurring task types,
creates the next occurrence. The mark-done router endpoint is a thin wrapper —
no scheduling logic duplicated anywhere else.

- **Next due_date is computed from the completion date, not the original due
  date.** A late cleaning doesn't compound lateness onto every future
  occurrence — it restarts the interval from when the work actually happened.
  This was a judgment call (not explicitly specified); matches
  architecture.md's "resets the next-due date based on the recurring
  interval." If a fixed calendar (next = original_due + interval regardless
  of completion date) is wanted instead, it's a one-line change in that
  function.
- Repair-category task types (interval = null) correctly produce no next
  instance.
- **Verified:** a 7-day-interval task marked done today produces a next
  instance due today+7 (not original_due+7); a repair instance produces
  `next: null` with the DB confirming no extra row created.

### Step 6 — Seed script
`backend/app/seed.py` — wipes and reseeds: 5 machines, 16 task types across
them (intervals from 3 to 60 days, plus repair types with no interval), 6
users spanning all three roles, task instances spread across
overdue/due-soon/pending, one instance pre-completed via the real
`complete_task_instance()` service (to demonstrate the chain), 2 repair logs
(one resolved, one open), 1 part replacement.

Data lives in `MACHINES` / `USERS` / `TASK_TYPES` constants at the top of the
file, deliberately separate from the seeding logic, so swapping in real
Kuberpack data later is a data edit, not a rewrite.

- **Bug found and fixed in this step — see §4** (UTC vs local-timezone due-date
  computation). `app/core/time.py::today_local()` was added here and is now
  used everywhere "today" matters for scheduling.
- **Verified:** seed runs cleanly and repeatably, exactly one credential hash
  per role, chained next-occurrence lands on `today_local() + interval`, all
  three seeded login types authenticate with correct permissions.

### Step 7 — Made the API wire format camelCase
Added `backend/app/schemas/base.py::CamelModel` (Pydantic `alias_generator`
+ `populate_by_name=True`) as the base class for every request/response
schema. Python field names stay snake_case (matching DB/ORM); only the JSON
wire format changed to camelCase, matching CLAUDE.md's TypeScript convention.
Query params with compound names (`machineId`, `unresolvedOnly`) got explicit
`Query(alias=...)` in the routers that use them, since plain function
parameters aren't covered by the schema-level alias generator.

This was done **before** the frontend was built, specifically so frontend
types could honestly mirror the wire format with zero manual transform layer
— retrofitting this after the frontend existed would have been much more
expensive.

- Also added read-only `GET /config` (`alert_upcoming_days`,
  `alert_overdue_escalate_days`) so the frontend's status-color thresholds
  read the same configured values as the backend, not a second hardcoded copy.
- **Verified:** login accepts/returns camelCase, nested objects cascade the
  alias correctly, query param aliases work, compound-field create/validation
  still works end to end including error messages.

### Step 8 — Frontend
`frontend/src/` — see §7 for the *complete* endpoint-by-endpoint coverage
table; the summary:

- **Auth:** `AuthProvider`/`useAuth` (JWT in `localStorage`, session restored
  via `GET /auth/me` on load), `ProtectedRoute`, a login page toggling
  phone+PIN / email+password.
- **API layer:** one file per resource under `src/api/`, mirroring the
  backend routers, typed to the camelCase wire format. `useAsync` hook
  (`src/lib/useAsync.ts`) to cut down on repeated loading/error boilerplate.
- **Status colors are computed client-side** from `due_date`
  (`src/lib/status.ts`), *not* read from the stored `status` DB column — that
  column is only updated by the daily scheduler job (step 9) and can be up to
  24h stale. Thresholds come from `GET /config`.
- **Pages:** `MachineListPage` (card grid, worst-status badge per machine,
  mobile-first), `MachineDetailPage` (pending tasks + mark-done, hidden
  entirely for management — not just disabled — plus a merged timeline of
  completed tasks/repair logs/part replacements), `OverduePage` (flat table
  across machines), `SummaryPage` (compliance % + per-machine breakdown,
  desktop-oriented per spec).
- **Verified with a real Playwright browser** (not just curl) driving the
  actual running dev server: mobile login → machine list with correct status
  colors → machine detail → mark a task done → confirmed it moved to history
  with the correct chained next occurrence, against real seeded Postgres
  data. Also verified: management sees zero mark-done buttons anywhere,
  unauthenticated access redirects to `/login`, wrong-PIN shows an inline
  error, logout actually clears the session. TypeScript strict mode and
  oxlint both clean (two documented, expected warnings in the generic
  `useAsync` hook's dependency array — not bugs, see the comment above that
  function).

### Step 9 — Camera capture
`frontend/src/components/CameraCapture.tsx` — camera-only photo input via
`capture="environment"` (no gallery picker), preview via object URL with
proper cleanup, retake control. Standalone/reusable — knows nothing about
`task_instances` or mark-done.

Chose `<input capture>` over `getUserMedia`: works over plain HTTP
(`getUserMedia` requires a secure context, which this project's internal
single-server deployment doesn't establish), zero extra JS, and was the
explicitly-offered default option.

**Backend addition this required:** `photo_url` was always a plain string
column with nowhere for a real photo to go. Added a small `POST /photos`
endpoint (operator/supervisor only), storing to local disk under
`backend/uploads/` (already persisted by the existing `./backend:/app` bind
mount in `docker-compose.yml` — no compose changes needed) with a generated
UUID filename, served back via a `StaticFiles` mount. This is *not* a
commitment to local-disk as the long-term storage strategy — `todo.md`
Phase 5 correctly still calls real (cloud) storage an open question — it's
the minimal thing that makes "wire into mark-as-done" actually work today.

- **Bug found and fixed during this step — see §4** (the API client was
  forcing `Content-Type: application/json` unconditionally, which would have
  silently broken the multipart upload).
- **Verified with a real browser:** captured a photo through the camera-only
  input, saw preview + retake render, marked the task done, confirmed the
  photo uploaded, persisted, and shows as a thumbnail in history — fetched
  through a new `/uploads` Vite proxy rule. Backend separately verified:
  403 for management, 400 for non-images, 413 for a 9MB file with no partial
  file left on disk.
- **NOT verified:** actual camera-vs-gallery behavior on a real phone. The
  component logic was verified via Playwright's `setInputFiles()`, which
  drives the same underlying `<input type="file">` element but cannot
  exercise the native OS camera-app-vs-photo-picker behavior that
  `capture="environment"` is supposed to trigger on real iOS/Android. That
  part is standard, well-understood platform behavior outside what headless
  Chromium can touch, but it has never been checked on an actual device.

### Step 10 — Alert logic
`backend/app/services/daily_check.py::run_daily_check()` — the single place
that flips `pending` task instances to `overdue` (comparing `due_date`
against `today_local()`, not UTC — same reasoning as step 6's fix) and
decides who gets alerted:
- **Upcoming** (due within `alert_upcoming_days`): supervisors.
- **Overdue:** supervisors, escalating to **management** once
  `alert_overdue_escalate_days` have passed. (This setting existed in
  `config.py` since step 1 but was dead/unused code until this step.)

Still-overdue items are re-included in *every* day's run until resolved —
that's what makes it an escalation rather than a one-time notice. There is
**no per-item "already alerted" de-duplication or rate-limiting** — fine
while sends are stubbed/logged, but worth revisiting once a real provider
makes repeated sends costly.

`backend/app/services/alerts.py::send_whatsapp_alert` /
`send_email_alert` are **stubs** — they log `"Would send X to Y"` instead of
calling any real API, matching "I have a WhatsApp Business account but
haven't picked a BSP yet." `notify_user()` sends through every channel a
user has a destination for (WhatsApp *and* email, not either/or).

`backend/app/scheduler.py` wires this into APScheduler's
`BackgroundScheduler`, a cron trigger at `settings.daily_check_hour` (default
7am) in `settings.local_timezone`, started/stopped via FastAPI's `lifespan`
context manager (not the deprecated `on_event` hooks). Documented
single-process assumption — fine for this project's one-container
deployment; would double-fire the alert job with multiple backend workers.

- **Verified:** app boots with the scheduler registered at the correct next
  run time in IST. Manually drove `run_daily_check()` against seeded data
  through all three cases (upcoming / overdue-not-yet-escalated /
  overdue-escalated) and confirmed the right status flip and recipient list
  for each, including management getting both a WhatsApp *and* email log
  line. Re-ran immediately to confirm still-overdue items keep re-alerting
  rather than going silent after the first hit.

### Step 11 — Postgres backup script
`scripts/backup.sh` — `pg_dump` → `gzip` →
`backups/<db>_<timestamp>.sql.gz`, pruning dumps older than
`BACKUP_RETENTION_DAYS` (default 14). Reads `POSTGRES_USER`/`PASSWORD`/`DB`
from the root `.env` (same variables `docker-compose.yml` already uses) and
connects over TCP to `localhost:5432`, so it works identically whether
Postgres is running via `docker compose` (which publishes that port to the
host) or bare-metal. **Always runs on the host, never inside a container** —
meant to be scheduled via host crontab (documented in `README.md`), not the
backend's in-process APScheduler, since backups are a disk/ops concern
independent of the app process's lifecycle.

Writes to a `.tmp` file and renames on success; `set -euo pipefail` means a
failed `pg_dump` never reaches the rename; a cleanup `trap` removes a
leftover `.tmp` if the run fails — this was specifically tested, see §4.

- **Verified:** dump succeeds with both default and `.env`-sourced connection
  settings. **Restored the dump into a fresh database and confirmed every
  table's row count matched the source exactly** (not just "looks like valid
  SQL"). Retention pruning deletes an artificially-aged file while keeping
  recent ones. A bad-password run exits non-zero and leaves no corrupt or
  stray file behind.

### Step 12 — Doc fix
`f1564b3` — the README's Docker instructions never mentioned running
migrations or the seed script inside the container. A fresh
`docker compose up` boots against an **empty database** — `/health` still
passes (it's just a DB ping) but every real endpoint would 500. Added the two
required commands to `README.md`.

---

## 3. Key architectural decisions and reasoning

**Auth model.** Phone+PIN for operator/supervisor, email+password for
management — this was specified by the user, not derived. Implementation
detail worth knowing: `users.phone_number` (login credential) is a
**separate column** from `users.whatsapp_number` (alert destination), even
though in practice they'll usually hold the same value — one is a login
credential, the other an alert destination, and a WhatsApp-number change
shouldn't silently break someone's login. Which hash column
(`pin_hash`/`password_hash`) is populated determines which login endpoint
works for a user — this is enforced by the `users` create/update endpoints
(exactly one of pin/password required, matching role), not by a DB
constraint.

**Permission model.** See step 4 above — this is the one significant thing
in this build that was **inferred, not specified**. It's grounded in
`architecture.md`'s explicit statement that management is fully read-only,
but the operator-vs-supervisor write boundaries for each of the six
resources were a judgment call. Worth a deliberate review against how the
Kuberpack team actually wants to work before staff start relying on it.

**Photo storage.** Local disk (`backend/uploads/`), not cloud storage. This
was a judgment call made in step 9 (see that section above) to make "wire
into mark-as-done" actually functional, without committing to a long-term
storage strategy that `todo.md` explicitly still calls open. If real cloud
storage (S3-compatible, etc.) is chosen later, the only thing that needs to
change is `backend/app/routers/photos.py`'s `upload_photo` function — the
frontend only ever deals with the `url` string it returns, never the storage
mechanism.

**Timezone handling.** `CLAUDE.md` says "all dates/times stored in UTC,
displayed in local (Sonipat) time." Timestamps (`created_at`, `completed_at`,
`reported_at`, etc.) are `timestamptz` columns, always UTC internally — this
was correct from the start. But **"today" for due-date/scheduling logic is a
local-calendar concept, not a UTC one** — IST is UTC+5:30, so UTC and IST
disagree about what day it is for the first 5.5 hours of every IST day. This
was originally implemented wrong (using UTC's `.date()`) and fixed in step 6
— see §4. The fix, `app/core/time.py::today_local()`, is now the only place
"today" should ever be computed for scheduling purposes; if new scheduling
logic is added later, use that function, not `date.today()` or
`datetime.now(timezone.utc).date()`.

**API wire format.** camelCase JSON in and out (see step 7). Python/DB stay
snake_case per CLAUDE.md; only the HTTP-layer serialization changed. Enum
*values* (e.g. `"part_replacement"`) are unaffected — the alias generator
only renames field keys, not string values a field can hold.

**Recurring schedule basis.** Next due date = completion date + interval,
not original due date + interval (see step 5). Explicitly flagged as a
judgment call at the time; easy to change if wrong.

**Status computation split.** The *stored* `task_instances.status` column is
only updated by the daily backend job (step 10) and can be up to 24h stale.
The *frontend's displayed* status color is always computed live from
`due_date` (step 8) and never trusts the stored column for display purposes.
This is deliberate — a live computation is always accurate at page-load
time; a batch job that ran hours ago might not be.

---

## 4. Every real bug found and fixed

These are worth knowing about specifically so none of them get silently
reintroduced by a future edit that looks reasonable in isolation.

1. **Alembic downgrade left Postgres enum types behind** (step 2). Alembic's
   autogenerate emits `DROP TABLE` on downgrade but not `DROP TYPE` for
   native Postgres enums, so a downgrade→upgrade cycle failed with
   `DuplicateObject` on the next `CREATE TYPE`. Fixed by adding explicit
   `sa.Enum(name=...).drop(op.get_bind(), checkfirst=True)` calls to the
   migration's `downgrade()` in
   `backend/alembic/versions/7dfe001e88c4_initial_schema.py`. If new enum
   columns are added in future migrations, remember this pattern.

2. **SQLAlchemy silently wiped audit-trail attribution on user delete**
   (step 4) — the most significant one. SQLAlchemy's default ORM delete
   behavior loads a parent's relationship collections and proactively sets
   their (nullable) FK columns to `NULL` before deleting the parent —
   *instead* of letting the database's `RESTRICT` constraint reject the
   delete. This meant deleting a user with task/repair/part history would
   silently null out `completed_by`/`reported_by`/`replaced_by` on all their
   historical records rather than being blocked, which is exactly the
   failure mode the RESTRICT constraint (step 2) was supposed to prevent —
   and it wasn't actually working. Fixed with `passive_deletes=True` on all
   five `User`-side relationships in `backend/app/models.py`, which tells
   SQLAlchemy to defer entirely to the database's FK behavior instead of
   managing it in Python. Verified: deleting a user with history now
   correctly 409s with the audit trail completely untouched. **If any new
   relationship is added from `User` to another table with a nullable FK,
   it needs `passive_deletes=True` too, or this bug comes back for that
   relationship.**

3. **Stale credential on role change** (step 4) — a related, smaller issue.
   Promoting a user's role (e.g. operator → management) could leave their
   old `pin_hash` in place even after a `password_hash` was set, opening a
   login path that shouldn't exist for the new role — a management user
   shouldn't be able to log in via the PIN endpoint. Fixed in
   `backend/app/routers/users.py::update_user` by explicitly clearing the
   now-irrelevant hash column whenever role changes. Verified: an old PIN
   stops working the moment someone's promoted.

4. **UTC vs local-timezone bug in due-date computation** (step 6, see §3
   above for the full explanation). `complete_task_instance()` was computing
   the next due date from `datetime.now(timezone.utc).date()`. Not
   observable in the sandbox this was built in (its system clock runs on
   UTC with no offset, so the bug was silent there), but would have produced
   due dates off by a day for roughly a quarter of every day once deployed
   on a real Sonipat (IST) machine. Fixed by adding
   `backend/app/core/time.py::today_local()` and using it in both
   `complete_task_instance()` and the seed script's due-date generation.

5. **API client would have silently broken photo uploads** (step 9).
   `frontend/src/api/client.ts`'s `apiFetch` unconditionally set
   `Content-Type: application/json` on every request. A `FormData` body
   (the photo upload) needs the browser to set its own multipart
   `Content-Type` with a boundary string — forcing JSON's content type would
   have made the upload arrive malformed. Fixed by detecting
   `init?.body instanceof FormData` and omitting the header in that case.
   Caught before it ever shipped, during the same step that introduced the
   upload flow — but if any *other* new endpoint ever needs a non-JSON body
   (e.g. `x-www-form-urlencoded`), check this logic still does the right
   thing for it.

6. **Backup script left a stray `.tmp` file on failure** (step 10, minor).
   `scripts/backup.sh` wrote to a `.tmp` file and renamed it on success —
   correct, no corrupt final dump was ever produced on failure — but a
   failed run (e.g. bad credentials) left the `.tmp` file behind
   permanently, since it doesn't match the `*.sql.gz` glob the retention
   pruning looks for. Fixed with a `trap 'rm -f "$tmp_file"' EXIT`. Found by
   deliberately testing the failure path, not just the happy path.

None of the above are still open — all six were fixed and re-verified in the
same step they were found in.

---

## 5. Seeded test credentials

From `backend/app/seed.py` (re-run with
`cd backend && .venv/bin/python -m app.seed` — **this wipes and reseeds
task/machine/user data**, safe for a dev/test database, not something to run
against real data without reading the script first):

| Name | Role | Phone | PIN | Email | Password |
|---|---|---|---|---|---|
| Ramesh Kumar | operator | 9812345001 | 1234 | | |
| Suresh Yadav | operator | 9812345002 | 2345 | | |
| Vikram Singh | operator | 9812345003 | 3456 | | |
| Anita Sharma | supervisor | 9812345004 | 4567 | | |
| Rajesh Verma | supervisor | 9812345005 | 5678 | | |
| Priya Kapoor | management | | | priya.kapoor@kuberpack.com | ChangeMe123! |

All fake — `@kuberpack.com` and the phone numbers are placeholders, not real
Kuberpack staff. Same table is in `README.md`.

---

## 6. Frontend vs backend endpoint coverage — the complete gap list

**⚠️ Superseded in part by §9 below.** This section describes the gap as it
stood at the end of the original build session. Priority 1 of the
frontend-coverage build-out (§9) has since closed two of these gaps
(`repair_logs` create, `part_replacements` create). The table below is left
as originally written for historical context; §9's table is the current
one.

The backend has **36 endpoints** across 9 routers. The frontend calls **12**
of them. This is not an oversight to silently fix — it reflects that the
explicit build order for the frontend (machine list, detail/timeline,
mark-done, overdue view, management summary) never asked for create/edit/
delete UI anywhere. Listed here so nothing is assumed to exist that doesn't.

| Resource | Used in frontend | Gap — API-only, no UI |
|---|---|---|
| **auth** (`/auth/*`) | all 3 (`login/pin`, `login/password`, `me`) | — |
| **config** (`/config`) | the 1 | — |
| **photos** (`/photos`) | the 1 (upload, used by mark-done) | — |
| **machines** | `GET` list, `GET` by id | `POST` create · `PATCH` update · `DELETE` |
| **task_types** | `GET` list | `GET` by id · `POST` create · `PATCH` update · `DELETE` |
| **task_instances** | `GET` list, `PATCH` mark-done | `GET` by id · `POST` create · `PATCH` reschedule · `DELETE` |
| **repair_logs** | `GET` list | `GET` by id · `POST` create · `PATCH` resolve · `DELETE` |
| **part_replacements** | `GET` list | `GET` by id · `POST` create · `PATCH` update · `DELETE` |
| **users** | *(none)* | `GET` list · `GET` by id · `POST` create · `PATCH` update · `DELETE` — **entire resource has zero frontend usage** |

**The pattern:** every resource has read (list) working in the UI. Beyond
that, only two write actions exist anywhere in the frontend — mark-done and
photo upload. Concretely, right now nobody can, through the app itself:
add a machine, add a task type to one, correct a wrong due date
(reschedule), resolve a reported repair, log a part swap, create an ad-hoc
task instance, or manage staff accounts. All of that is reachable only via
direct API calls (or, for initial setup, the seed script). This is the
natural "what to build next" list if that's the direction chosen.

This table was produced by grepping every `@router.` decorator in
`backend/app/routers/*.py` against every `apiFetch` call actually wired into
a page/component in `frontend/src/` — not from memory — so it should be
trustworthy as of this commit. Re-derive it the same way if either side
changes significantly.

---

## 7. Outstanding items before real deployment

Carried over from a "launch manifest" review during the session (an artifact
was published then; this section is the durable, in-repo version of it).

### Critical — before real use

- [ ] **Run one real `docker compose up --build` end to end.** This sandbox
      had no Docker daemon, so nothing since step 1 (§2) was verified in an
      actual container — only via backend/frontend run directly. The user
      verified Docker once, right after step 1, and nothing since.
      Afterward: `docker compose exec backend alembic upgrade head` then
      `docker compose exec backend python -m app.seed` (or real data) —
      compose starts against an empty DB, see step 12 in §2.
- [ ] **Fix GitHub's default branch** — still the feature branch, not
      `main`. See §1.
- [ ] **Replace every default secret:**
  - `backend/.env`: `JWT_SECRET` is still the code's dev fallback
    (`"change-me-in-.env"`)
  - root `.env`: `POSTGRES_PASSWORD` is still `maintain`
  - the seeded `ChangeMe123!` management password — delete that user or
    change it before anyone real logs in with it
- [ ] **Update `CORS_ORIGINS`** in `backend/.env` — currently only allows
      `http://localhost:5173`. Needs the real deployed frontend URL before
      the app is reachable from anywhere else.

### Before real data goes in

- [ ] **Swap seed data for real Kuberpack data** — edit the `MACHINES` /
      `USERS` / `TASK_TYPES` constants at the top of `backend/app/seed.py`.
- [ ] **Pick a WhatsApp BSP** (Gupshup/Twilio/Interakt — not chosen yet) and
      **set up SMTP** — both alert channels are stubbed (§2, step 10).
      Replace the two function bodies in `backend/app/services/alerts.py`;
      nothing that calls them (`notify_user`, `run_daily_check`) needs to
      change.
- [ ] **Tune alert timing** — `ALERT_UPCOMING_DAYS` (3),
      `ALERT_OVERDUE_ESCALATE_DAYS` (1), `DAILY_CHECK_HOUR` (7) in
      `backend/.env` are all explicitly placeholder defaults.
- [ ] **Review the permission model** (§3) against how the team actually
      works — it was inferred, not specified.
- [ ] **Test camera capture on a real phone** — never verified beyond
      component-logic testing in a headless browser (§2, step 9).
- [ ] **Decide what to build next given the coverage gap** (§6) — at minimum,
      creating machines/task_types and managing users currently requires
      direct API access; that may or may not be acceptable long-term.

### Ongoing

- [ ] **Schedule `scripts/backup.sh` via host crontab** — not automatic yet;
      see the Backups section of `README.md` for the exact crontab line.
- [ ] Decide who reviews/merges future PRs against `main`.

### Optional / explicitly deferred

- No automated test suite (pytest/vitest) — every verification claim above
  is from live manual/browser testing performed during development, not
  from committed regression tests. If the project grows, this is worth
  reconsidering.
- `todo.md` Phase 5 items: PDF export, search/filter across machines and
  history, the actual deploy to the shared PC/server.
- HTTPS/TLS — not required by the current architecture (internal-only, no
  public exposure per `architecture.md`), but worth a look before photo
  uploads or auth tokens ever leave a trusted LAN.

---

## 8. Things to be explicitly uncertain about

Stated plainly rather than glossed over:

- **Docker Compose**, beyond the one check right after step 1, is unverified
  for everything built since. High confidence it works (nothing in later
  steps touched `docker-compose.yml` itself except adding no new services),
  but "high confidence" is not "verified."
- **The permission model** (§3, §6) is this build's single largest inference
  from indirect evidence (`architecture.md`'s prose) rather than an explicit
  spec. It was exercised thoroughly for internal consistency (all 3 roles ×
  all 6 resources × read/write), but never checked against actual Kuberpack
  workflow expectations.
- **Real camera hardware behavior** (native camera-vs-gallery picker on
  actual iOS/Android) was never tested — only the underlying DOM element's
  behavior, via Playwright's `setInputFiles()`, which cannot exercise what
  happens when a real phone browser sees `capture="environment"`.
- **Alert de-duplication** doesn't exist (§2 step 10) — every currently
  overdue/upcoming item gets included in every day's alert run. Fine while
  stubbed; will spam real recipients once a real WhatsApp/email provider is
  wired in, unless addressed first.
- **Local `main` branch staleness** in whatever sandbox produced this file —
  see §1. Not a real risk (origin/main has everything) but worth knowing so
  nobody panics if a stale local checkout looks wrong.

---

## 9. Frontend UI coverage build-out — Priority 1 (floor operations)

A follow-up session (same day, branch `claude/kuberpack-maintenance-tracker-p5dqu5`)
started closing the §6 gap, in the priority order the user specified: floor
operations first, then supervisor setup/admin, then user management, with a
check-in after each group. **This entry covers Priority 1 only** — the other
two groups have not been started.

### What was built

Two new write actions on `MachineDetailPage`, next to the existing mark-done
action, both gated by the same role check mark-done already used (renamed
from `canMarkDone` to `canDoFloorWork` since it now gates three actions, not
one — pure rename, no behavior change to the existing mark-done gate):

- **Report a repair** — `frontend/src/components/ReportRepairForm.tsx`.
  Collapsed to a single button by default; expands to a form (issue
  description, required; downtime minutes, optional) on click. Submits via
  a new `createRepairLog()` in `frontend/src/api/repairLogs.ts`, calling
  the existing `POST /repair-logs` endpoint — no backend changes needed,
  that endpoint already existed and already takes `reported_by` from the
  JWT, not the request body.
- **Log a part replacement** — `frontend/src/components/LogPartReplacementForm.tsx`.
  Same collapse/expand pattern (part name required, replaced-on date
  defaulting to today in local/browser time, notes optional). Submits via
  a new `createPartReplacement()` in `frontend/src/api/partReplacements.ts`,
  calling the existing `POST /part-replacements` endpoint.

Both forms live in a new "Actions" section on the machine detail page,
above "Pending tasks." On successful submit they call the existing
`repairLogs.refetch()` / `partReplacements.refetch()` (the `useAsync` hooks
already wired up on that page) so the new entry appears in the History
timeline immediately, without a full page reload.

**No backend changes were needed or made** — both endpoints, their
permission gates, and their attribution-from-JWT behavior already existed
and were exercised for the first time by real UI in this step.

### Role visibility (per the existing, unchanged permission model)

- **Report a repair**: operator + supervisor. Management sees neither the
  "Actions" section nor its two buttons at all (not just disabled) —
  verified in the browser, see below.
- **Log a part replacement**: operator + supervisor. Same management
  exclusion.

This matches the backend's existing `_report_roles = require_roles(operator,
supervisor)` on both `POST /repair-logs` and `POST /part-replacements` — the
frontend gate mirrors, not redefines, the backend's rule.

### Verified — real Postgres, real browser

No Docker daemon in this sandbox (same limitation noted in §7/§8 for the
original build) — verified via local Postgres 16 + `uvicorn` + Vite dev
server directly, same approach the original session used successfully.

- Fresh local Postgres 16 database, `alembic upgrade head`, then
  `python -m app.seed` — clean migration and seed against a database this
  session created itself, not a reused one.
- **TypeScript strict mode**: `tsc -b` clean, zero errors.
- **oxlint**: clean except the two pre-existing, already-documented
  warnings in `useAsync.ts` (unrelated to this change).
- **Playwright driving the real running dev server** (Chromium at
  `/opt/pw-browsers/chromium-1194`, not a stub):
  - Logged in as operator (Ramesh Kumar) → machine detail page → "Actions"
    section with both buttons visible.
  - Reported a repair (issue description + downtime minutes) → form
    collapsed, entry appeared in History ("Repair: ... · open") without a
    page reload.
  - Logged a part replacement (part name + notes, default date) → same
    collapse-and-appear-in-History behavior.
  - **Confirmed directly in Postgres**, not just trusted the UI: both new
    rows exist in `repair_logs`/`part_replacements` with `reported_by`/
    `replaced_by` correctly set to Ramesh Kumar's actual user id (attribution
    really does come from the JWT server-side, not the form).
  - Logged out, logged in as management (Priya Kapoor) → navigated to the
    **same** machine detail URL directly → confirmed zero count for the
    "Actions" `<h2>`, the "Report a repair" button, the "Log a part
    replacement" button, and "Mark done" — management is fully excluded,
    not merely disabled.
  - Logged in as supervisor (Anita Sharma) → confirmed the "Actions"
    section is visible and a repair report submits successfully (operator
    and supervisor share this permission, per the model).
  - Submitted the part-replacement form with the required "part name" field
    left empty → HTML5 `required` validation blocked the submit client-side
    (form stayed open, no request sent), confirming the browser-level guard
    works.
  - **Follow-up, done directly against the API with `curl` (bypassing the
    browser/HTML5 validation entirely)**, to close the gap noted above:
    logged in via `POST /auth/login/pin`, then sent `POST /repair-logs`
    with `issueDescription` as `""` and, separately, omitted entirely —
    both `422`, `string_too_short` / `missing` respectively on the
    `issueDescription` field. Same for `POST /part-replacements`: empty
    `partName` → `422 string_too_short`; `partName` omitted → `422
    missing`; `replacedAt` omitted → `422 missing`. A valid request
    immediately after (real `issueDescription`, no other changes) returned
    `201`, confirming the 422s were genuinely about the missing/empty
    fields and not some unrelated breakage. Both endpoints' server-side
    validation is now directly confirmed, not just inferred from the
    original session's testing.

### Not built / not touched in this step

- Priority 2 (create/edit/delete machine & task_type, manual task_instance
  creation, reschedule, resolve repair_log) — not started as of this entry;
  see §10 below for its completion.
- Priority 3 (user management UI) — not started.
- **Undo/reopen a mark-done task instance**: confirmed still does not exist
  anywhere on the backend (grepped the whole `backend/` tree for
  reopen/undo/unmark — no matches; `task_instances.py` has only mark-done,
  reschedule, and delete). Not built here per instruction — flagging again
  so it doesn't get assumed to exist.

---

## 10. Frontend UI coverage build-out — Priority 2 (supervisor setup & admin)

Same session, same branch. Closes the six remaining items from Priority 2:
create/edit/delete machine, create/edit/delete task_type (enforcing the
category/interval invariant), manual (ad-hoc) task_instance creation,
reschedule a task_instance, and resolve a repair_log. All six are
**supervisor-only**, per the existing permission model — no change to that
model, only UI built for what the backend already enforces.

### What was built

- **Create machine** — `frontend/src/components/CreateMachineForm.tsx`.
  Toggle button ("+ Add machine") above the machine grid on
  `MachineListPage`, supervisor-only. On success, refetches the machine
  list.
- **Edit machine** — `frontend/src/components/EditMachineForm.tsx`. Toggle
  button in the machine detail page header, pre-filled, supervisor-only.
- **Delete machine** — plain button + `window.confirm` handled directly in
  `MachineDetailPage.tsx` (not its own component — a single confirm+call+
  redirect didn't earn a file). The confirm text spells out that this
  cascades through task types, task instances, repair logs, and part
  replacements, since `Machine`'s SQLAlchemy relationships are all
  `cascade="all, delete-orphan"` with DB-level `ondelete="CASCADE"` — a
  machine delete is a genuinely destructive, unrecoverable action, not a
  soft delete. On success, navigates back to the machine list.
- **Create/edit task_type** — `frontend/src/components/TaskTypeForm.tsx`, a
  single component parameterized by an optional `taskType` prop (present =
  edit, absent = create), since both share the same category/interval
  logic and duplicating that felt like the wrong tradeoff. The interval
  field is conditionally hidden and the category `repair` sends
  `defaultIntervalDays` as `undefined` (create) or explicit `null` (edit,
  so the PATCH actually clears a previously-set interval) — this mirrors
  the backend's `category=repair-iff-null-interval` validator
  (`TaskTypeCreate`'s `model_validator` / the router's re-check on update)
  rather than reimplementing it; the backend is still the source of truth
  and was independently re-verified via direct `curl` (see below).
- **Delete task_type** — inline button + `window.confirm` inside the new
  Task types list (see below), same cascade-warning reasoning as machine
  delete (a task_type delete cascades to its task instances).
- **Task types list/orchestration** —
  `frontend/src/components/TaskTypesSection.tsx`. New "Task types" section
  on the machine detail page, supervisor-only (task-type *reads* are open
  to every role on the backend, but raw task-type management has no
  reason to be visible to operator/management, so the whole section is
  gated). Lists each task type with Create instance / Edit / Delete
  inline, plus an "Add task type" toggle at the bottom.
- **Create task_instance manually (ad-hoc)** —
  `frontend/src/components/CreateTaskInstanceForm.tsx`. Small due-date +
  optional-notes form, opened per-task-type from the "Create instance"
  button in the Task types list (a manual instance is always *for* a
  specific task type, so that's where it's anchored). Date input defaults
  to today in local/browser time via the new shared
  `frontend/src/lib/date.ts::todayLocalDate()` (extracted from
  `LogPartReplacementForm`, which now imports it too, instead of keeping
  two copies of the same function).
- **Reschedule task_instance** —
  `frontend/src/components/RescheduleTaskInstanceForm.tsx`. Toggle button
  next to Mark done / Take photo in the Pending tasks list,
  supervisor-only (operators can mark done but not reschedule, per the
  existing model). Due date + optional reason, calls the existing
  `PATCH /task-instances/{id}/reschedule`.
- **Resolve repair_log** —
  `frontend/src/components/ResolveRepairLogForm.tsx`. Small "Resolve"
  button next to any repair entry in the History timeline that doesn't yet
  have a `resolvedAt`, supervisor-only. Optional resolution notes, calls
  the existing `PATCH /repair-logs/{id}/resolve`.

**No backend changes were needed or made** — all six endpoints, their
permission gates, validators, and cascade-delete behavior already existed.

### Role visibility

Every one of the six new actions above is **supervisor-only**: the
"Actions" section (Priority 1) stays operator+supervisor as before, but
everything from Priority 2 — Edit/Delete machine, the whole Task types
section, Reschedule, Resolve — is gated on `user?.role === 'supervisor'`
(a new `isSupervisor` boolean in `MachineDetailPage`, alongside the
existing `canDoFloorWork`). Verified in the browser for both excluded
roles, not just assumed from the gate existing in the code (see below).

### Verified — real Postgres, real browser, plus direct API calls

Same no-Docker-daemon setup as Priority 1 (local Postgres 16 +
`uvicorn` + Vite dev server), fresh `alembic upgrade head` +
`python -m app.seed` before testing, re-seeded again afterward to leave a
clean baseline.

- **TypeScript strict mode** (`tsc -b`) and **oxlint**: both clean, same
  two pre-existing `useAsync.ts` warnings as before and nothing new.
- **Playwright driving the real dev server**, as supervisor (Anita
  Sharma) unless noted:
  - Created a machine ("Laminator 2") from the list page → appeared in the
    grid, opened its detail page.
  - Created a `cleaning` task type with a 7-day interval, and a `repair`
    task type — confirmed the interval input is hidden and replaced with
    the "event-driven" explanatory text the instant `repair` is selected
    in the category dropdown, before any submit.
  - Edited the cleaning task type's description → updated in place.
  - Created an ad-hoc task instance from that edited task type → appeared
    in Pending tasks with the chosen due date.
  - Rescheduled that pending instance to a new due date with a reason →
    due date updated in place, still supervisor-only.
  - Reported a repair on the new machine, then resolved it with notes →
    History entry flipped from "open" to "resolved," Resolve button
    disappeared (only unresolved repairs show it).
  - Deleted the `repair`-category task type (zero instances) → gone from
    the list.
  - Deleted the whole machine → redirected to the machine list, confirmed
    absent once the list actually finished loading (see the caveat
    below), **and independently confirmed directly against Postgres**:
    zero rows in `machines`, zero `task_types`/`repair_logs` referencing
    the deleted machine's id, machine count back to the seeded baseline
    of 5.
  - Separately deleted a **seeded** task type that had two real task
    instances under it ("Clean rollers and belts" on Corrugator 1, not
    the zero-instance one above) — the more meaningful cascade case.
    Confirmed via direct Postgres query, not just the UI, that both the
    task type row and both task-instance rows are gone.
  - Logged in as **management** and **operator** and, after properly
    waiting for each page to finish loading (see caveat), confirmed zero
    count for every one of: "+ Add machine", Edit machine, Delete
    machine, the "Task types" section, Reschedule, Resolve. Operator
    additionally confirmed to *still* see Report a repair (1) and Mark
    done (2) — the Priority 1 gate is untouched by this change.
  - **Direct API calls with `curl`**, bypassing the UI entirely: a
    `cleaning` task type with no `defaultIntervalDays` → `422`; a `repair`
    task type *with* `defaultIntervalDays` set → `422` — both confirm the
    backend's own invariant, not just the frontend's conditional field.
    An operator's token attempting `POST /machines` → `403`, confirming
    the role gate is enforced server-side, not just hidden client-side.

**Caveat worth stating plainly**: an early pass of this verification
checked role-exclusion (`.count()` on buttons that shouldn't be visible)
immediately after `waitForURL`, before the page's own data fetch had
resolved — on a page that briefly shows "Loading…", a 0-count check at
that moment is meaningless (everything reads as absent, correctly-gated
or not). Caught this, redid every exclusion check gated behind a real
load-completion signal instead (e.g. waiting for the "History" heading,
which renders for every role once data has actually arrived), and the
results above are from that corrected pass. Flagging this so the
methodology is visible, not just the "PASS" outcome.

### Not built / not touched in this step

- Priority 3 (user management UI: list/create/edit/delete users) — not
  started as of this entry; see §11 below for its completion.
- Undo/reopen a mark-done task instance — still confirmed absent from the
  backend (see §9); unchanged this session.

---

## 11. Frontend UI coverage build-out — Priority 3 (user management)

Same branch (`claude/kuberpack-maintenance-tracker-p5dqu5`). Before this
step started, **PR #3** (containing Priority 1 + Priority 2, §9–§10) was
merged into `main` — merge commit `40447b2`, via GitHub's merge-commit
strategy, same as PR #1 and PR #2. The branch was then reset to a fresh
`origin/main` (`git checkout -B <branch> origin/main` +
`push --force-with-lease`) before this work began, per this repo's
"a merged PR is finished, restart follow-up work from main" convention —
so this section's commits sit directly on top of everything in §9–§10,
not stacked on the old, now-merged branch history.

This closes the last item from the original coverage gap (§6): **users**
went from zero frontend usage to full CRUD, completing all three planned
priorities.

### What was built

- **List/view users** — `frontend/src/pages/UsersPage.tsx`, new page at
  `/users`. Visible to **supervisor + management** (matching
  `GET /users`'s `_read_roles`), with a new "Users" nav link in
  `NavBar.tsx` filtered to those two roles — operators never see the link,
  and the page itself also checks the role and shows a plain message
  instead of calling the API if reached directly (defensive; the backend
  would 403 anyway, but this avoids firing a request that's guaranteed to
  fail and avoids a confusing error state).
- **Create user** — `frontend/src/components/CreateUserForm.tsx`,
  supervisor-only. Role selection drives which fields show: `management`
  → email + password (min. 8 chars); `operator`/`supervisor` → phone
  number + PIN (4–6 digits, matching the backend's regex). WhatsApp number
  is always optional, for alerts, independent of login credentials (per
  the existing `phone_number` vs `whatsapp_number` separation documented
  in §3).
- **Edit user** — `frontend/src/components/EditUserForm.tsx`,
  supervisor-only, including role changes. This is the one place real
  logic lives on the frontend rather than just mirroring the backend: a
  `credentialFamily(role)` helper (`'pin'` for operator/supervisor,
  `'password'` for management) compares the user's *original* role
  against the role being set. If they cross the pin/password boundary,
  the new credential field is marked `required` in the UI, because the
  backend's `update_user` (see §4 item 3 and §3) clears the now-irrelevant
  hash the moment role changes and then 422s if the new one isn't present
  — so leaving that field optional in the UI would just produce a
  confusing validation error after submit instead of before. If role
  *doesn't* cross that boundary, the credential field is optional
  ("leave blank to keep current"). The backend remains the actual
  authority; this is UI guidance built to match it, independently
  re-verified below rather than assumed correct from reading the code.
- **Delete user** — inline button + `window.confirm` in `UsersPage.tsx`
  (not a separate component — same reasoning as the machine-delete button
  in §10). On a `409` (user has task/repair/part history — the existing
  `RESTRICT` + `passive_deletes` behavior from §2 step 4 / §4 item 2), the
  backend's exact error message ("Cannot delete a user with existing
  task/repair/part history") surfaces inline via the existing `ApiError`
  handling — no special-case code needed, since that path already worked
  correctly for every other resource's delete button.

**No backend changes were needed or made** — `users.py`'s router, schemas,
and validators (§2 step 4, credential-family logic from §4 item 3) already
existed exactly as needed; this step only builds UI for them.

**Update:** the self-delete gap flagged above was raised and fixed as a
same-day follow-up — see the addendum at the end of §11 below.

### Role visibility

- **View the Users page**: supervisor + management (management read-only —
  no "+ Add user", no Edit/Delete buttons render for them at all).
- **Create/Edit/Delete a user**: supervisor only.
- **Operators**: no nav link, no page access (would 403 if they reached
  `/users` directly by URL; the page shows a plain message instead of
  attempting the call).

### Verified — real Postgres, real browser, plus direct API calls

Same no-Docker-daemon setup as §9/§10 (local Postgres 16 + `uvicorn` + Vite
dev server), fresh `alembic upgrade head` + `python -m app.seed` before
testing, re-seeded again afterward.

- **TypeScript strict mode** (`tsc -b`) and **oxlint**: both clean, same
  two pre-existing `useAsync.ts` warnings, nothing new.
- **Playwright driving the real dev server**:
  - Operator: confirmed no "Users" nav link (checked after waiting for the
    machine grid to actually render — the load-completion-signal lesson
    from §10 applied from the start this time).
  - Management: confirmed the "Users" nav link *is* present and the page
    loads all 6 seeded users, but with zero "+ Add user"/Edit/Delete
    controls. (One early check of the management nav-link visibility was
    done right after `waitForURL`, before the page had settled, and
    returned a false "0" — caught immediately, redone with a proper wait,
    confirmed correctly present. Noting this the same way §10 did, rather
    than only reporting the corrected number.)
  - Supervisor: created an `operator` user (phone+PIN) and a `management`
    user (email+password) — both appeared correctly in the list with the
    right contact field shown per role.
  - Renamed a user without changing role — confirmed the PIN field had no
    `required` attribute (optional, as intended).
  - Changed a user's role from `operator` to `management` — confirmed the
    password field became `required` the instant the role dropdown
    changed, filled it in, saved successfully.
  - **Logged out and confirmed the credential swap actually took effect**:
    the old PIN no longer logs that user in at all (error shown, stays on
    `/login`), the new password does (redirected to `/summary` as
    management). This is the same bug-fix behavior documented in §4 item
    3, now re-exercised through the real UI instead of only a direct API
    call.
  - Attempted to delete a user with real history (Ramesh Kumar, who has a
    completed task instance) — got the backend's `409` message inline,
    confirmed the user is still in the list afterward.
  - Deleted two users with zero history (both freshly created in this
    test session) — both succeeded, confirmed gone from the list.
  - **Direct API calls with `curl`**, bypassing the UI: an operator's
    token against `GET /users` → `403` (operators aren't in
    `_read_roles`); an operator's token against `POST /users` → `403`; a
    `management`-role create with no `password` → `422`; an
    `operator`-role create with no `phoneNumber` → `422`; an
    `operator`-role create with a 3-digit PIN (violates the `\d{4,6}`
    pattern) → `422`.
  - **Confirmed directly in Postgres** after the whole test pass: exactly
    6 users remain (back to the seeded baseline), the rename persisted,
    both test-created users are gone — not just "the UI stopped showing
    them."

### Not built / not touched in this step

- Nothing left from the three planned priorities — all of Priority 1, 2,
  and 3 are now built and verified. See §12 below for the honest summary
  of what that does and doesn't mean.
- Undo/reopen a mark-done task instance — still confirmed absent from the
  backend; still not built (never asked to be, per the original
  instruction — flagging its absence was the ask, not building it).

### Addendum — self-delete guard (same-day follow-up)

The self-delete gap flagged above was raised as a follow-up request and
closed the same day, on the same branch/PR (#4).

- **Backend**: `backend/app/routers/users.py::delete_user` now takes
  `current_user: User = Depends(_write_roles)` (previously discarded as
  `_user`) and compares `user.id == current_user.id` before the delete,
  raising `409` ("You cannot delete your own account") if they match —
  checked *before* `db.delete`/`commit_or_409`, so it never touches the
  row. Chose `409` over `403` for consistency with the sibling
  history-based rejection already on this same endpoint (both are "delete
  rejected because of what this row is/means," not an authorization
  failure — the caller has the role to delete users in general).
- **Frontend**: `UsersPage.tsx` hides the Delete button entirely (not
  disabled — matches the existing "hidden, not just disabled" convention
  used everywhere else for role-gated actions in this codebase) on the
  row where `u.id === currentUser?.id`, and labels that row "(you)" for
  clarity. Edit is still available on your own row — only delete is
  blocked.
- **Verified**: direct `curl` — a supervisor's own token against
  `DELETE /users/{their-own-id}` → `409` with the exact message above,
  confirmed via a follow-up `GET` that the account still exists
  afterward; the same supervisor deleting a *different*, freshly-created
  zero-history user → `204`, confirming the guard is scoped to self only
  and didn't regress normal deletes. **Real browser**, supervisor logged
  in as Anita Sharma: her own row shows "(you)" with only an Edit button
  (zero Delete buttons found for that row), every other row still has
  both Edit and Delete, and a freshly created throwaway user was deleted
  successfully end-to-end through the UI to confirm the normal path still
  works.

---

## 12. Where the frontend coverage build-out stands now

All three priorities from the original ask are done:

- **Priority 1** (§9): report a repair, log a part replacement.
- **Priority 2** (§10): create/edit/delete machine and task_type, manual
  task_instance creation, reschedule, resolve repair_log.
- **Priority 3** (§11): list/create/edit/delete users.

Combined with what already existed before this work (mark-done, photo
upload, the three read-heavy pages), the frontend now has UI for every one
of the backend's 36 endpoints **except**: `GET` by-id on several resources
(never needed — the list views and detail-page joins cover everything the
UI actually displays) and the two-step "create machine → create task type"
flow's `GET /task-types/{id}` (same reasoning, unused because the list
endpoint plus client-side filtering already gets there). None of those are
gaps in *capability* — every write action the backend supports now has a
UI path to it.

**Still explicitly open, not part of this build:**
- Undo/reopen a mark-done task instance — confirmed absent from the
  backend across all three priority groups' checks (§9, §11) at the time
  this section was written. **Built as a same-day follow-up — see §13.**
- Everything already listed as outstanding in §7 (secrets rotation, real
  WhatsApp/SMTP providers, camera-on-real-device testing, a full
  `docker compose up` re-verification beyond the one check after step 1)
  is untouched and still open — this build only ever touched the
  frontend's coverage of existing backend endpoints, nothing in §7's
  scope.
- **GitHub's default branch is still not `main`** — see §13's note; this
  one genuinely could not be done with the tools available in this
  session, not merely skipped.

---

## 13. Undo/reopen a mark-done task instance (built as a follow-up)

Requested directly, on the same branch, after §12 was written. This is a
**new backend endpoint** — the one place in this whole build where new
backend logic was actually needed, not just new frontend UI over an
existing one.

### What was built

- **`PATCH /task-instances/{id}/reopen`** —
  `backend/app/routers/task_instances.py`, delegating to a new
  `reopen_task_instance()` in `backend/app/services/scheduling.py`
  (mirroring where `complete_task_instance()` already lives — "the single
  place this logic lives," same reasoning as that function's own
  docstring). **Role: operator + supervisor**, the same level as mark-done
  itself — an inferred judgment call, not specified, on the reasoning that
  reopening is the direct inverse of an action operators already do
  (correcting your own mistake), unlike reschedule/resolve which are
  supervisor-only overrides of someone else's work. Flagging this the same
  way the original permission model was flagged as inferred (§3).
- **The real design problem**: the schema has no column linking a
  completed instance to the next occurrence `complete_task_instance()` may
  have spawned for it. Reopening has to infer that relationship instead of
  reading it, and get it right in three cases:
  1. **No successor exists** (repair-category task types, or the instance
     hasn't been re-completed since) — just reset the instance to
     `pending` and clear `completedAt`/`completedBy`/`notes`/`photoUrl`.
  2. **A successor exists and is still untouched** (pending, never
     completed or rescheduled) — it only exists *because* this completion
     spawned it, so it's deleted as part of the undo. This is the common
     "I just made a mistake, undo it" case for a recurring task type.
  3. **A successor exists and has itself been acted on** (completed or
     rescheduled) — undoing the earlier completion would leave that
     downstream activity dangling with nothing to hang off of, so the
     whole reopen is refused with `409` instead. The caller has to reopen
     the later one(s) first — which naturally forms a LIFO undo stack,
     verified below.
- **A real bug found and fixed during this step, before it ever shipped**:
  the first implementation found "later" instances of the same task type
  via `due_date > this.due_date` (strict). That's wrong whenever two
  completions land on the same calendar day — e.g. mark done, undo,
  mark done again, all within the same session — because
  `complete_task_instance()` computes the next due date from
  `today_local()`, so two same-day completions produce two instances with
  the *same* due_date. A strict `>` comparison misses that tie entirely,
  so reopening the earlier one would silently leave the tied successor
  orphaned in the database with nothing pointing at it. Fixed by comparing
  `>=` and explicitly excluding the instance's own id. **Caught by
  deliberately reproducing the same-day chain in testing, not by code
  review** — see the verification below for the exact repro.

### Verified — real Postgres, real browser, plus direct API calls

Same no-Docker-daemon setup as §9–§11.

- **Backend import check**: `python -c "import app.main"` — clean, and
  `alembic upgrade head` produced no new migration (this feature needed no
  schema change, by design — see above).
- **TypeScript strict mode** (`tsc -b`) and **oxlint**: both clean, same
  two pre-existing `useAsync.ts` warnings, nothing new.
- **Direct API calls with `curl`**, building and unwinding a real chain:
  - Reopened the seed script's one pre-completed instance → `200`, its
    auto-spawned successor confirmed deleted directly in Postgres.
  - Marked it done again (instance A, spawns B), then marked B done too
    (spawns C) — **reproduced the same-day due-date tie**: confirmed in
    Postgres that B and C landed on the identical `due_date`.
  - Attempted to reopen A while B was still `done` → `409` as expected.
  - Reopened B (the one with the tied successor C) → `200`, **confirmed C
    was actually deleted despite the tie** — this is the exact case the
    bug fix above addresses; it was re-verified after the fix, not just
    reasoned about.
  - Reopened A → `200`, now that B was unwound — confirmed exactly one
    instance remains for that task type, back to `pending`. Full LIFO
    unwind (A → B → C → undo C's effect → undo B's effect → undo A's
    effect) verified end to end.
  - A repair-category (non-recurring) instance: marked done, reopened
    cleanly with no chain to consider (`next: null` on mark-done, as
    expected).
  - Reopening an already-`pending` instance (never completed, or already
    reopened) → `409` "Task instance is not marked done."
  - A management token against `PATCH .../reopen` → `403`, confirming the
    operator+supervisor role gate server-side.
- **Real browser** (Playwright): as operator, opened a machine detail
  page, confirmed a "Reopen" button on the seeded completed entry in
  History, clicked it (through the real confirm-dialog warning about
  notes/photo clearing and possible successor removal), confirmed the
  entry disappeared from History and reappeared in Pending Tasks with a
  live-computed "Overdue" badge (due date was in the past) — and confirmed
  its previously-spawned successor (visible in Pending Tasks *before* the
  reopen, at a later due date) was gone from Pending Tasks *after* —
  the cascade cleanup working in the real UI, not just via direct API. As
  management, confirmed zero "Reopen" buttons anywhere.

### Frontend

- `frontend/src/api/taskInstances.ts::reopenTaskInstance()` — calls the
  new endpoint.
- `frontend/src/pages/MachineDetailPage.tsx` — a small "Reopen" button on
  each completed entry in the History timeline, gated by the existing
  `canDoFloorWork` (operator + supervisor). A `window.confirm` spells out
  the consequences (notes/photo cleared, a still-untouched successor gets
  removed) before calling the API, matching this codebase's established
  pattern for consequential actions (machine delete, task_type delete).
  On success, refetches task instances, which moves the entry from
  History to Pending Tasks automatically via the existing status-based
  filtering — no new client-side state machine needed.

### The GitHub default-branch request

Also asked in the same message: set GitHub's default branch to `main`
(flagged as still open since the very first build session, §1/§7). **This
was not done** — not skipped, but genuinely not possible with the tools
available in this session. Changing a repository's default branch is an
admin-level repository-settings call (`PATCH /repos/{owner}/{repo}` with
`default_branch` on GitHub's REST API), and no tool exposed by this
session's GitHub MCP server performs it — everything available operates
on PRs, branches-as-refs, files, issues, and reviews, not repository
settings. Confirmed by searching the available tools for anything
matching "default branch," "repository settings," or "administration"
before concluding this rather than guessing. Someone with repo admin
access needs to do this by hand: **Settings → General → Default branch**
on the GitHub web UI.

---

## 14. Deployment config for the real online deployment (Vercel + Railway)

Requested directly: moving from LAN-only (`architecture.md`'s original
assumption) to a real public deployment — frontend on Vercel, backend +
Postgres on Railway, over HTTPS. This section is deployment config only;
no application logic changed, and the local `docker-compose` setup was
kept fully working, not replaced.

### What was built

- **`architecture.md`** — only the Deployment Strategy section rewritten
  (as asked), everything else left intact. Now describes Vercel +
  Railway + HTTPS instead of "single internal deployment, no public
  exposure," and explicitly keeps local `docker-compose up` as still
  supported for dev/testing alongside it.
- **`backend/app/config.py`** — `Settings.database_url` gained a
  `field_validator` that normalizes both the old Heroku-style
  `postgres://` scheme and a driver-less `postgresql://` (either of which
  Railway might hand out) to the explicit `postgresql+psycopg2://` this
  app actually needs — leaving host/port/db-name/query-string (e.g. a
  `?sslmode=...` param, if Railway's URL includes one) completely
  untouched. This is the single source of truth for `database_url`
  (`alembic/env.py` already reads it via the same `get_settings()`, per
  the existing "one source of truth" comment in `alembic.ini`), so this
  one change covers both the running app and migrations.
- **`backend/Dockerfile`** — two changes, both pure deployment config:
  - Dropped `--reload` from the image's own `CMD` (a dev-mode
    file-watching flag with real overhead and zero benefit on an
    immutable production image) — moved to a `command:` override on
    `docker-compose.yml`'s `backend` service instead, so local dev's
    hot-reload behavior is completely unchanged, just relocated to where
    it actually belongs (the local-only compose file, not the image
    Railway builds and runs directly).
  - `CMD` now reads `$PORT` with an `${PORT:-8000}` fallback, via
    `sh -c "exec uvicorn ... --port ${PORT:-8000}"` (the `exec` keeps
    proper signal forwarding — no wrapper-shell zombie-process issue).
    Railway and most PaaS platforms assign the listening port dynamically
    through `$PORT`; docker-compose never sets that variable, so the
    fallback keeps local dev on the same fixed `8000` as before.
- **`docker-compose.yml`** — added the `command:` override described
  above; nothing else changed.
- **`frontend/src/api/client.ts`** — `API_BASE` now reads
  `VITE_API_BASE_URL` (falling back to the existing relative `/api` when
  unset, i.e. local dev is byte-for-byte unchanged). Also added a new
  exported `resolveAssetUrl()`, and — **this was the real find in this
  pass, not just following the literal checklist** — wired it into
  `MachineDetailPage.tsx`'s mark-done photo `<img src>`. The backend's
  `POST /photos` has always returned a bare relative path
  (`/uploads/xxx.jpg`); locally that only ever worked because Vite's dev
  server proxies `/uploads/*` to the backend, and that proxy simply
  doesn't exist in a static Vercel build. Without this fix, every
  proof-of-completion photo would have silently 404'd the moment this
  went live — the JSON API calls would have worked fine (that was the
  literal ask), but photos would have quietly broken. Caught by tracing
  every place a backend-relative path reaches the browser, not just the
  one call site named in the request.
- **`frontend/.env.example`** — documented the new `VITE_API_BASE_URL`
  alongside the existing `VITE_BACKEND_URL`, and explained why there are
  two (one Node-side dev-proxy-only, one browser-bundled production-only
  — easy to conflate, so spelled out explicitly).
- **`frontend/vercel.json`** (new, not one of the six items asked for) —
  a standard SPA rewrite (`/(.*)` → `/index.html`). This app is a
  client-side-routed SPA (`react-router-dom`, five routes including a
  dynamic `/machines/:id`) being deployed as a static build; without this,
  every deep link or page refresh on a non-root route 404s against
  Vercel's static hosting. Added proactively because the failure mode is
  bad (the app looks broken on the very first refresh) and the fix is a
  single, well-understood, zero-risk file — flagged clearly here and in
  the chat report rather than silently expanding scope.
- **`DEPLOYMENT.md`** (new) — the requested checklist: every backend env
  var Railway needs (required vs optional, with what value to use),
  every frontend env var Vercel needs, plus every Railway/Vercel-specific
  behavior this session could not verify directly (see below).
- **`README.md`** — one-line pointer to `DEPLOYMENT.md`, matching the
  existing doc-cross-reference pattern at the top of the file.

### A second real gap surfaced, not fixed (flagged, correctly out of scope)

`backend/app/main.py` mounts `/uploads` **unauthenticated** — the existing
code comment justifying that explicitly cites `architecture.md`'s old
"no public internet exposure, internal tool only" assumption, i.e. the
exact constraint this deployment change removes. Unguessable UUID
filenames are a much weaker property once genuinely public on the
internet (referrer leakage, logs, enumeration) than on a LAN. **Not
changed** — fixing it means adding auth to a static-files mount, which is
an application-logic change, and the user was explicit: "don't change any
application logic — this is purely deployment config." Flagged here, in
`DEPLOYMENT.md`, and in the chat report instead of being silently patched
or silently ignored.

### Verified

No Docker daemon available in this sandbox (same limitation noted
throughout this whole project — see §7/§8) — `docker build`/`docker
compose up --build` could not be run directly. Verified everything else
that could be, and was explicit in the report about the one thing that
couldn't:

- **`database_url` normalizer**: unit-level (all four cases — `postgres://`,
  driver-less `postgresql://`, already-explicit `postgresql+psycopg2://`,
  and a URL with `?sslmode=require` — normalize correctly, query string
  preserved), and confirmed SQLAlchemy's `create_engine()` accepts each
  result without error.
- **End-to-end with a real database**: ran a genuine `alembic upgrade
  head` against a **bare `postgresql://` URL** (no driver, simulating
  Railway's likely format) against a real fresh Postgres 16 database —
  succeeded, all 7 tables landed correctly. Then booted the actual FastAPI
  app against that same bare-scheme URL and confirmed `GET /health`
  (a real `SELECT 1` round-trip) returned `200`.
- **`$PORT` handling**: ran the Dockerfile's literal `CMD` string (`sh -c
  "exec uvicorn ... --port ${PORT:-8000}"`) directly — confirmed it
  defaults to `8000` with `$PORT` unset, and correctly binds to a
  different port (`4321`) when `$PORT` is set, with a real `/health`
  request succeeding against that dynamic port.
- **`docker-compose.yml` syntax**: `docker compose config` (validates
  without needing a running daemon) — confirmed the `backend` service's
  resolved `command` is exactly the pre-change `--reload` invocation,
  unchanged.
- **Frontend**: `tsc -b` and `oxlint` both clean (same two pre-existing
  `useAsync.ts` warnings, nothing new). Ran the **actual local dev flow**
  end to end in a real Playwright browser with `VITE_API_BASE_URL` unset
  — login, machine list, mark a task done with a photo, confirmed the
  photo's `<img src>` is still the bare `/uploads/...` path and the image
  actually loads — proving local dev is byte-for-byte unaffected. Then
  ran a **real production build** (`npm run build`, i.e. `tsc -b && vite
  build`) twice: once unset (builds clean), once with
  `VITE_API_BASE_URL=https://kuberpack-backend.up.railway.app` set —
  confirmed by grepping the built JS bundle that the URL is genuinely
  baked in via Vite's static env-var replacement, not just type-checked.

**What could not be verified** (stated plainly, not guessed at — also in
`DEPLOYMENT.md`'s closing section):
- Railway's actual UI flow for wiring a `DATABASE_URL` reference from an
  attached Postgres service.
- Whether Railway's managed Postgres requires `sslmode=require` and
  whether their provided `DATABASE_URL` already includes it.
- Whether Railway Volumes are available/sufficient to make `UPLOADS_DIR`
  persistent (uploaded photos are on local container disk, which is
  ephemeral on most PaaS platforms including likely Railway — flagged as
  a real, likely-to-bite issue in `DEPLOYMENT.md`, not fixed, since the
  real fix — cloud storage — is application-code territory already
  called out as open in `todo.md` Phase 5).
- Vercel's exact auto-detected build command/output directory for a Vite
  project once its project root is set to `frontend/`.

---

## 15. New `admin` role — tightening the user-management permission model

Requested directly: the existing model was too permissive (any supervisor
could create/edit/delete *any* other account, including other supervisors,
management, and — worst case — silently lock the team out by editing
everyone else's login credentials). Added a fourth role, `admin`, and
rewrote the write-permission rules so a supervisor's user-management power
is scoped to operators only, while every user — regardless of role —
keeps the ability to edit their own basic profile.

Final hierarchy implemented:

| Role | Can create/edit/delete (users) | Can change own role? |
|---|---|---|
| admin | any role (admin, supervisor, management, operator) | No |
| supervisor | operators only — 403 on any write touching a supervisor, management, or admin account | No |
| management | none (read-only, unchanged) | No |
| operator | none (unchanged) | No |

Every role, including operator and management, can edit their own
name/phone_number (or email, for management)/whatsapp_number — just never
their own role.

### What was built

- **`backend/app/models.py`** — added `admin` to `UserRole`.
- **`backend/alembic/versions/b926a4cc0bc4_add_admin_role.py`** (new) —
  `upgrade()` does `ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin'`
  (additive, safe on a live table with real rows — Postgres 12+ allows
  this outside a `DROP`/recreate). `downgrade()` is deliberately guarded:
  Postgres has no `ALTER TYPE ... DROP VALUE`, so reversing means
  recreating the 3-value enum and recasting the column — refuses with a
  `RuntimeError` naming the row count if any user still has `role='admin'`
  at downgrade time, rather than silently corrupting data.
- **Every existing `require_roles(UserRole.supervisor, ...)` call site**
  across `machines.py`, `task_types.py`, `task_instances.py`,
  `repair_logs.py`, `part_replacements.py`, `photos.py` — extended to also
  accept `UserRole.admin`, per the judgment call below that admin inherits
  every app-wide permission supervisor already had, not just
  user-management.
- **`backend/app/routers/users.py`** — the real logic change:
  - `_read_roles` = admin + supervisor + management (unchanged access,
    now admin included).
  - `_create_delete_roles` = admin + supervisor (baseline gate).
  - New `_check_can_manage_target(current_user, target, new_role)` helper:
    admin always passes; supervisor passes only if the *target's current
    role* is operator **and** (no role change requested, or the new role
    is still operator); everyone else (management, operator) is rejected
    before this helper is even reached.
  - `create_user` — supervisor additionally 403s inline if
    `payload.role != operator`.
  - `update_user` — dependency loosened to any authenticated user (self-edit
    must work for everyone); `is_self` short-circuits to only blocking a
    role change (`403 "You cannot change your own role"`); otherwise
    `_check_can_manage_target` applies. Credential-hashing / exactly-one-
    hash-per-role logic untouched.
  - `delete_user` — self-delete still unconditionally blocked (pre-existing
    guard), then scoped via the same helper.
- **`backend/app/create_supervisor.py` → `bootstrap_account.py`** (renamed
  via `git mv` to preserve history) — generalized to prompt for role first
  (`admin` or `supervisor`), otherwise the same interactive flow as
  before. Management isn't offered here: once one PIN-family account
  exists, a management account can be created through the app itself.
- **Frontend** — `UserRole` type gained `'admin'`; every hardcoded
  `'supervisor'`-only gate that should also admit admin was updated
  (`MachineDetailPage.tsx`'s floor-work and setup gates, `MachineListPage.tsx`'s
  create-machine gate). `CreateUserForm`/`EditUserForm` were rewritten
  around a caller-supplied `allowedRoles: UserRole[]` prop instead of a
  hardcoded role list, collapsing to a locked, non-editable label when
  there's only one legal choice (e.g. a supervisor editing an operator
  never sees a pointless one-option dropdown). `EditUserForm` gained an
  `isSelf: boolean` prop that hides the role field entirely for a
  self-edit and shows a "you can't change your own role" label instead,
  plus inline amber warnings on the phone/email field when its value has
  changed, explaining that the PIN/password stays the same but the login
  identifier changes going forward. `UsersPage.tsx` computes `allowedRoles`
  and a per-row `canManageRow()` from the viewer's own role, always
  excluding the viewer's own row (self-editing moved to a separate page).
  New `MyProfilePage.tsx` — reachable by every authenticated role via a
  new "My Profile" nav link with no role restriction — renders
  `EditUserForm` in self-edit mode against the auth context's cached user,
  and calls the new `AuthContext`/`AuthProvider` `refreshUser()` after a
  successful save so the navbar's name/role display and cached user object
  update immediately without a full reload.
- **`README.md`**, **`DEPLOYMENT.md`** — bootstrap references updated to
  `bootstrap_account.py` / `python -m app.bootstrap_account`.

### Judgment calls (flagged via `AskUserQuestion`, all resolved with the recommended option)

1. **Admin's app-wide scope** — does admin inherit every permission
   supervisor already has everywhere (machines, task types, task-instance
   reschedule, repair resolution, mark-done/report-repair/log-part), or
   only user-management? Resolved: full inheritance — an admin is a
   supervisor-plus-user-management-superpowers role, not a separate
   silo. Implemented by adding `UserRole.admin` alongside every existing
   `UserRole.supervisor` in `require_roles(...)`.
2. **Self-edit surface for roles with no existing `/users` UI access**
   (operator, management) — resolved via the new standalone `MyProfilePage`,
   visible to every role, rather than trying to retrofit self-edit into the
   admin/supervisor-only staff directory.
3. **Does management's "stays fully read-only everywhere" override
   self-edit?** — resolved no: self-edit is a distinct, universal
   capability that applies even to management.
4. **Does self-edit scope include email** (management's login identifier),
   symmetric with phone_number for the PIN-family roles? — resolved yes,
   with the same login-credential-change warning pattern applied to both.

### Verified against real Postgres + a real browser

- **Migration**: full round-trip against real Postgres 16 — `upgrade`
  confirmed via `SELECT unnest(enum_range(NULL::user_role))` returning all
  four values; `downgrade` correctly refuses (`RuntimeError` naming the
  row count) while a `role='admin'` row exists, then succeeds once removed;
  `up → down → up` leaves `SELECT count(*) FROM users` unchanged (no data
  loss). Confirmed the pre-existing seeded supervisor accounts did **not**
  auto-promote to admin — they're still `role='supervisor'` after the
  migration.
- **Bootstrap script**: ran `python -m app.bootstrap_account` end to end
  choosing `admin`, then logged in via `POST /auth/login/pin` with the
  phone+PIN just entered — succeeded, returned an admin-role JWT.
- **Full curl checklist against the running backend**, using real tokens
  for a bootstrapped admin plus the seeded supervisor/operator/management
  accounts:
  - supervisor blocked (403) creating a supervisor, a management, and an
    admin account; supervisor succeeds (201) creating an operator.
  - supervisor blocked (403) editing another supervisor and a management
    account; succeeds (200) editing an operator; blocked (403) deleting
    another supervisor.
  - management blocked (403) on both create and edit; still succeeds
    (200) on `GET /users` (read-only, unchanged).
  - self-role-change blocked (403, "You cannot change your own role") for
    all four roles individually, including admin attempting to change its
    own role.
  - admin succeeds editing a supervisor's name, editing a management
    account, and changing another user's role (promote/demote), then that
    change was reverted to leave the seed baseline untouched.
  - self-edit: changed an operator's own phone number via their own token
    — succeeded; a subsequent login attempt with the **old** number
    correctly failed (401); login with the **new** number + the same,
    unchanged PIN succeeded.
- **Real browser (Playwright, screenshots reviewed)**: supervisor's user
  list shows Edit/Delete only on operator rows, and its "Add user"/"Edit"
  role field renders as a locked "Operator" label, not a dropdown, with
  the amber phone-change warning appearing live as the field is edited.
  Admin's user list shows Edit/Delete on every row, including other
  supervisors and management. Management's user list renders with no
  Edit/Delete buttons anywhere. Operator's navbar has no "Users" link but
  does have "My Profile"; every role's own My Profile page shows the role
  field locked with a "you can't change your own role" label, and
  management's version shows the email field with the same amber
  login-credential warning as phone gets for the other roles.
- **Frontend**: `tsc -b` and `oxlint` both clean (same two pre-existing
  `useAsync.ts` warnings as every prior pass, nothing new).

After verification, the dev Postgres database was re-seeded back to its
normal baseline (`python -m app.seed`) and both dev servers plus Postgres
itself were stopped, leaving no test-only accounts (the bootstrapped admin,
the supervisor-created operator, etc.) behind.
