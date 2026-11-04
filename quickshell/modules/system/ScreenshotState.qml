pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Scope {
    id:root
    property string helper:Quickshell.env("PIXELRAIL_SHOT_HELPER") || Quickshell.shellPath("../scripts/pixelrail-shot")
    property string phase:"idle"
    // A pending/failed QProcess start must never take away Escape or keyboard focus.
    readonly property bool active:worker.running && Number(worker.processId)>0 && (phase==="arming" || phase==="capturing")
    property string error:""
    property string outcome:""
    property int generation:0
    property int lastExit:0
    property int startupTimeout:5000
    property int captureTimeout:300000
    property int stopTimeout:500
    function capture():bool {
        if(phase!=="idle" || worker.running)return false;
        stopper.stop();
        error="";outcome="";lastExit=0;++generation;
        // Arm guards BEFORE any operation that can fail or throw.
        startup.restart();deadline.restart();phase="starting";
        try {
            worker.command=[helper,"--capture-worker","--handshake"];
            worker.running=true;
        } catch(exception) {fail("Запуск screenshot worker: "+exception);}
        return phase!=="idle";
    }
    function finish():void {
        startup.stop();deadline.stop();stopper.stop();++generation;phase="idle";
    }
    function fail(message:string):void {
        error=message;console.warn("PixelRail screenshot:",message);abort();
    }
    function stopWorker(signum:int):void {
        if(!worker.running)return;
        // Never pass an invalid/zero PID to a signal operation during startup.
        if(Number(worker.processId)>0)worker.signal(signum);
        else worker.running=false;
    }
    function abort():void {
        // Fail open immediately, even if the worker ignores TERM or exits without
        // the expected signal. The finite escalation only targets this Process.
        startup.stop();deadline.stop();++generation;phase="idle";
        if(worker.running) {stopper.restart();stopWorker(15);}
        else stopper.stop();
    }
    function reset():void {outcome="reset";abort();}
    function message(line:string):void {
        let value;
        try {value=JSON.parse(line);} catch(exception) {fail("Некорректный ответ screenshot worker");return;}
        if(!value || typeof value!=="object") {fail("Некорректный ответ screenshot worker");return;}
        if(value.event==="ready" && phase==="starting") {
            phase="arming";const serial=generation;
            // Publish suppression/release grabs before allowing slurp to start.
            Qt.callLater(()=>{
                if(root.generation!==serial || root.phase!=="arming")return;
                try {worker.write("capture\n");}
                catch(exception) {root.fail("Screenshot handshake: "+exception);}
            });
        } else if(value.event==="selecting" && phase==="arming") {startup.stop();phase="capturing";}
        else if(value.event==="cancelled" || value.event==="saved")outcome=value.event;
    }
    function state():string {
        return JSON.stringify({active:active,phase:phase,pid:Number(worker.processId) || 0,
            running:worker.running,generation:generation,helper:helper,error:error,outcome:outcome,lastExit:lastExit,
            startupGuard:startup.running,watchdog:deadline.running,stopping:stopper.running});
    }
    Timer {id:startup;interval:root.startupTimeout;onTriggered:root.fail("Screenshot worker не подтвердил готовность: "+root.helper)}
    Timer {id:deadline;interval:root.captureTimeout;onTriggered:root.fail("Захват прерван по аварийному лимиту")}
    Timer {id:stopper;interval:root.stopTimeout;onTriggered:{root.stopWorker(9);root.phase="idle";}}
    Process {
        id:worker
        stdinEnabled:true
        stdout:SplitParser {onRead:data=>root.message(data)}
        stderr:StdioCollector {onStreamFinished:if(text.trim()) {root.error=text.trim().slice(0,1000);console.warn("PixelRail screenshot:",root.error);}}
        onExited:(code,status)=>{
            root.lastExit=code;
            if(code && !root.error && !stopper.running)root.error="Screenshot worker завершился с ошибкой (exit "+code+", status "+status+")";
            root.finish();
        }
        onRunningChanged:if(!running && root.phase!=="idle") {
            const serial=root.generation;
            Qt.callLater(()=>{
                if(root.generation===serial && !worker.running && root.phase!=="idle") {
                    if(root.phase==="starting" && !root.error)root.error="Не удалось запустить screenshot worker: "+root.helper;
                    root.finish();
                }
            });
        }
    }
}
