# How this app is put together

This is the design of the app as it is built. It is written from the code,
so it cannot drift away from it the way the last version of this file
did — that one described the app's very first design (dark only, an
amber accent, a 56px bar, 81 keys, eight API routes) and was never
updated after the app was rebuilt.

**The reference this app copies** is described in `docs/ui-reference.md`:
the ATK GEAR application. The numbers below are read off that reference
and out of `ui/tokens.css` and `ui/app.css`.

**The truth lives in the code.** Every token is in `ui/tokens.css`, every
component rule is in `ui/app.css`, and the page itself is
`ui/index.html`. This file explains how those fit together.

---

## The window

```
┌──────────────────────────────────────────────────────────────┐
│ top bar, white, 48px                                         │
├────────────┬─────────────────────────────────────────────────┤
│  sidebar   │   content, light grey, padding 24px              │
│  228px     │   two columns: the wide one, then a right rail  │
│  #f0f0f1   │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

- **Top bar** — 48px, white, a hairline underneath. The mark and the
  wordmark on the left, then the device tab, then the live readout of
  the effect and its colour, then refresh and the theme switch.
- **Sidebar** — 228px, `#f0f0f1`, full height, no border. A group
  label, the five sections, and the device's state at the foot.
- **Content** — `#f4f4f5`, 24px padding. The cards on it are white.

The app's own window is 1280x800 and will not go below 1100x720. The
Edge fallback, used when the webview cannot start, opens a normal
browser window instead, so the page has to survive a narrow one too.

## Colour

| What | Light | Dark |
|---|---|---|
| the page | `#f4f4f5` | `#17171a` |
| the sidebar | `#f0f0f1` | `#121214` |
| a card | `#ffffff` | `#212125` |
| a grey block inside a card | `#f1f1f2` | `#212125` |
| a track | `#eeeef0` | `#2c2c30` |
| a hairline | `#ebebec` | `#2f2f33` |
| text | `#17171a` | `#f0f0f0` |
| text, secondary | `#7a7a7a` | `#9a9aa0` |
| anything chosen | `#0a0a0a` | `#f5f5f7` |

**One accent, and it is the mark** — an orange bolt on a peach chip. It
is not used for selection: a chosen thing is black with white text.

## Type

Segoe UI Variable, which is on every Windows 11 machine, so the app
needs no web fonts and works offline.

| What | Size | Weight |
|---|---|---|
| the device name | 24px | 500 |
| the section title | 18px | 500 |
| a card title | 16px | 600 |
| a button, a nav item | 14px | 450–500 |
| a note under a title | 13px | 400 |
| the wordmark | 13px | 700 |

The sizes are named (`--text-device`, `--text-section`, `--text-title`,
`--text-body`, `--text-note`, `--text-label`, `--text-mark`) rather than
a numeric scale, so a rule says what it is for.

## Space, radius, movement

- Space: 4, 8, 12, 16, 24, 32 (`--space-1` … `--space-6`).
- Radius: 8 for rows and fields, 10 for icon chips, 12 for cards,
  16 for the largest panels.
- One shadow, `--shadow-1`, on the cards and the toast.
- Movement: 140ms for a quick change, 180ms for a slower one.
  `prefers-reduced-motion` cuts every duration to nothing.

## The page

One page, five sections, switched by the hash and by the sidebar. The
section that was last open is remembered, unless the user says not to.

| Section | What it holds |
|---|---|
| **Lighting** | the board, the colour picker, the list of effects, and the brightness, speed and direction |
| **Per-key** | the board to paint on, the colour to paint with, and the whole-board buttons |
| **Macros** | the recorded macros, and the keys that play them |
| **Profiles** | the lighting setups that are saved, and the three the board keeps itself |
| **Settings** | the app's own settings, what the keyboard takes, where the files are, and what the app is |

## The two columns

A section is a two-column workspace: the wide one on the left, a rail on
the right. The rail is 460px, or 400px when the window is narrower than
1320px — at which point the list of effects takes three columns instead
of one, so more of them are in sight without scrolling.

Below 1120px the workspace becomes a single column and the rail sits
underneath it in two columns. Below 620px the page is replaced by a
message saying the window is too small.

## The parts

- **A card** is white with a 12px radius and a hairline, never a
  shadow. It has a head (an icon, a title, a note and sometimes a
  value) and a body. When a card is shorter than its contents, the body
  scrolls — nothing is ever cut off and made unreachable.
- **A list** is a column of rows. A row is 46px or so, with a name, a
  note under it, and sometimes a button on the right.
- **A segmented track** is a `#eeeef0` bar about 40px tall. The chosen
  one is a black rounded rectangle with white text.
- **A switch** is a 44x24 pill: a grey track with a white knob, or a
  black track with the knob on the other side.
- **A button** is either the black one (the thing you are meant to do)
  or a light grey one with a hairline. A destructive one is red.
- **The board** is drawn by `ui/board.js` as an SVG, from the key
  geometry in `ui/assets/ak820-caps.json`: the case, the eighty-two
  keycaps, what is written on them, and the knob. It is not a picture
  of the board — it is a drawing of it, so the keycaps are in the right
  places and the colour on a key is the colour of that key. The key
  hitboxes are laid over it from the same numbers, so a click lands on
  the key it looks like it lands on.
- **The colour picker** is a saturation and brightness square, a hue
  strip and a hex field, with a random button and a button to pin the
  colour. It works with the mouse and from the keyboard.

## Movement on the board

The board's effect is a movement, and the preview shows it. A travelling
wave crosses the keycaps for the effects that move across the board, a
pulse for the ones that breathe, and a slow change of hue for the two
that cycle through the colours. The speed control changes how fast it
moves, because the board's speed control does.

## What is always true

- A skip link is the first thing in the page.
- Everything that can be clicked can be reached with the keyboard, and
  the focus ring is 2px of black with a 2px gap.
- The connection to the keyboard is announced politely, not shouted.
- Nothing is ever cut off: a card that is too short for its contents
  scrolls them.
- The app never writes to the registry, never reaches the internet, and
  never needs an installer.
