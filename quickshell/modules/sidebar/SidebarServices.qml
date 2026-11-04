import QtQuick
import Quickshell
import Quickshell.Services.UPower
import "../system" as System
import Quickshell.Networking
import "SidebarLogic.js" as Logic

Scope {
    id: root
    readonly property var batteryInfo: Logic.battery(UPower.devices.values.filter(device => device.ready), UPower.displayDevice)
    readonly property var batteries: batteryInfo.devices
    readonly property var percent: batteryInfo.percent
    readonly property bool charging: batteries.some(device => device.state === UPowerDeviceState.Charging || device.state === UPowerDeviceState.PendingCharge)
    readonly property string batteryLabel: percent === null ? "—" : Math.round(percent) + "%"
    readonly property string batteryTooltip: "Батарея: " + (percent === null ? "данные недоступны" : Math.round(percent) + "%")
        + (UPower.onBattery ? " · от батареи" : " · внешнее питание")
        + batteries.map(device => "\n" + device.nativePath + ": " + Math.round(device.percentage * 100) + "% · "
            + UPowerDeviceState.toString(device.state) + "\n" + device.model
            + " · " + device.energy.toFixed(1) + " / " + device.energyCapacity.toFixed(1) + " (UPower)").join("")
    readonly property var connectedDevice: Networking.devices.values.find(device => device.connected) || null
    readonly property var connectedNetwork: connectedDevice ? connectedDevice.networks.values.find(network => network.connected) || null : null
    readonly property bool wifi: connectedDevice !== null && connectedDevice.type === DeviceType.Wifi
    readonly property string networkGlyph: !connectedDevice ? "offline" : wifi ? "wifi" : "wired"
    readonly property string networkTooltip: !connectedDevice ? "Сеть: нет подключения" : (wifi ? "Wi-Fi: " : "Ethernet: ")
        + (connectedNetwork ? connectedNetwork.name : connectedDevice.name)
        + (wifi && connectedNetwork ? " · " + Math.round(connectedNetwork.signalStrength * 100) + "%" : "")
        + "\n" + NetworkConnectivity.toString(Networking.connectivity)
    readonly property var sink: System.SystemControls.sink
    readonly property var audio: System.SystemControls.audio
    readonly property bool muted:System.SystemControls.muted
    readonly property string volumeTooltip: !audio ? "Звук: устройство недоступно" : "Громкость: " + Math.round(System.SystemControls.volume * 100)
        + "%" + (muted ? " · выключена" : "") + "\n" + sink.description + "\nЛКМ — настройки · ПКМ — mute · колесо — громкость"
    function mute(): void { System.SystemControls.mute(); }
    function adjust(direction: int): void { if(audio)System.SystemControls.requestVolume(System.SystemControls.volume+direction*.05); }
}
