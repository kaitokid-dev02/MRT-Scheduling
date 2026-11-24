"""All SQL lives here. Services never write queries; routes never touch SQL."""
from __future__ import annotations

import json
import sqlite3

from app.db import transaction
from app.domain.models import type_label


def _passenger(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "type_label": type_label(row["type"]),
        "lane": row["lane"],
        "status": row["status"],
        "arrival_time": row["arrival_time"],
    }


def _log(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    data["route_path"] = json.loads(data["route_path"])
    data["type_label"] = type_label(data["type"])
    return data


class PassengerRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add(self, name: str, ptype: str, lane: str, arrival_iso: str, arrival_epoch: int) -> dict:
        cur = self.db.execute(
            "INSERT INTO passengers (name, type, lane, arrival_time, arrival_epoch) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, ptype, lane, arrival_iso, arrival_epoch),
        )
        return self.get(cur.lastrowid)  # type: ignore[return-value]

    def get(self, passenger_id: int) -> dict | None:
        row = self.db.execute("SELECT * FROM passengers WHERE id = ?", (passenger_id,)).fetchone()
        return _passenger(row)

    def list_waiting(self, lane: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM passengers WHERE status = 'waiting' AND lane = ? ORDER BY id", (lane,)
        ).fetchall()
        return [_passenger(r) for r in rows]  # type: ignore[misc]

    def list_serving(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM passengers WHERE status = 'serving' ORDER BY id"
        ).fetchall()
        return [_passenger(r) for r in rows]  # type: ignore[misc]

    _NEXT_SQL = (
        "SELECT * FROM passengers WHERE status = 'waiting' "
        "ORDER BY (lane = 'priority') DESC, id ASC LIMIT 1"
    )

    def peek_next(self) -> dict | None:
        return _passenger(self.db.execute(self._NEXT_SQL).fetchone())

    def claim_next(self) -> dict | None:
        """Atomically move the next waiting passenger to ``serving``."""
        with transaction(self.db):
            row = self.db.execute(self._NEXT_SQL).fetchone()
            if row is None:
                return None
            self.db.execute("UPDATE passengers SET status = 'serving' WHERE id = ?", (row["id"],))
        return self.get(row["id"])

    def transition(self, passenger_id: int, from_status: str, to_status: str) -> bool:
        """Compare-and-set status change. Returns False if the state didn't match."""
        cur = self.db.execute(
            "UPDATE passengers SET status = ? WHERE id = ? AND status = ?",
            (to_status, passenger_id, from_status),
        )
        return cur.rowcount == 1


class LogRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add(self, entry: dict) -> int:
        cur = self.db.execute(
            """INSERT INTO logs (passenger_id, timestamp_iso, timestamp_epoch, name, type, lane,
                                 start_station, destination, fare, route_path, total_time,
                                 train_line, train_number)
               VALUES (:passenger_id, :timestamp_iso, :timestamp_epoch, :name, :type, :lane,
                       :start_station, :destination, :fare, :route_path, :total_time,
                       :train_line, :train_number)""",
            {**entry, "route_path": json.dumps(entry["route_path"], ensure_ascii=False)},
        )
        return cur.lastrowid  # type: ignore[return-value]

    def get(self, log_id: int) -> dict | None:
        return _log(self.db.execute("SELECT * FROM logs WHERE id = ?", (log_id,)).fetchone())

    def list_all(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM logs ORDER BY timestamp_epoch DESC, id DESC").fetchall()
        return [_log(r) for r in rows]  # type: ignore[misc]

    def clear(self) -> int:
        return self.db.execute("DELETE FROM logs").rowcount
