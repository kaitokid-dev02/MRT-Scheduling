"""Kiosk dashboard, printable ticket, health check."""
from __future__ import annotations

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.db import get_db
from app.domain.models import passenger_type_options
from app.errors import DomainError, NotFoundError
from app.repositories import LogRepository
from app.security import read_ticket_token
from app.services import get_service

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET", "POST"])
def index():
    ext = current_app.extensions["mrt"]
    if request.method == "POST":  # no-JavaScript fallback for registering a passenger
        try:
            passenger = get_service().enqueue(request.form.get("name"), request.form.get("p_type"))
            flash(f"{passenger['name']} added to the {passenger['lane']} queue.", "success")
        except DomainError as err:
            flash(err.message, "error")
        return redirect(url_for("main.index"))

    return render_template(
        "index.html",
        passenger_types=passenger_type_options(),
        stations=ext["planner"].stations(),
    )


@bp.route("/ticket/<token>")
def ticket(token: str):
    log_id = read_ticket_token(token)
    log = LogRepository(get_db()).get(log_id) if log_id is not None else None
    if log is None:
        raise NotFoundError("Ticket not found.")
    return render_template("ticket.html", log=log)


@bp.route("/healthz")
def healthz():
    get_db().execute("SELECT 1")
    return jsonify({"status": "ok"})
