"""Find where every keycap sits on the board.

The per-key editor has to be able to say "that is the Q key" and put a
click target on it.  Every cap on the board is drawn with a dark outline, so
the caps can be found in a picture of it: the flood fill stops at the
outlines and each piece it fills is one cap.

The result is written as ``ui/assets/ak820-caps.json``: one box per cap, in
reading order.  The app draws the board from that file, so the numbers are
the record now, not the picture.  The picture is not in the repository and
is not used by the app.

    python tools/find_caps.py
"""

from __future__ import annotations

import base64
import json
import pathlib

from playwright.sync_api import sync_playwright

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "ui" / "assets"
PICTURE = ASSETS / "ak820-board.png"
OUT = ASSETS / "ak820-caps.json"

FIND_JS = """async (source) => {
  const img = new Image();
  img.src = source;
  await img.decode();
  const width = img.naturalWidth;
  const height = img.naturalHeight;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  const data = ctx.getImageData(0, 0, width, height).data;

  // The dark outline around a cap is the wall the fill stops at. A lit cap
  // is green, which is darker than the case but not dark enough to be a
  // wall, so the wall is the outline alone and then made a pixel thicker so
  // the fill cannot slip across a soft edge.
  const dark = new Uint8Array(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    if (data[i + 3] < 100) { dark[p] = 1; continue; }
    const lum = (data[i] * 299 + data[i+1] * 587 + data[i+2] * 114) / 1000;
    if (lum < 125) dark[p] = 1;
  }
  const wall = new Uint8Array(width * height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const p = y * width + x;
      if (!dark[p]) continue;
      wall[p] = 1;
      if (x > 0) wall[p - 1] = 1;
      if (x + 1 < width) wall[p + 1] = 1;
      if (y > 0) wall[p - width] = 1;
      if (y + 1 < height) wall[p + width] = 1;
    }
  }

  const seen = new Uint8Array(width * height);
  const boxes = [];
  const stack = [];
  for (let start = 0; start < wall.length; start += 1) {
    if (wall[start] || seen[start]) continue;
    stack.length = 0;
    stack.push(start);
    seen[start] = 1;
    let left = width, top = height, right = 0, bottom = 0, count = 0;
    while (stack.length) {
      const p = stack.pop();
      const x = p % width, y = (p - x) / width;
      count += 1;
      if (x < left) left = x;
      if (x > right) right = x;
      if (y < top) top = y;
      if (y > bottom) bottom = y;
      for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
        const np = ny * width + nx;
        if (!wall[np] && !seen[np]) { seen[np] = 1; stack.push(np); }
      }
    }
    boxes.push({ x: left, y: top, w: right - left + 1, h: bottom - top + 1, n: count });
  }
  return { width, height, boxes };
}"""


def main() -> int:
    data = base64.b64encode(PICTURE.read_bytes()).decode("ascii")
    url = f"data:image/png;base64,{data}"
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page()
        result = page.evaluate(FIND_JS, url)
        browser.close()

    boxes = result["boxes"]
    caps = [b for b in boxes if b["w"] >= 14 and 14 <= b["h"] <= 60 and b["n"] >= 250]
    # Group them into rows by where they sit, not by where they start: a
    # double-wide key is taller, so its top is higher than its neighbours'.
    caps.sort(key=lambda b: b["y"] + b["h"] / 2)
    rows: list[list[dict]] = []
    for box in caps:
        middle = box["y"] + box["h"] / 2
        if rows:
            last = rows[-1]
            centre = sum(b["y"] + b["h"] / 2 for b in last) / len(last)
            if abs(middle - centre) <= 9:
                last.append(box)
                continue
        rows.append([box])
    for row in rows:
        row.sort(key=lambda b: b["x"])

    # The key map knows which key is which and which light it uses.
    layout = json.loads(
        (ASSETS.parent.parent / "ak820" / "devices" / "ak820_wired.json")
        .read_text(encoding="utf-8")
    )
    expected = [key for row in layout["rows"] for key in row["keys"]]
    found = [box for row in rows for box in row]

    print("picture %dx%d" % (result["width"], result["height"]))
    print("%d caps found, %d keys in the map" % (len(found), len(expected)))
    if len(found) != len(expected):
        print("!! the counts do not match, not writing the file")
        return 1

    keys = []
    for key, box in zip(expected, found):
        keys.append({
            "led": key["chain"],
            "label": key["label"],
            "x": box["x"],
            "y": box["y"],
            "w": box["w"],
            "h": box["h"],
        })

    out = {
        "width": result["width"],
        "height": result["height"],
        "keys": keys,
        "knob": layout["knob"],
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s" % OUT.name)
    for key in keys[:4] + keys[-4:]:
        print("  %-6s led=%3d  x=%3d y=%3d w=%3d h=%3d" % (
            key["label"], key["led"], key["x"], key["y"], key["w"], key["h"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
