"""The system settings (Windows Lock, Exchange Key, report rate).

The offsets these tests pin are the vendor's own, taken from the official
driver's record writer and confirmed against a capture of it driving this
board (see ``ak820/protocol/stages.py``).  If one of these tests fails
after a change, the change broke the mapping - do not "fix" the test.
"""

from __future__ import annotations

import pytest

from ak820.protocol.stages import (
    POLLING_RATES,
    RECORD_SIZE,
    parse_stages,
    patch_stages,
)


def record(**overrides: int) -> bytes:
    """The 29-byte live record with any byte overridden."""
    out = bytearray(RECORD_SIZE)
    out[0x01] = 6  # a mode, so the record looks like a real one
    out[0x02] = 4
    for offset, value in overrides.items():
        out[int(offset, 16)] = value
    return bytes(out)


# -- reading -----------------------------------------------------------------


def test_all_off_is_the_default_record():
    stages = parse_stages(record())
    assert stages == {
        "exchange": 0,
        "win_lock": 0,
        "polling_rate": 0,
        "polling_hz": 1000,
    }


def test_the_offsets_are_the_ones_the_official_driver_writes():
    # Byte 0x13 = Exchange Key, 0x15 = Windows Lock, 0x16 = report rate.
    # These three are the flips the capture of the official app shows.
    assert parse_stages(record(**{"13": 1}))["exchange"] == 1
    assert parse_stages(record(**{"15": 1}))["win_lock"] == 1
    assert parse_stages(record(**{"16": 3}))["polling_rate"] == 3
    assert parse_stages(record(**{"16": 3}))["polling_hz"] == 125


def test_a_rate_the_board_does_not_list_falls_back_to_1000hz():
    # A byte past the four rates means a value this app cannot show; the
    # board's own default is the honest answer rather than a crash.
    stages = parse_stages(record(**{"16": 9}))
    assert stages["polling_rate"] == 0
    assert stages["polling_hz"] == 1000


def test_every_rate_round_trips_through_its_index():
    for index, hz in enumerate(POLLING_RATES):
        stages = parse_stages(record(**{"16": index}))
        assert stages["polling_hz"] == hz


def test_a_short_record_is_refused():
    with pytest.raises(ValueError):
        parse_stages(b"\x00" * 8)


# -- writing -----------------------------------------------------------------


def test_setting_one_stage_leaves_every_other_byte_alone():
    # Fill the tail with noise, so a zeroing bug cannot hide.
    noisy = bytearray(record())
    for offset in range(0x09, RECORD_SIZE):
        noisy[offset] = (offset * 7 + 3) & 0xFF
    noisy[0x14] = 0x21  # the N-key flag, which this app never drives
    updated = patch_stages(bytes(noisy), win_lock=1)
    assert updated[0x15] == 1
    assert updated[0x13] == noisy[0x13]
    assert updated[0x14] == 0x21
    assert updated[0x16] == noisy[0x16]
    assert updated[:0x15] == bytes(noisy[:0x15])


def test_all_three_stages_can_be_set_at_once():
    updated = patch_stages(record(), exchange=1, win_lock=1, polling_rate=2)
    assert updated[0x13] == 1
    assert updated[0x15] == 1
    assert updated[0x16] == 2


def test_out_of_range_values_are_refused():
    with pytest.raises(ValueError):
        patch_stages(record(), exchange=2)
    with pytest.raises(ValueError):
        patch_stages(record(), win_lock=-1)
    with pytest.raises(ValueError):
        patch_stages(record(), polling_rate=4)
