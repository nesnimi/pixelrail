pragma ComponentBehavior: Bound
import QtQuick
import "."
ControlSlider {
    id:root
    property real backendValue:from
    property bool backendPending:false
    signal requested(real requestedValue,bool finalValue)
    live:true
    wheelEnabled:true
    activeFocusOnTab:true
    Binding {target:root;property:"value";when:!root.pressed && !root.backendPending;value:root.backendValue;restoreMode:Binding.RestoreNone}
    onMoved:requested(value,false)
    onPressedChanged:if(!pressed && enabled)requested(value,true)
}
