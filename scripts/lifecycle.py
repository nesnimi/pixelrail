#!/usr/bin/env python3
"""Serialize PixelRail release transitions; never kill by executable name."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

class LifecycleError(RuntimeError):
    pass

@contextmanager
def locked(home):
    # Common across release directories, scoped to this home and Wayland session.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', str(home/'.cache')))
    runtime.mkdir(parents=True, exist_ok=True)
    display = os.environ.get('WAYLAND_DISPLAY', '')
    endpoint = str((runtime/display).resolve()) if display else 'offline'
    identity = str(home.resolve()) + '\0' + endpoint
    path = runtime / ('pixelrail-lifecycle-' + hashlib.sha256(identity.encode()).hexdigest()[:24] + '.lock')
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def owned_configs(home, source=None):
    configs = set()
    if source is not None:
        configs.add(str((source/'quickshell/shell.qml').resolve()))
    releases = (home/'.local/share/pixelrail/releases').resolve()
    for path in (home/'.local/state/pixelrail/deployments').glob('*/manifest.json'):
        try:
            data = json.loads(path.read_text())
            release = Path(data['release']).resolve()
            if Path(data['home']).resolve() != home.resolve() or release.parent != releases:
                continue
            configs.add(str((release/'quickshell/shell.qml').resolve()))
            for field in ('source_config', 'previous_config'):
                if data.get(field): configs.add(str(Path(data[field]).resolve()))
        except (OSError, ValueError, KeyError, TypeError):
            continue  # An unrecognized/corrupt manifest never broadens process ownership.
    return configs

class Shell:
    def __init__(self, configs):
        self.configs = set(configs)
        self.binary = shutil.which('qs') or shutil.which('quickshell')
        if not self.binary: raise LifecycleError('Quickshell не найден; прежний экземпляр сохранён')
        if not os.environ.get('WAYLAND_DISPLAY'):
            raise LifecycleError('Нет Wayland-сеанса; для установки без запуска используйте --no-start')

    def call(self, *arguments, timeout=3):
        try:
            return subprocess.run([self.binary,*arguments], capture_output=True, text=True,
                                  timeout=timeout, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            raise LifecycleError('Quickshell: ' + str(error)) from error

    def instances(self):
        try:
            # Quickshell 0.3.2 emits a plain-text sentinel even with --json.
            output = self.call('list','--all','--json')
            rows = [] if output in ('', 'No running instances.') else json.loads(output)
            if not isinstance(rows, list): raise ValueError('expected instance list')
            return [row for row in rows if isinstance(row, dict)
                    and isinstance(row.get('pid'), int) and isinstance(row.get('id'), str)
                    and isinstance(row.get('config_path'), str)
                    and str(Path(row['config_path']).resolve()) in self.configs]
        except (ValueError, KeyError) as error:
            raise LifecycleError('Не удалось разобрать список Quickshell; остановка отменена') from error

    @staticmethod
    def key(row):
        return row['id'], row['pid'], str(Path(row['config_path']).resolve())

    def ready(self, row):
        try:
            status = self.call('ipc','--pid',str(row['pid']),'call','menus','status', timeout=1)
            return status in {'unloaded','keys','clipboard','command','windows','controls','power','wallpaper','media','emoji'}
        except LifecycleError:
            return False

    def stop(self, row):
        # Revalidate ID, PID and config against the live registry immediately before stopping.
        identity = self.key(row)
        if not any(self.key(current) == identity for current in self.instances()): return
        self.call('kill','--id',row['id'])
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if not any(self.key(current) == identity for current in self.instances()): return
            time.sleep(.05)
        raise LifecycleError('PixelRail не завершился: ' + row['id'] + '; принудительный kill не выполнялся')

    def prepare(self, config):
        config = str(Path(config).resolve())
        if config not in self.configs or not Path(config).is_file():
            raise LifecycleError('Неизвестный или отсутствующий PixelRail QML: ' + config)
        before = {self.key(row) for row in self.instances()}
        candidates = [row for row in self.instances() if self.key(row)[2] == config]
        for row in candidates:
            if self.ready(row): return row, []
        try:
            self.call('--no-duplicate','--daemonize','-p',config, timeout=8)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                for row in self.instances():
                    if self.key(row)[2] == config and self.ready(row):
                        created = [r for r in self.instances() if self.key(r) not in before and self.key(r)[2] == config]
                        return row, created
                time.sleep(.1)
            raise LifecycleError('Новый PixelRail не подтвердил готовность IPC')
        except LifecycleError:
            # Only processes created by this attempt. Never touch a previously running release.
            for row in self.instances():
                if self.key(row) not in before and self.key(row)[2] == config: self.stop(row)
            raise

    def retire(self, keep=None):
        if keep is not None and not self.ready(keep):
            raise LifecycleError('IPC нового релиза недоступен; старые экземпляры сохранены')
        for row in self.instances():
            if keep is None or self.key(row) != self.key(keep):
                if keep is not None and not self.ready(keep):
                    raise LifecycleError('Новый релиз потерял IPC; оставшиеся старые экземпляры сохранены')
                self.stop(row)


def main():
    config = Path(sys.argv[1]).resolve()
    home = Path.home().resolve()
    try:
        with locked(home):
            source = Path(__file__).resolve().parent.parent
            configs = owned_configs(home, source)
            installed = home/'.local/bin/pixelrail-shell'
            if (source.parent == (home/'.local/share/pixelrail/releases').resolve()
                    and installed.is_symlink() and not os.environ.get('PIXELRAIL_QML')):
                selected = (installed.resolve().parent.parent/'quickshell/shell.qml').resolve()
                if str(selected) in configs and selected.is_file(): config = selected
            configs.add(str(config))  # Explicit PIXELRAIL_QML is owned only by this invocation.
            shell = Shell(configs)
            keep, _ = shell.prepare(config)
            shell.retire(keep)
            from panel import reconcile
            reconcile()
            from notifications import reconcile as reconcile_notifications
            reconcile_notifications()
    except (OSError, LifecycleError) as error:
        print('PixelRail: '+str(error),file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
