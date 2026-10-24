"""Try the board's per-key colour buffer: read it, paint a key, read it back.

The per-key editor needs two things the app does not have yet: a way to read
the board's colour buffer, and a way to paint one key.

    python tools/perkey_test.py [led]
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402

BUFFER_BYTES = 378  # 126 keys, three bytes each


def main() -> int:
    led = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    device = find_ak820()
    if device is None:
        print("no keyboard found")
        return 1
    session = KeyboardSession(device)

    before = session.read_custom_colors(BUFFER_BYTES)
    print("read %d bytes of the colour buffer" % len(before))
    if len(before) >= 6:
        print("  first two keys:",
              list(before[0:3]), list(before[3:6]))

    colour = bytes([255, 0, 0])
    session.write_custom_colors(colour, offset=led * 3)
    print("wrote %s to the stored set at key %d" % (list(colour), led))

    after = session.read_custom_colors(BUFFER_BYTES)
    if len(after) >= led * 3 + 3:
        got = list(after[led * 3:led * 3 + 3])
        print("read back: %s" % got)
        print("MATCH" if got == list(colour) else "DIFFERENT")
    else:
        print("read back failed (%d bytes)" % len(after))

    # Now the live buffer, which is what the board lights up from.
    session.set_per_key_colors(colour, offset=led * 3)
    print("wrote %s to the live buffer at key %d" % (list(colour), led))
    live = session.read_custom_colors(BUFFER_BYTES)
    print("live buffer reads back: %s" % list(live[led * 3:led * 3 + 3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
