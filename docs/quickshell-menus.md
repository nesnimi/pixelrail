> Deploy/rollback теперь управляют процессом PixelRail после проверки IPC.
> Текущий порядок и offline-флаг: [lifecycle.md](lifecycle.md).

> Зависимость Rofi удалена. Инструкция удаления пакета и восстановления:
> [PixelRail без Rofi](rofi-removal.md).

# Нативные меню PixelRail

Текущий этап после Pixel Launcher v1.1. Дизайн и поиск утверждённого Launcher
сохранены побайтно. Обычные операции browser/code, Kitty, Chrome, звук, яркость,
захват экрана, профиль, Waybar, SwayNC, раскладки и XKB не переписывались.

## Все заменённые интерфейсы

| Прежний вход / вызов Rofi | Нативный обработчик | Сочетание / вход |
|---|---|---|
| pixelrail-launcher-rofi, drun; Waybar on-click | launcher.toggle | одиночный Super_L/R, Super+Space, кнопка Waybar |
| pixelrail-keys, dmenu | menus.open keys | Super+/, Super+F1 |
| pixelrail-clipboard, cliphist → dmenu | menus.open clipboard | Super+V |
| config.rasi: run; теперь явный command launcher | menus.open command | Super+R |
| pixelrail-end4 windows, rofi -show window | menus.open windows | Super+Tab |
| pixelrail-end4 controls, dmenu; вложенные drun/window | menus.open controls | Super+A/G/I |
| pixelrail-power, pixelrail-end4 session, dmenu + confirmation | menus.open power | Ctrl+Alt+Delete, кнопка питания, SwayNC |
| pixelrail-end4 wallpaper, find → dmenu | menus.open wallpaper | Ctrl+Super+T, Quick Actions |
| pixelrail-end4 media, dmenu | menus.open media | Super+M |
| pixelrail-end4 emoji, dmenu | menus.open emoji | Super+Period |

Исполняемых вызовов Rofi в scripts/, hypr/ и quickshell/ больше нет.
`scripts/fallback/*` и `pixelrail-launcher-rofi` — только совместимые обёртки
нативных entrypoints. `rofi/*.rasi` сохранены как неиспользуемый архив; deploy
их не устанавливает. Строка `rofi -show drun` в deployment.py служит только для
миграции старой кнопки Waybar, а не для исполнения.

Super+R осознанно изменён с приложения на выполнение команд согласно новой задаче;
приложения остаются на одиночном Super и Super+Space. Другие сочетания сохранены.

## Организация

Один `shell.qml`, IPC endpoints `launcher` и `menus`. Новый MenuPanel загружается
через Loader только при обращении; после анимации закрытия Loader освобождает
QML-объекты, список clipboard и процессы. Утверждённый Launcher остаётся отдельным
компонентом без изменений. Одновременно фокус получает одна панель.

Новые панели используют общую `components/MenuPanel.qml` и существующую Palette:
540 px (справка — 700), строки 50 px, до пяти строк (справка — семь), плавность
140 мс. Стрелки/Tab, Enter, Esc, мышь; поиск по названию и подписи.

`pixelrail-menu-data` — короткоживущий Python3/std­lib helper для получения данных
и выполнения выбранного действия. Не отдельный UI/демон: запускается только на
открытие/выбор, не во время набора и не в фоне. JSON передаётся через stdin/stdout;
clipboard не попадает в аргументы команд и логи. Постоянного polling нет.
Открытие другой панели во время загрузки ставится в очередь.

- Справка читает `hyprctl -j binds` при открытии, добавляет Alt+Shift. Выбор строк
  не исполняет ни описания, ни команды.
- Clipboard читает cliphist при открытии; перед копированием проверяет актуальность
  ID и передаёт декодированные байты в wl-copy. Картинки не преобразуются в текст.
  Просмотр — текстовый preview cliphist; автоматической вставки нет.
- Command показывает исполняемые имена из PATH и позволяет явным Enter выполнить
  введённую команду с аргументами/пайпами через `/bin/sh -c`. Сам поиск ничего не
  выполняет. Это намеренный command launcher, не parser запросов приложений.
- Windows читает clients/activewindow; выбирает по адресу, перед фокусировкой
  проверяет, что окно ещё существует. Нет эскизов и polling. Это поиск + Enter,
  а не переключение при отпускании Super.
- Quick Actions сохраняет приложения, окна, уведомления, сеть, BT, звук, обои,
  профиль, lock и питание; добавлена ссылка на команды.
- Питание требует отдельного подтверждения для sleep/logout/reboot/shutdown;
  начальный выбор подтверждения — «Отмена». Lock без дополнительного запроса.
  Logout использует uwsm при его сеансе, иначе Lua API Hyprland.
- Обои сканируются при открытии из `$XDG_PICTURES_DIR` или `~/Pictures`.
  Выбор хранится в `$XDG_STATE_HOME/pixelrail/wallpaper`, по умолчанию
  `~/.local/state/pixelrail/wallpaper`; старый config-файл остаётся читаемым fallback.
  Сохранение состояния выполняется только по явному выбору, не при разработке.
  Нового wallpaper daemon нет: используется существующий swaybg.
- Ошибки внешних утилит показываются в нижней строке. Нет автоматического запуска
  Rofi поверх уже открытого native-меню при ошибке его данных.

## Запуск из репозитория

Quickshell 0.3.2, Python3, Bash/coreutils, hyprctl, cliphist/wl-clipboard,
swaybg и прежние программы действий. Пакеты автоматически не устанавливаются.

```bash
./scripts/pixelrail-shell
./scripts/pixelrail-keys
./scripts/pixelrail-clipboard
./scripts/pixelrail-menu command
./scripts/pixelrail-menu windows
./scripts/pixelrail-menu controls
./scripts/pixelrail-power
./scripts/pixelrail-menu wallpaper
```

`pixelrail-shell` вызывает qs/quickshell с `--no-duplicate --daemonize` и
каноническим абсолютным путём QML. Существующий `pixelrail-start` вызывает эту
обёртку; существующий `hyprland.start` уже запускает pixelrail-start. Отдельные
меню не стартуют shell и не создают дубли. При отсутствии shell возвращается
код 1 с инструкцией восстановления через Super+Return и pixelrail-shell.

```bash
qs ipc -p "$PWD/quickshell/shell.qml" call menus status
qs ipc -p "$PWD/quickshell/shell.qml" call menus hide
qs list -p "$PWD/quickshell/shell.qml" --json
```

`status` после закрытия возвращает `unloaded`. После ручного теста завершать только
этот экземпляр через `qs kill -p "$PWD/quickshell/shell.qml"`, не общий pkill qs.
Дедупликация выполняется на конфиг/дисплей; копия репозитория и установленный release
имеют разные пути и должны переключаться вручную с остановкой предыдущего экземпляра.

## Развёртывание и резервные копии

Работающие ~/.config и ~/.local/bin **не менялись при разработке**. Скрипты ниже
не запускались на настоящем HOME — проверялись только на временных HOME внутри repo.
По умолчанию оба скрипта печатают dry run, реальные изменения — только с `--apply`.

```bash
./scripts/deploy.sh
# После просмотра плана и ручной приёмки:
./scripts/deploy.sh --apply
```

Deploy создаёт отдельный release в `~/.local/share/pixelrail/releases/<id>`:
QML, scripts и Lua. Entry points в ~/.local/bin и два файла Lua — symlinks на
этот release. Backup каждого заменённого файла/ссылки и manifest находятся в
`~/.local/state/pixelrail/deployments/<id>` (каталог 0700). Сохраняются данные,
режимы файлов и исходные symlinks, включая dangling links.

Существующий основной hyprland.lua PixelRail не переписывается: его hooks уже
достаточны. В конфиг без hooks добавляются только entrypoints, отсутствующий
основной конфиг берётся из repo. Обнаружение существующих hooks текстовое — перед
`--apply` вручную убедиться, что упоминания pixelrail-start / pixelrail-end4-keys.lua
не находятся только в комментариях и нет иных пользовательских копий тех же биндов.
Конфиг с другим собственным набором bind'ов сначала согласовать вручную.

Существующий Waybar config сохраняется, заменяются только известные старые строки
кнопки launcher и tooltip. При кастомном `rofi` on-click, отличном от `rofi -show drun`,
поменять его вручную после просмотра. Темы Rofi не устанавливаются и не копируются;
существующие пользовательские темы не затрагиваются. Kitty, Chrome и SwayNC config не заменяются.

Скрипт не выполняет reload, не запускает shell/службы, не устанавливает пакеты.
Внешние symlink-каталоги, уводящие запись за пределы target HOME, отвергаются.
При обычной ошибке применения уже изменённые entrypoints восстанавливаются.
При принудительном прерывании процесса сохраняется manifest/backup для ручного восстановления.

После deploy оператор вручную:

1. Останавливает предыдущий PixelRail shell по его точному пути; особенно важно
   при переходе с repo или предыдущего release. Не останавливать чужие qs-конфиги.
2. Проверяет, что PIXELRAIL_QML не указывает на старую версию, затем запускает
   `~/.local/bin/pixelrail-shell`.
3. Выполняет `hyprctl reload`, отпускает все клавиши, проверяет
   `hyprctl configerrors`, `hyprctl -j binds` и матрицу ниже. Автозапуск через
   `hyprland.start` сработает при следующем входе, не при простом reload.
4. Для уже запущенного Waybar обновление кнопки требует его обычного ручного
   перезапуска. Уведомления и другие службы менять не нужно.

## Откат

```bash
./scripts/rollback.sh
./scripts/rollback.sh --apply
# Либо выбрать backup явно:
./scripts/rollback.sh --id <id> --apply
```

По умолчанию выбирается последний активный backup. Rollback сначала проверяет
все установленные файлы: если после deploy есть пользовательские правки, ничего
не перезаписывает и сообщает конфликт. Такие правки нужно предварительно сохранить
и согласовать вручную. Затем восстанавливает исходные файлы/ссылки и удаляет только
entrypoints, которых раньше не было. Releases и backups остаются для проверки.
Остановить текущий qs, восстановить backup и перечитать Hyprland нужно вручную.
Откат файла биндов возвращает прежнее действие Super+R. Rofi не удалялся.

Для staging без рабочего HOME:

```bash
mkdir -p .cache/staging-home
./scripts/deploy.sh --target-home "$PWD/.cache/staging-home" --apply
./scripts/rollback.sh --target-home "$PWD/.cache/staging-home" --apply
```

## Автоматические проверки

```bash
lua tests/super-tap.lua
lua tests/binds.lua
python3 tests/launcher-routing.py
python3 tests/menu-routing.py
python3 tests/menu-backend.py
python3 tests/deployment.py
QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qmltestrunner -input tests
/usr/lib/qt6/bin/qmllint quickshell/shell.qml quickshell/components/MenuPanel.qml quickshell/modules/launcher/Launcher.qml quickshell/theme/Palette.qml
python3 tests/smoke-quickshell.py
python3 tests/runtime-menus.py
```

Также проверены Bash/Lua syntax и git diff --check. Qt6 qmllint exit 0, с известными
предупреждениями динамического PanelWindow/Screen/Margins и Loader.item metadata;
не заявляется lint без предупреждений. На Quickshell 0.3.2 фактическая загрузка
прошла без QML errors, binding loops, duplicate signals и ошибок типов.

`runtime-menus.py` запускает настоящие qs/IPC/Process со скрытыми instance-overrides
окон и подставными hyprctl, cliphist, wl-copy, power и application-командами.
Проверяет все девять меню, lazy unload, readonly справку, бинарный clipboard,
фокусировку по адресу, Quick Actions navigation, cancel/confirm, command и
обычный/терминальный desktop launch. Четыре конкурентных повторных старта оставляют
один исходный PID. Системные действия и реальный clipboard не выполняются.

`binds.lua` регистрирует 95 уникальных сочетаний в mock Hyprland и проверяет Super,
Q/D, command и Space. `super-tap.lua` проверяет state machine и порядок отпускания.
Это не физический тест клавиатуры. Разбор focus dispatcher дополнительно проверен
через read-only `hyprctl eval` без dispatch/focus текущих окон.

## Ручная приёмка всех сочетаний

Проводится после добровольного ручного подключения. До её завершения Rofi сохранять.
В каждом меню проверить обе раскладки, Alt+Shift, стрелки/Tab/Shift+Tab/Enter/Esc,
мышь, пустой результат, длинные названия, закрытие и повторное открытие.

| Клавиши | Ожидаемое действие |
|---|---|
| Super_L, Super_R отдельно; Super+Space | утверждённый Launcher v1.1 |
| Super+/, Super+F1 | searchable readonly справка из активных bind'ов |
| Super+V | clipboard; выбрать текст и изображение, проверить последующую вставку |
| Super+R | command; команда с аргументами, пробелами/пайпом; Escape ничего не запускает |
| Super+Tab | окно по названию/class; Enter переводит на его workspace и фокусирует |
| Super+A/G/I | Quick Actions; проверить каждый пункт и вложенную навигацию |
| Ctrl+Alt+Delete; кнопка питания; питание SwayNC | power, отмена подтверждения; разрушительные действия только по желанию оператора |
| Ctrl+Super+T | обои: пробелы/кириллица, выбор, сохранение после повторного входа |
| Super+M | media: play/pause, next, previous, mute |
| Super+Period | emoji в clipboard |
| Super+N | существующий SwayNC, DND и кнопки не изменились |
| Super+J | показать/скрыть выбранную панель (Waybar/Sidebar) |
| Ctrl+Super+P | battery/performance visual profile |
| Super+Return, Super+T, Ctrl+Alt+T | прежний Kitty |
| Super+E/W/C/X; Ctrl+Shift+Escape | файлы / Chrome-браузер / code / nano / task manager |
| Super+Q, Super+Shift+Q | закрыть тестовое окно; после отпускания Super поиск не появляется |
| Super+D/F | maximized/fullscreen, без ложного Launcher |
| Super+Alt+Space/P | float / pin |
| Super+стрелки, Super+Shift+стрелки | фокус / перемещение окна |
| Super+mouse left/right | drag / resize, без ложного Launcher |
| Super+1…0 | workspace 1…10 |
| Super+Alt+1…0, Super+Shift+1…0 | перемещение на workspace без/с follow согласно существующим bind'ам |
| Ctrl+Super+Left/Right | предыдущий/следующий workspace |
| Super+S, Super+Alt+S | показать scratchpad / отправить окно |
| Alt+Tab | прежний compositor cycle_next |
| Super+Shift+S/C, Print, Ctrl+Print | область / color picker / screenshot в clipboard / файл |
| Super+Shift+R, Ctrl+Alt+R | start/stop записи области / экрана |
| Super+Shift+N/B/P/M, Super+Alt+M | media next/previous/pause, mute output/input |
| Super+L, Super+Shift+L | lock / sleep, без появления панели на lock-screen |
| Audio/brightness XF86 | прежние аппаратные регулировки |
| Alt+Shift | us ↔ ru во всех полях, Kitty и Chrome |

Дополнительно: оба порядка отпускания Super+Q/D/R/Tab и unbound клавиши,
Ctrl/Alt/Shift удержаны до Super, два Super вместе, reload после отпускания клавиш,
lock/unlock и suspend/resume. После каждого chord одиночный Super снова работает.

Проверить 1366×768, внешний экран/hotplug, фокус новых окон, отсутствие двух
экземпляров qs, `menus.status == unloaded` после закрытия и idle CPU/RSS.
Физическая матрица, видимые focus/scale и расход батареи автоматически не измерялись.
Если выявляется реальная проблема ввода, только тогда исследовать QtWayland textinput.

Pixel Sidebar v2.1 добавляет выбор панели без изменения бинда Super+J: [режимы и восстановление](sidebar.md).

Размещение v2.3: меню больше не центрируются по горизонтали; системные меню
привязаны сверху слева, команды/clipboard/windows/emoji — снизу слева, с учётом
Sidebar/Waybar. Полная таблица, размеры и ручные проверки:
[popup-placement.md](popup-placement.md).
