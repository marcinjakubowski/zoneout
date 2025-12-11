import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    clip: true
    contentWidth: parent.width

    ColumnLayout {
        width: parent.width
        spacing: 20
        anchors.margins: 20
        
        GroupBox {
            title: "Notifications"
            Layout.fillWidth: true
            Layout.margins: 10
            
            ColumnLayout {
                spacing: 20
                width: parent.width

                GridLayout {
                    columns: 2
                    
                    CheckBox {
                        text: "Microphone Connect/Disconnect"
                        checked: headset.notifyOnMicConnect
                        onToggled: headset.setNotifyOnMicConnect(checked)
                    }

                    CheckBox {
                        text: "Microphone Mute/Unmute"
                        checked: headset.notifyOnMicMute
                        onToggled: headset.setNotifyOnMicMute(checked)
                    }
                    
                    CheckBox {
                        text: "Bluetooth Connect/Disconnect"
                        checked: headset.notifyOnBtConnect
                        onToggled: headset.setNotifyOnBtConnect(checked)
                    }
                    
                    CheckBox {
                        text: "Bluetooth Enable/Disable"
                        checked: headset.notifyOnBtToggle
                        onToggled: headset.setNotifyOnBtToggle(checked)
                    }
                    
                    CheckBox {
                        text: "Charging Status"
                        checked: headset.notifyOnCharging
                        onToggled: headset.setNotifyOnCharging(checked)
                    }
                    
                    CheckBox {
                        text: "Noise Control Changes"
                        checked: headset.notifyOnNc
                        onToggled: headset.setNotifyOnNc(checked)
                    }
                }
                
                // Battery Notification Settings
                GridLayout {
                    columns: 2
                    
                    CheckBox {
                        text: "Low Battery Warning"
                        checked: headset.notifyOnBattery
                        onToggled: headset.setNotifyOnBattery(checked)
                        Layout.columnSpan: 2
                    }
                    
                    Label { 
                        text: "Threshold (%)" 
                        Layout.leftMargin: 28
                        opacity: headset.notifyOnBattery ? 1.0 : 0.5
                    }
                    RowLayout {
                        opacity: headset.notifyOnBattery ? 1.0 : 0.5
                        Slider {
                            id: battSlider
                            from: 5
                            to: 50
                            stepSize: 5
                            value: headset.batteryThreshold
                            onMoved: headset.setBatteryThreshold(value)
                        }
                        Label { text: battSlider.value + "%" }
                    }
                }

                Button {
                    text: "Test Notification"
                    onClicked: headset.testNotification()
                    Layout.topMargin: 20
                    Layout.alignment: Qt.AlignLeft
                }
            }
        }
    }
}
