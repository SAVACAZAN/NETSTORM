"""
NetStorm .shp sprite decoder — "1.10" hierarchical format.

File layout (_shapes.shp):
  Outer 1.10 at offset 0:
    [0..3]  magic "1.10"
    [4..7]  count (uint32) — number of top-level sprites
    [8..]   count × 8-byte section-relative offsets to frame data

  Inner 1.10 groups packed sequentially immediately after the outer pointer
  table.  Each group:
    [0..3]  magic "1.10"
    [4..7]  count (uint32) — frames in this animation group
    [8..]   count × 8-byte section-relative offsets to frame data

  All pointers are SECTION-RELATIVE: frame_file_offset = section_start + ptr.
  Frame offsets are NOT necessarily sequential — frames can be scattered
  across the file in any order.

Frame data layout (24-byte header + RLE):
  [0..1]   width   (uint16)  — canvas width
  [2..3]   height  (uint16)  — canvas height
  [4..5]   pivot_x (uint16)  — pivot X from canvas top-left
  [6..7]   pivot_y (uint16)  — pivot Y from canvas top-left
  [8..11]  x1 (int32) — bbox left,   pivot-relative
  [12..15] y1 (int32) — bbox top,    pivot-relative
  [16..19] x2 (int32) — bbox right,  pivot-relative (inclusive)
  [20..23] y2 (int32) — bbox bottom, pivot-relative (inclusive)
  [24..]   RLE rows — one per scanline of the BBOX REGION (not full canvas).
           bbox_w = x2 - x1 + 1
           bbox_h = y2 - y1 + 1

RLE row format (bbox-region rows) — reverse-engineered from
netstorm.exe FUN_00465b95 (the no-clip "fast path" blit):
  Each command byte encodes:
    flag = cmd & 1
    n    = cmd >> 1
  Four states:
    flag=0, n=0  -> END OF ROW (advance to next row; remaining pixels
                    of the row stay transparent)
    flag=0, n>0  -> FILL — read 1 byte color, write n pixels of that
                    color, then read next cmd
    flag=1, n=0  -> SKIP — read 1 byte count, advance dest by count
                    (transparent pixels), then read next cmd
    flag=1, n>0  -> LITERAL — read n bytes verbatim as pixels, then
                    read next cmd

  After bbox_h rows the stream ends; trailing bytes are footer metadata.

Visible-region positioning:
  The decoded bbox-region buffer covers (bbox_w x bbox_h) pixels.  When
  blitting to a larger canvas, position the buffer at:
      dst_x = pivot_x + x1
      dst_y = pivot_y + y1

History:
  v1: legacy (cmd >> 1)+1 skip/draw scheme — wrong, produced stripes.
  v2: (count, value) pair + 00 EOR — also wrong (decoded outer group
      accidentally because all small frames just happened to start with
      flag=1 LITERAL bytes).
  v3 (this file): exact port of FUN_00465b95 fast-path state machine.
      Validated visually on outer group 0, sunArcher (group 2), and
      windAviary (group 70) — sprites render as recognizable shapes.
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from pathlib import Path

_MAGIC = b"1.10"


@dataclass
class ShapeFrame:
    width: int          # bbox_w (decoded buffer width)
    height: int         # bbox_h (decoded buffer height)
    canvas_w: int       # full canvas width  (header w)
    canvas_h: int       # full canvas height (header h)
    pivot_x: int
    pivot_y: int
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 (pivot-relative)
    data: bytes         # palette-index pixels, row-major over bbox region
    mask: bytes         # 1 = opaque, 0 = transparent

    def to_rgba(self, palette: list[tuple[int, int, int]],
                transparent_indices: set[int] | None = None) -> bytes:
        """Convert to RGBA bytes.

        NetStorm palette convention (discovered 2026-05-03):
        Palette indices 0-9 are reserved for transparency (magenta in raw .col).
        We treat any index in `transparent_indices` as fully transparent.

        Default: indices 0-9 + any pixel with magenta RGB (255,0,255).
        """
        if transparent_indices is None:
            transparent_indices = set(range(10))  # 0..9 reserved per NetStorm convention

        rgba = bytearray(self.width * self.height * 4)
        for i in range(self.width * self.height):
            if self.mask[i]:
                idx = self.data[i]
                if idx in transparent_indices:
                    continue  # transparent
                r, g, b = palette[idx]
                if r == 255 and g == 0 and b == 255:
                    continue  # additional magenta safeguard
                rgba[i * 4]     = r
                rgba[i * 4 + 1] = g
                rgba[i * 4 + 2] = b
                rgba[i * 4 + 3] = 255
        return bytes(rgba)


@dataclass
class ShapeGroup:
    frames: list[ShapeFrame] = field(default_factory=list)


class ShpDecoder:
    def __init__(self, data: bytes) -> None:
        self.data = data
        # group 0  = outer sprites (one frame each, non-animated)
        # groups 1+ = inner animation sequences
        self.groups: list[ShapeGroup] = []

    def decode(self) -> None:
        if self.data[:4] != _MAGIC:
            raise ValueError("Not a 1.10 SHP file")

        outer_count = struct.unpack_from("<I", self.data, 4)[0]

        # Outer group: top-level sprites
        outer_group = self._parse_group(section_start=0, count=outer_count,
                                        ptr_table_offset=8)
        self.groups.append(outer_group)

        # Inner groups packed right after the outer pointer table
        pos = 8 + outer_count * 8
        while pos + 8 <= len(self.data):
            if self.data[pos: pos + 4] != _MAGIC:
                break
            inner_count = struct.unpack_from("<I", self.data, pos + 4)[0]
            if inner_count > 10_000:
                break
            group = self._parse_group(section_start=pos, count=inner_count,
                                      ptr_table_offset=pos + 8)
            self.groups.append(group)
            pos += 8 + inner_count * 8

    def _parse_group(self, section_start: int, count: int,
                     ptr_table_offset: int) -> ShapeGroup:
        group = ShapeGroup()
        for i in range(count):
            ptr = struct.unpack_from("<Q", self.data,
                                     ptr_table_offset + i * 8)[0]
            frame_off = section_start + ptr
            if frame_off + 24 >= len(self.data):
                continue
            w, h = struct.unpack_from("<HH", self.data, frame_off)
            if w == 0 or h == 0 or w > 1024 or h > 1024:
                continue
            try:
                group.frames.append(self._decode_frame(frame_off))
            except (IndexError, struct.error):
                pass
        return group

    def _decode_frame(self, offset: int) -> ShapeFrame:
        cw, ch, px, py = struct.unpack_from("<HHHH", self.data, offset)
        x1, y1, x2, y2 = struct.unpack_from("<iiii", self.data, offset + 8)

        bw = x2 - x1 + 1
        bh = y2 - y1 + 1
        # Defensive: clamp absurd sizes (some frames have bbox outside canvas)
        if bw <= 0 or bh <= 0 or bw > 4096 or bh > 4096:
            bw = max(1, cw)
            bh = max(1, ch)

        pixels = bytearray(bw * bh)
        mask   = bytearray(bw * bh)
        pos    = offset + 24
        end    = len(self.data)
        data   = self.data

        # Decode bbox_h rows using the exact FUN_00465b95 state machine.
        for y in range(bh):
            x = 0
            row_base = y * bw
            if pos >= end:
                break
            while pos < end:
                cmd = data[pos]
                pos += 1
                flag = cmd & 1
                n = cmd >> 1
                if flag == 0:
                    if n == 0:
                        # END OF ROW
                        break
                    # FILL: 1 color byte, n pixels of that color
                    if pos >= end:
                        break
                    color = data[pos]
                    pos += 1
                    for _ in range(n):
                        if 0 <= x < bw:
                            idx = row_base + x
                            pixels[idx] = color
                            mask[idx] = 1
                        x += 1
                else:
                    if n == 0:
                        # SKIP: 1 count byte, advance dest (transparent)
                        if pos >= end:
                            break
                        x += data[pos]
                        pos += 1
                    else:
                        # LITERAL: n verbatim pixel bytes
                        if pos + n > end:
                            break
                        for _ in range(n):
                            if 0 <= x < bw:
                                idx = row_base + x
                                pixels[idx] = data[pos]
                                mask[idx] = 1
                            pos += 1
                            x += 1

        return ShapeFrame(
            width=bw, height=bh,
            canvas_w=cw, canvas_h=ch,
            pivot_x=px, pivot_y=py,
            bbox=(x1, y1, x2, y2),
            data=bytes(pixels),
            mask=bytes(mask),
        )


def load(path: Path | str) -> ShpDecoder:
    data = Path(path).read_bytes()
    dec  = ShpDecoder(data)
    dec.decode()
    return dec
