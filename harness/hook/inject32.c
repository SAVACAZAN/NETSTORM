/*
 * inject32.c — 32-bit injector helper.
 * Must be compiled as x86 so that GetProcAddress returns the correct
 * 32-bit address of LoadLibraryA (same address space as the target).
 *
 * Usage: inject32.exe <pid> <dll_abs_path>
 * Stdout: module handle (hex) on success.
 * Exit code: 0 = success, 1 = failure.
 *
 * Build (from vcvarsall x86 environment):
 *   cl /nologo /O1 /GS- inject32.c /link /SUBSYSTEM:CONSOLE /NODEFAULTLIB /ENTRY:mainCRTStartup kernel32.lib
 */
#include <windows.h>

static int str_to_int(const char *s) {
    int n = 0;
    while (*s >= '0' && *s <= '9') n = n * 10 + (*s++ - '0');
    return n;
}

static int str_len(const char *s) { int n = 0; while (s[n]) n++; return n; }

static void write_str(HANDLE h, const char *s) {
    DWORD w; WriteFile(h, s, str_len(s), &w, NULL);
}

static void write_hex(HANDLE h, DWORD v) {
    char buf[12]; int i = 0;
    buf[i++] = '0'; buf[i++] = 'x';
    for (int s = 28; s >= 0; s -= 4) {
        int d = (v >> s) & 0xF;
        buf[i++] = d < 10 ? '0'+d : 'A'+(d-10);
    }
    buf[i++] = '\n';
    DWORD w; WriteFile(h, buf, i, &w, NULL);
}

int WINAPI mainCRTStartup(void) {
    HANDLE hout = GetStdHandle(STD_OUTPUT_HANDLE);
    HANDLE herr = GetStdHandle(STD_ERROR_HANDLE);

    /* parse argv manually from GetCommandLineA */
    char *cmd = GetCommandLineA();
    /* skip argv[0] */
    while (*cmd && *cmd != ' ') cmd++;
    while (*cmd == ' ') cmd++;
    /* argv[1] = pid */
    int pid = str_to_int(cmd);
    while (*cmd && *cmd != ' ') cmd++;
    while (*cmd == ' ') cmd++;
    /* argv[2] = dll path */
    const char *dll_path = cmd;
    if (!pid || !*dll_path) {
        write_str(herr, "Usage: inject32.exe <pid> <dll_path>\n");
        ExitProcess(1);
    }

    HANDLE h = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
    if (!h) { write_str(herr, "OpenProcess failed\n"); ExitProcess(1); }

    int dll_len = str_len(dll_path) + 1;
    LPVOID remote_buf = VirtualAllocEx(h, NULL, dll_len, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
    if (!remote_buf) { write_str(herr, "VirtualAllocEx failed\n"); ExitProcess(1); }

    DWORD written;
    WriteProcessMemory(h, remote_buf, dll_path, dll_len, &written);

    FARPROC load_lib = GetProcAddress(GetModuleHandleA("kernel32.dll"), "LoadLibraryA");
    HANDLE thread = CreateRemoteThread(h, NULL, 0, (LPTHREAD_START_ROUTINE)load_lib,
                                       remote_buf, 0, NULL);
    if (!thread) { write_str(herr, "CreateRemoteThread failed\n"); ExitProcess(1); }

    WaitForSingleObject(thread, 5000);
    DWORD exit_code = 0;
    GetExitCodeThread(thread, &exit_code);
    CloseHandle(thread);
    CloseHandle(h);

    if (!exit_code) { write_str(herr, "LoadLibraryA returned NULL\n"); ExitProcess(1); }
    write_hex(hout, exit_code);
    ExitProcess(0);
}
