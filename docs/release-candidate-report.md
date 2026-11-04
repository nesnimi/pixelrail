# PixelRail v3.0 — отчёт кандидата (UI v2.7)

**Подготовлен для ручной приёмки, не Stable.** Git commit/tag/push и deploy в реальный
HOME не выполнялись. Исходное дерево содержало незакоммиченный v2.6; эти изменения
сохранены. Пользовательский brightnessctl fix без `-n 1` сохранён и защищён тестом.

## Выполнено: v2.7

Sidebar сверху строго **Power → Wi-Fi → Battery%**. Только процент/«—», без часов,
звука, колокольчика, профиля и EN/RU. Ширина rail 54, окно/exclusive zone 66 px,
положение и нижний блок сохранены: workspace 1–5, приложения текущего workspace,
P последним у нижнего края. Системные функции перенесены, не удалены.

Quick Settings: заголовок и вкладки; Wi-Fi/Bluetooth 2 колонки; живые яркость/звук
и Mute; EN/RU и графический Battery/Performance; батарея/HH:mm; условный MPRIS;
«Питание и выход». Высота/resize/handle/scroll/placement сохранены. Notifications
остаётся отдельным режимом того же окна, с историей, действиями, DND и очисткой.
Clipboard upper close и Control Center × удалены, Escape/Back/outside grab сохранены.

EN/RU читает действительный active_keymap/main из Hyprland. activelayout/focus и
config reload вызывают coalesced запрос; после клика switchxkblayout выполняется
readback. Main keyboard приоритетен перед старым event hint; unknown — «—», не EN.
Alt+Shift и us,ru не менялись. Native event/socket fixture прошёл, реальные USB
клавиатуры/физический Alt+Shift остаются ручной проверкой.

Bluetooth: BlueZ установлен, service inactive/disabled, org.bluez без владельца;
hci0 обнаружен, btusb, USB 8087:0029, rfkill unblocked. Это **не отсутствие адаптера**.
UI теперь различает службу, адаптер, block, enabled/disabled и unknown.
Службы/rfkill/драйверы не изменены, pairing не проверен. Ручные команды только
после решения владельца: [bluetooth.md](bluetooth.md).

## Подготовка v3.0 и реальные исправления надёжности

- Единственный автозапуск pixelrail-start → serialized lifecycle/registry/IPC.
  Повторный запуск и старт разных релизов не дублируют управляемый qs.
- Native plugin: пассивные logind resume и BlueZ ownership events. Resume/hotplug
  закрывает transient UI/OSD и обновляет brightness/theme, не очищая историю.
- Atomic replace вместо прямой записи profile и deployment manifests.
- Missing native plugin блокирует apply до изменения ссылок/процессов/backup.
- Подтверждено восстановление после аварии **тестового** qs, invalid QML,
  missing plugin и ошибки середины установки. Чужой fixture qs не затронут.
- Архитектура NotificationServer/ownership, ClipHist watcher, swaybg и IPC сохранена.
  PipeWire/WirePlumber в autostart не добавлены. Бесконечного рестарта нет.
- Cleanup: подтверждённые compatibility wrappers и Waybar clock сохранены;
  удалений пользовательских данных/backup/истории/обоев нет.

Новых доказанных багов дублирования autostart не найдено: существующая защита
подтвердилась тестами. Исправления не выдаются за устранение несуществующей гонки.

## Проверки

32 сценария полного Python-прогона — PASS (каждый timeout 180 сек), включая:
settings/keyboard/session events/release fault injection; live sliders/OSD/native;
Control UI/runtime/IPC; Sidebar; menu/Launcher routing; Notifications/DND/ownership;
Material You; placement; Clipboard/Wallpaper; Power Audit; lifecycle; deploy/rollback;
performance и benchmark. Отдельно autostart PASS, Lua 95 unique binds и Super-tap
PASS, QtTest 6 PASS, Qt6 qmllint exit 0 (известные static warnings dynamic metadata),
Python/Bash/Lua syntax и git diff --check PASS.

Изоляция: private HOME/XDG, private buses, unmapped/offscreen окна, fake hardware;
read-only системная диагностика допустима. Настоящие suspend/reboot/logout, service
changes, brightness/audio writes, EPP/governor/GPU PM и live deploy не выполнялись.
Missing Hyprland socket в некоторых fixtures отмечен предупреждением; отдельный
keyboard/sidebar socket fixture действительно проверяет команды и события.

Артефакты полного прогона: `.cache/v27-tests/results.json`, логи в той же папке.
Benchmark: `.cache/benchmark-v30-rc.json`; 50 Launcher, 50 A/N, 30 Clipboard,
20 Wallpaper, 200 notifications, Dark/Light, detail pages, 60 сек soak / 21 цикл.
Один qs, история ≤60/live ≤20, ноль лишних одинаковых palette assignments.

## Производительность и ограничения

IPC median 29.77 → 28.65 ms; A→N 58.24 → 57.89; N→A 58.38 → 57.98 ms.
Это state readiness, **не представленная картинка**. Warm RSS 165.24 → 167.59 MiB,
settled до soak 163.81 → 159.29 MiB. Soak: 164.85 → 173.25 → 171.41 MiB;
добавочная нагрузка/кэши, не доказательство утечки или её отсутствия.
Повтор benchmark: A→N/N→A 58.03/57.97 ms, Wallpaper p95 244.41 ms
(первый повышенный p95 284.31 ms не воспроизвёлся); baseline/warm/settled RSS
146.29/167.73/163.43 MiB. Детали в performance.md.
CPU tick=0 на коротких idle samples не доказывает нулевую нагрузку.
Реальные 182–186 MiB / 5.39 W пользователя не сравниваются с fixture; отсутствие
энергетической регрессии не заявляется. [Измерения](performance.md).

Риски: native plugin привязан к установленному Qt/qs 0.3.2; после Qt upgrade нужна
пересборка. Реальные Bluetooth radio/agent/pairing, аудиоустройства и resume ещё
требуют приёмки. Короткие тесты не заменяют длительную работу ноутбука.

## Безопасная установка и rollback (выполняет владелец)

```bash
cd ~/Projects/pixelrail
./scripts/build-native.sh
git diff --check
./scripts/deploy.sh                 # dry-run
./scripts/deploy.sh --apply         # явное применение после review
```

Режимы не переключаются при deploy. По желанию, после успешной установки:

```bash
~/.local/bin/pixelrail-panel mode sidebar
~/.local/bin/pixelrail-notifications mode pixelrail
~/.local/bin/pixelrail-panel status
~/.local/bin/pixelrail-notifications status
```

```bash
cd ~/Projects/pixelrail
./scripts/rollback.sh
./scripts/rollback.sh --apply
# Дополнительные fallback, без удаления пакетов:
~/.local/bin/pixelrail-notifications mode swaync
~/.local/bin/pixelrail-panel mode waybar
```

## Ручная приёмка T480

- [ ] 1366×768: ровно три верхних элемента, большой gap, workspace/P внизу, app scroll.
- [ ] Chrome на 1/Kitty на 3, два окна одного приложения, перенос/закрытие/активация.
- [ ] Super без конфликтов Q/D; A/N туда-обратно, повтор закрывает, вкладки мышью.
- [ ] Escape/outside click во всех страницах; Launcher снизу, popup placement сохранён.
- [ ] EN/RU/Alt+Shift, смена фокуса/активной USB клавиатуры, кириллица в поиске.
- [ ] Live drag, короткие движения, release вне, wheel/key, внешние изменения звука/яркости.
- [ ] Fn/XF86 и mute, реальный OSD/readback, скрытие/неперехват фокуса, нет OSD поверх CC.
- [ ] Bluetooth: после осознанного ручного запуска службы — toggle/discovery/pair/connect.
- [ ] Notifications actions/history/DND/clear, возврат к SwayNC и Waybar.
- [ ] Батареи BAT0/BAT1, AC/Battery, часы, профиль эффектов без configerrors.
- [ ] Dark/Light/Auto/accent, Clipboard image Ctrl+V, обои сохраняются после запуска.
- [ ] Сон/крышка/долгий resume и monitor/HiDPI hotplug проверяет пользователь вручную.
- [ ] Высота CC сохраняется после ручного перезапуска; один qs; backup/rollback.
- [ ] Сопоставимый длительный idle/RSS/CPU/power audit с теми же приложениями.

## Готовность

Кандидат готов к ручной приёмке; **v3.0 Stable не объявлен**.
Предлагаемое имя первого тега после решения пользователя: `v3.0.0-rc.1`.
Stable `v3.0.0` — только после аппаратной приёмки. Ни один тег не создан.

## Журнал этапов

1. Git/AGENTS/исходники проверены, исходные изменения сохранены.
2–5. Minimal Sidebar → Quick Settings/EN-RU → Bluetooth → удаление close.
6. Целевые v2.7 проверки пройдены.
7–9. Аудит запуска, fault tests, native resume/BlueZ tests, safe hotplug/placement.
10. Аудит cleanup без рискованных удалений.
11. Dry-run/apply/failure/rollback в тестовом HOME.
12–13. Документация и полный регрессионный прогон.
14. Этот отчёт, без deploy/commit/tag/push.

## Изменённые файлы рабочего дерева

Список включает сохранённый незакоммиченный v2.6, а не только новый патч v2.7.
Native `.so` — локальный игнорируемый build artifact; в Git не добавлялся.

- `CHANGELOG.md`
- `README.md`
- `docs/architecture.md`
- `docs/bluetooth.md`
- `docs/control-center.md`
- `docs/installation.md`
- `docs/osd.md`
- `docs/performance.md`
- `docs/popup-placement.md`
- `docs/recovery.md`
- `docs/release-candidate-report.md`
- `docs/shortcuts.md`
- `docs/sidebar.md`
- `docs/troubleshooting.md`
- `hypr/pixelrail-end4-keys.lua`
- `quickshell/components/ClipboardView.qml`
- `quickshell/modules/control/BluetoothLogic.js`
- `quickshell/modules/control/ControlCenter.qml`
- `quickshell/modules/control/KeyboardState.qml`
- `quickshell/modules/control/LiveSlider.qml`
- `quickshell/modules/control/qmldir`
- `quickshell/modules/sidebar/Sidebar.qml`
- `quickshell/modules/sidebar/SidebarServices.qml`
- `quickshell/modules/system/OsdController.qml`
- `quickshell/modules/system/SessionState.qml`
- `quickshell/modules/system/SystemControls.qml`
- `quickshell/modules/system/SystemOsd.qml`
- `quickshell/modules/system/SystemState.qml`
- `quickshell/modules/system/qmldir`
- `quickshell/native/PixelRail/DBusLease/backlightwatch.hpp`
- `quickshell/native/PixelRail/DBusLease/lease.cpp`
- `quickshell/shell.qml`
- `scripts/build-native.sh`
- `scripts/deployment.py`
- `scripts/desktop.py`
- `scripts/pixelrail-desktop`
- `scripts/pixelrail-profile`
- `scripts/pixelrail-system`
- `tests/autostart.py`
- `tests/benchmark-runtime.py`
- `tests/binds.lua`
- `tests/control-runtime.py`
- `tests/control-ui.py`
- `tests/deployment.py`
- `tests/fixtures/sidebar_hyprland.py`
- `tests/keyboard-runtime.py`
- `tests/lifecycle-runtime.py`
- `tests/release-reliability.py`
- `tests/runtime-menus.py`
- `tests/session-events.py`
- `tests/settings.py`
- `tests/sidebar-runtime.py`
- `tests/smoke-quickshell.py`
- `tests/system-native.py`
- `tests/system-runtime.py`
- `tests/system-ui.py`
- `tests/system.py`
- `tests/tst_settings.qml`
