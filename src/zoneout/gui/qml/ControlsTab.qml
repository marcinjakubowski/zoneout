import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    clip: true
    contentWidth: parent.width
    
    property var pendingCommand: null

    Timer {
        id: sharedTimer
        interval: 200
        repeat: false
        onTriggered: {
            if (pendingCommand) {
                pendingCommand()
                pendingCommand = null
            }
        }
    }
    
    ColumnLayout {
        width: parent.width
        spacing: 20
        anchors.margins: 20
        
        // Audio Controls
        GroupBox {
            title: "Audio"
            Layout.fillWidth: true
            Layout.margins: 10
            
            GridLayout {
                columns: 2
                width: parent.width
                columnSpacing: 20
                rowSpacing: 10
                
                Label { text: "Volume" }
                RowLayout {
                    Layout.fillWidth: true
                    Slider {
                        id: volumeSlider
                        Layout.fillWidth: true
                        from: 0
                        to: 30
                        stepSize: 1
                        
                        Binding on value {
                            when: !volumeSlider.pressed
                            value: headset.volume
                        }
                        
                        onMoved: {
                            pendingCommand = () => headset.setVolume(volumeSlider.value)
                            sharedTimer.restart()
                        }
                        onPressedChanged: {
                            if (!pressed) {
                                sharedTimer.stop()
                                headset.setVolume(volumeSlider.value)
                                pendingCommand = null
                            }
                        }
                    }
                    Label { text: Math.round(volumeSlider.value) }
                }
                
                Label { text: "Game/Chat Balance" }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "G: " + Math.round(100 - balanceSlider.value) + "%" }
                    Slider {
                        id: balanceSlider
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        stepSize: 10
                        snapMode: Slider.SnapAlways
                        
                        Binding on value {
                            when: !balanceSlider.pressed
                            value: headset.balance
                        }
                        
                        onMoved: {
                            pendingCommand = () => headset.setBalance(balanceSlider.value)
                            sharedTimer.restart()
                        }
                        onPressedChanged: {
                            if (!pressed) {
                                sharedTimer.stop()
                                headset.setBalance(balanceSlider.value)
                                pendingCommand = null
                            }
                        }
                    }
                    Label { text: "C: " + Math.round(balanceSlider.value) + "%" }
                }
            }
        }
        
        // Noise Cancellation
        GroupBox {
            title: "Noise Control"
            Layout.fillWidth: true
            Layout.margins: 10
            
            ColumnLayout {
                width: parent.width
                spacing: 10
                
                RowLayout {
                    spacing: 10
                    
                    RadioButton {
                        text: "Off"
                        checked: headset.ncMode === 0
                        font.bold: checked
                        onToggled: if (checked) headset.setNcMode(0)
                    }
                    RadioButton {
                        text: "Noise Cancelling"
                        checked: headset.ncMode === 1
                        font.bold: checked
                        onToggled: if (checked) headset.setNcMode(1)
                    }
                    RadioButton {
                        text: "Ambient Sound"
                        checked: headset.ncMode === 2
                        font.bold: checked
                        onToggled: if (checked) headset.setNcMode(2)
                    }
                }
                
                GridLayout {
                    enabled: headset.ncMode === 2
                    opacity: enabled ? 1.0 : 0.5
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 20
                    rowSpacing: 10
                    Layout.leftMargin: 10
                    
                    Label { text: "Ambient Level" }
                    RowLayout {
                        Layout.fillWidth: true
                        Slider {
                            id: ambSlider
                            Layout.fillWidth: true
                            from: 1
                            to: 20
                            stepSize: 1
                            value: headset.ambientLevel
                            
                            onMoved: {
                                pendingCommand = () => headset.setAmbientLevel(ambSlider.value)
                                sharedTimer.restart()
                            }
                            onPressedChanged: {
                                if (!pressed) {
                                    sharedTimer.stop()
                                    headset.setAmbientLevel(ambSlider.value)
                                    pendingCommand = null
                                }
                            }
                        }
                        Label { text: ambSlider.value }
                    }
                    
                    Label { text: "Focus on Voice" }
                    Switch {
                        checked: headset.focusOnVoice
                        onToggled: headset.setFocusOnVoice(checked)
                    }
                }
            }
        }
        
        // Microphone
        GroupBox {
            title: "Microphone"
            Layout.fillWidth: true
            Layout.margins: 10
            
            GridLayout {
                columns: 2
                columnSpacing: 20
                rowSpacing: 10
                
                Label { text: "Status:" }
                Label { 
                    text: headset.micConnected ? (headset.micMuted ? "Muted" : "Active") : "Disconnected"
                    color: headset.micConnected ? (headset.micMuted ? "orange" : "green") : "red"
                    font.bold: true
                }
                
                Label { text: "Sidetone" }
                RowLayout {
                    Layout.fillWidth: true
                    Slider {
                        id: sidetoneSlider
                        Layout.fillWidth: true
                        from: 0
                        to: 10
                        stepSize: 1
                        
                        Binding on value {
                            when: !sidetoneSlider.pressed
                            value: headset.sidetone
                        }
                        
                        onMoved: {
                            pendingCommand = () => headset.setSidetone(Math.round(sidetoneSlider.value))
                            sharedTimer.restart()
                        }
                        onPressedChanged: {
                            if (!pressed) {
                                sharedTimer.stop()
                                headset.setSidetone(Math.round(sidetoneSlider.value))
                                pendingCommand = null
                            }
                        }
                    }
                    Label { text: Math.round(sidetoneSlider.value) }
                }
            }
        }
        
        // Bluetooth (Runtime)
        GroupBox {
            title: "Bluetooth"
            Layout.fillWidth: true
            Layout.margins: 10
            
            GridLayout {
                columns: 2
                columnSpacing: 20
                rowSpacing: 10
                
                Label { text: "Radio:" }
                Label {
                    text: headset.bluetoothEnabled ? "Enabled" : "Disabled"
                    color: headset.bluetoothEnabled ? "green" : "gray"
                    font.bold: true
                }

                Label { text: "Connection:" }
                Label {
                    text: headset.bluetoothConnected ? "Connected" : "Disconnected"
                    color: headset.bluetoothConnected ? "green" : "gray"
                    font.bold: true
                }
            }
        }
    }
}
