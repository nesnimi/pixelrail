"""Panel transactions with real child Waybars and isolated qs IPC fixtures."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
root=Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as temporary:
    base=Path(temporary);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    binary=base/'bin';binary.mkdir();home=base/'home';home.mkdir()
    barconfig=home/'.config/waybar';barconfig.mkdir(parents=True)
    (barconfig/'config.jsonc').write_text((root/'waybar/config.jsonc').read_text())
    (barconfig/'style.css').write_text((root/'waybar/style.css').read_text())
    model=base/'model.json';model.write_text(json.dumps({'prepared':False,'enabled':False,'visible':False,'screen':'test','exclusiveZone':0,'error':''}))
    fail=base/'fail';calls=base/'calls'
    qs=binary/'qs';qs.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
args=sys.argv[1:];p=pathlib.Path(os.environ['PANEL_MODEL']);data=json.loads(p.read_text())
control=pathlib.Path(os.environ['PANEL_FAIL']);failure=control.read_text() if control.exists() else ''
if args[0]=='list':print(json.dumps([{'id':'pixel','pid':987654,'config_path':os.environ['PANEL_QML']}]))
elif args[0]=='ipc':
    method=args[args.index('panel')+1]
    with open(os.environ['PANEL_CALLS'],'a') as log:log.write(method+'\\n')
    if method=='state':print(json.dumps(data))
    elif method=='prepare':
        data['prepared']=failure!='prepare';data['error']='fixture broken' if failure=='prepare' else '';p.write_text(json.dumps(data))
    elif method=='activate':
        if failure=='activate':print('false');sys.exit(0)
        data.update(enabled=True,visible=True,exclusiveZone=66);p.write_text(json.dumps(data));print('true')
    elif method=='hide':
        if failure=='hide':sys.exit(1)
        data.update(enabled=False,visible=False,prepared=False,exclusiveZone=0);p.write_text(json.dumps(data))
else:sys.exit(3)
''');qs.chmod(0o755)
    waybar=binary/'waybar';waybar.write_text('''#!/usr/bin/env python3
import os,time,sys
if os.environ.get('PANEL_BAR_FAIL')=='1':sys.exit(1)
while True:time.sleep(10)
''');waybar.chmod(0o755)
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_RUNTIME_DIR=str(runtime),
        XDG_CACHE_HOME=str(home/'.cache'),XDG_STATE_HOME=str(home/'.local/state'),
        WAYLAND_DISPLAY='panel-fixture',PATH=str(binary)+':/usr/bin',PANEL_MODEL=str(model),PANEL_FAIL=str(fail),
        PANEL_QML=str(root/'quickshell/shell.qml'),PANEL_CALLS=str(calls))
    def run(*args,success=True,extra=None):
        result=subprocess.run([str(root/'scripts/pixelrail-panel'),*args],env=env|(extra or {}),capture_output=True,text=True,timeout=10)
        assert (result.returncode==0)==success,result.stdout+result.stderr
        return result
    def status():return json.loads(run('status').stdout)
    def state():return json.loads(model.read_text())
    def stop_owned():
        for record in runtime.glob('pixelrail-panel-*/waybar.json'):
            pid=json.loads(record.read_text())['pid']
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    foreign=None
    try:
        assert status()['settings']['mode']=='waybar'
        run('start');first=status()['ownedWaybar'];assert first
        run('start');assert status()['ownedWaybar']==first
        concurrent=[subprocess.Popen([str(root/'scripts/pixelrail-panel'),'start'],env=env,stdout=subprocess.DEVNULL) for _ in range(4)]
        assert all(child.wait(timeout=6)==0 for child in concurrent)
        assert len(status()['waybar'])==1
        run('mode','sidebar');assert state()['enabled'] and not status()['waybar']
        assert status()['settings']['mode']=='sidebar' and status()['effectiveMode']=='sidebar'
        run('start');assert state()['enabled'] and not status()['waybar']
        run('toggle');assert not state()['enabled'] and state()['exclusiveZone']==0
        assert status()['settings']['mode']=='sidebar'
        run('toggle');assert state()['enabled']
        # Failure returning to Waybar restores the existing Sidebar.
        run('mode','waybar',success=False,extra={'PANEL_BAR_FAIL':'1'})
        assert state()['enabled'] and status()['settings']['mode']=='sidebar'
        run('mode','waybar');assert not state()['enabled'] and status()['ownedWaybar']
        fail.write_text('prepare');result=run('mode','sidebar',success=False)
        assert 'fixture broken' in result.stderr and status()['waybar'] and not state()['enabled']
        fail.write_text('activate');run('mode','sidebar',success=False)
        assert status()['waybar'] and status()['settings']['mode']=='waybar' and not state()['enabled']
        fail.unlink();run('mode','sidebar')
        fail.write_text('hide');run('mode','waybar',success=False)
        assert state()['enabled'] and not status()['waybar']
        fail.unlink();run('mode','waybar')
        # An unrelated Waybar is never adopted, signalled or overlaid.
        foreign=subprocess.Popen([str(waybar),'--foreign'],env=env)
        time.sleep(.06)
        owned=status()['ownedWaybar'];run('mode','sidebar',success=False)
        assert foreign.poll() is None and status()['ownedWaybar']==owned and not state()['enabled']
        # A stale/reused PID record with a different start time cannot confer ownership.
        record=next(runtime.glob('pixelrail-panel-*/waybar.json'))
        forged=dict(owned,start='0');record.write_text(json.dumps(forged))
        assert status()['ownedWaybar'] is None
        run('mode','sidebar',success=False);assert foreign.poll() is None
        record.write_text(json.dumps(owned))
        foreign.terminate();foreign.wait(timeout=3);foreign=None
        # Explicit waybar recovery also repairs malformed panel settings.
        config=home/'.config/pixelrail/panel.json';config.write_text('{broken')
        run('mode','waybar');assert status()['settings']['mode']=='waybar'
        assert str(root/'quickshell/shell.qml')==env['PANEL_QML']
    finally:
        if foreign and foreign.poll() is None:foreign.terminate();foreign.wait(timeout=3)
        stop_owned()
print('Panel: default Waybar, persisted modes, repeat/concurrent start, show/hide, failures/restore, foreign Waybar and PID reuse protection passed')
