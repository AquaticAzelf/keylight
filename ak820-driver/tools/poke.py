"""Send arbitrary packets to the board, for experiments.

    python tools/poke.py end-dynamic      # CMD_END_DYNAMIC_COLORS (0x13)
    python tools/poke.py static 255 0 0   # static mode, given RGB
    python tools/poke.py config 0x00 06 04 03 00 00 FF 00 00
    python tools/poke.py raw 12 38 00 00 00 <payload...>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.packet import make_packet  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402
from ak820.protocol.v2 import (  # noqa: E402
    CMD_END_DYNAMIC_COLORS,
    CMD_SEND_DYNAMIC_COLORS,
    CMD_WRITE_CONFIG,
)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = find_ak820()
    if path is None:
        print("AK820 not found")
        return 1
    session = KeyboardSession(path)
    command = sys.argv[1]

    if command == "end-dynamic":
        packet = make_packet(CMD_END_DYNAMIC_COLORS, 0, 0, 0, b"")
        for reply in session._transact([packet]):
            if reply:
                print("reply:", reply.hex(" "))

    elif command == "static":
        rgb = [int(v) for v in sys.argv[2:5]]
        session.apply_lighting(0x06, 4, 3, 0, False, *rgb)
        print("static rgb=%s" % rgb)

    elif command == "config":
        offset = int(sys.argv[2], 0)
        data = bytes(int(v, 0) for v in sys.argv[3:])
        session.write_config(offset, data)
        print("wrote %s at 0x%02X" % (data.hex(" "), offset))

    elif command == "raw":
        cmd = int(sys.argv[2], 0)
        size = int(sys.argv[3], 0)
        offset = int(sys.argv[4], 0)
        payload = bytes(int(v, 0) for v in sys.argv[5:])
        packet = make_packet(cmd, size, 0, offset, payload)
        for reply in session._transact([packet]):
            if reply:
                print("reply:", reply.hex(" "))

    else:
        print(__doc__)
        return 1

    data = session.read_config(0x00, 12)
    print("config 0x00: mode=0x%02X brightness=%d speed=%d dir=%d random=0x%02X rgb=%s"
          % (data[0], data[1], data[2], data[3], data[4], list(data[5:8])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
