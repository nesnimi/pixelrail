pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Quickshell
import "../../theme" as Theme
import "../../ui" as Ui
import "." as Controls
ColumnLayout {
    id:root
    required property var actions
    readonly property var files:DesktopEntries.applications.values.find(entry=>/nautilus|dolphin|thunar|nemo/.test(entry.id.toLowerCase())) || null
    readonly property var browser:DesktopEntries.applications.values.find(entry=>/chrome|chromium|firefox/.test(entry.id.toLowerCase())) || null
    Layout.fillWidth:true;spacing:Ui.Tokens.spaceMd
    GridLayout {
        Layout.fillWidth:true;columns:width<220 ? 1 : 2;columnSpacing:Ui.Tokens.spaceXs;rowSpacing:Ui.Tokens.spaceXs
        Repeater {model:["original","themed"];delegate:Controls.ControlButton {required property string modelData;Layout.fillWidth:true;Layout.preferredWidth:1;tonal:true;objectName:"settings-icons-"+modelData;text:modelData==="original" ? "Original" : "Pixel Themed";active:Theme.ThemeManager.iconStyle===modelData;onClicked:root.actions.request("iconStyle",modelData)}}
    }
    RowLayout {
        Layout.alignment:Qt.AlignHCenter;spacing:Ui.Tokens.space
        Ui.PixelAppIcon {objectName:"settings-preview-files";iconName:root.files ? root.files.icon : "system-file-manager";appName:root.files ? root.files.name : "Файлы";size:40}
        Ui.PixelAppIcon {iconName:root.browser ? root.browser.icon : "web-browser";appName:root.browser ? root.browser.name : "Браузер";size:40}
    }
}
