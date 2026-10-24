"""Dump the keyboard's config space and look for the known setting values.

The official driver keeps these settings for a keyboard: the polling rate,
the key repeat, the key repeat delay, the Windows lock flags and the
six-key flag. Their current values are known (0, 16, 0, 0, 0 and 1), so
the bytes that hold them can be picked out of the board's config space.

    python tools/dump_config.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402

SIZE = 0x200
WANTED = {0x00: "polling rate (0)", 0x10: "repeat (16)", 0x01: "six-key flag (1)"}


def main() -> int:
    device = find_ak820()
    if device is None:
        print("no keyboard found")
        return 1
    session = KeyboardSession(device)
    data = session.read_config(0, SIZE)
    print("read %d bytes" % len(data))
    for start in range(0, len(data), 16):
        chunk = data[start:start + 16]
        print("0x%03x  %s" % (start, " ".join("%02x" % b for b in chunk)))
    print()
    print("places a wanted value sits:")
    for value, name in WANTED.items():
        spots = [i for i, b in enumerate(data) if b == value]
        print("  %-22s %s" % (name, " ".join("0x%02x" % s for s in spots[:24])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
