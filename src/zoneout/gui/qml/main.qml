import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: !startHidden

    property int paneCount: deviceManager.controllers.length
    property int paneWidth: 530

    width: Math.max(1, paneCount) * paneWidth
    height: 680
    minimumWidth: Math.max(1, paneCount) * paneWidth
    minimumHeight: 680

    title: "ZoneOut"

    onClosing: (close) => {
        close.accepted = false
        window.hide()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: window.paneCount > 0

        Repeater {
            model: deviceManager.controllers

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                // Separator between panes
                Rectangle {
                    visible: index > 0
                    width: 1
                    Layout.fillHeight: true
                    color: palette.mid
                }

                DevicePane {
                    headset: modelData
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                }
            }
        }
    }

    // No supported receivers found
    Rectangle {
        anchors.fill: parent
        color: "#e6000000"
        visible: window.paneCount === 0

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 10

            Label {
                text: "No Devices Found"
                color: "white"
                font.pixelSize: 20
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Label {
                text: "Connect a supported INZONE USB receiver.\nScanning..."
                color: "lightgray"
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }

            Button {
                text: "Scan Now"
                Layout.alignment: Qt.AlignHCenter
                onClicked: deviceManager.rescan()
            }
        }
    }
}
