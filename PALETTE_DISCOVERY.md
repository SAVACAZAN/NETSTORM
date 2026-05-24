# Palette Discovery — Major Breakthrough

**Date**: 2026-05-03

## TL;DR

Cele **4 palete de teren globale** ale jocului NetStorm SUNT IDENTIFICATE prin nume, dar **fizic LIPSESC** din versiunea RIP a jocului pe care o avem. Trebuie obținute de la NetStormHQ sau de pe CD-ul original.

## Descoperiri

### 1. Cele 4 palete teren — confirmate prin Ghidra
String-uri găsite în netstorm.exe la adrese consecutive:
| Adresă | String | Rol presupus |
|---|---|---|
| `0x0051a1d0` | `windy.col` | Paleta vremii Wind |
| `0x0051a1dc` | `rainy.col` | Paleta vremii Rain |
| `0x0051a1e8` | `thundery.col` | Paleta vremii Thunder |
| `0x0051a1f8` | `sunny.col` | Paleta vremii Sun |

### 2. Tabel pointer-i la `0x0051a1a0`
Confirmat în `FUN_00436960` cu codul:
```c
(&PTR_s_windy_col_0051a1a0)[DAT_0051a19c]
```
unde `DAT_0051a19c` = index 0-3 (selector vreme curent).

### 3. Funcția de încărcare paletă: `FUN_004a98d0("ascendancyPalette", 1)`
Apelată din `FUN_00436960` cu numele paletei dinamic ales după vreme.

### 4. Setter actual: `FUN_00424500`
Conține string-ul `"Failed to set the palette entries in DirectDraw"`. Folosește:
- `DAT_00516b7c` = paleta runtime (256 × 4 bytes RGBA)
- `DAT_005529a0` = paleta cache
- DirectDraw `IDirectDrawPalette::SetEntries` la offset `+0x18` în vtable
- Win32 `CreatePalette` / `SelectPalette` / `RealizePalette` ca fallback

## Probleme

### A. Palete LIPSESC fizic
Verificat:
```bash
$ find NetStorm-Islands-at-War_Win_EN_RIP-Version/ -iname "*.col"
# Niciun rezultat — paletele teren NU sunt pe disc
```

În TARC există 32 `.col` pentru unități (`bulf.col`, `sunarcher.col` etc.) DAR **niciuna din cele 4 palete teren globale**.

### B. Versiunea RIP nu are CD assets
Versiunea pe care o avem este una "RIP" (Removed In-Place — fără cinematice + fără asset-uri de pe CD). Paletele teren sunt probabil pe **Disc 1 / Disc 2 al CD-ului original NetStorm 1997**.

## Soluții

### Opțiunea A — Cere de la NetStormHQ (recomandat, gratuit)
Postează pe Discord-ul lor (https://discord.gg/netstormhq) cu mesaj:

```
Hi! I'm reverse-engineering NetStorm for a Python+raylib reimplementation.
I've identified that the game looks for 4 terrain palettes:
  windy.col, rainy.col, thundery.col, sunny.col
referenced from PTR_DAT_0051a1a0 array in netstorm.exe.

These files are NOT in netstorm.tarc and NOT on the RIP version disc.
Were they on the original 1997 CD? Anyone has copies?

Will trade my SHP decoder fix (verified 100% via Ghidra decompile of
FUN_00465b95) and detailed RE notes in exchange.
```

### Opțiunea B — Procură CD original
- eBay, abandonware sites — caută "NetStorm Islands at War 1997 CD"
- Costă $5-30
- Timp: 1-2 săptămâni livrare

### Opțiunea C — Reconstruct from sprites (dificil dar posibil)
Toate cele 32 palete unități în TARC au header similar (`657a646f44d96173`). Poți încerca:
1. Identifică indexii **comuni** între cele 32 palete unități (acele indices care au RGB **identic** peste toate)
2. Acele indices = paleta GLOBAL/TEREN partajată
3. Indices care diferă = team-color part

Asta poate aproxima paleta globală chiar fără windy.col.

### Opțiunea D — Memory dump live (necesită CD)
Dacă cineva are jocul rulând cu CD, dump `DAT_00516b7c` (paleta runtime de 1024 bytes) imediat după `init palette`.

## Action items

1. **ACUM**: Postez pe Discord NetStormHQ
2. **ÎN PARALEL**: Implementez Opțiunea C (reconstruct from common indices)
3. **DACĂ NU PRIMESC RĂSPUNS**: Cumpăr CD original

## Files referenced

- [find_global_palette.py](find_global_palette.py) — pattern scanner (a generat 62977 candidați false-positive)
- [extracted/palette_candidates/](extracted/palette_candidates/) — top 5 candidați PNG preview
- C:/tmp/setpal.c — decompile FUN_00424500 (palette setter)
- C:/tmp/ascpal.c — decompile FUN_00436960 (ascendancy palette user)
- C:/tmp/loadpal2.c — decompile FUN_0049c1a0 (file loader)
