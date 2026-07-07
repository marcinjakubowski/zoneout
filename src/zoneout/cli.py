import argparse
import sys
import threading
import time
from typing import Dict, List, Tuple, Optional, Any
from .device import ZoneHeadset, find_devices, resolve_device
from .exceptions import DeviceNotFoundError
from .models import NcMode, BootNcMode, BootBtMode, Language, DeviceInfo


VAR_MAP: Dict[str, Tuple[str, str, Optional[str]]] = {
    'volume': ('audio', 'volume', 'set_volume'),
    'balance': ('audio', 'balance', 'set_balance'),
    'sidetone': ('audio', 'sidetone', 'set_sidetone'),
    'battery': ('audio', 'battery_level', None),

    'nc_mode': ('nc', 'nc_mode', 'set_noise_cancelling'),
    'mic_muted': ('nc', 'mic_muted', None),

    'auto_off': ('system', 'auto_off_minutes', 'set_auto_power_off'),
    'language': ('system', 'language', 'set_voice_language'),
    'notif': ('system', 'notif_enabled', 'set_notification_voice'),
    'mic_connected': ('system', 'mic_connected', None),
    'boot_nc': ('system', 'boot_nc', 'set_boot_nc_mode'),
    'boot_bt': ('system', 'boot_bt', 'set_boot_bt_mode'),
    'ambient_level': ('nc', 'ambient_level', 'set_ambient_sound_level'),
    'focus_voice': ('nc', 'focus_on_voice', 'set_ambient_sound_focus'),
}

VARIABLE_HELP = """
VARIABLES & ALLOWED VALUES:
---------------------------
[Audio]
  volume        0-30
  balance       0-100   (0=Max Game, 50=Mix, 100=Max Chat)
  sidetone      0-10    (Microphone Monitoring Level)

[Noise Control]
  nc_mode       0=Off, 1=Noise Cancelling, 2=Ambient Sound
  ambient_level 1-20    (Ambient Sound Level)
  focus_voice   0/1     (Focus on Voice)

[System]
  auto_off      0 (Disabled), 5, 10, 30, 60, 180 (Minutes)
  language      0=English, 1=Japanese, 2=Chinese
  notif         0=Off, 1=On (Beeps/Voice Guidance)

[Boot Defaults]
  boot_nc       0=Off, 1=NC, 2=Amb, 3=Remember Last
  boot_bt       0=Off, 1=On, 2=Remember Last

[Read Only]
  battery       (0-100%)
  mic_muted     (0/1)
  mic_connected (0/1)
"""

def format_value(value: Any) -> str:
    if isinstance(value, (NcMode, BootNcMode, BootBtMode, Language)):
        return f"{value.value} ({value.name.replace('_', ' ').title()})"
    if isinstance(value, bool):
        return "On" if value else "Off"
    return str(value)


def get_targets(device_arg: Optional[str]) -> List[DeviceInfo]:
    """Devices to operate on: the one named by --device, or all connected."""
    if device_arg:
        return [resolve_device(device_arg)]
    devices = find_devices()
    if not devices:
        raise DeviceNotFoundError(
            "No supported INZONE device found. "
            "Check USB connection and permissions (udev rules)."
        )
    return devices


def print_status(headset: ZoneHeadset) -> None:
    status = headset.get_all_data()

    charge_str = " (Charging)" if status.audio.charging else ""

    print(f"Device: {headset.name}\n")
    print("--- Audio ---")
    print(f"Volume:             {status.audio.volume}")
    print(f"Game/Chat Balance:  {status.audio.balance}")
    print(f"Sidetone:           {status.audio.sidetone}")
    if status.audio.battery_left is not None or status.audio.battery_case is not None:
        def pct(v): return f"{v}%" if v is not None else "-"
        print(f"Battery L/R/Case:   {pct(status.audio.battery_left)} / "
              f"{pct(status.audio.battery_right)} / {pct(status.audio.battery_case)}{charge_str}")
    else:
        print(f"Battery Level:      {status.audio.battery_level}%{charge_str}")

    print("\n--- Noise Cancellation ---")
    print(f"Current Mode:       {format_value(status.nc.nc_mode)}")
    print(f"Mic Muted:          {format_value(status.nc.mic_muted)}")

    print("\n--- System ---")
    print(f"Auto Power Off:     {status.system.auto_off_minutes} min")
    print(f"Notifications:      {format_value(status.system.notif_enabled)}")
    print(f"Language:           {format_value(status.system.language)}")
    print(f"Mic Connected:      {format_value(status.system.mic_connected)}")
    print(f"Bluetooth Conn:     {format_value(status.system.bt_state.connected)}")
    print(f"Boot Default (NC):  {format_value(status.system.boot_nc)}")
    print(f"Boot Default (BT):  {format_value(status.system.boot_bt)}")


def monitor_device(info: DeviceInfo, prefix: bool) -> None:
    label = f"[{info.name}] " if prefix else ""
    try:
        with ZoneHeadset(info.vendor_id, info.product_id) as headset:
            for event in headset.listen():
                if event is None:
                    continue
                print(f"{label}Event: {event.type.value} -> {format_value(event.value)}")
    except Exception as e:
        print(f"{label}Error: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZoneOut: Controller for Sony INZONE Headsets",
        epilog=VARIABLE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--get-all', action='store_true', help="Read and print all device settings.")
    group.add_argument('--get', metavar='VAR', choices=VAR_MAP.keys(), help="Get a specific setting value.")
    group.add_argument('--set', nargs=2, action='append', metavar=('VAR', 'VAL'), help="Set a variable (see list below).")
    group.add_argument('--monitor', action='store_true', help="Listen for events in real-time.")
    group.add_argument('--list-devices', action='store_true', help="List connected supported devices.")
    parser.add_argument('--device', metavar='MODEL', help="Target a specific model (e.g. 'h9', 'buds'). Default: all connected devices (--set requires it when several are connected).")

    args = parser.parse_args()

    if args.list_devices:
        devices = find_devices()
        if not devices:
            print("No supported devices connected.")
            sys.exit(1)
        for dev in devices:
            print(f"{dev.name}  ({dev.vendor_id:04x}:{dev.product_id:04x})")
        return

    try:
        targets = get_targets(args.device)
        multi = len(targets) > 1

        if args.get_all:
            for i, info in enumerate(targets):
                if i:
                    print("\n" + "=" * 40 + "\n")
                with ZoneHeadset(info.vendor_id, info.product_id) as headset:
                    print_status(headset)

        elif args.get:
            cat_attr, field_name, _ = VAR_MAP[args.get]
            for info in targets:
                with ZoneHeadset(info.vendor_id, info.product_id) as headset:
                    fetch = {
                        'audio': headset.get_audio_status,
                        'nc': headset.get_nc_status,
                        'system': headset.get_system_status,
                    }[cat_attr]
                    val = getattr(fetch(), field_name)
                    raw = val.value if hasattr(val, 'value') else int(val)
                    print(f"{info.name}: {raw}" if multi else raw)

        elif args.set:
            if multi:
                names = ", ".join(f"'{t.name}'" for t in targets)
                print(f"Error: Multiple devices connected ({names}). Use --device to select one.")
                sys.exit(1)

            info = targets[0]
            with ZoneHeadset(info.vendor_id, info.product_id) as headset:
                for var_name, val_str in args.set:
                    if var_name not in VAR_MAP:
                        print(f"Error: Unknown variable '{var_name}'")
                        sys.exit(1)

                    _, _, setter_name = VAR_MAP[var_name]
                    if setter_name is None:
                        print(f"Error: Variable '{var_name}' is read-only.")
                        sys.exit(1)

                    if val_str.lower() in ['on', 'true']: val_str = '1'
                    if val_str.lower() in ['off', 'false']: val_str = '0'

                    try:
                        value = int(val_str)
                    except ValueError:
                        print(f"Error: Value for '{var_name}' must be an integer.")
                        sys.exit(1)

                    getattr(headset, setter_name)(value)
                    print(f"Set {var_name} -> {value}")

        elif args.monitor:
            print("Listening for headset events (Ctrl+C to stop)...")
            threads = [
                threading.Thread(target=monitor_device, args=(info, multi), daemon=True)
                for info in targets
            ]
            for t in threads:
                t.start()
            try:
                while any(t.is_alive() for t in threads):
                    time.sleep(0.2)
            except KeyboardInterrupt:
                print("\nStopped.")

    except DeviceNotFoundError as e:
        print(f"Error: {e}")
        if e.__cause__:
            print(f"Details: {e.__cause__}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
