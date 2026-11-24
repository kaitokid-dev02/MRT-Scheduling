"""Administrator login (session based) with simple brute-force throttling."""
from __future__ import annotations

import time

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.security import constant_time_equals, csrf_token, is_safe_redirect

bp = Blueprint("auth", __name__)


def _attempts() -> list[float]:
    store = current_app.extensions["login_attempts"]
    window = current_app.config["LOGIN_WINDOW_SECONDS"]
    recent = [t for t in store.get(request.remote_addr, []) if time.time() - t < window]
    store[request.remote_addr] = recent
    return recent


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.values.get("next", "")

    if request.method == "POST":
        attempts = _attempts()
        if len(attempts) >= current_app.config["LOGIN_MAX_ATTEMPTS"]:
            flash("Too many failed attempts. Try again in a few minutes.", "error")
            return render_template("login.html", next_url=next_url), 429

        cfg = current_app.config
        user_ok = constant_time_equals(request.form.get("username", ""), cfg["ADMIN_USERNAME"])
        pass_ok = check_password_hash(cfg["ADMIN_PASSWORD_HASH"], request.form.get("password", ""))
        if user_ok and pass_ok:
            current_app.extensions["login_attempts"].pop(request.remote_addr, None)
            session.clear()
            session["admin"] = True
            csrf_token()  # fresh token for the new session
            return redirect(next_url if is_safe_redirect(next_url) else url_for("reports.reports"))

        attempts.append(time.time())
        flash("Invalid username or password.", "error")
        return render_template("login.html", next_url=next_url), 401

    return render_template("login.html", next_url=next_url)


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.index"))
