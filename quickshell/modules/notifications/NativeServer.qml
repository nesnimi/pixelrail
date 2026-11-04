import QtQuick
import Quickshell
import Quickshell.Services.Notifications
Scope {
    id: root
    property var manager: null
    property var lease:null
    function check(): bool {
        // Absolute import bypasses qs reload-cache copying: native .so files
        // must be loaded from the immutable release, not the QML cache.
        if(!lease) {
            try {lease=Qt.createQmlObject('import QtQml\nimport '+JSON.stringify('file://'+Quickshell.shellPath('native/PixelRail/DBusLease'))+' as Native\nNative.NotificationLease {}',root);}
            catch(error) {manager.error="Не найден Qt bridge: выполните scripts/build-native.sh перед deploy";return false;}
        }
        if(!lease.compatible()){manager.error="Пересоберите Qt bridge: scripts/build-native.sh";return false;}
        manager.bridgeReady=true;return true;
    }
    function start(): void {
        if(!check())return;
        if (lease.owner() && !lease.isOwner()) {manager.error="D-Bus Notifications уже принадлежит другому серверу";return;}
        backend.active=true;
        Qt.callLater(() => {
            if (lease.acquire()) {manager.enabled=true;manager.error="";}
            else manager.error="Не удалось получить notification D-Bus lease";
        });
    }
    function stop(): bool {
        if (lease && lease.isOwner() && !lease.release()) {manager.error="Не удалось освободить notification D-Bus lease";return false;}
        manager.enabled=false;
        manager.history.forEach(entry=>{if(entry.live)entry.live.expire();});
        backend.active=false;
        return true;
    }
    Loader {
        id:backend;active:false
        sourceComponent: Component {
            NotificationServer {
                keepOnReload:false;persistenceSupported:true;actionsSupported:true
                bodySupported:true;bodyMarkupSupported:false;bodyHyperlinksSupported:false
                imageSupported:false;bodyImagesSupported:false
                onNotification: notification => root.manager.adopt(notification)
            }
        }
    }
}
