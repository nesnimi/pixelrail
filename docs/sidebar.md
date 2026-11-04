# Pixel Sidebar — v3.1 RC2 (компоновка v3.0)

Один PanelWindow в существующем qs, видимая rail 54 logical px; прежнее окно и
exclusive zone 66 px сохранены. Скругления/Material You/положение не менялись.

RC2 возвращает исходный векторный знак PixelRail из `SidebarLogic.svg("home")`
(история `ded86e7`), без шрифтовой P. Цвет следует Material You. Power и Wi-Fi
используют Material Symbols Rounded Outlined по 22 px; Wi-Fi получил официальный
оптически более лёгкий wght200. Активный workspace — `primaryContainer` и
`primaryContainerText`, hover — тональная поверхность. При малой высоте символы
уменьшаются, а приложения по-прежнему прокручиваются отдельно.

Верх строго: **Power → Wi-Fi → Battery%**. Power открывает меню питания,
Wi-Fi — подробности в Control Center. Battery — только процент либо «—» при
отсутствии данных; подробности BAT0/BAT1 в tooltip. Звук, уведомления, профиль,
часы/дата удалены только из Sidebar; функции доступны через Super+A/N и shortcuts.
Раскладка EN/RU находится только в Quick Settings.

Затем большое гибкое пустое пространство. Низ сохранён: постоянные workspace
1–5, дополнительно активный workspace >5, окна текущего workspace данного
монитора, **P последним у нижнего края**. Скроллится только список приложений.
Пустые workspace не создаются ради отображения; клик выполняет Lua focus
через hyprctl eval и проверяет ответ ok. Окна фильтруются по workspace, служебные
Quickshell исключены; каждое окно имеет отдельную иконку и focus по address.
DesktopEntries/icon theme/fallback сохранены.

## Источники и режимы

Hyprland events обновляют модели workspace/toplevels; Networking и UPower —
состояния сети/батареи. BAT0/BAT1 агрегируются по энергии/ёмкости либо достоверному
UPower aggregate, не средним арифметическим процентов. Отсутствие BAT0 допускается.
Shared SystemControls обслуживает аудио для Control Center/OSD; собственных
аудиоконтролов и часов у Sidebar теперь нет.

```bash
pixelrail-panel mode sidebar
pixelrail-panel mode waybar
pixelrail-panel status
```

Первый install оставляет Waybar. Deploy не переключает выбранный режим.
В waybar mode Sidebar unloaded, не резервирует место и не перехватывает мышь.
Managed Waybar определяется по владению, чужие процессы не завершаются.
IPC: panel.prepare/activate/hide/state, запуск через существующий pixelrail-shell.
Не запускайте вторую копию qs для панели.

## Проверки

```bash
python3 tests/settings.py
python3 tests/sidebar-runtime.py
python3 tests/qt-ui.py
python3 tests/panel.py
```

Runtime проверяет реальный native Hyprland API на private socket fixture:
1→2→3→5→1, пустые workspace, окно на другом workspace/мониторе, перенос/закрытие,
focus по address, отказ dispatcher, layout и последний P. Qt проверяет контраст,
иконки и агрегирование батарей. Эти тесты не являются физической проверкой T480.

Ручная приёмка: 1366×768 и HiDPI, три верхних элемента в нужном порядке,
нижние workspace/P и скролл app-list, Chrome на 1/Kitty на 3, два окна одного
приложения, внешний монитор, возврат к Waybar, reload темы Dark/Light/Auto.
[Установка](installation.md), [восстановление](recovery.md).

В v3.1 системные значки используют Material Symbols Rounded, шрифт общий через
Ui.Tokens. Стиль приложений переключается в Settings → Иконки, либо
`pixelrail-theme ui iconStyle original|themed`; layout/zone не менялись.
