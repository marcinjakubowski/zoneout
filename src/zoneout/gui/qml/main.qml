import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 530
    height: 650
    minimumWidth: 530
    minimumHeight: 650
    title: headset.deviceName ? "ZoneOut — " + headset.deviceName : "ZoneOut"
    
    onClosing: (close) => {
        close.accepted = false
        window.hide()
    }

    ColumnLayout {
        anchors.fill: parent
        visible: headset.usbConnected // Hide entire UI (Tabs + Content + Status) when disconnected
        
        TabBar {
            id: bar
            width: parent.width
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
            width: parent.width
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex
            
            ControlsTab {
            }
            
            AdvancedTab {
            }
            
            NotificationsTab {
            }
        }
        
        Item { 
            Layout.fillWidth: true
            height: 40
            
            RowLayout {
                anchors.centerIn: parent
                spacing: 20

                ComboBox {
                    visible: headset.availableDevices.length > 1
                    model: headset.availableDevices
                    currentIndex: headset.currentDeviceIndex
                    onActivated: (index) => headset.selectDevice(index)
                    Layout.preferredWidth: 180
                }

                Label {
                    visible: headset.availableDevices.length <= 1
                    text: headset.deviceName
                    font.bold: true
                }

                Label {
                    property bool triBattery: headset.batteryLeft >= 0 || headset.batteryRight >= 0 || headset.batteryCase >= 0
                    function pct(v) { return v >= 0 ? v + "%" : "—" }
                    text: (triBattery
                           ? "L: " + pct(headset.batteryLeft) + "  R: " + pct(headset.batteryRight) + "  Case: " + pct(headset.batteryCase)
                           : "Battery: " + pct(headset.batteryLevel))
                          + (headset.isCharging ? " (Charging)" : "")
                    font.bold: true
                }
            }
        }
    }
    
    // Disconnected Overlay
    Rectangle {
        id: disconnectedOverlay
        anchors.fill: parent
        color: "#e6000000"
        visible: !headset.usbConnected
        
        property int retrySeconds: 5

        Timer {
            interval: 1000
            repeat: true
            running: parent.visible
            onTriggered: {
                if (disconnectedOverlay.retrySeconds > 1) {
                    disconnectedOverlay.retrySeconds -= 1
                } else {
                    disconnectedOverlay.retrySeconds = 5
                }
            }
            onRunningChanged: {
                if (running) {
                    disconnectedOverlay.retrySeconds = 5
                }
            }
        }
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 10
            
            Label {
                text: "Device Disconnected"
                color: "white"
                font.pixelSize: 20
                font.bold: true
            }
            
            Label {
                text: "Retrying in " + disconnectedOverlay.retrySeconds + " seconds..."
                color: "lightgray"
            }

            Button {
                text: "Retry Now"
                onClicked: {
                    headset.retryConnection()
                    disconnectedOverlay.retrySeconds = 5
                }
            }
        }
    }
}
