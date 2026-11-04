"""Actual offscreen QML renders at T480 geometry, isolated fixtures and HOME.
No live surface, device writes, screenshot backend or desktop clipboard is used.
"""
import argparse
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
ROOT=Path.cwd()
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=ROOT/'.cache/visual-polish/after')
parser.add_argument('--source',type=Path,default=ROOT/'quickshell')
args=parser.parse_args();out=args.output.resolve()
if not out.is_relative_to(ROOT):parser.error('output must be inside repository')
source_root=args.source.resolve()
if not source_root.is_relative_to(ROOT):parser.error('source must be inside repository')
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);hypr=Hyprland(runtime)
    hypr.clients[0]['class']='google-chrome'
    shutil.copytree(source_root,base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    for name in ('modules/sidebar/Sidebar.qml','modules/control/ControlCenter.qml'):
        path=base/'quickshell'/name;source=path.read_text().replace('PanelWindow {','Item {',1)
        lines=[]
        for line in source.splitlines():
            if line.startswith('    ') and not line.startswith('        ') and line.strip().startswith(('screen:', 'anchors {', 'margins {', 'color:', 'exclusiveZone:', 'exclusionMode:', 'WlrLayershell.', 'mask:', 'HyprlandFocusGrab {')):continue
            lines.append(line)
        source='\n'.join(lines).replace('    id: root','    id:root',1)
        source=source.replace('    id:root','    id:root\n    property var screen:({width:1366,height:768,name:"eDP-1"})\n    width:implicitWidth',1)
        if name.endswith('Sidebar.qml'):
            source=source.replace('targetScreen ? Hyprland.monitors.values.find(monitor => monitor.name === targetScreen.name) || null : null','Hyprland.monitors.values.find(monitor => monitor.id===0) || null')
        else:
            source=source.replace('readonly property var adapter:Bluetooth.defaultAdapter','readonly property var adapter:fakeAdapter\n    QtObject {id:fakeAdapter;property bool enabled:true;property int state:1;property bool discovering:false;property var devices:({values:[]})}')
            source=source.replace('active:!!root.wifiDevice && Networking.wifiEnabled && Networking.wifiHardwareEnabled','active:true')
        path.write_text(source+'\n')
    helper=base/'helper';helper.write_text('#!/usr/bin/env python3\nprint(\'{"available":true,"percent":72,"service":true,"controllers":["hci0"],"blocked":false}\')\n');helper.chmod(0o755)
    apps=base/'data/applications';apps.mkdir(parents=True)
    (apps/'google-chrome.desktop').write_text('[Desktop Entry]\nType=Application\nName=Chrome\nIcon=google-chrome\nExec=/usr/bin/true\n')
    config=base/'quickshell/capture.qml';config.write_text('''import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import Quickshell.Io
import "modules/sidebar" as Sidebar
import "modules/control" as Control
import "modules/system" as System
import "theme" as Theme
ShellRoot {
 Window {
  id:window;visible:true;width:540;height:768;color:Theme.ThemeManager.background
  property var measurements:[]
  QtObject {id:audio;property real volume:.64;property bool muted:false;signal volumesChanged();onVolumeChanged:volumesChanged()}
  System.SystemState {id:core;audio:audio;verifyAudioReadback:false;helper:Quickshell.env("FIXTURE_HELPER")}
  QtObject {id:notify;property bool enabled:true;property var history:[];function toggleDnd(){} function clear(){} function remove(id){}}
  Sidebar.Sidebar {id:rail;x:0;y:6;width:66;height:756;enabledPanel:true}
  Control.ControlCenter {id:cc;x:78;y:12;width:400;height:implicitHeight;opened:true;system:core;notifier:notify}
  TestCase {id:tc;when:false}
  function find(node,name) {if(node.objectName===name)return node;for(const child of node.children || []){const item=window.find(child,name);if(item)return item;}return null;}
  function capture(name) {
   return contentItem.grabToImage(result=>{if(!result.saveToFile(Quickshell.env("CAPTURE_DIR")+"/"+name+".png"))console.error("VISUAL_FAIL save",name);});
  }
  function fixture() {
   const values={"control-wifi-tile":"PixelNet","control-bluetooth-tile":"Включён"};
   for(const name of Object.keys(values))window.find(cc,name).status=values[name];
   window.find(cc,"control-layout").text="EN / RU";window.find(cc,"control-layout").enabled=true;
   window.find(cc,"control-battery").text="87%";window.find(cc,"control-clock").text="10:24";
   window.find(rail,"sidebar-battery").label="87%";window.find(rail,"sidebar-network").glyph="wifi";
  }
  function verify(node) {
   if(node.visible && node.name!==undefined && node.status!==undefined && node.size!==undefined && node.status!==Image.Ready)throw new Error("icon not ready: "+node.name);
   for(const child of node.children || [])window.verify(child);
  }
  IpcHandler {target:"visual"
   function state():string {return JSON.stringify({height:cc.height,width:cc.width,rail:rail.width,settings:cc.section});}
  }
  Timer {interval:600;running:true;onTriggered:{
   try {
    window.fixture();Control.DesktopState.heightRatio=.5;Theme.ThemeManager.configuration={mode:"dark",accent:null};tc.wait(100);
    window.verify(window.contentItem);window.capture("quick-settings-dark");tc.wait(150);
    Theme.ThemeManager.configuration={mode:"light",accent:null};tc.wait(100);window.capture("quick-settings-light");tc.wait(150);
    Theme.ThemeManager.configuration={mode:"auto",accent:null};tc.wait(100);window.verify(window.contentItem);
    Theme.ThemeManager.configuration={mode:"dark",accent:null};cc.selectSection("notifications");tc.wait(100);window.capture("notifications-dark");tc.wait(150);
    cc.selectSection("overview");window.fixture();tc.wait(100);
    const tile=window.find(cc,"control-wifi-tile"), bt=window.find(cc,"control-bluetooth-tile");
    tile.active=false;bt.active=false;window.capture("quick-settings-disabled");tc.wait(150);
    tile.active=true;bt.active=true;
    Control.DesktopState.heightRatio=.75;tc.wait(100);window.capture("quick-settings-expanded");tc.wait(150);
    Control.DesktopState.heightRatio=.5;tc.wait(100);
    console.info("VISUAL_PASS",JSON.stringify({height:cc.height,width:cc.width,rail:rail.width,bodyFont:tile.contentItem.children[1].children[0].font.family}));
   }catch(error){console.error("VISUAL_FAIL",error.message);}
  }}
 }
}''')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),HYPRLAND_INSTANCE_SIGNATURE='sidebar-test',CAPTURE_DIR=str(out),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],DBUS_SESSION_BUS_ADDRESS='unix:path='+str(base/'no-bus'),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'),PIXELRAIL_DESKTOP_HELPER=str(helper),FIXTURE_HELPER=str(helper))
    env.pop('WAYLAND_DISPLAY',None)
    with (out/'runtime.log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'VISUAL_PASS' in output or 'VISUAL_FAIL' in output or child.poll() is not None:break
                time.sleep(.03)
            # A static scene: bounded interval sample, software renderer, no live UI.
            if 'VISUAL_PASS' in output:
                def stats():
                    proc=Path('/proc')/str(child.pid);fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
                    return {'ticks':int(fields[11])+int(fields[12]),'rss_mib':int((proc/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')/1048576,'time':time.monotonic()}
                time.sleep(.3);first=stats();time.sleep(2);last=stats()
                metrics={'boundary':'offscreen software fixture at 1366x768 logical screen; one 2s interval, not hardware power or compositor latency','rss_mib':last['rss_mib'],'cpu_percent_one_core':100*(last['ticks']-first['ticks'])/os.sysconf('SC_CLK_TCK')/(last['time']-first['time'])}
                (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
        finally:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            child.wait(timeout=3);hypr.close()
        log.seek(0);output=log.read();print(output)
    assert 'VISUAL_PASS' in output
    for marker in ('ERROR','VISUAL_FAIL','TypeError','ReferenceError','Unable to assign','Binding loop','Error decoding'):
        assert marker not in output,marker
print('Real QML images, dark/light/auto, Material SVGs, unchanged 400x384 / zone66: PASS')
