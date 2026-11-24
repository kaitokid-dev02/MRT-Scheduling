"""Train frequencies and next-arrival calculations."""
from __future__ import annotations

from app.errors import ValidationError

DEFAULT_FREQUENCY_MINUTES = {
    "MRT Line 1": 5,
    "MRT Line 3": 4,
    "LRT Line 2": 6,
}


class TrainSchedule:
    """Fixed-headway schedule: train N on a line arrives in N * frequency minutes."""

    def __init__(self, frequency: dict[str, int] | None = None, trains_shown: int = 3) -> None:
        self.frequency = dict(DEFAULT_FREQUENCY_MINUTES if frequency is None else frequency)
        self.trains_shown = trains_shown

    def lines(self) -> list[str]:
        return sorted(self.frequency)

    def has_line(self, line: str) -> bool:
        return line in self.frequency

    def next_arrivals(self, line: str, count: int | None = None) -> list[dict]:
        if line not in self.frequency:
            return []
        headway = self.frequency[line]
        return [
            {
                "train_number": f"{line}-{i}",
                "line": line,
                "minutes": headway * i,
                "display": f"{headway * i} min",
            }
            for i in range(1, (count or self.trains_shown) + 1)
        ]

    def parse_train_number(self, value: str) -> tuple[str, int]:
        """Validate ``"<line>-<n>"`` and return ``(line, n)``."""
        line, _, index = str(value or "").rpartition("-")
        if line not in self.frequency or not index.isdigit():
            raise ValidationError(f"Unknown train: {value!r}.")
        n = int(index)
        if not 1 <= n <= self.trains_shown:
            raise ValidationError(f"Unknown train: {value!r}.")
        return line, n

    def next_train(self, line: str) -> str | None:
        arrivals = self.next_arrivals(line, count=1)
        return arrivals[0]["train_number"] if arrivals else None
