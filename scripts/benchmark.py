#!/usr/bin/env python3
"""Finite Quickshell benchmark. IPC/state readiness is NOT rendered-frame latency."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time
import panel

BOUNDARY='IPC command + QML state readiness; excludes compositor presentation and physical key delivery'
def summarize(values):
    ordered=sorted(values)
    return {'n':len(values),'median_ms':statistics.median(values) if values else None,'p95_ms':ordered[math.ceil(.95*len(values))-1] if len(values)>=20 else None,'min_ms':min(values) if values else None,'max_ms':max(values) if values else None}
def process(pid):
    directory=Path('/proc')/str(pid);fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
    if fields[0]=='Z':raise RuntimeError('Quickshell exited')
    return {'pid':pid,'start':fields[19],'ticks':int(fields[11])+int(fields[12]),'rss_mib':int((directory/'statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')/1048576,'time':time.monotonic()}
def interval(before,after):
    if before['start']!=after['start']:raise RuntimeError('PID identity changed')
    return 100*(after['ticks']-before['ticks'])/os.sysconf('SC_CLK_TCK')/(after['time']-before['time'])
class Benchmark:
    def __init__(self,pid):self.pid=pid;self.binary=shutil.which('qs') or shutil.which('quickshell');self.timings={};self.memory=[]
    def call(self,target,method,*args):
        result=subprocess.run([self.binary,'ipc','--pid',str(self.pid),'call',target,method,*map(str,args)],capture_output=True,text=True,timeout=5)
        if result.returncode:raise RuntimeError(result.stderr.strip() or 'IPC failed: '+target+'.'+method)
        return result.stdout.strip()
    def state(self,target):return json.loads(self.call(target,'state'))
    def wait(self,target,predicate):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            value=self.state(target)
            if value.get('error'):raise RuntimeError(str(value['error']))
            if predicate(value):return value
            time.sleep(.01)
        raise RuntimeError(target+' readiness timeout')
    def timed(self,name,operation):
        started=time.perf_counter();operation();self.timings.setdefault(name,[]).append((time.perf_counter()-started)*1000)
    def idle(self,name,seconds):
        before=process(self.pid);time.sleep(seconds);after=process(self.pid)
        self.memory.append(dict(after,stage=name,cpu_percent_one_core=interval(before,after)))
    def close(self):
        self.call('launcher','hide');self.call('control','hide');self.call('menus','hide')
        self.wait('menus',lambda state:state['mode']=='unloaded' and not state.get('pending',False))
    def launcher(self):
        self.call('launcher','toggle');self.wait('launcher',lambda state:state['opened']);self.call('launcher','hide')
    def control(self,section):
        self.call('control','open',section);self.wait('control',lambda state:state['opened'] and state['loaded'] and state['section']==section)
    def menu(self,kind):
        self.call('menus','open',kind);self.wait('menus',lambda state:state['mode']==kind and state['opened'] and not state['busy'])
        self.call('menus','hide');self.wait('menus',lambda state:state['mode']=='unloaded' and not state.get('pending',False))
    def exercise(self,counts,idle):
        self.close()
        # Separate initial allocation from repeated activity; no cache/GC tricks.
        self.launcher();self.control('overview');self.control('notifications');self.close()
        for kind in ('clipboard','wallpaper'):self.menu(kind)
        self.idle('warm',idle)
        for _ in range(counts['launcher']):self.timed('launcher_open_state_close',self.launcher)
        self.idle('launcher',idle)
        self.control('overview')
        for _ in range(counts['switch']):
            self.timed('A_to_N_state',lambda:self.control('notifications'))
            self.timed('N_to_A_state',lambda:self.control('overview'))
        self.close();self.idle('switch',idle)
        for kind in ('clipboard','wallpaper'):
            for _ in range(counts[kind]):self.timed(kind+'_open_ready_close',lambda:self.menu(kind))
            self.idle(kind,idle)
        for _ in range(counts['detail']):
            self.timed('control_open_wifi_ready',lambda:self.control('wifi'));self.control('bluetooth');self.close()
        self.idle('details',idle)
        for kind in ('controls','power','command','windows','keys','media','emoji'):self.timed(kind+'_open_ready_close',lambda:self.menu(kind))
        self.idle('settled',idle)
    def run(self,samples,idle,exercise=False,stress=False):
        initial=process(self.pid);self.idle('baseline',idle)
        for _ in range(samples):self.timed('control_state_IPC',lambda:self.state('control'))
        if exercise:self.exercise({'launcher':50 if stress else samples,'switch':50 if stress else samples,'clipboard':30 if stress else samples,'wallpaper':20 if stress else samples,'detail':20 if stress else samples},idle)
        else:self.idle('settled',idle)
        final=process(self.pid)
        if final['start']!=initial['start']:raise RuntimeError('PID changed')
        return {'schema':1,'boundary':BOUNDARY,'exercise':exercise,'stress':stress,'pid':self.pid,'process_count':len(panel.shells()),'process_count_scope':'owned PixelRail instances in this HOME/display','initial':initial,'final':final,'rss_delta_mib':final['rss_mib']-initial['rss_mib'],'memory':self.memory,'timings':{name:summarize(values) for name,values in self.timings.items()},'raw_ms':self.timings}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pid',type=int);parser.add_argument('--samples',type=int,default=20);parser.add_argument('--idle-seconds',type=float,default=2);parser.add_argument('--exercise',action='store_true',help='Explicitly open/close menus; no wallpaper apply, clipboard selection or theme changes');parser.add_argument('--stress',action='store_true');parser.add_argument('--json',action='store_true');parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    if not 1<=args.samples<=200 or not .1<=args.idle_seconds<=60:parser.error('samples 1..200; idle-seconds .1..60')
    if args.stress and not args.exercise:parser.error('--stress requires --exercise')
    rows=panel.shells();row=next((row for row in rows if row['pid']==args.pid),None) if args.pid else panel.current_shell(rows)
    if not row:raise RuntimeError('No owned PixelRail instance; no process started')
    bench=Benchmark(row['pid'])
    try:result=bench.run(args.samples,args.idle_seconds,args.exercise,args.stress)
    finally:
        if args.exercise:
            try:bench.close()
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:print('Benchmark cleanup: '+str(error),file=__import__('sys').stderr)
    if args.baseline:
        old=json.loads(args.baseline.read_text())
        if old.get('schema')!=1 or not isinstance(old.get('timings'),dict):raise ValueError('Unsupported baseline schema')
        result['comparison']={'baseline':str(args.baseline),'rss_delta_difference_mib':result['rss_delta_mib']-old['rss_delta_mib'],'median_difference_ms':{key:value['median_ms']-old['timings'][key]['median_ms'] for key,value in result['timings'].items() if key in old['timings']},'note':'Compare only equivalent workload/backend/mapped state; no significance claim'}
    if args.json:print(json.dumps(result,indent=2))
    else:
        print('PixelRail benchmark · '+BOUNDARY);print('Processes:',result['process_count'],'· RSS:',round(result['initial']['rss_mib'],2),'→',round(result['final']['rss_mib'],2),'MiB')
        for row in result['memory']:print(row['stage'],'RSS',round(row['rss_mib'],2),'MiB · CPU',round(row['cpu_percent_one_core'],3),'% of one core')
        for name,row in result['timings'].items():print(name,'n='+str(row['n']),'median='+str(round(row['median_ms'],2))+' ms','p95='+str(round(row['p95_ms'],2) if row['p95_ms'] is not None else 'insufficient samples'))
        if args.baseline:print(json.dumps(result['comparison'],indent=2))
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,panel.PanelError) as error:raise SystemExit('PixelRail benchmark: '+str(error))
