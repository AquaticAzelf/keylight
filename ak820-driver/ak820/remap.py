"""The remap layer - it works on the computer, not inside the keyboard.

A low-level keyboard hook watches what is pressed. When a key that has a
macro on it is pressed, the macro is played instead and the key itself is
swallowed. While a macro is being recorded, every key is swallowed so the
recording does not also fire whatever the key does.

This runs on the computer only. The keyboard keeps no macros and is not
changed by it.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

#: The flag the system sets on a key event that the app itself made.
LLKHF_INJECTED = 0x00000010

KEYEVENTF_KEYUP = 0x0002

#: The keys a macro can name, by the letter the user sees.
KEY_NAMES = {
    "Backspace": 0x08, "Tab": 0x09, "Enter": 0x0D, "Shift": 0x10, "Ctrl": 0x11,
    "Alt": 0x12, "Pause": 0x13, "CapsLock": 0x14, "Escape": 0x1B, "Space": 0x20,
    "PageUp": 0x21, "PageDown": 0x22, "End": 0x23, "Home": 0x24,
    "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28, "Insert": 0x2D,
    "Delete": 0x2E, "Win": 0x5B, "Menu": 0x5D, "F1": 0x70, "F2": 0x71,
    "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}
for _index in range(10):
    KEY_NAMES[f"F{_index + 1}"] = 0x70 + _index
for _code in range(0x30, 0x3A):
    KEY_NAMES[chr(_code)] = _code
for _code in range(0x41, 0x5B):
    KEY_NAMES[chr(_code)] = _code
KEY_NAMES.update({
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
})

#: What the key is called, for the list in the app.
KEY_LABELS = {code: name for name, code in KEY_NAMES.items()}


class KbdllHookStruct(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

_lock = threading.RLock()
_mapping: dict[int, str] = {}
_recorder = None
_thread: threading.Thread | None = None
_stopping = threading.Event()
_handle = None

if os.name == "nt":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # The signatures have to be said out loud.  Without them ctypes assumes
    # every argument and every result is a 32-bit int, and a module handle
    # on a 64-bit Windows is far bigger than that: the handle comes back
    # chopped in half, the hook is refused with "the specified module
    # could not be found", and the whole remap layer never goes in.
    _user32.SetWindowsHookExW.restype = wintypes.HHOOK
    _user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                           wintypes.HINSTANCE, wintypes.DWORD]
    _user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    _user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    _user32.CallNextHookEx.restype = ctypes.c_long
    _user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int,
                                       wintypes.WPARAM, wintypes.LPARAM]
    _user32.PeekMessageW.restype = wintypes.BOOL
    _user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                      wintypes.UINT, wintypes.UINT, wintypes.UINT]
    _user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.DispatchMessageW.restype = ctypes.c_long
    _user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE,
                                    wintypes.DWORD, ctypes.c_ulong]
    _kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    _kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
else:  # pragma: no cover - the app only runs on Windows
    _user32 = None
    _kernel32 = None


def play_macro(name: str) -> None:
    """Play a macro once, right now."""
    _play_macro(name)


def key_name(vk: int) -> str:
    """What a key is called."""
    return KEY_LABELS.get(vk, f"Key {vk}")


def _play_macro(name: str) -> None:
    """Play a macro's keys.

    A macro may say how many times it plays and how long it waits
    between the keys. A wait of nothing plays them as fast as the
    computer can manage them.
    """
    from ak820 import macros as macro_store

    try:
        macro = macro_store.load_macro(name)
    except Exception:
        return
    events = macro.get("events", [])
    times = macro.get("repeat", macro_store.DEFAULT_REPEAT)
    delay = macro.get("delay", macro_store.DEFAULT_DELAY_MS)
    if not isinstance(times, int) or times < 1:
        times = macro_store.DEFAULT_REPEAT
    if not isinstance(delay, int) or delay < 0:
        delay = macro_store.DEFAULT_DELAY_MS
    wait = delay / 1000
    for turn in range(times):
        for index, event in enumerate(events):
            vk = event.get("vk")
            if not isinstance(vk, int):
                continue
            down = bool(event.get("down", True))
            flags = 0 if down else KEYEVENTF_KEYUP
            try:
                _user32.keybd_event(vk, 0, flags, 0)
            except Exception:
                return
            if wait and not (turn == times - 1 and index == len(events) - 1):
                time.sleep(wait)


def _hook_proc(code, wparam, lparam):
    """The hook itself. It must never raise."""
    try:
        if code < 0:
            return _user32.CallNextHookEx(None, code, wparam, lparam)
        info = ctypes.cast(lparam, ctypes.POINTER(KbdllHookStruct)).contents
        if info.flags & LLKHF_INJECTED:
            # One of our own keys, played on purpose.
            return _user32.CallNextHookEx(None, code, wparam, lparam)
        down = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
        with _lock:
            recorder = _recorder
            target = _mapping.get(info.vkCode)
        if recorder is not None:
            recorder(info.vkCode, down)
            return 1
        if target:
            if down:
                threading.Thread(target=_play_macro, args=(target,), daemon=True).start()
            return 1
    except Exception:
        pass
    return _user32.CallNextHookEx(None, code, wparam, lparam)


_proc = HOOKPROC(_hook_proc)


def is_active() -> bool:
    """Whether the hook is watching the keyboard."""
    return _thread is not None and _thread.is_alive()


def recording() -> bool:
    """Whether a macro is being recorded."""
    with _lock:
        return _recorder is not None


def install_hook(mapping: dict[int, str] | None = None) -> bool:
    """Start watching the keyboard. Returns whether the hook went in.

    The bindings are kept when the hook is taken out and put back in, so
    switching the layer off and on again does not lose them. Pass
    ``mapping`` to replace them.
    """
    global _thread, _handle
    if os.name != "nt":
        return False
    with _lock:
        if mapping is not None:
            _mapping.clear()
            _mapping.update({int(key): str(value) for key, value in mapping.items()})
    if is_active():
        return True
    _stopping.clear()

    def run() -> None:
        global _handle
        module = _kernel32.GetModuleHandleW(None)
        _handle = _user32.SetWindowsHookExW(WH_KEYBOARD_LL, _proc, module, 0)
        if not _handle:
            return
        message = wintypes.MSG()
        while not _stopping.is_set():
            if _user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                _user32.TranslateMessage(ctypes.byref(message))
                _user32.DispatchMessageW(ctypes.byref(message))
            else:
                time.sleep(0.01)
        if _handle:
            _user32.UnhookWindowsHookEx(_handle)
            _handle = None

    _thread = threading.Thread(target=run, name="ak820-remap", daemon=True)
    _thread.start()
    time.sleep(0.15)
    return is_active()


def uninstall_hook() -> None:
    """Stop watching the keyboard.

    The bindings are left alone: the layer can be switched off and on again
    without losing them.
    """
    global _thread, _handle
    _stopping.set()
    with _lock:
        _recorder = None
    thread = _thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=1.0)
    _thread = None


def set_mapping(mapping: dict[int, str]) -> None:
    """Say which key plays which macro."""
    with _lock:
        _mapping.clear()
        _mapping.update({int(key): str(value) for key, value in mapping.items()})


def get_mapping() -> dict[str, str]:
    """The keys that have a macro on them, by name."""
    with _lock:
        return {key_name(vk): macro for vk, macro in _mapping.items()}


def start_recording(callback) -> bool:
    """Watch the keyboard and report every key to the callback."""
    global _recorder
    if not is_active():
        if not install_hook():
            return False
    with _lock:
        _recorder = callback
    return True


def stop_recording() -> None:
    """Stop watching for a recording."""
    global _recorder
    with _lock:
        _recorder = None
