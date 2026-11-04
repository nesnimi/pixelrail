#!/usr/bin/env python3
"""Transactional PixelRail panel selection. No daemon; no process-name kills."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent

class PanelError(RuntimeError): pass

def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'pixelrail/panel.json'

def settings():
    try: data=json.loads(config_path().read_text())
    except FileNotFoundError: return {'mode':'waybar','monitor':''}
    if not isinstance(data,dict) or data.get('mode') not in ('waybar','sidebar') or not isinstance(data.get('monitor',''),str):
        raise PanelError('Некорректный panel.json: нужны mode sidebar/waybar и необязательный monitor')
    return {'mode':data['mode'],'monitor':data.get('monitor','')}

def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(value,stream,ensure_ascii=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally: Path(temporary).unlink(missing_ok=True)

def endpoint(environment):
    display=environment.get('WAYLAND_DISPLAY','')
    return str((Path(environment.get('XDG_RUNTIME_DIR','/tmp'))/display).resolve()) if display else ''

def runtime_root():
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(Path.home()/'.cache')))
    identity=str(Path.home().resolve())+'\0'+endpoint(os.environ)
    return runtime/('pixelrail-panel-'+hashlib.sha256(identity.encode()).hexdigest()[:20])

@contextmanager
def locked():
    directory=runtime_root();directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    descriptor=os.open(directory/'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(descriptor,'w') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX);yield

def process(pid):
    """PID reuse protection, exact command, UID, HOME and display scope."""
    try:
        directory=Path('/proc')/str(pid)
        if directory.stat().st_uid!=os.getuid(): return None
        fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
        if fields[0]=='Z': return None
        command=[value.decode() for value in (directory/'cmdline').read_bytes().split(b'\0') if value]
        environment=dict(value.decode().split('=',1) for value in (directory/'environ').read_bytes().split(b'\0') if b'=' in value)
        if Path(environment.get('HOME','/')).resolve()!=Path.home().resolve() or endpoint(environment)!=endpoint(os.environ): return None
        return {'pid':int(pid),'start':fields[19],'command':command}
    except (OSError,ValueError,UnicodeError): return None

def owned_bar():
    try: record=json.loads((runtime_root()/'waybar.json').read_text())
    except (OSError,ValueError): return None
    return record if process(record.get('pid',0))==record else None

def bars():
    found=[]
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit(): continue
        # Cheap name check first; allow interpreter-based test fixtures as well.
        try:
            command=(directory/'cmdline').read_bytes().split(b'\0')
            if not any(Path(os.fsdecode(value)).name=='waybar' for value in command[:2] if value): continue
        except OSError: continue
        value=process(directory.name)
        if value: found.append(value)
    return found

def stop_bar(record):
    if not record or process(record['pid'])!=record: return
    os.kill(record['pid'],signal.SIGTERM)
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        if process(record['pid'])!=record: return
        time.sleep(.04)
    raise PanelError('Waybar PixelRail не завершилась; переключение отменено, принудительный kill не выполнялся')

def start_bar():
    if bars(): return  # A foreign bar is preserved and reused in waybar mode.
    binary=shutil.which('waybar')
    if not binary: raise PanelError('Waybar не найдена. Вернитесь к Sidebar: pixelrail-panel mode sidebar')
    config=Path.home()/'.config/waybar/config.jsonc';style=Path.home()/'.config/waybar/style.css'
    if not config.is_file() or not style.is_file():
        raise PanelError('Не найдены конфигурация/стиль Waybar; восстановите их из резервной копии')
    log=runtime_root()/'waybar.log'
    with log.open('ab') as stream:
        child=subprocess.Popen([binary,'-c',str(config),'-s',str(style)],stdin=subprocess.DEVNULL,
                               stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    # Bounded readiness check, never idle polling. Waybar has no readiness IPC.
    time.sleep(.2)
    record=process(child.pid)
    if child.poll() is not None or not record:
        if child.poll() is None: child.terminate();child.wait(timeout=3)
        raise PanelError('Waybar не запустилась; журнал: '+str(log))
    atomic(runtime_root()/'waybar.json',record)

def shells():
    from lifecycle import Shell, owned_configs, LifecycleError
    if not (shutil.which("qs") or shutil.which("quickshell")): return []
    if not os.environ.get("WAYLAND_DISPLAY"): return []
    try: return Shell(owned_configs(Path.home(),ROOT)).instances()
    except LifecycleError as error: raise PanelError(str(error)) from error

def call(row,method,*args):
    binary=shutil.which('qs') or shutil.which('quickshell')
    if not binary: raise PanelError('Quickshell недоступен')
    try:
        return subprocess.check_output([binary,'ipc','--pid',str(row['pid']),'call','panel',method,*args],
                                       text=True,stderr=subprocess.PIPE,timeout=3).strip()
    except (OSError,subprocess.SubprocessError) as error:
        raise PanelError('Sidebar IPC недоступен; восстановление: pixelrail-panel mode waybar') from error

def snapshot(row):
    if not row: return None
    try:
        value=json.loads(call(row,'state'))
        return value if isinstance(value,dict) and isinstance(value.get('enabled'),bool) and isinstance(value.get('prepared'),bool) else None
    except (PanelError,ValueError): return None

def current_shell(rows):
    installed=Path.home()/'.local/bin/pixelrail-shell'
    preferred=str((installed.resolve().parent.parent/'quickshell/shell.qml').resolve()) if installed.is_symlink() else str(ROOT/'quickshell/shell.qml')
    return next((row for row in rows if row['config_path']==preferred),rows[0] if len(rows)==1 else None)

def switch(mode,save=False,toggle=False):
    try: config=settings()
    except (OSError,ValueError,PanelError):
        if mode!='waybar' or not save: raise
        config={'mode':'waybar','monitor':''}
    rows=shells();row=current_shell(rows)
    old_visible=[value for value in rows if (snapshot(value) or {}).get('enabled')]
    owned=owned_bar();running=bars()
    if toggle:
        if mode=='sidebar':
            if row and (snapshot(row) or {}).get('enabled'): call(row,'hide');return
        elif owned:
            stop_bar(owned)
            for value in rows:
                if snapshot(value):call(value,'inset','0')
            return
    if mode=='sidebar':
        foreign=[value for value in running if value!=owned]
        if foreign:
            raise PanelError('Обнаружена незарегистрированная Waybar: PID '+', '.join(str(value['pid']) for value in foreign)
                + '. Она не остановлена. Закройте её вручную и повторите pixelrail-panel mode sidebar')
        if not row: raise PanelError('PixelRail не запущен. Выполните pixelrail-shell; восстановление: pixelrail-panel mode waybar')
        call(row,'prepare',config['monitor'])
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            state=snapshot(row) or {}
            if state.get('error'): raise PanelError(state['error'])
            if state.get('prepared'): break
            time.sleep(.04)
        else: raise PanelError('Sidebar не подтвердила загрузку; Waybar сохранена')
        if not state.get('screen'): raise PanelError('Sidebar: нет подключённого монитора; Waybar сохранена')
        try:
            stop_bar(owned)
            if bars(): raise PanelError('Во время переключения появилась другая Waybar; Sidebar не показана')
            if call(row,'activate')!='true' or not (snapshot(row) or {}).get('visible'):
                raise PanelError('Sidebar не подтвердила показ')
            if save: atomic(config_path(),dict(config,mode=mode))
        except BaseException:
            try: call(row,'hide')
            except PanelError: pass
            if running or config["mode"]=="waybar":
                start_bar()
                for value in rows:
                    if snapshot(value):call(value,'inset','66')
            raise
    else:
        for value in rows:
            state=snapshot(value)
            if state:
                call(value,'hide')
                if (snapshot(value) or {}).get('enabled'): raise PanelError('Sidebar не скрылась; Waybar не запущена')
            else:
                # Legacy releases have no Sidebar. A known v2.1 instance with failed
                # panel IPC must not be overlaid by Waybar.
                controller=Path(value['config_path']).parent/'components/PanelController.qml'
                if controller.exists(): raise PanelError('Sidebar IPC не отвечает; Waybar не запущена во избежание наложения')
        try:
            start_bar()
            for value in rows:
                if snapshot(value):call(value,'inset','66')
            if save: atomic(config_path(),dict(config,mode=mode))
        except BaseException:
            replacement=owned_bar()
            if replacement and replacement!=owned: stop_bar(replacement)
            for value in old_visible:
                try: call(value,'prepare',config['monitor']);call(value,'activate')
                except PanelError: pass
            raise

def reconcile():
    """After lifecycle handoff only. Never starts qs or changes saved selection."""
    try:
        with locked():
            desired=settings()['mode']
            if desired=='sidebar' and not snapshot(current_shell(shells())):
                # Rollback to pre-sidebar release: recover the old Waybar interface.
                switch('waybar')
                return
            switch(desired)
    except (OSError,ValueError,PanelError) as error:
        print('PixelRail panel: '+str(error)+'; восстановление: pixelrail-panel mode waybar',file=sys.stderr)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    mode=commands.add_parser('mode');mode.add_argument('value',choices=('sidebar','waybar'))
    commands.add_parser('status');commands.add_parser('start');commands.add_parser('toggle')
    args=parser.parse_args()
    try:
        if args.command=='mode' and args.value=='sidebar' and not current_shell(shells()):
            result=subprocess.run([str(ROOT/'scripts/pixelrail-shell')],timeout=15)
            if result.returncode: raise PanelError('Не удалось запустить PixelRail; используйте pixelrail-panel mode waybar')
        with locked():
            if args.command=='status':
                sidebars=[dict(pid=row['pid'],state=snapshot(row)) for row in shells()]
                running=bars();visible=any((row['state'] or {}).get('visible') for row in sidebars)
                print(json.dumps({'settings':settings(),'effectiveMode':'sidebar' if visible else 'waybar' if running else 'hidden',
                    'conflict':bool(visible and running),'sidebars':sidebars,'waybar':running,'ownedWaybar':owned_bar()},ensure_ascii=False));return 0
            switch(args.value if args.command=='mode' else settings()['mode'],save=args.command=='mode',toggle=args.command=='toggle')
        print('PixelRail panel: '+settings()['mode']);return 0
    except (OSError,ValueError,PanelError,subprocess.SubprocessError) as error:
        print('PixelRail: '+str(error),file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
