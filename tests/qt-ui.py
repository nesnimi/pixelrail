"""Actual Qt key/mouse events in a software/offscreen window, with qs static plugins."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

def live_group_members(group_id,home):
    found=[]
    for directory in Path('/proc').glob('[0-9]*'):
        try:
            fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z' or int(fields[2])!=group_id:continue
            if ('HOME='+str(home)).encode() in (directory/'environ').read_bytes().split(b'\0'):found.append(int(directory.name))
        except (OSError,ValueError):pass
    return found

root=Path.cwd(); binary=shutil.which('qs') or shutil.which('quickshell')
if not binary: raise SystemExit('Quickshell required')
for name in ('WallpaperTests','WallpaperCacheTests','ClipboardTests','SidebarTests','Rc4VisualTests'):
    with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
        base=Path(tmp); runtime=base/'runtime';runtime.mkdir(mode=0o700)
        config=base/'shell.qml'
        source='''import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    Window {
        id: window
        visible:true;width:1000;height:620
        Loader { id: tests; anchors.fill:parent;source:"SOURCE" }
        Timer {
            interval:150;running:true;repeat:false
            onTriggered:{
                window.requestActivate();
                try {tests.item.run();console.info("PIXELRAIL_UI_PASS");}
                catch(error) {console.error("PIXELRAIL_UI_FAIL",error.message);}
            }
        }
    }
}
'''.replace('SOURCE',str(root/'tests/gui'/f'{name}.qml'))
        config.write_text(source)
        env=dict(os.environ,HOME=str(base),PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',
                 XDG_RUNTIME_DIR=str(runtime),XDG_CACHE_HOME=str(base/'cache'),XDG_CONFIG_HOME=str(base/'config'),
                 XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'))
        env.pop('WAYLAND_DISPLAY',None)
        if name=='Rc4VisualTests' and (root/'pixelrail_1.png').exists():
            env['PIXELRAIL_TEST_IMAGE']=(root/'pixelrail_1.png').as_uri()
        if name=='WallpaperCacheTests':
            helper=base/'thumbnail-helper'
            helper.write_text('#!/usr/bin/env python3\nimport json,sys\njson.loads(sys.stdin.readline())\nprint(json.dumps({"url":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAJElEQVR4nGNImHCApohh1IJRC0YtGLVg1IJRC0YtGLVgaFgAAAJjEEwsnwkHAAAAAElFTkSuQmCC"}))\n')
            helper.chmod(0o755);env['PIXELRAIL_TEST_THUMB_HELPER']=str(helper)
        marker=base/'theme-helper.pid'
        if name=='SidebarTests':
            # A deliberately long-lived theme helper must be gone BEFORE rmtree.
            helper=base/'pixelrail-theme'
            helper.write_text('#!/usr/bin/env python3\nimport os,time\nfrom pathlib import Path\nPath(os.environ["PIXELRAIL_TEST_MARKER"]).write_text(str(os.getpid()))\ntime.sleep(30)\n')
            helper.chmod(0o755)
            env['PIXELRAIL_THEME_HELPER']=str(helper);env['PIXELRAIL_TEST_MARKER']=str(marker)
        with (base/'log').open('w+') as log:
            process=subprocess.Popen([binary,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                if name=='SidebarTests':
                    deadline=time.monotonic()+3
                    while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                    assert marker.exists(),'slow theme helper never started'
                deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    log.seek(0); output=log.read()
                    if 'PIXELRAIL_UI_PASS' in output or 'PIXELRAIL_UI_FAIL' in output or process.poll() is not None: break
                    time.sleep(.03)
            finally:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                process.wait(timeout=3)
                deadline=time.monotonic()+3
                while live_group_members(process.pid,base) and time.monotonic()<deadline:time.sleep(.02)
                remaining=live_group_members(process.pid,base)
                for pid in remaining:
                    try:os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                deadline=time.monotonic()+2
                while live_group_members(process.pid,base) and time.monotonic()<deadline:time.sleep(.02)
                assert not live_group_members(process.pid,base),'test helpers outlived their process group'
                if marker.exists():
                    helper_pid=int(marker.read_text())
                    try:assert (Path('/proc')/str(helper_pid)/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z','theme helper survived teardown'
                    except FileNotFoundError:pass
            log.seek(0);output=log.read();print(output)
            assert 'PIXELRAIL_UI_PASS' in output, name+' did not pass'
            for marker in ('PIXELRAIL_UI_FAIL','Unable to assign','TypeError','ReferenceError','Binding loop','Duplicate signal'):
                assert marker not in output, marker
print('Qt UI: mouse chips, dimensions/padding, Escape from every focus, reopen/cancel/apply, clipboard keyboard image selection; Sidebar batteries/icons/monitors/contrast/pressed states: passed')
