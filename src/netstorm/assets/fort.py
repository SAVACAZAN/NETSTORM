"""
NetStorm .fort map decoder.

Format updated via RE session 9 (hex analysis of MyOnlineGame.fort + Ghidra
decompile of FUN_0044c9f0 - the DataManager record serializer).

File layout (1070 bytes for the sample):

  Header (66 bytes, 0x00..0x41):
    0x00  uint16  magic/version   = 0x0046 in sample
    0x02  uint16  unknown1        = 0x000F (15) in sample
    0x04  uint32  seed_or_ts      = 0x0006952C in sample
    0x08  uint8   name_len        = length of player name (7 = "Unnamed")
    0x09  uint8   _pad            = 0
    0x0A  bytes   player_name     = name_len bytes (no terminator)
    0x0A+name_len .. 0x42         = remainder of header (varies, NOT yet
                                    fully reverse-engineered)

  Tile grid (0x42..0x342, 768 bytes):
    256 tiles (16x16), each tile 3 bytes (type_id, flags, extra).
    type_id 0x63 (99) = water/void.

    NOTE: previous version of this parser placed the grid at 0x3E. That
    was off by 4 bytes - the actual grid starts at 0x42. The 4 bytes at
    0x3E..0x41 (`AD 03 03 02` in the sample) are part of the trailing
    header section, not tile data.

  Section list (0x342 .. EOF):
    A sequence of length-prefixed records. The original game serializes
    its fort via FUN_0044c9f0 which writes, per registered DataManager
    field:

        uint16 size      // total record size, INCLUDING this 2-byte word
        bytes  body      // size - 2 bytes of payload

    Records continue until the buffer is exhausted (the file ends right
    after the last record). Empty records (size == 2, no body) appear as
    section terminators / unset fields.

    The MEANING of each record (which field it represents) is not
    self-describing in the file - the order is implicit and depends on
    the DataManager registration order at runtime. The parser exposes the
    raw record list; mapping records to game fields needs further RE.

    For MyOnlineGame.fort (entity_count placeholder = 3 in the original
    notes, actually meaning "3 entity-data records of body size > 10"):

        Record 0  @0x342 size=3  body=[00]              // counter / flag
        Record 1  @0x345 size=122 body[120]              // entity #1 (large)
        Record 2  @0x3BF size=2  body=[]                 // empty / terminator
        ...
        Record 4  @0x3C3 size=12  body[10]               // bridge link table?
        Record 5  @0x3CF size=6   body[4]
        Record 6  @0x3D5 size=3   body=[00]
        Record 10 @0x3DE size=23  body[21]               // entity #2 (medium)
        Records 11..29 size=3 body=[02]                  // 19 island flags
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from typing import List
import numpy as np


TILE_DATA_OFFSET = 0x42   # corrected: first tile byte (was 0x3E - off by 4)
TILE_STRIDE      = 3      # bytes per tile (type_id, flags, extra)
GRID_SIZE        = 16     # 16x16 tile grid confirmed
TILE_COUNT       = GRID_SIZE * GRID_SIZE   # 256

SECTION_OFFSET   = TILE_DATA_OFFSET + TILE_COUNT * TILE_STRIDE  # 0x342

TILE_WATER = 0x63  # type_id for water/void (99 decimal)


class FortTile:
    __slots__ = ("type_id", "flags", "extra")

    def __init__(self, type_id: int, flags: int, extra: int) -> None:
        self.type_id = type_id
        self.flags   = flags
        self.extra   = extra

    def is_empty(self) -> bool:
        return self.type_id == TILE_WATER

    def __repr__(self) -> str:
        return f"FortTile(type={self.type_id}, flags={self.flags}, extra={self.extra})"


@dataclass
class FortRecord:
    """One length-prefixed record from the post-grid section list.

    Format per RE of FUN_0044c9f0:
        uint16 size  // includes the 2-byte size header
        bytes  body  // size - 2 bytes
    """
    offset: int           # absolute file offset of the record's size field
    size:   int           # value of the size field (>=2)
    body:   bytes         # size - 2 raw bytes

    @property
    def is_empty(self) -> bool:
        return self.size == 2

    def __repr__(self) -> str:
        return (
            f"FortRecord(off={self.offset:#x}, size={self.size}, "
            f"body[{len(self.body)}]={self.body[:16].hex(' ')}"
            f"{'...' if len(self.body) > 16 else ''})"
        )


class FortFile:
    def __init__(self, data: bytes) -> None:
        self.data = data

        if len(data) < SECTION_OFFSET:
            raise ValueError(
                f".fort file too short: {len(data)} bytes "
                f"(need at least {SECTION_OFFSET} for header + grid)"
            )

        # --- Header ---
        self.magic    = struct.unpack_from("<H", data, 0x00)[0]  # 0x0046 in sample
        self.unknown1 = struct.unpack_from("<H", data, 0x02)[0]  # 0x000F in sample
        self.seed     = struct.unpack_from("<I", data, 0x04)[0]  # timestamp/seed
        name_len      = data[0x08]
        self.player_name = data[0x0A : 0x0A + name_len].decode("ascii", errors="replace")
        # Bytes 0x0A+name_len .. 0x42 = remainder of header (TBD)
        self._header_tail = data[0x0A + name_len : TILE_DATA_OFFSET]

        # --- Tile grid (16x16) ---
        self.tiles: list[FortTile] = []
        off = TILE_DATA_OFFSET
        for _ in range(TILE_COUNT):
            self.tiles.append(FortTile(data[off], data[off + 1], data[off + 2]))
            off += TILE_STRIDE
        # off should now be SECTION_OFFSET (0x342)

        # --- Section list (length-prefixed records) ---
        self.records: List[FortRecord] = self._parse_records(data, SECTION_OFFSET)

        # entity_count: kept for backwards compat with the previous parser.
        # The 'count' is no longer a separate uint16 - we expose the number of
        # records that look like entity data (body size >= 10) as an indicator.
        # For MyOnlineGame.fort this gives 3, matching the human-observed count
        # of "real" data records (the rest are flag-bytes / empty placeholders).
        self.entity_count = sum(1 for r in self.records if len(r.body) >= 10)

        # entity_data: raw bytes of all records concatenated (kept for compat).
        self.entity_data = data[SECTION_OFFSET:]

    @staticmethod
    def _parse_records(data: bytes, start: int) -> List[FortRecord]:
        """Walk the length-prefixed record stream from `start` until EOF.

        Each record is `[size:u16 LE][body:size-2]`. Stops cleanly if the
        next size would overrun the file or is < 2 (which is also invalid
        per the format - the size field itself is 2 bytes).
        """
        records: List[FortRecord] = []
        off = start
        n = len(data)
        while off + 2 <= n:
            size = struct.unpack_from("<H", data, off)[0]
            if size < 2 or off + size > n:
                # Truncated / corrupt record - stop gracefully.
                break
            body = data[off + 2 : off + size]
            records.append(FortRecord(offset=off, size=size, body=body))
            off += size
        return records

    @classmethod
    def from_file(cls, path: str) -> "FortFile":
        with open(path, "rb") as f:
            return cls(f.read())

    def tile(self, x: int, y: int) -> FortTile:
        return self.tiles[y * GRID_SIZE + x]

    def tile_grid(self) -> np.ndarray:
        """Returns a (16, 16) uint8 array of type_ids."""
        return np.array([t.type_id for t in self.tiles], dtype=np.uint8).reshape(GRID_SIZE, GRID_SIZE)

    def __repr__(self) -> str:
        non_empty = sum(1 for t in self.tiles if not t.is_empty())
        return (
            f"FortFile(player={self.player_name!r}, "
            f"tiles={TILE_COUNT}, non_empty={non_empty}, "
            f"records={len(self.records)}, "
            f"entity_records={self.entity_count})"
        )
