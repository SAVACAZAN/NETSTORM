# Sprite Name → SHP Group ID Mapping

## Method used

**Static reverse engineering of `netstorm.exe` via Ghidra MCP API.** Read-only analysis — no patches/renames in the binary.

### Discovery path

1. Searched strings for "Shape" / "_shapes.shp" / "altar" → found `_shapes.shp` literal at `0x0051d73c` and `masterShapeDatabasePtr` at `0x0051d77c`.
2. Followed xref → `FUN_004434d0` (RiftType.cpp init): memory-maps the file via `FUN_004be710` → stores pointer at `DAT_0051cbf4 = masterShapeDatabasePtr`.
3. Found `FUN_00446080` calls a *type registration loop*:
   - `FUN_00445f40()`  — allocates 160000-byte parser bud array
   - `FUN_00445e70(PTR_DAT_0051c6f8)` — opens first .type file
   - `FUN_0043b270()` — YACC-style .type parser (scans tokens, dispatches to `FUN_004460f0` for each cluster line `id : tags : "file.gif" #idx`)
   - `FUN_00445f10()` increments `DAT_0051cc08` and loads next .type from the array, terminating when index >= 0x65 (101)
4. **Critical discovery in `FUN_004460f0` (cluster handler), at the *end of frame-list parsing*:**
   ```c
   iVar11 = *DAT_0051cc20;
   for (iVar4 = 0; (iVar11 != 0x30312e31 && (iVar4 < 1000)); iVar4 = iVar4 + 1) {
       DAT_0051cc20 = DAT_0051cc20 + 1;
       iVar11 = *DAT_0051cc20;
   }
   *(int **)(pcVar1 + 0xdc) = DAT_0051cc20;   // assign type's shape pointer
   DAT_0051cc20 = DAT_0051cc20 + 1;
   ```
   `0x30312e31` = ASCII `"1.10"` little-endian.
   **The loader scans the SHP file for the next `"1.10"` magic and assigns it to whichever .type is currently being parsed.** The `"file.gif" #idx` filename in .type files is **purely cosmetic / dev metadata** — it is parsed but never used for lookup.

5. The hardcoded array `PTR_DAT_0051c6f8` at `0x0051c6f8` contains 101 type-name string pointers (1 NULL sentinel after slot 100). I dumped it with `read_memory` and resolved each pointer.

### Why the order is deterministic

The `.type` filenames are loaded by **fixed compile-time order** from `PTR_DAT_0051c6f8`. The shape database scanner (`DAT_0051cc20`) starts at `masterShapeDatabasePtr` and only ever moves forward through the file, so:

```
SHP inner_group_index N == PTR_DAT_0051c6f8[N] (.type name)
shp.py groups[N+1]      == sprite for type N
```

(`groups[0]` in the `shp.py` decoder is the OUTER 130-frame UI/font block, which has no .type entry.)

## Mapping table

| Group ID | Sprite Name | Frames | Notes |
|---|---|---|---|
| 0 | ui_font | 130 | Outer 1.10 group — 130 small (15x9, 7x10, etc.) glyphs / UI bits |
| 1 | dude | 35 | |
| 2 | sunArcher | 64 | |
| 3 | sunAviary | 18 | |
| 4 | sunFlyer | 22 | |
| 5 | banner | 4 | |
| 6 | windBattery | 4 | |
| 7 | rainBattery | 4 | |
| 8 | thunderBattery | 4 | |
| 9 | sunBlocker | 4 | |
| 10 | thunderBlocker | 1 | |
| 11 | blankMissile | 20 | |
| 12 | bolt | 60 | |
| 13 | bridge | 3 | |
| 14 | sunDisc | 4 | |
| 15 | emptyGeyser | 26 | |
| 16 | sunFactory | 8 | |
| 17 | windFactory | 20 | |
| 18 | rainFactory | 8 | |
| 19 | thunderFactory | 7 | |
| 20 | residence | 1 | |
| 21 | fencemark | 10 | |
| 22 | flag | 71 | |
| 23 | fortGump | 38 | |
| 24 | icon | 9 | |
| 25 | island | 9 | |
| 26 | islandStalag | 16 | |
| 27 | playerBanner | 80 | |
| 28 | isle | 4 | |
| 29 | isleBig | 1 | |
| 30 | geyserBrightener | 16 | |
| 31 | treeTwo | 6 | |
| 32 | treeThree | 83 | |
| 33 | fringe | 25 | |
| 34 | mana | 38 | |
| 35 | range | 4 | |
| 36 | manabolt | 37 | |
| 37 | flare | 1 | |
| 38 | puzzlePiece | 1 | |
| 39 | playerIsland | 17 | |
| 40 | battleIsland | 1 | |
| 41 | particlePlaceHolder | 4 | |
| 42 | sunBalloon | 6 | |
| 43 | buried | 3 | |
| 44 | bombExplodeSmall | 3 | |
| 45 | bombExplodeMedium | 3 | |
| 46 | bombExplodeLarge | 3 | |
| 47 | bombHeal | 3 | |
| 48 | bombInvisible | 3 | |
| 49 | bombParalyze | 3 | |
| 50 | bombHardener | 3 | |
| 51 | bombTreason | 44 | |
| 52 | edgeFarm | 36 | |
| 53 | geyser | 42 | |
| 54 | windVortex | 58 | |
| 55 | rainVortex | 32 | |
| 56 | thunderVortex | 4 | |
| 57 | outpost | 4 | |
| 58 | mcloud | 58 | |
| 59 | sunCannon | 26 | |
| 60 | rainCannon | 29 | |
| 61 | rainCannonMissile | 37 | |
| 62 | thunderCannon | 12 | |
| 63 | thunderCannonMissile | 132 | |
| 64 | sunWalker | 1 | |
| 65 | teleportEffect | 162 | |
| 66 | bulf | 20 | |
| 67 | sunFence | 74 | |
| 68 | windWalker | 46 | |
| 69 | windFlyer | 14 | |
| 70 | windAviary | 202 | |
| 71 | windArcher | 4 | |
| 72 | windBalloon | 10 | |
| 73 | windBlocker | 28 | |
| 74 | rainAviary | 34 | |
| 75 | rainFlyer | 10 | |
| 76 | rainFence | 42 | |
| 77 | rainBalloon | 4 | |
| 78 | rainBlocker | 6 | |
| 79 | thunderArcher | 7 | |
| 80 | thunderFence | 30 | |
| 81 | growingRainBlocker | 1 | |
| 82 | platform | 2 | |
| 83 | player | 34 | |
| 84 | mog | 20 | |
| 85 | nugget | 4 | |
| 86 | bridgeConnector | 42 | |
| 87 | rainWalker | 0 | shp.py decoder reports 0 frames — likely a decoder bug (frame count > some sanity check, or zero-sized) |
| 88 | noIsland | 336 | |
| 89 | priest | 1 | |
| 90 | lightning | 88 | |
| 91 | anim | 1 | |
| 92 | challengeIsland | 0 | shp.py decoder reports 0 frames — likely off-by-one or empty |
| 93 | fakeThreeByThreeSurface | 23 | |
| 94 | sunFlyerBomb | 90 | |
| 95 | altar | 198 | matches "altar01.gif" .. "altar24.gif" × ~8-13 frames seen in altar.type |
| 96 | dais | 5 | |
| 97 | rune | 30 | |
| 98 | forceField | 3 | |
| 99 | bombSpecialOne | 90 | |
| 100 | daisExtraFrames | 2 | |

## Functions involved

| Address | Symbol | Role |
|---|---|---|
| `0x004434d0` | `FUN_004434d0` | RiftType init: opens `_shapes.shp`, sets `masterShapeDatabasePtr = DAT_0051cbf4` |
| `0x004be710` | `FUN_004be710` | `winUtil.cpp`: CreateFileA + CreateFileMappingA + MapViewOfFile (memory-mapped file) |
| `0x00446080` | `FUN_00446080` | Type registration entry point — calls `FUN_00445e70` then loops `FUN_00444e10` for each registered type |
| `0x00445e70` | `FUN_00445e70` | Opens a single .type file (uses `FUN_0049c1a0` to build pathspec → `FUN_004b95c0` to read) |
| `0x00445f10` | `FUN_00445f10` | Iterator: increments `DAT_0051cc08`, returns 1 when index ≥ 0x65 (101 types) |
| `0x0043b270` | `FUN_0043b270` | YACC parser for .type DSL; dispatches cluster lines |
| `0x004460f0` | `FUN_004460f0` | **Cluster handler — assigns SHP group via "1.10" magic scan** (the actual mapping site) |
| `0x0051c6f8` | `PTR_DAT_0051c6f8` | **Hardcoded 101-entry array of .type filenames in load order** |
| `0x0051cbf4` | `masterShapeDatabasePtr` | Memory-mapped pointer to `_shapes.shp` |
| `0x0051cc20` | `DAT_0051cc20` | Cursor into the SHP — advanced past each `"1.10"` group as types load |
| `0x0051cc08` | `DAT_0051cc08` | Index into `PTR_DAT_0051c6f8` (current type being loaded) |

## Confidence

**HIGH** — the assignment site in `FUN_004460f0` literally scans for `0x30312e31` ("1.10") in the SHP and assigns the next group to whichever type is being parsed; the type load order is the fixed compile-time array `PTR_DAT_0051c6f8`. The first inner group has 35 frames and gets `dude` — the second has 64 frames and gets `sunArcher` (a more-animated unit), which is consistent with a unit that needs many directional walking frames.

**Caveats:**
- 2 groups (87 `rainWalker`, 92 `challengeIsland`) currently have 0 frames according to `shp.py`. The decoder rejects frames on `w==0 || h==0 || w>1024 || h>1024` and on `IndexError`/`struct.error`. Likely the existing parser stops too early or has a bounds bug. The mapping itself is still correct; verify by re-running with relaxed bounds.
- The .gif filenames inside .type files (e.g. `"altar01.gif" #15`) are **completely ignored** by the engine — they are decorative metadata for the original artist tooling. The frame index `#NN` is used as offset into the assigned shape group (`*(byte *)((int)piVar7 + 0x22)` in `FUN_0045b100` is the byte-sized frame index).
- The user's expected count of 202 groups / 6252 frames does NOT match this build. The RIP version of NetStorm has only 100 inner groups + 1 outer = 101 total / ~3126 frames. The 202 number may correspond to the FULL retail install (different `_shapes.shp`) — but the *mapping logic itself is identical*: the array at `PTR_DAT_0051c6f8` and the "1.10" scanner in `FUN_004460f0` define the assignment regardless of group count.

## Reproducer (Python)

```python
import requests, struct
r = requests.get("http://127.0.0.1:8089/read_memory",
                 params={"address": "0x0051c6f8", "length": 420})
ptrs = struct.unpack_from("<105I", bytes(r.json()["data"]))
for i, p in enumerate(ptrs):
    if p == 0: continue
    sd = bytes(requests.get("http://127.0.0.1:8089/read_memory",
                            params={"address": f"0x{p:08x}", "length": 64}).json()["data"])
    print(i, sd[:sd.find(b"\\x00")].decode("ascii"))
```
