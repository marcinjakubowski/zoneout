import sys
import signal
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtGui import QIcon

from zoneout.gui.controller import HeadsetController


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setApplicationName("ZoneOut")
    app.setOrganizationName("ZoneOut")
    app.setOrganizationDomain("zoneout.local")
    
    app.setQuitOnLastWindowClosed(False)

    tray_icon = QSystemTrayIcon(app)
    
    icon_path = Path(__file__).parent / "resources" / "zoneout.png"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
    elif QIcon.hasThemeIcon("audio-headset"):
        icon = QIcon.fromTheme("audio-headset")
    else:
        icon = QIcon.fromTheme("audio-card")
        
    tray_icon.setIcon(icon)
    tray_icon.setToolTip("ZoneOut Controller")
    
    tray_menu = QMenu()
    
    vol_action = tray_menu.addAction("Volume: ...")
    vol_action.setEnabled(False)
    bal_action = tray_menu.addAction("Balance: ...")
    bal_action.setEnabled(False)
    nc_action = tray_menu.addAction("NC Mode: ...")
    nc_action.setEnabled(False)
    mic_action = tray_menu.addAction("Mic: ...")
    mic_action.setEnabled(False)
    bt_action = tray_menu.addAction("Bluetooth: ...")
    bt_action.setEnabled(False)
    
    tray_menu.addSeparator()
    
    show_action = tray_menu.addAction("Show")
    quit_action = tray_menu.addAction("Quit")
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    engine = QQmlApplicationEngine()
    
    controller = HeadsetController()
    
    engine.rootContext().setContextProperty("headset", controller)
    
    qml_file = Path(__file__).parent / "qml" / "main.qml"
    
    if not qml_file.exists():
        print(f"Error: QML file not found at {qml_file}")
        sys.exit(1)
        
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    window = engine.rootObjects()[0]
    window.setIcon(icon)
    
    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()
        
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if window.isVisible():
                window.hide()
            else:
                show_window()
            
    tray_icon.activated.connect(on_tray_activated)
    show_action.triggered.connect(show_window)
    quit_action.triggered.connect(app.quit)
    
    def on_notification_requested(title, message):
        tray_icon.showMessage(title, message, icon, 3000)
        
    controller.notificationRequested.connect(on_notification_requested)

    def update_tray_tooltip(*args):
        if not controller.usbConnected:
            tray_icon.setToolTip("ZoneOut\n\nDisconnected")
            vol_action.setText("Disconnected")
            bal_action.setVisible(False)
            nc_action.setVisible(False)
            mic_action.setVisible(False)
            bt_action.setVisible(False)
            return
        
        bal_action.setVisible(True)
        nc_action.setVisible(True)
        mic_action.setVisible(True)
        bt_action.setVisible(True)

        nc_modes = {0: "Off", 1: "Noise Cancelling", 2: "Ambient Sound"}
        nc_mode_str = nc_modes.get(controller.ncMode, "Unknown")

        if not controller.micConnected:
            mic_status = "Disconnected"
        else:
            mic_status = "Muted" if controller.micMuted else "Active"

        if not controller.bluetoothEnabled:
            bt_status = "Disabled"
        elif controller.bluetoothConnected:
            bt_status = "Connected"
        else:
            bt_status = "Enabled"
            
        bal = controller.balance
        if bal == 0:
            bal_str = "Game 100%"
        elif bal == 100:
            bal_str = "100% Chat"
        else:
            bal_str = f"Game {100 - bal}%/{bal}% Chat"

        tooltip = (
            f"ZoneOut\n\n"
            f"Volume: {controller.volume}\n"
            f"Balance: {bal_str}\n"
            f"Noise control mode: {nc_mode_str}\n"
            f"Microphone status: {mic_status}\n"
            f"Bluetooth status: {bt_status}"
        )
        tray_icon.setToolTip(tooltip)
        
        vol_action.setText(f"Volume: {controller.volume}")
        bal_action.setText(f"Balance: {bal_str}")
        nc_action.setText(f"Noise Control: {nc_mode_str}")
        mic_action.setText(f"Mic: {mic_status}")
        bt_action.setText(f"Bluetooth: {bt_status}")

    controller.volumeChanged.connect(update_tray_tooltip)
    controller.balanceChanged.connect(update_tray_tooltip)
    controller.ncModeChanged.connect(update_tray_tooltip)
    controller.micMutedChanged.connect(update_tray_tooltip)
    controller.micConnectedChanged.connect(update_tray_tooltip)
    controller.bluetoothConnectedChanged.connect(update_tray_tooltip)
    controller.bluetoothEnabledChanged.connect(update_tray_tooltip)
    controller.usbConnectedChanged.connect(update_tray_tooltip)
    
    update_tray_tooltip()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
