# Changelog

## Unreleased — v3.1.0 public packaging

- Owner-selected MIT license, copyright nesnimi; third-party font/symbol/cursor
  notices kept separate. English/Russian README, reviewed fixture screenshots.
- Existing deploy/rollback reused by install/uninstall wrappers, dependency/Qt
  build checks, explicit unmanaged-dotfile approval, whole-chain recovery and
  per-user source releases. No package/service/driver/power-policy setup.
- Read-only publication/history audit and reproducible source archives excluding
  local references, caches, history, native binaries and GoogleDot binary themes.
- Portable battery audit summary, quoted generic startup paths, default-root
  limitations and second-computer acceptance checklist documented.
- Publication, commit, tag and real installation remain owner actions.

## Unreleased — v3.1.0, финальный кандидат

- Удалены дублирующие быстрые действия Launcher и занимаемое ими пространство.
- Стартовая сетка: категории пользовательских приложений, накопленная частота,
  desktop visibility и объединение одинаковых команд. При отсутствии качественных
  кандидатов — обычный список. Системные утилиты доступны по явному запросу.
- Одноразовое асинхронное чтение недостающих desktop-полей для Quickshell 0.3.2;
  без нового индексатора, polling или постоянно работающего процесса.
- RC4: согласованы Notifications, Clipboard и Wallpaper Picker; раскрытие длинных
  уведомлений, тональные карточки, поиск pill и заметное выделение обоев.
- RC5: сетка, атомарная ограниченная статистика, ранжирование точных/префиксных
  совпадений и пространственная навигация; дублирующие действия RC5 удалены выше.
- Подготовлены проверки, инструкции выпуска/восстановления и ручная приёмка.
  Выпуск, commit и тег не выполнены; Stable требует подтверждения владельца.

## Unreleased — v3.1 RC3

- Launcher 2.0: compact Pixel search, tonal results, shared keyboard chips,
  original/themed icons with a distinct selected state; existing search preserved.
- Settings: responsive left navigation, lazy cards, independent scrolling,
  existing theme/accent/icon/motion/profile actions and persistence.
- Screenshot mode, focus grabs, Sidebar and system backends preserved.

## Unreleased — v3.1 RC2

- Visual polish: restored the original vector logo, optically balanced Sidebar
  symbols, tonal Quick Settings, 64 px tiles and 28 px live slider tracks.
- Sidebar width/zone, Control Center height/resize, screenshot/focus/IPC and
  system backends preserved. Offline SVG integrity and visual regressions tested.
- Critical screenshot fix: READY/GO handshake, inactive until worker ready,
  immediate Escape recovery, bounded TERM/KILL cleanup and manual IPC reset.
- Screenshot CLI reports refused/failed startup and IPC/tool errors; slurp Escape
  cancellation remains supported, including `selection cancelled` stderr.
- Screenshot mode: Super+Shift+S сохраняет открытые popup при запуске slurp.
- Общий IPC/Process lifecycle, временное снятие keyboard/focus grabs и Escape.
- Восстановление после cancel/error/crash, bounded watchdog, без второго qs.
- Сохранены grim/slurp/wl-copy, PNG/Pictures/Screenshots и буфер изображения.


## Unreleased — v3.1 RC1

- Единая Pixel Experience система: tokens, typography, Material Symbols Rounded.
- Launcher 2.0 визуально, Material tiles, shared app icons, notification cards/empty state.
- Settings в существующем процессе: theme/accent, original/themed icons, animations,
  графический профиль, backend режима панели/уведомлений, keyboard/hotkeys.
- Atomic, backward-compatible UI preferences в theme.json, без сброса неизвестных ключей.
- GoogleDot offline integration preview + licensing, без установки в систему.
- Реальные offscreen screenshots, новые UI/config/cache tests.
- Никаких новых биндов, процессов/демонов, EPP или изменений драйверов.


## Unreleased — кандидат v3.0 (включает v2.7)

Не Stable; тег и commit не созданы. Требуется ручная приёмка владельца T480.

- Minimal Sidebar: только Power/Wi-Fi/Battery% сверху; низ, геометрия и P сохранены.
- Quick Settings: профиль эффектов, реальная EN/RU, батарея и часы; компактные
  Wi-Fi/Bluetooth, live sliders, MPRIS и питание сохранены.
- Bluetooth: различение службы/адаптера/rfkill/unknown; событийный refresh BlueZ.
- Убраны верхние close у Clipboard и Control Center; Escape/Back сохранены.
- Resume/hotplug: закрытие transient окон, refresh brightness/theme; пассивный
  logind listener в прежнем native plugin. Без реального suspend в разработке.
- Profile и deployment manifest записываются atomic replace; apply проверяет
  наличие native plugin до изменений. Добавлены fault-injection/crash tests.
- Сохранён пользовательский фикс brightnessctl без `-n 1`; regression test.
- Расширены документация установки/восстановления и чек-лист кандидата.

## v2.6 — существующая база

Live brightness/volume sliders, 40 ms coalescing, shared SystemControls,
readback-based system OSD, XF86 IPC, backlight events. После ручной проверки
пользователь удалил несовместимый аргумент brightnessctl `-n 1`.
