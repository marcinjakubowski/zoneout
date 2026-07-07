import argparse
import sys
import signal
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from zoneout.gui.controller import DeviceManager

NC_MODES = {0: "Off", 1: "Noise Cancelling", 2: "Ambient Sound"}

INSTANCE_SOCKET = "zoneout-gui"


def activate_running_instance() -> bool:
    """If another instance is running, ask it to show its window."""
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_SOCKET)
    if sock.waitForConnected(500):
        sock.write(b"show\n")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()
        return True
    return False


def battery_text(ctrl):
    def pct(v):
        return f"{v}%" if v >= 0 else "—"

    if ctrl.batteryLeft >= 0 or ctrl.batteryRight >= 0 or ctrl.batteryCase >= 0:
        text = (f"L {pct(ctrl.batteryLeft)} / R {pct(ctrl.batteryRight)}"
                f" / Case {pct(ctrl.batteryCase)}")
    else:
        text = pct(ctrl.batteryLevel)
    if ctrl.isCharging:
        text += " (Charging)"
    return text


def balance_text(ctrl):
    bal = ctrl.balance
    if bal == 0:
        return "Game 100%"
    if bal == 100:
        return "100% Chat"
    return f"Game {100 - bal}%/{bal}% Chat"


def device_section(ctrl):
    if not ctrl.usbConnected:
        return f"{ctrl.deviceName}\n  Disconnected"

    if not ctrl.micConnected:
        mic_status = "Disconnected"
    else:
        mic_status = "Muted" if ctrl.micMuted else "Active"

    if not ctrl.bluetoothEnabled:
        bt_status = "Disabled"
    elif ctrl.bluetoothConnected:
        bt_status = "Connected"
    else:
        bt_status = "Enabled"

    return (
        f"{ctrl.deviceName}\n"
        f"  Battery: {battery_text(ctrl)}\n"
        f"  Volume: {ctrl.volume}\n"
        f"  Balance: {balance_text(ctrl)}\n"
        f"  Noise control: {NC_MODES.get(ctrl.ncMode, 'Unknown')}\n"
        f"  Microphone: {mic_status}\n"
        f"  Bluetooth: {bt_status}"
    )


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = argparse.ArgumentParser(prog="zoneout-gui")
    parser.add_argument("--tray", action="store_true",
                        help="Start minimized to the system tray")
    args, qt_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + qt_args)
    app.setApplicationName("ZoneOut")
    app.setOrganizationName("ZoneOut")
    app.setOrganizationDomain("zoneout.local")

    app.setQuitOnLastWindowClosed(False)

    if activate_running_instance():
        print("ZoneOut is already running — asked it to show its window.")
        return

    QLocalServer.removeServer(INSTANCE_SOCKET)  # clean up stale socket
    instance_server = QLocalServer()
    instance_server.listen(INSTANCE_SOCKET)

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

    manager = DeviceManager()

    tray_menu = QMenu()
    device_actions = []
    show_action = tray_menu.addAction("Show")
    quit_action = tray_menu.addAction("Quit")
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("deviceManager", manager)
    engine.rootContext().setContextProperty("startHidden", args.tray)

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

    def on_instance_connection():
        while instance_server.hasPendingConnections():
            conn = instance_server.nextPendingConnection()
            conn.disconnected.connect(conn.deleteLater)
        show_window()

    instance_server.newConnection.connect(on_instance_connection)

    notification_icon = QIcon.fromTheme("zoneout")

    def on_notification_requested(title, message):
        tray_icon.showMessage(title, message, notification_icon, 3000)

    manager.notificationRequested.connect(on_notification_requested)

    def update_tray(*args):
        controllers = manager.controllers

        if not controllers:
            tray_icon.setToolTip("ZoneOut\n\nNo devices found")
        else:
            sections = "\n\n".join(device_section(c) for c in controllers)
            tray_icon.setToolTip(f"ZoneOut\n\n{sections}")

        for action in device_actions:
            tray_menu.removeAction(action)
        device_actions.clear()

        for ctrl in controllers:
            if ctrl.usbConnected:
                label = f"{ctrl.deviceName} — {battery_text(ctrl)}"
            else:
                label = f"{ctrl.deviceName} — Disconnected"
            action = QAction(label, tray_menu)
            action.setEnabled(False)
            tray_menu.insertAction(show_action, action)
            device_actions.append(action)

        if device_actions:
            sep = tray_menu.insertSeparator(show_action)
            device_actions.append(sep)

    wired = set()

    def wire_controllers():
        for ctrl in manager.controllers:
            if id(ctrl) in wired:
                continue
            wired.add(id(ctrl))
            for sig_name in (
                "volumeChanged", "balanceChanged", "ncModeChanged",
                "micMutedChanged", "micConnectedChanged",
                "bluetoothConnectedChanged", "bluetoothEnabledChanged",
                "usbConnectedChanged", "batteryLevelChanged",
                "batteryLeftChanged", "batteryRightChanged",
                "batteryCaseChanged", "isChargingChanged",
            ):
                getattr(ctrl, sig_name).connect(update_tray)
        update_tray()

    manager.controllersChanged.connect(wire_controllers)
    wire_controllers()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
