# GoogleDot: подготовка системной интеграции

Источник: https://github.com/ful1e5/Google_Cursor . GPL-3.0, копия лицензии рядом
в GoogleDot-LICENSE.txt. Официальные варианты GoogleDot-Black / GoogleDot-White;
размеры XCursor включают 24/28/32. Black/White подготовлены в repository cache,
но не устанавливались; непроверенные Hyprcursor-переупаковки не распространяются.

```bash
./scripts/pixelrail-cursor status
./scripts/pixelrail-cursor prepare --theme GoogleDot-Black --size 24
```

Это **preview**, не применение: файлы только в `.cache/cursor-preview` репозитория.
При отсутствии установленной темы вывод installed=false. Готовые файлы и проверка
описаны ниже. На новой машине cache можно восстановить prepare-cursor-assets.py;
установка в пользовательский icons directory остаётся ручной.

После решения владельца вручную включите подготовленный cursor.lua из постоянного
пользовательского пути в Hyprland Lua. Не ссылайтесь на временный release после
rollback. GTK settings фрагмент нужно объединить с существующим settings.ini,
а не перезаписать весь файл. XCURSOR_THEME/SIZE нужны также Qt/GTK/XWayland
приложениям при старте. `hyprctl setcursor GoogleDot-Black 24` — отдельное ручное
runtime-применение, не выполняемое installer. Новым приложениям/сеансу могут
потребоваться обновлённые env; hot reload не гарантирует обновление всех клиентов.

XCursor — bitmap theme с несколькими размерами; Hyprcursor — другой формат с
manifest.hl. Upstream GoogleDot не следует объявлять Hyprcursor темой лишь по имени.
Preview выключает использование Hyprcursor, чтобы использовать настоящий XCursor.
Это локальная опция cursor, не изменение драйверов. Для масштабирования выберите
24/28/32; проверьте разные DPI мониторов. GTK может предпочитать свои settings,
Qt — env/платформенную интеграцию. Программы иногда имеют собственные cursors.

Проверьте arrow, text, pointer, ew/ns resize, move/grabbing, wait/progress,
not-allowed на Hyprland, Qt, GTK и XWayland. Для отката восстановите предыдущие
cursor env/config из своей копии и перезапустите затронутые клиенты вручную.

Settings показывает инструкцию, но **не декоративный переключатель**: применение
системного курсора оставлено ручным из-за различий GTK/Qt/Hyprcursor и отсутствия
установленного GoogleDot. Курсор не рисуется QML-изображением.

## Дополнение: реальные ресурсы подготовлены

В рамках дополнения получены официальные Linux архивы **v2.0.0** только Black и
White (около 9.4 MB загрузки суммарно; остальные цвета/Windows/repository не скачивались).
Тезис выше «бинарники не скачивались» относится к первоначальному RC1 и более не актуален.
Теперь `.cache/cursor-assets/GoogleDot-Black` и `GoogleDot-White` — настоящие XCursor
темы: 39 файлов +106 алиасов каждая, только размеры 24/28/32. Всего около 3 MB.
Исходные пиксели, hotspots, задержки и кадры выбранных размеров сохранены.

```bash
python scripts/prepare-cursor-assets.py --download  # один раз; только repository cache
python scripts/prepare-cursor-assets.py           # повторно офлайн из проверенных архивов
./scripts/pixelrail-cursor status
./scripts/pixelrail-cursor prepare --theme GoogleDot-White --size 28
python tests/graphic-resources.py
```

Native libXcursor проверила чтение файлов и lookup по имени темы для default,
text, pointer, ew/ns-resize, move, wait, progress, not-allowed во всех трёх размерах.
Это подтверждает формат/алиасы, но не физическую отрисовку в каждой программе.
Установка и применение по-прежнему **не выполнялись**. Новые пакеты не нужны для
подготовки; используется Python stdlib. Полные цвета/размеры не распаковываются.

Ручная установка владельцем после проверки (эти команды Codex не выполнял):

```bash
mkdir -p "$HOME/.local/share/icons"
test ! -e "$HOME/.local/share/icons/GoogleDot-Black" && cp -a .cache/cursor-assets/GoogleDot-Black "$HOME/.local/share/icons/"
test ! -e "$HOME/.local/share/icons/GoogleDot-White" && cp -a .cache/cursor-assets/GoogleDot-White "$HOME/.local/share/icons/"
```

Не перезаписывайте существующую тему. Затем вручную объедините preview Lua/env/GTK
с пользовательскими файлами с backup; не заменяйте settings.ini целиком.
Qt/GTK/XWayland приложения могут потребовать нового запуска с XCURSOR_THEME/SIZE.
Для runtime-теста владельцем: `hyprctl setcursor GoogleDot-Black 24`.

## Сохранение текущей темы и откат

Команды ниже выполняет владелец. Сначала сверить XCURSOR_THEME/SIZE с текущей
конфигурацией: после прежнего ручного `setcursor` env может быть устаревшим.
Если текущая пара неизвестна, её нужно определить до применения, а не угадывать.

```bash
cd ~/Projects/pixelrail
: "${XCURSOR_THEME:?Сначала определите текущую тему курсора}"
: "${XCURSOR_SIZE:?Сначала определите текущий размер курсора}"
pixelrail_cursor_backup="$HOME/.local/state/pixelrail/cursor-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$pixelrail_cursor_backup"
XCURSOR_THEME="$XCURSOR_THEME" XCURSOR_SIZE="$XCURSOR_SIZE" python3 - "$pixelrail_cursor_backup" <<'PY'
import json, os, shutil, sys
from pathlib import Path
backup=Path(sys.argv[1]); config=Path.home()/'.config'
(backup/'current.json').write_text(json.dumps({'theme':os.environ['XCURSOR_THEME'],'size':os.environ['XCURSOR_SIZE']}))
for name in ['hypr/hyprland.lua','gtk-3.0/settings.ini','gtk-4.0/settings.ini']:
    source=config/name
    if source.is_file():
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
print('Копия:',backup)
PY
```

Затем установка **только отсутствующих** тем командами выше и opt-in preview:

```bash
./scripts/pixelrail-cursor prepare --theme GoogleDot-Black --size 24
hyprctl setcursor GoogleDot-Black 24
```

Для постоянного применения вручную объединить созданные cursor.lua/environment.txt/
gtk-settings.ini с существующими файлами, сохраняя остальные параметры. Qt/GTK/XWayland
могут требовать новые процессы/следующий сеанс с XCURSOR_THEME/SIZE. Нельзя обещать,
что setcursor сменит указатель каждого уже работающего клиента.

Runtime-откат к сохранённой паре (pixelrail_cursor_backup — из предыдущего терминала):

```bash
python3 - "$pixelrail_cursor_backup/current.json" <<'PY'
import json, subprocess, sys
saved=json.load(open(sys.argv[1]))
subprocess.run(['hyprctl','setcursor',saved['theme'],saved['size']],check=True)
PY
```

Если изменялись постоянные настройки, сначала сравнить их с копиями в backup,
затем восстановить только изменённые cursor-строки (либо проверенные целые файлы).
Резервные копии не удалять. PixelRail не выполняет эти команды и не требует
GoogleDot для запуска. Поддерживаются оба варианта Black/White и 24/28/32 px.
Для отката верните прежние env/GTK/cursor config и выбранную тему; ничего удалять
не требуется. Native Hyprcursor-конверсия не заявляется: preview использует XCursor.

GPL/source: staged themes содержат лицензию и upstream source tag. Cache не включён
в deploy и не распространяется как binary release. При перераспространении нужно
предоставить corresponding source/build inputs, а не только ссылку.

GTK3: merge fragment в `$XDG_CONFIG_HOME/gtk-3.0/settings.ini`; GTK4 — в
`$XDG_CONFIG_HOME/gtk-4.0/settings.ini`. Не уничтожайте остальные Settings keys.
Если desktop portal/GSettings имеет приоритет, владелец сначала читает
`gsettings get org.gnome.desktop.interface cursor-theme` и `cursor-size`, сохраняет
прежние значения и только затем сам решает применять их через `gsettings set`.
PixelRail не делает это автоматически. Для Qt/QtWayland/XWayland подготовлен
XCURSOR env; действующие клиенты могут сохранить прежние значения до перезапуска.
При native cursor-shape protocol тема выбирается композитором. На смешанных DPI
нужно проверить и compositor, и GTK/Qt, а не только окно PixelRail.
