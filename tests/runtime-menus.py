"""Real Quickshell/IPC/Process integration with hidden panels and fake system tools.
All generated files and desktop entries live inside the repository .cache.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import struct
import zlib
import signal
import shlex
import time
import sys
sys.path.insert(0,str(Path.cwd()/"scripts"))
from material_you import contrast

root = Path.cwd()
qs = shutil.which('qs') or shutil.which('quickshell')
if not qs: raise SystemExit('Quickshell required')
wayland = os.environ.get('WAYLAND_DISPLAY', '')
if not wayland: raise SystemExit('Wayland session required')
if not wayland.startswith('/'): wayland = str(Path(os.environ['XDG_RUNTIME_DIR'])/wayland)

with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base = Path(tmp); runtime = base/'runtime'; runtime.mkdir(mode=0o700)
    binary = base/'bin'; binary.mkdir(); config = base/'shell.qml'
    calls = base/'calls'; copied = base/'copied'; app_log = base/'apps'
    fake = '''#!/usr/bin/env python3
import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
with open(os.environ['TEST_CALLS'],'a') as f: f.write(json.dumps([name]+sys.argv[1:])+"\\n")
if name=='rofi': sys.exit(99)
elif name=='hyprctl':
    if sys.argv[1:]==['-j','binds']: print(json.dumps([{'key':'Q','modmask':64,'description':'Закрыть окно'}]))
    elif sys.argv[1:]==['-j','clients']: print(json.dumps([{'address':'0xabc','title':'Тестовое окно','class':'fixture','workspace':{'name':'1'}}]))
    elif sys.argv[1:]==['-j','activewindow']: print('{"address":"0xabc"}')
    else: print('ok')
elif name=='cliphist':
    if sys.argv[1]=='list':
        for key in range(9,39): print(str(key)+'\\t[[ binary data 93 B png 16x16 ]]')
        print('7\\tИстория теста')
    else:
        key=sys.stdin.buffer.read().split(b'\\t')[0].strip()
        sys.stdout.buffer.write(pathlib.Path(os.environ['TEST_IMAGE']).read_bytes() if key.isdigit() and int(key)>=9 else b'fixture\\x00bytes')
elif name=='swaybg':
    import time
    while True: time.sleep(1)
elif name=='wl-copy': pathlib.Path(os.environ['TEST_COPY']).write_bytes(sys.stdin.buffer.read())
elif name in ('pixelrail-test-command','pixelrail-test-app','kitty'):
    with open(os.environ['TEST_APPS'],'a') as f: f.write(name+"\\n")
'''
    for name in ('hyprctl','cliphist','wl-copy','systemctl','uwsm','playerctl','wpctl','pkill','swaybg',
                 'hyprlock','rofi','pixelrail-test-command','pixelrail-test-app','kitty'):
        p = binary/name; p.write_text(fake); p.chmod(0o755)
    data = base/'data'; apps = data/'applications'; apps.mkdir(parents=True)
    for terminal in (False,True):
        name = 'pixelrail-fixture-terminal' if terminal else 'pixelrail-fixture-app'
        (apps/(name+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+name+'\nExec='+str(binary/'pixelrail-test-app')+'\nTerminal='+str(terminal).lower()+'\n')
    def image(path):
        path.parent.mkdir(parents=True,exist_ok=True)
        def chunk(kind,data): return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',16,16,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x80\x90\xb0'*16)*16))+chunk(b'IEND',b''))
    pictures = base/'Pictures'; pictures.mkdir()
    for number in range(120): image(pictures/'Wallpapers'/f'Фото {number:03}.png')
    downloaded=base/'Downloads/Скачанные обои # с длинным именем.png'; image(downloaded)
    image(pictures/'Screenshots/fixture.png')
    for folder in ('components','modules','theme','ui','assets'):
        (base/folder).symlink_to(root/'quickshell'/folder, target_is_directory=True)
    backend_wrapper=base/'menu-data'
    backend_wrapper.write_text('#!/bin/sh\nexport WAYLAND_DISPLAY=wallpaper-fixture\nexec '+shlex.quote(str(root/'scripts/pixelrail-menu-data'))+' "$@"\n')
    backend_wrapper.chmod(0o755)
    # Instance-level visible overrides prevent any surface from mapping or taking focus.
    source = (root/'quickshell/shell.qml').read_text()
    source = source.replace('Launcher { id: launcher }','Launcher { id: launcher; visible: false }')
    source = source.replace('MenuPanel {', 'MenuPanel {\nvisible: false\nbackend: '+json.dumps(str(backend_wrapper)))
    source = source.replace('id: shell', 'id: shell; property string appliedWallpaper: ""')
    source = source.replace('onWallpaperChanged: path => Theme.ThemeManager.requestSync()', 'onWallpaperChanged: path => { appliedWallpaper = path; Theme.ThemeManager.requestSync(); }')
    source = source.rstrip()[:-1] + '''
    IpcHandler {
        target: "probe"
        function textColors(): string {
            const pairs=[];
            function background(item) {
                for (let node=item;node;node=node.parent) {
                    if (node.background && node.background.color !== undefined) return String(node.background.color);
                    if (node.radius !== undefined && node.color !== undefined && node.color.a > 0.99) return String(node.color);
                }
                return "";
            }
            function visit(node) {
                // Hidden monograms/symbolic alternatives are not painted. Their
                // foreground is paired with a different surface when enabled.
                if(node.visible===false)return;
                if (typeof node.text === "string" && node.text && node.color !== undefined && node.font !== undefined) {
                    const bg=background(node);
                    if (bg) pairs.push({text:node.text,background:bg,color:String(node.color)});
                }
                if (node.placeholderTextColor !== undefined && node.background)
                    pairs.push({text:"placeholder",background:background(node),color:String(node.placeholderTextColor)});
                for (const child of (node.children || [])) visit(child);
            }
            visit(launcher.contentItem);
            if (menus.item) visit(menus.item.contentItem);
            return JSON.stringify(pairs);
        }
        function themeColors(): string {
            const wallpaper=wallpaperView(), clipboard=clipboardView();
            const frame=launcher.contentItem.children.find(child => child.objectName === "launcher-surface");
            const menu=menus.item ? menus.item.contentItem.children.find(child => child.objectName === "menu-surface") : null;
            return JSON.stringify({background:String(Theme.ThemeManager.background),launcherSurface:String(Theme.ThemeManager.surfaceContainer),mode:Theme.ThemeManager.mode,busy:Theme.ThemeManager.busy,
                launcher:frame ? String(frame.color) : "", menu:menu ? String(menu.color) : "",
                wallpaper:wallpaper ? String(wallpaper.color) : "",clipboard:clipboard ? String(clipboard.color) : ""});
        }
        function wallpaperView(): var {
            if (!menus.item) return null;
            const loader = menus.item.contentItem.children.find(child => child.item && child.item.objectName === "pixelrail-wallpaper-view");
            return loader ? loader.item : null;
        }
        function clipboardView(): var {
            if (!menus.item) return null;
            const loader=menus.item.contentItem.children.find(child => child.item && child.item.objectName === "pixelrail-clipboard-view");
            return loader ? loader.item : null;
        }
        function clipboardSnapshot(): string {
            const view=clipboardView();
            return JSON.stringify({present:!!view,count:view ? view.entries.length : 0,thumbnails:view ? Object.keys(view.thumbnails).length : 0,
                titles:view ? view.entries.map(entry => entry.title) : []});
        }
        function wallpaperSnapshot(): string {
            const view = wallpaperView();
            return JSON.stringify({present: !!view, canApply: view ? view.canApply : false,
                selected: view && view.selected ? view.selected.id : "", count: view ? view.entries.length : 0});
        }
        function wallpaperFilter(category: string): void { if (menus.item) menus.item.wallpaperCategory = category; }
        function wallpaperKey(key: int, modifiers: int): void {
            const view=wallpaperView(); if (view) view.key({key: key, modifiers: modifiers, accepted: false});
        }
        function snapshot(): string {
            return JSON.stringify({pendingMenu:shell.pendingMenu,mode: menus.item ? menus.item.mode : "unloaded",
                busy: menus.item ? menus.item.busy : false, error: menus.item ? menus.item.error : "",
                pending: menus.item ? menus.item.pending : null,
                placement:menus.item ? {left:menus.item.anchors.left,top:menus.item.anchors.top,bottom:menus.item.anchors.bottom,x:menus.item.margins.left,yTop:menus.item.margins.top,yBottom:menus.item.margins.bottom,width:menus.item.implicitWidth,height:menus.item.implicitHeight,screenWidth:menus.item.screen.width,screenHeight:menus.item.screen.height} : null,
                count: menus.item ? menus.item.entries.length : 0, wallpaper: shell.appliedWallpaper, launcher: launcher.opened});
        }
        function choose(id: string): void {
            if (menus.item) menus.item.choose(menus.item.filtered.findIndex(row => row.id === id));
        }
        function launchApp(id: string): void { launcher.launch(launcher.results.findIndex(app => app.id === id)); }
        function queuePendingMenu():void {shell.pendingMenu="controls";}
        function pid(): int { return Quickshell.processId; }
    }
}
'''
    source=source.replace("suppressed:control.opened", "suppressed:true || control.opened")
    config.write_text(source)
    env = dict(os.environ, QT_QPA_PLATFORM='wayland', WAYLAND_DISPLAY=wayland,
               XDG_RUNTIME_DIR=str(runtime), PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'], XDG_CACHE_HOME=str(base/'cache'),
               XDG_CONFIG_HOME=str(base/'config'), XDG_DATA_HOME=str(data),
               XDG_STATE_HOME=str(base/'state'), HOME=str(base),PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'),PIXELRAIL_LAUNCHER_METADATA=str(root/'scripts/launcher_entries.py'),
               XDG_PICTURES_DIR=str(pictures), XDG_DOWNLOAD_DIR=str(base/'Downloads'), PATH=str(binary)+':/usr/bin',
               TEST_CALLS=str(calls),TEST_COPY=str(copied),TEST_APPS=str(app_log),TEST_IMAGE=str(downloaded),PIXELRAIL_CLIPBOARD_TRACE='1')
    def ipc(target, method, *arguments):
        return subprocess.check_output([qs,'ipc','-p',str(config),'call',target,method,*arguments],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
    def wait(predicate, message):
        for _ in range(100):
            if predicate(): return
            time.sleep(.04)
        raise AssertionError(message)
    def state(): return json.loads(ipc('probe','snapshot'))
    def ready():
        try: return ipc('menus','status') == 'unloaded'
        except subprocess.SubprocessError: return False
    def open_menu(mode):
        assert ipc('menus','open',mode)=='true'
        wait(lambda: state()['mode']==mode and not state()['busy'] and state()['count']>0, mode+' ready')
        assert not state()['error'], state()
        placement=state()['placement'];bottom=mode in ('command','clipboard','windows','emoji')
        assert placement['left'] and placement['bottom']==bottom and placement['top']!=bottom,placement
        assert placement['yTop']==12 and placement['yBottom']==12 and placement['x']>=12,placement
        assert placement['x']+placement['width']+12<=placement['screenWidth'],placement
        assert placement['height']<=placement['screenHeight']-24,placement
    def close_menu():
        ipc('menus','hide'); wait(lambda: state()['mode']=='unloaded','lazy unload')
    with (base/'log').open('w+') as log:
        process = subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait(ready,'shell ready')
            original_pid = ipc('probe','pid')
            ipc('probe','queuePendingMenu');ipc('menus','hide')
            assert state()['pendingMenu']=='','hide must cancel a menu queued behind Launcher fade'
            # Switch while fetch/animation may still be pending: the last request wins.
            for _ in range(8):
                for kind in ('controls','clipboard','command','wallpaper','keys','power'):
                    assert ipc('menus','open',kind)=='true'
                wait(lambda:state()['mode']=='power' and not state()['busy'],'rapid menu convergence')
                close_menu()
            assert ipc('probe','pid')==original_pid

            duplicates = [subprocess.Popen([qs,'--no-duplicate','--daemonize','-p',str(config)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for _ in range(4)]
            for duplicate in duplicates: assert duplicate.wait(timeout=5)==0
            assert ipc('probe','pid')==original_pid
            for mode in ('keys','clipboard','command','windows','controls','power','wallpaper','media','emoji'):
                open_menu(mode); close_menu()
            # Same QML objects react while loaded: no reopen/restart required.
            for themed_mode in ('keys','clipboard','wallpaper','command','windows','controls','power','media','emoji'):
                open_menu(themed_mode)
                for theme_mode in ('light','dark'):
                    result=subprocess.run([str(root/'scripts/pixelrail-theme'),'mode',theme_mode],env=env,capture_output=True,text=True,timeout=10)
                    assert result.returncode==0,result.stdout
                    def themed():
                        value=json.loads(ipc('probe','themeColors'))
                        roles=['launcher', 'wallpaper' if themed_mode=='wallpaper' else 'clipboard' if themed_mode=='clipboard' else 'menu']
                        return value['mode']==theme_mode and not value['busy'] and all(value[role]==value['launcherSurface' if role=='launcher' else 'background'] for role in roles)
                    wait(themed,'reactive panel theme '+themed_mode+' '+theme_mode)
                    samples=json.loads(ipc('probe','textColors'))
                    assert samples
                    for sample in samples:
                        assert contrast(sample['background'],sample['color'])>=4.5,(themed_mode,theme_mode,sample)
                assert ipc('probe','pid')==original_pid
                close_menu()
            open_menu('wallpaper')
            def wallpaper_state(): return json.loads(ipc('probe','wallpaperSnapshot'))
            wait(lambda: wallpaper_state()['canApply'],'wallpaper bounded preview ready')
            assert wallpaper_state()['count']==122
            wait(lambda: len(list((base/'cache/pixelrail/wallpapers').glob('*.png')))>=2,'grid thumbnails generated')
            assert len(list((base/'cache/pixelrail/wallpapers').glob('*.png')))<35
            selected=wallpaper_state()['selected']
            ipc('probe','wallpaperKey',str(0x01000014),'0')  # Qt.Key_Right
            assert wallpaper_state()['selected']!=selected
            assert not (base/'state/pixelrail/wallpaper').exists()  # Selecting/previewing never applies.
            ipc('probe','wallpaperFilter','downloads')
            wait(lambda: wallpaper_state()['count']==1 and wallpaper_state()['canApply'],'downloads tab')
            assert wallpaper_state()['selected']==str(downloaded)
            ipc('probe','wallpaperKey',str(0x01000004),str(0x04000000))  # Ctrl+Return
            ipc('menus','hide')  # Hiding an explicitly committed apply must not kill its helper.
            wait(lambda: state()['mode']=='unloaded','wallpaper applied')
            assert state()['wallpaper']==str(downloaded)
            assert (base/'state/pixelrail/wallpaper').read_text().removesuffix('\n')==str(downloaded)
            palette=base/'cache/pixelrail/theme/palette.json'
            wait(lambda: palette.exists() and json.loads(palette.read_text()).get('source',{}).get('path')==str(downloaded),'wallpaperChanged palette generation')
            assert sum(json.loads(line)[0]=='swaybg' for line in calls.read_text().splitlines())==1
            open_menu('keys'); ipc('probe','choose','0'); time.sleep(.1); assert state()['mode']=='keys'; close_menu()
            open_menu('controls'); ipc('probe','choose','applications')
            wait(lambda: state()['launcher'] and state()['mode']=='unloaded','applications navigation')
            ipc('launcher','hide')
            for _ in range(3):
                open_menu('clipboard'); assert ipc('menus','open','clipboard')=='true'
                wait(lambda: state()['mode']=='unloaded','Super+V-style toggle closed')
            open_menu('clipboard')
            wait(lambda: json.loads(ipc('probe','clipboardSnapshot'))['thumbnails']>=1,'clipboard PNG preview')
            assert json.loads(ipc('probe','clipboardSnapshot'))['count']==31
            assert json.loads(ipc('probe','clipboardSnapshot'))['thumbnails']<7
            assert all('binary data' not in title for title in json.loads(ipc('probe','clipboardSnapshot'))['titles'])
            started=time.perf_counter(); ipc('probe','choose','9')
            wait(lambda: state()['mode']=='unloaded','clipboard image restore')
            assert time.perf_counter()-started<1.5
            assert copied.read_bytes()==downloaded.read_bytes()
            calls_before=sum(json.loads(line)==['cliphist','list'] for line in calls.read_text().splitlines())
            open_menu('clipboard'); ipc('probe','choose','7')
            wait(lambda: copied.exists() and copied.read_bytes()==b'fixture\x00bytes','clipboard copied')
            wait(lambda: state()['mode']=='unloaded','clipboard unloaded')
            assert sum(json.loads(line)==['cliphist','list'] for line in calls.read_text().splitlines())==calls_before+1
            open_menu('windows'); ipc('probe','choose','0xabc'); wait(lambda: state()['mode']=='unloaded','window selected')
            open_menu('controls'); ipc('probe','choose','power')
            wait(lambda: state()['mode']=='power' and not state()['busy'],'power navigation')
            ipc('probe','choose','shutdown')
            wait(lambda: state()['pending']=='shutdown' and not state()['busy'],'power confirmation')
            assert not calls.exists() or not any('systemctl' in line for line in calls.read_text().splitlines())
            ipc('probe','choose','cancel')
            wait(lambda: state()['pending'] is None and not state()['busy'],'cancel confirmation')
            ipc('probe','choose','shutdown'); wait(lambda: state()['pending']=='shutdown' and not state()['busy'],'confirm ready')
            ipc('probe','choose','confirm'); wait(lambda: state()['mode']=='unloaded','confirmed fake shutdown')
            open_menu('command'); ipc('probe','choose','pixelrail-test-command')
            wait(lambda: app_log.exists() and 'pixelrail-test-command' in app_log.read_text(),'command executed')
            wait(lambda: state()['mode']=='unloaded','command closed')
            for app_id in ('pixelrail-fixture-app','pixelrail-fixture-terminal'):
                ipc('probe','launchApp',app_id)
            wait(lambda: 'kitty' in app_log.read_text() and 'pixelrail-test-app' in app_log.read_text(),'desktop and terminal app launch')
            close_menu()
            assert not any(json.loads(line)[0] == 'rofi' for line in calls.read_text().splitlines())
        except BaseException:
            log.seek(0); print(log.read()); print(state())
            raise
        finally:
            process.terminate(); process.wait(timeout=5)
            for record in runtime.glob('pixelrail-swaybg-*.json'):
                pid=json.loads(record.read_text())['pid']
                try: os.kill(pid,signal.SIGTERM)
                except ProcessLookupError: pass
        log.seek(0); output=log.read(); print(output)
        for marker in ('ERROR','TypeError','ReferenceError','Unable to assign','Binding loop','Duplicate signal'):
            assert marker not in output, marker
    print('Wallpaper grid/filter/preview/keyboard/apply with bounded thumbnails; 9 native menus, lazy unload, IPC, selection/confirmation, binary clipboard, app/terminal launch, 4 duplicate starts: passed')
