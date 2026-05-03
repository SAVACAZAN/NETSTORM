"""
.nsrec — NetStorm Recording Format

Binary file that captures a full game run from the original executable
at tick granularity. Used as ground truth for differential testing.

File layout:
    [Header 28 bytes]
    [Frame 0]
    [Frame 1]
    ...
    [Frame N]
    [Footer 8 bytes]

Header:
    magic       4s      b"NSRC"
    version     H       format version (current: 1)
    flags       H       bit 0 = has_rng, bit 1 = has_state_hash, bit 2 = has_net
    rng_seed    I       initial RNG state captured from process
    map_id      H       which map was loaded
    player_id   B       local player slot (0-based)
    _pad        B       reserved
    tick_rate   f       ticks per second (float32)
    start_ts    Q       unix timestamp ms when recording started

Frame:
    tick        I       tick counter
    input_mask  I       bitmask of active inputs this tick (see InputBit)
    mouse_x     h       cursor screen X (-1 if no mouse event)
    mouse_y     h       cursor screen Y
    rng_state   I       RNG state BEFORE this tick's rand() calls (0 if not captured)
    state_hash  I       FNV-32 of the game state struct AFTER tick (0 if not captured)
    net_len     H       bytes of network payload this tick (0 if none)
    net_data    <net_len bytes>

Footer:
    total_ticks I       sanity check = number of frames written
    crc32       I       CRC32 of all frame bytes (not including header/footer)
"""

from __future__ import annotations
import io
import struct
import zlib
from dataclasses import dataclass, field
from enum import IntFlag
from pathlib import Path


MAGIC = b"NSRC"
FORMAT_VERSION = 1

HEADER_FMT = "<4sHHIHBBfQ"   # 28 bytes
HEADER_SIZE = struct.calcsize(HEADER_FMT)
assert HEADER_SIZE == 28, HEADER_SIZE

FRAME_BASE_FMT = "<IIhhIIH"   # 22 bytes + net_len bytes
FRAME_BASE_SIZE = struct.calcsize(FRAME_BASE_FMT)

FOOTER_FMT = "<II"
FOOTER_SIZE = struct.calcsize(FOOTER_FMT)


class RecFlags(IntFlag):
    HAS_RNG        = 0x01
    HAS_STATE_HASH = 0x02
    HAS_NET        = 0x04


class InputBit(IntFlag):
    MOUSE_L    = 0x0001
    MOUSE_R    = 0x0002
    MOUSE_M    = 0x0004
    KEY_UP     = 0x0010
    KEY_DOWN   = 0x0020
    KEY_LEFT   = 0x0040
    KEY_RIGHT  = 0x0080
    # ... more to be filled as controls are RE'd


@dataclass
class RecHeader:
    flags: RecFlags
    rng_seed: int
    map_id: int
    player_id: int
    tick_rate: float
    start_ts: int  # unix ms

    def pack(self) -> bytes:
        return struct.pack(
            HEADER_FMT,
            MAGIC, FORMAT_VERSION, int(self.flags),
            self.rng_seed, self.map_id, self.player_id, 0,
            self.tick_rate, self.start_ts,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "RecHeader":
        (magic, ver, flags, rng_seed, map_id, player_id, _,
         tick_rate, start_ts) = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
        if magic != MAGIC:
            raise ValueError(f"bad magic: {magic!r}")
        if ver != FORMAT_VERSION:
            raise ValueError(f"unsupported version: {ver}")
        return cls(RecFlags(flags), rng_seed, map_id, player_id, tick_rate, start_ts)


@dataclass
class RecFrame:
    tick: int
    input_mask: InputBit
    mouse_x: int = -1
    mouse_y: int = -1
    rng_state: int = 0
    state_hash: int = 0
    net_data: bytes = b""

    def pack(self) -> bytes:
        base = struct.pack(
            FRAME_BASE_FMT,
            self.tick, int(self.input_mask),
            self.mouse_x, self.mouse_y,
            self.rng_state, self.state_hash,
            len(self.net_data),
        )
        return base + self.net_data

    @classmethod
    def unpack_from(cls, buf: io.BytesIO) -> "RecFrame":
        base = buf.read(FRAME_BASE_SIZE)
        if len(base) < FRAME_BASE_SIZE:
            raise EOFError
        tick, inputs, mx, my, rng_st, st_hash, net_len = struct.unpack(FRAME_BASE_FMT, base)
        net = buf.read(net_len)
        return cls(tick, InputBit(inputs), mx, my, rng_st, st_hash, net)


@dataclass
class Recording:
    header: RecHeader
    frames: list[RecFrame] = field(default_factory=list)

    def append(self, frame: RecFrame) -> None:
        self.frames.append(frame)

    def save(self, path: Path | str) -> None:
        body = b"".join(f.pack() for f in self.frames)
        footer = struct.pack(FOOTER_FMT, len(self.frames), zlib.crc32(body) & 0xFFFFFFFF)
        Path(path).write_bytes(self.header.pack() + body + footer)

    @classmethod
    def load(cls, path: Path | str) -> "Recording":
        data = Path(path).read_bytes()
        header = RecHeader.unpack(data)
        body = data[HEADER_SIZE:-FOOTER_SIZE]
        total_ticks, crc = struct.unpack(FOOTER_FMT, data[-FOOTER_SIZE:])
        if (zlib.crc32(body) & 0xFFFFFFFF) != crc:
            raise ValueError("CRC mismatch — recording is corrupt")
        buf = io.BytesIO(body)
        frames: list[RecFrame] = []
        while True:
            try:
                frames.append(RecFrame.unpack_from(buf))
            except EOFError:
                break
        if len(frames) != total_ticks:
            raise ValueError(f"frame count mismatch: got {len(frames)}, expected {total_ticks}")
        return cls(header, frames)
