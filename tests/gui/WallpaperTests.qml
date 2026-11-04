import QtQuick
import QtTest
import "../../quickshell/theme" as Theme
import "../../quickshell/components" as Parts

Item {
    id: harness
    property int closedCount: 0
    property int appliedCount: 0
    TestEvent { id: events }
    function check(condition, message) { if (!condition) throw new Error(message); }
    function item(parent, name) {
        if (parent.objectName === name) return parent;
        const children=parent.children || [];
        for (let i=0;i<children.length;i++) { const found=item(children[i],name); if (found) return found; }
        return null;
    }
    function pressEscape() { check(events.keyClick(Qt.Key_Escape,Qt.NoModifier,5),"key injection failed"); }
    Parts.WallpaperView {
        id: view
        anchors.fill: parent
        backend: "/not-used"
        entries: [{id:"one",title:"Горы · длинное имя.png",subtitle:"Папка",thumbnail:"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAJElEQVR4nGNImHCApohh1IJRC0YtGLVg1IJRC0YtGLVgaFgAAAJjEEwsnwkHAAAAAElFTkSuQmCC"}]
        onCategoryChanged: category => activeCategory=category
        onCloseRequested: { harness.closedCount++; visible=false; }
        onApplyRequested: harness.appliedCount++
    }
    function run() {
        const search=item(view,"wallpaper-search");
        check(Theme.ThemeManager.contrast(String(search.background.color),String(search.color))>=4.5,"input contrast");
        check(Theme.ThemeManager.contrast(String(search.background.color),String(search.placeholderTextColor))>=4.5,"placeholder contrast");
        check(Theme.ThemeManager.contrast(String(search.selectionColor),String(search.selectedTextColor))>=4.5,"input selection contrast");

        const names=["all","wallpapers","downloads","screenshots","all","screenshots"];
        for (let i=0;i<names.length;i++) {
            view.visible=true;
            const chip=item(view,"wallpaper-chip-"+names[i]);check(chip,"missing chip");
            check(events.mouseClick(chip,chip.width/2,chip.height/2,Qt.LeftButton,Qt.NoModifier,5),"mouse injection failed");
            check(view.activeCategory===names[i] && chip.selected,"active category mismatch");
            check(Theme.ThemeManager.contrast(String(chip.background.color),String(chip.contentItem.color))>=4.5,"selected chip contrast");
            chip.down=true;
            check(Theme.ThemeManager.contrast(String(chip.background.color),String(chip.contentItem.color))>=4.5,"pressed chip contrast");
            chip.down=false;
            check(chip.height>=34 && chip.height<=38,"chip height");
            check(chip.leftPadding===14 && chip.rightPadding===14,"chip padding");
            check(chip.width>=chip.contentItem.implicitWidth+28,"clipped chip text");
            if (i>0 && i<4) {
                const previous=item(view,"wallpaper-chip-"+names[i-1]);
                check(Math.abs(chip.x-previous.x-previous.width-8)<0.1,"chip spacing");
            }
            chip.forceActiveFocus();pressEscape();
            check(closedCount===i+1 && !view.visible,"Escape after tab "+names[i]);
        }
        const focus=["wallpaper-search","wallpaper-grid","wallpaper-preview"];
        for (let i=0;i<focus.length;i++) {
            view.visible=true;item(view,focus[i]).forceActiveFocus();pressEscape();
            check(closedCount===names.length+i+1 && !view.visible,"Escape from "+focus[i]);
        }
        check(appliedCount===0,"Escape applied wallpaper");
        check(item(view,"wallpaper-close")===null,"removed close button still exists");
        view.visible=true;view.focusSearch();
        events.keyClick(Qt.Key_Return,Qt.ControlModifier,5);
        check(appliedCount===1,"Ctrl+Enter did not apply");
        pressEscape();check(closedCount===10,"reopening/Escape");
    }
}
