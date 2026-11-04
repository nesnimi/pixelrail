import QtQuick
import QtQuick.Layouts
import "../../theme" as Theme
import "../../ui" as Ui
Rectangle {
    id:root
    default property alias contents:body.data
    property string title:""
    property string description:""
    Layout.fillWidth:true
    implicitHeight:column.implicitHeight+24
    radius:Ui.Tokens.radiusLg
    color:Theme.ThemeManager.surfaceContainerHigh
    ColumnLayout {
        id:column
        anchors {left:parent.left;right:parent.right;top:parent.top;margins:Ui.Tokens.spaceMd}
        spacing:Ui.Tokens.spaceSm
        Text {Layout.fillWidth:true;visible:text!=="";text:root.title;color:Theme.ThemeManager.surfaceText;wrapMode:Text.Wrap;font {family:Ui.Tokens.font;pixelSize:Ui.Tokens.body;weight:Font.Medium}}
        Text {Layout.fillWidth:true;visible:text!=="";text:root.description;color:Theme.ThemeManager.surfaceVariantText;wrapMode:Text.Wrap;font {family:Ui.Tokens.font;pixelSize:Ui.Tokens.label}}
        ColumnLayout {id:body;Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm}
    }
}
