"""Release transitions against a fake qs registry; never connects to the real session."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path.cwd()
with tempfile.TemporaryDirectory(dir=root/'.cache') as tmp:
    base=Path(tmp); home=base/'home'; home.mkdir(); binary=base/'bin'; binary.mkdir()
    runtime=base/'runtime'; runtime.mkdir(mode=0o700)
    state=base/'state.json'; log=base/'calls.jsonl'; control=base/'fail'
    state.write_text(json.dumps({'counter':0,'instances':[
        {'id':'foreign','pid':900001,'config_path':str(base/'foreign/shell.qml')},
        {'id':'unregistered','pid':900002,'config_path':str(home/'.local/share/pixelrail/releases/not-managed/quickshell/shell.qml')}
    ]}))
    fake = '''#!/usr/bin/env python3
import json, os, pathlib, sys
state=pathlib.Path(os.environ['TEST_STATE']); data=json.loads(state.read_text()); args=sys.argv[1:]
with open(os.environ['TEST_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
if args[0]=='list': print(json.dumps(data['instances']))
elif args[0]=='ipc':
    pid=int(args[args.index('--pid')+1]); row=next((r for r in data['instances'] if r['pid']==pid),None)
    if row is None or row.get('unready'): sys.exit(1)
    print('unloaded')
elif args[0]=='kill':
    ident=args[args.index('--id')+1]
    data['instances']=[r for r in data['instances'] if r['id']!=ident]
    state.write_text(json.dumps(data))
else:
    config=args[args.index('-p')+1]
    if not any(r['config_path']==config for r in data['instances']):
        data['counter']+=1
        row={'id':'pixel'+str(data['counter']),'pid':1000000+data['counter'],'config_path':config}
        data['instances'].append(row)
        if pathlib.Path(os.environ['TEST_FAIL']).exists(): row['unready']=True
        state.write_text(json.dumps(data))
        if row.get('unready'): sys.exit(1)
'''
    qs=binary/'qs'; qs.write_text(fake); qs.chmod(0o755)
    env=dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY='fixture',
             PATH=str(binary)+':/usr/bin',TEST_STATE=str(state),TEST_LOG=str(log),TEST_FAIL=str(control))
    env.pop('PIXELRAIL_QML',None)
    def command(script,*args,ok=True):
        result=subprocess.run([str(root/'scripts'/script),*args],env=env,capture_output=True,text=True,timeout=25)
        assert (result.returncode==0)==ok, result.stdout+result.stderr
        return result
    def deploy(ok=True): return command('deploy.sh','--target-home',str(home),'--apply',ok=ok)
    def rollback(ok=True): return command('rollback.sh','--target-home',str(home),'--apply',ok=ok)
    def rows(): return json.loads(state.read_text())['instances']
    def managed(): return [r for r in rows() if r['id'].startswith('pixel')]
    def intact(): assert {r['id'] for r in rows() if not r['id'].startswith('pixel')}=={'foreign','unregistered'}
    def current(): return (home/'.local/bin/pixelrail-shell').resolve().parent.parent
    deploy(); first=current(); first_id=managed()[0]['id']; intact()
    assert len(managed())==1 and managed()[0]['config_path']==str(first/'quickshell/shell.qml')
    # Concurrent login/start calls share a lock even across release directories.
    starts=[subprocess.Popen([str(home/'.local/bin/pixelrail-shell')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
    for process in starts:
        stdout,stderr=process.communicate(timeout=20); assert process.returncode==0,stderr
    assert len(managed())==1 and managed()[0]['id']==first_id
    deploy(); second=current(); second_id=managed()[0]['id']; intact()
    assert first!=second and len(managed())==1 and second_id!=first_id
    starts=[subprocess.Popen([str(release/'scripts/pixelrail-shell')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            for release in (first,second,first,second)]
    for process in starts:
        stdout,stderr=process.communicate(timeout=20); assert process.returncode==0,stderr
    assert len(managed())==1 and managed()[0]['id']==second_id
    # Legacy backup metadata has no previous_config; derive it from the backed-up symlink.
    for manifest_path in (home/'.local/state/pixelrail/deployments').glob('*/manifest.json'):
        metadata=json.loads(manifest_path.read_text())
        if metadata['release']==str(second):
            metadata.pop('previous_config',None); manifest_path.write_text(json.dumps(metadata))
    operations=[json.loads(line) for line in log.read_text().splitlines()]
    kill_index=next(i for i,args in enumerate(operations) if args==['kill','--id',first_id])
    new_pid=managed()[0]['pid']
    assert ['ipc','--pid',str(new_pid),'call','menus','status'] in operations[:kill_index]
    # Failed launch creates a broken instance; it is cleaned while old process/links survive.
    control.touch(); deploy(ok=False)
    assert current()==second and len(managed())==1 and managed()[0]['id']==second_id; intact()
    control.unlink()
    # Failed rollback startup must preserve the current process, links and rollback eligibility.
    control.touch(); rollback(ok=False)
    assert current()==second and managed()[0]['id']==second_id and len(managed())==1
    control.unlink(); rollback()
    assert current()==first and len(managed())==1 and managed()[0]['config_path']==str(first/'quickshell/shell.qml'); intact()
    # Current release's autostart remains idempotent after rollback.
    result=subprocess.run([str(home/'.local/bin/pixelrail-shell')],env=env,capture_output=True,timeout=20)
    assert result.returncode==0 and len(managed())==1
    rollback(); assert not managed(); intact()
    # Offline staging never invokes qs, even with a Wayland environment present.
    previous_log=log.read_text()
    command('deploy.sh','--target-home',str(home),'--apply','--no-start')
    command('rollback.sh','--target-home',str(home),'--apply','--no-start')
    assert log.read_text()==previous_log
print('Lifecycle: update, 4 concurrent starts, readiness-before-stop, failed launch/rollback, rollback, unrelated instances, offline mode passed')
