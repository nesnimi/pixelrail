pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import "../../ui" as Ui
Scope {
    id:root
    property var system:SystemControls
    property bool suppressed:false
    property int sideOffset:12
    property var targetScreen:null
    property bool opened:false
    property bool alive:false
    property string kind:"volume"
    readonly property bool loaded:panel.status===Loader.Ready
    function show(value):void {
        if(suppressed || (value==="volume" ? !system.audioAvailable : !system.brightness.available))return;
        kind=value;opened=true;alive=true;dismiss.restart();
    }
    function hide():void {opened=false;dismiss.stop();}
    function cancel():void {opened=false;alive=false;dismiss.stop();}
    onSuppressedChanged:if(suppressed)cancel()
    onTargetScreenChanged:cancel()
    Connections {target:root.system
        function onOsdRequested(kind){root.show(kind);}
        function onAudioErrorChanged(){if(root.kind==="volume" && root.system.audioError!=="")root.cancel();}
        function onAudioChanged(){if(root.kind==="volume" && !root.system.audioAvailable)root.cancel();}
        function onBrightnessChanged(){if(root.kind==="brightness" && !root.system.brightness.available)root.cancel();}
    }
    Timer {id:dismiss;interval:Ui.Tokens.osdTimeout;onTriggered:root.hide()}
    Loader {
        id:panel;active:root.alive;source:"SystemOsd.qml"
        onLoaded:{item.system=root.system;item.opened=Qt.binding(()=>root.opened);item.kind=Qt.binding(()=>root.kind);item.sideOffset=Qt.binding(()=>root.sideOffset);item.targetScreen=Qt.binding(()=>root.targetScreen);item.dismissed.connect(()=>{if(!root.opened)root.alive=false;});}
    }
}
