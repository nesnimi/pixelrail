"""Native wl-copy/wl-paste/cliphist on a private surface-free Wayland server.
Optional --benchmark reproduces the old 8s PIPE timeout once. No real clipboard access.
"""
import base64
import ctypes as C
import json
import os
from pathlib import Path
import shutil
import statistics
import shlex
import struct
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import zlib

root=Path.cwd(); sys.path.insert(0,str(root/'scripts'))
import clipboard_history as history
import wallpapers

def png(path,width=32,height=24,color=b'\x60\x90\xc0'):
    def chunk(kind,data): return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress((b'\0'+color*width)*height))+chunk(b'IEND',b''))
    return path.read_bytes()

def wait(condition,message):
    for _ in range(100):
        if condition(): return
        time.sleep(.025)
    raise AssertionError(message)

for tool in ('cc','wayland-scanner','cliphist','wl-copy','wl-paste'):
    if not shutil.which(tool): raise SystemExit('Test requires installed '+tool+'; no automatic installation')
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp); runtime=base/'runtime'; runtime.mkdir(mode=0o700)
    original=dict(os.environ)
    os.environ.update(HOME=str(base),XDG_RUNTIME_DIR=str(runtime),WAYLAND_DISPLAY='pixelrail-clipboard-test',
                      XDG_CACHE_HOME=str(base/'cache'),XDG_CONFIG_HOME=str(base/'config'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),PIXELRAIL_CLIPBOARD_TRACE='0')
    os.environ.pop('CLIPHIST_DB_PATH',None)
    xml='/usr/share/wayland-protocols/staging/ext-data-control/ext-data-control-v1.xml'
    subprocess.run(['wayland-scanner','server-header',xml,str(base/'control.h')],check=True)
    subprocess.run(['wayland-scanner','private-code',xml,str(base/'control.c')],check=True)
    subprocess.run(['cc','-Wall','-Wextra','-I',str(base),str(root/'tests/fixtures/clipboard-server.c'),str(base/'control.c'),'-lwayland-server','-o',str(base/'server')],check=True)
    server=subprocess.Popen([str(base/'server')])
    def store(data): subprocess.run(['cliphist','store'],input=data,capture_output=True,check=True)
    def paste(mime=None): return subprocess.check_output(['wl-paste','--no-newline']+(['--type',mime] if mime else []),timeout=3,stderr=subprocess.DEVNULL)
    def watchers():
        result=[]
        for folder in Path('/proc').iterdir():
            if folder.name.isdecimal():
                record=wallpapers.process(int(folder.name))
                if record and Path(record['argv'][0]).name=='wl-paste' and '--watch' in record['argv'] and wallpapers.same_session(record['pid']): result.append(record)
        return result
    measurements={}
    try:
        wait(lambda:(runtime/'pixelrail-clipboard-test').exists(),'private Wayland socket')
        assert history.listing()[0]==[]
        short='Привет, Pixel 👋'.encode(); long=('Большой текст 🌌\nстрока два\tданные\n'*3000).encode()
        image=base/'photo.png'; png_bytes=png(image,1600,900)
        pix=wallpapers.pixbuf(); error=C.POINTER(wallpapers.GError)()
        obj=pix.lib.gdk_pixbuf_new_from_file_at_scale(os.fsencode(image),128,128,True,C.byref(error))
        jpg=base/'photo.jpg'
        assert pix.lib.gdk_pixbuf_savev(obj,os.fsencode(jpg),b'jpeg',None,None,C.byref(error))
        pix.obj.g_object_unref(obj); jpg_bytes=jpg.read_bytes()
        webp_bytes=base64.b64decode('UklGRh4AAABXRUJQVlA4TBEAAAAvH8AFAAdQyEIVuP+BiOh/AAA=')
        for data in (short,long,png_bytes,jpg_bytes,webp_bytes): store(data)
        rows,listing_time=history.listing(); measurements['listing']=listing_time
        assert len(rows)==5
        image_rows=[row for row in rows if row['kind']=='image']; assert len(image_rows)==3
        assert all('binary data' not in row['title'] for row in image_rows)
        text_rows=[row for row in rows if row['kind']=='text']
        assert len(text_rows)==2
        # Decoding and restoring original bytes; no history re-query during activation.
        for row in rows:
            decoded=subprocess.check_output(['cliphist','decode'],input=row['id'].encode())
            start=time.perf_counter()
            reply=subprocess.run([str(root/'scripts/pixelrail-menu-data'),'activate','clipboard'],input=json.dumps(row).encode(),capture_output=True,check=True,timeout=3,env=dict(os.environ,PIXELRAIL_CLIPBOARD_TRACE='1'))
            elapsed=(time.perf_counter()-start)*1000
            response=json.loads(reply.stdout); assert not response.get('error'),response
            assert paste()==decoded; assert paste()==decoded  # Native owner survives helper exit and repeated paste.
            measurements[row['kind']+'_'+row['id']]=dict(total_ms=round(elapsed,3),**response['timings'])
        for row in image_rows:
            preview=history.thumbnail(row)
            assert preview['width']>0 and preview['height']>0
            assert preview['mime'] in ('image/png','image/jpeg','image/webp')
            path=Path(preview['url'].removeprefix('file://'))
            width,height=struct.unpack('!2I',path.read_bytes()[16:24]); assert width<=512 and height<=384
            with patch.object(history.subprocess,'run',side_effect=AssertionError('cached preview was decoded again')):
                assert history.thumbnail(row)['url']==preview['url']
        # Missing thumbnail/original is a fast error and never overwrites the clipboard.
        store(b'ephemeral test record')
        expired=history.listing()[0][0]
        subprocess.run(['cliphist','delete'],input=expired['id'].encode(),capture_output=True,check=True)
        preserved=paste()
        for operation in (history.restore,history.thumbnail):
            try: operation(expired)
            except ValueError: pass
            else: raise AssertionError('deleted record unexpectedly restored/previewed')
        assert paste()==preserved and not list(history.cache_root().glob('*.source'))
        # Bounded cache under repeated image arrivals.
        with patch.object(history,'CACHE_ENTRIES',2),patch.object(history,'CACHE_BYTES',1024*1024):
            for number in range(4):
                data=png(base/'next.png',color=bytes([number+1,80,120]));store(data)
                row=history.listing()[0][0]; history.thumbnail(row)
            assert len(list(history.cache_root().glob('*.png')))<=2
            assert sum(p.stat().st_size for p in history.cache_root().glob('*') if p.is_file())<=1024*1024
        # Byte limit is independent of entry count, and interrupted jobs are removed.
        quota=base/'quota';quota.mkdir()
        for number in range(3):
            (quota/f'{number}.png').write_bytes(b'x'*(300*1024))
            (quota/f'{number}.json').write_text('{}')
        (quota/'orphan.png').write_bytes(b'orphan')
        (quota/'interrupted.source').write_bytes(b'private original fixture')
        with patch.object(history,'CACHE_BYTES',512*1024),patch.object(history,'CACHE_ENTRIES',256): history.prune(quota)
        assert sum(path.stat().st_size for path in quota.iterdir())<=512*1024
        assert not (quota/'orphan.png').exists() and not list(quota.glob('*.source'))
        # Before/after: old full path and all stage timings, on the real tools.
        row=next(row for row in history.listing()[0] if row['kind']=='text')
        if '--benchmark' in sys.argv:
            old={}; start=time.perf_counter()
            with history.timing(old,'list_ms'): raw=subprocess.check_output(['cliphist','list'])
            with history.timing(old,'parse_ms'): line=next(line for line in raw.splitlines() if line.split(b'\t')[0]==row['id'].encode())
            with history.timing(old,'decode_ms'): value=subprocess.check_output(['cliphist','decode'],input=line)
            subprocess.run(['wl-copy','--clear'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            copy_start=time.perf_counter()
            def observe():
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    try:
                        if paste()==value:
                            old['clipboard_available_ms']=round((time.perf_counter()-copy_start)*1000,3); return
                    except subprocess.SubprocessError: pass
                    time.sleep(.01)
            observer=threading.Thread(target=observe); observer.start()
            try:
                subprocess.run(['wl-copy'],input=value,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=8)
            except subprocess.TimeoutExpired: old['timeout']=True
            observer.join(timeout=3)
            assert 'clipboard_available_ms' in old and old['clipboard_available_ms']<1000
            old['wl_copy_ms']=round((time.perf_counter()-copy_start)*1000,3)
            old['total_ms']=round((time.perf_counter()-start)*1000,3)
            assert old.get('timeout') and paste()==value
            measurements['before']=old
        trials=[]
        for _ in range(8):
            start=time.perf_counter(); stages=history.restore(row); trials.append((time.perf_counter()-start)*1000)
            assert paste()==subprocess.check_output(['cliphist','decode'],input=row['id'].encode())
        measurements['after']={'median_ms':round(statistics.median(trials),3),'max_ms':round(max(trials),3),'stages_last':stages}
        # Real QML -> helper -> native wl-copy -> UI callback, with no mapped surface.
        qs=shutil.which('qs') or shutil.which('quickshell')
        if qs and original.get('WAYLAND_DISPLAY'):
            gui=base/'gui'; gui.mkdir()
            for folder in ('components','modules','theme','ui','assets'):
                (gui/folder).symlink_to(root/'quickshell'/folder,target_is_directory=True)
            backend=gui/'menu-data'
            backend.write_text('#!/bin/sh\nexport WAYLAND_DISPLAY=pixelrail-clipboard-test\nexec '+shlex.quote(str(root/'scripts/pixelrail-menu-data'))+' "$@"\n')
            backend.chmod(0o755)
            source=(root/'quickshell/shell.qml').read_text().replace('Launcher { id: launcher }','Launcher { id: launcher; visible:false }')
            source=source.replace('MenuPanel {','MenuPanel {\nvisible:false\nbackend: '+json.dumps(str(backend)))
            source=source.rstrip()[:-1]+'''
            IpcHandler {
                target:"probe"
                function state(): string { return JSON.stringify({opened:menus.item ? menus.item.opened : false,busy:menus.item ? menus.item.busy : false,error:menus.item ? menus.item.error : "",count:menus.item ? menus.item.entries.length : 0}); }
                function choose(id: string): void { if(menus.item) menus.item.choose(menus.item.filtered.findIndex(row => row.id === id)); }
            }
            }
            '''
            config=gui/'shell.qml';config.write_text(source)
            display=original['WAYLAND_DISPLAY']
            if not display.startswith('/'): display=str(Path(original['XDG_RUNTIME_DIR'])/display)
            env=dict(os.environ,PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'),QT_QPA_PLATFORM='wayland',WAYLAND_DISPLAY=display,PIXELRAIL_CLIPBOARD_TRACE='1')
            def ipc(target,method,*args):
                return subprocess.check_output([qs,'ipc','-p',str(config),'call',target,method,*args],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
            def gui_ready():
                try: return ipc('menus','status')=='unloaded'
                except subprocess.SubprocessError: return False
            def gui_state(): return json.loads(ipc('probe','state'))
            with (gui/'log').open('w+') as log:
                process=subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
                try:
                    wait(gui_ready,'native clipboard QML ready')
                    assert ipc('menus','open','clipboard')=='true'
                    wait(lambda:gui_state()['opened'] and not gui_state()['busy'] and gui_state()['count']>0,'native clipboard model')
                    short_row=next(entry for entry in history.listing()[0] if entry['title'].startswith('Привет'))
                    ipc('probe','choose',short_row['id'])
                    wait(lambda:not gui_state()['opened'],'native clipboard UI acknowledged')
                    assert not gui_state()['error'] and paste()==short
                finally: process.terminate();process.wait(timeout=3)
                log.seek(0);output=log.read(); print(output)
                import re
                match=re.search(r'clipboard restore .*ui_total_ms (\d+)',output)
                assert match,output
                measurements['native_qml_callback_ms']=int(match[1])
                for marker in ('TypeError','ReferenceError','Unable to assign','Binding loop','Duplicate signal'):
                    assert marker not in output,marker
            assert paste()==short  # Clipboard ownership also survives the Quickshell test exit.
        else: print('Native QML timing skipped: requires qs and a Wayland session; core native tests still run')
        # Upgrade text-only capture into ONE native watcher; no parallel text/image watchers.
        legacy=subprocess.Popen(['wl-paste','--type','text','--watch','cliphist','store'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        wait(lambda:len(watchers())==1,'legacy watcher started')
        history.ensure_watcher(); legacy.wait(timeout=3)
        assert len(watchers())==1 and watchers()[0]['argv'][1:]==['--watch','cliphist','store']
        keeper=watchers()[0]['pid']
        children=[subprocess.Popen([sys.executable,str(root/'scripts/clipboard_history.py'),'watch'],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
        for child in children:
            out,err=child.communicate(timeout=5); assert child.returncode==0,err
        assert len(watchers())==1 and watchers()[0]['pid']==keeper
        previous_id=int(history.listing()[0][0]['id'])
        watched_png=png(base/'watched.png',color=b'\xfe\x34\x09')
        subprocess.run(['wl-copy','--type','image/png'],input=watched_png,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        wait(lambda:int(history.listing()[0][0]['id'])>previous_id and history.listing()[0][0]['kind']=='image','PNG captured by watcher')
        latest=history.listing()[0][0]
        assert subprocess.check_output(['cliphist','decode'],input=latest['id'].encode())==watched_png
        previous_id=int(latest['id'])
        subprocess.run(['wl-copy','--type','image/jpeg'],input=jpg_bytes,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        wait(lambda:int(history.listing()[0][0]['id'])>previous_id and history.listing()[0][0]['format']=='JPEG','JPEG captured by same watcher')
        subprocess.run(['wl-copy','--type','text/plain;charset=utf-8'],input=b'watcher text fixture',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        wait(lambda:history.listing()[0][0]['title']=='watcher text fixture','text captured by same watcher')
        print(json.dumps(measurements,indent=2))
        output=root/'.cache/clipboard-benchmark.json'
        (root/'.cache/clipboard-latest.json').write_text(json.dumps(measurements,indent=2))
        if '--benchmark' in sys.argv: output.write_text(json.dumps(measurements,indent=2))
    finally:
        for record in watchers(): wallpapers.terminate(record)
        subprocess.run(['wl-copy','--clear'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
        server.terminate();server.wait(timeout=3)
        os.environ.clear();os.environ.update(original)
print('Native clipboard: text/Unicode/multiline, PNG/JPEG/WebP bytes and MIME, lazy bounded previews, ownership, rapid restore, watcher upgrade/dedup: passed')
