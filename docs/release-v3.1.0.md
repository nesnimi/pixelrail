# PixelRail v3.1.0 — финальный кандидат

Подготовлен без deploy, commit, тега, перезапуска рабочего qs и изменения живого
HOME. **Stable не объявлен**: требуется аппаратная приёмка владельцем T480.

## Launcher

- Быстрые действия «Снимок/Bluetooth/Настройки/Обои», заголовок и контейнеры удалены.
  Соответствующие команды, панели и горячие клавиши сохранены.
- Сетка использует реальные Categories и статистику. Settings/HardwareSettings,
  микшеры и файловые помощники не заполняют её по алфавиту. FileManager/терминал/
  браузер/редактор и основные пользовательские категории имеют понятный приоритет.
  Два осознанных запуска могут поднять утилиту; одного случайного запуска мало.
  Отдельного существующего источника избранного в PixelRail нет.
- Hidden/NoDisplay, XDG override, OnlyShowIn/NotShowIn учтены. Последние два поля
  ограничивают стартовый экран, но не мешают явному поиску утилит. Исправление
  основано на проверке фактического DesktopEntries Quickshell 0.3.2: этих полей
  в API нет и фильтрация окружения там не выполняется.
- Один асинхронный reader стандартной библиотеки Python читает только XDG
  applications, затем завершается. Повторное чтение — по изменению каталога,
  без polling/демона и без нового поискового индекса. При отказе доступен список.
- Одинаковые команды объединены, разные аргументы/Terminal/рабочие каталоги
  сохраняются. Частота учитывается до объединения; статистика не сбрасывается.
- Без качественных кандидатов показывается обычный список. Сетка до 4×2,
  панель 540×308 px при двух рядах; поиск 48 px, иконки 32 px. В поиске остаются
  пять видимых строк, точное/префиксное ранжирование, Original/Pixel Themed.

## Проверки

Qt6 qmllint: 40 QML-файлов, exit 0. Остаются предупреждения динамических
Loader/PanelWindow типов из метаданных; runtime не выявил ошибок типов/binding loops.
QtTest: 14 passed; desktop metadata: 3 unit-теста; Launcher Qt UI: категории,
visibility/дубликаты, поиск утилит, fallback/отказ helper, RU/EN, клавиши, безопасный
Exec, Original/Themed, контраст, сохранение частоты и перезапуск — passed.

34 финальные регрессионные команды прошли: Qt/Control UI, Notifications/DND,
Clipboard PNG/JPEG/WebP/Unicode, Wallpaper, Material You, ресурсы/лицензии/caches,
Settings, системные slider/OSD/native tests, keyboard/Sidebar/session events,
Control/runtime IPC, screenshot backend/Escape/runtime, popup placement,
launcher routing, lifecycle/autostart, release reliability, deployment/rollback,
Hyprland Battery/Performance parser, Power Audit, benchmark unit, 95 биндов и Super-tap.
Один screenshot-runtime потребовал исправления гонки теста и повторного запуска
(см. ниже); исходный сбой сохранён в логах, не замаскирован пропуском.
Проверена доставка нового metadata helper и сохранение Launcher state при откате.
Защищённые исходники, focus/grab/Escape-guard, slurp DEVNULL и brightnessctl без
`-n 1` сохранены. `git diff --check` прошёл. Логи: `.cache/stable-results/`.
Все GUI-сценарии используют offscreen/unmapped поверхности, fixtures, отдельные
HOME/runtime/D-Bus; это не аппаратная приёмка и не снимки рабочего T480.

В screenshot-runtime исправлена гонка **теста**: короткий watchdog 150 мс теперь
вооружается после готовности fake-selector, а не включает его Python/IPC startup.
Проверка настоящего watchdog/cleanup сохранена. Производственный захват не менялся.

## Ограниченный benchmark

Один запуск существующего tests/benchmark-runtime.py, без soak: 50 циклов Launcher,
50 A↔N в каждом направлении, 30 Clipboard, 20 Wallpaper, 20 вложенных страниц,
200 тестовых уведомлений и переключения темы. Один PixelRail qs; история ограничена
60 записями/20 live, повторный одинаковый palette JSON не вызвал присваиваний.

| Метрика (IPC/QML state, без первого кадра) | median / p95 |
| --- | --- |
| control.state round trip, 20 выборок | 29,47 / 30,37 мс |
| Launcher open→state→hide, 50 | 86,65 / 88,73 мс |
| A→N state, 50 | 58,23 / 59,99 мс |
| N→A state, 50 | 58,08 / 59,81 мс |

RSS: cold baseline 157,65 МиБ → warm 181,37 → после 50 Launcher 174,84 → settled
184,70 → после темы/уведомлений и завершения 174,79 МиБ. Значения не растут
монотонно; ограниченный прогон не показал очевидной утечки, но не доказывает
отсутствие всех долгосрочных утечек. На спокойных 1–2-секундных интервалах CPU
0,0% одного ядра; разрешение счётчика около 0,5–1 процентного пункта, интервалы
с завершающейся работой доходили до 1%. Это не точный аппаратный idle 0–0,2%.

Исторический RC1 в том же unmapped harness: Launcher median 85,82 мс, settled RSS
188,47 МиБ. Разница latency около 0,8 мс не даёт основания объявлять ускорение или
регрессию; условия/версия отличаются от установленного RC5. Реальный кадр, idle
T480, GPU PM и энергопотребление не измерялись; ориентир 5,39 Вт не перепроверен.
JSON: `.cache/stable-results/benchmark.json`; новых постоянных процессов/polling нет.

## Изменённые файлы этого этапа

- Launcher.qml, Search.js; новый `scripts/launcher_entries.py`.
- SettingsPage.qml: только подпись версии в разделе «О PixelRail».
- tests/launcher-ui.py, tst_search.qml, новый launcher-entries.py, deployment.py;
  runtime-menus.py/screenshot-escape.py — путь к reader в fixtures;
  screenshot-runtime.py — порядок включения watchdog в тесте.
- README.md, CHANGELOG.md, docs/installation.md, launcher.md, performance.md,
  design/cursor.md и этот отчёт. Все более ранние изменения RC сохранены.

## Git и ресурсы

Существующие незакоммиченные изменения всех RC сохранены. В дереве много нужных
неотслеживаемых QML, Python, native headers, SVG/Roboto и тестов: их необходимо
включить в будущий commit, а не коммитить только tracked diff. Список проверки:
`.cache/stable-results/untracked-files.txt`. Случайных .tmp/.part/.o/.so вне
игнорируемого cache/build не обнаружено. Ничего не удалялось.

Roboto — SIL OFL; Material Symbols Rounded — Apache-2.0; GoogleDot — GPL-3.0.
Лицензии/источники находятся в assets и docs/design. Original icons берутся из
установленных Linux-пакетов, не переупаковываются. Бинарный native plugin игнорируется
Git и собирается локально. При новом checkout нужны исходники, native headers и
ресурсы; исходные pixelrail_1/2.png — необязательные референсы владельца.

GoogleDot Black/White и aliases проверены, установки нет. Cache тем не является
обязательным компонентом оболочки. [Команды установки, backup текущей темы и
runtime-отката](design/cursor.md#сохранение-текущей-темы-и-откат); постоянные GTK/Qt/
Hyprland-фрагменты применяются владельцем вручную после сравнения с backup.

## Установка / откат владельцем

```bash
cd ~/Projects/pixelrail
# На новом checkout / после смены Qt; поверх RC5 при неизменном Qt не требуется:
./scripts/build-native.sh
git diff --check
./scripts/deploy.sh                 # dry-run
./scripts/deploy.sh --apply         # только после просмотра плана
# Откат:
./scripts/rollback.sh               # dry-run
./scripts/rollback.sh --apply
```

Deployment сохраняет theme/desktop/panel/notifications и Launcher XDG state,
проверяет новый IPC до завершения старого управляемого процесса. Waybar/SwayNC
остаются fallback. Драйверы, службы и системное питание не меняются.

## Будущий Git-релиз — только после ручной приёмки

Эти команды **не выполнялись**. Перед stage проверить diff и перечисленные новые
файлы; исходные референсы владельца автоматически в список не включены.
После приёмки владелец меняет Unreleased на дату выпуска в CHANGELOG, статус
кандидата в README/этом отчёте и подпись версии SettingsPage.qml, затем делает commit.

```bash
git status --short
git diff --check
git add -- README.md CHANGELOG.md docs hypr quickshell scripts share tests
git diff --cached --check
git diff --cached --stat
git diff --cached                  # внимательно просмотреть, включая ресурсы
git commit -m "Release PixelRail v3.1.0"
git tag -a v3.1.0 -m "PixelRail v3.1.0"
# Только если настроен правильный remote и владелец решил публиковать:
git push origin HEAD
git push origin v3.1.0
```

## Аппаратная приёмка T480

- [ ] Пустой Launcher: нет случайных помощников/действий; частота и список fallback.
- [ ] Super, RU/EN, Alt+Shift, стрелки/Tab/Shift+Tab/Enter/Escape, outside click,
  запуск и повторное открытие, оба стиля иконок, длинные названия.
- [ ] Sidebar 54 px / zone 66, workspace 1–5, приложения текущего workspace,
  оригинальный векторный логотип последним; мониторы/масштаб/1366×768.
- [ ] Super+A/N, resize handle/сохранение высоты, Wi-Fi/BlueZ scan/connect, EN/RU,
  батареи и Battery/Performance (только графические эффекты).
- [ ] Живые яркость/звук, mute, Fn/XF86 и OSD; нет brightnessctl `-n 1`.
- [ ] NotificationServer/D-Bus, история/DND/действия/очистка и SwayNC fallback.
- [ ] Clipboard текст/изображения/Ctrl+V, Wallpaper preview/apply/cancel,
  ThemeManager Dark/Light/Auto/accent и Settings persistence.
- [ ] Super+Shift+S при открытых панелях: selector/cancel/repeat/reset,
  обычный Escape/outside click после отмены; slurp stdin=DEVNULL сохранён.
- [ ] После deploy и rollback один PixelRail qs, IPC готов, настройки сохранены.
- [ ] Сопоставимый idle Power Audit/benchmark на батарее; GoogleDot отдельно opt-in.

После этой приёмки владелец может объявить v3.1.0 Stable и выполнить Git-команды.
