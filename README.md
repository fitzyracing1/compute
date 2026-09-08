# cycleclock

A bounded weekly clock, built as an alternate to continuous Unix time for
operations that don't need it.

## The problem it sidesteps

Unix time counts seconds continuously since 1970 in a fixed-width signed
32-bit integer. That counter runs out of room on 2038-01-19 — the classic
Year 2038 problem. Any system still relying on a 32-bit `time_t` has to
either widen the integer or stop counting continuously.

`cycleclock` takes the second path, deliberately, for workloads that never
needed continuous wall-clock time in the first place.

## How it works

Time is split into two numbers instead of one running counter:

- **`cycle_id`** — increments once per week, every Monday 09:00. Ticking
  once a week instead of once a second means a 32-bit `cycle_id` doesn't
  run out of room for roughly **41 million years**.
- **`offset`** — seconds since the current cycle's matrix window opened.
  It resets to `0` every Monday 09:00, so it never accumulates toward an
  overflow point. The matrix window is at most 374,400 seconds long —
  under 2^19 — nowhere near where a 32-bit counter would even start to
  worry.

Each week has two nested windows:

```
        Mon              Tue   Wed   Thu              Fri
      09:00 17:00                                 09:00 17:00
        |-----|            .     .     .            |-----|
matrix: |=====|============================================|
services|=====|            quiet (matrix stays up)   |=====|
        |                                                   |
      restart                                             ends,
                                                          resets
```

- **matrix window** — Monday 09:00 to Friday 17:00. The underlying
  compute layer is up.
- **services window** — Monday 09:00–17:00 and Friday 09:00–17:00,
  nested inside the matrix window. The application layer accepts work.
  Tuesday through Thursday (and Monday evening) the matrix stays up but
  services sit quiet.

Outside the matrix window — Friday 17:00 to the following Monday 09:00 —
everything is down. That's the reset gap between cycles.

## Usage

```python
from datetime import datetime, timezone
from cycleclock import CycleClock

clock = CycleClock()
now = datetime.now(timezone.utc)

cycle = clock.to_cycle(now)
print(cycle.cycle_id, cycle.offset_seconds)

clock.matrix_active(now)      # is the compute layer up?
clock.services_active(now)    # is the application layer taking work?
clock.next_boundary(now)      # when does that next flip?

# round-trip back to an absolute datetime
clock.to_absolute(cycle) == now
```

## Who it suits

- Batch or scheduled compute that only cares how far into the current
  work window it is, not the absolute date.
- Edge or embedded devices that don't need wall-clock accuracy — just a
  bounded, self-resetting operational cycle.
- Systems where downtime is already scheduled, so the "off" period
  (the weekend gap) costs nothing extra.

## Interop

Anything that needs to talk to the outside world in real dates —
logs, cross-system timestamps — goes through one translation function:

```
absolute_time = epoch_anchor + cycle_id * WEEK + offset_seconds
```

That translation layer can use arbitrary-precision integers, so it's
never the thing that overflows; only the operational counters inside a
`cycleclock`-based system stay bounded.

## Status

Early — the core clock and window logic are implemented and tested.
Not yet packaged for PyPI.

## License

MIT
