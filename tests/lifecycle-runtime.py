"""Real qs registry/IPC transitions using generated surface-free QML and isolated HOME."""
import os
from pathlib import Path
import shutil
import signal
import time
import sys
import tempfile

sys.path.insert(0,str(Path.cwd()/'scripts'))
from lifecycle import LifecycleError, Shell, locked

root=Path.cwd()
if not (shutil.which('qs') or shutil.which('quickshell')): raise SystemExit('Quickshell required')
with tempfile.TemporaryDirectory(dir=root/'.cache') as temporary:
    base=Path(temporary); runtime=base/'runtime'; runtime.mkdir(mode=0o700)
    original=dict(os.environ)
    wayland=original.get('WAYLAND_DISPLAY','')
    if not wayland: raise SystemExit('Wayland required')
    if not wayland.startswith('/'): wayland=str(Path(original['XDG_RUNTIME_DIR'])/wayland)
    os.environ.update(HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CACHE_HOME=str(base/'cache'),
                      XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),
                      WAYLAND_DISPLAY=wayland,QT_QPA_PLATFORM='wayland')
    content='import Quickshell\nimport Quickshell.Io\nShellRoot { IpcHandler { target: "menus"; function status(): string { return "unloaded"; } } }\n'
    paths=[]
    for name in ('old','new','foreign','bad'):
        folder=base/name; folder.mkdir(); path=folder/'shell.qml'
        path.write_text(content if name!='bad' else 'not valid QML')
        paths.append(path)
    old,new,foreign,bad=paths
    own=Shell({str(old),str(new),str(bad)})
    outsider=Shell({str(foreign)})
    try:
        with locked(base):
            unrelated,_=outsider.prepare(foreign)
            first,_=own.prepare(old)
            second,_=own.prepare(new)
            assert own.ready(first) and own.ready(second)
            own.retire(second)
            assert [own.key(row) for row in own.instances()]==[own.key(second)]
            assert outsider.ready(unrelated)
            repeated,_=own.prepare(new); assert own.key(repeated)==own.key(second)
            try: own.prepare(bad)
            except LifecycleError: pass
            else: raise AssertionError('Invalid QML unexpectedly became ready')
            assert own.ready(second) and outsider.ready(unrelated)
            # Abrupt crash of this fixture only; never a user-session process.
            assert Path(second['config_path']).is_relative_to(base)
            assert any(own.key(row)==own.key(second) for row in own.instances())
            os.kill(second['pid'],signal.SIGKILL)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline and any(own.key(row)==own.key(second) for row in own.instances()):time.sleep(.05)
            recovered,_=own.prepare(new);assert own.ready(recovered) and own.key(recovered)!=own.key(second)
            restored,_=own.prepare(old); own.retire(restored)
            assert own.ready(restored) and outsider.ready(unrelated)
    finally:
        own.retire()
        outsider.retire()  # Test-owned foreign fixture only; not used by deployment.
        os.environ.clear(); os.environ.update(original)
print('Real Quickshell: release switch, exact instance cleanup, repeat start, invalid QML, abrupt crash/recovery, rollback, foreign instance preserved: passed')
