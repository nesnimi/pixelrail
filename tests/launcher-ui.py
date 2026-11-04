"""Actual Qt Launcher keys/mouse, private desktop entries and harmless Exec marker."""
import json,os,re,shutil,signal,subprocess,tempfile,time
from pathlib import Path
ROOT=Path.cwd()
with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as tmp:
    base=Path(tmp);runtime=base/'runtime';runtime.mkdir(mode=0o700);shutil.copytree(ROOT/'quickshell',base/'quickshell')
    p=base/'quickshell/modules/launcher/Launcher.qml';s=p.read_text().replace('PanelWindow {','Item {',1)
    s=re.sub(r'^    screen:.*$', '    property var screen:({width:1366,height:768})\n    width:implicitWidth;height:implicitHeight',s,flags=re.M)
    s='\n'.join(line for line in s.splitlines() if not (line.startswith('    ') and not line.startswith('        ') and (line.strip().startswith(('anchors {','margins {','exclusionMode:','WlrLayershell.','HyprlandFocusGrab {')) or line.strip()=='color: "transparent"')))+'\n';p.write_text(s)
    apps=base/'data/applications';apps.mkdir(parents=True)
    icon=base/'color.svg';icon.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="16" height="32" fill="#e74c3c"/><rect x="16" width="16" height="32" fill="#3498db"/></svg>')
    executable=base/'app';executable.write_text('#!/bin/sh\nprintf launched > "'+str(base/'launched')+'"\n');executable.chmod(0o755)
    state=base/'state/pixelrail/launcher.json';state.parent.mkdir(parents=True)
    state.write_text(json.dumps({'version':1,'counts':{'4':4,'0':2,'uninstalled':100}}))
    for i,name in enumerate(['Chrome','Файлы','Терминал','Notes','Music','Editor','Browser']):
        named=base/(['google-chrome','system-file-manager','utilities-terminal','notes','music','code','web-browser'][i]+'.svg');named.write_bytes(icon.read_bytes())
        categories=['Network;WebBrowser;','System;FileTools;FileManager;','System;TerminalEmulator;','Utility;TextEditor;','AudioVideo;Player;','Development;','Network;WebBrowser;'][i]
        (apps/(str(i)+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+name+'\nGenericName='+('Папки' if i==1 else name)+'\nIcon='+str(named)+'\nCategories='+categories+'\nExec='+str(executable)+' app-'+str(i)+'\n')
    for ident,name,fields,args in [('aux-settings','AA Adapters','Categories=Settings;HardwareSettings;','--settings'),('aux-volume','AA Volume','Categories=AudioVideo;Mixer;','--volume'),('aux-rename','AA Rename','Categories=Utility;Filesystem;','--rename'),('foreign','Foreign Browser','OnlyShowIn=GNOME;\nCategories=Network;','--foreign'),('notshow','Excluded Browser','NotShowIn=Hyprland;\nCategories=Network;','--excluded'),('hidden','Hidden','Hidden=true','--hidden'),('nodisplay','NoDisplay','NoDisplay=true','--nodisplay'),('dup-chrome','Chrome Duplicate','Categories=Network;WebBrowser;','app-0')]:
        (apps/(ident+'.desktop')).write_text('[Desktop Entry]\nType=Application\nName='+name+'\nExec='+str(executable)+' '+args+'\n'+fields+'\n')
    config=base/'quickshell/test.qml';config.write_text('''import QtQuick
import QtQuick.Window
import QtTest
import Quickshell
import "modules/launcher" as Launcher
import "theme" as Theme
ShellRoot {
 Window {id:window;visible:true;width:560;height:460
  Launcher.Launcher {id:view}
  TestEvent {id:events} TestCase {id:tc;when:false}
  function find(node,name) {if(node.objectName===name)return node;for(const child of node.children || []){const item=window.find(child,name);if(item)return item;}return null;}
  function check(value,message){if(!value)throw new Error(message);}
  function capture(name){if(Quickshell.env("PIXELRAIL_RC3_CAPTURE"))view.grabToImage(result=>result.saveToFile(Quickshell.env("PIXELRAIL_RC3_CAPTURE")+"/"+name+".png"));tc.wait(100);}
  Timer {interval:250;running:true;onTriggered:{try {
   window.requestActivate();view.toggle();const search=window.find(view,"launcher-search"),list=window.find(view,"launcher-results");
   const deadline=Date.now()+3000;while((view.results.length<10 || !view.usageLoaded || !view.metadataReady) && Date.now()<deadline)tc.wait(30);
   window.check(view.results.length===10 && search.activeFocus,"initial apps/focus/visibility/dedup");
   window.check(view.showHome && view.homeApps.length===7 && view.homeApps[0].name==="Music","saved usage/grid ordering");
   window.check(list.count===0 && window.find(view,"launcher-home").visible,"hidden list still instantiated");
   window.check(!view.homeApps.some(app=>/^(aux-|foreign|notshow|hidden|nodisplay)/.test(app.id)),"helpers/foreign apps in grid");
   window.check(window.find(view,"launcher-action-0")===null,"removed quick actions remain");
   tc.wait(220); // Capture the settled panel, not a mid-animation frame.
   window.check(search.parent.height>=44 && search.parent.height<=48 && search.font.pixelSize===14,"Pixel search geometry");
   window.check(view.height<=420 && list.height<=266,"compact max five visible rows");
   for(const mode of ["dark","light","auto"])for(const style of ["original","themed"]) {
    Theme.ThemeManager.configuration={mode:mode,iconStyle:style};tc.wait(30);
    const tile=window.find(view,"launcher-app-0");window.check(Theme.ThemeManager.contrast(String(tile.color),String(Theme.ThemeManager.primaryContainerText))>=4.5,"selected grid contrast");
    window.check(Theme.ThemeManager.contrast(String(search.background.color || Theme.ThemeManager.surfaceContainerHigh),String(search.color))>=4.5,"search contrast");
    let count=0;function icons(node){if(node.appName!==undefined && node.themed!==undefined){window.check(node.themed===(style==="themed"),"live icon style");window.check(node.size===32,"icon size");count++;}for(const child of node.children || [])icons(child);}icons(view);window.check(count>0,"no app icons");
    if(mode!=="auto")window.capture("launcher-home-"+mode+"-"+style);
    search.text="chr";tc.wait(20);const row=window.find(view,"launcher-result-0");
    window.check(!view.showHome && !window.find(view,"launcher-home").visible && Theme.ThemeManager.contrast(String(row.color),String(Theme.ThemeManager.primaryContainerText))>=4.5,"selected search contrast");
    search.text="";tc.wait(20);
   }
   events.mouseClick(window.find(view,"launcher-app-0"),50,35,Qt.LeftButton,Qt.NoModifier,1);
   window.check(!view.opened && view.usage["4"]===5,"grid mouse launch/usage");view.toggle();tc.wait(20);
   search.text="фай";tc.wait(20);window.check(view.results.length===1 && view.results[0].name==="Файлы","Cyrillic search");
   search.text="CHROME";tc.wait(20);window.check(view.results.length===1,"Latin search");
   search.text="volume";tc.wait(20);window.check(view.results.length===1 && view.results[0].id==="aux-volume","utility disappeared from explicit search");
   search.text="foreign";tc.wait(20);window.check(view.results.length===1 && view.results[0].id==="foreign","explicit foreign utility search");
   search.text="missing";tc.wait(20);window.check(window.find(view,"launcher-empty").visible,"empty state");window.capture("launcher-empty");
   search.text="";view.usage={};view.homeIndex=0;tc.wait(20);
   window.check(view.homeApps.length===7 && !view.homeApps.some(app=>app.id.startsWith("aux-")) && window.find(view,"launcher-home-heading").text==="Приложения","user-facing fallback");
   const metadata=view.entryMetadata;let bare={};for(const id of Object.keys(metadata))bare[id]=Object.assign({},metadata[id],{categories:[]});
   view.entryMetadata=bare;tc.wait(30);window.check(!view.showHome && list.visible && !window.find(view,"launcher-home").visible,"no quality candidates must use ordinary list");
   view.entryMetadata=metadata;tc.wait(30);
   const metadataHelper=view.metadataHelper;view.metadataHelper="/missing-pixelrail-metadata";view.metadataReady=false;view.metadataPending=true;view.loadMetadata();tc.wait(180);
   window.check(!view.showHome && list.visible && search.activeFocus,"metadata failure must preserve list/focus");
   events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);window.check(!view.opened,"metadata failure Escape");view.toggle();
   view.metadataHelper=metadataHelper;view.metadataPending=true;view.loadMetadata();
   for(let wait=0;!view.metadataReady && wait<50;wait++)tc.wait(20);
   window.check(view.showHome,"metadata retry did not recover grid");
   search.forceActiveFocus();events.keyClick(Qt.Key_Down,Qt.NoModifier,1);window.check(view.homeIndex===4,"grid Down");
   events.keyClick(Qt.Key_Tab,Qt.NoModifier,1);window.check(view.homeIndex===5,"grid Tab");
   events.keyClick(Qt.Key_Backtab,Qt.ShiftModifier,1);window.check(view.homeIndex===4,"grid Shift+Tab");
   events.keyClick(Qt.Key_Up,Qt.NoModifier,1);window.check(view.homeIndex===0,"grid Up");
   events.keyClick(Qt.Key_Right,Qt.NoModifier,1);window.check(view.homeIndex===1,"grid Right");
   events.keyClick(Qt.Key_Left,Qt.NoModifier,1);window.check(view.homeIndex===0,"grid Left");
   view.homeIndex=3;events.keyClick(Qt.Key_Down,Qt.NoModifier,1);window.check(view.homeIndex===6,"incomplete grid row");
   events.keyClick(Qt.Key_Down,Qt.NoModifier,1);window.check(view.homeIndex===2,"grid vertical wrap");
   events.keyClick(Qt.Key_Up,Qt.NoModifier,1);window.check(view.homeIndex===6,"grid reverse wrap");
   events.keyClick(Qt.Key_Tab,Qt.NoModifier,1);window.check(view.homeIndex===0,"home Tab wrap");
   view.screen={width:800,height:300};tc.wait(30);view.homeIndex=view.homeApps.length-1;view.revealHome();
   window.check(view.height<=276 && window.find(view,"launcher-home").contentY>0,"short screen scroll/selection");
   view.screen={width:1366,height:768};tc.wait(30);
   search.text="r";tc.wait(20);events.keyClick(Qt.Key_Down,Qt.NoModifier,1);window.check(list.currentIndex===1,"results Down");
   events.keyClick(Qt.Key_Tab,Qt.NoModifier,1);window.check(list.currentIndex===2,"results Tab");
   events.keyClick(Qt.Key_Backtab,Qt.ShiftModifier,1);window.check(list.currentIndex===1,"results Shift+Tab");
   events.keyClick(Qt.Key_Up,Qt.NoModifier,1);window.check(list.currentIndex===0,"results Up");
   events.keyClick(Qt.Key_Escape,Qt.NoModifier,1);window.check(!view.opened,"Escape");
   view.toggle();search.text="Chrome";tc.wait(20);events.keyClick(Qt.Key_Return,Qt.NoModifier,1);window.check(!view.opened,"Enter launch closes");
   console.info("LAUNCHER_UI_PASS");
  }catch(error){console.error("LAUNCHER_UI_FAIL",error.message);}}}
 }
}''')
    env=dict(os.environ,HOME=str(base),XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_DATA_HOME=str(base/'data'),XDG_STATE_HOME=str(base/'state'),XDG_DATA_DIRS=str(base/'data'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',DBUS_SESSION_BUS_ADDRESS='unix:path='+str(base/'no-bus'),PIXELRAIL_THEME_HELPER=str(ROOT/'scripts/pixelrail-theme'))
    env.pop('WAYLAND_DISPLAY',None)
    env.update(PIXELRAIL_LAUNCHER_METADATA=str(ROOT/'scripts/launcher_entries.py'),XDG_CURRENT_DESKTOP='Hyprland')
    with (base/'log').open('w+') as log:
        child=subprocess.Popen(['qs','-p',str(config),'--no-color'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                log.seek(0);output=log.read()
                if 'LAUNCHER_UI_FAIL' in output or 'LAUNCHER_UI_PASS' in output or child.poll() is not None:break
                time.sleep(.02)
            deadline=time.monotonic()+2
            while 'LAUNCHER_UI_PASS' in output and time.monotonic()<deadline:
                try:
                    if (base/'launched').exists() and json.loads(state.read_text())['counts'].get('0')==1:break
                except (OSError,ValueError):pass
                time.sleep(.02)
        finally:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            child.wait(timeout=3)
        log.seek(0);output=log.read();print(output)
    assert 'LAUNCHER_UI_PASS' in output and (base/'launched').read_text()=='launched'
    assert json.loads(state.read_text())['counts']['0']==1
    for marker in ('LAUNCHER_UI_FAIL','TypeError','ReferenceError','Unable to assign','Binding loop'):assert marker not in output,marker
    restart=base/'quickshell/restart.qml'
    restart.write_text('''import QtQuick
import Quickshell
import "modules/launcher" as Launcher
ShellRoot {
 Launcher.Launcher {id:view}
 Timer {interval:100;running:true;repeat:true;onTriggered:if(view.usageLoaded && view.metadataReady && view.homeApps.length){console.info("USAGE_RESTART",view.usage["0"],view.homeApps[0].id);Qt.quit();}}
}''')
    result=subprocess.run(['qs','-p',str(restart),'--no-color'],env=env,capture_output=True,text=True,timeout=5)
    assert result.returncode==0 and 'USAGE_RESTART 1 0' in result.stdout+result.stderr,result.stdout+result.stderr
print('Launcher UI: category/visibility/usage grid, no quick actions, dedup, utility search/list fallback, short screen, focus/RU/EN/keys/Exec/styles/contrast/restart: PASS')
