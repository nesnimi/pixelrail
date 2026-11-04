"""Read-only system probes and real keyboard command routing, with fake devices."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('desktop',ROOT/'scripts/desktop.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Settings(unittest.TestCase):
    def reply(self,data):return subprocess.CompletedProcess([],0,json.dumps(data),'')
    def test_real_keymap_and_toggle_readback(self):
        en={'keyboards':[{'name':'thinkpad','main':True,'active_keymap':'English (US)'}]}
        ru={'keyboards':[{'name':'thinkpad','main':True,'active_keymap':'Russian'}]}
        with patch.object(d.shutil,'which',return_value='/hyprctl'),patch.object(d.subprocess,'run',side_effect=[self.reply(en),subprocess.CompletedProcess([],0,'ok\n',''),self.reply(ru)]) as run:
            self.assertEqual(d.keyboard_state(toggle=True)['label'],'RU')
            self.assertEqual(run.call_args_list[1].args[0],['/hyprctl','switchxkblayout','thinkpad','next'])
        for data in ({'keyboards':[]},{'keyboards':[{'name':'x','main':True,'active_keymap':'Unknown'}]}):
            with patch.object(d.shutil,'which',return_value='/hyprctl'),patch.object(d.subprocess,'run',return_value=self.reply(data)):
                self.assertFalse(d.keyboard_state()['available']);self.assertEqual(d.keyboard_state()['label'],'—')
    def test_active_keyboard_hint_and_error(self):
        data={'keyboards':[{'name':'internal','main':True,'active_keymap':'English (US)'},{'name':'USB клавиатура','active_keymap':'Russian'}]}
        with patch.object(d.shutil,'which',return_value='/hyprctl'),patch.object(d.subprocess,'run',return_value=self.reply(data)):
            self.assertEqual(d.keyboard_state('USB клавиатура')['label'],'EN')
            data['keyboards'][0]['main']=False;data['keyboards'][1]['main']=True
        with patch.object(d.shutil,'which',return_value='/hyprctl'),patch.object(d.subprocess,'run',return_value=self.reply(data)):
            self.assertEqual(d.keyboard_state('internal')['label'],'RU')
        with patch.object(d.shutil,'which',return_value='/hyprctl'),patch.object(d.subprocess,'run',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):d.keyboard_state()
    def test_bluetooth_service_hardware_and_block(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);rf=base/'class/rfkill/rfkill0';rf.mkdir(parents=True)
            for name,value in {'type':'bluetooth','soft':'0','hard':'0'}.items():(rf/name).write_text(value)
            (base/'class/bluetooth/hci0').mkdir(parents=True)
            for service in (True,False):
                with patch.object(d.shutil,'which',return_value='/busctl'),patch.object(d.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'b '+str(service).lower(),'')):
                    state=d.bluetooth_state(base);self.assertEqual(state['service'],service);self.assertEqual(state['controllers'],['hci0']);self.assertFalse(state['blocked'])
                    (rf/'hard').write_text('1');self.assertTrue(d.bluetooth_state(base)['blocked']);(rf/'hard').write_text('0')
            with patch.object(d.shutil,'which',return_value='/busctl'),patch.object(d.subprocess,'run',side_effect=PermissionError('denied')):
                self.assertIsNone(d.bluetooth_state(base)['service']);self.assertTrue(d.bluetooth_state(base)['error'])
    def test_minimal_ui_and_no_brightness_regression(self):
        sidebar=(ROOT/'quickshell/modules/sidebar/Sidebar.qml').read_text();top=sidebar.split('id: systemGroup')[1].split('Item { Layout.fillWidth: true; Layout.fillHeight: true }')[0]
        import re
        self.assertEqual(re.findall(r'objectName: "([^"]+)"',top),['sidebar-power','sidebar-network','sidebar-battery'])
        self.assertLess(sidebar.index('sidebar-workspaces'),sidebar.index('sidebar-apps'));self.assertLess(sidebar.index('sidebar-apps'),sidebar.index('sidebar-home'))
        for name in ('sidebar-clock','sidebar-profile','sidebar-volume','sidebar-notifications'):self.assertNotIn(name,sidebar)
        control=(ROOT/'quickshell/modules/control/ControlCenter.qml').read_text()
        for name in ('control-layout','control-profile','control-battery','control-clock'):self.assertIn(name,control)
        self.assertNotIn('text:"×"',control);self.assertNotIn('ScrollBar.vertical',control)
        self.assertNotIn('Закрыть · Esc',(ROOT/'quickshell/components/ClipboardView.qml').read_text())
        for file in ('scripts/desktop.py','scripts/pixelrail-system'):self.assertNotIn("'-n'",(ROOT/file).read_text());self.assertNotIn('-n 1',(ROOT/file).read_text())
        self.assertIn('kb_layout = "us,ru"',(ROOT/'hypr/hyprland.lua').read_text());self.assertIn('grp:alt_shift_toggle',(ROOT/'hypr/hyprland.lua').read_text())
if __name__=='__main__':unittest.main()
