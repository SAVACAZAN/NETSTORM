"""
NetStorm .chfnt bitmap font decoder.

File layout:
  [0..15]   magic "BitmapFontData\x1a\x00"
  [16..19]  version (uint32)
  [20..23]  size    (uint32) — font size in points
  [24..27]  ascent  (uint32) — pixels above baseline
  [28..31]  descent (uint32) — pixels below baseline  (ascent+descent == size)
  [32..35]  glyph_count (uint32) — always 256
  [36..36+count*4-1]  advance widths (uint32 per char, 0..count-1)
  [36+count*4 ..]     glyph 1.10 sections, one per character code 0..255
                        packed sequentially; each uses the same 1.10/frame
                        format as _shapes.shp (see shp.py).

All 256 glyph sections have the same canvas size (w×h fixed per font) but
different visible content encoded via RLE.  The character advance width is
taken from the widths table, not from the frame dimensions.
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from pathlib import Path

from netstorm.assets.shp import ShapeFrame, ShpDecoder


@dataclass
class NetStormFont:
    size: int
    ascent: int
    descent: int
    widths: list[int]   # advance width per char code 0..255
    glyphs: list[ShapeFrame | None]  # glyph per char code; None if missing

    def get_width(self, char: str) -> int:
        idx = ord(char) & 0xFF
        return self.widths[idx] if idx < len(self.widths) else 0

    def get_glyph(self, char: str) -> ShapeFrame | None:
        idx = ord(char) & 0xFF
        return self.glyphs[idx] if idx < len(self.glyphs) else None


def load(path: Path | str) -> NetStormFont:
    data = Path(path).read_bytes()
    if not data.startswith(b"BitmapFontData\x1a"):
        raise ValueError(f"Not a valid .chfnt file: {path}")

    version = struct.unpack_from("<I", data, 16)[0]
    size    = struct.unpack_from("<I", data, 20)[0]
    ascent  = struct.unpack_from("<I", data, 24)[0]
    descent = struct.unpack_from("<I", data, 28)[0]
    count   = struct.unpack_from("<I", data, 32)[0]

    widths = [struct.unpack_from("<I", data, 36 + i * 4)[0] for i in range(count)]

    # Collect all per-glyph 1.10 sections sequentially after the width table.
    # Each section: 8-byte 1.10 header + 8-byte ptr + frame data.
    # Sections are packed in character-code order 0..255.
    glyphs: list[ShapeFrame | None] = [None] * count
    glyph_idx = 0
    pos = 36 + count * 4   # first byte after width table

    while glyph_idx < count and pos < len(data):
        # Skip bytes until we find a "1.10" section header
        idx = data.find(b"1.10", pos)
        if idx == -1:
            break
        sec_count = struct.unpack_from("<I", data, idx + 4)[0]
        if sec_count != 1:
            pos = idx + 4
            continue

        ptr = struct.unpack_from("<Q", data, idx + 8)[0]
        frame_off = idx + ptr
        if frame_off + 24 >= len(data):
            pos = idx + 4
            continue

        dec = ShpDecoder(data)
        try:
            frame = dec._decode_frame(frame_off)
            glyphs[glyph_idx] = frame
        except (IndexError, struct.error):
            pass

        glyph_idx += 1
        pos = idx + 4   # advance past this section header

    return NetStormFont(
        size=size,
        ascent=ascent,
        descent=descent,
        widths=widths,
        glyphs=glyphs,
    )
