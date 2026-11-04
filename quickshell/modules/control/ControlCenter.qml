pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Networking
import Quickshell.Bluetooth
import Quickshell.Services.Mpris
import "../../theme" as Theme
import "../sidebar" as Sidebar
import "../notifications" as Notifications
import "." as Controls
import "../../components/PopupPlacement.js" as Placement
import "../system" as System
import "../../ui" as Ui
import "BluetoothLogic.js" as BluetoothLogic

PanelWindow {
    id:root
    property bool opened:false
    property real contentReveal:0
    property string section:"overview"
    property int sideOffset:12
    property var targetScreen:null
    property var notifier:null
    property var allowedWindow:null
    signal closeRequested()
    signal powerRequested()
    signal menuRequested(string mode)
    readonly property var keyboardState:keyboard.state
    function toggleKeyboard():void {keyboard.toggle();}
    screen:targetScreen || Quickshell.screens[0]
    visible:opened && !!screen
    anchors {left:true;top:true}
    margins {left:Placement.left(screen ? screen.width : 400,root.sideOffset);top:12}
    implicitWidth:Placement.width(section==="settings" ? Ui.Tokens.settingsWidth : Ui.Tokens.controlWidth,screen ? screen.width : 400,root.sideOffset)
    implicitHeight:screen ? Math.max(1,Math.min(screen.height-24,Math.round(screen.height*Controls.DesktopState.heightRatio))) : 380
    exclusionMode:ExclusionMode.Ignore;color:"transparent"
    WlrLayershell.namespace:"pixelrail-control-center";WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:opened && !System.ScreenshotState.active ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    Theme.Palette {id:colors}
    Sidebar.SidebarServices {id:services}
    HyprlandFocusGrab {windows:root.allowedWindow ? [root,root.allowedWindow] : [root];active:root.visible && !System.ScreenshotState.active;onCleared:if(root.visible && root.opened && !System.ScreenshotState.active)root.closeRequested()}
    Shortcut {sequence:"Escape";context:Qt.WindowShortcut;enabled:root.opened && !System.ScreenshotState.active;onActivated:root.closeRequested()}
    readonly property var wifiDevice: Networking.devices.values.find(device=>device.type===DeviceType.Wifi) || null
    readonly property var wifiNetwork:wifiDevice ? wifiDevice.networks.values.find(network=>network.connected) || null : null
    readonly property var adapter:Bluetooth.defaultAdapter
    property var bluetoothProbe:({service:null,controllers:[],blocked:false})
    property bool bluetoothRefreshPending:false
    readonly property string bluetoothStatus:BluetoothLogic.status(adapter,BluetoothAdapterState.Blocked,bluetoothProbe)
    function refreshBluetooth():void {if(bluetoothJob.running){bluetoothRefreshPending=true;return;}bluetoothRefreshPending=false;bluetoothJob.running=true;}
    Process {
        id:bluetoothJob;command:[Controls.DesktopState.helper,"bluetooth-state"]
        stdout:StdioCollector {onStreamFinished:{try{root.bluetoothProbe=JSON.parse(text);}catch(error){root.bluetoothProbe={service:null,error:"Состояние неизвестно"};}}}
        onExited:if(root.bluetoothRefreshPending)Qt.callLater(root.refreshBluetooth)
    }
    Connections {target:System.SessionState;function onBackendChanged(){root.refreshBluetooth();}function onResumed(){root.refreshBluetooth();}}
    onAdapterChanged:refreshBluetooth()
    Controls.BluetoothActions {id:bluetoothActions;available:!!root.adapter && root.adapter.enabled && root.bluetoothProbe.service!==false && !root.bluetoothProbe.blocked}
    Controls.KeyboardState {id:keyboard}
    SystemClock {id:clock;precision:SystemClock.Minutes}
    readonly property string profilePath:(Quickshell.env("XDG_CACHE_HOME") || Quickshell.env("HOME")+"/.cache")+"/pixelrail/profile"
    property string profile:"battery"
    FileView {
        id:profileFile;path:root.profilePath;watchChanges:true;preload:true;printErrors:false
        onLoaded:root.profile=text().trim()==="performance" ? "performance" : "battery"
        onFileChanged:{watchChanges=false;reload();Qt.callLater(()=>{profileFile.watchChanges=true;profileFile.reload();});}
    }
    Process {id:profileJob;
        onExited:{profileFile.watchChanges=false;profileFile.reload();Qt.callLater(()=>{profileFile.watchChanges=true;profileFile.reload();});}
    }
    function toggleProfile():void {if(profileJob.running)return;profileJob.command=[(Quickshell.env("PIXELRAIL_SCRIPTS") || Quickshell.shellPath("../scripts"))+"/pixelrail-profile","toggle"];profileJob.running=true;}
    property var selectedPlayer:null
    readonly property var player: selectedPlayer && Mpris.players.values.includes(selectedPlayer) ? selectedPlayer : Mpris.players.values.find(p=>p.isPlaying) || Mpris.players.values[0] || null
    readonly property bool notificationsMode:section==="notifications"
    readonly property bool quickOverview:!notificationsMode && !detail
    readonly property bool detail:section==="wifi" || section==="bluetooth" || section==="settings"
    property var selectedWifi:null
    property string networkError:""
    property string bluetoothError:""
    property var system:System.SystemControls
    readonly property var brightness:system.brightness
    function refreshBrightness():void {system.refreshBrightness();}
    function selectSection(value):void {
        section=value || "overview";
        Qt.callLater(()=>{const item=value==="wifi" ? wifiCard : value==="bluetooth" ? bluetoothCard : value==="volume" ? audioCard : null;
            if(item && !root.detail)scroll.contentY=Math.max(0,Math.min(scroll.contentHeight-scroll.height,item.y));else scroll.contentY=0;
            if(root.detail)backButton.forceActiveFocus();});
    }
    function revealFocus():void {
        const window=scroll.Window.window;
        const item=window ? window.activeFocusItem : null;
        if(!item)return;
        let ancestor=item;
        while(ancestor && ancestor!==content)ancestor=ancestor.parent;
        if(!ancestor)return;
        const position=item.mapToItem(content,0,0);
        if(position.y<scroll.contentY)scroll.contentY=position.y;
        else if(position.y+item.height>scroll.contentY+scroll.height)scroll.contentY=position.y+item.height-scroll.height;
        scroll.contentY=Math.max(0,Math.min(Math.max(0,scroll.contentHeight-scroll.height),scroll.contentY));
    }
    Connections {target:scroll.Window.window;function onActiveFocusItemChanged(){Qt.callLater(root.revealFocus);}}
    function connectWifi(network):void {
        networkError="";selectedWifi=network;
        if(network.connected)network.disconnect();
        else if(network.known || network.security===WifiSecurityType.Open || network.security===WifiSecurityType.Owe)network.connect();
        else if(![WifiSecurityType.Wpa2Psk,WifiSecurityType.WpaPsk,WifiSecurityType.Sae].includes(network.security))networkError="Для этой сети используйте системный редактор подключений";
    }
    property bool scanning:false
    property var scanTarget:null
    property var btScanTarget:null
    function scanWifi():void {if(wifiDevice){scanTarget=wifiDevice;scanTarget.scannerEnabled=true;scanning=true;scanTimeout.restart();}}
    Timer {id:scanTimeout;interval:12000;onTriggered:{if(root.scanTarget)root.scanTarget.scannerEnabled=false;root.scanTarget=null;root.scanning=false;}}
    Component.onDestruction:{if(scanTarget && scanning)scanTarget.scannerEnabled=false;if(btScanTarget)btScanTarget.discovering=false;}
    Component.onCompleted:{contentReveal=1;refreshBrightness();refreshBluetooth();selectSection(section);}
    onOpenedChanged:if(opened)refreshBrightness()
    Connections {target:root.selectedWifi;ignoreUnknownSignals:true;function onConnectionFailed(reason){root.networkError=ConnectionFailReason.toString(reason);}}
    Rectangle {
        opacity:root.contentReveal
        Behavior on opacity {NumberAnimation {duration:Ui.Tokens.panel;easing.type:Easing.OutCubic}}
        objectName:"control-surface"
        anchors.fill:parent;radius:Ui.Tokens.radiusPanel;color:colors.surfaceContainer
        ColumnLayout {
            anchors {fill:parent;margins:Ui.Tokens.space} spacing:Ui.Tokens.spaceSm
            RowLayout {
                Layout.fillWidth:true
                Controls.ControlButton {id:backButton;objectName:"control-back";visible:root.detail;symbol:"arrow_back";text:"";implicitWidth:32;Accessible.name:"Назад";onClicked:{const previous=root.section;root.selectSection("overview");(previous==="wifi" ? wifiTile : previous==="settings" ? settingsEntry : bluetoothTile).forceActiveFocus();}}
                Controls.ControlLabel {objectName:"control-heading";Layout.fillWidth:true;text:root.detail ? (root.section==="wifi" ? "Wi-Fi" : root.section==="settings" ? "PixelRail Settings" : "Bluetooth") : root.notificationsMode ? "Уведомления" : "Быстрые настройки";font {pixelSize:Ui.Tokens.controlTitle;weight:Font.Medium} maximumLineCount:1;elide:Text.ElideRight}
            }
            Rectangle {
                Layout.fillWidth:true;implicitHeight:40;radius:Ui.Tokens.radiusPill;color:colors.surfaceContainerHigh
                RowLayout {
                    anchors {fill:parent;margins:3} spacing:Ui.Tokens.spaceXs
                    Controls.ControlButton {objectName:"control-tab-settings";symbol:"settings";tonal:true;Layout.fillWidth:true;Layout.preferredWidth:1;text:"Настройки";active:!root.notificationsMode;onClicked:root.selectSection("overview")}
                    Controls.ControlButton {objectName:"control-tab-notifications";symbol:"notifications";tonal:true;Layout.fillWidth:true;Layout.preferredWidth:1;text:"Уведомления";active:root.notificationsMode;onClicked:root.selectSection("notifications")}
                }
            }
            Flickable {
                id:scroll;objectName:"control-scroll"
                Layout.fillWidth:true;Layout.fillHeight:true;clip:true
                contentWidth:width;contentHeight:content.implicitHeight;boundsBehavior:Flickable.StopAtBounds
                // No ScrollBar: wheel/touchpad and keyboard still scroll the full width.
                Keys.onPressed:event=>{
                    if(event.key===Qt.Key_PageDown || event.key===Qt.Key_PageUp) {
                        contentY=Math.max(0,Math.min(Math.max(0,contentHeight-height),contentY+(event.key===Qt.Key_PageDown ? 1 : -1)*height*.8));
                        event.accepted=true;
                    }
                }
                ColumnLayout {
                    id:content;width:scroll.width;spacing:Ui.Tokens.spaceSm
                    GridLayout {
                        id:quickGrid;objectName:"control-quick-grid";visible:root.quickOverview
                        Layout.fillWidth:true;columns:2;columnSpacing:8;rowSpacing:8
                        Controls.ControlTile {
                            id:wifiTile;objectName:"control-wifi-tile";Layout.fillWidth:true;Layout.preferredWidth:1
                            symbol:"wifi";text:"Wi-Fi";status:!root.wifiDevice ? "Нет адаптера" : !Networking.wifiHardwareEnabled ? "Заблокирован" : !Networking.wifiEnabled ? "Выключен" : root.wifiNetwork ? root.wifiNetwork.name : "Не подключён"
                            active:!!root.wifiDevice && Networking.wifiEnabled && Networking.wifiHardwareEnabled
                            onClicked:root.selectSection("wifi")
                        }
                        Controls.ControlTile {
                            id:bluetoothTile;objectName:"control-bluetooth-tile";Layout.fillWidth:true;Layout.preferredWidth:1
                            symbol:"bluetooth";text:"Bluetooth";status:root.bluetoothStatus
                            active:!!root.adapter && root.bluetoothProbe.service!==false && root.adapter.enabled;onClicked:root.selectSection("bluetooth")
                        }
                    }
                    Rectangle {
                        id:wifiCard;visible:root.section==="wifi";Layout.fillWidth:true;implicitHeight:wifiContent.implicitHeight+24;radius:Ui.Tokens.radiusLg;color:colors.surfaceContainer
                        ColumnLayout {
                            id:wifiContent;anchors {left:parent.left;right:parent.right;top:parent.top;margins:Ui.Tokens.spaceMd} spacing:Ui.Tokens.spaceSm
                            RowLayout {
                                Controls.ControlLabel {text:"Wi-Fi";font.weight:Font.Medium;Layout.fillWidth:true}
                                Controls.ControlButton {text:!Networking.wifiHardwareEnabled ? "Блок" : Networking.wifiEnabled ? "Вкл" : "Выкл";active:Networking.wifiEnabled && Networking.wifiHardwareEnabled;enabled:!!root.wifiDevice && Networking.wifiHardwareEnabled;onClicked:Networking.wifiEnabled=!Networking.wifiEnabled}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;text:!root.wifiDevice ? "Wi-Fi адаптер недоступен" : !Networking.wifiHardwareEnabled ? "Wi-Fi заблокирован аппаратно" : services.networkTooltip;color:colors.muted}
                            Controls.ControlButton {text:root.scanning ? "Поиск сетей…" : "Обновить сети";enabled:!!root.wifiDevice && Networking.wifiEnabled && !root.scanning;onClicked:root.scanWifi()}
                            Repeater {
                                model:root.wifiDevice && Networking.wifiEnabled ? root.wifiDevice.networks.values : []
                                delegate: Controls.ControlButton {required property var modelData;Layout.fillWidth:true;text:modelData.name+" · "+Math.round(modelData.signalStrength*100)+"%"+(modelData.connected ? " · подключено" : "");active:modelData.connected;enabled:!modelData.stateChanging;onClicked:root.connectWifi(modelData)}
                            }
                            TextField {
                                id:password;Layout.fillWidth:true;visible:!!root.selectedWifi && !root.selectedWifi.known && !root.selectedWifi.connected && [WifiSecurityType.Wpa2Psk,WifiSecurityType.WpaPsk,WifiSecurityType.Sae].includes(root.selectedWifi.security)
                                placeholderText:"Пароль выбранной сети";echoMode:TextInput.Password;color:colors.text;placeholderTextColor:colors.muted;selectionColor:colors.selected;selectedTextColor:colors.selectedText
                                background:Rectangle {radius:Ui.Tokens.radiusSm;color:colors.surfaceHigh;border.width:password.activeFocus ? 1 : 0;border.color:colors.accent}
                            }
                            Controls.ControlButton {
                                visible:password.visible;text:"Подключиться";enabled:password.text.length>0
                                onClicked:{const n=root.selectedWifi;if(n && [WifiSecurityType.Wpa2Psk,WifiSecurityType.WpaPsk,WifiSecurityType.Sae].includes(n.security))n.connectWithPsk(password.text);else root.networkError="Для этой сети используйте системный редактор подключений";password.clear();}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;visible:root.networkError!=="";text:root.networkError;color:colors.error}
                            Controls.ControlButton {text:"Расширенные настройки сети";onClicked:Quickshell.execDetached(["nm-connection-editor"])}
                        }
                    }
                    Rectangle {
                        id:bluetoothCard;visible:root.section==="bluetooth";Layout.fillWidth:true;implicitHeight:bluetoothContent.implicitHeight+24;radius:Ui.Tokens.radiusLg;color:colors.surfaceContainer
                        ColumnLayout {
                            id:bluetoothContent;anchors {left:parent.left;right:parent.right;top:parent.top;margins:Ui.Tokens.spaceMd} spacing:Ui.Tokens.spaceSm
                            RowLayout {
                                Controls.ControlLabel {text:"Bluetooth";font.weight:Font.Medium;Layout.fillWidth:true}
                                Controls.ControlButton {text:root.adapter && root.adapter.enabled ? "Вкл" : "Выкл";active:!!root.adapter && root.bluetoothProbe.service!==false && root.adapter.enabled;enabled:!!root.adapter && root.bluetoothProbe.service!==false && !root.bluetoothProbe.blocked && root.adapter.state!==BluetoothAdapterState.Blocked;onClicked:root.adapter.enabled=!root.adapter.enabled}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;text:root.bluetoothStatus;color:colors.muted}
                            Controls.ControlButton {text:root.adapter && root.adapter.discovering ? "Остановить поиск" : "Найти устройства";enabled:!!root.adapter && root.bluetoothProbe.service!==false && root.adapter.enabled;onClicked:{if(root.adapter.discovering){root.adapter.discovering=false;root.btScanTarget=null;btTimeout.stop();}else{root.btScanTarget=root.adapter;root.btScanTarget.discovering=true;btTimeout.restart();}}}
                            Timer {id:btTimeout;interval:20000;onTriggered:{if(root.btScanTarget)root.btScanTarget.discovering=false;root.btScanTarget=null;}}
                            Repeater {
                                model:root.adapter && root.bluetoothProbe.service!==false && root.adapter.enabled ? root.adapter.devices.values : []
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth:true
                                    Controls.ControlLabel {Layout.fillWidth:true;text:modelData.name+" · "+(["Не подключено","Подключено","Отключение…","Подключение…"][modelData.state] || "Неизвестно")}
                                    Controls.ControlButton {text:modelData.connected ? "Отключить" : modelData.paired ? "Подключить" : "Сопрячь";enabled:!modelData.pairing && !bluetoothActions.pending;onClicked:bluetoothActions.request(parent.modelData)}
                                }
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;visible:bluetoothActions.error!=="";text:bluetoothActions.error;color:colors.error}
                            Controls.ControlLabel {Layout.fillWidth:true;text:"Подтверждение PIN/доступа выполняется Bluetooth-агентом системы";color:colors.muted}
                        }
                    }
                    RowLayout {
                        objectName:"control-system-controls";visible:root.quickOverview;Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm
                        Controls.ControlButton {objectName:"control-layout";symbol:"language";tonal:true;Layout.fillWidth:true;Layout.preferredWidth:1;text:keyboard.state.label;Accessible.name:"Раскладка клавиатуры";enabled:keyboard.state.available && !keyboard.togglePending;onClicked:keyboard.toggle()}
                        Controls.ControlButton {objectName:"control-profile";symbol:root.profile==="battery" ? "eco" : "speed";tonal:true;Layout.fillWidth:true;Layout.preferredWidth:1;text:root.profile==="battery" ? "Battery" : "Performance";Accessible.name:"Графический профиль";active:root.profile==="performance";enabled:!profileJob.running;onClicked:root.toggleProfile()}
                    }
                    Rectangle {
                        id:audioCard;objectName:"control-audio";visible:root.quickOverview;Layout.fillWidth:true;implicitHeight:audioContent.implicitHeight;color:"transparent"
                        ColumnLayout {
                            id:audioContent;anchors {left:parent.left;right:parent.right;top:parent.top} spacing:Ui.Tokens.spaceXs
                            RowLayout {
                                spacing:Ui.Tokens.spaceSm
                                Item {Layout.preferredWidth:32;Layout.preferredHeight:36;Ui.PixelIcon {anchors.centerIn:parent;name:"light_mode";size:22;color:colors.text}}
                                Controls.LiveSlider {id:brightnessSlider;objectName:"control-brightness-slider";Accessible.name:"Яркость";Layout.fillWidth:true;from:1;to:100;visible:!!root.brightness.available;enabled:visible;backendValue:root.brightness.percent || 1;backendPending:root.system.brightnessUiPending;onRequested:(value,finalValue)=>root.system.requestBrightness(value,finalValue)}
                                Controls.ControlLabel {objectName:"control-brightness-percent";font.pixelSize:Ui.Tokens.controlPercent;Layout.minimumWidth:34;horizontalAlignment:Text.AlignRight;text:root.brightness.available ? Math.round(brightnessSlider.pressed || root.system.brightnessUiPending ? brightnessSlider.value : root.brightness.percent)+"%" : "Недоступна";color:colors.muted}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;visible:!!root.brightness.error;text:root.brightness.error || "";color:colors.error}
                            RowLayout {
                                spacing:Ui.Tokens.spaceSm
                                Controls.ControlButton {objectName:"control-mute";symbol:root.system.muted ? "volume_off" : "volume_up";text:"";implicitWidth:32;Accessible.name:root.system.muted ? "Включить звук" : "Отключить звук";enabled:root.system.audioAvailable;active:root.system.audioAvailable && root.system.muted;onClicked:root.system.mute();ToolTip.visible:hovered;ToolTip.text:Accessible.name}
                                Controls.LiveSlider {id:volumeSlider;objectName:"control-volume-slider";Accessible.name:"Громкость";Layout.fillWidth:true;visible:root.system.audioAvailable;enabled:visible;backendValue:root.system.audioAvailable ? root.system.volume : 0;backendPending:root.system.volumeUiPending;onRequested:(value,finalValue)=>root.system.requestVolume(value,finalValue)}
                                Controls.ControlLabel {objectName:"control-volume-percent";font.pixelSize:Ui.Tokens.controlPercent;Layout.minimumWidth:34;horizontalAlignment:Text.AlignRight;text:!root.system.audioAvailable ? "Недоступна" : Math.round((volumeSlider.pressed || root.system.volumeUiPending ? volumeSlider.value : root.system.volume)*100)+"%"+(root.system.muted ? " · Mute" : "");color:colors.muted}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;visible:root.system.audioError!=="";text:root.system.audioError;color:colors.error}
                        }
                    }
                    Rectangle {
                        objectName:"control-system-info";visible:root.quickOverview;Layout.fillWidth:true;implicitHeight:30;radius:Ui.Tokens.radiusPill;color:colors.surfaceContainerHigh
                        RowLayout {
                            anchors {fill:parent;leftMargin:12;rightMargin:12} spacing:Ui.Tokens.spaceSm
                            Ui.PixelIcon {name:"battery_full";size:18;color:colors.muted}
                            Controls.ControlLabel {objectName:"control-battery";font.pixelSize:Ui.Tokens.controlPercent;text:services.batteryLabel;Accessible.name:services.batteryTooltip;color:colors.text;Layout.fillWidth:true}
                            Ui.PixelIcon {name:"schedule";size:18;color:colors.muted}
                            Controls.ControlLabel {objectName:"control-clock";font.pixelSize:Ui.Tokens.controlPercent;text:Qt.formatDateTime(clock.date,"HH:mm");color:colors.text}
                        }
                    }
                    Rectangle {
                        id:mediaCard;objectName:"control-media";visible:root.quickOverview && !!root.player;Layout.fillWidth:true;implicitHeight:mediaContent.implicitHeight+20;radius:Ui.Tokens.radiusLg;color:colors.surfaceContainer
                        ColumnLayout {
                            id:mediaContent;anchors {left:parent.left;right:parent.right;top:parent.top;margins:10} spacing:Ui.Tokens.spaceXs
                            RowLayout {
                                Image {visible:!!root.player && source!=="";source:root.player ? root.player.trackArtUrl : "";Layout.preferredWidth:40;Layout.preferredHeight:40;sourceSize {width:128;height:128} fillMode:Image.PreserveAspectFit;asynchronous:true;cache:false}
                                Controls.ControlLabel {Layout.fillWidth:true;text:root.player ? root.player.trackTitle+"\n"+root.player.trackArtist : "Нет MPRIS-плееров"}
                            }
                            RowLayout {
                                Controls.ControlButton {text:"Пред.";enabled:!!root.player && root.player.canGoPrevious;onClicked:root.player.previous()}
                                Controls.ControlButton {text:root.player && root.player.isPlaying ? "Пауза" : "Играть";enabled:!!root.player && root.player.canTogglePlaying;onClicked:root.player.togglePlaying()}
                                Controls.ControlButton {text:"След.";enabled:!!root.player && root.player.canGoNext;onClicked:root.player.next()}
                            }
                            Controls.ControlButton {visible:Mpris.players.values.length>1;text:"Плеер: "+(root.player ? root.player.identity : "");onClicked:playerList.visible=!playerList.visible}
                            ColumnLayout {id:playerList;visible:false;Repeater {model:Mpris.players.values;delegate:Controls.ControlButton {required property var modelData;text:modelData.identity;onClicked:root.selectedPlayer=modelData}}}
                        }
                    }
                    Rectangle {
                        id:notificationsCard;objectName:"control-notifications";visible:root.notificationsMode;Layout.fillWidth:true;implicitHeight:notificationsContent.implicitHeight;color:"transparent"
                        ColumnLayout {
                            id:notificationsContent;anchors {left:parent.left;right:parent.right;top:parent.top} spacing:Ui.Tokens.spaceMd
                            RowLayout {
                                Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm
                                Controls.ControlButton {objectName:"control-dnd";text:"Не беспокоить";symbol:"notifications_off";tonal:true;Layout.fillWidth:true;Accessible.name:"Не беспокоить";active:!!root.notifier && root.notifier.enabled && Controls.DesktopState.dnd;enabled:!!root.notifier && root.notifier.enabled;onClicked:root.notifier.toggleDnd();ToolTip.visible:hovered;ToolTip.text:"Не беспокоить"}
                                Controls.ControlButton {objectName:"control-clear-notifications";text:"Очистить";tonal:true;visible:!!root.notifier && root.notifier.history.length>0;enabled:visible;onClicked:root.notifier.clear()}
                            }
                            Controls.ControlLabel {Layout.fillWidth:true;visible:!root.notifier || !root.notifier.enabled;text:"Уведомления обслуживает внешний сервер";color:colors.muted}
                            Controls.ControlButton {visible:!root.notifier || !root.notifier.enabled;text:"Открыть SwayNC";onClicked:Quickshell.execDetached(["swaync-client","-t","-sw"])}
                            ColumnLayout {
                                visible:!!root.notifier && root.notifier.history.length===0;Layout.fillWidth:true;Layout.preferredHeight:Math.max(180,scroll.height-Ui.Tokens.controlChipHeight-Ui.Tokens.spaceMd);spacing:Ui.Tokens.spaceMd
                                Item {Layout.fillHeight:true}
                                Rectangle {Layout.alignment:Qt.AlignHCenter;implicitWidth:64;implicitHeight:64;radius:Ui.Tokens.radiusLg;color:colors.surfaceHigh;Ui.PixelIcon {anchors.centerIn:parent;name:"notifications";size:32;color:colors.accent}}
                                Controls.ControlLabel {objectName:"control-empty-notifications";Layout.fillWidth:true;text:"Нет уведомлений";font.weight:Font.Medium;horizontalAlignment:Text.AlignHCenter}
                                Controls.ControlLabel {Layout.fillWidth:true;text:"Здесь появятся уведомления приложений";font.pixelSize:Ui.Tokens.label;color:colors.muted;horizontalAlignment:Text.AlignHCenter}
                                Item {Layout.fillHeight:true}
                            }
                            Notifications.NotificationCards {Layout.fillWidth:true;manager:root.notifier;visible:!!root.notifier && root.notifier.history.length>0}
                        }
                    }
                    RowLayout {
                        visible:root.quickOverview;Layout.fillWidth:true;spacing:Ui.Tokens.spaceSm
                        Controls.ControlButton {id:settingsEntry;objectName:"control-settings";symbol:"settings";tonal:true;text:"PixelRail";Accessible.name:"Настройки PixelRail";Layout.fillWidth:true;Layout.preferredWidth:1;onClicked:root.selectSection("settings")}
                        Controls.ControlButton {objectName:"control-power";symbol:"power_settings_new";tonal:true;text:"Питание";Accessible.name:"Питание и выход";Layout.fillWidth:true;Layout.preferredWidth:1;onClicked:root.powerRequested()}
                    }
                    Loader {
                        id:settingsLoader;objectName:"control-settings-loader"
                        Layout.fillWidth:true;visible:root.section==="settings"
                        Layout.preferredHeight:item ? item.implicitHeight : 0
                        asynchronous:true
                        function syncPage():void {
                            if(root.section==="settings" && String(source)==="")setSource(Qt.resolvedUrl("SettingsPage.qml"),{controller:root,viewportHeight:scroll.height});
                            else if(root.section!=="settings")source="";
                        }
                        Component.onCompleted:syncPage()
                        Connections {target:root;function onSectionChanged(){settingsLoader.syncPage();}}
                        onLoaded:item.viewportHeight=Qt.binding(()=>scroll.height)
                    }
                    Controls.ControlLabel {Layout.fillWidth:true;visible:root.section==="settings" && settingsLoader.status===Loader.Loading;text:"Загрузка настроек…";color:colors.muted}
                    Controls.ControlLabel {Layout.fillWidth:true;visible:root.section==="settings" && settingsLoader.status===Loader.Error;text:"Не удалось загрузить Settings. Вернитесь назад и проверьте журнал Quickshell.";color:colors.error}
                    Controls.ControlLabel {Layout.fillWidth:true;visible:Controls.DesktopState.error!=="";text:Controls.DesktopState.error;color:colors.error}
                }
            }
            Rectangle {
                id:dragHandle;objectName:"control-resize-handle";Layout.fillWidth:true;implicitHeight:16;radius:Ui.Tokens.radiusXs;color:resizeMouse.containsMouse || resizeMouse.pressed ? colors.selected : colors.surfaceContainer
                Rectangle {anchors.centerIn:parent;width:44;height:4;radius:2;color:colors.outline}
                MouseArea {
                    id:resizeMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.SizeVerCursor
                    property real startY:0;property real startRatio:.5
                    onPressed:{startY=mapToGlobal(mouseX,mouseY).y;startRatio=Controls.DesktopState.heightRatio;}
                    onPositionChanged:if(pressed && root.screen){const delta=mapToGlobal(mouseX,mouseY).y-startY;Controls.DesktopState.heightRatio=Math.max(.3,Math.min(.75,startRatio+delta/root.screen.height));}
                    onReleased:Controls.DesktopState.save()
                }
            }
        }
    }
}
