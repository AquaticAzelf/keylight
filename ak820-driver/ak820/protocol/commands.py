"""The EVision V1 command set.

The AK820's firmware speaks the EVision V1 dialect: a 64-byte HID output report
whose first byte is the report id and whose last two command bytes are a
checksum over the rest.
"""

CMD_BEGIN = 0x01
CMD_END = 0x02
CMD_SET_PARAMETER = 0x06
CMD_LED_DATA = 0x11

COMMAND_NAMES = {
    CMD_BEGIN: "BEGIN",
    CMD_END: "END",
    CMD_SET_PARAMETER: "SET_PARAMETER",
    CMD_LED_DATA: "LED_DATA",
}
