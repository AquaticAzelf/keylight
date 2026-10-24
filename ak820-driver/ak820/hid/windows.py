"""Thin ctypes binding to the Win32 HID stack.

Only what the AK820 driver needs: enumerate HID interface paths, read a
collection's usage page and report sizes, and do overlapped reads and writes on
an open handle. No third-party dependency, so the packaged exe stays small.

Two Windows quirks this file exists to work around:

* ``HidD_GetAttributes`` reports device-level values, not the collection's
  usage page, on this keyboard. The usage page has to come from
  ``HidP_GetCaps`` on the preparsed data.
* ``hidclass.dll`` is not present on every machine, so the ``HidP_GetUsagePage``
  route is not available. ``HidP_GetCaps`` lives in ``hid.dll`` and is.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
ERROR_ACCESS_DENIED = 5
ERROR_SHARING_VIOLATION = 32
ERROR_IO_PENDING = 997
HIDP_STATUS_SUCCESS = 0x00110000

_GUID_DEVINTERFACE_HID = "{4D1E55B2-F16F-11CF-88CB-001111000030}"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_size_t),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_size_t),
        ("InternalHigh", ctypes.c_size_t),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]


setupapi = ctypes.WinDLL("setupapi.dll", use_last_error=True)
hid = ctypes.WinDLL("hid.dll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
hid.HidD_GetHidGuid.restype = None
hid.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
hid.HidD_GetPreparsedData.restype = ctypes.c_ubyte
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidD_FreePreparsedData.restype = ctypes.c_ubyte
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid.HidP_GetCaps.restype = ctypes.c_long

setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)]
setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA), ctypes.c_void_p,
    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED)]
kernel32.ReadFile.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED)]
kernel32.WriteFile.restype = wintypes.BOOL
kernel32.GetOverlappedResult.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(OVERLAPPED), ctypes.POINTER(wintypes.DWORD),
    wintypes.BOOL]
kernel32.GetOverlappedResult.restype = wintypes.BOOL
kernel32.CreateEventW.argtypes = [
    ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.CancelIo.argtypes = [wintypes.HANDLE]
kernel32.CancelIo.restype = wintypes.BOOL


@dataclass(frozen=True)
class CollectionInfo:
    """What a HID collection reports about itself."""

    usage_page: int
    usage: int
    input_report_length: int
    output_report_length: int
    feature_report_length: int


def enumerate_hid_interface_paths() -> list[str]:
    """Every HID interface path currently present on the machine."""
    guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(guid))

    hdev = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE)
    if hdev == INVALID_HANDLE_VALUE:
        return []

    paths: list[str] = []
    # DevicePath is a WCHAR[1] directly after the DWORD cbSize, so it always
    # starts at offset 4. cbSize itself is 8 on 64-bit and 6 on 32-bit.
    path_offset = 4
    cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
    try:
        index = 0
        while True:
            data = SP_DEVICE_INTERFACE_DATA()
            data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                    hdev, None, ctypes.byref(guid), index, ctypes.byref(data)):
                break
            index += 1

            required = wintypes.DWORD(0)
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(data), None, 0, ctypes.byref(required), None)
            buf = ctypes.create_string_buffer(required.value)
            buf[0:4] = cb_size.to_bytes(4, "little")
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                    hdev, ctypes.byref(data), buf, required.value,
                    ctypes.byref(required), None):
                continue
            paths.append(ctypes.wstring_at(ctypes.addressof(buf) + path_offset))
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)
    return paths


def open_handle(path: str, access: int, share: int, overlapped: bool = False) -> int:
    """Open a HID collection. Returns the raw handle, or INVALID_HANDLE_VALUE."""
    flags = FILE_FLAG_OVERLAPPED if overlapped else 0
    return kernel32.CreateFileW(
        path, access, share, None, OPEN_EXISTING, flags, None)


def close_handle(handle: int) -> None:
    kernel32.CloseHandle(handle)


def last_error() -> int:
    return ctypes.get_last_error()


def collection_info(path: str) -> CollectionInfo | None:
    """Read a collection's usage page and report sizes.

    Returns ``None`` when the collection cannot be opened (another program is
    holding it, or the OS owns it, as it does the keyboard and mouse
    collections of a composite keyboard).
    """
    handle = open_handle(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE)
    if handle == INVALID_HANDLE_VALUE:
        return None
    try:
        preparsed = ctypes.c_void_p()
        if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            return None
        try:
            caps = HIDP_CAPS()
            if hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) != HIDP_STATUS_SUCCESS:
                return None
            return CollectionInfo(
                usage_page=caps.UsagePage,
                usage=caps.Usage,
                input_report_length=caps.InputReportByteLength,
                output_report_length=caps.OutputReportByteLength,
                feature_report_length=caps.FeatureReportByteLength,
            )
        finally:
            hid.HidD_FreePreparsedData(preparsed)
    finally:
        close_handle(handle)


def write_report(handle: int, data: bytes) -> int:
    """Write one output report. ``data[0]`` is the report id."""
    buf = ctypes.create_string_buffer(data, len(data))
    written = wintypes.DWORD(0)
    overlapped = OVERLAPPED()
    overlapped.hEvent = kernel32.CreateEventW(None, True, False, None)
    try:
        ok = kernel32.WriteFile(
            handle, buf, len(data), ctypes.byref(written), ctypes.byref(overlapped))
        if not ok:
            err = last_error()
            if err != ERROR_IO_PENDING:
                raise OSError(err, f"WriteFile failed: {ctypes.FormatError(err)}")
        wait = kernel32.WaitForSingleObject(overlapped.hEvent, 1000)
        if wait != WAIT_OBJECT_0:
            raise OSError(0, "WriteFile timed out")
        if not kernel32.GetOverlappedResult(
                handle, ctypes.byref(overlapped), ctypes.byref(written), False):
            err = last_error()
            raise OSError(err, f"WriteFile failed: {ctypes.FormatError(err)}")
        return written.value
    finally:
        kernel32.CloseHandle(overlapped.hEvent)


def read_report(handle: int, size: int, timeout_ms: int) -> bytes | None:
    """Read one input report. Returns ``None`` if nothing arrived in time."""
    buf = ctypes.create_string_buffer(size)
    read = wintypes.DWORD(0)
    overlapped = OVERLAPPED()
    overlapped.hEvent = kernel32.CreateEventW(None, True, False, None)
    try:
        ok = kernel32.ReadFile(
            handle, buf, size, ctypes.byref(read), ctypes.byref(overlapped))
        if not ok:
            err = last_error()
            if err != ERROR_IO_PENDING:
                raise OSError(err, f"ReadFile failed: {ctypes.FormatError(err)}")
        wait = kernel32.WaitForSingleObject(overlapped.hEvent, timeout_ms)
        if wait != WAIT_OBJECT_0:
            kernel32.CancelIo(handle)
            kernel32.GetOverlappedResult(
                handle, ctypes.byref(overlapped), ctypes.byref(read), False)
            return None
        if not kernel32.GetOverlappedResult(
                handle, ctypes.byref(overlapped), ctypes.byref(read), False):
            err = last_error()
            raise OSError(err, f"ReadFile failed: {ctypes.FormatError(err)}")
        return buf.raw[: read.value]
    finally:
        kernel32.CloseHandle(overlapped.hEvent)
