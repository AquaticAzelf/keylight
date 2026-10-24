"""The EVision V2 command set - the one this keyboard actually speaks.

The AK820 answers the V2 query set even though the vendor's own app never
uses it, which is how we get on-device profiles, custom colour sets and a
read-back of the current state.

Config space layout, confirmed against the board:

    0x00            which profile is active (0, 1 or 2)
    0x01            profile 0's parameter block
    0x41            profile 1's parameter block
    0x81            profile 2's parameter block

Inside a parameter block the byte offset *is* the parameter id:

    0x00 mode          0x01 brightness   0x02 speed        0x03 direction
    0x04 random flag   0x05..0x07 mode colour (RGB)
    0x08 colour offset 0x11 led mode colour
    0x19 current custom colour set
    0x1a logo          0x23 logo on/off   0x24 edge        0x2b end

Writing the profile byte at 0x00 makes the board re-apply that profile.
"""

MAX_PAYLOAD = 56  # 64-byte packet minus the 8-byte header

CMD_READ_CAPABILITIES = 0x03
CMD_READ_CONFIG = 0x05
CMD_WRITE_CONFIG = 0x06
CMD_READ_CUSTOM_COLORS = 0x0A
CMD_WRITE_CUSTOM_COLORS = 0x0B
CMD_SEND_DYNAMIC_COLORS = 0x12
CMD_END_DYNAMIC_COLORS = 0x13

OFFSET_CURRENT_PROFILE = 0x00
OFFSET_FIRST_PROFILE = 0x01
PROFILE_STRIDE = 0x40
PROFILE_COUNT = 3

PARAM_MODE = 0x00
PARAM_BRIGHTNESS = 0x01
PARAM_SPEED = 0x02
PARAM_DIRECTION = 0x03
PARAM_RANDOM_COLOR_FLAG = 0x04
PARAM_MODE_COLOR = 0x05
PARAM_COLOR_OFFSET = 0x08
PARAM_LED_MODE_COLOR = 0x11
PARAM_CURRENT_CUSTOM_MODE = 0x19
PARAM_LOGO = 0x1A
PARAM_LOGO_ON_OFF = 0x23
PARAM_EDGE = 0x24
PARAM_END = 0x2B

PARAM_NAMES = {
    PARAM_MODE: "mode",
    PARAM_BRIGHTNESS: "brightness",
    PARAM_SPEED: "speed",
    PARAM_DIRECTION: "direction",
    PARAM_RANDOM_COLOR_FLAG: "random_colour_flag",
    PARAM_MODE_COLOR: "mode_colour",
    PARAM_COLOR_OFFSET: "colour_offset",
    PARAM_LED_MODE_COLOR: "led_mode_colour",
    PARAM_CURRENT_CUSTOM_MODE: "current_custom_mode",
    PARAM_LOGO: "logo",
    PARAM_LOGO_ON_OFF: "logo_on_off",
    PARAM_EDGE: "edge",
}

# Lighting modes, with the names the vendor's own app uses.
MODE_WAVE = 0x01
MODE_CLOUD = 0x02
MODE_VORTEX = 0x03
MODE_SPECTRUM = 0x04
MODE_BREATH = 0x05
MODE_STATIC = 0x06
MODE_REACTIVE = 0x07
MODE_RIPPLE = 0x08
MODE_TRAVERSE = 0x09
MODE_STARS = 0x0A
MODE_FLOWERS = 0x0B
MODE_ROLL = 0x0C
MODE_WAVE_BAR = 0x0D
MODE_CARTOON = 0x0E
MODE_RAIN = 0x0F
MODE_SCAN = 0x10
MODE_SURMOUNT = 0x11
MODE_SPEED = 0x12
MODE_CUSTOM = 0x14
MODE_DIRECT = 0xFF  # software controlled: the board shows exactly what we send

# A parameter the board does not implement reads back as this.
UNSUPPORTED = 0xFF

CAPABILITIES_MAGIC = (0xAA, 0x55)


def profile_offset(index: int) -> int:
    """Config offset of a profile's parameter block."""
    if not 0 <= index < PROFILE_COUNT:
        raise ValueError("profile index out of range: %r" % (index,))
    return OFFSET_FIRST_PROFILE + index * PROFILE_STRIDE


def parse_capabilities(payload: bytes) -> dict | None:
    """Read the READ_CAPABILITIES reply, or ``None`` if the board did not answer."""
    if len(payload) < 7:
        return None
    if payload[0] != CAPABILITIES_MAGIC[0] or payload[1] != CAPABILITIES_MAGIC[1]:
        return None
    return {
        "supported": True,
        "map_size": payload[5],
        "macros_size": payload[6] * 0x80,
        "raw": payload[:7].hex(" "),
    }
