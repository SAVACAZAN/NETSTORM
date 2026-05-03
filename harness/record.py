"""
Record a game session from a running netstorm.exe process.

Two recording backends:
  memory  — polls game state via ReadProcessMemory at tick boundaries.
             Non-invasive. Use when hook DLL is not needed.
  hook    — injects netstorm_hook.dll; hook pushes one frame per tick over
             a named pipe. More accurate: no polling jitter, exact tick boundary.

Usage:
    python -m harness.record --output session.nsrec [--backend memory|hook]

Memory layout (Virtual Addresses — netstorm.exe is non-ASLR, base 0x400000):
    rng_tls_idx      0x5472F4  CRT TLS index; rand_state = TlsGetValue(idx)+0x14
                               (confirmed: rand()@0x4F17B0 -> _getptd()@0x4F5410 -> [EAX+0x14])
                               Note: external ReadProcessMemory needs TEB TLS slot access.
    game_tick        0x50F248  DAT_0050f248 frame counter; incremented by FUN_004012d0
"""

from __future__ import annotations
import argparse
import io
import time
import zlib
from pathlib import Path
from typing import Protocol

from harness.formats import (
    FRAME_BASE_SIZE, InputBit, RecFlags, RecFrame, RecHeader, Recording,
)
from netstorm.engine.timer import RENDER_RATE_HZ

# --------------------------------------------------------------------------
# Memory layout — Virtual Addresses confirmed via Ghidra RE
# --------------------------------------------------------------------------

OFFSETS: dict[str, int] = {
    # rand_state is in CRT _ptiddata TLS slot; external ReadProcessMemory access
    # requires reading TEB TLS array: teb_base + 0xE10 + tls_index*4 (for index < 64)
    "rng_tls_idx_va":   0x5472F4,   # global storing CRT TLS index for _ptiddata
    "rng_state_offset": 0x14,       # offset of rand_state within _ptiddata
    "game_tick":        0x0050F248, # DAT_0050f248 — frame counter, confirmed via WinMain RE
    # fort_name_ptr: char* at this VA; *ptr = current fort name (no ext, e.g. "battle01").
    # Confirmed via FUN_004ca410 ("getCurFort") assertion *curFort and FUN_004ca6a0 writes here.
    "fort_name_ptr":    0x0053F458,
}


# --------------------------------------------------------------------------
# Backend protocol
# --------------------------------------------------------------------------

class RecorderBackend(Protocol):
    def attach(self, pid: int) -> None: ...
    def read_rng_state(self) -> int: ...
    def read_tick(self) -> int: ...
    def read_map_id(self) -> int: ...
    def read_state_hash(self) -> int: ...
    def detach(self) -> None: ...


# --------------------------------------------------------------------------
# Memory reader backend (Windows ReadProcessMemory, polling)
# --------------------------------------------------------------------------

class MemoryReader:
    def __init__(self) -> None:
        self._handle: int = 0
        try:
            import ctypes
            self._k32 = ctypes.windll.kernel32
        except Exception as e:
            raise RuntimeError("MemoryReader requires Windows") from e

    def attach(self, pid: int) -> None:
        PROCESS_VM_READ = 0x0010
        PROCESS_QUERY_INFORMATION = 0x0400
        self._handle = self._k32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
        )
        if not self._handle:
            raise OSError(f"OpenProcess failed for PID {pid}")

    def _read_va(self, va: int) -> int:
        """Read uint32 at an absolute Virtual Address in the target process."""
        import ctypes
        buf = (ctypes.c_uint32 * 1)()
        read = ctypes.c_size_t(0)
        ok = self._k32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(va),
            buf, 4, ctypes.byref(read)
        )
        return buf[0] if (ok and read.value == 4) else 0

    def read_rng_state(self) -> int:
        # rand_state is in the main thread's TLS slot.
        # TLS index at 0x5472F4; slot value is in the TEB at 0xE10 + index*4.
        # We read the main thread's TEB base from NtQueryInformationThread (complex)
        # so return 0 for now — hook backend has a reliable in-process TlsGetValue path.
        return 0

    def read_tick(self) -> int:
        return self._read_va(OFFSETS["game_tick"])

    def _read_str_ptr(self, ptr_va: int, max_len: int = 64) -> bytes:
        """Read a char* at ptr_va, then dereference and read up to max_len bytes."""
        import ctypes
        ptr = self._read_va(ptr_va)
        if not ptr:
            return b""
        buf = (ctypes.c_char * max_len)()
        read = ctypes.c_size_t(0)
        self._k32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(ptr), buf, max_len, ctypes.byref(read)
        )
        return buf.value  # nul-terminated by c_char array

    def read_map_id(self) -> int:
        # fort_name_ptr (0x53F458) is a char* to the current fort name string.
        # We hash it to a uint16 so it fits the RecHeader.map_id field.
        name = self._read_str_ptr(OFFSETS["fort_name_ptr"])
        return zlib.crc32(name) & 0xFFFF if name else 0

    def read_fort_name(self) -> str:
        name = self._read_str_ptr(OFFSETS["fort_name_ptr"])
        return name.decode("ascii", errors="replace")

    def read_state_hash(self) -> int:
        return 0  # TBD — needs full game state struct VA

    def detach(self) -> None:
        if self._handle:
            self._k32.CloseHandle(self._handle)
            self._handle = 0


# --------------------------------------------------------------------------
# Session recorder — polling backend (MemoryReader)
# --------------------------------------------------------------------------

def record_session(
    pid: int,
    output: Path,
    backend: RecorderBackend | None = None,
    duration_s: float = 0,
) -> Recording:
    if backend is None:
        backend = MemoryReader()

    backend.attach(pid)
    try:
        flags = RecFlags.HAS_RNG
        header = RecHeader(
            flags=flags,
            rng_seed=backend.read_rng_state(),
            map_id=backend.read_map_id(),
            player_id=0,
            tick_rate=RENDER_RATE_HZ,
            start_ts=int(time.time() * 1000),
        )
        rec = Recording(header=header)

        last_tick = -1
        start = time.monotonic()

        print(f"Recording PID {pid} -> {output} (Ctrl+C to stop)")
        try:
            while True:
                current_tick = backend.read_tick()
                if current_tick != last_tick:
                    frame = RecFrame(
                        tick=current_tick,
                        input_mask=InputBit(0),
                        rng_state=backend.read_rng_state(),
                        state_hash=backend.read_state_hash(),
                    )
                    rec.append(frame)
                    last_tick = current_tick
                    if current_tick % 150 == 0:
                        print(f"  tick {current_tick}")

                if duration_s and (time.monotonic() - start) >= duration_s:
                    break
                time.sleep(0.001)

        except KeyboardInterrupt:
            pass

        rec.save(output)
        print(f"Saved {len(rec.frames)} frames -> {output}")
        return rec
    finally:
        backend.detach()


# --------------------------------------------------------------------------
# Hook recorder — push-based via named pipe (HookRecorder)
# --------------------------------------------------------------------------

_PIPE_NAME = rb"\\.\pipe\netstorm_hook"

# ctypes returns c_int by default; INVALID_HANDLE_VALUE is -1 as signed 32-bit.
# We also check 0xFFFFFFFF for safety (unsigned comparison).
def _is_invalid_handle(h: int) -> bool:
    return h == -1 or h == 0xFFFFFFFF or h == 0


def _read_map_id_from_pid(pid: int) -> int:
    """Open the target process read-only, read fort_name_ptr, return crc32 & 0xFFFF."""
    import ctypes
    k32 = ctypes.windll.kernel32
    PROCESS_VM_READ = 0x0010
    h = k32.OpenProcess(PROCESS_VM_READ, False, pid)
    if not h:
        return 0
    try:
        ptr_buf = (ctypes.c_uint32 * 1)()
        read = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(
            h, ctypes.c_void_p(OFFSETS["fort_name_ptr"]), ptr_buf, 4, ctypes.byref(read)
        )
        ptr = ptr_buf[0] if (ok and read.value == 4) else 0
        if not ptr:
            return 0
        str_buf = (ctypes.c_char * 64)()
        k32.ReadProcessMemory(h, ctypes.c_void_p(ptr), str_buf, 64, ctypes.byref(read))
        name = str_buf.value
        return zlib.crc32(name) & 0xFFFF if name else 0
    finally:
        k32.CloseHandle(h)


def hook_record_session(
    pid: int,
    output: Path,
    duration_s: float = 0,
) -> Recording:
    """
    Inject netstorm_hook.dll, connect to its named pipe, and record every
    tick frame the hook pushes. More accurate than polling — no jitter.
    """
    import ctypes
    from harness.hook.inject import inject

    k32 = ctypes.windll.kernel32

    print(f"Injecting hook DLL into PID {pid}...")
    inject(pid)

    # After inject, DLL creates the pipe and waits for a client on a
    # background thread. Connect here — this unblocks the hook thread
    # which then installs the JMP trampoline.
    print("Connecting to hook pipe...")
    pipe_handle = -1
    GENERIC_READ = 0x80000000
    OPEN_EXISTING = 3
    for attempt in range(50):  # retry up to 5 s
        pipe_handle = k32.CreateFileA(
            _PIPE_NAME, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None
        )
        if not _is_invalid_handle(pipe_handle):
            break
        if attempt == 0:
            err = k32.GetLastError()
            print(f"  pipe not ready yet (err={err}), retrying...")
        time.sleep(0.1)

    if _is_invalid_handle(pipe_handle):
        err = k32.GetLastError()
        raise OSError(f"Could not connect to hook pipe (err={err}) — injection may have failed")

    try:
        flags = RecFlags.HAS_RNG
        header = RecHeader(
            flags=flags,
            rng_seed=0,   # filled from the first frame
            map_id=_read_map_id_from_pid(pid),
            player_id=0,
            tick_rate=RENDER_RATE_HZ,
            start_ts=int(time.time() * 1000),
        )
        rec = Recording(header=header)
        first_frame = True
        start = time.monotonic()

        print(f"Recording via hook -> {output} (Ctrl+C to stop)")
        try:
            while True:
                buf = (ctypes.c_uint8 * FRAME_BASE_SIZE)()
                read = ctypes.c_ulong(0)
                ok = k32.ReadFile(
                    pipe_handle, buf, FRAME_BASE_SIZE, ctypes.byref(read), None
                )
                if not ok or read.value != FRAME_BASE_SIZE:
                    print("Pipe closed or read error — stopping.")
                    break

                frame = RecFrame.unpack_from(io.BytesIO(bytes(buf)))

                if first_frame:
                    rec.header.rng_seed = frame.rng_state
                    first_frame = False

                rec.append(frame)

                if frame.tick % 150 == 0:
                    print(f"  tick {frame.tick}")

                if duration_s and (time.monotonic() - start) >= duration_s:
                    break

        except KeyboardInterrupt:
            pass

        rec.save(output)
        print(f"Saved {len(rec.frames)} frames -> {output}")
        return rec

    finally:
        k32.CloseHandle(pipe_handle)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Record netstorm.exe session")
    ap.add_argument("--pid", type=int, help="PID (auto-detect if omitted)")
    ap.add_argument("--output", type=Path, default=Path("session.nsrec"))
    ap.add_argument("--duration", type=float, default=0,
                    help="seconds to record (0 = until Ctrl+C)")
    ap.add_argument("--backend", choices=["memory", "hook"], default="hook",
                    help="memory = ReadProcessMemory polling; hook = DLL pipe (default)")
    args = ap.parse_args()

    pid = args.pid
    if not pid:
        import psutil
        procs = [
            p for p in psutil.process_iter(["pid", "name"])
            if "netstorm" in p.info["name"].lower()
        ]
        if not procs:
            print("netstorm.exe not running")
            return
        pid = procs[0].info["pid"]
        print(f"Auto-detected PID {pid}")

    if args.backend == "hook":
        hook_record_session(pid, args.output, duration_s=args.duration)
    else:
        record_session(pid, args.output, duration_s=args.duration)


if __name__ == "__main__":
    main()
