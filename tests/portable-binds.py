"""Registration only: verify original hotkey argv with spaces, Unicode and shell chars."""
import json
import os
from pathlib import Path
import shlex
import subprocess
root=Path.cwd()
stub=(root/'tests/binds.lua').read_text().split("dofile('hypr/pixelrail-end4-keys.lua')",1)[0]
for home in ["/fixture/Другой пользователь", "/fixture/user'quote$`name"]:
    source=stub+'\nlocal getenv=os.getenv;os.getenv=function(name) if name=="HOME" then return '+json.dumps(home,ensure_ascii=False)+' end return getenv(name) end\n'
    source+='''dofile('hypr/pixelrail-end4-keys.lua')
for _,key in ipairs({'SUPER+A','SUPER+SHIFT+S','SUPER+R','XF86MONBRIGHTNESSUP'}) do print(binds[key].action.command) end
events['input.keyboard.key'](133,0,1);events['input.keyboard.key'](133,0,0);binds['SUPER+SUPER_L'].action()
print(launches[1])
'''
    result=subprocess.run(['lua','-'],input=source,text=True,capture_output=True,timeout=5,check=True)
    expected=[['pixelrail-control'],['pixelrail-shot'],['pixelrail-menu','command'],['pixelrail-system','brightness-up'],['pixelrail-launcher']]
    for line,arguments in zip(result.stdout.splitlines(),expected):
        assert shlex.split(line)==[home+'/.local/bin/'+arguments[0],*arguments[1:]],line
print('Portable bind paths: argv preserved, Unicode/spaces/quotes/dollar/backtick, Super and screenshot route: PASS')
