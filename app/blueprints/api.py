"""JSON API used by the dashboard. Every response has an ``ok`` flag."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, url_for

from app.errors import ValidationError
from app.security import make_ticket_token
from app.services import get_service

bp = Blueprint("api", __name__, url_prefix="/api")


def _payload() -> dict:
    return request.get_json(silent=True) or request.form.to_dict()


def _int(data: dict, key: str) -> int:
    try:
        return int(data.get(key))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid {key}.") from None


@bp.get("/queues")
def queues():
    return jsonify({"ok": True, **get_service().queues()})


@bp.post("/enqueue")
def enqueue():
    data = _payload()
    passenger = get_service().enqueue(data.get("name"), data.get("p_type") or data.get("type"))
    return jsonify({"ok": True, "passenger": passenger, **get_service().queues()}), 201


@bp.post("/serve")
def serve():
    passenger = get_service().serve_next()
    return jsonify({"ok": True, "passenger": passenger})


@bp.post("/return")
def return_to_queue():
    passenger = get_service().return_to_queue(_int(_payload(), "id"))
    return jsonify({"ok": True, "passenger": passenger})


@bp.post("/remove")
def remove():
    removed = get_service().remove(_int(_payload(), "id"))
    return jsonify({"ok": True, "removed": removed, **get_service().queues()})


@bp.get("/route")
def route_preview():
    preview = get_service().preview_route(
        request.args.get("start", ""), request.args.get("destination", "")
    )
    return jsonify({"ok": True, **preview})


@bp.post("/assign")
def assign():
    data = _payload()
    result = get_service().assign(
        passenger_id=_int(data, "passenger_id"),
        start_station=data.get("start_station", ""),
        destination=data.get("destination", ""),
        train_number=data.get("train_number") or None,
    )
    ticket_url = url_for("main.ticket", token=make_ticket_token(result["id"]))
    return jsonify(
        {
            "ok": True,
            "log_id": result["id"],
            "route_path": result["route_path"],
            "route_path_str": result["route_path_str"],
            "total_time": result["total_time"],
            "fare": result["fare"],
            "train_line": result["train_line"],
            "train_number": result["train_number"],
            "ticket_url": ticket_url,
        }
    ), 201
