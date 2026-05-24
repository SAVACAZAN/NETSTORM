"""
Game timing — confirmed via RE of WinMain (FUN_00485b20).

There is NO separate simulation tick rate. The main loop runs:
  FUN_004012d0()        frame timer / fps / frame-counter increment
  <6 other per-frame calls>
  if (0.2 < elapsed):   FUN_004bfee0() at ~5 Hz  (sound/display update)
  FUN_0041ae80()        game state machine
  if state == ok:       ~20 simulation update functions — every frame, no gating

Observed render rate from session recordings: ~71 fps.
Simulation is frame-rate-dependent; the Python reimplementation targets the
same observed rate in free-running mode.  In replay mode, GameTimer is not
used — the driver steps one frame per recorded entry.
"""

from __future__ import annotations
import time

RENDER_RATE_HZ: float = 71.0           # confirmed from session01.nsrec (1070 frames/15s)
FRAME_MS: float = 1000.0 / RENDER_RATE_HZ

SLOW_UPDATE_RATE_HZ: float = 5.0       # FUN_004bfee0 gating: 0.2s interval in WinMain


class GameTimer:
    """Tracks elapsed frames. Targets RENDER_RATE_HZ in free-running mode."""

    def __init__(self) -> None:
        self._origin_ns: int = time.perf_counter_ns()
        self._frame_count: int = 0
        self._last_frame_ns: int = self._origin_ns

    @property
    def frame(self) -> int:
        return self._frame_count

    def elapsed_ms(self) -> float:
        return (time.perf_counter_ns() - self._origin_ns) / 1_000_000.0

    def should_tick(self) -> bool:
        """Return True when a frame interval has elapsed; advance internal counter."""
        now = time.perf_counter_ns()
        elapsed_ms = (now - self._last_frame_ns) / 1_000_000.0
        if elapsed_ms >= FRAME_MS:
            self._last_frame_ns += int(FRAME_MS * 1_000_000)
            self._frame_count += 1
            return True
        return False

    def reset(self) -> None:
        now = time.perf_counter_ns()
        self._origin_ns = now
        self._last_frame_ns = now
        self._frame_count = 0
