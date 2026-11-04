import os
from pathlib import Path
import subprocess
import tempfile

root = Path.cwd()
def execute(script, home, *args, success=True):
    result = subprocess.run([str(root/'scripts'/script),'--target-home',str(home),'--no-start',*args],capture_output=True,text=True,env=dict(os.environ,XDG_RUNTIME_DIR=str(home/'.test-runtime')))
    assert (result.returncode == 0) == success, result.stdout+result.stderr
    return result
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    home = Path(tmp)/'home'; home.mkdir()
    hypr = home/'.config/hypr'; hypr.mkdir(parents=True)
    main = hypr/'hyprland.lua'; source=(root/'hypr/hyprland.lua').read_text(); main.write_text(source)
    bin_dir=home/'.local/bin'; bin_dir.mkdir(parents=True)
    original=bin_dir/'pixelrail-keys'; original.symlink_to('/fixture/old-keys')
    regular=bin_dir/'pixelrail-power'; regular.write_text('original power'); regular.chmod(0o750)
    bar=home/'.config/waybar/config.jsonc'; bar.parent.mkdir(); bar.write_text('{"on-click":"rofi -show drun"}')
    themes=home/'.config/rofi'; themes.mkdir()
    (themes/'custom.rasi').write_text('user theme')
    theme=home/'.config/pixelrail/theme.json';theme.parent.mkdir();theme.write_text('{"mode":"light","accent":"#AABBCC","iconStyle":"themed","animations":false,"future":"keep"}')
    cache=home/'.cache/pixelrail/theme/palette.json';cache.parent.mkdir(parents=True);cache.write_text('theme cache sentinel')
    panel=home/'.config/pixelrail/panel.json';panel.write_text('{"mode":"sidebar","monitor":"eDP-1"}')
    desktop=home/'.config/pixelrail/desktop.json';desktop.write_text('{"heightRatio":0.63,"dnd":true}')
    notifications=home/'.config/pixelrail/notifications.json';notifications.write_text('{"mode":"pixelrail"}')
    saved_desktop=desktop.read_bytes();saved_notifications=notifications.read_bytes()
    saved_panel=panel.read_bytes()
    saved_theme=theme.read_bytes();saved_cache=cache.read_bytes()
    usage=home/'.local/state/pixelrail/launcher.json';usage.parent.mkdir(parents=True,exist_ok=True)
    usage.write_text('{"version":1,"counts":{"user-app":12}}');saved_usage=usage.read_bytes()
    initial_main=main.read_bytes()
    execute('deploy.sh',home)
    assert not (home/'.local/share/pixelrail/releases').exists()
    execute('deploy.sh',home,'--apply','--accept-config-changes')
    assert sorted(p.name for p in themes.iterdir()) == ['custom.rasi']
    assert (themes/'custom.rasi').read_text() == 'user theme'
    assert main.read_bytes()==initial_main
    assert theme.read_bytes()==saved_theme and cache.read_bytes()==saved_cache
    assert panel.read_bytes()==saved_panel
    assert usage.read_bytes()==saved_usage
    assert desktop.read_bytes()==saved_desktop and notifications.read_bytes()==saved_notifications
    assert original.is_symlink() and original.resolve().exists()
    assert 'pixelrail-launcher' in bar.read_text()
    manifests=list((home/'.local/state/pixelrail/deployments').glob('*/manifest.json')); assert len(manifests)==1
    # Deploy is non-destructive to the approved launcher; releases are immutable copies.
    release_launcher=original.resolve().parents[1]/'quickshell/modules/launcher/Launcher.qml'
    assert release_launcher.read_bytes()==(root/'quickshell/modules/launcher/Launcher.qml').read_bytes()
    release = release_launcher.parents[3]
    assert not list(release.rglob('*.rasi'))
    assert (bin_dir/'pixelrail-shell-error').resolve().is_file()
    assert (bin_dir/'pixelrail-theme').resolve().is_file()
    assert (release/'scripts/material_you.py').is_file()
    assert (release/'scripts/launcher_entries.py').read_bytes()==(root/'scripts/launcher_entries.py').read_bytes()
    assert (bin_dir/'pixelrail-control').resolve().is_file()
    assert (bin_dir/'pixelrail-power-audit').resolve().is_file()
    assert (bin_dir/'pixelrail-benchmark').resolve().is_file()
    assert (bin_dir/'pixelrail-system').resolve().is_file()
    assert (release/'quickshell/modules/system/SystemState.qml').is_file()
    assert (release/'quickshell/modules/system/SystemOsd.qml').is_file()
    assert (release/'quickshell/modules/system/ScreenshotState.qml').is_file()
    for relative in ('ui/Keycap.qml','modules/control/SettingsCard.qml','modules/control/IconStylePicker.qml'):
        assert (release/'quickshell'/relative).is_file(),relative
    assert (release/'quickshell/assets/symbols/light_mode.svg').is_file()
    assert (release/'quickshell/assets/symbols/wifi.svg').read_bytes()==(root/'quickshell/assets/symbols/wifi.svg').read_bytes()
    assert (release/'scripts/screenshot.py').is_file()
    assert (bin_dir/'pixelrail-settings').resolve().is_file()
    assert (home/'.local/share/applications/pixelrail-settings.desktop').is_file()
    assert 'Exec="'+str(bin_dir/'pixelrail-settings')+'"' in (home/'.local/share/applications/pixelrail-settings.desktop').read_text()
    for asset_file in ('ui/PixelIcon.qml','ui/PixelAppIcon.qml','ui/Tokens.qml','modules/control/SettingsPage.qml','assets/fonts/Roboto.ttf','assets/fonts/OFL.txt','assets/symbols/LICENSE'):
        assert (release/'quickshell'/asset_file).is_file(),asset_file
    assert (release/'scripts/benchmark.py').is_file()
    assert (release/'scripts/power_audit.py').is_file()
    assert not (release/'extras/power/epp_helper.py').exists()
    assert not (bin_dir/'pixelrail-epp').exists()
    assert (bin_dir/'pixelrail-notifications').resolve().is_file()
    assert (release/'quickshell/native/PixelRail/DBusLease/libpixelraillease.so').is_file()
    assert (release/'quickshell/theme/ThemeManager.qml').is_file()
    # A deployed entrypoint must explain recovery even with no Qt/Quickshell installed.
    isolated = home/'test-bin'; isolated.mkdir()
    for name in ('bash','dirname','readlink'):
        (isolated/name).symlink_to('/usr/bin/'+name)
    environment = dict(os.environ, HOME=str(home), PATH=str(isolated), XDG_RUNTIME_DIR=str(home))
    environment.pop('PIXELRAIL_QML', None)
    for script in ('pixelrail-menu','pixelrail-launcher','pixelrail-shell','pixelrail-launcher-rofi'):
        failure = subprocess.run([str(bin_dir/script)],env=environment,capture_output=True,text=True)
        assert failure.returncode == 1 and 'Super+Return' in failure.stderr
        assert str(release/'scripts/pixelrail-shell') in failure.stderr

    execute('rollback.sh',home)
    assert original.resolve().exists()
    regular.unlink(); regular.write_text('user edit')
    failure=execute('rollback.sh',home,'--apply',success=False)
    assert 'Changed since deployment' in failure.stderr
    assert original.resolve().exists()  # no partial rollback before conflict rejection
    regular.unlink()
    import json
    manifest=json.loads(manifests[0].read_text())
    target=next(record['after']['symlink'] for record in manifest['files'] if record['path']=='.local/bin/pixelrail-power')
    regular.symlink_to(target)
    execute('rollback.sh',home,'--apply')
    assert os.readlink(original)=='/fixture/old-keys'
    assert regular.read_text()=='original power' and regular.stat().st_mode & 0o777 == 0o750
    assert main.read_bytes()==initial_main
    assert theme.read_bytes()==saved_theme and cache.read_bytes()==saved_cache
    assert usage.read_bytes()==saved_usage
    assert panel.read_bytes()==saved_panel
    assert desktop.read_bytes()==saved_desktop and notifications.read_bytes()==saved_notifications
    assert bar.read_text()=='{"on-click":"rofi -show drun"}'
    assert not (bin_dir/'pixelrail-menu').exists()
    assert not (bin_dir/'pixelrail-power-audit').exists()
    assert not (bin_dir/'pixelrail-benchmark').exists()
    assert not (bin_dir/'pixelrail-system').exists()
    execute('rollback.sh',home,success=False)
    # Fresh installation, hook creation, repeated deployment and layered rollback.
    fresh=Path(tmp)/'fresh'; fresh.mkdir()
    execute('deploy.sh',fresh,'--apply')
    assert not (fresh/'.config/rofi').exists()
    assert (fresh/'.config/waybar/config.jsonc').read_bytes()==(root/'waybar/config.jsonc').read_bytes()
    assert not (fresh/'.config/pixelrail/panel.json').exists()
    assert (fresh/'.local/bin/pixelrail-panel').resolve().is_file()
    main_fresh=fresh/'.config/hypr/hyprland.lua'; assert main_fresh.read_text()==source
    execute('deploy.sh',fresh,'--apply')
    execute('rollback.sh',fresh,'--apply')
    assert (fresh/'.local/bin/pixelrail-menu').resolve().exists()
    execute('rollback.sh',fresh,'--apply')
    assert not main_fresh.exists()
    # Refuse parent symlinks escaping the explicit target home.
    escape=Path(tmp)/'escape'; escape.mkdir(); external=Path(tmp)/'external'; external.mkdir()
    (escape/'.config').symlink_to(external)
    execute('deploy.sh',escape,'--apply',success=False)
    assert not list(external.iterdir())
print('Deploy/rollback: dry run, original files/symlinks/modes, conflicts, fresh install, repeated deploy, external symlinks passed')
