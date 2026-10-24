"""The system settings the board keeps in its live config record.

The offsets are not a guess: they come from the vendor's own app.  Its
writer (``main_app.exe`` at ``0x00492b30``, reached from the option
handlers for ``winlockflag_option`` / ``wflag_option`` /
``polling_rate_option_0..3``) builds one 29-byte record and sends it with
WRITE_CONFIG at offset 0x0000, copying each stage byte out of the packed
``SystemStages`` struct by name:

    0x13  WFlag        Exchange Key (swap Win and Alt)   0 or 1
    0x14  Key6Flag     the N-key setting, hidden on this board
    0x15  WinFlag      Windows Lock                      0 or 1
    0x16  PollingRate  0..3 = 1000 / 500 / 250 / 125 Hz
    0x1B  MacMode
    0x1C  Wheel

A capture of the official driver (``.scratch/capture-official-full.jsonl``)
confirms the two toggles: a click of Windows Lock flips byte 0x15 and a
click of Exchange Key flips byte 0x13, each in a plain 29-byte write.  The
polling byte (0x16) holds the option index, 0 meaning 1000 Hz - the value
the board ships with and the one the capture shows.
"""

from __future__ import annotations

#: The record the official app writes at config offset 0x0000.
RECORD_SIZE = 29

OFFSET_EXCHANGE = 0x13
OFFSET_KEY6 = 0x14
OFFSET_WIN_LOCK = 0x15
OFFSET_POLLING_RATE = 0x16
OFFSET_MAC_MODE = 0x1B
OFFSET_WHEEL = 0x1C

#: The polling byte is the index into this tuple.
POLLING_RATES = (1000, 500, 250, 125)

POLLING_MIN = 0
POLLING_MAX = len(POLLING_RATES) - 1


def parse_stages(record: bytes) -> dict:
    """The stages as the board holds them, read out of the live record."""
    if len(record) < RECORD_SIZE:
        raise ValueError(
            f"the config record is {len(record)} bytes, expected {RECORD_SIZE}")
    rate = record[OFFSET_POLLING_RATE]
    return {
        "exchange": 1 if record[OFFSET_EXCHANGE] else 0,
        "win_lock": 1 if record[OFFSET_WIN_LOCK] else 0,
        "polling_rate": rate if rate <= POLLING_MAX else POLLING_MIN,
        "polling_hz": POLLING_RATES[rate] if rate <= POLLING_MAX else POLLING_RATES[0],
    }


def patch_stages(record: bytes, exchange: int | None = None,
                 win_lock: int | None = None,
                 polling_rate: int | None = None) -> bytes:
    """A new 29-byte record with only the asked-for stages changed.

    Everything else - the lighting bytes, the flags this app does not
    drive - is carried over untouched, exactly as the official app's
    writer carries them, so setting one stage never disturbs another.
    """
    if len(record) < RECORD_SIZE:
        raise ValueError(
            f"the config record is {len(record)} bytes, expected {RECORD_SIZE}")
    out = bytearray(record[:RECORD_SIZE])
    if exchange is not None:
        if exchange not in (0, 1):
            raise ValueError(f"exchange must be 0 or 1, got {exchange}")
        out[OFFSET_EXCHANGE] = exchange
    if win_lock is not None:
        if win_lock not in (0, 1):
            raise ValueError(f"win_lock must be 0 or 1, got {win_lock}")
        out[OFFSET_WIN_LOCK] = win_lock
    if polling_rate is not None:
        if not POLLING_MIN <= polling_rate <= POLLING_MAX:
            raise ValueError(
                f"polling_rate must be {POLLING_MIN}..{POLLING_MAX}, got {polling_rate}")
        out[OFFSET_POLLING_RATE] = polling_rate
    return bytes(out)
