# Prompt for Codex CLI

Run from the project root (where `AGENTS.md` lives) and paste everything in the block below:

```
You are working in an existing Flask 3 + SQLite project (MRT/LRT kiosk: priority queue,
Dijkstra routing, tickets, admin reports). Read AGENTS.md and docs/ARCHITECTURE.md first and
follow them strictly. Do not rewrite the architecture; extend it.

PHASE 0 - BASELINE (do first)
1. Create/activate a venv, `pip install -r requirements-dev.txt`.
2. Run `pytest` and `ruff check .`. Fix any lint findings without changing behaviour.
   All tests must pass before you continue. Report the baseline result.

PHASE 1 - ROLES & USERS
- Replace the single env-based admin with a `users` table (id, username, password_hash, role in
  {attendant, admin}, active). Add `flask create-user` CLI. Keep the env admin only as a
  first-run bootstrap.
- Kiosk endpoints (/api/*, /) require role attendant or admin; /reports* and log clearing
  require admin. Keep CSRF, throttling and safe-redirect behaviour.
- Add an audit_log table (who, action, timestamp) for serve, assign, remove, clear-logs.

PHASE 2 - FAIRNESS & MULTI-COUNTER
- Add config PRIORITY_RATIO (default 3): after N consecutive priority passengers, serve one
  waiting regular passenger. Implement in PassengerRepository/service, keep it deterministic.
- Add counters (windows): a serving passenger records counter_id; the UI shows which counter
  serves whom. Migrations must be additive and idempotent (no data loss on existing DBs).

PHASE 3 - REAL-TIME & UX
- Replace the 5 s polling in static/js/app.js with Server-Sent Events (/api/stream) and
  fall back to polling if SSE fails. No new JS framework.
- Accessibility pass: keyboard focus trap in the assign modal, aria-live updates, colour
  contrast >= WCAG AA. Add a Filipino (fil) translation layer via a small JSON dictionary.

PHASE 4 - TICKETS
- Add a QR code on the ticket (add `qrcode` dependency) encoding the signed ticket URL, and a
  /api/tickets/<token>/validate endpoint that marks a ticket as used once (409 if reused).

PHASE 5 - DEPLOYMENT & QUALITY
- Add Dockerfile (non-root, waitress/gunicorn), docker-compose.yml with a volume for instance/,
  and a /healthz-based healthcheck.
- Raise coverage to >= 90% (`pytest --cov=app`). Add tests for every new behaviour plus
  regression tests for edge cases (concurrent claim_next, double assign, expired sessions).
- Update README.md and docs/ARCHITECTURE.md.

RULES
- Work phase by phase. After each phase: run pytest + ruff, fix failures, then commit with a
  clear message (e.g. "phase 2: priority ratio and counters"). Never leave tests failing.
- Keep the /api JSON contract backwards compatible unless a phase says otherwise; if you change
  it, update static/js/app.js and tests in the same commit.
- Do not weaken security (CSRF, CSP, parameterised SQL, textContent). No inline scripts.
- No new dependency unless required; record each in docs/DECISIONS.md with a one-line reason.
- If a requirement is ambiguous, choose the simplest option, note it in docs/DECISIONS.md, and
  continue rather than stopping to ask.
- Never touch .env, instance/, or *.db files.

FINISH with a summary: what changed per phase, test/coverage numbers, decisions made, and
anything left undone.
```

Tips: start with `codex` in the repo root and paste the block; to go slower, paste one PHASE at
a time. Review `git diff` between phases.
