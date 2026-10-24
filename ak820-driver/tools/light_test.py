"""Live test: set the keyboard to one colour, then put it back.

    python tools/light_test.py --mode 6 --brightness 4 --r 255 --g 0 --b 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ak820.hid.device import HidError, find_ak820  # noqa: E402
from ak820.protocol.lighting import MODE_NAMES  # noqa: E402
from ak820.protocol.packet import parse_packet  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402


def show(label: str, reply: bytes | None) -> None:
    if reply is None:
        print(f"  {label}: no reply (the board does not answer this command)")
        return
    parsed = parse_packet(reply)
    print(f"  {label}: {reply[:16].hex(' ')}")
    print(f"    command=0x{parsed['command']:02X} size={parsed['size']} "
          f"checksum_ok={parsed['checksum_ok']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", type=int, default=0x06, help="lighting mode id")
    parser.add_argument("--brightness", type=int, default=4)
    parser.add_argument("--speed", type=int, default=3)
    parser.add_argument("--direction", type=int, default=0)
    parser.add_argument("--r", type=int, default=255)
    parser.add_argument("--g", type=int, default=0)
    parser.add_argument("--b", type=int, default=0)
    parser.add_argument("--keep", action="store_true",
                        help="do not put the keyboard back to white afterwards")
    args = parser.parse_args()

    device = find_ak820()
    if device is None:
        print("AK820 not found (or another program is holding it).")
        return 1
    print(f"device: {device.path}")
    print(f"  usage page 0x{device.usage_page:04X} interface {device.interface}")

    session = KeyboardSession(device)
    name = MODE_NAMES.get(args.mode, "?")
    print(f"\nsetting mode 0x{args.mode:02X} ({name}) to rgb({args.r},{args.g},{args.b}) "
          f"at brightness {args.brightness}")
    try:
        replies = session.apply_lighting(
            args.mode, args.brightness, args.speed, args.direction,
            False, args.r, args.g, args.b)
    except HidError as exc:
        print(f"  failed: {exc}")
        return 1
    for label, reply in zip(("BEGIN", "SET", "END"), replies):
        show(label, reply)

    if not args.keep:
        print("\nputting the keyboard back to static white")
        replies = session.apply_lighting(0x06, args.brightness, args.speed, 0,
                                        False, 255, 255, 255)
        for label, reply in zip(("BEGIN", "SET", "END"), replies):
            show(label, reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
