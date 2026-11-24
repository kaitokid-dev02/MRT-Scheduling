# Architecture

**Layering (dependencies point downward only):**
`blueprints` → `services` → `repositories` → `db`, and `services` → `domain`.
`domain` imports nothing from Flask or SQL, so it is trivially unit-testable.

**Queue model.** One `passengers` table is the single source of truth (the prototype kept a second
in-memory copy that could drift). Status: `waiting → serving → served` (or `removed`).
`claim_next` runs in a `BEGIN IMMEDIATE` transaction so two attendants never get the same passenger.
Next passenger = priority lane first, then lowest id.

**Timestamps** are stored as UTC epoch + ISO string and formatted in `APP_TIMEZONE` at the edge.

**Security.** Session login for `/reports*`; CSRF token on every POST (header `X-CSRF-Token` or
form field); ticket URLs are signed tokens (no enumerable ids); CSP forbids inline scripts, so the
frontend uses `textContent` and JSON boot data; CSV export neutralises formula injection.

**Known limits / roadmap.** Strict priority can starve the regular lane; kiosk endpoints are
unauthenticated by design (single trusted terminal); login throttle is per-process; the station
network is fictional demo data; polling (5 s) rather than push updates.

**Deliberate removals vs. prototype.** The legacy server-rendered `/assign_route` page and `/serve`
redirect were dropped in favour of one flow (JSON API + modal); JSON file persistence was dead code.
