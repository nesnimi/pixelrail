# Восстановление PixelRail

Hyprland не зависит от успешной загрузки QML: при отказе меню откройте терминал
Super+Return. Не применяйте `pkill qs`, `killall waybar` или массовое удаление config.

```bash
~/.local/bin/pixelrail-shell
~/.local/bin/pixelrail-panel status
~/.local/bin/pixelrail-notifications status
```

Запуск сериализован lock на HOME/display. Готовый экземпляр переиспользуется,
старые управляемые процессы завершаются только после готовности нового IPC.
При аварии нет бесконечного рестарта: выполните pixelrail-shell вручную.
Чужие экземпляры не считаются управляемыми по одному имени executable.

Fallback включается явно:

```bash
~/.local/bin/pixelrail-notifications mode swaync
~/.local/bin/pixelrail-panel mode waybar
```

Переключение уведомлений проверяет D-Bus ownership; сторонний сервер не завершается.
Если текущий Quickshell не отвечает на IPC, не убивайте произвольный PID: сохраните
лог и используйте откат. При неудачной активации native уведомлений восстанавливается
SwayNC, если имя свободно. Чужой владелец имени остаётся нетронутым.

```bash
cd ~/Projects/pixelrail
./scripts/rollback.sh
./scripts/rollback.sh --apply
```

Резервные копии: `~/.local/state/pixelrail/deployments/ID`, релизы:
`~/.local/share/pixelrail/releases/ID`. Они не удаляются при откате.
Настройки в `$XDG_CONFIG_HOME/pixelrail`, кэш темы/профиля в `$XDG_CACHE_HOME/pixelrail`,
state обоев в `$XDG_STATE_HOME/pixelrail` (см. wallpapers.md) не переносятся в release.
Не удаляйте cliphist db, wallpaper state или настройки для исправления QML.

После обновления Qt и ошибки native plugin пересоберите его в репозитории и
повторите dry-run/apply. Plugin нужен для безопасного переключения notification
ownership и событий resume/backlight. Его отсутствие не запускает сторонние службы.
Откат не обновляет автоматически пользовательский Qt: старый бинарный plugin тоже
может потребовать пересборки под установленный Qt.
