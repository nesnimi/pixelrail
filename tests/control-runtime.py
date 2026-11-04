"""New panels remain unmapped. Notification traffic uses a private session bus."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from gi.repository import Gio, GLib
import sys
from unittest.mock import patch
foreign_child=None
root=Path.cwd()
sys.path.insert(0,str(root/'scripts'))
import notifications as notification_backend
# Deterministic regressions for both halves of the non-atomic D-Bus lookup.
with patch.object(notification_backend,'bus',side_effect=[['s',':1.old'],[]]):
    assert notification_backend.owner() is None
with patch.object(notification_backend,'bus',side_effect=[['s',':1.old'],['u','123'],['s',':1.new']]):
    assert notification_backend.owner() is None
with patch.object(notification_backend,'bus',side_effect=[['s',':1.stable'],['u','123'],['s',':1.stable']]):
    assert notification_backend.owner()=={'name':':1.stable','pid':123}
with patch.object(notification_backend,'bus',side_effect=notification_backend.NotificationError('transport unavailable')):
    try:notification_backend.owner()
    except notification_backend.NotificationError:pass
    else:raise AssertionError('D-Bus transport error was masked')
with tempfile.TemporaryDirectory(dir=root/'.cache') as temporary:
    base=Path(temporary);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    shutil.copytree(root/'quickshell',base/'quickshell');(base/'scripts').symlink_to(root/'scripts',target_is_directory=True)
    for relative in ('modules/control/ControlCenter.qml','modules/notifications/NotificationPopups.qml'):
        path=base/'quickshell'/relative
        source=path.read_text();lines=source.splitlines();lines=[('    visible:false' if line.strip().startswith('visible:') and line.startswith('    visible:') else line) for line in lines];path.write_text('\n'.join(lines)+'\n')
    config=base/'quickshell/shell.qml'
    source=config.read_text().replace('Launcher { id: launcher }','Launcher { id: launcher;visible:false }')
    source=source.rstrip()[:-1]+''' property var rememberedControlWindow:null
    IpcHandler {
        target:"test"
        function snapshot():string {return JSON.stringify({control:JSON.parse(control.state()),launcher:launcher.opened,
            sameWindow:rememberedControlWindow===control.window,count:notifications.history.length,popups:notifications.popups.length,live:notifications.history.filter(e=>e.live).length,
            first:notifications.history.length ? notifications.history[0].summary : ""});}
        function rememberWindow():void {rememberedControlWindow=control.window;}
        function mouseMode(value:string):void {control.window.selectSection(value);}
        function staleCloseReopen():void {
            control.open("overview");control.closeRequested();control.close();control.open("wifi");
        }
        function invokeFirst():void {if(notifications.history.length)notifications.invoke(notifications.history[0].id,0);}
        function clear():void {notifications.clear();}
        function hidePopup():void {notifications.popups.forEach(id=>notifications.hidePopup(id));}
    }
}'''
    source=source.replace("suppressed:control.opened", "suppressed:true || control.opened")
    config.write_text(source)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),
        XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),
        PIXELRAIL_QML=str(config),PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'))
    display=env.get('WAYLAND_DISPLAY','');env['WAYLAND_DISPLAY']=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    bus_config=base/'bus.conf'
    bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
    bus=subprocess.Popen(['dbus-daemon','--config-file='+str(bus_config),'--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,text=True)
    env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip()
    client=Gio.DBusConnection.new_for_address_sync(env['DBUS_SESSION_BUS_ADDRESS'],Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
    manifest=base/'.local/state/pixelrail/deployments/test/manifest.json';manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'home':str(base),'release':str(base/'.local/share/pixelrail/releases/test'),'source_config':str(config)}))
    binary=base/'bin';binary.mkdir()
    fake=binary/'swaync';fake.write_text('''#!/usr/bin/env python3
from gi.repository import Gio, GLib
import sys
from unittest.mock import patch
connection=Gio.bus_get_sync(Gio.BusType.SESSION,None)
if __import__('os').environ.get('FAKE_SWAYNC_FAIL')=='1':raise SystemExit(1)
loop=GLib.MainLoop()
Gio.bus_own_name_on_connection(connection,'org.freedesktop.Notifications',Gio.BusNameOwnerFlags.NONE,None,None)
loop.run()
''');fake.chmod(0o755)
    env['PATH']=str(binary)+':'+os.environ['PATH']
    def cli(*args,success=True,extra=None):
        result=subprocess.run([str(root/'scripts/pixelrail-notifications'),*args],env=env|(extra or {}),capture_output=True,text=True,timeout=12)
        assert (result.returncode==0)==success,result.stdout+result.stderr
        return result

    def ipc(target,method,*args):
        return subprocess.check_output(['qs','ipc','-p',str(config),'call',target,method,*map(str,args)],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
    def owner():
        p=subprocess.run(['busctl','--user','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner','s','org.freedesktop.Notifications'],env=env,capture_output=True,text=True)
        return p.stdout.strip() if p.returncode==0 else ''
    def snapshot():return json.loads(ipc('test','snapshot'))
    def wait(predicate):
        deadline=time.monotonic()+7
        value=None
        while time.monotonic()<deadline:
            try:
                value=snapshot()
                if predicate(value):return value
            except (subprocess.SubprocessError,ValueError):pass
            time.sleep(.04)
        raise AssertionError(value)
    def send(summary,replaces=0):
        value=client.call_sync('org.freedesktop.Notifications','/org/freedesktop/Notifications','org.freedesktop.Notifications','Notify',
            GLib.Variant('(susssasa{sv}i)',('Fixture',replaces,'',summary,'Body',['default','Open'],{},0)),
            GLib.VariantType.new('(u)'),Gio.DBusCallFlags.NONE,3000,None)
        return 'u '+str(value.unpack()[0])
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait(lambda value:not value['control']['opened'])
            assert not owner(),'default must not register NotificationServer'
            for section in ('overview','wifi','volume','notifications','battery'):
                ipc('control','open',section);wait(lambda value:value['control']['loaded'])
                assert not snapshot()['control']['error']
                ipc('launcher','toggle');wait(lambda value:value['launcher'] and not value['control']['opened'])
                ipc('launcher','hide')
            ipc('test','staleCloseReopen')
            wait(lambda value:value['control']['opened'] and value['control']['loaded'] and value['control']['section']=='wifi')
            ipc('control','hide')
            # Same helpers as Super+A/N, one retained PanelWindow across mode switches.
            cli('open');wait(lambda value:value['control']['mode']=='notifications' and value['control']['opened'])
            ipc('test','rememberWindow')
            subprocess.run([str(root/'scripts/pixelrail-control')],env=env,check=True,timeout=8)
            value=snapshot();assert value['sameWindow'] and value['control']['mode']=='quick-settings' and value['control']['opened'],value
            cli('open');value=snapshot();assert value['sameWindow'] and value['control']['mode']=='notifications' and value['control']['opened'],value
            cli('open');wait(lambda value:not value['control']['opened'])
            for iteration in range(2):
                subprocess.run([str(root/'scripts/pixelrail-control')],env=env,check=True,timeout=8)
                wait(lambda value:value['control']['opened']==(iteration==0))
            ipc('control','open','wifi');wait(lambda value:value['control']['section']=='wifi' and value['control']['opened'])
            ipc('test','rememberWindow');ipc('test','mouseMode','notifications')
            assert snapshot()['control']['mode']=='notifications'
            ipc('control','open','overview');value=snapshot();assert value['sameWindow'] and value['control']['opened'] and value['control']['mode']=='quick-settings',value
            ipc('control','open','wifi');wait(lambda value:value['control']['section']=='wifi')
            ipc('control','open','overview');wait(lambda value:not value['control']['opened'])
            # Full CLI transactions: current SwayNC PID, bridge preflight and verified qs owner.
            for iteration in range(2):
                cli('mode','swaync');assert owner()
                held_owner=owner();cli('mode','swaync');assert owner()==held_owner
                before=json.loads(cli('status').stdout)['owner']['pid'];assert before!=child.pid
                cli('mode','pixelrail');assert json.loads(cli('status').stdout)['owner']['pid']==child.pid
                held_owner=owner();cli('mode','pixelrail');assert owner()==held_owner
                cli('mode','swaync');assert json.loads(cli('status').stdout)['owner']['pid']!=child.pid
            cli('mode','pixelrail')
            # End-to-end keyboard routes, with a retained window and a real native server.
            import statistics
            samples={'legacy_N_to_A_ms':[],'N_to_A_ms':[],'A_to_N_ms':[],'direct_A_ms':[],'startup_only_ms':[],'IPC_A_ms':[]}
            legacy=base/'legacy-control'
            import shlex
            legacy.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'+shlex.quote(str(root/'scripts/pixelrail-shell'))+'\nexec python3 '+shlex.quote(str(root/'scripts/control.py'))+' "$@"\n');legacy.chmod(0o755)
            ipc('control','hide');cli('open')
            for iteration in range(3):
                started=time.monotonic();subprocess.run([str(legacy)],env=env,check=True,timeout=12,capture_output=True,text=True);samples['legacy_N_to_A_ms'].append((time.monotonic()-started)*1000)
                cli('open')
            for iteration in range(5):
                started=time.monotonic();subprocess.run([str(root/'scripts/pixelrail-control')],env=env,check=True,timeout=12,capture_output=True,text=True);samples['N_to_A_ms'].append((time.monotonic()-started)*1000)
                assert snapshot()['control']['mode']=='quick-settings' and snapshot()['control']['opened']
                started=time.monotonic();cli('open');samples['A_to_N_ms'].append((time.monotonic()-started)*1000)
                assert snapshot()['control']['mode']=='notifications' and snapshot()['control']['opened']
            for iteration in range(3):
                started=time.monotonic();subprocess.run([str(root/'scripts/pixelrail-shell')],env=env,check=True,timeout=12,capture_output=True,text=True);samples['startup_only_ms'].append((time.monotonic()-started)*1000)
                started=time.monotonic();subprocess.run([sys.executable,str(root/'scripts/control.py')],env=env,check=True,timeout=8,capture_output=True,text=True);samples['direct_A_ms'].append((time.monotonic()-started)*1000)
                cli('open')
                started=time.monotonic();ipc('control','open','overview');samples['IPC_A_ms'].append((time.monotonic()-started)*1000)
                cli('open')
            measurements={key:{'median':round(statistics.median(value),2),'samples':[round(v,2) for v in value]} for key,value in samples.items()}
            (root/'.cache/navigation-latest.json').write_text(json.dumps(measurements,indent=2))
            print('NAVIGATION_TIMINGS',json.dumps(measurements),flush=True)
            cli('mode','swaync',success=False,extra={'FAKE_SWAYNC_FAIL':'1'})
            wait(lambda value:json.loads(cli('status').stdout)['owner']['pid']==child.pid)
            assert json.loads(cli('status').stdout)['mode']=='pixelrail'
            cli('mode','swaync')
            library=base/'quickshell/native/PixelRail/DBusLease/libpixelraillease.so'
            held=library.with_suffix('.held');library.rename(held)
            old_owner=owner();cli('mode','pixelrail',success=False);assert owner()==old_owner
            held.rename(library)
            # Turn fallback off in this private bus before direct low-level API tests.
            import signal
            fallback=json.loads(cli('status').stdout)['owner']['pid'];os.kill(fallback,signal.SIGTERM)
            wait(lambda value:not owner())
            foreign=binary/'foreign';foreign.write_text(fake.read_text());foreign.chmod(0o755)
            foreign_child=subprocess.Popen([str(foreign)],env=env)
            wait(lambda value:bool(owner()))
            old_owner=owner();cli('mode','pixelrail',success=False);assert owner()==old_owner and foreign_child.poll() is None
            cli('mode','swaync',success=False);assert owner()==old_owner and foreign_child.poll() is None
            foreign_child.terminate();foreign_child.wait(timeout=3);foreign_child=None
            wait(lambda value:not owner())
            cli('mode','pixelrail');assert json.loads(cli('status').stdout)['owner']['pid']==child.pid
            assert ipc('notifications','disable')=='true';wait(lambda value:not owner())
            for cycle in range(3):
                ipc('notifications','enable')
                wait(lambda value:bool(owner()))
                state=json.loads(ipc('notifications','state'));assert state['enabled'],state
                ident=int(send('test '+str(cycle)).split()[-1]);wait(lambda value:value['popups']>0)
                count=snapshot()['count'];send('replacement',ident);wait(lambda value:value['first']=='replacement');assert snapshot()['count']==count
                ipc('test','hidePopup');assert snapshot()['count']==count and snapshot()['popups']==0
                ipc('notifications','dnd');send('muted');wait(lambda value:value['first']=='muted');assert snapshot()['popups']==0
                ipc('notifications','dnd')
                assert ipc('notifications','disable')=='true'
                wait(lambda value:not owner())
            ipc('notifications','enable');wait(lambda value:bool(owner()))
            monitor_log=base/'signals.log'
            with monitor_log.open('w+') as signals:
                monitor=subprocess.Popen(['busctl','--user','monitor','org.freedesktop.Notifications'],env=env,stdout=signals,stderr=subprocess.DEVNULL)
                try:
                    time.sleep(.1);send('Action test');wait(lambda value:value['first']=='Action test')
                    ipc('test','invokeFirst');time.sleep(.1)
                finally:monitor.terminate();monitor.wait(timeout=3)
                signals.seek(0);assert 'ActionInvoked' in signals.read()
            for index in range(65):send('history '+str(index))
            wait(lambda value:value['first']=='history 64');assert snapshot()['count']==60 and snapshot()['live']<=20
            ipc('test','clear');assert snapshot()['count']==0
            assert ipc('notifications','disable')=='true';wait(lambda value:not owner())
        finally:
            child.terminate();child.wait(timeout=5)
            if foreign_child and foreign_child.poll() is None:foreign_child.terminate();foreign_child.wait(timeout=3)
            import signal
            for directory in Path('/proc').glob('[0-9]*'):
                try:
                    if str(fake).encode() in (directory/'cmdline').read_bytes().split(b'\0'):os.kill(int(directory.name),signal.SIGTERM)
                except (OSError,ValueError):pass
            client.close_sync(None);bus.terminate();bus.wait(timeout=3)
            log.seek(0);output=log.read();print(output)
    for marker in ('ERROR','TypeError','ReferenceError','Unable to assign','Binding loop','not a type','Unexpected token'):
        assert marker not in output,marker
print('Control/Notifications: CLI A/N toggles, same window across modes, mouse/IPC synchronization, lazy panels, Launcher exclusion, private D-Bus acquire/release x3, history/DND/actions/clear passed')
