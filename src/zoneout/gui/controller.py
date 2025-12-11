import time
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, QThread, pyqtSlot, QTimer, QSettings

from zoneout.device import ZoneHeadset
from zoneout.models import (
    NcMode, BootNcMode, BootBtMode, Language, HeadsetEvent, EventType,
    PowerState, BluetoothState
)
from zoneout.exceptions import DeviceNotFoundError


class MonitorThread(QThread):
    event_received = pyqtSignal(object)  
    connection_lost = pyqtSignal(str)

    def __init__(self, headset: ZoneHeadset):
        super().__init__()
        self.headset = headset
        self._running = True

    def run(self):
        while self._running:
            try:
                for event in self.headset.listen():
                    if not self._running:
                        break
                    self.event_received.emit(event)
            except DeviceNotFoundError:
                self.connection_lost.emit("Device disconnected")
                break
            except Exception as e:
                self.connection_lost.emit(str(e))
                break
            
            time.sleep(1)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()

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
    isChargingChanged = pyqtSignal(bool)
    micMutedChanged = pyqtSignal(bool)
    micConnectedChanged = pyqtSignal(bool)
    bluetoothConnectedChanged = pyqtSignal(bool)
    bluetoothEnabledChanged = pyqtSignal(bool)
    
    notificationRequested = pyqtSignal(str, str)
    
    connectionStatusChanged = pyqtSignal(bool, str)
    usbConnectedChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
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
        self._is_charging = False
        self._mic_muted = False
        self._mic_connected = True
        self._bt_connected = False
        self._bt_enabled = False

        self._usb_connected = False
        
        self._settings = QSettings("ZoneOut", "HeadsetSettings")
        
        self._low_battery_notified = False
        self._user_battery_threshold = int(self._settings.value("notifications/batteryThreshold", 20))
        
        self._notify_mic_mute = self._settings.value("notifications/micMute", True, type=bool)
        self._notify_mic_connect = self._settings.value("notifications/micConnect", True, type=bool)
        self._notify_bt_connect = self._settings.value("notifications/btConnect", True, type=bool)
        self._notify_bt_toggle = self._settings.value("notifications/btToggle", True, type=bool)
        self._notify_battery = self._settings.value("notifications/battery", True, type=bool)
        self._notify_charging = self._settings.value("notifications/charging", True, type=bool)
        self._notify_nc = self._settings.value("notifications/nc", True, type=bool)
        
        QTimer.singleShot(0, self.connect_device)

    def connect_device(self):
        try:
            self._headset = ZoneHeadset()
            self._headset.connect()
            
            if self._retry_timer.isActive():
                self._retry_timer.stop()
                
            self._usb_connected = True
            self.usbConnectedChanged.emit(True)
            self.connectionStatusChanged.emit(True, "Connected")
            self.refresh_all()
            self.start_monitor()
        except Exception as e:
            self._usb_connected = False
            self.usbConnectedChanged.emit(False)
            self.connectionStatusChanged.emit(False, str(e))
            
            if not self._retry_timer.isActive():
                self._retry_timer.start()

    def refresh_all(self):
        if not self._headset:
            return
            
        status = self._headset.get_all_data()
        
        self._update_volume(status.audio.volume)
        self._update_balance(status.audio.balance)
        self._update_sidetone(status.audio.sidetone)
        self._update_battery(status.audio.battery_level, status.audio.charging)
        
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
            self._monitor_thread.start()

    def _handle_disconnect(self, msg):
        self._usb_connected = False
        self.usbConnectedChanged.emit(False)
        self.connectionStatusChanged.emit(False, msg)
        self._headset = None
        self._low_battery_notified = False
        
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
            
            if self._notify_battery and not charging and level <= self._user_battery_threshold and not self._low_battery_notified:
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
        self._settings.setValue("notifications/batteryThreshold", val)
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
        self._settings.setValue("notifications/micMute", val)
        self.notifyMicMuteChanged.emit(val)

    @pyqtProperty(bool, notify=notifyMicConnectChanged)
    def notifyOnMicConnect(self): return self._notify_mic_connect

    @pyqtSlot(bool)
    def setNotifyOnMicConnect(self, val):
        self._notify_mic_connect = val
        self._settings.setValue("notifications/micConnect", val)
        self.notifyMicConnectChanged.emit(val)

    @pyqtProperty(bool, notify=notifyBtConnectChanged)
    def notifyOnBtConnect(self): return self._notify_bt_connect

    @pyqtSlot(bool)
    def setNotifyOnBtConnect(self, val):
        self._notify_bt_connect = val
        self._settings.setValue("notifications/btConnect", val)
        self.notifyBtConnectChanged.emit(val)
        
    @pyqtProperty(bool, notify=notifyBtToggleChanged)
    def notifyOnBtToggle(self): return self._notify_bt_toggle

    @pyqtSlot(bool)
    def setNotifyOnBtToggle(self, val):
        self._notify_bt_toggle = val
        self._settings.setValue("notifications/btToggle", val)
        self.notifyBtToggleChanged.emit(val)

    notifyBatteryChanged = pyqtSignal(bool)
    notifyChargingChanged = pyqtSignal(bool)

    @pyqtProperty(bool, notify=notifyBatteryChanged)
    def notifyOnBattery(self): return self._notify_battery

    @pyqtSlot(bool)
    def setNotifyOnBattery(self, val):
        self._notify_battery = val
        self._settings.setValue("notifications/battery", val)
        self.notifyBatteryChanged.emit(val)

    @pyqtProperty(bool, notify=notifyChargingChanged)
    def notifyOnCharging(self): return self._notify_charging

    @pyqtSlot(bool)
    def setNotifyOnCharging(self, val):
        self._notify_charging = val
        self._settings.setValue("notifications/charging", val)
        self.notifyChargingChanged.emit(val)

    notifyNcChanged = pyqtSignal(bool)

    @pyqtProperty(bool, notify=notifyNcChanged)
    def notifyOnNc(self): return self._notify_nc

    @pyqtSlot(bool)
    def setNotifyOnNc(self, val):
        self._notify_nc = val
        self._settings.setValue("notifications/nc", val)
        self.notifyNcChanged.emit(val)

    @pyqtSlot()
    def testNotification(self):
        self.notificationRequested.emit("Test Notification", "This is a test notification from ZoneOut.")

    @pyqtProperty(bool, notify=usbConnectedChanged)
    def usbConnected(self): return self._usb_connected
