"""Opt-in actual Hyprland 0.57 check: focus only the already active targets.
No configuration writes, empty workspace creation or application launches.
"""
import json
import re
import subprocess

def query(name):
    return json.loads(subprocess.check_output(['hyprctl','-j',name],text=True,timeout=3))

def state():
    return query('activeworkspace')['id'],query('activewindow').get('address','')

before=state()
monitor=next(value for value in query('monitors') if value.get('focused'))['name']
status=query('status')
assert status.get('configProvider','').lower()=='lua',status
quote=lambda value:json.dumps(str(value),ensure_ascii=False)
commands=['hl.dispatch(hl.dsp.focus({ monitor = '+quote(monitor)+' })); hl.dispatch(hl.dsp.focus({ workspace = '+quote(before[0])+' }))']
if re.fullmatch(r'0x[0-9a-fA-F]+',before[1]):
    commands.append('hl.dispatch(hl.dsp.focus({ window = '+quote('address:'+before[1])+' }))')
assert state()==before,'Focus changed during inspection; run again without interacting'
for command in commands:
    result=subprocess.run(['hyprctl','eval',command],capture_output=True,text=True,timeout=3)
    assert result.returncode==0 and result.stdout.strip()=='ok',result.stdout+result.stderr
assert state()==before,'Unexpected focus change'
print('Actual Hyprland Lua: monitor/workspace/window dispatch accepted (ok); active workspace/window unchanged')
