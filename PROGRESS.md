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
    (form stayed open, no request sent) — didn't get to explicitly verify
    the *backend's* 422 on this specific field via direct API call, only
    that the browser-level guard works. The backend's `Field(min_length=1)`
    constraint on `part_name` was already covered by the original session's
    permission-matrix testing (§2 step 4), so this is very likely fine, but
    stating the gap plainly rather than implying full coverage.

### Not built / not touched in this step

- Priority 2 (create/edit/delete machine & task_type, manual task_instance
  creation, reschedule, resolve repair_log) — not started.
- Priority 3 (user management UI) — not started.
- **Undo/reopen a mark-done task instance**: confirmed still does not exist
  anywhere on the backend (grepped the whole `backend/` tree for
  reopen/undo/unmark — no matches; `task_instances.py` has only mark-done,
  reschedule, and delete). Not built here per instruction — flagging again
  so it doesn't get assumed to exist.
