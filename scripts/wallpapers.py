#!/usr/bin/env python3
"""Wallpaper discovery, bounded thumbnails and one swaybg per PixelRail display."""
import ctypes as C
from functools import lru_cache
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import signal
import sys
import tempfile
import time


def config_home(): return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))
def state_home(): return Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'pixelrail'
def choice_file(): return state_home()/'wallpaper'

def directory(kind):
    key = 'DOWNLOAD' if kind == 'Downloads' else kind.upper()
    value = os.environ.get('XDG_'+key+'_DIR')
    if not value:
        try:
            for line in (config_home()/'user-dirs.dirs').read_text().splitlines():
                if line.startswith('XDG_'+key+'_DIR='):
                    fields = shlex.split(line.split('=',1)[1], comments=True)
                    if fields: value = fields[0]
        except FileNotFoundError: pass
    return Path((value or str(Path.home()/kind)).replace('${HOME}', str(Path.home())).replace('$HOME', str(Path.home()))).expanduser()

def settings():
    path = config_home()/'pixelrail/wallpapers.json'
    try: data = json.loads(path.read_text())
    except FileNotFoundError: return {'directories':[], 'max_depth':4}
    if not isinstance(data, dict) or not isinstance(data.get('directories', []), list):
        raise ValueError('wallpapers.json: directories должен быть списком каталогов')
    depth = data.get('max_depth',4)
    if type(depth) is not int or not 0 <= depth <= 8: raise ValueError('max_depth: допустимо 0…8')
    return {'directories':data.get('directories',[]), 'max_depth':depth}

def roots():
    pictures = directory('Pictures'); downloads = directory('Downloads')
    candidates = [(pictures/'Wallpapers','wallpapers'), (Path.home()/'Pictures/Wallpapers','wallpapers'),
                  (pictures,'pictures'),(Path.home()/'Pictures','pictures'),
                  (downloads,'downloads'),(Path.home()/'Downloads','downloads')]
    for value in settings()['directories']:
        if not isinstance(value,str) or not value: raise ValueError('directories: ожидается непустой путь')
        path = Path(value.replace('$HOME', str(Path.home()))).expanduser()
        if not path.is_absolute(): raise ValueError('Дополнительный путь должен быть абсолютным или начинаться с ~/')
        if path.resolve() in (Path('/'),Path.home().resolve()):
            raise ValueError('Дополнительный каталог не может быть всей домашней директорией или /')
        candidates.append((path,'wallpapers'))
    result=[]; seen=set()
    for path,category in candidates:
        path=path.resolve()
        if path == Path('/') or path == Path.home().resolve():
            continue  # XDG permits disabled user-dirs to point at HOME; never scan it.
        if path not in seen: result.append((path,category)); seen.add(path)
    return result

class GSList(C.Structure): pass
GSList._fields_=[('data',C.c_void_p),('next',C.POINTER(GSList))]
class GError(C.Structure):
    _fields_=[('domain',C.c_uint),('code',C.c_int),('message',C.c_char_p)]

class Pixbuf:
    """Use the very same installed loader library as swaybg, not a suffix guess."""
    def __init__(self):
        self.lib=C.CDLL('libgdk_pixbuf-2.0.so.0'); self.glib=C.CDLL('libglib-2.0.so.0'); self.obj=C.CDLL('libgobject-2.0.so.0')
        self.lib.gdk_pixbuf_get_formats.restype=C.POINTER(GSList)
        self.lib.gdk_pixbuf_format_get_extensions.argtypes=[C.c_void_p]
        self.lib.gdk_pixbuf_format_get_extensions.restype=C.POINTER(C.c_char_p)
        self.lib.gdk_pixbuf_format_is_disabled.argtypes=[C.c_void_p]
        self.lib.gdk_pixbuf_format_is_disabled.restype=C.c_int
        self.glib.g_strfreev.argtypes=[C.POINTER(C.c_char_p)]
        self.glib.g_slist_free.argtypes=[C.POINTER(GSList)]
        self.glib.g_error_free.argtypes=[C.POINTER(GError)]
        self.obj.g_object_unref.argtypes=[C.c_void_p]
        self.lib.gdk_pixbuf_new_from_file_at_scale.argtypes=[C.c_char_p,C.c_int,C.c_int,C.c_int,C.POINTER(C.POINTER(GError))]
        self.lib.gdk_pixbuf_new_from_file_at_scale.restype=C.c_void_p
        self.lib.gdk_pixbuf_apply_embedded_orientation.argtypes=[C.c_void_p]
        self.lib.gdk_pixbuf_apply_embedded_orientation.restype=C.c_void_p
        self.lib.gdk_pixbuf_savev.argtypes=[C.c_void_p,C.c_char_p,C.c_char_p,C.POINTER(C.c_char_p),C.POINTER(C.c_char_p),C.POINTER(C.POINTER(GError))]
        self.lib.gdk_pixbuf_savev.restype=C.c_int
    @lru_cache(maxsize=1)
    def extensions(self):
        result=set(); head=self.lib.gdk_pixbuf_get_formats(); node=head
        try:
            while node:
                fmt=node.contents.data
                if not self.lib.gdk_pixbuf_format_is_disabled(fmt):
                    names=self.lib.gdk_pixbuf_format_get_extensions(fmt)
                    try:
                        index=0
                        while names[index]: result.add(names[index].decode().lower()); index+=1
                    finally: self.glib.g_strfreev(names)
                node=node.contents.next
        finally: self.glib.g_slist_free(head)
        return result
    def error(self, pointer):
        message=pointer.contents.message.decode('utf-8','replace') if pointer else 'Не удалось декодировать изображение'
        if pointer: self.glib.g_error_free(pointer)
        return ValueError(message)
    def thumbnail(self, source, destination):
        error=C.POINTER(GError)()
        image=self.lib.gdk_pixbuf_new_from_file_at_scale(os.fsencode(source),512,384,True,C.byref(error))
        if not image: raise self.error(error)
        oriented=None
        try:
            oriented=self.lib.gdk_pixbuf_apply_embedded_orientation(image)
            if not self.lib.gdk_pixbuf_savev(oriented or image,os.fsencode(destination),b'png',None,None,C.byref(error)):
                raise self.error(error)
        finally:
            if oriented: self.obj.g_object_unref(oriented)
            self.obj.g_object_unref(image)

@lru_cache(maxsize=1)
def pixbuf(): return Pixbuf()

def supported(path): return any(path.name.lower().endswith('.'+ext) for ext in pixbuf().extensions())

def allowed(value):
    path=Path(value).expanduser().resolve(strict=True)
    if not path.is_file() or not supported(path) or not any(path.is_relative_to(root) for root,_ in roots()):
        raise ValueError('Файл обоев недоступен или его формат не поддерживается swaybg')
    return path

def cache_file(path):
    stat=path.stat()
    digest=hashlib.sha256((str(path)+'\0'+str(stat.st_mtime_ns)+'\0'+str(stat.st_size)).encode()).hexdigest()
    return Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'pixelrail/wallpapers'/ (digest+'.png')

CACHE_ENTRIES=512
CACHE_BYTES=128*1024*1024

def prune_thumbnails(root,keep=None):
    # Only owned hash-named PNGs; never in-progress temp files or symlinks.
    rows=[]
    for file in root.glob('*.png'):
        if not re.fullmatch(r'[0-9a-f]{64}\.png',file.name) or file.is_symlink():continue
        try:rows.append((file,file.stat()))
        except FileNotFoundError:continue
    rows.sort(key=lambda row:(row[0]==keep,row[1].st_atime_ns),reverse=True)
    size=0;count=0
    for file,info in rows:
        if file==keep or (count<CACHE_ENTRIES and size+info.st_size<=CACHE_BYTES):
            size+=info.st_size;count+=1
        else:file.unlink(missing_ok=True)

def thumbnail(value):
    path=allowed(value); target=cache_file(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    with (target.parent/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not target.is_file():
            target.parent.mkdir(parents=True,exist_ok=True)
            descriptor,temporary=tempfile.mkstemp(suffix='.png',dir=target.parent)
            os.close(descriptor)
            try:
                pixbuf().thumbnail(path,Path(temporary))
                os.replace(temporary,target)
                prune_thumbnails(target.parent,keep=target)
            finally: Path(temporary).unlink(missing_ok=True)
        info=target.stat()
        os.utime(target,ns=(time.time_ns(),info.st_mtime_ns))
    return target.as_uri()

def catalog():
    cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'pixelrail/wallpapers'
    if cache.is_dir():
        with (cache/'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);prune_thumbnails(cache)
    extensions=tuple('.'+ext for ext in pixbuf().extensions())
    result=[]; seen=set(); visited=set(); depth_limit=settings()['max_depth']
    all_roots=roots()
    for folder,category in all_roots:
        if not folder.is_dir(): continue
        for current,dirs,files in os.walk(folder,followlinks=False):
            current=Path(current)
            if current in visited: dirs[:]=[]; continue
            visited.add(current)
            dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in {'node_modules','venv'} and not (current/d).is_symlink())
            if len(current.relative_to(folder).parts) >= depth_limit: dirs[:]=[]
            for filename in files:
                if filename.startswith('.') or not filename.lower().endswith(extensions): continue
                try:
                    path=(current/filename).resolve(strict=True)
                    if path in seen or not path.is_file() or not any(path.is_relative_to(root) for root,_ in all_roots): continue
                    stat=path.stat(); seen.add(path)
                    parts={part.casefold() for part in (current/filename).parts}
                    screenshot=bool(parts & {'screenshots','screenshot','скриншоты','снимки экрана'}) or filename.casefold().startswith(('screenshot','скриншот'))
                    kind='screenshots' if screenshot else category
                    if kind=='pictures': kind='wallpapers'
                    cached=cache_file(path)
                    result.append({'id':str(path),'title':filename,'subtitle':str(path.parent),'category':kind,
                                   'thumbnail':cached.as_uri() if cached.is_file() else '', 'mtime':stat.st_mtime_ns})
                except OSError: continue
    order={'wallpapers':0,'downloads':1,'screenshots':2}
    return sorted(result,key=lambda row:(order[row['category']],-row['mtime'],row['title'].casefold()))

def selected():
    for path in (choice_file(), config_home()/'pixelrail/wallpaper'):
        try:
            value=path.read_text().removesuffix('\n')
            if value and Path(value).expanduser().is_file(): return str(Path(value).expanduser().resolve())
        except FileNotFoundError: pass
    return None

def process(pid):
    try:
        folder=Path('/proc')/str(pid)
        if folder.stat().st_uid != os.getuid(): return None
        stat=(folder/'stat').read_text().rsplit(')',1)[1].split()
        if stat[0]=='Z': return None
        return {'pid':pid,'start':stat[19], 'argv':os.fsdecode((folder/'cmdline').read_bytes()).rstrip('\0').split('\0')}
    except (OSError,IndexError): return None

def same_session(pid):
    try:
        env=dict(pair.split(b'=',1) for pair in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0') if b'=' in pair)
        display=os.fsdecode(env.get(b'WAYLAND_DISPLAY',b''))
        runtime=Path(os.fsdecode(env.get(b'XDG_RUNTIME_DIR',b'/tmp')))
        own=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/os.environ.get('WAYLAND_DISPLAY','')
        return (runtime/display).resolve()==own.resolve()
    except OSError: return False

def terminate(record):
    current=process(record['pid'])
    if not current or current['start']!=record['start'] or current['argv']!=record['argv']: return
    # pidfd prevents accidentally signalling a reused PID.
    try: descriptor=os.pidfd_open(current['pid'])
    except ProcessLookupError: return
    try:
        latest=process(current['pid'])
        if not latest or latest['start']!=current['start']: return
        try: signal.pidfd_send_signal(descriptor,signal.SIGTERM)
        except ProcessLookupError: return
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            if not process(current['pid']): return
            time.sleep(.03)
        raise ValueError('Предыдущий swaybg не завершился; новый процесс не запущен')
    finally: os.close(descriptor)

def write_json(path,data):
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream: json.dump(data,stream)
        os.replace(temporary,path)
    finally: Path(temporary).unlink(missing_ok=True)

def apply(value=None):
    """One-shot start/apply; no persistent Python supervisor and no global pkill."""
    requested=str(allowed(value)) if value is not None else selected()
    if value is not None: thumbnail(requested)  # Validate before stopping the current background.
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(state_home())))
    runtime.mkdir(parents=True,exist_ok=True)
    display=str((runtime/os.environ.get('WAYLAND_DISPLAY','')).resolve())
    digest=hashlib.sha256(display.encode()).hexdigest()[:20]
    record_path=runtime/('pixelrail-swaybg-'+digest+'.json')
    with (runtime/('pixelrail-swaybg-'+digest+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        old=[]
        try:
            record=json.loads(record_path.read_text()); live=process(record['pid'])
            if live and live['start']==record['start'] and live['argv']==record['argv']:
                if value is None: return  # Idempotent session startup, preserve current process.
                old.append(record)
        except (FileNotFoundError,ValueError,KeyError): pass
        previous=selected()
        expected=['-i',previous,'-m','fill'] if previous else ['-c','#101827']
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit(): continue
            live=process(int(entry.name))
            if not live or Path(live['argv'][0]).name!='swaybg' or not same_session(live['pid']): continue
            if any(row['pid']==live['pid'] for row in old): continue
            if live['argv'][1:]==expected: old.append(live)  # Adopt the exact legacy PixelRail invocation.
            else: raise ValueError('В этом сеансе уже работает сторонний swaybg; остановите его вручную перед применением')
        for record in old: terminate(record)
        def launch(image):
            argv=['swaybg','-i',image,'-m','fill'] if image else ['swaybg','-c','#101827']
            descriptor=os.open(os.devnull,os.O_RDWR)
            try:
                actions=[(os.POSIX_SPAWN_DUP2,descriptor,fd) for fd in (0,1,2)]
                pid=os.posix_spawnp('swaybg',argv,dict(os.environ),setsid=True,file_actions=actions)
            finally: os.close(descriptor)
            time.sleep(.2)
            exited,_=os.waitpid(pid,os.WNOHANG)
            if exited: raise ValueError('swaybg не смог применить изображение; прежний выбор сохранён')
            live=process(pid)
            if not live: raise ValueError('Процесс swaybg завершился')
            try: write_json(record_path,live)
            except OSError:
                terminate(live)
                raise
            return live
        new=None
        try:
            new=launch(requested)
            if value is not None:
                state_home().mkdir(parents=True,exist_ok=True)
                descriptor,temporary=tempfile.mkstemp(dir=state_home())
                try:
                    with os.fdopen(descriptor,'w') as stream: stream.write(requested+'\n')
                    os.replace(temporary,choice_file())
                finally: Path(temporary).unlink(missing_ok=True)
        except (OSError,ValueError):
            if new: terminate(new)
            if old: launch(previous)
            raise

if __name__=='__main__':
    try: apply(sys.argv[2] if len(sys.argv)>2 and sys.argv[1]=='apply' else None)
    except (OSError,ValueError) as error:
        print('PixelRail wallpaper: '+str(error),file=sys.stderr); sys.exit(1)
