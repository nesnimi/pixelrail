# Screenshot Mode — v3.1 RC2, исправление lifecycle

Бинд не изменён: `Super+Shift+S` → `hypr/pixelrail-end4-keys.lua` →
`~/.local/bin/pixelrail-shot` → `screenshot.py`. Backend прежний:
`slurp` → `grim -g` → PNG в `${XDG_PICTURES_DIR:-$HOME/Pictures}/Screenshots` →
`wl-copy --type image/png`. Зависимостей, новых биндов и экземпляров qs не добавлено.

## Критическая регрессия и подтверждённые причины

В прежней реализации `active` означало любое `phase != idle`, включая состояние
**до запуска worker** и `stopping`. Включение этого флага отключало Escape,
Wlr keyboard focus и HyprlandFocusGrab сразу во всех popup. Таймеры включались
после команды запуска; startup guard проверял `Process.running`, а не готовность
worker. Watchdog вызывал `abort`, но тот ждал завершения worker, чтобы снять флаг.
При игнорировании SIGTERM / отсутствии ожидаемого exit состояние не очищалось.

Это воспроизведено на настоящем Quickshell 0.3.2 с изолированным worker:
через секунду после watchdog `active=true, phase=stopping`, повторный capture=false.
Скрипт при этом считал **false** успешным запуском и молча возвращал код 0.
Поэтому зависание одновременно блокировало Escape и все последующие снимки.
Дополнительно любой отказ slurp считался отменой, stderr отбрасывался — причина
первого отказа selector была скрыта.

После первой правки lifecycle владелец подтвердил на T480 отдельную причину
отсутствия selector: `slurp </dev/null` открывал выделение, а через worker stdin
slurp оставался pipe. `Popen` без явного stdin наследовал открытый канал QML →
worker. Slurp читает прямоугольники из нетерминального stdin до EOF; канал
handshake остаётся открытым, поэтому worker показывал `capturing`, но selector
ещё ждал входные данные. Предыдущие fake tools не читали stdin и пропустили баг.

Теперь только slurp запускается с `stdin=subprocess.DEVNULL`: EOF доступен сразу,
stdout по-прежнему содержит результат выделения, stderr сохраняется для диагностики.
Stdin worker остаётся доступен для READY/GO. ScreenshotState, IPC/reset, grim,
wl-copy, Escape и cleanup этим точечным исправлением не изменялись.

## Исправленный протокол

1. `pixelrail-shot` проверяет доступность screenshot IPC чтением `state`.
2. `capture` запускает отслеживаемый QML `Process`, заранее включив ограниченные
   startup/capture timers. В `starting` обычный Escape продолжает работать.
3. Python проверяет grim/slurp/wl-copy и устанавливает обработчики завершения.
   Только реальный worker сообщает JSON `ready` в stdout.
4. QML включает suppression, снимает keyboard/focus grabs и через `Qt.callLater`
   отправляет `capture\n` в stdin worker. Только после этого запускается slurp.
   Worker подтверждает `selecting`; этим завершается startup guard.
5. Success, cancel, ошибка и crash снимают режим. SIGTERM/INT и parent-death signal
   завершают только собственные slurp/grim; clipboard owner wl-copy сохраняется.

`active` теперь требует живого Process с PID **и** фазы `arming/capturing`.
Застрявшая строка phase без worker не отключает Escape. `abort/reset` немедленно
снимают suppression, не дожидаясь exit; через 500 мс оставшийся собственный Process
получает SIGKILL. Startup guard — 5 с, аварийный предел всей операции — 5 минут.
Таймеры одноразовые и работают только во время операции/cleanup; polling в простое нет.

Capture return — принятие запроса, не отрисовка selector. CLI отдельно проверяет
startup и сообщает отказ вместо молчаливого успеха. Повторный запрос во время
настоящего захвата не прерывает его и не создаёт второй selector; возвращается
понятная ошибка с командой reset. При сбое IPC после запроса выполняется reset,
**standalone selector повторно не запускается**, поскольку доставка могла состояться.
Если read-only preflight показывает отсутствие shell/API, доступен прежний standalone
захват без запуска qs. Сохранение popup в таком fallback не гарантируется.

Только `selection cancelled` (реальная строка установленного slurp при Escape),
либо пустая отмена с exit 0/1 считаются отменой. Ошибки display/keyboard grab и
другой stderr, ошибка grim, исключение Python и неисполняемый helper — реальные
ошибки с диагностикой. Частичный PNG удаляется; готовый файл при сбое wl-copy
сохраняется. Существующие снимки не перезаписываются.

## Popup и Escape

ScreenshotState используется только в:

- Launcher / Control Center / MenuPanel: Wlr keyboardFocus, FocusGrab.active/onCleared;
- Launcher/MenuPanel: Keys Escape;
- Control Center / Clipboard / Wallpaper: window Shortcut Escape.

Во время подтверждённого capture эти автоматические dismiss/Escape временно
подавлены. Явные closeRequested/IPC close не блокируются. Окна не пересоздаются,
скрытые панели не открываются. После success/cancel/reset/error восстанавливаются
обычный Escape, keyboard focus и outside-dismiss. Другие бинды не изменены.

## Диагностика и аварийный сброс

После установки исправления:

```bash
pixelrail-shot --status
pixelrail-shot --reset
```

Прямой IPC для выбранного установленного release:

```bash
shot_qml="$(dirname "$(dirname "$(readlink -f "$HOME/.local/bin/pixelrail-shot")")")/quickshell/shell.qml"
qs ipc -p "$shot_qml" call screenshot state
qs ipc -p "$shot_qml" call screenshot reset
qs log -p "$shot_qml" --no-color -t 100
```

`state` показывает active, phase, pid, running, helper, generation, error, outcome,
lastExit и состояние watchdog/cleanup. `reset` не завершает qs и не открывает окна.
`abort` также сохранён и теперь немедленно возвращает Escape. В старом RC2 до
установки этого исправления существует только `screenshot abort`; гарантированное
снятие зависшего режима реализовано новой версией QML, не одним новым CLI.
Нельзя копировать только скрипт: QML и worker доставляются одним release.
Не применять pkill/killall или перезапуск всей пользовательской сессии.

## Проверка

```bash
python3 tests/screenshot-backend.py
python3 tests/screenshot-runtime.py
python3 tests/screenshot-escape.py
python3 tests/control-ui.py
lua tests/binds.lua
lua tests/super-tap.lua
```

Runtime дополнительно проверяет фактический `/proc/self/fd/0` дочернего selector:
он должен указывать на `/dev/null`, а чтение — сразу возвращать EOF, несмотря на
открытый handshake pipe worker. До исправления эта проверка воспроизвела `pipe:[…]`.
После исправления пройдены `screenshot-backend`, `screenshot-runtime`,
`screenshot-escape`, `control-ui`, 95 Lua bindings и Super-tap. Результаты именно
этого патча: `.cache/screenshot-stdin/results.json`; исходное падение — `before.log`.

Backend: routing/fallback, подтверждение запуска, отказ и потеря IPC, slurp cancel
с реальным текстом, slurp/grim error, collisions, SIGTERM/SIGKILL cleanup.
Runtime: настоящий qs/IPC/Process, private HOME/XDG/D-Bus, unmapped panels и fake
capture tools/focus protocol. Проверяются 12 popup, сохранение объекта, ready до
selector, cancel/repeat/duplicate/error/crash, отсутствие/права helper, исключение,
отсутствие handshake, watchdog при игнорировании TERM, ручной reset, устаревшая
phase, потеря IPC после capture и повтор после неё, восстановление grabs и один qs.
Qt UI: настоящие Escape в A/N, Launcher, Clipboard, Wallpaper, keys/power/command
до capture, при stale state и failed start, во время capture и после reset.

Регрессионные результаты и логи: `.cache/screenshot-fix/results.json` и соседние
`*.log`. Ошибки fake helper/tool в негативных сценариях ожидаемы; JavaScript/QML
TypeError/ReferenceError/Binding loop не допускаются.

Фактический прогон исправления: 21 Python/UI/runtime suite, 95 Lua bindings,
Super-tap, Qt6 qmllint (exit 0, известные предупреждения static metadata) и QtTest
(10 PASS). Пройдены IPC/routing, Notifications/D-Bus, Material You, EN/RU, Sidebar,
placement, live sliders/OSD, deploy/rollback и lifecycle в изолированных HOME.
После последней правки повторно пройдены backend, Escape, screenshot runtime,
Control UI, deployment и lifecycle runtime — `.cache/screenshot-fix/final-targeted.json`.
Дополнительно установленный `/usr/bin/slurp` проверен с несуществующим тестовым
Wayland-сокетом: отказ соединения возвращается как ошибка, без захвата/буфера.
Рабочий qs остался с прежним PID; тестовых qs после cleanup нет.

Безопасная установка пользователем (автоматически не выполнялась):

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh          # dry-run
./scripts/deploy.sh --apply  # только после просмотра плана
pixelrail-shot --status
```

Откат: `./scripts/rollback.sh` для просмотра, затем
`./scripts/rollback.sh --apply`. Installer/lifecycle не изменялись этим исправлением.

## Ручная приёмка T480

1. Убедиться, что `pixelrail-shot --status` показывает idle/inactive.
2. A → Escape; N → Escape; одиночный Super → Escape; V → Escape; Wallpaper → Escape.
3. A → Super+Shift+S → выделить панель: она остаётся видимой и присутствует в PNG.
4. N, Launcher, Clipboard, Wallpaper, power/keys: повторить сохранение и Ctrl+V PNG.
5. Отменить slurp через Escape: исходная панель остаётся открытой. Второй обычный
   Escape закрывает её. Затем снова открыть и повторить захват.
6. После захвата проверить outside click, клавиатурный фокус и Super/Q/D.
7. Проверить ошибки через `--status`/`qs log`; `--reset` возвращает обычный Escape.
8. Убедиться, что qs один. Проверить оба монитора при наличии.

Настоящий selector, compositor keyboard grabs, physical key delivery и пиксели PNG
требуют этой проверки на T480. Автотесты не заменяют её: во время разработки не
запускались live capture, deploy, смена буфера, sudo или изменение настроек.
