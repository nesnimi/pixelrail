"""Real matugen in isolated XDG directories; no wallpaper/process changes."""
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
import material_you as engine

def png(path,color):
    path.parent.mkdir(parents=True,exist_ok=True)
    def chunk(kind,data): return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,24,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress((b'\0'+bytes(color)*32)*24))+chunk(b'IEND',b''))
    return path

class MaterialYou(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path.cwd()/'.cache');self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        context=patch.dict(os.environ,HOME=str(self.home),XDG_CONFIG_HOME=str(self.home/'config'),
                           XDG_STATE_HOME=str(self.home/'state'),XDG_CACHE_HOME=str(self.home/'cache'))
        context.start();self.addCleanup(context.stop)
    def sync(self):
        with engine.locked(): return engine.sync()
    def select(self,path): engine.atomic(engine.wallpapers.choice_file(),str(path)+'\n')
    def test_real_images_semantics_and_contrast(self):
        warm=png(self.home/'Обои с пробелами/Закат.png',(240,80,20));cool=png(self.home/'Холодный # фон.png',(30,70,230))
        self.select(warm);self.assertEqual(self.sync()['status'],'generated')
        first=engine.cached();self.assertIn('matugen',first['matugen']);engine.validate(first['schemes'])
        self.select(cool);self.sync();second=engine.cached()
        self.assertNotEqual(first['schemes']['dark']['primary'],second['schemes']['dark']['primary'])
        self.assertNotEqual(second['schemes']['dark']['surfaceContainer'],second['schemes']['dark']['surfaceContainerHigh'])
    def test_modes_and_content_identity_skip_matugen(self):
        path=png(self.home/'one.png',(70,120,200));self.select(path);self.sync()
        original=subprocess.run
        with patch.object(engine.subprocess,'run',wraps=original) as run:
            for mode in ('light','auto','dark'):
                engine.atomic(engine.config_path(),{'mode':mode,'accent':None})
                self.assertEqual(self.sync()['status'],'cached')
            path.write_bytes(path.read_bytes())  # New mtime, identical image bytes.
            self.assertEqual(self.sync()['status'],'cached')
            run.assert_not_called()
    def test_manual_accent_reset_and_persistence(self):
        path=png(self.home/'source.png',(200,50,20));self.select(path);self.sync();initial=engine.cached()['schemes']
        engine.atomic(engine.config_path(),{'mode':'light','accent':'#0A5'})
        self.sync();self.assertEqual(engine.settings(),{'mode':'light','accent':'#00AA55'})
        self.assertNotEqual(engine.cached()['schemes'],initial)
        engine.atomic(engine.config_path(),{'mode':'auto','accent':None});self.sync()
        self.assertEqual(engine.cached()['schemes'],initial)
    def test_missing_corrupt_input_and_missing_matugen_preserve_last(self):
        good=png(self.home/'good.png',(40,100,220));self.select(good);self.sync()
        before=engine.palette_path().read_bytes()
        for value in (self.home/'missing.png',self.home/'bad.png'):
            if value.name=='bad.png': value.write_bytes(b'bad image')
            self.select(value)
            with self.assertRaises((ValueError,OSError)): self.sync()
            self.assertEqual(engine.palette_path().read_bytes(),before)
        self.select(good)
        with patch.object(engine.shutil,'which',return_value=None):
            self.assertEqual(self.sync()['status'],'cached')
            engine.atomic(engine.config_path(),{'mode':'light','accent':'#FF3300'})
            with self.assertRaises(ValueError): self.sync()
        self.assertEqual(engine.palette_path().read_bytes(),before)
    def test_absent_matugen_fallback_and_settings_survive(self):
        with patch.object(engine.shutil,'which',return_value=None):
            with self.assertRaises(ValueError): self.sync()
        self.assertTrue(engine.config_path().is_file());self.assertFalse(engine.palette_path().exists())
        self.assertEqual(engine.settings()['mode'],'dark')
    def test_json4_and_legacy_parser_reject_partial(self):
        self.sync();schemes=engine.cached()['schemes']
        import re
        snake=lambda key: re.sub(r'([A-Z])',lambda m:'_'+m[0].lower(),key)
        old={'colors':{mode:{snake(key):value for key,value in data.items()} for mode,data in schemes.items()}}
        new={'colors':{snake(key):{mode:{'color':schemes[mode][key]} for mode in schemes} for key in schemes['dark']}}
        self.assertEqual(engine.normalize(old),schemes);self.assertEqual(engine.normalize(new),schemes)
        with self.assertRaises(ValueError):engine.normalize({'colors':{'primary':{'dark':{'color':'#000000'}}}})
        bad=json.loads(json.dumps(schemes));bad['dark']['onPrimary']=bad['dark']['primary']
        with self.assertRaises(ValueError):engine.validate(bad)
    def test_superseded_generation_does_not_commit(self):
        self.sync();before=engine.palette_path().read_bytes()
        engine.atomic(engine.config_path(),{'mode':'dark','accent':'#FF3300'})
        actual=engine.source;calls=0
        def source(config):
            nonlocal calls
            calls+=1
            return actual(config) if calls==1 else {'kind':'accent','color':'#0022FF'}
        with patch.object(engine,'source',side_effect=source):self.assertEqual(self.sync()['status'],'superseded')
        self.assertEqual(engine.palette_path().read_bytes(),before)
    def test_concurrent_requests_only_one_generation(self):
        binary=self.home/'bin';binary.mkdir();real=engine.shutil.which('matugen');log=self.home/'runs'
        tool=binary/'matugen';tool.write_text('#!/usr/bin/env python3\nimport os,sys\nwith open(os.environ["THEME_RUN_LOG"],"a") as stream: stream.write(" ".join(sys.argv[1:])+"\\n")\nos.execv('+repr(real)+',["matugen",*sys.argv[1:]])\n');tool.chmod(0o755)
        with patch.dict(os.environ,PATH=str(binary)+':'+os.environ['PATH'],THEME_RUN_LOG=str(log)):
            children=[subprocess.Popen([str(Path.cwd()/'scripts/pixelrail-theme'),'sync'],stdout=subprocess.PIPE) for _ in range(4)]
            for child in children:
                output,_=child.communicate(timeout=10);self.assertEqual(child.returncode,0,output)
        self.assertEqual(sum('--json' in line for line in log.read_text().splitlines()),1)
        self.assertEqual(len(log.read_text().splitlines()),2)  # version + generation, not per request.

if __name__=='__main__':unittest.main()
