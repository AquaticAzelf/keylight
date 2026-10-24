# AK820 Driver — design document

Date: 2026-10-20
Status: **awaiting owner approval**
Target hardware: AJAZZ AK820, 75% wired (USB `320F:505B`, EVision/Yichip family, usage page `0xFF1C`, interface 1)

---

## 1. Intent and the why

The official AJAZZ software for this keyboard is a 3.6 MB Win32 shell built on Tencent
DuiLib (DirectUI). It ships ~1,400 skin PNGs and 37 MB of Chinese fonts, drives mice,
headsets, hubs and mouse pads as well as keyboards, and talks to the internet to fetch
per-board configuration. The result is a device-list tab shell where every useful control
is buried, nothing is obvious, and the app is not portable.

The owner wants a **portable replacement for the AK820 specifically**: same hardware
control, modern interface, no installer, no registry writes, no cloud, no account, and
features the official app either lacks or hides.

## 2. Goals

- One portable executable. Double-click to run. Nothing installed, nothing registered.
  Uninstalling = deleting the file.
- Every customization the keyboard's firmware actually supports, and no fake buttons
  for things the firmware cannot do.
- Professional desktop look: real window, custom title bar, dark theme, no browser
  chrome, no device-picker tab shell.
- Works with the keyboard over plain USB HID. No kernel driver, no service, no admin.
- Local profile storage (save/load/rename/export). No cloud, no telemetry, no login.
- Lighting is the core and must be rock solid: every hardware mode, brightness, speed,
  direction, colour, per-key colour, screen-colour capture, mic-reactive mode.

## 3. Non-goals

- No support for other boards, mice, headsets, hubs or mouse pads.
- No TFT/clock/image upload, Bluetooth, 2.4 GHz wireless, Rapid Trigger or Hall-effect
  calibration. The plain wired AK820 has none of that hardware.
- No keymap-on-bootloader flashing, no firmware modification, no risk of bricking.
- No multi-device manager, no account, no update server.

## 4. Anti-goals (what would make this a failure)

- Shipping buttons that silently do nothing because the firmware ignores them.
- A "web app in a browser" that needs a browser extension or a manual driver setup.
- A UI that is only clean because features were removed.
- Writing anything to the registry, or leaving files in system directories.
- Taking control of the keyboard's key input globally (no OS-level key interception).

## 5. Constraints

- **No compiler toolchain on this PC** (no MSVC, gcc, Rust, .NET SDK, Java, Ghidra,
  rizin, objdump). Only Python 3.14, Node 24, Git, 7-Zip.
- **No live keyboard traffic yet** (owner instruction, 2026-10-20). Protocol work must
  proceed using captured/offline evidence until the owner permits a live test.
- The keyboard is currently plugged into this PC and enumerating correctly.
- Windows 11, PowerShell 5.1 (no `&&`; prefer `.ps1` files), `cmd.exe` quoting traps.
- A Ghidra/JDK install (~800 MB) would be needed only if the capture route fails.

## 6. How it gets made

### 6.1 Stack (my call)

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3, `ctypes` → `hid.dll` / `setupapi.dll` | Zero native dependencies, no compiler, works on Python 3.14, trivial to freeze |
| UI | HTML/CSS/JS, served by a loopback HTTP server on `127.0.0.1` | Clean modern UI; no Electron tax |
| Window | `pywebview` (Edge WebView2) | Real desktop window, no browser chrome, no registry writes, WebView2 ships with Windows 11 |
| Fallback window | If `pywebview`/WebView2 is missing: launch Edge in `--app=` mode at the same URL | Never a dead end |
| Packaging | PyInstaller `--onefile` | One `.exe`; `--onedir` optional for startup speed |
| Protocol | Pure-Python `protocol/` package | Unit-testable, no hardware needed for most tests |

Rejected: Electron (no prebuilt HID binding usable without a compiler; huge download),
C#/.NET (no SDK installed), Rust (no toolchain), a plain `.html` file (owner wants a real
portable `.exe`).

### 6.2 Project layout

```
application/
  docs/superpowers/specs/2026-10-20-ak820-driver-design.md
  docs/superpowers/plans/2026-10-20-ak820-driver.md
  .opencode/skills/                 project-local design skills (see 6.8)
  ak820-driver/
    ak820/                   python package
      __init__.py
      hid/                   ctypes HID transport (enumerate, open, write, read)
      protocol/              packet framing, EVision V1 commands, lighting, session
      devices/               board definitions (LED map, key layout, capabilities)
      app.py                 window bootstrap (pywebview) + Edge fallback
      server.py              loopback HTTP server + static file serving
      api.py                 JSON routes
      profiles.py            portable profile store
      remap.py  macros.py    PC-side remap layer (WH_KEYBOARD_LL) and macro storage
      mic.py                 native WASAPI level capture (no audio stored)
      screen.py              GDI pixel sample for the eyedropper
      settings.py            device settings that the firmware actually supports
    ui/                      index.html, app.css, app.js, tokens.css, keyboard.js,
                             effects.js, picker.js, DESIGN.md
    tools/                   probe.py, probe_params.py, light_test.py, fetch_board_config.py,
                             derive_led_map.py, capture/ (Frida harness)
    tests/                   offline protocol + API tests (no hardware required)
    docs/ak820-protocol.md   the measured byte-level protocol spec
    build.ps1                PyInstaller build
```

### 6.8 Design skills (installed project-local, not global)

The front-end is built by sub-agents that must load these from
`application/.opencode/skills/`:

| Skill | Role in this project |
|---|---|
| `frontend-design` | Art direction: palette, type, layout, anti-AI-slop traits, two-pass plan-then-build |
| `impeccable` | App-UI mode ("Operate"), plus its `shape` / `critique` / `polish` / `bolder` / `quieter` / `typeset` / `harden` commands |
| `design-taste-frontend` | Anti-slop house style, measured in a real browser, screenshot look-and-fix loop |
| `emil-design-eng` | Motion: springs, easing, perceived performance, responsive controls |
| `web-design-guidelines` | Final audit of accessibility, UX and interaction rules |
| `webapp-testing` | Playwright scripts to drive the local UI and capture screenshots for review |
| `design-systems-frontend-architecture` | Token structure and component contracts behind `ui/tokens.css` |
| `information-architecture-navigation` | Sidebar grouping, section labels, wayfinding |
| `ux-usability-foundations` | Affordances, feedback, error prevention, destructive-action confirmation |
| `interaction-patterns-components` | State and behaviour of pickers, lists, toggles, sliders, the on-screen keyboard canvas |
| `forms-inputs-checkout` | Inputs: sliders, segmented controls, validation, grouping |
| `ux-writing-content-design` | Microcopy: labels, empty states, confirmations, plain-language errors |
| `accessibility-inclusive-design` | Keyboard-only operation, focus order, contrast, control states |
| `ui-visual-composition` | Hierarchy, spacing, visual states of the mode rows and sliders |

**Freshness rule.** Popular is not the same as current — a heavily starred skill can be
years old and untouched. `.opencode/skills/README.md` records each skill's source,
licence and last-updated date; check it before loading one, and do not add a skill
whose own path has not changed in its repo for more than about three months without
asking the owner. Star count is not evidence of currency.

### 6.3 The protocol (known portion)

64-byte HID output report, report ID `0x04`:

```
byte 0     0x04              report id
byte 1-2   checksum          u16 LE, sum of bytes 3..63
byte 3     command           0x01 BEGIN | 0x02 END | 0x06 SET_PARAM | 0x11 LED data
byte 4     size
byte 5-6   parameter id / offset
byte 7     0
byte 8-63  payload
```

Lighting parameter: id `0x00`, size 8, payload
`[mode, brightness, speed, direction, random, R, G, B]`
(brightness 0-4, speed 0-5 where 0 = fastest, direction 0-3 = L/R/U/D).

Packet details, taken from the working reference implementation:

| Step | Bytes |
|---|---|
| `BEGIN` | `04 01 00 01 00 00 00 00 …` — checksum **not** computed, packet is fixed |
| `END` | `04 02 00 02 00 00 00 00 …` — checksum **not** computed, packet is fixed |
| `SET_PARAM` (0x06) | `04 <ck> <ck> 06 <size> <param> 00 <payload…>` — checksum computed |
| `LED data` (0x11) | `04 <ck> <ck> 11 <size> <off lo> <off hi> 00 <payload…>` — checksum computed |

Checksum = `sum(bytes[3..63])` as u16, little-endian into bytes 1-2. Every write is
followed by a read, to let the keyboard answer.

**Per-key colour is a firmware feature**, not a client-side trick: cmd `0x11` writes a
blob of `3 × LED count` bytes at a byte offset, where the offset of a key is
`led_index × 3`. So per-key colour needs (a) the wire command, which is known, and
(b) the key → LED index map, which is **not** public for this board (see 6.4).

The sibling V2 controller exposes a wider parameter space that the firmware family
shares — `MODE 0x00, BRIGHTNESS 0x01, SPEED 0x02, DIRECTION 0x03, RANDOM 0x04,
MODE_COLOR 0x05, COLOR_OFFSET 0x08, LED_MODE_COLOR 0x11, CURRENT_CUSTOM_MODE 0x19,
LOGO 0x1a, LOGO_ON_OFF 0x23, EDGE 0x24, END 0x2b`, plus polling rate `0x0F`
(125/250/500/1000 Hz) and custom-colour read-back `0x10`. These are the *candidate*
names for the extra settings we intend to surface; each must be confirmed against this
board before it appears in the UI.

Hardware modes `1..18, 20` = wave, cloud, vortex, spectrum, breath, static, reactive,
ripple, traverse, stars, fireworks, roll, wave bar, cartoon, rain, scan, surmount, speed,
custom. AJAZZ adds two software modes: `29` mic audio wave, `30` screen colour capture.

### 6.4 Unknowns to resolve (offline, no keyboard)

1. **Extended command set** — the official app funnels everything through one
   `PropertyControl(id, payload)` call in `osConfLib.dll`. Property ids and payloads for
   macros, key remap, on-device profiles, knob, and firmware settings are undocumented.
2. **Per-key LED index map** — needed for per-key colour, and **no public source exists
   for this board**. Every public AK820 project targets the AK820 **Max / Max Plus / Pro**
   (magnetic, Hall-effect, TFT), which is a different protocol. The plain wired AK820's
   map is only available from: (a) the board config the official app downloads from
   AJAZZ's servers, (b) the app's own resources, or (c) empirical probing once a live
   test is allowed. The shared reference implementation's `matrix_map[6][23]` belongs to
   other EVision boards and must not be trusted for the AK820.
3. **Firmware capability** — whether the board answers a capabilities query and whether it
   has on-device macro storage.
4. **Knob behaviour** — whether the rotary knob is configurable on this board.

### 6.5 How the unknowns get resolved

**Primary: instrument the official app, block the hardware.** Run a sandboxed copy of the
official app under **Frida** (Python package, no compiler, no driver, no admin). A
Frida script intercepts the app's HID write path and:
- records every 64-byte packet and every property id/argument the app sends, and
- **returns success without forwarding to the keyboard** — the keyboard is never written to.

The same run records the app's read-back traffic. The captured traffic becomes the
specification for the extended features, and is replayed in our own implementation.

**Secondary: static analysis of `osConfLib.dll` / the app** with `pefile` (already
available) for exports, imports, embedded strings, and resource/config data.

**Last resort: install Ghidra + JDK** to decompile `osConfLib.dll`. Needs owner approval
(~800 MB). Only reached if capture yields nothing.

**Live hardware test** (send one colour packet, read the reply) is a separate, later
step, gated on owner permission. Nothing in the build depends on it: the protocol layer
is written against the captured spec and unit-tested offline with recorded packets.

### 6.6 Feature set

**Lighting (core, hardware-backed)**
- All 19 firmware modes + Off, with a live animated preview of each on screen.
- Brightness, speed, direction, random-colour flag, master colour, "apply to all keys".
- Per-key colour editing on a live 82-key AK820 layout, with a picker, brush, fill and
  clear, and a "match official app" per-key table.
- Screen-colour capture: full-screen overlay picker that samples the real screen pixel
  (native grab, not a screenshot file).
- Mic-reactive mode: browser `getUserMedia` amplitude → device.
- Presets: save any lighting state as a named preset; presets live in a portable folder.

**Device settings (only what the firmware accepts)**
- On-device profile slots, if the firmware exposes them.
- Knob configuration, if exposed.
- Polling rate / NKRO / Windows-lock style toggles, if exposed.
- Any item the firmware rejects is **not shown** — the UI is built from measured
  capabilities, not from the official app's button list.

**Macros and key remap**
- Implement on-device if the firmware stores them.
- Otherwise implement as an in-app, opt-in "remap layer" that only applies while the app
  is running, clearly labelled as PC-side, and never a global hook.

**Profiles**
- Named local profiles, rename, duplicate, delete, import/export as JSON.
- Optional "apply at launch" is deliberately **not** included: it would need a startup
  entry (registry / startup folder), which the no-registry rule forbids.

### 6.7 UI direction

Dark, dense, keyboard-first. Left sidebar of sections, main canvas, a persistent top bar
showing device name, connection state and the current mode. A real on-screen AK820
layout is the centrepiece: it animates the active effect, doubles as the per-key colour
editor, and highlights keys as they are pressed (via the HID input report when the
firmware reports it, otherwise via a local key capture). Custom title bar, no
browser chrome, no device picker, no device list.

## 7. Decisions the owner made (not mine to revisit)

- Deliverable is a **portable `.exe`**, not a web page.
- It must **not write to the registry**.
- It must expose **every** customizable option the keyboard has.
- It should look like a **professional desktop application** — go all out.
- Scope is **everything**, not lighting-only.
- **No live keyboard traffic** until the owner says so.

## 7b. Decisions the owner made in response (resolved 2026-10-20)

1. **Live testing is allowed.** The owner's answer: "you know what you can test anything
   i dont mind" and "do what you kind you have full permission". Writes to the keyboard
   are permitted. The capture run is permitted. The hook is permitted.
2. **The official app may be run here**, sandboxed, with network access, under an
   in-process tracer that logs and blocks. "do what you kind you have full permission".
3. **A low-level keyboard hook is allowed** for the PC-side remap/macro fallback, clearly
   labelled as PC-side and active only while our app runs.
4. **Screen colour capture is a one-shot eyedropper**, not a live screen-average effect.


## 7c. My calls (made, not asked — correct me if wrong)

- **Licence cleanliness:** the protocol facts are re-implemented from scratch. No GPL
  code is copied. No vendor binaries are redistributed. The official app is used only
  locally, for observation.
- **"Portable" means:** no registry writes, nothing installed to Program Files, nothing
  written to AppData as an install, uninstall = delete the folder. A one-file `.exe` that
  unpacks itself to a temp folder at launch is acceptable; a persistent WebView2 profile
  is redirected into the app's own folder.
- **Microphone capture** is done natively (WASAPI via ctypes) rather than in the web
  page, because a web page in an embedded window cannot ask for the microphone
  reliably, and it must also work in the browser fallback.
- **The HID handle** is opened on demand per transaction and closed again, so the app
  never blocks other HID tools (the official driver, OpenRGB) from opening the keyboard.
- **Dev-time downloads** of the vendor's board config are acceptable during
  development; the shipped product contains no download and no network code at all.
- **Shipping order:** lighting first and complete, then profiles, then the extended
  features that the capture actually proves exist.

## 8. What is left for the builder

- Implement `hid/` transport (enumerate by VID/PID + usage page, open, write 64-byte
  reports, read input reports).
- Implement `protocol/` framing, checksum, BEGIN/END/SET_PARAM/LED-data, and the
  property-id table once capture fills it in.
- Implement the UI per 6.7.
- Build the Frida capture harness under `tools/`.
- Write offline unit tests that replay captured packets through the protocol layer.
- Package with PyInstaller; verify the `.exe` starts, finds the keyboard, and writes
  nothing outside its own folder.

## 9. Risks

| Risk | Impact | Fallback |
|---|---|---|
| The firmware supports only lighting (likely) | Macros/remap cannot be on-device | Implement the PC-side remap layer, label it honestly |
| Frida capture blocked by the app (anti-tamper) | Extended features unknown | Static analysis; then Ghidra install (owner approval) |
| WebView2 missing on some PCs | No window | Edge `--app` fallback, then plain browser |
| `pywebview`/`pyinstaller` wheels missing for Python 3.14 | Packaging blocked | Use Python 3.13/3.12 for the build if needed |
| Per-key LED map wrong | Per-key colours land on wrong keys | Derive empirically once a live test is allowed |
