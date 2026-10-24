"""The JSON API: what it answers, and what it answers without a keyboard.

The tests run against a real loopback server, so the headers and status codes
are the ones the app actually receives.  A fake board stands in for the
keyboard: it keeps a config space like the real one, so nothing here needs
hardware.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from ak820.api import Ak820Service, Api
from ak820.hid.device import HidError, HidPath
from ak820.server import create_server

FAKE_DEVICE = HidPath(
    path="fake",
    vid=0x320F,
    pid=0x505B,
    usage_page=0xFF1C,
    usage=0x46,
    interface=1,
)

LIGHTING = {"mode": 6, "brightness": 4, "speed": 3, "direction": 0, "color": [255, 0, 0]}

#: The board keeps three profile blocks and one byte naming the one on show.
PROFILE_OFFSETS = (0x01, 0x41, 0x81)


class FakeSession:
    """A keyboard that answers like the AK820, without any hardware."""

    def __init__(self) -> None:
        self.config = bytearray(256)
        self.colors = bytearray(378)
        self.lighting_writes: list[tuple] = []
        self.key_writes: list[tuple] = []

    def read_config(self, offset: int, size: int) -> bytes:
        return bytes(self.config[offset:offset + size])

    def read_lighting(self, profile: int = 0) -> dict:
        base = PROFILE_OFFSETS[profile]
        mode, brightness, speed, direction, random, red, green, blue = (
            self.config[base:base + 8]
        )
        return {
            "mode": mode,
            "brightness": brightness,
            "speed": speed,
            "direction": direction,
            "random": bool(random),
            "color": [red, green, blue],
        }

    def write_config(self, offset: int, data: bytes) -> bytes:
        self.config[offset:offset + len(data)] = data
        return bytes(64)

    def current_profile(self) -> int:
        index = self.config[0]
        return index if index < len(PROFILE_OFFSETS) else 0

    def set_current_profile(self, index: int) -> list:
        self.config[0] = index
        return []

    def read_current_lighting(self) -> dict:
        base = PROFILE_OFFSETS[self.current_profile()]
        mode, brightness, speed, direction, random, red, green, blue = (
            self.config[base:base + 8]
        )
        return {
            "mode": mode,
            "brightness": brightness,
            "speed": speed,
            "direction": direction,
            "random": bool(random),
            "color": [red, green, blue],
        }

    def apply_lighting(self, mode, brightness, speed, direction, random, r, g, b):
        self.lighting_writes.append((mode, brightness, speed, direction, random, r, g, b))
        record = bytes([mode, brightness, speed, direction, 0xFF if random else 0, r, g, b])
        for base in PROFILE_OFFSETS:
            self.config[base:base + 8] = record
        self.config[0] = 0
        return []

    def set_per_key_colors(self, colors: bytes, offset: int = 0):
        self.key_writes.append((bytes(colors), offset))
        self.colors[offset:offset + len(colors)] = colors
        return []

    def read_custom_colors(self, size: int = 378) -> bytes:
        return bytes(self.colors[:size])

    def read_capabilities(self) -> dict:
        return {"supported": True, "map_size": 128, "macros_size": 10240}

    def write_custom_colors(self, colors: bytes, offset: int = 0):
        self.colors[offset:offset + len(colors)] = colors
        return []

    def set_lighting(self, mode, brightness, speed, direction, random, r, g, b,
                     profile: int = 0, all_profiles: bool = True):
        self.lighting_writes.append((mode, brightness, speed, direction, random, r, g, b))
        # The board keeps the record, so that reading it back gives it.
        record = bytes([mode, brightness, speed, direction, 0xFF if random else 0, r, g, b])
        bases = PROFILE_OFFSETS if all_profiles else (PROFILE_OFFSETS[profile],)
        for base in bases:
            self.config[base:base + 8] = record
        self.config[0] = profile
        return []

    def read_stages(self) -> dict:
        from ak820.protocol.stages import parse_stages
        return parse_stages(bytes(self.config[:29]))

    def set_stages(self, exchange=None, win_lock=None, polling_rate=None) -> dict:
        from ak820.protocol.stages import patch_stages
        updated = patch_stages(bytes(self.config[:29]), exchange=exchange,
                               win_lock=win_lock, polling_rate=polling_rate)
        self.config[0:29] = updated
        return self.read_stages()


class FakeBoard:
    """A board the API can talk to, with a known set of lighting modes."""

    def __init__(self, supported_modes=(1, 6)) -> None:
        self.session = FakeSession()
        self.supported_modes = supported_modes

    def service(self) -> Ak820Service:
        return Ak820Service(
            device_finder=lambda: FAKE_DEVICE,
            session_factory=lambda device: self.session,
            mode_support=lambda: self.supported_modes,
        )


def request(server, method: str, path: str, payload=None):
    """Ask the server something. Returns (status, content-type, body)."""
    url = f"http://127.0.0.1:{server.server_address[1]}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    call = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(call, timeout=5) as response:
            return response.status, response.headers.get("Content-Type"), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Content-Type"), error.read()


@pytest.fixture
def server():
    """A real server on a free port, torn down after the test."""
    made: list = []

    def start(service):
        made.append(create_server(Api(service), port=0))
        thread = threading.Thread(target=made[-1].serve_forever, kwargs={"poll_interval": 0.05},
                                  daemon=True)
        thread.start()
        return made[-1]

    yield start
    for one in made:
        one.shutdown()
        one.server_close()


# -- the disconnected case, which is the common one ------------------------


def test_status_answers_without_a_keyboard(server):
    """No keyboard must never raise; it is the normal state on this machine."""
    status, content_type, body = request(server(Ak820Service(device_finder=lambda: None)),
                                        "GET", "/api/status")
    assert status == 200
    assert content_type == "application/json"
    payload = json.loads(body)
    assert payload["connected"] is False
    assert payload["device"] is None
    assert payload["version"]


def test_status_answers_when_the_keyboard_is_held_by_another_tool(server):
    """A busy device is a device we cannot use, not a crash."""
    def busy():
        raise HidError("Another program is using the keyboard.")

    status, content_type, body = request(server(Ak820Service(device_finder=busy)),
                                        "GET", "/api/status")
    assert status == 200
    assert content_type == "application/json"
    assert json.loads(body)["connected"] is False


def test_the_lighting_routes_report_that_no_keyboard_is_there(server):
    """The lighting routes answer 503 with a message, not with a traceback."""
    for method, path, payload in (
        ("GET", "/api/lighting", None),
        ("POST", "/api/lighting", LIGHTING),
        ("POST", "/api/keys/colors", {"led": 12, "color": [1, 2, 3]}),
    ):
        status, content_type, body = request(server(Ak820Service(device_finder=lambda: None)),
                                            method, path, payload)
        assert status == 503, path
        assert content_type == "application/json", path
        assert json.loads(body)["error"], path


# -- the modes the board actually implements --------------------------------


def test_modes_lists_only_what_the_board_reports_as_supported(server):
    board = FakeBoard(supported_modes=(1, 6))
    status, content_type, body = request(server(board.service()), "GET", "/api/modes")
    assert status == 200
    assert content_type == "application/json"
    modes = json.loads(body)["modes"]
    assert [mode["id"] for mode in modes] == [1, 6]
    assert all(mode["supported"] for mode in modes)
    assert {mode["id"]: mode["name"] for mode in modes} == {1: "Wave", 6: "Static"}


def test_a_mode_the_board_rejects_is_absent(server):
    """A control the keyboard would ignore must not be offered."""
    board = FakeBoard(supported_modes=(6,))
    _, _, body = request(server(board.service()), "GET", "/api/modes")
    modes = json.loads(body)["modes"]
    assert 1 not in [mode["id"] for mode in modes]


@pytest.fixture
def fresh_data_dir(tmp_path, monkeypatch):
    """A data folder of its own.

    Some of the routes write files - a profile, a macro. A test that
    walks them all needs a folder of its own, or the files it leaves
    behind turn up in the next test.
    """
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AK820_SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


# -- every route -----------------------------------------------------------

#: The routes the test walks. Every one of them is asked for, so a new route
#: that forgets an argument is caught here rather than in the app.
ROUTES = (
    ("GET", "/api/status", None),
    ("GET", "/api/modes", None),
    ("GET", "/api/lighting", None),
    ("POST", "/api/lighting", LIGHTING),
    ("GET", "/api/keys", None),
    ("GET", "/api/keys/colors", None),
    ("POST", "/api/keys/colors", {"led": 12, "color": [10, 20, 30]}),
    ("GET", "/api/profiles", None),
    ("POST", "/api/profiles", {"name": "Desk"}),
    ("POST", "/api/profiles/export", {"name": "Desk"}),
    ("POST", "/api/profiles/import", {"path": "Desk.json"}),
    ("POST", "/api/profiles/duplicate", {"name": "Desk", "new_name": "Desk copy"}),
    ("GET", "/api/board-profiles", None),
    ("POST", "/api/board-profiles", {"index": 0}),
    ("POST", "/api/board-profiles/use", {"index": 0}),
    ("GET", "/api/system-stages", None),
    ("POST", "/api/system-stages", {"win_lock": 1}),
    ("GET", "/api/macros", None),
    ("POST", "/api/macros", {"name": "Hi", "events": [{"vk": 65, "down": True}]}),
    ("POST", "/api/macros/reorder", {"name": "Hi", "to": 0}),
    ("POST", "/api/macros/play", {"name": "Hi"}),
    ("GET", "/api/remap", None),
    ("POST", "/api/remap", {"active": False, "mapping": {}}),
    ("GET", "/api/board-info", None),
    ("GET", "/api/settings", None),
    ("POST", "/api/settings", {"key": "theme", "value": "dark"}),
    ("POST", "/api/settings/reset", {}),
    ("POST", "/api/lighting/reset", {}),
    ("GET", "/api/colours/favourites", None),
    ("POST", "/api/colours/favourites", {"color": [10, 20, 30]}),
)

#: The routes the test does not walk: they put a hook on the keyboard of the
#: machine the tests run on, which is not a thing a test should do.
EXCLUDED_ROUTES = (
    ("POST", "/api/macros/record"),
    ("POST", "/api/macros/record/stop"),
)


def test_the_test_walks_every_route_the_api_has():
    """A new route must be put in the list above, so it gets tested too."""
    from ak820.api import Api

    known = {path for _, path in Api()._routes}
    listed = {path for _, path, _ in ROUTES} | {path for _, path in EXCLUDED_ROUTES}
    missing = known - listed
    assert not missing, f"these routes are not tested: {sorted(missing)}"


def test_every_route_answers_json(server, fresh_data_dir):
    for method, path, payload in ROUTES:
        status, content_type, body = request(server(FakeBoard().service()), method, path, payload)
        assert status == 200, path
        assert content_type == "application/json", path
        assert isinstance(json.loads(body), dict), path


def test_every_route_answers_json_even_when_it_fails(server, fresh_data_dir):
    """The disconnected case still answers JSON on every route."""
    for method, path, payload in ROUTES:
        status, content_type, body = request(server(Ak820Service(device_finder=lambda: None)),
                                            method, path, payload)
        assert content_type == "application/json", path
        assert status in (200, 400, 503), path
        assert isinstance(json.loads(body), dict), path


def test_an_unknown_endpoint_answers_json(server):
    status, content_type, body = request(server(FakeBoard().service()), "GET", "/api/nope")
    assert status == 404
    assert content_type == "application/json"
    assert json.loads(body)["error"]


def test_a_wrong_method_answers_json(server):
    status, content_type, body = request(server(FakeBoard().service()), "POST", "/api/status", {})
    assert status == 405
    assert content_type == "application/json"
    assert json.loads(body)["error"]


def test_a_broken_body_answers_json(server):
    status, content_type, body = request(server(FakeBoard().service()), "POST", "/api/profiles",
                                        {"name": ""})
    assert status == 400
    assert content_type == "application/json"
    assert json.loads(body)["error"]


def test_an_out_of_range_setting_answers_json(server):
    status, content_type, body = request(server(FakeBoard().service()), "POST", "/api/lighting",
                                        {"mode": 6, "brightness": 9, "speed": 3,
                                         "direction": 0, "color": [255, 0, 0]})
    assert status == 400
    assert content_type == "application/json"
    assert json.loads(body)["error"]


# -- what the routes do ----------------------------------------------------


def test_lighting_is_written_to_the_board(server):
    board = FakeBoard()
    status, _, body = request(server(board.service()), "POST", "/api/lighting", LIGHTING)
    assert status == 200
    assert json.loads(body) == LIGHTING
    assert board.session.lighting_writes == [(6, 4, 3, 0, False, 255, 0, 0)]


def test_lighting_is_read_back_from_the_board(server):
    board = FakeBoard()
    board.session.config[1:9] = bytes([6, 4, 3, 0, 0, 255, 0, 0])
    _, _, body = request(server(board.service()), "GET", "/api/lighting")
    assert json.loads(body) == LIGHTING


def test_a_key_colour_is_written_at_the_led_offset(server):
    """One key is painted; the rest of the buffer goes along unchanged.

    The board is fed a whole run of colours, so the API sends the whole
    buffer with the one key changed - not a single triple.
    """
    board = FakeBoard()
    status, _, body = request(server(board.service()), "POST", "/api/keys/colors",
                              {"led": 12, "color": [10, 20, 30]})
    assert status == 200
    assert json.loads(body) == {"ok": True, "led": 12, "color": [10, 20, 30]}
    written, offset = board.session.key_writes[0]
    assert offset == 0
    assert written[36:39] == bytes([10, 20, 30])
    assert written[:36] == bytes(36)
    assert written[39:] == bytes(378 - 39)


def test_the_colour_buffer_is_read_back(server):
    """The board's own colours come back, so the editor can start from them."""
    board = FakeBoard()
    board.session.colors[0:3] = bytes([1, 2, 3])
    status, _, body = request(server(board.service()), "GET", "/api/keys/colors")
    assert status == 200
    payload = json.loads(body)
    assert payload["count"] == 126
    assert payload["colors"][0] == [1, 2, 3]


def test_the_whole_buffer_can_be_written(server):
    """The per-key editor sends the whole buffer when it paints."""
    board = FakeBoard()
    colors = [[10, 20, 30]] * 126
    status, _, body = request(server(board.service()), "POST", "/api/keys/colors",
                              {"colors": colors})
    assert status == 200
    assert json.loads(body) == {"ok": True, "count": 126}
    written, offset = board.session.key_writes[0]
    assert offset == 0
    assert written == bytes([10, 20, 30]) * 126


def test_painting_a_key_keeps_the_rest_of_the_lighting(server):
    """Painting a key must not change the brightness, speed or colour.

    The board only shows per-key colours in the custom effect, so the effect
    has to change - but nothing else may.
    """
    board = FakeBoard()
    service = board.service()
    request(server(service), "POST", "/api/lighting",
            {"mode": 8, "brightness": 2, "speed": 1, "direction": 1,
             "color": [12, 34, 56]})
    board.session.lighting_writes.clear()

    status, _, _ = request(server(service), "POST", "/api/keys/colors",
                           {"led": 4, "color": [9, 9, 9]})
    assert status == 200
    assert board.session.lighting_writes == [(20, 2, 1, 1, False, 12, 34, 56)]


def test_the_status_says_when_another_program_is_holding_the_keyboard(server):
    """A keyboard that is on the bus but cannot be opened is busy, not gone."""
    from ak820 import api as api_module

    service = Ak820Service(device_finder=lambda: None)
    original = api_module.list_interface_paths
    api_module.list_interface_paths = lambda vid, pid: ["\\\\?\\hid#vid_320f&pid_505b#1"]
    try:
        status, _, body = request(server(service), "GET", "/api/status")
    finally:
        api_module.list_interface_paths = original
    payload = json.loads(body)
    assert status == 200
    assert payload["connected"] is False
    assert payload["device_state"] == "busy"
    assert "Another program" in payload["message"]


def test_the_status_says_when_the_keyboard_is_not_plugged_in(server):
    """No keyboard and nothing on the bus is simply missing."""
    from ak820 import api as api_module

    service = Ak820Service(device_finder=lambda: None)
    original = api_module.list_interface_paths
    api_module.list_interface_paths = lambda vid, pid: []
    try:
        status, _, body = request(server(service), "GET", "/api/status")
    finally:
        api_module.list_interface_paths = original
    payload = json.loads(body)
    assert payload["connected"] is False
    assert payload["device_state"] == "missing"


def test_the_keys_route_answers_the_board_layout(server):
    _, _, body = request(server(FakeBoard().service()), "GET", "/api/keys")
    payload = json.loads(body)
    assert len(payload["keys"]) == 82
    assert payload["keys"][0]["label"] == "Esc"
    assert payload["knob"]["kind"] == "knob"


def test_a_profile_is_created_and_kept(server):
    api = server(FakeBoard().service())
    status, _, body = request(api, "POST", "/api/profiles", {"name": "Desk"})
    assert status == 200
    assert json.loads(body)["name"] == "Desk"
    _, _, body = request(api, "GET", "/api/profiles")
    assert [profile["name"] for profile in json.loads(body)["profiles"]] == ["Desk"]


def test_the_settings_route_answers_json(server):
    status, content_type, body = request(server(FakeBoard().service()), "GET", "/api/settings")
    assert status == 200
    assert content_type == "application/json"
    payload = json.loads(body)
    assert isinstance(payload["settings"], list)
    keys = {setting["key"] for setting in payload["settings"]}
    assert "theme" in keys
    assert payload["folders"]["profiles"]


def test_the_api_can_be_called_without_a_socket():
    """The routes are plain functions, so the app can be driven without HTTP."""
    api = Api(Ak820Service(device_finder=lambda: None))
    status, payload = api.handle("GET", "/api/status")
    assert status == 200
    assert payload["connected"] is False
    status, payload = api.handle("GET", "/api/lighting")
    assert status == 503
    assert payload["error"]


# -- the system settings (Windows Lock, Exchange Key, report rate) -----------

def test_system_stages_read_all_off_from_a_fresh_board(server):
    board = FakeBoard()
    status, _, body = request(server(board.service()), "GET", "/api/system-stages")
    assert status == 200
    assert json.loads(body) == {"exchange": 0, "win_lock": 0,
                                "polling_rate": 0, "polling_hz": 1000}


def test_setting_windows_lock_flips_only_its_byte(server):
    board = FakeBoard()
    board.session.config[0x14] = 0x21  # the N-key flag, never driven by us
    status, _, body = request(server(board.service()), "POST", "/api/system-stages",
                              {"win_lock": 1})
    assert status == 200
    payload = json.loads(body)
    assert payload["win_lock"] == 1 and payload["exchange"] == 0
    config = board.session.config
    assert config[0x15] == 1
    assert config[0x13] == 0 and config[0x14] == 0x21 and config[0x16] == 0


def test_the_report_rate_takes_its_index_not_its_hertz(server):
    board = FakeBoard()
    status, _, body = request(server(board.service()), "POST", "/api/system-stages",
                              {"polling_rate": 3})
    assert status == 200
    assert json.loads(body)["polling_hz"] == 125
    assert board.session.config[0x16] == 3


def test_all_three_can_change_in_one_call(server):
    board = FakeBoard()
    status, _, body = request(server(board.service()), "POST", "/api/system-stages",
                              {"exchange": 1, "win_lock": 1, "polling_rate": 1})
    assert status == 200
    assert board.session.config[0x13:0x17] == bytearray([1, 0, 1, 1])


def test_a_bad_stage_value_is_a_400_not_a_write(server):
    board = FakeBoard()
    for bad in ({"win_lock": 2}, {"exchange": -1}, {"polling_rate": 4}, {}):
        status, _, body = request(server(board.service()), "POST", "/api/system-stages", bad)
        assert status == 400, bad
        assert json.loads(body)["error"], bad
    assert board.session.config[0x13:0x17] == bytearray(4)


def test_system_stages_report_a_missing_keyboard(server):
    status, _, body = request(server(Ak820Service(device_finder=lambda: None)),
                              "GET", "/api/system-stages")
    assert status == 503
    assert json.loads(body)["error"]
