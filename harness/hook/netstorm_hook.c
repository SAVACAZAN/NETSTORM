/*
 * netstorm_hook.dll — per-tick state capture for differential testing.
 *
 * Build (MSVC 2022, 32-bit target — from repo root or harness/hook/):
 *   cl /nologo /GS- /O1 /c /DWIN32 /I<vc>\include /I<sdk>\um /I<sdk>\shared /I<sdk>\ucrt netstorm_hook.c
 *   link /nologo /DLL /NODEFAULTLIB /ENTRY:DllMain@12 /MACHINE:X86 netstorm_hook.obj kernel32.lib /OUT:netstorm_hook.dll
 * Note: /ENTRY:DllMain@12 (no leading underscore) — linker prepends _ for stdcall.
 *
 * Inject via: python -m harness.hook.inject [--pid PID]
 *
 * Addresses confirmed via Ghidra RE + binary analysis:
 *   TICK_FUNC_VA         0x4012D0  — FUN_004012d0: per-frame timer, called each main-loop
 *                                    iteration; increments frame counter at 0x0050F248.
 *   RNG_TLS_IDX_VA       0x5472F4  — global holding the CRT TLS index for _ptiddata.
 *                                    rand_state = TlsGetValue(*(DWORD*)0x5472F4) + 0x14
 *                                    (confirmed: rand() at 0x4F17B0 reads [EAX+0x14] where
 *                                     EAX = TlsGetValue called via 0x4F5410)
 *   GAME_TICK_VA         0x50F248  — DAT_0050f248: frame counter global
 *
 * TRAMPOLINE_BYTES: must span complete x86 instructions at TICK_FUNC_VA.
 * Standard MSVC prologue: PUSH EBP(1) + MOV EBP,ESP(2) + SUB ESP,N(3-6) = 6-9 bytes.
 * 8 bytes is safe for this function. Verify with ghidra_disassemble if in doubt.
 */

#include <windows.h>
#include <stdint.h>

/* Inline byte-copy — avoids any CRT memcpy dependency */
static void hook_memcpy(void *dst, const void *src, unsigned n) {
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    while (n--) *d++ = *s++;
}

/* ---- RE addresses (Virtual Addresses — non-ASLR binary, base 0x400000) ---- */
#define TICK_FUNC_VA       0x004012D0u /* FUN_004012d0 — per-frame timer, WinMain loop */
#define RNG_TLS_IDX_VA     0x005472F4u /* global: CRT TLS index for _ptiddata */
#define RNG_STATE_OFFSET   0x14u       /* offset of rand_state in _ptiddata */
#define GAME_TICK_VA       0x0050F248u /* DAT_0050f248 — frame counter global */
#define SQUID_INIT_FLAG_VA 0x005395C0u /* DAT_005395C0 — 1 after FUN_004aaad0 runs */
#define SQUID_ARRAY_PTR_VA 0x005395DCu /* DAT_005395DC — ptr to squid array (malloced) */
#define SQUID_COUNT_VA     0x005395F4u /* DAT_005395F4 — total squid count (32000) */
#define SQUID_STRIDE       0x24u       /* sizeof(Squid) = 36 bytes */

/* Number of bytes to copy into trampoline — must end on instruction boundary.
 * Minimum 5 (size of a JMP rel32). Verify with Ghidra disassembly. */
#define TRAMPOLINE_BYTES 8u

/* ---- Named pipe ---- */
#define PIPE_NAME "\\\\.\\pipe\\netstorm_hook"

/* ---- Frame layout — matches harness/formats.py FRAME_BASE_FMT "<IIhhIIH" ---- */
#pragma pack(push, 1)
typedef struct {
    uint32_t tick;
    uint32_t input_mask;
    int16_t  mouse_x;
    int16_t  mouse_y;
    uint32_t rng_state;    /* captured BEFORE this tick's rand() calls */
    uint32_t state_hash;   /* FNV-32 of game state AFTER tick (0 = not captured) */
    uint16_t net_len;
} HookFrame;
#pragma pack(pop)

static HANDLE   g_pipe           = INVALID_HANDLE_VALUE;
static uint8_t *g_trampoline     = NULL;
static uint8_t  g_orig_bytes[TRAMPOLINE_BYTES];
static BOOL     g_hooked         = FALSE;

typedef void (__cdecl *TickFunc)(void);
static TickFunc g_original_tick  = NULL;

/* ---- Input capture — USER32 loaded dynamically (already in process) ---- */
typedef BOOL  (WINAPI *pfn_GetCursorPos)(POINT *);
typedef SHORT (WINAPI *pfn_GetAsyncKeyState)(int);
static pfn_GetCursorPos      g_GetCursorPos      = NULL;
static pfn_GetAsyncKeyState  g_GetAsyncKeyState  = NULL;

static void load_input_apis(void) {
    HMODULE u32 = GetModuleHandleA("user32.dll");
    if (!u32) return;
    g_GetCursorPos     = (pfn_GetCursorPos)    GetProcAddress(u32, "GetCursorPos");
    g_GetAsyncKeyState = (pfn_GetAsyncKeyState) GetProcAddress(u32, "GetAsyncKeyState");
}

/* ---- Helpers ---- */

static uint32_t read_rng_state(void) {
    /* 0x5472F4 holds the CRT TLS index; TlsGetValue returns _ptiddata ptr.
     * rand_state lives at _ptiddata+0x14 — same read the game's rand() uses. */
    DWORD tls_idx = *(volatile DWORD *)RNG_TLS_IDX_VA;
    uint8_t *ptd = (uint8_t *)TlsGetValue(tls_idx);
    if (!ptd) return 0;
    return *(volatile uint32_t *)(ptd + RNG_STATE_OFFSET);
}

/* ---- State hash — FNV-1a over entire squid array (32000 * 36 = ~1.15 MB) ----
 * Squid list confirmed via RE of FUN_004aaad0 (squid.cpp):
 *   alloc: count * 0x24 bytes at *SQUID_ARRAY_PTR_VA
 *   count: SQUID_COUNT_VA (32000)
 *   init flag: SQUID_INIT_FLAG_VA (set to 1 after init)
 * All 36 bytes per squid are meaningful state (zeroed on init, filled during play).
 * ~67 µs per call at 3 GHz, sequential read — cache friendly. */
static uint32_t compute_state_hash(void) {
    if (!*(volatile int32_t *)SQUID_INIT_FLAG_VA) return 0;
    const uint8_t *arr = *(volatile const uint8_t **)SQUID_ARRAY_PTR_VA;
    if (!arr) return 0;
    int32_t n = *(volatile int32_t *)SQUID_COUNT_VA;
    if (n <= 0 || n > 32000) return 0;

    uint32_t h = 2166136261u;           /* FNV-1a offset basis */
    const uint32_t *p = (const uint32_t *)arr;
    int32_t dwords = n * (SQUID_STRIDE / 4);  /* 32000 * 9 = 288000 dwords */
    int32_t i;
    for (i = 0; i < dwords; i++) {
        h ^= p[i];
        h *= 16777619u;                 /* FNV prime */
    }
    return h;
}

/* ---- Hook function (replaces the original tick at call time) ---- */

static void __cdecl hook_tick(void) {
    HookFrame f = {0};

    /* Capture state BEFORE tick executes */
    f.tick      = *(volatile uint32_t *)GAME_TICK_VA;
    f.rng_state = read_rng_state();

    /* Mouse position (screen coords) + button state via USER32 */
    if (g_GetCursorPos && g_GetAsyncKeyState) {
        POINT pt;
        if (g_GetCursorPos(&pt)) {
            f.mouse_x = (int16_t)pt.x;
            f.mouse_y = (int16_t)pt.y;
        }
        if (g_GetAsyncKeyState(VK_LBUTTON) & (SHORT)0x8000) f.input_mask |= 1u;
        if (g_GetAsyncKeyState(VK_RBUTTON) & (SHORT)0x8000) f.input_mask |= 2u;
        if (g_GetAsyncKeyState(VK_MBUTTON) & (SHORT)0x8000) f.input_mask |= 4u;
    } else {
        f.mouse_x = -1;
        f.mouse_y = -1;
    }

    /* Run original tick via trampoline */
    if (g_original_tick) g_original_tick();

    /* state_hash AFTER tick — FNV-1a over squid array */
    f.state_hash = compute_state_hash();

    if (g_pipe != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(g_pipe, &f, sizeof(f), &written, NULL);
    }
}

/* ---- Trampoline install / remove ---- */

static BOOL install_hook(void) {
    uint8_t *target = (uint8_t *)TICK_FUNC_VA;

    /* Allocate RWX memory for the trampoline buffer */
    g_trampoline = (uint8_t *)VirtualAlloc(
        NULL, TRAMPOLINE_BYTES + 5,
        MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!g_trampoline) return FALSE;

    /* Save original bytes */
    hook_memcpy(g_orig_bytes, target, TRAMPOLINE_BYTES);

    /* Build trampoline: [original N bytes] + [JMP back to target+N] */
    hook_memcpy(g_trampoline, target, TRAMPOLINE_BYTES);
    {
        uint8_t *from   = g_trampoline + TRAMPOLINE_BYTES + 5; /* end of jmp instr */
        uint8_t *to     = target + TRAMPOLINE_BYTES;
        g_trampoline[TRAMPOLINE_BYTES]     = 0xE9;             /* JMP rel32 */
        *(int32_t *)(g_trampoline + TRAMPOLINE_BYTES + 1) = (int32_t)(to - from);
    }
    g_original_tick = (TickFunc)g_trampoline;

    /* Patch TICK_FUNC_VA: write JMP to hook_tick (5 bytes) */
    {
        DWORD old;
        VirtualProtect(target, TRAMPOLINE_BYTES, PAGE_EXECUTE_READWRITE, &old);
        target[0] = 0xE9; /* JMP rel32 */
        *(int32_t *)(target + 1) = (int32_t)((uint8_t *)hook_tick - (target + 5));
        /* remaining bytes up to TRAMPOLINE_BYTES are now unreachable padding */
        VirtualProtect(target, TRAMPOLINE_BYTES, old, &old);
    }

    g_hooked = TRUE;
    return TRUE;
}

static void remove_hook(void) {
    if (!g_hooked) return;
    {
        uint8_t *target = (uint8_t *)TICK_FUNC_VA;
        DWORD old;
        VirtualProtect(target, TRAMPOLINE_BYTES, PAGE_EXECUTE_READWRITE, &old);
        hook_memcpy(target, g_orig_bytes, TRAMPOLINE_BYTES);
        VirtualProtect(target, TRAMPOLINE_BYTES, old, &old);
    }
    if (g_trampoline) {
        VirtualFree(g_trampoline, 0, MEM_RELEASE);
        g_trampoline = NULL;
    }
    g_original_tick = NULL;
    g_hooked = FALSE;
}

/* ---- Pipe connect thread (keeps DllMain non-blocking) ---- */

static DWORD WINAPI connect_and_hook(LPVOID param) {
    (void)param;
    /* Block here until harness/record.py connects as a pipe client */
    ConnectNamedPipe(g_pipe, NULL);
    load_input_apis();
    install_hook();
    return 0;
}

/* ---- DLL entry point ---- */

BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID reserved) {
    (void)reserved;
    switch (reason) {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hInst);
        g_pipe = CreateNamedPipeA(
            PIPE_NAME,
            PIPE_ACCESS_OUTBOUND,
            PIPE_TYPE_BYTE | PIPE_WAIT,
            1,      /* max instances */
            65536,  /* out buffer */
            0,      /* in buffer */
            0,      /* default timeout */
            NULL    /* security */
        );
        if (g_pipe == INVALID_HANDLE_VALUE) return FALSE;
        /* Spawn thread so DllMain returns immediately — no deadlock with injector */
        CloseHandle(CreateThread(NULL, 0, connect_and_hook, NULL, 0, NULL));
        break;

    case DLL_PROCESS_DETACH:
        remove_hook();
        if (g_pipe != INVALID_HANDLE_VALUE) {
            DisconnectNamedPipe(g_pipe);
            CloseHandle(g_pipe);
            g_pipe = INVALID_HANDLE_VALUE;
        }
        break;
    }
    return TRUE;
}
