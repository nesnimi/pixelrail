#!/usr/bin/env python3
"""Transactional matugen -> Material 3 schemes. No hooks, background daemon or polling."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import wallpapers

SCHEMA=1
ROLES=('primary','onPrimary','primaryContainer','onPrimaryContainer','secondary','onSecondary',
       'secondaryContainer','onSecondaryContainer','tertiary','onTertiary','background','onBackground',
       'surface','onSurface','surfaceContainer','surfaceContainerHigh','surfaceVariant','onSurfaceVariant',
       'outline','outlineVariant','error','onError')
HEX=re.compile(r'^#[0-9a-fA-F]{6}$')

def config_path(): return wallpapers.config_home()/'pixelrail/theme.json'
def cache_root(): return Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'pixelrail/theme'
def palette_path(): return cache_root()/'palette.json'

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream:
            stream.write(data if isinstance(data,str) else json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally: Path(temporary).unlink(missing_ok=True)

@contextmanager
def locked():
    cache_root().mkdir(parents=True,exist_ok=True)
    with (cache_root()/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield

def accent(value):
    if value is None or value=='wallpaper': return None
    if not isinstance(value,str): raise ValueError('accent должен быть HEX или null')
    value=value if value.startswith('#') else '#'+value
    if re.fullmatch(r'#[0-9a-fA-F]{3}',value): value='#'+''.join(letter*2 for letter in value[1:])
    if not HEX.fullmatch(value): raise ValueError('Ожидается HEX #RGB или #RRGGBB')
    return value.upper()

def settings():
    try: data=json.loads(config_path().read_text())
    except FileNotFoundError: return {'mode':'dark','accent':None}
    if not isinstance(data,dict) or data.get('mode','dark') not in ('dark','light','auto'):
        raise ValueError('theme.json: mode должен быть dark, light или auto')
    if data.get('iconStyle','original') not in ('original','themed'):raise ValueError('iconStyle')
    if type(data.get('animations',True)) is not bool:raise ValueError('animations')
    return dict(data,mode=data.get('mode','dark'),accent=accent(data.get('accent')))

def contrast(first,second):
    def luminance(color):
        channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        channels=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
        return sum(v*w for v,w in zip(channels,(.2126,.7152,.0722)))
    a,b=sorted((luminance(first),luminance(second)))
    return (b+.05)/(a+.05)

def validate(schemes):
    if not isinstance(schemes,dict): raise ValueError('Нет схем Material 3')
    pairs=(('tertiary','onTertiary'),('primary','onPrimary'),('primaryContainer','onPrimaryContainer'),('secondary','onSecondary'),
           ('secondaryContainer','onSecondaryContainer'),('background','onBackground'),('surface','onSurface'),
           ('surfaceContainer','onSurface'),('surfaceContainerHigh','onSurface'),('surfaceVariant','onSurfaceVariant'),('error','onError'))
    for mode in ('dark','light'):
        scheme=schemes.get(mode,{})
        if not isinstance(scheme,dict) or any(not isinstance(scheme.get(role),str) or not HEX.fullmatch(scheme[role]) for role in ROLES):
            raise ValueError('Неполная/некорректная палитра Material 3: '+mode)
        if any(contrast(scheme[a],scheme[b])<4.5 for a,b in pairs):
            raise ValueError('Недостаточный контраст палитры: '+mode)
    return schemes

def normalize(data):
    if not isinstance(data,dict) or not isinstance(data.get('colors'),dict):
        raise ValueError('Некорректный JSON matugen')
    colors=data['colors']
    result={mode:{} for mode in ('dark','light')}
    def camel(name):
        parts=name.split('_');return parts[0]+''.join(word.title() for word in parts[1:])
    for mode in result:
        # matugen 4.x: colors.primary.dark.color; legacy: colors.dark.primary.
        if isinstance(colors.get(mode),dict): entries=colors[mode].items()
        else: entries=((name,node.get(mode)) for name,node in colors.items() if isinstance(node,dict))
        for name,value in entries:
            color=value.get('color') if isinstance(value,dict) else value
            if isinstance(color,str) and HEX.fullmatch(color): result[mode][camel(name)]=color.lower()
    return validate(result)

def cached():
    try:
        data=json.loads(palette_path().read_text())
        if data.get('schema')!=SCHEMA: return None
        validate(data.get('schemes'));return data
    except (FileNotFoundError,ValueError,AttributeError): return None

def source(config):
    if config['accent']: return {'kind':'accent','color':config['accent']}
    for path in (wallpapers.choice_file(),wallpapers.config_home()/'pixelrail/wallpaper'):
        try: value=path.read_text().removesuffix('\n')
        except FileNotFoundError: continue
        if not value: continue
        image=Path(value).expanduser().resolve()
        if not image.is_file(): raise ValueError('Сохранённые обои не найдены: '+str(image))
        digest=hashlib.sha256()
        with image.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
        return {'kind':'image','path':str(image),'sha256':digest.hexdigest()}
    return {'kind':'fallback','color':'#ADC9FF'}

def fingerprint(value):
    return hashlib.sha256(json.dumps({'schema':SCHEMA,'scheme':'scheme-tonal-spot','source':value},sort_keys=True).encode()).hexdigest()

def sync():
    """Caller holds the lock, shared by CLI and the one QML Process across releases."""
    config=settings()
    if not config_path().exists(): atomic(config_path(),config)
    current=source(config); key=fingerprint(current); previous=cached()
    binary=shutil.which('matugen')
    if not binary:
        if previous and previous.get('sourceKey')==key: return {'status':'cached','warning':'matugen недоступен; используется сохранённая палитра'}
        raise ValueError('matugen не найден; сохранена последняя корректная палитра или встроенный fallback')
    stat=Path(binary).resolve().stat()
    signature=f'{Path(binary).resolve()}:{stat.st_mtime_ns}:{stat.st_size}'
    if previous and previous.get('sourceKey')==key and previous.get('binarySignature')==signature:
        return {'status':'cached'}
    version=subprocess.check_output([binary,'--version'],text=True,timeout=5).strip()
    configuration=cache_root()/'matugen.toml'
    if not configuration.exists(): atomic(configuration,'[config]\n[templates]\n')
    command=[binary,'--config',str(configuration),'--dry-run','--json','hex','--mode','dark','--type','scheme-tonal-spot']
    if current['kind']=='image':
        # Share the existing installed image decoder; matugen always receives bounded PNG.
        image=cache_root()/'source.png'
        descriptor,temporary=tempfile.mkstemp(suffix='.png',dir=cache_root());os.close(descriptor)
        try:
            wallpapers.pixbuf().thumbnail(Path(current['path']),Path(temporary))
            os.replace(temporary,image)
        finally: Path(temporary).unlink(missing_ok=True)
        command+=['--source-color-index','0','image',str(image)]
    else: command+=['color','hex',current['color']]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode: raise ValueError('matugen не смог построить палитру; прежние цвета сохранены')
    schemes=normalize(json.loads(result.stdout))
    # A later wallpaper apply/editor change must not receive an older generation's colors.
    if fingerprint(source(settings()))!=key: return {'status':'superseded'}
    atomic(palette_path(),{'schema':SCHEMA,'sourceKey':key,'source':current,'matugen':version,'binarySignature':signature,'schemes':schemes})
    return {'status':'generated'}

def ipc(method):
    binary=shutil.which('qs') or shutil.which('quickshell')
    config=os.environ.get('PIXELRAIL_QML',str(Path(__file__).resolve().parent.parent/'quickshell/shell.qml'))
    if binary:
        try: return subprocess.check_output([binary,'ipc','-p',config,'call','theme',method],stderr=subprocess.DEVNULL,text=True,timeout=2).strip()
        except (OSError,subprocess.SubprocessError): pass
    return None

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('sync');commands.add_parser('refresh');commands.add_parser('status')
    mode=commands.add_parser('mode');mode.add_argument('value',choices=('dark','light','auto'))
    color=commands.add_parser('accent');color.add_argument('value',help='HEX, wallpaper or reset')
    ui=commands.add_parser('ui');ui.add_argument('key',choices=('iconStyle','animations'));ui.add_argument('value')
    args=parser.parse_args()
    try:
        with locked():
            if args.command=='status':
                print(json.dumps({'settings':settings(),'cached':bool(cached()),'matugen':shutil.which('matugen')},ensure_ascii=False));return 0
            config=settings()
            if args.command=='mode': config['mode']=args.value;atomic(config_path(),config)
            elif args.command=='accent':
                config['accent']=accent(None if args.value=='reset' else args.value);atomic(config_path(),config)
            if args.command=='ui':
                if args.key=='iconStyle' and args.value not in ('original','themed'):raise ValueError('iconStyle')
                if args.key=='animations' and args.value not in ('true','false'):raise ValueError('animations')
                config[args.key]=args.value=='true' if args.key=='animations' else args.value
                config['uiVersion']=1;atomic(config_path(),config);result={'status':'updated'}
            else:result=sync()
        print(json.dumps(result,ensure_ascii=False))
        if args.command!='sync': ipc('reload')
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        message=str(error) if isinstance(error,ValueError) else 'Не удалось обновить Material You: '+str(type(error).__name__)
        print(json.dumps({'error':message},ensure_ascii=False))
        if args.command!='sync': ipc('reload')
        return 1

if __name__=='__main__': sys.exit(main())
