# NetStorm Engine Flow — Reverse Engineering Report

**Date**: 2026-05-03
**Method**: Ghidra MCP HTTP API (177 endpoints @ port 8089)
**Binar**: netstorm.exe (PE 32-bit, 3977 functii, base 0x00400000, max 0x006091ff, 2.12 MB)
**Compiler**: Microsoft Visual C++ 4.x (matches `ClientMain.cpp` source artifacts)

---

## 1. Game State Machine FUN_0041ae80

`FUN_0041ae80` este **dispatcherul principal de input + GUI + state-machine** (NU doar simplu state switcher) — ~1700 linii de cod, returneaza `int` non-zero cand cere un mode/screen change.

### State variable globala
**`DAT_00564c90`** = `pendState.state` (numele real din assert string @ `0x00518e04`: `"pendState.state == S_INVALID"`).

Confirmat prin xrefs WRITE in toate setterele:
- `FUN_0042fd10` -> `DAT_00564c90 = 0x2A` (S_FORT_CHECK_STATE)
- `FUN_0042fd50` -> `DAT_00564c90 = 0x27` (S_BATT_LOGIN_DENIED?)
- `FUN_0042fd70` -> `DAT_00564c90 = 0x03` (S_FORT_BLANK?)
- `FUN_0042fd80` -> `DAT_00564c90 = 0x06` (S_FORT_RUNNING?)
- `FUN_0042fe00` -> `DAT_00564c90 = 0x01` (S_FORT_INIT?)
- `FUN_0042ffd0` -> `DAT_00564c90 = 0x13`, plus salveaza `DAT_00564cd4 = sid`
- `FUN_0042d630` (network state machine) — 11 WRITEs catre `DAT_00564c90` (mai ales tranzitii META_*)

### Tabelul starilor (din strings @ 0x00518A60+)

Toate prefixate cu `S_` — ordinea sugereaza enumeratie. Patru familii:

**S_FORT_*** (Fortress / Build mode)
- `S_FORT_INIT`, `S_FORT_CREATE`, `S_FORT_BLANK`, `S_FORT_RUNNING`, `S_FORT_CHECK_STATE`, `S_FORT_META_INIT`

**S_BATT_*** (Battle / Multiplayer)
- `S_BATT_INIT`, `S_BATT_CONNECT`, `S_BATT_AWAITING_CONNECT`, `S_BATT_AWAITING_REPLY`, `S_BATT_LOGIN_DENIED`, `S_BATT_REPLY`, `S_BATT_RUNNING`, `S_BATT_SERVER_TAKEOVER`, `S_BATT_AWAITING_RECONNECT_REPLY`, `S_BATT_RECONNECT_REPLY`, `S_BATT_RECONNECT_DENIED`

**S_META_*** (Metaserver / Lobby) — cel mai larg, 14 stari
- `S_META_INIT`, `S_META_UNCONNECTED`, `S_META_ROOT_CONNECT`, `S_META_ROOT_AWAITING_CONNECT`, `S_META_ROOT_AWAITING_REPLY`, `S_META_ROOT_REPLY`, `S_META_CHAL_CONNECT`, `S_META_CHAL_AWAITING_CONNECT`, `S_META_CHAL_AWAITING_REPLY`, `S_META_CHAL_REPLY`, `S_META_CHAL_CONNECTED`, `S_META_CHAL_AWAITING_MOVE_REPLY`, `S_META_CHAL_MOVE_REPLY`, `S_META_CHAL_LOGIN_DENIED`, `S_META_CHAL_CONNECTED_MONITOR`, `S_META_FIND_SERVER`, `S_META_AWAITING_FIND_SERVER`, `S_META_FOUND_SERVER`, `S_META_LAUNCH_SERVER`, `S_META_AWAITING_LAUNCH_SERVER`

**S_GAME_*** (Bootstrap/Intro)
- `S_GAME_INIT`, `S_GAME_INTRO`, `S_GAME_INTRO_DONE`, `S_GAME_STARTUP`

**Plus**: `S_INVALID` (sentinela) si `S_VERSION_DIFF` (mismatch de versiune client/server).

Total: **~37 stari** intr-un singur enum global.

### Globale aditionale legate de stare
- `DAT_00564cd8 / 0xCDC` = stocheaza target server SID (in `FUN_0042ffd0`)
- `DAT_00564d14`, `DAT_00564d1c`, `DAT_00564fec` = sub-state flags resetate la tranzitii FORT
- `DAT_00540a1c` = `inBattleMode`, `DAT_00540a20` = `inFortMode`, `DAT_00540a24` = `inMetamapMode` (din assert @ `0x00519444`)

---

## 2. Update Pipeline (19 functii post-state-machine)

Lista completa functiilor apelate intre `FUN_0041ae80()` si `FUN_00486df0()` cand `iVar4 == 0` si `DAT_0052ea34 < 1`:

| # | Address | Function | Purpose | Category |
|---|---|---|---|---|
| 1 | 0x00433bf0 | FUN_00433bf0(0) | Music/audio cooldown timer (uses CONCAT44 globals @ 0x00564e* + atexit) | audio |
| 2 | 0x004a9c30 | FUN_004a9c30 | Wrapper: `if (DAT_0056f1a4 != 0) FUN_004a9090(0);` — UI hover/cursor poll | input/ui |
| 3 | 0x004333d0 | FUN_004333d0 | Music selector: branches on `DAT_00564e28 == 0x1d / 0x21 / 0xe` (track IDs) | audio |
| 4 | 0x00438e40 | FUN_00438e40 | EMPTY stub (`return;`) — placeholder | --- |
| 5 | 0x004336e0 | FUN_004336e0(0) | Music crossfade / fadeout (large, 0x808 stack — buffers strings) | audio |
| 6 | 0x004eca20 | FUN_004eca20 | Periodic timer `FUN_0048cc10(0,3000)` — random 0..3000ms event scheduler | timer |
| 7 | 0x004ecb30 | FUN_004ecb30 | Calendar/date check (`tm` struct + atexit) — anti-piracy/CD-check tick | misc |
| 8 | 0x00462eb0 | FUN_00462eb0 | EMPTY stub | --- |
| 9 | 0x00449250 | FUN_00449250 | Loops with FS-handler (try/catch) — likely **AI tick** (uses ushort iter on `psVar4`) | AI |
| 10 | 0x00436ca0 | FUN_00436ca0 | Music selector based on `FUN_0048ebe0()` -> `anticipation_mus` vs `ser22_mus` | audio |
| 11 | 0x0043e280 | FUN_0043e280 | Atexit setup + double-precision timer (chat keepalive?) | net? |
| 12 | 0x00442d10 | FUN_00442d10 | Lazy-allocates `0x4000` heap for `DAT_0051c544` (size 0x80x0x80 = 128x128 grid) — **likely terrain/heightmap update** | terrain |
| 13 | 0x004929b0 | FUN_004929b0 | Iterates Gump array `DAT_0056a618`, calls vtable+0 — **GUI gump tick** | gui |
| 14 | 0x00492990 | FUN_00492990 | Iterates `DAT_0056b5b8..0056b6f8` (size 0x140 = 80 ptrs), calls vtable+0x30 — **modal dialogs tick** | gui |
| 15 | 0x004d7350 | FUN_004d7350 | FS-handler wrap, double timer + 4 ints — **HTTP server tick** (matches WinMain `FUN_004b89a0`) | net |
| 16 | 0x004ed5d0 | FUN_004ed5d0 | Iterates `DAT_005b7bb4..005bba30` ptrs (~2400B), calls vtable+0x18 — **kernel/object updates** | kernel |
| 17 | 0x00415b30 | FUN_00415b30 | Compares double timers `DAT_005491f*` vs `DAT_005484a8` and `DAT_00512124 > 0` — **physics/animation tick** | physics |
| 18 | 0x004326a0 | FUN_004326a0 | Trigger when `DAT_00540a20 != 0` (inFortMode) si timer scadut — **fort mode periodic** | fort |
| 19 | 0x00484140 | FUN_00484140 | Iterates `DAT_0050f834 + 0xAC` stride, sanity-checks pairs (firstTempleSid, firstAltarSid, debugFirst*) — **dais/temple consistency** | gameplay |

**Sub-grupare:**
- audio (4): 0x00433bf0, 0x004333d0, 0x004336e0, 0x00436ca0
- gui (2): 0x004929b0, 0x00492990
- net (2): 0x0043e280, 0x004d7350
- AI (1): 0x00449250
- physics (1): 0x00415b30
- terrain (1): 0x00442d10
- gameplay (2): 0x00484140, 0x004326a0
- timer (2): 0x004eca20, 0x004ecb30
- kernel (1): 0x004ed5d0
- input (1): 0x004a9c30
- stub (2): 0x00438e40, 0x00462eb0

---

## 3. Render Pipeline FUN_00486df0

### Top-level flow (decompiled)
```c
void FUN_00486df0(void) {
    if (DAT_0052ea28 == 0 && (DAT_00516af0 & 1)) {
        FUN_004575a0();   // sets DAT_005203cc = 0 (clear flag — minimized state?)
    } else {
        // wait for vsync — busy loop comparing now vs _DAT_00567638 vs _DAT_0052e8e8 (frame budget)
        do { now = FUN_004011b0(local_8); } while (now - last < threshold);
        _DAT_00567638 = now; _DAT_0056763c = ...;

        FUN_004575e0();        // viewport / camera transform setup
        if (DAT_00540a98) FUN_004d6cc0();   // optional overlay
        FUN_004a9d10();        // bounding-box renderer (iterates DAT_0052d598 with /iVar5 stride divisions)
        FUN_004aa190();        // *** SQUID array iterator @ 0x005395dc, stride 0x24 (36B) ***
        FUN_004aa3f0();        // additional sprite layer
        FUN_004aa7a0();        // ...
        FUN_004aa5d0();        // ...
        FUN_004580b0();        // GUI overlays
    }
    // copy 16x DWORD palette/state from DAT_005203a8 -> DAT_00565c18
    for (i=0x10; i; --i) ...
}
```

### Graphics API
- **DirectDraw** confirmed: imports `DirectDrawCreate` (string @ `0x005170c0`), strings include `DirectDrawManager`, `DirectDrawVerify(%d)`, `AdjustDirectDraw`, `queryDirectDraw`, `Failed to set the palette entries in DirectDraw`, fallback DIB section path (`Illegal screen mode: no DirectDraw and no DIB`).
- **GDI**: `BitBlt` imported (single use — likely for windowed/DIB fallback path).
- **No Direct3D** — pure 2D blit pipeline + DIB fallback. Smacker (`SmackSoundOnOff`, `SmackSoundUseDirectSound`) for video playback.

### ISO formula — UNCONFIRMED
- Did **NOT** find direct `(x-y)*32, (x+y)*16` constants in render entry within timeout budget.
- `FUN_004572d0` (called by `FUN_004aa190`) computes:
  - `param_2[0] = __ftol()` (camera_x)
  - `param_2[1] = __ftol()` (camera_y)
  - `param_2[2] = DAT_00516b10 / *(int *)(param_1 + 8) + camera_x`
  - `param_2[3] = DAT_00516b14 / *(int *)(param_1 + 0xc) + camera_y`
  - `DAT_00516b10/b14` = screen width/height (set in WinMain to 0x280=640, 0x1d7=471).
  - `param_1+0x8 / +0xC` = zoom divisor pair (NOT 32/16 directly — varies per LOD level).
- ISO transform likely deeper (in `FUN_004eae20` / `FUN_004eafe0` after `__ftol()`-cascade).

### Squid array iteration — CONFIRMED
`FUN_004aa190` iterates squid array:
```c
for (squid_ptr = DAT_005395dc; squid_ptr < DAT_005395f4 * 0x24 + DAT_005395dc; squid_ptr += 0x24) {
    flags = FUN_004abac0();
    if (flags & 0x800) {
        idx = squid_ptr/0x24;
        if (DAT_0050f288 == 0) FUN_004aa090(idx); else FUN_004a9f80(idx);
    }
    FUN_004eafe0();
}
```
**Confirma struct 36-byte (0x24)**. `DAT_005395f4` = squid count. Flag `0x800` = `VISIBLE` / draw eligible.

---

## 4. Resource Economy

### Globals & Strings
- **Resursa unica = "Money"**. NU exista "psi", "wealth", "energy" — doar Money.
- Configurabilitate (`startMoney`, `aiMoneyRechargeRate`, `moneyCriteria`, `initialMoney`, `~kMoney=%d~`).
- Salvage system: "Salvage gains %d", "Salvage costs %d" (recoup/destroy fortress pieces).
- Cheat: `CheatGetCoolFort` exists.

### Geyser system — sursa de income
- 16 strings cu `Geyser`: `randGeysers`, `predictableGeysers`, `CreateInitialGeysers`, `aiGeyserAttachments`, `geyserMined%d.wav` (sample audio), `~[IfortGump.3] per Geyser` (= "X Money per Geyser" template format).
- Confirma: **economia este Geyser-based mining** — fiecare geyser produce X Money/tick when "attached" to fort/network.
- Genus flag: `gGEYSER` (in assert `s.getGenus()&gGEYSER` @ `0x00541238`).
- Stare: "Cannot make Geyser %d Ineligible", "Made Geyser %d Ineligible", "Trying geyser %d", "Gave up on geyser %d" — sugereaza **state machine per geyser** (CONNECTING / ELIGIBLE / GIVEN_UP / MINED).

### Ipoteza pentru offset Squid
Fara confirmare directa pe offset, dar prin context probabil:
- Squid struct (36B) contine: `pos_x` @ +0x0E (cunoscut din docs), neighbor_flags @ +0x0C, vtable @ +0x00 (call `(**piVar2 + 0x90)()`, `+0x6C`), flags incl bit `0x800` = VISIBLE, bit `0x10000` = GF_DEAD (vezi `g->flags & GF_DEAD`).

---

## 5. Pathfinding

### Algoritm
- Functie de mers: **`FUN_00402750`** (chemata din `FUN_00402100`).
- Aloc lazy: `DAT_0050f308 = FUN_004f1650(0x20000)` (128 KB cost map) si `DAT_0050f30c = FUN_004f1650(0x8000)` (32 KB visited/closed).
- Dimensiunea (32K bytes flag map) sugereaza **128×128 grid heightmap** (`DAT_0051c544` din pasul 12 update tick) — fiecare celula 2B = closed/parent flag.
- `MAX_PATH_LENGTH` constraint (assert `0x0050f3f0`: `nVert < MAX_PATH_LENGTH`) — output array de varfuri.
- Nume sursa cpp: `\Ns\o\path.cpp`, `\Ns\o\pathprocess.cpp`, `\Ns\o\path.h`.
- Algoritmul: **A\*** sau **Dijkstra cu heap** (sterge multiple aloc cu inits puse pe heap nu pe stack — clasic A*). NU am gasit "AStar" string explicit, dar topologia (cost map separata + closed map + MAX_PATH_LENGTH + nVert) este **A* canonical**.

### path.cpp constants
- `pathKILL`, `pathALREADY_DEAD`, `pathLINGER` (return codes — assert @ `0x0052dd1c`)
- `path.isValid()`, `currentPathVert > 0 && currentPathVert == path.nVert` (sanity asserts)
- `Receiving an invalid update for a path process. Client thinks the form is a %s.\n` (network sync — paths sync intre clienti = lockstep mode confirmat).

---

## 6. Save/Load .fort

### Strings & layout
- `loadFort`, `saveFort`, `ReadFort`, `NewFort`, `KillFortDat`, `BuildFortPiece`, `SetFortType`, `coolFort`, `mission.loadFort`, `lastMultiplayerFort`, `lastEditFort`.
- `*FORTLIST*` (sentinel @ `0x0053e1c0`) — contine lista forts cunoscute (catalog file?).
- `myFortData.isOpen()` (assert) — exista clasa `FortData` cu `isOpen()`.
- Format: `"%d: getting Fort Data of %d bytes\n"` (network) si `"sendFort from %d to %d\n"` — fortul se transfera prin retea ca **blob binar de N bytes** (`fortDataImage.end` assert @ `0x0051963c`).
- `fortFileSize != (int)-1` — file I/O standard (open returns -1 on error).
- Constanti UI: `Save Fortress As?`, `Send %s1000~[IfortGump.3]`, `Get 5,000 ~[IfortGump.3]`.

### Reader entry
- `ReadFort` callback xref @ `0x005132c0` (DATA — registered as a **named callback in a string-keyed registry**, classic engine pattern: `ReadFort` -> `FUN_xxx`). NU reusit identificare directa a addr-ului FUN_xxx — necesita lookup in tabela registry (in afara time-budget).
- Salvarea similar: `saveFort` callback @ `0x0042b7a9` xref (DATA registration).

### Layout
- 16×16 grid + record stream — NU am putut rula in detaliu, dar dimensiunile globale + `BuildFortPiece` + serialization via `fortDataImage` blob sugereaza:
  - Header (size word + version)
  - 16x16 cells (fortified piece type per cell)
  - Records list (units/upgrades parametrice).
- Pentru detaliu binar exact: necesita decompile `FUN_xxx` din `loadFort`/`ReadFort` registry handler — task urmator.

---

## Discoveries (5-7 surprize)

### 1. Sigur: **state machine = GUI/event/network MEGA-DISPATCHER, nu un simple switch**
`FUN_0041ae80` are >1700 linii si combina:
- mouse/keyboard events (`PeekMessageA` deja procesat in WinMain, dar el dispecerizeaza eventurile UI prin `DAT_005128**`/`DAT_00512c**` IDs)
- click handlers cu zeci de cazuri (each `if (DAT_005128xx == uVar19) { ... }` reprezinta un buton/control)
- audio feedback inline (`selectTab.wav`, `priestmove.wav`)
- network state checks via `DAT_00564c90`. **NU este "game state switcher" canonical**, ci comutator pentru **starea curenta a clientului (login/lobby/battle/fort)**.

### 2. Cod-sursa partial: numele cpp file-urilor leaked
`ClientMain.cpp`, `path.cpp`, `pathprocess.cpp`, `state.cpp`, `Screen.cpp`, `fortSpec.cpp`, `Gump.cpp`, `dais.cpp`, `zacket.cpp` — toate pastrate in binary (asserts cu `__FILE__` din MSVC). Sub-directorul real: `\Ns\o\` si `\Ns\zacket\` (modulul de packets pentru retea isi are propriul subdir).

### 3. **"zackets" = packet abstraction** custom
Strings precum `*((char *)((char *)zacket+8)) == (char)0xFFFFFFFF` confirma o lib custom UDP packet la `\Ns\zacket\zacket.cpp` cu byte-flag la offset +8. WinMain logheaza `init zackets` la initializare. Folosit in toate State machines BATT_/META_.

### 4. **AI flags ca strings (debug menu sau scriptable AI)**
`FOCUS_ON_THINGS_THAT_ATTACK_BUILDINGS`, `BUILD_BLOCKERS_WHEN_BUILDINGS_HARMED`, `STOP_COLLECTING_FROM_DANGEROUS_GEYSERS` — comportament AI exprimat ca **named flags string-based** (similar cu sistemul de cheats / config console). Se pot toggle din dev console (cheat `CheatGetCoolFort` confirma existenta).

### 5. **Multi-mode boolean assertion: 4 moduri exclusive**
Assert `0x00519444`: `(!inFortMode && !inBattleMode && !inMetamapMode) || (inFortMode && !inBattleMode && !inMetamapMode) || (!inFortMode && inBattleMode && !inMetamapMode) || (!inFortMode && !inBattleMode && inMetamapMode)` — **modul curent este mereu exact unul din 4**: NONE / FORT / BATTLE / METAMAP. Fiecare mod are sub-state-machine proprie (S_FORT_*, S_BATT_*, S_META_*, S_GAME_*).

### 6. **Render: 71 Hz NU e fixed — busy-wait pe vsync software**
In `FUN_00486df0` start: `do { now = ...; } while (now - last < threshold)` cu threshold = `_DAT_0052e8e8`. Frame rate vine din **threshold dynamic citit din config** + sleep busy-loop, NU din DirectDraw flip vsync. Asta explica 71 Hz raportate (1/0.014 ≈ 71). Threshold real ≈ 14ms.

### 7. **Anti-piracy CD-check ramane in tick-loop**
`FUN_00485b20` la pornire face `GetDriveTypeA` pe path de CD si cere "Please insert NetStorm CD". Suplimentar, `FUN_004ecb30` (functia 7 din update pipeline) verifica `tm` struct — posibil **time-bomb / trial expiration** activ in tick-loop.

### 8. **Localizare DE-only switch hardcodat**
`DAT_00565c10 == 2` -> mesaje in germana, alt = engleza. Doar 2 limbi (matches release: EN/DE).

---

## Adrese cheie — cheat sheet

| Symbol | Address | Note |
|---|---|---|
| WinMain | 0x00485B20 | Main entry |
| State machine dispatcher | 0x0041AE80 | NOT pure FSM — mega event handler |
| Tick / frame counter increment | 0x004012D0 | DAT_005484A8/AC (double precision time) |
| Render entry | 0x00486DF0 | DirectDraw + DIB fallback |
| Squid array | 0x005395DC | stride 36 (0x24) |
| Squid count | 0x005395F4 | int |
| Game state global | 0x00564C90 | pendState.state — 37 valori |
| inFortMode | 0x00540A20 | bool |
| inBattleMode | 0x00540A1C | bool |
| inMetamapMode | 0x00540A24 | bool |
| Screen W | 0x00516B10 | 0x280 (640) |
| Screen H | 0x00516B14 | 0x1D7 (471) |
| Frame budget | 0x0052E8E8 | double, ~14ms |
| Camera/viewport transform | 0x004572D0 | thiscall, 4-int output |
| Heightmap grid 128x128 | 0x0051C544 | lazy alloc 0x4000 |
| Pathfinder (A*) | 0x00402750 | aloc 0x20000 + 0x8000 |
| Pathfinder wrapper | 0x00402100 | called by FUN_0047EC60 etc |
| Cost map | 0x0050F308 | 128 KB |
| Closed/visited map | 0x0050F30C | 32 KB |
| Network state machine (UDP) | 0x0042D630 | BATT_/META_ transitions |
| HTTP server tick | 0x004D7350 | optional FUN_004B89A0 |
| AI tick | 0x00449250 | iterates ushort short array |
| Music selector | 0x004333D0 | track ID 0x1D / 0x21 / 0x0E |
| Gump tick (panels) | 0x004929B0 | DAT_0056A618+ |
| Modal dialogs tick | 0x00492990 | DAT_0056B5B8+ |
| `DAT_0050F248` (frame counter) | 0x0050F248 | NOT directly written — derived |
