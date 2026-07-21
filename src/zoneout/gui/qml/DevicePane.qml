import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var headset

    // Receiver enumerated but couldn't be opened (permissions/udev) vs.
    // receiver open but no headset linked to it wirelessly.
    readonly property bool receiverError: !headset.usbConnected
    readonly property bool linked: headset.usbConnected && headset.headsetConnected

    readonly property string statusText: receiverError
        ? "Receiver error — check permissions, retrying…"
        : (linked ? "Connected" : "Not connected — headset is off or out of range")

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 10
            spacing: 8

            Rectangle {
                width: 12
                height: 12
                radius: 6
                Layout.alignment: Qt.AlignVCenter
                color: pane.receiverError ? "#c62828"
                     : (pane.linked ? "#43a047" : "#1a1a1a")
                border.width: 1
                border.color: pane.linked ? "#2e7d32" : "#808080"

                ToolTip.visible: dotHover.hovered
                ToolTip.text: pane.statusText
                HoverHandler { id: dotHover }
            }

            Label {
                text: pane.headset.deviceName
                font.pixelSize: 18
                font.bold: true
            }
        }

        Label {
            text: pane.statusText
            visible: !pane.linked
            opacity: 0.65
            font.pixelSize: 12
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 2
        }

        Button {
            text: "Retry Now"
            visible: pane.receiverError
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 4
            onClicked: pane.headset.retryConnection()
        }

        TabBar {
            id: bar
            Layout.fillWidth: true
            Layout.topMargin: 6

            TabButton {
                text: "Controls"
                font.pixelSize: 16
                font.bold: true
                height: 50
            }
            TabButton {
                text: "Advanced"
                font.pixelSize: 16
                font.bold: true
                height: 50
            }
            TabButton {
                text: "Notifications"
                font.pixelSize: 16
                font.bold: true
                height: 50
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex

            // Device-bound tabs are inert without a linked headset;
            // notification preferences are local and always editable.
            ControlsTab { headset: pane.headset; enabled: pane.linked }
            AdvancedTab { headset: pane.headset; enabled: pane.linked }
            NotificationsTab { headset: pane.headset }
        }

        Item {
            Layout.fillWidth: true
            height: 40

            Label {
                anchors.centerIn: parent
                property bool triBattery: pane.headset.batteryLeft >= 0 || pane.headset.batteryRight >= 0 || pane.headset.batteryCase >= 0
                function pct(v) { return v >= 0 ? v + "%" : "—" }
                text: (triBattery
                       ? "L: " + pct(pane.headset.batteryLeft) + "  R: " + pct(pane.headset.batteryRight) + "  Case: " + pct(pane.headset.batteryCase)
                       : "Battery: " + pct(pane.headset.batteryLevel))
                      + (pane.headset.isCharging ? " (Charging)" : "")
                font.bold: true
            }
        }
    }
}
