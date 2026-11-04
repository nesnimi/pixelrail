"""Run with python3 from repository root; no real launcher or external writes."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path.cwd()
with tempfile.TemporaryDirectory(dir=root / '.cache') as temp:
    base = Path(temp)
    bin_dir = base / 'bin'
    bin_dir.mkdir()
    log = base / 'calls'
    for name, body in {
        'qs': 'printf "qs:%s\\n" "$*" >> "$CALL_LOG"; exit "${QS_STATUS:-0}"',
        'rofi': 'printf "rofi:%s\\n" "$*" >> "$CALL_LOG"',
        'notify-send': 'printf "notify:%s\\n" "$*" >> "$CALL_LOG"; exit 1',
    }.items():
        p = bin_dir / name
        p.write_text('#!/usr/bin/env bash\n' + body + '\n')
        p.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir) + ':/usr/bin', CALL_LOG=str(log),
               XDG_RUNTIME_DIR=str(base), HOME=str(base), PIXELRAIL_LAUNCHER='auto')
    env.pop('PIXELRAIL_QML', None)
    def run(**updates):
        log.write_text('')
        subprocess.run([str(root / 'scripts/pixelrail-launcher')],
                       env=env | updates, check=True)
        return log.read_text()
    calls = run()
    assert 'call launcher toggle' in calls and 'rofi:' not in calls
    calls = run(PIXELRAIL_LAUNCHER='rofi')
    assert 'call launcher toggle' in calls and 'rofi:' not in calls
    for updates in ({'QS_STATUS':'1'}, {'PIXELRAIL_QML':str(base/'missing.qml')}):
        log.write_text('')
        result = subprocess.run([str(root/'scripts/pixelrail-launcher')],env=env|updates,capture_output=True,text=True)
        assert result.returncode == 1 and 'pixelrail-shell' in result.stderr
        assert 'rofi:' not in log.read_text()
print('Launcher routing and terminal recovery: passed')
