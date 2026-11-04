# v3.1 — дополнение: реальные иконки и курсор

Живые config/bin, службы и рабочий qs не менялись. Deploy/sudo/установка пакетов
не выполнялись. Все прежние незакоммиченные файлы сохранены.

## Полностью подключено

- **Material Symbols Rounded**: 42 имени × outline/fill =84 настоящих SVG в
  quickshell/assets/symbols; единый PixelIcon, цвет ThemeManager, HiDPI, disabled,
  bounded cache 96. Дополнение получено отдельными файлами из официального commit
  `10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7`, не скачивался весь набор/шрифт.
- **Roboto**: уже bundled OFL font с Cyrillic/Latin; Google Sans Flex выбирается
  только при наличии локально и проверенном покрытии. System font installation нет.
- **Original**: настоящие DesktopEntries/icon theme, включая absolute/file Icon paths;
  исходные брендовые bitmap не перекрашиваются и не копируются в проект.
- **Pixel Themed**: один компонент Sidebar/Launcher/Window Switcher. Сначала
  app-specific symbolic, затем Linux symbolic категории; на software renderer или
  при отсутствии symbolic — настоящий Material vector категории. Он не выдаётся
  за сторонний брендовый монохромный логотип. Общая палитра, переключение Settings
  Original / Pixel Themed, сохранение без перезапуска.

## Ресурсы с fallback

Неизвестный класс приложения → tonal initial либо apps symbol; отсутствующая или
повреждённая original icon → apps symbol. Никаких пустых значков. Для software
renderer symbolic shader не требуется: используется bundled SVG. Реальный RHI tint
установленных symbolic требует визуальной проверки Intel UHD, не объявляется
аппаратно проверенным. Chrome/VS Code original не подвергаются tint.

Локальный аудит: Adwaita, AdwaitaLegacy, Breeze/Breeze-dark, hicolor/default;
курсоры Adwaita; 41 .desktop с Icon=. GoogleDot/Material font/Roboto/Google Sans Flex
как системные fonts/themes не обнаружены. Полный список (read-only) —
`.cache/icon-cursor-audit/local.json`. Bundled SVG/Roboto работают независимо от этого.

## Подготовлено, требует ручной установки владельцем

**GoogleDot Black/White v2.0.0** реально подготовлены в `.cache/cursor-assets`:
39 бинарных XCursor files +106 aliases каждая, 24/28/32, суммарно ~3 MB.
Официальные архивы сверены SHA256; size-filter сохраняет pixels/hotspots/delay/frames.
`libXcursor` проверила файл и theme lookup для 9 обязательных ролей ×3 размера ×2 темы.
Установка в icons directory и применение Hyprland/GTK/Qt не выполнялись.
Status показывает prepared отдельно от installed. [Ручная процедура](cursor.md).
Системного fake selector в Settings нет: без установки/применения он вводил бы в заблуждение.

## Источники и лицензии

- [Google Material Symbols](https://github.com/google/material-design-icons),
  [Apache-2.0](https://github.com/google/material-design-icons/blob/master/LICENSE).
  LICENSE/SOURCE.md и checksums.json включены. Shapes сохранены, runtime fill изменяется.
- [Roboto](https://github.com/google/fonts/tree/main/ofl/roboto), OFL 1.1,
  OFL.txt/SOURCE.md рядом; [Google Sans Flex](https://github.com/googlefonts/googlesans-flex) optional OFL.
- [GoogleDot v2.0.0](https://github.com/ful1e5/Google_Cursor/releases/tag/v2.0.0),
  [GPLv3](https://github.com/ful1e5/Google_Cursor/blob/v2.0.0/LICENSE). Лицензия в
  assets/cursors и staged themes. Binaries — cache dependency, не tracked binary release.
  При распространении предоставьте corresponding source/build inputs по GPL.
- Original app icons принадлежат установленным пакетам, не переупаковываются.

## Проверки после сборки

`build-native.sh` PASS; offline UI capture + Settings live style switch/persistence
PASS; все видимые PixelIcon Ready, remote image URL запрещён capture assertion.
Снимки: docs/design/screenshots/sidebar-launcher-themed.png и settings-icons-dark.png.
Network proxies направлены на закрытый local port; UI sources проверены как local.
QtTest semantic mappings/cache, SHA256 assets, native XCursor decode — PASS.
Это не тест физического курсора/HiDPI или отключение сети ноутбука.

```bash
python tests/graphic-resources.py
python tests/design-settings.py
python tests/design-screenshots.py
python tests/control-ui.py
QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qmltestrunner -input tests
```

Изменены PixelAppIcon/AppIcons.js, Symbols.js и отдельные SVG/checksums, Settings labels,
prepare-cursor-assets.py/pixelrail-cursor, GPL dependency metadata, resource/UI tests
и эта документация. Новых постоянно работающих процессов нет.
