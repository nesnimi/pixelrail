"""Statistics, CPU identity and default read-only behavior, without a desktop."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('benchmark_backend',ROOT/'scripts/benchmark.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Tests(unittest.TestCase):
    def test_nearest_rank_p95_and_small_sample(self):
        self.assertIsNone(b.summarize([1,2,3])['p95_ms']);self.assertEqual(b.summarize(list(range(1,21)))['p95_ms'],19)
        self.assertEqual(b.summarize([1,2])['median_ms'],1.5)
    def test_cpu_interval_and_pid_reuse(self):
        before={'start':'1','ticks':100,'time':10};after={'start':'1','ticks':110,'time':12}
        with patch.object(b.os,'sysconf',return_value=100):self.assertEqual(b.interval(before,after),5)
        after['start']='2'
        with self.assertRaises(RuntimeError):b.interval(before,after)
    def test_default_is_read_only(self):
        bench=b.Benchmark(123);state={'pid':123,'start':'1','ticks':1,'time':1,'rss_mib':180}
        with patch.object(b,'process',return_value=state),patch.object(bench,'idle'),patch.object(bench,'call',return_value='{}') as call,patch.object(b.panel,'shells',return_value=[{'pid':123}]):
            result=bench.run(20,1)
            self.assertEqual(result['process_count'],1);self.assertFalse(result['exercise'])
            self.assertTrue(all(row.args==('control','state') for row in call.call_args_list))
    def test_timeout_propagates(self):
        bench=b.Benchmark(123)
        with patch.object(b.subprocess,'run',side_effect=TimeoutError('fixture timeout')):
            with self.assertRaises(TimeoutError):bench.call('control','state')
if __name__=='__main__':unittest.main()
