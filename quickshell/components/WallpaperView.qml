pragma ComponentBehavior: Bound

import QtQuick
import "../modules/system" as System
import "../ui" as Ui
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import "../theme" as Theme

Rectangle {
    id: root
    objectName: "pixelrail-wallpaper-view"
    required property var entries
    required property string backend
    property bool busy: false
    property string error: ""
    property string activeCategory: "all"
    property int selectionIndex: entries.length ? 0 : -1
    readonly property var selected: selectionIndex >= 0 && selectionIndex < entries.length ? entries[selectionIndex] : null
    property var thumbnails: ({})
    property var failures: ({})
    property var missingCached:({})
    property string activeId: ""
    signal queryChanged(string text)
    signal categoryChanged(string category)
    signal applyRequested(int index)
    signal closeRequested()
    readonly property string selectedUrl: selected ? (thumbnails[selected.id] || (!missingCached[selected.id] ? selected.thumbnail : "") || "") : ""
    readonly property bool canApply: selected !== null && selectedUrl !== "" && !failures[selected.id] && !busy
    onEntriesChanged: { selectionIndex = entries.length ? 0 : -1; schedule(); }
    onSelectionIndexChanged: schedule()
    radius: Ui.Tokens.radiusPanel
    color: colors.background
    border { width: 1; color: colors.outlineVariant }
    Theme.Palette { id: colors }

    // One thumbnail job at a time. Recalculate demand from the current viewport,
    // so rapid scrolling cannot queue hundreds of abandoned image decodes.
    function retryThumbnail(id):void {
        if(missingCached[id]) {failures=Object.assign({},failures,{[id]:"Превью недоступно"});return;}
        missingCached=Object.assign({},missingCached,{[id]:true});
        const next=Object.assign({},thumbnails);delete next[id];thumbnails=next;
        schedule();
    }
    function focusSearch(): void { search.forceActiveFocus(); }
    function schedule(): void { Qt.callLater(pump); }
    function pump(): void {
        if (worker.running) return;
        const columns = Math.max(1, Math.floor(grid.width / grid.cellWidth));
        const first = Math.max(0, Math.floor(grid.contentY / grid.cellHeight) * columns);
        const last = Math.min(entries.length, first + (Math.ceil(grid.height / grid.cellHeight) + 1) * columns);
        const demand = selected ? [selected] : [];
        for (let i = first; i < last; ++i) demand.push(entries[i]);
        const next = demand.find(entry => !thumbnails[entry.id] && !(entry.thumbnail && !missingCached[entry.id]) && !failures[entry.id]);
        if (!next) return;
        activeId = next.id;
        worker.command = [backend, "thumbnail", "wallpaper"];
        worker.running = true;
    }
    function move(delta: int): void {
        if (!entries.length) return;
        selectionIndex = (selectionIndex + delta + entries.length) % entries.length;
        grid.positionViewAtIndex(selectionIndex, GridView.Contain);
    }
    function key(event): void {
        const columns = Math.max(1, Math.floor(grid.width / grid.cellWidth));
        if (event.key === Qt.Key_Left) move(-1);
        else if (event.key === Qt.Key_Right) move(1);
        else if (event.key === Qt.Key_Up) move(-columns);
        else if (event.key === Qt.Key_Down) move(columns);
        else if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && (event.modifiers & Qt.ControlModifier)) {
            if (canApply) applyRequested(selectionIndex);
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) preview.forceActiveFocus();
        else return;
        event.accepted = true;
    }
    Shortcut {
        sequence: "Escape"
        context: Qt.WindowShortcut
        enabled: root.visible && root.enabled && !System.ScreenshotState.active
        onActivated: root.closeRequested()
    }
    Component.onCompleted: { search.forceActiveFocus(); schedule(); }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: write(JSON.stringify({id: root.activeId}) + "\n")
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (data.url) root.thumbnails = Object.assign({}, root.thumbnails, {[root.activeId]: data.url});
                    else root.failures = Object.assign({}, root.failures, {[root.activeId]: data.error || "Ошибка изображения"});
                } catch (exception) { root.failures = Object.assign({}, root.failures, {[root.activeId]: "Ошибка превью"}); }
            }
        }
        onExited: (code, status) => {
            if (code !== 0) root.failures = Object.assign({}, root.failures, {[root.activeId]: "Ошибка превью"});
            root.schedule();
        }
    }
    ColumnLayout {
        anchors { fill: parent; margins:Ui.Tokens.space }
        spacing:Ui.Tokens.spaceMd
        Text {
            Layout.fillWidth: true
            text: "Обои"; color: colors.text
            font { family: colors.font; pixelSize:Ui.Tokens.controlTitle; weight: Font.Medium }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing:Ui.Tokens.spaceSm
            Repeater {
                model: [{title: "Все", kind: "all"}, {title: "Обои", kind: "wallpapers"},
                        {title: "Загрузки", kind: "downloads"}, {title: "Скриншоты", kind: "screenshots"}]
                delegate: Button {
                    id: chip
                    required property var modelData
                    objectName: "wallpaper-chip-" + modelData.kind
                    readonly property bool selected: root.activeCategory === modelData.kind
                    implicitHeight: 36
                    implicitWidth: contentItem.implicitWidth + leftPadding + rightPadding
                    Layout.minimumHeight: 36
                    Layout.maximumHeight: 36
                    leftPadding: 14; rightPadding: 14
                    topPadding: 0; bottomPadding: 0
                    hoverEnabled: true
                    Accessible.checkable: true
                    Accessible.checked: selected
                    text: modelData.title
                    onClicked: root.categoryChanged(modelData.kind)
                    contentItem: Text {
                        text: chip.text; color: chip.selected || chip.down ? colors.selectedText : colors.muted
                        font { family: colors.font; pixelSize:Ui.Tokens.body; weight: Font.Medium }
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: height / 2
                        color: chip.down ? Qt.tint(colors.selected, Qt.alpha(colors.accent, 0.18))
                             : chip.selected ? colors.selected
                             : chip.hovered ? Qt.tint(colors.surfaceContainer, Qt.alpha(colors.accent, 0.10)) : colors.surfaceContainer
                        border.width: 1
                        border.color: chip.selected ? Qt.alpha(colors.accent, 0.65) : colors.outlineVariant
                    }
                }
            }
            Item { Layout.fillWidth: true }
        }
        TextField {
            id: search
            objectName: "wallpaper-search"
            Layout.fillWidth: true
            implicitHeight: Ui.Tokens.launcherSearchHeight
            placeholderText: "Поиск по имени или папке…"
            color: colors.text; placeholderTextColor: colors.muted; selectionColor: colors.selected; selectedTextColor: colors.selectedText
            font { family: colors.font; pixelSize:Ui.Tokens.body }
            leftPadding: 48;rightPadding:Ui.Tokens.space
            onTextChanged: root.queryChanged(text)
            Keys.onPressed: event => root.key(event)
            background: Rectangle { radius:Ui.Tokens.radiusPill;color:colors.surfaceHigh;border.width:search.activeFocus ? 1 : 0;border.color:colors.accent }
            Ui.PixelIcon {anchors {left:parent.left;leftMargin:Ui.Tokens.space;verticalCenter:parent.verticalCenter} name:"search";size:22;color:colors.muted}
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing:Ui.Tokens.space
            GridView {
                id: grid
                objectName: "wallpaper-grid"
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.preferredWidth: root.width * 0.64
                clip: true; cacheBuffer: 0
                ScrollBar.vertical: ScrollBar {policy:ScrollBar.AlwaysOff}
                cellWidth: width / Math.max(1, Math.floor(width / 180))
                cellHeight: 152
                model: root.entries
                boundsBehavior: Flickable.StopAtBounds
                onContentYChanged: root.schedule()
                onWidthChanged: root.schedule()
                onHeightChanged: root.schedule()
                Keys.onPressed: event => root.key(event)
                delegate: Item {
                    id: tile
                    required property var modelData
                    required property int index
                    width: grid.cellWidth; height: grid.cellHeight
                    Rectangle {
                        objectName:"wallpaper-tile-"+tile.index
                        anchors { fill: parent; rightMargin:Ui.Tokens.spaceSm; bottomMargin:Ui.Tokens.spaceSm }
                        radius:Ui.Tokens.radiusLg
                        color: root.selectionIndex === tile.index ? colors.selected : hover.hovered ? colors.surfaceContainerHigh : colors.surfaceContainer
                        border.width:root.selectionIndex === tile.index ? 2 : 0
                        border.color:colors.accent
                        Image {
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins:Ui.Tokens.spaceSm }
                            height: parent.height - 40
                            source: root.thumbnails[tile.modelData.id] || (!root.missingCached[tile.modelData.id] ? tile.modelData.thumbnail : "") || ""
                            onStatusChanged:if(status===Image.Error)root.retryThumbnail(tile.modelData.id)
                            sourceSize { width: 256; height: 144 }
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true; cache: false
                        }
                        Rectangle {
                            anchors {top:parent.top;right:parent.right;margins:Ui.Tokens.spaceMd}
                            visible:root.selectionIndex===tile.index
                            width:24;height:24;radius:12;color:colors.accent
                            Ui.PixelIcon {anchors.centerIn:parent;name:"check";size:18;color:colors.primaryText}
                        }
                        Text {
                            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins:Ui.Tokens.spaceMd }
                            text: tile.modelData.title; textFormat: Text.PlainText
                            color: root.selectionIndex === tile.index ? colors.selectedText : colors.text; elide: Text.ElideMiddle
                            font { family: colors.font; pixelSize:Ui.Tokens.label }
                        }
                        MouseArea { id:tileClick;anchors.fill: parent; onClicked: { root.selectionIndex = tile.index; grid.forceActiveFocus(); } }
                        scale:tileClick.pressed ? .98 : 1
                        Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
                        ToolTip.visible: hover.hovered
                        ToolTip.text: tile.modelData.title
                        HoverHandler { id: hover }
                    }
                }
                ColumnLayout {
                    anchors.centerIn: parent
                    width:Math.max(0,parent.width-Ui.Tokens.space*2)
                    visible: root.entries.length === 0
                    spacing:Ui.Tokens.spaceMd
                    Ui.PixelIcon {Layout.alignment:Qt.AlignHCenter;name:"wallpaper";size:32;color:colors.accent}
                    Text {Layout.fillWidth:true;text:root.busy ? "Загрузка…" : "Изображения не найдены";wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium}}
                    Text {Layout.fillWidth:true;text:"Выберите другую вкладку или измените поиск";wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;color:colors.muted;font {family:colors.font;pixelSize:Ui.Tokens.label}}
                }
            }
            Rectangle {
                id: preview
                objectName: "wallpaper-preview"
                Layout.preferredWidth: Math.max(220, root.width * 0.32)
                Layout.fillHeight: true
                radius:Ui.Tokens.radiusLg; color: colors.surfaceHigh
                focus: false
                Keys.onPressed: event => root.key(event)
                ColumnLayout {
                    anchors { fill: parent; margins:Ui.Tokens.spaceMd }
                    spacing:Ui.Tokens.spaceMd
                    Image {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        source: root.selectedUrl
                        onStatusChanged:if(status===Image.Error && root.selected)root.retryThumbnail(root.selected.id)
                        sourceSize { width: 512; height: 384 }
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true; cache: false
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.selected ? root.selected.title : "Выберите изображение"
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere; maximumLineCount: 2; elide: Text.ElideMiddle
                        color: colors.text; font { family: colors.font; pixelSize:Ui.Tokens.body; weight: Font.Medium }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.selected ? root.selected.subtitle : ""
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle; color: colors.muted
                        font { family: colors.font; pixelSize:Ui.Tokens.caption }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: root.selected !== null && !!root.failures[root.selected.id]
                        text: root.selected ? root.failures[root.selected.id] || "" : ""
                        wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight
                        color: colors.accent; font { family: colors.font; pixelSize:Ui.Tokens.label }
                    }
                    Button {
                        id: applyButton
                        objectName:"wallpaper-apply"
                        Layout.fillWidth: true
                        implicitHeight:38
                        hoverEnabled:true
                        text: root.busy ? "Применение…" : "Применить"
                        enabled: root.canApply
                        onClicked: root.applyRequested(root.selectionIndex)
                        contentItem: Text {
                            text: applyButton.text; color: applyButton.down ? colors.primaryContainerText : applyButton.enabled ? colors.primaryText : colors.selectedText
                            font { family: colors.font; pixelSize:Ui.Tokens.body; weight: Font.Medium }
                            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {radius:Ui.Tokens.radiusPill;color:applyButton.down ? colors.primaryContainer : applyButton.enabled ? colors.accent : colors.selected;border.width:applyButton.visualFocus ? 2 : 0;border.color:colors.text}
                    }
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.error || "Стрелки — выбор   ·   Enter — просмотр   ·   Ctrl+Enter — применить   ·   Esc — закрыть"
            color: root.error ? colors.error : colors.muted
            textFormat: Text.PlainText; elide: Text.ElideRight
            font { family: colors.font; pixelSize:Ui.Tokens.caption }
        }
    }
}
