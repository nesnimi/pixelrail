"""Installer failure transactions and graphical profile writes in a private HOME."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('deployment',ROOT/'scripts/deployment.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Reliability(unittest.TestCase):
    def test_missing_native_stops_before_any_write(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);home=base/'home';home.mkdir()
            with patch.object(d,'REPO',base/'empty'):
                with self.assertRaisesRegex(ValueError,'build-native'):d.deploy(home,True,True)
            self.assertEqual(list(home.iterdir()),[])
    def test_install_failure_restores_previous_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            home=Path(tmp);binary=home/'.local/bin';binary.mkdir(parents=True)
            original=binary/'pixelrail-benchmark';original.write_text('previous');original.chmod(0o750)
            replace=d.replace;injected=[False];installs=[0]
            def fail_once(destination,**options):
                if destination.parent==binary:
                    installs[0]+=1
                    if installs[0]==3 and not injected[0]:injected[0]=True;raise OSError('injected mid-install failure')
                return replace(destination,**options)
            with patch.object(d,'replace',side_effect=fail_once):
                with self.assertRaisesRegex(OSError,'mid-install'):d.deploy(home,True,True,accept_changes=True)
            self.assertTrue(injected[0]);self.assertEqual(original.read_text(),'previous');self.assertEqual(original.stat().st_mode&0o777,0o750)
            self.assertEqual(list(binary.iterdir()),[original])
            manifests=list((home/'.local/state/pixelrail/deployments').glob('*/manifest.json'))
            self.assertEqual(len(manifests),1)
            import json
            self.assertFalse(json.loads(manifests[0].read_text())['complete'])
    def test_profile_atomic_failure_preserves_old_and_no_real_commands(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);binary=base/'bin';binary.mkdir();cache=base/'cache';state=cache/'pixelrail/profile';state.parent.mkdir(parents=True);state.write_text('battery\n')
            for name in ('hyprctl','notify-send'):
                path=binary/name;path.write_text('#!/bin/sh\nexit 0\n');path.chmod(0o755)
            env=dict(os.environ,HOME=str(base),XDG_CACHE_HOME=str(cache),PATH=str(binary)+':/usr/bin',HYPRLAND_INSTANCE_SIGNATURE='fixture',DBUS_SESSION_BUS_ADDRESS='unix:path='+str(base/'absent'))
            subprocess.run([str(ROOT/'scripts/pixelrail-profile'),'performance'],env=env,check=True,timeout=3)
            self.assertEqual(state.read_text(),'performance\n')
            fail=binary/'mv';fail.write_text('#!/bin/sh\nexit 1\n');fail.chmod(0o755)
            result=subprocess.run([str(ROOT/'scripts/pixelrail-profile'),'battery'],env=env,timeout=3)
            self.assertNotEqual(result.returncode,0);self.assertEqual(state.read_text(),'performance\n');self.assertFalse(list(state.parent.glob('.profile.*')))
if __name__=='__main__':unittest.main()
