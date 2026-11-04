#!/usr/bin/env bash
set -euo pipefail
root="$(dirname -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")")"
source_dir="$root/quickshell/native/PixelRail/DBusLease"
build_dir="$root/.cache/native-build"
for tool in python3 pkg-config g++; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool (install it manually)" >&2; exit 1; }
done
pkg-config --exists Qt6Core Qt6Gui Qt6Qml Qt6DBus || { echo 'Matching Qt6 development packages are required.' >&2; exit 1; }
[[ -x /usr/lib/qt6/moc ]] || { echo 'Qt6 moc is missing; see docs/installation.md.' >&2; exit 1; }
mkdir -p "$build_dir"
# Existing Qt/toolchain only. No package installation, no writes outside the repo.
/usr/lib/qt6/moc $(pkg-config --cflags Qt6Qml) "$source_dir/lease.cpp" -o "$build_dir/lease.moc"
/usr/lib/qt6/moc $(pkg-config --cflags Qt6Qml) "$source_dir/backlightwatch.hpp" -o "$build_dir/backlightwatch.moc"
qt_version="$(pkg-config --modversion Qt6Core)"
qt_include="$(pkg-config --variable=includedir Qt6Core)"
g++ -I"$qt_include/QtCore/$qt_version" -I"$qt_include/QtCore/$qt_version/QtCore" -std=c++17 -fPIC -shared "$source_dir/lease.cpp" -I"$build_dir" $(pkg-config --cflags --libs Qt6Qml Qt6DBus Qt6Gui) -o "$build_dir/libpixelraillease.so"
mv "$build_dir/libpixelraillease.so" "$source_dir/libpixelraillease.so"
python3 - "$source_dir" "$qt_version" <<'PY'
import hashlib,json,os,sys,platform
from pathlib import Path
folder=Path(sys.argv[1]); library=folder/'libpixelraillease.so'
temporary=folder/'.build-info.json.tmp'
sources=b''.join(name.encode()+b'\0'+(folder/name).read_bytes() for name in ['lease.cpp','backlightwatch.hpp','qmldir'])
temporary.write_text(json.dumps({'qt':sys.argv[2],'architecture':platform.machine(),'source_sha256':hashlib.sha256(sources).hexdigest(),'sha256':hashlib.sha256(library.read_bytes()).hexdigest()},indent=2)+'\n')
os.replace(temporary,folder/'build-info.json')
PY
echo 'Built PixelRail notification lease for installed Qt.'
