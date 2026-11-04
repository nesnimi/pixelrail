# Типичные неисправности

- **Меню не открывается:** Super+Return → `pixelrail-shell`; проверьте путь релиза,
  сообщения QML/IPC. См. [recovery.md](recovery.md). Не запускайте второй qs вручную.
- **Громкость недоступна:** проверьте `wpctl status`, default sink и существующие
  PipeWire/WirePlumber user services. Отсутствие ready sink скрывает ползунок.
  Ничего не устанавливается/не перезапускается автоматически.
- **Яркость:** `brightnessctl -m -c backlight` только читает состояние. В записи
  PixelRail не должно быть `-n 1` — это зафиксированная регрессия T480. Ошибку доступа
  показываем, а не подменяем процент. См. [osd.md](osd.md).
- **Bluetooth:** различайте службу, контроллер и rfkill; [bluetooth.md](bluetooth.md).
- **EN/RU показывает —:** не удалось прочитать активную клавиатуру либо keymap
  неизвестен. Значение не подменяется EN. Повторно откройте Quick Settings;
  `hyprctl -j devices` должен вернуть main keyboard / active_keymap.
- **Уведомления:** проверьте `pixelrail-notifications status`. По умолчанию SwayNC;
  native режим включается явно. Не запускайте оба сервера независимо.
- **После сна:** временные панели закрываются, brightness/theme обновляются,
  сервисы восстанавливают свои модели. Реальный suspend/resume проверяется вручную.
  Если сборка plugin старая, пересоберите перед установкой.
- **Deploy отказал:** missing native → build-native.sh; changed since deployment →
  просмотрите изменения и backup. Не удаляйте защитные manifest/backup.
- **Waybar ещё виден:** `pixelrail-panel status`, затем явное переключение режима.
  Чужой Waybar может потребовать отдельного решения пользователя.

Сбор диагностик не должен менять EPP, governor, GPU PM или службы:
`pixelrail-power-audit --help`, `pixelrail-benchmark --help`.
Benchmark с exercise управляет UI: запускайте его в изолированном HOME либо осознанно
в своей сессии; время IPC/state readiness не является временем presented frame.
