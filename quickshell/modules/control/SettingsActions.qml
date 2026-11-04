import QtQuick
import Quickshell
import Quickshell.Io
Scope {
    id:root
    property var pending:({})
    property string error:""
    property string output:""
    property string helperDirectory:Quickshell.env("PIXELRAIL_SCRIPTS") || Quickshell.shellPath("../scripts")
    readonly property bool busy:job.running
    function request(kind,value):void {
        if(!["mode","accent","profile","panel","notifications","iconStyle","animations"].includes(kind))return;
        pending=Object.assign({},pending,{[kind]:value});Qt.callLater(run);
    }
    function run():void {
        if(job.running)return;
        const keys=Object.keys(pending);if(!keys.length)return;
        const kind=keys[0],value=pending[kind],copy=Object.assign({},pending);delete copy[kind];pending=copy;
        const commands={mode:["pixelrail-theme","mode"],accent:["pixelrail-theme","accent"],profile:["pixelrail-profile"],panel:["pixelrail-panel","mode"],notifications:["pixelrail-notifications","mode"],iconStyle:["pixelrail-theme","ui","iconStyle"],animations:["pixelrail-theme","ui","animations"]};
        const args=commands[kind];job.command=[helperDirectory+"/"+args[0]].concat(args.slice(1),[value]);output="";error="";job.running=true;
    }
    Process {id:job;stdout:StdioCollector {onStreamFinished:root.output=text} stderr:StdioCollector {onStreamFinished:if(text.trim())root.output=text} onExited:(code,status)=>{if(code)root.error="Не удалось применить настройку: "+root.output.slice(0,180);Qt.callLater(root.run);}}
}
