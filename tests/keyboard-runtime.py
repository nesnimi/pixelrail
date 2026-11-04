"""Native Hyprland raw events + real hyprctl against private fixture sockets; no windows."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path.cwd()/'tests/fixtures'))
from sidebar_hyprland import Hyprland
ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);hypr=Hyprland(runtime)
    shutil.copytree(ROOT/'quickshell',base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    config=base/'quickshell/test.qml';config.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "modules/control" as Control
ShellRoot {
 Control.KeyboardState {id:keyboard}
 IpcHandler {target:"test";function state():string{return JSON.stringify(keyboard.state);} function toggle():void{keyboard.toggle();}}
}''')
    display=os.environ['WAYLAND_DISPLAY'];display=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),WAYLAND_DISPLAY=display,HYPRLAND_INSTANCE_SIGNATURE='sidebar-test',QT_QPA_PLATFORM='wayland')
    def ipc(method):return subprocess.check_output(['qs','ipc','-p',str(config),'call','test',method],env=env,stderr=subprocess.DEVNULL,timeout=2).decode().strip()
    def wait(label,name):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                value=json.loads(ipc('state'))
                if value.get('label')==label and value.get('name')==name:return
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(.03)
        raise AssertionError(value if 'value' in locals() else 'No IPC')
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait('EN','thinkpad');ipc('toggle');wait('RU','thinkpad')
            assert any(c=='switchxkblayout thinkpad next' for c in hypr.requests),hypr.requests
            # Alt+Shift produces activelayout; no QML flag or optimistic toggle.
            hypr.keyboards[0]['active_keymap']='English (US)';hypr.emit('activelayout>>thinkpad,English (US)');wait('EN','thinkpad')
            hypr.keyboards[0]['main']=False;hypr.keyboards[1]['main']=True
            hypr.emit('activelayout>>usb,Russian');wait('RU','usb')
            hypr.keyboards[1]['active_keymap']='English (US)';hypr.emit('activewindowv2>>aaa');wait('EN','usb')
            hypr.keyboards[0]['main']=True;hypr.keyboards[1]['main']=False;hypr.keyboards[0]['active_keymap']='Russian';hypr.emit('activewindowv2>>bbb');wait('RU','thinkpad')
            before=len(hypr.requests);time.sleep(.3);assert len(hypr.requests)==before,'idle polling'
        finally:
            child.terminate();child.wait(timeout=3);hypr.close()
        log.seek(0);output=log.read();print(output)
        for marker in ('TypeError','ReferenceError','Binding loop'):assert marker not in output
print('Keyboard: initial real state, actual switchxkblayout command/readback, Alt+Shift event, active keyboard/focus refresh, no idle polling: PASS')
