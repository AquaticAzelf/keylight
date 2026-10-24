# The look we are copying: ATK GEAR

The owner owns a VXE R1 NK mouse and drives it with ATK GEAR. They said the
design is "absolutely magnificent" and asked for the whole app to be rebuilt
in that look — its elements, its dimensions, everything.

The reference screenshots are in `C:\Users\Azelf\Documents\opencode`:
`Screenshot 2026-10-20 143200.png` (Configuration Manager), `143218.png`
(Parameter Settings), `143236.png` (Macro Settings), `143310.png` (device
home), and the two closest-ups `144803.png` (the sidebar) and `144835.png`
(the parameter page).

This file is what the front end is measured against. Everything below was
read off those screenshots.

## The shape of the window

```
┌──────────────────────────────────────────────────────────────┐
│ top bar, white, 48px                                         │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│  sidebar   │   content, light grey, padding 24px              │
│  228px     │   two columns: the wide one, then a right rail  │
│  #f0f0f1   │                                                 │
│            │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

- **Top bar**: 48px, white, a 1px hairline underneath. On the left an
  orange lightning mark on a peach chip, the wordmark, a divider, then a
  device tab (a grey rounded pill with the device name and a close X). On the
  right a row of 18px line icons, then a user chip, then a gear.
- **Sidebar**: 228px, `#f0f0f1`, full height, no border. It runs to the
  bottom of the window; the top bar does not cover it.
- **Content**: **light grey**, 24px padding, two columns — the wide one on
  the left and a narrower rail on the right. The cards on it are white.

## Colour

| What | Value |
|---|---|
| canvas (the page the cards sit on) | `#f4f4f5` |
| sidebar | `#f0f0f1` |
| card | `#ffffff` |
| grey block inside a card that holds a setting | `#f1f1f2` |
| a row / the panel a list sits in | `#f4f4f5`, tracks `#eeeef0` |
| hairline | `#ebebec` |
| strong hairline | `#dcdcdf` |
| text | `#17171a` |
| text, secondary | `#7a7a7a` |
| text, faint | `#a5a5a5` |
| primary button, selected segment, toggle-on | `#0a0a0a` |
| accent (the logo only) | `#f97316`, on a `#ffe6d8` chip |

The accent is used **once**, in the mark. Everything else is black, white
and grey. A selected item is black with white text, never orange.

## Type

A clean grotesque throughout. We use Segoe UI Variable, which is on every
Windows 11 machine, with the display optical size for the big headings.

| What | Size | Weight |
|---|---|---|
| device name on the home card | 24px | 500 |
| section title in the content | 18px | 500 |
| card title | 16px | 600 |
| device tab, nav item, button | 14px | 450–500 |
| description under a card title | 13px | 400 |
| small label over a group | 13px | 400, `--text-faint` |
| wordmark | 13px | 700 |

## Radius and space

- cards and panels: **12px**
- buttons, rows, tracks: **8px**
- the square icon chips: **10px**
- switches: a full pill
- page padding 24px, card padding 16px, gap between cards 16px,
  gap between a title and its description 4px.

## The parts, in the order they appear

### Sidebar
1. **Device block** — a white card (12px radius) at the top with the
   device's battery or link state on the first line, the device name on the
   second, and a chevron on the right.
2. **A group label** in `--text-faint` 13px, e.g. "Mouse Configuration".
3. **Nav items** — a 16px line icon then the label, 14px. The item that is
   open is a **grey pill** with a **black bar down its left edge**, its text
   dark; the rest are plain `--text-dim` on the grey.
4. At the very bottom, a small line and a "Bug Feedback" item.

### Content, a page of settings (Parameter Settings)
- The page is grey; each **card** is white with a 12px radius and a hairline.
- A card holds **setting rows**. A wide control has its title and
  description at the top of the card and the control below it. A narrow
  control (a switch) sits in a **grey block** with the title and description
  on the left and the control on the right, vertically centred.

The controls:

- **Switch** — 44×24, a pill. Off: a `#d5d5d7` track with a white knob at
  the left. On: a black track with a white knob at the right.
- **Segmented track** — a `#eeeef0` rounded (8px) bar about 40px tall, the
  options spread evenly across it, the text in `--text-dim`. **The chosen one
  is a black rounded rectangle (6px) with white text.** When the options are
  a scale (0ms, 1ms, 2ms, 4ms, 8ms…) the bar is full width.
- **A slider** is the same bar with the chosen part filled black and the
  value in white inside the black part.
- A row of **separate buttons**: the first one black, the rest light grey
  `#f1f1f2` with a hairline.

### Content, a page of a list (Configuration Manager / Macro Settings)
- A title on the left and **buttons on the right**: the secondary ones are
  light grey `#f1f1f2` with a hairline, the primary one is **black**.
- A **grey panel** (`#f1f1f2`, 12px radius) holding a list of **rows**: a
  `#f4f4f5` rounded (8px) bar about 46px tall with a name on the left and
  icons on the right. The chosen row is **white with a black 1px border**.
- A row may start with a **square icon chip**: a 40px `#eeeef0` square with
  a 10px radius and a line icon in it.
- **Empty states** sit on a faint square grid and hold a rounded icon
  square, a line of text, and a black button.

## The rules we take from it

1. The app is **light**. A grey page, a grey sidebar, white cards on them.
2. **One accent**, and it is the mark. Selection is black.
3. Everything is a **card with a hairline border**, never a shadow.
4. The board is the hero, on white, with its light showing.
5. Type is set in Segoe UI Variable at real weights, and the size steps are
   13 / 14 / 16 / 18 / 24.
