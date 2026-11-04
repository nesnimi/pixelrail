#!/usr/bin/env python3
"""Explicit, backed-up per-user deployment. Activates PixelRail only; never reloads Hyprland or system services."""
import argparse
import difflib
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid
from lifecycle import LifecycleError, Shell, locked, owned_configs

REPO = Path(__file__).resolve().parent.parent

def token(path):
    if path.is_symlink(): return {'symlink': os.readlink(path)}
    if path.is_file(): return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': path.stat().st_mode & 0o777}
    if path.exists(): raise ValueError(f'Not a regular file/symlink: {path}')
    return None

def safe_parent(home, path):
    if not path.parent.resolve().is_relative_to(home):
        raise ValueError(f'Parent symlink escapes target home; review manually: {path}')

def replace(path, source=None, link=None, content=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.pixelrail-' + uuid.uuid4().hex)
    try:
        if link is not None: temporary.symlink_to(link)
        elif source is not None:
            source=Path(source)
            if source.is_symlink():temporary.symlink_to(os.readlink(source))
            else:
                descriptor=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
                with os.fdopen(descriptor,'wb') as output,source.open('rb') as original:shutil.copyfileobj(original,output)
                shutil.copystat(source,temporary,follow_symlinks=False)
        else:
            mode=path.stat().st_mode & 0o777 if path.is_file() else 0o644
            descriptor=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            with os.fdopen(descriptor,'w') as output:
                os.fchmod(output.fileno(),mode);output.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists() or temporary.is_symlink(): temporary.unlink()

def restore(home, backup, record):
    destination = home / record['path']
    safe_parent(home, destination)
    if record['before'] is None:
        if destination.exists() or destination.is_symlink(): destination.unlink()
    else:
        replace(destination, source=backup / record['backup'])

def plan(home, release):
    actions = []
    entry=(REPO/"share/applications/pixelrail-settings.desktop").read_text()
    executable=str(home/".local/bin/pixelrail-settings")
    # Desktop Entry quoting, not shell interpolation; no dependency on login PATH.
    quoted='"'+''.join(chr(92)*4 if c==chr(92) else chr(92)*2+c if c in '"`$' else '%%' if c=='%' else c for c in executable)+'"'
    entry=entry.replace("\nExec=pixelrail-settings\n","\nExec="+quoted+"\n").replace("\nTryExec=pixelrail-settings\n","\nTryExec="+executable.replace(chr(92),chr(92)*2)+"\n")

    for script in sorted((REPO / 'scripts').glob('pixelrail-*')):
        if script.is_file():
            actions.append((Path('.local/bin') / script.name, {'link': str(release/'scripts'/script.name)}))
    for name in ('pixelrail-end4-keys.lua', 'pixelrail-super-tap.lua'):
        actions.append((Path('.config/hypr')/name, {'link': str(release/'hypr'/name)}))
    main_path = home / '.config/hypr/hyprland.lua'
    if main_path.exists():
        source = main_path.read_text()
        modified = source
        # Existing PixelRail already has these hooks: leave its main config untouched.
        if 'pixelrail-end4-keys.lua' not in source:
            modified += '\n-- PixelRail managed keybind entrypoint\ndofile((os.getenv("HOME") or "") .. "/.config/hypr/pixelrail-end4-keys.lua")\n'
        if 'pixelrail-start' not in source:
            modified += '\n-- PixelRail managed session entrypoint\nhl.on("hyprland.start", function()\n  local command = string.format("%q", (os.getenv("HOME") or "") .. "/.local/bin/pixelrail-start")\n  command = command:gsub("%$", "\\\\$"):gsub("`", "\\\\`")\n  hl.exec_cmd(command)\nend)\n'
        if modified != source: actions.append((Path('.config/hypr/hyprland.lua'), {'content': modified}))
    else:
        actions.append((Path('.config/hypr/hyprland.lua'), {'content': (REPO/'hypr/hyprland.lua').read_text()}))
    bar = home / '.config/waybar/config.jsonc'
    if bar.is_file():
        source = bar.read_text()
        modified = source.replace('"rofi -show drun"', '"$HOME/.local/bin/pixelrail-launcher"').replace('Приложения · Super+D', 'Приложения · Super')
        if modified != source: actions.append((Path('.config/waybar/config.jsonc'), {'content': modified}))
    for name in ('config.jsonc','style.css'):
        relative=Path('.config/waybar')/name
        if not (home/relative).exists(): actions.append((relative, {'source':REPO/'waybar'/name}))
    actions.append((Path(".local/share/applications/pixelrail-settings.desktop"), {"content":entry}))
    for relative, _ in actions:
        safe_parent(home, home/relative)
        token(home/relative)
    return actions

def managed_files(home):
    """Only an exact, unedited manifest result is safe to update automatically."""
    owned = {}
    for path in sorted((home/'.local/state/pixelrail/deployments').glob('*/manifest.json')):
        try:
            data = json.loads(path.read_text())
            if data.get('home') != str(home) or not data.get('complete') or data.get('rolled_back'): continue
            for record in data['files']:
                validate_record(record);safe_parent(home,home/record['path'])
                current = token(home/record['path'])
                if current != record.get('after'): continue
                if current and 'symlink' in current:
                    target = (home/record['path']).resolve()
                    expected = record.get('target_sha256')
                    if not expected or not target.is_relative_to(home/'.local/share/pixelrail/releases') or not target.is_file(): continue
                    if hashlib.sha256(target.read_bytes()).hexdigest() != expected: continue
                owned[record['path']] = current
        except (OSError, ValueError, KeyError, TypeError): continue
    return owned


def conflicts(home, actions):
    owned = managed_files(home)
    found = [str(path) for path, _ in actions if token(home/path) is not None and str(path) not in owned]
    if not (home/'.config/hypr/hyprland.lua').exists() and (home/'.config/hypr/hyprland.conf').exists():
        found.append('.config/hypr/hyprland.conf (would be shadowed by the Lua sample)')
    return found


def deploy(home, apply, no_start=False, accept_changes=False, show_diff=False):
    # Fail before backups/links/process changes, including an offline installation.
    native=REPO/'quickshell/native/PixelRail/DBusLease/libpixelraillease.so'
    if apply and (not native.is_file() or native.stat().st_size==0):
        raise ValueError('Native plugin отсутствует: сначала ./scripts/build-native.sh; установка не изменена')
    deployment = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    release = home / '.local/share/pixelrail/releases' / deployment
    backup = home / '.local/state/pixelrail/deployments' / deployment
    safe_parent(home, release); safe_parent(home, backup)
    actions = plan(home, release)
    changed_foreign = conflicts(home, actions)
    print('Target home:', home)
    for path, _ in actions: print('Install:', path)
    for path in changed_foreign: print('REVIEW existing/unverifiable configuration:', path)
    if show_diff:
        for path, options in actions:
            destination = home/path
            if not destination.is_file(): continue
            try:
                old = destination.read_text()
                source = REPO/Path(options['link']).relative_to(release) if 'link' in options else options.get('source')
                new = options['content'] if 'content' in options else source.read_text()
                print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(path),tofile=str(path)+' (PixelRail)')),end='')
            except (OSError, UnicodeError, ValueError): pass
    if not apply:
        print('Dry run. Pass --apply to install; no processes will be started or reloaded.')
        return
    if changed_foreign and not accept_changes:
        raise ValueError('Existing dotfiles/legacy links preserved. Review --diff, then explicitly pass --accept-config-changes if these exact replacements are intended.')
    if not no_start:
        from preflight import report, explain
        requirements = report(REPO); explain(requirements)
        if requirements['errors']: raise ValueError('Required checks failed; no files or processes changed.')
    backup.mkdir(parents=True, mode=0o700)
    manifest = {'home':str(home), 'release':str(release), 'complete':False, 'rolled_back':False, 'files':[], 'source_config':str((REPO/'quickshell/shell.qml').resolve()), 'previous_config':None, 'created_ns':time.time_ns()}
    previous = home/'.local/bin/pixelrail-shell'
    if previous.is_symlink():
        previous_config = previous.resolve().parent.parent/'quickshell/shell.qml'
        if str(previous_config.resolve()) in owned_configs(home, REPO):
            manifest['previous_config'] = str(previous_config.resolve())
    for index, (relative, _) in enumerate(actions):
        before = token(home/relative)
        name = str(index)
        if before is not None: shutil.copy2(home/relative, backup/name, follow_symlinks=False)
        manifest['files'].append({'path':str(relative), 'before':before, 'backup':name})
    manifest_path = backup/'manifest.json'
    replace(manifest_path, content=json.dumps(manifest, indent=2))
    changed = []
    runtime = None
    created = []
    keep = None
    try:
        release.mkdir(parents=True)
        for directory in ('scripts','quickshell','hypr'):
            shutil.copytree(REPO/directory, release/directory, ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','.cache','.env','.env.*','*.bak','*.backup','*.old','*.swp','*.tmp','*.part','.DS_Store'))
        for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
            if (REPO/name).is_file():shutil.copy2(REPO/name,release/name)
        if not no_start:
            runtime = Shell(owned_configs(home, REPO))
            keep, created = runtime.prepare(release/'quickshell/shell.qml')
        for (relative, options), record in zip(actions, manifest['files']):
            replace(home/relative, **options)
            changed.append(record)
            record['after'] = token(home/relative)
            if 'link' in options and (home/relative).is_file():
                record['target_sha256'] = hashlib.sha256((home/relative).read_bytes()).hexdigest()
        manifest['complete'] = True
        replace(manifest_path, content=json.dumps(manifest, indent=2))
    except BaseException:
        for record in reversed(changed): restore(home, backup, record)
        if runtime:
            for row in created: runtime.stop(row)
        manifest['complete'] = False
        manifest['failed'] = True
        replace(manifest_path, content=json.dumps(manifest, indent=2))
        raise
    print('Backup:', backup)
    if runtime:
        try:
            runtime.retire(keep)
        except LifecycleError as error:
            manifest['runtime_error'] = str(error)
            replace(manifest_path, content=json.dumps(manifest, indent=2))
            raise LifecycleError('Файлы установлены, backup сохранён, но очистка старых экземпляров не завершена: ' + str(error)) from error
    if runtime:
        from panel import reconcile
        reconcile()
        from notifications import reconcile as reconcile_notifications
        reconcile_notifications()
    print('Installed. PixelRail activated.' if runtime else 'Installed without process changes (--no-start).')
    print('Rollback ID:', deployment)

def rollback(home, deployment, apply, no_start=False):
    directory = home/'.local/state/pixelrail/deployments'
    safe_parent(home, directory/'placeholder')
    candidates = []
    for path in sorted(directory.glob('*/manifest.json')):
        manifest = json.loads(path.read_text())
        if manifest.get('complete') and not manifest.get('rolled_back'): candidates.append((path,manifest))
    if deployment:
        if Path(deployment).name != deployment: raise ValueError('Expected deployment ID, not a path')
        candidates = [(path,data) for path,data in candidates if path.parent.name == deployment]
    if not candidates: raise ValueError('No matching active deployment backup')
    candidates.sort(key=lambda entry: entry[1].get('created_ns', entry[0].stat().st_mtime_ns))
    manifest_path, manifest = candidates[-1]
    if Path(manifest['home']) != home: raise ValueError('Backup belongs to another target home')
    # Validate everything before the first mutation. Do not overwrite later user edits.
    for record in manifest['files']:
        validate_record(record)
        destination = home/record['path']; safe_parent(home,destination)
        if token(destination) != record['after']:
            raise ValueError(f'Changed since deployment; preserve/reconcile manually: {destination}')
        if record.get('target_sha256') and (not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest()!=record['target_sha256']):
            raise ValueError('Managed target edited; preserve/reconcile manually: '+str(destination))
        if record['before'] is not None and token(manifest_path.parent/record['backup']) != record['before']:
            raise ValueError('Backup was changed: '+record['path'])
    print('Restore:', manifest_path.parent.name)
    for record in manifest['files']: print('Restore file:', record['path'])
    if not apply:
        print('Dry run. Pass --apply to restore. No processes will be started or reloaded.')
        return
    runtime = None
    keep = None
    created = []
    if not no_start:
        runtime = Shell(owned_configs(home, REPO))
        previous_config = manifest.get('previous_config')
        if 'previous_config' not in manifest:  # Backups made before lifecycle support.
            record = next((row for row in manifest['files'] if row['path'] == '.local/bin/pixelrail-shell'), None)
            target = (record or {}).get('before') or {}
            if target.get('symlink'):
                old_script = (home/'.local/bin'/target['symlink']).resolve()
                candidate = str((old_script.parent.parent/'quickshell/shell.qml').resolve())
                if candidate in runtime.configs: previous_config = candidate
        if previous_config:
            keep, created = runtime.prepare(previous_config)
    # Keep the current release and a recovery snapshot until all files are restored.
    current = manifest_path.parent/'rollback-current'
    current.mkdir(exist_ok=True)
    restored = []
    try:
        for index, record in enumerate(reversed(manifest['files'])):
            destination = home/record['path']
            snapshot = current/str(index)
            replace(snapshot,source=destination)
            restore(home,manifest_path.parent,record)
            restored.append((destination,snapshot))
    except BaseException:
        for destination,snapshot in reversed(restored): replace(destination,source=snapshot)
        if runtime:
            for row in created: runtime.stop(row)
        raise
    manifest['rolled_back'] = True
    replace(manifest_path, content=json.dumps(manifest,indent=2))
    if runtime:
        try:
            runtime.retire(keep)
        except LifecycleError as error:
            manifest['runtime_error'] = str(error)
            replace(manifest_path, content=json.dumps(manifest, indent=2))
            raise
    if runtime:
        from panel import reconcile
        reconcile()
        from notifications import reconcile as reconcile_notifications
        reconcile_notifications()
    print('Restored. Release and backup retained.' + (' Previous PixelRail activated.' if keep else ''))


def validate_record(record):
    relative = Path(record['path'])
    if relative.is_absolute() or '..' in relative.parts or str(relative) in ('.',''):
        raise ValueError('Unsafe manifest path')
    if Path(record['backup']).name != record['backup'] or not record['backup'].isdigit():
        raise ValueError('Unsafe backup path')


def uninstall(home, apply, no_start=False):
    directory=home/'.local/state/pixelrail/deployments'
    safe_parent(home,directory/'placeholder')
    active=[]
    for path in directory.glob('*/manifest.json'):
        data=json.loads(path.read_text())
        if data.get('complete') and not data.get('rolled_back'):
            if data.get('home')!=str(home):raise ValueError('Backup belongs to another target home')
            active.append((path,data))
    active.sort(key=lambda item:item[1].get('created_ns',item[0].stat().st_mtime_ns),reverse=True)
    if not active:raise ValueError('No active PixelRail deployment; no files changed.')
    virtual={};records={}
    for path,data in active:
        for record in data['files']:
            validate_record(record);destination=home/record['path'];safe_parent(home,destination)
            current=virtual[record['path']] if record['path'] in virtual else token(destination)
            if current!=record['after']:raise ValueError('Changed since deployment; preserve/reconcile manually: '+str(destination))
            if record['before'] is not None and token(path.parent/record['backup'])!=record['before']:raise ValueError('Backup changed: '+record['path'])
            virtual[record['path']]=record['before'];records[record['path']]=record
    print('Uninstall: restore',len(active),'deployment(s) to the original configuration.')
    for name in sorted(records):print('Restore original:',name)
    print('Keep user settings, clipboard history, wallpapers, releases and all backups. Shared wallpaper/adopted clipboard processes are preserved.')
    if not apply:
        print('Dry run. Pass --apply; --no-start performs no process changes.');return
    runtime=Shell(owned_configs(home,REPO)) if not no_start else None
    native_notifications=False
    recovery=directory/('uninstall-'+uuid.uuid4().hex)
    recovery.mkdir(mode=0o700)
    snapshots=[]
    for index,name in enumerate(sorted(records)):
        before=token(home/name);saved=recovery/str(index)
        if before is not None:shutil.copy2(home/name,saved,follow_symlinks=False)
        snapshots.append((home/name,saved,before))
    manifests=[(path,path.read_text()) for path,_ in active]
    replace(recovery/'recovery.json',content=json.dumps({'home':str(home),'paths':[str(path.relative_to(home)) for path,_,_ in snapshots]},indent=2))
    try:
        if runtime:
            import notifications
            owner=notifications.owner()
            if owner and any(row['pid']==owner['pid'] for row in runtime.instances()):
                if not shutil.which('swaync'):raise ValueError('Native notifications active; restore a notification server first, or use offline --no-start explicitly.')
                notifications.switch('swaync',save=False);native_notifications=True
        for path,_ in active:rollback(home,path.parent.name,True,True)
    except BaseException:
        for destination,saved,before in snapshots:
            if before is None:
                if destination.exists() or destination.is_symlink():destination.unlink()
            else:replace(destination,source=saved)
        for path,text in manifests:replace(path,content=text)
        if native_notifications:
            try:notifications.switch('pixelrail',save=False)
            except Exception as error:print('Notification recovery requires attention:',error,file=sys.stderr)
        raise
    if runtime:
        runtime.retire()
        import clipboard_history
        clipboard_history.stop_owned_watcher()
        import panel
        with panel.locked():
            panel.stop_bar(panel.owned_bar())
            if shutil.which('waybar') and (home/'.config/waybar/config.jsonc').is_file() and not panel.bars():panel.start_bar()
    print('Uninstalled. Original files restored; recovery snapshot:',recovery)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('deploy','rollback','uninstall'))
    parser.add_argument('--target-home', type=Path, default=Path.home(), help='For isolated staging/tests, or an explicit user home')
    parser.add_argument('--no-start', action='store_true', help='Offline/staging: change files only, do not inspect/start/stop Quickshell')
    parser.add_argument('--apply', action='store_true', help='Perform changes and activate PixelRail unless --no-start; default is dry run')
    parser.add_argument('--id', help='Rollback deployment ID; default is latest active deployment')
    parser.add_argument('--accept-config-changes',action='store_true',help='Explicitly approve reviewed unmanaged dotfile replacements (never implied by --apply)')
    parser.add_argument('--diff',action='store_true',help='Show proposed text changes before confirmation')
    parser.add_argument('--check',action='store_true',help='Read-only dependency/native build report; no installation')
    parser.add_argument('--json',action='store_true',help='JSON dependency report with --check')
    arguments = parser.parse_args()
    home = arguments.target_home.expanduser().resolve()
    if home == Path('/'): parser.error('Target home must not be /')
    if any(ord(character)<32 for character in str(home)): parser.error('Control characters are not supported in target-home')
    try:
        if arguments.apply and os.geteuid()==0:raise ValueError('Per-user installation only: do not run as root or with sudo.')
        if arguments.id and arguments.operation!='rollback':raise ValueError('--id is only valid for rollback')
        if arguments.operation!='deploy' and (arguments.accept_config_changes or arguments.diff):raise ValueError('--diff/--accept-config-changes are install/deploy options, not force-restore options')
        if arguments.check:
            from preflight import report,explain
            data=report(REPO)
            print(json.dumps(data,indent=2)) if arguments.json else explain(data)
            return 1 if data['errors'] else 0
        if arguments.apply and not arguments.no_start:
            for key,expected in [('XDG_CONFIG_HOME',home/'.config'),('XDG_DATA_HOME',home/'.local/share'),('XDG_STATE_HOME',home/'.local/state')]:
                if os.environ.get(key) and Path(os.environ[key]).expanduser().resolve()!=expected:
                    raise ValueError(key+' differs from the supported install layout; use explicit offline --target-home/--no-start. No live changes performed.')
        if arguments.apply and not arguments.no_start and home != Path.home().resolve():
            raise ValueError('Для другого HOME используйте --no-start или запускайте с HOME целевого пользователя')
        with locked(home) if arguments.apply else nullcontext():
            if arguments.operation == 'deploy': deploy(home, arguments.apply, arguments.no_start,arguments.accept_config_changes,arguments.diff)
            elif arguments.operation == 'rollback': rollback(home, arguments.id, arguments.apply, arguments.no_start)
            else: uninstall(home,arguments.apply,arguments.no_start)
    except (OSError,ValueError,KeyError,TypeError,LifecycleError) as error:
        print('PixelRail deployment:',error,file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
