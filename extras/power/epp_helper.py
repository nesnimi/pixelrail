#!/usr/bin/python3 -I
"""UNINSTALLED EPP broker candidate. Fixed operations only; no PixelRail UI hook."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

PREFERENCES={'battery':'balance_power','performance':'balance_performance'}
SYS=Path('/sys/devices/system/cpu/cpufreq')
STATE=Path('/var/lib/pixelrail-epp/state.json')
GATE=Path('/etc/pixelrail/epp-enabled')
MANAGERS=('tlp.service','tuned.service','power-profiles-daemon.service','auto-cpufreq.service')
class EppError(RuntimeError):pass

def atomic(path,value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as stream:
            json.dump(value,stream);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:Path(temporary).unlink(missing_ok=True)

class Transaction:
    # Constructor injection is for repository tests only; CLI paths are constants.
    def __init__(self,sysroot=SYS,state=STATE,boot_id=None):
        self.sysroot=Path(sysroot);self.state=Path(state)
        self.boot_id=boot_id if boot_id is not None else Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def policies(self):
        paths=sorted((p for p in self.sysroot.glob('policy*') if re.fullmatch(r'policy[0-9]+',p.name)),key=lambda p:int(p.name[6:]))
        if not paths:raise EppError('No CPU policies / EPP unavailable')
        result={}
        for path in paths:
            driver=(path/'scaling_driver').read_text().strip();governor=(path/'scaling_governor').read_text().strip()
            supported=(path/'energy_performance_available_preferences').read_text().split()
            value=(path/'energy_performance_preference').read_text().strip()
            if driver!='intel_pstate' or governor!='powersave':raise EppError(path.name+': expected intel_pstate + powersave; no governor changes allowed')
            if value not in supported:raise EppError(path.name+': current EPP cannot be restored safely')
            result[path.name]={'epp':value,'supported':supported}
        return result
    def plan(self,profile):
        target=PREFERENCES[profile];rows=self.policies()
        for name,row in rows.items():
            if target not in row['supported']:raise EppError(name+': unsupported EPP '+target)
        return {name:{'before':row['epp'],'after':target} for name,row in rows.items()}
    def load(self):
        try:state=json.loads(self.state.read_text())
        except FileNotFoundError:return None
        if not isinstance(state,dict) or state.get('schema')!=1 or state.get('boot_id')!=self.boot_id:raise EppError('Invalid or stale state; manual review required (no writes)')
        for mapping in (state.get('baseline'),state.get('pending')):
            if mapping is None:continue
            if not isinstance(mapping,dict) or not mapping or any(not re.fullmatch(r'policy[0-9]+',name) or not isinstance(value,str) for name,value in mapping.items()):raise EppError('Invalid saved policy map')
        if not isinstance(state.get('baseline'),dict):raise EppError('Missing baseline')
        return state
    def write(self,name,value):
        # No arbitrary path/value operation is exposed on the CLI.
        path=self.sysroot/name/'energy_performance_preference'
        with path.open('w') as stream:stream.write(value+'\n')
        if path.read_text().strip()!=value:raise EppError(name+': EPP readback mismatch')
    def commit(self,targets,rows,state):
        before={name:row['epp'] for name,row in rows.items()}
        if set(targets)!=set(rows):raise EppError('CPU policy topology changed; no writes')
        for name,target in targets.items():
            if target not in rows[name]['supported']:raise EppError(name+': saved/target EPP unsupported')
        pending=dict(state,pending=state.get('pending') or before)
        atomic(self.state,pending)  # Durable rollback information precedes every sysfs write.
        try:
            for name,target in targets.items():
                if rows[name]['epp']!=target:self.write(name,target)
            atomic(self.state,dict(state,pending=None))
        except (OSError,EppError) as error:
            failures=[]
            for name,value in reversed(list(before.items())):
                try:
                    if (self.sysroot/name/'energy_performance_preference').read_text().strip()!=value:self.write(name,value)
                except (OSError,EppError) as rollback:failures.append(name+': '+str(rollback))
            if not failures:
                try:atomic(self.state,state)
                except OSError as rollback:failures.append('state: '+str(rollback))
            raise EppError(str(error)+'; '+('rollback incomplete; pending state retained: '+', '.join(failures) if failures else 'previous values restored')) from error
    def apply(self,profile):
        plan=self.plan(profile);rows=self.policies();before={name:row['epp'] for name,row in rows.items()}
        state=self.load() or {'schema':1,'boot_id':self.boot_id,'baseline':before,'pending':None}
        if state.get('pending'):raise EppError('Unfinished transaction: recover first')
        if set(state['baseline'])!=set(rows):raise EppError('CPU policy topology changed; no writes')
        # Re-read after plan, before any write (hotplug/driver/governor changes fail closed).
        if set(plan)!=set(rows):raise EppError('CPU policy topology changed; no writes')
        self.commit({name:row['after'] for name,row in plan.items()},rows,state)
    def restore(self,recover=False):
        state=self.load()
        if state is None:raise EppError('No saved state; no writes')
        if state.get('pending') and not recover:raise EppError('Unfinished transaction: recover first')
        targets=state.get('pending') if recover else state['baseline']
        if targets is None:return
        self.commit(targets,self.policies(),state)

def trusted(path):
    for parent in (path,*path.parents):
        info=parent.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:raise EppError('Untrusted root-owned path: '+str(parent))

def authorize(operation):
    if os.geteuid()!=0:raise EppError('Root-only broker; not enabled by PixelRail. No automatic sudo/pkexec.')
    # Prevent an eventual privileged caller from running a user-writable release.
    trusted(Path(__file__).absolute())
    if operation=='apply':
        trusted(GATE)
        if not GATE.is_file() or GATE.read_text().strip()!='enabled':raise EppError('EPP management is disabled')
    if STATE.parent.exists():trusted(STATE.parent)
    else:
        trusted(STATE.parent.parent);STATE.parent.mkdir(mode=0o700)
    if STATE.exists() or STATE.is_symlink():trusted(STATE)

@contextmanager
def locked():
    directory=Path('/run/pixelrail-epp')
    if not directory.exists():
        trusted(directory.parent);directory.mkdir(mode=0o700)
    trusted(directory)
    lock=directory/'lock'
    descriptor=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(descriptor,'w') as stream:
        info=os.fstat(stream.fileno())
        if info.st_uid!=0 or info.st_mode & 0o022:raise EppError('Untrusted lock')
        fcntl.flock(stream,fcntl.LOCK_EX);yield

def check_managers():
    result=subprocess.run(['systemctl','list-units','--all','--type=service','--no-legend','--no-pager','--plain','--state=active,activating'],capture_output=True,text=True,timeout=3,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
    if result.returncode:raise EppError('Cannot verify power managers; refuse apply: '+result.stderr.strip())
    if any(line.split()[0] in MANAGERS for line in result.stdout.splitlines() if line.split()):raise EppError('Conflicting power manager is active')
    for directory in Path('/proc').glob('[0-9]*'):
        try:names={Path(value.decode()).name for value in directory.joinpath('cmdline').read_bytes().split(b'\0')[:2] if value}
        except (FileNotFoundError,ProcessLookupError):continue
        if names & {'tlp','tuned','power-profiles-daemon','auto-cpufreq'}:raise EppError('Conflicting manager process is running')

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='operation',required=True)
    for action in ('plan','apply'):commands.add_parser(action).add_argument('profile',choices=PREFERENCES)
    for action in ('restore','recover'):commands.add_parser(action)
    args=parser.parse_args()
    try:
        transaction=Transaction()
        if args.operation=='plan':print(json.dumps({'read_only':True,'profile':args.profile,'plan':transaction.plan(args.profile)},indent=2));return 0
        authorize(args.operation)
        with locked():
            if args.operation=='apply':check_managers();transaction.apply(args.profile)
            else:transaction.restore(recover=args.operation=='recover')
        return 0
    except (OSError,ValueError,EppError,subprocess.SubprocessError) as error:print('PixelRail EPP: '+str(error),file=__import__('sys').stderr);return 1
if __name__=='__main__':raise SystemExit(main())
