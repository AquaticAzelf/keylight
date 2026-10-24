"""Light up chain slots in distinct colours, so the chain can be measured.

The board's colour buffer has 126 slots. Which physical key each slot
drives is what we are measuring: paint a few slots in loud colours and
look at the board.  The slot numbers this app uses were worked out from
a *generic* 75% layout, so the right-hand cluster is in doubt.

    python tools/paint_slots.py 0 1 7 8      # four slots, four colours
    python tools/paint_slots.py --round 1     # the second dozen keys
    python tools/paint_slots.py --list       # what is in each round
    python tools/paint_slots.py --undo       # put the board back

Each round lights up twelve keys in twelve colours that cannot be
confused with each other.  Write down which key is which colour and the
chain is known.  There are seven rounds for the eighty-two keys.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ak820.hid.device import find_ak820  # noqa: E402
from ak820.protocol.session import KeyboardSession  # noqa: E402
from ak820.protocol.v2 import MODE_DIRECT  # noqa: E402

MAP_SIZE = 126

PALETTE = [
    (255, 255, 255),  # white
    (255, 0, 0),      # red
    (0, 255, 0),      # green
    (0, 0, 255),      # blue
    (255, 255, 0),    # yellow
    (255, 0, 255),    # magenta
    (0, 255, 255),    # cyan
    (255, 128, 0),    # orange
    (128, 0, 255),    # violet
    (128, 255, 0),    # lime
    (0, 128, 128),    # teal
    (255, 128, 128),  # pink
]
NAMES = ["white", "red", "green", "blue", "yellow", "magenta", "cyan", "orange",
         "violet", "lime", "teal", "pink"]

PER_ROUND = 12


def our_keys() -> list[dict]:
    """The keys this app knows about, with the slot each one uses."""
    caps = json.loads(
        (Path(__file__).resolve().parent.parent / "ui" / "assets" / "ak820-caps.json")
        .read_text(encoding="utf-8")
    )
    keys = caps["keys"] if isinstance(caps, dict) else caps
    return sorted(keys, key=lambda key: key["led"])


def rounds() -> list[list[dict]]:
    """The keys, cut into rounds of twelve."""
    keys = our_keys()
    return [keys[start:start + PER_ROUND] for start in range(0, len(keys), PER_ROUND)]


def paint(session: KeyboardSession, slots: list[int]) -> None:
    """Light up the given slots and leave every other one dark."""
    session.set_lighting(MODE_DIRECT, 4, 3, 0, False, 0, 0, 0)
    blob = bytearray()
    for slot in range(MAP_SIZE):
        colour = (0, 0, 0)
        for index, target in enumerate(slots):
            if slot == target:
                colour = PALETTE[index]
        blob.extend(colour)
    session.set_per_key_colors(bytes(blob))


def main() -> int:
    if "--list" in sys.argv:
        for number, group in enumerate(rounds()):
            print(f"round {number}:")
            for key in group:
                print(f"   slot {key['led']:3}  {key['label']}")
        return 0

    path = find_ak820()
    if path is None:
        print("the keyboard is not there, or another program is holding it")
        return 1
    session = KeyboardSession(path)

    if "--undo" in sys.argv:
        paint(session, [])
        print("every slot is dark again")
        return 0

    if "--round" in sys.argv:
        index = int(sys.argv[sys.argv.index("--round") + 1])
        group = rounds()[index]
        slots = [key["led"] for key in group]
        paint(session, slots)
        print(f"round {index} is on the keyboard:")
        for number, key in enumerate(group):
            print(f"   {NAMES[number]:<8} -> slot {key['led']:3} (we think it is {key['label']})")
        print("\nWhich key is each colour? Write it down and we will know the chain.")
        return 0

    slots = [int(a, 0) for a in sys.argv[1:]]
    if not slots:
        print("usage: paint_slots.py <slot> [slot ...] | --round N | --list | --undo")
        return 2
    if len(slots) > len(PALETTE):
        print(f"at most {len(PALETTE)} markers at a time")
        return 2
    paint(session, slots)
    print("painted:")
    for index, slot in enumerate(slots):
        print(f"  chain slot {slot:<4} -> {NAMES[index]}")
    print("\nWhich physical key is each of those? (everything else is dark)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
