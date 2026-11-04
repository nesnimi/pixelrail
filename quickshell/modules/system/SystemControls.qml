pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.Pipewire
import "../control" as Control
SystemState {
    id:root
    helper:Control.DesktopState.helper
    sink:Pipewire.defaultAudioSink
    audio:sink && sink.ready && sink.audio && sink.audio.channels.length>0 ? sink.audio : null
    PwObjectTracker {objects:root.sink ? [root.sink] : []}
    property var watcher:null
    readonly property bool backlightEvents:!!watcher && watcher.available
    Component.onCompleted:{
        try {
            watcher=Qt.createQmlObject('import QtQml\nimport '+JSON.stringify('file://'+Quickshell.shellPath('native/PixelRail/DBusLease'))+' as Native\nNative.BacklightWatch {}',root);
            watcher.changed.connect(root.backlightChanged);
        }catch(error){console.warn("PixelRail: backlight events unavailable; rebuild native plugin");}
    }
}
