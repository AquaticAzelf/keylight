"""The lighting state the AK820 stores, and the packet that carries it.

The keyboard keeps one 8-byte record per profile: mode, brightness, speed,
direction, a random-colour flag and the RGB triple.
"""

from __future__ import annotations

from .packet import make_packet
from .v2 import CMD_SEND_DYNAMIC_COLORS

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 4
SPEED_MIN = 0
#: The board keeps six speeds, 0 (fastest) to 5 (slowest).
SPEED_MAX = 5
DIRECTION_MIN = 0
#: The board's own direction byte can hold more values than this app drives.
#: The two below are the ones this app writes.
DIRECTION_MAX = 1

DIRECTION_NAMES = {0: "Left to right", 1: "Right to left"}

#: The lighting modes the AK820 implements, with the names this app uses.
#: The numbers come from the official driver's own effect list for this board
#: (``DefaultData/default_light.json``), so they are the board's.  An effect
#: the driver does not offer for this board is not in here.
MODE_NAMES = {
    0x01: "Wave",
    0x02: "Cloud",
    0x03: "Vortex",
    0x04: "Spectrum",
    0x05: "Breath",
    0x06: "Static",
    0x07: "Reaction",
    0x08: "Ripples",
    0x09: "Traverse",
    0x0A: "Stars",
    0x0B: "Fireworks",
    0x0C: "Roll",
    0x0D: "Wave bar",
    0x0E: "Cartoon",
    0x0F: "Rain",
    0x10: "Scan",
    0x11: "Surmount",
    0x12: "Speed",
    0x14: "Custom",
    0x1D: "Audio wave",
    0x1E: "Capture colour",
}


def _check(name: str, value: int, low: int, high: int) -> int:
    if not low <= value <= high:
        raise ValueError(f"{name} must be {low}..{high}, got {value}")
    return value


def state_payload(mode: int, brightness: int, speed: int, direction: int,
                  random: bool, r: int, g: int, b: int) -> bytes:
    """The 8-byte lighting record the board keeps in a profile block."""
    _check("brightness", brightness, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
    _check("speed", speed, SPEED_MIN, SPEED_MAX)
    _check("direction", direction, DIRECTION_MIN, DIRECTION_MAX)
    for name, value in (("r", r), ("g", g), ("b", b)):
        _check(name, value, 0, 255)
    if not 0 <= mode <= 0xFF:
        raise ValueError(f"mode must be 0..255, got {mode}")
    return bytes([
        mode,
        brightness,
        speed,
        direction,
        0xFF if random else 0x00,
        r,
        g,
        b,
    ])


def make_per_key_packet(colors: bytes, offset: int = 0) -> bytes:
    """Build the packet that writes per-key colours.

    ``colors`` is a run of RGB triples; ``offset`` is the byte offset of the
    first triple in the keyboard's colour buffer.
    """
    if len(colors) % 3:
        raise ValueError(f"per-key colours must be whole RGB triples, got {len(colors)} bytes")
    if not 0 <= offset <= 0xFFFF:
        raise ValueError(f"offset must be 0..65535, got {offset}")
    return make_packet(CMD_SEND_DYNAMIC_COLORS, size=len(colors), offset=offset,
                       payload=colors)
