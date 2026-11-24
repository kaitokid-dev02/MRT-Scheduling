import pytest

from app.domain import analytics
from app.domain.models import clean_name, lane_for, normalize_passenger_type
from app.domain.network import EDGES, STATION_LINES, RoutePlanner
from app.domain.schedule import TrainSchedule
from app.errors import RouteNotFoundError, ValidationError
from app.timeutils import resolve_timezone

# ---- passenger types -------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("regular", "REGULAR"),
        ("  Priority ", "PRIORITY"),
        ("senior citizen", "SENIOR CITIZEN"),
        ("Senior", "SENIOR CITIZEN"),
        ("pwd", "PWD"),
        (None, "REGULAR"),
    ],
)
def test_normalize_passenger_type(raw, expected):
    assert normalize_passenger_type(raw) == expected


def test_unknown_passenger_type_is_rejected():
    with pytest.raises(ValidationError):
        normalize_passenger_type("VIP")


def test_lanes():
    assert lane_for("REGULAR") == "regular"
    assert all(lane_for(t) == "priority" for t in ("PRIORITY", "SENIOR CITIZEN", "PWD", "PREGNANT"))


def test_clean_name():
    assert clean_name("  Juan   dela  Cruz ") == "Juan dela Cruz"
    for bad in ("", "   ", None, "x" * 81, "bad\x00name"):
        with pytest.raises(ValidationError):
            clean_name(bad)


# ---- network ---------------------------------------------------------------


def test_every_station_has_a_line_and_graph_is_symmetric():
    planner = RoutePlanner()
    assert set(planner.stations()) == set(STATION_LINES)
    for a, b, minutes in EDGES:
        assert planner.shortest_path(a, b).minutes <= minutes
        assert planner.shortest_path(b, a).minutes == planner.shortest_path(a, b).minutes


def test_known_shortest_path():
    route = RoutePlanner().shortest_path("North Avenue", "Guadalupe")
    assert route.path == ("North Avenue", "Quezon Avenue", "Araneta-Cubao", "Ortigas", "Boni", "Guadalupe")
    assert route.minutes == 18


def test_pasig_taguig_is_bidirectional():
    # Regression: the original graph only had Pasig -> Taguig.
    planner = RoutePlanner()
    assert planner.shortest_path("Taguig", "Pasig").minutes == 4


def test_unknown_station():
    with pytest.raises(ValidationError):
        RoutePlanner().shortest_path("North Avenue", "Atlantis")


def test_disconnected_stations_raise_route_not_found():
    planner = RoutePlanner(edges=(("A", "B", 1), ("C", "D", 1)), station_lines={})
    with pytest.raises(RouteNotFoundError):
        planner.shortest_path("A", "D")


def test_identify_line_prefers_real_lines():
    planner = RoutePlanner()
    assert planner.identify_line(("Marikina", "Pasig")) == "LRT Line 2"
    assert planner.identify_line(("Pasig",)) == "Connecting Line"
    assert planner.identify_line(()) == "Unknown"


# ---- schedule --------------------------------------------------------------


def test_schedule_arrivals_and_parsing():
    schedule = TrainSchedule()
    arrivals = schedule.next_arrivals("MRT Line 3")
    assert [a["minutes"] for a in arrivals] == [4, 8, 12]
    assert schedule.parse_train_number("MRT Line 3-2") == ("MRT Line 3", 2)
    assert schedule.next_train("LRT Line 2") == "LRT Line 2-1"
    assert schedule.next_train("Connecting Line") is None
    for bad in ("MRT Line 3-9", "Nope-1", "MRT Line 3", "", "MRT Line 3-x"):
        with pytest.raises(ValidationError):
            schedule.parse_train_number(bad)


# ---- analytics -------------------------------------------------------------

MANILA = resolve_timezone("Asia/Manila")


def _log(epoch, lane="regular", line="MRT Line 3", dest="Boni", route=("A", "B")):
    return {"timestamp_epoch": epoch, "lane": lane, "train_line": line,
            "destination": dest, "route_path": list(route)}  # fmt: skip


def test_peak_hours_uses_local_timezone():
    # 2025-01-01 00:30 UTC is 08:30 in Manila.
    base = 1735691400
    data = analytics.peak_hours([_log(base), _log(base + 60), _log(base + 7200)], MANILA)
    assert data["total_transactions"] == 3
    assert data["peak_volume"] == 2
    assert data["peak_hours"] == ["08:00 - 08:59"]
    assert [row["count"] for row in data["breakdown"]] == [2, 1]


def test_peak_hours_ties_and_empty():
    base = 1735691400
    tied = analytics.peak_hours([_log(base), _log(base + 7200)], MANILA)
    assert len(tied["peak_hours"]) == 2
    assert analytics.peak_hours([], MANILA)["total_transactions"] == 0


def test_by_train_line_counts_lanes_correctly():
    # Regression: the original compared 'Priority' to stored 'PRIORITY', so counts were always 0.
    logs = [_log(1, "priority"), _log(2, "priority"), _log(3, "regular")]
    stats = analytics.by_train_line(logs, ["MRT Line 3", "MRT Line 1"])
    assert stats["MRT Line 3"] == {"total": 3, "priority": 2, "regular": 1}
    assert stats["MRT Line 1"] == {"total": 0, "priority": 0, "regular": 0}


def test_top_destinations_and_routes():
    logs = [_log(1, dest="Boni"), _log(2, dest="Boni"), _log(3, dest="Ayala", route=("X", "Y"))]
    assert analytics.top_destinations(logs)[0] == ("Boni", 2)
    assert analytics.top_routes(logs)[0] == ("A → B", 2)
