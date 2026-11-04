# PixelRail v2.3 — размещение окон и навигация

Все временные окна используют существующий процесс Quickshell, overlay layer
и ExclusionMode.Ignore: они не резервируют новое место для tiled-окон и не
создают полноэкранный слой, блокирующий мышь. Их размеры и внутренний дизайн
сохранены; ширина/высота уменьшаются только при нехватке пространства.

| Окно | Сочетание / маршрут | Привязка |
| --- | --- | --- |
| Quick Settings | Super+A | сверху слева |
| Notifications | Super+N, колокольчик Sidebar | сверху слева |
| Quick Actions | Super+G, Super+I, `controls` | сверху слева |
| Power | Ctrl+Alt+Delete (`session` → `power`), кнопки питания | сверху слева |
| Media | Super+M, `media` | сверху слева |
| Keybinds | Super+/, Super+F1, `keys` | сверху слева |
| Wallpaper Picker | Super+Ctrl+T, `wallpaper` | сверху слева, галерея до 1000×620 |
| Pixel Launcher | одиночный Super, Super+Space | снизу слева |
| Command | Super+R, `command` | снизу слева |
| Clipboard | Super+V, `clipboard` | снизу слева |
| Window Switcher | Super+Tab, `windows` | снизу слева |
| Emoji | Super+Period, `emoji` | снизу слева |
| Notification toast | NotificationServer | сверху слева |
| System OSD v2.6 | физические brightness/volume keys | слева по центру, input transparent |

Правила `quickshell/components/PopupPlacement.js` задают группу меню и ограничивают
геометрию в logical px. Отступ сверху/снизу — 12 px; слева — существующая ширина
занятой панели + 12 px. Для Sidebar это 78 px от края экрана (66 px layer surface,
54 px видимая панель); для Waybar используется уже работающий IPC inset.
Если Sidebar находится на другом мониторе, Launcher/MenuPanel используют 12 px.
На маленьком экране сохраняется правый отступ 12 px, окно сжимается по доступной
ширине. При 1366×768 обычные размеры, включая галерею, остаются прежними.

Launcher и MenuPanel выбирают focused Hyprland monitor при открытии; если его
нет — первый доступный экран. Удалённый экран не удерживается: binding возвращает
окно на доступный output. Control Center/toasts сохраняют существующий выбор
монитора Sidebar с fallback на первый экран. Геометрия реактивна к разрешению/scale.
Вызов нового меню скрывает несовместимую панель; при переходе из Launcher ожидается
его существующее завершение fade. MenuPanel сразу скрывается при замене другим
типом панели, сохраняя штатный fade при обычном закрытии. Focus grab разрешает
поверхность Sidebar и закрывает меню по клику вне; мышь вне окна не блокируется.
Toast скрыт, пока открыты Launcher, Control Center или MenuPanel; история сохраняется.

## Причина задержки N → A

Старый `pixelrail-control` безусловно вызывал `pixelrail-shell` перед control IPC.
Lifecycle даже для готового процесса выполнял discovery/readiness, согласование
режима панели и NotificationServer. Super+N этого пути не проходил; вкладки мышью
работают напрямую в QML. Это объясняет асимметрию без пересоздания Control Center.

Теперь `control.py` сначала находит текущий принадлежащий PixelRail процесс и
отправляет IPC. Только если процесса нет, запускается штатный pixelrail-shell.
Ошибочный IPC не вызывает второй экземпляр. Lifecycle, ownership и startup/recovery
не переписаны; периодический polling не добавлен.

Измерения в изолированном HOME, реальный qs и native NotificationServer на отдельной
D-Bus-шине (это время CLI до возврата/проверки состояния, не photon latency):

| Путь | Медиана, мс |
| --- | ---: |
| исходный N→A, первое измерение | 815.72 |
| старый N→A, повтор старого wrapper с одинаковым capture измерением | 771.82 |
| исправленный N→A, 5 повторов | 136.57 |
| исправленный A→N, 5 повторов | 136.21 |
| lifecycle отдельно, 3 повтора | 632.85 |
| control.py напрямую, 3 повтора | 131.89 |
| control IPC отдельно, 3 повтора | 30.19 |

Первое измерение использовало subprocess.wait с timeout; сопоставимый повтор
старого wrapper использует capture_output, как оба итоговых направления. A→N
в первом измерении составлял 138.64 мс. Микрозадержки и интервалы планировщика
влияют на итог, поэтому тест не навязывает аппаратно-зависимый порог времени.

## Проверка

```bash
python3 tests/control-routing.py
python3 tests/control-runtime.py
python3 tests/popup-placement.py
python3 tests/runtime-menus.py
python3 tests/control-ui.py
lua tests/binds.lua
lua tests/super-tap.lua
```

Control runtime сохраняет сырые измерения и медианы в `.cache/navigation-latest.json`.
Старый wrapper воспроизводится только внутри тестового HOME. На активном сеансе
тест не меняет настройки/режимы устройств. Popup placement проверяет сами QML-правила
для 1366×768, больших/узких экранов и нескольких inset; runtime-menus проверяет
настоящие anchors/margins/implicit size всех девяти режимов. Control routing
проверяет fast path без lifecycle и сохранённый холодный запуск.

Вручную на T480: настоящие Super+A/N по 10 раз, повтор для закрытия, Escape,
вкладки мышью; все строки таблицы в Sidebar/Waybar, HiDPI и hotplug, клики вне
и через Sidebar, отсутствие кратковременных наложений и правильный фокус.
Автотесты используют unmapped/offscreen окна и не доказывают визуальное время
отрисовки либо поведение физических клавиш/тачпада в compositor.

Установка и откат выполняются пользователем:

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh
./scripts/deploy.sh --apply
# При необходимости:
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

System OSD v2.6 использует тот же left inset, ширину 280 logical px и высоту 72;
отсутствие вертикальных anchors центрирует layer surface по высоте. В CC/Launcher/
MenuPanel он подавлен, focus=None, input Region пустая. См. [osd.md](osd.md).
