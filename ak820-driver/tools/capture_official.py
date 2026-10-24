"""Watch what the official AJAZZ driver writes to the keyboard.

The vendor's app is the only thing that knows the extra settings - polling
rate, key repeat, the Windows-key lock, macros - and where they live in the
board's config space. This runs the app with Frida attached and logs every HID
report it sends, so those settings can be found by clicking them in the app
and watching which bytes change.

    python tools/capture_official.py --app "<path to>/AJAZZ AK820 (RGB Keyboard.exe"

The log is written to ``captures/official-<timestamp>.jsonl`` (one line per
report) and also echoed to the console.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import frida  # noqa: E402

HOOK_JS = r"""
const hooked = {};

function attach(module, fn, onEnter) {
    const key = module.name + "!" + fn;
    if (hooked[key]) return;
    let addr;
    try { addr = module.getExportByName(fn); } catch (e) { return; }
    hooked[key] = true;
    send({event: "hooked", target: key});
    Interceptor.attach(addr, {onEnter: onEnter});
}

function hexOf(buf, len) {
    const data = buf.readByteArray(len);
    return Array.from(new Uint8Array(data))
        .map(b => b.toString(16).padStart(2, "0")).join(" ");
}

function hookHid() {
    for (const module of Process.enumerateModules()) {
        if (module.name.toLowerCase() !== "hid.dll") continue;
        for (const fn of ["HidD_SetOutputReport", "HidD_SetFeatureReport"]) {
            attach(module, fn, function (args) {
                const len = args[2].toInt32();
                if (len <= 0 || len > 1024) return;
                let hex = "";
                try { hex = hexOf(args[1], len); } catch (e) { return; }
                send({event: "report", fn: fn, len: len, hex: hex});
            });
        }
    }
}

function hookWriteFile() {
    for (const module of Process.enumerateModules()) {
        if (module.name.toLowerCase() !== "kernel32.dll") continue;
        attach(module, "WriteFile", function (args) {
            const len = args[2].toInt32();
            if (len !== 64) return;   // a HID report is 64 bytes
            let hex = "";
            try { hex = hexOf(args[1], len); } catch (e) { return; }
            send({event: "report", fn: "WriteFile", len: len, hex: hex});
        });
    }
}

function hookAll() {
    hookHid();
    hookWriteFile();
}

Process.attachModuleObserver({ onAdded() { hookAll(); } });
setInterval(hookAll, 200);
hookAll();
send({event: "ready", modules: Process.enumerateModules().map(m => m.name).join(",")});
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, help="path to the official app's .exe")
    parser.add_argument("--out", default=None, help="where to write the log")
    args = parser.parse_args()

    app = Path(args.app)
    if not app.is_file():
        print("app not found: %s" % app)
        return 1

    out_dir = Path(__file__).resolve().parent.parent.parent / "captures"
    out_dir.mkdir(exist_ok=True)
    log_path = Path(args.out) if args.out else out_dir / (
        "official-%s.jsonl" % time.strftime("%Y%m%d-%H%M%S")
    )
    log = log_path.open("w", encoding="utf-8", buffering=1)

    def on_message(message, data):
        if message.get("type") == "send":
            payload = message["payload"]
            payload["t"] = time.time()
            if payload.get("event") == "report":
                print("%s  %s" % (time.strftime("%H:%M:%S"), payload["hex"]))
            else:
                print("· %s" % payload.get("event"))
            log.write(json.dumps(payload) + "\n")
        else:
            print("! %s" % message.get("description", message))
            log.write(json.dumps({"event": "error", "message": message}) + "\n")

    print("spawning %s" % app)
    device = frida.get_local_device()
    pid = device.spawn([str(app)], cwd=str(app.parent))
    session = device.attach(pid)
    script = session.create_script(HOOK_JS)
    script.on("message", on_message)
    script.load()
    device.resume(pid)
    print("running; log -> %s" % log_path)
    print("close the app when you are done, or press Ctrl-C here.")
    print("press Enter in this window to drop a marker into the log, so a "
          "setting change can be tied to the exact moment it happened.")

    def marker_reader() -> None:
        """Press Enter -> write a marker line, so changes can be located."""
        try:
            for line in sys.stdin:
                line = line.strip()
                log.write(json.dumps({
                    "event": "marker",
                    "note": line,
                    "t": time.time(),
                }) + "\n")
                log.flush()
                print("* marker%s" % (": " + line if line else ""))
        except Exception:
            pass  # no console to read from; markers are optional

    reader = threading.Thread(target=marker_reader, daemon=True)
    reader.start()

    try:
        while True:
            time.sleep(0.5)
            if not any(p.pid == pid for p in device.enumerate_processes()):
                break
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        print("log written to %s" % log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
