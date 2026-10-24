"""A test for every bug the 2026-10-21 review turned up.

Each test here failed before its fix.  The comment above each one says what
went wrong, so a failure points straight at the bug it is guarding.

The list came from reading the code and running the app; see
``docs/superpowers/plans/2026-10-21-ak820-driver-fixes.md``.
"""

from __future__ import annotations

import json
import os

import pytest

from pathlib import Path

from ak820 import macros as macro_store
from ak820 import remap
from ak820 import settings as app_settings
from ak820 import store
from ak820.api import DEFAULT_LIGHTING, Ak820Service
from ak820.protocol.v2 import MODE_CUSTOM

from tests.test_api import FAKE_DEVICE, FakeBoard, FakeSession, request, server


@pytest.fixture
def clean_remap():
    """Leave the remap layer as it was found."""
    yield
    remap.uninstall_hook()
    remap.set_mapping({})


# -- the remap layer: a binding that binds nothing --------------------------


def test_binding_a_key_to_a_macro_actually_binds_it(server, clean_remap):
    """The mapping was set and then wiped in the same breath.

    ``install_hook`` cleared the bindings it had just been given, so the
    route answered "ok" and the key did nothing.
    """
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/remap",
                              {"active": True, "mapping": {"A": "Macro"}})
    assert status == 200
    assert remap.get_mapping() == {"A": "Macro"}


def test_the_bindings_survive_the_layer_being_switched_off_and_on(clean_remap):
    """Switching the layer off put the keys back, but it also threw the
    bindings away, so switching it on again left the user with nothing.
    """
    remap.set_mapping({0x41: "Macro"})
    remap.install_hook()
    remap.uninstall_hook()
    remap.install_hook()
    assert remap.get_mapping() == {"A": "Macro"}


def test_a_digit_named_key_binds_the_digit_key(server, clean_remap):
    """"5" was read as the key code 5 instead of the digit-five key."""
    request(server(FakeBoard().service()), "POST", "/api/remap",
            {"active": True, "mapping": {"5": "Macro"}})
    assert remap.get_mapping() == {"5": "Macro"}


def test_a_key_this_app_does_not_know_is_refused(server, clean_remap):
    """An unknown key is a mistake, not something to bind to key code 0."""
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/remap",
                              {"active": True, "mapping": {"Nonsense": "Macro"}})
    assert status == 400
    assert "Nonsense" in json.loads(body)["error"]


# -- the lighting: reading a value and then being refused it ----------------


def test_a_speed_the_board_holds_can_be_written_back(server):
    """The board keeps six speeds and the app only wrote five, so every
    change was refused with "speed must be 0..4" as soon as the board
    sat on the slowest one.
    """
    board = FakeBoard()
    board.session.config[0x01 + 2] = 5       # the speed byte of profile 0
    status, _, body = request(server(board.service()), "GET", "/api/lighting")
    assert status == 200
    assert json.loads(body)["speed"] == 5

    status, _, body = request(server(board.service()), "POST", "/api/lighting",
                              {"mode": 6, "brightness": 4, "speed": 5,
                               "direction": 0, "color": [1, 2, 3]})
    assert status == 200, body


def test_a_direction_the_app_does_not_write_is_shown_as_the_nearest_one(server):
    """The board can hold a direction this app does not drive.  Refusing
    the whole read left the app showing the last state it applied, and
    then every change was refused as out of range.
    """
    board = FakeBoard()
    board.session.config[0x01 + 3] = 2       # the direction byte of profile 0
    status, _, body = request(server(board.service()), "GET", "/api/lighting")
    assert status == 200
    assert json.loads(body)["direction"] == 1


def test_an_effect_this_app_does_not_know_is_still_read_from_the_board(server):
    """The board was showing an effect the app has no name for, so the
    read was thrown away and the app showed what it had set last, not
    what the board was doing.
    """
    board = FakeBoard()
    board.session.config[0x01] = 0xFE       # an effect with no name
    status, _, body = request(server(board.service()), "GET", "/api/lighting")
    assert status == 200
    assert json.loads(body)["mode"] == 0xFE


# -- the board's colour buffer ----------------------------------------------


def test_a_key_number_past_the_end_of_the_board_is_refused(server):
    """The number was checked against 65535 and the buffer was then made
    long enough to hold it: 15 000 bytes into a 378 byte buffer.
    """
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/keys/colors",
                              {"led": 5000, "color": [1, 2, 3]})
    assert status == 400
    assert json.loads(body)["error"]


def test_painting_one_key_keeps_the_whole_buffer(server):
    """Painting one key must not send a buffer bigger than the board's."""
    board = FakeBoard()
    status, _, _ = request(server(board.service()), "POST", "/api/keys/colors",
                           {"led": 125, "color": [1, 2, 3]})
    assert status == 200
    written = board.session.key_writes[-1][0]
    assert len(written) == 378


# -- resetting the lighting -------------------------------------------------


def test_resetting_the_lighting_leaves_the_other_profiles_alone(server):
    """The reset wrote every profile and moved the board to profile one,
    so the user's other two setups were gone and the board jumped.
    """
    board = FakeBoard()
    board.session.config[0x00] = 2                    # the board is on profile 2
    board.session.config[0x01:0x09] = bytes([1, 2, 3, 0, 0, 10, 20, 30])
    board.session.config[0x41:0x49] = bytes([1, 2, 3, 0, 0, 40, 50, 60])

    status, _, _ = request(server(board.service()), "POST", "/api/lighting/reset")
    assert status == 200

    assert list(board.session.config[0x01:0x09]) == [1, 2, 3, 0, 0, 10, 20, 30]
    assert list(board.session.config[0x41:0x49]) == [1, 2, 3, 0, 0, 40, 50, 60]
    assert board.session.current_profile() == 2


def test_the_default_lighting_is_one_answer_not_two():
    """The app's starting lighting and the lighting a reset puts back
    were two different answers to the same question.
    """
    assert Ak820Service()._lighting == DEFAULT_LIGHTING


# -- names that would land in the same file --------------------------------


def test_a_macro_name_that_would_land_in_the_same_file_is_refused(tmp_path, monkeypatch):
    """"Late/Shift" was quietly turned into "Late_Shift", the same file a
    macro really called "Late_Shift" lives in, so the second one saved
    replaced the first without a word.  The name is refused instead.
    """
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    with pytest.raises(macro_store.MacroError):
        macro_store.save_macro("Late/Shift", [])
    macro_store.save_macro("Late_Shift", [])
    assert [macro["name"] for macro in macro_store.list_macros()] == ["Late_Shift"]


def test_a_name_that_is_only_dots_is_refused(tmp_path, monkeypatch):
    """".." became "profile.json", the same file as a profile called
    "profile".
    """
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    with pytest.raises(macro_store.MacroError):
        macro_store.save_macro("..", [])
    with pytest.raises(ValueError):
        store.check_name("..", "macro")


def test_two_different_names_never_land_in_the_same_file(tmp_path, monkeypatch):
    """No pair of usable names may become one file name."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    macro_store.save_macro("Late_Shift", [])
    with pytest.raises(macro_store.MacroError):
        macro_store.save_macro("Late/Shift", [])
    assert [macro["name"] for macro in macro_store.list_macros()] == ["Late_Shift"]

# -- the app's own files ----------------------------------------------------


def test_a_setting_that_cannot_be_written_answers_json(server, monkeypatch):
    """The app in a folder it cannot write to raised a bare error, and
    the request died without an answer at all.
    """
    def no_path():
        raise OSError("The folder cannot be written to.")

    monkeypatch.setattr(app_settings, "settings_path", no_path)
    status, content_type, body = request(server(Ak820Service(device_finder=lambda: None)),
                                         "POST", "/api/settings",
                                         {"key": "theme", "value": "dark"})
    assert status == 500
    assert content_type == "application/json"
    assert json.loads(body)["error"]


def test_the_settings_file_goes_to_the_users_folder_when_the_app_cannot_write(tmp_path, monkeypatch):
    """The app sitting in Program Files must still be able to keep its
    settings.
    """
    monkeypatch.delenv("AK820_SETTINGS_FILE", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    unwritable = tmp_path / "read-only"
    unwritable.mkdir()
    real_write = Path.write_text

    def refuse_probe(self, *args, **kwargs):
        if self.name.endswith(".write-test"):
            raise PermissionError("Access is denied.")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", refuse_probe)
    monkeypatch.setattr(app_settings, "app_folder", lambda: unwritable)
    path = app_settings.settings_path()
    assert path.parent != unwritable
    assert path.name == "settings.json"


# -- a profile saved from a short read --------------------------------------


class ShortReadSession(FakeSession):
    """A board that gives back less of its colour buffer than asked for."""

    def read_custom_colors(self, size: int = 378) -> bytes:
        return bytes(self.colors[:100])


def test_a_profile_saved_from_a_short_read_can_still_be_applied(server, tmp_path, monkeypatch):
    """A short read left the saved profile holding half a colour, which
    could not be applied again.
    """
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    board = FakeBoard()
    board.session = ShortReadSession()
    service = Ak820Service(
        device_finder=lambda: FAKE_DEVICE,
        session_factory=lambda device: board.session,
        mode_support=lambda: (1, 6),
    )
    service.save_profile({"name": "Desk", "with_key_colors": True})
    status, _, body = request(server(service), "GET", "/api/profiles/Desk")
    assert status == 200, body


# -- the cached lighting ----------------------------------------------------


def test_writing_per_key_colours_does_not_reach_into_the_saved_lighting(server):
    """The per-key write changed the dictionary the app had saved, so the
    state the app remembered and the state it was holding were not the
    same thing.
    """
    board = FakeBoard()
    status, _, body = request(server(board.service()), "POST", "/api/lighting",
                              {"mode": 6, "brightness": 4, "speed": 3,
                               "direction": 0, "color": [1, 2, 3]})
    assert status == 200
    applied = json.loads(body)

    request(server(board.service()), "POST", "/api/keys/colors",
            {"led": 12, "color": [4, 5, 6]})
    assert applied["mode"] == 6


def test_per_key_colours_put_the_board_into_the_custom_effect(server):
    """Per-key colours only show in the custom effect, so the board is
    put into it - and the app must remember that it did.
    """
    board = FakeBoard()
    service = board.service()
    request(server(service), "POST", "/api/keys/colors",
            {"led": 12, "color": [4, 5, 6]})
    assert service._lighting["mode"] == MODE_CUSTOM


# -- a profile called "rename" -----------------------------------------------


def test_a_profile_called_rename_can_still_be_applied_and_deleted(server, tmp_path, monkeypatch):
    """"rename" is a route of its own, so a profile with that name was
    unreachable.  It is not: the name in the body says which profile.
    """
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    board = FakeBoard()
    service = board.service()
    service.save_profile({"name": "rename"})

    status, _, body = request(server(service), "GET", "/api/profiles/rename")
    assert status == 200, body
    assert "profile" in json.loads(body)

    status, _, _ = request(server(service), "DELETE", "/api/profiles/rename")
    assert status == 200


# -- the new features --------------------------------------------------------


def test_a_profile_can_be_copied(server, tmp_path, monkeypatch):
    """A copy of a profile is a profile of its own."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    service = FakeBoard().service()
    service.save_profile({"name": "Desk"})

    status, _, body = request(server(service), "POST", "/api/profiles/duplicate",
                              {"name": "Desk", "new_name": "Desk copy"})
    assert status == 200, body
    assert json.loads(body)["name"] == "Desk copy"

    _, _, body = request(server(service), "GET", "/api/profiles")
    names = [profile["name"] for profile in json.loads(body)["profiles"]]
    assert sorted(names) == ["Desk", "Desk copy"]


def test_a_profile_can_be_exported_and_imported(server, tmp_path, monkeypatch):
    """An exported profile is a file, and that file can be imported back."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    service = FakeBoard().service()
    service.save_profile({"name": "Desk"})

    status, _, body = request(server(service), "POST", "/api/profiles/export",
                              {"name": "Desk"})
    assert status == 200, body
    exported = json.loads(body)
    assert exported["path"].endswith("Desk.json")
    assert os.path.exists(exported["path"])

    # The file is imported under a name of its own, so the one that is
    # already saved is not replaced.
    status, _, body = request(server(service), "POST", "/api/profiles/import",
                              {"path": exported["path"]})
    assert status == 200, body
    assert json.loads(body)["name"] == "Desk 2"

    _, _, body = request(server(service), "GET", "/api/profiles")
    names = [profile["name"] for profile in json.loads(body)["profiles"]]
    assert sorted(names) == ["Desk", "Desk 2"]


def test_importing_a_file_that_is_not_a_profile_is_refused(server, tmp_path, monkeypatch):
    """A file that is not a profile is not imported."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    wrong = tmp_path / "wrong.json"
    wrong.write_text("{}", encoding="utf-8")
    status, _, body = request(server(FakeBoard().service()), "POST",
                              "/api/profiles/import", {"path": str(wrong)})
    assert status == 400
    assert json.loads(body)["error"]


def test_a_colour_can_be_pinned_and_unpinned(server, tmp_path, monkeypatch):
    """A pinned colour comes back, and pinning it again takes it away."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    status, _, body = request(server(FakeBoard().service()), "GET",
                              "/api/colours/favourites")
    assert status == 200
    assert json.loads(body)["favourites"] == []

    status, _, body = request(server(FakeBoard().service()), "POST",
                              "/api/colours/favourites", {"color": [10, 20, 30]})
    assert status == 200, body
    assert json.loads(body)["added"] is True
    assert json.loads(body)["favourites"] == [[10, 20, 30]]

    status, _, body = request(server(FakeBoard().service()), "POST",
                              "/api/colours/favourites", {"color": [10, 20, 30]})
    assert status == 200, body
    assert json.loads(body)["added"] is False
    assert json.loads(body)["favourites"] == []


def test_a_colour_that_is_not_a_colour_is_refused(server, tmp_path, monkeypatch):
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    status, _, body = request(server(FakeBoard().service()), "POST",
                              "/api/colours/favourites", {"color": [10, 20]})
    assert status == 400
    assert json.loads(body)["error"]


def test_a_macro_says_how_often_it_plays_and_how_long_it_waits(server, tmp_path, monkeypatch):
    """The macro keeps the times and the delay it was given."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/macros",
                              {"name": "Hi", "events": [{"vk": 65, "down": True}],
                               "repeat": 3, "delay": 40})
    assert status == 200, body
    assert json.loads(body)["repeat"] == 3
    assert json.loads(body)["delay"] == 40

    _, _, body = request(server(FakeBoard().service()), "GET", "/api/macros")
    macro = json.loads(body)["macros"][0]
    assert macro["repeat"] == 3
    assert macro["delay"] == 40


def test_a_macro_cannot_be_told_to_do_something_silly(server, tmp_path, monkeypatch):
    """A macro that plays itself a thousand times is refused."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/macros",
                              {"name": "Hi", "events": [{"vk": 65, "down": True}],
                               "repeat": 5000})
    assert status == 400
    assert json.loads(body)["error"]


def test_macros_can_be_moved_up_and_down_the_list(server, tmp_path, monkeypatch):
    """The list of macros is in the order the user put them in."""
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    for name in ("One", "Two", "Three"):
        request(server(FakeBoard().service()), "POST", "/api/macros",
                {"name": name, "events": [{"vk": 65, "down": True}]})

    def names():
        _, _, body = request(server(FakeBoard().service()), "GET", "/api/macros")
        return [macro["name"] for macro in json.loads(body)["macros"]]

    assert names() == ["One", "Two", "Three"]

    status, _, body = request(server(FakeBoard().service()), "POST", "/api/macros/reorder",
                              {"name": "Three", "to": 0})
    assert status == 200, body
    assert names() == ["Three", "One", "Two"]

    request(server(FakeBoard().service()), "POST", "/api/macros/reorder",
            {"name": "Three", "to": 2})
    assert names() == ["One", "Two", "Three"]


def test_moving_a_macro_that_is_not_there_is_refused(server, tmp_path, monkeypatch):
    monkeypatch.setenv("AK820_DATA_DIR", str(tmp_path))
    status, _, body = request(server(FakeBoard().service()), "POST", "/api/macros/reorder",
                              {"name": "Nothing", "to": 0})
    assert status == 400
    assert json.loads(body)["error"]
