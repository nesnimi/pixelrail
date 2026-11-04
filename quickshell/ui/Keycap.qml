import QtQuick
import "../theme" as Theme
Rectangle {
    id:root
    property alias text:label.text
    implicitWidth:label.implicitWidth+12
    implicitHeight:20
    radius:Tokens.radiusXs
    color:Theme.ThemeManager.surfaceContainerHigh
    Text {id:label;anchors.centerIn:parent;color:Theme.ThemeManager.surfaceVariantText;font {family:Tokens.font;pixelSize:Tokens.caption;weight:Font.Medium}}
}
