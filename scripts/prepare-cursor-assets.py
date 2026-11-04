#!/usr/bin/env python3
"""Prepare selected official XCursor dependencies inside the repo. Never install/apply."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile
import urllib.request
ROOT=Path(__file__).resolve().parent.parent
VERSION='v2.0.0'
HASHES={'Black':'f9d84dccabfac08626a1a48cdbc4af909154988f3d66d39013a844fcafbd00e3','White':'cd369380d6d597fdee01fc72981109bf61933db96efc3b27b49dc88763b3cdb0'}
SIZES={24,28,32}
IMAGE=0xfffd0002

def prune(data):
    if len(data)<16:raise ValueError('Invalid XCursor header')
    magic,header,version,count=struct.unpack_from('<4I',data)
    if magic!=0x72756358 or header<16 or header+count*12>len(data):raise ValueError('Invalid XCursor table')
    chunks=[]
    for index in range(count):
        kind,size,offset=struct.unpack_from('<3I',data,header+index*12)
        if kind!=IMAGE or size not in SIZES:continue
        if offset+36>len(data):raise ValueError('Truncated cursor')
        h,t,s,v,w,height,x,y,delay=struct.unpack_from('<9I',data,offset)
        end=offset+h+w*height*4
        if h<36 or t!=kind or s!=size or not 0<w<=256 or not 0<height<=256 or x>=w or y>=height or end>len(data):raise ValueError('Invalid image chunk')
        chunks.append((size,data[offset:end]))
    if {s for s,_ in chunks}!=SIZES:raise ValueError('Missing required cursor sizes')
    output=bytearray(struct.pack('<4I',magic,16,version,len(chunks)));position=16+12*len(chunks)
    for size,chunk in chunks:output.extend(struct.pack('<3I',IMAGE,size,position));position+=len(chunk)
    for _,chunk in chunks:output.extend(chunk)
    return bytes(output),len(chunks)

def prepare(download=False,output=None):
    cache=ROOT/'.cache/icon-cursor-audit';cache.mkdir(parents=True,exist_ok=True)
    output=(output or ROOT/'.cache/cursor-assets').resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must be inside repository/release')
    manifest={'upstream':'https://github.com/ful1e5/Google_Cursor','version':VERSION,'license':'GPL-3.0','installed':False,'sizes':sorted(SIZES),'themes':{}}
    for color,expected in HASHES.items():
        name='GoogleDot-'+color;archive=cache/(name+'.tar.gz')
        url=f'https://github.com/ful1e5/Google_Cursor/releases/download/{VERSION}/{name}.tar.gz'
        if not archive.exists():
            if not download:raise ValueError('Archive missing; explicitly run with --download')
            with urllib.request.urlopen(url,timeout=30) as stream:data=stream.read(6000000)
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Archive checksum mismatch')
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise ValueError('Cached archive checksum mismatch')
        folder=output/name;cursor=folder/'cursors'
        if not cursor.resolve().is_relative_to(output):raise ValueError('Staging path escapes output')
        cursor.mkdir(parents=True,exist_ok=True)
        frames=0;files={};links={}
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                path=Path(member.name)
                if path.parts[:2]!=(name,'cursors') or len(path.parts)!=3:continue
                target=cursor/path.name
                if member.isfile():
                    data=source.extractfile(member).read();filtered,count=prune(data);frames+=count
                    if target.is_symlink():raise ValueError('Refusing to overwrite staged symlink')
                    target.write_bytes(filtered);files[path.name]=hashlib.sha256(filtered).hexdigest()
                elif member.issym():
                    if '/' in member.linkname or member.linkname in ('.','..'):raise ValueError('Unsafe cursor alias')
                    links[path.name]=member.linkname
            for alias,target_name in links.items():
                # Preserve aliases only when their ultimate target is staged.
                seen=set();resolved=target_name
                while resolved in links and resolved not in seen:seen.add(resolved);resolved=links[resolved]
                if resolved not in files:raise ValueError('Dangling cursor alias '+alias)
                target=cursor/alias
                if target.is_symlink():target.unlink()
                elif target.exists():raise ValueError('Alias would overwrite regular file')
                target.symlink_to(target_name)
        for filename in ('index.theme','LICENSE','SOURCE.txt'):
            if (folder/filename).is_symlink():raise ValueError('Unsafe staging metadata symlink')
        (folder/'index.theme').write_text('[Icon Theme]\nName='+name+'\nComment=GoogleDot '+VERSION+'; PixelRail selected sizes 24/28/32\nInherits=Adwaita\n')
        (folder/'LICENSE').write_bytes((ROOT/'quickshell/assets/cursors/GoogleDot-LICENSE.txt').read_bytes())
        (folder/'SOURCE.txt').write_text('Official dependency: '+url+'\nSHA256 '+expected+'\nGPLv3 source: https://github.com/ful1e5/Google_Cursor/tree/'+VERSION+'\nPixelRail modification: removed other image sizes; image pixels, hotspots, delays and frames unchanged.\nNot installed. Private dependency staging, not a bundled binary release.\n')
        manifest['themes'][name]={'archive':url,'archiveSha256':expected,'files':files,'aliases':links,'frames':frames}
    output.mkdir(parents=True,exist_ok=True)
    if (output/'manifest.json').is_symlink():raise ValueError('Unsafe manifest symlink')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return output,manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:
        output,manifest=prepare(args.download,args.output);print(json.dumps({'prepared':str(output),'themes':list(manifest['themes']),'installed':False}))
    except (OSError,ValueError,tarfile.TarError) as error:parser.exit(1,str(error)+'\n')
