# AK820 protocol

Everything here was measured on a real AJAZZ AK820 (USB `320F:505B`), not
guessed. Where something is still uncertain it says so.

## The device

| | |
|---|---|
| USB | VID `0x320F`, PID `0x505B` |
| HID collection | interface 1, collection 4 (`mi_01&col04`) |
| Usage page | `0xFF1C` |
| Report length | 64 bytes in, 64 bytes out |
| Report ID | `0x04` |

The board is an **EVision / Yichip** keyboard. It speaks the older "V1"
command set *and* answers the newer "V2" query set, which the vendor's own app
never uses. V2 is the interesting one: it lets us read the board's state back
and store things on the board itself.

## Packet format

64 bytes.

```
byte  0      report id (0x04)
byte  1-2    checksum, little endian uint16 = sum(bytes 3..63)
byte  3      command
byte  4      size
byte  5-6    parameter id (V1) or offset (V2), little endian
byte  7      status (0 = ok)
byte  8-63   payload
```

`BEGIN_CONFIGURE` (0x01) and `END_CONFIGURE` (0x02) frame a group of
commands. The two frames are sent with a fixed body - their checksum is not
computed, it is already correct.

## Commands

| Code | Name | Direction |
|---|---|---|
| 0x01 | BEGIN_CONFIGURE | → |
| 0x02 | END_CONFIGURE | → |
| 0x03 | READ_CAPABILITIES | → |
| 0x05 | READ_CONFIG / write | ↔ |
| 0x06 | WRITE_CONFIG | → |
| 0x07 | chunked transfer | ↔ |
| 0x09 | write keymap | → |
| 0x0A | READ_CUSTOM_COLORS | → |
| 0x0B | WRITE_CUSTOM_COLORS | → |
| 0x0D | commit / re-sync | → |
| 0x12 | SEND_DYNAMIC_COLORS | → |
| 0x13 | END_DYNAMIC_COLORS | → |
| 0x1A | read memory | ↔ |
| 0x1B | custom colours, chunked | ↔ |

The left half of that table is the command set we use. The right half is what
the **vendor's own app** sends, recorded from the wire while it ran against
this keyboard (see `tools/capture_official.py`):

| Command | What the app sends | How often |
|---|---|---|
| 0x05 | one byte at offset `0x01`, and 29 bytes at offset `0x1d` | 3 each |
| 0x06 | a 29-byte per-key record at offset `0x0000` | 36 |
| 0x07 / 0x09 | the 384-byte keymap, in 7 chunks of 56, the last 48 at offset `0x150` | 7 / 14 |
| 0x12 | the whole colour buffer, 7 chunks (56 × 6, then 42) at offsets `0x00`, `0x38`, `0x70`, `0xA8`, `0xE0`, `0x118`, `0x150` | **19 292** |
| 0x1A | six bytes at offset 0 | every 5 s |

Two things fall out of that:

* **On-device key remapping is real.** The app writes the keymap to the board,
  and the bytes it writes are the same ones we read back from `0xC0`.
* **The app streams the colour buffer instead of sending it once.** 19 292
  chunks is its live on-screen preview redrawing itself, not a protocol
  requirement - one buffer of 378 bytes is enough, and that is what we send.

The 29-byte record the app writes for the "Button Settings" tab looks like
`00 <key index> 04 02 00 <00|01> <R> <G> <B> ... FF at 23, 00 00 00 00`.
Across the 36 records the app sent, the fields that ever change are:

| Byte | Values seen | Likely meaning |
|---|---|---|
| 1 | `01`..`0c`, `fe` | which key (`fe` = all of them) |
| 5 | `00`, `01` | enabled |
| 6-8 | any | the key's colour |
| 19 | `00`, `01` | |
| 20 | `01`, `ff` | |
| 21 | `00`, `01` | |
| 25 | `00`, `02` | |

The names of those four flags are still unknown.

`READ_CAPABILITIES` answers `AA 55 00 00 0D 80 50`:

* `0x0D` = 13 → **map size 128** colour slots
* `0x80` → **80 × 0x80 = 10240 bytes** of on-device macro storage
* `0x50` → unknown

The firmware's map size is 128, but the **colour buffer this board actually
uses is 126 slots** (378 bytes): the vendor's app streams exactly that, and the
board's highest LED is slot 125. The two spare slots belong to the number pad
of the generic template the firmware carries.

## Config space

```
0x00          which profile is active (0, 1 or 2)
0x01          profile 0's parameter block
0x41          profile 1's parameter block
0x81          profile 2's parameter block
0xC0          keycode table: 128 slots x 3 bytes
              (modifier, usage high, usage low)
```

Inside a parameter block the byte offset *is* the parameter id:

| Offset | Parameter |
|---|---|
| 0x00 | mode |
| 0x01 | brightness (0-4) |
| 0x02 | speed (0-5, 0 = fastest) |
| 0x03 | direction (0 left, 1 right, 2 up, 3 down) |
| 0x04 | random colour flag |
| 0x05-0x07 | mode colour (RGB) |
| 0x08 | colour offset |
| 0x11 | LED mode colour |
| 0x19 | current custom colour set |
| 0x1a | logo |
| 0x23 | logo on/off |
| 0x24 | edge |
| 0x2b | end |

**The board only shows a profile once the profile byte at `0x00` is written.**
Write the parameters first, then the profile byte.

## System settings (the live record)

The board keeps its system settings in a **29-byte record at config `0x0000`**
- the same record that starts with the profile index and profile 0's lighting
bytes. Bytes `0x09..0x1C` hold the global settings:

| Offset | Setting | Values |
|---|---|---|
| `0x13` | **Exchange key** (swap Win/Alt) | 0 / 1 |
| `0x14` | N-key flag (not exposed on this board) | preserved |
| `0x15` | **Windows Lock** (disable the Win key) | 0 / 1 |
| `0x16` | **Report rate** | 0..3 = 1000 / 500 / 250 / 125 Hz |
| `0x1B`, `0x1C` | Mac mode, wheel | preserved |

The official driver changes a setting by reading the whole record, patching
the one byte and writing all 29 bytes back - so the lighting bytes and the
flags it does not drive are carried over, never zeroed. We do the same.
`0x0D` is the vendor's bare "commit" packet, sent after a profile restore;
a plain stage write does not need it.

All six lighting speeds (0 = fastest … 5 = slowest) store verbatim, and so
does every mode id - including `0x1D` and `0x1E`, which the vendor's app
writes as `0xFE` because *it* drives those two from the PC. The board
accepts the plain ids; the `0xFE` form is the vendor's convention, not a
firmware requirement.

`0x00` is **the index of the profile on show, not a setting.** A value outside
`0..2` leaves the board without a profile and it falls back to cycling through
its own effects - which looks exactly like "my colour change did nothing".

Which profile the board is showing is not ours to guess, so the same state is
written to all three blocks and the index is set to a valid one afterwards.
The board then shows the right thing whichever one it was on.

## Lighting modes

| Id | Name | Id | Name |
|---|---|---|---|
| 0x01 | wave | 0x0A | stars |
| 0x02 | cloud | 0x0B | flowers |
| 0x03 | vortex | 0x0C | roll |
| 0x04 | spectrum | 0x0D | wave bar |
| 0x05 | breath | 0x0E | cartoon |
| 0x06 | **static** | 0x0F | rain |
| 0x07 | reactive | 0x10 | scan |
| 0x08 | ripple | 0x11 | surmount |
| 0x09 | traverse | 0x12 | speed |
| | | 0x14 | custom |
| | | 0xFF | **software controlled** |

`0xFF` ("software controlled") is the mode that shows exactly the per-key
colours we send; the animated modes ignore the per-key buffer.

The vendor's own app also offers two modes that are implemented in software on
the PC, not in the board: `0x1D` audio wave (microphone) and `0x1E` capture
colour (pick a colour off the screen). We implement those ourselves.

## Per-key colours

`SEND_DYNAMIC_COLORS` (0x12) writes RGB triples into the board's 126-slot
colour buffer. Each write is 3 bytes at a byte offset of `slot * 3`, and the
whole buffer goes out in chunks of 56 bytes, closed by `END_DYNAMIC_COLORS`
(0x13).

The board's slot order is its own LED chain order, and it is **not** the same
as the numbering the vendor's app uses in its own layout files (we tried the
vendor's table once; the hardware lit the grid's keys, not the vendor's). The
mapping is **measured, not assumed**: `ak820-driver/ui/assets/ak820-caps.json`
holds all 82 keys with their slots, pinned by painting the chain and reading
it back (`tools/paint_slots.py`).

The chain is *mostly* an 8-column grid, but not exactly - the letter row
runs one slot earlier than the grid formula says (left Shift 4, Z 20, X 28,
… `/` 92, right Shift 108), Del is 114, and slots such as 12 and 100 light
nothing at all. Measure, then trust the measurement.

The alternative command `0x11` does the same job but sets the status byte to
`0xFF` instead of `0x00`.

## The keycode table at 0xC0

128 slots of 3 bytes, holding the keycode the board sends for each physical
key. The board ships a **generic full-size ANSI template** in it (it has
Num Lock, F13-F17 and a number pad, none of which this board has) - the
vendor's app overwrites it with the real layout when you remap keys. Its
order is a generic 8-column grid, not this board's wiring.

**The table can be written.** The app writes it with command `0x09`, in the
same seven 56-byte chunks the colour buffer uses (the last chunk is 48 bytes
at offset `0x150`), and the bytes it writes are byte-for-byte what we read
back from `0xC0`. So the keymap is ours to change: three bytes per slot,
`[modifier class, usage high, usage low]`.

## Vendor usage encoding

The board does not use raw HID usages. Modifier keys are encoded as
`0x100` LCtrl, `0x200` LShift, `0x400` LAlt, `0x800` LGUI, with the modifier
byte distinguishing left from right (`0x20` left, `0xA0` right, `0xD0`
function keys, `0x30` keypad).

## What is still unknown

* The knob. It is a rotary encoder on the board; nothing in the config space
  has been identified as its setting yet.
* The on-device macro storage format. The board has 10 KB of it, but the
  layout is not known - reading high config offsets returns data that does
  not match the offset asked for, so the area has not been found yet.
* Whether the logo and edge parameters do anything on this board.
* A handful of LED chain slots nothing lit for (12, 100) - hidden positions,
  most likely for keys this board does not have.

## The vendor's own API

The app does not talk to the keyboard directly from its menu code. It calls
one exported function in `SDK/x64/vista/osConfLib.dll`:

```c
PropertyControl(int header[4], long long propertyId, void **buffer,
                unsigned long length, char flag);
```

`header` is the four bytes of the packet that go at bytes 3..7 (command,
size, offset), `propertyId` is a setting number, and `buffer` points at a
1024-byte payload.

That library is a generic **Dolby/DTS audio DSP** library ("Audio
Configuration Library for Vista/Win7/Win8/Win8.1/Win10" is its own banner),
used by the app for the audio-reactive lighting. The keyboard's own protocol
code lives in the app's main executable, which imports `HidD_SetOutputReport`
and loads the audio library dynamically.

## Where this came from

The lighting half of this protocol is public: OpenRGB's
`Controllers/EVisionKeyboardController` implements the V1 command set, and its
V2 controller documents the config space above. The board ids
(`320F:505B`) are not in OpenRGB's V2 detector list, so nothing in the wild
had driven this board with the V2 commands before.

The system settings were read out of the official driver's own executable
(its record writer, reached from the Windows Lock / Exchange / report-rate
click handlers), confirmed against a wire capture of the official app, and
then verified live on the board - each setting written, read back and
restored. The per-key chain order was measured on the hardware.
