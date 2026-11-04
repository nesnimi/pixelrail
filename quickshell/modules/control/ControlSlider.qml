import QtQuick
import "../../ui" as Ui
import QtQuick.Controls
import "../../theme" as Theme
Slider {
    id: root
    Theme.Palette {id:colors}
    from:0;to:1
    implicitHeight:Ui.Tokens.controlSliderHeight
    leftPadding:0;rightPadding:0;topPadding:0;bottomPadding:0
    background: Rectangle {
        objectName:"pixel-slider-track"
        x:root.leftPadding;y:root.topPadding+root.availableHeight/2-height/2
        width:root.availableWidth;height:Ui.Tokens.controlSliderTrack;radius:height/2
        color:colors.surfaceVariant;opacity:root.enabled ? 1 : Ui.Tokens.disabledOpacity
        Rectangle {width:root.visualPosition*parent.width;height:parent.height;radius:height/2;color:colors.primary}
        Rectangle {anchors.fill:parent;radius:parent.radius;color:"transparent";border.width:root.visualFocus ? 2 : 0;border.color:colors.primary}
    }
    handle: Rectangle {
        x:root.leftPadding+root.visualPosition*(root.availableWidth-width)
        y:root.topPadding+root.availableHeight/2-height/2
        width:Ui.Tokens.controlSliderHandle;height:Ui.Tokens.controlSliderTrack-8;radius:width/2
        color:root.visualPosition*root.availableWidth<width ? colors.primary : colors.primaryText
        opacity:root.enabled ? 1 : Ui.Tokens.disabledOpacity
    }
}
