"""The window.

The app is a loopback server plus a window pointed at it.  The window is a
WebView2 (Edge) view through pywebview; if that cannot be opened, the same
address is handed to Edge in app mode, so there is never a dead end.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from ak820.server import create_server

WINDOW_TITLE = "Keylight"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
MIN_WIDTH = 1100
MIN_HEIGHT = 720

EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def log(message: str) -> None:
    """Write a line to the log beside the app.

    The packed app has no console window, so anything worth saying has to
    go somewhere the user can open.
    """
    try:
        from ak820 import store

        path = store.app_folder() / "keylight.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def main() -> int:
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, name="ak820-http", daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Keylight on {url}", flush=True)
    log(f"Keylight on {url}")
    try:
        try:
            import webview
        except ImportError as exc:
            print(f"No window toolkit available ({exc}).", file=sys.stderr)
            log(f"No window toolkit available ({exc}).")
        else:
            try:
                webview.create_window(WINDOW_TITLE, url, width=WINDOW_WIDTH,
                                      height=WINDOW_HEIGHT,
                                      min_size=(MIN_WIDTH, MIN_HEIGHT))
                webview.start()
                return 0
            except Exception as exc:  # pywebview raises its own types
                print(f"Could not open a window ({exc}).", file=sys.stderr)
                log(f"Could not open a window ({exc}).")
        return _open_in_edge(url)
    finally:
        server.shutdown()
        server.server_close()


def _open_in_edge(url: str) -> int:
    """Show the app in an Edge app window when no other window was possible."""
    edge = next((path for path in EDGE_PATHS if Path(path).exists()), None)
    if edge is None:
        print(f"Open this address to use the app: {url}", file=sys.stderr)
        log(f"Open this address to use the app: {url}")
        return 1
    print("Opening the app in Microsoft Edge.", flush=True)
    log("Opening the app in Microsoft Edge.")
    subprocess.run([edge, f"--app={url}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
