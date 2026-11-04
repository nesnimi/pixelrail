"""Notification transactions with real busctl error text; no live bus/processes."""
from contextlib import ExitStack, nullcontext
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('notification_backend',ROOT/'scripts/notifications.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)

class Notifications(unittest.TestCase):
    def test_absent_owner_and_pid_races(self):
        ok=lambda value:subprocess.CompletedProcess([],0,value,'')
        fail=lambda value:subprocess.CompletedProcess([],1,'','Call failed: '+value+'\n')
        for text in ('The name does not have an owner',f'Name "{n.NAME}" does not exist',f"Could not get owner of name '{n.NAME}': no such name"):
            with self.subTest(text=text),patch.object(n.subprocess,'run',return_value=fail(text)) as run:
                self.assertIsNone(n.owner());self.assertEqual(run.call_args.kwargs['env']['LC_ALL'],'C')
        for text in ('The name does not have an owner',"Could not get PID of name ':1.7': no such name"):
            with self.subTest(text=text),patch.object(n.subprocess,'run',side_effect=[ok('s ":1.7"'),fail(text)]):
                self.assertIsNone(n.owner())
        with patch.object(n.subprocess,'run',side_effect=[ok('s ":1.7"'),ok('u 123'),ok('s ":1.8"')]):
            self.assertIsNone(n.owner())
        with patch.object(n.subprocess,'run',side_effect=[ok('s ":1.7"'),ok('u 123'),fail('The name does not have an owner')]):
            self.assertIsNone(n.owner())

    def test_other_errors_propagate(self):
        for text in ('Access denied','Failed to connect to bus: No medium found','Connection reset by peer',
                     'The name org.example.Service was not provided by any .service files','Unexpected protocol failure'):
            with self.subTest(text=text),patch.object(n.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','Call failed: '+text)):
                with self.assertRaises(n.NotificationError):n.owner()
        with patch.object(n.subprocess,'run',side_effect=subprocess.TimeoutExpired('busctl',3)):
            with self.assertRaises(subprocess.TimeoutExpired):n.owner()

    def transaction(self,initial='swaync',fail=False):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp,ExitStack() as stack:
            config=Path(tmp)/'shell.qml';lib=Path(tmp)/'native/PixelRail/DBusLease/libpixelraillease.so'
            lib.parent.mkdir(parents=True);lib.touch()
            row={'pid':200,'config_path':str(config)}
            owners={'swaync':{'name':':1.sway','pid':100},'pixelrail':{'name':':1.qs','pid':200},'foreign':{'name':':1.other','pid':300},None:None}
            current=[owners[initial]];events=[];saved=[]
            def ipc(row,method,*args):
                events.append(method)
                if method=='enable':
                    self.assertIsNone(current[0],'must release old name before acquisition')
                    if fail:raise n.NotificationError('fixture: native start failed')
                    current[0]=owners['pixelrail']
                if method=='disable' and current[0]==owners['pixelrail']:current[0]=None
                return 'true'
            def kill(pid,sig):
                self.assertEqual(pid,100);events.append('stop-swaync');current[0]=None
            def start():
                self.assertIsNone(current[0]);events.append('start-swaync');current[0]=owners['swaync']
            def wait(predicate,message,timeout=4):self.assertTrue(predicate(),message)
            replacements=[(n,'owner',lambda:current[0]),(n,'swaync',lambda owner:owner==owners['swaync']),
                          (n,'state',lambda row:{'enabled':current[0]==owners['pixelrail'],'bridgeReady':True}),
                          (n,'ipc',ipc),(n,'start_swaync',start),(n,'wait',wait),
                          (n.panel,'shells',lambda:[row]),(n.panel,'current_shell',lambda rows:row),
                          (n.panel,'process',lambda pid:{'pid':pid,'start':42}),(n.panel,'atomic',lambda *args:saved.append(args)),
                          (n.os,'kill',kill),(n.subprocess,'check_output',lambda *a,**k:'Quickshell 0.3.2 test'),
                          (__import__('shutil'),'which',lambda name:'/fixture/qs')]
            for obj,name,value in replacements:stack.enter_context(patch.object(obj,name,value))
            if initial=='foreign' or fail:
                with self.assertRaises(n.NotificationError):n.switch('pixelrail',save=True)
                self.assertFalse(saved)
                self.assertEqual(current[0],owners['foreign' if initial=='foreign' else 'swaync'])
                if initial=='foreign':self.assertEqual(events,[])
                else:self.assertEqual(events,['preflight','stop-swaync','enable','disable','start-swaync'])
            else:
                n.switch('pixelrail',save=True)
                self.assertEqual(current[0],owners['pixelrail']);self.assertEqual(len(saved),1)
                self.assertEqual(events,['preflight']+(['stop-swaync'] if initial else [])+['enable'])

    def test_recovery_only_starts_on_free_name(self):
        for owner in (None,{'name':':1.foreign','pid':300}):
            with self.subTest(owner=owner),patch.object(n,'locked',nullcontext),patch.object(n,'owner',return_value=owner),patch.object(n,'start_swaync') as start:
                n.recover_swaync()
                self.assertEqual(start.call_count,1 if owner is None else 0)

    def test_reconcile_fallback_and_recovery(self):
        with patch.object(n,'locked',nullcontext),patch.object(n,'mode',return_value='pixelrail'),patch.object(n.panel,'shells',return_value=[]),patch.object(n.panel,'current_shell',return_value=None),patch.object(n,'switch') as switch:
            n.reconcile();switch.assert_called_once_with('swaync')
        with patch.object(n,'locked',nullcontext),patch.object(n,'mode',return_value='swaync'),patch.object(n.panel,'shells',return_value=[]),patch.object(n.panel,'current_shell',return_value=None),patch.object(n,'switch',side_effect=n.NotificationError('fixture failure')),patch.object(n,'recover_swaync') as recover,patch('sys.stderr'):
            n.reconcile();recover.assert_called_once_with()

    def test_swaync_to_native(self):self.transaction()
    def test_free_name(self):self.transaction(initial=None)
    def test_native_failure_restores_swaync(self):self.transaction(fail=True)
    def test_foreign_untouched(self):self.transaction(initial='foreign')

if __name__=='__main__':unittest.main()
