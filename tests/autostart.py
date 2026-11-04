"""Run the actual session entrypoint with fake helpers; no live processes/services."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);scripts=base/'scripts';scripts.mkdir();binary=base/'bin';binary.mkdir();log=base/'calls'
    shutil.copy2(ROOT/'scripts/pixelrail-start',scripts/'pixelrail-start')
    stub='''#!/usr/bin/env python3
import os,sys
from pathlib import Path
with Path(os.environ['TEST_LOG']).open('a') as stream:stream.write(Path(sys.argv[0]).name+'\\n')
if Path(sys.argv[0]).name=='pixelrail-shell':sys.exit(int(os.environ.get('SHELL_FAIL','0')))
'''
    for directory,names in [(scripts,['pixelrail-shell','pixelrail-panel','pixelrail-notifications','pixelrail-clipboard-watch']),(binary,['pgrep','cliphist','wl-paste'])]:
        for name in names:
            path=directory/name;path.write_text('#!/bin/sh\nexit 0\n' if name=='pgrep' else stub);path.chmod(0o755)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(base/'runtime'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),PATH=str(binary)+':/usr/bin',TEST_LOG=str(log))
    subprocess.run([str(scripts/'pixelrail-start')],env=env,check=True,timeout=5)
    assert log.read_text().splitlines()==['pixelrail-shell','pixelrail-clipboard-watch']
    log.write_text('');subprocess.run([str(scripts/'pixelrail-start')],env=env|{'SHELL_FAIL':'1'},check=True,timeout=5)
    assert log.read_text().splitlines()==['pixelrail-shell','pixelrail-panel','pixelrail-notifications','pixelrail-clipboard-watch']
source=(ROOT/'hypr/hyprland.lua').read_text();assert source.count('pixelrail-start')==1
start=(ROOT/'scripts/pixelrail-start').read_text()
for forbidden in ('pipewire','wireplumber','systemctl','sudo'):assert forbidden not in start.lower()
print('Actual autostart routing: one primary entrypoint, fallback only after failure, watcher path, no PipeWire/system service startup: PASS')
