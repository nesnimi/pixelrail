pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import "../../theme" as Theme
import "../../ui" as Ui
import "../../components/PopupPlacement.js" as Placement
import "../sidebar/SidebarLogic.js" as Icons
PanelWindow {
    id:root
    property var system:SystemControls
    property bool opened:false
    property string kind:"volume"
    property int sideOffset:12
    property var targetScreen:null
    property real reveal:opened ? 1 : 0
    readonly property bool volume:kind==="volume"
    readonly property bool muted:volume && system.audioAvailable && system.muted
    readonly property real level:volume ? (system.audioAvailable ? system.volume : 0) : (system.brightness.percent || 0)/100
    signal dismissed()
    screen:targetScreen || Quickshell.screens[0]
    visible:reveal>0 && !!screen
    anchors.left:true
    margins.left:Placement.left(screen ? screen.width : 1366,sideOffset)
    implicitWidth:Placement.width(280,screen ? screen.width : 1366,sideOffset)
    implicitHeight:72
    exclusionMode:ExclusionMode.Ignore;color:"transparent"
    WlrLayershell.namespace:"pixelrail-system-osd";WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
    mask:Region {} // Output-only: mouse and wheel pass through the entire OSD.
    Behavior on reveal {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
    onRevealChanged:if(!opened && reveal===0)dismissed()
    Theme.Palette {id:colors}
    Rectangle {
        anchors.fill:parent;radius:Ui.Tokens.radiusPill;color:colors.surfaceContainer;opacity:root.reveal
        border {width:1;color:colors.outlineVariant}
        transform:Translate {x:-6*(1-root.reveal)}
        RowLayout {
            anchors {fill:parent;margins:Ui.Tokens.space} spacing:Ui.Tokens.spaceMd
            Ui.PixelIcon {name:root.volume ? root.muted ? "volume_off" : "volume_up" : "brightness_6";size:24;color:colors.accent}
            ColumnLayout {
                Layout.fillWidth:true;spacing:7
                Text {text:root.volume ? root.muted ? "Без звука" : "Громкость" : "Яркость";color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body}}
                Rectangle {
                    Layout.fillWidth:true;implicitHeight:6;radius:3;color:colors.surfaceVariant
                    Rectangle {height:parent.height;width:parent.width*Math.max(0,Math.min(1,root.level));radius:3;color:root.muted ? colors.muted : colors.accent}
                }
            }
            Text {objectName:"osd-percent";text:Math.round(root.level*100)+"%";color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium} Layout.minimumWidth:38;horizontalAlignment:Text.AlignRight}
        }
    }
}
