import os
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True, scope="session")
def app_data_in_a_temporary_folder():
    """Keep the tests out of the user's own folders.

    The app keeps profiles, macros and its settings next to itself, or in
    the user's own folder. The tests must not write into either, so they
    are pointed at a folder that is thrown away afterwards.
    """
    with tempfile.TemporaryDirectory() as folder:
        previous = os.environ.get("AK820_DATA_DIR")
        os.environ["AK820_DATA_DIR"] = folder
        # The settings file sits next to the app, not in the data folder, so
        # it is pointed somewhere harmless as well.
        settings = os.environ.get("AK820_SETTINGS_FILE")
        os.environ["AK820_SETTINGS_FILE"] = str(pathlib.Path(folder) / "settings.json")
        try:
            yield folder
        finally:
            if previous is None:
                os.environ.pop("AK820_DATA_DIR", None)
            else:
                os.environ["AK820_DATA_DIR"] = previous
            if settings is None:
                os.environ.pop("AK820_SETTINGS_FILE", None)
            else:
                os.environ["AK820_SETTINGS_FILE"] = settings
