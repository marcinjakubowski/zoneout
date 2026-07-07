import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: pane
    required property var headset

    ColumnLayout {
        anchors.fill: parent
        visible: pane.headset.usbConnected
        spacing: 0

        Label {
            text: pane.headset.deviceName
            font.pixelSize: 18
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 10
            Layout.bottomMargin: 6
        }

        TabBar {
            id: bar
            Layout.fillWidth: true

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

            ControlsTab { headset: pane.headset }
            AdvancedTab { headset: pane.headset }
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

    // Receiver present but headset connection failed (e.g. permissions)
    Rectangle {
        anchors.fill: parent
        color: "#e6000000"
        visible: !pane.headset.usbConnected

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 10

            Label {
                text: pane.headset.deviceName
                color: "white"
                font.pixelSize: 20
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: "Connecting..."
                color: "lightgray"
                Layout.alignment: Qt.AlignHCenter
            }

            Button {
                text: "Retry Now"
                Layout.alignment: Qt.AlignHCenter
                onClicked: pane.headset.retryConnection()
            }
        }
    }
}
