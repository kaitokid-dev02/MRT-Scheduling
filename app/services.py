"""Use-cases that coordinate domain rules and repositories."""
from __future__ import annotations

import sqlite3
from datetime import tzinfo

from flask import current_app

from app.db import get_db, transaction
from app.domain.models import clean_name, lane_for, normalize_passenger_type
from app.domain.network import DEFAULT_START_STATION, RoutePlanner
from app.domain.schedule import TrainSchedule
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories import LogRepository, PassengerRepository
from app.timeutils import utc_now


class TicketingService:
    def __init__(
        self,
        db: sqlite3.Connection,
        planner: RoutePlanner,
        schedule: TrainSchedule,
        fare: int,
        tz: tzinfo,
    ) -> None:
        self.passengers = PassengerRepository(db)
        self.logs = LogRepository(db)
        self.db = db
        self.planner = planner
        self.schedule = schedule
        self.fare = fare
        self.tz = tz

    # -- queue -------------------------------------------------------------
    def enqueue(self, name: object, passenger_type: object) -> dict:
        ptype = normalize_passenger_type(passenger_type)
        now = utc_now()
        return self.passengers.add(
            clean_name(name), ptype, lane_for(ptype), now.isoformat(), int(now.timestamp())
        )

    def queues(self) -> dict:
        return {
            "priority_q": self.passengers.list_waiting("priority"),
            "regular_q": self.passengers.list_waiting("regular"),
            "serving": self.passengers.list_serving(),
            "next": self.passengers.peek_next(),
        }

    def serve_next(self) -> dict:
        passenger = self.passengers.claim_next()
        if passenger is None:
            raise NotFoundError("No passenger to serve.")
        return passenger

    def return_to_queue(self, passenger_id: int) -> dict:
        """Undo a serve (attendant cancelled). The passenger keeps their original place."""
        if not self.passengers.transition(passenger_id, "serving", "waiting"):
            raise ConflictError("Passenger is not currently being served.")
        return self.passengers.get(passenger_id)  # type: ignore[return-value]

    def remove(self, passenger_id: int) -> dict:
        passenger = self.passengers.get(passenger_id)
        if passenger is None:
            raise NotFoundError("Passenger not found.")
        if not self.passengers.transition(passenger_id, "waiting", "removed"):
            raise ConflictError("Only waiting passengers can be removed.")
        return passenger

    # -- routing & tickets -------------------------------------------------
    def preview_route(self, start: str, destination: str) -> dict:
        start = start or DEFAULT_START_STATION
        route = self._route(start, destination)
        line = self.planner.identify_line(route.path)
        return {
            "route_path": list(route.path),
            "route_path_str": route.path_str,
            "total_time": route.minutes,
            "train_line": line,
            "fare": self.fare,
            "trains": self.schedule.next_arrivals(line),
        }

    def assign(
        self,
        passenger_id: int,
        start_station: str,
        destination: str,
        train_number: str | None = None,
    ) -> dict:
        passenger = self.passengers.get(passenger_id)
        if passenger is None:
            raise NotFoundError("Passenger not found.")
        if passenger["status"] != "serving":
            raise ConflictError("Passenger is not currently being served.")

        start_station = start_station or DEFAULT_START_STATION
        route = self._route(start_station, destination)
        line = self.planner.identify_line(route.path)

        if train_number:
            self.schedule.parse_train_number(train_number)
        else:
            train_number = self.schedule.next_train(line) or "N/A"

        now = utc_now()
        entry = {
            "passenger_id": passenger["id"],
            "timestamp_iso": now.astimezone(self.tz).isoformat(),
            "timestamp_epoch": int(now.timestamp()),
            "name": passenger["name"],
            "type": passenger["type"],
            "lane": passenger["lane"],
            "start_station": start_station,
            "destination": destination,
            "fare": self.fare,
            "route_path": list(route.path),
            "total_time": route.minutes,
            "train_line": line,
            "train_number": train_number,
        }
        with transaction(self.db):
            log_id = self.logs.add(entry)
            if not self.passengers.transition(passenger_id, "serving", "served"):
                raise ConflictError("Passenger is not currently being served.")
        return {**entry, "id": log_id, "route_path_str": route.path_str}

    def _route(self, start: str, destination: str):
        if not destination:
            raise ValidationError("Destination is required.")
        if start == destination:
            raise ValidationError("Start and destination must be different stations.")
        return self.planner.shortest_path(start, destination)


def get_service() -> TicketingService:
    ext = current_app.extensions["mrt"]
    return TicketingService(
        get_db(),
        ext["planner"],
        ext["schedule"],
        current_app.config["FLAT_FARE"],
        ext["tz"],
    )
