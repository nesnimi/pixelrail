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
    objectName: "pixelrail-clipboard-view"
    required property var entries
    required property string backend
    property bool busy: false
    property string error: ""
    property var thumbnails: ({})
    property var failures: ({})
    property var retries: ({})
    property var activeEntry: null
    signal queryChanged(string text)
    signal chooseRequested(int index)
    signal closeRequested()
    color: colors.background; radius: Ui.Tokens.radiusPanel
    border { width: 1; color: colors.outlineVariant }
    Theme.Palette { id: colors }
    Shortcut {
        sequence: "Escape"; context: Qt.WindowShortcut
        enabled: root.visible && root.enabled && !System.ScreenshotState.active
        onActivated: root.closeRequested()
    }
    function focusSearch(): void { search.forceActiveFocus(); }
    function imageFailed(id: string): void {
        const next = Object.assign({}, thumbnails); delete next[id]; thumbnails = next;
        if (retries[id]) failures = Object.assign({}, failures, {[id]: "Превью недоступно"});
        else { retries[id] = 1; schedule(); }
    }
    function schedule(): void { Qt.callLater(pump); }
    function pump(): void {
        if (worker.running) return;
        const children = list.contentItem.children;
        for (let i = 0; i < children.length; ++i) {
            const card = children[i];
            if (card.objectName !== "clipboard-card" || card.y + card.height <= list.contentY || card.y >= list.contentY + list.height) continue;
            const entry = card.entry;
            if (entry.kind !== "image" || thumbnails[entry.id] || failures[entry.id]) continue;
            activeEntry = entry;
            worker.command = [backend, "thumbnail", "clipboard"];
            worker.running = true;
            break;
        }
    }
    function move(delta: int): void {
        if (!entries.length) return;
        list.currentIndex = (list.currentIndex + delta + entries.length) % entries.length;
        list.positionViewAtIndex(list.currentIndex, ListView.Contain);
    }
    function key(event): void {
        if (event.key === Qt.Key_Up) move(-1);
        else if (event.key === Qt.Key_Down) move(1);
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) root.chooseRequested(list.currentIndex);
        else return;
        event.accepted = true;
    }
    onEntriesChanged: { list.currentIndex = entries.length ? 0 : -1; schedule(); }
    Component.onCompleted: { focusSearch(); schedule(); }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: write(JSON.stringify(root.activeEntry) + "\n")
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(text);
                    if (data.url) root.thumbnails = Object.assign({}, root.thumbnails, {[root.activeEntry.id]: data});
                    else root.failures = Object.assign({}, root.failures, {[root.activeEntry.id]: data.error || "Превью недоступно"});
                } catch (exception) { root.failures = Object.assign({}, root.failures, {[root.activeEntry.id]: "Превью недоступно"}); }
            }
        }
        onExited: (code, status) => {
            if (code !== 0) root.failures = Object.assign({}, root.failures, {[root.activeEntry.id]: "Превью недоступно"});
            root.schedule();
        }
    }
    ColumnLayout {
        anchors { fill: parent; margins:Ui.Tokens.space }
        spacing:Ui.Tokens.spaceMd
        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Буфер обмена"; color: colors.text
                font { family: colors.font; pixelSize:Ui.Tokens.controlTitle; weight: Font.Medium }
            }

        }
        TextField {
            id: search
            objectName: "clipboard-search"
            Layout.fillWidth: true
            implicitHeight: Ui.Tokens.launcherSearchHeight; leftPadding: 48; rightPadding: Ui.Tokens.space
            placeholderText: "Поиск в истории…"
            color: colors.text; placeholderTextColor: colors.muted
            selectionColor: colors.selected; selectedTextColor: colors.selectedText
            font { family: colors.font; pixelSize:Ui.Tokens.body }
            onTextChanged: root.queryChanged(text)
            Keys.onPressed: event => root.key(event)
            background: Rectangle { radius:Ui.Tokens.radiusPill; color: colors.surfaceHigh;border.width:search.activeFocus ? 1 : 0;border.color:colors.accent }
            Ui.PixelIcon {anchors {left:parent.left;leftMargin:Ui.Tokens.space;verticalCenter:parent.verticalCenter} name:"search";size:22;color:colors.muted}
        }
        ListView {
            id: list
            objectName: "clipboard-list"
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root.entries
            spacing:Ui.Tokens.spaceSm; clip: true; cacheBuffer: 0
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {policy:ScrollBar.AlwaysOff}
            onContentYChanged: root.schedule()
            onHeightChanged: root.schedule()
            Keys.onPressed: event => root.key(event)
            delegate: Rectangle {
                id: card
                objectName: "clipboard-card"
                required property var modelData
                required property int index
                readonly property var entry: modelData
                readonly property var thumbnail: root.thumbnails[entry.id] || null
                width: list.width
                height: entry.kind === "image" ? 184 : 84
                radius:Ui.Tokens.radiusLg
                color: ListView.isCurrentItem ? colors.selected : hover.hovered ? Qt.tint(colors.surfaceContainer,Qt.alpha(colors.accent,0.08)) : colors.surfaceContainer
                border.width:card.activeFocus ? 1 : 0; border.color:colors.accent
                Component.onCompleted: root.schedule()
                ColumnLayout {
                    anchors { fill: parent; margins:Ui.Tokens.spaceMd }
                    spacing: Ui.Tokens.spaceSm
                    RowLayout {
                        Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm
                        Ui.PixelIcon {name:card.entry.kind==="image" ? "image" : /^https?:\/\//i.test(card.entry.title) ? "public" : "description";size:22;color:card.ListView.isCurrentItem ? colors.selectedText : colors.muted}
                        Text {
                            Layout.fillWidth:true
                            text:card.entry.title;textFormat:Text.PlainText
                            wrapMode:Text.WrapAnywhere;maximumLineCount:card.entry.kind==="image" ? 1 : 2;elide:Text.ElideRight
                            color:card.ListView.isCurrentItem ? colors.selectedText : colors.text
                            font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium}
                        }
                        Ui.PixelIcon {visible:card.ListView.isCurrentItem;name:"check";size:18;color:colors.selectedText}
                    }
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        visible: card.entry.kind === "image"
                        Image {
                            id: previewImage
                            anchors.fill: parent
                            source: card.thumbnail ? card.thumbnail.url : ""
                            sourceSize { width: 512; height: 256 }
                            asynchronous: true; cache: false
                            fillMode: Image.PreserveAspectFit
                            onStatusChanged: {
                                if (status === Image.Error) root.imageFailed(card.entry.id);
                                else if (status === Image.Ready) root.retries[card.entry.id] = 0;
                            }
                        }
                        Text {
                            anchors.centerIn:parent;width:parent.width
                            visible: previewImage.status !== Image.Ready
                            text: root.failures[card.entry.id] ? "Превью недоступно · оригинал можно скопировать" : "Подготовка превью…"
                            color: card.ListView.isCurrentItem ? colors.selectedText : colors.muted
                            horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap
                            font { family: colors.font; pixelSize:Ui.Tokens.label }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: card.thumbnail ? card.thumbnail.width + "×" + card.thumbnail.height + " · " + card.thumbnail.format : card.entry.kind==="text" ? (/^https?:\/\//i.test(card.entry.title) ? "Ссылка" : "Текст") : card.entry.subtitle
                        textFormat: Text.PlainText; elide: Text.ElideRight
                        color: card.ListView.isCurrentItem ? colors.selectedText : colors.muted
                        font { family: colors.font; pixelSize:Ui.Tokens.caption }
                    }
                }
                HoverHandler { id: hover }
                MouseArea { id:cardClick;anchors.fill: parent; enabled: !root.busy; onClicked: root.chooseRequested(card.index) }
                scale:cardClick.pressed ? .99 : 1
                Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
            }
            ColumnLayout {
                anchors.centerIn: parent
                width:Math.max(0,parent.width-Ui.Tokens.space*2)
                visible: root.entries.length === 0
                spacing:Ui.Tokens.spaceMd
                Ui.PixelIcon {Layout.alignment:Qt.AlignHCenter;name:"content_paste";size:32;color:colors.accent}
                Text {Layout.fillWidth:true;text:root.busy ? "Загрузка…" : search.text ? "Ничего не найдено" : "История пуста";horizontalAlignment:Text.AlignHCenter;color:colors.text;font {family:colors.font;pixelSize:Ui.Tokens.body;weight:Font.Medium}}
                Text {Layout.fillWidth:true;text:search.text ? "Попробуйте другой запрос" : "Скопированный текст и изображения появятся здесь";wrapMode:Text.Wrap;horizontalAlignment:Text.AlignHCenter;color:colors.muted;font {family:colors.font;pixelSize:Ui.Tokens.label}}
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.error || (root.busy ? "Подготовка…" : "↑↓ — выбор   ·   Enter — скопировать   ·   Esc — закрыть")
            textFormat: Text.PlainText; elide: Text.ElideRight
            color: root.error ? colors.error : colors.muted
            font { family: colors.font; pixelSize:Ui.Tokens.caption }
        }
    }
}
