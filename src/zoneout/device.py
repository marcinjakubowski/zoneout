from typing import Generator, Optional, List, Any, Union, Tuple

import hid

from . import protocol
from .exceptions import DeviceNotFoundError, ProtocolError
from .models import (
    AudioStatus, NcStatus, SystemStatus, HeadsetFullStatus,
    HeadsetEvent, BluetoothState, NcMode, BootNcMode, BootBtMode,
    Language, EventType, PowerState
)


class ZoneHeadset:
    def __init__(self) -> None:
        self.device: Optional[Any] = None
        self.seq: int = 1  # Rolling sequence counter

    def connect(self) -> None:
        try:
            self.device = hid.device()
            self.device.open(protocol.VENDOR_ID, protocol.PRODUCT_ID)
            self.device.set_nonblocking(0)
        except Exception as e:
            raise DeviceNotFoundError(
                f"Could not open H9 Headset ({hex(protocol.VENDOR_ID)}:{hex(protocol.PRODUCT_ID)}). "
                f"Check USB connection and permissions (udev rules)."
            ) from e

    def close(self) -> None:
        if self.device:
            self.device.close()
            self.device = None

    def __enter__(self) -> "ZoneHeadset":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # --- Low Level Protocol ---

    def _send_cmd(self, setting_key: str, value: Union[int, Tuple[int, ...]]) -> None:
        if setting_key not in protocol.WRITE_MAP:
            raise ProtocolError(f"Unknown setting key: {setting_key}")

        type_byte, cmd_byte, val_idx, chk_idx, chk_const, spacers = protocol.WRITE_MAP[setting_key]

        data = bytearray(64)
        header = bytes([
            protocol.REPORT_ID, type_byte, 0x01, 0x00, 0xfc, (type_byte - 4),
            protocol.MAGIC_1, protocol.MAGIC_2, 0x41, cmd_byte, 0x02, self.seq
        ])
        data[0:len(header)] = header
        if isinstance(val_idx, tuple):
            if not isinstance(value, (tuple, list)) or len(value) != len(val_idx):
                raise ProtocolError(f"Value mismatch for multi-write key {setting_key}")
            
            chk_sum_base = 0
            for i, idx in enumerate(val_idx):
                v = value[i]
                data[idx] = v
                chk_sum_base += v
            
            for idx, byte_val in spacers.items():
                data[idx] = byte_val

            data[chk_idx] = (self.seq + chk_sum_base + chk_const) & 0xFF
        else:
            data[val_idx] = value

            for idx, byte_val in spacers.items():
                data[idx] = byte_val

            data[chk_idx] = (self.seq + value + chk_const) & 0xFF

        if self.device:
            self.device.write(data)

        self.seq = (self.seq + 1) if self.seq < 255 else 1

        # Aggressive flush of any immediate response/echo
        try:
            if self.device:
                self.device.read(64, timeout_ms=20)
        except:
            pass

    def _get_report(self, cmd_id: int, retries: int = 10) -> List[int]:
        req = bytearray(64)

        # Calculate Checksum for Read Request
        # Observed pattern:
        # Req 06 (Audio): Checksum A2 (06 + 9C = A2)
        # Req 07 (NC):    Checksum A3 (07 + 9C = A3)
        # Req 08 (Sys):   Checksum A4 (08 + 9C = A4)
        read_checksum = (cmd_id + 0x9C) & 0xFF

        header = bytes([
            protocol.REPORT_ID, 0x0C, 0x01, 0x00, 0xFC, 0x08,
            protocol.MAGIC_1, protocol.MAGIC_2, 0x41, cmd_id,
            0x01, 0x01, 0x00, read_checksum  # Mode=1, Seq=1, Val=0, Checksum
        ])
        req[0:len(header)] = header

        if not self.device:
            raise DeviceNotFoundError("Device not connected")

        # flush
        while True:
            d = self.device.read(64, timeout_ms=10)
            if not d: break

        # send
        self.device.write(req)

        # read
        for _ in range(retries):
            data = self.device.read(64, timeout_ms=15)
            if not data: continue

            # Check length and Command ID (Byte 9)
            if len(data) >= 64 and data[9] == cmd_id:
                return data

        raise ProtocolError(f"Timeout waiting for Report CMD {hex(cmd_id)}")

    # --- Public API: Setters ---

    def set_volume(self, value: int) -> None:
        self._send_cmd('volume', max(0, min(30, int(value))))

    def set_balance(self, value: int) -> None:
        self._send_cmd('balance', max(0, min(100, int(value))))

    def set_sidetone(self, value: int) -> None:
        self._send_cmd('sidetone', max(0, min(10, int(value))))

    def set_noise_cancelling(self, mode: int) -> None:
        self._send_cmd('nc_mode', max(0, min(2, int(mode))))

    def set_auto_power_off(self, minutes: int) -> None:
        self._send_cmd('auto_off', int(minutes))

    def set_notification_voice(self, enabled: bool) -> None:
        self._send_cmd('notif_voice', 1 if enabled else 0)

    def set_voice_language(self, lang_idx: int) -> None:
        self._send_cmd('voice_lang', max(0, min(2, int(lang_idx))))

    def set_boot_nc_mode(self, mode: int) -> None:
        self._send_cmd('boot_nc', max(0, min(3, int(mode))))

    def set_boot_bt_mode(self, mode: int) -> None:
        self._send_cmd('boot_bt', max(0, min(2, int(mode))))

    def set_ambient_sound(self, level: int, focus: bool) -> None:
        level = max(0, min(20, int(level)))
        focus_val = 1 if focus else 0
        self._send_cmd('ambient_sound', (level, focus_val))

    def set_ambient_sound_level(self, level: int) -> None:
        """Helper for CLI: sets level with Focus=False"""
        self.set_ambient_sound(level, False)

    def set_ambient_sound_focus(self, focus: int) -> None:
        """Helper for CLI: sets focus with Level=20 (Max)"""
        self.set_ambient_sound(20, bool(focus))

    # --- Public API: Getters (Typed) ---

    def get_audio_status(self) -> AudioStatus:
        data = self._get_report(protocol.REQ_AUDIO_STATUS)
        # Byte 22 is an internal state checksum, ignored.

        return AudioStatus(
            volume=data[17],
            balance=data[19],
            sidetone=data[20],
            battery_level=data[15],
            charging=bool(data[14])
        )

    def get_nc_status(self) -> NcStatus:
        data = self._get_report(protocol.REQ_NC_STATUS)
        return NcStatus(
            nc_mode=NcMode(data[16]),
            mic_muted=bool(data[13]),
            ambient_level=data[17],
            focus_on_voice=bool(data[19])
        )

    def get_system_status(self) -> SystemStatus:
        data = self._get_report(protocol.REQ_SYSTEM_STATUS)
        return SystemStatus(
            boot_nc=BootNcMode(data[13]),
            bt_state=BluetoothState(enabled=bool(data[14]), connected=data[15] == 1),
            boot_bt=BootBtMode(data[17]),
            auto_off_minutes=data[18],
            language=Language(data[21]),
            notif_enabled=data[22] == 1,
            mic_connected=data[24] == 0
        )

    def get_all_data(self) -> HeadsetFullStatus:
        return HeadsetFullStatus(
            audio=self.get_audio_status(),
            nc=self.get_nc_status(),
            system=self.get_system_status()
        )

    # --- Public API: Event Listener ---

    def listen(self) -> Generator[HeadsetEvent, None, None]:
        """Yields typed HeadsetEvent objects."""
        if not self.device:
            raise DeviceNotFoundError("Device not connected")

        while True:
            data = self.device.read(64, timeout_ms=1000)
            if not data: continue

            if len(data) >= 16 and data[2] == 0x04 and data[8] == protocol.EVT_CATEGORY:
                cmd = data[9]

                if cmd == protocol.EVT_POWER:
                    yield HeadsetEvent(
                        EventType.POWER,
                        PowerState(charging=bool(data[13]), battery_level=data[14])
                    )

                elif cmd == protocol.EVT_VOL_CHANGED:
                    yield HeadsetEvent(EventType.VOLUME, int(data[14]))

                elif cmd == protocol.EVT_BAL_CHANGED:
                    yield HeadsetEvent(EventType.BALANCE, int(data[13]))

                elif cmd == protocol.EVT_NC_CHANGED:
                    yield HeadsetEvent(EventType.NC_MODE, NcMode(data[13]))

                elif cmd == protocol.EVT_MIC_MUTE:
                    yield HeadsetEvent(EventType.MIC_MUTE, bool(data[13]))

                elif cmd == protocol.EVT_MIC_CONN:
                    # 0=Connected, 1=Disconnected
                    yield HeadsetEvent(EventType.MIC_CONN, data[13] == 0)

                elif cmd == protocol.EVT_BT_STATE:
                    yield HeadsetEvent(
                        EventType.BLUETOOTH,
                        BluetoothState(enabled=bool(data[13]), connected=bool(data[14]))
                    )
