"""Use the installed Hyprland parser, never reload the live compositor."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
root=Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as temporary:
    base=Path(temporary);config=base/'.config/hypr';config.mkdir(parents=True)
    for file in (root/'hypr').glob('*.lua'):shutil.copy2(file,config/file.name)
    state=base/'.cache/pixelrail/profile';state.parent.mkdir(parents=True)
    runtime=base/'runtime';runtime.mkdir(mode=0o700)
    for profile in ('battery','performance'):
        state.write_text(profile)
        env=dict(os.environ,HOME=str(base),XDG_CONFIG_HOME=str(base/'.config'),XDG_CACHE_HOME=str(base/'.cache'),XDG_STATE_HOME=str(base/'.local/state'),XDG_RUNTIME_DIR=str(runtime))
        env.pop('HYPRLAND_INSTANCE_SIGNATURE',None)
        result=subprocess.run(['Hyprland','--verify-config','-c',str(config/'hyprland.lua')],env=env,capture_output=True,text=True,timeout=15)
        print(profile,result.returncode,result.stdout[-1800:],result.stderr[-600:])
        assert result.returncode==0 and 'config ok' in result.stdout,profile
    broken=config/'broken.lua'
    broken.write_text((config/'hyprland.lua').read_text().replace('bezier = "pixelrail"','curve = "pixelrail"'))
    result=subprocess.run(['Hyprland','--verify-config','-c',str(broken)],env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode!=0 or 'config ok' not in result.stdout,'validator accepted the old broken schema'
print('Actual Hyprland 0.57 parser: Battery/Performance passed; old curve schema rejected')
