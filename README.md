# ZoneOut

**ZoneOut** is an open-source Linux CLI controller and Python library for **Sony INZONE™ H9 II** (and compatible) gaming headsets. 

It enables access to hardware features on Linux that are usually locked behind the Windows-only "INZONE Hub" software, such as Sidetone control, Chat/Game hardware mixing, and Auto-Power Off settings.

> **Note:** This project is not affiliated with, endorsed by, or connected to Sony Group Corporation. "Sony" and "INZONE" are registered trademarks of Sony Group Corporation.

## Features

* **Audio Control:** Adjust Hardware Game/Chat Balance and Sidetone (Mic Monitoring) level.
* **Monitoring:** Read **Battery Percentage** and Charging status.
* **Noise Control:** Switch between Noise Cancelling, Ambient Sound, and Off.
* **System Settings:** Configure Auto-Power Off timers, Voice Guide Language, and Notification sounds.
* **Boot Defaults:** Configure what the headset does (NC/Bluetooth) immediately upon powering on.
* **Scriptable:** CLI designed for easy integration with scripts, polybar, or keybindings.

## Installation

### Prerequisites (Arch Linux)
You need `hidapi` installed on your system.
```bash
sudo pacman -S hidapi python-setuptools
```

### Install Package
Clone the repository and install:
```bash
pip install .
```

### USB Permissions (udev)
By default, Linux requires root to access raw USB HID devices. To run `zoneout` as a standard user, create a udev rule.

1. Create `/etc/udev/rules.d/99-zoneout.rules`:
   ```bash
   SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0fa8", MODE="0666"
   ```
2. Reload rules and re-plug your headset transceiver:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

## Usage

The package installs the `zoneout` command.

### Reading Status

**Get all settings (Human Readable):**
```bash
zoneout --get-all
```

**Get a single raw value:**
Useful for scripts or status bars.
```bash
zoneout --get battery
# Output: 80
```

### Changing Settings

**Set Volume:**
```bash
zoneout --set volume 20
```

**Set Game/Chat Balance:**
0 is Max Game, 100 is Max Chat.
```bash
zoneout --set balance 100
```

**Configure Noise Cancelling & Sidetone:**
Set mode to Ambient (2) and Sidetone to Max (10).
```bash
zoneout --set nc_mode 2 --set sidetone 10
```

**Set Auto-Power Off:**
Set to 30 minutes.
```bash
zoneout --set auto_off 30
```

### Command Reference

| Variable | Values | Description |
| :--- | :--- | :--- |
| `volume` | 0-30 | Master Volume |
| `balance` | 0-100 | 0=Game, 50=Mix, 100=Chat |
| `sidetone` | 0-10 | Microphone monitoring level |
| `battery` | 0-100 | **Battery Percentage** (Read-only) |
| `nc_mode` | 0, 1, 2 | 0=Off, 1=NC, 2=Ambient |
| `auto_off` | 0, 5, 10... | Minutes (0=Disabled) |
| `language` | 0, 1, 2 | 0=Eng, 1=Jpn, 2=Chi |
| `notif` | 0, 1 | 1=On (Beeps/Voice enabled) |
| `boot_nc` | 0-3 | Default NC mode on boot |
| `boot_bt` | 0-2 | Default BT mode on boot |

## Technical Details

For details on the reverse-engineered USB HID protocol used by this device, please see [SPECS.md](SPECS.md).