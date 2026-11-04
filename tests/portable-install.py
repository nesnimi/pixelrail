"""Portable install/uninstall against a private HOME. No session/package operations."""
import importlib.util
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
import deployment as d
import preflight


class Portable(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=ROOT/'.cache');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.home=self.base/'Другой пользователь';self.home.mkdir()
        self.env=dict(os.environ,XDG_RUNTIME_DIR=str(self.base/'runtime'))

    def run_cli(self,name,*args,ok=True):
        result=subprocess.run([str(ROOT/'scripts'/name),'--target-home',str(self.home),'--no-start',*args],capture_output=True,text=True,env=self.env,timeout=20)
        self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr);return result

    def test_foreign_confirmation_full_chain_and_userdata(self):
        config=self.home/'.config/hypr/hyprland.lua';config.parent.mkdir(parents=True)
        config.write_text('-- independent configuration\nhl.config({input={kb_layout="de"}})\n');config.chmod(0o600);original=config.read_bytes()
        state=self.home/'.local/state/pixelrail/launcher.json';state.parent.mkdir(parents=True);state.write_text('user history sentinel')
        result=self.run_cli('install.sh','--diff');self.assertIn('REVIEW',result.stdout);self.assertEqual(config.read_bytes(),original)
        self.assertFalse((self.home/'.local/share/pixelrail/releases').exists())
        self.run_cli('install.sh','--apply',ok=False);self.assertEqual(config.read_bytes(),original)
        self.run_cli('install.sh','--apply','--accept-config-changes')
        self.assertEqual(config.stat().st_mode&0o777,0o600)
        self.assertIn('kb_layout="de"',config.read_text());self.assertIn('string.format("%q"',config.read_text())
        self.run_cli('install.sh','--apply')
        self.run_cli('uninstall.sh');self.assertTrue((self.home/'.local/bin/pixelrail-shell').exists())
        self.run_cli('uninstall.sh','--apply')
        self.assertEqual(config.read_bytes(),original);self.assertEqual(state.read_text(),'user history sentinel')
        self.assertFalse((self.home/'.local/bin/pixelrail-shell').exists())
        self.assertEqual(len(list((self.home/'.local/share/pixelrail/releases').iterdir())),2)
        self.run_cli('uninstall.sh','--apply',ok=False)

    def test_conf_and_user_edits_are_not_overwritten(self):
        config=self.home/'.config/hypr/hyprland.conf';config.parent.mkdir(parents=True);config.write_text('independent config')
        self.run_cli('install.sh','--apply',ok=False)
        self.assertFalse(config.with_suffix('.lua').exists())
        self.run_cli('install.sh','--apply','--accept-config-changes')
        launcher=self.home/'.local/bin/pixelrail-launcher';launcher.unlink();launcher.write_text('user edit')
        self.run_cli('uninstall.sh','--apply',ok=False);self.assertEqual(launcher.read_text(),'user edit')
        self.assertEqual(config.read_text(),'independent config')

    def test_edited_managed_target_needs_confirmation(self):
        self.run_cli('install.sh','--apply')
        target=(self.home/'.config/hypr/pixelrail-end4-keys.lua').resolve();target.write_text('-- custom keys\n')
        self.run_cli('install.sh','--apply',ok=False);self.assertEqual(target.read_text(),'-- custom keys\n')

    def test_uninstall_failure_restores_installed_files(self):
        d.deploy(self.home,True,True)
        shell=self.home/'.local/bin/pixelrail-shell';before=d.token(shell)
        restore=d.restore;calls=[0]
        def fail_once(*args):
            calls[0]+=1
            if calls[0]==2:raise OSError('injected uninstall failure')
            return restore(*args)
        with patch.object(d,'restore',side_effect=fail_once):
            with self.assertRaisesRegex(OSError,'injected'):d.uninstall(self.home,True,True)
        self.assertEqual(d.token(shell),before)
        self.assertFalse(json.loads(next((self.home/'.local/state/pixelrail/deployments').glob('*/manifest.json')).read_text())['rolled_back'])

    def test_dependency_report_does_not_install(self):
        with patch.object(preflight.shutil,'which',return_value=None),patch.object(preflight.subprocess,'run') as command:
            data=preflight.report(ROOT)
        self.assertTrue(data['errors']);self.assertIn('audio',data['missing_optional'])
        self.assertFalse(any('sudo' in str(call) or 'pacman' in str(call) or 'systemctl' in str(call) for call in command.call_args_list))

    def test_clipboard_cleanup_requires_owned_identity(self):
        import clipboard_history as clipboard
        import hashlib
        runtime=self.base/'watch-runtime';runtime.mkdir()
        record={'pid':42,'start':'100','argv':['wl-paste','--watch','cliphist','store']}
        display=str((runtime/'wayland-fixture').resolve())
        path=runtime/('pixelrail-cliphist-'+hashlib.sha256(display.encode()).hexdigest()[:20]+'.json')
        with patch.dict(os.environ,XDG_RUNTIME_DIR=str(runtime),WAYLAND_DISPLAY='wayland-fixture'),patch.object(clipboard.wallpapers,'terminate') as stop,patch.object(clipboard.wallpapers,'same_session',return_value=True):
            clipboard.stop_owned_watcher();stop.assert_not_called()
            path.write_text(json.dumps(record))
            with patch.object(clipboard.wallpapers,'process',return_value=dict(record,start='reused')):clipboard.stop_owned_watcher()
            stop.assert_not_called()
            with patch.object(clipboard.wallpapers,'process',return_value=record):clipboard.stop_owned_watcher()
            stop.assert_called_once_with(record);self.assertFalse(path.exists())

    def test_live_uninstall_notification_ownership_without_live_calls(self):
        import notifications,panel,clipboard_history
        for owner_pid in (123,999):
            home=self.base/('live-'+str(owner_pid));home.mkdir();d.deploy(home,True,True)
            runtime=Mock();runtime.instances.return_value=[{'pid':123}]
            with patch.object(d,'Shell',return_value=runtime),patch.object(notifications,'owner',return_value={'pid':owner_pid}),patch.object(notifications,'switch') as switch,patch.object(d.shutil,'which',side_effect=lambda name:'/fixture/swaync' if name=='swaync' else None),patch.object(panel,'locked',return_value=nullcontext()),patch.object(panel,'owned_bar',return_value=None),patch.object(panel,'stop_bar'),patch.object(clipboard_history,'stop_owned_watcher'):
                d.uninstall(home,True,False)
                if owner_pid==123:switch.assert_called_once_with('swaync',save=False)
                else:switch.assert_not_called()
            runtime.retire.assert_called_once_with()


if __name__=='__main__':unittest.main()
