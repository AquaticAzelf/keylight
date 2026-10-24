# Keylight — a guide

Keylight is a small program for setting the lights on an **AK820**
keyboard. It runs on your computer and talks to the keyboard over USB.
It is not made by the people who make the keyboard, and it is not
supported by them.

---

## Getting it running

1. Copy the folder with the program onto your computer. Any folder will
   do — the desktop is fine.
2. Double-click **Keylight.exe**.
3. A window opens. If the keyboard is plugged in, the app finds it.

There is nothing to install. The program does not write to the registry,
does not reach the internet, does not want an account, and does not
start up when you log on. The only thing it adds is a small log file
next to the program, called `keylight.log`.

**To remove it:** close the window, delete the folder. That is the whole
of it. Your profiles, macros and settings go with it, so copy them out
first if you want to keep them.

### If the window does not open

Keylight shows itself in a window built on the Microsoft Edge WebView2,
which is already part of Windows 11. If that is not available, Keylight
opens in Microsoft Edge instead. If neither works, open
`keylight.log` next to the program in Notepad — the last line says the
address to visit.

---

## The five things it does

### Lighting

The board is the picture at the top. What it does now is written beside
it.

- **Effect** — the pattern the board runs. Pick one and it changes.
- **Colour** — the colour of the effect. Click the square, drag the
  strip, or type a colour code in the box. **Random** gives you a
  colour to try. **Pin** keeps a colour you like, so it is always one
  click away.
- **Brightness, Speed, Direction** — how bright, how fast, and which
  way it travels. Some effects do not move, and the direction is greyed
  out for those.

Everything is sent to the keyboard as you make it. There is no "apply"
button because there is nothing to apply.

### Per-key

Click a key on the board to paint it. Hold the mouse down and drag to
paint a run of keys.

- **Whole board** — paint every key at once, clear them all, or invert
  the colours.
- **Brush** — leave it off and only the key you click is painted; turn
  it on and every key the mouse passes over is painted too.

Colours are kept in the keyboard, so they are still there when you
unplug it.

### Macros

A macro is a few keys played in order.

- **Record** — press it, then press the keys you want. The app holds
  them back while you record, so they do not do anything.
- **Times** and **Delay** — how many times the macro plays, and how
  long it waits between the keys. A delay of nothing plays them as fast
  as the computer can manage them.
- **Play** — play the macro once, to hear what it does.
- **Keys** — bind a macro to one key. While the app is changing keys,
  pressing that key plays the macro instead. Turn it off and the keys
  go back to what they were.

**The macros run on your computer, not inside the keyboard.** The
keyboard itself keeps no macros and nothing about it changes. The app
has to be running for them to play.

### Profiles

A profile is the lighting you saved, so you can come back to it.

- **Save the current lighting** — saves what the board is showing now.
- **Duplicate, Export, Import** — copy a profile, write it to a file to
  give to someone, or read one back in.
- Click a profile to put it on the keyboard.

The keyboard also keeps three setups of its own, under **On the
keyboard**. They are the board's own, and they travel with the board
when you unplug it.

### Settings

- **Theme** — light, dark, or the same as Windows.
- **Look for the keyboard** — how often the app checks whether the
  keyboard is plugged in. "Never" means never.
- **Remember where you were** — open on the section you left.
- **Ask before deleting** — always check before removing a profile or a
  macro.
- **Show what the app is doing** — say when a change has reached the
  keyboard.

**This app** holds the settings above. **The keyboard** shows what the
board takes — the report rate, Windows Lock (which stops the Win key
reaching Windows) and Exchange key (which swaps Win and Alt) — and has a
button to put the lighting back to how it came. Those three live on the
board itself, so they stay set when the app is closed.
**Where the app keeps its files** shows the folders, so you can back
them up.

---

## Where your files are

| What | Where |
|---|---|
| Profiles | `profiles` folder next to the program |
| Macros | `macros` folder next to the program |
| Pinned colours | `colours` folder next to the program |
| Settings | `settings.json` next to the program |
| Exported profiles | `exports` folder next to the program |

If the program is in a folder Windows will not let it write to — under
`Program Files`, say — the folders go to your own folder instead, under
`%APPDATA%\Keylight`. The Settings page shows you where they ended up.

Copying the program folder to another computer takes your profiles,
macros and settings with it.

---

## When something goes wrong

**"No keyboard is connected."** Plug the keyboard in and press "Check
again". The app looks for it every couple of seconds anyway.

**"Another program is using the keyboard."** Something else has it open
— the vendor's own program, most likely. Close that one. Keylight
cannot open the keyboard while another program is holding it.

**Nothing happens when I change the lighting.** The app says so if the
board did not take the change. Try a different effect.

**The keys I bind do not work.** The app has to be running, and "Let
the app change keys" has to be on. Some programs that run as
administrator cannot see the keys that a normal program binds.

**A macro does not play.** Some programs that run as administrator get
the keys before the app does.

**The window is too small.** The app needs about 1100 by 720 to show
everything. It can be made smaller, but some controls will be out of
sight until you make it bigger.

**The app will not start.** Open `keylight.log` next to the program.
The last line says what went wrong.

---

## What it is not

Keylight is a third-party program. It is not made by, and not endorsed
by, the company that makes the AK820 keyboard. Their name and their
marks belong to them, and they are used here only to say which keyboard
this program is for.

The keyboard's own protocol was worked out by reading the hardware and
by reading [OpenRGB](https://openrgb.org), which did the same job
first. No code was taken from the vendor's program.
