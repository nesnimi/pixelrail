pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import "../control" as Control
Scope {
    id:root
    property bool enabled:false
    property bool bridgeReady:false
    property bool pendingStart:false
    property string error:""
    property var history:[]
    property var popups:[]
    property var popupDeadlines:({})
    readonly property bool dnd: Control.DesktopState.dnd
    function warmup():void {error="";pendingStart=false;if(native.item)native.item.check();else native.active=true;}
    function prepare():void {error="";pendingStart=true;if(native.item)native.item.start();else native.active=true;}
    function stop():bool {
        if(native.item && !native.item.stop())return false;
        enabled=false;bridgeReady=false;popups=[];popupTimer.stop();native.active=false;return true;
    }
    function state():string{return JSON.stringify({enabled:enabled,bridgeReady:bridgeReady,error:error,count:history.length,dnd:dnd});}
    function adopt(notification):void {
        notification.tracked=true;
        const entry={id:notification.id,summary:notification.summary.slice(0,256),body:notification.body.slice(0,4096),
            app:notification.appName.slice(0,128),icon:String(notification.appIcon || "").slice(0,2048),live:notification,time:Date.now(),expires:notification.expireTimeout===0 ? 0 : Date.now()+(notification.expireTimeout>0 ? notification.expireTimeout : 5000)}
        const existing=history.find(value=>value.id===entry.id);
        if(!existing || existing.live!==notification) {
            notification.closed.connect(()=>root.archive(entry.id));
            // qs 0.3.2 mutates an existing QObject for replaces_id without emitting
            // NotificationServer.notification again. Keep snapshots/popups current.
            const refresh=()=>{const current=root.history.find(value=>value.id===entry.id);if(current && current.live===notification && notification.tracked)root.adopt(notification);};
            const changed=()=>Qt.callLater(refresh);
            notification.summaryChanged.connect(changed);
            notification.bodyChanged.connect(changed);
            notification.appNameChanged.connect(changed);
            if(notification.appIconChanged)notification.appIconChanged.connect(changed);
            notification.expireTimeoutChanged.connect(changed);
            notification.actionsChanged.connect(changed);
        }
        let items=history.filter(value=>value.id!==entry.id);
        items.unshift(entry);
        // Bound both snapshots and native objects (which may carry opaque image hints).
        const evicted=items.slice(60);items=items.slice(0,60);history=items;
        evicted.forEach(value=>{if(value.live)value.live.expire();});
        const live=history.filter(value=>value.live);
        live.slice(20).forEach(value=>value.live.expire());
        if(!dnd) {
            popups=[entry.id].concat(popups.filter(id=>id!==entry.id)).slice(0,3);
            const deadlines={};popups.forEach(id=>{if(id!==entry.id)deadlines[id]=popupDeadlines[id];});deadlines[entry.id]=Date.now()+Math.min(8000,notification.expireTimeout>0 ? notification.expireTimeout : 5000);popupDeadlines=deadlines;
        }
        armTimer();
        // Closing a popup never expires/dismisses its history entry.
    }
    function archive(id):void {hidePopup(id);history=history.map(value=>value.id===id ? Object.assign({},value,{live:null}) : value);}
    function hidePopup(id):void {popups=popups.filter(value=>value!==id);const deadlines=Object.assign({},popupDeadlines);delete deadlines[id];popupDeadlines=deadlines;}
    function remove(id):void {const entry=history.find(value=>value.id===id);history=history.filter(value=>value.id!==id);hidePopup(id);if(entry && entry.live)entry.live.dismiss();}
    function clear():void {popupTimer.stop();const items=history;history=[];popups=[];items.forEach(value=>{if(value.live)value.live.dismiss();});}
    function invoke(id,index):void {
        const entry=history.find(value=>value.id===id);
        if(entry && entry.live && entry.live.actions[index]) {entry.live.actions[index].invoke();hidePopup(id);}
    }
    function toggleDnd():void {Control.DesktopState.dnd=!Control.DesktopState.dnd;}
    onDndChanged: if(dnd)popups=[]
    function armTimer():void {
        const now=Date.now();
        const deadlines=history.filter(value=>value.live && value.expires>0).map(value=>value.expires)
            .concat(popups.map(id=>popupDeadlines[id]));
        if(!deadlines.length){popupTimer.stop();return;}
        popupTimer.interval=Math.max(1,Math.min(...deadlines)-now);popupTimer.restart();
    }
    Timer {
        id:popupTimer;repeat:false
        onTriggered:{
            const now=Date.now();root.popups=root.popups.filter(id=>root.popupDeadlines[id]>now);
            root.history.filter(value=>value.live && value.expires>0 && value.expires<=now).forEach(value=>value.live.expire());
            const deadlines={};root.popups.forEach(id=>deadlines[id]=root.popupDeadlines[id]);root.popupDeadlines=deadlines;
            root.armTimer();
        }
    }
    Loader {
        id:native;active:false;source:"NativeServer.qml"
        onLoaded: {item.manager=root;if(root.pendingStart)item.start();else item.check();}
        onStatusChanged: if(status===Loader.Error)root.error="Не удалось загрузить NotificationServer / Qt bridge"
    }
}
