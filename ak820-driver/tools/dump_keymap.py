"""Dump the board's own keycode table (config space 0xC0).

The board stores 128 slots of 3 bytes: modifier, usage high, usage low.
This is the table the vendor app writes when you remap keys.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402

KEYMAP_OFFSET = 0xC0
KEYMAP_SLOTS = 128
SLOT_SIZE = 3


def read_keymap(session: KeyboardSession) -> bytes:
    data = bytearray()
    while len(data) < KEYMAP_SLOTS * SLOT_SIZE:
        chunk = session.read_config(KEYMAP_OFFSET + len(data), SLOT_SIZE * 8)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def main() -> int:
    path = find_ak820()
    if path is None:
        print("AK820 not found")
        return 1
    session = KeyboardSession(path)
    raw = read_keymap(session)
    if not raw:
        print("no keymap data")
        return 1
    for slot in range(min(KEYMAP_SLOTS, len(raw) // SLOT_SIZE)):
        mod, hi, lo = raw[slot * SLOT_SIZE : slot * SLOT_SIZE + SLOT_SIZE]
        if mod == 0 and hi == 0 and lo == 0:
            continue
        usage = (hi << 8) | lo
        print(f"slot {slot:3d}  mod 0x{mod:02x}  usage 0x{usage:04x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
