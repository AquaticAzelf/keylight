"""The session sends BEGIN, the settings, then END."""

from ak820.protocol.session import KeyboardSession


class FakeDevice:
    def __init__(self):
        self.writes = []
        self.reads = 0

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def read(self, timeout_ms=200):
        self.reads += 1
        return bytes(64)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _session(monkeypatch):
    fake = FakeDevice()
    import ak820.protocol.session as s
    monkeypatch.setattr(s, "open_device", lambda p: fake)
    return fake, KeyboardSession(device=None)


def test_lighting_goes_into_the_profile_the_board_is_showing(monkeypatch):
    """A change goes into one profile, not into all three.

    The board keeps three lighting setups of its own, so they have to stay
    three different setups.
    """
    fake, sess = _session(monkeypatch)
    sess.apply_lighting(0x06, 4, 3, 0, False, 255, 0, 0)
    cmds = [w[3] for w in fake.writes]
    # A read of the profile index, then the write of that one profile and
    # the index itself.
    assert cmds == [0x01, 0x05, 0x02, 0x01, 0x06, 0x06, 0x02]
    assert [w[5] for w in fake.writes[4:6]] == [0x01, 0x00]
    assert fake.writes[4][8:16] == bytes([0x06, 4, 3, 0, 0, 255, 0, 0])


def test_the_profile_index_is_written_last_and_is_a_valid_index(monkeypatch):
    """A mode value in byte 0x00 leaves the board without a profile."""
    fake, sess = _session(monkeypatch)
    sess.apply_lighting(0xFF, 4, 3, 0, False, 0, 0, 0)
    last = fake.writes[-2]
    assert last[3] == 0x06 and last[5] == 0x00
    assert last[8] in (0, 1, 2)


def test_a_profile_index_outside_the_board_is_refused():
    import pytest

    with pytest.raises(ValueError):
        KeyboardSession(device=None).set_current_profile(6)


def test_per_key_colours_are_wrapped_the_same_way(monkeypatch):
    fake, sess = _session(monkeypatch)
    sess.set_per_key_colors(bytes([1, 2, 3]), offset=9)
    cmds = [w[3] for w in fake.writes]
    assert cmds == [0x01, 0x12, 0x13, 0x02]
    assert fake.writes[1][4] == 3
    assert fake.writes[1][5] == 9
    assert fake.writes[1][8:11] == bytes([1, 2, 3])


def test_a_reply_is_read_after_every_write(monkeypatch):
    fake, sess = _session(monkeypatch)
    sess.apply_lighting(0x06, 4, 3, 0, False, 255, 0, 0)
    assert fake.reads == len(fake.writes)


def test_the_device_is_closed_afterwards(monkeypatch):
    fake, sess = _session(monkeypatch)
    sess.apply_lighting(0x06, 4, 3, 0, False, 255, 0, 0)
    assert fake.writes  # the transaction happened
    # __exit__ ran, so a second transaction needs a fresh handle
    again = FakeDevice()
    import ak820.protocol.session as s
    monkeypatch.setattr(s, "open_device", lambda p: again)
    KeyboardSession(device=None).apply_lighting(0x06, 4, 3, 0, False, 255, 0, 0)
    assert len(again.writes) == 7


# -- the system settings (Windows Lock, Exchange Key, report rate) -----------

class RecordDevice(FakeDevice):
    """A board that answers config reads out of a record it keeps."""

    def __init__(self):
        super().__init__()
        self.record = bytearray(29)
        self.record[1] = 6  # a mode, so the record looks real
        self.record[2] = 4

    def read(self, timeout_ms=200):
        self.reads += 1
        last = self.writes[-1] if self.writes else None
        if last is not None and last[3] == 0x05:
            size, offset = last[4], last[5] | (last[6] << 8)
            reply = bytearray(64)
            reply[3] = 0x05
            reply[4] = size
            reply[5] = offset & 0xFF
            reply[6] = (offset >> 8) & 0xFF
            reply[8:8 + size] = self.record[offset:offset + size]
            return bytes(reply)
        return bytes(64)


def _record_session(monkeypatch):
    fake = RecordDevice()
    import ak820.protocol.session as s
    monkeypatch.setattr(s, "open_device", lambda p: fake)
    return fake, KeyboardSession(device=None)


def test_read_stages_sees_all_off_on_a_fresh_board(monkeypatch):
    _, sess = _record_session(monkeypatch)
    assert sess.read_stages() == {
        "exchange": 0,
        "win_lock": 0,
        "polling_rate": 0,
        "polling_hz": 1000,
    }


def test_set_stages_writes_the_whole_record_and_only_the_stage(monkeypatch):
    """The write is the official driver's: 29 bytes, everything carried over."""
    fake, sess = _record_session(monkeypatch)
    fake.record[0x14] = 0x21      # the N-key flag this app never drives
    fake.record[0x16] = 0x02      # already at 250 Hz
    fake.record[0x06:0x09] = b"\xF1\x80\x34"  # a lighting colour
    stages = sess.set_stages(win_lock=1)
    assert stages["win_lock"] == 1
    assert stages["polling_hz"] == 250
    # The one config write of the 29-byte record, inside BEGIN/END.
    cmds = [w[3] for w in fake.writes]
    assert cmds[0] == 0x01 and cmds[-1] == 0x02
    writes = [w for w in fake.writes if w[3] == 0x06]
    assert len(writes) == 1
    write = writes[0]
    assert write[4] == 29 and (write[5] | write[6] << 8) == 0
    payload = write[8:8 + 29]
    assert payload[0x15] == 1                     # the stage asked for
    assert payload[0x13] == 0                     # Exchange untouched
    assert payload[0x14] == 0x21                  # N-key untouched
    assert payload[0x16] == 0x02                  # rate untouched
    assert payload[0x06:0x09] == b"\xF1\x80\x34"  # lighting untouched


def test_set_stages_needs_a_steady_read(monkeypatch):
    """A board whose reads disagree is refused, not written over."""
    class Wobbly(RecordDevice):
        def read(self, timeout_ms=200):
            self.reads += 1
            if self.reads % 2:  # odd reads answer with yesterday's news
                return bytes(64)
            last = self.writes[-1] if self.writes else None
            if last is not None and last[3] == 0x05:
                size, offset = last[4], last[5] | (last[6] << 8)
                reply = bytearray(64)
                reply[3] = 0x05
                reply[4] = size
                reply[5] = offset & 0xFF
                reply[6] = (offset >> 8) & 0xFF
                reply[8:8 + size] = self.record[offset:offset + size]
                return bytes(reply)
            return bytes(64)

    fake = Wobbly()
    import ak820.protocol.session as s
    monkeypatch.setattr(s, "open_device", lambda p: fake)
    import pytest

    with pytest.raises(ValueError):
        KeyboardSession(device=None).set_stages(exchange=1)
    assert not [w for w in fake.writes if w[3] == 0x06]
