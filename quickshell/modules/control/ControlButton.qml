import QtQuick
import "../../ui" as Ui
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme" as Theme
Button {
    id: root
    scale:down ? .98 : 1
    Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
    property bool active: false
    property bool tonal:false
    property string symbol:""
    Theme.Palette {id:colors}
    implicitHeight: tonal ? Ui.Tokens.controlChipHeight : 36
    leftPadding:root.text==="" && root.symbol!=="" ? 6 : 12;rightPadding:leftPadding
    readonly property color foreground:down || (tonal && active) ? colors.primaryContainerText : active ? colors.selectedText : colors.text
    contentItem:RowLayout {
        spacing:root.text==="" ? 0 : 8
        Item {Layout.fillWidth:true;visible:root.symbol!==""}
        Ui.PixelIcon {visible:root.symbol!=="";name:root.symbol;size:20;color:root.foreground;filled:root.active}
        Text {visible:root.text!=="";Layout.fillWidth:root.symbol==="";text:root.text;textFormat:Text.PlainText;wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;color:root.foreground;font {family:colors.font;pixelSize:root.tonal ? Ui.Tokens.controlPercent : Ui.Tokens.body} elide:Text.ElideRight}
        Item {Layout.fillWidth:true;visible:root.symbol!==""}
    }

    background: Rectangle { radius:Ui.Tokens.radiusPill;border.width:root.visualFocus ? 1 : 0;border.color:colors.accent;color:root.down || (root.tonal && root.active) ? colors.primaryContainer : root.active ? colors.selected : root.hovered || root.tonal ? colors.surfaceContainerHigh : colors.surfaceContainer;opacity:root.enabled ? 1 : Ui.Tokens.disabledOpacity}
}
