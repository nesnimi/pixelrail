"""Real Qt drag/events with fake hardware, delayed replies, coalescing and OSD."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell')
    helper=base/'brightness-helper';helper.write_text('''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
root=Path(os.environ['SYSTEM_TEST_ROOT']);state=root/'brightness.json'
action=sys.argv[1]
with (root/'calls.jsonl').open('a') as stream:stream.write(json.dumps({'time':time.monotonic(),'action':action,'value':sys.argv[2] if len(sys.argv)>2 else None})+'\\n')
time.sleep(.08)
value=int(state.read_text()) if state.exists() else 40
if action=='set-brightness':value=int(sys.argv[2]);state.write_text(str(value))
print(json.dumps({'available':True,'percent':value,'device':'fake','current':value,'maximum':100}))
''');helper.chmod(0o755)
    denied=base/'denied-helper';denied.write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps({"available":False,"error":"test denied"}));sys.exit(1)\n');denied.chmod(0o755)
    audio_reader=base/'audio-reader';audio_reader.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"available":True,"node":11,"volume":.23,"muted":True}))\n');audio_reader.chmod(0o755)
    controller=base/'quickshell/modules/system/OsdController.qml';controller.write_text(controller.read_text().replace('    id:root','    id:root\n    readonly property var testWindow:panel.item',1).replace('source:"SystemOsd.qml"','source:"OsdFake.qml"'))
    (controller.parent/'OsdFake.qml').write_text('''import QtQuick
import Quickshell
Scope {property var system;property bool opened:false;property string kind;property int sideOffset;property var targetScreen;signal dismissed();onOpenedChanged:if(!opened)Qt.callLater(dismissed)}''')
    osd=controller.parent/'SystemOsd.qml';source=osd.read_text().replace('PanelWindow {','Item {',1)
    source=source.replace('    screen:targetScreen || Quickshell.screens[0]','    property var screen:({width:1366,height:768})\n    width:implicitWidth;height:implicitHeight')
    source='\n'.join(line for line in source.splitlines() if not line.strip().startswith(('anchors.left:','margins.left:','exclusionMode:','WlrLayershell.','mask:')));osd.write_text(source)
    config=base/'quickshell/test.qml';config.write_text('''import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import "modules/control" as Control
import "modules/system" as System
import "theme" as Theme
ShellRoot {
 Window {
  id:window;visible:true;width:650;height:500
  QtObject {id:audio
   property real volume:.4
   property bool muted:false
   property int writes:0
   signal volumesChanged()
   onVolumeChanged:{writes++;volumesChanged();}
  }
  QtObject {id:refusing;property real volume:.3;property bool muted:false;signal volumesChanged();onVolumeChanged:{if(Math.abs(refusing.volume-.3)>.001)refusing.volume=.3;refusing.volumesChanged();}}
  QtObject {id:fakeSink;property int id:11}
  System.SystemState {id:core;verifyAudioReadback:false;audio:audio;helper:Quickshell.env("SYSTEM_TEST_HELPER")}
  System.OsdController {id:osd;system:core}
  System.SystemOsd {id:card;system:core;opened:osd.opened;kind:osd.kind;y:240}
  Control.LiveSlider {id:bright;objectName:"brightness";x:20;y:25;width:280;from:1;to:100;backendValue:core.brightness.percent || 1;backendPending:core.brightnessUiPending;enabled:!!core.brightness.available;onRequested:(value,finalValue)=>core.requestBrightness(value,finalValue)}
  Text {id:brightPercent;x:320;y:25;text:Math.round(bright.value)+"%"}
  Control.LiveSlider {id:volume;x:20;y:100;width:280;backendValue:core.audioAvailable ? core.audio.volume : 0;backendPending:core.volumeUiPending;enabled:core.audioAvailable;onRequested:(value,finalValue)=>core.requestVolume(value,finalValue)}
  TestEvent {id:events}
  TestCase {id:tc;when:false}
  function check(ok,message){if(!ok)throw new Error(message);}
  function waitUntil(predicate,message){let count=0;while(!predicate() && count++<100)tc.wait(20);check(predicate(),message);}
  Timer {interval:200;running:true;onTriggered:{
   try {
    core.refreshBrightness();window.waitUntil(()=>core.brightness.available,"initial brightness");
    window.requestActivate();
    events.mousePress(bright,20,15,Qt.LeftButton,Qt.NoModifier,0);
    events.mouseMove(bright,220,15,0,Qt.LeftButton,Qt.NoModifier);
    window.check(bright.pressed && bright.value>60,"drag not live");
    window.check(brightPercent.text===Math.round(bright.value)+"%","percentage not live");
    const dragging=bright.value;
    core.brightness={available:true,percent:5,device:"fake"};tc.wait(30);
    window.check(Math.abs(bright.value-dragging)<.1,"stale backend moved thumb during drag");
    window.waitUntil(()=>core.brightness.percent>60,"system brightness did not apply while pressed");window.check(bright.pressed,"drag ended before backend update");
    events.mouseMove(bright,240,15,0,Qt.LeftButton,Qt.NoModifier);
    const finalBrightness=Math.round(bright.value);
    events.mouseRelease(bright,240,70,Qt.LeftButton,Qt.NoModifier,0);
    window.check(!bright.pressed,"outside release did not end drag");
    window.waitUntil(()=>!core.brightnessPending,"last drag did not flush");
    window.check(core.brightness.percent===finalBrightness,"final brightness lost");
    for(let i=0;i<100;i++)core.requestBrightness(30+i%20);
    core.requestBrightness(73,true);window.waitUntil(()=>!core.brightnessPending,"coalescing stalled");window.check(core.brightness.percent===73,"latest brightness lost");
    events.mousePress(bright,150,15,Qt.LeftButton,Qt.NoModifier,0);events.mouseRelease(bright,150,15,Qt.LeftButton,Qt.NoModifier,0);
    const shortValue=Math.round(bright.value);window.waitUntil(()=>!core.brightnessPending,"short gesture pending");window.check(core.brightness.percent===shortValue,"short gesture lost");
    bright.forceActiveFocus();const beforeKey=bright.value;events.keyClick(Qt.Key_Right,Qt.NoModifier,0);
    window.check(bright.value>beforeKey,"keyboard slider");window.waitUntil(()=>!core.brightnessPending,"keyboard pending");
    const beforeWheel=bright.value;events.mouseWheel(bright,150,15,Qt.NoButton,Qt.NoModifier,0,120,0);
    window.check(bright.value>beforeWheel,"wheel slider");window.waitUntil(()=>!core.brightnessPending,"wheel pending");
    events.mousePress(volume,30,15,Qt.LeftButton,Qt.NoModifier,0);
    events.mouseMove(volume,240,15,0,Qt.LeftButton,Qt.NoModifier);
    window.check(volume.pressed && volume.value>.7,"volume drag not live");
    const v=volume.value;audio.volume=.1;tc.wait(20);window.check(Math.abs(volume.value-v)<.01,"stale volume reset drag");
    events.mouseRelease(volume,240,60,Qt.LeftButton,Qt.NoModifier,0);
    window.waitUntil(()=>!core.volumePending,"volume not confirmed");window.check(Math.abs(audio.volume-v)<.01,"final volume lost");
    audio.volume=.2;tc.wait(20);window.check(Math.abs(volume.value-.2)<.01,"external volume not reflected");
    const count=audio.writes;for(let i=0;i<100;i++)core.requestVolume((i%10)/10);core.requestVolume(.73,true);
    tc.wait(60);window.check(audio.writes-count<5 && Math.abs(audio.volume-.73)<.01,"volume coalescing");
    window.check(!osd.opened,"slider created OSD");
    volume.forceActiveFocus();core.audioError="previous failure";core.mute("hardware");window.check(core.audioError==="","mute retained stale error");window.waitUntil(()=>osd.opened && osd.loaded,"mute OSD absent");
    window.check(audio.muted && card.muted,"mute display wrong");
    const existing=osd.testWindow;tc.wait(400);core.requestBrightness(81,true,"hardware");
    window.waitUntil(()=>osd.kind==="brightness","brightness OSD absent");window.check(existing===osd.testWindow,"OSD recreated on kind change");
    window.check(volume.activeFocus,"OSD stole keyboard focus");
    core.requestBrightness(61,true,"hardware");tc.wait(30);core.requestBrightness(67,false,"hardware");tc.wait(100);
    window.check(Math.abs(bright.value-core.brightness.percent)<.1,"hardware updates hidden while next request pending");
    window.waitUntil(()=>!core.brightnessPending,"hardware final pending");
    core.requestBrightness(86,true,"hardware");core.requestVolume(.65,true,"hardware");
    window.waitUntil(()=>!core.brightnessPending,"delayed cross-channel reply");
    window.check(osd.kind==="volume","old brightness reply replaced newer volume OSD");
    osd.suppressed=true;window.check(!osd.opened,"menu suppression failed");core.mute("hardware");tc.wait(100);window.check(!osd.opened,"OSD over Control Center");
    osd.suppressed=false;core.mute("hardware");window.waitUntil(()=>osd.opened,"OSD reopen");tc.wait(800);core.mute("hardware");tc.wait(650);window.check(osd.opened,"hide timer was not reset");tc.wait(800);window.check(!osd.opened && !osd.alive,"OSD did not unload");
    core.audio=null;window.check(!core.audioAvailable && !volume.enabled,"missing device has active slider");window.check(!core.action("volume-up"),"fake audio control accepted");core.audio=audio;audio.volume=.3;tc.wait(20);window.check(core.audioAvailable && Math.abs(volume.value-.3)<.01,"audio did not recover");
    const brightnessHelper=core.helper;core.sink=fakeSink;core.verifyAudioReadback=true;core.helper=Quickshell.env("SYSTEM_TEST_AUDIO_HELPER");core.requestVolume(.81,true,"hardware");
    window.waitUntil(()=>osd.opened && Math.abs(core.volume-.23)<.001,"server readback not used");window.check(Math.abs(card.level-.23)<.001 && card.muted,"OSD showed optimistic target instead of server value");
    osd.cancel();core.helper=brightnessHelper;core.verifyAudioReadback=false;core.sink=null;
    core.audio=refusing;core.requestVolume(.8,true,"hardware");tc.wait(1100);
    window.check(!core.volumePending && core.audioError!=="" && !osd.opened && Math.abs(core.audio.volume-.3)<.01,"unconfirmed volume was shown or remained pending "+JSON.stringify({pending:core.volumePending,error:core.audioError,osd:osd.opened,actual:core.audio.volume}));core.audio=audio;
    const originalHelper=core.helper;core.helper=Quickshell.env("SYSTEM_TEST_ERROR_HELPER");core.requestBrightness(33,true);
    window.waitUntil(()=>!core.brightnessPending,"brightness error left pending");window.check(!core.brightness.available && !bright.enabled,"failed brightness stays active");
    core.helper=originalHelper;core.refreshBrightness();window.waitUntil(()=>core.brightness.available,"brightness recovery");
    for(const mode of ["dark","light"]) {Theme.ThemeManager.configuration={mode:mode};window.check(Theme.ThemeManager.contrast(String(Theme.ThemeManager.surfaceContainer),String(Theme.ThemeManager.surfaceText))>=4.5,"OSD contrast");}
    console.info("SYSTEM_UI_PASS",JSON.stringify({brightness:core.brightness.percent,volume:audio.volume}));
   }catch(error){console.error("SYSTEM_UI_FAIL",error.message);}
  }}
 }
}''')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',SYSTEM_TEST_HELPER=str(helper),SYSTEM_TEST_ERROR_HELPER=str(denied),SYSTEM_TEST_AUDIO_HELPER=str(audio_reader),SYSTEM_TEST_ROOT=str(base),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'))
    env.pop('WAYLAND_DISPLAY',None)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+18
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'SYSTEM_UI_PASS' in output or 'SYSTEM_UI_FAIL' in output or child.poll() is not None:break
                time.sleep(.03)
        finally:
            os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=4)
            # Reap test helpers before TemporaryDirectory cleanup.
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                alive=[]
                for entry in Path('/proc').glob('[0-9]*'):
                    try:
                        fields=entry.joinpath('stat').read_text().rsplit(')',1)[1].split()
                        if fields[0]!='Z' and int(fields[2])==child.pid:alive.append(entry)
                    except OSError:pass
                if not alive:break
                time.sleep(.02)
            assert not alive,'system UI helper survived'
        log.seek(0);output=log.read();print(output)
    assert 'SYSTEM_UI_PASS' in output
    for marker in ('ERROR','TypeError','ReferenceError','Unable to assign','Binding loop','Duplicate signal'):assert marker not in output,marker
    calls=[json.loads(line) for line in (base/'calls.jsonl').read_text().splitlines()]
    writes=[row for row in calls if row['action']=='set-brightness']
    assert len(writes)<15,len(writes)
    assert all(b['time']-a['time']>=.07 for a,b in zip(writes,writes[1:])),writes
    print('Live sliders, percentages during drag, stale reply guard, final outside release, coalescing, hotplug, mute, OSD reuse/suppression/timer/focus/contrast: PASS; brightness writes:',len(writes))
