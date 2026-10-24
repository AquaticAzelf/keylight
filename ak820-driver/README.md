# Ak820Driver

A portable Windows configurator for the **AJAZZ AK820** 75% wired keyboard
(USB `320F:505B`, EVision/Yichip family).

No installer, no registry writes, no cloud, no account. One `.exe`; delete the folder
to uninstall.

## Layout

| Path | What it is |
|---|---|
| `ak820/` | Python package: HID transport, protocol, features, HTTP API |
| `ui/` | The visible front end (vanilla HTML/CSS/JS, no build step) |
| `tools/` | Protocol probes, the live-light test, the Frida capture harness |
| `tests/` | Offline tests — most need no hardware |
| `docs/ak820-protocol.md` | The measured byte-level protocol spec |

## Development

```
C:\Python314\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install pytest frida pywebview pyinstaller
.venv\Scripts\python.exe -m pytest
```

## Documents

- Design: `../docs/superpowers/specs/2026-10-20-ak820-driver-design.md`
- Plan: `../docs/superpowers/plans/2026-10-20-ak820-driver.md`
