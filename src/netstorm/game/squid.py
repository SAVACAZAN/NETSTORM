"""
NetStorm Game Entity (Squid) system.
Matches the 36-byte structure of the original engine for bit-perfect parity.

Confirmed offsets via RE of netstorm.exe (Ghidra / Squid.cpp):
  +0x00  vtable ptr          (4 bytes)
  +0x04  next_sid            (ushort) free-list getNext(); overwritten at allocation
  +0x06  ?                   (2 bytes) zeroed on alloc, type-ctor may fill
  +0x08  ?                   (2 bytes) zeroed on alloc, type-ctor may fill
  +0x0A  type_id             (byte)   squid type index into type table
  +0x0B  flags               (byte)   bit0=isFree, bit1=?, bit2=isVoid, bit3=isContained
  +0x0C  neighbor_flags      (ushort)
  +0x0E  pos_x               (float32)
  +0x12  pos_y               (float32)
  +0x16  grid_x              (short, truncated from pos_x)
  +0x18  grid_y              (short, truncated from pos_y)
  +0x1A  ?                   (5 bytes)
  +0x1F  state               (byte)   0=dead/void, 1=weak, 2=medium, 3=strong (weather power)
  +0x20  owner               (byte)   player index 0-3
  +0x21  power_key           (signed byte) used as targeting sort key (lower = weaker)
  +0x22  direction           (byte)   sprite variant / rotation index
  +0x23  flags2              (byte)   bit3=?, bit7=init_done
"""

from __future__ import annotations
import struct
import numpy as np
from dataclasses import dataclass


# sizeof(Squid) = 36 bytes (stride confirmed: 0x24)
SQUID_STRIDE = 36
MAX_SQUIDS = 32000

# Field byte offsets (all confirmed via RE)
_NEXT_OFF = 0x04   # ushort — free-list next SID
_TYPE_OFF = 0x0A   # byte   — type index
_FLAG_OFF = 0x0B   # byte   — isFree=bit0, isVoid=bit2, isContained=bit3
_NFLG_OFF = 0x0C   # ushort — neighbor flags
_POSX_OFF = 0x0E   # float32
_POSY_OFF = 0x12   # float32
_GRDX_OFF = 0x16   # int16  — int(pos_x)
_GRDY_OFF = 0x18   # int16  — int(pos_y)
_STAT_OFF = 0x1F   # byte   — 0=dead, 1-3=power state
_OWNR_OFF = 0x20   # byte   — player 0-3
_PWRK_OFF = 0x21   # signed byte — targeting power key
_DIRN_OFF = 0x22   # byte   — sprite direction/variant
_FLG2_OFF = 0x23   # byte   — flags2


class GameState:
    """Manages the global state of all entities (Squids)."""

    def __init__(self) -> None:
        self.data = np.zeros(MAX_SQUIDS * SQUID_STRIDE, dtype=np.uint8)
        self.is_initialized = False

    def get_squid_data(self, index: int) -> np.ndarray:
        """Returns a view of the 36 bytes for a specific squid."""
        start = index * SQUID_STRIDE
        return self.data[start : start + SQUID_STRIDE]

    # --- Free-list / allocation ---

    def is_free(self, index: int) -> bool:
        """bit0 of +0x0B — slot is in the free list."""
        return bool(self.get_squid_data(index)[_FLAG_OFF] & 1)

    def set_free(self, index: int, free: bool) -> None:
        view = self.get_squid_data(index)
        if free:
            view[_FLAG_OFF] |= np.uint8(1)
        else:
            view[_FLAG_OFF] &= np.uint8(0xFE)

    def is_void(self, index: int) -> bool:
        """bit2 of +0x0B — slot has no type assigned."""
        return bool(self.get_squid_data(index)[_FLAG_OFF] & 4)

    def get_next_sid(self, index: int) -> int:
        """+0x04: getNext() — next SID in the free list."""
        view = self.get_squid_data(index)
        return int(view[_NEXT_OFF]) | (int(view[_NEXT_OFF + 1]) << 8)

    def get_id(self, index: int) -> int:
        """Alias for get_next_sid — +0x04 is the free-list next field."""
        return self.get_next_sid(index)

    def set_id(self, index: int, value: int) -> None:
        view = self.get_squid_data(index)
        view[_NEXT_OFF] = value & 0xFF
        view[_NEXT_OFF + 1] = (value >> 8) & 0xFF

    # --- Type ---

    def get_type_id(self, index: int) -> int:
        """+0x0A: squid type index."""
        return int(self.get_squid_data(index)[_TYPE_OFF])

    def set_type_id(self, index: int, value: int) -> None:
        self.get_squid_data(index)[_TYPE_OFF] = np.uint8(value)

    # --- Position ---

    def get_pos(self, index: int) -> tuple[np.float32, np.float32]:
        """+0x0E/+0x12: (pos_x, pos_y) as float32."""
        view = self.get_squid_data(index)
        x = np.frombuffer(view[_POSX_OFF:_POSX_OFF + 4], dtype=np.float32)[0]
        y = np.frombuffer(view[_POSY_OFF:_POSY_OFF + 4], dtype=np.float32)[0]
        return x, y

    def set_pos(self, index: int, x: float, y: float) -> None:
        view = self.get_squid_data(index)
        np.frombuffer(view[_POSX_OFF:_POSX_OFF + 4], dtype=np.float32)[:] = np.float32(x)
        np.frombuffer(view[_POSY_OFF:_POSY_OFF + 4], dtype=np.float32)[:] = np.float32(y)
        view[_GRDX_OFF:_GRDX_OFF + 2] = np.frombuffer(
            np.array([int(x)], dtype=np.int16).tobytes(), dtype=np.uint8
        )
        view[_GRDY_OFF:_GRDY_OFF + 2] = np.frombuffer(
            np.array([int(y)], dtype=np.int16).tobytes(), dtype=np.uint8
        )

    # --- State (health/power) ---

    def get_state(self, index: int) -> int:
        """
        +0x1F: power state — 0=dead/void, 1=weak (<=2.0), 2=medium (<=4.0), 3=strong (>4.0).
        This is the 'health' equivalent in NetStorm (weather power, not HP).
        """
        return int(self.get_squid_data(index)[_STAT_OFF])

    def set_state(self, index: int, value: int) -> None:
        self.get_squid_data(index)[_STAT_OFF] = np.uint8(value & 0x03)

    # --- Owner ---

    def get_owner(self, index: int) -> int:
        """+0x20: owner — player index 0-3."""
        return int(self.get_squid_data(index)[_OWNR_OFF])

    def set_owner(self, index: int, value: int) -> None:
        self.get_squid_data(index)[_OWNR_OFF] = np.uint8(value)

    # --- Direction ---

    def get_direction(self, index: int) -> int:
        """+0x22: sprite direction/variant index."""
        return int(self.get_squid_data(index)[_DIRN_OFF])

    def set_direction(self, index: int, value: int) -> None:
        self.get_squid_data(index)[_DIRN_OFF] = np.uint8(value)

    # --- Hash ---

    def compute_hash(self) -> int:
        """FNV-1a hash of the entire squid array — matches netstorm_hook.c.

        Uses Python int arithmetic (not numpy scalars) to guarantee uint32 wrap.
        numpy uint32 * uint32 silently promotes to uint64, giving a wrong hash.
        """
        h = 2166136261  # FNV-1a offset basis (uint32)
        for w in self.data.view(np.uint32):
            h = ((h ^ int(w)) * 16777619) & 0xFFFFFFFF
        return h


@dataclass
class Squid:
    """Python-friendly wrapper for a single Squid entity."""
    index: int
    state: GameState

    @property
    def id(self) -> int:
        return self.state.get_id(self.index)

    @id.setter
    def id(self, value: int) -> None:
        self.state.set_id(self.index, value)

    @property
    def type_id(self) -> int:
        return self.state.get_type_id(self.index)

    @property
    def pos(self) -> tuple[np.float32, np.float32]:
        return self.state.get_pos(self.index)

    @property
    def power_state(self) -> int:
        return self.state.get_state(self.index)

    @property
    def owner(self) -> int:
        return self.state.get_owner(self.index)

    @property
    def is_free(self) -> bool:
        return self.state.is_free(self.index)

    @property
    def is_void(self) -> bool:
        return self.state.is_void(self.index)
