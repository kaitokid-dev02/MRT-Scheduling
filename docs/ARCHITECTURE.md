# Architecture

## Layers

Dependencies point downward: `blueprints` call `services`, which use `repositories` and `domain`; repositories access `db`. The `domain` package is pure Python and does not import Flask or SQL, so its logic can be tested independently.

## Queue and passenger status

The `passengers` table is the single source of truth. Passenger status moves from `waiting` to `serving` to `served`, or to `removed`. `claim_next` uses a `BEGIN IMMEDIATE` transaction so two attendants cannot claim the same passenger at once. It chooses the priority lane first, then the lowest passenger ID within that lane.

## Database and timestamps

All SQL is in `app/repositories.py` and uses parameterized queries. Multi-step writes run inside `transaction(db)`. Timestamps are stored as UTC epoch values and formatted using `APP_TIMEZONE` at the application boundary.

## Security

- `/reports` routes require an authenticated admin session.
- State-changing requests require a CSRF token in the `X-CSRF-Token` header or form field.
- Ticket URLs use signed tokens instead of enumerable database IDs.
- Content Security Policy blocks inline scripts. Frontend code inserts dynamic text with `textContent`.
- CSV exports neutralize formula injection.

## Known limits

- Strict priority can starve the regular lane.
- Kiosk endpoints are unauthenticated by design and assume a trusted terminal.
- Login throttling is per process.
- The station network is fictional demo data.
- The UI polls every five seconds instead of using push updates.

## Removed from the prototype

The legacy server-rendered `/assign_route` page and `/serve` redirect were replaced with one JSON API and modal-based flow. JSON file persistence was removed as unused code.
