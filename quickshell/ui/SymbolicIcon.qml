import QtQuick
import QtQuick.Effects
// Loaded only for opted-in symbolic icons on an RHI renderer.
MultiEffect {
    property var artwork:null
    property color tint:"white"
    source:artwork;colorization:1;colorizationColor:tint
    blurEnabled:false;shadowEnabled:false
}
