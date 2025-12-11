import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 530
    height: 550
    minimumWidth: 530
    minimumHeight: 550
    title: "ZoneOut"
    
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
                
                Label {
                    text: "Battery: " + headset.batteryLevel + "%" + (headset.isCharging ? " (Charging)" : "")
                    font.bold: true
                }
            }
        }
    }
    
    // Disconnected Overlay
    Rectangle {
        anchors.fill: parent
        color: "#e6000000"
        visible: !headset.usbConnected
        
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
                text: "Retrying in 5 seconds..."
                color: "lightgray"
            }

            Button {
                text: "Retry Now"
                onClicked: headset.retryConnection()
            }
        }
    }
}
