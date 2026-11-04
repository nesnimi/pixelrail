"""Native logind/BlueZ events on a private system bus; never suspends or starts BlueZ."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from gi.repository import Gio,GLib
ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell')
    display=os.environ['WAYLAND_DISPLAY'];display=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),WAYLAND_DISPLAY=display)
    bus_config=base/'bus.conf';bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
    bus=subprocess.Popen(['dbus-daemon','--config-file='+str(bus_config),'--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,text=True,start_new_session=True)
    address=bus.stdout.readline().strip();env['DBUS_SESSION_BUS_ADDRESS']=address;env['DBUS_SYSTEM_BUS_ADDRESS']=address
    connection=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
    def name(method,value):return connection.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus',method,GLib.Variant('(su)',(value,4)) if method=='RequestName' else GLib.Variant('(s)',(value,)),None,Gio.DBusCallFlags.NONE,2000,None)
    name('RequestName','org.freedesktop.login1')
    config=base/'quickshell/test.qml';config.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "modules/system" as System
ShellRoot {
 property int resumes:0
 property int changes:0
 Connections {target:System.SessionState;function onResumed(){resumes++;}function onBackendChanged(){changes++;}}
 IpcHandler {target:"test";function state():string{return JSON.stringify({resumes:resumes,changes:changes,error:System.SessionState.error,bluez:!!System.SessionState.events && System.SessionState.events.bluezAvailable});}}
}''')
    def state():return json.loads(subprocess.check_output(['qs','ipc','-p',str(config),'call','test','state'],env=env,stderr=subprocess.DEVNULL,timeout=2))
    def wait(predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                value=state()
                if predicate(value):return value
            except (ValueError,subprocess.SubprocessError):pass
            time.sleep(.03)
        raise AssertionError(value if 'value' in locals() else 'no IPC')
    try:
        with (base/'log').open('w+') as log:
            child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                wait(lambda v:not v['error']);time.sleep(.1)
                connection.emit_signal(None,'/org/freedesktop/login1','org.freedesktop.login1.Manager','PrepareForSleep',GLib.Variant('(b)',(True,)));connection.flush_sync(None);time.sleep(.1);assert state()['resumes']==0
                connection.emit_signal(None,'/org/freedesktop/login1','org.freedesktop.login1.Manager','PrepareForSleep',GLib.Variant('(b)',(False,)));connection.flush_sync(None);wait(lambda v:v['resumes']==1)
                name('RequestName','org.bluez');wait(lambda v:v['bluez'] and v['changes']>=1)
                name('ReleaseName','org.bluez');wait(lambda v:not v['bluez'] and v['changes']>=2)
            finally:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=3)
            # Missing plugin must leave the rest of QML/IPC usable, with a clear error.
            (base/'quickshell/native/PixelRail/DBusLease/libpixelraillease.so').unlink()
            child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:wait(lambda v:bool(v['error']))
            finally:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=3)
    finally:connection.close_sync(None);os.killpg(bus.pid,signal.SIGTERM);bus.wait(timeout=3)
print('Private system D-Bus: prepare/sleep/resume, BlueZ loss/reconnect, missing plugin leaves IPC alive: PASS')
