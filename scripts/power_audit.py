#!/usr/bin/env python3
"""Finite, read-only power snapshots. No hardware probing commands or settings writes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

MANAGERS=('tlp.service','tuned.service','power-profiles-daemon.service','auto-cpufreq.service')
PROCESS_NAMES={'tlp','tuned','power-profiles-daemon','auto-cpufreq'}

def read(path,errors):
    try:return path.read_text().strip()
    except FileNotFoundError:return None
    except OSError as error:errors.append(str(path)+': '+str(error));return None

def number(path,errors):
    value=read(path,errors)
    try:return float(value) if value is not None else None
    except ValueError:errors.append(str(path)+': invalid number');return None

def managers():
    try:
        result=subprocess.run(['systemctl','show','--no-pager','--property=Id,LoadState,ActiveState,SubState',*MANAGERS],capture_output=True,text=True,timeout=3,env=dict(os.environ,LC_ALL='C'))
        entries=[]
        for block in result.stdout.strip().split('\n\n'):
            row=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
            if row.get('Id'):entries.append(row)
        return {'units':entries,'error':result.stderr.strip() or (None if result.returncode==0 else 'systemctl query failed')}
    except (OSError,subprocess.SubprocessError) as error:return {'units':[],'error':str(error)}

def snapshot(sysroot=Path('/sys'),procroot=Path('/proc'),manager_query=managers):
    errors=[];batteries={};external=[]
    for entry in sorted((sysroot/'class/power_supply').glob('*')):
        kind=read(entry/'type',errors)
        if kind=='Battery':
            status=read(entry/'status',errors);percent=number(entry/'capacity',errors)
            energy=number(entry/'energy_now',errors);full=number(entry/'energy_full',errors)
            if percent is None and energy is not None and full and full>0:percent=100*energy/full
            watts=None;method=None
            if status=='Discharging':
                power=number(entry/'power_now',errors)
                if power is not None and power>=0:watts=power/1e6;method='power_now'
                elif power is None:
                    current=number(entry/'current_now',errors);voltage=number(entry/'voltage_now',errors)
                    if current is not None and voltage is not None and current>=0 and voltage>0:watts=current*voltage/1e12;method='current_now × voltage_now'
                if read(entry/'status',errors)!=status:watts=None;method=None
            batteries[entry.name]={'status':status,'percent':percent,'discharge_w':watts,'power_method':method,
                                   'energy_now_wh':energy/1e6 if energy is not None else None,'energy_full_wh':full/1e6 if full is not None else None}
        else:
            online=number(entry/'online',errors)
            if online is not None:external.append({'name':entry.name,'type':kind,'online':bool(online)})
    source='AC' if any(item['online'] for item in external) else 'Battery' if external or any(item['status']=='Discharging' for item in batteries.values()) else 'Unknown'
    policies=[]
    for entry in sorted((sysroot/'devices/system/cpu/cpufreq').glob('policy[0-9]*'),key=lambda p:int(p.name[6:]) if p.name[6:].isdigit() else -1):
        if not entry.name[6:].isdigit():continue
        policies.append({'policy':entry.name,'driver':read(entry/'scaling_driver',errors),'governor':read(entry/'scaling_governor',errors),'epp':read(entry/'energy_performance_preference',errors),'available_epp':(read(entry/'energy_performance_available_preferences',errors) or '').split()})
    nvidia=[]
    for entry in sorted((sysroot/'bus/pci/devices').glob('*')):
        if read(entry/'vendor',errors)!='0x10de':continue
        try:driver=(entry/'driver').resolve(strict=True).name
        except OSError:driver=None
        nvidia.append({'pci':entry.name,'driver':driver,'control':read(entry/'power/control',errors),'status':read(entry/'power/runtime_status',errors),'active_ms':number(entry/'power/runtime_active_time',errors),'suspended_ms':number(entry/'power/runtime_suspended_time',errors)})
    shells=[];running=[]
    for entry in procroot.glob('[0-9]*'):
        try:
            command=entry.joinpath('cmdline').read_bytes().split(b'\0');names={Path(v.decode(errors='replace')).name for v in command[:2] if v}
            if names & PROCESS_NAMES:running.append({'pid':int(entry.name),'names':sorted(names & PROCESS_NAMES)})
            if entry.stat().st_uid!=os.getuid():continue
            # CPU accounting: utime/stime, identity: starttime. RSS is in pages.
            fields=entry.joinpath('stat').read_text().rsplit(')',1)[1].split()
            comm=entry.joinpath('comm').read_text().strip()
            if comm in ('qs','quickshell'):
                rss=int(entry.joinpath('statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')/1048576
                shells.append({'pid':int(entry.name),'start':fields[19],'ticks':int(fields[11])+int(fields[12]),'rss_mib':rss})
        except (FileNotFoundError,ProcessLookupError):continue
        except (OSError,ValueError,IndexError) as error:errors.append(str(entry)+': '+str(error))
    # Services may run under root; systemd unit query is not restricted to this UID.
    return {'time':datetime.now(timezone.utc).isoformat(),'monotonic':time.monotonic(),'source':source,'external':external,'batteries':batteries,'cpu':policies,'nvidia':nvidia,'quickshell':shells,'managers':dict(manager_query(),processes=running),'errors':errors}

def delta(before,after):
    duration=after['monotonic']-before['monotonic'];previous={(p['pid'],p['start']):p for p in before['quickshell']}
    cpu={}
    for p in after['quickshell']:
        old=previous.get((p['pid'],p['start']))
        cpu[str(p['pid'])]=100*(p['ticks']-old['ticks'])/os.sysconf('SC_CLK_TCK')/duration if old and duration>0 and p['ticks']>=old['ticks'] else None
    devices={p['pci']:p for p in before['nvidia']};gpu={}
    for p in after['nvidia']:
        old=devices.get(p['pci'],{});gpu[p['pci']]={}
        for name in ('active_ms','suspended_ms'):
            a=old.get(name);b=p.get(name)
            gpu[p['pci']][name]=b-a if a is not None and b is not None and b>=a else None
    return {'interval_s':duration,'quickshell_cpu_percent_one_core':cpu,'nvidia_delta_ms':gpu}

def compact(row):
    sample=row['sample'];change=row['delta'];bat=sample['batteries'].get('BAT1',{})
    batteries=list(sample['batteries'].values());percent=None
    if len(batteries)==1:percent=batteries[0]['percent']
    elif batteries and all(value.get('energy_now_wh') is not None and (value.get('energy_full_wh') or 0)>0 for value in batteries):
        percent=100*sum(value['energy_now_wh'] for value in batteries)/sum(value['energy_full_wh'] for value in batteries)
    discharging=[value for value in batteries if value['status']=='Discharging']
    watts=sum(value['discharge_w'] for value in discharging) if discharging and all(value['discharge_w'] is not None for value in discharging) else None
    cpu=change['quickshell_cpu_percent_one_core'] if change else {}
    known=[value for value in cpu.values() if value is not None]
    return {'time':sample['time'],'source':sample['source'],'batteries':sample['batteries'],'battery_percent':percent,'discharge_w':watts,
            'BAT1_status':bat.get('status'),'BAT1_percent':bat.get('percent'),'BAT1_discharge_w':bat.get('discharge_w'),'qs_cpu_percent':sum(known) if known else None,'qs_rss_mib':round(sum(p['rss_mib'] for p in sample['quickshell']),2),'nvidia':sample['nvidia'],'nvidia_delta_ms':change['nvidia_delta_ms'] if change else None,'epp':{p['policy']:p['epp'] for p in sample['cpu']},'active_managers':[p['Id'] for p in sample['managers']['units'] if p.get('ActiveState') in ('active','activating')],'errors':sample['errors'],'manager_query_error':sample['managers']['error']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int,default=2);parser.add_argument('--interval',type=float,default=1)
    output=parser.add_mutually_exclusive_group();output.add_argument('--json',action='store_true');output.add_argument('--jsonl',action='store_true')
    args=parser.parse_args()
    if not 1<=args.samples<=3600 or not .1<=args.interval<=3600:parser.error('samples: 1..3600; interval: 0.1..3600 seconds')
    rows=[];previous=None
    for index in range(args.samples):
        if index:time.sleep(args.interval)
        current=snapshot();row={'sample':current,'delta':delta(previous,current) if previous else None};rows.append(row);previous=current
        if args.jsonl:print(json.dumps(compact(row),ensure_ascii=False),flush=True)
    if args.json:print(json.dumps({'schema':1,'read_only':True,'measurements':rows},ensure_ascii=False,indent=2))
    elif not args.jsonl:
        last=rows[-1];sample=last['sample'];summary=compact(last)
        def show(value,suffix=''):return 'unavailable' if value is None else str(round(value,2) if isinstance(value,float) else value)+suffix
        print('PixelRail power audit (read-only) · '+sample['time'])
        print('Power:',sample['source'],'· battery:',show(summary['battery_percent'],'%'),'· discharge:',show(summary['discharge_w'],' W'))
        for name,battery in sample['batteries'].items():print(name+':',show(battery['percent'],'%'),battery['status'],'· discharge:',show(battery['discharge_w'],' W'))
        if not sample['batteries']:print('Battery: none detected')
        for p in sample['cpu']:print(p['policy']+':',p['driver'],p['governor'],'· EPP:',p['epp'] or 'unavailable','· supported:',','.join(p['available_epp']) or 'unavailable')
        for p in sample['nvidia']:print('NVIDIA',p['pci'],p['driver'],p['control'],p['status'],'· counters ms:',p['active_ms'],p['suspended_ms'],'· delta:',summary['nvidia_delta_ms'])
        if not sample['nvidia']:print('NVIDIA runtime PM: unavailable / no NVIDIA device')
        print('Quickshell:',len(sample['quickshell']),'process(es) · RSS',summary['qs_rss_mib'],'MiB · CPU',show(summary['qs_cpu_percent'],'% of one core'))
        for p in sample['quickshell']:print('  PID',p['pid'],'· RSS',round(p['rss_mib'],2),'MiB · CPU',show((last['delta'] or {}).get('quickshell_cpu_percent_one_core',{}).get(str(p['pid'])),'%'))
        print('Active power managers:',', '.join(summary['active_managers']) or 'none reported','· processes:',sample['managers']['processes'])
        if sample['managers']['error']:print('Manager query:',sample['managers']['error'])
        for error in sample['errors']:print('Read error:',error)
if __name__=='__main__':main()
