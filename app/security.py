"""Authentication, CSRF protection, signed ticket links and security headers."""
from __future__ import annotations

import hmac
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, abort, current_app, jsonify, redirect, request, session, url_for
from itsdangerous import BadSignature, URLSafeSerializer

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


# -- authentication --------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def is_safe_redirect(target: str | None) -> bool:
    """Only allow same-site relative paths (blocks open redirects)."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and "\\" not in target


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# -- CSRF ------------------------------------------------------------------
def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def _check_csrf() -> None:
    if not current_app.config["CSRF_ENABLED"] or request.method not in _UNSAFE_METHODS:
        return
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    expected = session.get("_csrf", "")
    if not expected or not sent or not constant_time_equals(sent, expected):
        if request.path.startswith("/api/") or request.path.startswith("/reports/"):
            response = jsonify({"ok": False, "error": "Invalid or missing CSRF token."})
            response.status_code = 403
            abort(response)
        abort(403)


# -- signed ticket links ---------------------------------------------------
def _ticket_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="ticket-link")


def make_ticket_token(log_id: int) -> str:
    return _ticket_serializer().dumps(log_id)


def read_ticket_token(token: str) -> int | None:
    try:
        value = _ticket_serializer().loads(token)
    except BadSignature:
        return None
    return value if isinstance(value, int) else None


# -- headers ---------------------------------------------------------------
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; form-action 'self'"
    ),
}


def init_app(app: Flask) -> None:
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(_check_csrf)

    @app.after_request
    def add_headers(response):
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response
