#!/usr/bin/env python3
"""Small on-demand XDG settings/backlight helper. No daemon or polling."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from panel import atomic

def path():return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'pixelrail/desktop.json'
def load():
    try:data=json.loads(path().read_text())
    except (OSError,ValueError):data={}
    if not isinstance(data,dict):data={}
    ratio=data.get('heightRatio',.5)
    if not isinstance(ratio,(int,float)):ratio=.5
    return dict(data,heightRatio=max(.3,min(.75,ratio)),dnd=data.get('dnd') is True)

def parse_brightness(result):
    try:
        device,kind,current,percent,maximum=result.stdout.strip().splitlines()[0].split(',')
        if result.returncode or kind!='backlight' or int(maximum)<=0 or not 0<=int(current)<=int(maximum) or not 0<=int(percent.rstrip('%'))<=100:raise ValueError('unavailable')
        return {'available':True,'percent':int(percent.rstrip('%')),'device':device,'current':int(current),'maximum':int(maximum)}
    except (ValueError,IndexError):return {'available':False,'error':result.stderr.strip() or 'Подсветка недоступна'}
def brightness():
    binary=shutil.which('brightnessctl')
    if not binary:return {'available':False,'error':'brightnessctl не установлен'}
    return parse_brightness(subprocess.run([binary,'-m','-c','backlight'],capture_output=True,text=True,timeout=3))
def audio_state(value):
    node_id=int(value)
    if not 0<=node_id<2**32:raise ValueError('Invalid PipeWire node id')
    binary=shutil.which('pw-dump')
    if not binary:return {'available':False,'error':'pw-dump недоступен: реальный уровень OSD не подтверждён'}
    def get(identifier):
        result=subprocess.run([binary,'-N',str(identifier)],check=True,capture_output=True,text=True,timeout=3)
        return next((row for row in json.loads(result.stdout) if row.get('id')==identifier),None)
    node=get(node_id)
    if not node or node.get('type')!='PipeWire:Interface:Node':raise ValueError('Audio node disappeared')
    info=node.get('info',{});props=info.get('props',{});control=None
    if 'device.id' in props and 'card.profile.device' in props:
        device=get(int(props['device.id']));index=int(props['card.profile.device'])
        for route in (device or {}).get('info',{}).get('params',{}).get('Route',[]):
            if route.get('device')==index and route.get('props',{}).get('channelVolumes'):
                control=route['props'];break
    if control is None:
        control=next((row for row in info.get('params',{}).get('Props',[]) if row.get('channelVolumes')),None)
    if not control or type(control.get('mute')) is not bool:raise ValueError('Audio properties unavailable')
    values=control['channelVolumes']
    if not values or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in values):raise ValueError('Invalid audio volume')
    volume=sum(v**(1/3) for v in values)/len(values)
    return {'available':True,'node':node_id,'volume':volume,'muted':control['mute']}
def keyboard_state(preferred="", toggle=False):
    binary=shutil.which('hyprctl')
    if not binary:return {'available':False,'label':'—','error':'Hyprland недоступен'}
    def devices():
        result=subprocess.run([binary,'-j','devices'],check=True,capture_output=True,text=True,timeout=2)
        return json.loads(result.stdout).get('keyboards',[])
    keyboards=devices()
    keyboard=next((k for k in keyboards if k.get('main')),None) or next((k for k in keyboards if k.get('name')==preferred),None)
    if not keyboard:return {'available':False,'label':'—','error':'Активная клавиатура неизвестна'}
    name=keyboard['name']
    if toggle:
        result=subprocess.run([binary,'switchxkblayout',name,'next'],check=True,capture_output=True,text=True,timeout=2)
        if result.stdout.strip()!='ok':raise ValueError('Не удалось переключить раскладку')
        keyboard=next((k for k in devices() if k.get('name')==name),{})
    keymap=keyboard.get('active_keymap','').lower()
    label='EN' if keymap.startswith('english') else 'RU' if keymap.startswith('russian') else '—'
    return {'available':label!='—','label':label,'name':name,'keymap':keyboard.get('active_keymap','')}

def bluetooth_state(sysroot=Path('/sys')):
    result={'service':None,'controllers':[],'blocked':False,'error':''}
    try:
        binary=shutil.which('busctl')
        if binary:
            reply=subprocess.run([binary,'--system','--timeout=2','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','NameHasOwner','s','org.bluez'],check=True,capture_output=True,text=True,timeout=3)
            if reply.stdout.strip() not in ('b true','b false'):raise ValueError('Неизвестный ответ D-Bus')
            result['service']=reply.stdout.strip()=='b true'
        result['controllers']=[p.name for p in (sysroot/'class/bluetooth').glob('hci*')]
        for path in (sysroot/'class/rfkill').glob('rfkill*'):
            if (path/'type').read_text().strip()=='bluetooth' and any((path/key).read_text().strip()=='1' for key in ('soft','hard')):result['blocked']=True
    except (OSError,ValueError,subprocess.SubprocessError):result['error']='Не удалось проверить Bluetooth'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('load','save','brightness','set-brightness','audio-state','keyboard-state','keyboard-toggle','bluetooth-state'));p.add_argument('value',nargs='?');args=p.parse_args()
    try:
        if args.action=='load':result=load()
        elif args.action=='save':
            data=json.loads(args.value)
            if not isinstance(data,dict):raise ValueError('Ожидается объект настроек')
            old=load()
            ratio=data.get('heightRatio',old['heightRatio'])
            if not isinstance(ratio,(int,float)):raise ValueError('heightRatio')
            result=dict(old,heightRatio=max(.3,min(.75,ratio)),dnd=data.get('dnd',old['dnd']) is True);atomic(path(),result)
        elif args.action=='brightness':result=brightness()
        elif args.action=='audio-state':result=audio_state(args.value)
        elif args.action.startswith('keyboard-'):result=keyboard_state(args.value or '',args.action=='keyboard-toggle')
        elif args.action=='bluetooth-state':result=bluetooth_state()
        else:
            value=max(0,min(100,int(args.value)))
            result=parse_brightness(subprocess.run(['brightnessctl','-m','-c','backlight','set',str(value)+'%'],check=True,capture_output=True,text=True,timeout=3))
        print(json.dumps(result,ensure_ascii=False));return 0
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        message=getattr(error,'stderr',None) or str(error)
        if isinstance(message,bytes):message=message.decode(errors='replace')
        print(json.dumps({'available':False,'error':message},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
