# How to capture the byte offsets (polling rate, Windows Lock, Exchange Key)

The official AJAZZ driver is the only thing that knows where those three
settings live in the board's config. We watch what it writes to the keyboard
while you click them, and the byte that moves is the answer.

**Time needed: about 10 minutes.**

## Before you start

- The keyboard must be plugged in, and the **Keylight app must be CLOSED**
  (it holds the board open exclusively — it will fight the official driver).
- The official driver lives in the repo at
  `.scratch/vendor/official_app/app/`. The file to open is
  `AJAZZ AK820 有线RGB Keyboard.exe` (the name has Chinese characters in it:
  有线 = "wired").

## 1. Start the capture

Open a terminal (PowerShell) in the `ak820-driver` folder and run:

```powershell
.venv\Scripts\python.exe tools\capture_official.py --app "..\.scratch\vendor\official_app\app\AJAZZ AK820 有线RGB Keyboard.exe"
```

The official driver will start on its own, hooked. Leave that window open.

> If the driver refuses to start, or flashes and exits, stop and tell me — I
> will find another way in. Do not fight it.

## 2. Click through the settings

In the official driver, open the keyboard's device settings. For each of the
three settings below: **change it, wait 10 seconds, change it back, wait 10
seconds.**

| # | Setting | What to click |
|---|---|---|
| 1 | **USB report rate** | 1000Hz -> 500Hz -> back to 1000Hz |
| 2 | **Windows Lock** | on -> off |
| 3 | **Exchange Key** | on -> off |

Do them one at a time, with a clear gap between them. Do not touch anything
else in the driver while you do this — every extra click is another byte that
moves.

## 3. Mark the moments

In the terminal running the capture, **press Enter** just before you change a
setting, and type what you are about to do, then Enter again:

```
polling rate 1000 -> 500
```

That drops a timestamped marker into the log so the change can be tied to the
exact moment. If you skip the markers it still works — I can still see which
bytes changed — but the markers make it unambiguous.

## 4. Stop

Close the official driver. The capture window will say the log was written to
`captures/official-<timestamp>.jsonl`. **That file is the whole result.**

## 5. Tell me

Say "capture done". I will read the log and report which byte is which.

## If something goes wrong

- The driver will not start -> tell me, do not force it.
- The keyboard stopped responding -> unplug and replug it, then tell me.
- The capture window shows `!` lines -> tell me, that means the hook failed.
