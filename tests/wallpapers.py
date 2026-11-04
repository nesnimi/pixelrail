"""Real image decoding and fake swaybg; all state/config/children are test-owned."""
import contextlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0,str(Path.cwd()/'scripts'))
import wallpapers as wp

def png(path, width=32, height=24):
    path.parent.mkdir(parents=True,exist_ok=True)
    def chunk(kind,data): return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress((b'\0'+b'\x60\x90\xc0'*width)*height))+chunk(b'IEND',b''))
    return path

class Wallpapers(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd()/'.cache'); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.home=self.base/'home'; self.home.mkdir()
        self.runtime=self.base/'runtime'; self.runtime.mkdir(mode=0o700)
        self.environment=patch.dict(os.environ, HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'.config'),
                                    XDG_STATE_HOME=str(self.base/'state'),XDG_CACHE_HOME=str(self.base/'cache'),
                                    XDG_RUNTIME_DIR=str(self.runtime),WAYLAND_DISPLAY='wallpaper-fixture',
                                    XDG_PICTURES_DIR=str(self.home/'Pictures'),XDG_DOWNLOAD_DIR=str(self.home/'Downloads'),
                                    XDG_DOWNLOADS_DIR=str(self.home/'Downloads'))
        self.environment.start(); self.addCleanup(self.environment.stop)
    def config(self, data):
        path=self.home/'.config/pixelrail/wallpapers.json'; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data))
    def test_cache_bound_protects_current_and_unrelated_files(self):
        root=self.base/'thumbs';root.mkdir()
        for index in range(8):
            path=root/(format(index,'064x')+'.png');path.write_bytes(b'x'*16);os.utime(path,(index+1,index+1))
        unrelated=root/'temporary.png';unrelated.write_bytes(b'do not remove')
        outside=self.base/'original.png';outside.write_bytes(b'original')
        link=root/('f'*64+'.png');link.symlink_to(outside)
        keep=root/('0'*64+'.png')
        with patch.object(wp,'CACHE_ENTRIES',3),patch.object(wp,'CACHE_BYTES',48):wp.prune_thumbnails(root,keep)
        cached=[path for path in root.glob('*.png') if len(path.stem)==64 and not path.is_symlink()]
        self.assertEqual(len(cached),3);self.assertLessEqual(sum(path.stat().st_size for path in cached),48)
        self.assertTrue(keep.is_file());self.assertTrue(link.is_symlink());self.assertEqual(outside.read_bytes(),b'original');self.assertTrue(unrelated.exists())
    def test_sources_categories_unicode_dedup_and_depth(self):
        image=png(self.home/'Pictures/Wallpapers/Горы с длинным именем.png')
        downloaded=png(self.home/'Downloads/Новые обои.PNG')
        screenshot=png(self.home/'Pictures/Screenshots/2026.png')
        extra=png(self.base/'extra/space # " файл.png')
        hidden=png(self.home/'Downloads/.hidden/no.png')
        deep=png(self.home/'Downloads/a/b/c/d/e/deep.png')
        self.config({'directories':[str(extra.parent),str(image.parent)]})
        rows=wp.catalog(); ids=[row['id'] for row in rows]
        self.assertEqual(len(ids),4); self.assertEqual(len(set(ids)),4)
        self.assertNotIn(str(hidden),ids); self.assertNotIn(str(deep),ids)
        self.assertEqual(next(r['category'] for r in rows if r['id']==str(downloaded)),'downloads')
        self.assertEqual(rows[-1]['id'],str(screenshot))
        self.assertEqual(next(r['title'] for r in rows if r['id']==str(image)),image.name)
        self.assertNotEqual(rows[0]['category'],'screenshots')
    def test_localized_xdg_user_dirs_and_disabled_home(self):
        image=png(self.home/'Загрузки/фон.png')
        path=self.home/'.config/user-dirs.dirs'; path.parent.mkdir(parents=True)
        path.write_text('XDG_DOWNLOAD_DIR="$HOME/Загрузки"\nXDG_PICTURES_DIR="$HOME"\n')
        with patch.dict(os.environ):
            for name in ('XDG_DOWNLOAD_DIR','XDG_DOWNLOADS_DIR','XDG_PICTURES_DIR'): os.environ.pop(name,None)
            self.assertIn(str(image),[row['id'] for row in wp.catalog()])
        self.config({'directories':['~/']})
        with self.assertRaises(ValueError): wp.catalog()
    def test_runtime_formats_thumbnail_limits_cache_and_invalid(self):
        image=png(self.home/'Pictures/large # кириллица.png',1200,800)
        uri=wp.thumbnail(image); target=wp.cache_file(image); timestamp=target.stat().st_mtime_ns
        self.assertTrue(uri.startswith('file:///')); self.assertTrue(target.is_file())
        header=target.read_bytes(); width,height=struct.unpack('!2I',header[16:24])
        self.assertLessEqual(width,512); self.assertLessEqual(height,384)
        self.assertEqual(wp.thumbnail(image),uri); self.assertEqual(target.stat().st_mtime_ns,timestamp)
        png(image,800,600); self.assertNotEqual(wp.thumbnail(image),uri)
        formats=wp.pixbuf().extensions(); self.assertIn('png',formats); self.assertIn('jpeg',formats)
        other=self.home/'Downloads/test.ppm'; other.parent.mkdir(exist_ok=True)
        other.write_bytes(b'P6\n2 2\n255\n'+b'\xff\0\0'*4)
        if 'ppm' in formats: self.assertTrue(wp.thumbnail(other))
        broken=self.home/'Pictures/broken.png'; broken.write_bytes(b'not an image')
        with self.assertRaises(ValueError): wp.thumbnail(broken)
        outside=png(self.base/'outside.png')
        with self.assertRaises(ValueError): wp.thumbnail(outside)
    def test_manager_apply_restore_concurrency_failure_and_foreign(self):
        binary=self.base/'bin'; binary.mkdir(); log=self.base/'starts'; failure=self.base/'fail'
        fake=binary/'swaybg'
        fake.write_text('''#!/usr/bin/env python3
import os, pathlib, sys, time
with open(os.environ['WALLPAPER_TEST_LOG'],'a') as stream: stream.write(repr(sys.argv[1:])+"\\n")
if pathlib.Path(os.environ['WALLPAPER_TEST_FAIL']).exists() and 'failure.png' in ' '.join(sys.argv): sys.exit(1)
while True: time.sleep(1)
'''); fake.chmod(0o755)
        image=png(self.home/'Downloads/первая.png'); second=png(self.home/'Pictures/Wallpapers/вторая.png')
        bad=png(self.home/'Downloads/failure.png')
        with patch.dict(os.environ,PATH=str(binary)+':/usr/bin',WALLPAPER_TEST_LOG=str(log),WALLPAPER_TEST_FAIL=str(failure)):
            def record(): return json.loads(next(self.runtime.glob('pixelrail-swaybg-*.json')).read_text())
            def cleanup():
                for path in self.runtime.glob('pixelrail-swaybg-*.json'):
                    with contextlib.suppress(OSError,ValueError): wp.terminate(json.loads(path.read_text()))
            self.addCleanup(cleanup)
            try:
                wp.apply(image); initial=record(); self.assertIsNotNone(wp.process(initial['pid']))
                self.assertEqual(wp.selected(),str(image))
                wrapper=str(Path.cwd()/'scripts/pixelrail-wallpaper')
                starts=[subprocess.Popen([wrapper],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
                for child in starts:
                    output,error=child.communicate(timeout=10); self.assertEqual(child.returncode,0,error)
                self.assertEqual(record()['pid'],initial['pid']); self.assertEqual(len(log.read_text().splitlines()),1)
                wp.apply(second); active=record(); self.assertNotEqual(active['pid'],initial['pid'])
                self.assertIsNone(wp.process(initial['pid'])); self.assertEqual(wp.selected(),str(second))
                failure.touch()
                with self.assertRaises(ValueError): wp.apply(bad)
                self.assertEqual(wp.selected(),str(second)); active=record(); self.assertIsNotNone(wp.process(active['pid']))
                wp.terminate(active)
                subprocess.run([wrapper],check=True,capture_output=True,timeout=10)
                self.assertEqual(wp.selected(),str(second)); active=record()
                self.assertIn(str(second),active['argv'])
                # A distinct, test-owned process deliberately presents swaybg argv[0].
                foreign=subprocess.Popen(['swaybg',str(fake)],executable='/usr/bin/python3')
                try:
                    import time; time.sleep(.1)
                    with self.assertRaisesRegex(ValueError,'сторонний'): wp.apply(image)
                    self.assertIsNone(foreign.poll()); self.assertIsNotNone(wp.process(active['pid']))
                finally: foreign.terminate(); foreign.wait(timeout=3)
            finally: cleanup()

if __name__=='__main__': unittest.main()
