pragma Singleton
import QtQuick
import Quickshell
Scope {
    id:root
    property var events:null
    property string error:""
    signal resumed()
    signal backendChanged()
    Component.onCompleted:{
        try {
            events=Qt.createQmlObject('import QtQml\nimport '+JSON.stringify('file://'+Quickshell.shellPath('native/PixelRail/DBusLease'))+' as Native\nNative.SystemEvents {}',root);
            events.resumed.connect(root.resumed);events.backendChanged.connect(root.backendChanged);
        }catch(error){root.error="События resume недоступны: пересоберите native plugin";console.warn(root.error);}
    }
}
