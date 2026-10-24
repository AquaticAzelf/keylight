"""The chain map: which colour-buffer slot drives which key."""

import pytest

from ak820.devices import all_keys, colour_buffer, key_by_label, load_device


@pytest.fixture(scope="module")
def device():
    return load_device("ak820_wired")


def test_the_device_is_the_one_we_probed(device):
    assert device["vid"] == 0x320F
    assert device["pid"] == 0x505B
    assert device["usage_page"] == 0xFF1C
    assert device["chain_size"] == 126


def test_it_has_the_ak820s_keys_and_the_knob(device):
    assert len(all_keys(device)) == 82
    assert device["knob"]["kind"] == "knob"


def test_every_known_slot_is_used_once(device):
    slots = [k["chain"] for k in all_keys(device) if k["chain"] is not None]
    assert len(slots) == len(set(slots))


def test_the_measured_keys_point_at_the_right_slots(device):
    """Checked against the keyboard by eye, and the shop's product photo."""
    measured = {
        "Esc": 0, "~": 1, "Tab": 2, "Caps": 3, "Shift": 4, "Ctrl": 5,
        "F1": 8, "1!": 9, "Q": 10, "A": 11, "Z": 20, "N": 60,
        "Spacebar": 45, "-_": 89, "Backspace": 105, "\\|": 106,
        "Enter": 107, "PgUp": 122, "PgDn": 115, "Fn": 85,
        "←": 109, "↓": 117, "→": 125,
    }
    by_label = {}
    for key in all_keys(device):
        label = key.get("realLabel") or key["label"]
        by_label.setdefault(label, key)
    for label, slot in measured.items():
        key = by_label.get(label)
        assert key is not None, "no key labelled %r" % label
        assert key["chain"] == slot, "%s should drive slot %d" % (label, slot)


def test_the_keys_taken_from_the_led_grid(device):
    """Delete, Home, End and the right Ctrl land in the grid's empty cells."""
    by_label = {}
    for key in all_keys(device):
        label = key.get("realLabel") or key["label"]
        by_label.setdefault(label, key)
    for label, slot in {"Del": 104, "Home": 121, "End": 123, "Ctrl_R": 101}.items():
        assert by_label[label]["chain"] == slot, "%s should drive slot %d" % (label, slot)


def test_the_keyboard_has_two_alt_keys(device):
    """The product photo shows a right Alt next to the spacebar."""
    alts = [k for k in all_keys(device) if k["label"] == "Alt"]
    assert len(alts) == 2
    assert alts[0]["chain"] == 21
    assert alts[1]["chain"] == 77


def test_the_whole_keyboard_fits_in_the_colour_buffer(device):
    slots = [k["chain"] for k in all_keys(device) if k["chain"] is not None]
    assert all(0 <= s < device["chain_size"] for s in slots)


def test_the_colour_buffer_is_one_triple_per_slot(device):
    buffer = colour_buffer(device)
    assert len(buffer) == device["chain_size"] * 3
    assert set(buffer) == {0}


def test_a_colour_lands_in_its_own_slot(device):
    buffer = colour_buffer(device, {5: (255, 0, 0)})
    assert buffer[15:18] == bytes([255, 0, 0])
    assert buffer[12:15] == bytes([0, 0, 0])


def test_a_slot_outside_the_buffer_is_refused(device):
    with pytest.raises(ValueError):
        colour_buffer(device, {device["chain_size"]: (1, 2, 3)})


def test_the_right_hand_keys_can_be_told_apart(device):
    by_label = key_by_label(device)
    assert by_label["Alt"]["chain"] == 21
    assert by_label["Ctrl_R"]["chain"] == 101
