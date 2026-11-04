# Battery / Performance — только графика

Финальная проверка кандидата v3.1.0 и границы измерений:
[отчёт](release-v3.1.0.md#ограниченный-benchmark). Один unmapped прогон: Launcher
open→state→hide median 86,65 мс, RSS после завершения 174,79 МиБ, один qs.
Это не время первого кадра и не аппаратный idle/энергопотребление T480.

`pixelrail-profile battery|performance|toggle` сохраняет прежнее поведение:
файл `${XDG_CACHE_HOME:-$HOME/.cache}/pixelrail/profile`, reload Hyprland и уведомление.
Политики CPU/GPU, TLP, службы и драйверы не меняются. Профиль переключается в
Quick Settings/PixelRail Settings; в минималистичной Sidebar остаются Power/Wi-Fi/Battery%.

В `hypr/hyprland.lua` исправлена схема установленного Hyprland 0.57:

```lua
hl.curve("pixelrail", { type = "bezier", points = { {0.22, 1.0}, {0.36, 1.0} } })
hl.animation({ leaf = "global", enabled = fancy, speed = 3.5, bezier = "pixelrail" })
```

У windows/workspaces/fade также используется `bezier="pixelrail"`, не `curve`.
Скорости соответственно 3.5/4.0/3.0; существующие popin/slidefade сохранены.
Global имеет speed даже при выключенном профиле, поскольку валидатор проверяет
параметры объявления. Battery выключает глобальные анимации, blur и shadow;
Performance включает прежние лёгкие эффекты. Новых blur-эффектов не добавлено.

```bash
python3 tests/performance.py
```

Тест запускает настоящий `Hyprland --verify-config` отдельно для Battery и
Performance с копиями Lua в тестовом HOME; оба дали `config ok`. В verify-only
окружении возможна служебная Socket2 warning, это не animation/configerror.
Работающий compositor не перезагружается и живая конфигурация не записывается.

Deploy сохраняет существующий пользовательский hyprland.lua и использует
исправленный исходник при свежей установке. Уже вручную исправленный конфиг
пользователя не перезаписывается. Физическую плавность и `hyprctl configerrors`
после самостоятельной установки/переключения нужно проверить в рабочем сеансе.

Этап 1 системной оптимизации v2.4: [energy.md](energy.md). Подготовлен read-only
аудит и отключённый EPP-кандидат; этот графический скрипт не менялся и EPP не управляет.

# v2.5 — Performance, Memory & Stability

## Аудит и подтверждённые исправления

| Компонент | Результат аудита |
| --- | --- |
| shell / контроллеры | Подтверждена ошибка отмены: menus.hide не сбрасывал pendingMenu за fade Launcher. Теперь pending запрос отменяется; регрессия до патча падала. Один процесс, существующие lazy Loader. MenuPanel выгружается после fade и завершения действия, Control Center — при закрытии. При A↔N тот же объект окна. Добавлены только read-only state IPC Launcher/MenuPanel для измерений. |
| Sidebar | Один SystemClock с precision Minutes; Hyprland/NetworkManager/PipeWire/UPower — события. hyprctl только при действии пользователя; профиль читается FileView. Таймерного опроса системных команд не найдено. |
| Launcher | DesktopEntries и поиск по событиям; скрытая панель сохраняет модель приложений. Принудительная выгрузка не внедрялась: выгода памяти/влияние на latency не доказаны. |
| Control Center | Поиск сетей 12 с/устройств 20 с только по кнопке; остановка при уничтожении. Яркость читается при открытии. DesktopState — один singleton, записи объединяются. Сохранять тяжёлое скрытое окно ради скорости не стали без доказанной пользы. |
| Notifications | 60 snapshots, 20 live, 3 queued popup/1 видимый, deadline Timer без polling. Подключения к QObject защищены проверкой existing.live. Подтверждён лишний двойной armTimer на одно adopt; оставлен один. Реальный QML-тест до исправления считал 2, после — 1, повторный adopt не дублирует refresh subscription. |
| ThemeManager | FileView.rearm нужен для atomic rename; второй reload сохранён. Подтверждено повторное присваивание тех же schemes: 10 записей идентичного JSON давали 10 schemesChanged. Теперь последнее успешно проверенное содержимое кешируется; идентичный текст не парсится/валидируется/присваивается снова. Повреждённый JSON не кешируется. Новые схемы и режимы обновляются по-прежнему. |
| Clipboard | Видимые миниатюры по запросу, не вся история; дисковый cache уже ограничен 256/64 MiB, QML-карты исчезают с MenuPanel. Исправный механизм не переписан. |
| Wallpaper | Подтверждён неограниченный дисковый cache. Теперь максимум 512 hash PNG / 128 MiB, текущая выдаваемая миниатюра защищена, временные/посторонние файлы и symlink не удаляются. Prune под тем же lock, вне UI. Оригиналы не трогаются. Cache-hit не декодирует заново и не меняет mtime. Ошибка загрузки вытесненного thumbnail вызывает одно ленивое восстановление, затем понятный отказ без бесконечного retry. |
| PopupPlacement | Чистые функции logical geometry, без таймеров/процессов. Привязки и дизайн не менялись. |
| Python / lifecycle | Одноразовые helpers. Исправленный v2.3 fast path сохранён; shell не стартует на каждый вызов. Discovery/IPC subprocess — измеримая часть latency. Переходить на постоянный Python-демон ради нескольких вызовов не стали. Lifecycle/deploy/rollback не переписаны. |

Это сокращение конкретной лишней работы, а не обещание снижения idle RAM/W.
В Power Audit, EPP, governor, NVIDIA, графических профилях, цветах и раскладке
нет изменений. Никакие кэши не очищались ради маленького RSS; Qt GC принудительно
не запускался. Измеренный прогрев, allocator retention и deferred destruction
учитываются отдельно от утечки. Изменения интерфейса ограничены восстановлением
вытесненного превью; размеры, размещение, навигация и рисунок сохранены.

## Benchmark

```bash
# По умолчанию только read-only control.state IPC и /proc, без открытия окон.
./scripts/pixelrail-benchmark --samples 20 --idle-seconds 10
./scripts/pixelrail-benchmark --samples 20 --idle-seconds 10 --json \
  > .cache/reference.json

# Только по явному запросу: открывает/закрывает меню, отменяет незавершённый ввод.
# Не выбирает clipboard entry, не применяет обои и не переключает тему/сервер.
./scripts/pixelrail-benchmark --exercise --stress --json > .cache/run.json
./scripts/pixelrail-benchmark --exercise --stress --json \
  --baseline .cache/run.json > .cache/repeat.json
```

После пользовательского deploy доступно имя `pixelrail-benchmark`. Новый CLI
не запускает qs автоматически. --pid выбирает только зарегистрированный owned
PixelRail текущего HOME/display; process_count имеет именно эту область, а не
считает чужие qs того же UID. По умолчанию samples=20, idle=2 с; всё конечно.

Граница измерения: **доставка IPC + подтверждённое состояние QML**, не получение
физической клавиши, не frame rendered/presented. `control_state_IPC` — только
round trip; A↔N дополнительно подтверждает loaded/section/opened. Launcher metric
включает open/state/hide. Menu metrics включают list-ready, close и ожидание unload
(в том числе существующий fade 140 мс); это не latency первого видимого кадра.
Превью изображений не обязаны декодироваться до list-ready. Cold Control Center
измеряется отдельно при открытии Wi-Fi после unload. Приведённые ~58 мс A↔N нельзя
напрямую сравнивать со 137 мс v2.3: тот замер включал Python route/discovery.

JSON содержит сырые выборки, n/median/min/max, nearest-rank p95 только при n≥20,
RSS и CPU по интервалам, initial/warm/settled этапы. CPU=100% соответствует одному
логическому ядру. При коротком окне 1 с шаг одного tick уже около 1%; для оценки
0–0.2% используйте 10–30 с и несколько независимых окон. RSS — не PSS/heap live
bytes; память shared библиотек и allocator caches не доказывает утечку.
`--baseline` выводит арифметическую разницу, не статистическую значимость;
сравнивать нужно одинаковые workloads, mode, devices, mapped state и фоновые задачи.

## Изолированные memory/stability тесты

```bash
python3 tests/benchmark.py
python3 tests/performance-qml.py
python3 tests/benchmark-runtime.py --output .cache/benchmark-current.json
python3 tests/benchmark-runtime.py --soak-seconds 600 \
  --output .cache/benchmark-soak.json
```

Тест копирует QML в временный HOME внутри `.cache`, скрывает PanelWindow на уровне
инстанса, создаёт отдельную D-Bus-шину без activation service directories. Нативный
NotificationServer настоящий, основная сессия/её владелец имени не переключается.
Системные API читаются без переключения устройств. Menu data конечные и подставные:
60 clipboard/text карточек с одним изображением, 80 wallpaper entries, cached 32×24
PNG. Это воспроизводимый тест allocations/lifecycle, не нагрузка полноразмерными
обоями или GPU-отрисовкой. Реальные decode/MIME/оригинальные байты проверяются
отдельными clipboard-wayland/wallpapers/runtime-menus тестами.

После прогрева: Launcher 50 раз, 50 пар A↔N, Clipboard 30, Wallpaper 20, вложенные
Wi-Fi/Bluetooth 20; 200 уведомлений, 10 dark/light переходов и 10 identical palette
atomic updates. Дополнительно выполняется конечный soak с интервалом около 2 с
между циклами. Снимаются RSS/starttime, caps истории и один owned процесс; после
завершения уничтожается только группа тестовых процессов до удаления HOME.
Никаких wallpaper apply/clipboard restore/device controls в benchmark fixture нет.
`--legacy` воспроизводит только старые повторные palette/timer операции в частной
копии для сопоставимого baseline. Полноценное изображение/фокус на T480 этим не
доказывается. Итоговый fixture-helper читает одну JSON-строку, как настоящий API; сравнимые
прогоны выполнены с одинаковыми данными и завершением thumbnail jobs.

Результаты конкретного прогона и ограничения приведены ниже; сырые JSON остаются
в `.cache/benchmark-*.json`. Отчёт не обещает снижение мощности без новых физических
контрольных серий после ручного deploy.

## Установка, проверка и откат

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh
./scripts/deploy.sh --apply
# После ручной проверки:
pixelrail-benchmark --samples 20 --idle-seconds 10
pixelrail-power-audit --samples 13 --interval 10 --jsonl
# Откат:
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Для воспроизводимости сохраняйте brightness, приложения, Chrome tabs, графический
профиль, питание/заряд и monitor scale. Вручную: физические Super/A/N/Escape,
фокус/клики вне, 1366×768 и hotplug, картинки большого размера, отзывчивость при
нагрузке и несколько минут стабилизированного idle. Показатель пользователя
5.39 W остаётся внешним baseline; его нельзя сравнивать с CPU-нагруженным прогоном
тестов или коротким snapshot. EPP и runtime PM при этом не меняйте.

## Зафиксированные сравнительные результаты

Два прогона на вариант, порядок A/B и B/A; before — private legacy copy, after — текущий код.
Интерфейс unmapped, Sidebar не активирована (отдельно проверена runtime-тестами).
Медиана / p95 в мс; навигационный эффект не считается доказанным ускорением.

| Метрика | До | После | n на вариант |
| --- | ---: | ---: | ---: |
| Control state IPC | 29.46 / 31.8 | 30.06 / 36.3 | 40 |
| Launcher open/state/hide | 86.38 / 89.21 | 89.35 / 103.39 | 100 |
| Cold Control Center (Wi-Fi) | 105.72 / 136.78 | 106.24 / 152.52 | 40 |
| A→N state | 58.0 / 66.15 | 58.83 / 71.44 | 100 |
| N→A state | 57.89 / 63.99 | 58.71 / 71.46 | 100 |
| Clipboard ready/close | 241.17 / 258.56 | 239.16 / 252.91 | 60 |
| Wallpaper ready/close | 239.37 / 246.57 | 241.63 / 253.0 | 40 |

Один after-прогон совпал с другой нагрузкой: отдельные median Launcher менялись
от ~86 до ~98 мс, A↔N — от ~58 до ~63 мс. После повторения в обратном порядке
устойчивого ускорения/замедления этих маршрутов не обнаружено; p95 в нагруженном
прогоне выше. Это не статистическое доказательство эквивалентности, и результаты
не следует выдавать за выигрыш v2.5. Оптимизации убирают конкретную лишнюю работу
на palette/notification events, а не меняют обычный IPC/nav путь.

RSS после прогрева: before 164.82/164.84 MiB, after 164.54/167.07 MiB.
После операций и пауз: before 161.95/162.92, after 162.40/162.01 MiB.
Разница ~0.2 MiB между средними конечными значениями меньше межпрогонного разброса;
уменьшение RAM не доказано. Cold baseline ~140 MiB без mapped UI не сопоставим
с пользовательскими 182–186 MiB рабочего desktop. Короткие тихие окна fixture
часто дают 0 ticks; при 1–2 с это не разрешает оценить выигрыш на уровне 0.2% CPU.
Read-only замеры живого старого релиза выполнялись при регрессионной нагрузке,
поэтому их CPU не считается idle baseline и не сравнивается с 5.39 W.

Подтверждённый эффект: 10 identical palette updates → 10→0 лишних schemesChanged;
один notification adopt → 2→1 deadline arm. Дисковый wallpaper cache ограничен
512/128 MiB вместо отсутствия предела. Cached thumbnail hit не сканирует весь
cache: pruning выполняется при catalog и создании нового thumbnail.

Финальный soak с исправленной JSON-line заглушкой:
`.cache/benchmark-soak-final.json`, 600 с операций (602.13 с с финальной паузой),
147 дополнительных циклов после основного stress. Один PID/starttime и один owned
qs, caps 60 snapshots / 20 live, панели закрыты, QML runtime errors отсутствуют,
тестовые descendants завершены до удаления HOME. RSS во время soak 163.25–171.47
MiB, конечное тихое измерение 172.04 MiB; warm перед stress 163.98 MiB. Это рост
около 8 MiB относительно warm, а не экономия памяти. После первых десятков циклов
значения колебались преимущественно в диапазоне 168–172 MiB без устойчивой
линейной зависимости от числа операций. Это не доказывает ни утечку, ни её
отсутствие на протяжении суток: retained allocations/GC/кэши требуют длительных
физических замеров. Принудительный GC/cache clear не использовался.

Для таблицы выше использованы только `benchmark-comparable-before{,-2}.json` и
`benchmark-comparable-after{,-2}.json`; exploratory before/after файлы с первоначальной
заглушкой не являются итоговым сравнением. Короткие CPU окна fixture дали обычно
0 ticks и иногда один tick (~1% за 1 с); снижения idle CPU на уровне 0.2% не доказано.

Финальные проверки: 23 существующих/целевых Python suite (UI, IPC/runtime, native
notifications, Material You, popup placement, Sidebar, Power Audit, clipboard bytes,
wallpapers, routing, lifecycle и deploy/rollback), новые benchmark unit tests,
QtTest LauncherSearch (3 PASS), 95 unique bindings и Super tap. Qt6 qmllint exit 0;
остаются известные warnings static metadata динамических Loader/PanelWindow.
Дополнительно проверены быстрые смены шести разных меню, отмена queued menu,
пустая палитра/fallback и восстановление удалённой миниатюры. Все тестовые
записи/сигналы выполнялись в sandbox; production deploy не запускался.

## Кандидат v3.0 / UI v2.7: ограниченный прогон

Сохранённый v2.6 и текущий кандидат: одинаковый benchmark stress workload,
unmapped окна, private NotificationServer, fake menu data, software fixtures.
Это IPC + QML state readiness, не время физической клавиши/presented frame.
Контролы нового UI добавляют on-demand диагностику и чтение реальной раскладки.

| Метрика | v2.6 median / p95, ms | кандидат median / p95, ms |
|---|---:|---:|
| control_state_IPC | 29.77 / 35.31 | 28.65 / 29.87 |
| launcher_open_state_close | 86.93 / 89.32 | 85.90 / 88.10 |
| A_to_N_state | 58.24 / 59.52 | 57.89 / 59.30 |
| N_to_A_state | 58.38 / 59.34 | 57.98 / 59.79 |
| clipboard_open_ready_close | 239.53 / 244.50 | 237.31 / 240.49 |
| wallpaper_open_ready_close | 242.49 / 246.95 | 244.73 / 284.31 |
| control_open_wifi_ready | 100.96 / 108.35 | 105.29 / 113.60 |

RSS до дополнительного soak: baseline 145.98 → 145.91 MiB, warm
165.24 → 167.59 MiB, theme/notifications settled 163.81 → 159.29 MiB.
Малые различия RAM/latency не считаем доказанным улучшением. Wallpaper p95 вырос
246.95 → 284.31 ms при близкой медиане: единичный прогон не отделяет шум от
регрессии; необходима повторная физическая приёмка, обещания ускорения нет.

Кандидат дополнительно прошёл 60-секундный soak (21 цикл, фактически ~63 сек):
RSS samples 164.85 → 173.25 → 171.41 MiB; после soak 171.41 MiB. В baseline
этого soak не было, сравнивать after-soak между версиями нельзя. Рост после
дополнительных сценариев/кэшей не является сам по себе доказательством утечки;
три выборки не доказывают её отсутствие. История ≤60, live native notifications
≤20, управляемый qs один, одинаковые palette reload не создают assignments.
Включены 50 launcher, 50 A/N switches, 30 clipboard, 20 wallpaper и вложенные
страницы Wi-Fi/Bluetooth, 200 notifications, десять Dark/Light переключений.

Короткие интервальные idle samples дали 0 CPU ticks — этого недостаточно для
точной оценки 0.2% или утверждения об улучшении. Физические ориентиры владельца
182–186 MiB и 5.39 W получены в других условиях и не сравниваются с fixture RSS.
Реальный battery drain, NVIDIA runtime PM и длительный idle здесь не измерялись.
Артефакты: `.cache/benchmark-v30-rc.json`, `.cache/v27-tests/results.json`.

Повтор того же stress workload без дополнительного soak: A→N median/p95
58.03/58.73 ms, N→A 57.97/58.79 ms; Wallpaper 238.36/244.41 ms;
Wi-Fi open 103.93/108.35 ms. Выросший p95 Wallpaper первого прогона не
воспроизвёлся. Baseline/warm/settled RSS 146.29/167.73/163.43 MiB. Это
поддерживает интерпретацию как вариации нагрузки, но не заменяет аппаратную
приёмку. Артефакт: `.cache/benchmark-v30-rc-repeat.json`.

## v3.1 RC1 — дизайн и стоимость UI

Одинаковый изолированный benchmark, unmapped QML, private NotificationServer,
fake menu data. Сравнение с сохранённым v3.0 candidate, не с физическим idle T480.
Значения — IPC/state-ready; presented frame не измерен.

| Метрика | v3.0 median / p95 ms | v3.1 median / p95 ms |
|---|---:|---:|
| control_state_IPC | 29.01 / 30.21 | 29.33 / 30.62 |
| launcher_open_state_close | 86.85 / 89.61 | 86.90 / 88.96 |
| A_to_N_state | 58.03 / 58.73 | 58.54 / 60.20 |
| N_to_A_state | 57.97 / 58.79 | 58.72 / 60.24 |
| clipboard_open_ready_close | 237.87 / 246.60 | 278.45 / 303.28 |
| wallpaper_open_ready_close | 238.36 / 244.41 | 282.08 / 285.47 |

RSS baseline: 146.29 → 166.47 MiB; warm: 167.73 → 188.25; theme/notifications
settled: 163.43 → 182.13. Рост RAM **не скрывается**: оптимизация памяти не
доказана; отдельная библиотечная причина не локализована. UI, bundled font и
QML type caches изменились, но это не доказательство точной причины роста.
Symbolic colorization вынесен в отдельный lazy компонент; экономия от этого
отдельно не доказана. Короткие idle интервалы дали 0 ticks, не точный CPU=0%.

Операции Clipboard/Wallpaper включают закрытие: общий motion изменён с 140 на
200 ms. Поэтому они стали длиннее; это не измерение backend decode/clipboard restore
и не время физического открытия. Reduced motion отключает эти анимации.

Дополнительный 60 s soak до завершающей полировки: 20 циклов, RSS samples
176.10/182.75 MiB, после settle 182.98; только две выборки не доказывают отсутствие
утечки. 50 Launcher, 50 A/N switches, 30 Clipboard, 20 Wallpaper, 200 notifications,
Dark/Light и detail pages пройдены, один qs; history ≤60/live ≤20; identical palette
assignments=0. Финальный повтор без soak также PASS.

Артефакты: `.cache/benchmark-v31-rc1.json` (soak),
`.cache/benchmark-v31-rc1-release.json` (завершающий прогон). Реальные батарея/5.39 W,
NVIDIA PM и автономность не переизмерялись. RAM/energy budget — ручной release gate.
