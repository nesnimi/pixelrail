// Real offscreen QML rendering with fixture content; never reads user history/wallpapers.
import QtQuick
import QtTest
import Quickshell
import "../../quickshell/components" as Parts
import "../../quickshell/theme" as Theme
import "../../quickshell/ui" as Ui

Item {
    id:harness
    property int chosen:-1
    readonly property string picture:Quickshell.env("PIXELRAIL_TEST_IMAGE") || Qt.resolvedUrl("../../quickshell/assets/symbols/wallpaper.svg")
    TestCase {id:tc;when:false}
    TestEvent {id:events}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function find(node,name) {if(node.objectName===name)return node;for(const child of node.children || []){const result=find(child,name);if(result)return result;}return null;}
    function surface(node) {
        for(let item=node.parent;item;item=item.parent) {
            if(item.background && item.background.color!==undefined)return String(item.background.color);
            if(item.radius!==undefined && item.color!==undefined && item.color.a>.99)return String(item.color);
        }
        return "";
    }
    function verify(node) {
        if(node.visible===false)return;
        if(node.text && node.font!==undefined && node.color!==undefined) {
            const bg=surface(node);
            check(!bg || Theme.ThemeManager.contrast(bg,String(node.color))>=4.5,"text contrast: "+node.text);
        }
        if(node.name!==undefined && node.size!==undefined && node.status!==undefined)check(node.status===Image.Ready,"unloaded icon: "+node.name);
        for(const child of node.children || [])verify(child);
    }
    function capture(item,name) {
        const directory=Quickshell.env("PIXELRAIL_SCREENSHOT_DIR");
        if(!directory)return;
        let saved=false;
        item.grabToImage(result=>{check(result.saveToFile(directory+"/"+name+".png"),"capture save");saved=true;});
        for(let i=0;i<30 && !saved;i++)tc.wait(20);
        check(saved,"capture timeout");
    }
    Parts.ClipboardView {
        id:clipboard;width:640;height:620;backend:"/not-used"
        entries:[{id:"1",kind:"text",title:"Встреча завтра в 10:30\nКириллица, Unicode ✓ и многострочный текст",subtitle:""},
                 {id:"2",kind:"text",title:"https://example.org/pixelrail",subtitle:""},
                 {id:"3",kind:"image",title:"Изображение · PNG",subtitle:"Превью"}]
        thumbnails:({"3":{url:harness.picture,width:1586,height:992,format:"PNG"}})
        onChooseRequested:index=>harness.chosen=index
    }
    Parts.WallpaperView {
        id:wallpaper;width:1000;height:620;visible:false;backend:"/not-used"
        entries:[{id:"one",title:"Лавандовый вечер · длинное имя.png",subtitle:"Обои · тестовый файл",thumbnail:harness.picture},
                 {id:"two",title:"Второе изображение с кириллицей.png",subtitle:"Загрузки · тестовый файл",thumbnail:harness.picture}]
    }
    function run() {
        for(const mode of ["dark","light","auto"]) {
            Theme.ThemeManager.configuration={mode:mode,accent:null,animations:false};tc.wait(120);
            verify(clipboard);
            const search=find(clipboard,"clipboard-search");
            check(search.height===48 && search.leftPadding===48,"clipboard Pixel search");
            check(Theme.ThemeManager.contrast(String(search.background.color),String(search.placeholderTextColor))>=4.5,"placeholder contrast");
        }
        Theme.ThemeManager.configuration={mode:"dark",accent:null,animations:false};tc.wait(100);
        capture(clipboard,"clipboard-dark");
        const card=find(clipboard,"clipboard-card");
        events.mouseClick(card,60,24,Qt.LeftButton,Qt.NoModifier,5);check(chosen===0,"clipboard mouse copy request");
        clipboard.visible=false;wallpaper.visible=true;tc.wait(150);
        for(const mode of ["dark","light","auto"]) {
            Theme.ThemeManager.configuration={mode:mode,accent:null,animations:false};tc.wait(80);verify(wallpaper);
            const apply=find(wallpaper,"wallpaper-apply");apply.down=true;
            check(Theme.ThemeManager.contrast(String(apply.background.color),String(apply.contentItem.color))>=4.5,"pressed apply contrast");apply.down=false;
        }
        Theme.ThemeManager.configuration={mode:"dark",accent:null,animations:false};tc.wait(100);
        const first=find(wallpaper,"wallpaper-tile-0"),second=find(wallpaper,"wallpaper-tile-1");
        check(first.border.width===2 && second.border.width===0,"wallpaper selection outline");
        events.mouseClick(second,40,40,Qt.LeftButton,Qt.NoModifier,5);tc.wait(30);
        check(wallpaper.selectionIndex===1 && second.border.width===2 && first.border.width===0,"wallpaper mouse selection");
        capture(wallpaper,"wallpaper-dark");
        wallpaper.entries=[];tc.wait(30);verify(wallpaper);check(!wallpaper.canApply,"empty wallpaper apply enabled");
        wallpaper.visible=false;clipboard.visible=true;clipboard.entries=[];tc.wait(30);verify(clipboard);
        check(Ui.Tokens.hover===0,"reduced motion ignored");
    }
}
