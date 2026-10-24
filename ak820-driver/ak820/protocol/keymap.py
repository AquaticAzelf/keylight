"""The board's keycode table.

Config offset 0xC0 holds 128 slots of three bytes:

    modifier mask | modifier bits | HID usage

The slots are the board's own colour chain, in order, so reading this table
tells us which physical key each chain slot drives.  A slot holding a key
this board does not have (F13, the numpad, ...) lights nothing.
"""

from __future__ import annotations

KEYMAP_OFFSET = 0xC0
SLOT_SIZE = 3
SLOT_COUNT = 128

# HID usage codes, keyboard page.
USAGE_NAMES = {
    0x04: "a", 0x05: "b", 0x06: "c", 0x07: "d", 0x08: "e", 0x09: "f",
    0x0A: "g", 0x0B: "h", 0x0C: "i", 0x0D: "j", 0x0E: "k", 0x0F: "l",
    0x10: "m", 0x11: "n", 0x12: "o", 0x13: "p", 0x14: "q", 0x15: "r",
    0x16: "s", 0x17: "t", 0x18: "u", 0x19: "v", 0x1A: "w", 0x1B: "x",
    0x1C: "y", 0x1D: "z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4", 0x22: "5", 0x23: "6",
    0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "enter", 0x29: "esc", 0x2A: "backspace", 0x2B: "tab",
    0x2C: "space", 0x2D: "minus", 0x2E: "equal", 0x2F: "leftbrace",
    0x30: "rightbrace", 0x31: "backslash", 0x32: "nonus_hash",
    0x33: "semicolon", 0x34: "quote", 0x35: "grave", 0x36: "comma",
    0x37: "period", 0x38: "slash", 0x39: "capslock",
    0x3A: "F1", 0x3B: "F2", 0x3C: "F3", 0x3D: "F4", 0x3E: "F5",
    0x3F: "F6", 0x40: "F7", 0x41: "F8", 0x42: "F9", 0x43: "F10",
    0x44: "F11", 0x45: "F12",
    0x46: "intl_ro", 0x47: "katakana", 0x48: "hiragana",
    0x49: "intl_convert", 0x4A: "intl_nonconvert",
    0x4B: "pageup", 0x4C: "pagedown", 0x4D: "delete", 0x4E: "end",
    0x4F: "right", 0x50: "left", 0x51: "down", 0x52: "up",
    0x53: "numlock", 0x54: "kp_slash", 0x55: "kp_star", 0x56: "kp_minus",
    0x57: "kp_plus", 0x58: "kp_enter", 0x59: "kp_1", 0x5A: "kp_2",
    0x5B: "kp_3", 0x5C: "kp_4", 0x5D: "kp_5", 0x5E: "kp_6", 0x5F: "rshift",
    0x60: "intl_backslash", 0x61: "intl_ro2",
    0x62: "kp_7", 0x63: "kp_8", 0x64: "nonus_backslash", 0x65: "kp_9",
    0x66: "kp_dot",
    0xA201: "F13", 0xA202: "F14", 0xA203: "F15", 0xA204: "F16",
    0xA205: "F17",
}

# The second byte says which modifier a key is (or carries, for the plain
# keys it is zero and the usage is the key itself).  Bit 0x80 marks the
# F13..F17 family, which stores its number in the usage byte instead.
MODIFIER_NAMES = {
    0x01: "ctrl", 0x02: "shift", 0x04: "alt", 0x08: "gui",
}


def decode_slot(mask: int, modifier: int, usage: int) -> str:
    """Turn one slot into a key name, or an empty string if it holds none."""
    if modifier & 0x80 and 1 <= usage <= 5:
        return "F%d" % (12 + usage)
    if modifier & 0x0F and usage == 0:
        side = "r" if mask & 0x40 else "l"
        return MODIFIER_NAMES.get(modifier & 0x0F, "mod%02X" % modifier) + "_" + side
    name = USAGE_NAMES.get(usage)
    return name or ""


def read_keymap(read_config) -> list[dict]:
    """Read the 128 keycode slots.

    ``read_config(offset, size)`` returns raw config bytes.
    """
    raw = read_config(KEYMAP_OFFSET, SLOT_SIZE * SLOT_COUNT)
    slots: list[dict] = []
    for index in range(SLOT_COUNT):
        chunk = raw[index * SLOT_SIZE:index * SLOT_SIZE + SLOT_SIZE]
        if len(chunk) < SLOT_SIZE:
            slots.append({"slot": index, "mask": 0, "modifier": 0, "usage": 0,
                          "name": ""})
            continue
        mask, modifier, usage = chunk[0], chunk[1], chunk[2]
        slots.append({
            "slot": index,
            "mask": mask,
            "modifier": modifier,
            "usage": usage,
            "name": decode_slot(mask, modifier, usage),
        })
    return slots
