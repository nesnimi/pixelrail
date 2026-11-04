# PixelRail v3.1 RC1 — implementation report

**RC1 подготовлен для ручной приёмки. Не Stable.** Deploy/rollback в реальном HOME,
sudo, службы, драйверы, power policies, git commit/tag/push не выполнялись.
Исходное незакоммиченное v3.0 сохранено; reference PNG пользователя не менялись.

## 1. Реализовано

Общий Ui.Tokens + прежний ThemeManager/Palette; coverage-aware typography;
offline Material Symbols; Sidebar states/P; Pixel tiles/controls; Notifications
cards/source icons/empty state; Launcher 2.0 visual shell; original/themed app icons;
лёгкие Settings, CLI/.desktop; reduced motion; Clipboard/Wallpaper/OSD polish.
Search.js, app execution, IPC, Super, 95 биндов, native notification ownership,
clipboard bytes, swaybg и lifecycle сохранены. `brightnessctl -n 1` не возвращён.

## 2. Два референса

Взяты rounded tonal surfaces, крупные Wi-Fi/BT symbols, pill controls, компактные
системные строки, читаемые подписи и динамический accent. Не копировались
генеративные ошибки: Sidebar не 64, Notifications отдельная вкладка, volume и
Battery/Performance сохранены, resize handle остаётся. Нет фиксированной фиолетовой
темы или вмешательства в Chrome. Surface/text пары берутся из MD3 palette.

## 3. Размеры и tokens

| Назначение | Значения logical px |
|---|---|
| Spacing | 4 / 8 / 12 / 16 / 20 / 24 |
| Radius | 8 / 12 / 16 / 20 / 26 / pill |
| Typography | caption 11, label 12, body 14, section 16, title 20, display 26 |
| Icons | 20–24 базовые, tile 26, empty-state 36 |
| Sidebar | rail 54, окно/exclusive zone 66; layout/position сохранены |
| Launcher | 540, max 5 результатов по 50, новая section label; max-height screen−24 |
| Control Center | 400, default 50%, resize 30–75%, bottom handle сохранён |
| OSD | 280×72, output-only pill, timeout 1300 ms |
| Motion | pressed 120, state token 160, panels 200, reduced motion 0 |

JSON `onSurface/onPrimary/...` остаются семантическими MD3 ролями. QML использует
совместимые surfaceText/primaryText/primaryContainerText и т.д.: прежняя ошибка
специальных onX имён не возвращается. Цвет фона и контрастный текст меняются
одновременно; нет ColorAnimation между несовместимыми foreground/background.
Тяжёлого blur/shadow нет; тень — только token, не новый эффект на каждом элементе.

## 4. Шрифты

Официальный Roboto variable upright включён в assets (488584 bytes), SIL OFL 1.1,
лицензия рядом. fc-query подтвердил Latin и Cyrillic 0400–0486. Native PixelTypography
предпочитает установленный Google Sans Flex, только если QRawFont покрывает
ASCII, А–я, Ё/ё; затем Roboto. FontLoader предоставляет bundled Roboto; при ошибке
— системный sans-serif. Native default font задаётся **только процессу qs**, включая
stock controls/tooltips, не меняет системный fontconfig/другие приложения.

[Roboto source/OFL](https://github.com/google/fonts/tree/main/ofl/roboto),
[Google Sans Flex/OFL](https://github.com/googlefonts/googlesans-flex).
Google Sans Flex не скачивался и не устанавливался в систему.

## 5. Material Symbols Rounded

31 icon × outlined/filled = 62 SVG, optical 24, weight 400, из официального Google
репозитория; Apache-2.0, LICENSE/SOURCE.md/checksums.json в assets. Paths не менялись,
fill определяется Palette. PixelIcon: name/size/color/filled/disabled, HiDPI sourceSize,
fallback apps; color-string cache ограничен 96 записями, проверен QtTest.

[Источник](https://github.com/google/material-design-icons),
[лицензия и руководство](https://developers.google.com/fonts/docs/material_symbols).
Symbol font не требуется; никаких tofu/лигатур из отсутствующего font package.

## 6. Иконки приложений

Оригинальные — существующая icon theme/DesktopEntries, цветные изображения не tint-ятся.
Themed — только явно названные *-symbolic варианты, tint через маленький lazy
MultiEffect без blur/shadow; иначе tonal initial/Material apps fallback. В software
renderer — монограмма, а не пустой shader output. Нет перерисовки сложного
оригинального PNG одним цветом. Source broken/missing также получает fallback.

Один PixelAppIcon в Sidebar, Launcher, Window Switcher; ThemeManager.iconStyle
обновляет их без рестарта. Live переключение/память настроек подтверждены Qt UI;
совместное переключение Sidebar/Launcher подтверждено capture test. Цветовой
RHI-render symbolic требует ручной проверки на Intel UHD; fake успех не заявляется.

## 7. GoogleDot

GPLv3 проверена по [upstream](https://github.com/ful1e5/Google_Cursor), копия лицензии
в GoogleDot-LICENSE.txt. `pixelrail-cursor status/prepare` поддерживает Black/White,
24/28/32, выдаёт только offline Lua/env/GTK preview внутри репозитория/release.
Lua preview проверен реальным Hyprland parser в sandbox. Темы отсутствуют локально,
бинарники не скачивались и не устанавливались; applied=false.

Settings содержит честную инструкцию, **не фиктивный переключатель курсора**.
Полное системное применение остаётся ручным: GTK/Qt/XWayland env, XCursor против
Hyprcursor и разные DPI требуют проверки владельца. [Инструкция](cursor.md).
Курсор не имитируется QML-картинкой. Это незавершённый системный шаг приёмки.

## 8. PixelRail Settings

Кнопка в Quick Settings → lazy page того же Window/процесса. Также
`pixelrail-settings` и .desktop; deploy подставляет абсолютный Exec/TryExec,
не зависит от PATH. Categories: appearance, Sidebar, Launcher, icons, cursor,
notifications, input, effects, hotkeys, about.

Рабочие операции: Dark/Light/Auto, wallpaper/manual HEX/reset accent,
original/themed icons, animations, графический Battery/Performance, Sidebar/Waybar,
native/SwayNC, реальные keyboard toggle и открытие keys/wallpaper. Launcher/cursor
страницы не выдумывают неподдерживаемые настройки. Backend operations async,
serialized/coalesced по ключу, ошибки видимы. Bluetooth actions подтверждаются
сигналами connected/paired или ограниченным deadline; ошибки короткие, сканирование
и системный pairing-agent сохранены. Службы не менялись.

UI preferences расширяют XDG `pixelrail/theme.json`: iconStyle, animations, uiVersion=1.
Отсутствующие поля = original / true. Unknown keys и mode/accent сохраняются,
запись atomic под прежним lock. UI-only changes не запускают matugen. Height/DND
остаются desktop.json, неизвестные ключи там теперь тоже сохраняются.
После restart стиль/animations/height проверены. Старые helper до v3.1 могут
потерять новые UI поля при **последующей ручной записи** темы после rollback;
сам rollback config/cache не изменяет. Сохраните theme.json перед работой со старой веткой.

```bash
pixelrail-theme ui iconStyle themed
pixelrail-theme ui iconStyle original
pixelrail-theme ui animations false
pixelrail-theme mode auto
pixelrail-theme accent '#AABBCC'
pixelrail-theme accent reset
```

## 9. Изменённые файлы

Список рабочего дерева включает сохранённый незакоммиченный v3.0, не только v3.1.
Ignored native .so — локальный build artifact, не добавлен в Git.

- `CHANGELOG.md`
- `README.md`
- `docs/architecture.md`
- `docs/bluetooth.md`
- `docs/control-center.md`
- `docs/design/GoogleDot-LICENSE.txt`
- `docs/design/cursor.md`
- `docs/design/pixelrail-v3.1-implementation-report.md`
- `docs/design/pixelrail-v3.1-ui-spec.md`
- `docs/installation.md`
- `docs/launcher.md`
- `docs/osd.md`
- `docs/performance.md`
- `docs/popup-placement.md`
- `docs/recovery.md`
- `docs/release-candidate-report.md`
- `docs/shortcuts.md`
- `docs/sidebar.md`
- `docs/troubleshooting.md`
- `hypr/pixelrail-end4-keys.lua`
- `quickshell/assets/checksums.json`
- `quickshell/assets/fonts/OFL.txt`
- `quickshell/assets/fonts/Roboto.ttf`
- `quickshell/assets/fonts/SOURCE.md`
- `quickshell/components/ClipboardView.qml`
- `quickshell/components/ControlController.qml`
- `quickshell/components/MenuPanel.qml`
- `quickshell/components/WallpaperView.qml`
- `quickshell/modules/control/BluetoothActions.qml`
- `quickshell/modules/control/BluetoothLogic.js`
- `quickshell/modules/control/ControlButton.qml`
- `quickshell/modules/control/ControlCenter.qml`
- `quickshell/modules/control/ControlLabel.qml`
- `quickshell/modules/control/ControlSlider.qml`
- `quickshell/modules/control/ControlTile.qml`
- `quickshell/modules/control/KeyboardState.qml`
- `quickshell/modules/control/LiveSlider.qml`
- `quickshell/modules/control/SettingsActions.qml`
- `quickshell/modules/control/SettingsPage.qml`
- `quickshell/modules/control/qmldir`
- `quickshell/modules/launcher/Launcher.qml`
- `quickshell/modules/notifications/NotificationCards.qml`
- `quickshell/modules/notifications/NotificationController.qml`
- `quickshell/modules/sidebar/Sidebar.qml`
- `quickshell/modules/sidebar/SidebarButton.qml`
- `quickshell/modules/sidebar/SidebarServices.qml`
- `quickshell/modules/system/OsdController.qml`
- `quickshell/modules/system/SessionState.qml`
- `quickshell/modules/system/SystemControls.qml`
- `quickshell/modules/system/SystemOsd.qml`
- `quickshell/modules/system/SystemState.qml`
- `quickshell/modules/system/qmldir`
- `quickshell/native/PixelRail/DBusLease/backlightwatch.hpp`
- `quickshell/native/PixelRail/DBusLease/lease.cpp`
- `quickshell/shell.qml`
- `quickshell/theme/Palette.qml`
- `quickshell/theme/ThemeManager.qml`
- `quickshell/ui/PixelAppIcon.qml`
- `quickshell/ui/PixelIcon.qml`
- `quickshell/ui/SymbolicIcon.qml`
- `quickshell/ui/Symbols.js`
- `quickshell/ui/Tokens.qml`
- `quickshell/ui/qmldir`
- `scripts/build-native.sh`
- `scripts/control.py`
- `scripts/deployment.py`
- `scripts/desktop.py`
- `scripts/material_you.py`
- `scripts/pixelrail-cursor`
- `scripts/pixelrail-desktop`
- `scripts/pixelrail-menu-data`
- `scripts/pixelrail-profile`
- `scripts/pixelrail-settings`
- `scripts/pixelrail-system`
- `share/applications/pixelrail-settings.desktop`
- `tests/autostart.py`
- `tests/benchmark-runtime.py`
- `tests/binds.lua`
- `tests/clipboard-wayland.py`
- `tests/control-runtime.py`
- `tests/control-ui.py`
- `tests/deployment.py`
- `tests/design-screenshots.py`
- `tests/design-settings.py`
- `tests/fixtures/sidebar_hyprland.py`
- `tests/keyboard-runtime.py`
- `tests/lifecycle-runtime.py`
- `tests/material-you-runtime.py`
- `tests/release-reliability.py`
- `tests/runtime-menus.py`
- `tests/session-events.py`
- `tests/settings.py`
- `tests/sidebar-runtime.py`
- `tests/smoke-quickshell.py`
- `tests/system-native.py`
- `tests/system-runtime.py`
- `tests/system-ui.py`
- `tests/system.py`
- `tests/tst_design.qml`
- `tests/tst_settings.qml`
- `quickshell/assets/symbols/`: 62 SVG, LICENSE, SOURCE.md.
- `docs/design/screenshots/`: 7 реальных Qt-rendered PNG.

## 10. Тесты

35 Python scenario suites полного regression — PASS; последующие target checks
после финальной полировки также PASS (Control UI/persistence, Bluetooth confirmation,
Qt UI, native events/plugin, screenshots, deployment/failure/rollback/lifecycle).
QtTest: 9 PASS; Qt6 qmllint exit 0 с известными static metadata warnings, syntax и
`git diff --check` PASS; 95 unique bindings/Super-tap PASS.

Проверены IPC, A/N, Escape/focus, placement/1366×768, Sidebar top order/P, Native
NotificationServer/ownership/DND/actions, Wallpaper/Clipboard images, real payload,
live sliders/OSD/Fn routes, EN/RU events, Material You Dark/Light/Auto/accent,
UI style persistence/unknown-key migration/cache bound, autostart, native plugin,
Power Audit/Benchmark, deploy/rollback в test HOME. Не было live deploy.

Первые три старых fixtures не включали ui/assets; обновлены. Один тест искал панель
по radius=24 — теперь по semantic objectName. Реальные ошибки не скрывались.
Артефакты: `.cache/v31-tests/verified-results.json` + targeted logs той же папки.

## 11. Производительность

| Операция | v3.0 median/p95 ms | v3.1 median/p95 ms |
|---|---:|---:|
| control_state_IPC | 29.01 / 30.21 | 29.33 / 30.62 |
| launcher_open_state_close | 86.85 / 89.61 | 86.90 / 88.96 |
| A_to_N_state | 58.03 / 58.73 | 58.54 / 60.20 |
| N_to_A_state | 57.97 / 58.79 | 58.72 / 60.24 |
| clipboard_open_ready_close | 237.87 / 246.60 | 278.45 / 303.28 |
| wallpaper_open_ready_close | 238.36 / 244.41 | 282.08 / 285.47 |

Это state readiness, **не физическая клавиша и не presented frame**. RSS baseline
146.29→166.47 MiB, warm 167.73→188.25, settled 163.43→182.13. Рост примерно 20 MiB
зафиксирован, не выдаётся за улучшение; точная библиотечная причина не локализована.
Стало больше UI/font/type caches, но это возможные факторы, не доказанная причина.
Closing-inclusive меню дольше при новых 200 ms вместо 140; это стоимость выбранного
motion, не доказанная задержка backend. Reduced motion — рабочая альтернатива.

Finite 60 s soak: 20 циклов, bounded notifications, один qs; последующие benchmark
повторы PASS; identical palette assignments=0. Короткие idle интервалы дали
0 ticks, не доказательство CPU=0%/экономии батареи. Аппаратные 182–186 MiB/5.39 W
из другой сессии не сравниваются напрямую. Подробности: [performance.md](../performance.md).

## 12. Ограничения и оставшиеся проверки

- GoogleDot требует ручной установки/применения; Settings selector не симулируется.
- RHI symbolic tint, HiDPI и реальная визуальная приёмка — T480.
- Рост RSS и более длинный close motion требуют принятия/измерения пользователем.
- Реальные Fn/audio/Bluetooth pairing/scan, sleep/resume, внешние мониторы не
  объявлены проверенными этим редизайном; backend tests используют fixtures.
- Launcher unified windows/commands/files search не добавлен: Search.js сохранён
  ради стабильности; рабочие команды/окна остаются Super+R/Super+Tab. File backend нет.
- Notification grouping не имитируется: backend хранит bounded chronological history.
- Развёртывание требует пересборки native plugin под текущий Qt/qs 0.3.2.

## 13. Сборка и безопасная установка

```bash
cd ~/Projects/pixelrail
./scripts/build-native.sh
git diff --check
./scripts/deploy.sh                  # dry-run
./scripts/deploy.sh --apply          # только по решению владельца после review
```

Режимы панели/уведомлений сохраняются; по умолчанию первой установки Waybar/SwayNC.
Не устанавливать системные пакеты автоматически. После apply: открыть Settings
кнопкой в Super+A или `~/.local/bin/pixelrail-settings`.

## 14. Откат

```bash
cd ~/Projects/pixelrail
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Backup/release сохраняются, user config/cache не удаляются; изменение пользовательских
файлов вызывает отказ с объяснением. Cursor preview в deploy не применяется.
Подробности: [installation](../installation.md), [recovery](../recovery.md).

## 15. Скриншоты и ручная приёмка

Ниже настоящие Qt-rendered offscreen snapshots **тестовых** компонентов, не
сгенерированные AI и не физический Hyprland screenshot. PanelWindow адаптирован
к offscreen Item для безопасного capture; часть данных — fake audio/brightness/apps,
часть — read-only service state. CC снимался после тестового resize (~63%), не как
доказательство default 50%. Чёрная/прозрачная область — canvas, обои не подставлялись.

![Quick Settings dark](screenshots/quick-settings-dark.png)
![Quick Settings light](screenshots/quick-settings-light.png)
![Sidebar + Launcher](screenshots/sidebar-launcher-dark.png)
![Themed Sidebar + Launcher](screenshots/sidebar-launcher-themed.png)
![Settings icons](screenshots/settings-icons-dark.png)
![Notifications](screenshots/notifications-dark.png)

- [ ] 1366×768 / HiDPI: три верхних элемента, workspace 1–5 и последний P, app scroll.
- [ ] Original icons действительно цветные; themed symbolic/monograms на Intel RHI,
  missing icons, несколько окон, разные palettes и перезапуск.
- [ ] Super/Q/D, A/N туда-обратно/повтор, Escape/outside click, nested Back.
- [ ] Settings theme/accent/reset/Auto/animations/profile, .desktop/CLI, сохранение.
- [ ] Кириллица/EN-RU/Alt+Shift, фокус и текстовые поля.
- [ ] Два live sliders, Fn/mute/readback/OSD, отсутствие OSD поверх CC.
- [ ] Wi-Fi/BT scan/pair/connect/error/recovery, MPRIS, BAT0/BAT1/AC.
- [ ] Notification actions/DND/clear, Clipboard image Ctrl+V, Wallpaper persist.
- [ ] Resize height/handle/scroll; sleep/resume и monitor hotplug — только вручную.
- [ ] Реальные RSS/CPU/power в сопоставимых idle условиях; оценить +RAM/close motion.
- [ ] GoogleDot Black/White, 24/28/32, arrow/text/link/resize/move/wait/not-allowed
  в Qt/GTK/XWayland после осознанной ручной установки.
- [ ] Deploy/rollback/fallback без второго qs, сохранить theme.json перед старым helper.

RC1 — для приёмки, не обещание финальной стабильности. Тег `v3.1.0-rc.1` предложен,
но не создавался. Новые функции за пределами задания не начинались.

## Дополнение: иконки/курсор

Актуальное состояние ресурсов, источники, native/offline проверки и разделение
connected/fallback/manual: [resources-addendum.md](resources-addendum.md).
GoogleDot уже подготовлен в cache как dependency; первоначальные утверждения о
нескачанных бинарниках и 31/62 symbols заменяются этим дополнением (42/84).
