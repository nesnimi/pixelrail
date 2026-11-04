pragma ComponentBehavior: Bound

import QtQuick
import "../modules/system" as System
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import "../theme" as Theme
import "../ui" as Ui
import "../modules/sidebar/SidebarLogic.js" as Apps
import "PopupPlacement.js" as Placement

PanelWindow {
    id: root
    signal dismissed()
    signal applicationsRequested()
    signal wallpaperChanged(string path)
    property string wallpaperCategory: "all"
    property alias searchText: query.text
    property string mode: ""
    property int sideOffset:12
    property var allowedWindow:null
    property var requestedScreen:null
    screen:requestedScreen && Quickshell.screens.includes(requestedScreen) ? requestedScreen : Quickshell.screens[0]
    property string title: ""
    property string error: ""
    property var entries: []
    property var pending: null
    property double actionStarted: 0
    property double fetchStarted: 0
    property string queued: ""
    property bool superseded:false
    property bool opened: false
    property real reveal: opened ? 1 : 0
    property string backend: Quickshell.shellPath("../scripts/pixelrail-menu-data")
    readonly property bool busy: fetch.running || action.running
    readonly property var filtered: {
        const words = query.text.toLocaleLowerCase().trim().split(/\s+/).filter(w => w.length);
        const rows = entries.filter(entry => (mode !== "wallpaper" || wallpaperCategory === "all" || entry.category === wallpaperCategory) && words.every(w => (entry.title + " " + (entry.subtitle || "") + " " + (entry.search || "")).toLocaleLowerCase().includes(w)));
        if (mode === "command" && query.text.trim() && !pending)
            return [{id: query.text, title: "Выполнить: " + query.text, command: query.text}].concat(rows);
        return rows;
    }
    onFilteredChanged: list.currentIndex = filtered.length ? 0 : -1
    visible: !superseded && (opened || reveal > 0)
    onRevealChanged: if (reveal === 0 && !opened && !action.running) dismissed()
    Behavior on reveal { NumberAnimation { duration: Ui.Tokens.panel; easing.type: Easing.OutCubic } }
    color: "transparent"
    anchors {left:true;top:!Placement.bottom(root.mode);bottom:Placement.bottom(root.mode)}
    margins {left:Placement.left(screen.width,root.sideOffset);top:12;bottom:12}
    implicitWidth: Placement.width(mode === "wallpaper" ? 1000 : mode === "clipboard" ? 640 : mode === "keys" ? 700 : 540, screen.width, root.sideOffset)
    implicitHeight: Placement.height((mode === "wallpaper" || mode === "clipboard") ? 620 : 154 + Math.max(1, Math.min(mode === "keys" ? 7 : 5, filtered.length)) * 54 - 4, screen.height)
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.namespace: "pixelrail-menu"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: opened && !System.ScreenshotState.active ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    Theme.Palette { id: colors }
    HyprlandFocusGrab {windows:root.allowedWindow ? [root,root.allowedWindow] : [root];active:root.opened && root.visible && !System.ScreenshotState.active;onCleared:if(!System.ScreenshotState.active)root.close()}

    function showMenu(kind: string): void {
        // Serialized requests keep stale subprocess output out of a different menu.
        if (busy) { queued = kind; return; }
        const monitor = Hyprland.focusedMonitor;
        const target = monitor ? Quickshell.screens.find(s => s.name === monitor.name) : null;
        requestedScreen=target || Quickshell.screens[0];
        mode = kind; wallpaperCategory = "all"; pending = null; entries = []; error = ""; title = "Загрузка…";
        query.text = "";
        superseded=false;
        opened = true;
        if (kind !== "wallpaper" && kind !== "clipboard") query.forceActiveFocus();
        else Qt.callLater(() => { if (wallpaper.item) wallpaper.item.focusSearch(); if (clipboard.item) clipboard.item.focusSearch(); });
        fetchStarted = Date.now();
        fetch.command = [backend, "list", kind];
        fetch.running = true;
    }
    function closeForReplacement():void {superseded=true;close();}
    function close(): void {
        queued = "";
        opened = false;
        if (reveal === 0 && !action.running) dismissed();
    }
    function processDone(): void {
        Qt.callLater(() => {
            if (queued && !busy) {
                const kind = queued; queued = ""; showMenu(kind);
            } else if (!opened && reveal === 0 && !busy) dismissed();
        });
    }
    function move(delta: int): void {
        if (filtered.length) {
            list.currentIndex = (list.currentIndex + delta + filtered.length) % filtered.length;
            list.positionViewAtIndex(list.currentIndex, ListView.Contain);
        }
    }
    function choose(index: int): void {
        if (busy || index < 0 || index >= filtered.length) return;
        if (mode === "keys") return;
        const entry = filtered[index];
        if (pending && entry.id === "cancel") { showMenu("power"); return; }
        actionStarted = Date.now();
        action.request = pending ? {id: pending, confirmed: true} : entry;
        action.command = [backend, "activate", mode];
        action.running = true;
    }
    Process {
        id: fetch
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const parsedAt = Date.now();
                    const data = JSON.parse(text);
                    root.title = data.title || root.mode;
                    root.error = data.error || "";
                    root.entries = data.items || [];
                    if (data.timings) console.info("clipboard list", JSON.stringify(data.timings), "ui_model_ms", Date.now() - parsedAt, "fetch_total_ms", Date.now() - root.fetchStarted);
                } catch (exception) { root.error = "Не удалось прочитать список"; }
            }
        }
        onExited: (code, status) => { if (code !== 0) root.error = "Ошибка загрузки меню"; root.processDone(); }
    }
    Process {
        id: action
        property var request: ({})
        stdinEnabled: true
        onStarted: write(JSON.stringify(request) + "\n")
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (data.timings) console.info("clipboard restore", JSON.stringify(data.timings), "ui_total_ms", Date.now() - root.actionStarted);
                    if (data.error) { root.error = data.error; return; }
                    if (data.wallpaper) root.wallpaperChanged(data.wallpaper);
                    if (!root.opened) return;
                    if (data.confirm) {
                        root.pending = data.confirm; root.title = data.title;
                        query.text = "";
                        root.entries = [{id: "cancel", title: "Отмена"}, {id: "confirm", title: "Подтвердить"}];
                    } else if (data.next === "applications") {
                        root.close(); root.applicationsRequested();
                    } else if (data.next) {
                        // Process.running becomes false at exit; defer navigation one event turn.
                        Qt.callLater(() => { if (root.opened) root.showMenu(data.next); });
                    } else if (!data.keep && !root.queued) root.close();
                } catch (exception) { root.error = "Не удалось выполнить действие"; }
            }
        }
        onExited: (code, status) => { if (code !== 0) root.error = "Ошибка выполнения действия"; root.processDone(); }
    }
    Loader {
        id: wallpaper
        anchors.fill: parent
        active: root.mode === "wallpaper"
        opacity: root.reveal
        enabled: root.opened
        sourceComponent: Component {
            WallpaperView {
                entries: root.filtered
                activeCategory: root.wallpaperCategory
                backend: root.backend
                busy: root.busy
                error: root.error
                onQueryChanged: text => root.searchText = text
                onCategoryChanged: category => root.wallpaperCategory = category
                onApplyRequested: index => root.choose(index)
                onCloseRequested: root.close()
            }
        }
    }
    Loader {
        id: clipboard
        anchors.fill: parent
        active: root.mode === "clipboard"
        opacity: root.reveal
        enabled: root.opened
        sourceComponent: Component {
            ClipboardView {
                entries: root.filtered
                backend: root.backend
                busy: root.busy
                error: root.error
                onQueryChanged: text => root.searchText = text
                onChooseRequested: index => root.choose(index)
                onCloseRequested: root.close()
            }
        }
    }
    Rectangle {
        objectName:"menu-surface"
        visible: root.mode !== "wallpaper" && root.mode !== "clipboard"
        anchors.fill: parent
        radius: Ui.Tokens.radiusPanel
        color: colors.background
        border { width: 1; color: colors.outlineVariant }
        opacity: root.reveal
        enabled: root.opened
        Column {
            anchors { fill: parent; margins:Ui.Tokens.space }
            spacing: 10
            Text {
                width: parent.width
                text: root.title
                textFormat: Text.PlainText
                color: colors.accent
                elide: Text.ElideRight
                font { family: colors.font; pixelSize:Ui.Tokens.section; weight: Font.Medium }
            }
            TextField {
                id: query
                width: parent.width
                height: 56
                placeholderText: root.pending ? "Подтверждение действия…" : "Поиск…"
                color: colors.text
                placeholderTextColor: colors.muted
                selectionColor: colors.selected
                selectedTextColor: colors.selectedText
                font { family: colors.font; pixelSize: 17 }
                leftPadding: 18
                selectByMouse: true
                activeFocusOnTab: false
                background: Rectangle {
                    radius:Ui.Tokens.radiusLg; color: colors.surfaceHigh
                    border { width: 1; color: query.activeFocus ? colors.accent : colors.outlineVariant }
                }
                Keys.onPressed: event => {
                    if (event.key === Qt.Key_Escape && !System.ScreenshotState.active) root.close();
                    else if (event.key === Qt.Key_Down || (event.key === Qt.Key_Tab && !(event.modifiers & Qt.ShiftModifier))) root.move(1);
                    else if (event.key === Qt.Key_Up || event.key === Qt.Key_Backtab || event.key === Qt.Key_Tab) root.move(-1);
                    else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) root.choose(list.currentIndex);
                    else return;
                    event.accepted = true;
                }
            }
            ListView {
                id: list
                width: parent.width
                height: Math.max(0, root.height - 154)
                clip: true
                spacing:Ui.Tokens.spaceXs
                model: (root.mode === "wallpaper" || root.mode === "clipboard") ? [] : root.filtered
                boundsBehavior: Flickable.StopAtBounds
                delegate: Rectangle {
                    id: row
                    required property var modelData
                    required property int index
                    width: list.width; height: 50; radius: Ui.Tokens.radius
                    color: ListView.isCurrentItem ? colors.selected : colors.surfaceContainer
                    readonly property var desktopMatch:root.mode==="windows" ? Apps.application({lastIpcObject:{class:modelData.appClass || ""}},DesktopEntries.applications.values) : null
                    Ui.PixelAppIcon {anchors {left:parent.left;leftMargin:14;verticalCenter:parent.verticalCenter} size:30;visible:root.mode==="windows";appName:row.modelData.appClass || row.modelData.title;iconName:row.desktopMatch && row.desktopMatch.entry ? row.desktopMatch.entry.icon : row.modelData.appClass || ""}
                    Column {
                        anchors { left: parent.left; right: parent.right; margins: 14; leftMargin:root.mode==="windows" ? 56 : 14; verticalCenter: parent.verticalCenter }
                        spacing: 1
                        Text {
                            width: parent.width; text: row.modelData.title; textFormat: Text.PlainText
                            elide: Text.ElideRight; color: row.ListView.isCurrentItem ? colors.selectedText : colors.text
                            font { family: colors.font; pixelSize:Ui.Tokens.body; weight: Font.Medium }
                        }
                        Text {
                            visible: text.length > 0
                            width: parent.width; text: row.modelData.subtitle || ""; textFormat: Text.PlainText
                            elide: Text.ElideRight; color: row.ListView.isCurrentItem ? colors.selectedText : colors.muted
                            font { family: colors.font; pixelSize:Ui.Tokens.caption }
                        }
                    }
                    MouseArea { anchors.fill: parent; onClicked: root.choose(row.index) }
                }
            }
            Text {
                width: parent.width
                text: root.error || (root.busy ? "Загрузка…" : root.filtered.length ? (root.mode === "keys" ? "↑↓ / Tab  выбор   ·   Esc  закрыть" : "↑↓ / Tab  выбор   ·   Enter  открыть   ·   Esc  закрыть") : "Ничего не найдено")
                textFormat: Text.PlainText
                color: root.error ? colors.error : colors.muted
                elide: Text.ElideRight
                font { family: colors.font; pixelSize:Ui.Tokens.caption }
            }
        }
    }
}
