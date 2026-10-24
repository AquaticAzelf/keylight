"""Call one of the app's API routes and print what came back.

    python tools/call_api.py <url> <path> [json]
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    url = sys.argv[1].rstrip("/")
    path = sys.argv[2]
    payload = json.dumps(json.loads(sys.argv[3])).encode("utf-8") if len(sys.argv) > 3 else None
    request = urllib.request.Request(
        url + path, data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(response.status, response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read().decode("utf-8", "replace"))
    except Exception as exc:
        print("FAILED:", type(exc).__name__, exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
