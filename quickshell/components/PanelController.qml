pragma ComponentBehavior: Bound
import QtQuick
import Quickshell

Scope {
    id: root
    property bool enabledPanel: false
    property int fallbackInset: 66
    property string monitorName: ""
    signal launcherRequested()
    signal powerRequested()
    signal sectionRequested(string section)
    signal dndRequested()
    readonly property bool prepared: sidebar.status === Loader.Ready && sidebar.item !== null
    readonly property var window: prepared ? sidebar.item : null
    readonly property bool showing: prepared && sidebar.item.visible
    readonly property var targetScreen: prepared ? sidebar.item.targetScreen : null
    function prepare(): void { sidebar.active = true; }
    function show(): bool { if (!prepared || !sidebar.item.targetScreen) return false; fallbackInset = 0; enabledPanel = true; return true; }
    function hide(): void { enabledPanel = false; fallbackInset = 0; sidebar.active = false; }
    function state(): string {
        return JSON.stringify({prepared: prepared, visible: !!(prepared && sidebar.item.visible),
            enabled: enabledPanel, error: sidebar.status === Loader.Error ? "Не удалось загрузить Sidebar" : "",
            screen: prepared && sidebar.item.targetScreen ? sidebar.item.targetScreen.name : "",
            exclusiveZone: prepared ? sidebar.item.exclusiveZone : 0});
    }
    Loader {
        id: sidebar
        active: false
        source: "../modules/sidebar/Sidebar.qml"
        onLoaded: {
            item.enabledPanel = Qt.binding(() => root.enabledPanel);
            item.monitorName = Qt.binding(() => root.monitorName);
            item.launcherRequested.connect(root.launcherRequested);
            item.powerRequested.connect(root.powerRequested);
            item.sectionRequested.connect(root.sectionRequested);
            item.dndRequested.connect(root.dndRequested);
        }
    }
}
