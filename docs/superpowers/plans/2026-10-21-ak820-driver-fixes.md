# Ak820Driver — fix list and missing features

Written 2026-10-21. Ground truth is git history plus live inspection, **not** the
checkboxes in `2026-10-20-ak820-driver.md` (the previous session was corrupted and
never ticked them).

## Progress

| Phase | State | Commit |
|---|---|---|
| A — safety net | done | `749331a` |
| B — the capture | ready; the owner runs it | `a6cb377` (the tooling) |
| C — backend correctness | done | `a6cb377` |
| D — front-end correctness | done | `665e710` |
| F — the Tier 1 features | done | `c3876bd` |
| H — the rebrand to Keylight | done | `46f3dc2` |
| E — dead code and documents | done | `ea4b247` |
| G — USB report rate, Windows Lock, Exchange Key | done — read out of the vendor's own binary | |
| I — packaging and the user guide | done | `88ad60b`, `43b8d14` |
| J — the final check | done | `43b8d14` |
| B35 — the chain slots | closed by the paint test: the vendor numbers were wrong, the grid held except the letter row and Del, now observed | |

**103 tests pass.** The suite was 57 before this work; the rest are a
regression test for every bug that was fixed, plus tests for the new
features.

### What the final check found

The check walks all five sections at 1280x768 and at 1920x1080, looks at
every control, and asks whether anything is cut off by a card that cannot
scroll to it, then clicks everything that is safe to click.

- **Every control is reachable and clickable at both sizes.** No console
  errors, no page errors.
- **All 21 effects move in the preview** — 17 animate, and the four that
  do not move (Static, Custom, Audio wave, Capture colour) stay still.
- **The remap layer works end to end** on the real keyboard: the binding
  sticks, switching the layer off and on keeps it, and the key named "5"
  binds the digit-five key.
- **The packed program works**: `dist/Keylight.exe` (13.3 MB, one file)
  serves the page, every API route answers, and every asset is there.
  `dist/Keylight.zip` holds it and the guide.
- One more CSS bug came out of it: the rail's first-card rule was more
  specific than the colour card's own, so the colour card was stretched to
  fill the rail and cut its palette off. Fixed.
- **Two more, found by the 2026-10-24 re-check.** The speed track offered
  0..4 while the board keeps six speeds (OpenRGB's own header names
  0x00 fastest .. 0x05 slowest; the board stores all six) - the slowest
  speed was unreachable and a board holding 5 showed no choice at all.
  And the keyboard's own settings (report rate, Windows Lock, Exchange)
  were only read when the app opened, so plugging the board in later left
  the Settings page saying it was not connected. Both fixed.

### What the review turned up that the code review alone had missed

- **The keyboard hook had never worked.** `ak820/remap.py` had no declared
  ctypes signatures, so ctypes treated every result as a 32-bit int.
  `GetModuleHandleW` returns a 64-bit module handle; it came back chopped in
  half, `SetWindowsHookExW` refused the module that did not exist (error
  126), and `install_hook()` returned False every time. Reading the code
  did not show this — running it did.
- **Two CSS conflicts.** `.rail > .card:first-child .card-body` (0,3,0) beat
  `.colour-card .card-body` (0,2,0), so the per-key colour card was forced
  into a column and its palette was pushed off the bottom of the card. And
  the board picture sat in a grey panel, so the space above and below it
  read as a mistake rather than as room.
- **The card that was cut off was cut off by a floor.** The 150px minimum
  under `.list` was bigger than the space the card had, so the list was
  taller than the card and the card cut it off instead of scrolling it.

### Ruled out, so nobody spends time on them

The F11/F12 keys are in the table. A profile called "rename" can be
reached. The route split before `unquote` cannot be reached. The 126 and
128 colour slots differ, but no key uses the last two and the vendor's own
driver for this board drives 126, so the app follows the vendor.

### CLOSED — the chain slots in the per-key editor (B35), settled by the owner's paint test

**The answer, 2026-10-24.** The owner ran the paint test over three rounds
(about two minutes of looking at the keyboard). The verdict:

- **The vendor table is wrong for this board.** All four probe slots lit
  the *old* grid's keys (slot 105 = Backspace, 84 = the period key,
  57 = the `7`, 96 = F12), none of the vendor's (left Ctrl / left Shift /
  End / Up). Whatever `keyboarddevice.xml`'s `userdata="light_N"` numbers,
  it is not this board's LED chain.
- **The old grid was right where it mattered** — the F row, the number
  row, Backspace, the right-hand cluster (Home, PgDn, End, the arrows and
  the right Shift all lit exactly where the grid said) — **except two
  places**, found and fixed by observation:
  - the whole letter row sat one slot late: left Shift 20→4, Z…M shift
    back by one, `,` `.` `/` land on 76/84/92, and the `/` key's old
    slot 4 was simply wrong (slot 4 is the left Shift); slots 12 and 100
    light nothing (unused chain positions);
  - Del is on **114**, not 104.

`ui/assets/ak820-caps.json` now holds the observed slots *and* keeps the
vendor-derived letter-row **labels** (the paint test says nothing against
those; the 94px key really is the Shift). Twenty-one direct observations
are pinned in the commit message and every one holds in the file.

**What is still an assumption** (never observed, unchanged from the grid,
and what the app has shipped all along): PgUp, `\\`, Enter, the right
Ctrl, and the bottom row (left Ctrl, Win, Alt, Space, Fn). The full
seven-round sweep (`tools/paint_slots.py --list`, `--round N`) is there
if ever a slot-by-slot record is wanted.

**What is not the answer.** Three things look like they would settle it
and do not:

- The board's own table at config `0xC0` is a **generic full-size
  template** (it has Num Lock, F13-F17 and a number pad, none of which
  this board has). It is the *keycode* map, not the LED chain.
- The vendor's `DefaultData/Keyboard.json` `KeyList` is 126 entries
  long, but it is numbered in the vendor's own order, not the chain's.
- ~~The vendor's `keyboarddevice.xml` `pos` values do not line up with our
  picture.~~ **Re-checked 2026-10-23: it looked like the answer — and the
  paint test disproved it the next day.** It names `key_0` ... `key_125`,
  each with `userdata="light_N"` and a `tooltip`, and its 82 visible keys
  matched ours position for position — which is why its **labels** were
  worth taking. But its **slot numbers** are not this board's chain: every
  probe lit the grid's key, not the vendor's. The file numbers some other
  index (the vendor app's own key order, most likely), not the LED chain
  this board walks.

**The test that settles it (about 30 seconds).** `tools/paint_slots.py` takes
raw slot numbers and lights each one in a different colour, everything else
dark. Four slots tell the two orders apart at a glance: under the vendor order
they are **left Ctrl / left Shift / End / Up**, under the order we ship today
they are **Backspace / the `.` key / `7` / F12**.

```
python tools/paint_slots.py 105 84 57 96    # white, red, green, blue
python tools/paint_slots.py --undo          # put the board back
```

Say which key is white, red, green and blue, and the chain is known. The full
seven-round sweep (`--list`, `--round N`) is still there when a slot-by-slot
record is wanted.

**A second defect, found 2026-10-23.** `ui/assets/ak820-caps.json` *draws*
row 4 wrongly too: its leftmost key is 94px wide (the left Shift's shape) but
is *labelled* `Z`, and the letter labels are shifted by one, leaving two keys
both labelled `Shift`. The geometry is a real 75% shape; only the labels are
wrong. The vendor table fixes that as a side effect.

**Why it matters.** The per-key editor paints the chain slot the user
clicks. If the slot is wrong, the wrong key lights up. Nothing in the
app can tell the difference — it is one photograph per round.

**Applied 2026-10-24, on the owner's instruction** ("apply now, then I'll
confirm"), **then corrected the same day when the paint test disproved the
vendor numbers.** The vendor slot values were live for a few hours; the
correction put the grid's numbers back everywhere the grid was right and
fixed the two places the rounds showed it was wrong (the letter row, Del).
The 11 letter-row **labels** from the vendor table survive — the labels
were a real fix and the paint test does not touch them.
`tools/build_device_json.py` is **superseded**: running it would clobber
the file with the old computed grid, letter row and all.

## Decisions taken 2026-10-21

| Question | Answer |
|---|---|
| Legal / branding | **Full rebrand.** The app stops using the AJAZZ name, the AJAZZ logo and the vendor's keyboard artwork. It becomes an independent configurator. |
| The app's new name | **Keylight.** One string to change if a different name is preferred. |
| USB report rate / Windows Lock / Exchange Key | **Yes, do the capture.** The owner will run the official driver and change the settings while the write traffic is hooked. The byte that moves is the offset. |
| Scope of this pass | **Everything in one go** — all 13 steps, through to a packaged `.exe` and a user guide. |

### What the rebrand means concretely

- **Name.** "Keylight" replaces "AJAZZ AK820" everywhere the app talks about
  *itself* — window title, page title, wordmark, the top bar, the About note.
  "AK820" survives only where it names the **hardware the user has plugged in**
  ("works with the AK820 keyboard"), which is what a model name is for.
- **The mark.** `ui/assets/ajazz-mark.png` (the vendor's logo) is deleted and
  replaced with `ui/assets/keylight-mark.svg`: an orange bolt on a peach chip,
  drawn for this app. The `--accent` and `--accent-chip` tokens were added, so
  the "one accent, and it is the mark" rule is now true.
- **The board artwork.** `ui/assets/ak820-board.png` (the vendor's picture of
  the board) is deleted. The board is now **drawn** by `ui/board.js` from the
  key geometry in `ui/assets/ak820-caps.json` (82 keys with x/y/w/h): the
  case, the keycaps and the legends. This kills two birds: the vendor's file
  is gone, and the key hitboxes become correct by construction instead of by
  reverse-engineering a photo. It also fixed the colours — the old preview
  could only tint a picture, the new one puts the real colour on each key, and
  the legends are readable.
  - The light that crosses the board and the shading on the caps are now
    SVG layers clipped to the keycaps, so the case stays still.
  - The animations were re-pointed: the travelling wave animates the SVG
    band with `transform`, and the breathing and colour-cycling effects
    animate the keycaps themselves.
  - The two tools that imported the vendor's artwork (`tools/build_logo.py`,
    which downloaded the AJAZZ logo from the web, and `tools/build_board_art.py`)
    are deleted. `tools/find_caps.py` stays, and its note now says the numbers
    are the record.
- **Paperwork.** `LICENSE` (MIT), `README.md`, `NOTICE` (which credits
  OpenRGB for the protocol and explains that no code was copied from it), and
  an About note in the Settings section saying what the app is, that it is not
  affiliated with AJAZZ, who makes the keyboard, and the licence.

---

## Where we left off

Everything below is **verified**, not guessed. Nothing in the repo has been modified
yet — this session was read-only apart from this file.

Verified working:
- `pytest -q` from `ak820-driver/` -> **57 passed in 4.12s**.
- Live app against real hardware: `/api/status` -> `connected: true`; `/api/modes` ->
  21 modes, all `supported: true`; `/api/lighting` -> `{mode: 8, brightness: 4,
  speed: 3, direction: 0, color: [0,153,255]}`; `/api/settings` -> 5 app settings.
- Browser page: **0 console events, 0 page errors**, both API calls 200, 1513 DOM
  nodes, 175 buttons (82 per-key LEDs), board PNG loads as an `<img>` (no canvas).
- Our 21 lighting mode IDs match the official driver's visible set **exactly**
  (`app/DefaultData/default_light.json`: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,20,29,30).
  **No lighting effect is missing and no ID is wrong.** Only the English names differ.

Sub-agent results (**recovered by resuming both sessions**):
- **Backend hunt (agent `ses_ea5d2d324ffel2xLA6z5X4nhp3`) — DONE.** 27 confirmed
  bugs, most reproduced at runtime, not inferred. It also read `ui/app.js`,
  `ui/app.css`, `ui/board.js`, `ui/picker.js` and `ui/index.html`, so the front end
  is covered too. Full list in **Part 1b**.
- **Front-end hunt (agent `ses_ea5d2d310ffeNA7JIE4NdKArr5`) — NOT DONE.** It was
  interrupted after reading only `ui/index.html` (which it found clean: no duplicate
  DOM ids, correct script order, the inline theme bootstrap cannot throw, the skip
  link target exists). It left four **open leads, not findings**: two picker
  instances (`#picker`, `#perkey-picker`), three board instances (`#board`,
  `#perkey-board`, `#settings-board`), the nav order differs from the DOM order
  (`#section-profiles` before `#section-macros`), and `#readout` ships with the
  `hidden` attribute so `app.js` must remove it. **All four still need checking
  against `app.js`.**
- A **previous** session left a plan at `.opencode/plans/2026-10-20-ak820-finish.md`.
  Its Phase 1 rule is: bug-hunt Profiles / Settings / Macros separately, and **add a
  test for every bug found**. Honour that rule below.
- The hardware capture of the **official driver** (`.scratch/capture-official-full.jsonl`,
  19 523 WriteFile reports) has been decoded. See Part 3 — it settles what we know
  about the config block, and it is the tool we need for the gated features.

One thing ruled out: `git status` shows 13 `.opencode/skills/make-interfaces-feel-better/`
files as modified. They are **not** modified — `git hash-object` on the working tree
equals the index blob and the HEAD blob for every one. It is a stale git stat cache
(`git diff-files --raw` shows a zero destination hash). No sub-agent touched the repo.

---

## Part 0 — safety net (do this before anything else)

| # | Action | Why |
|---|---|---|
| 0.1 | Commit every uncommitted change | There is **a lot** of unsaved work: 5 new Python modules (`ak820/macros.py`, `profiles.py`, `remap.py`, `settings.py`, `store.py`), `ui/board.js`, `ui/picker.js`, `ui/assets/ak820-caps.json`, plus edits to `api.py`, `protocol/lighting.py`, `protocol/session.py`, `devices/ak820_wired.json`, 4 test files, 4 tool scripts and 5 UI files. If the disk died today it is gone. |
| 0.2 | Delete the 5 stale scratch files tracked at the repo root: `css_now.css`, `out_app.css`, `out_app.js`, `out_index.html`, `out_tokens.css` | Older snapshots of the UI (1 400+ diff lines against the live ones). Not in `.gitignore` (it only catches `out*.txt`). Also add `out_*.css`, `out_*.js`, `out_*.html`, `css_now.css` to `.gitignore`. |
| 0.3 | Rewrite or delete `ak820-driver/ui/DESIGN.md` | It is a fossil of the **first** design (dark-only, amber accent, 56px bar, 240px sidebar, 774x306 plate, 81 keys, numeric type scale, 8 API routes) and it says "everything here is what the code does". The code now follows `docs/ui-reference.md` (ATK GEAR: 48px bar, 228px sidebar, light+dark, black selection, 82 keys, 20+ routes). It actively misleads. |
| 0.4 | Decide what to do with `.scratch/`, `captures/`, `_ghidra_proj/`, and the ~20 one-off probe scripts in `tools/` | `.scratch/capture-official-full.jsonl` is 5.4 MB and is the only source for Part 3. The `tools/` probes are scratch. |

---

## Part 1 — confirmed bugs

### B1. The board preview does not animate for 15 of 21 effects  *(the big one)*
`ui/app.css:792` defines a `.board-wave` layer with three animation families:
`board-travel` (wave, ripples, traverse, roll, wave-bar, cloud, stars — app.css:824-833),
`board-pulse` (breath, speed, rain, fireworks, cartoon, scan, surmount, reaction —
app.css:840-855) and `board-hue` on `.board-light` (spectrum, vortex — app.css:835-838).
**`ui/board.js:17-22` only creates `.board-art`, `.board-light`, `.board-paint` and
`.board-keys`. There is no `.board-wave` element anywhere.** So 15 modes never animate
and only spectrum and vortex do (and only while `.board-tint` is on, because
`.board-light` is `display: none` otherwise).

- **Fix:** create the `.board-wave` layer in `board.js`. The CSS already exists.
- **Also fix:** the comment at `ui/app.js:38` ("The preview moves the way the board
  does") and its twin at `ui/app.css:821` are false until this is done.
- **Check:** pick each of the 21 modes in the app and confirm the preview moves.

### B2. The "Never" poll option still polls every 2 seconds
`ui/app.js:1461` -> `}, Math.max(500, (state.checkInterval || 2) * 1000));`.
`state.checkInterval` is the **string** `"0"` for Never, and `"0" || 2` is `"0"`
(a non-empty string is truthy), so `("0" || 2) * 1000` is `0` -> `Math.max(500, 0)`
-> 500 ms, and `"0" || 2` is *not* what decides it. Either way the intent is broken:
Never must not schedule a poll at all.
- **Fix:** parse it as a number, and when it is 0 do not arm the timer.
- **Check:** set it to Never, watch the network panel, expect zero requests.

### B3. Cards clip their content instead of scrolling  *(the screenshot bug)*
`ui/app.css:548` gives `.card` `overflow: hidden`. `ui/app.css:500-504` lets
`.rail > .card:first-child` shrink (`flex: 1 1 auto; min-height: 0`) below its content
height when the window is short, and `.card { overflow: hidden }` then **cuts the
overflow off** instead of scrolling it. `ui/app.css:896-902` gives `.list`
`flex: 1; min-height: 150px; overflow-y: auto` — but the 150px floor is bigger than
the space the card actually has, so the list is clipped by the card.

This is what breaks the default 1280x768 window:
- **Lighting** — the Effect card shows only ~3 of 21 effects, cut off mid-list.
- **Macros** — the right-hand "Keys" card is cut mid-control; the Key dropdown, the
  Macro dropdown and the Add button are unreachable and overlap the card below.
- **Settings** — the "This app" card shows only 3 of 5 rows; "Ask before deleting",
  "Show what the app is doing" and "Reset the settings" are unreachable. The
  "The keyboard" card loses its "Reset the lighting" button.
- **Profiles** — the "Saved profiles" card is mostly void; the path box wraps mid-word.
- **Per-key** — the board preview is letterboxed with dead bands above and below.

- **Fix:** let the card body scroll instead of clipping. Keep the card frame, put
  `overflow-y: auto` on the scrollable region, and drop the 150px floor that
  over-subscribes the space. Then re-check the 1280x768 window for all five sections.
- **Also:** `ui/app.css:32, 301, 1225, 1576` also set `overflow: hidden` — check each
  is intentional.

### B4. `--radius-sm` is used but never defined
`ui/app.css:1250` uses `border-radius: var(--radius-sm);` but `ui/tokens.css` only
defines `--radius-1..4`. Invalid at computed-value time, so those path boxes get no
rounding at all.
- **Fix:** use `--radius-1` (or define `--radius-sm` in tokens.css — pick one and be
  consistent).

### B5. The theme has two sources of truth
The theme lives in `localStorage['ak820-theme']` (read by the inline script in
`ui/index.html`) **and** in `settings.json` under `theme`. "Reset the settings"
resets `settings.json` but not localStorage, so **the theme does not actually reset**.
- **Fix:** pick one owner. Cheapest correct answer: `settings.json` is the source of
  truth; the inline script keeps only the first-paint flash guard, and "Reset"
  clears localStorage too.

### B6. The device line never changes
`ui/app.js:1244` and `ui/app.js:1247` both write
`dom.deviceState.textContent = 'AJAZZ AK820 · wired';` — the connected and the
disconnected branch are identical, so the line never reflects reality.
- **Fix:** show the real state (connected / not found / busy).

### B7. The per-key colour buffer can be sent short
`sendKeyColors()` loops to `state.keyColors.length`. If `GET /api/keys/colors` failed
(503, e.g. another app had the board), the array is empty and **only the keys you
painted get sent** — the rest of the board keeps whatever it had. The code comment
claims un-sent slots go out as black.
- **Fix:** always send the full 126-slot buffer; on a failed read, send black for the
  unknown slots (or refuse the write and say so). Do not silently send a partial
  buffer.

### B8. The section-open animation only works on 2 of 5 sections
`enterSection()` picks the panel as `lighting -> perKey -> placeholder`. For
Profiles, Settings and Macros both real panels are hidden, so it animates the
**hidden placeholder**, which has no `.card` children — nothing moves.
- **Fix:** animate the panel that is actually being shown. Then delete the now-unused
  `#section-placeholder` panel and its CSS.

### B9. The Direction control highlights "Left" for effects that do not move
`ui/app.js:28` defines `NO_DIRECTION = {0x05, 0x06, 0x14, 0x1D, 0x1E}` (Breath,
Static, Custom, Audio wave, Capture) and the UI says "This effect does not move" —
but "Left" is still drawn as selected.
- **Fix:** disable or deselect the direction control for those modes.

---

## Part 1b — backend bugs found by the sub-agent (27, all reproduced)

From the resumed backend hunt. Most were reproduced by running the code, so these are
facts, not suspicions. **Every one of these needs a regression test in
`tests/test_api.py`** (per the previous session's plan rule). Ordered by damage.

### The remap feature does not work at all

**B10. Installing the hook wipes the key→macro mapping.**
`ak820/remap.py:154-162` — `install_hook(mapping=None)` starts with `_mapping.clear()`
and only re-populates if a `mapping` argument is passed. `ak820/api.py:605-606` calls
`remap.set_mapping(pairs)` **then** `remap.install_hook()` with no argument, so the
mapping is set and immediately erased.
Reproduced: `POST /api/remap {"active": true, "mapping": {"A": "MyMacro"}}` ->
`{"ok": true, "active": true}`, then `GET /api/remap` -> `"mapping": {}`.
**No key is ever bound.** Pressing the chosen key does nothing and the Macros page's
"Keys" list stays empty.

**B11. Turning the layer off and on loses every binding.**
`ak820/remap.py:195` — `uninstall_hook` also calls `_mapping.clear()`, and the mapping
is never persisted, so a toggle loses it. The intent is that switching the layer off
puts the keys back but keeps the bindings.

**B12. The key-name table is wrong, so wrong keys get bound.**
`ak820/remap.py:41-42` overwrites F11 and F12 (the literal already had them at
0x7A/0x7B), so only F1-F10 survive. `ak820/remap.py:43-46` then puts digits 0-9 and
letters A-Z into the *same* name→code table as the special keys, so the digit "5"
maps to virtual-key 5 (which is not a key) instead of to the 5 key.
Reproduced: `{'5':'MacroA','A':'MacroB','F5':'MacroC','Space':'MacroD'}` ->
`{5:…, 65:…, 116:…, 32:…}`, and the label comes back as `"Key 5"`.

**B13. A digit key name is bound to the wrong key.**
`ak820/api.py:602-603` — `remap.key_name(int(key))` is applied to a name that may
already be a digit string, turning `"5"` into `key_name(5)` -> `"Key 5"` -> code 5.

**B25. Removing a binding can remove the wrong one.**
`ui/app.js:1019-1047` + `ak820/api.py:578-590` — the front end's list is keyed by the
*name* the back end returns, the back end keys by *code*. With B12 the name is not a
stable identity for a key.

**B26. The "Add" button dies with an uncaught TypeError.**
`ui/app.js:952, 963` — `state.remapMapping` and `state.remapKeyNames` are never
initialised. If `addRemap()` runs before `/api/remap` has ever succeeded (Macros page
opened while that route was failing), `Object.assign({}, state.remapMapping)` throws
`TypeError: Cannot convert undefined or null to object` and the user gets no feedback.

### The lighting write path can reject a value it just read

**B14. The read accepts a speed and direction the write refuses.**
`ak820/api.py:219` validates `speed > 5` and `direction > 3`, but
`ak820/protocol/lighting.py:15,17` narrowed the *write* range to speed 0-4 and
direction 0-1. Reproduced: `GET /api/lighting` -> `speed 5`, then
`POST /api/lighting` -> `ApiError: speed must be 0..4, got 5`.
**Every lighting change fails with a 400** until the user drags the speed slider back
into range by hand.

**B15. Mode 0x00 ("Off") is rejected on read.**
`MODE_NAMES` no longer contains 0x00, so a board sitting in "off" mode fails the
`mode not in MODE_NAMES` check, `_read_lighting` returns `None`, and the app keeps
showing stale cached state instead of reality.

### Writes that go past the end of the board's buffers

**B16. An out-of-range LED index writes 15 KB into a 378-byte buffer.**
`ak820/api.py:301` validates `led` as `0..0xFFFF`, then extends the colour buffer to
`(led+1)*3` bytes and writes **all** of it.
Reproduced: `POST /api/keys/colors {"led": 5000, "color": [1,2,3]}` -> `ok: true`,
`bytes written to board: 15003`. The bulk route at `ak820/api.py:326` *does* cap at
`COLOR_SLOTS`; the single-key path is missing the same check.

**B17. "Reset the lighting" wipes all three board profiles and jumps to profile 1.**
`ak820/api.py:709-711` — `reset_lighting` calls `set_lighting` with the default
`profile=0, all_profiles=True` and writes `OFFSET_CURRENT_PROFILE = 0`.
Reproduced: the active profile byte went 2 -> 0, and profile 0 and profile 1 blocks
were both overwritten with the defaults. The per-profile work at
`ak820/api.py:230-237` and `ak820/protocol/session.py:66-73` exists precisely so the
other two setups are left alone; the reset button throws that away.

**B18. The reset writes white; the app's own default is red.**
`ak820/api.py:710-711` uses `[255,255,255]`; `ak820/api.py:117` uses `[255,0,0]`.

**B27. The per-key buffer is 126 slots but the board's keymap says 128.**
`ak820/api.py:44-46` hard-codes `COLOR_SLOTS = 126` / `COLOR_BUFFER_BYTES = 378`, but
`ak820/protocol/keymap.py:16` says `SLOT_COUNT = 128`. The two highest chain slots are
never read or written. **OPEN: which is right? Not decidable from the code alone —
needs a real board read.**

### Names that collide and lose data

**B19. Two macro names silently overwrite each other.**
`ak820/profiles.py:70-86` rejects `\ / : * ? " < > |` in profile names, but
`ak820/macros.py:50-56` only checks empty and length, and `store.safe_name`
(`ak820/store.py:70-74`) silently replaces illegal characters with `_`.
Reproduced: macro `Late/Shift` then macro `Late_Shift` -> one file, and the first
macro is lost without ever being shown.

**B20. `safe_name` maps several different names onto one file.**
`ak820/store.py:70-74` — `..` maps to `profile`, which collides with a profile
literally named `profile`.

**B21 / B31. A profile or macro named "rename" cannot be used.**
`ak820/api.py:779-802` — `_named_route` matches `parts[2] == "rename"` (profiles) and
`name == "rename"` (macros) *before* dispatching, so `GET /api/profiles/rename` goes
to the rename handler instead of applying the profile.

**B29. A short colour read saves a profile that can never be applied.**
`ak820/api.py:426-428` stores 126 triples from 378 bytes, but `read_custom_colors`
(`ak820/protocol/session.py:136-138`) breaks out of the loop on a `None` reply. A
short read stores short tuples, and `apply_profile` (`ak820/api.py:462-468`) then
raises `ApiError: color must be three numbers`. A profile that saved cleanly cannot
be applied later.

### The API breaking its own promise

**B22. A read-only install folder kills the API with a non-JSON 500.**
`ak820/settings.py:63-68` writes `settings.json` straight into `app_folder()` with no
writability probe and no `%APPDATA%` fallback — even though `store.data_folder`
(`ak820/store.py:28-51`) has one. `Api.handle` (`ak820/api.py:772-777`) catches only
`ApiError`, `HidError` and `ValueError`, so `FileNotFoundError` escapes.
Reproduced: `handle raised FileNotFoundError [WinError 3]`.
**This breaks the promise that every route answers JSON, including the failures.**

### Smaller but real

| # | Where | What |
|---|---|---|
| B23 | `ak820/api.py:695-700` + `ui/app.js:818-838` | "Reset the settings" re-reads the file but never calls `setTheme`, so the app keeps the old theme until the next page load. |
| B24 | `ui/app.js:828` + `ui/app.js:1457-1461` | A poll-interval change is read only when the next timer is armed, so it takes effect only after the current (up to 10 s) wait. |
| B28 | `ui/app.js:651-660` | "Invert" builds `[color[2], color[1], color[0]]` — a channel **rotation**. True inversion is `255 - channel`. Red `[255,0,0]` becomes blue `[0,0,255]` instead of cyan `[0,255,255]`. |
| B30 | `ak820/api.py:338-357` | `_write_colors` mutates the shared `self._lighting` dict in place while `apply_lighting`/`apply_profile` replace it, so the cache is not a reliable snapshot. |
| B32 | `ak820/api.py:543-556` | Imports `key_name` from `remap` and never uses it. |
| B32 | `ak820/api.py:384-390` | `Ak820Service.settings()` returns `{}` and is never called — dead code that invites the wrong route being wired up later. |
| B32 | `ak820/settings.py:87-95` | Says "The keyboard does not take a setting called x" when in fact the app simply does not implement it. Wrong-worded error on a trust-boundary path. |
| B32 | `ak820/macros.py:114-125` | `describe_macro` shows only the first 8 down-events and appends "…" based on the wrong count. |
| B33 | `ak820/api.py:781-794` | **Latent.** The route is split on "/" *before* `unquote`, so a future name containing "/" would 404 instead of resolving. Unreachable today. |
| **B34** | `ak820/remap.py:75-81` | **The keyboard hook never went in at all.** Found by running it, not by reading it. The `ctypes` calls had no declared signatures, so ctypes assumed every result was a 32-bit int. `GetModuleHandleW` returns a 64-bit module handle, so it came back chopped in half, `SetWindowsHookExW` was handed a module that does not exist and refused it with error 126 ("the specified module could not be found"), and `install_hook()` returned False every time. The whole key-to-macro feature was dead because of it. **Fixed** by declaring the signatures; `install_hook` now returns True. |

### Ruled out — looked at, and not a bug

The review reported these; checking them against the code showed they are not
real, so no fix and no test:

| Reported | Why it is not a bug |
|---|---|
| "F11 and F12 are lost from the key table" | They are there. `KEY_NAMES` has 70 names and `KEY_LABELS` 70 labels, no duplicate codes, and `key_name(0x7A)` is `"F11"`. The `for _index in range(10)` loop only touches F1-F10, and it writes the same values the literal already had. |
| "A profile or macro called `rename` cannot be reached" | It can. The rename route takes the profile's name from the **body**, so `GET /api/profiles/rename` applies the profile called "rename" and `POST /api/profiles/rename` renames whichever profile the body names. There is no collision. A test now proves it. |
| "The route is split on `/` before `unquote`" | True, but a name cannot hold a `/` — it is refused when it is saved — so no name can reach that path. Harmless today. |
| "The device card CSS is dead" | True, and it is being removed in the dead-code sweep (2.5). Not a bug. |

### Checked and found CLEAN by the backend hunt
`ak820/api.py` route table and dispatch (every route is exercised by
`tests/test_api.py:237-260`, and `test_the_test_walks_every_route_the_api_has`
enforces the list stays complete); 404/405 split; profile lifecycle end to end
(save / apply / rename / delete / the board's own three profiles); the
foreign-keyboard refusal (`ak820/profiles.py:95-99`); per-profile write isolation
(the index byte is written **last**); colour and int validation; `ak820/hid/windows.py`
(ctypes bindings, OVERLAPPED layout, interface enumeration);
`ak820/protocol/packet.py` (checksum, 64-byte layout); `ak820/protocol/v2.py`;
`ak820/protocol/lighting.py` payload builders; `ak820/server.py` (path-traversal
safe, Content-Length always set, JSON for all `/api/` paths — the one gap is B22);
`ak820/app.py`; `store.read_json`/`write_json` (atomic); `ui/board.js` (geometry,
hitboxes, ResizeObserver, 82 unique LED indices); `ui/picker.js` (HSV round trip,
pointer capture, arrow keys, quiet `set()`); `ui/app.css` + `ui/index.html` (every
`getElementById` target exists — verified programmatically); the 57-test suite.

### Not covered by the hunt
- The `ak820-driver/tools/` scripts (about 20 untracked one-off diagnostics).
- `ak820/protocol/keymap.py` is read but **not wired into the API or the UI** — which
  is why B27's 126-vs-128 mismatch has no live symptom to point at.
- `tests/test_device.py`, `tests/test_hid_busy.py`, `tests/test_hid_enum.py`,
  `tests/test_protocol.py`, `tests/test_smoke.py`, `ui/tokens.css`, `ui/DESIGN.md`.
- The four open leads from the front-end agent (two pickers, three boards, DOM order,
  `#readout` hidden).

---

## Part 2 — dead code and inconsistencies

| # | Where | What |
|---|---|---|
| 2.1 | `ui/app.js:19` | `const POLL_MS = 2000;` — never used. |
| 2.2 | `ui/app.js` | `state.painting` — declared, never used. |
| 2.3 | `ui/app.js` | `state.sent` — used in 3 places, never declared in the state literal. |
| 2.4 | `ui/app.js:1158` | `let remapMapping = {}` duplicates `state.remapMapping`. |
| 2.5 | `ui/app.css` | Dead rules: `.device`, `.device-swatch`, `.device-text`, `.device-state`, `.device-name`, `.device-chevron` (the device card was removed in a commit but the CSS stayed), plus `.setting-stack` and `.colour-hex` (the HTML uses `.colour-rgb`). |
| 2.6 | `ui/app.css:501` and `ui/app.css:1014` | `.colour-card` is styled **twice** with contradictory `flex` values (`1 1 auto` then `none`). The later one wins. |
| 2.7 | `ui/index.html` + `ui/app.js:11-17` | Section titles and notes are written **twice** (HTML and the `SECTIONS` array). The JS copy is only used by the dead placeholder. |
| 2.8 | three places | "81 keys" vs "82 keys" disagree. |
| 2.9 | `ui/tokens.css` header | Says "there is exactly one accent — the orange in the mark". The mark is **red** (`ajazz-mark.png`) and there is no orange anywhere. |
| 2.10 | `ui/picker.js` | Sets `outline: none` on the hex field. The old design rule said no `outline: none`; it substitutes a border colour, so it is still visible, but decide on one rule and put it in the spec. |
| 2.11 | `ui/app.py` | The "too small" screen says "at least 620 pixels wide", but the window `min_size` is 1100x720 — so that screen can only ever appear in the Edge `--app=` fallback. Meanwhile the CSS breakpoint at `max-width: 1120px` *does* trigger at the window's minimum width. Either lower the window minimum or raise the message. |
| 2.12 | `ui/assets/README.txt` | Does not mention `ajazz-mark.png` or `ak820-caps.json`. It also says "This file came out of the official AJAZZ driver" while sitting next to the PNG it is describing. |

---

## Part 3 — features the official driver has and we do not

### 3.1 What the official driver actually offers
Read out of the vendor app in `.scratch/vendor/official_app/app/`:
- `Skin/lan_en.xml` (32 480 B) — the whole English string table.
- `DefaultData/Keyboard.json` — the board's settings model. It contains
  `SystemStages: { Key6Flag: 1, PollingRate: 0, Repeat: 16, RepeatDelay: 0,
  WFlag: 0, WinFlag: 0 }`.
- `Skin/XML/DeviceXml/keyboarddevice.xml` (75 352 B) — the device panel. It maps:
  - `winlockflag_option` -> `WinFlag`   = "Windows Lock"
  - `wflag_option`       -> `WFlag`     = "Exchange Key" (swap Win / Alt)
  - `6flag_option`       -> `Key6Flag`  = "N Key"  **hidden on this board** (parent
    layout is `visible="false"`)
  - `polling_rate_option_0..3` -> `PollingRate` = **1000Hz / 500Hz / 250Hz / 125Hz**
    (from the image names `1000HZ_normal.png`, `500HZ1.png`, `250HZ.png`, `125HZ1.png`)
  - Repeat Rate / Repeat Delay exist in the config but their whole panel is
    `visible="false"` on this board.

### 3.2 Tier 1 — safe to build now, all app-side, no protocol risk

| # | Feature | Notes |
|---|---|---|
| 3.2.1 | **Profile export / import / duplicate** | `ak820/profiles.py` **already implements** export, import and duplicate. `api.py` has **no routes** for them and there is **no UI**. Dead code today. Cheapest real feature win in the whole list. |
| 3.2.2 | **Macro reorder** (move up / down / to top / to bottom) | Official has `macro_btn_uptop/up/down/downbottom_text`. Ours is a JSON list in `ak820/macros.py`; needs a route and UI buttons. |
| 3.2.3 | **Macro repeat count / rate** | Official `macro_set_times_text` "Rate" and `macro_set_repeat_macro_text` "Repeat this macro". App-side field on the macro. |
| 3.2.4 | **Favourite colours** | Official `collect_color_text` "Favorite Colors". We already ship the 14 vendor palette colours; letting the user pin their own is a small addition to the picker. |
| 3.2.5 | **Random colour** | Official `random_color_text` / `random_all_color_text`. One button in the picker. |
| 3.2.6 | **Macro recording: "Fixed Time (ms)" / "Ignore Latency"** | Official `redio_constant_time` / `redio_ignore_time`. Our `ak820/remap.py` swallows all keys while recording. A fixed-time mode is a small change. |

### 3.3 Tier 2 — gated: needs a hardware capture first, do NOT guess the bytes

These are the features the brief called out. **The semantics are known; the byte
offsets on this board are not.** Writing the wrong offset could corrupt the board's
config, so each one needs the offset confirmed first.

**Resolved 2026-10-24 — read out of the vendor's own program, so no labelled
capture was needed after all.** The official app (`main_app.exe`, a DuiLib
program; the `SDK/osConfLib.dll` folders turn out to hold an *audio* library)
was decompiled with Ghidra. Its record writer at `0x00492b30` — the function
the `winlockflag_option` / `wflag_option` / `polling_rate_option_0..3` click
handlers reach — copies the stages by name out of the packed `SystemStages`
struct into the 29-byte record it sends with WRITE_CONFIG at config 0x0000:

| config | stage | values |
|---|---|---|
| 0x13 | WFlag — **Exchange Key** (swap Win/Alt) | 0 / 1 |
| 0x14 | Key6Flag (hidden on this board; never driven) | preserved |
| 0x15 | WinFlag — **Windows Lock** | 0 / 1 |
| 0x16 | **PollingRate** | 0..3 = 1000 / 500 / 250 / 125 Hz |
| 0x1B / 0x1C | MacMode / Wheel (not exposed) | preserved |

The old capture confirms it: the two flips in it (config 0x15 at 13:05:07,
config 0x13 at 13:05:09) are Windows Lock and Exchange Key being clicked, and
the record's byte order (WFlag, Key6Flag, WinFlag, PollingRate) is *not* the
JSON's order — which is why guessing from `Keyboard.json` had failed. The
polling byte holds the option index, 0 = 1000 Hz. Implemented as
`ak820/protocol/stages.py` (read-modify-write of the whole record, so nothing
else is disturbed), `/api/system-stages`, and three rows in Settings; verified
live on the board — each stage writes, reads back, and restores. The capture
recipe below is kept as the record of how the question would have been settled
the other way.

| # | Feature | Known | Unknown |
|---|---|---|---|
| 3.3.1 | **USB report rate** (1000/500/250/125 Hz) | Field `SystemStages.PollingRate`, 4 values, confirmed from the vendor XML and `Keyboard.json` | Which config byte holds it |
| 3.3.2 | **Windows Lock** (disable the Win key) | Field `SystemStages.WinFlag`, 0/1 | Which config byte |
| 3.3.3 | **Exchange Key** (swap Win and Alt) | Field `SystemStages.WFlag`, 0/1 | Which config byte |
| 3.3.4 | **8 lighting directions** | Official has 8 (`up_to_down`, `down_to_up`, `left_to_right`, `right_to_left`, `inside_to_outside`, `outside_to_inside`, `clockwise`, `anticlockwise`); ours has 2 | Whether this board's firmware honours all 8 |

**How to get the offsets (the tooling already exists):**
`.scratch/capture-official-full.jsonl` was made by hooking `WriteFile` with frida
while the official driver ran. Decoded, it shows the official app writing the config
with `WRITE_CONFIG` (cmd 0x06) at **offset 0x0000, 29 bytes** — one write of the
whole profile block. Decoded payload layout (config offset = payload index):

```
payload[0]      config 0x00  current profile index (0..2)
payload[1]      config 0x01  mode          (1,2,3,...,12, 0xfe)
payload[2]      config 0x02  brightness    (0..4)
payload[3]      config 0x03  speed         (0..4)
payload[4]      config 0x04  direction
payload[5]      config 0x05  random-colour flag
payload[6..8]   config 0x06-08  mode colour RGB
payload[20]     config 0x14  (0xff normally, 0x01 when direction=1)
payload[21]     config 0x15  (0x02 in one capture)
```

This **confirms our own `protocol/v2.py` layout exactly** (mode@0x01, brightness@0x02,
speed@0x03, direction@0x04, random@0x05, colour@0x06-08) — good news, our protocol
is right. It also shows the official app only ever writes **29 bytes** (config
0x00-0x1C), so the system settings are either in the untouched tail of the 0x40-byte
profile block (config 0x1D-0x40) or in a separate region. **Unknown — needs a capture
with the setting actually changed.**

**Checked live against the board on 2026-10-23 (read-only).** The config space is:
`0x00` current profile index; `0x01`/`0x41`/`0x81` three 64-byte profiles; then a
**384-byte keymap from `0xC0` to `0x23F`**; everything after that reads back as zeros.
The keymap is written by the official app's **cmd `0x09`** (its payload matches the
live read byte for byte), which rules the config space out as the home of
WinFlag/PollingRate. So the system stage is under a different command (`0x07` writes
384 bytes at `0x00`, `0x1B` writes 128 bytes) or a region we cannot read — either way
**it still needs a capture with the setting actually changed.**

**The capture recipe:** run the official driver with the frida `WriteFile` hook
already used for `capture-official-full.jsonl`, change *one* setting (say the polling
rate 1000Hz -> 500Hz), stop, and diff the 29-byte payloads. The one byte that
changed is the offset. Repeat for Windows Lock and Exchange Key. That is a
15-minute human-in-the-loop job.

**Until then:** 3.3.1-3.3.3 can be built as far as *UI and storage* (the setting
exists, is remembered, and is labelled "not confirmed for this board" or is simply
not shown). **Do not write a guessed byte to the board.**

### 3.4 Tier 3 — deliberately not doing, and why

| Feature | Why not |
|---|---|
| **Firmware update** | The official driver can flash the board. Dangerous, and a bad flash bricks the keyboard. Out of scope. |
| **Cloud Setting** | Our spec says no cloud, no account, no network. `app/DefaultData` shows a vendor cloud API (`ak980.json` returns a `return_rate` field). Staying off it is the right call. |
| **Board-side macro storage** | The official driver stores macros on the board (up to 125). Our `ak820/macros.py` is PC-side only, on purpose, because the board's macro format is not a library we speak. Keep it PC-side. |
| **N-Key** | Hidden in the official UI for this board, so the firmware may not expose it. |
| **Game Mode** | Real feature, but a big chunk of work with unclear storage. Only if there is time after Tier 1 and 2. |
| **Per-key function assignment (Multimedia / System / Office)** | The official driver assigns functions to keys **on the board**. Ours remaps keys to macros **on the PC** with a low-level hook. Different design, already documented. |

---

## Part 4 — publishability

### 4.1 Legal / IP — the biggest exposure
- **No LICENSE, README or NOTICE anywhere in the repo.** For something you intend to
  publish, that alone blocks it.
- `ui/assets/ak820-board.png` (313 KB) is **the vendor's artwork**, taken from the
  official driver's `app/Skin/Kb/KbKey_normal@150.png`.
  `ui/assets/ajazz-mark.png` (180 KB) is the **AJAZZ logo**.
  Both are redistributed with only a 4-line provenance note and **no permission**.
- The app presents itself as the vendor's product: window title `AJAZZ AK820`
  (`ak820/app.py` `WINDOW_TITLE`), page title `AK820 Driver`, and the string
  "AJAZZ AK820" in `ui/index.html:32` (top bar), `:113` (device line), `:150` and
  `:277` (board captions) plus aria labels. AJAZZ and AK820 are the vendor's marks
  and this is a third-party reimplementation.
  - **Minimum fix:** rename the app, drop the AJAZZ logo, use our own wordmark, and
    describe the product as "a third-party configurator for the AK820 keyboard".
    A "not affiliated with / not endorsed by AJAZZ" line in the About panel and the
    README.
  - **Also:** the artwork must go, or be replaced with something we drew. Redistributing
    a vendor's PNG and logo in a published app is the kind of thing that gets a
    takedown notice.
  - The board's real maker is 深圳市黑爵同创电子科技有限公司 (from
    `company_name_text`), so the AJAZZ mark is a brand on top of that.

### 4.2 Correctness — no errors, every button working
- Live check at 1280x768: **0 console errors, 0 page errors**, both API calls 200.
- 175 buttons render; 6 are correctly disabled.
- **But** the clipped-card bug (B3) makes 3 buttons on Settings, 2 on Macros and
  most of the 21-effect list **unreachable at the default window size** — so "every
  button works" is not true yet at 1280x768. Fix B3, then click every control in all
  five sections and confirm.
- The 3.2.x features add new buttons; each needs a test.

### 4.3 Still not built from the original plan
- **Task 12** — PyInstaller packaging: `build.ps1`, `ak820-driver.spec`,
  `dist/Ak820Driver.exe`. None exist.
- **Task 13** — final audit, end-to-end hardware test, `docs/user-guide.md`. None exist.
- **Task 9b** — mic-reactive mode, knob, polling rate. No `mic.py` / `screen.py`.
  (The "polling rate" in the brief is Tier 2 above — the *keyboard's* USB report
  rate, which is a different thing from our app-side `check_interval`, which is "how
  often the app checks whether the keyboard is plugged in". Say so in the UI.)

---

## Part 5 — execution order (phases)

Ordered by damage-per-risk, not by how easy they are. Each phase is independently
shippable. **Every bug in Parts 1, 1b and 2 gets a regression test** (the rule from
the previous session's plan).

**Phase B runs in parallel with the rest** — the owner is at the keyboard while
the code work carries on.

| Phase | What | Why this order |
|---|---|---|
| **A** | Safety net: commit everything uncommitted, delete the 5 stale tracked root scratch files, fix `.gitignore`, replace the fossil `ui/DESIGN.md`, decide the fate of `.scratch/`, `captures/`, `_ghidra_proj/` and `tools/` | Nothing is lost if the disk dies. Does not touch working code. |
| **B** | **The capture** (owner, in parallel) | Finds the byte offsets for the three gated features. Needs the official driver and the real keyboard, so it is the long pole. |
| **C** | Backend correctness: the dead remap feature (B10-B13, B25, B26); the lighting read/write bounds (B14, B15); the LED overflow (B16); "Reset the lighting" destroying profiles (B17, B18); data loss and the API contract (B19-B22, B29, B31) | A feature that silently does nothing, and a write path that can push 15 KB into a 378-byte buffer, are worse than a cosmetic bug. |
| **D** | Front-end correctness: the animations (B1), the "Never" poll (B2), the clipped cards (B3), `--radius-sm` (B4), the theme's two sources of truth (B5), the device line (B6), the short per-key buffer (B7), the section animation (B8), the remaining front-end bugs (B9) | The screenshots the owner supplied are all Phase D. |
| **E** | Dead code sweep and documentation (Part 2 in full, plus a real `ui/DESIGN.md` written from the finished code) | Only worth doing once the code has stopped moving. |
| **F** | Tier 1 features (3.2.1 - 3.2.6), with tests | All app-side, no protocol risk. |
| **G** | Tier 2 features (3.3.1 - 3.3.3), once Phase B has landed | Cannot be written before the offsets are known. |
| **H** | The rebrand: the name, a new mark, our own board artwork, LICENSE / README / NOTICE, the About panel | Touches `index.html`, `app.css` and `app.js`, so it goes after Phase D has settled those files. |
| **I** | Packaging: `build.ps1`, `ak820-driver.spec`, a one-file `.exe`, `docs/user-guide.md` | The old plan's Tasks 12 and 13. |
| **J** | Final verification: `pytest` green with a test per bug; every control in all five sections clicked at 1280x768 and 1920x1080; a clean-machine install | Definition of done, below. |

### Phase B — the capture recipe (owner at the keyboard)

The tooling already exists and was used to make `.scratch/capture-official-full.jsonl`:

- `ak820-driver/tools/capture_official.py` — attaches frida to the official
  driver, hooks `WriteFile` and `HidD_SetOutputReport`, and writes every HID
  report to a JSONL file.
- `ak820-driver/tools/inspect_capture.py` — reads a capture back and prints the
  config writes.

**What to do:**

1. Open the official driver. The unpacked copy is at
   `.scratch/vendor/official_app/app/AJAZZ AK820 有线RGB Keyboard.exe`.
   If the unpacked copy does not start, the original installer folder is the
   same tree — the exe is the same file. It needs its own runtime; if it
   refuses to start, say so and we find another way.
2. Start the capture **before** you touch any setting.
3. Open the device's settings panel and change **one** setting:
   the USB report rate from 1000Hz to 500Hz. Wait ~10 seconds.
4. Change it back to 1000Hz. Wait ~10 seconds.
5. Do the same for **Windows Lock** (on, then off) and **Exchange Key**
   (on, then off).
6. Stop the capture.

**What we get:** every config write the official driver made, in order. The
official driver writes the profile block as one 29-byte write at offset
0x0000, so the byte that changes between "1000Hz" and "500Hz" is the polling
rate's byte, and the byte that changes between "Windows Lock off" and "on" is
the Windows Lock byte.

**Why the write diff and not a read.** The official driver only ever writes
config `0x00-0x1C`. The system settings must live in the untouched tail of the
0x40-byte profile block (`0x1D-0x40`) or in a separate region, so we cannot
find them by reading defaults — every default is 0. A change makes the byte
move, and a moving byte is an answer we can trust.

**Until it lands:** do not write a guessed byte to the board. A wrong offset
in a config write can corrupt the board's setup.


### Definition of done
- `pytest -q` green, with a **new test for every bug fixed** in Parts 1, 1b and 2.
- All five sections clicked end to end at **1280x768** and **1920x1080**; no clipped
  control, no unreachable button, 0 console errors.
- The preview animates for every mode that the board animates.
- A lighting change works from every state the board can be in, including "off".
- "Bind a key to a macro" survives an off/on cycle and binds the right key.
- "Reset the lighting" leaves the other two board profiles alone.
- Every `/api/` route answers JSON, including on a read-only install folder.
- A fresh install on a clean machine: unzip, run, works, uninstall = delete folder.
- A README that says what it is, what it is not, and who made it.

---

## Appendix — how to reproduce the live checks

```powershell
# start the app against the real board, with a scratch data folder
cd ak820-driver
$env:AK820_DATA_DIR="$env:TEMP\opencode\ak820-data"
.venv\Scripts\python.exe -m ak820.server --port 8731
# -> "Ak820Driver on http://127.0.0.1:8731/"

# the Playwright MCP server wants channel 'chrome', which is NOT installed here.
# ms-playwright's own chromium works:
& "$env:LOCALAPPDATA\ms-playwright\chromium-1243\chrome-win64\chrome.exe" `
  --headless=new --remote-debugging-port=9222 --window-size=1280,768 `
  --user-data-dir="$env:TEMP\opencode\chrome-profile" http://127.0.0.1:8731/
# then drive it with the REA CDP tools:
#   rea_list_browser_targets  (cdp_endpoint http://127.0.0.1:9222,
#                              allowed_origins ["http://127.0.0.1:8731"])
#   rea_inspect_web_page      (target_id from the listing; the id changes on relaunch)
```

Machine notes:
- `rg` is **not** installed. Use the grep tool or `findstr`.
- `more` hangs the shell here (interactive pager) — do not use it.
- `timeout /t` fails when stdin is redirected; use `ping -n N 127.0.0.1 >nul`.
- For one-off Python, write a file under
  `C:\Users\Azelf\AppData\Local\Temp\opencode` and run it with the venv python
  (fragile `cmd -c` quoting bites).
- The REA `capture_browser_scenario` tool rejects `duration_ms` as a string — unusable.
