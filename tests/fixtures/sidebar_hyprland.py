"""Event socket and request socket fixture for native Quickshell.Hyprland."""
import json
import re
from pathlib import Path
import socket
import threading
import time

class Hyprland:
    def __init__(self,runtime):
        directory=Path(runtime)/'hypr/sidebar-test';directory.mkdir(parents=True)
        self.requests=[];self.events=[];self.closed=False;self.fail_next=False
        self.keyboards=[{'name':'thinkpad','main':True,'active_keymap':'English (US)'},{'name':'usb','main':False,'active_keymap':'Russian'}]
        self.monitor={'id':0,'name':'eDP-1','width':1366,'height':768,'scale':1,'x':0,'y':0,
            'focused':True,'activeWorkspace':{'id':1,'name':'1'},'specialWorkspace':{'id':0,'name':''}}
        self.workspaces=[{'id':1,'name':'1','monitor':'eDP-1','monitorID':0,'windows':1,'hasfullscreen':False},
            {'id':3,'name':'3','monitor':'eDP-1','monitorID':0,'windows':2,'hasfullscreen':False}]
        self.clients=[self.window('0xaaa','Chrome'),self.window('0xbbb','Kitty A',workspace=3),self.window('0xbee','Kitty B',workspace=3),self.window('0xccc','Shell','org.quickshell')]
        self.workspaces.append(dict(id=9,name='9',monitor='DP-1',monitorID=1,windows=1,hasfullscreen=False))
        foreign=self.window('0xfff','Other monitor',workspace=9);foreign['monitor']=1;self.clients.append(foreign)
        self.secondary=dict(self.monitor,id=1,name='DP-1',x=1366,focused=False,activeWorkspace={'id':9,'name':'9'})
        self.active=self.clients[0]
        self.listeners=[]
        for name,handler in (('.socket.sock',self.request),('.socket2.sock',self.event)):
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);listener.bind(str(directory/name));listener.listen();listener.settimeout(.1)
            self.listeners.append(listener)
            threading.Thread(target=self.accept,args=(listener,handler),daemon=True).start()
    @staticmethod
    def window(address,title,app='pixelrail-fixture-app',workspace=1):
        return {'fixture':True,'address':address,'mapped':True,'hidden':False,'class':app,'initialClass':app,'title':title,
            'initialTitle':title,'workspace':{'id':workspace,'name':str(workspace)},'monitor':0,'pid':100,'floating':False,'focusHistoryID':0}
    def accept(self,listener,handler):
        while not self.closed:
            try:connection,_=listener.accept()
            except (TimeoutError,OSError):continue
            threading.Thread(target=handler,args=(connection,),daemon=True).start()
    def request(self,connection):
        with connection:
            try:
                command=connection.recv(65536).decode().removeprefix('/');self.requests.append(command)
                if command.startswith('switchxkblayout '):
                    _,name,target=command.split(' ')
                    keyboard=next(k for k in self.keyboards if k['name']==name)
                    keyboard['active_keymap']='Russian' if keyboard['active_keymap'].startswith('English') else 'English (US)'
                    self.emit('activelayout>>'+name+','+keyboard['active_keymap']);connection.sendall(b'ok');return
                if command.startswith('eval '):
                    self.dispatch(command,connection);return
                key=command.removeprefix('j/')
                value={'devices':{'keyboards':self.keyboards},'status':{'configProvider':'lua','backend':'wayland'},'monitors':[self.monitor,self.secondary],'workspaces':self.workspaces,'clients':self.clients,
                    'activeworkspace':self.monitor['activeWorkspace'],'activewindow':self.active,
                    'version':{'version':'0.57.0','tag':'v0.57.0'}}.get(key)
                connection.sendall((json.dumps(value) if value is not None else 'ok').encode())
            except OSError:pass
    def dispatch(self,command,connection):
        if self.fail_next:
            self.fail_next=False;connection.sendall(b'error: rejected test dispatcher');return
        workspace=re.search(r'hl\.dispatch\(hl\.dsp\.focus\(\{ workspace = "([0-9]+)" \}\)\)',command)
        window=re.search(r'hl\.dispatch\(hl\.dsp\.focus\(\{ window = "address:(0x[0-9a-f]+)" \}\)\)',command)
        if workspace:
            ident=int(workspace[1]);name=str(ident)
            if not any(w['id']==ident for w in self.workspaces):
                self.workspaces.append(dict(id=ident,name=name,monitor='eDP-1',monitorID=0,windows=0,hasfullscreen=False))
                self.emit('createworkspacev2>>'+name+','+name)
            self.monitor['activeWorkspace']={'id':ident,'name':name}
            self.emit('workspacev2>>'+name+','+name)
            self.emit('focusedmonv2>>eDP-1,'+name)
            connection.sendall(b'ok')
        elif window:
            match=next((w for w in self.clients if w['address']==window[1]),None)
            if not match:connection.sendall(b'error: window closed');return
            self.active=match;self.emit('activewindowv2>>'+window[1].removeprefix('0x'));connection.sendall(b'ok')
        else:connection.sendall(b'error: unsupported Lua dispatcher')
    def event(self,connection):self.events.append(connection)
    def emit(self,text):
        deadline=time.monotonic()+2
        while not self.events and time.monotonic()<deadline:time.sleep(.01)
        assert self.events,'native Hyprland did not subscribe'
        for connection in list(self.events):
            try:connection.sendall((text+'\n').encode())
            except OSError:self.events.remove(connection)
    def close(self):
        self.closed=True
        for connection in self.events+self.listeners:connection.close()
