# PixelRail v2.6 — Live Sliders и System OSD

## Архитектура

В существующем qs работают `modules/system/SystemControls.qml` (singleton) и
тестируемый `SystemState.qml`. Sidebar и Control Center читают тот же default sink,
а `PwObjectTracker` один на выбранный sink. PipeWire backend сохранён; нет второй
копии mixer-state и опроса wpctl. При ready=false/смене sink очередь старого
устройства отменяется. Отсутствующий default sink не заменяется вымышленным.

Яркость обслуживает прежний desktop.py/brightnessctl. Одна Process, одно последнее
ожидающее значение, throttle 40 мс. Пока выполняется job, новая цель заменяет
предыдущую, а не добавляется в FIFO. Final при отпускании запускается сразу при
свободном backend или после уже идущего job; он живёт в singleton и не теряется
при закрытии Control Center. Ответ сохраняется как реальное состояние системы.
UI во время drag не подменяется ответом предыдущего запроса.

`LiveSlider.qml` явно задаёт live/wheelEnabled. Локальные value/position/проценты
обновляются сразу; Binding к backend активен только вне drag и вне собственной
неподтверждённой записи. Поэтому проценты не ждут backend, а старый ответ не
переставляет бегунок под мышью. После подтверждения привязка возвращается к
системе. Изменения физическими клавишами продолжают отображаться по реальному
состоянию даже при следующем pending аппаратном запросе.

Звук записывается через существующий PipeWire backend Quickshell. Записи
объединяются каждые 40 мс, последний release flush не ждёт timer. Нет процессов
на каждое движение ползунка громкости.

В Quickshell 0.3.2 writable volume/muted обновляются оптимистически:
[исходник PwNode](https://raw.githubusercontent.com/quickshell-mirror/quickshell/v0.3.2/src/services/pipewire/node.cpp).
Поэтому локальный сигнал сам по себе не подтверждает реальный уровень OSD.
Для аппаратного управления выполняется объединённое асинхронное чтение через
имеющийся `pw-dump -N`: параметры Node, либо Device Route для аппаратного sink.
Линейные каналы преобразуются в используемую Quickshell кубическую шкалу.
Одновременно работает максимум один reader; устаревший ответ другого sink
отбрасывается. Подтверждённое состояние общее для Sidebar, Control Center и OSD.
При отсутствии `pw-dump`, ошибке чтения или исчезновении устройства предполагаемое
значение не показывается как реальное. Новые пакеты и демоны не устанавливаются.
Ползунки не запускают этот OSD-readback. Для неподтверждённой native-записи есть
конечный timeout 1 с и сообщение об ошибке.

Яркость: `brightnessctl -m -c backlight set N%` возвращает machine-readable
readback после записи — отдельный get после каждого set не запускается.
`pixelrail-desktop` вызывает тот же Python backend напрямую без двух shell forks
readlink/dirname на каждое движение. На 40 мс приходится максимум одна попытка;
медленный backend уменьшает частоту, не блокируя UI. Одна запись — Python helper
и brightnessctl, а не сотни процессов в секунду. Cached/external read также
объединяется с записью, и очередь не растёт.

Пределы: UI яркость 1–100%, аппаратный путь 0–100%, как в проверенном v2.6.
Проблемный аргумент `-n 1` удалён пользователем после теста T480 и не возвращается.
Шаг ±5%. Для громкости UI/raise ограничены 100%, lower
уменьшает реальный текущий уровень на 5 пунктов, включая внешние значения >100%;
нижняя граница 0. Mute не сбрасывается произвольно при регулировке громкости.

## Внешние изменения яркости без polling

`BacklightWatch` добавлен в уже используемый native Qt-плагин. Это read-only
NETLINK_KOBJECT_UEVENT socket + QSocketNotifier в event loop того же qs. Не udevadm
monitor, не новый демон, не дополнительный процесс. Обрабатываются только kernel
messages (sender nl_pid=0), точный SUBSYSTEM=backlight; число datagrams за callback
ограничено 64, всплеск объединяется в один refresh. Readback выполняется через
тот же desktop backend. SOURCE=hotkey разрешает OSD после readback, SOURCE=sysfs
от слайдера/другой программы — только синхронизацию состояния. Это поддерживает
firmware hotkeys, которые изменяют подсветку без обычного XF86 bind.

Основание: [Linux backlight API](https://docs.kernel.org/gpu/backlight.html)
документирует uevents при изменении actual_brightness и уведомления hotkey.
Обычный FileView/inotify для sysfs не используется как гарантия внешних событий.
При ENOBUFS запрашивается свежий readback, при постоянной socket error watcher
отключается, без busy-loop. Если plugin/socket недоступен, остаются refresh при
открытии, явный IPC refresh и общий путь физических XF86-команд; произвольные
внешние изменения без uevent тогда требуют повторного открытия/refresh.

Плагин необходимо пересобрать существующим build-native.sh перед deploy. Новых
пакетов не устанавливается; версия Qt должна совпадать с notification bridge.
Управление D-Bus notification ownership не изменено.

## OSD

`OsdController` — lazy Loader, один SystemOsd PanelWindow. При частых нажатиях и
смене brightness/volume используется тот же объект окна. Последний тип аппаратного
запроса имеет приоритет: медленный ответ яркости не заменяет более поздний volume
OSD. Значение берётся из readback/PipeWire properties, а не target арифметики.

Карточка 280×72 logical px, Material You surface/text/accent, radius 22, собственные
SVG speaker/mute, солнце, bar и процент. Время показа 1300 мс после последнего
подтверждённого события, fade/translate 120 мс; после fade окно выгружается.
Нет blur, постоянной анимации, desktop notification или отдельного qs.

Слева отступ как у остальных popup: layer-width Sidebar/Waybar + 12 px, вертикально
центр экрана. PopupPlacement ограничивает ширину, нет exclusive zone. KeyboardFocus
None и пустая input Region пропускают мышь/колесо, фокус не меняется. При Launcher,
Control Center, MenuPanel и pending переходах OSD сразу скрыт и не создаётся.
Слайдеры не генерируют OSD; завершение их записи после закрытия панели тоже не
генерирует OSD. История NotificationServer не используется.

## Диагноз «громкость недоступна»

Историческая диагностика v2.6 (не текущий диагноз пользовательского T480):
read-only проверка тогда показала:

- PipeWire 1.6.10 активен, Quickshell Pipewire.ready=true;
- nodes=2: Dummy-Driver и Freewheel-Driver, defaultAudioSink=null;
- wireplumber.service и pipewire-pulse.service не найдены, wpctl отсутствует;
- PulseAudio unit не найден, pactl info возвращает Connection refused.

Пользователь после v2.6 восстановил рабочие PipeWire/WirePlumber и проверил звук.
Ниже описана обработка отсутствующего sink, а не утверждение о нынешней системе.
В прежнем окружении недоступность была подтверждена, а не исправлена обходом проверки ready. Mute
больше не выглядит включённой кнопкой рядом с несуществующим устройством:
показывается disabled «—», ползунок скрыт. После появления реального ready sink
подписка восстанавливает управление без перезапуска qs. Установку/запуск сервисов
код не делает. Нельзя переносить этот диагноз на другой T480/session без проверки.

Команды только чтения на пользовательском T480:

```bash
systemctl --user status pipewire.service wireplumber.service pipewire-pulse.service --no-pager
pw-cli list-objects Node
wpctl status                 # если уже установлен
pactl info                  # необязательная проверка Pulse endpoint
qs list
qs ipc --pid PID call system state
qs ipc --pid PID call system refresh   # только backlight readback
```

Путь state сообщает audioAvailable/volume/muted/error, brightness/pending/busy,
наличие backlight events и состояние OSD. action=true означает принятую заявку,
не завершение записи. Настройки аудиосервера требуют отдельного решения; никаких
автоматических systemctl enable/start, установки WirePlumber или подмены backend.

## Мультимедийные клавиши

В hypr/pixelrail-end4-keys.lua изменены команды пяти существующих биндов, не
добавлены новые регистрации. Всего остаётся 95. Repeat flags сохранены.

| Событие | Команда |
| --- | --- |
| XF86MonBrightnessUp | pixelrail-system brightness-up |
| XF86MonBrightnessDown | pixelrail-system brightness-down |
| XF86AudioRaiseVolume | pixelrail-system volume-up |
| XF86AudioLowerVolume | pixelrail-system volume-down |
| XF86AudioMute | pixelrail-system volume-mute |

Wrapper посылает один system.action IPC текущему qs по config, не запускает shell
повторно. Если IPC недоступен, выполняется старый brightnessctl/wpctl fallback с
ограничениями. IPC=false (устройство отсутствует) не вызывает второй параллельный
backend. Ни в одном пути нет notify-send. Другие бинды и mic-mute не менялись.

Проверяйте реальные keysym через уже установленный wev, `hyprctl -j binds` и
поведение FnLock; не предполагается универсальная комбинация Fn. Если firmware
сама меняет brightness, наблюдается kernel hotkey event, но отсутствие события
на конкретном драйвере требует ручной проверки. Встроенный скрипт не remap-ит
клавиатуру, не меняет раскладки, BIOS, драйверы или службы.

## Проверки

```bash
python3 tests/system.py
python3 tests/system-native.py
python3 tests/system-ui.py
python3 tests/system-runtime.py --soak-seconds 120
python3 tests/control-ui.py
lua tests/binds.lua
```

Qt UI проверяет value/percentage во время удержания, старые ответы, короткий drag,
release вне, keyboard/wheel, коалесцирование 100 requests, final flush, смену sink,
mute/recovery, отсутствие OSD от слайдеров, reuse, таймер, suppression/focus и цвета.
В одном прогоне 100 быстрых заявок дали несколько реальных fake-backend записей,
а не 100 процессов. Native test компилирует настоящий parser uevent и не отправляет
синтетические сообщения ядру.

Runtime использует настоящий qs/layer-shell/IPC и native plugin на отдельной шине,
все PanelWindow unmapped, только fake audio и private-file brightness. Kernel
события в fake core вводятся тестовым IPC; реальный parser проверяется отдельно.
Слушатель не передаёт случайные физические события пользовательской сессии в fixture. Нет записи
реальных громкости/яркости. Проверяются placement, отсутствие focus/exclusive zone,
переключение типа с запоздавшим ответом, suppression при CC, hardware/sysfs события,
last slider write после закрытия, отказ записи/восстановление, неподтверждённый
volume с timeout без fake OSD и отсутствие desktop notifications.

Результат ограниченного двухминутного прогона: 428 циклов, RSS 144.71–145.81 MiB
без роста, одна плашка во время потока событий. Это mock workload, не суточный GUI
тест и не доказательство изменения physical idle энергопотребления. Навигационный
benchmark v2.6: A→N ~58.24 мс, N→A ~58.38 мс (QML state-ready, не presented frame),
без заметного изменения против сопоставимого v2.5. Cold RSS вырос ~6 MiB из-за ранней
инициализации PipeWire; после прогрева разница около 2 MiB, без доказанного
значимого эффекта. Idle CPU на коротких окнах не считается точным измерением 0.2%.

## Установка и откат

```bash
cd ~/Projects/pixelrail
./scripts/build-native.sh
./scripts/deploy.sh
./scripts/deploy.sh --apply
# Откат пользовательского релиза:
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Deploy автоматически не выполняется, режим уведомлений не переключается. EPP,
governor, NVIDIA PM и прочие power policies не меняются. Если новый native watcher
не собран, slider/XF86 IPC остаётся доступным, но полноценная event sync требует
сборки. Уже установленный Rofi/Waybar/SwayNC не удаляются и не перенастраиваются.

Вручную на T480: реальные Fn/XF86 events, существующий рабочий audio sink, drag
в обе стороны с удержанием и короткими движениями, отпускание вне, mute/повтор,
аппаратная яркость при открытом CC, внешняя программа, меню/фокус/Escape, показ
OSD на нужном output при HiDPI/hotplug, Dark/Light/Auto. Не утверждаем физическое
изменение громкости без default sink или отсутствие длительного аппаратного бага
на основании fake-устройств. Пакеты/службы при разработке не менялись.

Readback-тест отдельно проверяет ответ сервера 23% / mute при запрошенных 81%: OSD показывает 23%, а не оптимистическое свойство.
