#!/usr/bin/env python3
"""Explicit, checked SwayNC <-> PixelRail notification ownership transactions."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
import panel

NAME='org.freedesktop.Notifications'
class NotificationError(RuntimeError):pass

def path():return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'pixelrail/notifications.json'
def mode():
    try:data=json.loads(path().read_text())
    except FileNotFoundError:return 'swaync'
    if not isinstance(data,dict):raise NotificationError('Неверный notifications.json')
    value=data.get('mode','swaync')
    if value not in ('swaync','pixelrail'):raise NotificationError('Неверный notifications.json')
    return value
@contextmanager
def locked():
    identity=str(Path.home())+'\0'+os.environ.get('DBUS_SESSION_BUS_ADDRESS','session')
    directory=Path(os.environ.get('XDG_RUNTIME_DIR',str(Path.home()/'.cache')));directory.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(directory/('pixelrail-notifications-'+hashlib.sha256(identity.encode()).hexdigest()[:20]+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'w') as stream:fcntl.flock(stream,fcntl.LOCK_EX);yield

def bus(*args,missing=False):
    result=subprocess.run(['busctl','--user','call',*args],capture_output=True,text=True,timeout=3,env=dict(os.environ,LC_ALL='C'))
    if result.returncode:
        # busctl exposes the daemon's error text, not its D-Bus error name.
        # Match only name-lookup errors in a fixed locale, never bus/ACL failures.
        lookup=args[:4]==('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner') or args[:4]==('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID')
        message=result.stderr.strip().removeprefix('Call failed: ')
        name=re.escape(args[-1]) if args else ''
        absent=message in ('The name does not have an owner','The name does not have an owner.') or bool(re.fullmatch(r'(?:Could not get (?:owner|PID) of name [\"\']'+name+r'[\"\']: no such name|Name [\"\']'+name+r'[\"\'] does not exist)',message))
        if missing and lookup and absent:return []
        raise NotificationError('D-Bus: '+result.stderr.strip())
    return shlex.split(result.stdout)
def owner():
    reply=bus('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner','s',NAME,missing=True)
    if not reply:return None
    unique=reply[1]
    pid_reply=bus('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID','s',unique,missing=True)
    if not pid_reply:return None  # Owner exited between the two D-Bus queries.
    pid=int(pid_reply[1])
    confirmed=bus('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner','s',NAME,missing=True)
    if not confirmed or confirmed[1]!=unique:return None  # Name changed while its old connection remained alive.
    return {'name':unique,'pid':pid}
def swaync(value):
    if not value:return False
    process=panel.process(value['pid'])
    return bool(process and any(Path(arg).name=='swaync' for arg in process['command'][:2]))
def ipc(row,method,*args):
    binary=__import__('shutil').which('qs') or __import__('shutil').which('quickshell')
    if not row or not binary:raise NotificationError('PixelRail IPC недоступен; восстановление: pixelrail-notifications mode swaync')
    result=subprocess.run([binary,'ipc','--pid',str(row['pid']),'call','notifications',method,*args],capture_output=True,text=True,timeout=3)
    if result.returncode:raise NotificationError('Notification IPC недоступен: '+result.stderr.strip())
    return result.stdout.strip()
def state(row):
    try:
        value=json.loads(ipc(row,'state'));return value if isinstance(value,dict) and isinstance(value.get('enabled'),bool) else None
    except (ValueError,NotificationError):return None

def wait(predicate,message,timeout=4):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.04)
    raise NotificationError(message)
def start_swaync():
    current=owner()
    if current:
        if swaync(current):return
        raise NotificationError('Notifications уже принадлежат другому серверу; он сохранён')
    directory=panel.runtime_root();directory.mkdir(parents=True,exist_ok=True)
    with (directory/'swaync.log').open('ab') as log:
        child=subprocess.Popen(['swaync'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        wait(lambda: bool((value:=owner()) and value['pid']==child.pid and swaync(value)),'SwayNC не получила D-Bus name; проверьте swaync.log')
    except BaseException:
        if child.poll() is None:child.terminate();child.wait(timeout=3)
        raise

def switch(target,save=False):
    rows=panel.shells();row=panel.current_shell(rows);previous=owner()
    if target=='pixelrail':
        if not row or state(row) is None:raise NotificationError('Нет notification IPC v2.2; выполните pixelrail-shell / deploy, либо вернитесь к swaync')
        if previous and previous['pid']!=row['pid'] and not swaync(previous):
            raise NotificationError('D-Bus Notifications занят сторонним процессом; переключение отменено')
        binary=__import__('shutil').which('qs') or __import__('shutil').which('quickshell')
        version=subprocess.check_output([binary,'--version'],text=True,timeout=3)
        if not version.startswith('Quickshell 0.3.2 '):raise NotificationError('Qt lease поддерживает Quickshell 0.3.2; SwayNC сохранена')
        plugin=Path(row['config_path']).parent/'native/PixelRail/DBusLease/libpixelraillease.so'
        if not plugin.is_file():raise NotificationError('Сначала scripts/build-native.sh и deploy; SwayNC сохранена')
        ipc(row,'preflight')
        def checked():
            value=state(row) or {}
            if value.get('error'):raise NotificationError(value['error'])
            return value.get('bridgeReady')
        wait(checked,'Qt bridge не прошёл preflight; SwayNC сохранена')
        old_process=panel.process(previous['pid']) if swaync(previous) else None
        try:
            if old_process:
                # Revalidate exact identity, UID, HOME and display before terminating only
                # the current notification service; never systemctl disable/stop.
                if owner()!=previous or panel.process(previous['pid'])!=old_process:raise NotificationError('SwayNC изменилась; повторите команду')
                os.kill(previous['pid'],signal.SIGTERM)
                wait(lambda:owner() is None,'SwayNC не освободила D-Bus name; чужие процессы не остановлены')
            ipc(row,'enable')
            def ready():
                value=state(row) or {}
                if value.get('error'):raise NotificationError(value['error'])
                current=owner()
                return value.get('enabled') and current and current['pid']==row['pid']
            wait(ready,'PixelRail не получила notification D-Bus name')
            if save:panel.atomic(path(),{'mode':target})
        except BaseException:
            try:ipc(row,'disable')
            except NotificationError:pass
            if old_process:
                # Do not start fallback until our lease is actually released.
                wait(lambda:(current:=owner()) is None or current['pid']!=row['pid'],
                     'PixelRail не освободила D-Bus name; SwayNC не запущена поверх неё')
                if owner() is None:start_swaync()
            raise
    else:
        ours=previous and any(value['pid']==previous['pid'] for value in rows)
        if ours:
            owning=next(value for value in rows if value['pid']==previous['pid'])
            if ipc(owning,'disable')!='true':raise NotificationError('PixelRail не освободила notification lease; SwayNC не запускается поверх неё')
            wait(lambda:(current:=owner()) is None or swaync(current),'Notification lease остался занят')
        current=owner()
        if current and not swaync(current):raise NotificationError('Уведомления принадлежат стороннему серверу; он сохранён')
        try:
            start_swaync()
            if save:panel.atomic(path(),{'mode':target})
        except BaseException:
            if ours:
                try:ipc(owning,'enable')
                except NotificationError:pass
            raise

def recover_swaync():
    try:
        with locked():
            if owner() is None:start_swaync()
    except (OSError,ValueError,NotificationError,panel.PanelError,subprocess.SubprocessError) as error:
        print('SwayNC recovery: '+str(error),file=sys.stderr)

def reconcile():
    try:
        with locked():
            target=mode();row=panel.current_shell(panel.shells())
            if target=='pixelrail' and (not row or state(row) is None):target='swaync'
            switch(target)
    except (OSError,ValueError,NotificationError,panel.PanelError,subprocess.SubprocessError) as error:
        recover_swaync()
        print('PixelRail notifications: '+str(error)+'; восстановление: pixelrail-notifications mode swaync',file=sys.stderr)

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    modes=commands.add_parser('mode');modes.add_argument('value',choices=('swaync','pixelrail'))
    for name in ('status','start','open','dnd'):commands.add_parser(name)
    args=parser.parse_args()
    try:
        if args.command=='mode' and args.value=='pixelrail' and not panel.current_shell(panel.shells()):
            subprocess.run([str(panel.ROOT/'scripts/pixelrail-shell')],check=True,timeout=15)
        with locked():
            if args.command=='status':
                row=panel.current_shell(panel.shells());print(json.dumps({'mode':mode(),'owner':owner(),'native':state(row)},ensure_ascii=False));return 0
            if args.command in ('mode','start'):switch(args.value if args.command=='mode' else mode(),save=args.command=='mode')
            else:
                row=panel.current_shell(panel.shells());current=owner()
                if row and (args.command=='open' or (current and current['pid']==row['pid'])):ipc(row,'open' if args.command=='open' else 'dnd')
                else:subprocess.run(['swaync-client','-t' if args.command=='open' else '-d','-sw'],check=True,timeout=3)
        return 0
    except (OSError,ValueError,NotificationError,panel.PanelError,subprocess.SubprocessError) as error:
        if args.command=='start' or (args.command=='mode' and args.value=='pixelrail'):recover_swaync()
        print('PixelRail notifications: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
