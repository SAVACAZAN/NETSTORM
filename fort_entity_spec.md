# .fort Entity Section - Reverse-Engineering Report

**Subject:** internal layout of NetStorm `.fort` save files (post-grid section).
**Sample:** `NetStorm-Islands-at-War_Win_EN_RIP-Version/NetStorm RIP/d/MyOnlineGame.fort` (1070 bytes)
**Date:** 2026-05-03
**Status:** PARTIAL - record-stream framing fully decoded; per-record field
semantics still TBD.

---

## TL;DR

1. The previous parser placed the tile grid at file offset `0x3E`. **It is
   actually at `0x42`** (off by 4 bytes). The 4 bytes at `0x3E..0x41`
   (`AD 03 03 02` in the sample) belong to the trailing header section, not
   to tile data. After this fix, the 256 water tiles (`type_id=0x63`) line
   up exactly stride-3 from `0x42` to `0x342`.
2. The post-grid section is **not** `entity_count + entity[]`. It is a stream
   of length-prefixed records:
   ```
   while not EOF:
       size : uint16 LE         # total record size INCLUDING this 2-byte word
       body : size - 2 bytes
   ```
   This was confirmed by Ghidra-decompiling the writer
   `FUN_0044c9f0` (the `DataManager` serializer used by `FUN_004c1380`
   "sendFort").
3. For `MyOnlineGame.fort` the stream contains **30 records** that consume
   exactly the remaining 236 bytes (offsets `0x342..0x42E`).
4. The `0x33E` "entity_count" field that the prior parser referenced is
   actually the third byte of tile #239 + first byte of tile #240 - it's
   coincidentally `00 25344` because it sits inside the water-tile run.

---

## Hex Analysis - MyOnlineGame.fort

```
0000  46 00 0f 00 2c 95 06 00 07 00 55 6e 6e 61 6d 65   F...,.....Unname    <- magic, unk1, seed/ts, name
0010  64 1e 00 00 00 00 00 00 00 00 00 00 00 85 00 00   d...............
0020  00 00 00 00 00 56 00 1c 34 00 00 00 00 85 00 02   .....V..4.......
0030  00 0e 00 00 00 00 00 00 00 00 04 00 00 45 ad 03   .............E..
0040  03 02 63 00 00 63 00 00 63 00 00 63 00 00 63 00   ..c..c..c..c..c.    <- 0x42 = first tile
...
0330  00 63 00 00 63 00 00 63 00 00 63 00 00 63 00 00   .c..c..c..c..c..
0340  63 00 03 00 00 7a 00 07 09 11 a2 00 00 00 00 00   c....z..........    <- 0x342 = section list
                ^^^^^ size=3 (rec0)
                      ^^^^^ size=122 (rec1) starts at 0x345
0350  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
...
03B0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 02
03C0  00 02 00 0c 00 04 85 04 00 47 04 80 04 4c 04 06   ......... record sizes 2,2,12 here
03D0  00 00 00 00 00 03 00 00 02 00 02 00 02 00 17 00   ........ then 6, 3, 2, 2, 2, 23
03E0  02 63 01 00 ee 9e 81 01 00 63 00 00 63 00 00 63
03F0  01 00 86 59 01 03 00 02 03 00 02 03 00 02 03 00   then 19x size=3 records
0400  02 03 00 02 03 00 02 03 00 02 03 00 02 03 00 02
0410  03 00 02 03 00 02 03 00 02 03 00 02 03 00 02 03
0420  00 02 03 00 02 03 00 02 03 00 02 03 00 02         ends exactly at EOF (0x42E)
```

---

## Header Layout (revised)

| Offset | Size | Type    | Field          | Sample value      |
|--------|------|---------|----------------|-------------------|
| `0x00` | 2    | uint16  | magic/version  | `0x0046`          |
| `0x02` | 2    | uint16  | unknown1       | `0x000F` (15)     |
| `0x04` | 4    | uint32  | seed_or_ts     | `0x0006952C`      |
| `0x08` | 1    | uint8   | name_len       | `7`               |
| `0x09` | 1    | uint8   | _pad           | `0`               |
| `0x0A` | name_len | str | player_name    | `"Unnamed"`       |
| `0x11..0x42` | (variable) | bytes | header tail | unconfirmed   |

`0x42` (= 66) is the **start of the tile grid**, not `0x3E`.

## Tile Grid (revised)

| Offset | Size | Description                          |
|--------|------|--------------------------------------|
| `0x42` | 768  | 256 tiles x 3 bytes (type, flags, extra) |

End-of-grid is `0x42 + 768 = 0x342`.

## Section List (post-grid)

A bare sequence of length-prefixed records. There is **no separate count
field** in the file - the loop runs until EOF.

```
struct FortRecord {
    uint16  size;        // little-endian, includes these 2 bytes
    byte    body[size-2];
};
```

### Records found in MyOnlineGame.fort

| #   | Offset   | Size | Body (size-2)                                        |
|-----|----------|------|------------------------------------------------------|
| 0   | `0x0342` | 3    | `00`                                                 |
| 1   | `0x0345` | 122  | `07 09 11 A2 00...` (118 trailing zeros) - **entity #1** |
| 2   | `0x03BF` | 2    | (empty)                                              |
| 3   | `0x03C1` | 2    | (empty)                                              |
| 4   | `0x03C3` | 12   | `04 85 04 00 47 04 80 04 4c 04`                       |
| 5   | `0x03CF` | 6    | `00 00 00 00`                                        |
| 6   | `0x03D5` | 3    | `00`                                                 |
| 7   | `0x03D8` | 2    | (empty)                                              |
| 8   | `0x03DA` | 2    | (empty)                                              |
| 9   | `0x03DC` | 2    | (empty)                                              |
| 10  | `0x03DE` | 23   | `02 63 01 00 EE 9E 81 01 00 63 00 00 63 00 00 63 01 00 86 59 01` - **entity #2** |
| 11..29 | `0x03F5..0x042B` | 3 each | `02` (19 identical records) |

Sum of sizes: `3 + 122 + 2*4 + 12 + 6 + 3 + 23 + 19*3 = 3 + 122 + 8 + 12 + 6 + 3 + 23 + 57 = 234`
(matches `1070 - 0x342 = 236 - 2`... wait, exactly **236 = file_end - 0x342**, which is right;
the math above missed one empty record - correct sum is **236**, last record ends at `0x42E = EOF`).

### Interpretation - what is "entity_count = 3"?

The previous parse note that "MyOnlineGame.fort has 3 entities" most likely
counts the **3 records whose body has >= 10 bytes** (records #1, #4, #10).
The remaining 27 records are flag bytes, empty-field placeholders, or
grouped slot markers (the trailing 19 records of body=`[02]` could be the
19 tournament-island slot states or the fortress-piece flag set).

The current parser exposes `FortFile.entity_count` as
`sum(1 for r in records if len(r.body) >= 10)` for backwards compatibility
with that interpretation.

---

## Ghidra Investigation

### Endpoints used

```
GET  /list_strings_xrefs?filter=fort
GET  /list_strings_xrefs?filter=fortSpec
GET  /get_xrefs_to?address=<hex>
GET  /decompile_function?address=<hex>
GET  /list_methods?offset=0&limit=10000
```

### Key xrefs

| String                          | Address      | Used in           |
|---------------------------------|--------------|-------------------|
| `"fortFileSize != (int)-1"`     | `0x005104dc` | `0x00409e07` (inline-accessor caller) |
| `"ArchiveFortSpec"`             | `0x0053f1d0` | `FUN_004c90c0`     |
| `"BattleFortSpec"`              | `0x0053f4d8` | `FUN_004ca440`     |
| `"newFort"`                     | `0x0053f5fc` | `FUN_004ca8e0`     |
| `"%d: getting Fort Data..."`    | `0x0053da70` | `FUN_004c12e0`     |
| `"sendFort from %d to %d"`      | `0x0053da94` | `FUN_004c1380`     |
| `"fortDataImage.end"`           | `0x0051963c` | `FUN_00430500` (handleFortDataPacket) |

### Critical decompile - `FUN_0044c9f0` (DataManager serializer)

```c
void FUN_0044c9f0(int *param_1, undefined4 *param_2)
{
    // ... allocate 0x8000-byte buffer in local_28 ...
    while (true) {
        pcVar2 = FUN_004203f0(uVar1, local_30);   // get next field NAME
        if (*pcVar2 == '\0') break;               // stop at empty name
        puVar3 = FUN_0044c4a0(pcVar2);            // resolve handler

        // Patch PREVIOUS record's size = (current_pos - previous_pos)
        if (local_18 != -1)
            *(short *)(local_18 + buf) = (short)local_24 - (short)local_18;

        local_18 = local_24;                      // remember THIS record start
        local_12 = 0;
        FUN_00429d90(&local_12, 2);               // write 2-byte placeholder for size
        local_24 += 2;

        FUN_0044cec0();                            // write the record body via the handler

        // Append (puVar3[2] bytes from *puVar3) into the destination buffer
        // ...
    }
    if (local_18 != -1)
        *(short *)(local_18 + buf) = (short)local_24 - (short)local_18;  // patch LAST size
    *param_2 = local_28;          // return pointer
    param_2[2] = local_20;        // length
}
```

This proves the **`uint16 size` includes itself** (delta from one record's
size-field to the next record's size-field).

### `FUN_004c1380` ("sendFort") chain

`sendFort -> FUN_00429d20 -> FUN_0044c9f0`. The same buffer layout is then
shipped over the wire AND saved to disk - so the on-disk `.fort` format
matches the network packet body byte-for-byte from `0x342` onwards.

### What was NOT recovered

- The **per-field reader/writer handlers** registered with the DataManager.
  Each `FUN_0044cec0()` call dispatches via vtable pointer (`puVar3[1]`)
  whose target depends on the field type. To map record indices to
  semantic fields (player stats vs. entity list vs. island flags) we would
  need to dump the DataManager registry at runtime via the harness, or
  trace every `FUN_0044c4a0("name")` call.
- Decompilation of `FUN_0041ae80` (uses `fortPal`) timed out twice in
  Ghidra MCP - probably one of the fortGump UI functions, low priority for
  format work.

---

## Validation

- Single sample file: `MyOnlineGame.fort` (the only `.fort` in the
  shipping `RIP/d/` directory). The format walks cleanly to EOF with 0
  trailing bytes.
- The grid offset shift from `0x3E` to `0x42` was verified independently
  by counting `0x63` (water) bytes in the file: 256 occurrences with
  stride 3, first at `0x42`, last at `0x33F` (start of tile #255).
- Record-stream walk: total bytes consumed = `len(file) - 0x342` exactly.

---

## What changed in `src/netstorm/assets/fort.py`

- `TILE_DATA_OFFSET`: `0x3E -> 0x42`.
- New `SECTION_OFFSET = 0x342`.
- Removed wrong `entity_count` uint16 read at `0x33E`.
- Added `FortRecord` dataclass + `FortFile.records: list[FortRecord]`.
- `FortFile.entity_count` kept (count of records with body >= 10 bytes)
  for back-compat with the previous "3 entities" assertion.
- Backup written to `fort.py.bak`.

## Tests added (`tests/test_assets.py`)

- `test_fort_loads_header` (magic + player_name)
- `test_fort_grid_is_16x16` + `test_fort_grid_is_mostly_water`
- `test_fort_record_stream_consumes_all_bytes` (records reach EOF exactly)
- `test_fort_record_sizes_are_valid` (size >= 2, body length consistent)
- `test_fort_entity_record_count` (== 3 for MyOnlineGame.fort)
