import QtQuick
import QtTest
import "../../quickshell/theme" as Theme
import "../../quickshell/components" as Parts
Item {
    id: harness
    property int closedCount: 0
    property int chosen: -1
    TestEvent { id: events }
    function check(condition, message) { if (!condition) throw new Error(message); }
    function item(parent, name) {
        if (parent.objectName===name) return parent;
        const children=parent.children || [];
        for(let i=0;i<children.length;i++){const found=item(children[i],name);if(found)return found;}
        return null;
    }
    Parts.ClipboardView {
        id: view
        anchors.fill: parent
        backend:"/not-used"
        entries:[{id:"1",kind:"text",title:"Кириллица 👋\nвторая строка",subtitle:"Текст"},
                 {id:"2",kind:"image",title:"Изображение · PNG",subtitle:"32×24 · PNG"}]
        thumbnails: ({"2":{url:"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAIAAAAUMWhjAAAAJElEQVR4nGNImHCApohh1IJRC0YtGLVg1IJRC0YtGLVgaFgAAAJjEEwsnwkHAAAAAElFTkSuQmCC",width:32,height:24,format:"PNG"}})
        onCloseRequested:{harness.closedCount++;visible=false;}
        onChooseRequested:index => harness.chosen=index
    }
    function run(){
        const search=item(view,"clipboard-search");
        check(Theme.ThemeManager.contrast(String(search.background.color),String(search.color))>=4.5,"input contrast");
        check(Theme.ThemeManager.contrast(String(search.background.color),String(search.placeholderTextColor))>=4.5,"placeholder contrast");
        check(Theme.ThemeManager.contrast(String(search.selectionColor),String(search.selectedTextColor))>=4.5,"input selection contrast");

        view.focusSearch();events.keyClick(Qt.Key_Down,Qt.NoModifier,5);events.keyClick(Qt.Key_Return,Qt.NoModifier,5);
        check(chosen===1,"keyboard image selection");
        events.keyClick(Qt.Key_Escape,Qt.NoModifier,5);check(closedCount===1 && !view.visible,"clipboard Escape");
        for(let i=0;i<4;i++){
            view.visible=true;item(view,"clipboard-list").forceActiveFocus();
            events.keyClick(Qt.Key_Escape,Qt.NoModifier,5);check(closedCount===i+2 && !view.visible,"reopen/list Escape");
        }
    }
}
