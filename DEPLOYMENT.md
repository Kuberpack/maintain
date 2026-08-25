# Deployment — Vercel (frontend) + Railway (backend + Postgres)

This is a checklist for the real online deployment, alongside (not replacing)
the local `docker-compose` setup described in `README.md`. See
`architecture.md`'s Deployment Strategy section for the reasoning.

Both platforms build straight from this repo. Since backend and frontend
live in subdirectories, **set each platform's project root/build context
accordingly** — Railway's service root to `backend/`, Vercel's project root
to `frontend/` — rather than the repo root.

---

## Railway — backend + PostgreSQL

1. **Add a PostgreSQL database** to the Railway project (their managed
   Postgres add-on), then **attach the backend service to it** so
   `DATABASE_URL` is wired in automatically as a variable reference,
   rather than typed in by hand. *(Railway's exact click-path for this has
   changed before and I can't verify today's UI from here — if this
   doesn't match what you see, their current docs will.)*
2. **Backend service root**: `backend/` (where `Dockerfile` lives).
3. **Environment variables** — set on the backend service:

   | Variable | Required? | Value |
   |---|---|---|
   | `DATABASE_URL` | Yes | From the Postgres attachment (step 1), not typed by hand. Whatever scheme Railway provides (`postgres://` or driver-less `postgresql://`) is normalized automatically — see the note below. |
   | `JWT_SECRET` | **Yes** | A real random string, not the dev placeholder. Generate one with `openssl rand -hex 32` or `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
   | `CORS_ORIGINS` | **Yes** | A JSON array string of allowed frontend origin(s), e.g. `["https://your-app.vercel.app"]`. **Must be JSON-array syntax, not a bare string** — this is parsed as JSON, not comma-split (see note below). Include every origin that will call this API (production domain, and any Vercel preview-deployment URL you rely on). |
   | `JWT_ALGORITHM` | No | Default `HS256`, fine as-is. |
   | `JWT_EXPIRES_MINUTES` | No | Default `10080` (7 days) — matches the shared-device assumption (workers stay logged in). Lower it if that no longer fits. |
   | `ALERT_UPCOMING_DAYS` | No | Default `3`. Still a placeholder per `PROGRESS.md` §7 — tune when ready. |
   | `ALERT_OVERDUE_ESCALATE_DAYS` | No | Default `1`. Same as above. |
   | `LOCAL_TIMEZONE` | No | Default `Asia/Kolkata` — already correct for Sonipat. |
   | `DAILY_CHECK_HOUR` | No | Default `7` (7am local time) for the daily overdue-check job. |
   | `MAX_UPLOAD_SIZE_MB` | No | Default `8`. |
   | `UPLOADS_DIR` | No | Default `uploads`. **Read the callout below before deploying — this one matters.** |

   **`DATABASE_URL` scheme**: this app's SQLAlchemy setup needs
   `postgresql+psycopg2://...` explicitly. `backend/app/config.py` now
   normalizes both the old `postgres://` scheme and a driver-less
   `postgresql://` to that automatically, so whatever format Railway hands
   you should work without editing it by hand — verified locally against
   both a bare `postgresql://` URL and a full end-to-end `alembic upgrade
   head` run. If Railway's Postgres requires SSL and the connection string
   doesn't already carry `?sslmode=require`, the normalizer preserves any
   query string untouched, so you can append that yourself if a connection
   attempt fails with an SSL-related error — not something I could test
   without a real Railway database in front of me.

   **`CORS_ORIGINS` JSON-array gotcha**: this is a Pydantic list field, so
   the raw environment variable string is JSON-decoded, not comma-split.
   `["https://your-app.vercel.app"]` works; `https://your-app.vercel.app`
   alone (no brackets/quotes) will fail to parse at startup.

   **⚠️ `UPLOADS_DIR` — uploaded photos are written to local container
   disk.** Most container-hosting platforms, Railway included, run
   services on an **ephemeral filesystem** by default: anything written to
   local disk is lost on the next redeploy, restart, or scale event. Proof-
   of-completion photos (uploaded via mark-done) would silently disappear
   the next time the service redeploys, unless you either:
   - attach a **Railway Volume** mounted at the uploads path (a
     deployment-config-level fix, no code change) — check Railway's docs
     for whether Volumes are supported on the plan/service type in use,
     since I haven't verified this against a real Railway project, or
   - move to real cloud storage (S3-compatible, etc.), which `todo.md`
     Phase 5 already calls an open question — that's an application-code
     change, out of scope for this deployment-config pass.

   This isn't new risk introduced by this deployment — it was already true
   locally without a bind mount — but it's much more likely to actually
   bite once redeploys happen regularly on a real hosting platform, so
   it's worth resolving before real proof-of-completion photos matter.

4. **Run migrations after the first deploy** (and after any future schema
   change): Railway doesn't have a `docker compose exec` equivalent, but
   the Railway CLI's `railway run` (or the dashboard's one-off command /
   shell feature, naming may vary) lets you run a command against the
   deployed service's environment:
   ```bash
   railway run alembic upgrade head
   ```
5. **Bootstrap the first real account** the same way, using the script
   added earlier in this project (prompts for role -- `admin` or
   `supervisor`):
   ```bash
   railway run python -m app.bootstrap_account
   ```
6. **Health check**: `GET /health` does a real DB round-trip (`SELECT 1`),
   not just a liveness ping — point Railway's health check at this path if
   it asks for one.

---

## Vercel — frontend

1. **Project root**: `frontend/`.
2. **Build command / output directory**: Vercel's Vite framework preset
   normally auto-detects `npm run build` and a `dist/` output directory
   correctly once the project root above is set — I haven't been able to
   confirm this against a real Vercel project, so double-check the
   detected settings before the first deploy rather than assuming.
3. **Environment variable**: do **not** set `VITE_API_BASE_URL` on Vercel.
   The browser calls same-origin `/api`. `frontend/vercel.json` rewrites
   `/api/*` and `/uploads/*` to the Railway backend so company WiFi only
   needs `*.vercel.app` (it blocks `*.up.railway.app`).

4. **`frontend/vercel.json`**: (1) proxy `/api` and `/uploads` to Railway;
   (2) SPA fallback so deep links like `/machines/:id` do not 404 on refresh.
   The Railway URL in that file must match the public backend host.

---

## After both are deployed

- Set `CORS_ORIGINS` on Railway to the real Vercel URL (step 3 above) —
  until that's done, the frontend's requests will be blocked by CORS.
- Log in through the deployed frontend with the account created via
  `bootstrap_account`, confirm a machine/task type can be created, and
  confirm a mark-done photo upload actually displays afterward.
  On company WiFi, `https://<frontend>/api/health` should return the
  backend health JSON even though `*.up.railway.app` is blocked.
- Rotate every secret still at its dev/seed default before anyone real
  uses the deployment — `PROGRESS.md` §7 already has the full list
  (`JWT_SECRET`, `POSTGRES_PASSWORD`, the seeded management password).

## What I flagged rather than guessed at

Everything above that says "I haven't verified this against a real
Railway/Vercel project" is exactly that — general knowledge about how
these platforms commonly behave, not something tested against the real
services from this environment. Specifically:

- Railway's exact UI flow for wiring a Postgres `DATABASE_URL` reference.
- Whether Railway's managed Postgres requires `sslmode=require` by default
  or already includes it in the connection string it hands out.
- Whether Railway Volumes are available/sufficient to make `UPLOADS_DIR`
  persistent for the service type in use here.
- Vercel's exact auto-detected build command/output directory for a Vite
  project once the project root is set to `frontend/`.
