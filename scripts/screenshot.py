#!/usr/bin/env python3
"""Existing grim/slurp/wl-copy capture, supervised by the single Quickshell process."""
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import select
import signal
import subprocess
import sys
import tempfile
import time

class Cancelled(Exception):pass
child=None

def cancelled(signum,frame):
    if child is not None and child.poll() is None:
        try:os.killpg(child.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    raise Cancelled()

def supervised(command,*,stdin=None):
    global child
    parent=os.getpid()
    def guard():
        # If the capture worker itself is killed, its GUI selector must not linger.
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.prctl(1,signal.SIGTERM,0,0,0)!=0 or os.getppid()!=parent:os._exit(125)
    with tempfile.TemporaryFile(dir=os.environ.get("XDG_RUNTIME_DIR")) as errors:
        child=subprocess.Popen(command,stdin=stdin,stdout=subprocess.PIPE,stderr=errors,start_new_session=True,preexec_fn=guard)
        try:
            output,_=child.communicate();code=child.returncode
        finally:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
            child=None
        errors.seek(0);message=errors.read(500).decode(errors='replace')
    return code,output,message

def worker(managed=False,handshake=False):
    for tool in ('grim','slurp','wl-copy'):
        if not shutil.which(tool):raise RuntimeError('Missing grim/slurp/wl-copy: '+tool)
    signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
    if managed:
        parent=os.getppid();libc=ctypes.CDLL(None,use_errno=True)
        if parent<=1 or libc.prctl(1,signal.SIGTERM,0,0,0)!=0 or os.getppid()!=parent:raise Cancelled()
    def event(name):
        if handshake:print(json.dumps({'event':name}),flush=True)
    if handshake:
        # Suppress dismissal only after a real worker is ready. A lost parent or
        # IPC must not leave a selector waiting with the shell's Escape disabled.
        event('ready')
        if not select.select([sys.stdin],[],[],5)[0] or sys.stdin.readline()!='capture\n':
            raise RuntimeError('Screenshot handshake: Quickshell не разрешил запуск slurp')
        event('selecting')
    # slurp reads candidate rectangles from non-terminal stdin until EOF. Do not
    # inherit the worker's still-open QML handshake pipe or selection never starts.
    code,region,message=supervised(['slurp'],stdin=subprocess.DEVNULL)
    if code or not region.strip():
        # Installed slurp prints this exact diagnostic on Escape. Other exit-1
        # failures (display, keyboard grab, allocation) must remain real errors.
        if code not in (0,1) or message.strip() not in ('','selection cancelled'):
            raise RuntimeError('slurp (exit '+str(code)+'): '+(message.strip() or 'не удалось выбрать область'))
        event('cancelled');return 0
    folder=Path(os.environ.get('XDG_PICTURES_DIR') or str(Path.home()/'Pictures'))/'Screenshots';folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for index in range(1000):
        file=folder/(stamp+('_'+str(index) if index else '')+'.png')
        try:file.touch(exist_ok=False);break
        except FileExistsError:continue
    else:raise RuntimeError('Не удалось выбрать имя снимка')
    complete=False
    try:
        code,_,message=supervised(['grim','-g',region.decode().strip(),str(file)])
        if code or not file.stat().st_size:raise RuntimeError('grim (exit '+str(code)+'): '+(message.strip() or 'захват не выполнен'))
        complete=True
        with file.open('rb') as stream:
            # wl-copy's detached clipboard owner must survive. Never wait on inherited
            # output pipes or kill its process group after successful ownership transfer.
            subprocess.run(['wl-copy','--type','image/png'],stdin=stream,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,check=True,timeout=5)
        event('saved')
        if shutil.which('notify-send'):
            try:subprocess.run(['notify-send','PixelRail','Screenshot saved: '+str(file)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
            except subprocess.SubprocessError:pass
    finally:
        if not complete:file.unlink(missing_ok=True)  # Only our newly reserved, failed output.
    return 0

def main():
    if sys.argv[1:]==['--capture-worker']:return worker(managed=True)
    if sys.argv[1:]==['--capture-worker','--handshake']:return worker(managed=True,handshake=True)
    option=sys.argv[1:]
    if option not in ([],['--status'],['--reset']):raise ValueError('Usage: pixelrail-shot [--status | --reset]')
    binary=shutil.which('qs') or shutil.which('quickshell')
    config=os.environ.get('PIXELRAIL_QML',str(Path(__file__).resolve().parent.parent/'quickshell/shell.qml'))
    def ipc(method):
        reply=subprocess.run([binary,'ipc','-p',config,'call','screenshot',method],capture_output=True,text=True,timeout=3)
        if reply.returncode:raise RuntimeError('Screenshot IPC '+method+': '+(reply.stderr.strip() or reply.stdout.strip() or str(reply.returncode)))
        return reply.stdout.strip()
    def state():
        value=json.loads(ipc('state'))
        if not isinstance(value,dict) or not isinstance(value.get('active'),bool):raise ValueError('Некорректный screenshot.state')
        return value
    if option:
        if not binary:raise RuntimeError('Quickshell IPC недоступен; screenshot mode не изменён')
        if option==['--reset']:ipc('reset')
        print(json.dumps(state(),ensure_ascii=False));return 0
    if binary:
        try:
            state()  # Read-only preflight: fallback is safe before any capture request.
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
            print('PixelRail screenshot: '+str(error)+'; пробую самостоятельный захват',file=sys.stderr)
        else:
            reply=None
            try:
                reply=ipc('capture')
                if reply not in ('true','false'):raise RuntimeError('Screenshot IPC capture: некорректный ответ '+reply)
                if reply=='false':
                    # Do not abort someone else's already running selection.
                    value=state()
                    print('PixelRail screenshot: захват уже выполняется: '+json.dumps(value,ensure_ascii=False)+'; сброс: pixelrail-shot --reset',file=sys.stderr)
                    return 1
                # Acceptance is not successful startup. Never silently eat a
                # hotkey when QProcess cannot execute its helper.
                deadline=time.monotonic()+6
                while time.monotonic()<deadline:
                    value=state()
                    if value.get('error'):raise RuntimeError(value['error'])
                    if value.get('phase')=='capturing' or value.get('outcome') in ('saved','cancelled'):return 0
                    if value.get('phase')=='idle':raise RuntimeError('Screenshot worker завершился до запуска slurp')
                    time.sleep(.02)
                raise RuntimeError('Screenshot worker: истёк срок подтверждения запуска')
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
                # Delivery may be ambiguous: release a possibly accepted request.
                # Never launch a second, standalone selector after this point.
                if reply!='false':
                    try:ipc('reset')
                    except (OSError,RuntimeError,subprocess.SubprocessError):pass
                raise
    # Shell absent/old: retain the standalone backend; do not start a second qs.
    return worker()

if __name__=='__main__':
    try:sys.exit(main())
    except Cancelled:sys.exit(0)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('PixelRail screenshot: '+str(error),file=sys.stderr);sys.exit(1)
