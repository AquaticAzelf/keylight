# Keylight

A small, portable configurator for the **AK820** 75% keyboard, for Windows.

It talks to the keyboard over USB directly, so it can set the lighting, paint
each key its own colour, change the report rate, lock the Windows key or swap
Win and Alt, record short macros and bind them to a key, and keep a set of
lighting profiles of your own.

**It is not made by, or endorsed by, AJAZZ.** It is a third-party tool for a
keyboard that AJAZZ sells. "AK820" is used here only to say which keyboard it
works with.

## What it does

| Section | What it is for |
|---|---|
| **Lighting** | The effect the board runs, its brightness, speed and direction, and its colour. There are twenty-one effects; the board decides which of them it can do. |
| **Per-key** | Painting each key its own colour, one at a time or across the whole board at once. |
| **Macros** | Recording a few keys and playing them again with one key. The keys are recorded and played on the computer; the keyboard itself keeps no macros. |
| **Profiles** | Saving the lighting you like, and putting it back later. |
| **Settings** | The app's own settings, and the keyboard's own: the report rate (1000/500/250/125 Hz), Windows Lock and Exchange key, read from and written to the board itself. |

## What it does not do

- **No cloud, no account, no network.** Nothing leaves the computer.
- **No installer and no registry.** Copy the folder anywhere and run it.
  Delete the folder and it is gone.
- **No firmware updates.** Flashing a keyboard is not something a small tool
  should be able to do by accident.

## Running it

Needs Windows 10 or later and Python 3.11 or later (tested on 3.14).

```powershell
cd ak820-driver
.venv\Scripts\python.exe -m ak820.app
```

The app opens a window on `http://127.0.0.1:8731` and serves it to itself.
Nothing else can reach that address.

To run the tests:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Where it keeps your files

Next to the app, in a `profiles` folder and a `macros` folder, and a
`settings.json`. If the folder the app is in cannot be written to, those files
go to `%APPDATA%\Keylight` instead. The app shows you where they are, under
**Settings**.

## Building the one-file executable

```powershell
cd ak820-driver
powershell -ExecutionPolicy Bypass -File build.ps1
```

The result is `dist\Keylight.exe`. It needs the WebView2 runtime, which is on
every Windows 11 machine and on Windows 10 where it has been installed.

## How the keyboard was worked out

The whole protocol - the packet framing, the config space, the twenty-one
effects, the per-key LED chain, the system settings - is written up in
[docs/ak820-protocol.md](docs/ak820-protocol.md), and everything in it was
measured on the hardware or read out of the official driver. The working
notes from that investigation are under
[docs/superpowers/plans/](docs/superpowers/plans/); the vendor files they
reference were never part of this repository.

## Licence

MIT — see [LICENSE](LICENSE). See also [NOTICE](NOTICE) for the credits.
