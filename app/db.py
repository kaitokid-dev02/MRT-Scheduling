"""SQLite access: connection handling, schema, and explicit transactions."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import click
from flask import Flask, current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS passengers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    type          TEXT    NOT NULL,
    lane          TEXT    NOT NULL CHECK (lane IN ('priority', 'regular')),
    status        TEXT    NOT NULL DEFAULT 'waiting'
                  CHECK (status IN ('waiting', 'serving', 'served', 'removed')),
    arrival_time  TEXT    NOT NULL,
    arrival_epoch INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_passengers_queue ON passengers (status, lane, id);

CREATE TABLE IF NOT EXISTS logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_id    INTEGER REFERENCES passengers (id),
    timestamp_iso   TEXT    NOT NULL,
    timestamp_epoch INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    type            TEXT    NOT NULL,
    lane            TEXT    NOT NULL,
    start_station   TEXT    NOT NULL,
    destination     TEXT    NOT NULL,
    fare            INTEGER NOT NULL,
    route_path      TEXT    NOT NULL,
    total_time      INTEGER NOT NULL,
    train_line      TEXT    NOT NULL,
    train_number    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_epoch ON logs (timestamp_epoch);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a connection in autocommit mode; use ``transaction()`` for atomic work."""
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE ... COMMIT, rolling back on any error.

    IMMEDIATE takes the write lock up front so two attendants can never claim
    the same passenger.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def _close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app: Flask) -> None:
    db_path = Path(app.config["DATABASE"])
    if not db_path.is_absolute() and str(db_path) != ":memory:":
        db_path = Path(app.instance_path) / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"] = str(db_path)

    conn = connect(db_path)
    try:
        init_schema(conn)
    finally:
        conn.close()

    app.teardown_appcontext(_close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create tables if they do not exist."""
        c = connect(app.config["DATABASE"])
        init_schema(c)
        c.close()
        click.echo(f"Database ready at {app.config['DATABASE']}")
