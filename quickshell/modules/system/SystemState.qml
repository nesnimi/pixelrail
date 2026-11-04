pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
Scope {
    id:root
    property var audio:null
    property var sink:null
    property string helper:Quickshell.shellPath("../scripts/pixelrail-desktop")
    readonly property bool audioAvailable:audio!==null
    property string audioError:""
    property var volumeDesired:null
    property var muteDesired:null
    property bool volumeWaiting:false
    property bool muteWaiting:false
    property real expectedVolume:0
    property bool expectedMute:false
    property bool audioOsd:false
    property string volumeOrigin:"slider"
    readonly property bool volumeUiPending:volumePending && volumeOrigin==="slider"
    readonly property bool volumePending:volumeDesired!==null || volumeWaiting
    property string requestedOsdKind:""
    property bool verifyAudioReadback:true
    property bool flushingAudio:false
    property var confirmedAudio:null
    property var confirmedSink:null
    property int audioRevision:0
    property int audioObservation:0
    property bool audioReadPending:false
    property var readSink:null
    property int readRevision:0
    property int readObservation:0
    property var audioReply:null
    readonly property real volume:confirmedAudio && confirmedSink===sink ? confirmedAudio.volume : audio ? audio.volume : 0
    readonly property bool muted:confirmedAudio && confirmedSink===sink ? confirmedAudio.muted : audio ? audio.muted : false
    function observeAudio():void {
        if(!flushingAudio && audioAvailable){audioObservation++;confirmedAudio={volume:audio.volume,muted:audio.muted};confirmedSink=sink;}
        confirmAudio();
    }
    function showAudio():void {
        if(!audioOsd || requestedOsdKind!=="volume")return;
        if(!verifyAudioReadback){audioOsd=false;confirmedAudio={volume:audio.volume,muted:audio.muted};confirmedSink=sink;osdRequested("volume");return;}
        if(confirmedAudio && confirmedSink===sink && Math.abs(confirmedAudio.volume-audio.volume)<.001 && confirmedAudio.muted===audio.muted){audioOsd=false;osdRequested("volume");return;}
        audioReadPending=true;if(!audioReadThrottle.running)audioReadThrottle.start();
    }
    function readAudio():void {
        if(!audioOsd || requestedOsdKind!=="volume"){audioReadPending=false;return;}
        if(audioReader.running || !audioReadPending || !audioAvailable || !sink)return;
        audioReadPending=false;audioReply=null;readSink=sink;readRevision=audioRevision;readObservation=audioObservation;
        audioReader.command=[helper,"audio-state",String(sink.id)];audioReader.running=true;
    }
    function finishAudioRead(code):void {
        if(readSink!==sink || !audioAvailable){if(audioAvailable && audioReadPending && !audioReadThrottle.running)audioReadThrottle.start();return;}
        const hardwareCurrent=audioOsd && requestedOsdKind==="volume";
        if(hardwareCurrent && code===0 && audioReply && audioReply.available && audioReply.node===sink.id){
            if(readObservation===audioObservation){confirmedAudio=audioReply;confirmedSink=sink;}
            if(confirmedAudio){osdRequested("volume");if(readRevision===audioRevision)audioOsd=false;}
        }else if(hardwareCurrent && readRevision===audioRevision){audioError=audioReply && audioReply.error || "Не удалось подтвердить громкость OSD";audioOsd=false;}
        if(audioOsd && requestedOsdKind==="volume")audioReadPending=true;
        if(audioReadPending && !audioReadThrottle.running)audioReadThrottle.start();
    }
    Timer {id:audioReadThrottle;interval:40;onTriggered:root.readAudio()}
    Process {
        id:audioReader
        stdout:StdioCollector {onStreamFinished:{try{root.audioReply=JSON.parse(text);}catch(error){root.audioReply=null;}}}
        onExited:(code,status)=>root.finishAudioRead(code)
    }
    signal osdRequested(string kind)
    function requestVolume(value,finalValue=false,origin="slider",limit=1):bool {
        if(!audioAvailable)return false;
        audioRevision++;if(origin!=="hardware"){confirmedAudio=null;audioReadPending=false;}
        volumeDesired=Math.max(0,Math.min(limit,value));volumeOrigin=origin;audioOsd=origin==="hardware";if(origin==="hardware")requestedOsdKind="volume";audioError="";
        if(finalValue){audioThrottle.stop();flushAudio();}else if(!audioThrottle.running)audioThrottle.start();
        return true;
    }
    function adjustVolume(direction):bool {
        if(!audioAvailable)return false;
        const base=volumeDesired!==null ? volumeDesired : volumeWaiting ? expectedVolume : root.volume;
        return requestVolume(base+direction*.05,false,"hardware",direction>0 ? 1 : Math.max(1,base));
    }
    function mute(origin="slider"):bool {
        if(!audioAvailable)return false;
        audioError="";audioRevision++;if(origin!=="hardware"){confirmedAudio=null;audioReadPending=false;}
        muteDesired=!(muteDesired!==null ? muteDesired : muteWaiting ? expectedMute : root.muted);audioOsd=origin==="hardware";if(origin==="hardware")requestedOsdKind="volume";
        if(!audioThrottle.running)audioThrottle.start();return true;
    }
    function confirmAudio():void {
        if(!audioAvailable)return;
        if(volumeWaiting && Math.abs(audio.volume-expectedVolume)<.005)volumeWaiting=false;
        if(muteWaiting && audio.muted===expectedMute)muteWaiting=false;
        if(!volumeWaiting && !muteWaiting){audioAck.stop();if(audioOsd && requestedOsdKind==="volume" && volumeDesired===null && muteDesired===null){showAudio();}}
    }
    function flushAudio():void {
        if(!audioAvailable)return;
        flushingAudio=true;
        if(volumeDesired!==null){expectedVolume=volumeDesired;volumeWaiting=true;volumeDesired=null;audio.volume=expectedVolume;}
        if(muteDesired!==null){expectedMute=muteDesired;muteWaiting=true;muteDesired=null;audio.muted=expectedMute;}
        flushingAudio=false;confirmAudio();if(volumeWaiting || muteWaiting)audioAck.restart();
    }
    Timer {id:audioThrottle;interval:40;onTriggered:root.flushAudio()}
    Timer {id:audioAck;interval:1000;onTriggered:{root.volumeWaiting=false;root.muteWaiting=false;root.audioOsd=false;root.audioError="Звук: изменение не подтверждено";}}
    Connections {target:root.audio;ignoreUnknownSignals:true;function onVolumesChanged(){root.observeAudio();} function onMutedChanged(){root.observeAudio();}}
    onAudioChanged:{audioRevision++;audioReadPending=false;confirmedAudio=null;confirmedSink=null;audioReadThrottle.stop();audioThrottle.stop();audioAck.stop();volumeDesired=null;muteDesired=null;volumeWaiting=false;muteWaiting=false;audioOsd=false;audioError="";}

    property var brightness:({available:false})
    property var brightnessDesired:null
    property int brightnessSteps:0
    property bool refreshPending:false
    property bool hardwareRefresh:false
    property bool brightnessOsdAllowed:false
    property bool finalBrightness:false
    property bool brightnessWriting:false
    property string brightnessOrigin:"slider"
    property string jobOrigin:""
    property string jobKind:""
    property real jobTarget:0
    property var reply:null
    readonly property bool brightnessPending:brightnessDesired!==null || brightnessWriting || brightnessSteps!==0
    readonly property bool brightnessUiPending:(brightnessDesired!==null && brightnessOrigin==="slider") || (brightnessWriting && jobOrigin==="slider")
    readonly property bool brightnessBusy:brightnessJob.running
    function backlightChanged(hardware=false):void {hardwareRefresh=hardwareRefresh || hardware;if(hardware){brightnessOsdAllowed=true;requestedOsdKind="brightness";}refreshBrightness();}
    function refreshBrightness():void {refreshPending=true;if(!brightnessThrottle.running)brightnessThrottle.start();}
    function requestBrightness(value,finalValue=false,origin="slider"):bool {
        if(!brightness.available)return false;
        brightnessDesired=Math.max(origin==="hardware" ? 0 : 1,Math.min(100,Math.round(value)));brightnessSteps=0;brightnessOrigin=origin;brightnessOsdAllowed=origin==="hardware";if(origin==="hardware")requestedOsdKind="brightness";if(origin==="slider")hardwareRefresh=false;finalBrightness=finalValue;
        if(finalValue){brightnessThrottle.stop();flushBrightness();}else if(!brightnessThrottle.running)brightnessThrottle.start();
        return true;
    }
    function adjustBrightness(direction):bool {
        if(!brightness.available){brightnessOsdAllowed=true;requestedOsdKind="brightness";brightnessSteps=Math.max(-100,Math.min(100,brightnessSteps+direction*5));refreshPending=true;if(!brightnessJob.running){brightnessThrottle.stop();flushBrightness();}return true;}
        const base=brightnessDesired!==null ? brightnessDesired : brightnessJob.running && jobKind==="write" ? jobTarget : brightness.percent;
        return requestBrightness(base+direction*5,false,"hardware");
    }
    function flushBrightness():void {
        if(brightnessJob.running)return;
        reply=null;
        if(brightnessDesired!==null){
            jobTarget=brightnessDesired;brightnessWriting=true;brightnessDesired=null;jobKind="write";jobOrigin=brightnessOrigin;finalBrightness=false;
            brightnessJob.command=[helper,"set-brightness",String(jobTarget)];
        }else if(refreshPending){refreshPending=false;jobKind="read";jobOrigin=hardwareRefresh ? "hardware" : "";hardwareRefresh=false;brightnessJob.command=[helper,"brightness"];}
        else return;
        brightnessJob.running=true;
    }
    function brightnessFinished(code):void {
        if(code!==0 || !reply || !reply.available){brightness=reply || {available:false,error:"Подсветка недоступна"};brightnessDesired=null;brightnessSteps=0;refreshPending=false;hardwareRefresh=false;brightnessOsdAllowed=false;finalBrightness=false;brightnessWriting=false;return;}
        brightness=reply;brightnessWriting=false;
        if(jobOrigin==="hardware" && brightnessOsdAllowed && requestedOsdKind==="brightness")osdRequested("brightness");
        if(brightnessSteps!==0){const steps=brightnessSteps;brightnessSteps=0;brightnessDesired=Math.max(0,Math.min(100,brightness.percent+steps));brightnessOrigin="hardware";finalBrightness=true;}
        if(brightnessDesired!==null || refreshPending){if(finalBrightness)Qt.callLater(flushBrightness);else if(!brightnessThrottle.running)brightnessThrottle.start();}
    }
    Timer {id:brightnessThrottle;interval:40;onTriggered:root.flushBrightness()}
    Process {
        id:brightnessJob
        stdout:StdioCollector {onStreamFinished:{try{root.reply=JSON.parse(text);}catch(error){root.reply={available:false,error:"Не удалось прочитать яркость"};}}}
        onExited:(code,status)=>root.brightnessFinished(code)
    }
    function action(value):bool {
        if(value==="volume-up")return adjustVolume(1);
        if(value==="volume-down")return adjustVolume(-1);
        if(value==="volume-mute")return mute("hardware");
        if(value==="brightness-up")return adjustBrightness(1);
        if(value==="brightness-down")return adjustBrightness(-1);
        return false;
    }
    function state():string {return JSON.stringify({audioAvailable:audioAvailable,volume:audioAvailable ? root.volume : null,muted:audioAvailable ? root.muted : null,audioError:audioError,volumePending:volumePending,brightness:brightness,brightnessPending:brightnessPending,brightnessBusy:brightnessBusy});}
}
