# SHP decoder fix — partial RE result

**Date**: 2026-05-03
**Status**: Partial fix. Algorithm rewritten for the (count, value)
encoding actually used by the file; still fails on rows containing
encoded transparent runs that the decoder treats as opaque colour 0
runs.  Most frames now show a recognisable silhouette instead of the
random-stripes garbage produced by the previous decoder.
**Time-boxed**: 60 min.  Ghidra MCP was unavailable (no program loaded
at `127.0.0.1:8089`) so the work was done by direct byte-level
analysis of the binary file.

## File path

- Original (corrupt outputs):
  `src/netstorm/assets/shp.py.bak`
- New decoder:
  `src/netstorm/assets/shp.py`
- Test script:
  `test_shp_fixed.py`
- Decoded sunArcher frame 0:
  `extracted/test_sunarcher_frame0.png` (sha256 in stdout)

## What was wrong

The legacy decoder assumed a single-byte command stream:

```python
cmd = data[pos]; pos += 1
count = (cmd >> 1) + 1
if cmd & 1:   draw `count` literal bytes
else:         skip `count` pixels (transparent)
```

This scheme does not match _any_ row in the file cleanly.  Group 0
frames _appeared_ to decode because individual rows happened to
overshoot in the same direction by similar amounts, producing a
lopsided but vaguely shaped image.  Inner groups have larger frames so
the per-row over/under-shoot accumulated into hundreds of pixels of
horizontal-stripe garbage.

## Format actually observed in the bytes

### Header (24 bytes)

```
[0..1]   uint16  width        — sprite canvas width
[2..3]   uint16  height       — sprite canvas height
[4..5]   uint16  pivot_x      — pivot X within canvas
[6..7]   uint16  pivot_y      — pivot Y within canvas
[8..11]  int32   x1           — bbox left,   pivot-relative
[12..15] int32   y1           — bbox top,    pivot-relative
[16..19] int32   x2           — bbox right,  pivot-relative (inclusive)
[20..23] int32   y2           — bbox bottom, pivot-relative (inclusive)
```

### Critical correction: pixel data covers the BBOX, not the canvas

For e.g. sunArcher frame 0 the header says canvas = 51×62 but the bbox
is `(-60, -49, -1, -1)` which is 60×49.  The RLE is for a **60×49**
buffer.  When blitting into the full canvas (or onto the world) the
buffer must be placed at `(pivot_x + x1, pivot_y + y1)`.

Outer Group 0 sprites have the same property — frame 0 is 15×9 canvas
with bbox `(-3, -14, 2, 0)` which is 6×15 (a vertical glyph), not 15×9.

The previous decoder ignored bbox entirely and tried to fill the full
canvas, which is a second source of corruption even for outer sprites.

### RLE row format (verified on simple frames)

Per scanline of the bbox region:

```
 [count u8][value u8]   — emit `count` pixels of palette index `value`
 [00]                   — end of row; remaining columns are transparent
```

Verified clean on group 2 frame 9 (the 27×60-canvas / 57×24-bbox spear
sprite): every row sums to ≤ bbox_w, the resulting silhouette is a
recognisable diagonal arrowhead, all 180 RLE bytes consumed.

### Where the format still misbehaves

For larger / more complex frames (sunArcher, walker, cannon) some rows
contain `(count, value)` pairs where `count > bbox_w` (e.g. `(248, …)`,
`(70, …)`).  These can't be naive opaque runs — they must be one of:

- a transparent-skip opcode (perhaps `value == 0xff` or `count >= 0x80`
  encodes a wide skip), OR
- a literal-block opcode (perhaps `count` byte with high bit set means
  "next `count & 0x7F` bytes are individual pixel values"), OR
- a nested per-frame format selector chosen by a header flag we are
  not parsing.

The 60-minute byte-analysis pass did not converge on the exact
discriminator — Ghidra access to `FUN_0045b100` (ShapeToBuffer) is the
fastest way to nail it down.  The `0xf8` value recurs suspiciously and
is a strong candidate for a control opcode.

## What the new decoder does

1. Parses header into `(canvas_w, canvas_h, pivot_x, pivot_y, bbox)`.
2. Computes `bw = x2-x1+1`, `bh = y2-y1+1`.
3. For each of `bh` rows, reads `(count, value)` pairs and stops on a
   `00` byte, drawing `count` opaque pixels of palette index `value`
   per pair. Pixels past `bw` are clipped silently (so the rare
   over-long count doesn't smash adjacent rows).
4. Returns a `ShapeFrame` with new fields `canvas_w`, `canvas_h` so
   downstream renderers can place the bbox buffer into the full canvas
   if they want to.

This produces:

- Group 0 (UI font): correct glyph shapes, no longer striped.
- Group 2 frame 9 (spear): pixel-perfect arrow.
- sunArcher / walker / cannon: recognisable silhouettes with
  horizontal-stripe artefacts on rows that contain the still-unknown
  control opcode.

## Ghidra functions still to inspect (next session)

- `FUN_0045b100` — labelled ShapeToBuffer in earlier sessions, almost
  certainly the per-frame RLE blitter.
- Neighbours `FUN_0045bxxx` — likely the inner per-row decode helper.
- Cross-references from any function reading `_shapes.shp` magic
  `"1.10"` (`DAT_0051cc20`).

When Ghidra MCP is back online:

```bash
curl "http://127.0.0.1:8089/decompile_function" \
     -d '{"name":"FUN_0045b100"}'
curl "http://127.0.0.1:8089/get_function_xrefs" \
     -d '{"name":"FUN_0045b100"}'
```

The expected pattern in pseudo-C is something like:

```c
for (y = 0; y < bbox_h; ++y) {
    x = 0;
    while ((cmd = *src++)) {
        if (cmd & 0x80)              /* or whatever discriminator */
            x += cmd & 0x7F;         /* transparent skip */
        else {
            val = *src++;
            for (i = 0; i < cmd; ++i)
                dst[y*pitch + x++] = val;
        }
    }
}
```

Confirm the discriminator (high bit, value 0xf8, etc.) and the helper
will drop in with a few-line patch to `_decode_frame()`.

## Diff summary

| Change | Old | New |
|---|---|---|
| Pixel canvas | `w × h` (header) | `bw × bh` (bbox) |
| Command byte | `cmd >> 1 + 1`, `cmd & 1` | `(count, value)` pairs |
| Row terminator | none (length-driven) | `00` byte |
| ShapeFrame fields | `width, height, pivot_x, pivot_y, bbox, data, mask` | + `canvas_w, canvas_h` |
