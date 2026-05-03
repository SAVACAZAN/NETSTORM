# NetStorm RE Toolkit — Scripts & Workflow

> Inventar complet al scripturilor disponibile pentru reverse-engineering NetStorm: Islands at War (1997).
> Status: **2026-05-03**, după sesiunea cu 3 agenți paraleli.

---

## 🎯 Quick Start (cele mai utile)

| Comandă | Ce face |
|---|---|
| `python extract_assets.py` | Extrage TOT din `netstorm.tarc` + `_shapes.shp` + fonturi → `extracted/` |
| Deschide `extracted/catalog.html` în browser | Catalog vizual cu sprite-uri, fonturi, sounds, TARC entries |
| `python -m harness.record --output session.nsrec` | Record live netstorm.exe (frame counter + RNG + state hash) |
| `python -m harness.compare session.nsrec --verbose` | Compară reimplementarea Python vs binarul real |
| `pytest tests/` | Toate testele |

---

## 📦 1. Asset Extraction & Visualization

### `extract_assets.py` ⭐ MASTER SCRIPT
**Locație**: `understandgame-master/extract_assets.py`
**Output**: `understandgame-master/extracted/`

Folosește parserele existente (`tarc.py`, `shp.py`, `chfnt.py`) pentru a extrage:
- **`tarc_dump/`** — toate cele 258 entries din `netstorm.tarc` (cu sub-paths). Decriptate cu cheia XOR `mydoghasfleas`.
- **`sprites_png/`** — primele 100 sprite-uri din `_shapes.shp` ca PNG (cu paletă din `\d\bulf.col` + transparență RLE).
- **`fonts_preview/`** — pentru fiecare din 11 `.chfnt`, un PNG cu alfabet ASCII randat.
- **`wav_listing/listing.json`** — metadata 179 WAV-uri (durată, sample rate, canale). Nu copiază (~50MB).
- **`catalog.html`** — vizualizator vanilla HTML/JS cu 4 tab-uri: TARC tabel + filtru, Sprites grid, Fonts, Sounds cu HTML5 audio.
- **`INDEX.md`** — counts, top 10 mari fișiere, lista mapelor `.fort`, stats extensii.

**Statisticile descoperite**:
- 258 entries TARC (122 `.type`, 39 `.german`, 34 `.english`, 32 `.col`, 23 `.fort`, 2 `.dat`)
- 3126 frames totale în `_shapes.shp` (101 grupuri: 1 outer cu 130 + 100 inner)
- Cea mai mare TARC entry: `\d\help.german` (121,616 B)

---

## 🔧 2. Parsers (Python — în `src/netstorm/assets/`)

| Modul | Format | Status | Note |
|---|---|---|---|
| `tarc.py` | TAFF v0.2 archive | ✅ Stabil | 258 entries, decriptare XOR `mydoghasfleas` |
| `shp.py` | Sprite sheet 1.10 | ✅ Stabil | Decoder RLE, paletă din `bulf.col` |
| `chfnt.py` | Bitmap font | ✅ Stabil | 256 secțiuni 1.10 individuale |
| `fort.py` | Fortăreață map | ✅ **Recent fixed** | **Bug fix 2026-05-03**: grid începe la `0x42`, nu `0x3E`. Format post-grid = stream records prefixate cu length |
| `type_parser.py` | `.type` definitions | ⚠ Fragil | Regex clustere poate prinde linii greșite |

### Parser API common

```python
from src.netstorm.assets.tarc import TarcArchive

archive = TarcArchive.from_path("netstorm.tarc")
print(archive.entries)              # list[(name, offset, size)]
data = archive.get("\\d\\bulf.col") # bytes (decriptate)
```

---

## 🪝 3. Hook + Recorder (Live Capture)

### `harness/hook/netstorm_hook.dll` (4KB, x86, no CRT)
- DLL injectat în `netstorm.exe`
- Hook pe `FUN_004012d0` (tick function)
- Capturează 22 bytes/frame: `tick`, `input_mask`, `mouse_xy`, `rng_state`, `state_hash`, `net_len`

### `harness/hook/inject32.exe` (3KB)
- Injector x86 (apelat din Python 64-bit)
- Strategy: `CreateRemoteThread` + `LoadLibrary`

### `harness/record.py` ⭐
```bash
python -m harness.record --output tests/differential/recordings/session_X.nsrec
```
- Backends: hook (precis) sau memory-reader (fallback poll)
- Citește `fort_name_ptr` la `0x53F458` → identifică harta curentă
- Output: `.nsrec` binary cu magic `NSRC` + CRC32 footer

### `harness/replay.py`
- Driverul reimplementării Python folosind un `.nsrec` ca ground truth
- Conectat la `World` + `GameState` (nu mai e stub din sesiunea 6)

### `harness/compare.py`
```bash
python -m harness.compare session.nsrec --verbose
```
- Diff tick-by-tick: RNG state + state_hash
- Output: `DiffReport` cu prima divergență

---

## 🧪 4. Tests

| Test | Ce verifică |
|---|---|
| `tests/test_rng.py` | MSVC LCG produce aceeași secvență ca `rand()` din binar |
| `tests/test_formats.py` | `.nsrec` round-trip + CRC |
| `tests/test_parsers.py` | TARC, SHP, CHFNT decode corect |
| `tests/test_assets.py` | **+6 teste noi pentru `.fort`** (header, grid, record stream) |
| `tests/differential/test_differential.py` | Parametric parity vs recordings |

### ✅ Status teste (2026-05-03)
- **29/31 pass, 2 skipped** (recordings live)
- **Setup necesar**:
  ```bash
  pip install -e .   # install netstorm-py editable
  ```
- **Junction creat** ca testele să găsească asseturile (testele caută la `9_GAMES/understandgame-master/netstorm/NetStorm RIP/`):
  ```powershell
  New-Item -ItemType Junction `
      -Path "9_GAMES\understandgame-master\netstorm" `
      -Target "9_GAMES\NetStorm-Islands-at-War_Win_EN_RIP-Version"
  ```

---

## 📜 5. PowerShell Dumps (legacy de la sesiunile RE anterioare)

> Nu mai sunt active — au fost folosite la mapping inițial. Le păstrez ca referință istorică.

| Script | RE target |
|---|---|
| `dump_idata.ps1` | Import Address Table |
| `dump_rng.ps1` | Constantele MSVC RNG (`0x343FD`, `0x269EC3`) |
| `dump_call.ps1` | Call sites pentru o funcție specifică |
| `dump_target.ps1` | Generic byte dump la VA |
| `dump_<addr>.ps1` (×13) | Dumps targeted la adrese specifice (FUN_*) |
| `find_15hz*.ps1` | Tick rate hunt (initially crezut 15 Hz, apoi confirmat 71 Hz) |
| `find_rng_*.ps1` | rand/srand call sites |
| `find_tick_*.ps1` | Frame counter references |
| `find_state_*.ps1` | Game state machine access |
| `find_translate_*.ps1` | i18n lookup |
| `find_iat_ref.ps1` | IAT thunks |
| `find_import_str.ps1` | DLL imports + strings |
| `find_ptr_*.ps1` | Pointer init / assign |
| `find_string.ps1` | String search |
| `find_eax_*.ps1` | Trace EAX through tick/state code |
| `find_cmp_42.ps1` | Compare with constant 0x42 |
| `find_sleep.ps1` | Sleep() calls |
| `analyze_calls.ps1` | Call graph analysis |
| `count_imports.ps1` | Import count |
| `read_pe.ps1` | PE header reader |

---

## 🤖 6. Ghidra MCP Toolkit (NEW 2026-05-03)

### Setup
- **Ghidra 12.0.4** la `10_Toolz/tools/ghidra-release/ghidra_12.0.4_PUBLIC/`
- **Plugin GhidraMCP 5.6.0** instalat în `Extensions/Ghidra/`
- **HTTP server** pe `http://127.0.0.1:8089` cu **177 tool-uri**
- **MCP bridge Python** la `10_Toolz/tools/ghidra-mcp/bridge_mcp_ghidra.py`
- **Înregistrat în Claude Code** (`~/.claude.json`)

### Project
- `9_GAMES/understandgame-master/NetStormRE.gpr` — proiect cu `netstorm.exe` analizat (3977 funcții, 14691 simboluri).

### Lansare GUI
```bash
# PowerShell
Start-Process "C:\Kits work\limaje de programare\10_Toolz\tools\ghidra-release\ghidra_12.0.4_PUBLIC\ghidraRun.bat"
```

### Utilizare API direct (curl)
```bash
# Info program
curl http://127.0.0.1:8089/get_current_program_info

# List funcții
curl "http://127.0.0.1:8089/list_functions?offset=0&limit=100"

# Decompile
curl -X POST http://127.0.0.1:8089/decompile_function \
  -H "Content-Type: application/json" \
  -d '{"name":"FUN_0041ae80"}'

# Search funcții
curl "http://127.0.0.1:8089/search_functions?query=rand"

# Search strings
curl "http://127.0.0.1:8089/list_strings?filter=fort"

# Cross references
curl -X POST http://127.0.0.1:8089/get_function_xrefs \
  -H "Content-Type: application/json" \
  -d '{"name":"FUN_004012d0"}'
```

### Utilizare prin Claude Code
După restart Claude Code, simplu spui în chat:
> "decompilează `FUN_0041ae80`"
> "caută toate funcțiile care apelează `rand`"
> "arată-mi xrefs către `0x005395DC`"

Tool-urile MCP se invocă automat: `mcp__ghidra__decompile_function`, `mcp__ghidra__search_functions`, etc.

### Headless Analyzer (CLI, fără GUI)
Pentru re-import sau analiza altor binare (ex: `nsutil.exe`, `r.exe`):
```powershell
$ghidra = "C:\Kits work\limaje de programare\10_Toolz\tools\ghidra-release\ghidra_12.0.4_PUBLIC"
& "$ghidra\support\analyzeHeadless.bat" `
    "C:\Kits work\limaje de programare\9_GAMES\understandgame-master" `
    NetStormRE `
    -import "C:\path\to\binary.exe" `
    -overwrite
# Durează ~3-8 min per binar pentru auto-analiza completă.
```

---

## 📋 7. Workflow recomandat pe sesiuni

### Pentru o nouă sesiune RE (typical flow)

1. **Pornește Ghidra GUI** și deschide `NetStormRE.gpr` → dublu-click pe `netstorm.exe` → activează plugin-ul `GhidraMCPPlugin` în `File → Configure → Miscellaneous`.
2. **Verifică MCP** răspunde:
   ```bash
   curl http://127.0.0.1:8089/get_current_program_info
   ```
3. **Identifică ce vrei să investighezi** — citește `status_proiect.md` să vezi ce-i deja confirmat.
4. **Folosește Claude Code în chat** pentru queries naturale care invocă MCP.
5. **Pentru hot loops** — folosește `curl` direct (mai rapid decât prin chat).
6. **Update `status_proiect.md`** cu adresele/funcțiile noi confirmate.

### Pentru asset extraction
1. `python extract_assets.py` (re-rulează dacă schimbă parserele)
2. Deschide `extracted/catalog.html` în browser
3. Verifică `extracted/errors.log` pentru parser failures

### Pentru differential validation
1. Rulează `netstorm.exe` original
2. `python -m harness.record --output session_NEW.nsrec` (~20s gameplay)
3. `python -m harness.compare session_NEW.nsrec --verbose`
4. Prima divergență → identifică sursa (Ghidra MCP)
5. Fix în `src/netstorm/`, retry

---

## 🚧 8. Status RE — Ce-i confirmat vs Ce lipsește

### ✅ Confirmat (din `status_proiect.md`)
- `WinMain` = `FUN_00485b20`
- Tick func = `FUN_004012d0`
- rand/srand = `0x004F23B0` / `0x004F23A0`
- Frame counter = `0x0050F248`
- Squid array = `0x005395DC` (32000 × 36B), toate offset-urile struct confirmate
- TLS rand state via `_ptiddata + 0x14`
- Game state machine = `FUN_0041ae80`
- Render = `FUN_00486df0`
- Net state machine = `FUN_0042d630`
- TARC v0.2 + SHP 1.10 + CHFNT + FORT — toate parserele funcționează
- RNG MSVC LCG verificat live: 462/1298 ticks parity

### ✅ Confirmat suplimentar (2026-05-03 sesiune Ghidra MCP)
- **Game state machine FUN_0041AE80** — mega-dispatcher 1700+ linii cu ~37 stări (4 familii: `S_FORT_*`, `S_BATT_*`, `S_META_*`, `S_GAME_*`)
- **Variabila globală state**: `DAT_00564C90` (`pendState.state`)
- **19 funcții update** post-state-machine (nu 17) — toate mapate cu purpose în `engine_flow.md`
- **Graphics API**: DirectDraw 2D pur + DIB fallback (NU D3D, NU GDI primary)
- **Frame rate 71 Hz** = busy-wait software (threshold 14ms în `DAT_0052E8E8`), NU vsync DirectDraw
- **Money + Geyser system** — singura resursă (NU psi/wealth). Strings: `aiMoneyRechargeRate`, `geyserMined%d.wav`
- **Pathfinding A\*** = `FUN_00402750` (wrapper `FUN_00402100`), 128KB cost-map + 32KB closed-map (grid 128×128). Sursă: `\Ns\o\path.cpp`. **Lockstep multiplayer**: pathuri sincronizate prin rețea.
- **Custom UDP lib "zackets"** (`\Ns\zacket\zacket.cpp`)
- **AI flags scriptable ca strings** (debug menu): `FOCUS_ON_THINGS_THAT_ATTACK_BUILDINGS`, etc.
- **4 moduri exclusive**: NONE/FORT/BATTLE/METAMAP
- **Localizare**: doar EN/DE
- **Anti-piracy CD-check** + posibil time-bomb în tick-loop (`FUN_004ECB30` cu `tm` struct)
- **`.fort` reader** = blob binar registry-driven (`fortDataImage`, callback string-keyed `ReadFort`/`saveFort`)

### ⚠ Parțial / Lipsă
- **Render formula ISO** `(x-y)*32, (x+y)*16` — neconfirmată direct, viewport folosește divizori dinamici de zoom (`param+0x8`, `param+0xC`); formula reală în `FUN_004EAE20` (peste budget)
- **Resource economy semantica per-câmp** — Money + Geyser identificate, dar offset Squid `+0x06`/`+0x08` semantica TBD
- **Combat detaliat** — clase atac (Shooter, Bomber), proiectile
- **`.fort` entity per-record semantics** — record stream framing OK, dar ce înseamnă fiecare câmp e TBD (necesită runtime trace al `FUN_0044c4a0`)
- **TypeParser robust** — neconfirmat pe `.type` reale

---

## 🎯 9. Priorități următoare (ordonate)

1. **Recording nou** cu DLL curent → `state_hash ≠ 0` pentru hash comparison
2. **Render formula ISO** — confirmă `(x-y)*32, (x+y)*16` via decompile `FUN_004EAE20` (entry deep into render)
3. **Money + Geyser semantics** — runtime trace al state machine per Geyser (CONNECTING/ELIGIBLE/MINED) + variabila globală Money
4. **Combat** — proiectile + damage application (search funcții cu "shoot", "fire", "projectile")
5. **`.fort` per-record semantics** — runtime trace `FUN_0044c4a0("nume_camp")` din DataManager registry
6. **UI/Gumps** — sute de cazuri pe `DAT_005128xx` (button IDs) în FUN_0041AE80
7. **Combat clase atac** — Shooter, Bomber type definitions în .type files

---

## 📁 10. File Layout Reference

```
understandgame-master/
├── SCRIPTS.md                ← acest fișier
├── CLAUDE.md                 ← guidance pentru Claude Code
├── GEMINI.md                 ← guidance pentru Gemini
├── README.md
├── status_proiect.md         ← stare detaliată RE (UPDATE-ABLE)
├── planul1.md
├── raspuns.md
├── pyproject.toml            ← Python deps
├── decodare.py               ← (legacy) brute-force XOR pe TARC
├── extract_assets.py         ← MASTER asset extractor (NEW 2026-05-03)
├── fort_entity_spec.md       ← RE report .fort records (NEW 2026-05-03)
│
├── extracted/                ← OUTPUT extract_assets.py (NEW 2026-05-03)
│   ├── catalog.html          ← vizualizator
│   ├── INDEX.md
│   ├── errors.log
│   ├── tarc_dump/            ← 258 entries
│   ├── sprites_png/          ← 100 sprite PNGs
│   ├── fonts_preview/        ← 11 font alphabets
│   └── wav_listing/listing.json
│
├── src/netstorm/
│   ├── main.py
│   ├── engine/
│   │   ├── rng.py            ← MSVC LCG ✅
│   │   └── timer.py          ← 71 Hz ✅
│   ├── assets/
│   │   ├── tarc.py           ← TAFF v0.2 ✅
│   │   ├── shp.py            ← v1.10 ✅
│   │   ├── chfnt.py          ← BitmapFontData ✅
│   │   ├── fort.py           ← FIXED 2026-05-03 ✅
│   │   ├── fort.py.bak       ← backup pre-fix
│   │   └── type_parser.py    ⚠
│   ├── game/
│   │   ├── squid.py          ← struct 36B ✅
│   │   ├── world.py          ⚠ resources placeholder
│   │   └── type_registry.py  ✅
│   ├── render/
│   │   └── renderer.py       ⚠ ISO formula neconfirmată
│   └── ui/
│
├── harness/
│   ├── formats.py            ← .nsrec ✅
│   ├── record.py             ✅
│   ├── replay.py             ✅
│   ├── compare.py            ✅
│   └── hook/
│       ├── netstorm_hook.c
│       ├── netstorm_hook.dll ✅
│       ├── inject32.c
│       ├── inject32.exe      ✅
│       └── inject.py
│
├── tests/
│   ├── test_rng.py
│   ├── test_formats.py
│   ├── test_parsers.py
│   ├── test_assets.py        ← +6 teste fort 2026-05-03
│   └── differential/
│       └── recordings/
│           ├── session01.nsrec
│           └── session_gameplay.nsrec
│
└── (legacy PS scripts)       ← dump_*.ps1, find_*.ps1
```

---

## 📚 11. Referințe externe

- Format `.tarc` (TAFF v0.2) — proprietary Titanic Studios. Magic `TAFF v0.2\x1A`. Header 0x2C bytes. Decriptare XOR cyclic cu `mydoghasfleas`.
- Format `.shp` v1.10 — proprietary. Magic `1.10` ASCII. Offset table de uint64 (offset:uint32, ?:uint32).
- Format `.chfnt` (BitmapFontData) — magic `BitmapFontData\x1A`. 256 secțiuni glyph cu widths uint32 la offset 36.
- Format `.fort` — header 62B, grid 16×16×3B la `0x42`, post-grid = length-prefixed records (size:u16 LE include cei 2 bytes).
- MSVC RNG LCG — `state = state*214013 + 2531011`; `rand() = (state>>16) & 0x7FFF`.

---

## 🔥 12. Comenzi cheat-sheet

```bash
# === ASSET EXTRACTION ===
cd "c:/Kits work/limaje de programare/9_GAMES/understandgame-master/understandgame-master"
python extract_assets.py
start extracted/catalog.html      # Windows → deschide în browser default

# === GHIDRA ===
# Pornește Ghidra GUI
Start-Process "c:\Kits work\limaje de programare\10_Toolz\tools\ghidra-release\ghidra_12.0.4_PUBLIC\ghidraRun.bat"

# Test MCP
curl http://127.0.0.1:8089/get_current_program_info

# Decompile rapid
curl -X POST http://127.0.0.1:8089/decompile_function -H "Content-Type: application/json" -d '{"name":"FUN_004012d0"}'

# === RECORDING ===
# Pornește netstorm.exe original, apoi:
python -m harness.record --output tests/differential/recordings/session_$(date +%Y%m%d_%H%M).nsrec

# === DIFFERENTIAL ===
python -m harness.compare tests/differential/recordings/session_gameplay.nsrec --verbose

# === TESTS ===
pytest                               # toate
pytest tests/test_rng.py             # un singur fișier
pytest tests/differential/           # parity suite
```

---

**Last update**: 2026-05-03 (sesiunea cu 3 agenți paraleli + Ghidra MCP setup)
**Maintainer**: actualizează acest file la fiecare descoperire majoră în RE.
