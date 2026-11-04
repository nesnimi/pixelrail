import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme" as Theme
import "../../ui" as Ui
Button {
    id:root
    scale:down ? .98 : 1
    Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
    property string status:""
    property string symbol:"settings"
    property bool active:false
    readonly property color foreground:down ? colors.primaryContainerText : active ? colors.primaryContainerText : colors.text
    Theme.Palette {id:colors}
    implicitHeight:Ui.Tokens.controlTileHeight
    leftPadding:12;rightPadding:12;topPadding:10;bottomPadding:10
    activeFocusOnTab:true;Accessible.description:status
    contentItem:RowLayout {
        spacing:8
        Rectangle {
            implicitWidth:32;implicitHeight:32;radius:16
            color:root.active || root.down ? colors.primary : colors.surfaceVariant
            Ui.PixelIcon {anchors.centerIn:parent;name:root.symbol;size:22;color:root.active || root.down ? colors.primaryText : colors.surfaceVariantText;filled:false}
        }
        ColumnLayout {
            Layout.fillWidth:true;spacing:3
            Text {Layout.fillWidth:true;text:root.text;textFormat:Text.PlainText;elide:Text.ElideRight;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium} color:root.foreground}
            Text {Layout.fillWidth:true;text:root.status;textFormat:Text.PlainText;elide:Text.ElideRight;font {family:colors.font;pixelSize:Ui.Tokens.label} color:root.active || root.down ? root.foreground : colors.muted}
        }
        Ui.PixelIcon {name:"chevron_right";size:14;color:root.foreground}
    }
    background:Rectangle {
        radius:Ui.Tokens.controlTileRadius
        color:root.down || root.active ? colors.primaryContainer : colors.surfaceContainerHigh
        border.width:root.visualFocus ? 2 : 0;border.color:colors.accent
        opacity:root.enabled ? 1 : Ui.Tokens.disabledOpacity
        Rectangle {anchors.fill:parent;radius:parent.radius;color:root.foreground;opacity:root.down ? .10 : root.hovered ? .05 : 0}
    }
    ToolTip.visible:hovered;ToolTip.text:status
}
