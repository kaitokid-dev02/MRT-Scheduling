"""Timezone helpers. Timestamps are stored in UTC and formatted at the edge."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

log = logging.getLogger(__name__)


def resolve_timezone(name: str) -> tzinfo:
    """Load an IANA zone, falling back to the machine's zone (never crashes).

    On Windows the ``tzdata`` package must be installed for ZoneInfo to work;
    it is listed in requirements.txt.
    """
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        log.warning("Timezone %r not found; falling back to the system timezone.", name)
        return datetime.now().astimezone().tzinfo or UTC


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_epoch(epoch: int | None, tz: tzinfo, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if epoch is None:
        return "—"
    return datetime.fromtimestamp(epoch, tz).strftime(fmt)
