import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0,str(Path.cwd()/'scripts'))

loader = importlib.machinery.SourceFileLoader('menu_data', 'scripts/pixelrail-menu-data')
spec = importlib.util.spec_from_loader(loader.name, loader)
backend = importlib.util.module_from_spec(spec)
loader.exec_module(backend)

class Menus(unittest.TestCase):
    def test_keys_read_only_and_layout(self):
        data = [{'key':'Slash', 'modmask':64, 'description':'Справка'},
                {'key':'Q','modmask':64,'description':'Закрыть','submap':'other'}]
        with patch.object(backend, 'run', return_value=json.dumps(data).encode()):
            rows = backend.listing('keys')
        self.assertEqual(rows[0]['title'], 'Super + /')
        self.assertEqual(rows[-1]['id'], 'layout')
        with patch.object(backend, 'run') as run:
            self.assertTrue(backend.activate('keys', {'id':'anything'})['keep'])
            run.assert_not_called()

    def test_clipboard_uses_native_restore_without_listing(self):
        with patch.object(backend.clipboard_history, 'restore', return_value={}) as restore, patch.object(backend, 'clipboard') as listing:
            backend.activate('clipboard', {'id':'7','kind':'image'})
            restore.assert_called_once_with({'id':'7','kind':'image'})
            listing.assert_not_called()

    def test_command_only_on_activate(self):
        with patch.object(backend, 'detach') as detach:
            backend.listing('command')
            detach.assert_not_called()
            backend.activate('command', {'id':'printf test | cat', 'command':'printf test | cat'})
            detach.assert_called_once_with(['/bin/sh','-c','printf test | cat'])

    def test_power_requires_confirmation(self):
        for key in ('suspend','logout','reboot','shutdown'):
            with patch.object(backend, 'detach') as detach, patch.object(backend, 'run') as run:
                self.assertEqual(backend.activate('power', {'id':key})['confirm'], key)
                detach.assert_not_called(); run.assert_not_called()
        with patch.object(backend, 'detach') as detach:
            backend.activate('power', {'id':'shutdown','confirmed':True})
            detach.assert_called_once_with(['systemctl','poweroff'])

    def test_windows_fresh_address_and_literal_lua(self):
        with patch.object(backend, 'run', side_effect=[b'[{"address":"0xabc"}]',b'ok']) as run:
            backend.activate('windows', {'id':'0xabc'})
            self.assertIn('window = "address:0xabc"', run.call_args.args[0][-1])
        with patch.object(backend, 'run', return_value=b'[]'):
            with self.assertRaises(ValueError): backend.activate('windows', {'id':'0xabc'})
        with self.assertRaises(ValueError): backend.activate('windows', {'id':'0xabc";os.exit()'})

    def test_actions_media_and_emoji(self):
        self.assertEqual(backend.activate('controls', {'id':'applications'}), {'next':'applications'})
        with patch.object(backend, 'run') as run:
            backend.activate('emoji', {'id':'💚'})
            run.assert_called_once_with(['wl-copy'], '💚'.encode())
        with patch.object(backend, 'run') as run:
            backend.activate('media', {'id':'next'})
            run.assert_called_once_with(['playerctl','next'])

    def test_wallpaper_routes_use_shared_manager(self):
        with patch.object(backend.wallpapers, 'catalog', return_value=[{'id':'fixture'}]):
            self.assertEqual(backend.listing('wallpaper'), [{'id':'fixture'}])
        with patch.object(backend.wallpapers, 'apply') as apply:
            result=backend.activate('wallpaper', {'id':'/fixture/image.png'})
            apply.assert_called_once_with('/fixture/image.png')
            self.assertEqual(result, {'wallpaper':'/fixture/image.png'})

if __name__ == '__main__': unittest.main()
