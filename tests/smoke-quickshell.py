"""Hidden-window runtime/IPC check; use an installed qs or QS_BINARY.
No keybind reload, GUI toggle, application execution or system installation.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

root = Path.cwd()
binary = os.environ.get('QS_BINARY') or shutil.which('qs') or shutil.which('quickshell')
if not binary:
    raise SystemExit('Quickshell absent; set QS_BINARY or run after manual installation.')
wayland = os.environ.get('WAYLAND_DISPLAY', '')
if not wayland:
    raise SystemExit('A Wayland session is required (PanelWindow has no offscreen backend).')
if not wayland.startswith('/'):
    wayland = str(Path(os.environ['XDG_RUNTIME_DIR']) / wayland)
with tempfile.TemporaryDirectory(dir=root / '.cache') as tmp:
    base = Path(tmp)
    runtime = base / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, WAYLAND_DISPLAY=wayland, QT_QPA_PLATFORM='wayland',
               XDG_RUNTIME_DIR=str(runtime), PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'], XDG_CACHE_HOME=str(base / 'cache'),
               XDG_CONFIG_HOME=str(base / 'config'), HOME=str(base), XDG_STATE_HOME=str(base/'state'), XDG_DATA_HOME=str(base/'data'))
    shutil.copytree(root/'quickshell',base/'quickshell')
    (base/'scripts').symlink_to(root/'scripts',target_is_directory=True)
    page=base/'quickshell/shell.qml';page.write_text(page.read_text().replace('suppressed:control.opened','suppressed:true || control.opened'))
    config = str(page)
    with (base / 'log').open('w+') as log:
        process = subprocess.Popen([binary, '-p', config, '--no-color'], env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise AssertionError('Quickshell exited during startup')
                result = subprocess.run([binary, 'ipc', '-p', config, 'call', 'launcher', 'hide'],
                                        env=env, capture_output=True, timeout=2)
                if result.returncode == 0:
                    break
                time.sleep(.1)
            else:
                raise AssertionError('IPC did not become ready')
            time.sleep(.2)
        finally:
            process.terminate()
            process.wait(timeout=5)
        log.seek(0)
        output = log.read()
        print(output)
        assert 'Configuration Loaded' in output
        for marker in ('ERROR', 'Unable to assign', 'ReferenceError', 'TypeError', 'Binding loop'):
            assert marker not in output, marker
print('Hidden Quickshell load + IPC hide: passed')
