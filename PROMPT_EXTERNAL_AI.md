# 🤖 Prompt pentru AI extern (Claude.ai, ChatGPT, Kimi, Gemini)

> Copy-paste integral conținutul de mai jos într-o sesiune nouă. AI-ul va primi context complet despre proiectul nostru de RE pe NetStorm și ne poate da idei pe ce să atacăm în continuare.

---

## CONTEXT

Sunt în mijlocul unui proiect de **reverse engineering + reimplementare Python** a jocului **NetStorm: Islands at War (1997, Titanic Studios / Activision)**. Scopul: paritate comportamentală 1:1 cu binarul original `netstorm.exe`.

Am citit despre NetStormHQ (https://www.netstormhq.net/) — o comunitate care deja a făcut RE pe joc și a livrat patch-uri pentru a-l rula pe Windows 10/11 + servere private. Vreau să știu cum aș putea să cooperez cu ei sau să fac mai eficient ce fac ei.

## CE AM DEJA REUȘIT (ultimele 2 zile, foarte multe descoperiri)

### Static analysis prin Ghidra MCP (peste 3977 funcții decompilate)

| Componentă | Status | Detalii |
|---|---|---|
| Game state machine | ✅ Confirmat | `FUN_0041AE80` = mega-dispatcher 1700+ linii cu ~37 stări (S_FORT_*, S_BATT_*, S_META_*, S_GAME_*) |
| State variable globală | ✅ | `DAT_00564C90` (`pendState.state`) |
| Update pipeline post-state-machine | ✅ | 19 funcții mapate cu purpose (input, AI, physics, network, audio) |
| Graphics API | ✅ | DirectDraw 2D pur + DIB fallback (NU D3D, NU GDI) |
| Frame rate | ✅ | 71 Hz busy-wait software (threshold 14ms în `DAT_0052E8E8`) |
| Pathfinding | ✅ | A* canonic la `FUN_00402750` cu lockstep multiplayer; sursa `\Ns\o\path.cpp`; 128KB cost-map + 32KB closed-map pe grid 128×128 |
| Resource economy | ⚠ Parțial | Money + Geyser system identificat (`aiMoneyRechargeRate`, geyserMined wav-uri); semantica per-câmp TBD |
| RNG | ✅ | MSVC LCG `state*214013+2531011`; `rand()` la `0x004F23B0`, verificat live cu 462/1298 ticks parity |
| Squid struct (units/buildings) | ✅ | 36 bytes; toate offset-urile mapate (pos_x/y, owner, state, type_id, flags) |

### Asset extraction (foarte multe ore de muncă)

| Format | Status |
|---|---|
| TARC v0.2 archive | ✅ Decoded — 258 entries, decriptare XOR cheie `mydoghasfleas` |
| `.shp` v1.10 sprites | ✅ **DECODER FIXED 2026-05-03** — vechi era greșit pentru inner groups (genera dungi colorate). Reparat prin Ghidra decompile la `FUN_00465772` (main blit) + `FUN_00465b95` (fast path). Vezi mai jos algoritmul corect. |
| `.chfnt` bitmap fonts | ✅ Decoded |
| `.fort` map files | ✅ Header + grid 16×16×3B la offset `0x42` (fix 2026-05-03 — era `0x3E` în parser-ul vechi). Records post-grid (length-prefixed). |
| `.type` text files (122 unități/clădiri) | ✅ Decoded ca text human-readable. Au refs `"altar01.gif" #15` |
| Sprite name mapping | ✅ **DESCOPERIT 2026-05-03** — Tabel hardcodat la `PTR_DAT_0051c6f8` cu 101 string pointers. Numele "altar01.gif" sunt pure decoration — engine-ul folosește **ordinea fixă** + scanner secvențial pentru magic `"1.10"`. Frame index `#NN` = byte index direct în group. |

### Algoritmul SHP RLE corect (pentru referință)

```python
# Format per row, terminat cu cmd byte == 0:
#   cmd = byte
#   flag = cmd & 1
#   n    = cmd >> 1
#
#   if cmd == 0:               END OF ROW
#   if flag == 0 and n > 0:    FILL — read 1 byte color, paint n pixels
#   if flag == 1 and n == 0:   SKIP — read 1 byte count, advance n_skip transparent pixels
#   if flag == 1 and n > 0:    LITERAL — copy next n bytes verbatim as palette indices
```

## CE AM ÎNCERCAT ȘI A EȘUAT

1. **Render hărți cu sprite-uri reale** — am eșuat pentru că:
   - Vechiul SHP decoder producea noise pentru inner groups (am reparat acum)
   - Paleta de **teren** (isle, water, fringe) NU EXISTĂ în TARC ca `.col`. Doar 26 din 101 grupuri au paletă proprie. Restul folosesc paleta globală GDI/DirectDraw.

2. **Multiple ipoteze RLE incorecte** — am pierdut ~3 ore încercând (count, value), (skip, count, color), 0x80-mask skip etc. înainte să decompilez funcția reală.

3. **Decoder Python pentru post-grid records în .fort** — formatul de framing OK (length-prefixed records), dar ce înseamnă fiecare câmp e necunoscut. Fiecare record ≥10 bytes ar trebui să fie o entitate (geyser, altar, spawn point) cu poziție + tip + owner — dar maparea câmpurilor nu e descoperită.

## CE AVEM SUSPENDAT (incerți, vrem ajutor cu prioritizare)

### Prioritate ÎNALTĂ (blochează progresul)

1. **Paleta globală de teren** — unde e? Probabil:
   - În binar ca tabel de 256×3 bytes
   - Setată via `SetPaletteEntries` Win32 la game init
   - Sau hardcoded ca array literal în cod
   Cum o găsesc rapid?

2. **`.fort` post-grid records semantica per-câmp** — am 30 records în `MyOnlineGame.fort`, 3 mari (≥10 bytes). Cum descopăr ce înseamnă bytes 0-N în fiecare?
   - Hipoteză: prima byte = tip (geyser/altar/spawn), apoi {x:u8, y:u8, owner:u8, ...}
   - Cum verific? Memory scan în jocul real în timp ce încarcă o hartă cu poziții cunoscute?

3. **Tile_id → sprite mapping** — știu numele grupurilor (group 88 = noIsland/water, group 28 = isle), dar nu știu ce sprite frame se folosește pentru `tile_id == 0x9D` într-o hartă. Pe mapele NetStorm, fiecare tile poate avea variante (margine NE, margine SW, geyser pe el, altar pe el). Cum derivez maparea automată?

### Prioritate MEDIE

4. **Render formula ISO** — `(x-y)*32, (x+y)*16` plauzibilă dar neconfirmată. Viewport real folosește divizori dinamici de zoom (`param+0x8`, `param+0xC`). Funcția deep e `FUN_004EAE20`. Cum o decompilez eficient?

5. **Combat & projectiles** — funcțiile shoot/fire/projectile nu sunt clar identificate. Cum le caut sistematic?

6. **UI / Gumps** — sute de cazuri pe `DAT_005128xx` (button IDs) în `FUN_0041AE80`. Cum extrag definițiile UI?

### Prioritate JOASĂ

7. **Recording hash mismatch** — prima divergență la tick 115944 (frame 462). Cauza: 2 apeluri rand() pe frame 461 din mașina de stare network (`FUN_0042d630` cazurile 0x22/0x23 = UDP server discovery). Pentru offline simulation, e irelevant. Dar pentru replay multiplayer perfect, aș vrea să-l fix.

## COMPARAȚIE CU NETSTORMHQ (ce știu despre ei)

NetStormHQ a făcut:
- Reverse engineering pe `netstorm.exe` cu Ghidra/IDA Pro
- Binary patching pentru:
  - Compatibilitate Win10/11
  - Redirecționare requests rețea către servere private
  - Corectare paletă 8-bit pe monitoare moderne
  - Mod fereastră / rezoluții mari
- Wrappers ca `dgVoodoo2` / `cnc-ddraw` pentru DirectDraw → modern
- Recreat protocol UDP pentru servere private (AKA "zackets" — confirm: `\Ns\zacket\zacket.cpp` în binar)

**Diferențierea mea**: ei au făcut **patching minim** ca să meargă jocul original pe modern hardware. Eu fac **reimplementare completă în Python+raylib** pentru paritate 1:1 — diferit scope, dar overlap mare în RE static.

## CE ȚI CER ȚIE (AI-ului din browser)

Dă-mi feedback structurat pe:

### A. Cum atac eficient prioritățile ÎNALTE

Pentru fiecare din punctele 1, 2, 3 de mai sus — care e workflow-ul optim? Am Ghidra MCP cu API HTTP (177 endpoint-uri, decompile/search/xrefs), pot rula scripts Python pe jocul rulând (memory reads), pot face hex analysis pe fișiere binare.

### B. Strategia de cooperare cu NetStormHQ

- Merită să mă alătur Discord-ului lor (https://www.netstormhq.net/)?
- Care e probabilitatea ca ei să aibă deja **maparea sprite_id → group** (lucru pe care eu am descoperit-o cu 6 ore de Ghidra) într-un format public?
- Există **leak-uri de cod sursă** sau **documente tehnice interne** publicate de Titanic ex-employees după 27 ani?

### C. Dacă aș vrea să fac **modding** pe jocul original (nu reimplementare)

- Cea mai bună unealtă pentru re-pack TARC archive cu cheia `mydoghasfleas`?
- Cum aș face un editor de hărți (`.fort`) UI-driven?
- Pot adăuga **unități noi** prin doar editarea `.type` files, sau am nevoie să modific binarul?

### D. Idei out-of-the-box

Există abordări la care nu m-am gândit? Ex:
- Folosirea unui **decompiler ML** (RetDec / tensorflow-based) pentru funcții greu de RE
- **Symbolic execution** cu angr pentru logica de damage/pathfinding
- **Differential testing** unde rulezi jocul original + reimplementarea și diff-ezi outputs
- Reverse-engineering **din asset files** (există vreo metodă să infer structuri din date?)

## TLDR

Am avansat enorm tehnic (decoder SHP fix, mapping nume sprite, parsers TARC/CHFNT/FORT, engine flow documented). Sunt blocat la **paleta de teren globală** (#1) și **semantica records în .fort** (#2). Vreau idei smart să le rezolv fără să mai pierd ore cu ipoteze greșite.

**RĂSPUNDE-MI** structurat pe secțiuni A, B, C, D de mai sus. Dă-mi cele mai bune **5-10 next steps** prioritizate. Spune-mi onest dacă crezi că ar trebui să **renunț la reimplementare** și să cooperez direct cu NetStormHQ pentru un patch comunitar.
