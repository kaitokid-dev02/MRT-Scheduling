# MRT/LRT Ticketing and Route Assignment

A Flask 3 and SQLite kiosk app for registering passengers, serving a priority-aware queue, finding routes with Dijkstra's algorithm, issuing printable tickets, and viewing admin reports.

## Requirements

- Python 3.11 or newer
- PowerShell on Windows, or a shell on macOS/Linux

## Run locally

From the project root, create a virtual environment and install the development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Start the development server:

```powershell
python run.py
```

Open <http://127.0.0.1:5000>. The development login defaults are username `admin` and password `password`; change them in `.env` for local use. Do not use the development defaults in production.

Run checks in a separate terminal while the server is stopped:

```powershell
pytest
ruff check .
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`; the remaining commands are the same.

## Publish to GitHub

Create an empty repository in the GitHub account where you want the project to live. If you want it public, choose **Public** in GitHub. Do not initialize it with a README, license, or `.gitignore`, because this project already has those files.

Then, from this project folder, replace `YOUR_USERNAME` with that account's username and run:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/mrt_web_system.git
git branch -M main
git push -u origin main
```

Git may open a browser sign-in flow. Complete it with the GitHub account that owns the new repository. Check the repository page afterward to confirm the files are visible.

The `.gitignore` excludes `.env`, `instance/`, SQLite database files, and virtual environments. Keep real credentials and local data out of GitHub, especially in a public repository.

## How it works

| Step | What happens |
| --- | --- |
| Register | Passenger joins the priority lane (Priority, Senior Citizen, PWD, Pregnant) or regular lane. |
| Serve next | Priority lane first; FIFO within each lane. The passenger becomes serving and is not deleted. |
| Assign | Choose a start and destination, preview the route, select a train, and issue a ticket. Cancel returns the passenger to their original place. |
| Report | Admin-only peak hours, busiest destinations and routes, per-line statistics, and CSV export. |

## Project layout

```text
app/
  __init__.py        Application factory and error handlers
  config.py          Environment-driven configuration
  db.py              SQLite connection, schema, and transactions
  repositories.py    SQL and data access
  services.py        Queue and assignment use cases
  security.py        Authentication, CSRF, signed ticket links, and headers
  domain/            Pure logic: models, network, schedule, and analytics
  blueprints/        Thin HTTP routes: main, API, auth, and reports
  templates/         HTML templates
  static/            CSS and JavaScript
tests/               Domain, API, security, and import tests
scripts/             Legacy database import
docs/                Architecture notes
```

## Migrate data from the old prototype

Preview the import first, then run it without `--dry-run` to apply it:

```powershell
python -m scripts.import_legacy_db path\to\app_data.db --dry-run
python -m scripts.import_legacy_db path\to\app_data.db
```

## Production notes

Set `APP_ENV=production`, a strong `SECRET_KEY`, and `ADMIN_PASSWORD_HASH`; the app refuses to start with unsafe defaults. Serve it behind HTTPS with a production WSGI server, such as Waitress or Gunicorn. Login throttling is in-memory per process, so use a shared store when running multiple workers.
