# Сочетания PixelRail

Источник истины: `hypr/pixelrail-end4-keys.lua` и `pixelrail-super-tap.lua`.
Регрессионный тест ожидает 95 уникальных биндов; v2.7 новых биндов не добавляет.

| Клавиши | Действие |
|---|---|
| одиночный Super / Super+Space | существующий Launcher снизу слева |
| Super+A | Quick Settings; повтор закрывает |
| Super+N | Notifications; повтор закрывает |
| Super+/ / Super+F1 | справка по сочетаниям |
| Super+G / Super+I | Quick Actions |
| Super+V | Clipboard History с изображениями |
| Super+R | команды |
| Super+Tab | Window Switcher |
| Super+Ctrl+T | Wallpaper Picker |
| Super+Ctrl+P | графический Battery/Performance |
| Super+J | текущая панель: показать/скрыть |
| Super+1…0 | workspace 1…10 |
| Super+Alt+1…0 | перенести окно на workspace |
| Super+Q / Super+D / Super+F | закрыть / maximize / fullscreen |
| Super+Return / Super+T | Kitty |
| Super+W | браузер |
| Alt+Shift | системное переключение us/ru (сохранено) |
| XF86MonBrightnessUp/Down | яркость ±5%, реальный readback и OSD |
| XF86AudioRaise/LowerVolume | громкость ±5 п.п., лимит raise 100%, OSD |
| XF86AudioMute | mute/unmute и OSD |
| Escape | закрыть активную панель |

Super+Q/D и другие сочетания отменяют одиночный Super. FnLock/физические keysym
зависят от оборудования: PixelRail не меняет firmware или раскладки. Справка
Super+/ получает фактические описания зарегистрированных биндов. Полная проверка:
`lua tests/binds.lua`, `lua tests/super-tap.lua`. Физические нажатия проверяются вручную.
