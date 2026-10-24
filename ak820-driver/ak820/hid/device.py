"""Device discovery and access for the AK820's vendor HID collection."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import windows as w

_VIDPID_RE = re.compile(r"vid_([0-9a-f]{4})&pid_([0-9a-f]{4})", re.IGNORECASE)
_MI_RE = re.compile(r"&mi_(\d+)", re.IGNORECASE)

AK820_VID = 0x320F
AK820_PID = 0x505B
AK820_USAGE_PAGE = 0xFF1C
AK820_INTERFACE = 1
PACKET_SIZE = 64


class HidError(RuntimeError):
    """A HID operation failed. ``code`` is the Win32 error code, when there was one."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class HidPath:
    """One HID collection of a device, with the facts needed to identify it."""

    path: str
    vid: int
    pid: int
    usage_page: int
    usage: int
    interface: int


def list_interface_paths(vid: int, pid: int) -> list[str]:
    """Raw interface paths of a device, without opening any of them.

    Works even when another program is holding the device, so it can be used to
    tell "not plugged in" apart from "someone else is using it".
    """
    found = []
    for path in w.enumerate_hid_interface_paths():
        match = _VIDPID_RE.search(path)
        if not match:
            continue
        if (int(match.group(1), 16), int(match.group(2), 16)) == (vid, pid):
            found.append(path)
    return found


def find_devices(vid: int, pid: int, usage_page: int | None = None) -> list[HidPath]:
    """Every collection of a device, optionally filtered by usage page.

    A collection that cannot be opened (the OS keeps the keyboard and mouse
    collections of a composite keyboard locked) is left out, so an empty result
    with a non-empty :func:`list_interface_paths` means the device is busy.
    """
    found: list[HidPath] = []
    for path in list_interface_paths(vid, pid):
        info = w.collection_info(path)
        if info is None:
            continue
        if usage_page is not None and info.usage_page != usage_page:
            continue
        match = _MI_RE.search(path)
        found.append(
            HidPath(
                path=path,
                vid=vid,
                pid=pid,
                usage_page=info.usage_page,
                usage=info.usage,
                interface=int(match.group(1)) if match else 0,
            )
        )
    found.sort(key=lambda d: (d.interface, d.path))
    return found


def find_ak820() -> HidPath | None:
    """The AK820's vendor collection, or ``None`` if it is not available.

    ``None`` also covers the case where the keyboard is present but another
    program is holding it — the usage page can only be read from an open
    collection. Use :func:`connect` to tell those two cases apart.
    """
    devices = find_devices(AK820_VID, AK820_PID, usage_page=AK820_USAGE_PAGE)
    for device in devices:
        if device.interface == AK820_INTERFACE:
            return device
    return devices[0] if devices else None


BUSY_MESSAGE = (
    "Another program is using the keyboard. Close the official AJAZZ driver, "
    "OpenRGB or any other keyboard tool and try again."
)
MISSING_MESSAGE = "AK820 not found. Plug the keyboard in and try again."


class HidDevice:
    """An open HID collection.

    The handle is held exclusively and only for as long as a transaction needs
    it, so other HID tools can still use the keyboard between transactions.
    """

    def __init__(self, path: HidPath) -> None:
        self.path = path
        self._handle = w.open_handle(
            path.path, w.GENERIC_READ | w.GENERIC_WRITE, 0, overlapped=True)
        if self._handle == w.INVALID_HANDLE_VALUE:
            code = w.last_error()
            if code in (w.ERROR_SHARING_VIOLATION, w.ERROR_ACCESS_DENIED):
                raise HidError(BUSY_MESSAGE, code)
            raise HidError(f"Could not open the keyboard (Windows error {code}).", code)

    def write(self, data: bytes) -> int:
        """Write one output report. ``data`` must be 64 bytes; byte 0 is the report id."""
        if len(data) != PACKET_SIZE:
            raise ValueError(f"output report must be {PACKET_SIZE} bytes, got {len(data)}")
        try:
            return w.write_report(self._handle, bytes(data))
        except OSError as exc:
            raise HidError(f"Writing to the keyboard failed: {exc}", exc.errno) from exc

    def read(self, timeout_ms: int = 200) -> bytes | None:
        """Read one input report, or ``None`` if the keyboard stayed quiet."""
        try:
            return w.read_report(self._handle, PACKET_SIZE, timeout_ms)
        except OSError as exc:
            raise HidError(f"Reading from the keyboard failed: {exc}", exc.errno) from exc

    def close(self) -> None:
        if getattr(self, "_handle", None) is not None:
            w.close_handle(self._handle)
            self._handle = None

    def __enter__(self) -> "HidDevice":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def open_device(path: HidPath) -> HidDevice:
    """Open a HID collection for reading and writing."""
    return HidDevice(path)


def connect() -> HidDevice:
    """Open the AK820, or explain why it could not be opened.

    Distinguishes the two failures a user actually sees: the keyboard is not
    plugged in, or something else already has it open.
    """
    device = find_ak820()
    if device is None:
        if list_interface_paths(AK820_VID, AK820_PID):
            raise HidError(BUSY_MESSAGE, w.ERROR_SHARING_VIOLATION)
        raise HidError(MISSING_MESSAGE)
    return open_device(device)
