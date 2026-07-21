import time
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, QThread, pyqtSlot, QTimer, QSettings

from zoneout.device import ZoneHeadset, find_devices
from zoneout.models import (
    NcMode, BootNcMode, BootBtMode, Language, HeadsetEvent, EventType,
    PowerState, BluetoothState, DeviceInfo
)
from zoneout.exceptions import DeviceNotFoundError, ProtocolError


class MonitorThread(QThread):
    event_received = pyqtSignal(object)
    connection_lost = pyqtSignal(str)  # receiver itself gone (unplug/IO error)
    battery_polled = pyqtSignal(object)  # AudioStatus
    status_read = pyqtSignal(object)  # HeadsetFullStatus, on link (re)establish
    link_changed = pyqtSignal(bool)  # headset answering over the wireless link

    BATTERY_POLL_SECONDS = 10
    LINK_PROBE_SECONDS = 3

    def __init__(self, headset: ZoneHeadset):
        super().__init__()
        self.headset = headset
        self._running = True
        self._linked = None  # unknown until first probe

    def _set_linked(self, up: bool):
        if self._linked != up:
            self._linked = up
            self.link_changed.emit(up)

    def run(self):
        # The receiver stays enumerated on USB while the headset is powered
        # off, but stops answering status requests — a read timeout
        # (ProtocolError) therefore means "link down", not "receiver gone".
        while self._running:
            try:
                status = self.headset.get_all_data()
            except ProtocolError:
                self._set_linked(False)
                for _ in range(self.LINK_PROBE_SECONDS):
                    if not self._running:
                        return
                    time.sleep(1)
                continue
            except DeviceNotFoundError:
                if self._running:
                    self.connection_lost.emit("Device disconnected")
                return
            except Exception as e:
                if self._running:
                    self.connection_lost.emit(str(e))
                return

            self._set_linked(True)
            self.status_read.emit(status)

            last_poll = time.monotonic()
            try:
                for event in self.headset.listen():
                    if not self._running:
                        return
                    if event is None:
                        # Idle tick: refresh battery here (this thread owns
                        # device reads; the GUI thread must not interleave).
                        # The poll doubles as a link check.
                        if time.monotonic() - last_poll >= self.BATTERY_POLL_SECONDS:
                            try:
                                self.battery_polled.emit(self.headset.get_audio_status())
                            except ProtocolError:
                                break  # link dropped; back to probing
                            last_poll = time.monotonic()
                        continue
                    self.event_received.emit(event)
            except DeviceNotFoundError:
                if self._running:
                    self.connection_lost.emit("Device disconnected")
                return
            except Exception as e:
                if self._running:
                    self.connection_lost.emit(str(e))
                return

    def stop(self):
        self._running = False
        # listen() yields an idle tick at least once a second, so the loop
        # notices _running on its own; closing the device is the fallback.
        if not self.wait(2500):
            try:
                self.headset.close()
            except Exception:
                pass
            self.wait(2000)

class HeadsetController(QObject):
    volumeChanged = pyqtSignal(int)
    balanceChanged = pyqtSignal(int)
    sidetoneChanged = pyqtSignal(int)
    ncModeChanged = pyqtSignal(int)
    autoPowerOffChanged = pyqtSignal(int)
    notificationSoundChanged = pyqtSignal(bool)
    languageChanged = pyqtSignal(int)
    bootNcModeChanged = pyqtSignal(int)
    bootBtModeChanged = pyqtSignal(int)
    ambientLevelChanged = pyqtSignal(int)
    focusOnVoiceChanged = pyqtSignal(bool)
    
    batteryLevelChanged = pyqtSignal(int)
    batteryLeftChanged = pyqtSignal(int)
    batteryRightChanged = pyqtSignal(int)
    batteryCaseChanged = pyqtSignal(int)
    isChargingChanged = pyqtSignal(bool)
    micMutedChanged = pyqtSignal(bool)
    micConnectedChanged = pyqtSignal(bool)
    bluetoothConnectedChanged = pyqtSignal(bool)
    bluetoothEnabledChanged = pyqtSignal(bool)
    
    notificationRequested = pyqtSignal(str, str)
    
    connectionStatusChanged = pyqtSignal(bool, str)
    usbConnectedChanged = pyqtSignal(bool)
    headsetConnectedChanged = pyqtSignal(bool)

    def __init__(self, device_info: DeviceInfo, parent=None):
        super().__init__(parent)
        self._info = device_info
        self._headset: Optional[ZoneHeadset] = None
        self._monitor_thread: Optional[MonitorThread] = None

        self._retry_timer = QTimer(self)
        self._retry_timer.setInterval(5000)
        self._retry_timer.timeout.connect(self.connect_device)
        
        self._volume = 0
        self._balance = 50
        self._sidetone = 0
        self._nc_mode = 0
        self._auto_off = 0
        self._notif_sound = False
        self._language = 0
        self._boot_nc = 0
        self._boot_bt = 0
        self._ambient_level = 20
        self._focus_on_voice = False
        
        self._battery_level = -1
        self._battery_left = -1
        self._battery_right = -1
        self._battery_case = -1
        self._is_charging = False
        self._mic_muted = False
        self._mic_connected = True
        self._bt_connected = False
        self._bt_enabled = False

        self._usb_connected = False
        self._headset_connected = False

        self._settings = QSettings("ZoneOut", "HeadsetSettings")

        self._low_battery_notified = False
        self._user_battery_threshold = int(self._setting("notifications/batteryThreshold", 20))

        self._notify_mic_mute = self._setting("notifications/micMute", True, bool)
        self._notify_mic_connect = self._setting("notifications/micConnect", True, bool)
        self._notify_bt_connect = self._setting("notifications/btConnect", True, bool)
        self._notify_bt_toggle = self._setting("notifications/btToggle", True, bool)
        self._notify_battery = self._setting("notifications/battery", True, bool)
        self._notify_charging = self._setting("notifications/charging", True, bool)
        self._notify_nc = self._setting("notifications/nc", True, bool)

        QTimer.singleShot(0, self.connect_device)

    def _skey(self, key: str) -> str:
        return f"device_{self._info.product_id:04x}/{key}"

    def _setting(self, key, default, type_=None):
        # Per-device value, falling back to the pre-multi-device global key.
        legacy = self._settings.value(key, default, type=type_) if type_ \
            else self._settings.value(key, default)
        if type_:
            return self._settings.value(self._skey(key), legacy, type=type_)
        return self._settings.value(self._skey(key), legacy)

    def _save_setting(self, key, value):
        self._settings.setValue(self._skey(key), value)

    def shutdown(self):
        self._retry_timer.stop()
        if self._monitor_thread:
            self._monitor_thread.stop()
            self._monitor_thread = None
        if self._headset:
            try:
                self._headset.close()
            except Exception:
                pass
            self._headset = None

    def connect_device(self):
        # Opens the USB receiver only. Whether a headset is actually linked
        # to it wirelessly is discovered by MonitorThread (link_changed).
        try:
            self._headset = ZoneHeadset(
                vendor_id=self._info.vendor_id, product_id=self._info.product_id
            )
            self._headset.connect()

            if self._retry_timer.isActive():
                self._retry_timer.stop()

            self._usb_connected = True
            self.usbConnectedChanged.emit(True)
            self.connectionStatusChanged.emit(True, "Connected")
            self.start_monitor()
        except Exception as e:
            self._headset = None
            self._usb_connected = False
            self.usbConnectedChanged.emit(False)
            self.connectionStatusChanged.emit(False, str(e))

            if not self._retry_timer.isActive():
                self._retry_timer.start()

    def _handle_status_read(self, status):
        self._update_volume(status.audio.volume)
        self._update_balance(status.audio.balance)
        self._update_sidetone(status.audio.sidetone)
        self._update_battery(status.audio.battery_level, status.audio.charging)
        self._update_component_batteries(status.audio)
        
        self._update_nc_mode(status.nc.nc_mode)
        self._update_mic_mute(status.nc.mic_muted)
        self._update_ambient_level(status.nc.ambient_level)
        self._update_focus_on_voice(status.nc.focus_on_voice)
        
        self._update_auto_off(status.system.auto_off_minutes)
        self._update_language(status.system.language)
        self._update_notif_sound(status.system.notif_enabled)
        self._update_mic_conn(status.system.mic_connected)
        self._update_bt_state(status.system.bt_state)
        self._update_boot_nc(status.system.boot_nc)
        self._update_boot_bt(status.system.boot_bt)

    def start_monitor(self):
        if self._monitor_thread:
            self._monitor_thread.stop()
        
        if self._headset:
            self._monitor_thread = MonitorThread(self._headset)
            self._monitor_thread.event_received.connect(self._handle_event)
            self._monitor_thread.connection_lost.connect(self._handle_disconnect)
            self._monitor_thread.battery_polled.connect(self._handle_battery_polled)
            self._monitor_thread.status_read.connect(self._handle_status_read)
            self._monitor_thread.link_changed.connect(self._handle_link_changed)
            self._monitor_thread.start()

    def _handle_link_changed(self, up: bool):
        if self._headset_connected != up:
            self._headset_connected = up
            self.headsetConnectedChanged.emit(up)
        if not up:
            # Reset battery state directly — going through _update_battery
            # would emit "Charging stopped"/low-battery notifications.
            self._low_battery_notified = False
            if self._battery_level != -1:
                self._battery_level = -1
                self.batteryLevelChanged.emit(-1)
            if self._is_charging:
                self._is_charging = False
                self.isChargingChanged.emit(False)
            self._update_component_batteries(None)

    def _handle_battery_polled(self, audio):
        self._update_battery(audio.battery_level, audio.charging)
        self._update_component_batteries(audio)

    def _update_component_batteries(self, audio=None):
        for attr, signal, value in (
            ('_battery_left', self.batteryLeftChanged, getattr(audio, 'battery_left', None)),
            ('_battery_right', self.batteryRightChanged, getattr(audio, 'battery_right', None)),
            ('_battery_case', self.batteryCaseChanged, getattr(audio, 'battery_case', None)),
        ):
            val = -1 if value is None else int(value)
            if getattr(self, attr) != val:
                setattr(self, attr, val)
                signal.emit(val)

    def _handle_disconnect(self, msg):
        self._usb_connected = False
        self.usbConnectedChanged.emit(False)
        self.connectionStatusChanged.emit(False, msg)
        self._headset = None
        self._handle_link_changed(False)

        if not self._retry_timer.isActive():
            self._retry_timer.start()

    @pyqtSlot()
    def retryConnection(self):
        self.connect_device()

    def _handle_event(self, event: HeadsetEvent):
        if event.type == EventType.VOLUME:
            self._update_volume(event.value)
        elif event.type == EventType.BALANCE:
            self._update_balance(event.value)
        elif event.type == EventType.NC_MODE:
            if self._nc_mode != event.value:
                self._update_nc_mode(event.value)
                if self._notify_nc:
                    modes = {0: "Off", 1: "Noise Cancelling", 2: "Ambient Sound"}
                    mode_str = modes.get(event.value, "Unknown")
                    self.notificationRequested.emit("Noise Control", mode_str)
            else:
                 self._update_nc_mode(event.value)
        elif event.type == EventType.MIC_MUTE:
            if self._mic_muted != event.value:
                self._update_mic_mute(event.value)
                if self._notify_mic_mute:
                    self.notificationRequested.emit("Microphone", "Muted" if event.value else "Unmuted")
        elif event.type == EventType.MIC_CONN:
            if self._mic_connected != event.value:
                self._update_mic_conn(event.value)
                if self._notify_mic_connect:
                    self.notificationRequested.emit("Microphone", "Connected" if event.value else "Disconnected")
        elif event.type == EventType.POWER:
            self._update_battery(event.value.battery_level, event.value.charging)
        elif event.type == EventType.BLUETOOTH:
            conn_changed = (self._bt_connected != event.value.connected)
            enabled_changed = (self._bt_enabled != event.value.enabled)
            
            self._update_bt_state(event.value)
            
            if event.value.enabled:
                if self._notify_bt_connect and conn_changed:
                   status = "Connected" if event.value.connected else "Disconnected"
                   self.notificationRequested.emit("Bluetooth", status)
            else:
                if self._notify_bt_toggle and enabled_changed:
                   self.notificationRequested.emit("Bluetooth", "Disabled")

    def _update_volume(self, val):
        if self._volume != val:
            self._volume = val
            self.volumeChanged.emit(val)

    def _update_balance(self, val):
        if self._balance != val:
            self._balance = val
            self.balanceChanged.emit(val)

    def _update_sidetone(self, val):
        if self._sidetone != val:
            self._sidetone = val
            self.sidetoneChanged.emit(val)

    def _update_battery(self, level, charging):
        if self._battery_level != level:
            self._battery_level = level
            self.batteryLevelChanged.emit(level)
            
            if self._notify_battery and not charging and 0 <= level <= self._user_battery_threshold and not self._low_battery_notified:
                self.notificationRequested.emit("Low Battery", f"Battery is at {level}%")
                self._low_battery_notified = True
            elif level > self._user_battery_threshold:
                self._low_battery_notified = False 
                
        if self._is_charging != charging:
            self._is_charging = charging
            self.isChargingChanged.emit(charging)
            
            if self._notify_charging:
                status = "Charging started" if charging else "Charging stopped"
                self.notificationRequested.emit("Power", status)

    def _update_nc_mode(self, val):
        if self._nc_mode != val:
            self._nc_mode = int(val)
            self.ncModeChanged.emit(self._nc_mode)

    def _update_mic_mute(self, val):
        if self._mic_muted != val:
            self._mic_muted = val
            self.micMutedChanged.emit(val)

    def _update_ambient_level(self, val):
        if self._ambient_level != val:
            self._ambient_level = val
            self.ambientLevelChanged.emit(val)

    def _update_focus_on_voice(self, val):
        if self._focus_on_voice != val:
            self._focus_on_voice = val
            self.focusOnVoiceChanged.emit(val)

    def _update_auto_off(self, val):
        if self._auto_off != val:
            self._auto_off = val
            self.autoPowerOffChanged.emit(val)

    def _update_notif_sound(self, val):
        if self._notif_sound != val:
            self._notif_sound = val
            self.notificationSoundChanged.emit(val)

    def _update_language(self, val):
        if self._language != val:
            self._language = int(val)
            self.languageChanged.emit(self._language)

    def _update_mic_conn(self, val):
        if self._mic_connected != val:
            self._mic_connected = val
            self.micConnectedChanged.emit(val)

    def _update_bt_state(self, val: BluetoothState):
        if self._bt_connected != val.connected:
            self._bt_connected = val.connected
            self.bluetoothConnectedChanged.emit(val.connected)
        if self._bt_enabled != val.enabled:
            self._bt_enabled = val.enabled
            self.bluetoothEnabledChanged.emit(val.enabled)

    def _update_boot_nc(self, val):
        if self._boot_nc != val:
            self._boot_nc = int(val)
            self.bootNcModeChanged.emit(self._boot_nc)

    def _update_boot_bt(self, val):
        if self._boot_bt != val:
            self._boot_bt = int(val)
            self.bootBtModeChanged.emit(self._boot_bt)

    @pyqtProperty(int, notify=volumeChanged)
    def volume(self): return self._volume
    
    @pyqtSlot(int)
    def setVolume(self, val):
        if self._headset:
            self._headset.set_volume(val)
        
        self._update_volume(val)

    @pyqtProperty(int, notify=balanceChanged)
    def balance(self): return self._balance

    @pyqtSlot(int)
    def setBalance(self, val):
        if self._headset: self._headset.set_balance(val)
        self._update_balance(val)

    @pyqtProperty(int, notify=sidetoneChanged)
    def sidetone(self): return self._sidetone

    @pyqtSlot(int)
    def setSidetone(self, val):
        if self._headset: self._headset.set_sidetone(val)
        self._update_sidetone(val)

    @pyqtProperty(int, notify=ncModeChanged)
    def ncMode(self): return self._nc_mode

    @pyqtSlot(int)
    def setNcMode(self, val):
        if self._headset: 
            if val == 2:
                self._headset.set_ambient_sound(self._ambient_level, self._focus_on_voice)
            else:
                self._headset.set_noise_cancelling(val)
        
        self._update_nc_mode(val)

    @pyqtProperty(int, notify=ambientLevelChanged)
    def ambientLevel(self): return self._ambient_level

    @pyqtSlot(int)
    def setAmbientLevel(self, val):
        self._ambient_level = val
        self.ambientLevelChanged.emit(val)
        if self._headset:
            self._headset.set_ambient_sound(self._ambient_level, self._focus_on_voice)
            
            self._update_nc_mode(2)

    @pyqtProperty(bool, notify=focusOnVoiceChanged)
    def focusOnVoice(self): return self._focus_on_voice

    @pyqtSlot(bool)
    def setFocusOnVoice(self, val):
        self._focus_on_voice = val
        self.focusOnVoiceChanged.emit(val)
        if self._headset:
            self._headset.set_ambient_sound(self._ambient_level, self._focus_on_voice)
            
            self._update_nc_mode(2)

    @pyqtProperty(int, notify=autoPowerOffChanged)
    def autoPowerOff(self): return self._auto_off

    @pyqtSlot(int)
    def setAutoPowerOff(self, val):
        if self._headset: self._headset.set_auto_power_off(val)

    @pyqtProperty(bool, notify=notificationSoundChanged)
    def notificationSound(self): return self._notif_sound

    @pyqtSlot(bool)
    def setNotificationSound(self, val):
        if self._headset: self._headset.set_notification_voice(val)

    @pyqtProperty(int, notify=languageChanged)
    def language(self): return self._language

    @pyqtSlot(int)
    def setLanguage(self, val):
        if self._headset: self._headset.set_voice_language(val)

    @pyqtProperty(int, notify=bootNcModeChanged)
    def bootNcMode(self): return self._boot_nc

    @pyqtSlot(int)
    def setBootNcMode(self, val):
        if self._headset: self._headset.set_boot_nc_mode(val)

    @pyqtProperty(int, notify=bootBtModeChanged)
    def bootBtMode(self): return self._boot_bt

    @pyqtSlot(int)
    def setBootBtMode(self, val):
        if self._headset: self._headset.set_boot_bt_mode(val)
        
    @pyqtProperty(int, notify=batteryLevelChanged)
    def batteryLevel(self): return self._battery_level

    @pyqtProperty(int, notify=batteryLeftChanged)
    def batteryLeft(self): return self._battery_left

    @pyqtProperty(int, notify=batteryRightChanged)
    def batteryRight(self): return self._battery_right

    @pyqtProperty(int, notify=batteryCaseChanged)
    def batteryCase(self): return self._battery_case

    @pyqtProperty(bool, notify=isChargingChanged)
    def isCharging(self): return self._is_charging
    
    @pyqtProperty(bool, notify=micMutedChanged)
    def micMuted(self): return self._mic_muted
    
    @pyqtProperty(bool, notify=micConnectedChanged)
    def micConnected(self): return self._mic_connected
    
    @pyqtProperty(bool, notify=bluetoothConnectedChanged)
    def bluetoothConnected(self): return self._bt_connected
    
    @pyqtProperty(bool, notify=bluetoothEnabledChanged)
    def bluetoothEnabled(self): return self._bt_enabled

    batteryThresholdChanged = pyqtSignal(int)

    @pyqtProperty(int, notify=batteryThresholdChanged)
    def batteryThreshold(self): return self._user_battery_threshold

    @pyqtSlot(int)
    def setBatteryThreshold(self, val):
        self._user_battery_threshold = val
        self._save_setting("notifications/batteryThreshold", val)
        self.batteryThresholdChanged.emit(val)

    notifyMicMuteChanged = pyqtSignal(bool)
    notifyMicConnectChanged = pyqtSignal(bool)
    notifyBtConnectChanged = pyqtSignal(bool)
    notifyBtToggleChanged = pyqtSignal(bool) 

    @pyqtProperty(bool, notify=notifyMicMuteChanged)
    def notifyOnMicMute(self): return self._notify_mic_mute

    @pyqtSlot(bool)
    def setNotifyOnMicMute(self, val):
        self._notify_mic_mute = val
        self._save_setting("notifications/micMute", val)
        self.notifyMicMuteChanged.emit(val)

    @pyqtProperty(bool, notify=notifyMicConnectChanged)
    def notifyOnMicConnect(self): return self._notify_mic_connect

    @pyqtSlot(bool)
    def setNotifyOnMicConnect(self, val):
        self._notify_mic_connect = val
        self._save_setting("notifications/micConnect", val)
        self.notifyMicConnectChanged.emit(val)

    @pyqtProperty(bool, notify=notifyBtConnectChanged)
    def notifyOnBtConnect(self): return self._notify_bt_connect

    @pyqtSlot(bool)
    def setNotifyOnBtConnect(self, val):
        self._notify_bt_connect = val
        self._save_setting("notifications/btConnect", val)
        self.notifyBtConnectChanged.emit(val)
        
    @pyqtProperty(bool, notify=notifyBtToggleChanged)
    def notifyOnBtToggle(self): return self._notify_bt_toggle

    @pyqtSlot(bool)
    def setNotifyOnBtToggle(self, val):
        self._notify_bt_toggle = val
        self._save_setting("notifications/btToggle", val)
        self.notifyBtToggleChanged.emit(val)

    notifyBatteryChanged = pyqtSignal(bool)
    notifyChargingChanged = pyqtSignal(bool)

    @pyqtProperty(bool, notify=notifyBatteryChanged)
    def notifyOnBattery(self): return self._notify_battery

    @pyqtSlot(bool)
    def setNotifyOnBattery(self, val):
        self._notify_battery = val
        self._save_setting("notifications/battery", val)
        self.notifyBatteryChanged.emit(val)

    @pyqtProperty(bool, notify=notifyChargingChanged)
    def notifyOnCharging(self): return self._notify_charging

    @pyqtSlot(bool)
    def setNotifyOnCharging(self, val):
        self._notify_charging = val
        self._save_setting("notifications/charging", val)
        self.notifyChargingChanged.emit(val)

    notifyNcChanged = pyqtSignal(bool)

    @pyqtProperty(bool, notify=notifyNcChanged)
    def notifyOnNc(self): return self._notify_nc

    @pyqtSlot(bool)
    def setNotifyOnNc(self, val):
        self._notify_nc = val
        self._save_setting("notifications/nc", val)
        self.notifyNcChanged.emit(val)

    @pyqtSlot()
    def testNotification(self):
        self.notificationRequested.emit("Test Notification", "This is a test notification from ZoneOut.")

    @pyqtProperty(bool, notify=usbConnectedChanged)
    def usbConnected(self): return self._usb_connected

    @pyqtProperty(bool, notify=headsetConnectedChanged)
    def headsetConnected(self): return self._headset_connected

    @pyqtProperty(str, constant=True)
    def deviceName(self): return self._info.name


class DeviceManager(QObject):
    """Owns one HeadsetController per connected supported receiver."""

    controllersChanged = pyqtSignal()
    notificationRequested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controllers = {}  # (vid, pid) -> HeadsetController

        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(3000)
        self._scan_timer.timeout.connect(self.rescan)
        self._scan_timer.start()

        QTimer.singleShot(0, self.rescan)

    @pyqtSlot()
    def rescan(self):
        found = {(d.vendor_id, d.product_id): d for d in find_devices()}
        changed = False

        for key in list(self._controllers):
            if key not in found:
                ctrl = self._controllers.pop(key)
                ctrl.shutdown()
                ctrl.deleteLater()
                changed = True

        for key, info in found.items():
            if key not in self._controllers:
                ctrl = HeadsetController(info, self)
                ctrl.notificationRequested.connect(
                    lambda title, msg, name=info.name:
                        self.notificationRequested.emit(f"{name} — {title}", msg)
                )
                self._controllers[key] = ctrl
                changed = True

        if changed:
            self._controllers = dict(
                sorted(self._controllers.items(), key=lambda kv: kv[1].deviceName)
            )
            self.controllersChanged.emit()

    @pyqtProperty('QVariantList', notify=controllersChanged)
    def controllers(self):
        return list(self._controllers.values())
