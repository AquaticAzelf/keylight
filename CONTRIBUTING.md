# Contributing to Keylight

Thanks for wanting to help. Keylight is a small, self-contained Windows tool;
the bar for a change is that it stays that way.

## Development setup

From PowerShell, in the repository root:

```powershell
cd ak820-driver
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

`[dev]` includes pytest, PyInstaller and the capture/analysis tools under
`tools/`. The `.venv` folder is git-ignored.

Run the app:

```powershell
.\.venv\Scripts\python.exe -m ak820.app
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite is designed to run without the keyboard attached: `conftest.py`
redirects profiles, macros and settings into a temporary folder so tests never
touch your own files. Tests that do need the board are marked `hardware`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not hardware"
```

CI runs on Windows against Python 3.11, 3.12 and 3.13 (see
`.github/workflows/tests.yml`). If you add a test for packet framing or the
config space, put the expected bytes in the assertion rather than recomputing
them with the same helper the app uses — a test that mirrors the implementation
cannot catch an encoding mistake.

## Working on the protocol

- `docs/ak820-protocol.md` is the reference: packet framing, the config space,
  the lighting effects and the per-key LED chain.
- The investigation notes live under `docs/superpowers/`. The vendor files they
  refer to were never part of this repository, and must not be added.
- `tools/CAPTURE-HOWTO.md` describes how to capture traffic from the official
  driver if you need to verify a command.
- Facts about the hardware are fine to document; code from other projects is
  not. See [NOTICE](NOTICE) for how the protocol facts are credited.

Please include the command numbers, the observed bytes and the keyboard/firmware
variant when reporting a protocol finding — "it didn't work" is not reproducible.

## Pull requests

Keep changes focused, say what you tested and on which Windows/Python version,
and update the docs when behaviour changes. Do not add network access, accounts,
telemetry, an installer, or registry writes; those are explicit non-goals of the
project.

## Licence

MIT — see [LICENSE](LICENSE). By contributing you agree your change is licensed
under the same terms. See also [NOTICE](NOTICE).
