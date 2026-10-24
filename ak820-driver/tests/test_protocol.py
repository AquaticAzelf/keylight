"""Packet framing and the lighting record, checked against the reference layout."""

from ak820.protocol.lighting import make_per_key_packet, state_payload
from ak820.protocol.packet import (
    compute_checksum,
    make_begin,
    make_end,
    make_packet,
    parse_packet,
)


def test_begin_packet_is_fixed():
    p = make_begin()
    assert p[:4] == bytes([0x04, 0x01, 0x00, 0x01])
    assert len(p) == 64 and set(p[4:]) == {0}


def test_end_packet_is_fixed():
    p = make_end()
    assert p[:4] == bytes([0x04, 0x02, 0x00, 0x02])


def test_checksum_is_sum_of_bytes_3_to_63():
    buf = bytearray(64)
    buf[3] = 0x06
    buf[4] = 8
    buf[5] = 0
    buf[8:16] = bytes([1, 2, 3, 4, 5, 6, 7, 8])
    compute_checksum(buf)
    assert buf[1] == sum(buf[3:64]) & 0xFF
    assert buf[2] == (sum(buf[3:64]) >> 8) & 0xFF


def test_lighting_record_layout():
    assert state_payload(0x06, 4, 3, 0, False, 255, 0, 0) == bytes(
        [0x06, 4, 3, 0, 0, 255, 0, 0]
    )


def test_lighting_record_marks_random_colours():
    assert state_payload(0x04, 4, 3, 0, True, 0, 0, 0)[4] == 0xFF


def test_lighting_record_rejects_out_of_range_values():
    import pytest

    for args in (
        (0x06, 5, 3, 0, False, 0, 0, 0),
        (0x06, 4, 6, 0, False, 0, 0, 0),
        (0x06, 4, 3, 4, False, 0, 0, 0),
        (0x06, 4, 3, 0, False, 256, 0, 0),
    ):
        with pytest.raises(ValueError):
            state_payload(*args)


def test_per_key_packet_uses_the_dynamic_colour_command():
    p = make_per_key_packet(bytes([1, 2, 3, 4, 5, 6]), offset=12)
    assert p[3] == 0x12
    assert p[4] == 6
    assert p[5] == 12 and p[6] == 0
    assert p[8:14] == bytes([1, 2, 3, 4, 5, 6])


def test_begin_and_end_have_a_consistent_checksum():
    """The fixed bytes 1-2 of BEGIN/END happen to equal their own checksum."""
    for packet in (make_begin(), make_end()):
        assert parse_packet(packet)["checksum_ok"]


def test_parse_packet_reads_back_what_was_sent():
    payload = bytes([0x0A, 3, 2, 1, 0xFF, 10, 20, 30])
    p = make_packet(0x06, size=8, offset=0x41, payload=payload)
    parsed = parse_packet(p)
    assert parsed["command"] == 0x06
    assert parsed["size"] == 8
    assert parsed["offset"] == 0x41
    assert parsed["payload"] == payload
    assert parsed["checksum_ok"]


def test_parse_packet_reports_a_bad_checksum():
    p = bytearray(make_packet(0x06, size=8, offset=0x01,
                              payload=bytes([0x06, 4, 3, 0, 0, 255, 0, 0])))
    p[9] ^= 0xFF
    assert parse_packet(bytes(p))["checksum_ok"] is False
