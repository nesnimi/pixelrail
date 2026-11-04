# Архитектура PixelRail — кандидат v3.0

Один процесс Quickshell 0.3.2, одна точка входа `quickshell/shell.qml`.
Hyprland 0.57 Lua управляет композитором и 95 существующими биндами. Исходники
end4 не копировались. Rofi не вызывается; старые имена wrapper сохранены для совместимости.

| Слой | Ответственность |
|---|---|
| modules/launcher | Launcher, поиск DesktopEntries, Super IPC |
| components/PanelController + modules/sidebar | lazy Sidebar, workspace/window events, exclusive zone |
| components/ControlController + modules/control | одно окно, Settings/Notifications, nested pages, resize |
| modules/system | общий PipeWire/brightness, live slider coalescing, OSD, session events |
| modules/notifications | ленивый NotificationServer, bounded history, DND/popups |
| components/MenuPanel, ClipboardView, WallpaperView | native меню, thumbnails, навигация |
| theme/ThemeManager | semantic palette, atomic FileView reload, fallback/контраст |
| native/PixelRail/DBusLease | notification lease для qs 0.3.2, backlight netlink, passive logind/BlueZ |
| scripts | короткие IPC routers, backend helpers, lifecycle/deployment, audit/benchmark |

## Запуск и владение

`hyprland.start` → `pixelrail-start` → `pixelrail-shell` → lifecycle lock/registry/IPC.
Повторный старт переиспользует готовый процесс. Управляемые релизы определяются
по manifest/точному пути; executable name не служит основанием для kill.
Panel mode и notifications mode сохраняются отдельно; первая установка оставляет
Waybar/SwayNC. Native notification takeover — явная транзакция с проверкой владельца,
не глобальное отключение службы. Clipboard watcher использует собственную блокировку.
PipeWire/WirePlumber управляются существующим systemd --user, не Hyprland autostart.

## События и производительность

Hyprland event socket: workspaces/toplevels/activelayout/focus. Keyboard-state
читает действительное active_keymap и выполняет re-query после switchxkblayout.
NetworkManager, UPower, PipeWire, BlueZ, MPRIS используют существующие модели qs.
Backlight: kernel netlink + QSocketNotifier, без polling/демона. Logind resume
закрывает transient окна, обновляет brightness/theme; смена BlueZ ownership
обновляет открытые настройки. Hotplug закрывает временные панели; screen bindings
пересчитывают позицию и ограничивают высоту. Реальный suspend/hotplug — ручная приёмка.
Один minute clock живёт в открытом Control Center; таймеры throttling/OSD конечные.

## Данные и установка

Release содержит код, не пользовательские настройки. XDG config/cache/state
сохраняются при deploy/rollback; подробности в тематических документах. Theme JSON,
настройки панели/Control Center и графический profile записываются атомарно.
Deploy: dry-run default, backup, новый release, readiness IPC, commit ссылок,
retire старого; failed apply возвращает файлы. Manifest записывается atomic replace.
Rollback сохраняет release и backup, проверяет изменения пользователя.
Native .so пересобирается под текущий Qt; его отсутствие блокирует apply заранее.

[Установка](installation.md), [восстановление](recovery.md),
[Control Center](control-center.md), [OSD](osd.md), [производительность](performance.md).
