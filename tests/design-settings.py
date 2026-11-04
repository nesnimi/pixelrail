"""UI config migrations, validation and cursor preview, isolated XDG only."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
ROOT=Path.cwd()
class Design(unittest.TestCase):
    def test_legacy_migration_unknown_keys_and_atomic_ui_updates(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700)
            env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),PIXELRAIL_QML=str(base/'not-running.qml'))
            config=base/'config/pixelrail/theme.json';config.parent.mkdir(parents=True);config.write_text(json.dumps({'mode':'light','accent':'#ABCDEF','future':{'preserve':True}}))
            def command(*args):return subprocess.run([str(ROOT/'scripts/pixelrail-theme'),*args],env=env,capture_output=True,text=True,timeout=5)
            for index in range(6):
                self.assertEqual(command('ui','iconStyle','themed' if index%2==0 else 'original').returncode,0)
                data=json.loads(config.read_text());self.assertEqual(data['mode'],'light');self.assertEqual(data['accent'],'#ABCDEF');self.assertEqual(data['future'],{'preserve':True});self.assertEqual(data['uiVersion'],1)
            self.assertEqual(command('ui','animations','false').returncode,0);self.assertFalse(json.loads(config.read_text())['animations'])
            before=config.read_bytes()
            for key,value in [('animations','maybe'),('iconStyle','garbage')]:self.assertNotEqual(command('ui',key,value).returncode,0);self.assertEqual(config.read_bytes(),before)
            self.assertFalse((base/'cache/pixelrail/theme/palette.json').exists(),'UI changes generated an unrelated palette')
            self.assertEqual(command('status').returncode,0)
    def test_desktop_unknown_preferences_survive(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);config=base/'config';file=config/'pixelrail/desktop.json';file.parent.mkdir(parents=True);file.write_text(json.dumps({'heightRatio':.63,'dnd':True,'future':'keep'}))
            env=dict(os.environ,HOME=tmp,XDG_CONFIG_HOME=str(config))
            result=subprocess.run([str(ROOT/'scripts/pixelrail-desktop'),'save',json.dumps({'heightRatio':.7,'dnd':False})],env=env,capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,0,result.stderr);data=json.loads(file.read_text());self.assertEqual(data['future'],'keep');self.assertEqual(data['heightRatio'],.7);self.assertFalse(data['dnd'])
    def test_cursor_preview_never_applies(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            output=Path(tmp)/'preview';result=subprocess.run([str(ROOT/'scripts/pixelrail-cursor'),'prepare','--theme','GoogleDot-White','--size','28','--output',str(output)],capture_output=True,text=True,timeout=3)
            self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(json.loads(result.stdout)['applied']);self.assertIn('GoogleDot-White',(output/'cursor.lua').read_text())
            if shutil.which('Hyprland'):
                runtime=Path(tmp)/'runtime';runtime.mkdir(mode=0o700)
                env=dict(os.environ,HOME=tmp,XDG_RUNTIME_DIR=str(runtime),XDG_CACHE_HOME=str(Path(tmp)/'cache'),XDG_CONFIG_HOME=str(Path(tmp)/'config'),XDG_STATE_HOME=str(Path(tmp)/'state'))
                env.pop('HYPRLAND_INSTANCE_SIGNATURE',None)
                verified=subprocess.run(['Hyprland','--verify-config','-c',str(output/'cursor.lua')],env=env,capture_output=True,text=True,timeout=15)
                self.assertEqual(verified.returncode,0,verified.stdout+verified.stderr)
            bad=subprocess.run([str(ROOT/'scripts/pixelrail-cursor'),'prepare','--output','/tmp/pixelrail-forbidden-preview'],capture_output=True,text=True,timeout=3);self.assertNotEqual(bad.returncode,0)
    def test_sources_and_no_brightness_regression(self):
        self.assertTrue((ROOT/'quickshell/assets/fonts/OFL.txt').is_file());self.assertIn('Apache License',(ROOT/'quickshell/assets/symbols/LICENSE').read_text())
        for file in ['scripts/desktop.py','scripts/pixelrail-system']:self.assertNotIn('-n 1',(ROOT/file).read_text())
        source=(ROOT/'quickshell/ui/PixelAppIcon.qml').read_text();self.assertIn('-symbolic',(ROOT/'quickshell/ui/AppIcons.js').read_text());self.assertIn('!root.themed',source);self.assertIn('canTint',source)
if __name__=='__main__':unittest.main()
