pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
Scope {
    id:root
    property bool opened:false
    property int revision:0
    property string section:"overview"
    readonly property string mode:section==="notifications" ? "notifications" : "quick-settings"
    readonly property var window:loader.item
    property int sideOffset:12
    property var targetScreen:null
    property var notifier:null
    property var allowedWindow:null
    signal closeRequested()
    signal powerRequested()
    signal menuRequested(string mode)
    function open(value):void {revision++;section=value || "overview";opened=true;loader.active=true;if(loader.item)loader.item.selectSection(section);}
    function close():void {revision++;opened=false;loader.active=false;}
    function requestClose():void {
        if(!opened)return;
        const requestedRevision=revision;
        // Defer unloading out of a Window binding/signal, but never let an old
        // close request close a panel reopened by a newer IPC/user action.
        Qt.callLater(()=>{if(root.opened && root.revision===requestedRevision)root.close();});
    }
    function toggle(value):void {
        const target=value || "overview";
        if(opened && (section===target || (target==="overview" && mode==="quick-settings")))close();else open(target);
    }
    function state():string {return JSON.stringify({opened:opened,section:section,mode:mode,loaded:loader.status===Loader.Ready,error:loader.status===Loader.Error ? "Control Center не загрузился" : ""});}
    Connections {target:loader.item;function onSectionChanged(){if(loader.item)root.section=loader.item.section;}}
    Loader {
        id:loader;active:false;source:"../modules/control/ControlCenter.qml"
        onLoaded:{item.opened=Qt.binding(()=>root.opened);item.section=root.section;item.sideOffset=Qt.binding(()=>root.sideOffset);item.targetScreen=Qt.binding(()=>root.targetScreen);item.notifier=Qt.binding(()=>root.notifier);item.allowedWindow=Qt.binding(()=>root.allowedWindow);item.closeRequested.connect(root.closeRequested);item.powerRequested.connect(root.powerRequested);item.menuRequested.connect(root.menuRequested);item.selectSection(root.section);}
    }
}
