from dataclasses import dataclass
from enum import IntEnum, Enum
from typing import Union


# --- Enums for Readability ---

class NcMode(IntEnum):
    OFF = 0
    NOISE_CANCELLING = 1
    AMBIENT_SOUND = 2


class BootNcMode(IntEnum):
    OFF = 0
    NOISE_CANCELLING = 1
    AMBIENT_SOUND = 2
    REMEMBER_LAST = 3


class BootBtMode(IntEnum):
    OFF = 0
    ON = 1
    REMEMBER_LAST = 2


class Language(IntEnum):
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


# --- Data Containers ---

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


@dataclass
class NcStatus:
    nc_mode: NcMode
    mic_muted: bool


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
