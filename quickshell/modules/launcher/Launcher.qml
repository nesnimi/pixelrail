pragma ComponentBehavior: Bound

import QtQuick
import "../system" as System
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import "../../theme" as Theme
import "../../ui" as Ui
import "Search.js" as Search
import "../../components/PopupPlacement.js" as Placement

PanelWindow {
    id: root
    property bool opened: false
    property real revealProgress: opened ? 1 : 0
    visible: opened || revealProgress > 0
    Behavior on revealProgress {
        NumberAnimation { duration: Ui.Tokens.panel; easing.type: Easing.OutCubic }
    }
    color: "transparent"
    property var requestedScreen:null
    screen:requestedScreen && Quickshell.screens.includes(requestedScreen) ? requestedScreen : Quickshell.screens[0]
    property int sideOffset: 12
    property var allowedWindow: null
    anchors { left: true; bottom: true }
    margins { left: Placement.left(screen.width,root.sideOffset); bottom: 12 }
    implicitWidth: Placement.width(Ui.Tokens.launcherWidth,screen.width,root.sideOffset)
    implicitHeight: Math.max(1,Math.min(showHome ? homeContent.implicitHeight + Ui.Tokens.launcherSearchHeight + 20 + Ui.Tokens.spaceSm*2 + Ui.Tokens.space*2 : Ui.Tokens.launcherChromeHeight + (results.length ? Math.min(5, results.length) * 54 - 4 : 72), screen.height - 24))
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "pixelrail-launcher"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: opened && !System.ScreenshotState.active ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

    HyprlandFocusGrab { windows: root.allowedWindow ? [root,root.allowedWindow] : [root]; active: root.visible && root.opened && !System.ScreenshotState.active; onCleared:if(!System.ScreenshotState.active)root.close() }
    Theme.Palette { id: colors }
    readonly property var catalog:DesktopEntries.applications.values
    property var entryMetadata:({})
    property bool metadataReady:false
    property bool metadataPending:false
    property string metadataHelper:Quickshell.env("PIXELRAIL_LAUNCHER_METADATA") || Quickshell.shellPath("../scripts/launcher_entries.py")
    property var results: Search.search(catalog, search.text, entryMetadata)
    readonly property bool emptyQuery:search.text.trim()===""
    readonly property bool showHome:emptyQuery && homeApps.length>0
    property var usage:({})
    property var pendingUsage:({})
    property bool usageLoaded:false
    property int homeIndex:0
    readonly property int homeColumns:Math.max(1,Math.min(4,Math.floor((root.width-Ui.Tokens.space*2)/104)))
    readonly property var homeApps:emptyQuery && metadataReady ? Search.suggestions(catalog,usage,8,entryMetadata) : []
    onCatalogChanged:{metadataPending=true;Qt.callLater(loadMetadata);}
    function loadMetadata():void {
        if(metadataReader.running || !metadataPending || !catalog.length)return;
        metadataPending=false;metadataReader.running=true;
    }
    Process {
        id:metadataReader;command:["python3",root.metadataHelper]
        stdout:StdioCollector {onStreamFinished:{
            try {const value=JSON.parse(text);if(value.version!==1 || !value.entries)throw new Error("format");root.entryMetadata=value.entries;root.metadataReady=true;}
            catch(error){console.warn("PixelRail Launcher: desktop metadata unavailable; using application list");}
        }}
        onExited:(code,status)=>{if(code)console.warn("PixelRail Launcher: desktop metadata reader failed",code);Qt.callLater(root.loadMetadata);}
    }
    Timer {interval:3000;running:metadataReader.running;onTriggered:metadataReader.running=false}
    function finishUsage(counts):void {
        if(usageLoaded)return;
        let next=Search.cleanCounts(counts);
        for(const id of Object.keys(pendingUsage))next[id]=Math.min(1000000,(next[id] || 0)+pendingUsage[id]);
        usage=Search.cleanCounts(next);usageLoaded=true;
        if(Object.keys(pendingUsage).length)saveUsage();
        pendingUsage=({});
    }
    function saveUsage():void {usageFile.setText(JSON.stringify({version:1,counts:usage}));}
    function remember(id):void {
        usage=Search.record(usage,id);
        if(usageLoaded)saveUsage();else pendingUsage=Search.record(pendingUsage,id);
    }
    FileView {
        id:usageFile
        path:(Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME")+"/.local/state")+"/pixelrail/launcher.json"
        preload:true;blockLoading:false;blockWrites:false;atomicWrites:true;printErrors:false
        onLoaded:{try {const data=JSON.parse(text());root.finishUsage(data.version===1 ? data.counts : {});}catch(error){root.finishUsage({});}}
        onLoadFailed:root.finishUsage({})
        onSaveFailed:error=>console.warn("PixelRail Launcher: не удалось сохранить частоту запусков",error)
    }
    onResultsChanged: {list.currentIndex = results.length ? 0 : -1;homeIndex=0;homeScroll.contentY=0;}
    onHomeAppsChanged:homeIndex=Math.min(homeIndex,Math.max(0,homeApps.length-1))
    function close(): void { opened = false; }
    function toggle(): void {
        if (opened) { close(); return; }
        const monitor = Hyprland.focusedMonitor;
        const target = monitor ? Quickshell.screens.find(s => s.name === monitor.name) : null;
        requestedScreen=target || Quickshell.screens[0];
        search.text = "";
        list.currentIndex = results.length ? 0 : -1;
        homeIndex = 0;
        homeScroll.contentY=0;
        opened = true;
        search.forceActiveFocus();
    }
    function move(delta: int): void {
        if(showHome) {
            const count=homeApps.length;if(!count)return;
            homeIndex=(homeIndex+delta+count)%count;
            Qt.callLater(revealHome);
        } else if (results.length) {
            list.currentIndex = (list.currentIndex + delta + results.length) % results.length;
            list.positionViewAtIndex(list.currentIndex, ListView.Contain);
        }
    }
    function revealHome():void {
        const tile=apps.itemAt(homeIndex);
        if(!tile)return;
        const point=tile.mapToItem(homeContent,0,0);
        homeScroll.contentY=Math.max(0,Math.min(Math.max(0,homeScroll.contentHeight-homeScroll.height),point.y<homeScroll.contentY ? point.y : Math.max(homeScroll.contentY,point.y+tile.height-homeScroll.height)));
    }
    function moveVertical(direction:int):void {
        if(!showHome){move(direction);return;}
        const cells=[];
        for(let index=0;index<homeApps.length;index++) {
            const item=apps.itemAt(index);
            if(item)cells.push({index:index,point:item.mapToItem(homeContent,item.width/2,item.height/2)});
        }
        const current=cells.find(cell=>cell.index===homeIndex);if(!current)return;
        const next=cells.filter(cell=>direction*(cell.point.y-current.point.y)>1);
        const rows=next.length ? next : cells;
        const target=rows.reduce((best,cell)=>direction*(cell.point.y-best.point.y)<0 ? cell : best);
        const row=rows.filter(cell=>Math.abs(cell.point.y-target.point.y)<1);
        homeIndex=row.reduce((best,cell)=>Math.abs(cell.point.x-current.point.x)<Math.abs(best.point.x-current.point.x) ? cell : best).index;
        revealHome();
    }
    function activateSelection():void {
        if(!showHome)launch(list.currentIndex);
        else if(homeIndex>=0 && homeIndex<homeApps.length)launchApp(homeApps[homeIndex]);
    }
    function launch(index: int): void {
        if (index < 0 || index >= results.length) return;
        launchApp(results[index]);
    }
    function launchApp(app):void {
        // Quickshell 0.2 execute() ignores Terminal=true: handle it explicitly.
        if (app.runInTerminal) {
            Quickshell.execDetached({command: ["kitty", "-e"].concat(app.command), workingDirectory: app.workingDirectory});
        } else {
            app.execute();
        }
        remember(app.id);
        close();
    }

    Rectangle {
        objectName:"launcher-surface"
        anchors.fill: parent
        radius: Ui.Tokens.radiusPanel
        opacity: root.revealProgress
        enabled: root.opened
        transform: Translate { y: -8 * (1 - root.revealProgress) }
        color: colors.surfaceContainer
        Column {
            id: content
            anchors { left: parent.left; right: parent.right; top: parent.top; margins:Ui.Tokens.space }
            spacing:Ui.Tokens.spaceSm
            Rectangle {
                width: parent.width
                height: Ui.Tokens.launcherSearchHeight
                radius: Ui.Tokens.radiusPill
                color: colors.surfaceHigh
                border.width: search.activeFocus ? 1 : 0
                border.color: colors.accent
                Ui.PixelIcon {anchors {left:parent.left;leftMargin:16;verticalCenter:parent.verticalCenter} name:"search";size:22;color:colors.accent}
                TextField {
                    id: search
                    objectName:"launcher-search"
                    anchors { fill: parent; leftMargin: 48; rightMargin: 16 }
                    background: Item {}
                    color: colors.text
                    placeholderText: "Поиск приложений…"
                    placeholderTextColor: colors.muted
                    selectionColor: colors.selected
                    selectedTextColor: colors.selectedText
                    font { family: colors.font; pixelSize:Ui.Tokens.body }
                    cursorDelegate:Rectangle {width:2;color:colors.accent}
                    selectByMouse: true
                    activeFocusOnTab: false
                    Keys.onPressed: event => {
                        if (event.key === Qt.Key_Escape && !System.ScreenshotState.active) root.close();
                        else if (event.key === Qt.Key_Down) root.moveVertical(1);
                        else if (event.key === Qt.Key_Up) root.moveVertical(-1);
                        else if (event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier)) root.move(1);
                        else if (event.key === Qt.Key_Backtab || event.key === Qt.Key_Tab) root.move(-1);
                        else if(root.showHome && event.key===Qt.Key_Right)root.move(1);
                        else if(root.showHome && event.key===Qt.Key_Left)root.move(-1);
                        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) root.activateSelection();
                        else return;
                        event.accepted = true;
                    }
                }
            }
            Flickable {
                id:homeScroll;objectName:"launcher-home"
                visible:root.showHome;width:parent.width
                height:Math.min(homeContent.implicitHeight,Math.max(0,root.height-Ui.Tokens.launcherSearchHeight-20-Ui.Tokens.spaceSm*2-Ui.Tokens.space*2))
                contentWidth:width;contentHeight:homeContent.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
                Column {
                    id:homeContent;width:homeScroll.width;spacing:Ui.Tokens.spaceSm
                    Text {objectName:"launcher-home-heading";text:root.homeApps.some(app=>(root.usage[app.id] || 0)>0) ? "Часто используемые" : "Приложения";color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium} height:20;leftPadding:4}
                    Grid {
                        id:appGrid;width:parent.width;columns:root.homeColumns;spacing:Ui.Tokens.spaceXs
                        Repeater {
                            id:apps;model:root.homeApps
                            delegate:Rectangle {
                                id:appTile;objectName:"launcher-app-"+index
                                required property var modelData
                                required property int index
                                readonly property bool emphasized:root.homeIndex===index || appMouse.pressed
                                width:(appGrid.width-(appGrid.columns-1)*appGrid.spacing)/appGrid.columns;height:80
                                radius:Ui.Tokens.radiusLg;color:emphasized ? colors.primaryContainer : appMouse.containsMouse ? colors.surfaceHigh : "transparent"
                                scale:appMouse.pressed ? .98 : 1
                                Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
                                Ui.PixelAppIcon {anchors {horizontalCenter:parent.horizontalCenter;top:parent.top;topMargin:Ui.Tokens.spaceMd} size:Ui.Tokens.launcherIcon;highlighted:appTile.emphasized;appName:appTile.modelData.name;iconName:appTile.modelData.icon || ""}
                                Text {anchors {left:parent.left;right:parent.right;bottom:parent.bottom;margins:Ui.Tokens.spaceSm} text:appTile.modelData.name;textFormat:Text.PlainText;elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter;color:appTile.emphasized ? colors.primaryContainerText : colors.text;font {family:colors.font;pixelSize:Ui.Tokens.label}}
                                Accessible.role:Accessible.Button;Accessible.name:modelData.name
                                ToolTip.visible:appMouse.containsMouse;ToolTip.text:modelData.name
                                MouseArea {id:appMouse;anchors.fill:parent;hoverEnabled:true;onClicked:root.launchApp(appTile.modelData)}
                            }
                        }
                    }
                }
            }
            Text {visible:!root.showHome;text:"Приложения";color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium} height:20;verticalAlignment:Text.AlignVCenter;leftPadding:4}
            ListView {
                id: list
                objectName:"launcher-results"
                width: parent.width
                height: Math.min(5 * 54 - 4, Math.max(0, root.height - Ui.Tokens.launcherChromeHeight), contentHeight)
                clip: true
                visible: !root.showHome && root.results.length > 0
                spacing:Ui.Tokens.spaceXs
                model: root.showHome ? [] : root.results
                boundsBehavior: Flickable.StopAtBounds
                delegate: Rectangle {
                    id: row
                    objectName:"launcher-result-"+index
                    required property var modelData
                    required property int index
                    width: list.width
                    height: 50
                    radius:Ui.Tokens.radius
                    readonly property bool emphasized:ListView.isCurrentItem || rowMouse.pressed
                    color: emphasized ? colors.primaryContainer : rowMouse.containsMouse ? colors.surfaceHigh : "transparent"
                    scale:rowMouse.pressed ? .99 : 1
                    Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
                    readonly property string subtitle: modelData.genericName && modelData.genericName.trim().toLocaleLowerCase()!==modelData.name.trim().toLocaleLowerCase() ? modelData.genericName.trim() : ""
                    // Check both names: a missing fallback must not reach the image provider.
                    // Quickshell 0.3.2 iconPath(name, true) returns "" for absent icons.
                    readonly property string appIcon: modelData.icon ? Quickshell.iconPath(modelData.icon, true) : ""
                    readonly property string fallbackIcon: appIcon ? "" : Quickshell.iconPath("application-x-executable", true)
                    Ui.PixelAppIcon {
                        id:icon
                        anchors {left:parent.left;leftMargin:12;verticalCenter:parent.verticalCenter}
                        size:Ui.Tokens.launcherIcon;highlighted:row.emphasized;appName:row.modelData.name;iconName:row.modelData.icon || "";originalSource:row.appIcon || row.fallbackIcon
                    }
                    Column {
                        anchors { left: icon.right; leftMargin:Ui.Tokens.spaceMd; right: parent.right; rightMargin: 38; verticalCenter: parent.verticalCenter }
                        spacing: 1
                        Text {
                            width: parent.width
                            text: row.modelData.name
                            textFormat: Text.PlainText
                            color: row.emphasized ? colors.primaryContainerText : colors.text
                            elide: Text.ElideRight
                            font { family: colors.font; pixelSize:Ui.Tokens.body; weight: Font.Medium }
                        }
                        Text {
                            visible: text.length > 0
                            width: parent.width
                            text: row.subtitle
                            textFormat: Text.PlainText
                            color: row.emphasized ? colors.primaryContainerText : colors.muted
                            elide: Text.ElideRight
                            font { family: colors.font; pixelSize:Ui.Tokens.caption }
                        }
                    }
                    Ui.PixelIcon {anchors {right:parent.right;rightMargin:12;verticalCenter:parent.verticalCenter} opacity:row.ListView.isCurrentItem ? 1 : 0;visible:opacity>0;name:"chevron_right";size:18;color:colors.primaryContainerText;Behavior on opacity {NumberAnimation {duration:Ui.Tokens.state}}}
                    MouseArea {
                        id:rowMouse;hoverEnabled:true
                        anchors.fill: parent
                        onClicked: root.launch(row.index)
                    }
                }
            }
            Column {
                objectName:"launcher-empty"
                visible: !root.showHome && root.results.length === 0
                width: parent.width
                height:72;spacing:8;topPadding:4
                Ui.PixelIcon {anchors.horizontalCenter:parent.horizontalCenter;name:"search";size:24;color:colors.muted}
                Text {width:parent.width;text:"Ничего не найдено";horizontalAlignment:Text.AlignHCenter;color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body}}
            }
            Item {
                width: parent.width
                height: 20
                Row {
                    anchors { left: parent.left; leftMargin:Ui.Tokens.spaceXs; right: resultCount.left; rightMargin:Ui.Tokens.spaceMd; verticalCenter: parent.verticalCenter }
                    spacing:Ui.Tokens.spaceSm
                    Ui.Keycap {text:root.showHome ? "← ↑ ↓ → / Tab" : "↑ ↓ / Tab"}
                    Ui.Keycap {text:"Enter"}
                    Text {text:"открыть";color:colors.muted;font {family:colors.font;pixelSize:Ui.Tokens.caption} anchors.verticalCenter:parent.verticalCenter}
                    Ui.Keycap {text:"Esc"}
                }
                Text {
                    id: resultCount
                    anchors { right: parent.right; rightMargin:Ui.Tokens.spaceXs; verticalCenter: parent.verticalCenter }
                    visible:!root.showHome
                    text: root.showHome ? "" : "Найдено: "+root.results.length
                    color: colors.accent
                    font { family: colors.font; pixelSize:Ui.Tokens.caption; weight: Font.Medium }
                }
            }
        }
    }
}
