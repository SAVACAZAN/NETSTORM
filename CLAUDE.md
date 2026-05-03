# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

High-fidelity Python + raylib reimplementation of **NetStorm: Islands at War** (1997, Activision).
Behavioral parity target: timings, RNG sequences, float32 math, UI layout, asset decoding, and gameplay rules must match the original as closely as practical.

The original binaries live at `../netstorm/NetStorm RIP/` — analyzed via the Ghidra MCP server.

## Commands

```bash
pip install -e ".[harness]"          # install with recording deps
pytest                                # run all tests
pytest tests/test_rng.py             # run single module
pytest tests/differential/           # run differential parity suite

python -m harness.record --output tests/differential/recordings/session.nsrec
python -m harness.replay session.nsrec
python -m harness.compare session.nsrec --verbose
```

## Architecture

```
src/netstorm/
  engine/
    rng.py          MSVC LCG — must match original rand() exactly
    timer.py        15 Hz tick loop (tick rate TBD from RE)
  assets/
    tarc.py         .tarc archive loader (format TBD — two layout guesses)
    shp.py          _shapes.shp sprite decoder (format TBD)
    chfnt.py        .chfnt bitmap font decoder (format TBD)
  render/
    renderer.py     raylib renderer + isometric projection
  main.py           entry point

harness/
  formats.py        .nsrec binary recording format (magic NSRC, CRC32 footer)
  record.py         memory-reader backend — polls running netstorm.exe
  replay.py         drives reimplementation from a recording
  compare.py        tick-by-tick diff → DiffReport
  hook/
    netstorm_hook.c JMP trampoline DLL for precise tick interception
    inject.py       CreateRemoteThread + LoadLibrary injector

tests/
  test_rng.py
  test_formats.py
  differential/
    recordings/     .nsrec ground-truth files (not in git — too large)
    test_differential.py  parametric parity suite
```

## Behavioral Parity Rules

- **Float32**: use `numpy.float32` for all game math. Never let Python promote to float64.
- **RNG**: `rng.py` must produce the exact same sequence as netstorm.exe for every seed. Add known-sequence fixtures to `test_rng.py` once confirmed via RE.
- **Tick rate**: `engine/timer.py:RENDER_RATE_HZ` — 71.0 (Confirmed from RE/recordings). Simulation is frame-dependent.
- **Integer overflow**: use `& 0xFFFFFFFF` masks everywhere the original uses `DWORD` arithmetic.

## Reverse Engineering Workflow

Original binary: `C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe`

Ghidra MCP tools available (restart Claude Code if tools not loaded):

```
ghidra_analyze(binary)                              # run once — creates cached project
ghidra_function_context(binary, "name_or_0xaddr")  # decompile + xrefs + strings → cache file
ghidra_search(binary, "pattern")                   # find functions/symbols by regex
ghidra_imports(binary)                             # all Win32 API calls
ghidra_strings(binary)                             # string literals
```

### RE priorities

1. **RNG** — search `0x343FD` or `0x269EC3` (MSVC rand constants). Confirm or correct `rng.py`.
2. **Tick function** — find `timeGetTime`/`GetTickCount` callers → main game loop → tick function address for `harness/hook/netstorm_hook.c`.
3. **RNG global address** — needed for `harness/record.py:OFFSETS["rng_state"]`.
4. **Asset loaders** — search `_shapes.shp`, `.tarc`, `.chfnt` strings → implement decoders.
5. **Game state struct** — needed for `harness/replay.py:_compute_state_hash()`.

### How to fill in memory offsets (record.py)

```python
# 1. Find RNG function via Ghidra:
ghidra_search(netstorm.exe, "rand|srand")
# 2. Decompile to find the global it reads/writes:
ghidra_function_context(netstorm.exe, "0x<rand_addr>")
# 3. Look at defined_data for the global:
ghidra_defined_data(netstorm.exe)
# 4. Put the VA into harness/record.py:OFFSETS["rng_state"]
```

## .nsrec Format

Binary, little-endian. Magic `NSRC`, version 1, CRC32 footer.
See `harness/formats.py` for full spec — the struct layout is the contract between
recorder and replayer, changing it breaks all existing recordings.

## Asset Paths (relative to `../netstorm/`)

| File | Module | Status |
|---|---|---|
| `NetStorm RIP/netstorm.exe` | — | RE target |
| `d/_shapes.shp` | `assets/shp.py` | format TBD |
| `d/*.chfnt` | `assets/chfnt.py` | format TBD |
| `netstorm.tarc` | `assets/tarc.py` | two guesses, unconfirmed |
