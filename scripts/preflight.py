"""Read-only install requirements. Never installs packages or starts services."""
import json
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys

FEATURES = {
    'native_build_tools': ['g++', 'pkg-config'],
    'wallpaper': ['swaybg'], 'dynamic_colors': ['matugen'],
    'clipboard': ['cliphist', 'wl-copy', 'wl-paste'],
    'audio': ['wpctl', 'pw-dump'], 'brightness': ['brightnessctl'],
    'screenshots': ['grim', 'slurp', 'wl-copy'],
    'fallback_panel': ['waybar'], 'fallback_notifications': ['swaync', 'swaync-client'],
    'session': ['hyprlock', 'hypridle'], 'media_keys': ['playerctl'],
    'network_editor': ['nm-connection-editor'], 'terminal_shortcut': ['kitty'],
}


def version(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4)
        return (result.stdout + result.stderr).strip() if result.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def report(repo):
    errors = []
    if sys.platform != 'linux': errors.append('Linux is required; other platforms are unsupported.')
    if sys.version_info < (3, 10): errors.append('Python >= 3.10 is required.')
    for name in ['bash', 'python3', 'Hyprland', 'busctl']:
        if not shutil.which(name): errors.append('Missing required executable: ' + name)
    qs = shutil.which('qs') or shutil.which('quickshell')
    qs_version = version([qs, '--version']) if qs else ''
    hypr_version = version(['Hyprland', '--version']) if shutil.which('Hyprland') else ''
    if not re.search(r'Quickshell 0\.3\.2(?:\s|$)', qs_version): errors.append('Quickshell 0.3.2 is required by the native bridge; rebuild/revalidate before using another version.')
    if not re.search(r'Hyprland (?:v)?0\.57\.', hypr_version): errors.append('Validated compositor API: Hyprland 0.57.x with Lua configuration.')
    native = repo / 'quickshell/native/PixelRail/DBusLease/libpixelraillease.so'
    stamp = native.with_name('build-info.json')
    if not native.is_file() or native.stat().st_size == 0:
        errors.append('Native plugin missing: run ./scripts/build-native.sh on this machine.')
    elif stamp.is_file():
        import hashlib
        try:
            data = json.loads(stamp.read_text())
            qt = version(['pkg-config', '--modversion', 'Qt6Core'])
            sources=b''.join(name.encode()+b'\0'+(native.parent/name).read_bytes() for name in ['lease.cpp','backlightwatch.hpp','qmldir'])
            if data['sha256'] != hashlib.sha256(native.read_bytes()).hexdigest() or not qt or data['qt'] != qt or data.get('source_sha256')!=hashlib.sha256(sources).hexdigest() or data.get('architecture')!=platform.machine():
                errors.append('Native plugin / Qt build stamp mismatch: rebuild with ./scripts/build-native.sh.')
        except (OSError, ValueError, KeyError): errors.append('Invalid native build-info.json; rebuild locally.')
    else:
        errors.append('Native build stamp missing: rebuild with ./scripts/build-native.sh before activation.')
    optional = {feature: [name for name in commands if not shutil.which(name)] for feature, commands in FEATURES.items()}
    return {'supported_platform': 'Arch Linux, Hyprland 0.57.x Lua, Quickshell 0.3.2',
            'errors': errors, 'missing_optional': {name: missing for name, missing in optional.items() if missing},
            'quickshell': qs_version, 'hyprland': hypr_version.splitlines()[0] if hypr_version else '',
            'note': 'NetworkManager/BlueZ/PipeWire/UPower services and actual hardware need session testing. No package/service changes performed.'}


def explain(data):
    print('Validated platform:', data['supported_platform'])
    for error in data['errors']: print('REQUIRED:', error)
    for name, missing in data['missing_optional'].items(): print('OPTIONAL:', name, '— missing', ', '.join(missing))
    print(data['note'])
