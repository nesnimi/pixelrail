# PixelRail v3.1 RC5 — Pixel Search 2.0

Подготовлено без установки и без Git commit/tag/push.

- Пустой запрос: до восьми приложений, сетка до 4×2. Приоритет у часто запускаемых
  через Launcher; остальные места занимают установленные приложения по алфавиту.
  Конкретные приложения не зашиты в код. Скрытые/удалённые приложения не выводятся.
- Частота хранится между сеансами в `$XDG_STATE_HOME/pixelrail/launcher.json`
  (fallback `~/.local/state/pixelrail/launcher.json`), максимум 64 идентификатора.
  FileView Quickshell 0.3.2 читает один раз асинхронно, пишет атомарно только при
  запуске приложения. Запросы поиска не сохраняются. Ошибка чтения даёт fallback
  к установленным приложениям; ошибка записи не мешает запуску.
- Быстрые действия используют существующие команды: `pixelrail-shot`,
  `pixelrail-control bluetooth`, `pixelrail-settings`, `pixelrail-menu wallpaper`.
  Закрытие/замена панелей и захват управляются прежними обработчиками этих команд.
- При вводе показывается прежний список приложений: точное название → начало
  названия → остальные совпадения. Сохранены id/genericName/keywords и несколько
  слов. Другие источники не имитируются. Счётчик подписан «Найдено: …».
- Стрелки перемещают выбор по сетке и действиям, Tab/Shift+Tab — последовательно,
  Enter запускает выбранное; поиск сохраняет фокус. RU/EN и прежний Escape сохранены.
- Материал, шрифты и Original/Pixel Themed — существующие компоненты RC3.
  На 1366×768 стартовый экран 540×378 px, клетки 80 px; список остаётся до пяти
  видимых строк. Положение снизу слева и inset Sidebar не менялись. При малой
  высоте стартовое содержимое прокручивается с раскрытием выбранного элемента.
  Новых процессов в простое, polling, демонов и зависимостей нет.

Изменены: `quickshell/modules/launcher/Launcher.qml`, `Search.js`,
`tests/launcher-ui.py`, `tests/tst_search.qml` и этот отчёт. ScreenshotState,
скрипты захвата, FocusGrab/Escape-guard, shell IPC, Sidebar, Quick Settings,
ThemeManager и Lua-бинды проверены по исходникам и не изменены.

Проверки: Qt6 qmllint exit 0 (известное предупреждение метаданных screen.width),
QtTest 12/12; Launcher Qt UI — сетка, сохранение/перезапуск статистики, fallback,
действия мышью/клавиатурой, Dark/Light/Auto, оба стиля иконок, контраст ≥4.5:1,
короткий экран, RU/EN, Enter/стрелки/Tab/Escape, безопасный настоящий desktop Exec.
Пройдены runtime-menus, screenshot-escape/runtime, popup-placement, binds (95),
super-tap и deployment/rollback в изолированном HOME. `git diff --check` прошёл.
Логи и реальные offscreen-снимки с тестовыми иконками: `.cache/rc5-results/`.
Аппаратные latency/RSS/ватты не измерялись.

Установка владельцем после просмотра плана:

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh
./scripts/deploy.sh --apply
```

Откат: `./scripts/rollback.sh`, затем `./scripts/rollback.sh --apply`.
Нативный plugin не менялся и не требует пересборки поверх RC4.
На T480 проверить одиночный Super, Alt+Shift/RU/EN, длинные названия, оба стиля
иконок, настоящие действия, outside click, Super+Shift+S/cancel/repeat и Escape.
Статистика учитывает запуски через Launcher, а не все запуски в системе;
редактор закреплённых приложений не добавлялся. Stable не объявляется.
