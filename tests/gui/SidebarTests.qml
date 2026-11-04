import QtQuick
import QtTest
import "../../quickshell/modules/sidebar" as Parts
import "../../quickshell/modules/sidebar/SidebarLogic.js" as Logic
import "../../quickshell/theme" as Theme
Item {
    TestEvent { id: events }
    Theme.Palette { id: colors }
    Parts.SidebarButton { id: button; x:20; y:20; glyph:"home" }
    property var lastCommand: []
    Parts.SidebarButton { id: workspaceButton; x:20; y:80; label:"1"; onClicked: lastCommand=Logic.workspaceCommand({id:Number(label)},"eDP-1",true) }
    function check(value,message) { if (!value) throw new Error(message); }
    function find(node,name) {if(node.objectName===name)return node;for(const child of node.children || []){const found=find(child,name);if(found)return found;}return null;}
    function battery(energy,capacity,percentage,name) {
        return {isPresent:true,isLaptopBattery:true,energy:energy,energyCapacity:capacity,percentage:percentage,nativePath:name};
    }
    function run() {
        const brand=find(button,"sidebar-brand"),systemIcon=find(button,"sidebar-system-icon");
        check(brand && brand.visible && brand.status===Image.Ready,"original brand SVG not rendered");
        check(decodeURIComponent(String(brand.source)).includes('M6 18V6h7a4 4 0 0 1 0 8H6m0-4h7'),"original PixelRail path changed");
        check(!systemIcon.visible && !button.label,"brand must not use font P or fallback apps");
        button.glyph="wifi";
        check(systemIcon.visible && systemIcon.size>=20 && systemIcon.size<=22 && !systemIcon.filled,"consistent outlined Sidebar system icon");
        button.glyph="home";
        const bat0=battery(10,20,.5,"BAT0"),bat1=battery(60,60,1,"BAT1");
        check(Logic.battery([bat0,bat1],null).percent===87.5,"energy weighted dual battery");
        check(Logic.battery([bat0],null).percent===50,"single battery");
        bat1.isPresent=false;
        check(Logic.battery([bat0,bat1],null).percent===50,"removed battery");
        check(Logic.battery([],null).percent===null,"battery absent");
        bat1.isPresent=true;bat0.energyCapacity=0;
        check(Logic.battery([bat0,bat1],{isPresent:true,percentage:.73}).percent===73,"trusted UPower aggregate fallback");
        check(Logic.battery([bat0,bat1],null).percent===null,"must not average unknown capacities");
        const entries=[{id:"org.example.App.desktop",startupClass:"Example",icon:"example"}];
        check(Logic.application({lastIpcObject:{class:"EXAMPLE"}},entries).entry===entries[0],"desktop StartupWMClass match");
        check(Logic.application({lastIpcObject:{class:"org.example.App"}},entries).entry===entries[0],"desktop id match");
        const windows=[{title:"one",lastIpcObject:{class:"Example"}},{title:"two",lastIpcObject:{class:"Example"}},
            {lastIpcObject:{class:"org.quickshell"}},{lastIpcObject:{class:"unknown"}}];
        check(Logic.windows(windows.map(w=>Object.assign(w,{workspace:{id:3}})),"org.quickshell",{id:3}).length===3,"one button per window, no shell windows");
        check(!Logic.application(windows[3],entries).entry,"missing desktop fallback");
        const spaces=[{id:1,active:true,toplevels:{values:[]}},{id:2,active:false,toplevels:{values:[]}},
            {id:-1337,active:false,toplevels:{values:[{}]}},{id:-99,active:true,toplevels:{values:[{}]}}];
        check(Logic.workspaces(spaces, {id:1}).map(w=>w.id).join(",")==="1,2,3,4,5","persistent desktops");
        check(Logic.workspaces([], {id:6}).map(w=>w.id).join(",")==="1,2,3,4,5,6","additional active desktop");
        check(Logic.windows(windows,"org.quickshell",{id:1}).length===0,"other workspace hidden");
        const command=Logic.windowCommand({address:"bbb"},true);
        check(command[1]==="eval" && command[2]==='hl.dispatch(hl.dsp.focus({ window = "address:0xbbb" }))',"Lua window command");
        check(Logic.windowCommand({address:'bad;inject'},true).length===0,"address injection guard");
        for (const ident of [1,2,3,5,1]) {
            workspaceButton.label=String(ident);
            check(events.mouseClick(workspaceButton,10,10,Qt.LeftButton,Qt.NoModifier,5),"workspace mouse event");
            check(lastCommand[1]==="eval" && lastCommand[2].includes('workspace = "'+ident+'"'),"mouse Lua command");
        }
        const screens=[{name:"eDP-1",width:1366},{name:"DP-1",width:1920}];
        check(Logic.targetScreen(screens,"DP-1",null)===screens[1],"configured monitor");
        check(Logic.targetScreen(screens,"missing",screens[1])===screens[1],"monitor disconnect fallback");
        check(Logic.targetScreen([],"",null)===null,"no monitors");
        check(Logic.targetScreen(screens,"",screens[0])===screens[0],"primary monitor");
        for (const mode of ["dark","light","auto"]) {
            Theme.ThemeManager.configuration={mode:mode,accent:null};
            button.selected=false;
            check(Theme.ThemeManager.contrast(String(colors.surfaceContainer),String(button.foreground))>=4.5,"sidebar text contrast");
            button.accented=true;
            check(Theme.ThemeManager.contrast(String(colors.surfaceContainer),String(button.foreground))>=3,"accent icon contrast");
            button.accented=false;
            button.selected=true;
            check(Theme.ThemeManager.contrast(String(button.color),String(button.foreground))>=4.5,"selected contrast");
            events.mousePress(button,10,10,Qt.LeftButton,Qt.NoModifier,5);
            check(Theme.ThemeManager.contrast(String(button.color),String(button.foreground))>=4.5,"pressed contrast");
            events.mouseRelease(button,10,10,Qt.LeftButton,Qt.NoModifier,5);
        }
        check(Logic.svg("volume","#ffffff").startsWith("data:image/svg+xml"),"own icons");
    }
}
