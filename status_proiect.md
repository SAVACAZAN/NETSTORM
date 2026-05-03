# Status Proiect — NetStorm-Py

Reimplementare Python + raylib a NetStorm: Islands at War (1997, Activision).
Țintă: paritate comportamentală completă cu binarele originale.

---

## Stare Curentă

Data ultimei actualizări: 2026-05-02 (sesiunea 7)

---

## 1. Reverse Engineering — Adrese Confirmate

Toate adresele sunt **Virtual Addresses** în netstorm.exe (non-ASLR, image base `0x400000`).
Confirmate prin Ghidra + verificare binară + test live.

| Simbol | Adresă VA | Detalii |
|---|---|---|
| `FUN_004012d0` (TICK_FUNC) | `0x004012D0` | Per-frame timer, WinMain loop; incrementează frame counter. |
| Frame counter global | `0x0050F248` | `DAT_0050f248` — ~71 fps pe hardware de test. |
| `rand()` | `0x004F23B0` | MSVC LCG: `state = state*214013 + 2531011`, return `(state>>16)&0x7FFF`. Confirmat via Ghidra search `^rand$`. |
| `srand()` | `0x004F23A0` | Scrie seed (re-seeds TLS state). Apelată din `FUN_00430d20` cu seed time-based. |
| TLS index `_ptiddata` | `0x005472F4` | `rand_state = TlsGetValue(*(DWORD*)0x5472F4) + 0x14`. |
| `rand_state` offset | `+0x14` | Offset în `_ptiddata`. |
| `_getptd()` | `0x004F5410` | Returnează ptr la `_ptiddata`. |
| Frame counter | `0x0050F248` | `DAT_0050f248`. |
| Squid array ptr | `0x005395DC` | `DAT_005395DC` — pointer la buffer (32000 × 36 bytes). |
| Squid count | `0x005395F4` | `DAT_005395F4` — 32000. |
| Squid init flag | `0x005395C0` | `DAT_005395C0` — 1 după `FUN_004aaad0`. |
| Squid[i].next_sid | +0x04 | ushort — free-list `getNext()` pointer (= SID+1 pentru squids proaspete). |
| Squid[i].flags | +0x0B | byte: bit0=isFree, bit2=isVoid, bit3=isContained. Confirmat: `FUN_004aaad0`, `FUN_004aae40`. |
| Squid[i].neighbor_flags | +0x0C | ushort — flaguri vecini adiacenți. |
| Squid[i].pos_x | +0x0E | float32. Confirmat: `FUN_004ad490`, `FUN_004aeec0`, `FUN_004aef30`. |
| Squid[i].pos_y | +0x12 | float32. Confirmat: idem. |
| Squid[i].grid_x | +0x16 | short — int(pos_x) truncat. |
| Squid[i].grid_y | +0x18 | short — int(pos_y) truncat. |
| Squid[i].type_id | +0x0A | byte — index în type table (DAT_0051c960, stride 0x1D4). Confirmat: `FUN_004abae0`, `FUN_004ab390`. |
| Squid[i].state | +0x1F | byte — 0=mort/void, 1=slab(<=2.0), 2=mediu(<=4.0), 3=puternic. Echivalent HP în NetStorm. Confirmat: `FUN_004acb00`. |
| Squid[i].owner | +0x20 | byte — player index 0-3. Confirmat: `FUN_0041a720`, `FUN_004d1120`. |
| Squid[i].power_key | +0x21 | signed byte — cheie sortare targeting (lower=mai slab). |
| Squid[i].direction | +0x22 | byte — index variantă sprite/rotație. Confirmat: `FUN_004acb00`. |
| Squid[i].flags2 | +0x23 | byte: bit3=?, bit7=init_done. |
| **NOTE** | +0x06/+0x08 | 4 bytes necunoscuți — zeroed la alocare, pot fi inițializați de vtable ctor. NU există câmp HP separat! |
| Fort name ptr | `0x0053F458` | char* → current fort name (no ext). Confirmat: `FUN_004ca410` assert `*curFort`. |
| Fort mode | `0x0051286C` | 0=MP, 2=edit. |

### Adrese INCORECTE din documente anterioare
- ~~`0x4F39DB`~~ — interior `setvbuf`, nu tick.
- ~~`0x546E50`~~ — nu este tick counter.
- ~~`0x004F17B0`~~ — adresă rand() **incorectă**; corectă: `0x004F23B0`.
- ~~`0x004F17A0`~~ — adresă srand() **incorectă**; corectă: `0x004F23A0`.

### Structura main loop (WinMain `FUN_00485b20`)
```
do {
    FUN_004012d0();   // frame timer + FPS + frame counter
    FUN_00430200();   // input/state copy
    FUN_00437c80();
    FUN_0048eee0();
    FUN_004bff50();
    FUN_004ec4b0();
    if (0.2 < now - last_slow) {  // 5 Hz gating
        FUN_004bfee0();
        last_slow = now;
    }
    FUN_004175e0();
    iVar4 = FUN_0041ae80();   // game state machine
    if (iVar4 == 0) {
        // ~17 funcții update, fără gating
        FUN_00486df0();       // render
    }
} while(true);
// Simularea rulează la fiecare frame (~71fps), fără tick separat.
```

---

## 2. Sistemul de Înregistrare (Harness)

### Componente compilate
| Fișier | Status | Note |
|---|---|---|
| `harness/hook/netstorm_hook.dll` | ✅ | x86, 4KB, KERNEL32 only. Input capture via USER32 dinamic. |
| `harness/hook/inject32.exe` | ✅ | x86, 3KB. Injecție corectă 32-bit din Python 64-bit. |

### HookFrame (22 bytes, packed)
```c
uint32_t tick;        // frame counter din DAT_0050f248
uint32_t input_mask;  // bit0=LBtn, bit1=RBtn, bit2=MBtn (GetAsyncKeyState via USER32)
int16_t  mouse_x;     // GetCursorPos screen X
int16_t  mouse_y;     // GetCursorPos screen Y
uint32_t rng_state;   // TlsGetValue(*(DWORD*)0x5472F4) + 0x14 ÎNAINTE de tick
uint32_t state_hash;  // FNV-1a peste squid array DUPĂ tick
uint16_t net_len;     // 0
```

---

## 3. Stare Module Python

| Modul | Status | Note |
|---|---|---|
| `engine/rng.py` | ✅ | MSVC LCG corect; test known-sequence activat. |
| `engine/timer.py` | ✅ | `RENDER_RATE_HZ=71.0`; `SLOW_UPDATE_RATE_HZ=5.0`. |
| `assets/tarc.py` | ✅ | TAFF v0.2; 258 entries verificate; `get()` decriptează cu `mydoghasfleas`. |
| `assets/shp.py` | ✅ | Decoder 1.10; 130 frames outer + 100 inner groups (3037 frames). |
| `assets/chfnt.py` | ✅ | 256 secțiuni 1.10 individuale; widths uint32 la offset 36. |
| `assets/type_parser.py` | ⚠️ | Parser functional dar fragil (regex clustere poate captura linii greșite; parsează doar primul bloc `{}`). Neconfirmat pe fișiere .type reale. |
| `assets/fort.py` | ✅ | **Format confirmat prin hex-analysis sesiunea 8** (MyOnlineGame.fort). Header 62B; tile grid 16×16×3B la offset 0x3E; player_name cu lungime-prefix la 0x08; entity_count uint16 la 0x33E. Testat pe fișier real. |
| `game/squid.py` | ✅ | Struct 36B; toate offseturile confirmate prin RE sesiunea 7. pos=+0x0E/+0x12, owner=+0x20, state=+0x1F, type=+0x0A. FNV-1a corect. **Nu există câmp HP separat** — sănătatea = state(0-3). |
| `game/world.py` | ⚠️ | spawn/damage folosesc `is_free()` corect. `_update_resources()` = placeholder inventat (+0.01/frame), neconfirmat prin RE. |
| `game/type_registry.py` | ✅ | Încarcă .type din TARC; lookup by name. |
| `render/renderer.py` | ⚠️ | `set_target_fps(71)` corect. Formula ISO `(x-y)*32, (x+y)*16` plauzibilă, neconfirmată RE. Mapping tile_id→frame neconfirmat. |
| `harness/record.py` | ✅ | Hook + memory backends; `fort_name_ptr` la `0x53F458`; `read_map_id()` implementat. |
| `harness/formats.py` | ✅ | NSRC; `HEADER_SIZE=28`; `FRAME_BASE_SIZE=22`. |
| `harness/hook/inject.py` | ✅ | Folosește `inject32.exe` pentru injecție corectă 32-bit. |

### Modificări sesiunea 6
- `harness/replay.py`: stub-urile `_game_tick/pass` și `_compute_state_hash/return 0` înlocuite cu `World.tick()` și `world.state.compute_hash()`. Adăugat `_NullRegistry` (duck-type pentru TypeRegistry fără arhivă).
- `status_proiect.md`: adresă `rand()` corectată (`0x004F17B0` → `0x004F23B0`), adresă `srand()` corectată (`0x004F17A0` → `0x004F23A0`).

### Bug-uri rezolvate în sesiunea 5
- `squid.py`: `compute_hash()` — numpy `uint32*uint32`→`uint64` silențios; fix: Python int `& 0xFFFFFFFF`
- `squid.py`: `is_free()` / `set_free()` adăugate (free bit la +0x0B, RE confirmat)
- `world.py`: `_process_combat` și `spawn_unit` foloseau `get_id==0` ca proxy pentru free; fix: `is_free()`
- `renderer.py`: `set_target_fps(60)` → 71

---

## 4. Rezultate Verificate (Test Live)

### session01.nsrec (meniu)
- 1070 frames / 15 secunde → **~71 fps**
- RNG: `0x3FBD8755` (neschimbat pe meniu)

### session_gameplay.nsrec (gameplay activ)
- 1298 frames / 20 secunde
- **Verificare LCG confirmată:** `0x45524DD5` → `0x3856D2F7` → `0x190D5129` ✅

### Differential Validation — Sesiunea 6 ✅
- `harness/replay.py` conectat la `World` + `GameState` (nu mai e stub).
- RNG parity: **35.59%** (462/1298 ticks) — primele 462 tickuri sunt corecte.
- Hash parity: 100% trivial (toate hash-urile din recording sunt 0 — DLL vechi).
- Prima divergență: **tick 115944** (frame index 462).
- Cauza: jocul apelează `rand()` de **2 ori** pe frame-ul 461 (2 pași LCG exacti).
- Sursă identificată: **mașina de stare de networking** `FUN_0042d630`, cazuri 0x22/0x23 (server discovery UDP broadcast). Aceasta re-probe-uiește la intervale aleatorii.
  - `FUN_00430d20` (apelat din case 0x22): `srand(time)` + `rand()×4` + broadcast → **nu este** sursa celor 2 apeluri (ar face state non-determinist).
  - Cazul 0x23: `rand()×1` când timer expiră → 2 call-uri în total pe recording.
- **Consecință:** Pentru simulare offline (fără networking), RNG-ul nu va fi afectat de aceste apeluri. Paritate RNG 100% posibilă în single-player cu logica de joc corectă.
- **Blocker**: Recording vechi (DLL fără compute_hash) → state_hash=0 peste tot. Nevoie de recording nou cu DLL-ul curent pentru hash comparison.

---

## 5. Priorități Următoare

### Prioritate înaltă
1. ~~**Differential Validation**~~ — ✅ DONE sesiunea 6. Blocat pe recording nou (state_hash=0).
2. ~~**RE squid struct complet**~~ — ✅ DONE sesiunea 7. Toate offseturile confirmate (pos, owner, state, type, flags). Nu există HP clasic.
3. **Recording nou** — rulează DLL-ul curent, captează `state_hash` ≠ 0 pentru hash comparison.

### Prioritate medie
3. ~~**RE format .fort**~~ — ✅ DONE sesiunea 8. Header 62B + grid 16×16×3B confirmat; entity section parțial (entity_count uint16 confirmat, format intern entități necunoscut).
4. **RE entity section** — format intern al entităților la 0x33E (3 entități × ? bytes) neconfirmat.
4. **Pathfinding** — algoritm mișcare pe grid izometric (RE main update loop).
5. **Combat detaliat** — clase atac (Shooter, Bomber), proiectile.

### Prioritate scăzută
6. **UI & Gumps** — meniuri și interfață control.
7. **TypeParser robust** — validare pe fișiere .type reale; regex mai precis.

---

## 6. Fișiere Importante

```
netstorm-py/
  harness/hook/
    netstorm_hook.c     — sursa hook-ului (MSVC x86, no CRT)
    netstorm_hook.dll   — compilat (4KB, kernel32 + USER32 dinamic)
    inject32.c          — sursa injector-ului 32-bit
    inject32.exe        — compilat (3KB)
    inject.py           — wrapper Python
  harness/
    record.py           — recorder (hook + memory backends; fort_name_ptr)
    formats.py          — format .nsrec (HEADER=28B, FRAME=22B)
  src/netstorm/
    engine/rng.py       — MSVC LCG
    engine/timer.py     — 71 Hz
    assets/tarc.py      — TAFF v0.2
    assets/type_parser.py — parser .type (fragil)
    assets/fort.py      — decoder .fort (placeholder)
    game/squid.py       — struct 36B + FNV-1a
    game/world.py       — simulare (resurse = placeholder)
    game/type_registry.py — registry tipuri
    render/renderer.py  — raylib + ISO
  tests/differential/recordings/
    session01.nsrec         — 1070 frames, meniu
    session_gameplay.nsrec  — 1298 frames, gameplay, RNG verificat
```
