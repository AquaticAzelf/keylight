"""Where the app keeps its own files.

Everything the app saves - profiles, macros, its settings - lives in a
folder next to the executable, so a portable copy of the app carries them
along. When that folder cannot be written to (the app sitting in
``Program Files``, say) the files go to the user's own folder instead.

Nothing is written to the registry.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "Keylight"


def app_folder() -> Path:
    """The folder the app is running from."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_folder(name: str) -> Path:
    """A folder for one kind of the app's own files.

    The folder next to the app is used when it can be written to; otherwise
    the user's own folder is. ``AK820_DATA_DIR`` puts the files somewhere
    else entirely, which is how the tests keep out of the user's way.
    """
    override = os.environ.get("AK820_DATA_DIR")
    if override:
        folder = Path(override) / name
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    try:
        folder = app_folder() / name
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return folder
    except OSError:
        base = os.environ.get("APPDATA") or str(Path.home())
        folder = Path(base) / APP_NAME / name
        folder.mkdir(parents=True, exist_ok=True)
        return folder


def read_json(path: Path, default):
    """Read a JSON file, or give back the default when it is not there."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    """Write a JSON file, replacing it whole."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def safe_name(name: str) -> str:
    """A name that is safe to use as a file name."""
    cleaned = "".join("_" if character in '\\/:*?"<>|' else character for character in name)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "profile"


#: Characters Windows will not put in a file name.
ILLEGAL_NAME_CHARS = set('\\/:*?"<>|')


def check_name(name: str, what: str = "profile") -> str:
    """The name as it may be used, or a refusal in plain words.

    A name that Windows would change on the way to the disk is refused
    rather than changed.  Changing it quietly is how two different names
    end up in the same file, and the second one saved replaces the first
    without a word.
    """
    clean = str(name).strip()
    if not clean:
        raise ValueError(f"A {what} name is needed.")
    if len(clean) > 64:
        raise ValueError(f"A {what} name can be at most 64 characters long.")
    if set(clean) & ILLEGAL_NAME_CHARS:
        raise ValueError(f'A {what} name cannot contain \\ / : * ? " < > or |.')
    if clean != safe_name(clean):
        raise ValueError(f"A {what} name cannot start or end with a dot, "
                         "or be only dots.")
    return clean
