#!/usr/bin/env python3
"""On-demand clipboard data/preview helpers; wl-copy keeps native Wayland ownership."""
from contextlib import contextmanager
import codecs
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid
import ctypes as C
import wallpapers

CACHE_BYTES = 64 * 1024 * 1024
CACHE_ENTRIES = 256

@contextmanager
def timing(stages, name):
    start=time.perf_counter()
    try: yield
    finally: stages[name]=round((time.perf_counter()-start)*1000,3)

def trace(stages):
    if os.environ.get('PIXELRAIL_CLIPBOARD_TRACE') == '1':
        print('PixelRail clipboard timing '+json.dumps(stages),file=sys.stderr)

def cache_root():
    root=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'pixelrail/clipboard'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    return root

def database_revision():
    # Namespace previews by DB path and revision: wiping/reusing an ID cannot show old pixels.
    database=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'cliphist/db'
    config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'cliphist/config'
    try:
        # cliphist's native config syntax is 'db-path /absolute/path', not YAML.
        for line in config.read_text().splitlines():
            fields=line.strip().split(maxsplit=1)
            if len(fields)==2 and fields[0]=='db-path': database=Path(fields[1])
    except FileNotFoundError: pass
    try:
        stat=database.stat(); identity=f'{database.resolve()}:{stat.st_ino}:{stat.st_mtime_ns}:{stat.st_size}'
    except FileNotFoundError: identity=str(database.resolve())+':session:'+uuid.uuid4().hex
    return hashlib.sha256(identity.encode()).hexdigest()[:24]

def listing():
    stages={}
    with timing(stages,'list_ms'):
        result=subprocess.run(['cliphist','list'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
    if result.returncode:
        # cliphist returns 1 for an empty, not-yet-created database.
        if b'no such file' in result.stderr.lower() or b'empty' in result.stderr.lower() or b'please store something first' in result.stderr.lower(): return [],stages
        result.check_returncode()
    with timing(stages,'parse_ms'):
        revision=database_revision(); rows=[]
        formats=wallpapers.pixbuf().extensions() if b'[[ binary data ' in result.stdout else set()
        # Go cliphist may emit raw WebP/other unsupported Go-image previews. Split
        # only on LF, not Python splitlines()'s additional binary control characters.
        for line in result.stdout.split(b'\n'):
            raw_key,separator,raw=line.partition(b'\t')
            key=raw_key.decode('ascii','replace')
            if not separator or not key.isdecimal(): continue
            preview=raw.decode('utf-8','replace')
            technical=preview.startswith('[[ binary data ')
            binary=technical or b'\0' in raw
            extension=next((token.lower() for token in preview.split() if token.lower() in formats),'') if technical else ''
            if raw[:4]==b'RIFF' and b'WEBP' in raw[8:16]: extension='webp'
            for magic,name in ((b'GIF87a','gif'),(b'GIF89a','gif'),(b'BM','bmp'),(b'II*\0','tiff'),(b'MM\0*','tiff'),(b'\0\0\1\0','ico')):
                if raw.startswith(magic): extension=name
            if b'ftyp' in raw[:12]:
                if any(tag in raw[8:32] for tag in (b'avif',b'avis')): extension='avif'
                elif any(tag in raw[8:32] for tag in (b'heic',b'heix',b'mif1')): extension='heif'
            if raw.lstrip().startswith(b'<svg') or (raw.lstrip().startswith(b'<?xml') and b'<svg' in raw): extension='svg'
            binary=binary or bool(extension)
            dimensions=re.search(r'\b(\d+)x(\d+)\b',preview) if binary else None
            size_match=re.search(r'binary data (.+?) '+re.escape(extension)+r'\b',preview) if extension else None
            size=size_match.group(1) if size_match else ''
            width=int(dimensions[1]) if dimensions else 0; height=int(dimensions[2]) if dimensions else 0
            kind='image' if extension else 'binary' if binary else 'text'
            rows.append(dict(id=key,kind=kind,revision=revision,format=extension.upper(),width=width,height=height,
                             title=('Изображение · '+extension.upper()) if extension else 'Данные буфера' if binary else preview[:500],
                             subtitle=(' · '.join(filter(None,[f'{width}×{height}' if width else '',extension.upper(),size]))) if extension else 'Enter — скопировать',
                             search=preview if not binary else extension))
    trace(stages)
    return rows,stages

def validate_id(value):
    value=str(value)
    if not re.fullmatch(r'\d+',value): raise ValueError('Неверная запись буфера')
    return value

def decode(key, destination, stages):
    with timing(stages,'decode_ms'):
        result=subprocess.run(['cliphist','decode'],input=validate_id(key).encode(),stdout=destination,stderr=subprocess.PIPE,timeout=8)
        if result.returncode: raise ValueError('Запись уже удалена или недоступна; откройте историю заново')
    destination.flush(); destination.seek(0)

def image_info(path):
    pix=wallpapers.pixbuf(); lib=pix.lib
    lib.gdk_pixbuf_get_file_info.argtypes=[C.c_char_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]
    lib.gdk_pixbuf_get_file_info.restype=C.c_void_p
    lib.gdk_pixbuf_format_get_mime_types.argtypes=[C.c_void_p]
    lib.gdk_pixbuf_format_get_mime_types.restype=C.POINTER(C.c_char_p)
    width=C.c_int(); height=C.c_int()
    format=lib.gdk_pixbuf_get_file_info(os.fsencode(path),C.byref(width),C.byref(height))
    if not format: raise ValueError('Превью недоступно; оригинал можно скопировать')
    names=lib.gdk_pixbuf_format_get_mime_types(format)
    try: mime=names[0].decode() if names and names[0] else 'application/octet-stream'
    finally: pix.glib.g_strfreev(names)
    return dict(width=width.value,height=height.value,mime=mime,format=mime.removeprefix('image/').upper())

def mime_type(payload, hint):
    prefix=payload.read(4096); payload.seek(0)
    for magic,mime in ((b'\x89PNG\r\n\x1a\n','image/png'),(b'\xff\xd8\xff','image/jpeg'),
                       (b'GIF87a','image/gif'),(b'GIF89a','image/gif'),(b'BM','image/bmp'),
                       (b'II*\0','image/tiff'),(b'MM\0*','image/tiff')):
        if prefix.startswith(magic): return mime
    if prefix[:4]==b'RIFF' and prefix[8:12]==b'WEBP': return 'image/webp'
    if hint=='image':
        # /proc/self/fd supplies a filename for GdkPixbuf without persisting the original.
        try: return image_info('/proc/self/fd/'+str(payload.fileno()))['mime']
        except ValueError: pass
    if hint=='binary': return None
    if b'\0' not in prefix:
        try:
            codecs.getincrementaldecoder('utf-8')().decode(prefix,final=False)
            return 'text/plain;charset=utf-8'
        except UnicodeDecodeError: pass
    return None  # Preserve wl-copy's type inference for other binary formats.

def restore(request):
    stages={}; key=validate_id(request.get('id',''))
    with tempfile.TemporaryFile(dir=cache_root(),buffering=0) as payload:
        decode(key,payload,stages)
        with timing(stages,'mime_ms'): mime=mime_type(payload,request.get('kind',''))
        arguments=['wl-copy']+(['--type',mime] if mime else [])
        # wl-copy forks a long-lived owner. NEVER capture its inherited stdout/stderr
        # with PIPE: communicate() would wait for the owner's EOF, not parent readiness.
        with timing(stages,'wl_copy_ms'), tempfile.TemporaryFile(dir=cache_root()) as errors:
            subprocess.run(arguments,stdin=payload,stdout=subprocess.DEVNULL,stderr=errors,timeout=8,check=True)
    trace(stages)
    return stages

def prune(root):
    # Recover interrupted preview jobs without retaining originals or orphan PNGs.
    for path in root.glob('*.source'): path.unlink(missing_ok=True)
    for path in root.glob('*.png'):
        if not path.with_suffix('.json').exists(): path.unlink(missing_ok=True)
    pairs=sorted(root.glob('*.json'),key=lambda path:path.stat().st_mtime_ns,reverse=True)
    size=0
    for index,metadata in enumerate(pairs):
        image=metadata.with_suffix('.png')
        try: amount=image.stat().st_size+metadata.stat().st_size
        except FileNotFoundError: metadata.unlink(missing_ok=True); continue
        size+=amount
        if index>=CACHE_ENTRIES or size>CACHE_BYTES:
            image.unlink(missing_ok=True); metadata.unlink(missing_ok=True)

def thumbnail(request):
    key=validate_id(request.get('id','')); stages={}; root=cache_root()
    revision=str(request.get('revision') or database_revision())
    digest=hashlib.sha256((revision+':'+key).encode()).hexdigest()
    image=root/(digest+'.png'); metadata=root/(digest+'.json')
    with (root/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:
            prune(root)
            if image.is_file() and metadata.is_file():
                result=json.loads(metadata.read_text()); os.utime(metadata,None); prune(root)
                return dict(result,url=image.as_uri())
            with tempfile.TemporaryFile(dir=root,buffering=0) as original:
                decode(key,original,stages)
                source=Path('/proc/self/fd')/str(original.fileno())
                with timing(stages,'thumbnail_ms'):
                    result=image_info(source)
                    descriptor,temporary=tempfile.mkstemp(dir=root,suffix='.png'); os.close(descriptor)
                    try:
                        wallpapers.pixbuf().thumbnail(source,Path(temporary))
                        os.replace(temporary,image)
                    finally: Path(temporary).unlink(missing_ok=True)
            metadata.write_text(json.dumps(result)); metadata.chmod(0o600); prune(root)
            trace(stages)
            return dict(result,url=image.as_uri())
        except (OSError,ValueError):
            image.unlink(missing_ok=True); metadata.unlink(missing_ok=True)
            raise

def ensure_watcher():
    """Upgrade the existing text-only watcher; one native watcher, no Python daemon."""
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(cache_root())))
    runtime.mkdir(parents=True,exist_ok=True)
    display=str((runtime/os.environ.get('WAYLAND_DISPLAY','')).resolve())
    lockfile=runtime/('pixelrail-cliphist-'+hashlib.sha256(display.encode()).hexdigest()[:20]+'.lock')
    with lockfile.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=[]; old=[]
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit(): continue
            record=wallpapers.process(int(entry.name))
            if not record or Path(record['argv'][0]).name!='wl-paste' or not wallpapers.same_session(record['pid']): continue
            arguments=record['argv'][1:]
            if '--watch' not in arguments: continue
            index=arguments.index('--watch'); sink=arguments[index+1:]
            if len(sink)!=2 or Path(sink[0]).name!='cliphist' or sink[1]!='store': continue
            prefix=arguments[:index]
            if not prefix: current.append(record)
            elif prefix==['--type','text']: old.append(record)
            else: raise ValueError('Уже работает пользовательский cliphist watcher; новый не запущен')
        for record in old+current[1:]: wallpapers.terminate(record)
        if current: return
        descriptor=os.open(os.devnull,os.O_RDWR)
        try:
            actions=[(os.POSIX_SPAWN_DUP2,descriptor,fd) for fd in (0,1,2)]
            pid=os.posix_spawnp('wl-paste',['wl-paste','--watch','cliphist','store'],dict(os.environ),setsid=True,file_actions=actions)
        finally: os.close(descriptor)
        time.sleep(.05)
        exited,_=os.waitpid(pid,os.WNOHANG)
        if exited: raise ValueError('Не удалось запустить cliphist watcher')
        record=wallpapers.process(pid)
        if record:wallpapers.write_json(lockfile.with_suffix('.json'),record)

def stop_owned_watcher():
    """Uninstall only a watcher we spawned and recorded; adopted/user watchers survive."""
    runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(cache_root())))
    display=str((runtime/os.environ.get('WAYLAND_DISPLAY','')).resolve())
    record_path=runtime/('pixelrail-cliphist-'+hashlib.sha256(display.encode()).hexdigest()[:20]+'.json')
    if not record_path.is_file():return
    with record_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        try:record=json.loads(record_path.read_text())
        except (OSError,ValueError):return
        current=wallpapers.process(record.get('pid',0))
        if current==record and wallpapers.same_session(record['pid']) and Path(record['argv'][0]).name=='wl-paste' and record['argv'][1:]==['--watch','cliphist','store']:
            wallpapers.terminate(record);record_path.unlink(missing_ok=True)

if __name__=='__main__':
    try:
        if sys.argv[1:]!=['watch']: raise ValueError('Ожидается команда watch')
        ensure_watcher()
    except (OSError,ValueError) as error:
        print('PixelRail clipboard: '+str(error),file=sys.stderr); sys.exit(1)
