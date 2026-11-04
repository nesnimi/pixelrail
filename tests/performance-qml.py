"""Real QML regressions: identical palette reloads and duplicate notification scheduling."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import time
root=Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    (base/'control').symlink_to(root/'quickshell/modules/control',target_is_directory=True)
    (base/'notifications').mkdir()
    source=(root/'quickshell/modules/notifications/NotificationController.qml').read_text().replace('    id:root','    id:root\n    property int measuredCalls:0',1).replace('    function armTimer():void {','    function armTimer():void {measuredCalls++;')
    (base/'notifications/NotificationController.qml').write_text(source)
    config=base/'shell.qml';config.write_text('''import QtQuick
import Quickshell
import "notifications" as Notify
ShellRoot {
    Notify.NotificationController {id:notifications}
    QtObject {id:message
        property bool tracked:false
        property int id:1
        property string summary:"Test"
        property string body:"Body"
        property string appName:"Test"
        property int expireTimeout:0
        property var actions:[]
        signal closed()
        function expire(){tracked=false;closed();}
        function dismiss(){expire();}
    }
    Timer {interval:100;running:true;onTriggered:{
        notifications.adopt(message);
        if(notifications.measuredCalls!==1)console.error("PERF_FAIL duplicate armTimer",notifications.measuredCalls);
        else {
            notifications.adopt(message);
            message.summary="Replacement";
            Qt.callLater(()=>{
                if(notifications.measuredCalls!==3 || notifications.history.length!==1)console.error("PERF_FAIL duplicate notification subscriptions",notifications.measuredCalls);
                else console.info("PERF_PASS notification scheduling and single refresh subscription");
            });
        }
    }}
}''')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PIXELRAIL_DESKTOP_HELPER=str(root/'scripts/pixelrail-desktop'))
    env.pop('WAYLAND_DISPLAY',None)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'PERF_PASS' in output or 'PERF_FAIL' in output or child.poll() is not None:break
                time.sleep(.02)
        finally:child.terminate();child.wait(timeout=3)
        log.seek(0);output=log.read()
        assert 'PERF_PASS' in output,output
        for marker in ('ERROR','TypeError','ReferenceError','Unable to assign'):assert marker not in output,output
print('Real QML: exactly one notification deadline arm per adoption: PASS')
# An empty file must not hit the initial empty cache sentinel and hide corruption.
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    palette=base/'cache/pixelrail/theme/palette.json';palette.parent.mkdir(parents=True);palette.write_text('')
    helper=base/'pixelrail-theme';helper.write_text('#!/usr/bin/env python3\nprint(\'{"error":"test helper disabled"}\')\n');helper.chmod(0o755)
    config=base/'shell.qml';config.write_text('''import QtQuick
import Quickshell
import "THEME" as Theme
ShellRoot {
    property int attempts:0
    Timer {interval:100;running:true;repeat:true;onTriggered:{
        if(Theme.ThemeManager.lastError.includes("палитра")) {console.info("EMPTY_PALETTE_PASS");stop();}
        else if(++attempts>=20) {console.error("EMPTY_PALETTE_FAIL",Theme.ThemeManager.lastError);stop();}
    }}
}'''.replace('THEME',(root/'quickshell/theme').as_uri()))
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PIXELRAIL_THEME_HELPER=str(helper))
    env.pop('WAYLAND_DISPLAY',None)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'EMPTY_PALETTE_PASS' in output or 'EMPTY_PALETTE_FAIL' in output or child.poll() is not None:break
                time.sleep(.02)
        finally:child.terminate();child.wait(timeout=3)
        log.seek(0);output=log.read();assert 'EMPTY_PALETTE_PASS' in output,output
print('Real QML: initial empty palette reports an error and retains fallback: PASS')
