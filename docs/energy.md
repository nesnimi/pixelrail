# PixelRail v2.4 — Energy Optimization, этап 1

## Что изменилось и что осталось отключено

`pixelrail-power-audit` — конечная read-only диагностика, без демона, polling в
оболочке, перезапуска qs, sudo или изменения оборудования. Нужны уже используемые
Python 3 и systemctl (только запрос состояния). Нет nvidia-smi, probing PCI config,
пакетных установок или новых служб. Отсутствие systemd/bus/прав явно отражается
как неизвестное/ошибка; оно не считается доказательством отсутствия конфликтов.

Существующий `pixelrail-profile` не изменён: Battery/Performance по-прежнему
сохраняет графический профиль и перезагружает Hyprland. Связи с EPP пока нет.
Sidebar, Launcher, Control Center, NotificationServer, Material You и IPC не
получили новых timers/processes. EPP, governor, Turbo Boost и NVIDIA не меняются.

Подготовлен отдельный **неустановленный** кандидат брокера
`extras/power/epp_helper.py`. Обычный deploy копирует scripts/quickshell/hypr;
extras не доставляется в релиз и не устанавливается с привилегиями. Нет PolicyKit,
udev, sudoers, setuid или прав записи sysfs для оболочки. Даже запуск кандидата
от root требует доверенного root-owned пути к самому helper; apply дополнительно
требует отдельный root-owned `/etc/pixelrail/epp-enabled` со значением `enabled`.
Создание этого файла и установка helper в данном этапе не выполняются.

## Аудит

```bash
cd ~/Projects/pixelrail
./scripts/pixelrail-power-audit                 # два снимка с интервалом 1 с
./scripts/pixelrail-power-audit --samples 1     # только состояние, без CPU/delta
./scripts/pixelrail-power-audit --json
./scripts/pixelrail-power-audit --samples 13 --interval 10 --jsonl
```

После пользовательского deploy команда доступна как `pixelrail-power-audit`.
Инструмент сам не записывает файлы. JSON содержит полные снимки, JSONL — одну
сравнимую строку на измерение. Число снимков конечно; default — 2, непрерывного
опроса нет. Реальный интервал и время UTC сохраняются, длительность запросов
учитывается, а не выдаётся за ровно заданный sleep. `null` означает недоступность,
а не нулевую нагрузку/мощность. В JSONL сохраняются также ошибки чтения, список
CPU EPP, состояние менеджеров, NVIDIA и изменения runtime-счётчиков.

- Источник AC/Battery определяется по online внешних power_supply; при отсутствии
  таких данных допускается Battery по Discharging, иначе Unknown. Батареи не
  считаются внешними источниками. BAT0 не требуется, BAT1 отображается отдельно.
- Процент BAT1 — capacity либо energy_now/energy_full при отсутствии capacity.
- Ватты выводятся **только для status=Discharging**, с повторной проверкой status
  после чтения. power_now (µW) переводится в W. Если его нет, возможен явно
  помеченный fallback current_now (µA) × voltage_now (µV); иначе мощность неизвестна.
  Charging/Full/Not charging не дают «разряд», даже если power_now ненулевой.
- Все найденные policy перечисляются численно: driver, governor, EPP и доступные
  значения. Отсутствующий атрибут не заменяется предполагаемым значением.
- NVIDIA выбирается по vendor 0x10de. Читаются driver symlink и power/control,
  runtime_status, runtime_active_time/runtime_suspended_time (ms). Нет записи и
  опроса GPU через драйвер. Уменьшение/сброс счётчика даёт неизвестный delta.
- CPU qs измеряется по разнице utime+stime / CLOCK_TICKS / прошедшие секунды.
  100% — одно логическое CPU, не весь восьмипоточный процессор. Starttime защищает
  сравнение от PID reuse. Первый снимок не имеет CPU/delta. RSS — resident pages,
  не PSS; сумма нескольких процессов включает их разделяемые страницы повторно.
  Показываются qs текущего UID, а не только активного дисплея.
- Проверяются systemd states TLP, tuned, power-profiles-daemon, auto-cpufreq и
  доступные cmdline этих процессов, включая процессы другого UID. Active/exited
  TLP тоже может означать применённую политику. Неизвестные сторонние программы
  инструмент не обещает обнаружить; прямые изменения BIOS/скриптов не отслеживаются.

При разработке read-only снимок рабочего сеанса показал BAT1=21%, Discharging,
около 12.26 W; один qs=191.68 MiB, все policy0–7 intel_pstate/powersave с
balance_performance; nouveau/auto/suspended. На коротком интервале ~0.26 с qs
имел 0 ticks, NVIDIA +0 ms active и +238 ms suspended; менеджеры inactive/not-found.
**Это не замер простоя и не доказательство экономии:** Chrome/Codex и другая
нагрузка не контролировались. Короткий CPU=0 не означает постоянный нулевой CPU.

## Измеримый эксперимент

1. Отдельно измерять простой и рабочую нагрузку. Зафиксировать яркость, монитор,
   Wi-Fi/Bluetooth, открытые приложения, состояние вкладок Chrome и режим графики.
   Дать системе стабилизироваться после отключения AC; не сравнивать зарядку с
   разрядом. Не запускать benchmarks/QML smoke одновременно с измерением простоя.
2. Снять несколько конечных серий по 2–5 минут; пометить условия рядом с данными.
3. Только после отдельного разрешения включить EPP и повторить серии в тех же
   условиях. Сравнивать медиану/разброс W только Battery+Discharging, CPU qs,
   долю suspended NVIDIA, отзывчивость переключений и анимаций.
4. Не обещать снижение W заранее. RSS ~191 MiB не является непосредственным
   измерением мощности. Исходные 15–16 W при Chrome/Codex нельзя называть idle.

```bash
mkdir -p .cache/power
./scripts/pixelrail-power-audit --samples 13 --interval 10 --jsonl \
  > .cache/power/baseline-workload.jsonl
# Повторить в тех же условиях отдельной серией, меняя имя файла.
python3 - <<'PY'
import json, statistics
from pathlib import Path
for path in sorted(Path('.cache/power').glob('*.jsonl')):
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    watts=[r['BAT1_discharge_w'] for r in rows if r['source']=='Battery'
           and r['BAT1_status']=='Discharging' and r['BAT1_discharge_w'] is not None]
    print(path.name, 'n=',len(watts), 'median W=',statistics.median(watts) if watts else None)
PY
```

## Подготовленный механизм EPP

Соответствие: Battery → `balance_power`, Performance → `balance_performance`.
Оба сохраняют governor `powersave`; это не установка governor `performance`.
Intel_pstate powersave/HWP допускает EPP, а performance/HWP отвергает часть
настроек EPP. Источник: [документация ядра intel_pstate](https://www.kernel.org/doc/html/latest/admin-guide/pm/intel_pstate.html).
Runtime PM: [документация ядра PCI PM](https://www.kernel.org/doc/html/latest/power/pci.html).

Сейчас разрешена только подготовка/просмотр плана:

```bash
python3 extras/power/epp_helper.py plan battery
python3 extras/power/epp_helper.py plan performance
python3 tests/power.py
```

Plan не требует root и ничего не пишет. Предложенный broker:

- Изолированный Python (`#!/usr/bin/python3 -I`), stdlib, фиксированные CLI операции
  plan/apply battery/apply performance/restore/recover. Нет параметров пути,
  произвольного значения EPP или команды shell; XDG/env не определяют root пути.
- Apply/restore/recover root-only. Проверяются root ownership и отсутствие
  group/world write/symlink у пути helper, state и их родителей. Политика отказа
  закрытая; из пользовательского Git/release привилегированные операции запрещены.
- Запись только в `policy[0-9]+/energy_performance_preference` под фиксированным
  `/sys/devices/system/cpu/cpufreq`. Проверяются intel_pstate, powersave, текущий
  EPP, поддержка цели **всех** policy до первого изменения. Нет записи governor,
  частоты, boost/no_turbo, GPU или произвольного sysfs.
- Apply отказывает при активном известном менеджере или ошибке проверки менеджеров.
  Restore/recover не блокируются этим условием, чтобы можно было откатиться.
- Межпроцессный flock на root-owned `/run/pixelrail-epp/lock`. Начальные значения
  каждого policy сохраняются отдельно от release, атомарно с fsync в
  `/var/lib/pixelrail-epp/state.json` (root-only directory/file). Перед записью
  сохраняется pending-map непосредственного предыдущего состояния; после записи
  выполняется readback каждой policy. Несколько sysfs записей не атомарны.
- При ошибке восстанавливаются значения **до этой операции**, а исходный baseline
  не перезаписывается следующим профилем. Если откат тоже не удался, pending
  остаётся, ошибка явно сообщает о частичном состоянии; новый apply запрещён.
  Recover возвращает сохранённое предыдущее состояние, restore — первый baseline.
  Крах процесса также оставляет durable pending для ручного recover.
- Смена boot_id, топологии policy или поддержки значений требует ручного разбора,
  без автоматической записи старого состояния в новую конфигурацию. После reboot
  значения может сбросить ядро: автоматического повторного применения пока нет.

### План включения — только после отдельного разрешения

1. Повторно проверить доступный EPP, права, отсутствие конфликтов, baseline и
   измерения. Убедиться, что выбранные драйвер/governor не изменились.
2. Отдельно проверить код кандидата. Администратор устанавливает root-owned копию
   в фиксированный libexec путь, вне пользовательского репозитория и releases.
3. Если потребуется пользовательский вызов, согласовать ограниченный PolicyKit
   action для **этого пути** с административной аутентификацией. Backend проверяет
   allowlist операций сам. Не выдавать оболочке write-access на sysfs, sudoers
   wildcard или setuid. Если PolicyKit отсутствует — сначала согласовать зависимость.
4. Только явно включить gate, проверить одну транзакцию и restore. Пока не
   доставлены ни privileged policy, ни gate, ни автозапуск, ни вызов из Sidebar.
5. В следующем согласованном патче подключить opt-in к существующему визуальному
   профилю. При отказе EPP графика остаётся рабочей, системная ошибка показывается
   отдельно; нельзя утверждать, что CPU-профиль применён, если запись не прошла.
6. Для отключения сначала recover при pending/restore baseline, проверить все
   policy, затем убрать gate и optional policy/helper. Не удалять state до проверки.

Команды привилегированной установки/активации намеренно не предлагаются на этапе 1.
Ни sudo, ни pkexec, ни apply/restore на настоящем sysfs при разработке не запускались.

## Доставка диагностики и откат

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh                 # только просмотр
./scripts/deploy.sh --apply         # выполнить пользователю
pixelrail-power-audit
# Откат пользовательского релиза:
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Это доставляет только обычный read-only audit/helper-module из scripts. Extras EPP
не устанавливается, что проверено deployment-тестом. Системного EPP изменения
сейчас нет, поэтому rollback релиза не должен и не пытается менять sysfs.

Тесты в `.cache`: BAT1 без BAT0, AC/разряд, отсутствие power_now/EPP/runtime PM,
ошибки доступа, все 8 policy, CPU/PID reuse и runtime deltas, конечный JSONL,
отсутствие привилегий/gate/path override, preflight, частичный apply/rollback,
постоянный сбой с recover, сохранение baseline между профилями, stale state и
hotplug topology. Никакие тестовые записи не идут в настоящий sysfs.
