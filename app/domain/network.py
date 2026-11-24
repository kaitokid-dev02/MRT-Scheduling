"""Station network and shortest-path routing (Dijkstra).

The network is declared as an *undirected* edge list, so every connection is
guaranteed to be bidirectional (the original dict-of-dicts allowed one-way
typos such as Pasig -> Taguig without the reverse).
"""
from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.errors import RouteNotFoundError, ValidationError

CONNECTING_LINE = "Connecting Line"

# (station A, station B, travel minutes)
EDGES: tuple[tuple[str, str, int], ...] = (
    ("North Avenue", "Quezon Avenue", 3),
    ("North Avenue", "Trinoma", 2),
    ("Quezon Avenue", "GMA-Kamuning", 4),
    ("Quezon Avenue", "Araneta-Cubao", 3),
    ("GMA-Kamuning", "Araneta-Cubao", 3),
    ("Araneta-Cubao", "Ortigas", 6),
    ("Araneta-Cubao", "Dynasty", 4),
    ("Dynasty", "Kamuning", 2),
    ("Kamuning", "Ortigas", 3),
    ("Ortigas", "Shaw Boulevard", 5),
    ("Ortigas", "Boni", 3),
    ("Shaw Boulevard", "Boni", 4),
    ("Shaw Boulevard", "Ayala", 3),
    ("Boni", "Guadalupe", 3),
    ("Guadalupe", "Buendia", 5),
    ("Guadalupe", "Makati", 4),
    ("Buendia", "Ayala", 2),
    ("Ayala", "Makati", 2),
    ("Makati", "Taguig", 6),
    ("Taguig", "Pasay", 5),
    ("Pasay", "EDSA", 4),
    ("EDSA", "Cartimar", 3),
    ("Cartimar", "Baclaran", 2),
    ("Trinoma", "Recto", 8),
    ("Recto", "Legarda", 5),
    ("Recto", "Blumentritt", 3),
    ("Legarda", "Central Terminal", 4),
    ("Blumentritt", "Central Terminal", 3),
    ("Central Terminal", "Santa Cruz", 2),
    ("Santa Cruz", "LRT Tayuman", 3),
    ("LRT Tayuman", "Bambang", 4),
    ("Bambang", "Marikina", 5),
    ("Marikina", "Pasig", 3),
    ("Pasig", "Taguig", 4),
)

STATION_LINES: dict[str, str] = {
    "North Avenue": "MRT Line 3",
    "Quezon Avenue": "MRT Line 3",
    "GMA-Kamuning": "MRT Line 3",
    "Araneta-Cubao": "MRT Line 3",
    "Dynasty": "MRT Line 3",
    "Kamuning": "MRT Line 3",
    "Ortigas": "MRT Line 3",
    "Shaw Boulevard": "MRT Line 3",
    "Boni": "MRT Line 3",
    "Guadalupe": "MRT Line 3",
    "Buendia": "MRT Line 3",
    "Ayala": "MRT Line 3",
    "Makati": "MRT Line 3",
    "Taguig": "MRT Line 1",
    "Pasay": "MRT Line 1",
    "EDSA": "MRT Line 1",
    "Cartimar": "MRT Line 1",
    "Baclaran": "MRT Line 1",
    "Trinoma": "LRT Line 2",
    "Recto": "LRT Line 2",
    "Legarda": "LRT Line 2",
    "Blumentritt": "LRT Line 2",
    "Central Terminal": "LRT Line 2",
    "Santa Cruz": "LRT Line 2",
    "LRT Tayuman": "LRT Line 2",
    "Bambang": "LRT Line 2",
    "Marikina": "LRT Line 2",
    "Pasig": CONNECTING_LINE,
}

DEFAULT_START_STATION = "North Avenue"


@dataclass(frozen=True)
class Route:
    path: tuple[str, ...]
    minutes: int

    @property
    def path_str(self) -> str:
        return " → ".join(self.path)


class RoutePlanner:
    def __init__(
        self,
        edges: tuple[tuple[str, str, int], ...] = EDGES,
        station_lines: dict[str, str] | None = None,
    ) -> None:
        self._graph: dict[str, dict[str, int]] = defaultdict(dict)
        for a, b, minutes in edges:
            self._graph[a][b] = minutes
            self._graph[b][a] = minutes
        self._station_lines = dict(STATION_LINES if station_lines is None else station_lines)

    # -- catalogue ---------------------------------------------------------
    def stations(self) -> list[str]:
        return sorted(self._graph)

    def lines(self) -> list[str]:
        return sorted(set(self._station_lines.values()))

    def stations_on_line(self, line: str) -> list[str]:
        return sorted(s for s, ln in self._station_lines.items() if ln == line)

    def line_of(self, station: str) -> str:
        return self._station_lines.get(station, "Unknown")

    # -- routing -----------------------------------------------------------
    def identify_line(self, path: tuple[str, ...] | list[str]) -> str:
        """The real line that covers most stations on the path.

        The pseudo-line "Connecting Line" is only returned when the path
        touches no real line at all.
        """
        counts = Counter(
            self.line_of(s) for s in path if self.line_of(s) not in ("Unknown", CONNECTING_LINE)
        )
        if counts:
            return counts.most_common(1)[0][0]
        return CONNECTING_LINE if any(self.line_of(s) == CONNECTING_LINE for s in path) else "Unknown"

    def shortest_path(self, start: str, end: str) -> Route:
        """Dijkstra's algorithm. Raises ValidationError / RouteNotFoundError."""
        for station in (start, end):
            if station not in self._graph:
                raise ValidationError(f"Unknown station: {station!r}.")

        distances = {station: float("inf") for station in self._graph}
        previous: dict[str, str] = {}
        distances[start] = 0
        heap: list[tuple[int, str]] = [(0, start)]

        while heap:
            dist, station = heapq.heappop(heap)
            if station == end:
                break
            if dist > distances[station]:
                continue
            for neighbour, weight in self._graph[station].items():
                candidate = dist + weight
                if candidate < distances[neighbour]:
                    distances[neighbour] = candidate
                    previous[neighbour] = station
                    heapq.heappush(heap, (candidate, neighbour))

        if distances[end] == float("inf"):
            raise RouteNotFoundError(f"No route found between {start} and {end}.")

        path = [end]
        while path[-1] != start:
            path.append(previous[path[-1]])
        path.reverse()
        return Route(path=tuple(path), minutes=int(distances[end]))
