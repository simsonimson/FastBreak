"""Thin ctypes layer: low-level input hooks, SendInput and key names."""

import ctypes
import threading
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t

# Tag for events injected by FastBreak, so the hooks can ignore them.
MAGIC = 0x46425246  # "FBRF"

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0100, 0x0101, 0x0104, 0x0105

VK_LBUTTON, VK_RBUTTON, VK_MBUTTON, VK_XBUTTON1, VK_XBUTTON2 = 0x01, 0x02, 0x04, 0x05, 0x06
MOUSE_VKS = frozenset({VK_LBUTTON, VK_RBUTTON, VK_MBUTTON, VK_XBUTTON1, VK_XBUTTON2})

_MOUSE_MSGS = {
    0x0201: (VK_LBUTTON, True), 0x0202: (VK_LBUTTON, False),
    0x0204: (VK_RBUTTON, True), 0x0205: (VK_RBUTTON, False),
    0x0207: (VK_MBUTTON, True), 0x0208: (VK_MBUTTON, False),
    0x020B: (VK_XBUTTON1, True), 0x020C: (VK_XBUTTON1, False),
}

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC_EX = 4


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.UnhookWindowsHookEx.restype = wt.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = wt.BOOL
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostThreadMessageW.restype = wt.BOOL
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wt.UINT
user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
user32.MapVirtualKeyW.restype = wt.UINT
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetKeyNameTextW.argtypes = [wt.LONG, wt.LPWSTR, ctypes.c_int]
user32.GetKeyNameTextW.restype = ctypes.c_int
kernel32.GetCurrentThreadId.restype = wt.DWORD
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HMODULE


def send_key(vk: int, up: bool) -> None:
    """Inject one key event by scan code (works in games reading raw input)."""
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX)
    flags = KEYEVENTF_SCANCODE
    if scan & 0xFF00 in (0xE000, 0xE100):
        flags |= KEYEVENTF_EXTENDEDKEY
    if up:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, scan & 0xFF, flags, 0, MAGIC)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def is_down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def key_name_text(vk: int) -> str:
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX)
    if not scan:
        return ""
    lparam = ((scan & 0xFF) << 16) | ((1 << 24) if scan & 0xFF00 else 0)
    buf = ctypes.create_unicode_buffer(32)
    n = user32.GetKeyNameTextW(lparam, buf, 32)
    return buf.value[:n]


def set_app_id(app_id: str) -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
    except Exception:
        pass


class InputHook(threading.Thread):
    """Global low-level keyboard and/or mouse hook on its own message loop.

    handler(vk, down) runs on the hook thread and must return quickly.
    Returning True swallows the event.
    """

    def __init__(self, keyboard: bool, mouse: bool, handler):
        super().__init__(name="FastBreakHook", daemon=True)
        self.keyboard = keyboard
        self.mouse = mouse
        self.ok = False
        self._handler = handler
        self._tid = 0
        self._ready = threading.Event()
        self._kb_proc = HOOKPROC(self._on_keyboard)
        self._ms_proc = HOOKPROC(self._on_mouse)

    def start(self) -> bool:
        super().start()
        self._ready.wait(2.0)
        return self.ok

    def stop(self) -> None:
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        self.join(1.0)

    def run(self) -> None:
        self._tid = kernel32.GetCurrentThreadId()
        hmod = kernel32.GetModuleHandleW(None)
        hooks = []
        try:
            if self.keyboard:
                hooks.append(user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, hmod, 0))
            if self.mouse:
                hooks.append(user32.SetWindowsHookExW(WH_MOUSE_LL, self._ms_proc, hmod, 0))
            self.ok = bool(hooks) and all(hooks)
            self._ready.set()
            if self.ok:
                msg = wt.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    pass
        finally:
            for h in hooks:
                if h:
                    user32.UnhookWindowsHookEx(h)
            self._ready.set()

    def _on_keyboard(self, code, wparam, lparam):
        try:
            if code == 0:
                k = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if k.dwExtraInfo != MAGIC:
                    down = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    if self._handler(k.vkCode, down):
                        return 1
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def _on_mouse(self, code, wparam, lparam):
        try:
            if code == 0 and wparam in _MOUSE_MSGS:
                m = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if m.dwExtraInfo != MAGIC:
                    vk, down = _MOUSE_MSGS[wparam]
                    if vk == VK_XBUTTON1 and (m.mouseData >> 16) & 0xFFFF == 2:
                        vk = VK_XBUTTON2
                    if self._handler(vk, down):
                        return 1
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)
