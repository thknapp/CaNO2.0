import QtQuick 2.15
import QtQuick.Controls 2.15

Switch {
    id: autosaveSwitch
    width: 50
    height: 30
    checked: false  // Default state
    
    onCheckedChanged: {
        autosaveSwitchSignal.checkedChanged(checked)
    }
}