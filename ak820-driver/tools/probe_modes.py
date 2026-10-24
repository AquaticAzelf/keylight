"""Read the board's live lighting state and try the software-direct mode.

The board keeps its lighting state in config space 0x00:
    0x00 mode, 0x01 brightness, 0x02 speed, 0x03 direction,
    0x04 random flag, 0x05..0x07 mode colour (RGB)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402


def show(session: KeyboardSession, label: str) -> None:
    data = session.read_config(0x00, 12)
    if not data:
        print("%-28s <no reply>" % label)
        return
    mode = data[0]
    print("%-28s mode=0x%02X brightness=%d speed=%d direction=%d random=0x%02X "
          "rgb=%s" % (label, mode, data[1], data[2], data[3], data[4],
                      list(data[5:8])))


def main() -> int:
    path = find_ak820()
    if path is None:
        print("AK820 not found")
        return 1
    session = KeyboardSession(path)

    show(session, "current state")

    for mode in (0x06, 0x14, 0xFF, 0x00):
        print("\n-- trying mode 0x%02X via V1 packet --" % mode)
        session.apply_lighting(mode, 4, 3, 0, False, 0, 0, 0)
        show(session, "  after V1 write")

        session.write_config(0x00, bytes([mode, 4, 3, 0, 0, 0, 0, 0]))
        show(session, "  after V2 config write")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
