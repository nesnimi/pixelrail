"""Read-only audit and EPP transactions against temporary sysfs; never live writes."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
audit=load('power_audit',ROOT/'scripts/power_audit.py');epp=load('epp_candidate',ROOT/'extras/power/epp_helper.py')
class Power(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.cache');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.sys=self.base/'sys';self.proc=self.base/'proc';self.proc.mkdir()
        self.cpu=self.sys/'devices/system/cpu/cpufreq';self.state=self.base/'state/state.json'
        self.bat=self.sys/'class/power_supply/BAT1'
        for name,value in {'type':'Battery','status':'Discharging','capacity':'42','power_now':'15000000'}.items():self.put(self.bat/name,value)
        self.put(self.sys/'class/power_supply/AC/type','Mains');self.put(self.sys/'class/power_supply/AC/online','0')
        self.gpu=self.sys/'bus/pci/devices/0000:01:00.0';self.put(self.gpu/'vendor','0x10de')
        for name,value in {'control':'auto','runtime_status':'suspended','runtime_active_time':'100','runtime_suspended_time':'900'}.items():self.put(self.gpu/'power'/name,value)
        for index in range(8):
            for name,value in {'scaling_driver':'intel_pstate','scaling_governor':'powersave','energy_performance_preference':'balance_performance','energy_performance_available_preferences':'default performance balance_performance balance_power power'}.items():self.put(self.cpu/f'policy{index}'/name,value)
        self.tx=epp.Transaction(self.cpu,self.state,'test-boot')
    def put(self,path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value+'\n')
    def snapshot(self):return audit.snapshot(self.sys,self.proc,lambda:{'units':[],'error':None})
    def values(self):return {path.name:(path/'energy_performance_preference').read_text().strip() for path in sorted(self.cpu.glob('policy*'))}
    def test_only_bat1_on_battery(self):
        row=self.snapshot();self.assertEqual(row['source'],'Battery');self.assertNotIn('BAT0',row['batteries'])
        self.assertEqual(row['batteries']['BAT1']['discharge_w'],15);self.assertEqual(row['batteries']['BAT1']['percent'],42)
        self.assertEqual(len(row['cpu']),8)
    def test_portable_summary_bat0_weighted_and_unknown_energy(self):
        self.bat.rename(self.bat.with_name('BAT0'));self.bat=self.bat.with_name('BAT0')
        row=audit.compact({'sample':self.snapshot(),'delta':None})
        self.assertEqual(row['battery_percent'],42);self.assertIsNone(row['BAT1_percent'])
        second=self.bat.with_name('OTHER-BATTERY')
        for name,value in {'type':'Battery','status':'Discharging','capacity':'100','power_now':'2000000'}.items():self.put(second/name,value)
        row=audit.compact({'sample':self.snapshot(),'delta':None});self.assertIsNone(row['battery_percent'])
        for path,value in [(self.bat/'capacity','50'),(self.bat/'energy_now','50000000'),(self.bat/'energy_full','100000000'),(second/'energy_now','10000000'),(second/'energy_full','10000000')]:self.put(path,value)
        row=audit.compact({'sample':self.snapshot(),'delta':None})
        self.assertAlmostEqual(row['battery_percent'],100*60/110);self.assertEqual(row['discharge_w'],17)
    def test_ac_never_reports_charging_draw_as_discharge(self):
        self.put(self.sys/'class/power_supply/AC/online','1')
        for status in ('Charging','Full','Not charging','Unknown'):
            self.put(self.bat/'status',status);row=self.snapshot();self.assertEqual(row['source'],'AC');self.assertIsNone(row['batteries']['BAT1']['discharge_w'])
    def test_missing_power_now(self):
        (self.bat/'power_now').unlink();self.assertIsNone(self.snapshot()['batteries']['BAT1']['discharge_w'])
        self.put(self.bat/'current_now','1000000');self.put(self.bat/'voltage_now','12000000')
        self.assertEqual(self.snapshot()['batteries']['BAT1']['discharge_w'],12)
    def test_missing_epp_and_runtime_pm(self):
        (self.cpu/'policy7/energy_performance_preference').unlink()
        for path in (self.gpu/'power').iterdir():path.unlink()
        row=self.snapshot();self.assertIsNone(row['cpu'][7]['epp']);self.assertIsNone(row['nvidia'][0]['status'])
        with self.assertRaises((OSError,epp.EppError)):self.tx.apply('battery')
        self.assertFalse(self.state.exists())
    def test_read_permission_error(self):
        original=Path.read_text
        def denied(path,*args,**kwargs):
            if path==self.cpu/'policy0/energy_performance_preference':raise PermissionError('fixture denied')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',denied):
            row=self.snapshot();self.assertIsNone(row['cpu'][0]['epp']);self.assertTrue(any('fixture denied' in error for error in row['errors']))
            with self.assertRaises(PermissionError):self.tx.apply('battery')
        self.assertFalse(self.state.exists())
    def test_cpu_and_runtime_counter_deltas(self):
        before=self.snapshot();after=self.snapshot();after['monotonic']=before['monotonic']+2
        before['quickshell']=[{'pid':4,'start':'10','ticks':100,'rss_mib':191}]
        after['quickshell']=[{'pid':4,'start':'10','ticks':100+os.sysconf('SC_CLK_TCK'),'rss_mib':191}]
        after['nvidia'][0]['suspended_ms']=2900
        change=audit.delta(before,after);self.assertEqual(change['quickshell_cpu_percent_one_core']['4'],50)
        self.assertEqual(change['nvidia_delta_ms']['0000:01:00.0']['suspended_ms'],2000)
        after['quickshell'][0]['start']='11';after['nvidia'][0]['suspended_ms']=1
        change=audit.delta(before,after);self.assertIsNone(change['quickshell_cpu_percent_one_core']['4']);self.assertIsNone(change['nvidia_delta_ms']['0000:01:00.0']['suspended_ms'])
    def test_manager_query_failures_not_reported_as_clean(self):
        with patch.object(audit.subprocess,'run',side_effect=PermissionError('denied')):self.assertIn('denied',audit.managers()['error'])
        with patch.object(epp.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'tlp.service loaded active exited TLP\n','')):
            with self.assertRaises(epp.EppError):epp.check_managers()
    def test_finite_jsonl_comparison(self):
        row=self.snapshot();later=self.snapshot();later['monotonic']=row['monotonic']+1
        output=io.StringIO()
        with patch.object(audit,'snapshot',side_effect=[row,later]),patch.object(audit.time,'sleep'),patch.object(sys,'argv',['audit','--jsonl','--samples','2']),redirect_stdout(output):audit.main()
        lines=[json.loads(line) for line in output.getvalue().splitlines()];self.assertEqual(len(lines),2);self.assertIsNotNone(lines[1]['nvidia_delta_ms'])
    def test_plan_read_only(self):
        before=self.values();self.assertEqual(len(self.tx.plan('battery')),8);self.assertEqual(self.values(),before);self.assertFalse(self.state.exists())
    def test_eight_policies_apply_and_restore_original_not_previous_profile(self):
        original=self.values();self.tx.apply('battery');self.assertEqual(set(self.values().values()),{'balance_power'})
        saved=json.loads(self.state.read_text());self.assertEqual(saved['baseline'],original)
        self.tx.apply('performance');self.tx.apply('battery');self.tx.restore();self.assertEqual(self.values(),original)
    def test_unsupported_policy_preflight_no_partial_write(self):
        self.put(self.cpu/'policy7/energy_performance_available_preferences','balance_performance')
        before=self.values()
        with self.assertRaises(epp.EppError):self.tx.apply('battery')
        self.assertEqual(self.values(),before);self.assertFalse(self.state.exists())
    def test_no_governor_or_turbo_changes(self):
        self.put(self.cpu/'policy7/scaling_governor','performance');before=self.values()
        with self.assertRaises(epp.EppError):self.tx.apply('battery')
        self.assertEqual(self.values(),before);self.assertEqual((self.cpu/'policy7/scaling_governor').read_text().strip(),'performance')
    def test_partial_write_failure_rolls_back_and_keeps_baseline(self):
        original=self.values();write=self.tx.write
        def denied(name,value):
            if name=='policy4' and value=='balance_power':raise PermissionError('fixture write denied')
            write(name,value)
        with patch.object(self.tx,'write',side_effect=denied):
            with self.assertRaisesRegex(epp.EppError,'previous values restored'):self.tx.apply('battery')
        self.assertEqual(self.values(),original);saved=json.loads(self.state.read_text());self.assertEqual(saved['baseline'],original);self.assertIsNone(saved['pending'])
    def test_persistent_failure_retains_recoverable_pending(self):
        write=self.tx.write;original=self.values()
        def broken(name,value):
            if name=='policy4' and value=='balance_power':raise PermissionError('apply denied')
            if name=='policy0' and value=='balance_performance':raise PermissionError('rollback denied')
            write(name,value)
        with patch.object(self.tx,'write',side_effect=broken):
            with self.assertRaisesRegex(epp.EppError,'rollback incomplete'):self.tx.apply('battery')
        self.assertEqual(json.loads(self.state.read_text())['pending'],original)
        with self.assertRaisesRegex(epp.EppError,'recover first'):self.tx.apply('performance')
        self.tx.restore(recover=True);self.assertEqual(self.values(),original);self.assertIsNone(json.loads(self.state.read_text())['pending'])
    def test_second_profile_failure_restores_immediate_previous_values(self):
        original=self.values();self.tx.apply('battery');previous=self.values();write=self.tx.write
        def denied(name,value):
            if name=='policy4' and value=='balance_performance':raise PermissionError('second apply denied')
            write(name,value)
        with patch.object(self.tx,'write',side_effect=denied):
            with self.assertRaises(epp.EppError):self.tx.apply('performance')
        self.assertEqual(self.values(),previous);self.assertEqual(json.loads(self.state.read_text())['baseline'],original)
    def test_state_write_failure_precedes_sysfs_changes(self):
        before=self.values()
        with patch.object(epp,'atomic',side_effect=PermissionError('state denied')):
            with self.assertRaises(PermissionError):self.tx.apply('battery')
        self.assertEqual(self.values(),before)
    def test_gate_is_required_even_for_root(self):
        with patch.object(epp.os,'geteuid',return_value=0),patch.object(epp,'trusted'),patch.object(epp,'GATE',self.base/'missing-gate'):
            with self.assertRaisesRegex(epp.EppError,'disabled'):epp.authorize('apply')
        self.assertFalse(self.state.exists())
    def test_interrupted_second_apply_recovers_previous_not_baseline(self):
        original=self.values();self.tx.apply('battery');previous=self.values()
        state=json.loads(self.state.read_text());state['pending']=previous;epp.atomic(self.state,state)
        self.put(self.cpu/'policy0/energy_performance_preference','balance_performance')
        restarted=epp.Transaction(self.cpu,self.state,'test-boot');restarted.restore(recover=True)
        self.assertEqual(self.values(),previous);self.assertEqual(json.loads(self.state.read_text())['baseline'],original)
    def test_no_privileges_and_cli_has_no_root_override(self):
        with patch.object(epp.os,'geteuid',return_value=1000):
            with self.assertRaisesRegex(epp.EppError,'Root-only'):epp.authorize('apply')
        result=subprocess.run([sys.executable,str(ROOT/'extras/power/epp_helper.py'),'apply','battery','--sysroot',str(self.cpu)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(self.state.exists())
    def test_stale_state_or_topology_fail_closed(self):
        self.tx.apply('battery');before=self.values();state=json.loads(self.state.read_text());state['boot_id']='other';epp.atomic(self.state,state)
        with self.assertRaises(epp.EppError):self.tx.restore()
        self.assertEqual(self.values(),before)
        state['boot_id']='test-boot';epp.atomic(self.state,state)
        __import__('shutil').rmtree(self.cpu/'policy7');remaining=self.values()
        with self.assertRaisesRegex(epp.EppError,'topology'):self.tx.apply('performance')
        self.assertEqual(self.values(),remaining)
    def test_audit_does_not_write(self):
        before={str(path):path.read_bytes() for path in self.sys.rglob('*') if path.is_file()}
        self.snapshot();self.assertEqual(before,{str(path):path.read_bytes() for path in self.sys.rglob('*') if path.is_file()})
if __name__=='__main__':unittest.main()
