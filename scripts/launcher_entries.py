"""Read desktop visibility metadata missing from Quickshell 0.3.2. No writes/watchers."""
import configparser
import json
import os
from pathlib import Path


def catalog(environment=None):
    env = os.environ if environment is None else environment
    home = Path(env.get('HOME', str(Path.home())))
    roots = [Path(env.get('XDG_DATA_HOME') or home / '.local/share')]
    roots += [Path(path) for path in env.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if path]
    desktops = set(filter(None, (env.get('XDG_CURRENT_DESKTOP') or 'Hyprland').split(':')))
    entries = {}
    for root in dict.fromkeys(roots):
        applications = root / 'applications'
        for path in sorted(applications.rglob('*.desktop')):
            ident = str(path.relative_to(applications).with_suffix('')).replace(os.sep, '-')
            if ident in entries:
                continue  # User overrides, including Hidden tombstones, win.
            entries[ident] = {'hidden': True}
            try:
                if path.stat().st_size > 1024 * 1024:
                    continue
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.optionxform = str
                parser.read_string(path.read_text(encoding='utf-8', errors='replace'))
                section = parser['Desktop Entry']
                only = set(filter(None, section.get('OnlyShowIn', '').split(';')))
                excluded = set(filter(None, section.get('NotShowIn', '').split(';')))
                entries[ident] = {
                    'hidden': section.get('Hidden', 'false').lower() == 'true' or section.get('Type', '') != 'Application',
                    'noDisplay': section.get('NoDisplay', 'false').lower() == 'true',
                    'showInDesktop': (not only or bool(only & desktops)) and not bool(excluded & desktops),
                    'categories': list(filter(None, section.get('Categories', '').split(';'))),
                }
            except (OSError, KeyError, configparser.Error):
                pass
    return {'version': 1, 'entries': entries}


if __name__ == '__main__':
    print(json.dumps(catalog(), ensure_ascii=False, separators=(',', ':')))
