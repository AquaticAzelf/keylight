"""The loopback HTTP server: the JSON API and the static front end.

It binds 127.0.0.1 only and takes a free port unless one is given.  The address
it ended up on is printed to stdout, because that is how the window — or a
browser, when there is no window — finds the app.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ak820.api import Api

if getattr(sys, "frozen", False):
    # In a packed app the files live in the folder the packer unpacked
    # them into, not next to the module.
    UI_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "ui"
else:
    UI_DIR = Path(__file__).resolve().parent.parent / "ui"

HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    """One request: either an API call or a file from ``ui/``."""

    server_version = "Keylight"
    protocol_version = "HTTP/1.1"

    api: Api = None  # set on the subclass made by create_server

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            self._api(method, path)
        else:
            self._static(path)

    def _api(self, method: str, path: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        status, payload = self.api.handle(method, path, body)
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (UI_DIR / name).resolve()
        try:
            target.relative_to(UI_DIR.resolve())
        except ValueError:
            self._not_found()
            return
        if not target.is_file():
            self._not_found()
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("javascript"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _not_found(self) -> None:
        data = b"Not found\n"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        """Keep stdout clean: the address is the only thing this program prints."""

    def log_error(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def create_server(api: Api | None = None, port: int = 0) -> ThreadingHTTPServer:
    """A server on 127.0.0.1. Port 0 picks a free one."""
    handler = type("BoundHandler", (Handler,), {"api": api or Api()})
    server = ThreadingHTTPServer((HOST, port), handler)
    server.daemon_threads = True
    return server


def serve(api: Api | None = None, port: int = 0) -> None:
    """Run the server until the program is stopped."""
    server = create_server(api, port)
    print(f"Keylight on http://{HOST}:{server.server_address[1]}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Keylight app.")
    parser.add_argument("--port", type=int, default=0,
                        help="port to listen on; 0 picks a free one")
    args = parser.parse_args(argv)
    serve(port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
