"""Run real QML placement rules with screen dimensions independent of live output."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
root=Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    source='''import QtQuick
import Quickshell
import "HELPER" as Placement
ShellRoot {
    Timer {interval:10;running:true;onTriggered:{
        try {
            for(const width of [1366,1920,800,320,80])for(const height of [768,1080,480,230])for(const inset of [78,12,140]) {
                const left=Placement.left(width,inset);
                for(const desired of [400,540,640,700,1000]) {
                    const w=Placement.width(desired,width,inset),h=Placement.height(620,height);
                    if(left<0 || left+w+12>width || h+24>height || w<=0 || h<=0)throw new Error("off screen");
                }
            }
            if(Placement.left(1366,78)!==78 || Placement.width(1000,1366,78)!==1000)throw new Error("normal geometry changed");
            for(const mode of ["launcher","command","clipboard","windows","emoji"])if(!Placement.bottom(mode))throw new Error(mode);
            for(const mode of ["controls","power","keys","wallpaper","media","overview","notifications"])if(Placement.bottom(mode))throw new Error(mode);
            console.info("PLACEMENT_PASS");
        }catch(error){console.error("PLACEMENT_FAIL",error.message);}
    }}
}'''.replace('HELPER',str(root/'quickshell/components/PopupPlacement.js'))
    config=base/'shell.qml';config.write_text(source)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software')
    env.pop('WAYLAND_DISPLAY',None)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'PLACEMENT_PASS' in output or 'PLACEMENT_FAIL' in output or child.poll() is not None:break
                time.sleep(.02)
        finally:child.terminate();child.wait(timeout=3)
        log.seek(0);output=log.read();assert 'PLACEMENT_PASS' in output,output
        for marker in ('ERROR','TypeError','ReferenceError','Unable to assign'):assert marker not in output,output
print('Popup placement: actual QML rules, all menus, Sidebar/Waybar insets, 1366x768/resizes/narrow outputs: PASS')
