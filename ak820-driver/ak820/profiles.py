"""The lighting setups the user saves.

A profile remembers the lighting and the per-key colours, and which
keyboard it was made for. A profile made for another keyboard is refused
rather than written to the wrong device.

Profiles live as JSON files in a ``profiles`` folder next to the app, or in
the user's own folder when that one cannot be written to.
"""

from __future__ import annotations

import time
from pathlib import Path

from ak820.store import check_name, data_folder, read_json, safe_name, write_json

#: The keyboard this app drives. A profile for any other keyboard is
#: refused.
DEVICE_ID = "ak820_wired"

FILES = "profiles"

#: Where the profiles the user shares with someone else are written.
EXPORTS = "exports"


class ProfileError(Exception):
    """A profile could not be used. The message says why, in plain words."""


def profile_dir() -> Path:
    """The folder the profiles are kept in."""
    return data_folder(FILES)


def _path(name: str) -> Path:
    return profile_dir() / f"{safe_name(name)}.json"


def _check_name(name: str) -> str:
    """The name as it is kept, or a refusal in plain words."""
    try:
        return check_name(name, "profile")
    except ValueError as exc:
        raise ProfileError(str(exc)) from None


def list_profiles() -> list[dict]:
    """Every profile, newest first."""
    found = []
    for path in sorted(profile_dir().glob("*.json")):
        data = read_json(path, None)
        if not isinstance(data, dict):
            continue
        data.setdefault("name", path.stem)
        data["storage"] = str(path)
        found.append(data)
    found.sort(key=lambda item: item.get("modified", ""), reverse=True)
    return found


def save_profile(name: str, state: dict) -> dict:
    """Save the lighting under a name, replacing one with the same name."""
    clean = _check_name(name)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    profile = {
        "name": clean,
        "device": DEVICE_ID,
        "created": stamp,
        "modified": stamp,
        "lighting": state.get("lighting", {}),
        "key_colors": state.get("key_colors", []),
    }
    existing = read_json(_path(clean), None)
    if isinstance(existing, dict) and existing.get("created"):
        profile["created"] = existing["created"]
    write_json(_path(clean), profile)
    return profile


def load_profile(name: str) -> dict:
    """Read a profile, refusing one that was made for another keyboard."""
    path = _path(name)
    data = read_json(path, None)
    if not isinstance(data, dict):
        raise ProfileError(f"There is no profile called “{name}”.")
    device = data.get("device")
    if device != DEVICE_ID:
        raise ProfileError(
            f"That profile was made for a different keyboard ({device or 'an unknown one'}), "
            f"so it will not be written to this one.")
    return data


def delete_profile(name: str) -> None:
    """Remove a profile."""
    path = _path(name)
    if not path.exists():
        raise ProfileError(f"There is no profile called “{name}”.")
    path.unlink()


def rename_profile(name: str, new_name: str) -> dict:
    """Give a profile a different name."""
    clean = _check_name(new_name)
    profile = load_profile(name)
    if clean == name:
        return profile
    if _path(clean).exists():
        raise ProfileError(f"There is already a profile called “{clean}”.")
    profile["name"] = clean
    profile["modified"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_json(_path(clean), profile)
    _path(name).unlink(missing_ok=True)
    return profile


def duplicate_profile(name: str, new_name: str) -> dict:
    """Copy a profile under a new name."""
    profile = load_profile(name)
    return save_profile(new_name, {
        "lighting": profile.get("lighting", {}),
        "key_colors": profile.get("key_colors", []),
    })


def export_profile(name: str, destination: Path) -> Path:
    """Write a profile to a file the user can keep or share."""
    profile = load_profile(name)
    path = Path(destination)
    write_json(path, profile)
    return path


def export_dir() -> Path:
    """The folder the profiles the user shares are written to."""
    return data_folder(EXPORTS)


def export_path(name: str) -> Path:
    """Where an exported profile is written.

    Its own folder, so that an exported file is not mistaken for one of
    the profiles the app keeps.
    """
    return export_dir() / f"{safe_name(name)}.json"


def import_profile(source: Path) -> dict:
    """Read a profile from a file the user picked."""
    data = read_json(Path(source), None)
    if not isinstance(data, dict):
        raise ProfileError("That file does not hold a profile.")
    device = data.get("device")
    if device != DEVICE_ID:
        raise ProfileError(
            f"That profile was made for a different keyboard ({device or 'an unknown one'}), "
            f"so it will not be written to this one.")
    name = str(data.get("name") or Path(source).stem).strip()
    # A profile of that name may already be here. The copy is given a
    # number rather than replacing the one that is already saved.
    if _path(name).exists():
        number = 2
        while _path(f"{name} {number}").exists():
            number += 1
        name = f"{name} {number}"
    return save_profile(name, {
        "lighting": data.get("lighting", {}),
        "key_colors": data.get("key_colors", []),
    })
