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
            title: "Power & System"
            Layout.fillWidth: true
            Layout.margins: 10
            
            GridLayout {
                columns: 2
                rowSpacing: 10
                columnSpacing: 20
                
                Label { text: "Auto Power Off (Minutes)" }
                ComboBox {
                    model: [0, 5, 10, 30, 60, 180]
                    currentIndex: model.indexOf(headset.autoPowerOff)
                    onActivated: (index) => headset.setAutoPowerOff(currentValue)
                    
                }
                
                Label { text: "Voice Language" }
                ComboBox {
                    model: ["English", "Japanese", "Chinese"]
                    currentIndex: headset.language
                    onActivated: (index) => headset.setLanguage(index)
                }
                
                Label { text: "Notification Sounds (Voice/Beep)" }
                Switch {
                    checked: headset.notificationSound
                    onToggled: headset.setNotificationSound(checked)
                }
            }
        }
        
        GroupBox {
            title: "Boot Defaults"
            Layout.fillWidth: true
            Layout.margins: 10
            
            ColumnLayout {
                width: parent.availableWidth
                
                Label { 
                    text: "These settings apply when the headset is turned on." 
                    font.italic: true
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
                
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    rowSpacing: 10
                    columnSpacing: 20
                    
                    Label { text: "Noise Control" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Off", "Noise Cancelling", "Ambient Sound", "Remember Last"]
                        currentIndex: headset.bootNcMode
                        onActivated: (index) => headset.setBootNcMode(index)
                    }
                    
                    Label { text: "Bluetooth" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Off", "On", "Remember Last"]
                        currentIndex: headset.bootBtMode
                        onActivated: (index) => headset.setBootBtMode(index)
                    }
                }
            }
        }
        
    }
}
