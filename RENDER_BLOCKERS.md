# Render Blockers - Map & Sprite Visualization

**Date**: 2026-05-03
**Status**: Map rendering blocked by 2 unresolved issues. Documented here for next session.

---

## What works

✅ **Sprite name mapping** (101 groups identified):
- Group 25 = `island`, 28 = `isle`, 29 = `isleBig`, 33 = `fringe`, 88 = `noIsland` (water)
- Group 53 = `geyser`, 95 = `altar`, 96 = `dais`
- Group 64 = `sunWalker`, 68 = `windWalker`, 87 = `rainWalker`
- Group 2 = `sunArcher`, 71 = `windArcher`, 79 = `thunderArcher`
- Etc. (full list in `extracted/sprite_name_mapping.json`)

✅ **Map structure** (16x16 tile grid, post-grid records)
✅ **Tile_id distribution** (e.g. `thewarbegins`: 0x00=139 land, 0x9D=82, 0xFD=15, etc.)
✅ **Catalog UI** with names: `extracted/catalog_named.html`

---

## What doesn't work yet

### Blocker 1: SHP inner groups decode corrupted

**Symptom**: Group 0 (UI font, outer) decodes correctly with `bulf.col` palette.
But inner groups (1-100) produce garbled images even with their own .col palette:
- `sunArcher` (group 2) with `sunarcher.col` -> still corrupted horizontal stripes
- `isle` (group 28) shows mismatched colors (red/green/blue stripes)

**Hypothesis**:
1. Inner group RLE format may differ from outer format
2. Frame headers may have additional fields not parsed (e.g. compression flag)
3. The shp.py decoder was written/tested only against group 0 (130 small UI sprites)

**Evidence pointing to (1) or (2)**:
- `shp.py:_decode_frame()` reads 24-byte header (w, h, pivot_x, pivot_y, x1, y1, x2, y2)
  followed by RLE rows. This matches outer group format.
- For inner groups, large sprites (e.g. 121x152, 593x406) may use different layout.

**Fix path** (next session, ~2-4h):
1. Decompile RLE decode function in netstorm.exe via Ghidra MCP
2. Compare with `shp.py:to_rgba()` line-by-line
3. Look for branch on group_id == 0 vs > 0

### Blocker 2: Terrain palette not in TARC

**Symptom**: 75 of 101 sprite groups have NO matching .col file in TARC (only 26 do).
All terrain sprites (isle, island, fringe, geyser, altar, walkers without team prefix) are missing palette.

**Hypothesis**:
- Game uses a **global system palette** loaded from binary or set via Windows VGA
- Or sprites with no .col use a **default 256-color palette** hardcoded somewhere

**Fix path** (next session, ~1h):
1. Search Ghidra for `SetPaletteEntries` / `CreatePalette` / `RealizePalette` Win32 calls
2. Find palette init code (likely runs once at game start)
3. Extract palette bytes via Ghidra memory dump

---

## What I built (works partially)

### Tools created today

| File | Purpose | Status |
|---|---|---|
| `extract_all_sprites.py` | Extracts all 6252 frames with bulf.col palette | OK (but wrong palette) |
| `build_catalog_v2.py` | HTML catalog with size-based categories | OK |
| `build_named_catalog.py` | HTML catalog with REAL names + categories | OK |
| `render_map.py` | Map rendering with colored diamonds | OK (placeholder) |
| `render_map_v2.py` | Map rendering with sprite tiles | Wrong colors (palette issue) |
| `extract_sprites_correct_palette.py` | Per-group palette mapping | Half OK (only 26/101 match) |
| `RENDER_BLOCKERS.md` | This file | OK |

### Output paths
- `extracted/catalog_named.html` - **best catalog** with names
- `extracted/sprites_all/` - 6252 PNGs (wrong palette for non-bulf sprites)
- `extracted/sprites_palette_correct/` - 26 groups with correct palette (still SHP-decode issues)
- `extracted/maps/` - 24 maps with colored diamonds
- `extracted/maps_v2/` - 24 maps with sprite tiles (wrong palette)
- `extracted/sprite_name_mapping.json` - 101 group names (CONFIRMED via Ghidra)
- `extracted/sprites_palette_correct/palette_map.json` - 26 group->palette mappings

---

## Plan for next session

### Priority 1: Fix SHP decoder (highest impact)
- 4-6 hours work
- Decompile FUN_004460xx series in Ghidra
- Most likely a missing flag or different RLE for big sprites
- After fix: can render real sprites

### Priority 2: Find terrain palette
- 1-2 hours
- Search GDI calls in binary
- Could be in a fixed memory location loaded at startup

### Priority 3: Render maps with real sprites + buildings
- Need fixes 1 and 2 first
- Then map renderer is straightforward

### Priority 4: Decode post-grid records (for buildings)
- Currently we know the framing (length-prefixed) but not field semantics
- 3 records "large" (>=10B) likely encode {position, type, owner} for buildings
- Requires runtime trace via Ghidra debugger

---

## Honest status

What I claimed worked but didn't:
- "Render maps with real sprites" - I rendered them, but they look corrupted because
  of the 2 blockers above. The maps_v2/*.png files are NOT correct visuals.

What works as advertised:
- Sprite extraction (raw frames)
- Name identification (via Ghidra)
- Catalog UIs (display the wrong sprites correctly)
- Tile distribution analysis

**Bottom line**: We have all the metadata and all the raw bytes correctly identified.
The remaining work is decoding the bytes correctly into pixels.
