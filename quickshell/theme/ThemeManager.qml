pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import "Fallback.js" as Fallback

Scope {
    id: root
    readonly property string configPath: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/pixelrail/theme.json"
    readonly property string palettePath: (Quickshell.env("XDG_CACHE_HOME") || Quickshell.env("HOME") + "/.cache") + "/pixelrail/theme/palette.json"
    property string helper: Quickshell.env("PIXELRAIL_THEME_HELPER") || Quickshell.shellPath("../scripts/pixelrail-theme")
    property var configuration: ({mode: "dark", accent: null})
    property var schemes: Fallback.schemes
    property string lastError: ""
    property string lastSettingsText: ""
    property string lastPaletteText:""
    property bool pending: false
    readonly property bool busy: generator.running
    readonly property string configuredMode: configuration.mode || "dark"
    readonly property string mode: configuredMode === "auto" ? (Qt.styleHints.colorScheme === Qt.ColorScheme.Light ? "light" : "dark") : configuredMode
    readonly property string iconStyle:configuration.iconStyle==="themed" ? "themed" : "original"
    readonly property bool animations:configuration.animations!==false
    readonly property bool isDark: mode === "dark"
    readonly property var required: ["primary", "onPrimary", "primaryContainer", "onPrimaryContainer", "secondary", "onSecondary", "secondaryContainer", "onSecondaryContainer", "tertiary", "onTertiary", "background", "onBackground", "surface", "onSurface", "surfaceContainer", "surfaceContainerHigh", "surfaceVariant", "onSurfaceVariant", "outline", "outlineVariant", "error", "onError"]

    // Avoid onX QML property names: they are treated as handler bindings and
    // can retain the default black color. JSON role names remain standard MD3.
    readonly property color primary: root.role("primary")
    readonly property color primaryText: root.role("onPrimary")
    readonly property color primaryContainer: root.role("primaryContainer")
    readonly property color primaryContainerText: root.role("onPrimaryContainer")
    readonly property color secondary: root.role("secondary")
    readonly property color secondaryText: root.role("onSecondary")
    readonly property color secondaryContainer: root.role("secondaryContainer")
    readonly property color secondaryContainerText: root.role("onSecondaryContainer")
    readonly property color tertiary: root.role("tertiary")
    readonly property color tertiaryText: root.role("onTertiary")
    readonly property color background: root.role("background")
    readonly property color backgroundText: root.role("onBackground")
    readonly property color surface: root.role("surface")
    readonly property color surfaceText: root.role("onSurface")
    readonly property color surfaceContainer: root.role("surfaceContainer")
    readonly property color surfaceContainerHigh: root.role("surfaceContainerHigh")
    readonly property color surfaceVariant: root.role("surfaceVariant")
    readonly property color surfaceVariantText: root.role("onSurfaceVariant")
    readonly property color outline: root.role("outline")
    readonly property color outlineVariant: root.role("outlineVariant")
    readonly property color error: root.role("error")
    readonly property color errorText: root.role("onError")

    function role(name: string): color { return (schemes[mode] || Fallback.schemes[mode])[name] || Fallback.schemes[mode][name]; }
    function contrast(first, second): real {
        function luminance(hex) {
            const values = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
                .map(value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
            return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
        }
        const a = luminance(first), b = luminance(second);
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    }
    function valid(value): bool {
        const pairs = [["surface", "onSurface"], ["surfaceVariant", "onSurfaceVariant"],
            ["primary", "onPrimary"], ["primaryContainer", "onPrimaryContainer"],
            ["secondary", "onSecondary"], ["secondaryContainer", "onSecondaryContainer"],
            ["tertiary", "onTertiary"], ["background", "onBackground"], ["error", "onError"],
            ["surfaceContainer", "onSurface"], ["surfaceContainerHigh", "onSurface"]];
        return value && ["dark", "light"].every(mode => value[mode]
            && required.every(name => /^#[0-9a-fA-F]{6}$/.test(value[mode][name] || ""))
            && pairs.every(pair => root.contrast(value[mode][pair[0]], value[mode][pair[1]]) >= 4.5));
    }
    function rearm(view): void {
        // Atomic rename removes a QFileSystemWatcher file watch. Explicitly attach
        // again to the new inode, then reload once more to cover changes in the gap.
        view.watchChanges = false;
        view.reload();
        Qt.callLater(() => { view.watchChanges = true; view.reload(); });
    }
    function reload(): void { rearm(configFile); rearm(paletteFile); }
    function requestSync(): void { pending = true; Qt.callLater(kick); }
    function kick(): void {
        if (generator.running || !pending) return;
        pending = false;
        generator.command = [helper, "sync"];
        generator.running = true;
    }
    FileView {
        id: configFile
        path: root.configPath
        watchChanges: true
        preload: true
        blockLoading: false
        printErrors: false
        onFileChanged: root.rearm(configFile)
        onLoaded: {
            const value = text();
            if (value === root.lastSettingsText) return;
            try {
                const data = JSON.parse(value);
                if (!["dark", "light", "auto"].includes(data.mode || "dark")) throw new Error("mode");
                if(data.iconStyle!==undefined && !["original","themed"].includes(data.iconStyle))throw new Error("iconStyle");
                if(data.animations!==undefined && typeof data.animations!=="boolean")throw new Error("animations");
                const colorsChanged=root.lastSettingsText==="" || (root.configuration.mode || "dark")!==(data.mode || "dark") || (root.configuration.accent || null)!==(data.accent || null);
                root.configuration = data;
                root.lastSettingsText = value;
                if(colorsChanged)root.requestSync();
            } catch (error) { root.lastError = "Некорректный theme.json"; }
        }
    }
    FileView {
        id: paletteFile
        path: root.palettePath
        watchChanges: true
        preload: true
        blockLoading: false
        printErrors: false
        onFileChanged: root.rearm(paletteFile)
        onLoaded: {
            try {
                const value=text();
                if(value.length && value===root.lastPaletteText)return;
                const data = JSON.parse(value);
                if (data.schema !== 1 || !root.valid(data.schemes)) throw new Error("palette");
                root.schemes = data.schemes;
                root.lastPaletteText=value;
            } catch (error) { root.lastError = "Некорректная палитра; сохранены предыдущие цвета"; }
        }
    }
    Process {
        id: generator
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.lastError = result.error || result.warning || "";
                    if (result.status === "superseded") root.pending = true;
                } catch (error) { root.lastError = "Не удалось обновить Material You"; }
            }
        }
        onExited: (code, status) => {
            root.reload();
            Qt.callLater(root.kick);
        }
    }
    Component.onCompleted: requestSync()
}
