pragma Singleton
import QtQuick
import Quickshell
import "../theme" as Theme
QtObject {
    id:root
    property var typography:null
    onFontChanged:if(typography)typography.apply(font)
    onTypographyChanged:if(typography)typography.apply(font)
    Component.onCompleted:{try{typography=Qt.createQmlObject('import QtQml\nimport '+JSON.stringify('file://'+Quickshell.shellPath('native/PixelRail/DBusLease'))+' as Native\nNative.PixelTypography {}',root);}catch(error){}}
    readonly property int spaceXs:4
    readonly property int spaceSm:8
    readonly property int spaceMd:12
    readonly property int space:16
    readonly property int spaceLg:20
    readonly property int spaceXl:24
    readonly property int radiusXs:8
    readonly property int radiusSm:12
    readonly property int radius:16
    readonly property int radiusLg:20
    readonly property int radiusPanel:26
    readonly property int radiusPill:999
    readonly property int caption:11
    readonly property int label:12
    readonly property int body:14
    readonly property int section:16
    readonly property int title:20
    readonly property int display:26
    readonly property int launcherWidth:540
    readonly property int launcherSearchHeight:48
    readonly property int launcherChromeHeight:144
    readonly property int launcherIcon:32
    readonly property int controlWidth:400
    readonly property int settingsWidth:680
    readonly property int sidebarWidth:54
    readonly property int sidebarWindowWidth:66
    readonly property int sidebarIcon:22
    readonly property int controlTitle:18
    readonly property int controlTileHeight:64
    readonly property int controlTileRadius:22
    readonly property int controlChipHeight:34
    readonly property int controlPercent:13
    readonly property int controlSliderHeight:44
    readonly property int controlSliderTrack:28
    readonly property int controlSliderHandle:6
    readonly property int rowHeight:50
    readonly property int sliderTrack:12
    readonly property int sliderHandle:22
    readonly property int icon:24
    readonly property real disabledOpacity:.55
    readonly property real dividerOpacity:.35
    readonly property real shadowOpacity:.12
    readonly property int hover:Theme.ThemeManager.animations ? 120 : 0
    readonly property int state:Theme.ThemeManager.animations ? 160 : 0
    readonly property int panel:Theme.ThemeManager.animations ? 200 : 0
    readonly property int osdTimeout:1300
    property FontLoader roboto:FontLoader {source:"../assets/fonts/Roboto.ttf"}
    readonly property string font:typography && typography.family ? typography.family : roboto.status===FontLoader.Ready ? roboto.name : "sans-serif"
}
