"""The app's own settings, and the keyboard settings it accepts.

Two kinds of setting live here. The app's own settings - the theme, how
often it looks for the keyboard - are kept in a small file next to the app.
The keyboard's own settings are the ones the firmware confirms it keeps;
until the board tells us which those are, there are none, and the app does
not offer any.

A setting the keyboard does not support is never offered: it is left out
of the list rather than shown greyed out.
"""

from __future__ import annotations

import os
from pathlib import Path

from ak820.store import app_folder, read_json, write_json

FILE = "settings.json"

#: The app's own settings, with what each one can be.
APP_SETTINGS = {
    "theme": {
        "name": "Theme",
        "note": "Light, dark, or the same as Windows",
        "options": [("system", "Windows"), ("light", "Light"), ("dark", "Dark")],
        "default": "system",
    },
    "check_interval": {
        "name": "Look for the keyboard",
        "note": "How often the app checks the keyboard is plugged in",
        "options": [("0", "Never"), ("2", "2 sec"), ("5", "5 sec"), ("10", "10 sec")],
        "default": "2",
    },
    "remember_section": {
        "name": "Remember where you were",
        "note": "Open the app on the section you left it on",
        "options": [("1", "Yes"), ("0", "No")],
        "default": "1",
    },
    "confirm_delete": {
        "name": "Ask before deleting",
        "note": "Always check before a profile or a macro is removed",
        "options": [("1", "Yes"), ("0", "No")],
        "default": "1",
    },
    "show_confirmations": {
        "name": "Show what the app is doing",
        "note": "Say when a change has reached the keyboard",
        "options": [("1", "Yes"), ("0", "No")],
        "default": "1",
    },
}

DEFAULTS = {key: value["default"] for key, value in APP_SETTINGS.items()}

#: The keyboard settings the firmware confirms. Empty until the board says
#: otherwise, so the app never shows a setting the board would ignore.
DEVICE_SETTINGS: dict[str, dict] = {}


def settings_path() -> Path:
    """Where the app's own settings are kept.

    The file goes next to the app when that folder can be written to, and
    in the user's own folder when it cannot - the app sitting in
    ``Program Files``, say.  Without the fallback, changing a setting
    there would fail with an error the front end cannot explain.
    """
    override = os.environ.get("AK820_SETTINGS_FILE")
    if override:
        return Path(override)
    return _writable_path(app_folder() / FILE)


def _writable_path(preferred: Path) -> Path:
    """The preferred file, or one in the user's folder when it cannot be written."""
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        probe = preferred.with_suffix(".write-test")
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return preferred
    except OSError:
        base = os.environ.get("APPDATA") or str(Path.home())
        folder = Path(base) / "Keylight"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / preferred.name


def get_settings() -> dict:
    """Every setting, with the value it currently has."""
    stored = read_json(settings_path(), {})
    if not isinstance(stored, dict):
        stored = {}
    values = dict(DEFAULTS)
    for key in APP_SETTINGS:
        if key in stored:
            values[key] = stored[key]
    return values


def set_setting(key: str, value) -> dict:
    """Change one setting. An unknown setting is refused."""
    if key in APP_SETTINGS:
        allowed = [option for option, _ in APP_SETTINGS[key]["options"]]
        if str(value) not in allowed:
            raise ValueError(f"{key} must be one of {', '.join(allowed)}.")
        values = get_settings()
        values[key] = str(value)
        write_json(settings_path(), values)
        return values
    if key in DEVICE_SETTINGS:
        # The board confirmed it takes this one, but the app has not
        # taught itself to write it yet. Say that, rather than blaming
        # the keyboard.
        raise ValueError(f"This app does not know how to change “{key}” yet.")
    raise ValueError(f"There is no setting called “{key}”.")

def supported_settings() -> list[str]:
    """The keyboard settings the board accepts."""
    return sorted(DEVICE_SETTINGS)


def reset_settings() -> None:
    """Put the app's own settings back as they were."""
    write_json(settings_path(), dict(DEFAULTS))


def describe() -> list[dict]:
    """Every setting the app offers, ready for the front end."""
    values = get_settings()
    described = []
    for key, setting in APP_SETTINGS.items():
        described.append({
            "key": key,
            "name": setting["name"],
            "note": setting["note"],
            "value": values.get(key, setting["default"]),
            "options": [{"value": value, "name": name} for value, name in setting["options"]],
            "kind": "app",
        })
    for key, setting in DEVICE_SETTINGS.items():
        described.append({
            "key": key,
            "name": setting["name"],
            "note": setting.get("note", ""),
            "value": setting.get("default"),
            "options": setting.get("options", []),
            "kind": "device",
        })
    return described
