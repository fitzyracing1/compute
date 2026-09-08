"""
compute — a bounded weekly clock.

Standard Unix time counts seconds continuously since 1970 in a fixed-width
signed integer, which is what overflows on 2038-01-19. compute splits
time into two numbers instead of one running counter:

  cycle_id  Increments once per week, at Monday 09:00. Because it only
            ticks once a week, a 32-bit cycle_id doesn't run out of room
            for roughly 41 million years.

  offset    Seconds since the current cycle's matrix window opened. It
            resets to 0 every Monday 09:00, so it never accumulates
            toward an overflow point — it only ever needs to hold a few
            hundred thousand seconds (19 bits is enough).

Each week has two nested windows:

  matrix window     Mon 09:00 to Fri 17:00. The underlying compute layer
                     is up.
  services window    Mon 09:00-17:00 and Fri 09:00-17:00, nested inside
                     the matrix window. The application layer accepts
                     work. Tue-Thu the matrix stays up but services sit
                     quiet.

Outside the matrix window (Fri 17:00 to the following Mon 09:00)
everything is down — that's the reset gap between cycles.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

__all__ = ["CycleClock", "CycleTime", "EPOCH_ANCHOR"]

# First Monday after the Unix epoch, 09:00 UTC. cycle_id 0 starts here,
# so cycle_id stays legible against ordinary Unix-time intuition.
EPOCH_ANCHOR = datetime(1970, 1, 5, 9, 0, 0, tzinfo=timezone.utc)

WEEK = timedelta(days=7)
MATRIX_CLOSE = timedelta(days=4, hours=8)        # Friday 17:00
SERVICES_MORNING_CLOSE = timedelta(hours=8)      # Monday 17:00
SERVICES_FRIDAY_OPEN = timedelta(days=4)         # Friday 09:00


@dataclass(frozen=True)
class CycleTime:
    """A bounded-clock timestamp: which week, and how far into it."""

    cycle_id: int
    offset_seconds: int


class CycleClock:
    """Converts between absolute datetimes and bounded (cycle_id, offset) pairs."""

    def __init__(self, epoch_anchor: datetime = EPOCH_ANCHOR):
        if epoch_anchor.tzinfo is None:
            raise ValueError("epoch_anchor must be timezone-aware")
        self.epoch_anchor = epoch_anchor

    def _week_start(self, dt: datetime) -> datetime:
        """Most recent Monday 09:00 at or before dt."""
        weeks = (dt - self.epoch_anchor) // WEEK
        return self.epoch_anchor + weeks * WEEK

    def to_cycle(self, dt: datetime) -> CycleTime:
        """Convert an absolute datetime to (cycle_id, offset_seconds)."""
        if dt.tzinfo is None:
            raise ValueError("dt must be timezone-aware")
        week_start = self._week_start(dt)
        cycle_id = int((week_start - self.epoch_anchor) // WEEK)
        offset = int((dt - week_start).total_seconds())
        return CycleTime(cycle_id=cycle_id, offset_seconds=offset)

    def to_absolute(self, cycle: CycleTime) -> datetime:
        """Convert (cycle_id, offset_seconds) back to an absolute datetime."""
        week_start = self.epoch_anchor + cycle.cycle_id * WEEK
        return week_start + timedelta(seconds=cycle.offset_seconds)

    def matrix_active(self, dt: datetime) -> bool:
        """True if the matrix window is up (Mon 09:00 - Fri 17:00)."""
        offset = timedelta(seconds=self.to_cycle(dt).offset_seconds)
        return offset < MATRIX_CLOSE

    def services_active(self, dt: datetime) -> bool:
        """True if services are accepting work.

        Services run Mon 09:00-17:00 and Fri 09:00-17:00. Tue-Thu (and
        Monday evening) the matrix stays up but services sit quiet.
        """
        offset = timedelta(seconds=self.to_cycle(dt).offset_seconds)
        monday_window = offset < SERVICES_MORNING_CLOSE
        friday_window = SERVICES_FRIDAY_OPEN <= offset < MATRIX_CLOSE
        return monday_window or friday_window

    def next_boundary(self, dt: datetime) -> datetime:
        """The next time matrix_active or services_active would flip."""
        week_start = self._week_start(dt)
        boundaries = (
            week_start + SERVICES_MORNING_CLOSE,   # Mon 17:00 - services close
            week_start + SERVICES_FRIDAY_OPEN,     # Fri 09:00 - services reopen
            week_start + MATRIX_CLOSE,             # Fri 17:00 - matrix ends
            week_start + WEEK,                     # next Mon 09:00 - matrix restarts
        )
        for boundary in boundaries:
            if boundary > dt:
                return boundary
        return week_start + WEEK
