# Bluetooth: диагностика и восстановление

PixelRail использует существующий Quickshell.Bluetooth / BlueZ backend.
Поиск ограничен 20 секундами и останавливается при закрытии панели. Список и
connect/disconnect/pair относятся к реальным устройствам. Подтверждение PIN может
требовать установленного Bluetooth-агента; PixelRail не имитирует успешное сопряжение.

Статусы различают включённый и выключенный адаптер, rfkill block, отсутствие
службы, отсутствие контроллера и неизвестность. Наличие `hci0` при свободном
D-Bus имени не означает отсутствие железа. Probe асинхронный, при открытии,
смене адаптера, владельца org.bluez и resume; постоянного polling нет.

## Результат read-only диагностики при подготовке кандидата

- BlueZ установлен; bluetooth.service loaded, disabled, inactive (dead).
- D-Bus `NameHasOwner org.bluez` → false.
- rfkill: tpacpi_bluetooth_sw и hci0 unblocked (soft/hard).
- sysfs: контроллер hci0, драйвер btusb, USB ID 8087:0029.
- Контроллер hci0 обнаружен; `bluetoothctl list` не ответил за 5 секунд.
- lsusb в окружении отсутствует. Работоспособность радио, поиск и pairing не проверены.

На основании этого UI сообщает о недоступной службе, а не об отсутствии адаптера.
Службы/драйверы/rfkill не изменялись. На другой сессии диагноз нужно повторить.

## Только чтение

```bash
systemctl status bluetooth.service --no-pager
rfkill --json
ls -l /sys/class/bluetooth
readlink -f /sys/class/bluetooth/hci0/device/driver
busctl --system call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus NameHasOwner s org.bluez
timeout 5 bluetoothctl list
timeout 5 bluetoothctl show
journalctl -b -u bluetooth.service --no-pager -n 60
```

Не устанавливайте пакет только ради lsusb. При hard block проверьте физическое
радио/настройки устройства; программная разблокировка hard block не исправляет.

## Ручные действия владельца системы (не выполнялись Codex)

Только после проверки диагностики и решения пользователя:

```bash
sudo systemctl start bluetooth.service   # если BlueZ установлен, но служба остановлена
sudo rfkill unblock bluetooth           # только при soft block и по желанию владельца
bluetoothctl power on                   # если контроллер уже обнаружен службой
```

Постоянный autostart службы (`enable`) — отдельное решение пользователя.
Если BlueZ отсутствует, согласуйте установку средствами Arch; PixelRail этого не делает.
После появления имени org.bluez открытая панель обновится событийно; при ошибке
закройте/откройте страницу. Не перезапускайте драйверы без отдельной диагностики.
