# PixelRail v3.1 RC4 — визуальная согласованность

Подготовлено в репозитории, без установки. RC4 не объявляется Stable.

## Изменения

- **Notifications:** тональные карточки с радиусом 20 px, иконки приложений 30 px,
  заголовок 14 px, текст 13 px, время 11 px, отступы 12/8 px. Material-кнопка
  удаления, ограниченные шириной карточки действия. Длинный текст можно раскрыть
  и свернуть. DND получил понятную подпись. Пустое состояние центрируется в
  доступной области; при пустой истории кнопка очистки скрыта.
- **Clipboard:** заголовок 18 px, поиск pill высотой 48 px со значком и фокусом,
  карточки с иконками текста/ссылки/изображения, отметкой выбора и превью.
  Сохранены размеры карточек 84/184 px, окно 640×620 px и нижняя подсказка Escape.
  Метаданные изображений показывают размеры/формат. cliphist не предоставляет
  время копирования: временные метки не выдумываются из идентификаторов записей.
- **Wallpaper Picker:** поиск pill, тональный hover, заметный контур primary
  толщиной 2 px и отметка выбранного изображения, читаемые подписи и pill-кнопка
  применения. Сетка 152 px, окно 1000×620 px, bounded-превью и существующие
  filter chips сохранены. Контур обозначает текущий выбор для предпросмотра;
  смена обоев происходит только после применения.

Все цвета поступают из существующей Material You Palette; используются Tokens,
PixelIcon, PixelAppIcon и шрифт RC3. Короткая pressed-анимация использует Tokens.hover
(120 мс, 0 при отключённых анимациях). Новых библиотек, polling, процессов обработки
изображений или глобальных singleton нет. Прокрутка колёсиком/клавиатурой сохранена;
стандартные полосы Clipboard/галереи скрыты.

Sidebar, Launcher, Settings и Quick Settings не менялись. В ControlCenter изменено
только содержимое Notifications. Worker-логика Clipboard/обоев, ScreenshotState,
slurp DEVNULL, Escape/FocusGrab, IPC, NotificationServer, бинды и lifecycle сохранены.
GoogleDot Black/White, pixelrail-cursor и [инструкция владельцу](cursor.md) на месте;
системная установка курсора не выполнялась.

## Снимки

Это настоящие QML grabToImage в изолированном HOME, Qt software/offscreen,
с тестовыми уведомлениями и данными; не фотографии рабочего T480.
Для image-превью использован приложенный владельцем pixelrail_1.png.

- [Notifications Dark](screenshots/rc4/notifications-dark.png), окно 400×384.
- [Notifications Empty](screenshots/rc4/notifications-empty.png), окно 400×384.
- [Clipboard Dark](screenshots/rc4/clipboard-dark.png), окно 640×620.
- [Wallpaper Dark](screenshots/rc4/wallpaper-dark.png), окно 1000×620.

Получение снимков: `PIXELRAIL_SCREENSHOT_DIR="$PWD/.cache/rc4-captures" python tests/control-ui.py`
и аналогично `python tests/qt-ui.py` после создания каталога. Снимки не генерируются
нейросетью и не читают настоящую историю буфера или пользовательские обои.

## Проверки

- Qt6 qmllint: exit 0 для четырёх изменённых UI-файлов и нового fixture.
  Сохранились три известных предупреждения метаданных PanelWindow/margins;
  runtime не обнаружил ошибок QML. В offscreen Control UI ожидаемо нет Hyprland socket.
- QtTest: 10 passed, 0 failed. `qt-ui.py`: пять fixture, включая новый Rc4VisualTests,
  реальные mouse/key events, поиск, фильтры, навигация, Escape, отмена и применение.
  Проверены Dark/Light/Auto, контраст текста ≥4.5:1 и нажатой кнопки применения,
  символы, контур выбора, пустые состояния и отключение анимаций.
- `control-ui.py`: DND, время, отдельное удаление, очистка/скрытие кнопки,
  раскрытие длинного уведомления и действие с клавиатуры; вкладки, прокрутка,
  Escape/Screenshot Mode, resize и сохранение настроек после перезапуска.
- Один компактный регрессионный прогон: notifications, wallpapers,
  clipboard-wayland (Unicode/многострочный текст, PNG/JPEG/WebP, исходные bytes/MIME),
  material-you + material-you-runtime, popup-placement, graphic-resources,
  screenshot-backend/escape/runtime, runtime-menus, control-runtime,
  lifecycle-runtime, deployment, binds (95 уникальных), super-tap — все прошли.
  Тесты lifecycle/deploy/rollback используют отдельный HOME; пользовательские
  процессы не завершались. Проверены отсутствие дубликатов и сохранность настроек.
- `git diff --check`: passed. Контрольные хеши защищённых исходников совпали;
  worker/Escape-префиксы Clipboard/обоев и весь Control Center вне Notifications
  остались побайтно прежними. Логи: `.cache/rc4-results/`.

## Файлы RC4

`quickshell/modules/notifications/NotificationCards.qml`,
`quickshell/modules/control/ControlCenter.qml` (только Notifications),
`quickshell/components/ClipboardView.qml`, `quickshell/components/WallpaperView.qml`;
`tests/control-ui.py`, `tests/qt-ui.py`, `tests/gui/Rc4VisualTests.qml`;
этот отчёт и четыре PNG в `docs/design/screenshots/rc4/`.
Остальные незакоммиченные изменения предыдущих RC сохранены.

## Установка и откат владельцем

Нативный компонент не изменён; при установленном RC3 пересборка не требуется.
Команды применения Codex не выполнял:

```bash
cd ~/Projects/pixelrail
git diff --check
./scripts/deploy.sh             # просмотр плана
./scripts/deploy.sh --apply     # только после проверки плана
```

Откат: `./scripts/rollback.sh` (план), затем `./scripts/rollback.sh --apply`.
Существующий installer сохраняет резервные копии и пользовательские настройки.

Ручная проверка T480: Super+N — новое уведомление, действия, длинный текст,
DND/удаление/очистка; Super+V — поиск RU/EN, ссылки и оригинальные изображения;
Super+Ctrl+T — вкладки, прокрутка, выбор/применение/отмена. Проверить Light/Dark/Auto,
Escape, outside click, Super+A↔N, Super+Shift+S→cancel/repeat и обычный Escape после
отмены. Настоящие клавиши, Wayland-фокус, вставка в приложения и аппаратная визуальная
приёмка остаются владельцу. Сопоставимые RSS/CPU/ватты не измерялись; улучшение
автономности или отсутствие аппаратной регрессии производительности не заявляется.
