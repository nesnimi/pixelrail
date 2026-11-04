"""Real offscreen Sidebar/Launcher captures, copied QML, fixture Hyprland, no live surfaces."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path.cwd()/'tests/fixtures'))
from sidebar_hyprland import Hyprland
ROOT=Path.cwd();out=ROOT/'docs/design/screenshots';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);hypr=Hyprland(runtime);hypr.clients[0]['class']='google-chrome'
    shutil.copytree(ROOT/'quickshell',base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    for name in ('modules/sidebar/Sidebar.qml','modules/launcher/Launcher.qml'):
        path=base/'quickshell'/name;s=path.read_text().replace('PanelWindow {','Item {',1)
        lines=[]
        for line in s.splitlines():
            if line.strip().startswith(('screen:', 'anchors { left: true;', 'margins {', 'color: "transparent"','exclusiveZone:','exclusionMode:','WlrLayershell.','mask: Region')):continue
            lines.append(line)
        s='\n'.join(lines).replace('active: root.visible && root.opened','active:false')
        if 'sidebar' in name:s=s.replace('targetScreen ? Hyprland.monitors.values.find(monitor => monitor.name === targetScreen.name) || null : null','Hyprland.monitors.values.find(monitor => monitor.id===0) || null')
        # Launcher uses requested-screen expression; Item adapter supplies real dimensions.
        s=s.replace('anchors { left: true; bottom: true }','')
        s=s.replace('    id: root','    id: root\n    property var screen:({width:1366,height:768,name:"eDP-1"})\n    width:implicitWidth',1)
        path.write_text(s)
    config=base/'quickshell/capture.qml';config.write_text('''import QtQuick
import QtQuick.Window
import Quickshell
import "modules/sidebar" as Sidebar
import "modules/launcher" as Launcher
import "theme" as Theme
ShellRoot {
 Window {id:window;width:640;height:768;visible:true;color:"transparent"
  Sidebar.Sidebar {id:rail;enabledPanel:true;x:0;y:6;width:66;height:754}
  Launcher.Launcher {id:launcher;opened:true;x:78;y:window.height-height-12;width:540;height:implicitHeight}
  function capture(name){
      function verify(node){
          if(node.source!==undefined && /^(https?|ftp):/.test(String(node.source)))console.error("CAPTURE_FAIL network image",String(node.source));
          if(node.visible && node.name!==undefined && node.size!==undefined && node.status!==undefined && node.status!==Image.Ready)console.error("CAPTURE_FAIL unloaded PixelIcon",node.name);
          for(const child of node.children || [])verify(child);
      }
      verify(contentItem);contentItem.grabToImage(result=>{if(!result.saveToFile(Quickshell.env("CAPTURE_DIR")+"/"+name+".png"))console.error("CAPTURE_FAIL");});}
  Timer {interval:500;running:true;onTriggered:{window.capture("sidebar-launcher-dark");light.start();}}
  Timer {id:light;interval:250;onTriggered:{Theme.ThemeManager.configuration={mode:"light",accent:null};finish.start();}}
  Timer {id:finish;interval:250;onTriggered:{window.capture("sidebar-launcher-light");done.start();}}
  Timer {id:done;interval:250;onTriggered:{Theme.ThemeManager.configuration={mode:"dark",accent:null,iconStyle:"themed"};themed.start();}}
  Timer {id:themed;interval:250;onTriggered:{
      function count(node){let n=node.themed===true ? 1 : 0;for(const child of node.children || [])n+=count(child);return n;}
      if(count(rail)<1 || count(launcher)<2)console.error("CAPTURE_FAIL icon style not shared by Sidebar/Launcher");
      window.capture("sidebar-launcher-themed");complete.start();
  }}
  Timer {id:complete;interval:250;onTriggered:console.info("DESIGN_CAPTURE_PASS")}
 }
}''')
    apps=base/'data/applications';apps.mkdir(parents=True)
    for ident,title,icon in [('google-chrome','Chrome','google-chrome'),('org.gnome.Nautilus','Файлы','system-file-manager'),('org.gnome.Terminal','Терминал','utilities-terminal')]:
        (apps/(ident+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+title+'\nIcon='+icon+'\nExec=/usr/bin/true\n')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),HYPRLAND_INSTANCE_SIGNATURE='sidebar-test',CAPTURE_DIR=str(out),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'),PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'])
    env.pop('WAYLAND_DISPLAY',None)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+6
            while time.monotonic()<deadline:
                log.seek(0);text=log.read()
                if 'DESIGN_CAPTURE_PASS' in text or child.poll() is not None:break
                time.sleep(.05)
        finally:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=3);hypr.close()
        log.seek(0);text=log.read();print(text)
    assert 'DESIGN_CAPTURE_PASS' in text
    for marker in ('ERROR','TypeError','ReferenceError','Unable to assign','Binding loop','CAPTURE_FAIL'):assert marker not in text,marker
print('Actual Sidebar/Launcher dark/light offscreen screenshots: PASS (fixture devices/applications, no mapped desktop windows)')
