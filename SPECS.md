# Sony INZONE H9 II - USB HID Protocol Specifications

This document details the reverse-engineered USB HID protocol for the **Sony INZONE H9 II** (Vendor ID `0x054c`, Product ID `0x0fa8`). This information is intended for developers wishing to implement driver support on other platforms.

## Protocol Overview

The headset communicates via **USB HID Feature Reports** using 64-byte packets.

* **Interface:** HID (Generic)
* **Report ID:** `0x02`
* **Packet Size:** 64 Bytes

### Common Packet Structure

All packets (Read Requests and Write Commands) share a 10-byte header structure.

`02 [TYPE] 01 00 fc [SUB] 96 c3 [CAT] [CMD] [MODE] ...`

* **Byte 0:** `0x02` (Report ID)
* **Byte 1:** `TYPE` (Packet Length/Type descriptor)
* **Byte 5:** `SUB` (Calculated as `TYPE - 0x04`)
* **Byte 6-7:** `0x96 0xC3` (Sony Magic Bytes)
* **Byte 8:** `CAT` (Category/Page ID)
* **Byte 9:** `CMD` (Command ID)
* **Byte 10:** `MODE` (Operation Mode: `0x01` = Read/Static, `0x02` = Write/Sequenced, `0xA0` = Event)

## Read Protocol (Status)

To read the device state, the host sends a `SET_REPORT` packet with Mode `0x01`. The device replies with a 64-byte `GET_REPORT` response containing the requested data.

* **Type:** `0x0C`
* **Mode:** `0x01`

### Initialization Requests
The official driver sends 8 distinct requests during startup.

| Request | CAT | CMD | Description |
| :--- | :--- | :--- | :--- |
| **Req 1** | `0x21` | `0x01` | Undeciphered |
| **Req 2** | `0x41` | `0x02` | **Device Info** (Serial Number in ASCII) |
| **Req 3** | `0x41` | `0x04` | **Power Status** (Charging, Battery) |
| **Req 4** | `0x21` | `0x09` | Undeciphered |
| **Req 5** | `0x41` | `0x03` | Undeciphered |
| **Req 6** | `0x41` | `0x06` | **Audio Status** (Volume, Balance, Sidetone, Battery) |
| **Req 7** | `0x41` | `0x07` | **NC Status** (Mode, Mic Mute) |
| **Req 8** | `0x41` | `0x08` | **System Status** (Power/BT Defaults, Timers) |

### Response Decoding

#### Request 3 (Power Status)
* **Byte 13:** Charging Status (`1`=Charging, `0`=Discharging)
* **Byte 14:** Battery Level (0-100)
* **Byte 15:** Internal Offset (Ignore: value varies by state)

#### Request 6 (Audio Status)
* **Byte 14:** **Charging Status** (`1`=Charging, `0`=Not Charging)
* **Byte 15:** Battery Level (0-100)
* **Byte 17:** Volume (0-30)
* **Byte 19:** Game/Chat Balance (0-100)
* **Byte 20:** Sidetone Level (0-10)
* **Byte 22:** **State Checksum** (Composite of Vol, Bal, Bat). *Previously misidentified as Chat Mix Gain.*

#### Request 7 (NC Status)
* **Byte 13:** Mic Mute Status (`1`=Muted, `0`=Unmuted). *Note: Always `1` if Mic Disconnected.*
* **Byte 16:** Noise Cancellation Mode (`0`=Off, `1`=NC, `2`=Ambient)
* **Byte 17:** Ambient Sound Level (0-20)
* **Byte 19:** Focus on Voice (0/1)

#### Request 8 (System Status)
* **Byte 13:** NC Default on Boot (`0`=Off, `1`=NC, `2`=Amb, `3`=Remember)
* **Byte 14:** Bluetooth Enabled (`0`=Off, `1`=On)
* **Byte 15:** Bluetooth Connection (`0`=No, `1`=Yes, `3`=N/A)
* **Byte 17:** BT Default on Boot (`0`=Off, `1`=On, `2`=Remember)
* **Byte 18:** Auto Power Off Timer (Minutes)
* **Byte 21:** Voice Guide Language (`0`=English, `1`=Japanese, `2`=Chinese)
* **Byte 22:** Notification/Voice Guide (`1`=On, `2`=Off)
* **Byte 24:** Mic Physical Connection (`0`=Connected, `1`=Disconnected)

## Write Protocol (Control)

To change settings, a packet is sent via `SET_REPORT` with Mode `0x02`. These packets include a sequence counter and a rolling checksum.

* **CAT:** `0x41` (All known writes use this category)
* **Mode:** `0x02`

### Checksum Algorithm
```python
checksum = (Sequence + Value + Constant) % 256
```

### Command Table

| Feature | Type | Cmd | Val Offset | Chk Offset | Constant | Spacers/Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Noise Cancelling** | `0x10` | `0x41` | 13 | 17 | `0xF0` | Byte 14=`0x14`, 15=`0xFF` |
| **Volume** | `0x0F` | `0x21` | 14 | 16 | `0xBC` | Byte 15=`0xFF` |
| **Game/Chat Balance** | `0x0D` | `0x22` | 13 | 14 | `0xBE` | |
| **Sidetone** | `0x0E` | `0x23` | 13 | 15 | `0xBE` | Byte 14=`0xFF` |
| **Auto Power Off** | `0x0E` | `0x81` | 13 | 15 | `0x22` | Byte 14=`0x05` |
| **Notif. & Voice** | `0x0D` | `0x84` | 13 | 14 | `0x20` | |
| **Language** | `0x0D` | `0x83` | 13 | 14 | `0x1F` | |
| **NC Default (Boot)** | `0x0D` | `0x43` | 13 | 14 | `0xDF` | |
| **BT Default (Boot)** | `0x0D` | `0x63` | 13 | 14 | `0xFF` | |
| **Ambient Sound** | `0x10` | `0x41` | Mixed | 17 | `0xDC` | Special Checksum: `(Seq+Mode(2)+Lvl+Focus+0xDC)&0xFF`. Byte 13=`0x02`, 14=Lvl(0-20), 15=`0xFF`, 16=Focus(0/1) |

## Asynchronous Event Protocol

The headset sends unsolicited packets when physical controls are used OR periodically while charging.

### Event Header Structure
`02 [TYPE] 04 FF [SUB] 00 96 C3 14 [CMD] A0 ...`

* **Byte 2:** `0x04` (Event Indicator)
* **Byte 8:** `0x14` (Event Category)
* **Byte 9:** `CMD` (Event Type)
* **Byte 10:** `0xA0` (Event Mode)

### Event Table

| CMD | Description | Payload | Notes |
| :--- | :--- | :--- | :--- |
| `0x04` | **Power State** | Byte 13: Charging (`0`/`1`), Byte 14: Level (`0`-`100`) | Sends every ~60s while charging. |
| `0x21` | **Volume Changed** | Byte 14: New Volume (0-30) | |
| `0x22` | **Balance Changed** | Byte 13: New Balance (0-100) | |
| `0x41` | **NC Mode Changed** | Byte 13: New Mode (0/1/2) | |
| `0x24` | **Mic Mute State** | Byte 13: `1`=Muted, `0`=Unmuted | |
| `0x8F` | **Mic Connection** | Byte 13: `0`=Connected, `1`=Disconnected | |
| `0x61` | **Bluetooth State** | Byte 13: Enabled (0/1), Byte 14: Connected (0/1) | |