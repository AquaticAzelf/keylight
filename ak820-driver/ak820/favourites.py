"""The colours the user has pinned.

A pinned colour is kept in the app's own folder, so it is there next
time the app starts and on the other computer if the folder is copied.
"""

from __future__ import annotations

from ak820.store import data_folder, read_json, write_json

FILES = "colours"
FILE = "favourites.json"

#: How many pinned colours are kept. A row of a hundred is not a row.
MAX = 12


def _path():
    return data_folder(FILES) / FILE


def _clean(colour) -> list[int] | None:
    """The colour as three numbers, or None when it is not one."""
    if not isinstance(colour, (list, tuple)) or len(colour) != 3:
        return None
    channels = []
    for channel in colour:
        if isinstance(channel, bool) or not isinstance(channel, int):
            return None
        if not 0 <= channel <= 255:
            return None
        channels.append(channel)
    return channels


def favourites() -> list[list[int]]:
    """The pinned colours, in the order they were pinned."""
    stored = read_json(_path(), [])
    if not isinstance(stored, list):
        return []
    found = []
    for entry in stored:
        colour = _clean(entry)
        if colour is not None:
            found.append(colour)
    return found


def toggle(colour) -> tuple[list[list[int]], bool]:
    """Pin a colour, or unpin it if it is already pinned.

    Gives back the list of pinned colours and whether the colour was
    added or taken away.
    """
    clean = _clean(colour)
    if clean is None:
        raise ValueError("A colour must be three numbers from 0 to 255.")
    found = favourites()
    if clean in found:
        found.remove(clean)
        added = False
    else:
        found.append(clean)
        found = found[-MAX:]
        added = True
    write_json(_path(), found)
    return found, added
