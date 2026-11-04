import QtQuick
import QtTest
import "../quickshell/modules/control/BluetoothLogic.js" as Bluetooth
TestCase {
    name:"BluetoothStates"
    function test_states() {
        compare(Bluetooth.status({enabled:true,state:1},3,{}),"Включён");
        compare(Bluetooth.status({enabled:false,state:1},3,{}),"Выключен");
        compare(Bluetooth.status({enabled:true,state:3},3,{}),"Заблокирован");
        compare(Bluetooth.status(null,3,{blocked:true}),"Заблокирован");
        compare(Bluetooth.status(null,3,{service:false,controllers:["hci0"]}),"Служба Bluetooth недоступна");
        compare(Bluetooth.status(null,3,{service:true,controllers:[]}),"Адаптер не обнаружен");
        compare(Bluetooth.status(null,3,{service:true,controllers:["hci0"]}),"Контроллер обнаружен · подключение…");
        compare(Bluetooth.status(null,3,{service:null}),"Состояние неизвестно");
        compare(Bluetooth.status(null,3,{service:true,error:"denied"}),"Состояние неизвестно");
    }
}
