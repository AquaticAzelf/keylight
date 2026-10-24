"""The macros the user records.

A macro is a list of key presses: which key, and whether it went down or
up. They are kept as JSON files in a ``macros`` folder next to the app.

These macros are played on the computer, not stored in the keyboard: the
keyboard's own macro storage is written by the official driver through a
library of its own that this app does not speak.
"""

from __future__ import annotations

import time
from pathlib import Path

from ak820.store import check_name, data_folder, read_json, safe_name, write_json

FILES = "macros"

#: How many times a macro plays, and how long it waits between the keys,
#: unless the macro says otherwise.
DEFAULT_REPEAT = 1
DEFAULT_DELAY_MS = 12
MAX_REPEAT = 50
MAX_DELAY_MS = 1000


def _number(value, low: int, high: int, default: int) -> int:
    """A whole number in a range, or the default when it is not one."""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise MacroError("That number is not a number.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise MacroError("That number is not a number.") from None
    if not low <= number <= high:
        raise MacroError(f"That number must be {low}..{high}.")
    return number


class MacroError(Exception):
    """A macro could not be used. The message says why, in plain words."""


def macro_dir() -> Path:
    return data_folder(FILES)


def _path(name: str) -> Path:
    return macro_dir() / f"{safe_name(name)}.json"


def list_macros() -> list[dict]:
    """Every macro, in the order the user put them.

    A macro that has never been moved keeps the order it was made in, so
    the list starts as newest first and the user can arrange it from
    there.
    """
    found = []
    for path in sorted(macro_dir().glob("*.json")):
        data = read_json(path, None)
        if not isinstance(data, dict):
            continue
        data.setdefault("name", path.stem)
        data["events"] = data.get("events", [])
        found.append(data)
    newest_first = sorted(found, key=lambda item: item.get("modified", ""), reverse=True)
    for index, data in enumerate(newest_first):
        if not isinstance(data.get("order"), int):
            data["order"] = index
    found.sort(key=lambda item: (item["order"], item.get("name", "")))
    return found


def move_macro(name: str, to: int) -> list[str]:
    """Move a macro to another place in the list.

    The macros are numbered from zero, so the first one is 0. The names
    of the macros in their new order are given back.
    """
    found = list_macros()
    names = [macro["name"] for macro in found]
    if name not in names:
        raise MacroError(f"There is no macro called “{name}”.")
    index = names.index(name)
    target = max(0, min(len(names) - 1, int(to)))
    if target == index:
        return names
    names.insert(target, names.pop(index))
    for position, macro_name in enumerate(names):
        macro = load_macro(macro_name)
        macro["order"] = position
        write_json(_path(macro_name), macro)
    return names


def _check_name(name: str) -> str:
    """The name as it is kept, or a refusal in plain words.

    A macro called "Late/Shift" and one called "Late_Shift" would land in
    the same file, and the second one saved would quietly replace the
    first.  A name that cannot be used as it is, is refused.
    """
    try:
        return check_name(name, "macro")
    except ValueError as exc:
        raise MacroError(str(exc)) from None


def save_macro(name: str, events: list[dict], repeat: int | None = None,
               delay: int | None = None) -> dict:
    """Save a macro under a name, replacing one with the same name.

    ``repeat`` is how many times the macro plays, and ``delay`` is how
    long it waits between the keys, in milliseconds. A delay of zero
    plays the keys as fast as the computer can manage them.
    """
    clean = _check_name(name)
    times = _number(repeat, 1, MAX_REPEAT, DEFAULT_REPEAT)
    wait = _number(delay, 0, MAX_DELAY_MS, DEFAULT_DELAY_MS)
    clean_events = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        vk = event.get("vk")
        if not isinstance(vk, int):
            continue
        clean_events.append({
            "vk": vk,
            "down": bool(event.get("down", True)),
            "text": str(event.get("text", ""))[:32],
        })
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    macro = {
        "name": clean,
        "created": stamp,
        "modified": stamp,
        "events": clean_events,
        "repeat": times,
        "delay": wait,
    }
    existing = read_json(_path(clean), None)
    if isinstance(existing, dict):
        if existing.get("created"):
            macro["created"] = existing["created"]
        if isinstance(existing.get("order"), int):
            macro["order"] = existing["order"]
    else:
        # A new macro goes to the end of the list.
        macro["order"] = len(list_macros())
    write_json(_path(clean), macro)
    return macro


def load_macro(name: str) -> dict:
    path = _path(name)
    data = read_json(path, None)
    if not isinstance(data, dict):
        raise MacroError(f"There is no macro called “{name}”.")
    return data


def delete_macro(name: str) -> None:
    path = _path(name)
    if not path.exists():
        raise MacroError(f"There is no macro called “{name}”.")
    path.unlink()


def rename_macro(name: str, new_name: str) -> dict:
    clean = str(new_name).strip()
    if not clean:
        raise MacroError("A macro needs a name.")
    macro = load_macro(name)
    if clean == name:
        return macro
    if _path(clean).exists():
        raise MacroError(f"There is already a macro called “{clean}”.")
    macro["name"] = clean
    macro["modified"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_json(_path(clean), macro)
    _path(name).unlink(missing_ok=True)
    return macro


def describe_macro(macro: dict) -> str:
    """A macro in words, for the list."""
    from ak820.remap import key_name

    events = macro.get("events", [])
    if not events:
        return "Empty"
    parts = []
    for event in events:
        if event.get("down"):
            parts.append(event.get("text") or key_name(event.get("vk", 0)))
    if not parts:
        return "Empty"
    if len(parts) <= 6:
        return " then ".join(parts)
    # Say how many there are, so it is clear that the list is shortened.
    return f"{' then '.join(parts[:6])} then {len(parts) - 6} more"
