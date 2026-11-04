import QtQuick
import QtQuick.Window
import "../theme" as Theme
import "Symbols.js" as Symbols
Image {
    id:root
    property string name:"apps"
    property int size:Tokens.icon
    property color color:Theme.ThemeManager.surfaceText
    property bool filled:false
    width:size;height:size
    sourceSize {width:Math.ceil(root.size*Screen.devicePixelRatio);height:Math.ceil(root.size*Screen.devicePixelRatio)}
    source:Symbols.svg(name,String(color),filled)
    fillMode:Image.PreserveAspectFit
    opacity:enabled ? 1 : Tokens.disabledOpacity
    Accessible.ignored:true
}
