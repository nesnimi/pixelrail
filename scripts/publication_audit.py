#!/usr/bin/env python3
"""Read-only, redacted checks of publishable files and reachable Git history."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

SECRET_PATTERNS = {
    'private-key': re.compile(r'-{5}BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-{5}'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'slack-token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'api-secret': re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b'),
    'credential-literal': re.compile(r'''(?i)(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)['"]?\s*[:=]\s*['"][A-Za-z0-9_/+=.-]{16,}['"]'''),
    'credential-url': re.compile(r'https?://[^\s/:"\']+:[^\s/@"\']+@'),
}
HOME_PATH = re.compile('/' + r'home/([^/\s"\'<>]+)/')
EXAMPLES = {'user','username','example','test','alice','bob','fixture','OWNER'}


def findings(data, location):
    if b'\0' in data[:8192]: return []
    text=data.decode('utf-8',errors='replace');result=[]
    for kind,pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):result.append({'kind':kind,'location':location,'line':text.count('\n',0,match.start())+1})
    for match in HOME_PATH.finditer(text):
        if match[1] not in EXAMPLES and not match[1].startswith(('$','<')):
            result.append({'kind':'absolute-home','location':location,'line':text.count('\n',0,match.start())+1})
    return result


def audit(root, history=False):
    result={'worktree':[],'history':[],'history_metadata':{},'limitations':'Pattern scan, not proof of absence. Binary screenshots/artwork and commit identities require owner review. No matched values are printed.'}
    try:
        files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
    except subprocess.CalledProcessError:raise ValueError('Run inside a Git checkout')
    for name in sorted(set(filter(None,files))):
        path=root/name
        if path.is_file() and not path.is_symlink():result['worktree']+=findings(path.read_bytes(),name)
        if name.startswith(('.cache/','.ssh/')) or Path(name).name in ('.env','id_rsa','id_ed25519'):
            result['worktree'].append({'kind':'private-file-path','location':name})
    if history:
        objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=root,text=True).splitlines()
        child=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        try:
            for item in objects:
                sha,_,name=item.partition(' ')
                child.stdin.write((sha+'\n').encode());child.stdin.flush()
                header=child.stdout.readline().decode().split()
                if len(header)!=3:continue
                size=int(header[2]);data=child.stdout.read(size);child.stdout.read(1)
                if header[1]=='blob':
                    result['history']+=findings(data,sha[:12]+':'+name)
                    if name.startswith(('.cache/','.ssh/')) or Path(name).name in ('.env','id_rsa','id_ed25519'):
                        result['history'].append({'kind':'private-file-path','location':sha[:12]+':'+name})
                elif header[1] in ('commit','tag'):
                    result['history']+=findings(data.partition(b'\n\n')[2],sha[:12]+':message')
        finally:child.stdin.close();child.wait(timeout=5)
        identities=set(subprocess.check_output(['git','log','--all','--format=%ae%n%ce'],cwd=root,text=True).splitlines())
        result['history_metadata']={'commit_count':int(subprocess.check_output(['git','rev-list','--all','--count'],cwd=root)),
            'distinct_emails':len(identities),'non_github_noreply_emails':sum(not value.endswith('@users.noreply.github.com') for value in identities),
            'action':'Review git log --all --format=fuller locally before pushing; this tool does not rewrite authors/history.'}
    result['counts']={key:dict(Counter(item['kind'] for item in result[key])) for key in ('worktree','history')}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--history',action='store_true');parser.add_argument('--json',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent;result=audit(root,args.history)
    print(json.dumps(result,indent=2,ensure_ascii=False)) if args.json else print(json.dumps({'counts':result['counts'],'history_metadata':result['history_metadata'],'limitations':result['limitations']},indent=2))
    return int(bool(result['worktree'] or result['history']))


if __name__=='__main__':raise SystemExit(main())
