"""Talking to the keyboard as a session: a BEGIN, some writes, an END.

The handle is opened per transaction and closed again, so other HID tools can
still use the keyboard between calls.
"""

from __future__ import annotations

from ak820.hid.device import HidPath, open_device

from .lighting import state_payload
from .packet import make_begin, make_end, make_packet
from .stages import RECORD_SIZE, parse_stages, patch_stages
from .v2 import (
    CMD_END_DYNAMIC_COLORS,
    CMD_READ_CAPABILITIES,
    CMD_READ_CONFIG,
    CMD_READ_CUSTOM_COLORS,
    CMD_SEND_DYNAMIC_COLORS,
    CMD_WRITE_CONFIG,
    CMD_WRITE_CUSTOM_COLORS,
    MAX_PAYLOAD,
    OFFSET_CURRENT_PROFILE,
    PROFILE_COUNT,
    parse_capabilities,
    profile_offset,
)


class KeyboardSession:
    """Writes lighting settings to one keyboard."""

    def __init__(self, device: HidPath | None = None) -> None:
        self.device = device

    def _transact(self, packets: list[bytes]) -> list[bytes | None]:
        """Send BEGIN, the given packets, then END. Returns the reply to each write."""
        def run(device):
            replies: list[bytes | None] = []
            for packet in [make_begin(), *packets, make_end()]:
                device.write(packet)
                replies.append(device.read())
            return replies

        with open_device(self.device) as device:
            return run(device)

    def apply_lighting(self, mode: int, brightness: int, speed: int, direction: int,
                       random: bool, r: int, g: int, b: int) -> list[bytes | None]:
        """Set the backlight of the profile the board is showing.

        The board keeps three lighting profiles of its own, and they are
        meant to be three different setups. So a change goes into the one
        that is on screen, and the other two are left as they were.
        """
        index = self.current_profile()
        return self.set_lighting(mode, brightness, speed, direction, random, r, g, b,
                                profile=index, all_profiles=False)

    def set_lighting(self, mode: int, brightness: int, speed: int, direction: int,
                     random: bool, r: int, g: int, b: int, profile: int = 0,
                     all_profiles: bool = True) -> list[bytes | None]:
        """Set the backlight the way the board expects it.

        The board keeps three profile blocks and shows one of them. Byte 0x00
        of the config space is the *index* of the profile on show - not a
        setting - so a value outside 0..2 leaves the board without a profile
        and it falls back to cycling through its own effects.

        The record is therefore written into the profile block first and the
        index last.
        """
        payload = state_payload(mode, brightness, speed, direction, random, r, g, b)
        targets = range(PROFILE_COUNT) if all_profiles else (profile,)
        packets = [self._config_write(profile_offset(i), payload) for i in targets]
        packets.append(self._config_write(OFFSET_CURRENT_PROFILE, bytes([profile])))
        return self._transact(packets)

    def set_current_profile(self, index: int) -> list[bytes | None]:
        """Point the board at one of its three profiles."""
        if not 0 <= index < PROFILE_COUNT:
            raise ValueError(f"profile index must be 0..{PROFILE_COUNT - 1}, got {index}")
        return self._transact([self._config_write(OFFSET_CURRENT_PROFILE, bytes([index]))])

    @staticmethod
    def _config_write(offset: int, data: bytes) -> bytes:
        return make_packet(CMD_WRITE_CONFIG, size=len(data), offset=offset, payload=data)

    def read_lighting(self, profile: int = 0) -> dict:
        """Read back the lighting state of a profile."""
        data = self.read_config(profile_offset(profile), 8)
        if len(data) < 8:
            return {}
        return {
            "mode": data[0],
            "brightness": data[1],
            "speed": data[2],
            "direction": data[3],
            "random": data[4] != 0,
            "color": [data[5], data[6], data[7]],
        }

    def read_current_lighting(self) -> dict:
        """Read back the lighting of the profile the board is showing."""
        return self.read_lighting(self.current_profile())

    def current_profile(self) -> int:
        """Which profile the board is showing.

        A value outside 0..2 means the board is in a state we did not put it
        in, so profile 0 is assumed rather than trusting it.
        """
        data = self.read_config(OFFSET_CURRENT_PROFILE, 1)
        index = data[0] if data else 0
        return index if index < PROFILE_COUNT else 0

    def set_per_key_colors(self, colors: bytes, offset: int = 0) -> list[bytes | None]:
        """Write per-key RGB triples into the board's colour buffer."""
        if len(colors) % 3:
            raise ValueError(f"per-key colours must be whole RGB triples, got {len(colors)} bytes")
        packets = []
        at = 0
        while at < len(colors):
            chunk = colors[at:at + MAX_PAYLOAD]
            packets.append(make_packet(CMD_SEND_DYNAMIC_COLORS, size=len(chunk),
                                       offset=offset + at, payload=chunk))
            at += len(chunk)
        packets.append(make_packet(CMD_END_DYNAMIC_COLORS, size=0, offset=0, payload=b""))
        return self._transact(packets)

    def read_custom_colors(self, size: int = 378) -> bytes:
        """Read the board's colour buffer - three bytes per key."""
        chunks: list[bytes] = []
        at = 0
        while at < size:
            count = min(size - at, MAX_PAYLOAD)
            reply = self.query(CMD_READ_CUSTOM_COLORS, offset=at, size=count)
            if reply is None:
                break
            chunks.append(reply[8:8 + count])
            at += count
        return b"".join(chunks)

    def write_custom_colors(self, colors: bytes, offset: int = 0) -> list[bytes | None]:
        """Write the board's stored colour buffer, the one it keeps."""
        if len(colors) % 3:
            raise ValueError(f"colours must be whole RGB triples, got {len(colors)} bytes")
        packets = []
        at = 0
        while at < len(colors):
            chunk = colors[at:at + MAX_PAYLOAD]
            packets.append(make_packet(CMD_WRITE_CUSTOM_COLORS, size=len(chunk),
                                       offset=offset + at, payload=chunk))
            at += len(chunk)
        return self._transact(packets)

    def read_stages(self) -> dict:
        """The system settings (Windows Lock, Exchange Key, polling rate).

        Read from the live record at config 0x0000, twice, because the
        board can answer a config read with a reply left over from an
        earlier transaction.  Only matching reads are believed.
        """
        first = self.read_config(0x0000, RECORD_SIZE)
        second = self.read_config(0x0000, RECORD_SIZE)
        if len(first) < RECORD_SIZE or first != second:
            raise ValueError("the board did not answer a steady config read")
        return parse_stages(first)

    def set_stages(self, exchange: int | None = None, win_lock: int | None = None,
                   polling_rate: int | None = None) -> dict:
        """Change system settings, leaving every other byte as it was.

        The record is read back, the one stage asked for is patched into
        it, and the whole 29 bytes go out again - the same read-modify-
        write the official driver does, so the lighting bytes and the
        flags this app does not drive are carried over, not zeroed.
        """
        record = None
        for _ in range(2):
            first = self.read_config(0x0000, RECORD_SIZE)
            second = self.read_config(0x0000, RECORD_SIZE)
            if len(first) == RECORD_SIZE and first == second:
                record = first
                break
        if record is None:
            raise ValueError("the board did not answer a steady config read")
        updated = patch_stages(record, exchange=exchange, win_lock=win_lock,
                               polling_rate=polling_rate)
        self._transact([self._config_write(0x0000, updated)])
        return parse_stages(updated)

    def read_reply(self, timeout_ms: int = 200) -> bytes | None:
        """Read one reply without sending anything."""
        with open_device(self.device) as device:
            return device.read(timeout_ms)

    # -- V2 queries -------------------------------------------------------

    def query(self, command: int, offset: int = 0, size: int = 0,
              payload: bytes = b"") -> bytes | None:
        """Send one command and return the reply packet."""
        packet = make_packet(command, size=size, offset=offset, payload=payload)
        return self._transact([packet])[1]

    def read_config(self, offset: int, size: int) -> bytes:
        """Read ``size`` bytes of config space, one 56-byte packet at a time."""
        chunks: list[bytes] = []
        remaining = size
        at = offset
        while remaining > 0:
            count = min(remaining, MAX_PAYLOAD)
            reply = self.query(CMD_READ_CONFIG, offset=at, size=count)
            if reply is None:
                break
            chunks.append(reply[8:8 + count])
            at += count
            remaining -= count
        return b"".join(chunks)

    def write_config(self, offset: int, data: bytes) -> bytes | None:
        """Write raw bytes into config space."""
        return self.query(CMD_WRITE_CONFIG, offset=offset, size=len(data), payload=data)

    def read_capabilities(self) -> dict | None:
        """Ask the board what it can do, or ``None`` if it does not answer."""
        reply = self.query(CMD_READ_CAPABILITIES, offset=0, size=7)
        if reply is None:
            return None
        return parse_capabilities(reply[8:15])
