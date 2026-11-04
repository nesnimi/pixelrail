pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import "modules/launcher"
import "components"
import "theme" as Theme
import "modules/notifications" as Notifications
import "modules/system" as System

ShellRoot {
    id: shell
    signal wallpaperChanged(string path)
    onWallpaperChanged: path => Theme.ThemeManager.requestSync()
    Launcher { id: launcher }
    readonly property int sideOffset: panel.showing ? 78 : panel.fallbackInset + 12
    Binding {target:launcher;property:"sideOffset";value:panel.showing && launcher.screen!==panel.targetScreen ? 12 : shell.sideOffset}
    Binding {target:launcher;property:"allowedWindow";value:panel.window}
    Notifications.NotificationController {id:notifications}
    System.OsdController {
        id:osd;system:System.SystemControls;sideOffset:shell.sideOffset;targetScreen:panel.targetScreen
        suppressed:control.opened || launcher.opened || launcher.visible || shell.pendingControl!=="" || shell.pendingMenu!=="" || !!(menus.item && (menus.item.opened || menus.item.visible))
    }
    function resumeSession():void {
        pendingControl="";pendingMenu="";control.close();launcher.close();
        if(menus.item)menus.item.closeForReplacement();osd.cancel();notifications.popups=[];
        System.SystemControls.refreshBrightness();Theme.ThemeManager.requestSync();
    }
    Connections {target:System.SessionState;function onResumed(){shell.resumeSession();}}
    Connections {target:Quickshell;function onScreensChanged(){shell.resumeSession();}}
    IpcHandler {
        target:"screenshot"
        function capture():bool {return System.ScreenshotState.capture();}
        function abort():void {System.ScreenshotState.abort();}
        function reset():void {System.ScreenshotState.reset();}
        function state():string {return System.ScreenshotState.state();}
    }
    IpcHandler {
        target:"system"
        function action(value:string):bool {return System.SystemControls.action(value);}
        function refresh():void {System.SystemControls.refreshBrightness();}
        function state():string {const value=JSON.parse(System.SystemControls.state());value.backlightEvents=System.SystemControls.backlightEvents;value.osd={opened:osd.opened,loaded:osd.loaded,kind:osd.kind,suppressed:osd.suppressed};return JSON.stringify(value);}
    }
    ControlController {
        id:control
        sideOffset:shell.sideOffset;targetScreen:panel.targetScreen;notifier:notifications;allowedWindow:panel.window
        onCloseRequested:control.requestClose()
        onPowerRequested:{control.close();shell.openMenu("power");}
        onMenuRequested:mode=>{control.close();shell.openMenu(mode);}
    }
    Loader {
        active:notifications.enabled && notifications.popups.length>0 && !control.opened && !launcher.visible && !(menus.item && menus.item.visible)
        sourceComponent:Component {Notifications.NotificationPopups {manager:notifications;sideOffset:shell.sideOffset;targetScreen:panel.targetScreen;onOpenRequested:shell.openControl("notifications");}}
    }
    property string pendingControl: ""
    property string pendingMenu:""
    Connections {
        target:launcher
        function onVisibleChanged():void {
            if(!launcher.visible && shell.pendingMenu) {
                const kind=shell.pendingMenu;shell.pendingMenu="";shell.openMenu(kind);
            } else if(!launcher.visible && shell.pendingControl) {
                const section=shell.pendingControl;shell.pendingControl="";control.toggle(section);
            }
        }
    }
    function openControl(section:string):void {
        section=section || "overview";
        pendingMenu="";
        if(menus.item)menus.item.closeForReplacement();notifications.popups=[];
        if(launcher.visible) {pendingControl=section;launcher.close();}
        else {pendingControl="";launcher.close();control.toggle(section);}
    }
    function toggleLauncher():void {pendingControl="";pendingMenu="";control.close();if(menus.item)menus.item.closeForReplacement();launcher.toggle();}
    IpcHandler {
        target:"control"
        function open(section:string):void {shell.openControl(section);}
        function settings():void {shell.openControl("settings");}
        function hide():void {shell.pendingControl="";control.close();}
        function state():string {const value=JSON.parse(control.state());value.pending=shell.pendingControl!=="";return JSON.stringify(value);}
    }
    IpcHandler {
        target:"notifications"
        function preflight():void {notifications.warmup();}
        function enable():void {notifications.prepare();}
        function disable():bool {return notifications.stop();}
        function state():string {return notifications.state();}
        function open():void {shell.openControl("notifications");}
        function dnd():void {notifications.toggleDnd();}
    }
    PanelController {
        id: panel
        onLauncherRequested:shell.toggleLauncher()
        onPowerRequested: shell.openMenu("power")
        onSectionRequested: section=>shell.openControl(section)
        onDndRequested: {if(notifications.enabled)notifications.toggleDnd();else Quickshell.execDetached(["swaync-client","-d","-sw"]);}
    }
    IpcHandler {
        target: "panel"
        function inset(value:int):void {panel.fallbackInset=Math.max(0,Math.min(200,value));}
        function prepare(monitor: string): void { panel.monitorName = monitor; panel.prepare(); }
        function activate(): bool { return panel.show(); }
        function hide(): void { panel.hide(); }
        function state(): string { return panel.state(); }
    }
    Loader {
        id: menus
        active: false
        sourceComponent: Component {
            MenuPanel {
                sideOffset:panel.showing && screen!==panel.targetScreen ? 12 : shell.sideOffset
                allowedWindow:panel.window
                onDismissed: Qt.callLater(() => { if (menus.item && !menus.item.opened && !menus.item.visible) menus.active = false; })
                onApplicationsRequested: shell.toggleLauncher()
                onWallpaperChanged: path => shell.wallpaperChanged(path)
            }
        }
    }
    function openMenu(kind: string): bool {
        if (!["keys", "clipboard", "command", "windows", "controls", "power", "wallpaper", "media", "emoji"].includes(kind)) return false;
        pendingControl="";control.close();
        if(launcher.visible){pendingMenu=kind;launcher.close();return true;}
        pendingMenu="";
        if (menus.item && menus.item.opened && menus.item.mode === kind) {
            menus.item.close();
        } else {
            menus.active = true;
            menus.item.showMenu(kind);
        }
        return true;
    }
    IpcHandler {
        target: "theme"
        function reload(): void { Theme.ThemeManager.reload(); }
        function refresh(): void { Theme.ThemeManager.requestSync(); }
        function state(): string {
            return JSON.stringify({configuredMode: Theme.ThemeManager.configuredMode, mode: Theme.ThemeManager.mode,
                primary: Theme.ThemeManager.primary, busy: Theme.ThemeManager.busy, error: Theme.ThemeManager.lastError});
        }
    }
    IpcHandler {
        target: "launcher"
        function state():string {return JSON.stringify({opened:launcher.opened,visible:launcher.visible,results:launcher.results.length});}
        function toggle(): void {
            shell.toggleLauncher();
        }
        function hide(): void { launcher.close(); }
    }
    IpcHandler {
        target: "menus"
        function open(kind: string): bool { return shell.openMenu(kind); }
        function hide(): void { shell.pendingMenu="";if (menus.item) menus.item.close(); }
        function status(): string { return menus.item ? menus.item.mode : "unloaded"; }
        function state():string {return JSON.stringify({pending:shell.pendingMenu!=="",mode:menus.item ? menus.item.mode : "unloaded",opened:!!(menus.item && menus.item.opened),busy:!!(menus.item && menus.item.busy),error:menus.item ? menus.item.error : ""});}
    }
}
