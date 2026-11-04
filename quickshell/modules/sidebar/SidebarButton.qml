pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import Quickshell
import "../../theme" as Theme
import "../../ui" as Ui
import "SidebarLogic.js" as Logic

Rectangle {
    id: root
    property string label: ""
    property int labelSize:Ui.Tokens.label
    property string glyph: ""
    property string image: ""
    property string appName:""
    property string iconName:""
    property string tooltip: ""
    property bool selected: false
    property bool attention: false
    property bool accented: false
    property bool animate: false
    property bool wheelEnabled: false
    readonly property color foreground: mouse.pressed || selected ? colors.primaryContainerText : attention ? colors.error : accented ? colors.accent : colors.text
    signal clicked()
    signal rightClicked()
    signal scrolled(int direction)
    implicitWidth: 42; implicitHeight: 36
    radius:Math.min(width,height)/2
    color: mouse.pressed ? colors.primaryContainer : selected ? colors.primaryContainer
         : mouse.containsMouse ? colors.surfaceHigh : "transparent"
    scale:mouse.pressed ? .96 : 1
    Behavior on scale {enabled:root.animate;NumberAnimation {duration:Ui.Tokens.hover}}
    Theme.Palette { id: colors }
    readonly property var symbols:({power:"power_settings_new",wifi:"wifi",offline:"wifi_off",wired:"lan",volume:"volume_up",muted:"volume_off",bell:"notifications",leaf:"eco"})
    // Original PixelRail vector from SidebarLogic.svg, retained since v2.1.
    Image {
        id:brand
        objectName:"sidebar-brand"
        anchors.centerIn:parent;width:Math.min(Ui.Tokens.icon,Math.max(12,root.height-6));height:width
        visible:root.glyph==="home"
        source:visible ? Logic.svg("home",String(root.foreground)) : ""
        sourceSize {width:Math.ceil(brand.width*Screen.devicePixelRatio);height:Math.ceil(brand.height*Screen.devicePixelRatio)}
        fillMode:Image.PreserveAspectFit
    }
    Ui.PixelIcon {objectName:"sidebar-system-icon";anchors.centerIn:parent;name:root.symbols[root.glyph] || "apps";size:Math.min(Ui.Tokens.sidebarIcon,Math.max(12,root.height-6));color:root.foreground;filled:false;visible:root.glyph!=="" && root.glyph!=="home" && root.image===""}
    Ui.PixelAppIcon {anchors.centerIn:parent;size:24;visible:root.image!=="";originalSource:root.image;iconName:root.iconName;appName:root.appName}
    Text {
        anchors.centerIn: parent
        visible: root.label !== ""
        text: root.label; textFormat: Text.PlainText
        horizontalAlignment: Text.AlignHCenter
        color: root.foreground
        font { family: colors.font; pixelSize:root.labelSize; weight: Font.Medium }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: event => event.button === Qt.RightButton ? root.rightClicked() : root.clicked()
        onWheel: event => {
            event.accepted = root.wheelEnabled;
            if (root.wheelEnabled) root.scrolled(event.angleDelta.y > 0 ? 1 : -1);
        }
    }
    Loader {
        active: mouse.containsMouse && root.tooltip !== ""
        sourceComponent: PopupWindow {
            anchor.item: root
            anchor.rect.x: root.width + 8
            anchor.edges: Edges.Right
            anchor.gravity: Edges.Right
            implicitWidth: Math.min(300, description.implicitWidth + 24)
            implicitHeight: description.implicitHeight + 20
            color: "transparent"
            visible: true
            Rectangle {
                anchors.fill: parent; radius:Ui.Tokens.radiusSm
                color: colors.surfaceHigh
                border { width: 1; color: colors.outlineVariant }
                Text {
                    id: description
                    anchors { fill: parent; margins: 10 }
                    text: root.tooltip; textFormat: Text.PlainText; wrapMode: Text.Wrap
                    color: colors.text; font { family: colors.font; pixelSize:Ui.Tokens.label }
                }
            }
        }
    }
}
