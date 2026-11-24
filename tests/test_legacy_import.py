import sqlite3

from app.db import connect
from scripts.import_legacy_db import import_legacy

LEGACY_SCHEMA = """
CREATE TABLE passengers (id INTEGER PRIMARY KEY, name TEXT, type TEXT, arrival_time TEXT, queue TEXT);
CREATE TABLE logs (id INTEGER PRIMARY KEY, timestamp TEXT, timestamp_iso TEXT, timestamp_epoch INTEGER,
    time TEXT, name TEXT, type TEXT, destination TEXT, fare INTEGER, route_path TEXT, total_time INTEGER,
    train_line TEXT, train_number TEXT);
"""


def make_legacy(path):
    conn = sqlite3.connect(path)
    conn.executescript(LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO logs (timestamp, name, type, destination, fare, route_path, total_time, "
        "train_line, train_number) VALUES ('2025-12-07 08:41:49','Old Timer','PRIORITY','Guadalupe',55,"
        "'North Avenue -> Quezon Avenue -> Guadalupe',18,'MRT Line 3','MRT Line 3-1')"
    )
    conn.execute(
        "INSERT INTO passengers (name, type, arrival_time, queue) "
        "VALUES ('Waiting Wendy','Regular','2025-12-07 09:00:00','regular')"
    )
    conn.commit()
    conn.close()


def test_import_is_correct_and_idempotent(tmp_path):
    legacy, target = tmp_path / "legacy.db", tmp_path / "new.db"
    make_legacy(legacy)

    first = import_legacy(legacy, target, "Asia/Manila")
    assert first == {"logs": 1, "skipped_logs": 0, "passengers": 1}

    db = connect(target)
    log = db.execute("SELECT * FROM logs").fetchone()
    assert log["lane"] == "priority" and log["start_station"] == "North Avenue"
    assert log["timestamp_iso"].startswith("2025-12-07T08:41:49+08:00")
    assert db.execute("SELECT status FROM passengers").fetchone()["status"] == "waiting"
    db.close()

    second = import_legacy(legacy, target, "Asia/Manila")
    assert second["logs"] == 0 and second["skipped_logs"] == 1


def test_dry_run_writes_nothing(tmp_path):
    legacy, target = tmp_path / "legacy.db", tmp_path / "new.db"
    make_legacy(legacy)
    assert import_legacy(legacy, target, "Asia/Manila", dry_run=True)["logs"] == 1
    db = connect(target)
    assert db.execute("SELECT COUNT(*) FROM logs").fetchone()[0] == 0
