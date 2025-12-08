from typing import Dict, Tuple

# Device ID (Sony H9 II)
VENDOR_ID: int = 0x054c
PRODUCT_ID: int = 0x0fa8
REPORT_ID: int = 0x02

# Magic Bytes
MAGIC_1: int = 0x96
MAGIC_2: int = 0xC3

# -- Write Constants --
# Structure: [TYPE] ... [CMD] ... Val@Offset ... Chk@Offset ... Constant
# Mapped as: 'name': (TYPE, CMD, Val_Offset, Chk_Offset, Constant, {Spacers})
# Key: str
# Value: (Type Byte, Cmd Byte, Value Offset, Checksum Offset, Checksum Constant, Spacers Dict)
WRITE_MAP: Dict[str, Tuple[int, int, int, int, int, Dict[int, int]]] = {
    'nc_mode':       (0x10, 0x41, 13, 17, 0xF0, {14: 0x14, 15: 0xFF}),
    'volume':        (0x0F, 0x21, 14, 16, 0xBC, {15: 0xFF}),
    'balance':       (0x0D, 0x22, 13, 14, 0xBE, {}),
    'sidetone':      (0x0E, 0x23, 13, 15, 0xBE, {14: 0xFF}),
    'auto_off':      (0x0E, 0x81, 13, 15, 0x22, {14: 0x05}),
    'notif_voice':   (0x0D, 0x84, 13, 14, 0x20, {}),
    'voice_lang':    (0x0D, 0x83, 13, 14, 0x1F, {}),
    'boot_nc':       (0x0D, 0x43, 13, 14, 0xDF, {}),
    'boot_bt':       (0x0D, 0x63, 13, 14, 0xFF, {}),
}

# -- Read Constants --
# Request IDs (CMD bytes) for initialization
REQ_AUDIO_STATUS: int = 0x06
REQ_NC_STATUS: int = 0x07
REQ_SYSTEM_STATUS: int = 0x08

# -- Event Constants --
# Category 0x14, Mode 0xA0
EVT_CATEGORY: int = 0x14
EVT_POWER: int = 0x04        # Charging/Battery Event
EVT_VOL_CHANGED: int = 0x21
EVT_BAL_CHANGED: int = 0x22
EVT_NC_CHANGED: int = 0x41
EVT_MIC_MUTE: int = 0x24
EVT_MIC_CONN: int = 0x8F
EVT_BT_STATE: int = 0x61

# Value Mappings
LANG_MAP: Dict[int, str] = {0: "English", 1: "Japanese", 2: "Chinese"}
NC_MODE_MAP: Dict[int, str] = {0: "Off", 1: "Noise Cancelling", 2: "Ambient Sound"}
BOOT_NC_MAP: Dict[int, str] = {0: "Off", 1: "NC", 2: "Ambient", 3: "Remember Last"}
BOOT_BT_MAP: Dict[int, str] = {0: "Off", 1: "On", 2: "Remember Last"}