"""Real layer-shell/IPC, fake devices, private D-Bus. All test panels unmapped."""
import json
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
ROOT=Path.cwd()
parser=argparse.ArgumentParser();parser.add_argument('--soak-seconds',type=int,default=0);args=parser.parse_args()
if not 0<=args.soak_seconds<=180:parser.error('soak: 0..180 seconds')
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    helper=base/'brightness-helper';helper.write_text('''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
path=Path(os.environ['SYSTEM_BRIGHTNESS_FILE']);value=int(path.read_text()) if path.exists() else 40
time.sleep(.04)
if sys.argv[1]=='set-brightness':value=int(sys.argv[2]);path.write_text(str(value))
print(json.dumps({'available':True,'percent':value,'device':'fake'}))
''');helper.chmod(0o755)
    state=base/'quickshell/modules/system/SystemControls.qml';source=state.read_text().replace('helper:Control.DesktopState.helper','helper:Quickshell.env("SYSTEM_TEST_HELPER")').replace('sink:Pipewire.defaultAudioSink','sink:testSink').replace('audio:sink && sink.ready && sink.audio && sink.audio.channels.length>0 ? sink.audio : null','audio:sink && sink.ready ? testAudio : null')
    source=source.replace('    id:root','    id:root;verifyAudioReadback:false',1)
    source=source.replace('    PwObjectTracker {objects:root.sink ? [root.sink] : []}', '''    QtObject {id:testAudio;property real volume:.4;property bool muted:false;signal volumesChanged();onVolumeChanged:volumesChanged()}
    QtObject {id:testSink;property bool ready:true;property string description:"Test audio"}''');source=source.replace('watcher.changed.connect(root.backlightChanged)','watcher.changed.connect(function(hardware){})')
    state.write_text(source)
    osd=base/'quickshell/modules/system/SystemOsd.qml';osd.write_text(osd.read_text().replace('    visible:reveal>0 && !!screen','    visible:false'))
    controller=base/'quickshell/modules/system/OsdController.qml';controller.write_text(controller.read_text().replace('    id:root','    id:root\n    readonly property var testWindow:panel.item',1))
    for relative in ('modules/control/ControlCenter.qml','modules/notifications/NotificationPopups.qml'):
        path=base/'quickshell'/relative;path.write_text('\n'.join('    visible:false' if line.startswith('    visible:') else line for line in path.read_text().splitlines())+'\n')
    config=base/'quickshell/shell.qml';source=config.read_text().replace('import Quickshell.Io','import Quickshell.Wayland\nimport Quickshell.Io').replace('Launcher { id: launcher }','Launcher { id: launcher;visible:false }').replace('MenuPanel {','MenuPanel {visible:false;')
    source=source.rstrip()[:-1]+''' property var rememberedOsd:null
    IpcHandler {target:"test"
        function resume():void {System.SessionState.events.prepareForSleep(false);}
        function remember():void {shell.rememberedOsd=osd.testWindow;}
        function uiBrightness(value:int):void {System.SystemControls.requestBrightness(value,true);}
        function kernelEvent(hardware:bool):void {System.SystemControls.backlightChanged(hardware);}
        function snapshot():string {
            const win=osd.testWindow;
            return JSON.stringify({same:win===shell.rememberedOsd,opened:osd.opened,alive:osd.alive,kind:osd.kind,loaded:osd.loaded,suppressed:osd.suppressed,
                placement:win ? {left:win.anchors.left,top:win.anchors.top,bottom:win.anchors.bottom,margin:win.margins.left,width:win.implicitWidth,height:win.implicitHeight,screenWidth:win.screen.width,noFocus:win.WlrLayershell.keyboardFocus===WlrKeyboardFocus.None,noZone:win.exclusionMode===ExclusionMode.Ignore} : null});
        }
    }
}''';config.write_text(source)
    display=os.environ['WAYLAND_DISPLAY'];display=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),WAYLAND_DISPLAY=display,PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],PIXELRAIL_QML=str(config),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'),SYSTEM_TEST_HELPER=str(helper),SYSTEM_BRIGHTNESS_FILE=str(base/'brightness'))
    bus_config=base/'bus.conf';bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
    bus=subprocess.Popen(['dbus-daemon','--config-file='+str(bus_config),'--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,text=True);env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip()
    def ipc(target,method,*args):return subprocess.check_output(['qs','ipc','-p',str(config),'call',target,method,*map(str,args)],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
    def state():return json.loads(ipc('system','state'))
    def wait(predicate):
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            try:
                value=state()
                if predicate(value):return value
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(.03)
        raise AssertionError(state())
    def key(action):
        result=subprocess.run([str(ROOT/'scripts/pixelrail-system'),action],env=env,capture_output=True,text=True,timeout=4)
        assert result.returncode==0,result.stdout+result.stderr
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            wait(lambda row:row['audioAvailable']);key('volume-up');wait(lambda row:abs(row['volume']-.45)<.001 and row['osd']['loaded'])
            ipc('test','remember');key('volume-down');wait(lambda row:abs(row['volume']-.4)<.001)
            key('volume-mute');wait(lambda row:row['muted'])
            key('brightness-up');wait(lambda row:row['brightness'].get('percent')==45 and row['osd']['kind']=='brightness')
            snapshot=json.loads(ipc('test','snapshot'));assert snapshot['same'],snapshot
            placement=snapshot['placement'];assert placement['left'] and not placement['top'] and not placement['bottom'] and placement['noFocus'] and placement['noZone'],placement
            assert placement['margin']==78 and placement['width']+placement['margin']+12<=placement['screenWidth'],placement
            key('brightness-down');key('volume-up');wait(lambda row:row['brightness'].get('percent')==40 and not row['brightnessPending']);assert state()['osd']['kind']=='volume'
            key('brightness-up');wait(lambda row:row['brightness'].get('percent')==45 and row['osd']['kind']=='brightness')
            for _ in range(15):key('volume-up')
            wait(lambda row:row['volume']==1);assert json.loads(ipc('test','snapshot'))['same']
            key('brightness-down');wait(lambda row:row['brightness'].get('percent')==40)
            ipc('control','open','overview');wait(lambda row:row['osd']['suppressed'] and not row['osd']['opened'])
            key('volume-down');wait(lambda row:abs(row['volume']-.95)<.001);assert not state()['osd']['opened']
            ipc('test','uiBrightness','77');ipc('control','hide');wait(lambda row:row['brightness'].get('percent')==77 and not row['brightnessPending']);assert not state()['osd']['opened'],'slider completion showed OSD after close'
            ipc('control','open','overview');wait(lambda row:row['osd']['suppressed'])
            (base/'brightness').write_text('62');ipc('test','kernelEvent','false');wait(lambda row:row['brightness'].get('percent')==62);assert not state()['osd']['opened']
            ipc('control','hide');(base/'brightness').write_text('67');ipc('test','kernelEvent','true');wait(lambda row:row['brightness'].get('percent')==67 and row['osd']['opened'])
            time.sleep(.7);key('volume-down');time.sleep(.7);assert state()['osd']['opened'];wait(lambda row:not row['osd']['loaded'] and not row['osd']['opened'])
            key('brightness-up');wait(lambda row:row['osd']['loaded']);ipc('test','resume');wait(lambda row:not row['osd']['loaded'])
            ipc('control','open','overview');wait(lambda row:row['osd']['suppressed']);ipc('test','resume');wait(lambda row:not row['osd']['suppressed'])
            assert not json.loads(ipc('control','state'))['opened'],'resume left Control Center open'
            started=time.monotonic();cycles=0;rss=[]
            if args.soak_seconds:
                key('volume-down');wait(lambda row:row['osd']['loaded']);ipc('test','remember')
            while time.monotonic()-started<args.soak_seconds:
                for action in ('volume-up','brightness-up','volume-down','brightness-down'):
                    assert ipc('system','action',action)=='true'
                if cycles%10==0:
                    snap=json.loads(ipc('test','snapshot'));assert snap['same'] and snap['placement']['noFocus'],snap
                    rss.append(int((Path('/proc')/str(child.pid)/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')/1048576)
                cycles+=1;time.sleep(.15)
            wait(lambda row:not row['brightnessPending'] and not row['brightnessBusy'] and not row['volumePending'])
            wait(lambda row:not row['osd']['loaded'])
            print('SYSTEM_SOAK',json.dumps({'seconds':args.soak_seconds,'cycles':cycles,'rss_mib':rss}),flush=True)
            assert json.loads(ipc('notifications','state'))['count']==0,'OSD emitted a desktop notification'
            assert isinstance(state()['backlightEvents'],bool)
            assert child.poll() is None
        finally:
            os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5);time.sleep(.1);bus.terminate();bus.wait(timeout=3)
        log.seek(0);output=log.read();print(output)
    for marker in ('ERROR','ReferenceError','TypeError','Unable to assign','Binding loop','not a type','Duplicate signal'):assert marker not in output,marker
print('System runtime: actual qs IPC/key routes, fake hardware, one reused native OSD, placement/no-focus/no-zone, caps/mute, external kernel event sync, suppression and auto-unload: PASS')
