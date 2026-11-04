"""Screenshot backend/routing/cancellation with fake tools, private files only."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
ROOT=Path.cwd()
class Screenshot(unittest.TestCase):
    def test_installed_slurp_without_wayland(self):
        if not Path('/usr/bin/slurp').is_file():self.skipTest('installed slurp unavailable')
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);binary=base/'bin';binary.mkdir()
            for name in ('grim','wl-copy'):
                tool=binary/name;tool.write_text('#!/bin/sh\necho "unexpected capture after failed selector" >&2\nexit 99\n');tool.chmod(0o755)
            env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_PICTURES_DIR=str(base/'Pictures'),WAYLAND_DISPLAY=str(base/'no-such-wayland-socket'),PATH=str(binary)+':/usr/bin')
            result=subprocess.run([str(ROOT/'scripts/pixelrail-shot'),'--capture-worker'],env=env,capture_output=True,text=True,timeout=4)
            self.assertNotEqual(result.returncode,0,'real slurp failure used to be silently reported as cancellation')
            self.assertIn('slurp (exit',result.stderr);self.assertIn('failed to create display',result.stderr)
            self.assertNotIn('unexpected capture',result.stderr);self.assertFalse((base/'Pictures').exists())

    def test_backend_and_ipc(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
            base=Path(tmp);binary=base/'bin';binary.mkdir();runtime=base/'runtime';runtime.mkdir(mode=0o700)
            tool='''#!/usr/bin/env python3
import os,sys,time,json
from pathlib import Path
name=Path(sys.argv[0]).name
with Path(os.environ['SHOT_LOG']).open('a') as f:f.write(json.dumps([name]+sys.argv[1:])+'\\n')
if name=='qs':
 method=sys.argv[-1]
 if method=='state' and os.environ.get('QS_STATE_FAIL') and Path(os.environ['QS_MARKER']).exists():print('fixture IPC state failure',file=sys.stderr);sys.exit(1)
 if method=='capture':
  if os.environ.get('QS_STATE_FAIL'):Path(os.environ['QS_MARKER']).touch()
  print('false' if os.environ.get('QS_BUSY') else 'true')
 else:print(json.dumps({'active':False,'phase':'idle','error':'worker failed' if os.environ.get('QS_WORKER_FAIL') else '', 'outcome':'saved'}))
 sys.exit(int(os.environ.get('QS_FAIL','0')))
if name=='slurp':
 Path(os.environ['SHOT_PID']).write_text(str(os.getpid()))
 if os.environ.get('SELECT')=='cancel':sys.exit(1)
 if os.environ.get('SELECT')=='cancel-message':print('selection cancelled',file=sys.stderr);sys.exit(1)
 if os.environ.get('SELECT')=='error':print('failed to grab keyboard',file=sys.stderr);sys.exit(1)
 if os.environ.get('SELECT')=='wait':
  while True:time.sleep(.02)
 print('10,20 100x80')
if name=='grim':
 if os.environ.get('GRIM_FAIL'):sys.exit(2)
 Path(sys.argv[-1]).write_bytes(b'PNG ORIGINAL BYTES')
if name=='wl-copy':Path(os.environ['SHOT_CLIP']).write_bytes(sys.stdin.buffer.read())
'''
            for name in ('qs','slurp','grim','wl-copy','notify-send'):
                path=binary/name;path.write_text(tool);path.chmod(0o755)
            env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_PICTURES_DIR=str(base/'Картинки с пробелом'),PATH=str(binary)+':/usr/bin',SHOT_LOG=str(base/'log'),SHOT_PID=str(base/'selector.pid'),SHOT_CLIP=str(base/'clip'),QS_MARKER=str(base/'accepted'))
            shot=ROOT/'scripts/pixelrail-shot'
            def run(*args,**extra):return subprocess.run([str(shot),*args],env=env|extra,capture_output=True,text=True,timeout=4)
            self.assertEqual(run().returncode,0);rows=(base/'log').read_text().splitlines();self.assertEqual(len(rows),3);self.assertEqual(json.loads(rows[1])[-3:],['call','screenshot','capture'])
            self.assertNotEqual(run(QS_BUSY='1').returncode,0,'busy/stuck mode must not silently eat a hotkey')
            self.assertNotEqual(run(QS_WORKER_FAIL='1').returncode,0,'failed startup must be reported')
            self.assertEqual(json.loads(run('--status').stdout)['phase'],'idle')
            self.assertEqual(run('--reset').returncode,0)
            lost=run(QS_STATE_FAIL='1');self.assertNotEqual(lost.returncode,0);self.assertIn('IPC state',lost.stderr)
            self.assertEqual(json.loads((base/'log').read_text().splitlines()[-1])[-1],'reset','accepted IPC failure must attempt reset')
            (base/'accepted').unlink()
            lost_busy=run(QS_BUSY='1',QS_STATE_FAIL='1');self.assertNotEqual(lost_busy.returncode,0)
            self.assertEqual(json.loads((base/'log').read_text().splitlines()[-1])[-1],'state','rejected request must not abort an existing selection')
            self.assertEqual(run('--capture-worker').returncode,0);self.assertEqual((base/'clip').read_bytes(),b'PNG ORIGINAL BYTES')
            folder=base/'Картинки с пробелом/Screenshots';before=list(folder.glob('*.png'));self.assertEqual(len(before),1)
            self.assertEqual(run('--capture-worker',SELECT='cancel').returncode,0);self.assertEqual(list(folder.glob('*.png')),before)
            self.assertEqual(run('--capture-worker',SELECT='cancel-message').returncode,0);self.assertEqual(list(folder.glob('*.png')),before)
            error=run('--capture-worker',SELECT='error');self.assertNotEqual(error.returncode,0);self.assertIn('failed to grab keyboard',error.stderr)
            missing=run('--capture-worker','--handshake')
            self.assertNotEqual(missing.returncode,0);self.assertIn('handshake',missing.stderr)
            self.assertNotEqual(run('--capture-worker',GRIM_FAIL='1').returncode,0);self.assertEqual(list(folder.glob('*.png')),before)
            self.assertEqual(run(QS_FAIL='1').returncode,0);self.assertEqual(len(list(folder.glob('*.png'))),2,'collision must not overwrite earlier screenshot')
            for sig in (signal.SIGTERM,signal.SIGKILL):
                (base/'selector.pid').unlink(missing_ok=True)
                child=subprocess.Popen([str(shot),'--capture-worker'],env=env|{'SELECT':'wait'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                deadline=time.monotonic()+3
                while not (base/'selector.pid').exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue((base/'selector.pid').exists());pid=int((base/'selector.pid').read_text())
                os.kill(child.pid,sig);child.wait(timeout=4)
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    try:state=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[0]
                    except OSError:break
                    if state=='Z':break
                    time.sleep(.02)
                else:self.fail('Owned selector outlived capture worker')
if __name__=='__main__':unittest.main()
