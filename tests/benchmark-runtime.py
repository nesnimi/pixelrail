"""Isolated unmapped shell, finite stress/soak, private notification bus; no device writes."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from gi.repository import Gio,GLib
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from benchmark import Benchmark,process
parser=argparse.ArgumentParser();parser.add_argument('--legacy',action='store_true',help='Reproduce pre-v2.5 duplicate theme/timer work in the private copy');parser.add_argument('--soak-seconds',type=int,default=0);parser.add_argument('--output',type=Path,default=ROOT/'.cache/benchmark-latest.json');args=parser.parse_args()
if not 0<=args.soak_seconds<=900:parser.error('soak 0..900 seconds')
@contextmanager
def environment(values):
    previous=dict(os.environ);os.environ.update(values)
    try:yield
    finally:os.environ.clear();os.environ.update(previous)
def atomic(path,data):
    temporary=path.with_suffix('.new');temporary.write_bytes(data);os.replace(temporary,path)
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell');(base/'scripts').symlink_to(ROOT/'scripts',target_is_directory=True)
    if args.legacy:
        path=base/'quickshell/theme/ThemeManager.qml';source=path.read_text().replace('                if(value.length && value===root.lastPaletteText)return;','');path.write_text(source)
        path=base/'quickshell/modules/notifications/NotificationController.qml';source=path.read_text().replace('        }\n        armTimer();\n        // Closing', '            armTimer();\n        }\n        armTimer();\n        // Closing');path.write_text(source)
    image=base/'image.png'
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    image.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,24,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x50\x80\xb0'*32)*24))+chunk(b'IEND',b''))
    backend=base/'menu-backend';backend.write_text('''#!/usr/bin/env python3
import json,os,sys
image=os.environ['BENCH_IMAGE'];mode=sys.argv[2]
if sys.argv[1]=='thumbnail':
 json.loads(sys.stdin.readline());print(json.dumps({'url':image,'width':32,'height':24,'type':'PNG'}))
else:
 items=[{'id':str(i),'title':'Тест '+str(i),'subtitle':'Unicode ✓','kind':'text'} for i in range(60)]
 if mode=='wallpaper':items=[{'id':str(i),'title':'Обои '+str(i),'subtitle':'Test fixture','category':'wallpapers','thumbnail':image} for i in range(80)]
 if mode=='clipboard':items[0].update(kind='image',thumbnail=image)
 print(json.dumps({'title':mode,'items':items}))
''');backend.chmod(0o755)
    for relative in ('modules/control/ControlCenter.qml','modules/notifications/NotificationPopups.qml'):
        path=base/'quickshell'/relative;path.write_text('\n'.join('    visible:false' if line.startswith('    visible:') else line for line in path.read_text().splitlines())+'\n')
    config=base/'quickshell/shell.qml';source=config.read_text().replace('Launcher { id: launcher }','Launcher { id: launcher;visible:false }').replace('MenuPanel {','MenuPanel {visible:false;backend:'+json.dumps(str(backend))+';')
    source=source.rstrip()[:-1]+''' property int paletteAssignments:0
    Connections {target:Theme.ThemeManager;function onSchemesChanged(){shell.paletteAssignments++;}}
    IpcHandler {target:"bench"
        function state():string {return JSON.stringify({paletteAssignments:shell.paletteAssignments,mode:Theme.ThemeManager.mode,busy:Theme.ThemeManager.busy,notifications:notifications.history.length,live:notifications.history.filter(e=>e.live).length,control:control.opened,menus:!!menus.item});}
    }
}''';source=source.replace('suppressed:control.opened','suppressed:true || control.opened');config.write_text(source)
    display=os.environ.get('WAYLAND_DISPLAY','');display=display if display.startswith('/') else str(Path(os.environ['XDG_RUNTIME_DIR'])/display)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),WAYLAND_DISPLAY=display,PIXELRAIL_QML=str(config),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'),PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],BENCH_IMAGE=image.as_uri())
    bus_config=base/'bus.conf';bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
    bus=subprocess.Popen(['dbus-daemon','--config-file='+str(bus_config),'--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,text=True);env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip()
    client=Gio.DBusConnection.new_for_address_sync(env['DBUS_SESSION_BUS_ADDRESS'],Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
    manifest=base/'.local/state/pixelrail/deployments/test/manifest.json';manifest.parent.mkdir(parents=True);manifest.write_text(json.dumps({'home':str(base),'release':str(base/'.local/share/pixelrail/releases/test'),'source_config':str(config)}))
    subprocess.run([str(ROOT/'scripts/pixelrail-theme'),'sync'],env=env,check=True,capture_output=True,timeout=15)
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            with environment(env):
                bench=Benchmark(child.pid)
                deadline=time.monotonic()+8
                while True:
                    try:bench.state('control');break
                    except (RuntimeError,subprocess.SubprocessError):
                        if time.monotonic()>deadline:raise
                        time.sleep(.05)
                bench.call('notifications','enable');deadline=time.monotonic()+5
                while not bench.state('notifications')['enabled']:
                    if time.monotonic()>deadline:raise AssertionError('native server unavailable')
                    time.sleep(.05)
                def send(index):
                    client.call_sync('org.freedesktop.Notifications','/org/freedesktop/Notifications','org.freedesktop.Notifications','Notify',GLib.Variant('(susssasa{sv}i)',('Bench',0,'','Message '+str(index),'Кириллица',['default','Open'],{},0)),GLib.VariantType.new('(u)'),Gio.DBusCallFlags.NONE,3000,None)
                for index in range(200):send(index)
                assert bench.state('bench')['notifications']==60 and bench.state('bench')['live']<=20
                result=bench.run(20,1,exercise=True,stress=True)
                palette=base/'cache/pixelrail/theme/palette.json';data=palette.read_bytes();before=bench.state('bench')['paletteAssignments']
                for _ in range(10):atomic(palette,data);time.sleep(.08)
                result['same_palette_assignments']=bench.state('bench')['paletteAssignments']-before
                assert result['same_palette_assignments']==(10 if args.legacy else 0),result['same_palette_assignments']
                result['legacy']=args.legacy
                settings=base/'config/pixelrail/theme.json'
                for mode in ('light','dark')*5:
                    atomic(settings,json.dumps({'mode':mode,'accent':None}).encode());deadline=time.monotonic()+5
                    while bench.state('bench')['mode']!=mode or bench.state('bench')['busy']:
                        if time.monotonic()>deadline:raise AssertionError('theme did not settle')
                        time.sleep(.02)
                bench.idle('theme_notifications_settled',2)
                result['memory']=bench.memory
                result['fixture']='unmapped panels; real QML/qs/private NotificationServer; finite fake menu data and cached 32x24 images; no rendered-frame claim'
                started=time.monotonic();cycles=0;soak=[]
                while time.monotonic()-started<args.soak_seconds:
                    bench.launcher();bench.control('overview');bench.control('notifications');bench.control('wifi');bench.control('bluetooth');bench.close()
                    bench.menu('clipboard');bench.menu('wallpaper');send(cycles+200)
                    if cycles%10==0:soak.append(process(child.pid))
                    cycles+=1
                    time.sleep(min(2,max(0,args.soak_seconds-(time.monotonic()-started))))
                bench.close();bench.idle('after_soak',2);result['memory']=bench.memory
                result['soak']={'requested_seconds':args.soak_seconds,'elapsed_seconds':time.monotonic()-started,'cycles':cycles,'samples':soak}
                result['end_state']=bench.state('bench');assert not result['end_state']['control'] and not result['end_state']['menus']
                assert result['end_state']['notifications']<=60 and result['end_state']['live']<=20
                assert len(__import__('panel').shells())==1
                result['final_settled']=process(child.pid)
                args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
                print('Isolated benchmark PASS:',args.output,'same palette assignments',result['same_palette_assignments'],'soak cycles',cycles,flush=True)
        finally:
            os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5)
            # Wait for owned descendants before deleting their HOME.
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                alive=[]
                for entry in Path('/proc').glob('[0-9]*'):
                    try:
                        stat=entry.joinpath('stat').read_text().rsplit(')',1)[1].split()
                        if stat[0]!='Z' and int(stat[2])==child.pid and ('HOME='+str(base)).encode() in entry.joinpath('environ').read_bytes().split(b'\0'):alive.append(int(entry.name))
                    except (OSError,ValueError):pass
                if not alive:break
                time.sleep(.03)
            assert not alive,'test descendants outlived sandbox'
            client.close_sync(None);bus.terminate();bus.wait(timeout=3)
        log.seek(0);output=log.read()
        for marker in ('ERROR','TypeError','ReferenceError','Unable to assign','Binding loop','not a type'):assert marker not in output,output[-5000:]
