pragma ComponentBehavior: Bound
import QtQuick
import "../../ui" as Ui
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import "../../theme" as Theme
import "SidebarLogic.js" as Logic
import "." as Local

PanelWindow {
    id: root
    property bool enabledPanel: false
    property string monitorName: ""
    signal launcherRequested()
    signal powerRequested()
    signal sectionRequested(string section)
    signal dndRequested()
    readonly property var primaryMonitor: Hyprland.monitors.values.find(monitor => monitor.id === 0) || null
    readonly property var targetScreen: Logic.targetScreen(Quickshell.screens, monitorName, primaryMonitor)
    screen: targetScreen
    visible: enabledPanel && targetScreen !== null
    color: "transparent"
    anchors { left: true; top: true; bottom: true }
    margins { top: 6; bottom: 6 }
    implicitWidth: 66
    exclusiveZone: visible ? 66 : 0
    exclusionMode: visible ? ExclusionMode.Normal : ExclusionMode.Ignore
    WlrLayershell.namespace: "pixelrail-sidebar"
    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    mask: Region { item: rail }
    Theme.Palette { id: colors }
    Local.SidebarServices { id: services }
    readonly property bool compact: height < 650
    readonly property int extent: height < 500 ? Math.max(18, Math.floor((height - 70) / 13)) : compact ? 30 : 36
    readonly property var panelMonitor: targetScreen ? Hyprland.monitors.values.find(monitor => monitor.name === targetScreen.name) || null : null
    readonly property var activeWorkspace: panelMonitor ? panelMonitor.activeWorkspace : null
    readonly property var workspaces: Logic.workspaces(Hyprland.workspaces.values, activeWorkspace)
    readonly property var windows: Logic.windows(Hyprland.toplevels.values, Quickshell.appId, activeWorkspace)
    readonly property var desktopEntries: DesktopEntries.applications.values
    readonly property string helperDirectory: Quickshell.env("PIXELRAIL_SCRIPTS") || Quickshell.shellPath("../scripts")
    function command(args): void { Quickshell.execDetached(args); }
    property var pendingAction: null
    property string actionError: ""
    property string actionOutput: ""
    property string actionStderr: ""
    function switchWorkspace(workspace): void {
        if (!panelMonitor || !workspaces.some(value => value.id === workspace.id)) return;
        pendingAction = {kind: "workspace", workspace: workspace, monitor: panelMonitor.name};
        Qt.callLater(dispatchPending);
    }
    function focusWindow(window): void {
        if (!window || !windows.includes(window)) return; // Closed/moved windows cannot be activated by stale delegates.
        pendingAction = {kind: "window", window: window};
        Qt.callLater(dispatchPending);
    }
    function dispatchPending(): void {
        if (actionJob.running || !pendingAction) return;
        const request = pendingAction;
        pendingAction = null;
        if (request.kind === "window" && !windows.includes(request.window)) return;
        const args = request.kind === "workspace"
            ? Logic.workspaceCommand(request.workspace, request.monitor, Hyprland.usingLua)
            : Logic.windowCommand(request.window, Hyprland.usingLua);
        if (!args.length) return;
        actionError = ""; actionOutput = ""; actionStderr = "";
        actionJob.command = args;
        actionJob.running = true;
    }
    Process {
        id: actionJob
        stdout: StdioCollector { onStreamFinished: root.actionOutput = text.trim() }
        stderr: StdioCollector { onStreamFinished: root.actionStderr = text.trim() }
        onExited: (code, status) => {
            // hyprctl can report a dispatcher error on stdout even with exit code 0.
            if (code !== 0 || !/^(ok\s*)+$/.test(root.actionOutput)) {
                root.actionError = root.actionStderr || root.actionOutput || "Hyprland не выполнил переключение";
                console.warn("Pixel Sidebar:", root.actionError);
            }
            Qt.callLater(root.dispatchPending);
        }
    }
    function appIcon(window): string {
        const match = Logic.application(window, desktopEntries);
        const icon = match.entry ? match.entry.icon : match.key;
        return (icon ? Quickshell.iconPath(icon, true) : "") || Quickshell.iconPath("application-x-executable", true);
    }
    Rectangle {
        id: rail
        anchors { fill: parent; leftMargin: 6; rightMargin: 6 }
        radius: 23; color: colors.surfaceContainer
        border { width: 1; color: colors.outlineVariant }
        ColumnLayout {
            anchors { fill: parent; margins: 6 }
            spacing: root.height < 580 ? 2 : 5
            ColumnLayout {
                id: systemGroup
                Layout.fillWidth: true
                spacing: root.height < 580 ? 2 : 5
                Local.SidebarButton {
                    objectName: "sidebar-power"
                    Layout.fillWidth: true; Layout.preferredHeight: root.extent
                    glyph: "power"; tooltip: "Питание и выход"
                    onClicked: root.powerRequested()
                }
                Local.SidebarButton {
                    objectName: "sidebar-network"
                    Layout.fillWidth: true; Layout.preferredHeight: root.extent
                    glyph: services.networkGlyph; tooltip: services.networkTooltip
                    onClicked: root.sectionRequested("wifi")
                }
                Local.SidebarButton {
                    objectName: "sidebar-battery"
                    Layout.fillWidth: true; Layout.preferredHeight: root.extent
                    label: services.batteryLabel; tooltip: services.batteryTooltip
                    onClicked: root.sectionRequested("battery")
                    attention: services.percent !== null && services.percent <= 10 && !services.charging
                }

            }
            Item { Layout.fillWidth: true; Layout.fillHeight: true }
            Rectangle {Layout.alignment:Qt.AlignHCenter;implicitWidth:24;implicitHeight:1;color:colors.outlineVariant;opacity:Ui.Tokens.dividerOpacity}
                ListView {
                    id: workspaceList
                    objectName: "sidebar-workspaces"
                    Layout.fillWidth: true
                    Layout.preferredHeight: contentHeight
                    implicitHeight: contentHeight
                    visible: count > 0; spacing:Ui.Tokens.spaceXs; clip: true
                    model: root.workspaces
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: false
                    delegate: Local.SidebarButton {
                        required property var modelData
                        objectName: "sidebar-workspace-" + modelData.id
                        width: workspaceList.width; height: root.extent - 4
                        label: modelData.id > 0 ? String(modelData.id) : modelData.name.replace(/^special:/, "").slice(0,2)
                        labelSize: root.extent < 28 ? Ui.Tokens.label : Ui.Tokens.body
                        selected: modelData.active; attention: modelData.urgent; animate: true
                        tooltip: "Рабочий стол " + modelData.name + (root.actionError ? "\n" + root.actionError : "")
                        onClicked: root.switchWorkspace(modelData)
                    }
                }
                Rectangle {visible:appList.count>0;Layout.alignment:Qt.AlignHCenter;implicitWidth:24;implicitHeight:1;color:colors.outlineVariant;opacity:Ui.Tokens.dividerOpacity}
                ListView {
                    id: appList
                    objectName: "sidebar-apps"
                    Layout.fillWidth: true; Layout.preferredHeight: Math.min(contentHeight, Math.max(0, root.height - systemGroup.implicitHeight - workspaceList.contentHeight - root.extent - (root.height < 580 ? 20 : 32))); Layout.minimumHeight: 0; Layout.maximumHeight: 200
                    spacing:Ui.Tokens.spaceXs; clip: true
                    model: root.windows
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Local.SidebarButton {
                        required property var modelData
                        objectName: "sidebar-window-" + modelData.address
                        width: appList.width; height: root.extent
                        readonly property var appMatch:Logic.application(modelData,root.desktopEntries)
                        image: root.appIcon(modelData)
                        appName:appMatch.entry ? appMatch.entry.name : appMatch.key || modelData.title || ""
                        iconName:appMatch.entry ? appMatch.entry.icon : appMatch.key
                        glyph: image ? "" : "app"
                        selected: modelData.activated; attention: modelData.urgent
                        tooltip: (modelData.title || Logic.application(modelData, root.desktopEntries).key || "Окно") + (root.actionError ? "\n" + root.actionError : "")
                        onClicked: root.focusWindow(modelData)
                    }
                }
                Local.SidebarButton {
                    objectName: "sidebar-home"
                    Layout.fillWidth: true; Layout.preferredHeight: root.extent
                    glyph: "home"; selected:true; accented: true; tooltip: "Pixel Launcher"
                    onClicked: root.launcherRequested()
                }
        }
    }
}
