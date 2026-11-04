import QtQuick
import QtQuick.Window
import Quickshell
import "../theme" as Theme
import "AppIcons.js" as Apps
Rectangle {
    id:root
    property string iconName:""
    property string originalSource:""
    property int size:30
    property string appName:""
    property bool highlighted:false
    readonly property color tonalBackground:highlighted ? Theme.ThemeManager.primary : Theme.ThemeManager.secondaryContainer
    readonly property color tonalForeground:highlighted ? Theme.ThemeManager.primaryText : Theme.ThemeManager.secondaryContainerText
    readonly property bool themed:Theme.ThemeManager.iconStyle==="themed"
    readonly property bool canTint:GraphicsInfo.api!==GraphicsInfo.Software
    readonly property string semantic:Apps.semantic(iconName,appName)
    readonly property string symbolic:{
        for(const candidate of Apps.symbolicCandidates(iconName,semantic)){const path=Quickshell.iconPath(candidate,true);if(path)return path;}
        return "";
    }
    readonly property bool showSymbol:themed && (!canTint || symbolic==="" || art.status!==Image.Ready || tintLoader.status!==Loader.Ready)
    readonly property string original:originalSource || (iconName.startsWith("file:") || iconName.startsWith("/") ? iconName : iconName ? Quickshell.iconPath(iconName,true) : "")
    implicitWidth:size;implicitHeight:size;radius:width/2
    color:themed ? tonalBackground : "transparent"
    // Only explicitly symbolic artwork is eligible. Complex original PNGs are never tinted.
    Image {
        id:art;anchors.centerIn:parent;width:root.themed ? parent.width*.7 : parent.width;height:width
        source:root.themed ? root.symbolic : root.original
        visible:!root.themed && status===Image.Ready
        sourceSize {width:Math.ceil(root.size*Screen.devicePixelRatio);height:Math.ceil(root.size*Screen.devicePixelRatio)}
    }
    Loader {
        id:tintLoader
        anchors.fill:art;active:root.themed && root.canTint && root.symbolic!=="" && art.status===Image.Ready
        source:"SymbolicIcon.qml"
        onLoaded:{item.artwork=art;item.tint=Qt.binding(()=>root.tonalForeground);}
    }
    Text {anchors.centerIn:parent;visible:root.showSymbol && root.semantic==="" && root.appName!=="";text:root.appName.charAt(0).toLocaleUpperCase();color:root.tonalForeground;font {family:Tokens.font;pixelSize:root.size*.53;weight:Font.Medium}}
    PixelIcon {anchors.centerIn:parent;size:root.size*.7;visible:(root.showSymbol && (root.semantic!=="" || root.appName==="")) || (!root.themed && art.status!==Image.Ready);name:root.themed && root.semantic!=="" ? root.semantic : "apps";color:root.themed ? root.tonalForeground : Theme.ThemeManager.primary}
}
