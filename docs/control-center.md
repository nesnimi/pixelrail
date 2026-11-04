# Pixel Control Center — v3.1 RC2

Одно окно существующего Quickshell, сверху слева справа от Sidebar/Waybar.
Ширина 400 logical px с ограничением по экрану. Высота по умолчанию 50%, нижняя
ручка меняет её от 30 до 75%; выбранная доля сохраняется в XDG config.
Контент прокручивается колесом/тачпадом/PageUp/PageDown, фокус автоматически
показывается. Видимого вертикального scrollbar нет; resize handle сохранён.

Визуальная доработка RC2: тональный `surfaceContainer`, заголовок 18 px,
сегментированные вкладки, плитки 64 px / radius 22, компактные chips EN/RU и
профиля. Ползунки получили дорожку 28 px и зону ввода 44 px; их live backend
сохранён. Звук отключается кнопкой динамика слева, процент остаётся справа.
Настройки PixelRail и питание находятся рядом в нижней строке, доступной прокруткой.
[Снимки до/после, параметры и ограничения](design/pixelrail-v3.1-rc2-visual-polish.md).

## Режимы

Super+A открывает «Быстрые настройки», Super+N — «Уведомления».
Повтор того же сочетания закрывает окно, другое переключает содержимое того же
окна. Вкладки в заголовке синхронизированы с IPC. Escape и существующий
HyprlandFocusGrab закрывают панель; кнопка × убрана. Во вложенных Wi-Fi/Bluetooth
страницах сохранена кнопка «Назад». Launcher и несовместимые меню скрываются.

## Быстрые настройки

1. Две компактные плитки Wi-Fi / Bluetooth открывают подробности.
2. Живые яркость и громкость, Mute: процент и бегунок меняются во время drag,
   backend coalescing 40 мс, release применяет последнее значение. Недоступное
   устройство не получает фиктивно работающий slider. [OSD и backend](osd.md).
3. EN/RU — реальный Hyprland active_keymap. Клик вызывает switchxkblayout для
   выбранной клавиатуры и повторно читает состояние. Alt+Shift не меняется.
   События activelayout, focus/config reload обновляют индикатор без polling.
   Если данные неизвестны — «—», переключатель disabled. Действительный main keyboard имеет приоритет; имя
   activelayout используется только при отсутствии main в ответе Hyprland.
4. Battery/Performance — существующий графический профиль. Переключение вызывает
   pixelrail-profile, меняет эффекты Hyprland и уведомляет пользователя. EPP,
   governor, Turbo и GPU PM не изменяются.
5. Процент батареи (BAT0/BAT1 по суммарной энергии/ёмкости, не среднее процентов)
   и компактные часы HH:mm. При отсутствии данных батареи — «—».
6. MPRIS-карточка только при наличии плеера; управление и выбор плеера сохранены.
7. «Питание и выход» открывает существующее меню, не выполняет выключение сразу.

## Подробности

Wi-Fi использует Networking/NetworkManager, известные/open сети и PSK input;
поиск ограничен 12 секундами, закрытие отменяет свой scanner. Другие механизмы
аутентификации остаются в системном редакторе подключений.
Bluetooth использует BlueZ, реальный список и существующие connect/pair/disconnect.
Статус службы/rfkill/адаптера проверяется отдельно, ошибку одного API не считаем
доказательством отсутствия железа. [Диагностика](bluetooth.md).

## Уведомления

История ограничена NotificationController, карточки содержат приложение, время,
содержимое и доступные действия. Удаление отдельных/всех, DND и пустое состояние
сохранены. Закрытие панели/попапа не стирает историю. По умолчанию остаётся SwayNC;
переключение native режима выполняется явно и проверяет D-Bus ownership.

```bash
pixelrail-notifications mode pixelrail
pixelrail-notifications status
pixelrail-notifications mode swaync
```

Не запускайте второй NotificationServer самостоятельно. После сбоя транзакция
пытается восстановить SwayNC, если имя свободно; чужой сервер не завершается.

## Проверка и восстановление

```bash
python3 tests/settings.py
python3 tests/keyboard-runtime.py
python3 tests/control-ui.py
python3 tests/control-runtime.py
python3 tests/system-runtime.py
python3 tests/session-events.py
```

UI tests проверяют реальный drag/key/mouse на offscreen адаптере; runtime tests
используют unmapped окна, частную шину и fake hardware. Реальные T480 Fn,
Bluetooth pairing, внешние устройства, клики вне/фокус и suspend остаются ручной
приёмкой. [Установка и откат](installation.md), [восстановление](recovery.md).

## v3.1 RC1 — Pixel Experience

RC3 обновляет только Launcher и Settings: адаптивная левая навигация,
карточки и независимая прокрутка в прежнем окне. Страница Settings асинхронно
загружается из файла при открытии и освобождается при выходе; настройки хранятся
прежними backend. [Снимки, ограничения и проверки RC3](design/pixelrail-v3.1-rc3.md).

Единые Ui.Tokens/Roboto/Material Symbols, плитки Wi-Fi/BT и компактный ряд
EN/RU + профиль перед live sliders. Settings — ленивый вложенный раздел того же
окна: кнопка «Настройки PixelRail», команда `pixelrail-settings`, запись приложений
в Launcher после deploy. Профиль по-прежнему только графический.

`pixelrail-theme ui iconStyle themed|original` и `pixelrail-theme ui animations true|false`
сохраняют XDG theme.json атомарно, не генерируют новую палитру ради UI-флага.
Настройки применяются FileView без рестарта. DND/height остаются в desktop.json.
Reduced motion относится к оболочке; эффекты Hyprland выбирает отдельный profile.
Курсор подготавливается вручную: [cursor.md](design/cursor.md).
