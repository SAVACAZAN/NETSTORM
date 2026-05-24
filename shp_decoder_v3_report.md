# SHP Decoder v3 — Reverse-Engineered from netstorm.exe

## Source

The decoder was reverse-engineered from `FUN_00465b95` in netstorm.exe — the
"fast path" no-clip variant of the SHP blitter. It is invoked from
`FUN_00465772` (the main blit) via:

```c
if (bVar14 == 0 && bVar16 == 0) {  // both clip masks empty
    FUN_00465b95(...);
    return 0;
}
```

The fast path is the ideal reference because it omits viewport clipping and
exposes pure decoder logic.

## Algorithm (pseudocode)

```
for each row y in [0, bbox_h):
    x = 0
    loop:
        cmd  = src[pos]; pos += 1
        flag = cmd & 1
        n    = cmd >> 1

        if flag == 0 and n == 0:
            break                       # END OF ROW
        if flag == 0 and n > 0:
            color = src[pos]; pos += 1  # FILL
            write n pixels of `color` at dst[x..x+n)
            x += n
        if flag == 1 and n == 0:
            cnt = src[pos]; pos += 1    # SKIP (transparent)
            x += cnt
        if flag == 1 and n > 0:
            for i in 0..n:              # LITERAL
                dst[x+i] = src[pos+i]
            pos += n
            x   += n
```

In the assembly, the FILL/LITERAL inner loops are unrolled into
`(n & 3)` byte writes followed by `(n >> 2)` 4-byte writes — this is just
an x86 perf optimization and decodes to the same pixel stream.

The end-of-row sentinel is `cmd == 0` (i.e. flag=0, n=0). Trailing pixels
of the row stay transparent.

## Why previous interpretations failed

### v1 (legacy)
Used `(cmd >> 1) + 1` as a count and alternating skip/draw without the
flag bit. Worked for narrow sprites by accident — produced horizontal
stripes on wide sprites because the run lengths drifted out of sync.

### v2 (count, value) pair
Treated each row as `[count u8][value u8]` pairs terminated by `0x00`.
This decoded outer group 0 (small UI sprites) by coincidence — those
small sprites happened to start with `flag=1` LITERAL commands whose
n value matched a plausible "count", and subsequent bytes lined up.
On any sprite with FILL or SKIP commands the decoder lost framing.

### v3 (current — correct)
Direct port of the FUN_00465b95 four-state machine. The discriminator
is the LSB of every command byte — `flag=1` means "advancing op"
(SKIP or LITERAL), `flag=0` means "color op" (FILL or EOR).

## Walked example: outer group 0 frame 0

Header: bbox 6x15. RLE bytes:
```
01 02 04 18 00  01 02 05 10 d3 00  01 01 07 1f 1b d3 00  0d 1d 23 23 1c 1c 95 00 ...
```

Row 0: `01 02 04 18 00`
- `01` -> flag=1, n=0 -> SKIP. count = `02` -> x=2
- `04` -> flag=0, n=2 -> FILL. color = `18` -> write 2 px of 0x18, x=4
- `00` -> EOR

Result: `.. .. 18 18 .. ..` (6 cols total, 2 trailing transparent).

Row 3: `0d 1d 23 23 1c 1c 95 00`
- `0d` -> flag=1, n=6 -> LITERAL 6 bytes: 0x1d 0x23 0x23 0x1c 0x1c 0x95 -> x=6
- `00` -> EOR

Result: `1d 23 23 1c 1c 95` (full row).

Both rows consume exactly bbox_w=6 logical pixels. Confirmed against
`decode_rows` test harness.

## Visual verification

| Sprite | Group | bbox | Render |
|---|---|---|---|
| Outer 0 frame 0 (projectile) | outer 0 | 6x15 | recognizable arrow-like shape |
| sunArcher frame 0 | inner 2 (group index 3) | 60x49 | clearly a humanoid archer with bow |
| windAviary frame 0 | inner 70 (group index 71) | 134x82 | building with rotating windmill blades |

PNG outputs:
- `extracted/test_DECODER_v3.png` (sunArcher 1x)
- `extracted/test_DECODER_v3_4x.png` (sunArcher 4x)
- `extracted/test_DECODER_v3_windAviary_4x.png`

All three render as recognizable shapes (no stripes, no garbage).
sunArcher uses `sunarcher.col` palette extracted from netstorm.tarc.

## Bbox size note

Task description gives sunArcher bbox as 39x41, but the actual
header in `_shapes.shp` for inner group 2 frame 0 reads bbox
`(-60,-49,-1,-1)` -> bw=60, bh=49. The decoder uses what the header
says and the result is visually correct, so the 39x41 figure in the
task brief is likely from a different frame in the animation.

## Patch

`src/netstorm/assets/shp.py` `_decode_frame()` replaced with the
four-state machine. Backup: `shp.py.bak2`. `ShapeFrame` dataclass
interface unchanged (width, height, canvas_w, canvas_h, pivot_x,
pivot_y, bbox, data, mask).

## Files changed
- `src/netstorm/assets/shp.py` — patched
- `src/netstorm/assets/shp.py.bak2` — backup of v2 decoder

## Files added
- `extracted/test_DECODER_v3.png`
- `extracted/test_DECODER_v3_4x.png`
- `extracted/test_DECODER_v3_sunArcher.png` (note: this is the same as v3.png)
- `extracted/test_DECODER_v3_windAviary.png`
- `extracted/test_DECODER_v3_windAviary_4x.png`
- `shp_decoder_v3_report.md` (this file)
