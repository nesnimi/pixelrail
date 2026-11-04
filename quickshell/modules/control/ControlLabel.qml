import QtQuick
import "../../ui" as Ui
import "../../theme" as Theme
Text {Theme.Palette {id:colors} color:colors.text;wrapMode:Text.Wrap;textFormat:Text.PlainText;font {family:colors.font;pixelSize:Ui.Tokens.body}}
