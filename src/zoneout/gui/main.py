import sys
import signal
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtGui import QIcon

from zoneout.gui.controller import HeadsetController

def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setApplicationName("ZoneOut")
    app.setOrganizationName("ZoneOut")
    app.setOrganizationDomain("zoneout.local")
    
    # prevent window from closing the app, just hide it (if we want to minimize to tray)
    # But for now, let's keep standard behavior or just use tray for notifications/show/hide
    app.setQuitOnLastWindowClosed(False)

    # Setup System Tray
    tray_icon = QSystemTrayIcon(app)
    # Use standard icon or fallback
    if QIcon.hasThemeIcon("audio-headset"):
        icon = QIcon.fromTheme("audio-headset")
    else:
        # Fallback if no theme icon - potentially create a simple pixmap or expect one
        # For now, let's assume system theme or empty (which might not show)
        # PyQt usually needs an icon to show the tray
        icon = QIcon.fromTheme("audio-card") # another attempt
        
    tray_icon.setIcon(icon)
    tray_icon.setToolTip("ZoneOut Controller")
    
    tray_menu = QMenu()
    
    # Status Actions (Disabled to act as labels)
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
    
    # Initialize Controller
    controller = HeadsetController()
    
    # Expose to QML
    engine.rootContext().setContextProperty("headset", controller)
    
    # Load Main QML
    # Assuming qml/main.qml is relative to this file
    qml_file = Path(__file__).parent / "qml" / "main.qml"
    
    if not qml_file.exists():
        print(f"Error: QML file not found at {qml_file}")
        sys.exit(1)
        
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        sys.exit(-1)

    window = engine.rootObjects()[0]
    
    # Connect signals
    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()
        
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            show_window()
            
    tray_icon.activated.connect(on_tray_activated)
    show_action.triggered.connect(show_window)
    quit_action.triggered.connect(app.quit)
    
    # Handle window closing -> hide instead of quit if we want tray persistence
    # QML Window closing usually quits if quitOnLastWindowClosed is true.
    # We set it to False. But we need to handle the window close event to just hide.
    # Connecting to QQuickWindow closing signal is tricky from Py. 
    # Easiest is to let it close and show_window re-opens/creates it OR keeps it hidden.
    # But QML ApplicationWindow closing usually destroys it.
    # Let's override closing in QML or just allow quit for now on X click?
    # User requirement: "continuously monitor for events in the background"
    # So we should probably minimize to tray.
    
    def on_notification_requested(title, message):
        tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
        
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
        
        # Ensure visible
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
            
        # Balance formatting
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
        
        # Update Menu Actions
        vol_action.setText(f"Volume: {controller.volume}")
        bal_action.setText(f"Balance: {bal_str}")
        nc_action.setText(f"Noise Control: {nc_mode_str}")
        mic_action.setText(f"Mic: {mic_status}")
        bt_action.setText(f"Bluetooth: {bt_status}")

    # Connect signals to tooltip update
    controller.volumeChanged.connect(update_tray_tooltip)
    controller.balanceChanged.connect(update_tray_tooltip)
    controller.ncModeChanged.connect(update_tray_tooltip)
    controller.micMutedChanged.connect(update_tray_tooltip)
    controller.micConnectedChanged.connect(update_tray_tooltip)
    controller.bluetoothConnectedChanged.connect(update_tray_tooltip)
    controller.bluetoothEnabledChanged.connect(update_tray_tooltip)
    controller.usbConnectedChanged.connect(update_tray_tooltip)
    
    # Initial update
    update_tray_tooltip()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
