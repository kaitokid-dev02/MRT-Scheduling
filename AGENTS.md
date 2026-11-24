# AGENTS.md — instructions for coding agents (Codex CLI etc.)

## Project
Flask 3 + SQLite kiosk app: priority queue, Dijkstra routing, tickets, admin reports. Python ≥ 3.11.

## Commands
- Setup: `python -m venv .venv` → activate → `pip install -r requirements-dev.txt`
- Run: `python run.py`
- Test: `pytest` (must stay green) · Lint: `ruff check .` · Coverage: `pytest --cov=app`

## Architecture rules
- Layers: `blueprints` → `services` → `repositories` → `db`; `domain/` is pure (no Flask, no SQL).
- ALL SQL lives in `app/repositories.py`, always parameterised (`?`). Never build SQL with f-strings.
- Routes stay thin: parse input, call a service, return JSON/HTML. Business rules go in services/domain.
- Raise `DomainError` subclasses (`app/errors.py`); never return ad-hoc error tuples.
- Multi-step writes use `transaction(db)`. Status changes use `PassengerRepository.transition` (compare-and-set).
- Timestamps: store UTC epoch; format with `timeutils` / the `local_time` filter.

## Security rules (do not weaken)
- Every state-changing request needs CSRF (frontend uses `window.Api`, which sends `X-CSRF-Token`).
- No inline `<script>`/`onclick`; CSP is `script-src 'self'`. Insert dynamic text with `textContent`.
- Admin-only routes use `@login_required`. Validate `next` with `is_safe_redirect`.
- Never commit `.env`, `instance/`, `*.db`, or real credentials.

## Conventions
- Add/modify behaviour → add/modify tests in the same change. Regression tests for every bug fix.
- Type hints on new functions; line length 110; keep functions small.
- Extend the network via `EDGES` + `STATION_LINES` in `app/domain/network.py` (undirected edges only);
  new passenger types via `app/domain/models.py`; new lines' frequency in `app/domain/schedule.py`.
- API contract (`/api/*` JSON with `ok` flag) is consumed by `static/js/app.js`; change both together.

## Definition of done
`pytest` green, `ruff check .` clean, docs (README/ARCHITECTURE) updated if behaviour changed,
no new dependency without a line in `docs/DECISIONS.md` explaining why.
