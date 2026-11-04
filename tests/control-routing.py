"""Fast navigation must not re-enter lifecycle; cold start remains available."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
spec=importlib.util.spec_from_file_location('control_backend',root/'scripts/control.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Routing(unittest.TestCase):
    def test_ready_fast_path(self):
        with patch.object(module.panel,'shells',return_value=[]),patch.object(module.panel,'current_shell',return_value={'pid':123}),patch.object(module.shutil,'which',return_value='/qs'),patch.object(module.subprocess,'run') as start,patch.object(module.subprocess,'check_output',side_effect=['','{"opened":true,"loaded":true}']) as ipc,patch.object(sys,'argv',['pixelrail-control']):
            self.assertEqual(module.main(),0);start.assert_not_called()
            self.assertEqual(ipc.call_args_list[0].args[0][-2:],['open','overview'])
    def test_cold_start_only_when_absent(self):
        with patch.object(module.panel,'shells',return_value=[]),patch.object(module.panel,'current_shell',side_effect=[None,{'pid':123}]),patch.object(module.shutil,'which',return_value='/qs'),patch.object(module.subprocess,'run') as start,patch.object(module.subprocess,'check_output',side_effect=['','{"opened":true,"loaded":true}']),patch.object(sys,'argv',['pixelrail-control']):
            self.assertEqual(module.main(),0);start.assert_called_once()
            self.assertEqual(start.call_args.args[0],[str(root/'scripts/pixelrail-shell')])
    def test_ipc_failure_does_not_spawn_duplicate(self):
        with patch.object(module.panel,'shells',return_value=[]),patch.object(module.panel,'current_shell',return_value={'pid':123}),patch.object(module.shutil,'which',return_value='/qs'),patch.object(module.subprocess,'run') as start,patch.object(module.subprocess,'check_output',side_effect=subprocess.CalledProcessError(1,'qs')),patch.object(sys,'argv',['pixelrail-control']):
            with self.assertRaises(subprocess.CalledProcessError):module.main()
            start.assert_not_called()
if __name__=='__main__':unittest.main()
