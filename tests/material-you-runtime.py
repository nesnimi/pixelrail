"""Actual Quickshell singleton/FileView atomic updates; no mapped desktop surfaces."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
sys.path.insert(0,str(Path.cwd()/"scripts"))
from material_you import contrast
import time

root=Path.cwd(); qs=shutil.which('qs') or shutil.which('quickshell')
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp); runtime=base/'runtime';runtime.mkdir(mode=0o700)
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),
             XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),
             QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'))
    env.pop('WAYLAND_DISPLAY',None)
    helper=root/'scripts/pixelrail-theme'
    def cli(*args):
        p=subprocess.run([str(helper),*args],env=env,capture_output=True,text=True,timeout=10)
        assert p.returncode==0,p.stdout+p.stderr
        return json.loads(p.stdout)
    cli('sync')
    palette=base/'cache/pixelrail/theme/palette.json'; settings=base/'config/pixelrail/theme.json'
    first=json.loads(palette.read_text())
    cli('accent','#ee6633');second=json.loads(palette.read_text());cli('accent','reset')
    for folder in ('theme','ui','assets'):(base/folder).symlink_to(root/'quickshell'/folder,target_is_directory=True)
    config=base/'shell.qml';env['PIXELRAIL_QML']=str(config)
    config.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "THEME" as Theme
import "theme/Fallback.js" as Fallback
ShellRoot {
    property int paletteAssignments:0
    Connections {target:Theme.ThemeManager;function onSchemesChanged(){paletteAssignments++;}}
    Theme.Palette { id: colors }
    IpcHandler {
        target: "probe"
        function snapshot(): string { return JSON.stringify({paletteAssignments:paletteAssignments,mode: Theme.ThemeManager.mode,
            configured: Theme.ThemeManager.configuredMode, primary: String(colors.primary), surface:String(colors.surfaceContainer),
            roles:{primary:String(colors.primary),onPrimary:String(colors.primaryText),
                primaryContainer:String(colors.primaryContainer),onPrimaryContainer:String(colors.primaryContainerText),
                secondary:String(colors.secondary),onSecondary:String(colors.secondaryText),
                secondaryContainer:String(colors.selected),onSecondaryContainer:String(colors.selectedText),
                tertiary:String(colors.tertiary),onTertiary:String(colors.tertiaryText),
                background:String(colors.background),onBackground:String(colors.backgroundText),
                surface:String(colors.surface),onSurface:String(colors.text),surfaceVariant:String(colors.surfaceVariant),
                onSurfaceVariant:String(colors.muted),error:String(colors.error),onError:String(colors.errorText)},
            pairs:[
                [colors.background,colors.text],[colors.background,colors.muted],
                [colors.surfaceContainer,colors.text],[colors.surfaceContainer,colors.muted],
                [colors.surfaceHigh,colors.text],[colors.surfaceHigh,colors.muted],
                [colors.selected,colors.selectedText],
                [Qt.tint(colors.surfaceContainer,Qt.alpha(colors.accent,0.08)),colors.text],
                [Qt.tint(colors.surfaceContainer,Qt.alpha(colors.accent,0.08)),colors.muted],
                [Qt.tint(colors.surfaceContainer,Qt.alpha(colors.accent,0.10)),colors.muted],
                [Qt.tint(colors.selected,Qt.alpha(colors.accent,0.18)),colors.selectedText],
                [colors.primary,colors.primaryText],[colors.primaryContainer,colors.primaryContainerText],
                [colors.surfaceVariant,colors.surfaceVariantText],
                [colors.background,colors.accent],[colors.surfaceHigh,colors.accent],
                [colors.background,colors.error]
            ].map(pair=>pair.map(value=>String(value))),
            hint:Qt.styleHints.colorScheme, light:Qt.ColorScheme.Light, dark:Qt.ColorScheme.Dark, busy:Theme.ThemeManager.busy, error:Theme.ThemeManager.lastError}); }
        function valid(value: string): bool { return Theme.ThemeManager.valid(JSON.parse(value)); }
        function fallback(): void { Theme.ThemeManager.schemes = Fallback.schemes; }
        function systemMode(value: int): void { Qt.styleHints.colorScheme = value; }
    }
}
'''.replace('THEME','theme'))
    def ipc(method,*args):
        p=subprocess.run([qs,'ipc','-p',str(config),'call','probe',method,*map(str,args)],env=env,capture_output=True,text=True,timeout=3)
        if p.returncode: raise RuntimeError(p.stderr)
        return p.stdout.strip()
    measured=[]
    def wait(predicate):
        end=time.monotonic()+6
        while time.monotonic()<end:
            try:
                data=json.loads(ipc('snapshot'))
                for background,foreground in data['pairs']:
                    ratio=contrast(background,foreground)
                    measured.append(ratio)
                    assert ratio>=4.5,(data['mode'],background,foreground,ratio)
                for background,foreground in (('surface','onSurface'),('surfaceVariant','onSurfaceVariant'),
                        ('primary','onPrimary'),('primaryContainer','onPrimaryContainer'),
                        ('secondaryContainer','onSecondaryContainer'),('secondary','onSecondary'),('tertiary','onTertiary')):
                    assert contrast(data['roles'][background],data['roles'][foreground])>=4.5,(background,foreground,data)
                if predicate(data): return data
            except (RuntimeError,json.JSONDecodeError): pass
            time.sleep(.025)
        raise AssertionError('Theme update timeout: '+str(data if 'data' in locals() else 'unavailable'))
    def atomic(path,data):
        temporary=path.with_suffix('.new');temporary.write_text(json.dumps(data) if not isinstance(data,str) else data);temporary.replace(path)
    with (base/'log').open('w+') as log:
        process=subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait(lambda d:not d['busy'] and d['primary']==first['schemes']['dark']['primary'])
            assert wait(lambda d:not d['busy'])['roles']=={key:first['schemes']['dark'][key] for key in wait(lambda d:not d['busy'])['roles']}
            # Repeated rename must reattach watches to every new inode.
            for value in (second,first,second,first,second,first):
                atomic(palette,value)
                wait(lambda d:d['primary']==value['schemes']['dark']['primary'])
            atomic(palette,'{"incomplete":')
            wait(lambda d:'палитра' in d['error'])
            assert json.loads(ipc('snapshot'))['primary']==first['schemes']['dark']['primary']
            invalid=json.loads(json.dumps(first));invalid['schemes']['dark']['onSurface']='#111318'
            assert ipc('valid',json.dumps(invalid['schemes']))=='false'
            atomic(palette,invalid)
            wait(lambda d:'палитра' in d['error'])
            assert json.loads(ipc('snapshot'))['roles']['onSurface']==first['schemes']['dark']['onSurface']
            atomic(palette,first)
            wait(lambda d:d['primary']==first['schemes']['dark']['primary'])
            time.sleep(.15)
            before_assignments=json.loads(ipc('snapshot'))['paletteAssignments']
            for _ in range(5):
                atomic(palette,palette.read_text());time.sleep(.08)
            assert json.loads(ipc('snapshot'))['paletteAssignments']==before_assignments,'unchanged palette caused new schemes/binding updates'
            for mode in ('light','dark','auto','light','dark'):
                atomic(settings,{'mode':mode,'accent':None})
                wait(lambda d:d['configured']==mode and not d['busy'])
                if mode!='auto':
                    actual=wait(lambda d:d['mode']==mode)
                    assert actual['roles']=={key:first['schemes'][mode][key] for key in actual['roles']}
            atomic(settings,{'mode':'auto','accent':None});wait(lambda d:d['configured']=='auto' and not d['busy'])
            # Offscreen Qt has no platform theme and ignores setColorScheme;
            # verify documented Unknown -> dark fallback without claiming desktop coverage.
            assert json.loads(ipc('snapshot'))['hint']==0
            wait(lambda d:d['mode']=='dark')
            cli('accent','#ee6633');wait(lambda d:d['primary']==second['schemes']['dark']['primary'] and not d['busy'])
            cli('accent','reset');wait(lambda d:d['primary']==first['schemes']['dark']['primary'] and not d['busy'])
            for seed in ('#007AFF','#808080'):
                cli('accent',seed)
                generated=json.loads(palette.read_text())
                for configured in ('light','dark','auto'):
                    cli('mode',configured)
                    effective='dark' if configured=='auto' else configured
                    actual=wait(lambda d:d['mode']==effective and not d['busy'] and d['primary']==generated['schemes'][effective]['primary'])
                    assert actual['roles']=={key:generated['schemes'][effective][key] for key in actual['roles']}
            cli('accent','reset');wait(lambda d:d['primary']==first['schemes']['dark']['primary'] and not d['busy'])
            ipc('fallback');wait(lambda d:not d['busy'])
            assert process.poll() is None
            cli('mode','light');wait(lambda d:d['mode']=='light' and not d['busy'])
            saved=palette.read_bytes()
            process.terminate();process.wait(timeout=3)
            process=subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
            wait(lambda d:d['mode']=='light' and not d['busy'] and d['primary']==first['schemes']['light']['primary'])
            assert palette.read_bytes()==saved
        finally:
            process.terminate();process.wait(timeout=3)
            log.seek(0);output=log.read();print(output)
    for marker in ('TypeError','ReferenceError','Binding loop','Unable to assign','Failed to load configuration'):
        assert marker not in output,marker
print('Minimum measured text/state contrast: %.2f:1' % min(measured))
print('Material You runtime: repeated atomic updates, retained invalid palette, reactive modes/accent and Auto Unknown fallback, restart persistence and single live process passed')
