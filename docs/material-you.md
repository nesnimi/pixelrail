# Material You Theme Engine

PixelRail использует установленный `matugen` (проверено с 4.2.0), существующий
GdkPixbuf-декодер обоев, Python 3 и Quickshell 0.3.2. Новые пакеты и демоны
не устанавливаются. Waybar и SwayNC не меняются.

## Архитектура

После успешного сохранения обоев MenuPanel испускает `wallpaperChanged`.
Единственный ThemeManager запускает `pixelrail-theme sync` через асинхронный
Quickshell Process. Отмена/ошибка применения не запускают генерацию.
Механизм swaybg не изменён. На старте проверяются сохранённые обои и кэш.

`scripts/material_you.py` передаёт matugen ограниченное превью PNG из уже
поддерживаемого декодера. Используются `scheme-tonal-spot`, обе схемы dark/light,
собственный пустой TOML и `--dry-run --json hex`: пользовательские шаблоны,
hooks и установка обоев matugen не выполняются. Разобран фактический JSON 4.x:
`colors.primary.dark.color`; также поддерживается прежний `colors.dark.primary`.

Проверяются обязательные семантические роли, HEX и контраст основных пар ≥4.5:1.
Палитра записывается целиком атомарной заменой после успешной проверки.
При ошибке остаются последние цвета; до первой успешной генерации используется
встроенная полноценная пара Material 3 схем от фиксированного seed `#ADC9FF`.

`quickshell/theme/ThemeManager.qml` — единый singleton с реактивными цветами.
`Palette.qml` — совместимый фасад для Launcher, MenuPanel, Clipboard и Wallpaper
Picker. Quick Actions, команды, клавиши, питание и прочие меню используют MenuPanel.
Размеры и поведение Launcher сохранены, изменены только цвета и состояния.

FileView наблюдает настройки и палитру событийно. После rename подписка явно
снимается и восстанавливается на новый inode, с повторным чтением для закрытия
промежутка. CLI дополнительно вызывает существующий IPC `theme reload`.
Процесс Quickshell и окна не перезапускаются. Таймеров/polling нет.

## Настройки и команды

После ручного deploy доступны:

```bash
pixelrail-theme status
pixelrail-theme mode dark
pixelrail-theme mode light
pixelrail-theme mode auto
pixelrail-theme accent '#D07844'
pixelrail-theme accent wallpaper
pixelrail-theme accent reset
pixelrail-theme refresh
```

До deploy можно вызывать `./scripts/pixelrail-theme`, но команды изменения темы
пишут пользовательские XDG-настройки: это уже осознанная настройка рабочего сеанса.
`sync` — внутренний вариант без IPC; `refresh` проверяет актуальность и уведомляет
работающий экземпляр. Регенерация при неизменных данных не выполняется.

Настройки: `$XDG_CONFIG_HOME/pixelrail/theme.json` (по умолчанию
`~/.config/pixelrail/theme.json`):

```json
{"mode": "dark", "accent": null}
```

`accent` — `null` для обоев либо HEX `#RGB`/`#RRGGBB`. При ручном акценте смена
обоев сохраняет выбранные цвета. Сброс возвращает цвета текущих сохранённых обоев.
Можно атомарно редактировать этот файл вручную. По умолчанию режим dark.

Auto следует `Qt.styleHints.colorScheme` и его сигналам: Light → light,
Dark/Unknown → dark. При отсутствии поддержки темы со стороны Qt/platform theme
используется dark; время суток не опрашивается. На Hyprland наличие системной
темы зависит от настроенной интеграции Qt/desktop portal. Она здесь не меняется.

Кэш: `$XDG_CACHE_HOME/pixelrail/theme/` (по умолчанию `~/.cache/pixelrail/theme/`):
`palette.json`, ограниченное `source.png`, собственный `matugen.toml`, `.lock`.
Выбор обоев читается из `$XDG_STATE_HOME/pixelrail/wallpaper`.
Настройки и кэш находятся вне releases и сохраняются при deploy/rollback.

Отпечаток включает содержимое изображения, путь, seed и алгоритм. Версия/файл
matugen также проверяются. Смена только режима выбирает уже готовую схему и не
запускает matugen. flock сериализует запросы CLI/QML, повторные запросы используют
кэш; устаревшая генерация не публикуется, QML объединяет ожидающие изменения.
Хеширование, декодирование и matugen выполняются вне UI-потока.

## Ошибки и восстановление

При отсутствии matugen, повреждённом/отсутствующем изображении или плохом JSON
последняя корректная палитра не перезаписывается. CLI возвращает ненулевой код и
JSON с понятной ошибкой. Состояние текущего процесса:

```bash
release_dir="$(dirname "$(dirname "$(readlink -f "$HOME/.local/bin/pixelrail-theme")")")"
qs ipc -p "$release_dir/quickshell/shell.qml" call theme state
```

Исправьте путь обоев через Picker или сбросьте ручной акцент, затем выполните
`pixelrail-theme refresh`. При ошибках настроек восстановите JSON выше.
Для резервирования достаточно сохранить `theme.json` и `palette.json`; перед
заменой рекомендуется сделать собственные копии. Удаление кэша необязательно.
Theme Engine не устанавливает matugen автоматически.

## Проверки

В репозитории (временные HOME/XDG только внутри `.cache`):

```bash
python3 tests/material-you.py
python3 tests/material-you-runtime.py
python3 tests/qt-ui.py
python3 tests/runtime-menus.py
python3 tests/smoke-quickshell.py
python3 tests/deployment.py
/usr/lib/qt6/bin/qmllint quickshell/theme/ThemeManager.qml quickshell/shell.qml
```

Проверяются реальные matugen dark/light для разных изображений, кириллица и
пробелы, HEX/reset, кэш и конкурентные генерации, отсутствие matugen, повреждённые
данные, сохранение последней схемы, многократный rename JSON в работающем qs,
реактивные цвета панелей, IPC, отсутствие повторного процесса и сохранение
настроек/кэша при deploy/rollback. Escape проверяется Qt key events после вкладок,
поиска и превью; кнопки закрытия в шапке больше нет.

Qt 6 qmllint завершился успешно; остаются предупреждения статических метаданных
Quickshell (`PanelWindow`, динамические свойства Loader, singleton и тип styleHints).
Runtime smoke/UI-тесты не показали ошибок загрузки или привязок. Системный
`/usr/bin/qmllint` здесь относится к Qt 5 и не поддерживает используемый синтаксис.

Ручная проверка в Hyprland после установки:

1. Открыть Super+Ctrl+T: заголовок «Обои», без кнопки и пустого места; чипы прежние.
   Проверить Escape после каждой вкладки/поиска/превью, отмену и повторное открытие.
2. Применить разные тёплые/холодные обои. Открытые панели меняют оттенки;
   отмена и ошибка обоев сохраняют тему. Проверить сохранение после нового сеанса.
3. Проверить Launcher, Clipboard, команды, клавиши и питание в dark/light:
   читаемость, hover/focus/pressed/selected, иконки и навигацию.
4. В Auto переключить доступную системную тему Light/Dark. Offscreen Qt сообщает
   Unknown: автоматизированно проверен fallback dark, реальный системный переход
   требует этой проверки.
5. Проверить ручной HEX и reset, серию смен обоев, неизменный PID Quickshell,
   отсутствие matugen в простое, единственный swaybg и профили battery/performance.
   Полная визуальная оценка и энергопотребление на T480 требуют рабочего сеанса.

## Безопасное развёртывание и откат

Сначала просмотреть план, затем вручную применить:

```bash
cd ~/Projects/pixelrail
./scripts/deploy.sh
./scripts/deploy.sh --apply
```

Откат последнего развёртывания:

```bash
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Lifecycle и резервные копии использованы существующие. Команды установки здесь
не выполнялись; тесты используют `--target-home` и `--no-start`. Если предыдущий
релиз не содержит Theme Engine, он просто не использует сохранённую тему.

## Исправление контраста QML

В runtime обнаружена ошибка привязок свойств с именами `onSurface`,
`onSurfaceVariant`, `onPrimary` и других `onX`: при корректных значениях JSON
они оставались чёрными (`#000000`). Например, dark JSON содержал
`onSurface=#e2e2e9`, но `Palette.text` возвращал чёрный. Поэтому проверка одного
JSON не обнаруживала проблему.

Стандартные имена MD3 сохранены в matugen JSON и `Fallback.js`. В QML используются
имена без синтаксиса обработчиков `onX`: `surfaceText`, `surfaceVariantText`,
`primaryText`, `primaryContainerText`, `secondaryContainerText`, `selectedText`.
Они привязаны соответственно к `onSurface`, `onSurfaceVariant`, `onPrimary`,
`onPrimaryContainer`, `onSecondaryContainer`. Цвета не заменены константой white.

Поля поиска явно задают цвет ввода, placeholder и выбранного текста. Выбранные
карточки используют `secondaryContainerText` также для подписей; кнопки и чипы
используют соответствующий текстовый цвет при нажатии. Контур фокуса поиска
использует primary без ослабления прозрачностью. QML дополнительно отклоняет
полные, но неконтрастные схемы из кэша, сохраняя предыдущую палитру.

`tests/material-you-runtime.py` проверяет фактические цвета singleton/Palette,
полные семантические пары, подписи/placeholder, selected/hover/pressed-смеси,
разные HEX, dark/light/auto, fallback и обновления во время работы. Минимальный
контраст в проверенных текстовых состояниях — **5.03:1** при пороге 4.5:1.
`tests/qt-ui.py` проверяет реальные поля ввода, выделение и нажатие чипов.
`tests/runtime-menus.py` проверяет цвета текста в Launcher и всех девяти меню.
Desktop-иконки не перекрашиваются; для собственных значков проверяется
контраст акцента на используемой поверхности (не ниже 3:1).
