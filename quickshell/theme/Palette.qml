import QtQuick
import "../ui" as Ui

// Lightweight compatibility facade: every component binds to the same singleton.
QtObject {
    readonly property color primary: ThemeManager.primary
    readonly property color primaryText: ThemeManager.primaryText
    readonly property color primaryContainer: ThemeManager.primaryContainer
    readonly property color primaryContainerText: ThemeManager.primaryContainerText
    readonly property color secondary: ThemeManager.secondary
    readonly property color secondaryText: ThemeManager.secondaryText
    readonly property color secondaryContainer: ThemeManager.secondaryContainer
    readonly property color secondaryContainerText: ThemeManager.secondaryContainerText
    readonly property color tertiary: ThemeManager.tertiary
    readonly property color tertiaryText: ThemeManager.tertiaryText
    readonly property color backgroundText: ThemeManager.backgroundText
    readonly property color surfaceText: ThemeManager.surfaceText
    readonly property color surfaceContainer: ThemeManager.surfaceContainer
    readonly property color surfaceContainerHigh: ThemeManager.surfaceContainerHigh
    readonly property color surfaceVariant: ThemeManager.surfaceVariant
    readonly property color surfaceVariantText: ThemeManager.surfaceVariantText
    readonly property color outlineVariant: ThemeManager.outlineVariant
    readonly property color error: ThemeManager.error
    readonly property color errorText: ThemeManager.errorText
    readonly property color background: ThemeManager.background
    readonly property color surface: ThemeManager.surface
    readonly property color surfaceHigh: ThemeManager.surfaceContainerHigh
    readonly property color selected: ThemeManager.secondaryContainer
    readonly property color selectedText: ThemeManager.secondaryContainerText
    readonly property color text: ThemeManager.surfaceText
    readonly property color muted: ThemeManager.surfaceVariantText
    readonly property color accent: ThemeManager.primary
    readonly property color outline: ThemeManager.outline
    readonly property string font: Ui.Tokens.font
}
