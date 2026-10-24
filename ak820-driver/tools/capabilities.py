"""Ask the keyboard what it can do.

The board answers a capability query with its map size and how much room
it has for macros. This prints the answer.

    python tools/capabilities.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402


def main() -> int:
    device = find_ak820()
    if device is None:
        print("no keyboard found")
        return 1
    session = KeyboardSession(device)
    reply = session.query(0x03, offset=0, size=7)
    if reply is None:
        print("the board did not answer")
        return 1
    print("raw reply:", reply.hex(" "))
    print("payload: ", reply[8:15].hex(" "))
    from ak820.protocol.v2 import parse_capabilities
    print("parsed:  ", parse_capabilities(reply[8:15]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
