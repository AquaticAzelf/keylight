"""The JSON API the desktop app talks to.

Every route answers JSON — including the failures.  The common case is that no
keyboard is plugged in, so nothing here may raise because of that: the
device-facing routes answer ``503`` with a message the front end can show.

The routes are plain functions on :class:`Ak820Service`, so the API can be
tested without a socket.  :mod:`ak820.server` wraps them in HTTP.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import unquote

from ak820 import __version__
from ak820.hid.device import (
    AK820_PID,
    AK820_VID,
    BUSY_MESSAGE,
    HidError,
    HidPath,
    find_ak820,
    list_interface_paths,
)
from ak820.protocol.lighting import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    DIRECTION_MAX,
    DIRECTION_MIN,
    MODE_NAMES,
    SPEED_MAX,
    SPEED_MIN,
)
from ak820.protocol.session import KeyboardSession
from ak820.protocol.v2 import MODE_CUSTOM, PROFILE_COUNT

DEVICE_FILE = Path(__file__).parent / "devices" / "ak820_wired.json"

#: The board's colour buffer: three bytes for each of its keys.
#:
#: The board's own capabilities report a map of 128 slots, but the vendor's
#: driver for this board only drives 126 of them, and the last two slots
#: have no key on them.  This follows the vendor, so the board is left in
#: exactly the state the vendor's own app would leave it in.
COLOR_SLOTS = 126
COLOR_BUFFER_BYTES = COLOR_SLOTS * 3

NOT_CONNECTED = "No keyboard is connected. Plug the AK820 in and try again."

#: The lighting the board comes with, and the lighting a reset puts back.
#: There is one answer to "what is the default", not two.
DEFAULT_LIGHTING = {"mode": 0x06, "brightness": 4, "speed": 3, "direction": 0,
                    "color": [255, 255, 255]}


class ApiError(Exception):
    """A failure the front end should show as it is."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _int(payload: dict, key: str, low: int, high: int) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError(400, f"{key} must be a whole number.")
    if not low <= value <= high:
        raise ApiError(400, f"{key} must be {low}..{high}, got {value}.")
    return value


def _color(value: object) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ApiError(400, "color must be three numbers: [r, g, b].")
    channels = []
    for channel in value:
        if isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel <= 255:
            raise ApiError(400, "Every color channel must be a number from 0 to 255.")
        channels.append(channel)
    return channels[0], channels[1], channels[2]


def _profile_number(lighting: dict, key: str, default: int) -> int:
    """One number out of a saved profile.

    A profile file is written by hand as well as by the app, so a value may
    be missing, or be something that is not a number at all.  That is
    refused in plain words rather than being allowed to fall over the
    request.
    """
    value = lighting.get(key, default)
    if isinstance(value, bool):
        raise ApiError(400, f"That profile does not hold a usable {key}.")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError(400, f"That profile does not hold a usable {key}.") from None


class Ak820Service:
    """Everything the API needs from the keyboard, in one place.

    ``device_finder``, ``session_factory`` and ``mode_support`` are the seams
    the tests use to put a fake keyboard in front of the API.
    """

    def __init__(self,
                 device_finder: Callable[[], HidPath | None] | None = None,
                 session_factory: Callable[[HidPath], KeyboardSession] | None = None,
                 mode_support: Callable[[], Iterable[int]] | None = None) -> None:
        self._find_device = device_finder or find_ak820
        self._make_session = session_factory or KeyboardSession
        self._mode_support = mode_support
        # The board is opened exclusively, so two requests at once would have
        # one of them fail. Everything that touches the keyboard waits its
        # turn. It is re-entrant because finding the device and opening a
        # session on it both go through here.
        self._lock = threading.RLock()
        self._lighting = dict(DEFAULT_LIGHTING)
        self._profiles: list[dict] = []

    # -- the device ------------------------------------------------------

    def device(self) -> HidPath | None:
        """The keyboard, or None when it is not there (or is held by another tool)."""
        try:
            return self._find_device()
        except (HidError, OSError):
            return None

    def device_state(self) -> str:
        """Whether the keyboard is there, and whether it is ours to use.

        ``connected`` means we can talk to it, ``busy`` means another program
        is holding it open, and ``missing`` means it is not plugged in. The
        two are told apart by looking for the device on the bus, which works
        even when the collection cannot be opened.
        """
        if self.device() is not None:
            return "connected"
        try:
            on_the_bus = list_interface_paths(AK820_VID, AK820_PID)
        except (HidError, OSError):
            on_the_bus = []
        return "busy" if on_the_bus else "missing"

    def session(self) -> KeyboardSession:
        """A session on the keyboard, or a 503 when there is none."""
        device = self.device()
        if device is None:
            raise ApiError(503, NOT_CONNECTED)
        return self._make_session(device)

    def device_info(self) -> dict:
        """The board's own facts, read from the device definition."""
        data = json.loads(DEVICE_FILE.read_text(encoding="utf-8"))
        return {
            "id": data["id"],
            "name": data["name"],
            "vid": f"{data['vid']:04X}",
            "pid": f"{data['pid']:04X}",
            "interface": data["interface"],
        }

    # -- routes ----------------------------------------------------------

    def status(self) -> dict:
        with self._lock:
            device = self.device()
            state = "connected" if device is not None else self.device_state()
        return {
            "connected": state == "connected",
            "device_state": state,
            "message": "" if state == "connected" else (
                BUSY_MESSAGE if state == "busy" else NOT_CONNECTED),
            "device": None if device is None else self.device_info(),
            "version": __version__,
        }

    def modes(self) -> list[dict]:
        """The lighting modes this keyboard implements.

        The vendor table is the answer until a recorded capability probe says
        otherwise.  ``mode_support`` replaces it — that is how the tests put a
        board in front of the API that only implements a couple of modes.
        """
        supported = set(self._mode_support()) if self._mode_support else set(MODE_NAMES)
        return [
            {"id": mode, "name": name, "supported": mode in supported}
            for mode, name in sorted(MODE_NAMES.items())
            if mode in supported
        ]

    def lighting(self) -> dict:
        """The backlight as the board currently has it.

        The board answers a config read with a reply that can be a leftover
        from an earlier transaction, so the block is read twice and is only
        believed when both reads agree and hold values the firmware can
        store.  Otherwise the last state this app applied is kept.
        """
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            state = self._read_lighting()
        if state is not None:
            self._lighting = state
        return dict(self._lighting)

    def _read_lighting(self) -> dict | None:
        session = self.session()
        first = session.read_current_lighting()
        second = session.read_current_lighting()
        if not first or first != second:
            return None
        mode = first.get("mode")
        brightness = first.get("brightness")
        speed = first.get("speed")
        direction = first.get("direction")
        color = first.get("color") or [0, 0, 0]
        if not isinstance(mode, int) or not 0 <= mode <= 0xFF:
            return None
        if not isinstance(brightness, int) or not 0 <= brightness <= BRIGHTNESS_MAX:
            return None
        if not isinstance(speed, int) or speed < 0:
            return None
        if not isinstance(direction, int) or direction < 0:
            return None
        # The board can hold a speed or a direction this app does not write.
        # Showing the nearest value it can write is better than refusing the
        # whole read, because refusing it leaves the app showing the last
        # state it applied rather than the one the board is really in - and
        # then every change the user makes is refused as out of range.
        return {
            "mode": mode,
            "brightness": brightness,
            "speed": min(speed, SPEED_MAX),
            "direction": min(direction, DIRECTION_MAX),
            "color": list(color),
        }

    def apply_lighting(self, payload: dict) -> dict:
        """Write a backlight setting to the board.

        The change goes into the profile the board is showing, so the other
        two setups it keeps of its own are left alone. Then it is read back:
        if the board is not showing what was asked for, the value is written
        into every profile, because a board that shows something else looks
        to the user like a dead switch.
        """
        state = {
            "mode": _int(payload, "mode", 0, 0xFF),
            "brightness": _int(payload, "brightness", BRIGHTNESS_MIN, BRIGHTNESS_MAX),
            "speed": _int(payload, "speed", SPEED_MIN, SPEED_MAX),
            "direction": _int(payload, "direction", DIRECTION_MIN, DIRECTION_MAX),
            "color": list(_color(payload.get("color"))),
        }
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            index = session.current_profile()
            self._write_lighting(session, state, index)
            if not self._board_holds(session, index, state):
                # The board is showing another profile, or it did not take
                # the change. Write it everywhere, so that whichever profile
                # is on screen holds the value that was asked for.
                self._write_lighting(session, state, index, every_profile=True)
        self._lighting = state
        return dict(state)

    @staticmethod
    def _write_lighting(session: KeyboardSession, state: dict, index: int,
                        every_profile: bool = False) -> None:
        session.set_lighting(state["mode"], state["brightness"], state["speed"],
                             state["direction"], False, *state["color"],
                             profile=index, all_profiles=every_profile)

    @staticmethod
    def _board_holds(session: KeyboardSession, index: int, state: dict) -> bool:
        """Does the board really hold these values in that profile?

        The board can answer a read with a reply left over from an earlier
        transaction, so the profile is read twice and is only believed when
        both reads agree.
        """
        first = session.read_lighting(index)
        second = session.read_lighting(index)
        if not first or first != second:
            return False
        return (first.get("mode") == state["mode"]
                and first.get("brightness") == state["brightness"]
                and first.get("speed") == state["speed"]
                and first.get("direction") == state["direction"]
                and list(first.get("color") or []) == list(state["color"]))

    def keys(self) -> dict:
        """The 82 keys and the knob, laid out as they are on the board."""
        data = json.loads(DEVICE_FILE.read_text(encoding="utf-8"))
        keys = [key for row in data["rows"] for key in row["keys"]]
        return {"keys": keys, "knob": data["knob"]}

    def key_colors(self) -> dict:
        """The board's colour buffer: three bytes for each of its keys."""
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            data = self.session().read_custom_colors(COLOR_BUFFER_BYTES)
        colors = [list(data[at:at + 3]) for at in range(0, len(data) - 2, 3)]
        return {"colors": colors, "count": len(colors)}

    def set_key_color(self, payload: dict) -> dict:
        """Paint one key, keeping the rest of the buffer as it is."""
        led = _int(payload, "led", 0, COLOR_SLOTS - 1)
        color = list(_color(payload.get("color")))
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            buffer = bytearray(session.read_custom_colors(COLOR_BUFFER_BYTES))
            if len(buffer) < (led + 1) * 3:
                buffer.extend(bytes((led + 1) * 3 - len(buffer)))
            buffer[led * 3:led * 3 + 3] = bytes(color)
            self._write_colors(session, bytes(buffer))
        return {"ok": True, "led": led, "color": color}

    def set_key_colors(self, payload: dict) -> dict:
        """Paint keys.

        The client may send one key (``led`` and ``color``) or the whole
        buffer (``colors``). The board is fed a run of colours at a time, so
        the ones that are not changing are sent back unchanged.
        """
        if "colors" not in payload:
            return self.set_key_color(payload)
        colors = payload.get("colors")
        if not isinstance(colors, list) or not colors:
            raise ApiError(400, "colors must be a list of [r, g, b] triples.")
        if len(colors) > COLOR_SLOTS:
            raise ApiError(400, f"The board has {COLOR_SLOTS} keys, got {len(colors)}.")
        buffer = bytearray()
        for color in colors:
            buffer.extend(bytes(_color(color)))
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            self._write_colors(session, bytes(buffer))
        return {"ok": True, "count": len(colors)}

    def _write_colors(self, session: KeyboardSession, buffer: bytes) -> None:
        """Give the board the colours twice: once to keep, once to show."""
        session.write_custom_colors(buffer)
        session.set_per_key_colors(buffer)
        # Per-key colours only show in the custom effect, so the board is put
        # into it - but the rest of the lighting is left as the user had it.
        current = dict(self._lighting)
        color = current.get("color") or [255, 255, 255]
        state = {
            "mode": MODE_CUSTOM,
            "brightness": current["brightness"],
            "speed": current["speed"],
            "direction": current["direction"],
            "color": list(color),
        }
        index = session.current_profile()
        self._write_lighting(session, state, index)
        if not self._board_holds(session, index, state):
            self._write_lighting(session, state, index, every_profile=True)
        self._lighting = {**current, "mode": MODE_CUSTOM}

    def profiles(self) -> list[dict]:
        return list(self._profiles)

    def create_profile(self, payload: dict) -> dict:
        """Save the current backlight under a name.

        Profiles live for this run only; the portable profile store arrives
        with the Profiles section.
        """
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ApiError(400, "A profile needs a name.")
        if len(name) > 64:
            raise ApiError(400, "A profile name can be at most 64 characters long.")
        if set(name) & set('\\/:*?"<>|'):
            raise ApiError(400, 'A profile name cannot contain \\ / : * ? " < > or |.')
        profile = {
            "name": name,
            "mode": self._lighting["mode"],
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "storage": "session",
        }
        self._profiles.append(profile)
        return profile

    # -- profiles ---------------------------------------------------------

    def saved_profiles(self) -> list[dict]:
        """The lighting setups the user has saved."""
        from ak820 import profiles as profile_store

        found = []
        for profile in profile_store.list_profiles():
            lighting = profile.get("lighting", {})
            found.append({
                "name": profile.get("name", ""),
                "mode": lighting.get("mode"),
                "created": profile.get("created", ""),
                "modified": profile.get("modified", ""),
                "device": profile.get("device", ""),
            })
        return found

    def save_profile(self, payload: dict) -> dict:
        """Save the lighting as it is now under a name."""
        from ak820 import profiles as profile_store

        name = str(payload.get("name", "")).strip()
        if not name:
            raise ApiError(400, "A profile needs a name.")
        state = {"lighting": dict(self._lighting)}
        if payload.get("with_key_colors"):
            with self._lock:
                if self.device() is None:
                    raise ApiError(503, NOT_CONNECTED)
                # The buffer is read once and then cut up.  Reading it for
                # every key meant 126 round trips to the keyboard for one
                # save, which took the best part of ten seconds.
                buffer = self.session().read_custom_colors(COLOR_BUFFER_BYTES)
                # A short read is padded out, so a saved profile always
                # holds whole colours and can always be applied again.
                whole = bytes(buffer[:COLOR_BUFFER_BYTES])
                whole += bytes(COLOR_BUFFER_BYTES - len(whole))
                state["key_colors"] = [
                    list(whole[at:at + 3]) for at in range(0, COLOR_BUFFER_BYTES, 3)
                ]
        try:
            profile = profile_store.save_profile(name, state)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"name": profile["name"], "created": profile["created"],
                "modified": profile["modified"]}

    def apply_profile(self, name: str) -> dict:
        """Put a saved profile onto the keyboard.

        A profile made for another keyboard is refused here, in the back
        end, so it can never be written to the wrong board.
        """
        from ak820 import profiles as profile_store

        try:
            profile = profile_store.load_profile(name)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        lighting = profile.get("lighting", {})
        if not isinstance(lighting, dict) or "mode" not in lighting:
            raise ApiError(400, "That profile does not hold any lighting.")
        state = {
            "mode": _profile_number(lighting, "mode", 0x06),
            "brightness": _profile_number(lighting, "brightness", 4),
            "speed": _profile_number(lighting, "speed", 3),
            "direction": _profile_number(lighting, "direction", 0),
            "color": list(_color(lighting.get("color", [255, 0, 0]))),
        }
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            key_colors = profile.get("key_colors")
            if isinstance(key_colors, list) and key_colors:
                buffer = bytearray()
                for color in key_colors[:COLOR_SLOTS]:
                    buffer.extend(bytes(_color(color)))
                session.write_custom_colors(bytes(buffer))
                session.set_per_key_colors(bytes(buffer))
            # The lighting goes into the profile the board is showing, so the
            # other two setups the board keeps of its own are left alone.
            # Writing it into every profile block would throw them away.
            index = session.current_profile()
            self._write_lighting(session, state, index)
            if not self._board_holds(session, index, state):
                self._write_lighting(session, state, index, every_profile=True)
        self._lighting = state
        return dict(state)

    def delete_profile(self, name: str) -> dict:
        from ak820 import profiles as profile_store

        try:
            profile_store.delete_profile(name)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"ok": True, "name": name}

    def rename_profile(self, payload: dict) -> dict:
        from ak820 import profiles as profile_store

        name = str(payload.get("name", ""))
        new_name = str(payload.get("new_name", ""))
        try:
            profile = profile_store.rename_profile(name, new_name)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"name": profile["name"]}

    def export_profile(self, payload: dict) -> dict:
        """Write a profile to a file the user can copy or share.

        The file lands in the folder the app keeps its profiles in, so it
        is somewhere the user can find without being asked to.
        """
        from ak820 import profiles as profile_store

        name = str(payload.get("name", ""))
        try:
            path = profile_store.export_profile(name, profile_store.export_path(name))
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"ok": True, "name": name, "path": str(path)}

    def import_profile(self, payload: dict) -> dict:
        """Read a profile from a file the user has."""
        from ak820 import profiles as profile_store

        source = str(payload.get("path", "")).strip()
        if not source:
            raise ApiError(400, "Say which file to import.")
        # A full path is used as it is. A plain file name is looked for in
        # the folder the app exports profiles to, so a file that has been
        # copied there can be imported by its name.
        candidate = Path(source)
        if not candidate.exists() and not candidate.is_absolute():
            candidate = profile_store.export_dir() / source
        try:
            profile = profile_store.import_profile(candidate)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        except OSError as exc:
            raise ApiError(400, f"That file could not be read: {exc}") from exc
        return {"ok": True, "name": profile["name"]}

    def duplicate_profile(self, payload: dict) -> dict:
        """Copy a profile under a new name."""
        from ak820 import profiles as profile_store

        name = str(payload.get("name", ""))
        new_name = str(payload.get("new_name", ""))
        if not new_name.strip():
            raise ApiError(400, "A copy needs a name of its own.")
        try:
            profile = profile_store.duplicate_profile(name, new_name)
        except profile_store.ProfileError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"ok": True, "name": profile["name"]}

    def board_profiles(self) -> list[dict]:
        """The three lighting profiles the keyboard keeps of its own."""
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            active = session.current_profile()
            found = []
            for index in range(PROFILE_COUNT):
                state = session.read_lighting(index)
                found.append({
                    "index": index,
                    "active": index == active,
                    "mode": state.get("mode"),
                    "brightness": state.get("brightness"),
                    "color": state.get("color"),
                })
        return found

    def save_board_profile(self, payload: dict) -> dict:
        """Copy the lighting as it is now into one of the board's own slots."""
        index = _int(payload, "index", 0, PROFILE_COUNT - 1)
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            current = self._lighting
            session.set_lighting(current["mode"], current["brightness"], current["speed"],
                                 current["direction"], False, *current["color"],
                                 profile=index, all_profiles=False)
            session.set_current_profile(index)
        return {"ok": True, "index": index}

    def use_board_profile(self, payload: dict) -> dict:
        """Show one of the board's own profiles."""
        index = _int(payload, "index", 0, PROFILE_COUNT - 1)
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            self.session().set_current_profile(index)
        return {"ok": True, "index": index}

    # -- the system settings (Windows Lock, Exchange Key, polling) ----------

    def system_stages(self) -> dict:
        """What the board's system settings are set to."""
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            try:
                return self.session().read_stages()
            except ValueError as exc:
                # The board is there but would not give a steady answer,
                # which for the user is the same as not being usable.
                raise ApiError(503, f"The keyboard did not answer: {exc}") from exc

    def set_system_stages(self, payload: dict) -> dict:
        """Change one or more of the board's system settings.

        The offsets are the vendor's own - see ``protocol/stages.py`` -
        so the write is the same one the official driver makes.  Anything
        the board keeps in the rest of the record is carried over, not
        zeroed.
        """
        asked = {name: payload[name] for name in
                 ("exchange", "win_lock", "polling_rate") if name in payload}
        if not asked:
            raise ApiError(400, "Nothing to set: exchange, win_lock or polling_rate.")
        # Checked here so a bad value is a 400 while a silent board is a 503.
        bounds = {"exchange": (0, 1), "win_lock": (0, 1), "polling_rate": (0, 3)}
        for name, (low, high) in bounds.items():
            if name in asked:
                asked[name] = _int(asked, name, low, high)
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            try:
                return self.session().set_stages(**asked)
            except ValueError as exc:
                # The values were checked above, so this is the board not
                # answering, which for the user is the same as unusable.
                raise ApiError(503, f"The keyboard did not answer: {exc}") from exc

    # -- macros -----------------------------------------------------------

    def macros(self) -> list[dict]:
        from ak820 import macros as macro_store

        found = []
        for macro in macro_store.list_macros():
            found.append({
                "name": macro.get("name", ""),
                "created": macro.get("created", ""),
                "modified": macro.get("modified", ""),
                "events": macro.get("events", []),
                "summary": macro_store.describe_macro(macro),
                "repeat": macro.get("repeat", 1),
                "delay": macro.get("delay", 12),
                "order": macro.get("order", 0),
            })
        return found

    def save_macro(self, payload: dict) -> dict:
        from ak820 import macros as macro_store

        name = str(payload.get("name", ""))
        events = payload.get("events") or []
        try:
            macro = macro_store.save_macro(name, events,
                                           payload.get("repeat"),
                                           payload.get("delay"))
        except macro_store.MacroError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"name": macro["name"], "events": macro["events"],
                "repeat": macro["repeat"], "delay": macro["delay"]}

    def reorder_macro(self, payload: dict) -> dict:
        """Move a macro up or down the list."""
        from ak820 import macros as macro_store

        name = str(payload.get("name", ""))
        to = payload.get("to")
        if isinstance(to, bool) or not isinstance(to, int):
            raise ApiError(400, "Say where the macro should go: a number from 0.")
        try:
            names = macro_store.move_macro(name, to)
        except macro_store.MacroError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"ok": True, "names": names}

    def delete_macro(self, name: str) -> dict:
        from ak820 import macros as macro_store

        try:
            macro_store.delete_macro(name)
        except macro_store.MacroError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"ok": True, "name": name}

    def remap_state(self) -> dict:
        """Which keys play which macro, and whether the hook is watching."""
        from ak820 import remap

        return {
            "active": remap.is_active(),
            "recording": remap.recording(),
            "mapping": remap.get_mapping(),
            "keys": [
                {"code": code, "name": name}
                for name, code in sorted(remap.KEY_NAMES.items(), key=lambda pair: pair[1])
            ],
        }

    def set_remap(self, payload: dict) -> dict:
        """Say which key plays which macro, and turn the hook on or off."""
        from ak820 import remap

        wanted = bool(payload.get("active", True))
        mapping = payload.get("mapping") or {}
        if not isinstance(mapping, dict):
            raise ApiError(400, "mapping must be a list of key and macro names.")
        pairs = {}
        for key, macro in mapping.items():
            text = str(key)
            # The front end sends the name the user sees ("A", "F5", "5").
            # A name is looked up first, because "5" is a name and a number
            # at the same time - reading it as a key code would bind the
            # wrong key. A client that sends the code itself is still read.
            code = remap.KEY_NAMES.get(text)
            if code is None:
                if not text.isdigit() or not 0 <= int(text) <= 0xFF:
                    raise ApiError(400, f'"{text}" is not a key this app knows.')
                code = int(text)
            pairs[code] = str(macro)
        if wanted:
            remap.set_mapping(pairs)
            if not remap.install_hook():
                raise ApiError(500, "The keyboard hook could not be put in place.")
        else:
            remap.uninstall_hook()
        return {"ok": True, "active": remap.is_active()}

    def record_start(self) -> dict:
        """Start recording the keys for a macro."""
        from ak820 import remap

        recorded: list[dict] = []

        def remember(vk: int, down: bool) -> None:
            from ak820.remap import key_name

            recorded.append({"vk": vk, "down": down, "text": key_name(vk)})
            if len(recorded) > 400:
                del recorded[:len(recorded) - 400]

        if not remap.start_recording(remember):
            raise ApiError(500, "The keyboard hook could not be put in place.")
        self._recorded = recorded
        return {"ok": True}

    def record_stop(self) -> dict:
        """Stop recording and give back what was recorded."""
        from ak820 import remap

        remap.stop_recording()
        recorded = getattr(self, "_recorded", [])
        self._recorded = []
        return {"events": recorded}

    def recorded(self) -> list[dict]:
        """What has been recorded so far."""
        return list(getattr(self, "_recorded", []))

    def play_macro(self, payload: dict) -> dict:
        """Play a macro once, right now."""
        from ak820 import remap

        name = str(payload.get("name", ""))
        if not name:
            raise ApiError(400, "A macro needs a name.")
        remap.play_macro(name)
        return {"ok": True, "name": name}

    def board_info(self) -> dict:
        """What the keyboard says about itself."""
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            capabilities = self.session().read_capabilities()
        info = self.device_info()
        info["name"] = "AK820"
        info["keys"] = 82
        info["map_size"] = (capabilities or {}).get("map_size")
        info["macro_space"] = (capabilities or {}).get("macros_size")
        return info

    def rename_macro(self, payload: dict) -> dict:
        from ak820 import macros as macro_store

        name = str(payload.get("name", ""))
        new_name = str(payload.get("new_name", ""))
        try:
            macro = macro_store.rename_macro(name, new_name)
        except macro_store.MacroError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"name": macro["name"]}

    # -- the app's own settings --------------------------------------------

    def app_settings(self) -> list[dict]:
        from ak820 import settings as app_settings

        return app_settings.describe()

    def set_app_setting(self, payload: dict) -> dict:
        from ak820 import settings as app_settings

        key = str(payload.get("key", ""))
        value = payload.get("value")
        try:
            app_settings.set_setting(key, value)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"key": key, "value": str(value)}

    def reset_settings(self) -> dict:
        """Put the app's own settings back as they were."""
        from ak820 import settings as app_settings

        app_settings.reset_settings()
        return {"ok": True, "settings": app_settings.get_settings()}

    def reset_lighting(self) -> dict:
        """Put the keyboard's lighting back to how it came.

        Only the profile the board is showing is written. The other two
        setups the board keeps of its own are the user's, and a reset of
        the lighting must not throw them away - nor move the board off
        the profile it is on.
        """
        default = dict(DEFAULT_LIGHTING)
        with self._lock:
            if self.device() is None:
                raise ApiError(503, NOT_CONNECTED)
            session = self.session()
            index = session.current_profile()
            self._write_lighting(session, default, index)
        self._lighting = default
        return dict(default)

    def settings_folder(self) -> dict:
        """Where the app keeps its own files."""
        from ak820 import store

        return {
            "app": str(store.app_folder()),
            "profiles": str(store.data_folder("profiles")),
            "macros": str(store.data_folder("macros")),
            "exports": str(store.data_folder("exports")),
            "colours": str(store.data_folder("colours")),
        }

    # -- the colours the user has pinned -------------------------------------

    def colour_favourites(self) -> dict:
        """The colours the user has pinned."""
        from ak820 import favourites

        return {"favourites": favourites.favourites()}

    def toggle_colour_favourite(self, payload: dict) -> dict:
        """Pin a colour, or unpin it if it is already pinned."""
        from ak820 import favourites

        try:
            found, added = favourites.toggle(payload.get("color"))
        except ValueError as exc:
            raise ApiError(400, str(exc)) from exc
        return {"favourites": found, "added": added}


class Api:
    """Routes one request to the service and shapes the answer."""

    def __init__(self, service: Ak820Service | None = None) -> None:
        self.service = service or Ak820Service()
        self._routes: dict[tuple[str, str], Callable[[dict], dict]] = {
            ("GET", "/api/status"): lambda body: self.service.status(),
            ("GET", "/api/modes"): lambda body: {"modes": self.service.modes()},
            ("GET", "/api/lighting"): lambda body: self.service.lighting(),
            ("POST", "/api/lighting"): self.service.apply_lighting,
            ("GET", "/api/keys"): lambda body: self.service.keys(),
            ("GET", "/api/keys/colors"): lambda body: self.service.key_colors(),
            ("POST", "/api/keys/colors"): self.service.set_key_colors,
            ("GET", "/api/profiles"): lambda body: {"profiles": self.service.saved_profiles()},
            ("POST", "/api/profiles"): self.service.save_profile,
            ("POST", "/api/profiles/export"): self.service.export_profile,
            ("POST", "/api/profiles/import"): self.service.import_profile,
            ("POST", "/api/profiles/duplicate"): self.service.duplicate_profile,
            ("GET", "/api/board-profiles"): lambda body: {"profiles": self.service.board_profiles()},
            ("POST", "/api/board-profiles"): self.service.save_board_profile,
            ("POST", "/api/board-profiles/use"): self.service.use_board_profile,
            ("GET", "/api/system-stages"): lambda body: self.service.system_stages(),
            ("POST", "/api/system-stages"): self.service.set_system_stages,
            ("GET", "/api/macros"): lambda body: {"macros": self.service.macros()},
            ("POST", "/api/macros"): self.service.save_macro,
            ("POST", "/api/macros/reorder"): self.service.reorder_macro,
            ("GET", "/api/remap"): lambda body: self.service.remap_state(),
            ("POST", "/api/remap"): self.service.set_remap,
            ("GET", "/api/board-info"): lambda body: self.service.board_info(),
            ("POST", "/api/macros/play"): self.service.play_macro,
            ("GET", "/api/macros/record"): lambda body: {"events": self.service.recorded()},
            ("POST", "/api/macros/record"): lambda body: self.service.record_start(),
            ("POST", "/api/macros/record/stop"): lambda body: self.service.record_stop(),
            ("GET", "/api/settings"): lambda body: {"settings": self.service.app_settings(),
                                                   "folders": self.service.settings_folder()},
            ("POST", "/api/settings"): self.service.set_app_setting,
            ("POST", "/api/settings/reset"): lambda body: self.service.reset_settings(),
            ("POST", "/api/lighting/reset"): lambda body: self.service.reset_lighting(),
            ("GET", "/api/colours/favourites"): lambda body: self.service.colour_favourites(),
            ("POST", "/api/colours/favourites"): self.service.toggle_colour_favourite,
        }

    def handle(self, method: str, path: str, body: bytes = b"") -> tuple[int, dict]:
        """Answer one request. Always returns a status and a JSON body."""
        handler = self._routes.get((method, path))
        if handler is None:
            handler = self._named_route(method, path)
        if handler is None:
            if path in {route for _, route in self._routes}:
                return 405, {"error": f"{method} is not allowed on {path}."}
            return 404, {"error": f"There is no endpoint at {path}."}
        try:
            payload = self._body(body) if method == "POST" else {}
            return 200, handler(payload)
        except ApiError as exc:
            return exc.status, {"error": exc.message}
        except HidError as exc:
            return 503, {"error": str(exc)}
        except ValueError as exc:
            return 400, {"error": str(exc)}
        except OSError as exc:
            # A file that cannot be written, a folder that has gone. The
            # front end is promised an answer every time, so this is
            # reported like any other failure instead of killing the
            # connection with an empty body.
            return 500, {"error": f"The app could not write its own files: {exc}"}

    def _named_route(self, method: str, path: str):
        """The routes that carry a name in the path."""
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "profiles":
            if parts[2] == "rename" and method == "POST":
                return lambda body: self.service.rename_profile(body)
            # The name is a piece of a URL, so it comes back percent-encoded:
            # "My%20Profile" has to become "My Profile" before it can be
            # looked for.  Without this, a profile whose name holds a space
            # (or a colon, a slash, an ampersand...) could be saved and
            # listed but never applied or deleted.
            name = unquote(parts[2])
            if method == "DELETE":
                return lambda body: self.service.delete_profile(name)
            if method == "GET":
                return lambda body: {"profile": self.service.apply_profile(name)}
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "macros":
            # The name is a piece of a URL, so it comes back percent-encoded.
            name = unquote(parts[2])
            if method == "DELETE":
                return lambda body: self.service.delete_macro(name)
            if name == "rename" and method == "POST":
                return lambda body: self.service.rename_macro(body)
        return None

    @staticmethod
    def _body(body: bytes) -> dict:
        if not body:
            return {}
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, f"The request body is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ApiError(400, "The request body must be a JSON object.")
        return data
