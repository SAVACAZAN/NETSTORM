# NetStorm-Py Project Context

A high-fidelity Python + raylib reimplementation of **NetStorm: Islands at War** (1997, Activision).

## Project Goal
Behavioral parity with the original game. This includes exact timings, RNG sequences, float32 math results, UI layout, asset decoding, and gameplay rules.

## Core Technologies
- **Language:** Python 3.11+
- **Rendering:** [raylib-py](https://github.com/overte/raylib-py) (raylib >= 5.0.0)
- **Math:** `numpy` (specifically `float32` for parity)
- **Binary Parsing:** `construct` (for asset formats)
- **Testing:** `pytest` + `pytest-benchmark`

## Project Structure
- `src/netstorm/`: Core game engine and logic.
  - `assets/`: Asset decoders (`.tarc`, `.shp`, `.chfnt`).
  - `engine/`: Low-level systems (RNG, Timer).
  - `render/`: raylib renderer and isometric projection logic.
  - `game/`: Game rules and state management.
  - `ui/`: User interface components.
- `harness/`: Tools for reverse engineering and parity validation.
  - `record.py`: Records session state from `netstorm.exe` via DLL injection (`netstorm_hook.c`).
  - `replay.py`: Drives the Python implementation using an `.nsrec` recording.
  - `compare.py`: Diffs Python state against recordings.
- `tests/`:
  - `differential/`: Parity tests comparing behavior against `.nsrec` ground truth.

## Technical Details

### RNG (MSVC CRT)
The game uses the standard MSVC LCG (Linear Congruential Generator):
- **Multiplier:** `214013` (0x343FD)
- **Addend:** `2531011` (0x269EC3)
- **Sequence:** `state = (state * 214013 + 2531011) & 0xFFFFFFFF; result = (state >> 16) & 0x7FFF;`

### Asset Formats
- **TAFF (v0.2):** Titanic Archive File Format. Used in `netstorm.tarc`.
  - Header: `TAFF v0.2\x1a` (10 bytes) + 6 bytes padding.
  - Table based with relative offsets to data block.
- **SHP (1.10):** Hierarchical RLE sprites.
  - Command Byte: `bit 0` (1 = Draw, 0 = Skip), `cmd >> 1` = Count - 1.
  - Draw: Consume `count` bytes from stream.
  - Skip: Move `count` pixels horizontally.
- **CHFNT:** Bitmap fonts containing an embedded SHP 1.10 container for glyphs.

### Isometric Projection
- **Grid:** 64x32 pixels (logical).
- **Projection:**
  ```python
  sx = (tile_x - tile_y) * 32
  sy = (tile_x + tile_y) * 16
  ```

### Differential Testing (.nsrec)
Recordings capture input masks, RNG state, and game tick counters from the original game using `netstorm_hook.dll`.

## Documentation & Progress (Romanian)
The project includes several detailed status and planning files in Romanian:
- `planul1.md`: The multi-phase implementation roadmap.
- `status_proiect.md`: Detailed progress report, including RNG confirmation and asset decoding breakthroughs.
- `raspuns.md`: Log of the current decryption attempts on `.english` files.

## Decryption Breakthrough
All encrypted assets (`.type`, `.fort`, `.english`, and `.cfg` files) use a fixed XOR key:
- **Key:** `mydoghasfleas` (13 characters)
- **Algorithm:** Simple repeating XOR.
- **Verification:** Successfully decrypted `tutorial1.english`, `altar.type`, and `setup.cfg`.

## Building and Running
```bash
# Install
pip install -e ".[harness,dev]"

# Run Reimplementation
python -m netstorm.main

# Compare Parity
ns-compare tests/differential/recordings/session.nsrec
```

## Development Rules
1. **Float32 Only:** Use `np.float32` for all physics/gameplay math.
2. **RNG Integrity:** Never call `random.random()`. Use `netstorm.engine.rng.RNG`.
3. **Tick Rate:** Fixed at 15 Hz (`GameTimer`).
4. **Style:** Follow Ruff/Black (line-length 100).
