"""The keyboard must fail cleanly, with a readable message, when it is busy."""

import subprocess
import sys
import textwrap

import pytest

from ak820.hid.device import (
    HidError,
    connect,
    find_ak820,
    open_device,
)

pytestmark = pytest.mark.hardware


def test_second_open_reports_the_conflict():
    device = find_ak820()
    if device is None:
        pytest.skip("AK820 not plugged in")

    first = open_device(device)
    try:
        with pytest.raises(HidError) as caught:
            open_device(device)
    finally:
        first.close()

    message = str(caught.value)
    assert message, "the error must explain itself"
    assert "another program" in message.lower()
    assert caught.value.code is not None


def test_connect_explains_a_busy_keyboard_in_a_second_process():
    """A second process must fail the same way, not hang or crash."""
    device = find_ak820()
    if device is None:
        pytest.skip("AK820 not plugged in")

    holder = open_device(device)
    try:
        script = textwrap.dedent(
            """
            import sys
            from ak820.hid.device import connect, HidError
            try:
                connect()
            except HidError as exc:
                print("HidError:", exc)
                sys.exit(0)
            print("opened unexpectedly")
            sys.exit(1)
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        holder.close()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "another program" in result.stdout.lower()
