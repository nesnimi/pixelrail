.pragma library
function status(adapter, blockedState, probe) {
    if (probe.blocked || (adapter && adapter.state===blockedState)) return "Заблокирован";
    if (probe.service===false) return "Служба Bluetooth недоступна";
    if(adapter && adapter.discovering)return "Поиск устройств…";
    if(adapter && adapter.state===2)return "Включение…";
    if(adapter && adapter.state===3)return "Выключение…";
    if (adapter) return adapter.enabled ? "Включён" : "Выключен";
    if (probe.error || probe.service!==true) return "Состояние неизвестно";
    if (probe.controllers && probe.controllers.length) return "Контроллер обнаружен · подключение…";
    return "Адаптер не обнаружен";
}
