"""Hotkey logic: hold hotkey -> CTRL+T, hold P; release -> release P, CTRL+T."""

import atexit
import queue
import threading
import time

from PySide6.QtCore import QObject, Signal

from . import keys, win32

# Timing (seconds)
KEY_DELAY = 0.020       # gap between injected key events
RELEASE_DELAY = 0.040   # after P is released, before the second CTRL+T
WATCHDOG = 0.100        # how often the held hotkey is re-checked

_PRESS, _RELEASE, _RESET, _SHUTDOWN = range(4)


class KeySender:
    """Injects keys and remembers which ones are down so nothing gets stuck."""

    def __init__(self):
        self._down = set()
        self._lock = threading.Lock()

    def press(self, vk):
        with self._lock:
            self._down.add(vk)
            win32.send_key(vk, False)

    def release(self, vk):
        with self._lock:
            self._down.discard(vk)
            win32.send_key(vk, True)

    def tap_combo(self, mod, vk):
        self.press(mod)
        time.sleep(KEY_DELAY)
        self.press(vk)
        time.sleep(KEY_DELAY)
        self.release(vk)
        time.sleep(KEY_DELAY)
        self.release(mod)

    def release_all(self):
        with self._lock:
            for vk in list(self._down):
                try:
                    win32.send_key(vk, True)
                except Exception:
                    pass
            self._down.clear()


class Engine(QObject):
    held_changed = Signal(bool)
    captured = Signal(int)  # 0 = cancelled

    def __init__(self):
        super().__init__()
        self._hotkey = keys.DEFAULT_HOTKEY
        self._running = False
        self._capturing = False
        self._swallow_up = 0
        self._hook = None
        self._closed = False
        self._queue = queue.SimpleQueue()
        self._keys = KeySender()
        self._worker = threading.Thread(target=self._work, name="FastBreakWorker", daemon=True)
        self._worker.start()
        atexit.register(self._keys.release_all)

    # --- control (main thread) -------------------------------------------

    def start(self, hotkey: int) -> bool:
        self._hotkey = hotkey
        self._running = True
        if not self._apply_hooks():
            self._running = False
            self._apply_hooks()
            return False
        return True

    def stop(self) -> None:
        self._running = False
        self._apply_hooks()
        self._queue.put(_RESET)

    def begin_capture(self) -> bool:
        self._capturing = True
        if not self._apply_hooks():
            self.end_capture()
            return False
        return True

    def end_capture(self) -> None:
        self._capturing = False
        self._apply_hooks()

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._running = self._capturing = False
        self._apply_hooks()
        self._queue.put(_SHUTDOWN)
        self._worker.join(1.0)
        self._keys.release_all()

    def release_keys(self) -> None:
        self._keys.release_all()

    def _apply_hooks(self) -> bool:
        mouse_key = self._hotkey in win32.MOUSE_VKS
        want_kb = self._capturing or (self._running and not mouse_key)
        want_ms = self._capturing or (self._running and mouse_key)
        hook = self._hook
        if hook and (hook.keyboard, hook.mouse) == (want_kb, want_ms):
            return True
        if hook:
            hook.stop()
            self._hook = None
        if want_kb or want_ms:
            hook = win32.InputHook(want_kb, want_ms, self._on_input)
            if not hook.start():
                hook.stop()
                return False
            self._hook = hook
        return True

    # --- hook thread -----------------------------------------------------

    def _on_input(self, vk: int, down: bool) -> bool:
        if self._capturing:
            if not down or vk == win32.VK_LBUTTON:
                return False
            if vk == keys.VK_ESCAPE or keys.valid(vk):
                self._capturing = False
                self._swallow_up = vk
                self.captured.emit(vk if vk != keys.VK_ESCAPE else 0)
            return True
        if not down and vk == self._swallow_up:
            self._swallow_up = 0
            return True
        if self._running and vk == self._hotkey:
            self._queue.put(_PRESS if down else _RELEASE)
        return False

    # --- worker thread ---------------------------------------------------

    def _work(self) -> None:
        held = False
        misses = 0
        while True:
            try:
                cmd = self._queue.get(timeout=WATCHDOG)
            except queue.Empty:
                cmd = None
            try:
                if cmd is None:
                    # Safety net: hotkey released but the key-up was never seen.
                    if not held:
                        continue
                    misses = 0 if win32.is_down(self._hotkey) else misses + 1
                    if misses < 2:
                        continue
                    cmd = _RELEASE

                if cmd == _PRESS:
                    if not held:  # ignores key auto-repeat
                        held = True
                        misses = 0
                        self.held_changed.emit(True)
                        self._keys.tap_combo(keys.VK_LCONTROL, keys.VK_T)
                        time.sleep(KEY_DELAY)
                        self._keys.press(keys.VK_P)
                elif held:
                    self._keys.release(keys.VK_P)
                    time.sleep(RELEASE_DELAY)
                    self._keys.tap_combo(keys.VK_LCONTROL, keys.VK_T)
                    held = False
                    self.held_changed.emit(False)

                if cmd == _SHUTDOWN:
                    self._keys.release_all()
                    return
            except Exception:
                self._keys.release_all()
                if held:
                    held = False
                    self.held_changed.emit(False)
                if cmd == _SHUTDOWN:
                    return
