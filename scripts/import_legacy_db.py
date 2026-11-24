"""Import data from the original prototype's ``app_data.db`` into the new database.

Usage (from the project root):
    python -m scripts.import_legacy_db path/to/app_data.db [--target instance/mrt.db] [--dry-run]

* Logs keep their original timestamps (interpreted in APP_TIMEZONE).
* Waiting passengers are re-queued in their original order.
* The script is idempotent for logs: rows already imported are skipped.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from app.config import Config
from app.db import connect, init_schema
from app.domain.models import lane_for, normalize_passenger_type
from app.errors import ValidationError
from app.timeutils import resolve_timezone


def _parse_legacy_time(row: sqlite3.Row, tz) -> datetime:
    if "timestamp_epoch" in row.keys() and row["timestamp_epoch"]:
        return datetime.fromtimestamp(int(row["timestamp_epoch"]), tz)
    return datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)


def _safe_type(raw: str | None) -> str:
    try:
        return normalize_passenger_type(raw)
    except ValidationError:
        return "REGULAR"


def import_legacy(legacy_path: Path, target_path: Path, tz_name: str, dry_run: bool = False) -> dict:
    tz = resolve_timezone(tz_name)
    src = sqlite3.connect(f"file:{Path(legacy_path).as_posix()}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = connect(target_path)
    init_schema(dst)
    counts = {"logs": 0, "skipped_logs": 0, "passengers": 0}

    dst.execute("BEGIN IMMEDIATE")
    try:
        for row in src.execute("SELECT * FROM logs ORDER BY id"):
            moment = _parse_legacy_time(row, tz)
            epoch = int(moment.timestamp())
            route = [s for s in (row["route_path"] or "").split(" -> ") if s]
            exists = dst.execute(
                "SELECT 1 FROM logs WHERE timestamp_epoch = ? AND name = ? AND destination = ?",
                (epoch, row["name"], row["destination"]),
            ).fetchone()
            if exists:
                counts["skipped_logs"] += 1
                continue
            ptype = _safe_type(row["type"])
            dst.execute(
                """INSERT INTO logs (timestamp_iso, timestamp_epoch, name, type, lane, start_station,
                                     destination, fare, route_path, total_time, train_line, train_number)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    moment.isoformat(), epoch, row["name"], ptype, lane_for(ptype),
                    route[0] if route else "Unknown", row["destination"], row["fare"] or 0,
                    json.dumps(route, ensure_ascii=False), int(row["total_time"] or 0),
                    row["train_line"] or "Unknown", row["train_number"] or "N/A",
                ),
            )  # fmt: skip
            counts["logs"] += 1

        for row in src.execute("SELECT * FROM passengers ORDER BY id"):
            ptype = _safe_type(row["type"])
            try:
                when = datetime.strptime(row["arrival_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
            except (TypeError, ValueError):
                when = datetime.now(tz)
            dst.execute(
                "INSERT INTO passengers (name, type, lane, arrival_time, arrival_epoch) VALUES (?,?,?,?,?)",
                (row["name"], ptype, lane_for(ptype), when.isoformat(), int(when.timestamp())),
            )
            counts["passengers"] += 1
    except BaseException:
        dst.execute("ROLLBACK")
        raise
    else:
        dst.execute("ROLLBACK" if dry_run else "COMMIT")
    finally:
        src.close()
        dst.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("legacy_db", type=Path)
    parser.add_argument("--target", type=Path, default=Path("instance") / Config.DATABASE)
    parser.add_argument("--timezone", default=Config.APP_TIMEZONE)
    parser.add_argument("--dry-run", action="store_true", help="report counts without writing")
    args = parser.parse_args(argv)

    if not args.legacy_db.exists():
        print(f"Legacy database not found: {args.legacy_db}", file=sys.stderr)
        return 1
    args.target.parent.mkdir(parents=True, exist_ok=True)
    counts = import_legacy(args.legacy_db, args.target, args.timezone, args.dry_run)
    mode = "DRY RUN - nothing written. " if args.dry_run else ""
    print(
        f"{mode}Imported {counts['logs']} logs ({counts['skipped_logs']} already present), "
        f"{counts['passengers']} waiting passengers -> {args.target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
