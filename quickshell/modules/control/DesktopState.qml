pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Scope {
    id: root
    property real heightRatio: 0.5
    property bool dnd: false
    property bool loaded: false
    property bool pending: false
    property string error: ""
    readonly property string helper: Quickshell.env("PIXELRAIL_DESKTOP_HELPER") || (Quickshell.env("PIXELRAIL_THEME_HELPER") ? Quickshell.env("PIXELRAIL_THEME_HELPER").replace(/pixelrail-theme$/, "pixelrail-desktop") : "") || Quickshell.shellPath("../scripts/pixelrail-desktop")
    function save(): void { if (!loaded) return; pending=true; Qt.callLater(writePending); }
    function writePending(): void {
        if (writer.running || !pending) return;
        pending=false;writer.command=[helper,"save",JSON.stringify({heightRatio:heightRatio,dnd:dnd})];writer.running=true;
    }
    onDndChanged: save()
    Process {
        id: loader;command:[root.helper,"load"];running:true
        stdout: StdioCollector {onStreamFinished: {
            try {const data=JSON.parse(text);root.heightRatio=Math.max(.3,Math.min(.75,data.heightRatio || .5));root.dnd=data.dnd===true;}
            catch(error) {root.error="Не удалось прочитать настройки Control Center";}
            root.loaded=true;
        }}
    }
    Process {id:writer;onExited:(code,status)=>{if(code)root.error="Не удалось сохранить настройки";Qt.callLater(root.writePending);}}
}
