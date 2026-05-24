# Ghidra Project — NetStorm RE

`NetStormRE.zip` contains the full Ghidra 12.0.4 project with **3977 functions** analyzed.

## Extract

```powershell
Expand-Archive NetStormRE.zip -DestinationPath . -Force
```

Produces `NetStormRE.gpr` + `NetStormRE.rep/` (~25 MB uncompressed).

## Open

```powershell
& "C:\path\to\ghidra_12.0.4_PUBLIC\ghidraRun.bat"
# File -> Open Project -> NetStormRE.gpr
```

## Original binary

Not included (Activision copyright). To re-import:

```powershell
& "ghidra_12.0.4_PUBLIC\support\analyzeHeadless.bat" `
    . NetStormRE `
    -import "path\to\netstorm.exe" -overwrite
```

## Key findings (see `../engine_flow.md`, `../status_proiect.md`)

- Game state dispatcher: `FUN_0041AE80` (~37 states, 1700+ lines)
- A* pathfinding: `FUN_00402750` (lockstep multiplayer)
- 19 update pipeline functions mapped
- RNG: MSVC LCG confirmed live
- Squid struct (36B) fully mapped
- Frame counter + 15 Hz tick function (later revised to 71 Hz from recordings)
