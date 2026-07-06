from typing import Dict, Tuple, Union


VENDOR_ID: int = 0x054c
REPORT_ID: int = 0x02

# (vendor_id, product_id) -> model name. All models assumed protocol-compatible.
SUPPORTED_DEVICES: Dict[Tuple[int, int], str] = {
    (0x054c, 0x0fa8): "INZONE H9 II",
    (0x054c, 0x0ec2): "INZONE Buds",
}

MAGIC_1: int = 0x96
MAGIC_2: int = 0xC3

WRITE_MAP: Dict[str, Tuple[int, int, Union[int, Tuple[int, ...]], int, int, Dict[int, int]]] = {
    'nc_mode':       (0x10, 0x41, 13, 17, 0xF0, {14: 0x14, 15: 0xFF}),
    'volume':        (0x0F, 0x21, 14, 16, 0xBC, {15: 0xFF}),
    'balance':       (0x0D, 0x22, 13, 14, 0xBE, {}),
    'sidetone':      (0x0E, 0x23, 13, 15, 0xBE, {14: 0xFF}),
    'auto_off':      (0x0E, 0x81, 13, 15, 0x22, {14: 0x05}),
    'notif_voice':   (0x0D, 0x84, 13, 14, 0x20, {}),
    'voice_lang':    (0x0D, 0x83, 13, 14, 0x1F, {}),
    'boot_nc':       (0x0D, 0x43, 13, 14, 0xDF, {}),
    'boot_bt':       (0x0D, 0x63, 13, 14, 0xFF, {}),
    
    'ambient_sound': (0x10, 0x41, (14, 16), 17, 0xDE, {13: 0x02, 15: 0xFF}),
}

# Audio Status (0x06) response byte offsets. Writes use identical commands and
# scales on all models; only the response layout differs. The Buds shift the
# control fields and report three battery values (bud L/R at 15/17, case at 19).
DEFAULT_AUDIO_LAYOUT: Dict[str, int] = {
    'charging': 14, 'battery': 15, 'volume': 17, 'balance': 19, 'sidetone': 20,
}
AUDIO_STATUS_LAYOUTS: Dict[Tuple[int, int], Dict[str, int]] = {
    (0x054c, 0x0ec2): {
        'charging': 14, 'battery': 15, 'volume': 21, 'balance': 23, 'sidetone': 24,
        'battery_left': 15, 'battery_right': 17, 'battery_case': 19,
    },
}

REQ_AUDIO_STATUS: int = 0x06
REQ_NC_STATUS: int = 0x07
REQ_SYSTEM_STATUS: int = 0x08

EVT_CATEGORY: int = 0x14
EVT_POWER: int = 0x04        
EVT_VOL_CHANGED: int = 0x21
EVT_BAL_CHANGED: int = 0x22
EVT_NC_CHANGED: int = 0x41
EVT_MIC_MUTE: int = 0x24
EVT_MIC_CONN: int = 0x8F
EVT_BT_STATE: int = 0x61

LANG_MAP: Dict[int, str] = {0: "English", 1: "Japanese", 2: "Chinese"}
NC_MODE_MAP: Dict[int, str] = {0: "Off", 1: "Noise Cancelling", 2: "Ambient Sound"}
BOOT_NC_MAP: Dict[int, str] = {0: "Off", 1: "NC", 2: "Ambient", 3: "Remember Last"}
BOOT_BT_MAP: Dict[int, str] = {0: "Off", 1: "On", 2: "Remember Last"}