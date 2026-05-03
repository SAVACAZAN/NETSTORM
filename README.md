# understandgame — NetStorm: Islands at War (RE + Reimplementation)

High-fidelity Python + raylib reimplementation of **NetStorm: Islands at War** (1997, Activision).

Goal: behavioral parity with the original binary — exact RNG sequences, float32 math, timings, asset decoding, and gameplay rules.

---

## Ghidra MCP Server

This project uses a custom [Model Context Protocol](https://modelcontextprotocol.io/) server that wraps Ghidra's headless analyzer to expose decompilation and binary analysis tools to Claude Code (or any MCP client).

The server lives at `../ghidra-mcp/server.py` (sibling folder, not included in this repo).

### What it does

Exposes 11 tools that Claude can call to analyze binaries without opening the Ghidra GUI:

| Tool | Description |
|---|---|
| `ghidra_analyze` | Import and fully analyze a binary (run once) |
| `ghidra_list_functions` | List all functions with addresses |
| `ghidra_decompile` | Decompile a function by name or address |
| `ghidra_function_context` | Full context: decompiled C + callers + callees + strings |
| `ghidra_xrefs` | Cross-references to/from a function |
| `ghidra_disassemble` | Raw instruction listing |
| `ghidra_search` | Search functions/symbols by regex |
| `ghidra_strings` | Extract string literals |
| `ghidra_imports` | List Win32 / external imports |
| `ghidra_exports` | List exported symbols |
| `ghidra_defined_data` | Named global variables and structs |

### Prerequisites

- **Ghidra 12.x** — install via [chocolatey](https://community.chocolatey.org/packages/ghidra):
  ```
  choco install ghidra
  ```
  Or download from [ghidra-sre.org](https://ghidra-sre.org/) and unpack anywhere.

- **Java JDK 21** — Ghidra requires JDK 17+. Eclipse Adoptium recommended:
  ```
  choco install temurin21
  ```

- **Python 3.11+** with the `mcp` package:
  ```
  pip install mcp
  ```

### Installation

1. Clone or copy the `ghidra-mcp` folder next to this repo:
   ```
   work/
     netstorm-py/      ← this repo
     ghidra-mcp/       ← MCP server
       server.py
       ghidra_scripts/
   ```

2. Edit the two path constants at the top of `ghidra-mcp/server.py` to match your machine:
   ```python
   GHIDRA_DIR = r"C:\ProgramData\chocolatey\lib\ghidra\tools\ghidra_12.0.4_PUBLIC"
   JAVA_HOME  = r"C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot"
   ```
   Adjust to wherever Ghidra and your JDK are installed.

3. Create a `.mcp.json` file in the repo root (already present, not in git):
   ```json
   {
     "mcpServers": {
       "ghidra": {
         "command": "python",
         "args": ["C:\\path\\to\\ghidra-mcp\\server.py"]
       }
     }
   }
   ```
   Replace `C:\\path\\to\\ghidra-mcp\\server.py` with the actual absolute path.

4. Open Claude Code in this folder — the `ghidra` MCP tools will appear automatically.

### First use

Run analysis once per binary (creates a cached Ghidra project):
```
ghidra_analyze("C:/path/to/netstorm.exe")
```

Then decompile any function:
```
ghidra_function_context("C:/path/to/netstorm.exe", "0x004012D0")
ghidra_search("C:/path/to/netstorm.exe", "rand")
```

Results are cached in `ghidra-mcp/cache/` — subsequent calls to `ghidra_function_context` skip re-analysis and return instantly.

---

## Python Reimplementation

### Setup

```bash
pip install -e ".[harness]"
```

### Run tests

```bash
pytest                            # all tests
pytest tests/test_rng.py          # single module
pytest tests/differential/        # differential parity suite
```

### Record / replay

```bash
# Record a session from running netstorm.exe
python -m harness.record --output tests/differential/recordings/session.nsrec

# Replay and compare tick-by-tick
python -m harness.replay session.nsrec
python -m harness.compare session.nsrec --verbose
```

### Architecture

```
src/netstorm/
  engine/
    rng.py            MSVC LCG — matches netstorm.exe rand() exactly
    timer.py          71 Hz render loop, 5 Hz slow update
  assets/
    tarc.py           .tarc archive loader (TAFF v0.2, AES key: mydoghasfleas)
    shp.py            _shapes.shp sprite decoder (format 1.10)
    chfnt.py          .chfnt bitmap font decoder
    fort.py           .fort fortress file decoder (format confirmed via RE)
    type_parser.py    .type unit definition parser
  game/
    squid.py          Squid struct (36 bytes, all offsets RE-confirmed)
    world.py          Game simulation
    type_registry.py  Unit type lookup
  render/
    renderer.py       raylib + isometric projection

harness/
  formats.py          .nsrec recording format (magic NSRC)
  record.py           Memory reader — polls running netstorm.exe
  replay.py           Drives simulation from a recording
  hook/
    netstorm_hook.c   JMP trampoline DLL (x86, no CRT)
    inject32.c        32-bit injector (called from Python 64-bit)
    inject.py         Python wrapper

tests/
  test_rng.py
  test_formats.py
  differential/
    recordings/       .nsrec ground-truth files (excluded from git)
    test_differential.py
```

### Confirmed RE results

| Symbol | Address | Notes |
|---|---|---|
| Frame tick function | `0x004012D0` | ~71 fps |
| Frame counter | `0x0050F248` | global DWORD |
| `rand()` | `0x004F23B0` | MSVC LCG: `state = state*214013 + 2531011` |
| `srand()` | `0x004F23A0` | seeds TLS slot |
| Squid array ptr | `0x005395DC` | 32000 × 36 bytes |
| Fort name ptr | `0x0053F458` | `char*` current fort name |

---

## Original Binary

`NetStorm RIP/netstorm.exe` — Win32 x86, non-ASLR, image base `0x400000`.  
Not included; required for recording and RE.
