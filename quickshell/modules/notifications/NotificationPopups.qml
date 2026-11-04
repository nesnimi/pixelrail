pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Wayland
import "../../components/PopupPlacement.js" as Placement
PanelWindow {
    id:root
    required property var manager
    property int sideOffset:12
    property var targetScreen:null
    signal openRequested()
    screen:targetScreen || Quickshell.screens[0]
    visible:manager.enabled && manager.popups.length>0 && !!screen
    anchors {left:true;top:true}
    margins {left:Placement.left(screen ? screen.width : 400,root.sideOffset);top:12}
    implicitWidth:Placement.width(360,screen ? screen.width : 400,root.sideOffset)
    implicitHeight:Math.min(cards.implicitHeight,screen ? screen.height*.45 : 350)
    exclusionMode:ExclusionMode.Ignore;color:"transparent"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.namespace:"pixelrail-notifications"
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
    NotificationCards {id:cards;anchors {left:parent.left;right:parent.right} manager:root.manager;toast:true;onOpenRequested:root.openRequested()}
}
