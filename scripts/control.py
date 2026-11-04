#!/usr/bin/env python3
"""Open/toggle the native Control Center via the current owned qs instance."""
import json
import shutil
import subprocess
import sys
import time
import panel

def main():
    row=panel.current_shell(panel.shells())
    if not row:
        subprocess.run([str(panel.ROOT/'scripts/pixelrail-shell')],check=True,timeout=15)
        row=panel.current_shell(panel.shells())
    if not row:raise RuntimeError('PixelRail Control IPC недоступен')
    section=sys.argv[1] if len(sys.argv)>1 else 'overview'
    if section not in ('overview','wifi','volume','notifications','battery','profile','bluetooth','settings'):raise ValueError('Неизвестный раздел')
    binary=shutil.which('qs') or shutil.which('quickshell')
    def call(method,*args):return subprocess.check_output([binary,'ipc','--pid',str(row['pid']),'call','control',method,*args],text=True,timeout=3).strip()
    call('open',section)
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        value=json.loads(call('state'))
        if value.get('error'):raise RuntimeError(value['error'])
        if (not value.get('opened') and not value.get('pending')) or value.get('loaded'):return 0
        time.sleep(.04)
    raise RuntimeError('Control Center не подтвердил загрузку')
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,panel.PanelError) as error:
        print('PixelRail: '+str(error)+'; восстановление: pixelrail-shell / rollback',file=sys.stderr);sys.exit(1)
