# MRT/LRT Ticketing & Route Assignment

Flask app for a station kiosk: register passengers, serve them from a priority-aware queue,
compute the shortest route (Dijkstra), issue a printable ticket, and review analytics as an admin.

## Quick start (Windows PowerShell; on macOS/Linux use `source .venv/bin/activate`)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python run.py            # http://127.0.0.1:5000
pytest                   # run the tests
ruff check .             # lint
```

Admin login (dev defaults): `admin` / `password` → `/login` → `/reports`.

## How it works

| Step | What happens |
|------|--------------|
| Register | Passenger joins the **priority** lane (Priority, Senior Citizen, PWD, Pregnant) or **regular** lane. |
| Serve next | Priority lane first; FIFO inside each lane. Passenger becomes *serving* (not deleted). |
| Assign | Pick start/destination → route preview → train → ticket. *Cancel* returns the passenger to their original place. |
| Report | Admin-only peak hours, busiest destinations/routes, per-line stats, CSV export. |

## Project layout

```
app/
  __init__.py        application factory, error handlers
  config.py          env-driven configuration
  db.py              SQLite connection, schema, transactions
  repositories.py    ALL SQL
  services.py        use-cases (enqueue, serve, assign)
  security.py        auth guard, CSRF, signed ticket links, headers
  domain/            pure logic: models, network (Dijkstra), schedule, analytics
  blueprints/        thin HTTP layer: main, api, auth, reports
  templates/ static/ base layout + one stylesheet + small JS modules
tests/               pytest suite (domain, API, security, import)
scripts/             import_legacy_db.py
docs/                ARCHITECTURE.md, CODEX_PROMPT.md
```

## Migrating data from the old prototype

```powershell
python -m scripts.import_legacy_db path\to\app_data.db --dry-run
python -m scripts.import_legacy_db path\to\app_data.db
```

## Production notes

Set `APP_ENV=production`, `SECRET_KEY`, and `ADMIN_PASSWORD_HASH` (the app refuses to start with defaults).
Serve behind HTTPS with a WSGI server, e.g. `waitress-serve --call app:create_app` or gunicorn.
Login throttling is in-memory (per process); use a shared store if you run multiple workers.
