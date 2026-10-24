"""Board layouts: where the keys are, and how they map to the LED chain."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DEVICES = Path(__file__).parent


@lru_cache(maxsize=None)
def load_device(device_id: str = "ak820_wired") -> dict:
    """Return the layout data for a board id."""
    path = _DEVICES / ("%s.json" % device_id)
    if not path.is_file():
        raise KeyError("unknown device: %s" % device_id)
    return json.loads(path.read_text(encoding="utf-8"))


def all_keys(device: dict) -> list[dict]:
    """Every key of a layout, row by row."""
    return [key for row in device["rows"] for key in row["keys"]]


def key_by_label(device: dict) -> dict[str, dict]:
    """Every key of a layout, by its label.

    The right-hand Ctrl and the right Alt have the same label as their
    partners, so the second one found wins and the first is reachable as
    "Alt" / "Ctrl" only once.  Use the key's own ``chain`` slot to address
    them.
    """
    found: dict[str, dict] = {}
    for key in all_keys(device):
        found.setdefault(key.get("realLabel") or key["label"], key)
    return found


def colour_buffer(device: dict, colors: dict[int, tuple[int, int, int]] | None = None) -> bytes:
    """The board's colour buffer: one RGB triple per LED slot.

    ``colors`` maps a slot number to a colour.  Slots with no colour stay
    black, so the buffer always covers the whole keyboard.
    """
    colors = colors or {}
    slots = device["chain_size"]
    buffer = bytearray(slots * 3)
    for slot, color in colors.items():
        if not 0 <= slot < slots:
            raise ValueError("slot %r is outside the buffer" % (slot,))
        for channel, value in enumerate(color):
            if not 0 <= value <= 255:
                raise ValueError("colour channel %r is outside 0..255" % (value,))
            buffer[slot * 3 + channel] = value
    return bytes(buffer)
