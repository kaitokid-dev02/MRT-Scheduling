"""MRT/LRT ticketing and route assignment — application factory."""
from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from app import db, security
from app.config import CONFIGS, ProductionConfig
from app.domain.network import RoutePlanner
from app.domain.schedule import TrainSchedule
from app.errors import DomainError
from app.timeutils import format_epoch, resolve_timezone


def create_app(config: str | type | None = None, **overrides) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    if isinstance(config, type):
        app.config.from_object(config)
    else:
        env = config or os.environ.get("APP_ENV", "development")
        config_cls = CONFIGS.get(env)
        if config_cls is None:
            raise RuntimeError(f"Unknown APP_ENV {env!r}. Use one of: {', '.join(CONFIGS)}")
        if config_cls is ProductionConfig:
            ProductionConfig.validate()
        app.config.from_object(config_cls)
    app.config.update(overrides)

    if not app.config["ADMIN_PASSWORD_HASH"]:
        app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(app.config["ADMIN_PASSWORD"])

    tz = resolve_timezone(app.config["APP_TIMEZONE"])
    app.extensions["mrt"] = {"planner": RoutePlanner(), "schedule": TrainSchedule(), "tz": tz}
    app.extensions["login_attempts"] = {}

    db.init_app(app)
    security.init_app(app)

    from app.blueprints import api, auth, main, reports

    for blueprint in (main.bp, api.bp, auth.bp, reports.bp):
        app.register_blueprint(blueprint)

    @app.template_filter("local_time")
    def local_time(epoch, fmt="%Y-%m-%d %H:%M:%S"):
        return format_epoch(epoch, tz, fmt)

    _register_error_handlers(app)
    return app


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.path.startswith("/reports/clear")


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(DomainError)
    def handle_domain_error(err: DomainError):
        if _wants_json():
            return jsonify({"ok": False, "error": err.message}), err.status_code
        return render_template("error.html", code=err.status_code, message=err.message), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        if err.response is not None:
            return err.response
        if _wants_json():
            return jsonify({"ok": False, "error": err.description}), err.code
        return render_template("error.html", code=err.code, message=err.description), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        app.logger.exception("Unhandled error")
        if _wants_json():
            return jsonify({"ok": False, "error": "Internal server error."}), 500
        return render_template("error.html", code=500, message="Something went wrong."), 500
