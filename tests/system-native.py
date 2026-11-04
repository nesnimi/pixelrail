"""Build/test the real read-only uevent filter; no synthetic kernel events sent."""
from pathlib import Path
import shlex
import subprocess
import tempfile
root=Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp);source=base/'backlight-test.cpp'
    source.write_text('''#include "backlightwatch.hpp"
#include <cassert>
int main(){
 auto make=[](const char *data,int size){return QByteArray(data,size);};
 const char hotkey[]="change@/devices/test\\0SUBSYSTEM=backlight\\0SOURCE=hotkey\\0";
 const char sysfs[]="change@/devices/test\\0SUBSYSTEM=backlight\\0SOURCE=sysfs\\0";
 const char other[]="change@/devices/test\\0SUBSYSTEM=leds\\0SOURCE=hotkey\\0";
 const char suffix[]="change@/devices/test\\0X_SUBSYSTEM=backlight\\0SOURCE=hotkey\\0";
 assert(BacklightWatch::isBacklightEvent(make(hotkey,sizeof(hotkey))));
 assert(BacklightWatch::isHardwareEvent(make(hotkey,sizeof(hotkey))));
 assert(BacklightWatch::isBacklightEvent(make(sysfs,sizeof(sysfs))));
 assert(!BacklightWatch::isHardwareEvent(make(sysfs,sizeof(sysfs))));
 assert(!BacklightWatch::isHardwareEvent(make(other,sizeof(other))));
 assert(!BacklightWatch::isBacklightEvent(make(suffix,sizeof(suffix))));
}
''')
    flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','Qt6Core'],text=True))
    subprocess.run(['g++','-std=c++17','-fPIC','-I'+str(root/'quickshell/native/PixelRail/DBusLease'),str(source),'-o',str(base/'test'),*flags],check=True)
    subprocess.run([str(base/'test')],check=True)
print('Native backlight uevent filter: kernel subsystem/source parsing, no sysfs writes or polling: PASS')
