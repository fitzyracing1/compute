# compute

`compute` (v0.1.0, Python ≥ 3.9, standard library only) is a bounded weekly clock offered as an alternative to continuous Unix time, for workloads that do not need it. Time is two numbers. `cycle_id` increments once per week at Monday 09:00. `offset` counts seconds since the current cycle's matrix window opened, and is at most 374,400.

Weekly windows (README):
- **matrix window**: Monday 09:00 to Friday 17:00, when the compute layer is up
- **services window**: Monday 09:00–17:00 and Friday 09:00–17:00, nested inside the matrix window
- Friday 17:00 to Monday 09:00: everything is down (the reset gap)

## Getting started

```bash
pip install -e .
pip install pytest && pytest tests/
```

```python
from datetime import datetime, timezone
from compute import CycleClock
clock = CycleClock()
now = datetime.now(timezone.utc)
cycle = clock.to_cycle(now)            # CycleTime(cycle_id, offset_seconds)
clock.matrix_active(now); clock.services_active(now); clock.next_boundary(now)
clock.to_absolute(cycle)               # round-trip
```

## Files
`compute/core.py` (`CycleTime`, `CycleClock`, `EPOCH_ANCHOR`), `tests/test_core.py`, and `docs/` (static site). There is no CI.

MIT License (the LICENSE names fitzyracing1). Copyright (c) 2026 Joshua Almeida
