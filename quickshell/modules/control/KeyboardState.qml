import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import "../system" as System
Scope {
    id:root
    property string helper:DesktopState.helper
    property var state:({available:false,label:"—"})
    property string preferred:""
    property bool pending:false
    property bool togglePending:false
    property string output:""
    function refresh():void {pending=true;if(!debounce.running)debounce.start();}
    function toggle():void {if(!state.available || togglePending)return;togglePending=true;refresh();}
    function run():void {
        if(job.running || !pending)return;
        pending=false;output="";job.command=[helper,togglePending ? "keyboard-toggle" : "keyboard-state",preferred];togglePending=false;job.running=true;
    }
    Timer {id:debounce;interval:40;onTriggered:root.run()}
    Process {
        id:job
        stdout:StdioCollector {onStreamFinished:root.output=text}
        onExited:(code,status)=>{try{root.state=code===0 ? JSON.parse(root.output) : {available:false,label:"—"};}catch(error){root.state={available:false,label:"—"};}if(root.pending)root.refresh();}
    }
    Connections {target:Hyprland;function onRawEvent(event){
        if(event.name==="activelayout"){root.preferred=event.data.split(",")[0];root.refresh();}
        else if(["activewindowv2","focusedmon","focusedmonv2","configreloaded"].includes(event.name))root.refresh();
    }}
    Connections {target:System.SessionState;function onResumed(){root.refresh();}}
    Component.onCompleted:refresh()
}
