from dataclasses import dataclass
from enum import IntEnum, Enum
from typing import Optional, Union


class TolerantIntEnum(IntEnum):
    """Maps values a device reports for unsupported features (e.g. 0xFF) to UNKNOWN."""
    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


class NcMode(TolerantIntEnum):
    UNKNOWN = -1
    OFF = 0
    NOISE_CANCELLING = 1
    AMBIENT_SOUND = 2


class BootNcMode(TolerantIntEnum):
    UNKNOWN = -1
    OFF = 0
    NOISE_CANCELLING = 1
    AMBIENT_SOUND = 2
    REMEMBER_LAST = 3


class BootBtMode(TolerantIntEnum):
    UNKNOWN = -1
    OFF = 0
    ON = 1
    REMEMBER_LAST = 2


class Language(TolerantIntEnum):
    UNKNOWN = -1
    ENGLISH = 0
    JAPANESE = 1
    CHINESE = 2


class EventType(Enum):
    POWER = "power"
    VOLUME = "volume"
    BALANCE = "balance"
    NC_MODE = "nc_mode"
    MIC_MUTE = "mic_muted"
    MIC_CONN = "mic_connected"
    BLUETOOTH = "bluetooth"


@dataclass
class DeviceInfo:
    vendor_id: int
    product_id: int
    name: str


@dataclass
class PowerState:
    charging: bool
    battery_level: int


@dataclass
class BluetoothState:
    enabled: bool
    connected: bool


@dataclass
class AudioStatus:
    volume: int
    balance: int
    sidetone: int
    battery_level: int
    charging: bool
    # Per-component batteries for true-wireless models (None on headsets)
    battery_left: Optional[int] = None
    battery_right: Optional[int] = None
    battery_case: Optional[int] = None


@dataclass
class NcStatus:
    nc_mode: NcMode
    mic_muted: bool
    ambient_level: int
    focus_on_voice: bool


@dataclass
class SystemStatus:
    boot_nc: BootNcMode
    boot_bt: BootBtMode
    bt_state: BluetoothState
    auto_off_minutes: int
    language: Language
    notif_enabled: bool
    mic_connected: bool


@dataclass
class HeadsetFullStatus:
    audio: AudioStatus
    nc: NcStatus
    system: SystemStatus


@dataclass
class HeadsetEvent:
    type: EventType
    value: Union[int, bool, BluetoothState, NcMode, PowerState]
