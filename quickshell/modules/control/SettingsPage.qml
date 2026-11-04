pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import "../../theme" as Theme
import "../../ui" as Ui
import "." as Controls
Item {
    id:root;objectName:"settings-page"
    required property var controller
    property string category:"Внешний вид"
    property real viewportHeight:400
    readonly property bool compact:width<600
    implicitHeight:Math.max(80,viewportHeight)
    property real pageReveal:1
    readonly property var sections:[
        {key:"Внешний вид",label:"Внешний вид",icon:"palette",description:"Тема и динамические цвета"},
        {key:"Sidebar",label:"Sidebar",icon:"tune",description:"Левая панель PixelRail"},
        {key:"Launcher",label:"Launcher",icon:"apps",description:"Приложения — одним Super"},
        {key:"Иконки",label:"Иконки и курсор",icon:"mouse",description:"Значки приложений и GoogleDot"},
        {key:"Уведомления",label:"Уведомления",icon:"notifications",description:"История и сервер уведомлений"},
        {key:"Ввод",label:"Ввод и клавиатура",icon:"language",description:"Текущая раскладка Hyprland"},
        {key:"Эффекты",label:"Производительность",icon:"speed",description:"Анимации и графический профиль"},
        {key:"Клавиши",label:"Горячие клавиши",icon:"keyboard",description:"Существующие сочетания и поиск"},
        {key:"О PixelRail",label:"О PixelRail",icon:"info",description:"Pixel Experience для Linux"}
    ]
    readonly property var current:sections.find(section=>section.key===category) || sections[0]
    Theme.Palette {id:colors}
    Controls.SettingsActions {id:settingsActions}
    onCategoryChanged:Qt.callLater(()=>{
        body.contentY=0;
        const index=sections.findIndex(section=>section.key===category),item=navItems.itemAt(index);
        if(item)navigation.contentY=Math.max(0,Math.min(Math.max(0,navigation.contentHeight-navigation.height),item.y<navigation.contentY ? item.y : Math.max(navigation.contentY,item.y+item.height-navigation.height)));
        transition.restart();
    })
    NumberAnimation {id:transition;target:root;property:"pageReveal";from:.8;to:1;duration:Ui.Tokens.state;easing.type:Easing.OutCubic}
    function revealFocus():void {
        const item=root.Window.window ? root.Window.window.activeFocusItem : null;
        if(!item)return;
        for(const view of [navigation,body]) {
            let ancestor=item;
            while(ancestor && ancestor!==view.contentItem)ancestor=ancestor.parent;
            if(!ancestor)continue;
            const position=item.mapToItem(view.contentItem,0,0);
            if(position.y<view.contentY)view.contentY=position.y;
            else if(position.y+item.height>view.contentY+view.height)view.contentY=position.y+item.height-view.height;
            view.contentY=Math.max(0,Math.min(Math.max(0,view.contentHeight-view.height),view.contentY));
        }
    }
    Connections {target:root.Window.window;function onActiveFocusItemChanged(){Qt.callLater(root.revealFocus);}}
    RowLayout {
        anchors.fill:parent;spacing:Ui.Tokens.spaceMd
        Rectangle {
            Layout.preferredWidth:root.compact ? 48 : 192;Layout.fillHeight:true
            radius:Ui.Tokens.radiusLg;color:colors.surfaceContainerHigh
            Flickable {
                id:navigation;objectName:"settings-navigation"
                anchors {fill:parent;margins:4} clip:true;contentWidth:width;contentHeight:navColumn.implicitHeight;boundsBehavior:Flickable.StopAtBounds
                ColumnLayout {
                    id:navColumn;width:navigation.width;spacing:Ui.Tokens.spaceXs
                    Repeater {
                        id:navItems;model:root.sections
                        delegate:Controls.ControlButton {
                            id:navButton
                            required property var modelData
                            required property int index
                            objectName:"settings-nav-"+index
                            Layout.fillWidth:true;Layout.preferredHeight:40
                            tonal:true;symbol:modelData.icon;text:root.compact ? "" : modelData.label
                            active:root.category===modelData.key;Accessible.name:modelData.label
                            ToolTip.visible:root.compact && hovered;ToolTip.text:modelData.label
                            onClicked:root.category=modelData.key
                            background:Rectangle {radius:Ui.Tokens.radiusPill;color:navButton.down || navButton.active ? colors.primaryContainer : navButton.hovered ? colors.surfaceVariant : colors.surfaceContainerHigh;border.width:navButton.visualFocus ? 1 : 0;border.color:colors.accent}
                            Keys.onPressed:event=>{
                                if(event.key===Qt.Key_Down || event.key===Qt.Key_Up) {
                                    const next=(index+(event.key===Qt.Key_Down ? 1 : -1)+root.sections.length)%root.sections.length;
                                    root.category=root.sections[next].key;navItems.itemAt(next).forceActiveFocus();event.accepted=true;
                                }
                            }
                        }
                    }
                }
            }
        }
        Flickable {
            id:body;objectName:"settings-content"
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            contentWidth:width;contentHeight:page.implicitHeight;boundsBehavior:Flickable.StopAtBounds
            Keys.onPressed:event=>{if(event.key===Qt.Key_PageUp || event.key===Qt.Key_PageDown){contentY=Math.max(0,Math.min(Math.max(0,contentHeight-height),contentY+(event.key===Qt.Key_PageDown ? 1 : -1)*height*.8));event.accepted=true;}}
            ColumnLayout {
                id:page;width:body.width;spacing:Ui.Tokens.spaceMd;opacity:root.pageReveal
                Controls.ControlLabel {objectName:"settings-heading";Layout.fillWidth:true;text:root.current.label;font {pixelSize:Ui.Tokens.title;weight:Font.Medium}}
                Controls.ControlLabel {Layout.fillWidth:true;text:root.current.description;color:colors.muted;font.pixelSize:Ui.Tokens.label}
                Loader {
                    Layout.fillWidth:true;Layout.preferredHeight:item ? item.implicitHeight : 0
                    sourceComponent:root.category==="Внешний вид" ? appearance : root.category==="Sidebar" ? sidebar : root.category==="Launcher" ? launcher : root.category==="Иконки" ? icons : root.category==="Уведомления" ? notifications : root.category==="Ввод" ? input : root.category==="Эффекты" ? effects : root.category==="Клавиши" ? shortcuts : about
                }
                Controls.ControlLabel {Layout.fillWidth:true;visible:settingsActions.error!=="" || Controls.DesktopState.error!=="";text:settingsActions.error || Controls.DesktopState.error;color:colors.error}
            }
        }
    }
    Component {
        id:appearance
        ColumnLayout {
            spacing:Ui.Tokens.spaceMd
            Controls.SettingsCard {
                title:"Тема"
                GridLayout {Layout.fillWidth:true;columns:width<220 ? 1 : 3;columnSpacing:4;rowSpacing:4;Repeater {model:["dark","light","auto"];delegate:Controls.ControlButton {required property string modelData;objectName:"settings-mode-"+modelData;Layout.fillWidth:true;Layout.preferredWidth:1;tonal:true;text:({dark:"Тёмная",light:"Светлая",auto:"Авто"})[modelData];active:Theme.ThemeManager.configuredMode===modelData;onClicked:settingsActions.request("mode",modelData)}}}
            }
            Controls.SettingsCard {
                title:"Material You";description:"Цвета из обоев или ваш акцент"
                RowLayout {Layout.fillWidth:true;spacing:8;Repeater {model:[colors.primary,colors.primaryContainer,colors.secondary,colors.surface,colors.surfaceContainer];delegate:Rectangle {required property color modelData;Layout.fillWidth:true;implicitHeight:24;radius:12;color:modelData;Accessible.name:String(modelData)}}}
                Controls.ControlButton {objectName:"settings-accent-reset";Layout.fillWidth:true;tonal:true;symbol:"wallpaper";text:"Из обоев";active:!Theme.ThemeManager.configuration.accent;onClicked:settingsActions.request("accent","reset")}
                RowLayout {
                    Layout.fillWidth:true;spacing:8
                    TextField {id:accent;objectName:"settings-accent";Layout.fillWidth:true;implicitHeight:40;leftPadding:12;rightPadding:12;placeholderText:"#RRGGBB";text:Theme.ThemeManager.configuration.accent || "";color:colors.text;placeholderTextColor:colors.muted;font {family:colors.font;pixelSize:Ui.Tokens.body} selectionColor:colors.selected;selectedTextColor:colors.selectedText;background:Rectangle {radius:Ui.Tokens.radiusSm;color:colors.surfaceContainer} onAccepted:if(/^#[0-9a-fA-F]{6}$/.test(text))settingsActions.request("accent",text)}
                    Controls.ControlButton {objectName:"settings-accent-apply";text:"OK";Accessible.name:"Применить акцент";tonal:true;enabled:/^#[0-9a-fA-F]{6}$/.test(accent.text);onClicked:settingsActions.request("accent",accent.text)}
                }
                Controls.ControlButton {Layout.fillWidth:true;text:"Выбрать обои";onClicked:root.controller.menuRequested("wallpaper")}
            }
            Controls.SettingsCard {title:"Значки приложений";Controls.IconStylePicker {actions:settingsActions}}
            Controls.SettingsCard {title:"Движение и эффекты";Controls.ControlButton {Layout.fillWidth:true;tonal:true;symbol:"speed";text:Theme.ThemeManager.animations ? "Анимации включены" : "Анимации выключены";active:Theme.ThemeManager.animations;onClicked:settingsActions.request("animations",Theme.ThemeManager.animations ? "false" : "true")} Controls.ControlButton {Layout.fillWidth:true;text:"Графический профиль";onClicked:root.category="Эффекты"}}
        }
    }
    Component {
        id:sidebar
        ColumnLayout {
            spacing:12
            Controls.SettingsCard {title:"Pixel Sidebar";description:"Power → Wi-Fi → заряд\nWorkspace 1–5 → окна → логотип\nШирина 54 px · зона 66 px";Controls.ControlLabel {Layout.fillWidth:true;text:"Компоновка закреплена";color:colors.muted;font.pixelSize:12}}
            Controls.SettingsCard {title:"Режим панели";Controls.ControlButton {Layout.fillWidth:true;tonal:true;text:"Pixel Sidebar";onClicked:settingsActions.request("panel","sidebar")} Controls.ControlButton {Layout.fillWidth:true;tonal:true;text:"Waybar fallback";onClicked:settingsActions.request("panel","waybar")}}
        }
    }
    Component {
        id:launcher
        ColumnLayout {
            spacing:12
            Controls.SettingsCard {title:"Launcher 2.0";description:"Поиск установленных приложений, RU/EN. До пяти строк, остальные — прокруткой.";RowLayout {Ui.Keycap {text:"Super"} Controls.ControlLabel {text:"открыть";font.pixelSize:12}} RowLayout {Ui.Keycap {text:"Enter"} Ui.Keycap {text:"Esc"} Ui.Keycap {text:"↑ ↓ / Tab"}}}
            Controls.SettingsCard {title:"Иконки Launcher";Controls.IconStylePicker {actions:settingsActions}}
            Controls.SettingsCard {title:"Открытие";description:"Снизу слева, рядом с Sidebar. Повторный Super закрывает панель. Положение и клавиша закреплены.";Controls.ControlButton {Layout.fillWidth:true;text:"Все сочетания";onClicked:root.controller.menuRequested("keys")}}
        }
    }
    Component {
        id:icons
        ColumnLayout {
            spacing:12
            Controls.SettingsCard {title:"Стиль значков";description:"Original сохраняет цветные иконки. Pixel Themed использует symbolic, Material-категорию или монограмму.";Controls.IconStylePicker {actions:settingsActions}}
            Controls.SettingsCard {title:"GoogleDot Cursor";description:"Black / White · 24, 28, 32 px\nТребуется ручная установка темы. PixelRail не меняет системный курсор.";Ui.PixelIcon {name:"mouse";size:28;color:colors.accent} Controls.ControlLabel {Layout.fillWidth:true;text:"Справка: docs/design/cursor.md";font.pixelSize:12;color:colors.muted}}
        }
    }
    Component {
        id:notifications
        Controls.SettingsCard {title:"Уведомления";description:"Переключение использует существующий безопасный D-Bus backend.";Controls.ControlButton {Layout.fillWidth:true;tonal:true;symbol:"notifications";text:"Открыть историю";onClicked:root.controller.selectSection("notifications")} Controls.ControlButton {Layout.fillWidth:true;text:"PixelRail Notifications";onClicked:settingsActions.request("notifications","pixelrail")} Controls.ControlButton {Layout.fillWidth:true;text:"SwayNC fallback";onClicked:settingsActions.request("notifications","swaync")}}
    }
    Component {
        id:input
        Controls.SettingsCard {title:"Раскладка";description:"us / ru · переключение Alt+Shift";Controls.ControlButton {Layout.fillWidth:true;tonal:true;symbol:"language";text:root.controller.keyboardState.label;enabled:root.controller.keyboardState.available;onClicked:root.controller.toggleKeyboard()}}
    }
    Component {
        id:effects
        ColumnLayout {
            spacing:12
            Controls.SettingsCard {title:"Анимации";Controls.ControlButton {objectName:"settings-animations";Layout.fillWidth:true;tonal:true;text:Theme.ThemeManager.animations ? "Включены" : "Выключены";active:Theme.ThemeManager.animations;onClicked:settingsActions.request("animations",Theme.ThemeManager.animations ? "false" : "true")}}
            Controls.SettingsCard {title:"Графический профиль";description:"Меняет эффекты Hyprland. CPU, GPU и системное питание не затрагиваются.";RowLayout {Layout.fillWidth:true;spacing:4;Repeater {model:["battery","performance"];delegate:Controls.ControlButton {required property string modelData;Layout.fillWidth:true;Layout.preferredWidth:1;tonal:true;text:modelData==="battery" ? "Battery" : "Performance";active:root.controller.profile===modelData;onClicked:settingsActions.request("profile",modelData)}}}}
        }
    }
    Component {
        id:shortcuts
        Controls.SettingsCard {title:"Сочетания клавиш";description:"Единый список текущих биндов Hyprland, с поиском. Без отдельной копии в Settings.";RowLayout {Ui.Keycap {text:"Super + /"} Ui.Keycap {text:"Super + F1"}} Controls.ControlButton {Layout.fillWidth:true;tonal:true;symbol:"keyboard";text:"Открыть список";onClicked:root.controller.menuRequested("keys")}}
    }
    Component {
        id:about
        Controls.SettingsCard {title:"PixelRail v3.1.0 · кандидат";description:"Pixel Experience · Material You\nHyprland 0.57 · Quickshell 0.3.2";Controls.ControlLabel {Layout.fillWidth:true;text:"Roboto · SIL OFL\nMaterial Symbols · Apache-2.0\nНезависимый проект, не продукт Google.";color:colors.muted;font.pixelSize:12}}
    }
}
