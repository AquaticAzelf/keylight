"""Pull the interesting commands out of an official-app capture.

    python tools/inspect_capture.py captures/official-20261020-130004.jsonl
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict

INTERESTING = {0x05, 0x06, 0x09, 0x0A, 0x0B, 0x0D, 0x1A, 0x1B}


def load(path: str) -> list[bytes]:
    return [packet for _, packet in load_timed(path)]


def load_timed(path: str) -> list[tuple[float, bytes]]:
    """Every HID report with the time it was sent."""
    packets = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("event") != "report":
                continue
            try:
                raw = bytes.fromhex(record["hex"].replace(" ", ""))
            except ValueError:
                continue
            if len(raw) == 64:
                packets.append((record.get("t", 0.0), raw))
    return packets


def markers(path: str) -> list[tuple[float, str]]:
    """The markers the person doing the capture left behind."""
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("event") == "marker":
                out.append((record.get("t", 0.0), record.get("note", "")))
    return out


def timeline(path: str) -> None:
    """What changed, and when.

    The official driver writes the whole 29-byte profile block in one go, so
    a setting that lives in the block shows up as one byte changing between
    two otherwise-identical records. This prints exactly that.
    """
    timed = load_timed(path)
    marks = markers(path)

    print("\n--- what changed, and when ---")
    previous = None
    for when, packet in timed:
        if packet[3] != 0x06 or packet[4] != 29:
            continue
        record = packet[8:8 + 29]
        if previous is None:
            previous = record
            continue
        if record == previous:
            continue
        changed = [
            (index, previous[index], record[index])
            for index in range(29)
            if previous[index] != record[index]
        ]
        stamp = time.strftime("%H:%M:%S", time.localtime(when))
        note = ""
        for mark_when, mark_note in marks:
            if mark_when <= when and (not note or mark_when > 0):
                note = mark_note
        print("  %s  %s%s" % (
            stamp,
            ", ".join("byte %d: 0x%02X -> 0x%02X" % (i, a, b)
                      for i, a, b in changed),
            "   <- %s" % note if note else "",
        ))
        previous = record

    if marks:
        print("\n--- markers ---")
        for when, note in marks:
            print("  %s  %s" % (time.strftime("%H:%M:%S", time.localtime(when)),
                                note or "(no note)"))


def main() -> int:
    path = sys.argv[1]
    packets = load(path)
    print("%d packets" % len(packets))

    by_command = Counter(p[3] for p in packets)
    for command, count in sorted(by_command.items()):
        print("  cmd 0x%02X  %d" % (command, count))

    print("\n--- every packet that is not 0x12 or the BEGIN/END frames ---")
    seen = Counter()
    for packet in packets:
        command = packet[3]
        if command in (0x01, 0x02, 0x12):
            continue
        key = (command, packet[4], packet[5], packet[6])
        seen[key] += 1
        if seen[key] > 3:
            continue
        print("cmd 0x%02X size=%d off=0x%04X  %s"
              % (command, packet[4], packet[5] | (packet[6] << 8),
                 packet[8:8 + packet[4]].hex(" ")))

    print("\n--- the 29-byte records, field by field ---")
    records = [p[8:8 + 29] for p in packets if p[3] == 0x06 and p[4] == 29]
    print("%d records" % len(records))
    for index in range(29):
        values = sorted({r[index] for r in records})
        if len(values) <= 4:
            print("  byte %2d: %s" % (index, values))
        else:
            print("  byte %2d: %d distinct" % (index, len(values)))

    print("\n--- the records themselves ---")
    for record in records:
        print("  " + record.hex(" "))

    print("\n--- 0x05 writes ---")
    for packet in packets:
        if packet[3] == 0x05:
            print("  size=%d off=0x%04X  %s"
                  % (packet[4], packet[5] | (packet[6] << 8),
                     packet[8:8 + packet[4]].hex(" ")))

    timeline(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
