"""Building and reading EVision V1 packets.

A packet is 64 bytes:

    byte 0      report id (0x04)
    byte 1-2    checksum, u16 little endian, sum of bytes 3..63
    byte 3      command
    byte 4      size
    byte 5-6    parameter id, or a u16 little endian offset
    byte 7      0
    byte 8-63   payload
"""

from __future__ import annotations

from .commands import CMD_BEGIN, CMD_END

REPORT_ID = 0x04
PACKET_SIZE = 64
PAYLOAD_OFFSET = 8


def compute_checksum(buf: bytearray) -> None:
    """Write the checksum into bytes 1-2, in place. Sum of bytes 3..63."""
    total = sum(buf[3:PACKET_SIZE])
    buf[1] = total & 0xFF
    buf[2] = (total >> 8) & 0xFF


def make_packet(command: int, size: int = 0, param: int = 0, offset: int = 0,
                payload: bytes = b"", *, checksum: bool = True) -> bytes:
    """Build a 64-byte packet.

    ``param`` lands in byte 5 and is what SET_PARAMETER uses. ``offset`` is the
    u16 little endian pair in bytes 5-6 and is what the LED-data command uses.
    They share a field, so a non-zero ``offset`` wins; the LED-data command is
    the only one that ever carries one.
    """
    if len(payload) > PACKET_SIZE - PAYLOAD_OFFSET:
        raise ValueError(f"payload too long: {len(payload)} bytes")
    buf = bytearray(PACKET_SIZE)
    buf[0] = REPORT_ID
    buf[3] = command
    buf[4] = size
    if offset:
        buf[5] = offset & 0xFF
        buf[6] = (offset >> 8) & 0xFF
    else:
        buf[5] = param
    buf[PAYLOAD_OFFSET:PAYLOAD_OFFSET + len(payload)] = payload
    if checksum:
        compute_checksum(buf)
    return bytes(buf)


def parse_packet(raw: bytes) -> dict:
    """Read a packet back into its fields."""
    if len(raw) < PACKET_SIZE:
        raise ValueError(f"packet must be {PACKET_SIZE} bytes, got {len(raw)}")
    buf = bytearray(raw[:PACKET_SIZE])
    expected = bytearray(buf)
    compute_checksum(expected)
    size = buf[4]
    return {
        "report_id": buf[0],
        "command": buf[3],
        "size": size,
        "param": buf[5],
        "offset": buf[5] | (buf[6] << 8),
        "payload": bytes(buf[PAYLOAD_OFFSET:PAYLOAD_OFFSET + size]),
        "checksum_ok": bytes(expected[1:3]) == bytes(buf[1:3]),
    }


def make_begin() -> bytes:
    """The BEGIN packet. Fixed contents, no checksum step of its own."""
    buf = bytearray(PACKET_SIZE)
    buf[0] = REPORT_ID
    buf[1] = CMD_BEGIN
    buf[3] = CMD_BEGIN
    return bytes(buf)


def make_end() -> bytes:
    """The END packet. Fixed contents, no checksum step of its own."""
    buf = bytearray(PACKET_SIZE)
    buf[0] = REPORT_ID
    buf[1] = CMD_END
    buf[3] = CMD_END
    return bytes(buf)
