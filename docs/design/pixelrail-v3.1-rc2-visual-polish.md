# PixelRail v3.1 RC2 — Final Pixel UI Visual Polish

Подготовлено в репозитории, без установки. Незакоммиченная работа v3.1 сохранена.
Никаких sudo, deploy в рабочий HOME, commit/tag/push или остановки рабочего qs.

## Результат

Sidebar сохраняет 54 px видимой ширины / 66 px окна и exclusive zone, позицию,
порядок Power → Wi-Fi → Battery%, нижние workspace 1–5 → окна → логотип.
Вернулся исходный **векторный знак PixelRail**, а не шрифтовая P. Точный path
`M6 18V6h7a4 4 0 0 1 0 8H6m0-4h7` и stroke 1.8 взяты из существующего
`SidebarLogic.svg("home")`; они присутствуют в Git `ded86e7` и HEAD.
Сохранены пропорции, динамический цвет, центрирование и открытие Launcher.

Power/Wi-Fi используют Material Symbols Rounded Outlined по 22 px. Официальный
Wi-Fi wght400 визуально тяжелее Power; для Wi-Fi и Wi-Fi Off подключены отдельные
официальные wght200 SVG, без изменения контуров и растрового размытия. Это
оптическая компенсация, не смешение библиотек. Логотип рисуется в прежнем 24 px
viewBox; при низкой высоте кнопки символы уменьшаются. Workspace получил
primaryContainer + primaryContainerText и читаемые цифры, hover — tonal surface.

Quick Settings получил заметную визуальную иерархию: тональный фон вместо почти
чёрного background, сегментированные вкладки, компактные сетевые плитки с
акцентной иконкой, единые EN/RU и profile chips, две толстые pill-дорожки, компактную
батарею/часы. Mute доступен через кнопку динамика. PixelRail Settings и питание
остались снизу, теперь рядом. При default height видны обе дорожки и информация
о батарее; нижние действия доступны внутренней прокруткой.

Сохранены: ширина 400, default height 50%, resize 30–75%, нижняя ручка,
сохранение высоты, отсутствие scrollbar, Super+A/N и back-navigation.
Никаких новых функций, сервисов, polling, blur/shaders или постоянных анимаций.

## Реальные QML-снимки

Это Qt Quick software/offscreen render с fixture-сетью PixelNet, батареей 87%,
громкостью 64%, яркостью 72% и временем 10:24; логический экран 1366×768.
Показан левый участок 540×768. Окно CC — 400×384; expanded — 400×576.
Прозрачная область вокруг панелей не является новыми обоями.
Это не сгенерированные изображения и не снимок живого Hyprland/T480.

| До | После |
|---|---|
| ![До, Dark](screenshots/rc2-visual-polish/before-dark.png) | ![После, Dark](screenshots/rc2-visual-polish/after-dark.png) |
| ![До, Light](screenshots/rc2-visual-polish/before-light.png) | ![После, Light](screenshots/rc2-visual-polish/after-light.png) |

[Expanded: сохранён resize и нижние действия](screenshots/rc2-visual-polish/after-expanded.png),
[выключенные плитки](screenshots/rc2-visual-polish/after-disabled.png).

## Почему прежний RC1 мало отличался от v3.0

Read-only сравнение рабочего release `20261103T171238Z-4ac5b053` с исходниками
подтвердило идентичность Sidebar/Control Center/slider/PixelIcon/Tokens и Wi-Fi SVG.
Рабочий qs действительно использовал этот release. Deploy копирует всю папку
quickshell: ошибки путей/недоставленных ресурсов не обнаружено.

Причина была в визуальных решениях: основной CC использовал background,
ControlSlider сохранял дорожку 12 px и старую ручку, home явно задавался через
label P, а стандартный wifi.svg был слишком тяжёлым. PixelIcon читает встроенную
карту `ui/Symbols.js`, поэтому замены одного SVG на диске недостаточно. Карта и
checksums обновлены вместе; тест сверяет встроенные контуры с offline-файлами.

## Параметры и цвета

| Параметр | Значение |
|---|---|
| Sidebar rail / окно / exclusive zone | 54 / 66 / 66 px, без изменения |
| Системные символы Sidebar | 22 px, outlined, адаптация к малой высоте |
| Оригинальный logo viewBox | 24×24, stroke 1.8, round caps/joins |
| CC ширина / default height | 400 / 384 при 1366×768 |
| Header / title / status / percentage | 18 / 14 / 12 / 13 px |
| Плитка / radius | 64 / 22 px |
| Основной panel radius / padding | прежние 26 / 16 px |
| Chips | 34 px, pill |
| Live slider hit area / track / handle width | 44 / 28 / 6 px |
| Основной gap | 8 px |
| Новые интервальные таймеры в shell | нет |

Новые именованные tokens находятся в существующем Ui.Tokens; глобальные размеры
Launcher и OSD не менялись. Фон CC — surfaceContainer, неактивные плитки и chips —
surfaceContainerHigh, активные — primaryContainer. Текст берётся из surfaceText,
surfaceVariantText, primaryContainerText; акцентная пиктограмма — primaryText на
primary. Заполнение slider — primary, индикатор — primaryText; у минимума он
переключается на primary для читаемости на незаполненной дорожке.

Никакого фиксированного фиолетового. Палитра/генератор/сохранение настроек не менялись.
Dark/Light/Auto, ручной accent и оба режима иконок продолжают использовать прежний
ThemeManager. Roboto из существующего offline FontLoader подтверждён runtime;
установленный Google Sans Flex выбирается прежней coverage-aware политикой.

## Ресурсы

Логотип — исходная собственная графика PixelRail из Git.
Wi-Fi wght200 и sun light_mode wght400 — официальный Google Material Symbols
Rounded, Apache-2.0; лицензия сохранена. Получены только отдельные SVG из commit
`10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7`. Источники и исключения по весу описаны
в [SOURCE.md](../../quickshell/assets/symbols/SOURCE.md).
Все ресурсы bundled, проверены без сетевых URL в QML; системная установка не нужна.
Оригинальные .desktop-иконки и Pixel Themed backend не изменялись.

## Проверки

PASS: Qt6 qmllint (exit 0, прежние static metadata warnings), QtTest 10 PASS,
Control UI, Sidebar GUI/runtime, graphic resource checksums/JS parity,
Dark/Light/Auto contrast, EN/RU, Wi-Fi/BT detail/back, live sliders/coalescing,
Fn/OSD runtime, Notifications/D-Bus, settings persistence, popup placement,
95 биндов и Super-tap, screenshot backend/runtime/Escape, lifecycle и deploy/rollback
в тестовых HOME. Отдельно проверена доставка новых SVG в release.
Offscreen-рендер также пройден с `QT_SCALE_FACTOR=1.5`.

Source hash guard подтверждает: screenshot.py, ScreenshotState, pixelrail-shot,
Lua binds/Super-tap, LiveSlider и SystemState/SystemControls побайтно не менялись.
Весь префикс ControlCenter до визуальной Rectangle, включая FocusGrab,
Escape, IPC-facing state и методы backend, также побайтно сохранён.

Логи: `.cache/visual-polish/targeted.json`, `final-tests.json`, `*-final.log`,
`comparison.json`, `benchmark-baseline.json`, `benchmark-polished.json`.

## Производительность и границы измерений

Сравнивались исходные QML установленного RC2, скопированные в тестовый каталог,
и новые исходники. Ни одна операция benchmark не выполнялась над рабочим qs.

| Измерение | До | После |
|---|---:|---:|
| RSS нарисованного fixture UI, медиана 3 запусков, MiB | 141.60 | 143.44 |
| Диапазон RSS этих запусков, MiB | 139.18–145.47 | 139.66–143.75 |
| Launcher open/state/close, медиана 5, ms | 85.45 | 87.98 |
| A→N state, медиана 5, ms | 58.37 | 58.90 |
| N→A state, медиана 5, ms | 57.65 | 57.59 |
| State IPC, медиана 5, ms | 28.77 | 28.52 |
| RSS settled полного unmapped benchmark, один запуск, MiB | 176.65 | 167.88 |
| Основных qs в каждом benchmark | 1 | 1 |

IPC/state latency не равна времени отображения compositor frame. Для n=5 p95
не рассчитывался. Рост медианы rendered RSS ~1.84 MiB находится внутри
перекрывающихся диапазонов; снижение RSS unmapped-прогона не объявляется экономией.
Короткие 2-секундные CPU-сэмплы rendered UI дали 0–1 tick до и 0 ticks после,
в интервалах unmapped benchmark — 0 ticks. Это грубое измерение, не доказательство
изменения реальных 0–0.2% CPU или расхода T480 в ваттах.
В ограниченных тестах существенного провала отзывчивости не обнаружено;
аппаратные CPU/RSS/энергопотребление после установки нужно измерить отдельно.

## Файлы этой доработки

- `quickshell/ui/Tokens.qml`, `quickshell/ui/Symbols.js`.
- `quickshell/modules/sidebar/Sidebar.qml`, `SidebarButton.qml`.
- `quickshell/modules/control/ControlCenter.qml`, `ControlTile.qml`,
  `ControlSlider.qml`, `ControlButton.qml`.
- `quickshell/assets/symbols/wifi.svg`, `wifi_fill1.svg`, `wifi_off.svg`,
  `wifi_off_fill1.svg`, новый `light_mode.svg`, `SOURCE.md`; assets/checksums.json.
- `tests/control-ui.py`, `tests/gui/SidebarTests.qml`, `tests/graphic-resources.py`,
  `tests/deployment.py`, новый `tests/visual-polish.py`.
- `docs/control-center.md`, `docs/sidebar.md`, этот отчёт и шесть PNG рядом,
  `CHANGELOG.md`.

Остальные незакоммиченные файлы v3.1 существовали до этой задачи и сохранены.
Native plugin не менялся; новой обязательной зависимости/сборки для UI-патча нет.

## Безопасная установка и откат

Автоматически не выполнялись. Пользователь сначала просматривает dry-run:

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh
./scripts/deploy.sh --apply
```

Если native plugin ещё не собран для этой рабочей копии — предварительно
`./scripts/build-native.sh` (локальная сборка). Сам UI-патч rebuild plugin не требует.
Не копировать отдельные SVG поверх живой системы: installer доставляет QML,
встроенную Symbols.js и файлы assets одним release.

```bash
./scripts/rollback.sh          # dry-run
./scripts/rollback.sh --apply
```

Installer/lifecycle не менялись. Режимы Sidebar/Waybar и PixelRail/SwayNC сохраняются.

## Ручная приёмка T480

- Проверить узнаваемый векторный логотип, его последнее положение и открытие Launcher.
- Сравнить вес Power/Wi-Fi, hover и активный workspace; проверить окна текущего workspace.
- Super+A/N, повтор, tabs, Escape/outside click; нижний resize handle 30–75% и restart.
- Wi-Fi/BT включение, details/back; EN/RU/Alt+Shift; графический Battery/Performance.
- Drag/wheel/keyboard двух sliders, release снаружи, mute и Fn/OSD.
- Светлая/тёмная/Auto, новые обои/ручной accent и Original/Pixel Themed.
- Прокрутить к PixelRail Settings и питанию; только открыть меню питания.
- Super+Shift+S с открытой панелью → выбор/отмена/повтор; обычный Escape после отмены.
- Повторить power audit/benchmark в сопоставимом простое; проверить реальные CPU/RSS.

Физические устройства, изображение настоящего screenshot и работа compositor
на T480 не объявляются проверенными этим offscreen-прогоном.
