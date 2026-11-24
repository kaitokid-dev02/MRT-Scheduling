"""Passenger types and input normalisation."""
from __future__ import annotations

import re

from app.errors import ValidationError

REGULAR = "REGULAR"
PRIORITY_TYPES = ("PRIORITY", "SENIOR CITIZEN", "PWD", "PREGNANT")
PASSENGER_TYPES = (REGULAR, *PRIORITY_TYPES)

TYPE_LABELS = {
    "REGULAR": "Regular",
    "PRIORITY": "Priority",
    "SENIOR CITIZEN": "Senior Citizen",
    "PWD": "PWD",
    "PREGNANT": "Pregnant",
}

_ALIASES = {
    "SENIOR": "SENIOR CITIZEN",
    "PREGNANT WOMAN": "PREGNANT",
    "WHEELCHAIR": "PWD",
}

NAME_MAX_LENGTH = 80
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def normalize_passenger_type(raw: object) -> str:
    """Return the canonical upper-case passenger type or raise ValidationError."""
    value = " ".join(str(raw or REGULAR).split()).upper()
    value = _ALIASES.get(value, value)
    if value not in PASSENGER_TYPES:
        allowed = ", ".join(TYPE_LABELS[t] for t in PASSENGER_TYPES)
        raise ValidationError(f"Unknown passenger type. Allowed: {allowed}.")
    return value


def lane_for(passenger_type: str) -> str:
    """Priority types go to the priority lane, everything else to regular."""
    return "regular" if passenger_type == REGULAR else "priority"


def type_label(passenger_type: str) -> str:
    return TYPE_LABELS.get(passenger_type, passenger_type.title())


def clean_name(raw: object) -> str:
    """Collapse whitespace and validate a passenger name."""
    name = " ".join(str(raw or "").split())
    if not name:
        raise ValidationError("Passenger name is required.")
    if len(name) > NAME_MAX_LENGTH:
        raise ValidationError(f"Passenger name must be {NAME_MAX_LENGTH} characters or fewer.")
    if _CONTROL_CHARS.search(name):
        raise ValidationError("Passenger name contains invalid characters.")
    return name


def passenger_type_options() -> list[dict]:
    """Shape used by templates and the frontend."""
    return [
        {"value": t, "label": TYPE_LABELS[t], "priority": lane_for(t) == "priority"}
        for t in PASSENGER_TYPES
    ]
