import QtQuick
import Quickshell
Scope {
    id:root
    property bool available:false
    property var pending:null
    property string goal:""
    property string error:""
    property int confirmationTimeout:15000
    function request(device):void {
        if(!available || !device){error="Bluetooth недоступен";return;}
        if(pending)return;
        error="";pending=device;goal=device.connected ? "disconnect" : device.paired ? "connect" : "pair";deadline.restart();
        try {if(goal==="disconnect")device.disconnect();else if(goal==="connect")device.connect();else device.pair();confirm();}
        catch(exception){error="Не удалось выполнить действие Bluetooth";pending=null;deadline.stop();}
    }
    function confirm():void {
        if(!pending)return;
        if((goal==="connect" && pending.connected) || (goal==="disconnect" && !pending.connected) || (goal==="pair" && pending.paired)){pending=null;deadline.stop();}
    }
    onAvailableChanged:if(!available && pending){error="Служба или адаптер Bluetooth недоступны";pending=null;deadline.stop();}
    Timer {id:deadline;interval:root.confirmationTimeout;onTriggered:{root.error="Не получено подтверждение Bluetooth";root.pending=null;}}
    Connections {target:root.pending;ignoreUnknownSignals:true;function onConnectedChanged(){root.confirm();}function onPairedChanged(){root.confirm();}}
}
