"""Native Sidebar lazy load, API bindings, services: all windows remain unmapped."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import sys
sys.path.insert(0,str(Path.cwd()/"tests/fixtures"))
from sidebar_hyprland import Hyprland
root=Path.cwd();qs=shutil.which('qs') or shutil.which('quickshell')
wayland=os.environ['WAYLAND_DISPLAY']
if not wayland.startswith('/'):wayland=str(Path(os.environ['XDG_RUNTIME_DIR'])/wayland)
with tempfile.TemporaryDirectory(dir=root/'.cache') as temporary:
    base=Path(temporary);runtime=base/'runtime';runtime.mkdir(mode=0o700)
    compositor=Hyprland(runtime)
    (base/'scripts').symlink_to(root/'scripts',target_is_directory=True)
    # Copy only QML to instrument visibility. Native services/API types are untouched.
    shutil.copytree(root/'quickshell',base/'quickshell')
    panel=base/'quickshell/modules/sidebar/Sidebar.qml'
    source=panel.read_text().replace('visible: enabledPanel && targetScreen !== null','visible: false')
    source=source.replace('Logic.windows(Hyprland.toplevels.values, Quickshell.appId, activeWorkspace)', 'Logic.windows(Hyprland.toplevels.values, Quickshell.appId, activeWorkspace).filter(w => ["aaa", "bbb", "bee", "ddd", "fff"].includes(w.address))')
    source=source.replace('function command(args): void { Quickshell.execDetached(args); }','property var testCommands: []; function command(args): void { testCommands = testCommands.concat([args]); }')
    source=source.replace('root.height','754')
    source=source.replace('readonly property bool compact: height < 650','readonly property bool compact: false')
    source=source.replace('readonly property int extent: height < 500 ? Math.max(18, Math.floor((height - 70) / 13)) : compact ? 30 : 36','readonly property int extent: 36')
    panel.write_text(source)
    control=base/'quickshell/modules/control/ControlCenter.qml'
    control.write_text(control.read_text().replace('visible:opened && !!screen','visible:false'))
    button=base/'quickshell/modules/sidebar/SidebarButton.qml'
    button.write_text(button.read_text().replace('active: mouse.containsMouse && root.tooltip', 'active: root.tooltip').replace('visible: true','visible: false'))
    controller=base/'quickshell/components/PanelController.qml'
    controller.write_text(controller.read_text().replace('    id: root','    id: root; property alias testView: sidebar.item').replace('onLoaded: {','onLoaded: { item.contentItem.width=66; item.contentItem.height=754;'))
    config=base/'quickshell/shell.qml'
    source=config.read_text().replace('import Quickshell\n','import Quickshell\nimport Quickshell.Hyprland\n',1).replace('Launcher { id: launcher }','Launcher { id: launcher; visible: false }')
    source=source.replace('MenuPanel {','MenuPanel { visible: false;')
    source=source.rstrip()[:-1]+''' IpcHandler {
        target: "test"
        function loaded(): string { return panel.state(); }
        function button(name: string): bool {
            function find(node,wanted) {
                if(node.objectName===wanted)return node;
                for(const child of node.children || []) {const result=find(child,wanted);if(result)return result;}
                return null;
            }
            const view=panel.testView;
            const workspace=name.startsWith("sidebar-workspace-");
            const list=find(view.contentItem,workspace ? "sidebar-workspaces" : "sidebar-apps");
            if(list) {
                const index=workspace ? view.workspaces.findIndex(w=>"sidebar-workspace-"+w.id===name)
                    : view.windows.findIndex(w=>"sidebar-window-"+w.address===name);
                if(index>=0) {list.currentIndex=index;list.positionViewAtIndex(index,ListView.Contain);list.forceLayout();}
            }
            const button=find(view.contentItem,name);
            if(!button)return false;
            button.clicked();return true;
        }
        function actions(): string { return JSON.stringify({commands:panel.testView.testCommands,launcher:launcher.opened,power:menus.item ? menus.item.mode : ""}); }
        function layout():string {
            const view=panel.testView;
            function find(node,name) {if(node.objectName===name)return node;for(const child of node.children || []){const found=find(child,name);if(found)return found;}return null;}
            const names=["sidebar-power","sidebar-network","sidebar-battery","sidebar-workspaces","sidebar-apps","sidebar-home"];
            return JSON.stringify(names.map(name=>{const item=find(view.contentItem,name);return {name:name,y:item.mapToItem(view.contentItem,0,0).y,height:item.height};}));
        }
        function models(): string {
            const view=panel.testView;
            return JSON.stringify({usingLua:Hyprland.usingLua,workspaces:view ? view.workspaces.map(w=>({id:w.id,focused:w.active})) : [],
                error:view ? view.actionError : "", windows:view ? view.windows.map(w=>({address:w.address,title:w.title,active:w.activated,icon:view.appIcon(w)})) : []});
        }
        function workspace(id: int): void { const view=panel.testView;const w=view.workspaces.find(w=>w.id===id);if(w)view.switchWorkspace(w); }
        function focus(address: string): void { const view=panel.testView;view.focusWindow(view.windows.find(w=>w.address===address.replace(/^0x/,""))); }

    }
}'''
    source=source.replace("suppressed:control.opened", "suppressed:true || control.opened")
    config.write_text(source)
    apps=base/'data/applications';apps.mkdir(parents=True)
    icon=base/'fixture.svg';icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><rect width="24" height="24" fill="red"/></svg>')
    (apps/'pixelrail-fixture-app.desktop').write_text('[Desktop Entry]\nType=Application\nName=Fixture\nExec=true\nIcon='+str(icon)+'\n')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CACHE_HOME=str(base/'cache'),
        XDG_CONFIG_HOME=str(base/'config'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_HOME=str(base/'data'),
        HYPRLAND_INSTANCE_SIGNATURE='sidebar-test',PIPEWIRE_RUNTIME_DIR=os.environ['XDG_RUNTIME_DIR'],WAYLAND_DISPLAY=wayland,QT_QPA_PLATFORM='wayland',PIXELRAIL_THEME_HELPER=str(root/'scripts/pixelrail-theme'))
    def ipc(method,*args):
        return subprocess.check_output([qs,'ipc','-p',str(config),'call','panel',method,*args],env=env,stderr=subprocess.DEVNULL,timeout=3).decode().strip()
    def models():
        return json.loads(subprocess.check_output([qs,'ipc','-p',str(config),'call','test','models'],env=env,timeout=3).decode())
    def action(method,value):
        deadline=time.monotonic()+3
        while True:
            output=subprocess.check_output([qs,'ipc','-p',str(config),'call','test',method,str(value)],env=env).decode().strip()
            if method!='button' or output=='true':return
            if time.monotonic()>deadline:raise AssertionError('missing button '+str(value))
            time.sleep(.03)
    def model_wait(predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            value=models()
            if predicate(value):return value
            time.sleep(.03)
        raise AssertionError((value,compositor.requests))
    def wait(predicate):
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            try:
                value=json.loads(ipc('state'))
                if predicate(value): return value
            except (subprocess.CalledProcessError,json.JSONDecodeError): pass
            time.sleep(.03)
        raise AssertionError('Sidebar did not reach expected state: '+str(value if 'value' in locals() else 'no IPC'))
    with (base/'log').open('w+') as log:
        child=subprocess.Popen([qs,'-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait(lambda value:not value['prepared'] and not value['enabled'])
            for cycle in range(3):
                ipc('prepare','');wait(lambda value:value['prepared'] and bool(value['screen']))
                value=model_wait(lambda v:len(v['windows'])==1 and len(v['workspaces'])==5)
                assert [w['id'] for w in value['workspaces']]==[1,2,3,4,5]
                layout=json.loads(subprocess.check_output([qs,'ipc','-p',str(config),'call','test','layout'],env=env).decode())
                assert all(a['y']+a['height']<=b['y']+.1 for a,b in zip(layout,layout[1:])),layout
                assert abs(layout[-1]['y']+layout[-1]['height']-748)<1,layout
                assert value['windows'][0]['title']=='Chrome' and value['windows'][0]['icon']
                # Invoke real delegates, then require compositor state AND native event-model changes.
                if cycle==0:
                    for name in ('sidebar-network','sidebar-home'):
                        action('button',name)
                    result=json.loads(subprocess.check_output([qs,'ipc','-p',str(config),'call','test','actions'],env=env).decode())
                    assert result['launcher']
                    assert result['commands']==[]  # Sidebar system clicks now route to native Control Center sections.
                    action('button','sidebar-power')
                    result=json.loads(subprocess.check_output([qs,'ipc','-p',str(config),'call','test','actions'],env=env).decode())
                    assert result['power']=='power'
                    subprocess.check_call([qs,'ipc','-p',str(config),'call','menus','hide'],env=env,stdout=subprocess.DEVNULL)
                before=len(compositor.workspaces)
                assert before==3 if cycle==0 else before>=3
                assert value['usingLua']
                compositor.emit('focusedmonv2>>DP-1,9')
                model_wait(lambda v:len(v['windows'])==1 and v['windows'][0]['title']=='Chrome' and v['workspaces'][0]['focused'])
                compositor.emit('focusedmonv2>>eDP-1,1')
                for ident in (1,2,3,5,1):
                    action('button','sidebar-workspace-'+str(ident))
                    value=model_wait(lambda v:any(w['id']==ident and w['focused'] for w in v['workspaces']))
                    assert compositor.monitor['activeWorkspace']['id']==ident
                    expected=2 if ident==3 else 1 if ident==1 else 0
                    model_wait(lambda v:len(v['windows'])==expected)
                    assert not models()['error']
                assert not any('dispatch workspace ' in cmd for cmd in compositor.requests)
                compositor.fail_next=True
                action('button','sidebar-workspace-3')
                model_wait(lambda v:'rejected' in v['error'])
                assert compositor.monitor['activeWorkspace']['id']==1
                assert models()['workspaces'][0]['focused']
                action('button','sidebar-workspace-3')
                model_wait(lambda v:len(v['windows'])==2)
                for address in ('bbb','bee'):
                    action('button','sidebar-window-'+address)
                    model_wait(lambda v:any(w['address']==address and w['active'] for w in v['windows']))
                    assert compositor.active['address']=='0x'+address
                    assert 'eval hl.dispatch(hl.dsp.focus({ window = "address:0x'+address+'" }))' in compositor.requests
                # Move an existing window away; list must update without changing active workspace.
                compositor.clients[2]['workspace']={'id':1,'name':'1'}
                compositor.emit('movewindowv2>>bee,1,1')
                model_wait(lambda v:len(v['windows'])==1 and v['windows'][0]['address']=='bbb')
                count=len(compositor.requests);action('focus','0xbee');time.sleep(.08)
                assert not any(cmd.startswith('eval ') for cmd in compositor.requests[count:]),'stale moved window activated'
                compositor.clients[2]['workspace']={'id':3,'name':'3'}
                compositor.emit('movewindowv2>>bee,3,3')
                model_wait(lambda v:len(v['windows'])==2)
                compositor.clients.append(compositor.window('0xddd','New window',workspace=3))
                compositor.emit('openwindow>>ddd,3,pixelrail-fixture-app,New window')
                model_wait(lambda v:len(v['windows'])==3)
                compositor.clients.pop();compositor.emit('closewindow>>ddd')
                model_wait(lambda v:len(v['windows'])==2)
                count=len(compositor.requests);action('focus','0xddd');time.sleep(.08)
                assert not any(cmd.startswith('eval ') for cmd in compositor.requests[count:]),'closed window activated'
                # Non-base active workspace appears in addition to 1..5 and disappears on leaving.
                action('workspace',1)
                model_wait(lambda v:any(w['id']==1 and w['focused'] for w in v['workspaces']))
                if not any(w['id']==6 for w in compositor.workspaces):
                    compositor.workspaces.append(dict(id=6,name='6',monitor='eDP-1',monitorID=0,windows=0,hasfullscreen=False))
                compositor.monitor['activeWorkspace']={'id':6,'name':'6'}
                compositor.emit('createworkspacev2>>6,6');compositor.emit('workspacev2>>6,6')
                model_wait(lambda v:[w['id'] for w in v['workspaces']]==[1,2,3,4,5,6])
                model_wait(lambda v:len(v['windows'])==0)
                action('button','sidebar-workspace-1')
                model_wait(lambda v:len(v['workspaces'])==5 and len(v['windows'])==1)
                assert ipc('activate')=='true'
                wait(lambda value:value['enabled'] and not value['visible'] and value['exclusiveZone']==0)
                ipc('hide');wait(lambda value:not value['prepared'] and not value['enabled'])
        finally:
            child.terminate();child.wait(timeout=5)
            compositor.close()
            log.seek(0);output=log.read();print(output)
    for marker in ('ERROR','Unable to assign','TypeError','ReferenceError','Binding loop','not a type'):
        assert marker not in output,marker
print('Native Sidebar: lazy create/destroy x3, 1→2→3→5→1 Lua dispatch+state, per-workspace windows, focus/move/close, icons, services, IPC show/hide, disabled zone=0; no mapped windows passed')
