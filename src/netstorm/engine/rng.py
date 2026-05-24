"""
NetStorm RNG reverse-engineered implementation.

The original almost certainly uses MSVC CRT rand():
    state = state * 214013 + 2531011
    return (state >> 16) & 0x7FFF

TBD: confirm via Ghidra — look for constants 0x343FD (214013) and 0x269EC3 (2531011)
in netstorm.exe. If a different multiplier appears, update _MULT / _ADD below.
"""

from __future__ import annotations
import ctypes

_MULT = 214013      # 0x343FD  — MSVC rand() multiplier
_ADD  = 2531011     # 0x269EC3 — MSVC rand() addend
_MASK = 0xFFFFFFFF  # keep 32-bit unsigned

RAND_MAX = 0x7FFF


class RNG:
    """Deterministic LCG matching MSVC rand(). All state kept as uint32."""

    __slots__ = ("_state",)

    def __init__(self, seed: int = 1) -> None:
        self._state = seed & _MASK

    @property
    def state(self) -> int:
        return self._state

    def seed(self, value: int) -> None:
        self._state = value & _MASK

    def rand(self) -> int:
        """Return next value in [0, RAND_MAX] and advance state."""
        self._state = (self._state * _MULT + _ADD) & _MASK
        return (self._state >> 16) & RAND_MAX

    def rand_range(self, lo: int, hi: int) -> int:
        """Return integer in [lo, hi] inclusive."""
        span = hi - lo + 1
        return lo + (self.rand() % span)

    def snapshot(self) -> int:
        """Return raw state for differential testing."""
        return self._state

    def restore(self, state: int) -> None:
        self._state = state & _MASK

    def advance(self, n: int) -> None:
        """Skip n steps without collecting values (O(n) — acceptable for small n)."""
        for _ in range(n):
            self.rand()
