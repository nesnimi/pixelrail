"""Real Qt Escape events on production popup contents; offscreen adapters only.
No layer surface, clipboard, capture tool or user D-Bus is used.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as temporary:
    base=Path(temporary);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    shutil.copytree(ROOT/'quickshell',base/'quickshell')
    for relative in ('modules/launcher/Launcher.qml','components/MenuPanel.qml'):
        path=base/'quickshell'/relative
        source=path.read_text().replace('PanelWindow {','Item {',1)
        source=re.sub(r'^    screen:.*$', '    property var screen: ({width:1366,height:768})\n    width:implicitWidth;height:implicitHeight',source,flags=re.M)
        # Drop only compositor-specific root properties; all Escape/focus/content
        # handlers below remain exactly as shipped.
        source='\n'.join(line for line in source.splitlines() if not (
            line.startswith('    ') and not line.startswith('        ') and (
                line.strip().startswith(('anchors {','margins {','exclusionMode:','WlrLayershell.','HyprlandFocusGrab {')) or line.strip()=='color: "transparent"')))+'\n'
        path.write_text(source)
    helper=base/'worker';helper.write_text('''#!/usr/bin/env python3
import sys,time
print('{"event":"ready"}',flush=True)
assert sys.stdin.readline()=='capture\\n'
print('{"event":"selecting"}',flush=True)
time.sleep(30)
''');helper.chmod(0o755)
    menu=base/'menu';menu.write_text('#!/usr/bin/env python3\nprint(\'{"items":[],"title":"Fixture"}\')\n');menu.chmod(0o755)
    config=base/'quickshell/test.qml';config.write_text('''import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import "modules/launcher" as Apps
import "components" as Parts
import "modules/system" as System
ShellRoot {
 Window {
  id:window;visible:true;width:1100;height:740
  Apps.Launcher {id:launcher}
  Parts.MenuPanel {id:menu;backend:Quickshell.env("TEST_MENU")}
  TestCase {id:tc;when:false}
  TestEvent {id:events}
  function check(value,message) {if(!value)throw new Error(message);}
  function idle() {
   const deadline=Date.now()+2500;
   while(JSON.parse(System.ScreenshotState.state()).running && Date.now()<deadline)tc.wait(10);
   check(!System.ScreenshotState.active && !JSON.parse(System.ScreenshotState.state()).running,"worker still running");
  }
  function open(mode) {if(mode==="launcher")launcher.toggle();else menu.showMenu(mode);tc.wait(70);}
  Timer {interval:200;running:true
   onTriggered:{
    try {
     window.requestActivate();
     check(!System.ScreenshotState.active,"initial mode must be inactive");
     for(const mode of ["launcher","clipboard","wallpaper","keys","power","command"]) {
      const item=mode==="launcher" ? launcher : menu;
      window.open(mode);events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);check(!item.opened,mode+" initial Escape");tc.wait(220);
      window.open(mode);
      System.ScreenshotState.phase="arming"; // historical stale state, without a worker
      check(!System.ScreenshotState.active,"stale phase suppressed Escape");
      events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);check(!item.opened,mode+" stale Escape");System.ScreenshotState.reset();tc.wait(220);
      window.open(mode);System.ScreenshotState.helper=Quickshell.env("TEST_MISSING");System.ScreenshotState.capture();
      events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);check(!item.opened,mode+" failed-start Escape");window.idle();tc.wait(220);
      window.open(mode);System.ScreenshotState.helper=Quickshell.env("TEST_WORKER");
      check(System.ScreenshotState.capture(),"capture rejected");
      const deadline=Date.now()+2000;while(!System.ScreenshotState.active && Date.now()<deadline)tc.wait(10);
      check(System.ScreenshotState.active,"worker not ready");
      events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);check(item.opened,mode+" closed during capture");
      System.ScreenshotState.reset();events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);check(!item.opened,mode+" Escape after reset");window.idle();tc.wait(220);
     }
     console.info("SCREENSHOT_ESCAPE_PASS");
    }catch(error){console.error("SCREENSHOT_ESCAPE_FAIL",error.message);}
   }
  }
 }
}''')
    config.write_text(config.read_text().replace('check(', 'window.check(').replace('function window.check(', 'function check('))
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',DBUS_SESSION_BUS_ADDRESS='unix:path='+str(base/'no-bus'),TEST_MENU=str(menu),TEST_WORKER=str(helper),TEST_MISSING=str(base/'missing'),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'))
    env.pop('WAYLAND_DISPLAY',None)
    env['PIXELRAIL_LAUNCHER_METADATA']=str(ROOT/'scripts/launcher_entries.py')
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'SCREENSHOT_ESCAPE_PASS' in output or 'SCREENSHOT_ESCAPE_FAIL' in output or child.poll() is not None:break
                time.sleep(.03)
        finally:
            child.terminate();child.wait(timeout=3)
        log.seek(0);output=log.read();print(output)
    assert 'SCREENSHOT_ESCAPE_PASS' in output
    for marker in ('TypeError','ReferenceError','Unable to assign','Binding loop','SCREENSHOT_ESCAPE_FAIL'):
        assert marker not in output,marker
print('Real Escape: launcher/clipboard/wallpaper/keys/power/command, initial/stale/start failure/capture/reset: PASS')
