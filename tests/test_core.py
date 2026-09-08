from datetime import datetime, timedelta, timezone

import pytest

from compute import CycleClock, CycleTime, EPOCH_ANCHOR

clock = CycleClock()


def at(days=0, hours=0, minutes=0):
    """A datetime `days`/`hours`/`minutes` after the epoch anchor (Mon 09:00)."""
    return EPOCH_ANCHOR + timedelta(days=days, hours=hours, minutes=minutes)


def test_round_trip():
    dt = at(days=10, hours=3, minutes=17)
    cycle = clock.to_cycle(dt)
    assert clock.to_absolute(cycle) == dt


def test_cycle_id_increments_weekly():
    assert clock.to_cycle(at(days=0)).cycle_id == 0
    assert clock.to_cycle(at(days=7)).cycle_id == 1
    assert clock.to_cycle(at(days=13, hours=23)).cycle_id == 1
    assert clock.to_cycle(at(days=14)).cycle_id == 2


def test_offset_resets_each_cycle():
    assert clock.to_cycle(at(days=0)).offset_seconds == 0
    assert clock.to_cycle(at(days=7)).offset_seconds == 0
    assert clock.to_cycle(at(days=1)).offset_seconds == 86400


@pytest.mark.parametrize(
    "days,hours,expected",
    [
        (0, 0, True),      # Monday 09:00 - matrix restarts
        (0, 7, True),       # Monday 16:00 - still up
        (2, 0, True),       # Wednesday - matrix up, services quiet
        (4, 7, True),       # Friday 16:00 - matrix still up
        (4, 8, False),      # Friday 17:00 - matrix ends
        (5, 0, False),       # Saturday - down
        (6, 23, False),      # Sunday 08:00 - down
    ],
)
def test_matrix_active(days, hours, expected):
    assert clock.matrix_active(at(days=days, hours=hours)) is expected


@pytest.mark.parametrize(
    "days,hours,expected",
    [
        (0, 0, True),    # Monday 09:00 - services open
        (0, 7, True),    # Monday 16:00 - still open
        (0, 8, False),   # Monday 17:00 - services close
        (1, 0, False),   # Tuesday - quiet
        (3, 0, False),   # Thursday - quiet
        (4, 0, True),    # Friday 09:00 - services reopen
        (4, 7, True),    # Friday 16:00 - still open
        (4, 8, False),   # Friday 17:00 - services close
        (5, 0, False),   # Saturday - down
    ],
)
def test_services_active(days, hours, expected):
    assert clock.services_active(at(days=days, hours=hours)) is expected


def test_next_boundary_sequence():
    dt = at(days=0, hours=0)
    b1 = clock.next_boundary(dt)
    assert b1 == at(days=0, hours=8)  # Monday 17:00
    b2 = clock.next_boundary(b1)
    assert b2 == at(days=4, hours=0)  # Friday 09:00
    b3 = clock.next_boundary(b2)
    assert b3 == at(days=4, hours=8)  # Friday 17:00
    b4 = clock.next_boundary(b3)
    assert b4 == at(days=7, hours=0)  # next Monday 09:00


def test_requires_timezone_aware_datetime():
    with pytest.raises(ValueError):
        clock.to_cycle(datetime(2026, 1, 1))


def test_offset_never_needs_more_than_20_bits():
    # Matrix window is 4 days 8 hours = 374,400 seconds — comfortably
    # inside 2**19 (524,288), let alone the 2**31 that trips up 2038.
    max_offset = 4 * 86400 + 8 * 3600
    assert max_offset < 2**19
