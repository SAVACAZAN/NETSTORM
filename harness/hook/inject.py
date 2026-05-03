"""
Inject netstorm_hook.dll into a running netstorm.exe process.

Uses the classic CreateRemoteThread + LoadLibraryA technique.
Requires the DLL to be built first: see netstorm_hook.c.

Usage:
    python inject.py [--pid PID]
"""

from __future__ import annotations
import argparse
import ctypes
import ctypes.wintypes
import os
from pathlib import Path

DLL_PATH = Path(__file__).parent / "netstorm_hook.dll"
INJECT32_EXE = Path(__file__).parent / "inject32.exe"


def inject(pid: int, dll_path: Path = DLL_PATH) -> None:
    if not dll_path.exists():
        raise FileNotFoundError(
            f"DLL not found: {dll_path}\n"
            "Build with MSVC x86: see harness/hook/netstorm_hook.c"
        )
    if not INJECT32_EXE.exists():
        raise FileNotFoundError(
            f"inject32.exe not found: {INJECT32_EXE}\n"
            "Build with MSVC x86: cl /nologo /O1 /GS- inject32.c /link /SUBSYSTEM:CONSOLE "
            "/NODEFAULTLIB /ENTRY:mainCRTStartup kernel32.lib"
        )

    import subprocess
    # inject32.exe is a 32-bit process — it gets the correct 32-bit LoadLibraryA address
    # from its own kernel32.dll, avoiding the 64-bit→32-bit address mismatch.
    result = subprocess.run(
        [str(INJECT32_EXE), str(pid), str(dll_path.resolve())],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise OSError(
            f"inject32.exe failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    print(f"Injected {dll_path.name} into PID {pid} (module={result.stdout.strip()})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--dll", type=Path, default=DLL_PATH)
    args = ap.parse_args()

    pid = args.pid
    if not pid:
        import psutil
        procs = [p for p in psutil.process_iter(["pid", "name"]) if "netstorm" in p.info["name"].lower()]
        if not procs:
            print("netstorm.exe not running")
            return
        pid = procs[0].info["pid"]

    inject(pid, args.dll)


if __name__ == "__main__":
    main()
