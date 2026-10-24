"""Device discovery for the AK820's vendor HID collection."""

import pytest

from ak820.hid.device import (
    AK820_INTERFACE,
    AK820_PID,
    AK820_USAGE_PAGE,
    AK820_VID,
    find_ak820,
    find_devices,
    list_interface_paths,
)

pytestmark = pytest.mark.hardware


def test_finds_ak820_wired_vendor_collection():
    devs = find_devices(AK820_VID, AK820_PID, usage_page=AK820_USAGE_PAGE)
    if not devs:
        if list_interface_paths(AK820_VID, AK820_PID):
            pytest.skip("AK820 is present but its vendor collection is busy")
        pytest.skip("AK820 not plugged in")
    d = devs[0]
    assert d.vid == AK820_VID and d.pid == AK820_PID
    assert d.usage_page == AK820_USAGE_PAGE
    assert d.interface == AK820_INTERFACE


def test_find_ak820_returns_the_vendor_collection():
    device = find_ak820()
    if device is None:
        pytest.skip("AK820 not plugged in")
    assert device.usage_page == AK820_USAGE_PAGE
    assert device.interface == AK820_INTERFACE
    assert "col04" in device.path
