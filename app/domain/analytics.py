"""Report calculations over transaction logs (pure functions)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, tzinfo


def peak_hours(logs: list[dict], tz: tzinfo) -> dict:
    """Bucket transactions by local hour and flag the busiest hour(s)."""
    hourly: dict[int, int] = defaultdict(int)
    for log in logs:
        epoch = log.get("timestamp_epoch")
        if epoch is None:
            continue
        hourly[datetime.fromtimestamp(epoch, tz).hour] += 1

    if not hourly:
        return {
            "total_transactions": 0,
            "peak_volume": 0,
            "peak_hours": [],
            "breakdown": [],
        }

    peak_volume = max(hourly.values())
    breakdown = []
    peak_labels = []
    for hour in sorted(hourly):
        label = f"{hour:02d}:00 - {hour:02d}:59"
        is_peak = hourly[hour] == peak_volume
        breakdown.append(
            {
                "time": label,
                "count": hourly[hour],
                "is_peak": is_peak,
                "percent": round(hourly[hour] / peak_volume * 100),
            }
        )
        if is_peak:
            peak_labels.append(label)

    return {
        "total_transactions": sum(hourly.values()),
        "peak_volume": peak_volume,
        "peak_hours": peak_labels,
        "breakdown": breakdown,
    }


def top_destinations(logs: list[dict], limit: int = 5) -> list[tuple[str, int]]:
    return Counter(log["destination"] for log in logs if log.get("destination")).most_common(limit)


def top_routes(logs: list[dict], limit: int = 5) -> list[tuple[str, int]]:
    routes = (" → ".join(log["route_path"]) for log in logs if log.get("route_path"))
    return Counter(routes).most_common(limit)


def by_train_line(logs: list[dict], lines: list[str]) -> dict[str, dict]:
    """Totals per line split by lane. Lines with no traffic are still listed."""
    stats = {line: {"total": 0, "priority": 0, "regular": 0} for line in lines}
    for log in logs:
        entry = stats.get(log.get("train_line"))
        if entry is None:
            continue
        entry["total"] += 1
        entry["priority" if log.get("lane") == "priority" else "regular"] += 1
    return stats
