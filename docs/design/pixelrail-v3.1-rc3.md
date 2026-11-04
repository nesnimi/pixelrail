# PixelRail v3.1 RC3 — Launcher и Settings

Локальная визуальная доработка RC2; без deploy и без релизного тега.

План/спецификация:

- Launcher: прежние 540 px и нижнее левое положение; pill search 48 px, текст 14,
  icon 32, строки 50, максимум 5 видимых строк. Тональный surfaceContainer,
  primaryContainer selected state, короткие keyboard chips. Только приложения,
  прежние Search.js, IPC и клавиатура. Нового индексатора/источников нет.
- Settings: то же окно, ширина до 680 px только в режиме Settings; Quick/N —
  прежние 400 px. Высота/resize сохранены. Компактная левая
  навигация с tooltip; полные названия при ширине от 600 px. Независимый скролл
  навигации и карточек. Существующие SettingsActions/ThemeManager, без нового store.
- Карточки 16–20, spacing 8/12/16, заголовки 20, текст 14/12; palette roles RC2.
  Режимы темы, accent, иконки и motion/profile — настоящие действия. Launcher и
  Sidebar: справочные сведения и существующие действия. GoogleDot: справка,
  системный курсор не применяется. Горячие клавиши открывают существующий список.
- Motion 120/160/200 мс из Tokens, Reduced Motion обнуляет длительность.
  Нет polling, новых демонов, тяжёлых эффектов или дополнительного кэша иконок.
- Screenshot/FocusGrab/бинды/Sidebar/backends не изменяются.

## Выполнено

Launcher получил тональный фон, поле 48 px с контрастным курсором, строки 50 px,
иконки 32 px, выделение primaryContainer и мягкое появление маркера выбора.
Максимальная обычная высота с пятью результатами — 410 px вместо 422; ширина 540
и положение сохранены. Отдельное пустое состояние, полезные genericName без
дублирования имени, keyboard chips. Реальный поиск приложений не расширялся.
Original остаётся цветным; Pixel Themed использует прежние symbolic/Material/
монограмму. Выбранный тематический значок получает primary/primaryText badge.
Обнаружен и исправлен ложный movie-fallback: `mpv` внутри имени временного
каталога больше не считается идентификатором приложения.

Settings использует девять разделов. В обычном 680 px режиме слева полные подписи;
на узком экране (страница <600 px) — icon rail с tooltip/Accessible names.
Справа реальные карточки темы/акцента/иконок/анимаций/профиля и существующие
действия панели, уведомлений и ввода. Launcher/Sidebar также содержат справочные
сведения; курсор — явно ручная установка. Страница клавиш открывает существующий
поисковый список, без второго набора 95 биндов.

Только текущий раздел создаётся Loader. Сама SettingsPage загружается по URL
асинхронно при открытии, с настоящими loading/error состояниями. После выхода
освобождается; повторное открытие и controller/height bindings проверены.
Нового файла настроек и миграции не требуется: используется прежний theme.json,
SettingsActions, атомарная запись и сохранение неизвестных ключей.

## Снимки

Реальный Qt Quick offscreen render, не изображения генератора и не захват живой
сессии. Launcher использует private .desktop и безопасный Exec-marker; двухцветные
иконки — тестовые SVG для проверки Original, не брендовые ресурсы приложений.
В установленном Launcher используются настоящие .desktop/icon theme ресурсы.
Settings показаны в 680 px режиме того же окна после тестового resize (~63%); широкая
страница — отдельный Item-тест адаптивности, не новое окно приложения.

- [Launcher Original](screenshots/rc3/launcher-dark-original.png),
  [Pixel Themed](screenshots/rc3/launcher-dark-themed.png),
  [Light](screenshots/rc3/launcher-light-themed.png),
  [нет результатов](screenshots/rc3/launcher-empty.png).
- [Settings Dark](screenshots/rc3/settings-appearance-dark.png),
  [Light](screenshots/rc3/settings-appearance-light.png),
  [иконки/курсор](screenshots/rc3/settings-icons-dark.png),
  [страница Launcher](screenshots/rc3/settings-launcher-dark.png),
  [широкая навигация](screenshots/rc3/settings-wide-dark.png).

## Проверки

Один общий прогон: Qt6 qmllint, QtTest, Launcher/Control/Qt UI, icon resources,
settings/persistence, IPC/routing, Sidebar, EN/RU, sliders/OSD, Notifications,
Material You, Wallpaper/Clipboard, popup placement, 95 биндов/Super-tap,
screenshot backend/runtime/Escape, lifecycle и deployment/rollback test HOME.

Один сценарий первоначально использовал устаревшее ожидание background для
Launcher: оно заменено на surfaceContainer. Проверка контраста различает текстовый слой и Rectangle с alias text (Keycap),
исключает невидимые альтернативные монограммы и сохраняет порог 4.5 для текста.
После исправления адресный runtime-menus прогон прошёл. После lazy loading повторены
Control UI/runtime, deployment и lifecycle runtime; после icon-fallback — QtTest
и Launcher UI. Это адресные повторы, не второй полный прогон.
Итог — 29 актуальных проверок PASS, QtTest 10 PASS. Исходный лог падения
сохранён, адресный повтор runtime-menus прошёл. Логи: `.cache/rc3/results.json`,
`verified-results.json`, `post-lazy-tests.json`, `*-last.log`.

Launcher UI проверяет поиск RU/EN, фокус, Down/Up/Tab/Shift+Tab/Enter/Escape,
выполнение настоящего безопасного .desktop Exec в test HOME, пять видимых строк,
Dark/Light/Auto и мгновенную смену Original/Themed. Settings UI проверяет все
разделы, клавиатуру/scroll, wide layout, HEX validation/apply/reset, mode buttons,
icon/motion persistence после рестарта, Escape и освобождение страницы.

Source hash guard: screenshot.py, pixelrail-shot, ScreenshotState, shell IPC,
бинды, Sidebar/логотип, Search.js, SettingsActions, ThemeManager, LiveSlider и
SystemControls/SystemState побайтно сохранены. Focus/keyboard grab обоих окон не менялся. В префиксах изменены только
формулы визуальной высоты Launcher и ширины Settings.

## Производительность

Короткий изолированный benchmark, n=5, IPC + QML state readiness, **не время
отрисовки compositor**. RC2 baseline — существующий `.cache/visual-polish/benchmark-polished.json`.

| Медиана, ms | RC2 | RC3 с lazy Settings |
|---|---:|---:|
| Launcher open/state/close | 87.98 | 88.93 |
| A→N | 58.90 | 58.54 |
| N→A | 57.59 | 58.98 |

Различия малые, p95 при n=5 не приводится. В каждом окружении один qs,
неизменная палитра не генерировалась повторно. RSS settled: 167.88 MiB в старом
прогоне RC2, 182.70 в первом RC3; после отложенного разбора Settings — 172.50 MiB.
Это единичные измерения с allocator/cache шумом. После первого посещения Settings
скомпилированные QML и обычные Qt-кэши могут остаться; искусственной очистки нет.
Нет заявления об улучшении автономности или аппаратного CPU/RAM на T480.

## Изменённые файлы

Launcher.qml; ui/Tokens.qml, PixelAppIcon.qml, AppIcons.js, Keycap.qml, qmldir;
control/SettingsPage.qml, SettingsCard.qml, IconStylePicker.qml, ControlCenter.qml,
qmldir; tests/launcher-ui.py, control-ui.py, tst_design.qml, deployment.py,
runtime-menus.py; README, CHANGELOG, docs/launcher.md, docs/control-center.md,
этот отчёт и девять PNG. Все остальные незакоммиченные изменения сохранены.
Новых ресурсов из интернета, системных пакетов или native plugin изменений нет.

## Безопасная установка

Автоматически не выполнялась. После просмотра плана:

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh
./scripts/deploy.sh --apply
```

RC3 не требует пересборки неизменённого native plugin, если он уже собран для RC2.
Откат: `./scripts/rollback.sh`, затем `./scripts/rollback.sh --apply`.

Ручная приёмка T480: Super → RU/EN search/Enter/Tab/Escape; оба режима иконок;
Settings navigation/scroll/HEX/mode и повторный запуск; resize/Back; Super+A/N;
Fn/OSD; Super+Shift+S → cancel/repeat/reset и обычный Escape после отмены.
Реальные устройства, physical key delivery и визуальная приёмка владельцем
не объявляются проверенными в изолированной среде. RC3 не объявлен Stable,
commit/tag/push не выполнялись.
