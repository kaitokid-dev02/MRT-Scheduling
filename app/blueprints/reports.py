"""Admin-only reports, CSV export and log maintenance."""
from __future__ import annotations

import csv
import io

from flask import Blueprint, current_app, jsonify, render_template, request

from app.db import get_db
from app.domain import analytics
from app.repositories import LogRepository
from app.security import login_required, make_ticket_token

bp = Blueprint("reports", __name__)

_CSV_COLUMNS = (
    "timestamp_iso", "name", "type", "start_station", "destination", "fare",
    "route_path", "total_time", "train_line", "train_number",
)  # fmt: skip


def _csv_safe(value: object) -> object:
    """Neutralise spreadsheet formulas in user-supplied text (CSV injection)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@bp.route("/reports")
@login_required
def reports():
    ext = current_app.extensions["mrt"]
    logs = LogRepository(get_db()).list_all()
    for log in logs:
        log["ticket_token"] = make_ticket_token(log["id"])

    return render_template(
        "reports.html",
        logs=logs,
        peak=analytics.peak_hours(logs, ext["tz"]),
        busiest_dest=analytics.top_destinations(logs),
        busiest_routes=analytics.top_routes(logs),
        line_stats=analytics.by_train_line(logs, ext["planner"].lines()),
        train_lines=ext["planner"].lines(),
        server_tz=getattr(ext["tz"], "key", None) or str(ext["tz"]),
    )


@bp.route("/reports/export")
@login_required
def export_csv():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_COLUMNS)
    for log in LogRepository(get_db()).list_all():
        row = {**log, "route_path": " -> ".join(log["route_path"])}
        writer.writerow([_csv_safe(row[col]) for col in _CSV_COLUMNS])
    return current_app.response_class(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@bp.post("/reports/clear")
@login_required
def clear_logs():
    removed = LogRepository(get_db()).clear()
    current_app.logger.warning("Admin cleared %s transaction logs from %s", removed, request.remote_addr)
    return jsonify({"ok": True, "removed": removed})
