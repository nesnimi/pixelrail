import os
from pathlib import Path
import subprocess
import tempfile

root = Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base = Path(tmp); binary = base/'bin'; binary.mkdir(); log = base/'calls'
    for name, body in {
        'qs':'printf "qs:%s\\n" "$*" >> "$CALL_LOG"; if [[ "$1" == list ]]; then printf \'[{"config_path":"%s","id":"fixture","pid":1000000}]\\n\' "$TEST_CONFIG"; elif [[ "$*" == *"call menus status"* ]]; then echo unloaded; elif [[ "$1" == ipc ]]; then echo "${IPC_RESULT:-true}"; fi; exit "${QS_STATUS:-0}"',
        'rofi':'printf "rofi:%s\\n" "$*" >> "$CALL_LOG"',
        'notify-send': 'printf "notify:%s\\n" "$*" >> "$CALL_LOG"; exit 1',
    }.items():
        p = binary/name; p.write_text('#!/usr/bin/env bash\n'+body+'\n'); p.chmod(0o755)
    env = dict(os.environ, PATH=str(binary)+':/usr/bin', CALL_LOG=str(log),
               XDG_RUNTIME_DIR=str(base), HOME=str(base), WAYLAND_DISPLAY='fixture', TEST_CONFIG=str(root/'quickshell/shell.qml'), PIXELRAIL_UI='auto')
    env.pop('PIXELRAIL_QML', None)
    for mode in ('keys','clipboard','command','windows','controls','power','wallpaper','media','emoji','session'):
        log.write_text('')
        subprocess.run([str(root/'scripts/pixelrail-menu'),mode],env=env,check=True)
        calls = log.read_text()
        expected = 'power' if mode == 'session' else mode
        assert 'call menus open '+expected in calls and 'rofi:' not in calls
    # Old entrypoints remain safe for callers holding paths from previous releases.
    for relative, expected in (
        ('pixelrail-launcher-rofi', 'call launcher toggle'),
        ('fallback/pixelrail-keys', 'call menus open keys'),
        ('fallback/pixelrail-clipboard', 'call menus open clipboard'),
        ('fallback/pixelrail-power', 'call menus open power'),
        ('fallback/pixelrail-end4', 'call menus open keys'),
    ):
        log.write_text('')
        subprocess.run([str(root/'scripts'/relative)],env=env,check=True)
        assert expected in log.read_text() and 'rofi:' not in log.read_text()
    # Retired backend variables cannot bypass native IPC.
    subprocess.run([str(root/'scripts/pixelrail-menu'),'command'],env=env|{'PIXELRAIL_UI':'rofi'},check=True)
    for changes in ({'IPC_RESULT':'false'}, {'PIXELRAIL_QML':str(base/'absent')}):
        for mode in ('keys','clipboard','command','windows','controls','power','wallpaper','media','emoji','session'):
            log.write_text('')
            result = subprocess.run([str(root/'scripts/pixelrail-menu'),mode],env=env|changes,capture_output=True,text=True)
            assert result.returncode == 1 and 'pixelrail-shell' in result.stderr
            assert 'rofi:' not in log.read_text()
    result = subprocess.run([str(root/'scripts/pixelrail-menu'),'invalid'],env=env,capture_output=True)
    assert result.returncode == 2
    # A PATH without either Quickshell binary, Rofi, or notifications.
    isolated = base/'isolated'; isolated.mkdir()
    for name in ('bash','dirname','readlink'):
        (isolated/name).symlink_to('/usr/bin/'+name)
    missing_env = env | {'PATH':str(isolated)}
    for script in ('pixelrail-menu','pixelrail-launcher','pixelrail-shell'):
        result = subprocess.run([str(root/'scripts'/script)],env=missing_env,capture_output=True,text=True)
        assert result.returncode == 1 and 'pixelrail-shell' in result.stderr
    # Missing parent directories and failed daemon startup also explain recovery.
    for changes in ({'PIXELRAIL_QML':str(base/'missing/parent/shell.qml')}, {'QS_STATUS':'1'}):
        log.write_text('')
        result = subprocess.run([str(root/'scripts/pixelrail-shell')],env=env|changes,capture_output=True,text=True)
        assert result.returncode == 1 and 'Super+Return' in result.stderr and 'pixelrail-shell' in result.stderr
        assert 'rofi:' not in log.read_text()
    log.write_text('')
    subprocess.run([str(root/'scripts/pixelrail-shell')],env=env,check=True)
    assert 'call menus status' in log.read_text()
print('All menu routes, terminal recovery and shell-start arguments: passed')
