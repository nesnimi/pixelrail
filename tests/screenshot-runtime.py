"""Real qs IPC/worker lifecycle, fake focus protocol and tools. Never maps test windows."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
ROOT=Path.cwd();qs=shutil.which('qs') or shutil.which('quickshell')
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    testing=base/'quickshell/testing';testing.mkdir()
    (testing/'TestFocusGrab.qml').write_text('import QtQml\nQtObject {property var windows:[];property bool active:false;signal cleared();onActiveChanged:if(!active)cleared();}\n')
    for relative,import_path in [('modules/launcher/Launcher.qml','../../testing'),('modules/control/ControlCenter.qml','../../testing'),('components/MenuPanel.qml','../testing')]:
        path=base/'quickshell'/relative;s=path.read_text().replace('import QtQuick\n','import QtQuick\nimport "'+import_path+'" as Testing\n',1)
        s=s.replace('HyprlandFocusGrab {','Testing.TestFocusGrab {id:testGrab;')
        s=re.sub(r'    id: ?root\n','    id:root\n    property var testFocus:testGrab\n',s,count=1)
        # Preserve opened/grab/mode behavior, while unmapping actual layer surfaces.
        s=s.replace('active: root.visible && root.opened &&','active: root.opened &&').replace('active:root.opened && root.visible &&','active:root.opened &&').replace('active:root.visible &&','active:root.opened &&')
        s=s.replace('if(root.visible && root.opened &&','if(root.opened &&')
        s='\n'.join('    visible:false' if line.startswith('    visible:') else line for line in s.splitlines())+'\n';path.write_text(s)
    path=base/'quickshell/modules/notifications/NotificationPopups.qml';path.write_text(path.read_text().replace('    visible:', '    visible:false && '))
    backend=base/'menu';backend.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"items":[],"title":"Fixture"}))\n');backend.chmod(0o755)
    config=base/'quickshell/shell.qml';s=config.read_text().replace('import Quickshell.Io','import Quickshell.Wayland\nimport Quickshell.Io',1).replace('MenuPanel {','MenuPanel {backend:'+json.dumps(str(backend))+';')
    s=s.replace('suppressed:control.opened','suppressed:true || control.opened')
    s=s.rstrip()[:-1]+''' property var remembered:null
    function testView():var {return control.opened ? control.window : launcher.opened ? launcher : menus.item && menus.item.opened ? menus.item : null;}
    IpcHandler {target:"test"
        function remember():void {shell.remembered=shell.testView();}
        function clear():void {const item=shell.testView();if(item)item.testFocus.cleared();}
        function timeout(value:int):void {System.ScreenshotState.captureTimeout=value;System.ScreenshotState.startupTimeout=120;}
        function helper(value:string):void {System.ScreenshotState.helper=value;}
        function stale():void {System.ScreenshotState.phase="arming";}
        function snapshot():string {
            const item=shell.testView();return JSON.stringify({opened:!!item,same:item===shell.remembered,grab:!!item && item.testFocus.active,
              keyboardNone:!!item && item.WlrLayershell.keyboardFocus===WlrKeyboardFocus.None,
              capture:JSON.parse(System.ScreenshotState.state()),pid:Quickshell.processId});
        }
    }
}''';config.write_text(s)
    binary=base/'bin';binary.mkdir();tool='''#!/usr/bin/env python3
import json,os,sys,time,subprocess
from pathlib import Path
base=Path(os.environ['SHOT_BASE']);name=Path(sys.argv[0]).name
if name=='slurp':
 # The QML worker keeps its handshake stdin pipe open. The selector must not
 # inherit that pipe: real slurp reads candidate rectangles until EOF first.
 assert os.readlink('/proc/self/fd/0')==os.devnull,'slurp stdin must be /dev/null, got '+os.readlink('/proc/self/fd/0')
 assert os.read(0,1)==b'','slurp stdin must immediately return EOF'
 result=subprocess.check_output([os.environ['REAL_QS'],'ipc','-p',os.environ['PIXELRAIL_QML'],'call','test','snapshot'],timeout=2)
 state=json.loads(result);assert state['capture']['active'] and state['opened'] and not state['grab'] and state['keyboardNone'],state
 (base/'selector').write_bytes(result)
 while not (base/'release').exists():time.sleep(.02)
 if (base/'release').read_text()=='cancel':print('selection cancelled',file=sys.stderr);sys.exit(1)
 print('10,20 200x100')
if name=='grim':
 if (base/'release').read_text()=='fail':sys.exit(2)
 result=subprocess.check_output([os.environ['REAL_QS'],'ipc','-p',os.environ['PIXELRAIL_QML'],'call','test','snapshot'],timeout=2)
 assert json.loads(result)['opened'] and json.loads(result)['capture']['active']
 Path(sys.argv[-1]).write_bytes(b'PNG '+result)
if name=='wl-copy':(base/'clipboard').write_bytes(sys.stdin.buffer.read())
'''
    for name in ('slurp','grim','wl-copy','notify-send'):
        path=binary/name;path.write_text(tool);path.chmod(0o755)
    display=os.environ['WAYLAND_DISPLAY'];display=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    # Exercise the deployed/default helper path, rather than hiding it with an override.
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),XDG_PICTURES_DIR=str(base/'Pictures'),WAYLAND_DISPLAY=display,PATH=str(binary)+':/usr/bin',PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],PIXELRAIL_QML=str(config),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'),SHOT_BASE=str(base),REAL_QS=qs)
    env.pop('PIXELRAIL_SHOT_HELPER',None)
    bus_config=base/'bus.conf';bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
    bus=subprocess.Popen(['dbus-daemon','--config-file='+str(bus_config),'--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,text=True);env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip()
    def ipc(target,method,*args):return subprocess.check_output([qs,'ipc','-p',str(config),'call',target,method,*map(str,args)],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
    def snapshot():return json.loads(ipc('test','snapshot'))
    def wait(predicate):
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            try:
                value=snapshot()
                if predicate(value):return value
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(.02)
        raise AssertionError(value if 'value' in locals() else 'no IPC')
    def reset_files():
        for name in ('selector','release'):(base/name).unlink(missing_ok=True)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            wait(lambda row:not row['capture']['active']);original=snapshot()['pid']
            cases=[('control','overview'),('control','notifications'),('launcher',None)]+[('menus',mode) for mode in ('clipboard','wallpaper','power','keys','controls','command','windows','media','emoji')]
            for target,mode in cases:
                if target=='launcher':ipc(target,'toggle')
                else:ipc(target,'open',mode)
                wait(lambda row:row['opened'] and row['grab']);ipc('test','remember')
                for outcome in ('ok','cancel'):
                    reset_files();result=subprocess.run([str(ROOT/'scripts/pixelrail-shot')],env=env,capture_output=True,text=True,timeout=3);assert result.returncode==0,result.stderr
                    wait(lambda row:row['capture']['active'] and (base/'selector').exists())
                    assert ipc('screenshot','capture')=='false','duplicate selector accepted'
                    ipc('test','clear');assert snapshot()['opened'],'focus loss closed popup during capture'
                    (base/'release').write_text(outcome);wait(lambda row:not row['capture']['active'])
                    row=snapshot();assert row['opened'] and row['same'] and row['grab'] and not row['keyboardNone'],row
                ipc('test','clear');wait(lambda row:not row['opened'])
            # Tool error, abort, killed worker, failed start, watchdog, then another successful capture.
            ipc('control','open','overview');wait(lambda row:row['opened']);ipc('test','remember')
            for failure in ('fail','abort','kill','watchdog'):
                reset_files();ipc('test','timeout',10000);assert ipc('screenshot','capture')=='true'
                value=wait(lambda row:row['capture']['active'] and (base/'selector').exists())
                # Arm the short watchdog after the real fake-selector IPC round trip.
                # Under load that startup can itself exceed 150 ms; expiry before
                # the marker is valid cleanup, not a failed production capture.
                if failure=='watchdog':ipc('test','timeout',150)
                if failure=='fail':(base/'release').write_text('fail')
                elif failure=='abort':ipc('screenshot','abort')
                elif failure=='kill':os.kill(int(value['capture']['pid']),signal.SIGKILL) # This test's capture worker only.
                wait(lambda row:not row['capture']['active']);assert snapshot()['opened'] and snapshot()['grab']
            ipc('test','helper',str(base/'missing'));ipc('screenshot','capture');wait(lambda row:row['capture']['phase']=='idle');assert snapshot()['capture']['error']
            # A requested start is not a capture: no READY means Escape/grabs stay
            # normal. Exercise real QProcess EACCES, exceptions, no handshake and
            # a worker which cannot be stopped by TERM (the original hang).
            for failure in ('permission','exception','no-ready','ignore-term','bad-protocol'):
                helper=base/('helper-'+failure)
                source='#!/usr/bin/env python3\nimport sys,time,signal\n'
                if failure=='exception':source+='raise RuntimeError("fixture worker startup exception")\n'
                elif failure=='no-ready':source+='time.sleep(30)\n'
                else:
                    source+='signal.signal(signal.SIGTERM,signal.SIG_IGN)\nprint(\'{"event":"ready"}\',flush=True)\nsys.stdin.readline()\nprint(\'{"event":"selecting"}\',flush=True)\n'
                    if failure=='bad-protocol':source+='print("null",flush=True)\n'
                    source+='time.sleep(30)\n'
                helper.write_text(source);helper.chmod(0o644 if failure=='permission' else 0o755)
                ipc('test','helper',str(helper));ipc('test','timeout',10000)
                if failure=='ignore-term':
                    ipc('screenshot','capture');wait(lambda row:row['capture']['active']);ipc('test','timeout',150)
                    wait(lambda row:row['capture']['phase']=='idle' and not row['capture']['running'])
                    assert snapshot()['capture']['error'],'watchdog must diagnose the hung worker'
                    ipc('test','timeout',10000)
                    ipc('screenshot','capture');wait(lambda row:row['capture']['active'])
                    ipc('screenshot','reset');row=snapshot()
                    assert not row['capture']['active'] and row['grab'] and not row['keyboardNone'],row
                else:ipc('screenshot','capture')
                if failure=='no-ready':
                    row=snapshot();assert not row['capture']['active'] and row['grab'] and not row['keyboardNone'],row
                wait(lambda row:row['capture']['phase']=='idle' and not row['capture']['running'])
                row=snapshot();assert row['opened'] and row['grab'] and not row['keyboardNone'],row
                if failure!='ignore-term':assert row['capture']['error'],row
            # Stale mode without a worker must not suppress Escape / outside click.
            ipc('test','stale');row=snapshot();assert not row['capture']['active'] and row['grab'],row
            assert ipc('screenshot','capture')=='false';ipc('screenshot','reset')
            ipc('test','helper',str(ROOT/'scripts/pixelrail-shot'));ipc('test','timeout',10000);reset_files();ipc('screenshot','capture');wait(lambda row:(base/'selector').exists());(base/'release').write_text('ok');wait(lambda row:not row['capture']['active'])
            # Lose the startup acknowledgement AFTER real capture IPC. The
            # caller must reset that actual worker, never spawn a second slurp.
            proxy=binary/'qs';proxy.write_text('''#!/usr/bin/env python3
import os,sys
if sys.argv[-1]=='state' and os.path.exists(os.environ['SHOT_BASE']+'/lose-state'):
 print('fixture: screenshot IPC disconnected',file=sys.stderr);sys.exit(1)
if sys.argv[-1]=='capture':open(os.environ['SHOT_BASE']+'/lose-state','w').close()
os.execv(os.environ['REAL_QS'],[os.environ['REAL_QS']]+sys.argv[1:])
''');proxy.chmod(0o755)
            reset_files();result=subprocess.run([str(ROOT/'scripts/pixelrail-shot')],env=env,capture_output=True,text=True,timeout=5)
            assert result.returncode and 'IPC state' in result.stderr,result.stderr
            wait(lambda row:not row['capture']['active'] and not row['capture']['running'])
            assert snapshot()['opened'] and snapshot()['grab'];proxy.unlink()
            (base/'lose-state').unlink();reset_files()
            result=subprocess.run([str(ROOT/'scripts/pixelrail-shot')],env=env,capture_output=True,text=True,timeout=5);assert result.returncode==0,result.stderr
            wait(lambda row:(base/'selector').exists());(base/'release').write_text('cancel');wait(lambda row:not row['capture']['active'])
            registry=json.loads(subprocess.check_output([qs,'list','--all','--json'],env=env,text=True,timeout=3));assert len(registry)==1,registry
            assert snapshot()['pid']==original and snapshot()['same'];assert (base/'clipboard').read_bytes().startswith(b'PNG ')
            ipc('test','clear');wait(lambda row:not row['opened'])
        finally:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=4);time.sleep(.1);bus.terminate();bus.wait(timeout=3)
        log.seek(0);output=log.read();print(output)
    for marker in ('TypeError','ReferenceError','Unable to assign','Binding loop','Failed to load configuration'):assert marker not in output,marker
print('Screenshot runtime: 12 popups, READY-before-mode, cancel/repeat/error/abort/crash/EACCES/startup/handshake/watchdog/TERM escalation/stale reset, focus rearmed, one qs: PASS')
