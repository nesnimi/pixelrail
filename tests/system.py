"""Backend args/errors and multimedia routing: fake tools only, no hardware writes."""
import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('desktop_backend',ROOT/'scripts/desktop.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class Backend(unittest.TestCase):
    def test_parse_actual_and_unavailable(self):
        result=subprocess.CompletedProcess([],0,'intel_backlight,backlight,400,40%,1000\n','')
        self.assertEqual(d.parse_brightness(result)['percent'],40)
        for output in ('','bad','intel,backlight,1,0%,0','intel,leds,1,10%,10','intel,backlight,-1,10%,10'):
            result.stdout=output;self.assertFalse(d.parse_brightness(result)['available'])
        result.returncode=1;result.stderr='permission denied';self.assertIn('permission denied',d.parse_brightness(result)['error'])
    def test_set_uses_machine_readable_command_without_regressed_min_flag(self):
        result=subprocess.CompletedProcess([],0,'intel_backlight,backlight,1,0%,1000\n','')
        stream=io.StringIO()
        with patch.object(sys,'argv',['helper','set-brightness','0']),patch.object(d.subprocess,'run',return_value=result) as run,redirect_stdout(stream):self.assertEqual(d.main(),0)
        self.assertEqual(run.call_count,1);self.assertEqual(run.call_args.args[0],['brightnessctl','-m','-c','backlight','set','0%'])
        self.assertEqual(json.loads(stream.getvalue())['percent'],0)
    def test_permission_error_is_reported_not_assumed_success(self):
        stream=io.StringIO()
        with patch.object(sys,'argv',['helper','set-brightness','42']),patch.object(d.subprocess,'run',side_effect=PermissionError('denied')),redirect_stdout(stream):self.assertEqual(d.main(),1)
        self.assertFalse(json.loads(stream.getvalue())['available'])
    def test_audio_server_readback_uses_cubic_channels_and_device_route(self):
        node={'id':11,'type':'PipeWire:Interface:Node','info':{'props':{},'params':{'Props':[{'channelVolumes':[.125,.125],'mute':True}]}}}
        with patch.object(d.shutil,'which',return_value='/pw-dump'),patch.object(d.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps([node]),'')):
            value=d.audio_state('11');self.assertAlmostEqual(value['volume'],.5);self.assertTrue(value['muted'])
        node['info']['props']={'device.id':7,'card.profile.device':0}
        device={'id':7,'info':{'params':{'Route':[{'device':0,'props':{'channelVolumes':[.008,.008],'mute':False}}]}}}
        replies=[subprocess.CompletedProcess([],0,json.dumps([row]),'') for row in (node,device)]
        with patch.object(d.shutil,'which',return_value='/pw-dump'),patch.object(d.subprocess,'run',side_effect=replies) as run:
            value=d.audio_state('11');self.assertAlmostEqual(value['volume'],.2);self.assertFalse(value['muted']);self.assertEqual(run.call_count,2)
        with patch.object(d.shutil,'which',return_value=None):self.assertFalse(d.audio_state('11')['available'])
        with self.assertRaises(ValueError):d.audio_state('11;bad')
    def test_key_ipc_and_tool_fallback(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);binary=base/'bin';binary.mkdir();log=base/'calls'
            fake=binary/'qs';fake.write_text('''#!/usr/bin/env python3
import os,sys,json
from pathlib import Path
with Path(os.environ['TEST_LOG']).open('a') as stream:stream.write(json.dumps([Path(sys.argv[0]).name]+sys.argv[1:])+'\\n')
name=Path(sys.argv[0]).name
if name=='qs':
 print(os.environ.get('TEST_REPLY','true'));sys.exit(int(os.environ.get('TEST_EXIT','0')))
''');fake.chmod(0o755)
            for name in ('wpctl','brightnessctl'):(binary/name).symlink_to(fake)
            env=dict(os.environ,HOME=str(base),PATH=str(binary)+':/usr/bin',TEST_LOG=str(log),PIXELRAIL_QML=str(base/'shell.qml'))
            script=ROOT/'scripts/pixelrail-system'
            for action in ('volume-up','volume-down','volume-mute','brightness-up','brightness-down'):
                log.unlink(missing_ok=True);result=subprocess.run([str(script),action],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                rows=[json.loads(line) for line in log.read_text().splitlines()];self.assertEqual(len(rows),1);self.assertEqual(rows[0][-3:],['system','action',action])
            log.unlink();result=subprocess.run([str(script),'volume-up'],env=env|{'TEST_REPLY':'false'},capture_output=True,text=True)
            self.assertEqual(result.returncode,1);self.assertEqual(len(log.read_text().splitlines()),1)
            for action,expected in [('volume-up',['wpctl','set-volume','-l','1.0','@DEFAULT_AUDIO_SINK@','5%+']),('volume-down',['wpctl','set-volume','@DEFAULT_AUDIO_SINK@','5%-']),('volume-mute',['wpctl','set-mute','@DEFAULT_AUDIO_SINK@','toggle']),('brightness-down',['brightnessctl','-c','backlight','set','5%-'])]:
                log.unlink();result=subprocess.run([str(script),action],env=env|{'TEST_EXIT':'1'},capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);rows=[json.loads(line) for line in log.read_text().splitlines()];self.assertEqual(rows[-1],expected)
            log.unlink();result=subprocess.run([str(script),'malicious'],env=env,capture_output=True,text=True);self.assertEqual(result.returncode,2);self.assertFalse(log.exists())
if __name__=='__main__':unittest.main()
