#!/usr/bin/env python3
"""Reproducible source snapshot, including reviewed untracked sources, never Git history."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parent.parent
ROOT_FILES={'LICENSE','THIRD_PARTY_NOTICES.md','README.md','README.ru.md','CHANGELOG.md','.gitignore','.gitattributes'}
FOLDERS={'scripts','quickshell','hypr','config','share','waybar','swaync','kitty','rofi','extras','tests','docs','.github'}


def checkout(root):
    try:return Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()).resolve()==root.resolve()
    except (OSError,subprocess.CalledProcessError):return False


def public_files(root):
    try:
        if not checkout(root):raise OSError('source archive, no local Git root')
        output=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root,stderr=subprocess.DEVNULL)
        paths=[Path(name) for name in output.decode().split('\0') if name]
    except (OSError,subprocess.CalledProcessError):
        paths=[]
        for directory,folders,names in os.walk(root):
            folders[:]=[name for name in folders if name not in {'.git','.cache','__pycache__','dist'}]
            paths.extend((Path(directory)/name).relative_to(root) for name in names)
    files=[]
    for relative in sorted(set(paths)):
        if str(relative) not in ROOT_FILES and relative.parts[0] not in FOLDERS:continue
        if any(part in {'.git','.cache','__pycache__','dist'} for part in relative.parts):continue
        if relative.is_relative_to('docs/design/screenshots'):continue
        name=relative.name
        if name.startswith('.env') or name=='build-info.json' or relative.suffix in {'.so','.pyc','.o','.tmp','.part','.bak','.backup','.old','.swp'}:continue
        path=root/relative
        if path.is_symlink():raise ValueError('Review source symlink before packaging: '+str(relative))
        if path.is_file():files.append(relative)
    return files


def package(root,output,version):
    if version!='3.1.0':raise ValueError('This release recipe is for 3.1.0')
    output=output.resolve()
    if not output.is_relative_to(root.resolve()):raise ValueError('Output must be inside the checkout')
    for required in ['LICENSE','THIRD_PARTY_NOTICES.md','README.md','README.ru.md']:
        if not (root/required).is_file():raise ValueError('Missing publication file: '+required)
    from publication_audit import findings
    files=public_files(root)
    for relative in files:
        if findings((root/relative).read_bytes(),str(relative)):raise ValueError('Publication audit finding in '+str(relative)+'; run publication_audit.py')
    try:
        if not checkout(root):raise OSError('source archive')
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root))
    except (OSError,subprocess.CalledProcessError):revision=None;dirty=None
    try:tag=subprocess.check_output(['git','describe','--exact-match','--tags','HEAD'],cwd=root,stderr=subprocess.DEVNULL,text=True).strip() if revision else None
    except subprocess.CalledProcessError:tag=None
    metadata={'version':version,'kind':'source-release' if tag=='v'+version and not dirty else 'source-candidate','revision':revision,'dirty_worktree':dirty,
              'native_binary_included':False,'history_included':False,'license':'MIT','copyright_holder':'nesnimi'}
    output.mkdir(parents=True,exist_ok=True)
    archive=output/('pixelrail-'+version+'-source.tar.gz');prefix='pixelrail-'+version
    with archive.open('wb') as destination,gzip.GzipFile(filename='',fileobj=destination,mode='wb',mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as tar:
        for relative in files+[Path('RELEASE.json')]:
            data=json.dumps(metadata,sort_keys=True,indent=2).encode()+b'\n' if str(relative)=='RELEASE.json' else (root/relative).read_bytes()
            info=tarfile.TarInfo(prefix+'/'+relative.as_posix());info.size=len(data);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
            info.mode=0o755 if str(relative)!='RELEASE.json' and (root/relative).stat().st_mode&0o111 else 0o644
            tar.addfile(info,io.BytesIO(data))
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS').write_text(checksum+'  '+archive.name+'\n')
    return {'archive':str(archive.relative_to(root)),'sha256':checksum,'files':len(files),'metadata':metadata}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'.cache/dist');parser.add_argument('--version',default='3.1.0');args=parser.parse_args()
    print(json.dumps(package(ROOT,args.output,args.version),indent=2))
