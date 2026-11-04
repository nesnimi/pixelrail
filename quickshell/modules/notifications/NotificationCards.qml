pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import "../control" as Controls
import "../../theme" as Theme
import "../../ui" as Ui
ColumnLayout {
    id:root
    required property var manager
    property bool toast:false
    signal openRequested()
    spacing:Ui.Tokens.spaceSm
    Theme.Palette {id:colors}
    Repeater {
        model:!root.manager ? [] : root.toast ? root.manager.history.filter(entry=>root.manager.popups.includes(entry.id)).slice(0,1) : root.manager.history
        delegate: Rectangle {
            id:card
            required property var modelData
            property bool expanded:false
            objectName:"notification-card-"+modelData.id
            Layout.fillWidth:true;implicitHeight:details.implicitHeight+Ui.Tokens.spaceMd*2
            radius:Ui.Tokens.radiusLg;color:hover.hovered ? Qt.tint(colors.surfaceContainerHigh,Qt.alpha(colors.accent,.06)) : colors.surfaceContainerHigh
            HoverHandler {id:hover}
            MouseArea {id:toastClick;anchors.fill:parent;enabled:root.toast;onClicked:root.openRequested()}
            scale:toastClick.pressed ? .99 : 1
            Behavior on scale {NumberAnimation {duration:Ui.Tokens.hover;easing.type:Easing.OutCubic}}
            ColumnLayout {
                id:details;anchors {left:parent.left;right:parent.right;top:parent.top;margins:Ui.Tokens.spaceMd} spacing:Ui.Tokens.spaceSm
                RowLayout {
                    spacing:Ui.Tokens.spaceSm
                    Ui.PixelAppIcon {size:30;iconName:card.modelData.icon || "";appName:card.modelData.app}
                    Controls.ControlLabel {Layout.fillWidth:true;text:card.modelData.app;font.pixelSize:Ui.Tokens.label;color:colors.muted;maximumLineCount:1;elide:Text.ElideRight}
                    Controls.ControlLabel {objectName:"notification-time";visible:!root.toast;text:Qt.formatDateTime(new Date(card.modelData.time),"dd.MM HH:mm");font.pixelSize:Ui.Tokens.caption;color:colors.muted}
                    Controls.ControlButton {objectName:"notification-remove-"+card.modelData.id;symbol:"close";Accessible.name:root.toast ? "Скрыть всплывающее уведомление" : "Удалить уведомление";implicitWidth:32;implicitHeight:32;onClicked:root.toast ? root.manager.hidePopup(card.modelData.id) : root.manager.remove(card.modelData.id)}
                }
                Controls.ControlLabel {id:summary;Layout.fillWidth:true;text:card.modelData.summary;font.weight:Font.Medium;wrapMode:Text.WrapAnywhere;maximumLineCount:root.toast ? 2 : card.expanded ? 1000 : 3;elide:Text.ElideRight}
                Controls.ControlLabel {id:body;objectName:"notification-body-"+card.modelData.id;Layout.fillWidth:true;visible:text!=="";text:card.modelData.body;font.pixelSize:Ui.Tokens.controlPercent;wrapMode:Text.WrapAnywhere;maximumLineCount:root.toast ? 2 : card.expanded ? 1000 : 12;elide:Text.ElideRight}
                Controls.ControlButton {objectName:"notification-expand-"+card.modelData.id;visible:!root.toast && (card.expanded || summary.truncated || body.truncated);text:card.expanded ? "Свернуть" : "Показать полностью";tonal:true;onClicked:card.expanded=!card.expanded}
                Flow {
                    id:actions;Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm;visible:!root.toast
                    Repeater {
                        model:card.modelData.live ? card.modelData.live.actions.slice(0,6) : []
                        delegate: Controls.ControlButton {required property var modelData;required property int index;objectName:"notification-action-"+card.modelData.id+"-"+index;tonal:true;width:Math.min(implicitWidth,actions.width);implicitHeight:Math.max(Ui.Tokens.controlChipHeight,contentItem.implicitHeight+Ui.Tokens.spaceMd);text:modelData.text.slice(0,128);onClicked:root.manager.invoke(card.modelData.id,index)}
                    }
                }

            }
        }
    }
}
